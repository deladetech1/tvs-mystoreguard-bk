"""
Backdate utility for mystoreguard: only owners, admins, and mystoreguard admins can set a custom datetime.
When occurred_at is null or user lacks the required role, current datetime is used.
Accepts many date formats: ISO (2025-01-02T10:00:00, 2026-01-15T23:00), 2025-01-02, 2 January 2025, etc.
Timezone-aware values (e.g. with Z or +03:00) are normalized to UTC before storage so round-trip is accurate.
"""
from datetime import datetime, timezone
from typing import Optional, Any

from dateutil import parser as dateutil_parser
from trovesuite.utils import Helper

BACKDATE_ALLOWED_ROLES = {
    "role-owner",
    "role-admin",
    "role-subscribed-app-msg-admin",
    "role-msg-admin",
}


def can_backdate(current_user: Any) -> bool:
    """Return True if the current user has a role that permits backdating (owner, admin, or mystoreguard admin)."""
    if not current_user:
        return False
    data = current_user.get("data") if isinstance(current_user, dict) else getattr(current_user, "data", None)
    if not data:
        return False
    for dto in data:
        if not dto:
            continue
        rid = dto.get("role_id") if isinstance(dto, dict) else getattr(dto, "role_id", None)
        if rid and rid in BACKDATE_ALLOWED_ROLES:
            return True
    return False


def _parse_occurred_at(raw: str) -> Optional[datetime]:
    """Parse a date/datetime string into a naive datetime. Returns None on failure."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        if "T" in raw:
            iso = raw.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso)
            except ValueError:
                dt = dateutil_parser.parse(raw)
        elif len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
            if len(raw) >= 19:
                dt = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(raw[:10], "%Y-%m-%d")
        else:
            dt = dateutil_parser.parse(raw)
        # Normalize to UTC when timezone-aware, then store as naive UTC
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def resolve_backdate(
    occurred_at: Optional[str],
    current_user: Any,
) -> dict:
    """
    Resolve datetime for backdating. Only owners, admins, and mystoreguard admins can set a custom datetime.
    Returns dict with keys: cdate (str), ctime (str), cdatetime (datetime).
    If occurred_at is null, invalid, or user lacks the required role, uses current datetime.
    Accepted formats include: 2025-01-02, 2025-01-02T10:00:00, 2 January 2025, 2nd January, 2025.
    Timezone-aware values are converted to UTC; naive values are stored as-is (treated as wall-clock).
    """
    now_dict = Helper.current_date_time()
    if not can_backdate(current_user):
        return now_dict
    if not occurred_at or not str(occurred_at).strip():
        return now_dict
    dt = _parse_occurred_at(str(occurred_at))
    if dt is None:
        return now_dict
    return {
        "cdate": dt.strftime("%Y-%m-%d"),
        "ctime": dt.strftime("%H:%M:%S"),
        "cdatetime": dt,
    }
