"""
Audit logging helper. Wraps src/utils/db.py:log_audit so endpoint
handlers don't have to plumb request metadata themselves.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Request

from src.utils.db import log_audit


def audit(
    request: Optional[Request],
    user: Optional[dict],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
) -> None:
    user_id = None
    if user and isinstance(user, dict):
        user_id = user.get("sub") or ("anonymous" if user.get("anonymous") else None)
    ip = None
    user_agent = None
    if request is not None:
        client = getattr(request, "client", None)
        if client and getattr(client, "host", None):
            ip = client.host
        try:
            user_agent = request.headers.get("user-agent")
        except Exception:
            user_agent = None
    log_audit(user_id, action, resource_type, resource_id, ip, user_agent)
