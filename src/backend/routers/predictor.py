import threading
from datetime import date
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import settings
from dependencies import _get_s3_client
from ml_adapters.base import MLModelAdapter


router = APIRouter(prefix="/predict", tags=["predict"])


class PredictRequest(BaseModel):
    model_name: str
    start_date: date
    end_date: date


class PredictResponse(BaseModel):
    dates: list[str]
    predictions: list[float]
    model_name: str



def load_features(s3_client, start_date: date, end_date: date) -> pd.DataFrame:
    response = s3_client.get_object(Bucket=settings.minio_bucket, Key="latest/features.parquet")
    df = pd.read_parquet(response["Body"])

    mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
    df = df.loc[mask]

    if "Close" in df.columns:
        df = df.drop(columns=["Close"])

    return df


_adapter: Optional[MLModelAdapter] = None
_adapter_lock = threading.Lock()


def get_adapter() -> MLModelAdapter:
    global _adapter
    if _adapter is None:
        with _adapter_lock:
            if _adapter is None:
                _adapter = MLModelAdapter(settings.mlflow_tracking_uri)
    return _adapter


@router.post("/", response_model=PredictResponse)
def predict(
    request: PredictRequest,
    s3_client=Depends(_get_s3_client),
):
    try:
        features_df = load_features(s3_client, request.start_date, request.end_date)

        adapter = get_adapter()
        predictions = adapter.predict(request.model_name, features_df)

        return PredictResponse(
            dates=[d.strftime("%Y-%m-%d") for d in features_df.index],
            predictions=predictions.tolist(),
            model_name=request.model_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
