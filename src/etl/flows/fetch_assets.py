import argparse
import logging
import time
from datetime import datetime, timedelta

from prefect import flow, task, get_run_logger

from tasks.extract import (
    fetch_brent_history,
    fetch_gold_history,
    fetch_sber_history,
    fetch_usd_rub_history,
)
from tasks.load import load_records
from tasks.transform import transform_records

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_ASSET_CONFIG = {
    "stock": (fetch_sber_history, "stock_prices"),
    "usd_rub": (fetch_usd_rub_history, "usd_rub_prices"),
    "gold": (fetch_gold_history, "gold_prices"),
    "oil": (fetch_brent_history, "oil_prices"),
}


def _chunk_date_range(start_date: str, end_date: str, chunk_days: int = 30):
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    chunks = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((current.isoformat(), chunk_end.isoformat()))
        current = chunk_end + timedelta(days=1)
    return chunks


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def fetch_task(asset_type: str, start: str, end: str) -> list[dict]:
    logger = get_run_logger()
    fetch_func, _ = _ASSET_CONFIG[asset_type]
    logger.info(">>> FETCH %s %s..%s", asset_type, start, end)
    records = fetch_func(start, end)
    logger.info("<<< FETCH %s returned %d raw rows", asset_type, len(records))
    return records


@task(log_prints=True)
def transform_task(records: list[dict], asset_type: str) -> list[dict]:
    logger = get_run_logger()
    logger.info(">>> TRANSFORM %s: %d raw rows", asset_type, len(records))
    clean = transform_records(records, asset_type)
    logger.info("<<< TRANSFORM %s: %d clean rows", asset_type, len(clean))
    return clean


@task(log_prints=True)
def load_task(records: list[dict], table_name: str, db_url: str) -> int:
    logger = get_run_logger()
    logger.info(">>> LOAD %s: %d rows into %s", table_name, len(records), table_name)
    loaded = load_records(records, table_name, db_url)
    logger.info("<<< LOAD %s: %d rows inserted/updated", table_name, loaded)
    return loaded


@flow(name="fetch-all-assets", log_prints=True)
def fetch_all_assets(
    start_date: str,
    end_date: str,
    db_url: str,
    chunk_days: int = 30,
    sleep_seconds: float = 1.5,
):
    logger = get_run_logger()
    total = 0

    for asset_type, (_, table_name) in _ASSET_CONFIG.items():
        chunks = _chunk_date_range(start_date, end_date, chunk_days)
        logger.info("=== ASSET: %s | chunks: %d ===", asset_type, len(chunks))

        asset_total = 0
        for chunk_start, chunk_end in chunks:
            raw = fetch_task(asset_type, chunk_start, chunk_end)
            if not raw:
                logger.warning("EMPTY fetch for %s %s..%s", asset_type, chunk_start, chunk_end)
                continue

            clean = transform_task(raw, asset_type)
            if not clean:
                logger.warning("EMPTY transform for %s %s..%s", asset_type, chunk_start, chunk_end)
                continue

            loaded = load_task(clean, table_name, db_url)
            asset_total += loaded

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        logger.info("=== ASSET %s TOTAL: %d rows ===", asset_type, asset_total)
        total += asset_total

    logger.info("=== GRAND TOTAL: %d rows ===", total)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", required=True)
    parser.add_argument("--end_date", required=True)
    parser.add_argument("--db_url", required=True)
    parser.add_argument("--chunk_days", type=int, default=30)
    parser.add_argument("--sleep_seconds", type=float, default=1.5)
    args = parser.parse_args()

    fetch_all_assets(
        start_date=args.start_date,
        end_date=args.end_date,
        db_url=args.db_url,
        chunk_days=args.chunk_days,
        sleep_seconds=args.sleep_seconds,
    )
