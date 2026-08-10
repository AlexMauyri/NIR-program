import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


_COLUMN_MAP = {
    "stock": {
        "ticker": "SECID",
        "date": "TRADEDATE",
        "open": "OPEN",
        "high": "HIGH",
        "low": "LOW",
        "close": "CLOSE",
    },
    "usd_rub": {
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
    },
    "gold": {
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
    },
    "oil": {
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
    },
}


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ".").replace(" ", ""))
    except InvalidOperation:
        return None


def _to_date(value: Any) -> datetime.date | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, datetime.date):
            return value
        return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def transform_records(records: list[dict], asset_type: str) -> list[dict]:
    mapping = _COLUMN_MAP[asset_type]
    result: list[dict] = []

    for raw in records:
        date_val = _to_date(raw.get(mapping["date"]))
        close_val = _to_decimal(raw.get(mapping["close"]))

        if date_val is None or close_val is None:
            continue

        record: dict[str, Any] = {
            "date": date_val,
            "open": _to_decimal(raw.get(mapping["open"])),
            "high": _to_decimal(raw.get(mapping["high"])),
            "low": _to_decimal(raw.get(mapping["low"])),
            "close": close_val,
        }

        if "ticker" in mapping:
            ticker = raw.get(mapping["ticker"])
            record["ticker"] = str(ticker) if ticker else "SBER"

        result.append(record)

    return result
