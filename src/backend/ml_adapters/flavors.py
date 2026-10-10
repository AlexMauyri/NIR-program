import json

from mlflow.tracking import MlflowClient

SUPPORTED_FLAVORS = {"pytorch", "sklearn", "xgboost"}
FALLBACK_FLAVOR = "pyfunc"


def detect_flavor(model_name: str, version: str, tracking_uri: str) -> str:
    try:
        client = MlflowClient(tracking_uri=tracking_uri)
        mv = client.get_model_version(model_name, str(version))
        history = (mv.tags or {}).get("mlflow.log-model.history")
        if not history:
            return FALLBACK_FLAVOR
        for entry in json.loads(history):
            found = SUPPORTED_FLAVORS & set((entry.get("flavors") or {}).keys())
            if found:
                return sorted(found)[0]
    except Exception:
        return FALLBACK_FLAVOR
    return FALLBACK_FLAVOR
