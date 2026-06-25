import logging

from shared.settings import (
    MSG_TASKS_TABLE,
    MSG_TASK_STEPS_TABLE,
    MSG_TASK_STEP_DEPS_TABLE,
    MSG_TASK_STEP_TARGETS_TABLE,
    MSG_TASK_NOTIFICATION_SETTINGS_TABLE,
    MSG_TASK_NOTIFICATIONS_TABLE,
    CP_USERS_TABLE,
    CP_USER_GROUPS_TABLE,
)

logger = logging.getLogger("mystoreguard_functions")

DEFAULT_REMINDER_MINUTES = 120


def generate_due_task_reminders(cursor) -> int:
    """
    Insert REMINDER outbox rows for work still pending on people:
      - assignees of available TODO/IN_PROGRESS steps
      - approvers of DONE steps awaiting approval

    A reminder is only created when the recipient has opted in and no
    notification for that (step, user) exists within their reminder interval,
    which throttles reminders to one per interval. Group targets are expanded
    to their members via cp_user_groups. Returns the number of rows inserted.
    """
    query = f"""
        INSERT INTO {MSG_TASK_NOTIFICATIONS_TABLE}
            (tenant_id, org_id, bus_id, task_id, step_id, recipient_user_id, kind, status)
        SELECT o.tenant_id, o.org_id, o.bus_id, o.task_id, o.step_id, o.user_id, 'REMINDER', 'PENDING'
        FROM (
            -- assignees of available, not-yet-finished steps
            SELECT s.tenant_id, s.org_id, s.bus_id, s.task_id, s.id AS step_id, m.user_id
            FROM {MSG_TASK_STEPS_TABLE} s
            JOIN {MSG_TASK_STEP_TARGETS_TABLE} t
                ON t.step_id = s.id AND t.tenant_id = s.tenant_id AND t.target_kind = 'ASSIGNEE'
            JOIN LATERAL (
                SELECT t.target_id AS user_id WHERE t.target_type = 'USER'
                UNION
                SELECT ug.user_id FROM {CP_USER_GROUPS_TABLE} ug
                WHERE t.target_type = 'GROUP' AND ug.group_id = t.target_id AND ug.tenant_id = s.tenant_id
                    AND ug.is_active = true AND ug.delete_status = 'NOT_DELETED'
            ) m ON true
            WHERE s.status IN ('TODO', 'IN_PROGRESS')
                AND NOT EXISTS (
                    SELECT 1 FROM {MSG_TASK_STEP_DEPS_TABLE} d
                    JOIN {MSG_TASK_STEPS_TABLE} ps ON ps.id = d.depends_on_step_id AND ps.tenant_id = d.tenant_id
                    WHERE d.step_id = s.id AND d.tenant_id = s.tenant_id AND ps.status <> 'COMPLETED'
                )
            UNION
            -- approvers of steps awaiting approval
            SELECT s.tenant_id, s.org_id, s.bus_id, s.task_id, s.id AS step_id, m.user_id
            FROM {MSG_TASK_STEPS_TABLE} s
            JOIN {MSG_TASK_STEP_TARGETS_TABLE} t
                ON t.step_id = s.id AND t.tenant_id = s.tenant_id AND t.target_kind = 'APPROVER'
            JOIN LATERAL (
                SELECT t.target_id AS user_id WHERE t.target_type = 'USER'
                UNION
                SELECT ug.user_id FROM {CP_USER_GROUPS_TABLE} ug
                WHERE t.target_type = 'GROUP' AND ug.group_id = t.target_id AND ug.tenant_id = s.tenant_id
                    AND ug.is_active = true AND ug.delete_status = 'NOT_DELETED'
            ) m ON true
            WHERE s.status = 'DONE'
        ) o
        JOIN {MSG_TASKS_TABLE} tk
            ON tk.id = o.task_id AND tk.tenant_id = o.tenant_id
            AND tk.status = 'ACTIVE' AND tk.delete_status = 'NOT_DELETED'
        LEFT JOIN {MSG_TASK_NOTIFICATION_SETTINGS_TABLE} ns
            ON ns.tenant_id = o.tenant_id AND ns.org_id = o.org_id AND ns.bus_id = o.bus_id AND ns.user_id = o.user_id
        WHERE o.user_id IS NOT NULL
            AND COALESCE(ns.opt_in, true) = true
            AND NOT EXISTS (
                SELECT 1 FROM {MSG_TASK_NOTIFICATIONS_TABLE} n
                WHERE n.tenant_id = o.tenant_id AND n.step_id = o.step_id AND n.recipient_user_id = o.user_id
                    AND n.cdatetime > NOW() - (COALESCE(ns.reminder_interval_minutes, {DEFAULT_REMINDER_MINUTES}) * INTERVAL '1 minute')
            );
    """
    cursor.execute(query)
    return cursor.rowcount


def pick_up_pending_task_notifications(cursor, limit: int = 500) -> list[dict]:
    """Atomically claim pending task notifications for sending."""
    query = f"""
        UPDATE {MSG_TASK_NOTIFICATIONS_TABLE}
        SET picked_up_at = NOW()
        WHERE id IN (
            SELECT id FROM {MSG_TASK_NOTIFICATIONS_TABLE}
            WHERE status = 'PENDING' AND picked_up_at IS NULL
            ORDER BY cdatetime ASC
            LIMIT {int(limit)}
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, tenant_id, org_id, bus_id, task_id, step_id, recipient_user_id, kind;
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_recipient(cursor, tenant_id: str, user_id: str) -> dict | None:
    """Resolve a recipient's email and name."""
    cursor.execute(
        f"SELECT id, fullname, email FROM {CP_USERS_TABLE} WHERE id = %s AND tenant_id = %s LIMIT 1;",
        (user_id, tenant_id),
    )
    return cursor.fetchone()


def get_task_brief(cursor, tenant_id: str, task_id: str, step_id: str | None) -> dict:
    """Title of the task and (optionally) the step name for the email body."""
    cursor.execute(
        f"SELECT title, due_date FROM {MSG_TASKS_TABLE} WHERE id = %s AND tenant_id = %s LIMIT 1;",
        (task_id, tenant_id),
    )
    task = cursor.fetchone() or {}
    step_name = None
    if step_id:
        cursor.execute(
            f"SELECT name FROM {MSG_TASK_STEPS_TABLE} WHERE id = %s AND tenant_id = %s LIMIT 1;",
            (step_id, tenant_id),
        )
        srow = cursor.fetchone()
        step_name = srow["name"] if srow else None
    return {"title": task.get("title"), "due_date": task.get("due_date"), "step_name": step_name}


def mark_notification_sent(cursor, tenant_id: str, notification_id: str):
    cursor.execute(
        f"""UPDATE {MSG_TASK_NOTIFICATIONS_TABLE}
        SET status = 'SENT', sent_at = NOW()
        WHERE id = %s AND tenant_id = %s;""",
        (notification_id, tenant_id),
    )


def mark_notification_failed(cursor, tenant_id: str, notification_id: str, reason: str | None = None):
    cursor.execute(
        f"""UPDATE {MSG_TASK_NOTIFICATIONS_TABLE}
        SET status = 'FAILED', failure_reason = %s
        WHERE id = %s AND tenant_id = %s;""",
        (reason, notification_id, tenant_id),
    )
