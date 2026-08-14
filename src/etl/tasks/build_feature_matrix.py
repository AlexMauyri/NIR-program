from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import talib as ta
from prefect import task

from configs import FeatureParams, FEATURE_CONFIG, REQUIRED_FEATURES
from utils import _get_logger


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a / b).replace([np.inf, -np.inf], np.nan)


def _forward_fill_to_date(df: pd.DataFrame, end_date: date) -> pd.DataFrame:
    df = df.sort_index()
    start_date = df.index.min()
    end_dt = pd.to_datetime(end_date)

    if end_dt < start_date:
        raise ValueError("end_date must be >= minimum date in index")

    full_range = pd.date_range(start=start_date, end=end_dt, freq="D")
    return df.reindex(full_range).ffill()


def _build_external(ext_df: pd.DataFrame, prefix: str, cfg: FeatureParams) -> pd.DataFrame:
    df = ext_df.copy()
    close = df["Close"]
    high = df["High"] if "High" in df.columns else close
    low = df["Low"] if "Low" in df.columns else close
    open_ = df["Open"] if "Open" in df.columns else close

    out = pd.DataFrame(index=df.index)

    for k in range(1, cfg.n_lags + 1):
        out[f"{prefix}_lag_{k}"] = close.shift(k)

    out[f"{prefix}_Open_lag_1"] = open_.shift(1)
    out[f"{prefix}_High_lag_1"] = high.shift(1)
    out[f"{prefix}_Low_lag_1"] = low.shift(1)

    out[f"{prefix}_return_1"] = close.pct_change()
    out[f"{prefix}_log_return_1"] = np.log(close / close.shift(1))

    ema_col = f"{prefix}_EMA_{cfg.ema_period}"
    sma_col = f"{prefix}_SMA_{cfg.sma_period}"
    out[ema_col] = ta.EMA(close, timeperiod=cfg.ema_period)
    out[sma_col] = ta.SMA(close, timeperiod=cfg.sma_period)
    out[f"{prefix}_EMA_SMA_diff"] = out[ema_col] - out[sma_col]

    macd, macd_sig, macd_hist = ta.MACD(
        close,
        fastperiod=cfg.macd_fast,
        slowperiod=cfg.macd_slow,
        signalperiod=cfg.macd_signal,
    )
    out[f"{prefix}_MACD"] = macd
    out[f"{prefix}_MACD_signal"] = macd_sig
    out[f"{prefix}_MACD_hist"] = macd_hist

    out[f"{prefix}_RSI_{cfg.rsi_period}"] = ta.RSI(close, timeperiod=cfg.rsi_period)
    out[f"{prefix}_ROC_{cfg.roc_period}"] = ta.ROC(close, timeperiod=cfg.roc_period)

    slowk, slowd = ta.STOCH(
        high, low, close,
        fastk_period=cfg.stoch_fastk,
        slowk_period=3,
        slowk_matype=0,
        slowd_period=cfg.stoch_slowd,
        slowd_matype=0,
    )
    out[f"{prefix}_Stoch_K"] = slowk
    out[f"{prefix}_Stoch_D"] = slowd

    out[f"{prefix}_Std_{cfg.vol_window}"] = close.rolling(cfg.vol_window).std()
    out[f"{prefix}_ATR"] = ta.ATR(high, low, close, timeperiod=cfg.vol_window)

    out[f"{prefix}_intraday_range"] = high - low
    out[f"{prefix}_relative_range"] = _safe_div(high - low, close)
    out[f"{prefix}_intraday_return"] = close - open_

    return out.replace([np.inf, -np.inf], np.nan)


def _build_target(df: pd.DataFrame, cfg: FeatureParams, target: str = "Close") -> pd.DataFrame:
    out = df.copy()

    for k in range(1, cfg.n_lags + 1):
        out[f"{target}_lag_{k}"] = out[target].shift(k)

    out["Open_lag_1"] = out["Open"].shift(1)
    out["High_lag_1"] = out["High"].shift(1)
    out["Low_lag_1"] = out["Low"].shift(1)

    c1 = out[f"{target}_lag_1"]
    h1 = out["High_lag_1"]
    l1 = out["Low_lag_1"]
    o1 = out["Open_lag_1"]

    out["Log_return_1"] = np.log(c1 / out[f"{target}_lag_2"])
    out["Return_1"] = c1.pct_change()

    ema_col = f"EMA_{cfg.ema_period}"
    sma_col = f"SMA_{cfg.sma_period}"
    out[ema_col] = ta.EMA(c1, timeperiod=cfg.ema_period)
    out[sma_col] = ta.SMA(c1, timeperiod=cfg.sma_period)
    out["EMA_SMA_diff"] = out[ema_col] - out[sma_col]

    macd, macd_sig, macd_hist = ta.MACD(
        c1,
        fastperiod=cfg.macd_fast,
        slowperiod=cfg.macd_slow,
        signalperiod=cfg.macd_signal,
    )
    out["MACD"] = macd
    out["MACD_signal"] = macd_sig
    out["MACD_hist"] = macd_hist

    out[f"RSI_{cfg.rsi_period}"] = ta.RSI(c1, timeperiod=cfg.rsi_period)
    out[f"ROC_{cfg.roc_period}"] = ta.ROC(c1, timeperiod=cfg.roc_period)
    out["Stoch_K"], out["Stoch_D"] = ta.STOCH(
        h1, l1, c1,
        fastk_period=cfg.stoch_fastk,
        slowk_period=3,
        slowd_period=cfg.stoch_slowd,
    )

    out[f"Std_{cfg.vol_window}"] = c1.rolling(cfg.vol_window).std()
    out["ATR"] = ta.ATR(h1, l1, c1, timeperiod=cfg.vol_window)

    out["Intraday_range"] = h1 - l1
    out["Intraday_return"] = c1 - o1
    out["Relative_range"] = _safe_div(h1 - l1, c1)

    return out.replace([np.inf, -np.inf], np.nan)


@task(name="build_feature_matrix", log_prints=True)
def build_feature_matrix(
    raw_data: Dict[str, pd.DataFrame],
    feature_config: Dict[str, FeatureParams],
    target_key: str = "SBER",
    required_features: Optional[List[str]] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    logger = _get_logger()
    required_features = required_features or REQUIRED_FEATURES

    logger.info(">>> BUILD features")

    if end_date is None:
        end_date = max(df.index.max().date() for df in raw_data.values())
    logger.info("ffill end_date: %s", end_date)

    filled_data = {}
    for name, df in raw_data.items():
        before = len(df)
        filled = _forward_fill_to_date(df, end_date)
        after = len(filled)
        logger.info("%s: %d -> %d rows (ffill)", name, before, after)
        filled_data[name] = filled

    target_df = filled_data[target_key]
    external = {k: v for k, v in filled_data.items() if k != target_key}

    out = target_df.copy()
    logger.info("Initial: %d rows x %d cols", len(out), out.shape[1])

    if external:
        logger.info("Processing external factors...")
        for idx, (name, ext_df) in enumerate(external.items(), 1):
            cfg = feature_config.get(name) or feature_config.get(name.upper())
            if cfg is None:
                raise KeyError(
                    f"Parameters for asset '{name}' not found in feature_config. "
                    f"Available: {list(feature_config.keys())}"
                )

            ext_features = _build_external(ext_df, name, cfg)
            ext_features_shifted = ext_features.shift(1)
            n_new = ext_features_shifted.shape[1]

            before = out.shape[1]
            out = out.join(ext_features_shifted, how="left")
            after = out.shape[1]
            logger.info("%s: generated %d features, total cols %d", name, n_new, after)

    cfg = feature_config.get(target_key)
    if cfg is None:
        raise KeyError(
            f"Parameters for target asset '{target_key}' not found in feature_config. "
            f"Available: {list(feature_config.keys())}"
        )
    logger.info("Processing target asset: %s", target_key)
    out = _build_target(out, cfg, target="Close")

    logger.info("Cleanup...")
    for col in ("Open", "High", "Low"):
        if col in out.columns:
            out.drop(columns=[col], inplace=True)

    before_dropna = len(out)
    out.dropna(inplace=True)
    dropped = before_dropna - len(out)
    logger.info("Dropped %d rows with NaNs, remaining %d", dropped, len(out))

    available = set(out.columns)
    missing = [f for f in required_features if f not in available]
    if missing:
        raise KeyError(
            f"Requested features missing from dataframe: {missing}. "
            f"Available: {sorted(available)}"
        )
    keep = ["Close"] + list(required_features)
    out = out[keep]
    logger.info("Filtered to %d features + Close", len(required_features))

    logger.info("<<< BUILD features: %d rows x %d cols", len(out), out.shape[1])
    return out
