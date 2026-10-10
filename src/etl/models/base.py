from abc import ABC, abstractmethod
from typing import Any, Dict
import numpy as np
from configs import ModelConfig

class BaseModelWrapper(ABC):
    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
        self._is_fitted = False

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def framework(self) -> str:
        return self.config.framework

    @abstractmethod
    def fit_with_optuna(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        pass

    @abstractmethod
    def log_to_mlflow(self, run_id: str, signature=None, input_example=None) -> None:
        pass
