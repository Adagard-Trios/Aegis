"""
Consent records + the require_consent FastAPI dependency.

Schema lives in src/utils/db.py: consent_records table.

A "consent" represents a patient's authorisation for a specific category
of data use (twin simulation, complex diagnosis, FHIR export, research
sharing, …) with a JSON scope describing the data subset + purpose.
Records carry a granted_at + optional expires_at; revocation is a
non-destructive `revoked_at` stamp so the audit trail is preserved.

The `require_consent(consent_type, ...)` factory returns a FastAPI
dependency that 403s when no active consent exists for the patient_id
on the request. Patient-id resolution mirrors the existing
_resolve_patient_id pattern in app.py.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status

from src.utils.db import _pg_connect, _sqlite_connect, _using_postgres, DEFAULT_PATIENT_ID
from src.utils.auth import require_user

logger = logging.getLogger(__name__)


# ─── Consent CRUD ─────────────────────────────────────────────────────────

def grant_consent(
    *,
    patient_id: str,
    consent_type: str,
    scope: Optional[Dict[str, Any]] = None,
    granted_by: Optional[str] = None,
    expires_at: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a new consent record. Returns the created row."""
    rid = uuid.uuid4().hex
    pid = patient_id or DEFAULT_PATIENT_ID
    scope_json = json.dumps(scope or {})
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO consent_records "
                    "(id, patient_id, consent_type, scope, granted_by, expires_at, note) "
                    "VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)",
                    (rid, pid, consent_type, scope_json, granted_by, expires_at, note),
                )
            conn.commit()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO consent_records "
                "(id, patient_id, consent_type, scope, granted_by, expires_at, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rid, pid, consent_type, scope_json, granted_by, expires_at, note),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"consent grant failed: {e}")
    return {
        "id": rid,
        "patient_id": pid,
        "consent_type": consent_type,
        "scope": scope or {},
        "granted_by": granted_by,
        "expires_at": expires_at,
        "note": note,
    }


def revoke_consent(consent_id: str, *, by_user: Optional[str] = None) -> bool:
    """Stamp `revoked_at` on a consent. Returns True iff a row was updated."""
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consent_records SET revoked_at = NOW() "
                    "WHERE id = %s AND revoked_at IS NULL",
                    (consent_id,),
                )
                ok = cur.rowcount > 0
            conn.commit()
            conn.close()
            return ok
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "UPDATE consent_records SET revoked_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND revoked_at IS NULL",
                (consent_id,),
            )
            ok = cur.rowcount > 0
            conn.commit()
            conn.close()
            return ok
    except Exception as e:
        logger.warning(f"consent revoke failed: {e}")
        return False


def list_consents(patient_id: str, *, include_revoked: bool = False) -> List[Dict[str, Any]]:
    pid = patient_id or DEFAULT_PATIENT_ID
    where_extra = "" if include_revoked else " AND revoked_at IS NULL"
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, patient_id, consent_type, scope, granted_by, granted_at, "
                    "expires_at, revoked_at, note FROM consent_records "
                    f"WHERE patient_id = %s{where_extra} ORDER BY granted_at DESC",
                    (pid,),
                )
                rows = cur.fetchall()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, patient_id, consent_type, scope, granted_by, granted_at, "
                "expires_at, revoked_at, note FROM consent_records "
                f"WHERE patient_id = ?{where_extra} ORDER BY granted_at DESC",
                (pid,),
            )
            rows = cur.fetchall()
            conn.close()
        return [_row_to_dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"consent list failed: {e}")
        return []


def _row_to_dict(row) -> Dict[str, Any]:
    scope = row[3]
    if isinstance(scope, str):
        try:
            scope = json.loads(scope) if scope else {}
        except Exception:
            scope = {}
    return {
        "id": row[0],
        "patient_id": row[1],
        "consent_type": row[2],
        "scope": scope or {},
        "granted_by": row[4],
        "granted_at": str(row[5]) if row[5] else None,
        "expires_at": row[6],
        "revoked_at": str(row[7]) if row[7] else None,
        "note": row[8],
    }


def has_active_consent(patient_id: str, consent_type: str) -> Optional[Dict[str, Any]]:
    """Return the most recent active (non-revoked, non-expired) consent
    record for (patient_id, consent_type), or None if no such consent
    exists. Used by require_consent."""
    pid = patient_id or DEFAULT_PATIENT_ID
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        if _using_postgres():
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, patient_id, consent_type, scope, granted_by, granted_at, "
                    "expires_at, revoked_at, note FROM consent_records "
                    "WHERE patient_id = %s AND consent_type = %s "
                    "AND revoked_at IS NULL "
                    "AND (expires_at IS NULL OR expires_at > NOW()) "
                    "ORDER BY granted_at DESC LIMIT 1",
                    (pid, consent_type),
                )
                row = cur.fetchone()
            conn.close()
        else:
            conn = _sqlite_connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, patient_id, consent_type, scope, granted_by, granted_at, "
                "expires_at, revoked_at, note FROM consent_records "
                "WHERE patient_id = ? AND consent_type = ? "
                "AND revoked_at IS NULL "
                "AND (expires_at IS NULL OR expires_at > ?) "
                "ORDER BY granted_at DESC LIMIT 1",
                (pid, consent_type, now_str),
            )
            row = cur.fetchone()
            conn.close()
        if row is None:
            return None
        return _row_to_dict(row)
    except Exception as e:
        logger.warning(f"consent check failed: {e}")
        return None


# ─── FastAPI dependency ────────────────────────────────────────────────────

# Routes that require consent are gated by `MEDVERSE_CONSENT_REQUIRED=true`
# (default OFF for back-compat). When OFF, the dep is a no-op and
# attaches a synthetic "anonymous" consent so downstream handlers can
# still introspect it. When ON, missing consent → 403.

def _consent_required() -> bool:
    import os
    return os.environ.get("MEDVERSE_CONSENT_REQUIRED", "false").lower() in ("1", "true", "yes")


def require_consent(consent_type: str) -> Callable:
    """Factory that returns a FastAPI dependency 403'ing when the active
    patient has no current consent of the given type. The patient_id is
    resolved from a query/body field on the request (?patient_id=...) or
    falls back to DEFAULT_PATIENT_ID — matches the existing
    _resolve_patient_id behaviour in app.py.

    Usage:
        @app.post("/api/digital-twin/scenario",
                  dependencies=[Depends(require_consent("twin_simulation"))])
        async def scenario(...): ...
    """
    async def dep(request: Request, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        if not _consent_required():
            return {"consent_type": consent_type, "consent_required": False, "user": user}
        # Resolve patient_id from query string first, then body.
        pid = request.query_params.get("patient_id")
        if not pid:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    pid = body.get("patient_id")
            except Exception:
                pid = None
        pid = pid or DEFAULT_PATIENT_ID
        consent = has_active_consent(pid, consent_type)
        if consent is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "consent_required",
                    "consent_type": consent_type,
                    "patient_id": pid,
                    "hint": "Grant consent via POST /api/consent first.",
                },
                headers={"WWW-Authenticate": f'Consent type="{consent_type}"'},
            )
        return {"consent": consent, "consent_required": True, "user": user}
    return dep
