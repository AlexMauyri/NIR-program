import os

from flows.fetch_assets import fetch_all_assets

DEFAULT_DB_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql://admin:admin@localhost:5433/stocks"
)

FLOWS = [
    {
        "flow": fetch_all_assets,
        "name": "daily-etl",
        "cron": "0 9 * * *",
        "parameters": {
            "db_url": DEFAULT_DB_URL,
        },
    },
    {
        "flow": fetch_all_assets,
        "name": "backfill-etl",
        "cron": None,
        "parameters": {
            "start_date": "2020-01-01",
            "db_url": DEFAULT_DB_URL,
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
