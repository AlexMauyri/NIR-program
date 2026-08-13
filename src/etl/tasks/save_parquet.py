import os
import tempfile

import pandas as pd
from datetime import date
from prefect import task, get_run_logger


@task(name="save_parquet")
def save_to_parquet(df: pd.DataFrame, start_date: date, end_date: date) -> str:
    logger = get_run_logger()
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    filename = f"features_{start_str}_{end_str}.parquet"

    logger.info(">>> SAVE parquet: %s", filename)
    local_path = os.path.join(tempfile.gettempdir(), filename)
    df.to_parquet(local_path, index=True, engine="pyarrow")

    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    logger.info("<<< SAVE parquet: %s (%.2f MB)", local_path, size_mb)
    return local_path
