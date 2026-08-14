from datetime import date
from typing import Dict, List, Optional

from prefect import flow

from configs import DBConfig, FEATURE_CONFIG, MinioConfig, REQUIRED_FEATURES
from tasks import extract_from_db, build_feature_matrix, save_dataframe_to_parquet, upload_to_minio
from utils import _get_logger

@flow(name="build_ml_features", log_prints=True)
def build_ml_features(
    start_date: date,
    end_date: date,
    db_config: Optional[DBConfig] = None,
    minio_config: Optional[MinioConfig] = None,
    tables: Optional[Dict[str, str]] = None,
    required_features: Optional[List[str]] = None,
) -> Dict:
    logger = _get_logger()

    db_config = db_config or DBConfig()
    minio_config = minio_config or MinioConfig()
    tables = tables or {
        "SBER": "stock_prices",
        "GOLD": "gold_prices",
        "OIL": "oil_prices",
        "USDRUB": "usd_rub_prices",
    }
    required_features = required_features or REQUIRED_FEATURES

    logger.info("=" * 60)
    logger.info("FLOW: build-ml-features")
    logger.info("Date range: %s — %s", start_date, end_date)
    logger.info("Tables: %s", tables)
    logger.info("Target features (%d): %s", len(required_features), required_features)
    logger.info("=" * 60)

    raw_data = extract_from_db(db_config, tables, start_date, end_date)

    features_df = build_feature_matrix(
        raw_data,
        FEATURE_CONFIG,
        target_key="SBER",
        required_features=required_features,
        end_date=end_date,
    )

    feature_cols = [c for c in features_df.columns if c != "Close"]
    min_date = features_df.index.min().strftime("%Y-%m-%d")
    max_date = features_df.index.max().strftime("%Y-%m-%d")

    logger.info("-" * 60)
    logger.info("RESULT METADATA")
    logger.info("  Rows:               %d", len(features_df))
    logger.info("  Columns:            %d", features_df.shape[1])
    logger.info("  Number of features: %d", len(feature_cols))
    logger.info("  Date range:         %s — %s", min_date, max_date)
    logger.info("  Feature list:       %s", feature_cols)
    logger.info("-" * 60)
    
    filename = f"features_{min_date}_{max_date}.parquet"
    local_path = save_dataframe_to_parquet(features_df, filename)
    
    versioned = f"historical/{filename}"
    latest = "latest/features.parquet"
    upload_to_minio(local_path, versioned, minio_config)
    upload_to_minio(local_path, latest, minio_config)
    
    logger.info("=" * 60)
    logger.info("FLOW COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)

    return {
        "local_path": local_path,
        "rows": len(features_df),
        "cols": features_df.shape[1],
        "features": feature_cols,
        "date_range": [min_date, max_date],
    }


if __name__ == "__main__":
    build_ml_features(
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
    )
