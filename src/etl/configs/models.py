from dataclasses import dataclass, field
from typing import List, Optional, Any
import optuna


@dataclass
class HyperparamSpace:
    name: str
    type: str
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[List[Any]] = None
    log_scale: bool = False

    def suggest(self, trial: optuna.Trial) -> Any:
        if self.type == "int":
            return trial.suggest_int(self.name, int(self.low), int(self.high))
        elif self.type == "float":
            return trial.suggest_float(
                self.name, self.low, self.high, log=self.log_scale
            )
        elif self.type == "categorical":
            return trial.suggest_categorical(self.name, self.choices)
        else:
            raise ValueError(f"Unknown hyperparam type: {self.type}")


@dataclass
class ModelConfig:
    name: str
    display_name: str
    framework: str
    minio_artifact_key: str
    improvement_threshold: float = 0.01

    hyperparam_space: List[HyperparamSpace] = field(default_factory=list)

    fixed_params: dict = field(default_factory=dict)

    optuna_n_trials: int = 50
    optuna_timeout: Optional[int] = None
    optuna_direction: str = "minimize"
    optuna_metric: str = "val_rmse"


MODEL_REGISTRY = [
    ModelConfig(
        name="ridge_baseline",
        display_name="Ridge Regression",
        framework="sklearn",
        minio_artifact_key="models/ridge_baseline.pkl",
        optuna_n_trials=100,
        hyperparam_space=[
            HyperparamSpace("alpha", "float", 1e-4, 10.0, log_scale=True),
        ],
        fixed_params={
            "fit_intercept": True,
            "random_state": 42,
        },
    ),
    ModelConfig(
        name="rf_regressor",
        display_name="Random Forest",
        framework="sklearn",
        minio_artifact_key="models/rf_regressor.pkl",
        optuna_n_trials=100,
        hyperparam_space=[
            HyperparamSpace("n_estimators", "int", 500, 1500),
            HyperparamSpace("max_depth", "int", 5, 30),
            HyperparamSpace("min_samples_split", "int", 2, 20),
            HyperparamSpace("min_samples_leaf", "int", 1, 10),
            HyperparamSpace("max_samples", "float", 0.6, 1.0),
            HyperparamSpace("max_features", "categorical", choices=["sqrt", "log2", 0.3, 0.5, 0.8]),
            HyperparamSpace("min_impurity_decrease", "float", 1e-8, 1e-3, log_scale=True)
        ],
        fixed_params={
            "random_state": 42,
            "n_jobs": -1,
        },
    ),
    ModelConfig(
        name="xgb_regressor",
        display_name="XGBoost Regressor",
        framework="xgboost",
        minio_artifact_key="models/xgb_regressor.json",
        optuna_n_trials=100,
        hyperparam_space=[
            HyperparamSpace("n_estimators", "int", 1000, 2000),
            HyperparamSpace("max_depth", "int", 2, 6),
            HyperparamSpace("learning_rate", "float", 0.005, 0.05, log_scale=True),
            HyperparamSpace("subsample", "float", 0.4, 0.6),
            HyperparamSpace("colsample_bytree", "float", 0.5, 0.8),
            HyperparamSpace("min_child_weight", "float", 5.0, 50.0, log_scale=True),
            HyperparamSpace("gamma", "float", 1e-3, 1.0, log_scale=True),
            HyperparamSpace("reg_alpha", "float", 1e-8, 10.0, log_scale=True),
            HyperparamSpace("reg_lambda", "float", 1e-8, 10.0, log_scale=True),
        ],
        fixed_params={
            "objective": "reg:squarederror",
            "random_state": 42,
            "n_jobs": -1,
            "eval_metric": "rmse",
        },
    ),
]
