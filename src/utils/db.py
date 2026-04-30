"""
src/utils/db.py

Unified SQLite / PostgreSQL-TimescaleDB persistence layer.

Backend selection:
  • MEDVERSE_DB_URL unset  → SQLite (aegis_local.db in repo root)
  • MEDVERSE_DB_URL set    → PostgreSQL (psycopg2). When the URL is a
    Timescale-enabled database, the schema created by
    alembic/versions/001_timescale_init.py is used directly; otherwise
    plain Postgres works too.

All public helpers take a `patient_id` kwarg so multi-tenant deployments
can partition by patient without touching the HTTP layer. The default
(`"medverse-demo-patient"`) preserves back-compat for existing
single-patient SQLite dbs.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_PATIENT_ID = "medverse-demo-patient"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "aegis_local.db")

# ─── Backend selection ─────────────────────────────────────────────────────


def _db_url() -> Optional[str]:
    url = os.environ.get("MEDVERSE_DB_URL")
    if not url:
        return None
    # Normalize SQLAlchemy-style URLs back to a DBAPI-style one for psycopg2.
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return url


def _using_postgres() -> bool:
    return _db_url() is not None


# Lazy import of psycopg2 so SQLite-only installs don't need it.
def _pg_connect():
    try:
        import psycopg2
    except ImportError as e:
        raise RuntimeError(
            "MEDVERSE_DB_URL is set but psycopg2 is not installed. "
            "`pip install psycopg2-binary>=2.9`"
        ) from e
    return psycopg2.connect(_db_url())


def _sqlite_connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


# ─── Schema init ───────────────────────────────────────────────────────────


def init_db() -> None:
    if _using_postgres():
        # Postgres schema is managed by Alembic (`alembic upgrade head`),
        # so we just smoke-test the connection here.
        try:
            conn = _pg_connect()
            conn.close()
            logger.info("PostgreSQL/Timescale connection OK.")
        except Exception as e:
            logger.error(f"Postgres connection failed: {e}")
        return

    try:
        conn = _sqlite_connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_str   TEXT,
                patient_id      TEXT DEFAULT 'medverse-demo-patient',
                data            JSON
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interpretations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_str   TEXT,
                patient_id      TEXT DEFAULT 'medverse-demo-patient',
                specialty       TEXT,
                findings        TEXT,
                severity        TEXT,
                severity_score  REAL
            )
            """
        )
        # Back-compat: add patient_id column if the table existed before.
        for table in ("telemetry", "interpretations"):
            try:
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN patient_id TEXT DEFAULT 'medverse-demo-patient'"
                )
            except sqlite3.OperationalError:
                pass  # Column already there.
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_telemetry_patient_ts "
            "ON telemetry(patient_id, id DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_interp_patient_spec_ts "
            "ON interpretations(patient_id, specialty, id DESC)"
        )
        conn.commit()
        conn.close()
        logger.info("SQLite database initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite db: {e}")


# ─── Writes ────────────────────────────────────────────────────────────────


def insert_telemetry(snapshot: dict, patient_id: str = DEFAULT_PATIENT_ID) -> None:
    now_str = datetime.now().isoformat()
    payload = json.dumps(snapshot)
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO telemetry (patient_id, ts, data) VALUES (%s, now(), %s::jsonb)",
                (patient_id, payload),
            )
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            conn.execute(
                "INSERT INTO telemetry (timestamp_str, patient_id, data) VALUES (?, ?, ?)",
                (now_str, patient_id, payload),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Failed to insert telemetry: {e}")


def insert_interpretation(
    specialty: str,
    findings: str,
    severity: str,
    severity_score: float,
    patient_id: str = DEFAULT_PATIENT_ID,
) -> None:
    now_str = datetime.now().isoformat()
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO interpretations
                    (patient_id, ts, specialty, findings, severity, severity_score)
                VALUES (%s, now(), %s, %s, %s, %s)
                """,
                (patient_id, specialty, findings, severity, severity_score),
            )
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            conn.execute(
                """
                INSERT INTO interpretations
                    (timestamp_str, patient_id, specialty, findings, severity, severity_score)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (now_str, patient_id, specialty, findings, severity, severity_score),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Failed to insert interpretation: {e}")


# ─── Reads ─────────────────────────────────────────────────────────────────


def get_latest_telemetry(patient_id: str = DEFAULT_PATIENT_ID) -> dict:
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT data FROM telemetry WHERE patient_id=%s ORDER BY ts DESC LIMIT 1",
                (patient_id,),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                val = row[0]
                return val if isinstance(val, dict) else json.loads(val)
        else:
            conn = _sqlite_connect()
            cur = conn.execute(
                "SELECT data FROM telemetry WHERE patient_id=? ORDER BY id DESC LIMIT 1",
                (patient_id,),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
    except Exception as e:
        logger.error(f"Failed to fetch latest telemetry: {e}")
    return {}


def get_latest_interpretations(patient_id: str = DEFAULT_PATIENT_ID) -> Dict[str, Any]:
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT ON (specialty)
                       specialty, findings, severity, severity_score, ts
                  FROM interpretations
                 WHERE patient_id=%s
              ORDER BY specialty, ts DESC
                """,
                (patient_id,),
            )
            rows = cur.fetchall()
            conn.close()
            return {
                r[0]: {
                    "interpretation": r[1],
                    "severity": r[2],
                    "severity_score": r[3],
                    "generated_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
                }
                for r in rows
            }
        else:
            conn = _sqlite_connect()
            cur = conn.execute(
                """
                SELECT specialty, findings, severity, severity_score, timestamp_str
                  FROM interpretations
                 WHERE patient_id=?
                   AND id IN (SELECT MAX(id) FROM interpretations WHERE patient_id=? GROUP BY specialty)
                """,
                (patient_id, patient_id),
            )
            rows = cur.fetchall()
            conn.close()
            return {
                r[0]: {
                    "interpretation": r[1],
                    "severity": r[2],
                    "severity_score": r[3],
                    "generated_at": r[4],
                }
                for r in rows
            }
    except Exception as e:
        logger.error(f"Failed to fetch interpretations: {e}")
    return {}


# ─── History aggregation (for /api/history) ───────────────────────────────


def get_history(
    patient_id: str = DEFAULT_PATIENT_ID,
    resolution: str = "1h",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Rolled-up HR/SpO2/BR/HRV series for the /history dashboard.

    Timescale path uses the matching continuous aggregate view
    (`telemetry_vitals_1m` or `telemetry_vitals_1h`).
    SQLite path aggregates in Python over the `data` JSON blob because
    SQLite has no continuous-aggregate engine.
    """
    try:
        if _using_postgres():
            view = "telemetry_vitals_1m" if resolution == "1m" else "telemetry_vitals_1h"
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT bucket, heart_rate_avg, spo2_avg, br_avg, hrv_avg
                  FROM {view}
                 WHERE patient_id=%s
              ORDER BY bucket DESC
                 LIMIT %s
                """,
                (patient_id, limit),
            )
            rows = cur.fetchall()
            conn.close()
            return [
                {
                    "ts": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
                    "hr": float(r[1]) if r[1] is not None else None,
                    "spo2": float(r[2]) if r[2] is not None else None,
                    "br": float(r[3]) if r[3] is not None else None,
                    "hrv": float(r[4]) if r[4] is not None else None,
                }
                for r in reversed(rows)
            ]

        # SQLite fallback: bucket in Python.
        bucket_sec = 60 if resolution == "1m" else 3600
        conn = _sqlite_connect()
        # Pull a bounded number of recent rows (limit × bucket × ~1 row/sec).
        raw_rows_cap = limit * bucket_sec + 1000
        cur = conn.execute(
            """
            SELECT timestamp_str, data
              FROM telemetry
             WHERE patient_id=?
          ORDER BY id DESC
             LIMIT ?
            """,
            (patient_id, raw_rows_cap),
        )
        raw = cur.fetchall()
        conn.close()

        buckets: Dict[int, Dict[str, List[float]]] = {}
        for ts_str, blob in raw:
            try:
                ts = datetime.fromisoformat(ts_str)
                snap = json.loads(blob)
                vitals = snap.get("vitals") or {}
            except Exception:
                continue
            epoch = int(ts.timestamp())
            key = epoch - (epoch % bucket_sec)
            slot = buckets.setdefault(key, {"hr": [], "spo2": [], "br": [], "hrv": []})
            for metric, snap_key in (
                ("hr", "heart_rate"),
                ("spo2", "spo2"),
                ("br", "breathing_rate"),
                ("hrv", "hrv_rmssd"),
            ):
                v = vitals.get(snap_key)
                if isinstance(v, (int, float)) and v > 0:
                    slot[metric].append(float(v))

        def _avg(xs: List[float]) -> Optional[float]:
            return round(sum(xs) / len(xs), 2) if xs else None

        series = [
            {
                "ts": datetime.fromtimestamp(key).isoformat(),
                "hr": _avg(slot["hr"]),
                "spo2": _avg(slot["spo2"]),
                "br": _avg(slot["br"]),
                "hrv": _avg(slot["hrv"]),
            }
            for key, slot in sorted(buckets.items())
        ]
        return series[-limit:]
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        return []
