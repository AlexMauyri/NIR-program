from datetime import date, timedelta

import pandas as pd
from prefect import task

from configs import MinioConfig
from clients import MinioClient

from utils import _get_logger

@task(retries=2, retry_delay_seconds=30, name="fetch_features_from_minio")
def fetch_features_from_minio(
    minio_config: MinioConfig,
    months_back: int = 24,
) -> pd.DataFrame:
    logger = _get_logger()

    client = MinioClient(minio_config)
    logger.info("Fetching features from MinIO: %s", client.config.endpoint_url)

    data = client.download_to_memory("latest/features.parquet")
    df = pd.read_parquet(pd.io.common.BytesIO(data))
    
    cutoff_date = pd.Timestamp(date.today() - timedelta(days=30 * months_back))
    df = df[df.index >= cutoff_date]

    logger.info(
        "Loaded features: %d rows x %d cols, range %s to %s",
        len(df), df.shape[1],
        df.index.min().strftime("%Y-%m-%d"),
        df.index.max().strftime("%Y-%m-%d"),
    )

    return df
