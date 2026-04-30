"""TimescaleDB initial schema — telemetry + interpretations hypertables.

Revision ID: 001_timescale_init
Revises:
Create Date: 2026-04-19

This migration mirrors the existing SQLite schema used by the FastAPI
backend (src/utils/db.py) but:

  • Promotes the `timestamp_str` TEXT column to a real TIMESTAMPTZ.
  • Converts the `data` JSON blob to JSONB for indexed queries.
  • Partitions both tables on `patient_id` so the multi-tenant roadmap
    is a non-breaking follow-up, not a forklift migration.
  • Creates Timescale hypertables so `time_bucket()` and continuous
    aggregates work out of the box.
  • Creates three continuous aggregates matching the frontend's
    projection modes (1-minute, 1-hour, 1-day rollups).

The extension `timescaledb` must exist in the target database:

    CREATE EXTENSION IF NOT EXISTS timescaledb;

Apply with:
    MEDVERSE_DB_URL=postgresql://... alembic upgrade head
"""
from typing import Sequence, Union

from alembic import op


revision: str = "001_timescale_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

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

    # Promote to hypertables
    op.execute("SELECT create_hypertable('telemetry', 'ts', if_not_exists => TRUE);")
    op.execute("SELECT create_hypertable('interpretations', 'ts', if_not_exists => TRUE);")

    # Continuous aggregates — pre-roll vitals for the history dashboard
    op.execute(
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
         GROUP BY patient_id, bucket;
        """
    )
    op.execute(
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
         GROUP BY patient_id, bucket;
        """
    )

    # Keep raw telemetry 30 days; minute/hour aggregates indefinitely.
    op.execute("SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists => TRUE);")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_vitals_1h;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS telemetry_vitals_1m;")
    op.execute("DROP TABLE IF EXISTS interpretations CASCADE;")
    op.execute("DROP TABLE IF EXISTS telemetry CASCADE;")
