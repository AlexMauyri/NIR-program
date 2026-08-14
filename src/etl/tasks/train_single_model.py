from typing import Dict, Optional
import tempfile
import os
from configs.minio_config import MinioConfig
import pandas as pd
import numpy as np
from prefect import task
import mlflow

from configs import ModelConfig, MLFlowConfig, MinioConfig
from models import create_model
from tasks import calculate_metrics, upload_to_minio
from clients import MLFlowModelManager

from utils import _get_logger


def _make_decision(
    new_rmse: float,
    prod_rmse: float,
    threshold: float,
) -> tuple[bool, float]:
    if prod_rmse == float("inf"):
        return True, 1.0
    improvement = (prod_rmse - new_rmse) / prod_rmse
    return improvement > threshold, improvement


def _log_results(
    logger,
    test_metrics: Dict[str, float],
    improvement: float,
    threshold: float,
):
    logger.info("-" * 60)
    logger.info("RESULTS:")
    logger.info("  Test RMSE:     %.6f", test_metrics["rmse"])
    logger.info("  Test MAE:      %.6f", test_metrics["mae"])
    logger.info("  Test MAPE:     %.4f%%", test_metrics["mape"])
    logger.info("  Direction Acc: %.4f", test_metrics["direction_accuracy"])
    logger.info("  Improvement:   %.2f%%", improvement * 100)
    logger.info("  Threshold:     %.2f%%", threshold * 100)
    logger.info("-" * 60)


@task(name="train_single_model", log_prints=True)
def train_single_model(
    model_config: ModelConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    mlflow_manager: Optional[MLFlowModelManager] = None,
    minio_config: Optional[MinioConfig] = None,
) -> Dict:
    logger = _get_logger()
    model_name = model_config.name

    logger.info("=" * 60)
    logger.info("MODEL: %s", model_config.display_name)
    logger.info("Framework: %s | Optuna trials: %d",
                model_config.framework, model_config.optuna_n_trials)
    logger.info("Hyperparameter space:")
    for space in model_config.hyperparam_space:
        if space.type == "categorical":
            logger.info("  %s: categorical %s", space.name, space.choices)
        else:
            logger.info("  %s: %s [%s, %s]%s",
                       space.name, space.type, space.low, space.high,
                       " (log)" if space.log_scale else "")
    logger.info("=" * 60)

    prod_version = mlflow_manager.get_production_version(model_name) if mlflow_manager else None
    prod_rmse = prod_version["metrics"].get("test_rmse", float("inf")) if prod_version else float("inf")
    logger.info("Current Production RMSE: %.6f", prod_rmse)

    wrapper = create_model(model_config)

    with mlflow.start_run(run_name=f"train_{model_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_params({
            f"search_{s.name}": f"{s.type}[{s.low or ''}-{s.high or ''}]"
            for s in model_config.hyperparam_space
        })
        mlflow.log_param("optuna_n_trials", model_config.optuna_n_trials)
        mlflow.log_param("framework", model_config.framework)

        training_result = wrapper.fit_with_optuna(X_train, y_train, X_val, y_val)

        mlflow.log_params({f"optuna_{k}": v for k, v in training_result["final_params"].items()})
        mlflow.log_metric("optuna_best_cv_rmse", training_result["optuna_best_value"])
        mlflow.log_metric("optuna_n_trials", training_result["optuna_n_trials"])

        y_pred = wrapper.predict(X_test)
        test_metrics = calculate_metrics.fn(y_test, y_pred)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        suffix = f".{model_config.minio_artifact_key.split('.')[-1]}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            wrapper.save(tmp.name)
            upload_to_minio.fn(tmp.name, model_config.minio_artifact_key, minio_config)
            os.unlink(tmp.name)

        model_id = wrapper.log_to_mlflow(mlflow.active_run().info.run_id)

        new_rmse = test_metrics["rmse"]
        should_promote, improvement = _make_decision(
            new_rmse, prod_rmse, model_config.improvement_threshold
        )

        _log_results(logger, test_metrics, improvement, model_config.improvement_threshold)

        new_version = mlflow_manager.register_new_version(
            model_name,
            model_id,
        )

        if should_promote:
            mlflow_manager.archive_old_production(model_name)
            mlflow_manager.set_alias(model_name, new_version, "production")
            status_msg = f"PROMOTED to production alias: {model_name} v{new_version}"
        else:
            mlflow_manager.set_alias(model_name, new_version, "archived")
            status_msg = f"ARCHIVED (no improvement): {model_name} v{new_version}"

        logger.info(status_msg)

        return {
            "model": model_name,
            "updated": should_promote,
            "optuna_trials": training_result["optuna_n_trials"],
            "best_params": training_result["final_params"],
            "old_rmse": prod_rmse,
            "new_rmse": new_rmse,
            "improvement_pct": improvement * 100,
            "new_version": new_version,
            "metrics": test_metrics,
        }
