from dataclasses import dataclass
from typing import List, Dict

@dataclass(frozen=True)
class FeatureParams:
    n_lags: int
    ema_period: int
    sma_period: int
    rsi_period: int
    roc_period: int
    vol_window: int
    stoch_fastk: int = 14
    stoch_slowd: int = 3
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

FEATURE_CONFIG: Dict[str, FeatureParams] = {
    "GOLD": FeatureParams(
        n_lags=6,
        ema_period=13,
        sma_period=14,
        rsi_period=11,
        roc_period=4,
        vol_window=11,
    ),
    "OIL": FeatureParams(
        n_lags=4,
        ema_period=9,
        sma_period=14,
        rsi_period=18,
        roc_period=11,
        vol_window=12,
    ),
    "USDRUB": FeatureParams(
        n_lags=5,
        ema_period=13,
        sma_period=12,
        rsi_period=15,
        roc_period=15,
        vol_window=13,
    ),
    "SBER": FeatureParams(
        n_lags=4,
        ema_period=13,
        sma_period=8,
        rsi_period=9,
        roc_period=8,
        vol_window=8,
    ),
}

REQUIRED_FEATURES: List[str] = [
    "High_lag_1",
    "Close_lag_1",
    "Low_lag_1",
    "MACD",
    "USDRUB_EMA_13",
    "OIL_ROC_11",
    "OIL_SMA_14",
    "GOLD_intraday_return",
    "MACD_signal",
    "SMA_8",
    "Open_lag_1",
    "USDRUB_SMA_12",
    "GOLD_MACD_signal",
    "GOLD_EMA_SMA_diff",
    "GOLD_lag_6",
    "ROC_8",
]

