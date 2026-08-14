import os
import tempfile

import pandas as pd
from datetime import date
from prefect import task

from utils import _get_logger


@task(name="save_dataframe_to_parquet")
def save_dataframe_to_parquet(df: pd.DataFrame, filename: str)-> str:
    logger = _get_logger()

    logger.info(">>> SAVE parquet: %s", filename)
    local_path = os.path.join(tempfile.gettempdir(), filename)
    df.to_parquet(local_path, index=True, engine="pyarrow")

    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    logger.info("<<< SAVE parquet: %s (%.2f MB)", local_path, size_mb)
    return local_path
