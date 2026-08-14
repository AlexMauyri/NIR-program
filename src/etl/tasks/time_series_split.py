from typing import Dict

import numpy as np
import pandas as pd
from prefect import task

from utils import _get_logger

@task(name="time_series_split")
def time_series_split(
    df: pd.DataFrame,
    test_ratio: float = 0.2,
) -> Dict[str, np.ndarray]:
    logger = _get_logger()

    df = df.sort_index()
    feature_cols = [c for c in df.columns if c != "Close"]

    split_idx = int(len(df) * (1 - test_ratio))
    
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    val_split_idx = int(len(train_df) * 0.8)
    train_part = train_df.iloc[:val_split_idx]
    val_part = train_df.iloc[val_split_idx:]

    result = {
        "X_train": train_part[feature_cols].values,
        "y_train": train_part["Close"].values,
        "X_val": val_part[feature_cols].values,
        "y_val": val_part["Close"].values,
        "X_test": test_df[feature_cols].values,
        "y_test": test_df["Close"].values,
        "train_dates": train_part.index,
        "val_dates": val_part.index,
        "test_dates": test_df.index,
    }

    logger.info("Split: train=%d, val=%d, test=%d",
                len(result["y_train"]), len(result["y_val"]), len(result["y_test"]))

    return result
