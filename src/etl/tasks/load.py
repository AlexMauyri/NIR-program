import logging
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def load_records(
    records: list[dict[str, Any]],
    table_name: str,
    db_url: str,
) -> int:
    if not records:
        logger.info("No records to load into %s", table_name)
        return 0

    with psycopg.connect(db_url) as conn:
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

    logger.info("Loaded %d records into %s", len(records), table_name)
    return len(records)
