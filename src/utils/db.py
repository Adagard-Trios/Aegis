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
DB_PATH = os.environ.get(
    "MEDVERSE_SQLITE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "aegis_local.db"),
)

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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id                      TEXT PRIMARY KEY,
                mrn                     TEXT UNIQUE,
                name                    TEXT NOT NULL,
                dob                     TEXT,
                sex                     TEXT,
                gestational_age_weeks   INTEGER,
                conditions              TEXT,
                assigned_clinician_id   TEXT,
                care_plan_id            TEXT,
                created_at              TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id          TEXT NOT NULL,
                severity            INTEGER NOT NULL,
                source              TEXT,
                message             TEXT,
                snapshot_json       TEXT,
                acknowledged_by     TEXT,
                acknowledged_at     TEXT,
                created_at          TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # ── Phase 3: digital-twin state + simulation runs ────────────
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS twin_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          REAL NOT NULL,
                patient_id  TEXT NOT NULL,
                twin        TEXT NOT NULL,
                state       JSON
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_twin_snapshots_patient_ts "
            "ON twin_snapshots(patient_id, twin, ts DESC)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id           TEXT PRIMARY KEY,
                ts           TEXT DEFAULT CURRENT_TIMESTAMP,
                patient_id   TEXT NOT NULL,
                user_id      TEXT,
                twin         TEXT NOT NULL,
                kind         TEXT,            -- "scenario" | "plan" | "replay"
                params       JSON,
                horizon_min  INTEGER,
                result       JSON
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_simruns_patient_ts "
            "ON simulation_runs(patient_id, ts DESC)"
        )
        # ── Phase 5: consent records + append-only ledger ────────────
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS consent_records (
                id           TEXT PRIMARY KEY,
                patient_id   TEXT NOT NULL,
                consent_type TEXT NOT NULL,           -- "twin_simulation" | "complex_diagnosis" | "fhir_export" | "research" | ...
                scope        JSON,                    -- {"data": [...], "purpose": [...]}
                granted_by   TEXT,
                granted_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at   TEXT,
                revoked_at   TEXT,
                note         TEXT
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_consent_patient_type "
            "ON consent_records(patient_id, consent_type, revoked_at)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_events (
                seq           INTEGER PRIMARY KEY AUTOINCREMENT,
                ts            TEXT DEFAULT CURRENT_TIMESTAMP,
                event_type    TEXT NOT NULL,         -- "model_inference" | "simulation_run" | "consent_grant" | ...
                patient_id    TEXT,
                user_id       TEXT,
                payload       JSON,
                payload_hash  TEXT NOT NULL,         -- sha256(payload)
                chain_hash    TEXT NOT NULL          -- sha256(prev_chain_hash || payload_hash)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_ledger_event_ts "
            "ON ledger_events(event_type, ts DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_ledger_patient_ts "
            "ON ledger_events(patient_id, ts DESC)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ts              TEXT DEFAULT CURRENT_TIMESTAMP,
                user_id         TEXT,
                action          TEXT,
                resource_type   TEXT,
                resource_id     TEXT,
                ip              TEXT,
                user_agent      TEXT
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
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_alerts_patient_ack "
            "ON alerts(patient_id, acknowledged_at, id DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_audit_ts ON audit_log(ts DESC)"
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
            # Aggregate on-the-fly off the raw telemetry table. We
            # deliberately skipped the Timescale continuous aggregates
            # in migration 001 so plain Postgres (Neon, Supabase) works
            # — date_trunc + AVG covers it for our row volumes.
            trunc = "minute" if resolution == "1m" else "hour"
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT date_trunc(%s, ts) AS bucket,
                       AVG((data->'vitals'->>'heart_rate')::float)     AS hr_avg,
                       AVG((data->'vitals'->>'spo2')::float)           AS spo2_avg,
                       AVG((data->'vitals'->>'breathing_rate')::float) AS br_avg,
                       AVG((data->'vitals'->>'hrv_rmssd')::float)      AS hrv_avg
                  FROM telemetry
                 WHERE patient_id=%s
              GROUP BY bucket
              ORDER BY bucket DESC
                 LIMIT %s
                """,
                (trunc, patient_id, limit),
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


# ─── Patients (Phase 3) ────────────────────────────────────────────────────


def _patient_row(r) -> Dict[str, Any]:
    return {
        "id": r[0],
        "mrn": r[1],
        "name": r[2],
        "dob": r[3],
        "sex": r[4],
        "gestational_age_weeks": r[5],
        "conditions": json.loads(r[6]) if r[6] else [],
        "assigned_clinician_id": r[7],
        "care_plan_id": r[8] if len(r) > 8 else None,
        "created_at": str(r[9]) if len(r) > 9 and r[9] else None,
    }


PATIENT_COLS = "id, mrn, name, dob, sex, gestational_age_weeks, conditions, assigned_clinician_id, care_plan_id, created_at"


def list_patients() -> List[Dict[str, Any]]:
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(f"SELECT {PATIENT_COLS} FROM patients ORDER BY created_at DESC")
            rows = cur.fetchall()
            conn.close()
            return [_patient_row(r) for r in rows]
        else:
            conn = _sqlite_connect()
            cur = conn.execute(f"SELECT {PATIENT_COLS} FROM patients ORDER BY created_at DESC")
            rows = cur.fetchall()
            conn.close()
            return [_patient_row(r) for r in rows]
    except Exception as e:
        logger.error(f"list_patients failed: {e}")
        return []


def get_patient(patient_id: str) -> Optional[Dict[str, Any]]:
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(f"SELECT {PATIENT_COLS} FROM patients WHERE id=%s", (patient_id,))
            r = cur.fetchone()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.execute(f"SELECT {PATIENT_COLS} FROM patients WHERE id=?", (patient_id,))
            r = cur.fetchone()
            conn.close()
        return _patient_row(r) if r else None
    except Exception as e:
        logger.error(f"get_patient failed: {e}")
        return None


def upsert_patient(p: Dict[str, Any]) -> Dict[str, Any]:
    pid = p.get("id") or f"pt_{int(datetime.now().timestamp() * 1000)}"
    conditions = json.dumps(p.get("conditions") or [])
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO patients (id, mrn, name, dob, sex, gestational_age_weeks,
                                      conditions, assigned_clinician_id, care_plan_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  mrn=EXCLUDED.mrn, name=EXCLUDED.name, dob=EXCLUDED.dob,
                  sex=EXCLUDED.sex, gestational_age_weeks=EXCLUDED.gestational_age_weeks,
                  conditions=EXCLUDED.conditions,
                  assigned_clinician_id=EXCLUDED.assigned_clinician_id,
                  care_plan_id=EXCLUDED.care_plan_id
                """,
                (pid, p.get("mrn"), p.get("name"), p.get("dob"), p.get("sex"),
                 p.get("gestational_age_weeks"), conditions,
                 p.get("assigned_clinician_id"), p.get("care_plan_id")),
            )
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            conn.execute(
                """
                INSERT OR REPLACE INTO patients
                (id, mrn, name, dob, sex, gestational_age_weeks, conditions,
                 assigned_clinician_id, care_plan_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,
                  COALESCE((SELECT created_at FROM patients WHERE id=?), CURRENT_TIMESTAMP))
                """,
                (pid, p.get("mrn"), p.get("name"), p.get("dob"), p.get("sex"),
                 p.get("gestational_age_weeks"), conditions,
                 p.get("assigned_clinician_id"), p.get("care_plan_id"), pid),
            )
            conn.commit()
            conn.close()
        return get_patient(pid) or {}
    except Exception as e:
        logger.error(f"upsert_patient failed: {e}")
        return {}


# ─── Alerts (Phase 4) ──────────────────────────────────────────────────────


def insert_alert(patient_id: str, severity: int, source: str, message: str,
                 snapshot: Optional[dict] = None) -> int:
    snap_json = json.dumps(snapshot or {})
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO alerts (patient_id, severity, source, message, snapshot_json)
                   VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                (patient_id, severity, source, message, snap_json),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            conn.close()
            return int(new_id)
        else:
            conn = _sqlite_connect()
            cur = conn.execute(
                """INSERT INTO alerts (patient_id, severity, source, message, snapshot_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (patient_id, severity, source, message, snap_json),
            )
            new_id = cur.lastrowid
            conn.commit()
            conn.close()
            return int(new_id) if new_id is not None else 0
    except Exception as e:
        logger.error(f"insert_alert failed: {e}")
        return 0


def list_alerts(patient_id: Optional[str] = None, unacknowledged: bool = False,
                limit: int = 100) -> List[Dict[str, Any]]:
    try:
        clauses = []
        params: List[Any] = []
        if patient_id:
            clauses.append("patient_id=%s" if _using_postgres() else "patient_id=?")
            params.append(patient_id)
        if unacknowledged:
            clauses.append("acknowledged_at IS NULL")
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                f"""SELECT id, patient_id, severity, source, message,
                          acknowledged_by, acknowledged_at, created_at
                       FROM alerts {where}
                   ORDER BY id DESC LIMIT %s""",
                tuple(params + [limit]),
            )
            rows = cur.fetchall()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.execute(
                f"""SELECT id, patient_id, severity, source, message,
                          acknowledged_by, acknowledged_at, created_at
                       FROM alerts {where}
                   ORDER BY id DESC LIMIT ?""",
                tuple(params + [limit]),
            )
            rows = cur.fetchall()
            conn.close()
        return [
            {
                "id": r[0],
                "patient_id": r[1],
                "severity": r[2],
                "source": r[3],
                "message": r[4],
                "acknowledged_by": r[5],
                "acknowledged_at": str(r[6]) if r[6] else None,
                "created_at": str(r[7]) if r[7] else None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"list_alerts failed: {e}")
        return []


def acknowledge_alert(alert_id: int, user_id: str, note: str = "") -> bool:
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                """UPDATE alerts SET acknowledged_by=%s, acknowledged_at=now(),
                                     message = COALESCE(message,'') || CASE WHEN %s != ''
                                       THEN E'\\n[ack note] ' || %s ELSE '' END
                   WHERE id=%s""",
                (user_id, note, note, alert_id),
            )
            updated = cur.rowcount
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.execute(
                """UPDATE alerts SET acknowledged_by=?, acknowledged_at=CURRENT_TIMESTAMP,
                                     message = COALESCE(message,'') || CASE WHEN ?<>''
                                       THEN char(10) || '[ack note] ' || ? ELSE '' END
                   WHERE id=?""",
                (user_id, note, note, alert_id),
            )
            updated = cur.rowcount
            conn.commit()
            conn.close()
        return updated > 0
    except Exception as e:
        logger.error(f"acknowledge_alert failed: {e}")
        return False


def find_recent_alert(patient_id: str, source: str, within_seconds: int = 60) -> bool:
    """Returns True if an alert from `source` for `patient_id` was created in the last `within_seconds`."""
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                """SELECT 1 FROM alerts WHERE patient_id=%s AND source=%s
                   AND created_at > now() - (%s::text || ' seconds')::interval LIMIT 1""",
                (patient_id, source, within_seconds),
            )
            r = cur.fetchone()
            conn.close()
            return r is not None
        else:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(seconds=within_seconds)).isoformat(sep=" ")
            conn = _sqlite_connect()
            cur = conn.execute(
                "SELECT 1 FROM alerts WHERE patient_id=? AND source=? AND created_at>? LIMIT 1",
                (patient_id, source, cutoff),
            )
            r = cur.fetchone()
            conn.close()
            return r is not None
    except Exception:
        return False


# ─── Audit log (Phase 8) ───────────────────────────────────────────────────


def log_audit(user_id: Optional[str], action: str, resource_type: str,
              resource_id: Optional[str] = None, ip: Optional[str] = None,
              user_agent: Optional[str] = None) -> None:
    try:
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO audit_log (user_id, action, resource_type, resource_id, ip, user_agent)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (user_id, action, resource_type, resource_id, ip, user_agent),
            )
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            conn.execute(
                """INSERT INTO audit_log (user_id, action, resource_type, resource_id, ip, user_agent)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, action, resource_type, resource_id, ip, user_agent),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"log_audit failed: {e}")


def list_audit(limit: int = 200, user_id: Optional[str] = None,
               action: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        clauses = []
        params: List[Any] = []
        if user_id:
            clauses.append("user_id=%s" if _using_postgres() else "user_id=?")
            params.append(user_id)
        if action:
            clauses.append("action=%s" if _using_postgres() else "action=?")
            params.append(action)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        if _using_postgres():
            conn = _pg_connect()
            cur = conn.cursor()
            cur.execute(
                f"""SELECT id, ts, user_id, action, resource_type, resource_id, ip, user_agent
                       FROM audit_log {where} ORDER BY id DESC LIMIT %s""",
                tuple(params + [limit]),
            )
            rows = cur.fetchall()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.execute(
                f"""SELECT id, ts, user_id, action, resource_type, resource_id, ip, user_agent
                       FROM audit_log {where} ORDER BY id DESC LIMIT ?""",
                tuple(params + [limit]),
            )
            rows = cur.fetchall()
            conn.close()
        return [
            {
                "id": r[0], "ts": str(r[1]) if r[1] else None,
                "user_id": r[2], "action": r[3], "resource_type": r[4],
                "resource_id": r[5], "ip": r[6], "user_agent": r[7],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"list_audit failed: {e}")
        return []
