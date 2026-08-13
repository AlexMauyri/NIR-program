import pandas as pd
from datetime import date
from typing import Optional, Dict

from prefect import task

from configs import DBConfig
from clients import PostgresReader
from utils import _get_logger


@task(retries=3, retry_delay_seconds=10, name="extract_from_db")
def extract_from_db(
    db_config: DBConfig,
    tables: Dict[str, str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, pd.DataFrame]:
    logger = _get_logger()
    logger.info(">>> EXTRACT raw data: date range %s — %s", start_date, end_date)

    reader = PostgresReader(db_config)
    result = {
        name: reader.read_table(table, start_date=start_date, end_date=end_date)
        for name, table in tables.items()
    }

    total_rows = sum(len(df) for df in result.values())
    logger.info("<<< EXTRACT raw data: %d total rows from %d tables", total_rows, len(result))
    return result
