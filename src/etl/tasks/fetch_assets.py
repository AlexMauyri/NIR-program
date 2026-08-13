import datetime
from typing import Optional

import requests
from prefect import task, get_run_logger


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def _paginated_fetch(url: str, params: dict, session: requests.Session) -> list[dict]:
    logger = get_run_logger()
    records: list[dict] = []
    offset = 0
    while True:
        params["start"] = offset
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        columns = payload["history"]["columns"]
        data = payload["history"]["data"]
        if not data:
            break
        records.extend(dict(zip(columns, row)) for row in data)
        offset += len(data)
    return records


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def fetch_sber_moex(
    start_date: str,
    end_date: str,
    session: Optional[requests.Session] = None,
) -> list[dict]:
    logger = get_run_logger()
    logger.info(">>> FETCH sber %s..%s", start_date, end_date)
    sess = session or requests.Session()
    url = (
        "https://iss.moex.com/iss/history/engines/stock/"
        "markets/shares/securities/SBER.json"
    )
    params = {"from": start_date, "till": end_date}
    records = _paginated_fetch.fn(url, params, sess)
    if session is None:
        sess.close()
    logger.info("<<< FETCH sber returned %d raw rows", len(records))
    return records


def _fetch_yahoo_ohlc(
    ticker: str,
    start_date: str,
    end_date: str,
    session: requests.Session,
) -> list[dict]:
    start_ts = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    end_ts = int(datetime.datetime.strptime(end_date, "%Y-%m-%d").timestamp())

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "period1": start_ts, "period2": end_ts}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resp = session.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()

    payload = resp.json()
    result = payload.get("chart", {}).get("result")
    if not result:
        raise ValueError(f"Yahoo returned empty result for {ticker}: {payload}")

    meta = result[0]
    timestamps = meta["timestamp"]
    quote = meta["indicators"]["quote"][0]

    records: list[dict] = []
    for i, ts in enumerate(timestamps):
        close = quote["close"][i]
        if close is None:
            continue
        records.append(
            {
                "date": datetime.datetime.fromtimestamp(
                    ts, tz=datetime.timezone.utc
                ).strftime("%Y-%m-%d"),
                "open": quote["open"][i],
                "high": quote["high"][i],
                "low": quote["low"][i],
                "close": close,
            }
        )

    return records


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def fetch_usdrub_yahoo(
    start_date: str,
    end_date: str,
    session: Optional[requests.Session] = None,
) -> list[dict]:
    logger = get_run_logger()
    logger.info(">>> FETCH usd_rub %s..%s", start_date, end_date)
    sess = session or requests.Session()
    records = _fetch_yahoo_ohlc("USDRUB=X", start_date, end_date, sess)
    if session is None:
        sess.close()
    logger.info("<<< FETCH usd_rub returned %d raw rows", len(records))
    return records


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def fetch_gold_yahoo(
    start_date: str,
    end_date: str,
    session: Optional[requests.Session] = None,
) -> list[dict]:
    logger = get_run_logger()
    logger.info(">>> FETCH gold %s..%s", start_date, end_date)
    sess = session or requests.Session()
    records = _fetch_yahoo_ohlc("GC=F", start_date, end_date, sess)
    if session is None:
        sess.close()
    logger.info("<<< FETCH gold returned %d raw rows", len(records))
    return records


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def fetch_brent_yahoo(
    start_date: str,
    end_date: str,
    session: Optional[requests.Session] = None,
) -> list[dict]:
    logger = get_run_logger()
    logger.info(">>> FETCH oil %s..%s", start_date, end_date)
    sess = session or requests.Session()
    records = _fetch_yahoo_ohlc("BZ=F", start_date, end_date, sess)
    if session is None:
        sess.close()
    logger.info("<<< FETCH oil returned %d raw rows", len(records))
    return records
