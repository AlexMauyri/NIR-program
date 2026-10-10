import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
import optuna
import mlflow
import mlflow.sklearn

from models import BaseModelWrapper
from clients.optuna_engine import OptunaStudyManager
from typing import Any, Dict

class SklearnModelWrapper(BaseModelWrapper):
    def fit_with_optuna(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> Dict[str, Any]:
        def objective(trial: optuna.Trial) -> float:
            params = {
                space.name: space.suggest(trial)
                for space in self.config.hyperparam_space
            }
            params.update(self.config.fixed_params)

            model = self._create_model(params)

            tscv = TimeSeriesSplit(n_splits=3)
            scores = []

            for tr_idx, vl_idx in tscv.split(X_train):
                X_tr, X_vl = X_train[tr_idx], X_train[vl_idx]
                y_tr, y_vl = y_train[tr_idx], y_train[vl_idx]

                model.fit(X_tr, y_tr)
                pred = model.predict(X_vl)
                rmse = np.sqrt(np.mean((y_vl - pred) ** 2))
                scores.append(rmse)

            return np.mean(scores)

        optuna_manager = OptunaStudyManager(self.config)
        optuna_result = optuna_manager.run_optimization(objective)

        final_params = {**optuna_result["best_params"], **self.config.fixed_params}
        self._model = self._create_model(final_params)
        self._model.fit(X_train, y_train)
        self._is_fitted = True

        train_pred = self._model.predict(X_train)
        val_pred = self._model.predict(X_val)

        return {
            "optuna_best_value": optuna_result["best_value"],
            "optuna_n_trials": optuna_result["n_trials_completed"],
            "final_params": final_params,
            "train_rmse": np.sqrt(np.mean((y_train - train_pred) ** 2)),
            "val_rmse": np.sqrt(np.mean((y_val - val_pred) ** 2)),
        }

    def _create_model(self, params: dict) -> Any:
        if self.config.name == "ridge_baseline":
            return Ridge(**params)
        elif self.config.name == "rf_regressor":
            return RandomForestRegressor(**params)
        else:
            raise ValueError(f"Unknown sklearn model: {self.config.name}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict(X)

    def save(self, path: str) -> None:
        joblib.dump({"model": self._model, "config": self.config}, path)

    def load(self, path: str) -> None:
        data = joblib.load(path)
        self._model = data["model"]
        self._is_fitted = True

    def log_to_mlflow(self, run_id: str, signature=None, input_example=None) -> None:
        logged_model = mlflow.sklearn.log_model(
            self._model,
            name=self.config.name,
            signature=signature,
            input_example=input_example,
        )
        return logged_model.model_id
        
