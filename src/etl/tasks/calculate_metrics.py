from typing import Dict
import numpy as np
from prefect import task


@task(name="calculate_metrics")
def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

    direction_true = np.sign(np.diff(y_true))
    direction_pred = np.sign(np.diff(y_pred))
    direction_accuracy = np.mean(direction_true == direction_pred) if len(y_true) > 1 else 0.0

    return {
        "rmse": float(rmse),
        "mae": float(mae),
        "mape": float(mape),
        "direction_accuracy": float(direction_accuracy),
    }
