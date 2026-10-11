from pathlib import Path

from prefect.filesystems import LocalFileSystem
from flows.daily_etl_pipeline import daily_etl_pipeline
from flows.train_all_models import train_all_models
from configs import DBConfig, MinioConfig, MLFlowConfig


DEFAULT_DB_CONFIG = DBConfig()
DEFAULT_MINIO_CONFIG = MinioConfig()
DEFAULT_MLFLOW_CONFIG = MLFlowConfig()


FLOWS = [
    {
        "flow": daily_etl_pipeline,
        "entrypoint": "flows/daily_etl_pipeline.py:daily_etl_pipeline",
        "name": "daily-etl",
        "cron": "0 9 * * *",
        "parameters": {
            "db_config": DEFAULT_DB_CONFIG,
            "minio_config": DEFAULT_MINIO_CONFIG,
        },
    },
    {
        "flow": daily_etl_pipeline,
        "entrypoint": "flows/daily_etl_pipeline.py:daily_etl_pipeline",
        "name": "backfill-etl",
        "cron": None,
        "parameters": {
            "start_date": "2021-01-01",
            "db_config": DEFAULT_DB_CONFIG,
            "minio_config": DEFAULT_MINIO_CONFIG,
        },
    },
    {
        "flow": train_all_models,
        "entrypoint": "flows/train_all_models.py:train_all_models",
        "name": "monthly-model-retrain",
        "cron": "0 2 1 * *",
        "parameters": {
            "months_back": 24,
            "test_ratio": 0.2,
            "minio_config": DEFAULT_MINIO_CONFIG,
            "mlflow_config": DEFAULT_MLFLOW_CONFIG,
        },
    },
]


def deploy():
    source = str(Path(__file__).parent.resolve())

    for cfg in FLOWS:
        f = cfg["flow"]
        entrypoint = cfg["entrypoint"]
        name = cfg["name"]
        cron = cfg["cron"]
        params = cfg.get("parameters", {})

        print(f"Deploying {name} (entrypoint={entrypoint})...")

        deployment = f.from_source(
            source=source,
            entrypoint=entrypoint,
        ).deploy(
            name=name,
            work_pool_name="default",
            cron=cron,
            parameters=params,
        )

        print(f"Deployed {name} successfully")


if __name__ == "__main__":
    deploy()