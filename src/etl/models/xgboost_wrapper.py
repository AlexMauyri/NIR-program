import numpy as np
import xgboost as xgb
import optuna
import mlflow
import mlflow.xgboost

from models import BaseModelWrapper
from clients.optuna_engine import OptunaStudyManager
from typing import Any, Dict


class XGBoostModelWrapper(BaseModelWrapper):
    def fit_with_optuna(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> Dict[str, Any]:
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_val, label=y_val)

        def objective(trial: optuna.Trial) -> float:
            params = {
                space.name: space.suggest(trial)
                for space in self.config.hyperparam_space
            }
            params.update(self.config.fixed_params)

            num_boost_round = params.pop("n_estimators", 500)

            pruning_callback = optuna.integration.XGBoostPruningCallback(
                trial, "validation-rmse"
            )

            model = xgb.train(
                params,
                dtrain,
                num_boost_round=num_boost_round,
                evals=[(dval, "validation")],
                callbacks=[pruning_callback],
                verbose_eval=False,
            )

            pred = model.predict(dval)
            return np.sqrt(np.mean((y_val - pred) ** 2))

        optuna_manager = OptunaStudyManager(self.config)
        optuna_result = optuna_manager.run_optimization(objective)

        final_params = {**optuna_result["best_params"], **self.config.fixed_params}
        num_boost_round = final_params.pop("n_estimators", 500)

        self._model = xgb.train(
            final_params,
            dtrain,
            num_boost_round=num_boost_round,
            evals=[(dval, "validation")],
            verbose_eval=False,
        )
        self._is_fitted = True

        train_pred = self._model.predict(dtrain)
        val_pred = self._model.predict(dval)

        return {
            "optuna_best_value": optuna_result["best_value"],
            "optuna_n_trials": optuna_result["n_trials_completed"],
            "final_params": final_params,
            "train_rmse": np.sqrt(np.mean((y_train - train_pred) ** 2)),
            "val_rmse": np.sqrt(np.mean((y_val - val_pred) ** 2)),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        dmatrix = xgb.DMatrix(X)
        return self._model.predict(dmatrix)

    def save(self, path: str) -> None:
        self._model.save_model(path)

    def load(self, path: str) -> None:
        self._model = xgb.Booster()
        self._model.load_model(path)
        self._is_fitted = True

    def log_to_mlflow(self, run_id: str, signature=None, input_example=None) -> None:
        logged_model = mlflow.xgboost.log_model(
            self._model,
            name=self.config.name,
            signature=signature,
            input_example=input_example,
        )
        return logged_model.model_id

