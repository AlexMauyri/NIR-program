from datetime import date
from typing import Optional

import mlflow
from mlflow.exceptions import MlflowException
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import settings
from dependencies import _get_s3_client


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


class MLModelAdapter:
    def __init__(self, tracking_uri: str):
        mlflow.set_tracking_uri(tracking_uri)
        self._cache: dict = {}

    def predict(self, model_name: str, features_df: pd.DataFrame) -> np.ndarray:
        cache_key = f"{model_name}:production"
        if cache_key not in self._cache:
            try:
                self._cache[cache_key] = mlflow.pyfunc.load_model(
                    f"models:/{model_name}@production"
                )
            except MlflowException as e:
                if "not found" in str(e).lower():
                    raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found in Registry")
                raise HTTPException(status_code=503, detail=f"MLFlow unavailable: {e}")
        return self._cache[cache_key].predict(features_df)


_adapter: Optional[MLModelAdapter] = None


def get_adapter() -> MLModelAdapter:
    global _adapter
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
