import asyncio
import os
from typing import Any
from logging.config import fileConfig
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from alembic import context

# Garante que os modelos sejam importados para registro no SQLModel.metadata
from src.infrastructure.persistence.models import MessageLogs  # noqa: F401

# Carrega variáveis de ambiente dos arquivos .env e .env.local
load_dotenv(".env.local")
load_dotenv(".env")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = SQLModel.metadata

# Sobrescreve a URL do banco com o valor das variáveis de ambiente
db_url = os.getenv("DATABASE_URL")
if db_url:
    # O Alembic as vezes precisa que o driver seja asyncpg se for Postgres
    config.set_main_option("sqlalchemy.url", db_url)


def do_run_migrations(connection: Any) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Configura o connectable assíncrono para execução de migrações online."""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise ValueError("DATABASE_URL não configurada no ambiente ou no alembic.ini")

    # Garante suporte assíncrono
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
