import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base
from alembic import context

config = context.config

with open('/run/secrets/postgres_user') as f:
    db_user = f.read().strip()

with open('/run/secrets/postgres_password') as f:
    password = f.read().strip()

with open('/run/secrets/postgres_host') as f:
    host = f.read().strip()

with open('/run/secrets/postgres_db') as f:
    db = f.read().strip()

url_db = f'postgresql+asyncpg://{db_user}:{password}@{host}:6432/{db}'

if url_db:
    config.set_main_option("sqlalchemy.url", url_db)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramtype": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(url_db, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
