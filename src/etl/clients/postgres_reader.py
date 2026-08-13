from datetime import date
from typing import Optional, Dict, List

import pandas as pd
import psycopg
from psycopg.sql import SQL, Identifier, Placeholder

from configs import DBConfig
from utils import _get_logger


class PostgresReader:
    def __init__(self, config: DBConfig):
        self.config = config

    def read_table(
        self,
        table_name: str,
        date_col: str = "date",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        logger = _get_logger()
        logger.info(f"[Postgres] Reading table `{table_name}` ...")

        where_clauses: List[SQL] = []
        params: Dict[str, date] = {}
        if start_date:
            where_clauses.append(
                SQL("{} >= %(start_date)s").format(Identifier(date_col))
            )
            params["start_date"] = start_date
        if end_date:
            where_clauses.append(
                SQL("{} <= %(end_date)s").format(Identifier(date_col))
            )
            params["end_date"] = end_date

        where_sql = SQL(" AND ").join(where_clauses) if where_clauses else SQL("TRUE")
        query = SQL(
            "SELECT * FROM {} WHERE {} ORDER BY {} ASC"
        ).format(
            Identifier(table_name),
            where_sql,
            Identifier(date_col),
        )

        with psycopg.connect(self.config.connection_string) as conn:
            df = pd.read_sql(query.as_string(conn), conn, params=params)

        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

        drop_cols = [c for c in df.columns if c.lower() in {"ticker", "per", "time"}]
        if drop_cols:
            df.drop(columns=drop_cols, inplace=True)

        rename_map = {}
        for col in df.columns:
            lower = col.lower()
            if lower in {"open", "high", "low", "close"}:
                rename_map[col] = lower.capitalize()
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        required = {"Open", "High", "Low", "Close"}
        missing = required - set(df.columns)
        if missing:
            raise KeyError(
                f"In table `{table_name}` missing columns: {missing}. "
                f"Available: {list(df.columns)}"
            )

        logger.info(
            f"[Postgres] Read {len(df)} rows, "
            f"columns: {df.shape[1]} ({list(df.columns)})"
        )
        return df
