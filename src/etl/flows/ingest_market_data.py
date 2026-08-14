import argparse
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from prefect import flow

from configs import DBConfig
from tasks import (
    fetch_brent_yahoo,
    fetch_gold_yahoo,
    fetch_sber_moex,
    fetch_usdrub_yahoo,
    load_ohlc_to_db,
    transform_ohlc_records,
)
from utils import _get_logger

_ASSET_CONFIG = {
    "stock": (fetch_sber_moex, "stock_prices"),
    "usd_rub": (fetch_usdrub_yahoo, "usd_rub_prices"),
    "gold": (fetch_gold_yahoo, "gold_prices"),
    "oil": (fetch_brent_yahoo, "oil_prices"),
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


def _resolve_dates(start_date: Optional[str], end_date: Optional[str]) -> tuple[str, str]:
    yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()

    if not start_date:
        return yesterday, yesterday

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = (
        datetime.strptime(end_date, "%Y-%m-%d").date()
        if end_date
        else datetime.strptime(yesterday, "%Y-%m-%d").date()
    )

    if not end_date and start < datetime.strptime(yesterday, "%Y-%m-%d").date():
        end = datetime.strptime(yesterday, "%Y-%m-%d").date()

    return start.isoformat(), end.isoformat()


@flow(name="ingest_market_data", log_prints=True)
def ingest_market_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_config: Optional[DBConfig] = None,
    chunk_days: int = 30,
    sleep_seconds: float = 1.5,
):
    logger = _get_logger()

    logger.info("=" * 60)
    logger.info("FLOW: ingest-market-data")
    logger.info("=" * 60)
    
    db_config = db_config or DBConfig()
    start, end = _resolve_dates(start_date, end_date)

    logger.info("Resolved date range: %s to %s", start, end)

    total = 0
    for asset_type, (fetch_func, table_name) in _ASSET_CONFIG.items():
        chunks = _chunk_date_range(start, end, chunk_days)
        logger.info("=== ASSET: %s | chunks: %d ===", asset_type, len(chunks))

        asset_total = 0
        for chunk_start, chunk_end in chunks:
            raw = fetch_func(chunk_start, chunk_end)
            if not raw:
                logger.warning("EMPTY fetch for %s %s..%s", asset_type, chunk_start, chunk_end)
                continue

            clean = transform_ohlc_records(raw, asset_type)
            if not clean:
                logger.warning("EMPTY transform for %s %s..%s", asset_type, chunk_start, chunk_end)
                continue

            loaded = load_ohlc_to_db(clean, table_name, db_config)
            asset_total += loaded

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        logger.info("=== ASSET %s TOTAL: %d rows ===", asset_type, asset_total)
        total += asset_total

    logger.info("=== GRAND TOTAL: %d rows ===", total)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", default=None, help="YYYY-MM-DD or omit for yesterday")
    parser.add_argument("--end_date", default=None, help="YYYY-MM-DD or omit for auto-resolve")
    parser.add_argument("--chunk_days", type=int, default=30)
    parser.add_argument("--sleep_seconds", type=float, default=1.5)
    args = parser.parse_args()

    ingest_market_data(
        start_date=args.start_date,
        end_date=args.end_date,
        chunk_days=args.chunk_days,
        sleep_seconds=args.sleep_seconds,
    )
