"""
Persistence layer for digital-twin snapshots + simulation runs.

Two SQLite/Postgres tables, both created in src/utils/db.py:init_db():

  twin_snapshots(id, ts, patient_id, twin, state JSON)
    – append-only timeline of per-patient twin states. The live SSE
      loop writes one row per twin per tick (configurable rate).

  simulation_runs(id, ts, patient_id, user_id, twin, kind, params,
                  horizon_min, result JSON)
    – one row per /api/digital-twin/scenario or /plan invocation;
      `result` holds the full trajectory JSON so /runs/<id>/replay
      can rehydrate the exact same view later.

The functions here intentionally mirror the helper style in src/utils/db.py
(JSON encoding, both Postgres + SQLite paths, gracefully no-op on connect
failure so the live loop never crashes a snapshot write).
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.utils.db import _pg_connect, _sqlite_connect, _using_postgres, DEFAULT_PATIENT_ID

logger = logging.getLogger(__name__)


# ─── twin_snapshots ────────────────────────────────────────────────────────

def write_twin_snapshot(patient_id: str, twin: str, state: Dict[str, Any]) -> None:
    """Append one row per twin per tick. Safe to call from a hot loop —
    failures are logged but never raise."""
    pid = patient_id or DEFAULT_PATIENT_ID
    payload = json.dumps(state, default=str)
    ts = float(state.get("ts") or time.time())
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO twin_snapshots (ts, patient_id, twin, state) "
                    "VALUES (to_timestamp(%s), %s, %s, %s::jsonb)",
                    (ts, pid, twin, payload),
                )
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO twin_snapshots (ts, patient_id, twin, state) "
                "VALUES (?, ?, ?, ?)",
                (ts, pid, twin, payload),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.debug(f"twin_snapshot write skipped: {e}")


def read_twin_timeline(
    patient_id: str,
    twin: str,
    *,
    from_ts: Optional[float] = None,
    to_ts: Optional[float] = None,
    limit: int = 1000,
) -> List[Tuple[float, Dict[str, Any]]]:
    """Return up to `limit` snapshots in chronological order (oldest first)
    for the patient + twin, optionally bounded by [from_ts, to_ts] (epoch
    seconds). Used by GET /api/digital-twin/timeline to drive the time slider."""
    pid = patient_id or DEFAULT_PATIENT_ID
    where_extra: List[str] = []
    params: List[Any] = [pid, twin]
    if from_ts is not None:
        where_extra.append("ts >= ?")
        params.append(float(from_ts))
    if to_ts is not None:
        where_extra.append("ts <= ?")
        params.append(float(to_ts))
    where_clause = " AND ".join(where_extra)
    where_sql = f" AND {where_clause}" if where_clause else ""

    try:
        if _using_postgres():
            # Postgres: ts is a timestamptz, convert via extract(epoch from)
            sql = (
                "SELECT extract(epoch from ts) AS ts_epoch, state "
                "FROM twin_snapshots "
                "WHERE patient_id = %s AND twin = %s"
                + where_sql.replace("?", "%s")
                + " ORDER BY ts ASC LIMIT %s"
            )
            params.append(int(limit))
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            conn.close()
            out: List[Tuple[float, Dict[str, Any]]] = []
            for ts, state in rows:
                state_dict = state if isinstance(state, dict) else json.loads(state)
                out.append((float(ts), state_dict))
            return out
        else:
            sql = (
                "SELECT ts, state FROM twin_snapshots "
                "WHERE patient_id = ? AND twin = ?"
                + where_sql
                + " ORDER BY ts ASC LIMIT ?"
            )
            params.append(int(limit))
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.close()
            out2: List[Tuple[float, Dict[str, Any]]] = []
            for ts, state_str in rows:
                try:
                    out2.append((float(ts), json.loads(state_str) if state_str else {}))
                except Exception:
                    out2.append((float(ts), {}))
            return out2
    except Exception as e:
        logger.warning(f"twin timeline read failed: {e}")
        return []


# ─── simulation_runs ──────────────────────────────────────────────────────

def insert_simulation_run(
    *,
    patient_id: str,
    user_id: Optional[str],
    twin: str,
    kind: str,
    params: Dict[str, Any],
    horizon_min: int,
    result: List[Tuple[float, Dict[str, Any]]],
) -> str:
    """Persist a what-if run + its full trajectory result. Returns the
    new run ID (UUID). The trajectory is stored under `result.trajectory`
    so it's clearly distinguished from any future metadata fields."""
    run_id = uuid.uuid4().hex
    pid = patient_id or DEFAULT_PATIENT_ID
    result_payload = json.dumps(
        {"trajectory": [{"t_s": t, "state": s} for (t, s) in result]},
        default=str,
    )
    params_payload = json.dumps(params, default=str)
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO simulation_runs (id, patient_id, user_id, twin, kind, params, horizon_min, result) "
                    "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)",
                    (run_id, pid, user_id, twin, kind, params_payload, int(horizon_min), result_payload),
                )
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO simulation_runs (id, patient_id, user_id, twin, kind, params, horizon_min, result) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, pid, user_id, twin, kind, params_payload, int(horizon_min), result_payload),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"simulation_run insert failed: {e}")
    return run_id


def get_simulation_run(run_id: str) -> Optional[Dict[str, Any]]:
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, ts, patient_id, user_id, twin, kind, params, horizon_min, result "
                    "FROM simulation_runs WHERE id = %s",
                    (run_id,),
                )
                row = cur.fetchone()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, ts, patient_id, user_id, twin, kind, params, horizon_min, result "
                "FROM simulation_runs WHERE id = ?",
                (run_id,),
            )
            row = cur.fetchone()
            conn.close()
        if not row:
            return None
        params = row[6]
        result = row[8]
        return {
            "id": row[0],
            "ts": str(row[1]),
            "patient_id": row[2],
            "user_id": row[3],
            "twin": row[4],
            "kind": row[5],
            "params": params if isinstance(params, dict) else (json.loads(params) if params else {}),
            "horizon_min": row[7],
            "result": result if isinstance(result, dict) else (json.loads(result) if result else {}),
        }
    except Exception as e:
        logger.warning(f"simulation_run read failed: {e}")
        return None


def list_simulation_runs(patient_id: str, *, limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent runs (newest first) WITHOUT the trajectory payload —
    keeps the listing endpoint cheap. Caller fetches the full result via
    GET /api/digital-twin/runs/<id>."""
    pid = patient_id or DEFAULT_PATIENT_ID
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, ts, twin, kind, horizon_min FROM simulation_runs "
                    "WHERE patient_id = %s ORDER BY ts DESC LIMIT %s",
                    (pid, int(limit)),
                )
                rows = cur.fetchall()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, ts, twin, kind, horizon_min FROM simulation_runs "
                "WHERE patient_id = ? ORDER BY ts DESC LIMIT ?",
                (pid, int(limit)),
            )
            rows = cur.fetchall()
            conn.close()
        return [
            {"id": r[0], "ts": str(r[1]), "twin": r[2], "kind": r[3], "horizon_min": r[4]}
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"simulation_run list failed: {e}")
        return []
