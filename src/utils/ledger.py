"""
Append-only hash-chained ledger for high-stakes events.

Schema lives in src/utils/db.py: ledger_events table.

Each event stores:
  - sha256(payload) as `payload_hash`
  - sha256(prev_chain_hash || payload_hash) as `chain_hash`

This means corrupting any historical row breaks the chain at that
sequence number — `verify_chain()` walks the table and reports the
first inconsistency, so an after-the-fact tamper is detectable.

Designed as a clean seam for swapping in a permissioned blockchain
later (e.g. Hyperledger Fabric for the MDTBS dual-layer architecture
in the digital-twin paper). The `LedgerBackend` Protocol below is
what a future BlockchainLedgerBackend would implement; today only
SqlLedgerBackend exists, picked by default in `get_ledger()`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

from src.utils.db import _pg_connect, _sqlite_connect, _using_postgres

logger = logging.getLogger(__name__)


# Categories of event we treat as ledger-worthy. Other audit_log writes
# stay in audit_log only.
LEDGER_EVENT_TYPES = {
    "model_inference",
    "simulation_run",
    "twin_replay",
    "consent_grant",
    "consent_revoke",
    "alert_critical",
    "complex_diagnosis",
}


def _hash_payload(payload: Dict[str, Any]) -> str:
    """sha256(canonical-JSON(payload)) — sort keys for determinism."""
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _chain(prev_chain_hash: str, payload_hash: str) -> str:
    return hashlib.sha256((prev_chain_hash + payload_hash).encode("utf-8")).hexdigest()


# ─── Backend protocol ──────────────────────────────────────────────────────

class LedgerBackend(Protocol):
    """The seam — a future BlockchainLedgerBackend would implement this
    Protocol against (e.g.) a Fabric channel. Today we ship only the SQL
    backend; the design intentionally mirrors the MDTBS paper's two-layer
    ledger split so we can later add an inter-hospital chain on top of
    the per-hospital shard."""

    def append(self, event_type: str, payload: Dict[str, Any], *,
               patient_id: Optional[str] = None,
               user_id: Optional[str] = None) -> Dict[str, Any]: ...

    def list_events(self, *, limit: int = 100,
                    event_type: Optional[str] = None,
                    patient_id: Optional[str] = None) -> List[Dict[str, Any]]: ...

    def verify_chain(self) -> Dict[str, Any]: ...


# ─── SQL backend (default) ────────────────────────────────────────────────

class SqlLedgerBackend:
    """Reads/writes the ledger_events table. Both Postgres + SQLite paths."""

    def append(self, event_type: str, payload: Dict[str, Any], *,
               patient_id: Optional[str] = None,
               user_id: Optional[str] = None) -> Dict[str, Any]:
        payload_hash = _hash_payload(payload)
        prev_chain_hash = self._latest_chain_hash() or ""
        chain_hash = _chain(prev_chain_hash, payload_hash)
        payload_json = json.dumps(payload, default=str)

        try:
            if _using_postgres():
                conn = _pg_connect()
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO ledger_events "
                        "(event_type, patient_id, user_id, payload, payload_hash, chain_hash) "
                        "VALUES (%s, %s, %s, %s::jsonb, %s, %s) "
                        "RETURNING seq, ts",
                        (event_type, patient_id, user_id, payload_json, payload_hash, chain_hash),
                    )
                    seq, ts = cur.fetchone()
                conn.commit()
                conn.close()
            else:
                conn = _sqlite_connect()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO ledger_events "
                    "(event_type, patient_id, user_id, payload, payload_hash, chain_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (event_type, patient_id, user_id, payload_json, payload_hash, chain_hash),
                )
                seq = cur.lastrowid
                ts = None
                conn.commit()
                conn.close()
            return {
                "seq": seq, "ts": str(ts) if ts else None,
                "event_type": event_type,
                "payload_hash": payload_hash,
                "chain_hash": chain_hash,
            }
        except Exception as e:
            logger.warning(f"ledger append failed ({event_type}): {e}")
            return {"seq": None, "error": str(e)}

    def list_events(self, *, limit: int = 100,
                    event_type: Optional[str] = None,
                    patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        where_clauses: List[str] = []
        params: List[Any] = []
        if event_type:
            where_clauses.append("event_type = ?")
            params.append(event_type)
        if patient_id:
            where_clauses.append("patient_id = ?")
            params.append(patient_id)
        where = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        params.append(int(limit))

        sql = (
            "SELECT seq, ts, event_type, patient_id, user_id, payload, payload_hash, chain_hash "
            "FROM ledger_events"
            + where
            + " ORDER BY seq DESC LIMIT ?"
        )

        try:
            if _using_postgres():
                conn = _pg_connect()
                with conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s"), params)
                    rows = cur.fetchall()
                conn.close()
            else:
                conn = _sqlite_connect()
                cur = conn.cursor()
                cur.execute(sql, params)
                rows = cur.fetchall()
                conn.close()
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"ledger list failed: {e}")
            return []

    def verify_chain(self) -> Dict[str, Any]:
        """Walk the table from seq=1 up. Returns {ok: bool, count: N,
        broken_at: <seq>, expected_chain: ..., got_chain: ...}.

        On a tampered row, broken_at is the first seq whose stored
        chain_hash doesn't match the recomputed value. The corresponding
        payload_hash is included so the operator can see exactly what
        changed."""
        try:
            if _using_postgres():
                conn = _pg_connect()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT seq, payload, payload_hash, chain_hash FROM ledger_events "
                        "ORDER BY seq ASC"
                    )
                    rows = cur.fetchall()
                conn.close()
            else:
                conn = _sqlite_connect()
                cur = conn.cursor()
                cur.execute(
                    "SELECT seq, payload, payload_hash, chain_hash FROM ledger_events "
                    "ORDER BY seq ASC"
                )
                rows = cur.fetchall()
                conn.close()
        except Exception as e:
            return {"ok": False, "error": f"read failed: {e}"}

        prev_chain_hash = ""
        for row in rows:
            seq, payload, stored_payload_hash, stored_chain_hash = row
            try:
                payload_dict = payload if isinstance(payload, dict) else json.loads(payload)
            except Exception:
                payload_dict = {}
            recomputed_payload_hash = _hash_payload(payload_dict)
            recomputed_chain_hash = _chain(prev_chain_hash, recomputed_payload_hash)
            if recomputed_payload_hash != stored_payload_hash or recomputed_chain_hash != stored_chain_hash:
                return {
                    "ok": False,
                    "broken_at": seq,
                    "expected_payload_hash": recomputed_payload_hash,
                    "stored_payload_hash": stored_payload_hash,
                    "expected_chain_hash": recomputed_chain_hash,
                    "stored_chain_hash": stored_chain_hash,
                    "verified_count": seq - 1,
                }
            prev_chain_hash = stored_chain_hash
        return {"ok": True, "count": len(rows)}

    # ── internal ─────────────────────────────────────────────────────

    def _latest_chain_hash(self) -> Optional[str]:
        try:
            if _using_postgres():
                conn = _pg_connect()
                with conn.cursor() as cur:
                    cur.execute("SELECT chain_hash FROM ledger_events ORDER BY seq DESC LIMIT 1")
                    row = cur.fetchone()
                conn.close()
            else:
                conn = _sqlite_connect()
                cur = conn.cursor()
                cur.execute("SELECT chain_hash FROM ledger_events ORDER BY seq DESC LIMIT 1")
                row = cur.fetchone()
                conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def _row_to_dict(self, row) -> Dict[str, Any]:
        seq, ts, event_type, patient_id, user_id, payload, payload_hash, chain_hash = row
        if isinstance(payload, str):
            try:
                payload = json.loads(payload) if payload else {}
            except Exception:
                payload = {}
        return {
            "seq": seq,
            "ts": str(ts) if ts else None,
            "event_type": event_type,
            "patient_id": patient_id,
            "user_id": user_id,
            "payload": payload or {},
            "payload_hash": payload_hash,
            "chain_hash": chain_hash,
        }


# ─── Singleton ─────────────────────────────────────────────────────────────

_ledger_singleton: Optional[LedgerBackend] = None


def get_ledger() -> LedgerBackend:
    """Pick the active ledger backend. Default: SqlLedgerBackend.

    Future: when MEDVERSE_LEDGER_BACKEND=blockchain is set, we'd
    instantiate the BlockchainLedgerBackend here. The seam is
    intentionally clean so swapping doesn't require touching the
    callers — every audit-/log-side hook calls `get_ledger().append(...)`
    and that's it.
    """
    global _ledger_singleton
    if _ledger_singleton is None:
        backend = os.environ.get("MEDVERSE_LEDGER_BACKEND", "sql").lower()
        if backend == "sql":
            _ledger_singleton = SqlLedgerBackend()
        else:
            logger.warning(
                f"unsupported MEDVERSE_LEDGER_BACKEND={backend!r}; defaulting to sql"
            )
            _ledger_singleton = SqlLedgerBackend()
    return _ledger_singleton


# Convenience wrapper used at every callsite — keeps callers from
# having to import the backend type.
def append_event(event_type: str, payload: Dict[str, Any], *,
                 patient_id: Optional[str] = None,
                 user_id: Optional[str] = None) -> Dict[str, Any]:
    if event_type not in LEDGER_EVENT_TYPES:
        # Soft-allow — better to log a typo than to silently drop a real event.
        logger.debug(f"ledger event_type {event_type!r} not in known set; recording anyway")
    return get_ledger().append(event_type, payload, patient_id=patient_id, user_id=user_id)


def verify_chain() -> Dict[str, Any]:
    return get_ledger().verify_chain()
