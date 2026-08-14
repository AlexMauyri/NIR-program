from datetime import date
from typing import Dict, Optional

import pandas as pd
from prefect import flow

from configs import MinioConfig, MLFlowConfig, MODEL_REGISTRY
from clients import MLFlowModelManager
from tasks import (
    fetch_features_from_minio,
    time_series_split,
    train_single_model,
)
from utils import _get_logger

@flow(name="train_all_models", log_prints=True)
def train_all_models(
    months_back: int = 24,
    test_ratio: float = 0.2,
    minio_config: Optional[MinioConfig] = None,
    mlflow_config: Optional[MLFlowConfig] = None,
) -> Dict[str, Dict]:
    logger = _get_logger()

    minio_config = minio_config or MinioConfig()
    mlflow_config = mlflow_config or MLFlowConfig()

    mlflow_manager = MLFlowModelManager(
        mlflow_config.tracking_uri,
        mlflow_config.registry_uri,
    )

    logger.info("=" * 70)
    logger.info("FLOW: train-all-models with Optuna")
    logger.info("=" * 70)
    logger.info("Months back: %d | Test ratio: %.0f%%", months_back, test_ratio * 100)
    logger.info("Models: %d", len(MODEL_REGISTRY))
    for cfg in MODEL_REGISTRY:
        logger.info("  - %s (%s, %d trials)",
                   cfg.display_name, cfg.framework, cfg.optuna_n_trials)
    logger.info("=" * 70)

    features_df = fetch_features_from_minio(minio_config, months_back)

    split_data = time_series_split(features_df, test_ratio)

    results = {}
    for model_config in MODEL_REGISTRY:
        result = train_single_model(
            model_config,
            split_data["X_train"], split_data["y_train"],
            split_data["X_val"], split_data["y_val"],
            split_data["X_test"], split_data["y_test"],
            mlflow_manager, minio_config,
        )
        results[model_config.name] = result

    updated = [m for m, r in results.items() if r["updated"]]
    not_updated = [m for m, r in results.items() if not r["updated"]]

    logger.info("=" * 70)
    logger.info("FINAL SUMMARY")
    logger.info("Promoted to Production: %s", updated or "none")
    logger.info("Archived: %s", not_updated or "none")
    for name, res in results.items():
        status = "PROD" if res["updated"] else "ARCH"
        logger.info("  %s %s | RMSE: %.4f | Impr: %.2f%% | Trials: %d",
                   status, name, res["new_rmse"],
                   res["improvement_pct"], res["optuna_trials"])
    logger.info("=" * 70)

    return results


if __name__ == "__main__":
    train_all_models()
