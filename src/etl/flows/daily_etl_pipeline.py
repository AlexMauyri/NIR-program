from datetime import date, timedelta
from typing import Optional

from prefect import flow

from configs import DBConfig, FEATURE_CONFIG, MinioConfig, REQUIRED_FEATURES
from flows import build_ml_features, ingest_market_data 
from utils import _get_logger

@flow(name="daily_etl_pipeline", log_prints=True)
def daily_etl_pipeline(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_config: Optional[DBConfig] = None,
    minio_config: Optional[MinioConfig] = None,
    chunk_days: int = 60,
    sleep_seconds: float = 1.5,
) -> dict:
    logger = _get_logger()
    
    logger.info("=" * 60)
    logger.info("FLOW: daily_pipeline")
    logger.info("=" * 60)
    
    db_config = db_config or DBConfig()
    minio_config = minio_config or MinioConfig()

    logger.info("--- Step 1: ETL (fetch_all_assets) ---")
    etl_result = ingest_market_data(
        start_date=start_date,
        end_date=end_date,
        db_config=db_config,
        chunk_days=chunk_days,
        sleep_seconds=sleep_seconds,
    )
    logger.info(f"ETL completed: {etl_result} rows loaded")

    logger.info("--- Step 2: Feature Engineering (build_features_flow) ---")

    if start_date:
        feat_start = date.fromisoformat(start_date)
    else:
        feat_start = date.today() - timedelta(days=365 * 4)

    if end_date:
        feat_end = date.fromisoformat(end_date)
    else:
        feat_end = date.today() - timedelta(days=1)

    features_result = build_ml_features(
        start_date=feat_start,
        end_date=feat_end,
        db_config=db_config,
        minio_config=minio_config,
    )
    logger.info(f"Feature Engineering completed: {features_result['rows']} rows")

    logger.info("=" * 60)
    logger.info("DAILY PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)

    return {
        "etl_rows": etl_result,
        "features": features_result,
    }


if __name__ == "__main__":
    daily_etl_pipeline()
