from dataclasses import dataclass
import os


@dataclass
class MLFlowConfig:
    tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    registry_uri: str = os.getenv("MLFLOW_REGISTRY_URI", "http://localhost:5000")
