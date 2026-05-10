"""Initial schema — telemetry + interpretations.

Revision ID: 001_timescale_init
Revises:
Create Date: 2026-04-19

This migration mirrors the existing SQLite schema used by the FastAPI
backend (src/utils/db.py) and works against:

  • TimescaleDB-enabled Postgres (Timescale Cloud, self-hosted) — gets
    hypertables + continuous aggregates + a 30-day retention policy
    on raw telemetry. Best query performance for the history dashboard.
  • Plain Postgres (Neon, Supabase, Render basic_256mb) — gets the same
    base tables + indexes. The Timescale-specific blocks are skipped,
    and `/api/history` falls back to aggregating directly off the
    raw `telemetry` table (slower but functionally identical).

Detection happens at runtime via a probe of `pg_extension`. The
`CREATE EXTENSION` call is wrapped in its own savepoint so a permission
denied (Neon doesn't let you create the extension) doesn't poison the
rest of the migration.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "001_timescale_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _try_enable_timescale() -> bool:
    """Best-effort: attempt to install the timescaledb extension and
    report whether it ended up available. Wrapped in a savepoint so
    a CREATE EXTENSION failure (typical on managed Postgres without
    superuser, e.g. Neon) doesn't abort the surrounding transaction."""
    bind = op.get_bind()
    sp = bind.begin_nested()
    try:
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        sp.commit()
    except Exception:
        sp.rollback()
        return False
    # Verify it's actually available — `CREATE EXTENSION` may have been
    # a no-op on some managed providers that pretend to accept it.
    row = bind.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb' LIMIT 1;")
    ).first()
    return row is not None


def upgrade() -> None:
    has_timescale = _try_enable_timescale()

    # ── Base tables (every Postgres backend gets these) ─────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            id             BIGSERIAL,
            patient_id     TEXT NOT NULL DEFAULT 'default_patient',
            ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
            data           JSONB NOT NULL,
            PRIMARY KEY (id, ts)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_patient_ts ON telemetry (patient_id, ts DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_data_gin ON telemetry USING GIN (data);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS interpretations (
            id             BIGSERIAL,
            patient_id     TEXT NOT NULL DEFAULT 'default_patient',
            ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
            specialty      TEXT NOT NULL,
            findings       TEXT NOT NULL,
            severity       TEXT,
            severity_score REAL,
            PRIMARY KEY (id, ts)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_interp_patient_spec_ts "
        "ON interpretations (patient_id, specialty, ts DESC);"
    )

    if not has_timescale:
        # Plain Postgres path — no hypertables, no continuous aggregates,
        # no retention policy. Done.
        return

    # ── Timescale-only path: hypertables + continuous aggregates ─────
    op.execute("SELECT create_hypertable('telemetry', 'ts', if_not_exists => TRUE);")
    op.execute("SELECT create_hypertable('interpretations', 'ts', if_not_exists => TRUE);")

    # Continuous aggregates require running outside a transaction
    # (CREATE MATERIALIZED VIEW WITH DATA can't be transactional).
    # `op.execute` inside Alembic always wraps in a transaction, so use
    # the AUTOCOMMIT isolation level on a fresh connection.
    bind = op.get_bind()
    autocommit = bind.execution_options(isolation_level="AUTOCOMMIT")
    autocommit.execute(
        text(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_vitals_1m
            WITH (timescaledb.continuous) AS
            SELECT patient_id,
                   time_bucket('1 minute', ts) AS bucket,
                   AVG((data->'vitals'->>'heart_rate')::float)    AS heart_rate_avg,
                   AVG((data->'vitals'->>'spo2')::float)          AS spo2_avg,
                   AVG((data->'vitals'->>'breathing_rate')::float) AS br_avg,
                   AVG((data->'vitals'->>'hrv_rmssd')::float)     AS hrv_avg
              FROM telemetry
             GROUP BY patient_id, bucket
             WITH NO DATA;
            """
        )
    )
    autocommit.execute(
        text(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_vitals_1h
            WITH (timescaledb.continuous) AS
            SELECT patient_id,
                   time_bucket('1 hour', ts) AS bucket,
                   AVG((data->'vitals'->>'heart_rate')::float)    AS heart_rate_avg,
                   AVG((data->'vitals'->>'spo2')::float)          AS spo2_avg,
                   AVG((data->'vitals'->>'breathing_rate')::float) AS br_avg,
                   AVG((data->'vitals'->>'hrv_rmssd')::float)     AS hrv_avg
              FROM telemetry
             GROUP BY patient_id, bucket
             WITH NO DATA;
            """
        )
    )

    # Keep raw telemetry 30 days; minute/hour aggregates indefinitely.
    op.execute(
        "SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists => TRUE);"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_vitals_1h;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_vitals_1m;")
    op.execute("DROP TABLE IF EXISTS interpretations CASCADE;")
    op.execute("DROP TABLE IF EXISTS telemetry CASCADE;")
