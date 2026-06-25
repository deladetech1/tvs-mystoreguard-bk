"""Shared helpers for the tasks & workflow-templates entities.

Resolves core-platform groups/users so a step that targets a GROUP can be
expanded to the individual users who should be notified or who may claim it.
"""
from typing import List, Optional
from src.configs.settings import db_settings


def resolve_group_member_ids(cursor, tenant_id: str, group_id: str) -> List[str]:
    """Return the active user ids that belong to a core-platform group."""
    cursor.execute(
        f"""SELECT user_id FROM {db_settings.CORE_PLATFORM_USER_GROUPS_TABLE}
        WHERE group_id = %s AND tenant_id = %s
        AND is_active = true AND delete_status = 'NOT_DELETED'""",
        (group_id, tenant_id),
    )
    return [row["user_id"] for row in cursor.fetchall() if row.get("user_id")]


def user_in_group(cursor, tenant_id: str, group_id: str, user_id: str) -> bool:
    """True if user_id is an active member of group_id."""
    cursor.execute(
        f"""SELECT 1 FROM {db_settings.CORE_PLATFORM_USER_GROUPS_TABLE}
        WHERE group_id = %s AND tenant_id = %s AND user_id = %s
        AND is_active = true AND delete_status = 'NOT_DELETED'
        LIMIT 1""",
        (group_id, tenant_id, user_id),
    )
    return cursor.fetchone() is not None


def resolve_target_name(cursor, tenant_id: str, target_type: str, target_id: str) -> Optional[str]:
    """Human-readable name for a USER (fullname) or GROUP (group_name)."""
    if target_type == "USER":
        cursor.execute(
            f"SELECT fullname FROM {db_settings.CORE_PLATFORM_USERS_TABLE} WHERE id = %s AND tenant_id = %s",
            (target_id, tenant_id),
        )
        row = cursor.fetchone()
        return row["fullname"] if row else None
    if target_type == "GROUP":
        cursor.execute(
            f"SELECT group_name FROM {db_settings.CORE_PLATFORM_GROUPS_TABLE} WHERE id = %s AND tenant_id = %s",
            (target_id, tenant_id),
        )
        row = cursor.fetchone()
        return row["group_name"] if row else None
    return None


def expand_targets_to_user_ids(cursor, tenant_id: str, targets: List[dict]) -> List[str]:
    """Given target rows (each with target_type/target_id), return the distinct
    set of user ids: USER targets as-is, GROUP targets expanded to members."""
    user_ids = set()
    for t in targets:
        if t["target_type"] == "USER":
            user_ids.add(t["target_id"])
        elif t["target_type"] == "GROUP":
            user_ids.update(resolve_group_member_ids(cursor, tenant_id, t["target_id"]))
    return list(user_ids)
