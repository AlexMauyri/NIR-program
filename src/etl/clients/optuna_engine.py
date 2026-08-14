from typing import Dict, Any, Callable, Optional
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import HyperbandPruner
import pandas as pd
from prefect import get_run_logger
from configs import ModelConfig

class OptunaStudyManager:
    def __init__(self, config: ModelConfig, storage: Optional[str] = None):
        self.config = config
        self.storage = storage
        self.logger = get_run_logger()

    def create_study(self) -> optuna.Study:
        sampler = TPESampler(seed=42)
        pruner = HyperbandPruner()
        
        study = optuna.create_study(
            direction=self.config.optuna_direction,
            sampler=sampler,
            pruner=pruner,
            storage=self.storage,
            study_name=f"{self.config.name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}",
            load_if_exists=False,
        )
        return study

    def run_optimization(
        self,
        objective_fn: Callable[[optuna.Trial], float],
    ) -> Dict[str, Any]:
        study = self.create_study()

        self.logger.info(
            "Starting Optuna for %s: %d trials",
            self.config.display_name,
            self.config.optuna_n_trials,
        )

        study.optimize(
            objective_fn,
            n_trials=self.config.optuna_n_trials,
            timeout=self.config.optuna_timeout,
            show_progress_bar=False,
            catch=(Exception,),
        )

        best_trial = study.best_trial

        self.logger.info(
            "Optuna done: best value=%.6f (trial #%d)",
            best_trial.value,
            best_trial.number,
        )
        self.logger.info("Best params: %s", best_trial.params)

        return {
            "best_params": best_trial.params,
            "best_value": best_trial.value,
            "n_trials_completed": len(study.trials),
            "study_name": study.study_name,
        }
