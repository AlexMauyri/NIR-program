import os
import threading
from typing import Any, Optional

import mlflow
import mlflow.pyfunc
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import pandas as pd
from fastapi import HTTPException
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from config import settings
from ml_adapters.flavors import detect_flavor


class MLModelAdapter:
    def __init__(self, tracking_uri: str):
        self._tracking_uri = tracking_uri

        # Обеспечиваем доступ MLflow и boto3 к S3/MinIO
        minio_url = settings.minio_endpoint
        if not minio_url.startswith(("http://", "https://")):
            scheme = "https" if settings.minio_use_ssl else "http"
            minio_url = f"{scheme}://{minio_url}"

        s3_endpoint = settings.mlflow_s3_endpoint_url or minio_url
        os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", s3_endpoint)
        if settings.minio_access_key:
            os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.minio_access_key)
        if settings.minio_secret_key:
            os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.minio_secret_key)

        mlflow.set_tracking_uri(tracking_uri)
        self._client = MlflowClient(tracking_uri=tracking_uri)
        self._cache: dict = {}
        self._locks: dict[str, threading.Lock] = {}

    def _load(self, model_uri: str, flavor: str) -> Any:
        if flavor == "pytorch":
            try:
                import torch  # noqa: F401
                from mlflow import pytorch as mlflow_pytorch
            except ImportError:
                raise HTTPException(status_code=501, detail="pytorch not supported")
            return mlflow_pytorch.load_model(model_uri, map_location="cpu")
        if flavor == "sklearn":
            return mlflow.sklearn.load_model(model_uri)
        if flavor == "xgboost":
            return mlflow.xgboost.load_model(model_uri)
        return mlflow.pyfunc.load_model(model_uri)

    @staticmethod
    def _expected_columns(model_uri: str) -> Optional[list[str]]:
        try:
            schema = mlflow.models.get_model_info(model_uri).signature
            schema = schema.inputs if schema is not None else None
            if schema is None or not schema.has_input_names():
                return None
            return list(schema.input_names())
        except Exception:
            return None

    @staticmethod
    def _run(model: Any, flavor: str, df: pd.DataFrame) -> np.ndarray:
        if flavor == "pytorch":
            import torch

            model.eval()
            with torch.no_grad():
                tensor = torch.tensor(df.to_numpy(dtype="float32"))
                out = model(tensor).cpu().numpy()
            return out.reshape(len(df), -1)[:, 0] if out.ndim > 1 else out
        if flavor == "xgboost":
            import xgboost as xgb

            if isinstance(model, xgb.Booster):
                names = getattr(model, "feature_names", None)
                if names is None:
                    return model.predict(xgb.DMatrix(df.values))
                return model.predict(xgb.DMatrix(df.values, feature_names=names))
        return np.asarray(model.predict(df.values))

    def _resolve_version(self, model_name: str) -> tuple[Any, str]:
        """
        Определяет версию модели и её model_uri.
        Сначала пробует alias 'production', при отсутствии делает fallback
        на последнюю зарегистрированную версию (по аналогии с routers/ml_models.py).
        """
        try:
            version_obj = self._client.get_model_version_by_alias(model_name, "production")
            return version_obj, f"models:/{model_name}@production"
        except MlflowException as e:
            if "not found" not in str(e).lower() and "does not exist" not in str(e).lower():
                raise

        # Fallback: поиск по версиям модели
        try:
            versions = self._client.search_model_versions(f"name='{model_name}'")
            if not versions:
                raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found in Registry")
            latest_version = max(versions, key=lambda item: int(item.version))
            return latest_version, f"models:/{model_name}/{latest_version.version}"
        except HTTPException:
            raise
        except MlflowException as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found in Registry")
            raise HTTPException(status_code=503, detail=f"MLFlow unavailable: {e}")

    def predict(self, model_name: str, features_df: pd.DataFrame) -> np.ndarray:
        try:
            version, model_uri = self._resolve_version(model_name)
            cache_key = f"{model_name}:{version.version}"

            if cache_key not in self._cache:
                with self._locks.setdefault(cache_key, threading.Lock()):
                    if cache_key not in self._cache:
                        flavor = detect_flavor(model_name, str(version.version), self._tracking_uri)
                        model = self._load(model_uri, flavor)
                        self._cache[cache_key] = {
                            "model": model,
                            "flavor": flavor,
                            "columns": self._expected_columns(model_uri),
                        }
            entry = self._cache[cache_key]

            mv = self._client.get_model_version(model_name, str(version.version))
            raw = (mv.tags or {}).get("required_features")
            expected_from_tag = raw.split(",") if raw else None
            expected = expected_from_tag or entry["columns"]
            if expected:
                missing = set(expected) - set(features_df.columns)
                if missing:
                    raise HTTPException(status_code=422, detail=f"Missing features: {sorted(missing)}")
                features_df = features_df[expected]

            return self._run(entry["model"], entry["flavor"], features_df)
        except HTTPException:
            raise
        except MlflowException as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found in Registry")
            raise HTTPException(status_code=503, detail=f"MLFlow unavailable: {e}")