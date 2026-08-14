from typing import Optional, Dict
import mlflow
from mlflow.tracking import MlflowClient


class MLFlowModelManager:
    def __init__(self, tracking_uri: str, registry_uri: str):
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_registry_uri(registry_uri)
        self.client = MlflowClient()

    def get_production_version(self, model_name: str) -> Optional[Dict]:
        try:
            versions = self.client.search_model_versions(f"name='{model_name}'")
            for v in versions:
                aliases = self.client.get_model_version(model_name, v.version).aliases
                if "production" in aliases:
                    return {
                        "version": v.version,
                        "run_id": v.run_id,
                        "metrics": self._get_run_metrics(v.run_id),
                    }
            return None
        except Exception:
            return None

    def _get_run_metrics(self, run_id: str) -> Dict:
        run = self.client.get_run(run_id)
        return dict(run.data.metrics)

    def register_new_version(self, model_name: str, model_id: str) -> str:
        mv = mlflow.register_model(f"models:/{model_id}", model_name)
        return mv.version

    def set_alias(self, model_name: str, version: str, alias: str):
        self.client.set_registered_model_alias(
            name=model_name,
            alias=alias,
            version=version,
        )

    def remove_alias(self, model_name: str, alias: str):
        self.client.delete_registered_model_alias(
            name=model_name,
            alias=alias,
        )

    def archive_old_production(self, model_name: str):
        try:
            self.remove_alias(model_name, "production")
        except Exception:
            pass
