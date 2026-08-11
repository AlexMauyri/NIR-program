import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context


DATABASE_URL = os.getenv("DATABASE_URL", "postgres+asyncpg://admin:admin@localhost:5433/stocks") 
# Alembic Config object — читает alembic.ini
config = context.config

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# === МЕТАДАННЫЕ МОДЕЛЕЙ ===
# Импорт Base + явный импорт всех модулей с моделями,
# чтобы SQLAlchemy увидела таблицы и сгенерировала миграции
from models.base import Base
from models import *  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Генерация SQL без живого подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Синхронная функция, которую async connection запустит в отдельном потоке."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Основной async режим — подключается к БД и применяет миграции."""
    configuration = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# === ТОЧКА ВХОДА ===
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
