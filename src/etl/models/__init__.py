from configs import ModelConfig

from .base import BaseModelWrapper
from .sklearn_wrapper import SklearnModelWrapper
from .xgboost_wrapper import XGBoostModelWrapper


WRAPPER_REGISTRY = {
    "sklearn": SklearnModelWrapper,
    "xgboost": XGBoostModelWrapper,
}

def create_model(config: ModelConfig) -> BaseModelWrapper:
    wrapper_cls = WRAPPER_REGISTRY[config.framework]
    return wrapper_cls(config)
