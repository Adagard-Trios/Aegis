"""
Alembic environment for MedVerse.

Driven by the MEDVERSE_DB_URL env var so connection strings never land in
source control. Example:

    MEDVERSE_DB_URL=postgresql://medverse:secret@localhost:5432/medverse

When MEDVERSE_DB_URL is unset, the runtime app uses SQLite directly via
raw sqlite3 + idempotent CREATE TABLE IF NOT EXISTS in init_db() — the
sole Timescale migration here is Postgres-specific and would crash on
SQLite anyway. So this env.py exits cleanly when no Postgres URL is
present, letting `alembic upgrade head` be a safe no-op on SQLite-only
deploys (e.g. Render free tier without managed Postgres).
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url = os.environ.get("MEDVERSE_DB_URL")
if not db_url:
    # No Postgres configured — runtime falls back to SQLite which manages
    # its own schema in src/utils/db.py. Exiting 0 so deploy entrypoints
    # that chain `alembic upgrade head && python app.py` don't break.
    print("[alembic] MEDVERSE_DB_URL not set — skipping migrations (SQLite mode).", file=sys.stderr)
    sys.exit(0)

config.set_main_option("sqlalchemy.url", db_url)

target_metadata = None  # migrations are written as raw SQL


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
