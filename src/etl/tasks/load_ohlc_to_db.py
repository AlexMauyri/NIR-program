import logging
from typing import Any

import psycopg
from prefect import task

from configs import DBConfig
from utils import _get_logger

logger = logging.getLogger(__name__)


@task(log_prints=True)
def load_ohlc_to_db(
    records: list[dict[str, Any]],
    table_name: str,
    db_config: DBConfig,
) -> int:
    logger = _get_logger()
    logger.info(">>> LOAD %s: %d rows into %s", table_name, len(records), table_name)

    if not records:
        logger.info("No records to load into %s", table_name)
        return 0

    with psycopg.connect(db_config.connection_string) as conn:
        with conn.cursor() as cur:
            if "ticker" in records[0]:
                cur.executemany(
                    f"""
                    INSERT INTO {table_name}
                        (ticker, date, open, high, low, close)
                    VALUES
                        (%(ticker)s, %(date)s, %(open)s, %(high)s,
                         %(low)s, %(close)s)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close
                    """,
                    records,
                )
            else:
                cur.executemany(
                    f"""
                    INSERT INTO {table_name}
                        (date, open, high, low, close)
                    VALUES
                        (%(date)s, %(open)s, %(high)s, %(low)s,
                         %(close)s)
                    ON CONFLICT (date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close
                    """,
                    records,
                )

            conn.commit()

    logger.info("<<< LOAD %s: %d rows inserted/updated", table_name, len(records))
    return len(records)
