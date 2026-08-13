import os

from flows import daily_etl_pipeline
from configs import DBConfig, MinioConfig


DEFAULT_DB_CONFIG = DBConfig()
DEFAULT_MINIO_CONFIG = MinioConfig()

FLOWS = [
    {
        "flow": daily_etl_pipeline,
        "name": "daily-etl",
        "cron": "0 9 * * *",
        "parameters": {
            "db_config": DEFAULT_DB_CONFIG,
            "minio_config": DEFAULT_MINIO_CONFIG,
        },
    },
    {
        "flow": daily_etl_pipeline,
        "name": "backfill-etl",
        "cron": None,
        "parameters": {
            "start_date": "2024-01-01",
            "db_config": DEFAULT_DB_CONFIG,
            "minio_config": DEFAULT_MINIO_CONFIG,
        },
    },
]


def deploy():
    for cfg in FLOWS:
        f = cfg["flow"]
        name = cfg["name"]
        cron = cfg["cron"]
        params = cfg.get("parameters", {})

        print(f"Deploying {name} with cron '{cron}'...")

        deployment = f.to_deployment(
            name=name,
            cron=cron,
            parameters=params,
        )
        deployment.apply()

        print(f"Deployed {name} successfully")


if __name__ == "__main__":
    deploy()
