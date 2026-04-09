import asyncio
from logging.config import fileConfig
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.db.base  # noqa: F401 - ensure all models are imported
from alembic import context
from app.core.config import settings

config = context.config

# Support `alembic -x db=test upgrade head` to target the test database.
# Example: cd backend && uv run alembic -x db=test upgrade head
_cmd_kwargs = context.get_x_argument(as_dictionary=True)
if _cmd_kwargs.get("db") == "test":
    _ROOT = Path(__file__).resolve().parents[3]
    _test_env = dotenv_values(_ROOT / ".env.test") or dotenv_values(_ROOT / ".env")
    _db_url = _test_env.get("DATABASE_URL", settings.DATABASE_URL)
else:
    _db_url = settings.DATABASE_URL

config.set_main_option("sqlalchemy.url", _db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db.base_class import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
