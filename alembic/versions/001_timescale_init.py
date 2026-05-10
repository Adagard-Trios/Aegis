"""Initial Postgres schema — telemetry + interpretations.

Revision ID: 001_timescale_init
Revises:
Create Date: 2026-04-19

Mirrors the SQLite schema in src/utils/db.py. Pure vanilla Postgres —
no extensions, no hypertables, no continuous aggregates. Works on every
managed provider we care about (Neon, Supabase, Render basic_256mb,
Timescale Cloud, self-hosted).

If you want TimescaleDB-flavoured perf (hypertables, continuous
aggregates over the telemetry JSONB), add a separate migration on top
of this one — keep this one minimal so it stays widely compatible.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "001_timescale_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_telemetry_patient_ts "
        "ON telemetry (patient_id, ts DESC);"
    )
    # GIN over the JSONB blob — lets `data->'vitals'->>'heart_rate'`
    # filters use an index instead of a full scan once history grows.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_telemetry_data_gin "
        "ON telemetry USING GIN (data);"
    )

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


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS interpretations CASCADE;")
    op.execute("DROP TABLE IF EXISTS telemetry CASCADE;")
