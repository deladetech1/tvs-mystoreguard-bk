import logging

from shared.settings import (
    MSG_MESSAGES_TABLE,
    MSG_MESSAGE_RECIPIENTS_TABLE,
    MSG_MEETINGS_TABLE,
    MSG_MEETING_PARTICIPANTS_TABLE,
    MSG_SUPPLIERS_TABLE,
    MSG_CUSTOMERS_TABLE,
)

logger = logging.getLogger("mystoreguard_functions")


# ──────────────────────────────────────────────────
# Scheduled Messages
# ──────────────────────────────────────────────────

def pick_up_due_messages(cursor) -> list[dict]:
    """
    Atomically claim scheduled messages that are due for sending.
    Uses picked_up_at as a lock to prevent double-processing.
    Returns the claimed messages.
    """
    query = f"""
        UPDATE {MSG_MESSAGES_TABLE}
        SET picked_up_at = NOW(), status = 'QUEUED'
        WHERE status = 'SCHEDULED'
            AND scheduled_at <= NOW()
            AND picked_up_at IS NULL
        RETURNING id, tenant_id, org_id, bus_id, subject, body, channel, recipient_type;
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_message_recipients(cursor, tenant_id: str, org_id: str, bus_id: str, message_id: str) -> list[dict]:
    """Get all recipients for a message with their contact details."""
    query = f"""
        SELECT r.id, r.recipient_type, r.recipient_id,
               r.recipient_name, r.recipient_email, r.recipient_contact
        FROM {MSG_MESSAGE_RECIPIENTS_TABLE} r
        WHERE r.tenant_id = %s AND r.org_id = %s AND r.bus_id = %s AND r.message_id = %s
            AND r.status = 'PENDING';
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, message_id))
    return cursor.fetchall()


def update_recipient_status(cursor, tenant_id: str, org_id: str, bus_id: str, recipient_id: str, status: str, failure_reason: str | None = None):
    """Update the delivery status of a single recipient."""
    if status == 'DELIVERED':
        query = f"""
            UPDATE {MSG_MESSAGE_RECIPIENTS_TABLE}
            SET status = %s, delivered_at = NOW()
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s;
        """
        cursor.execute(query, (status, tenant_id, org_id, bus_id, recipient_id))
    else:
        query = f"""
            UPDATE {MSG_MESSAGE_RECIPIENTS_TABLE}
            SET status = %s, failure_reason = %s
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s;
        """
        cursor.execute(query, (status, failure_reason, tenant_id, org_id, bus_id, recipient_id))


def update_message_status(cursor, tenant_id: str, org_id: str, bus_id: str, message_id: str, status: str):
    """Update the overall message status after processing all recipients."""
    sent_at_clause = ", sent_at = NOW()" if status == 'SENT' else ""
    query = f"""
        UPDATE {MSG_MESSAGES_TABLE}
        SET status = %s{sent_at_clause}
        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s;
    """
    cursor.execute(query, (status, tenant_id, org_id, bus_id, message_id))


# ──────────────────────────────────────────────────
# Meeting Reminders
# ──────────────────────────────────────────────────

def pick_up_due_meeting_reminders(cursor) -> list[dict]:
    """
    Atomically claim meetings whose reminder time has arrived.
    Reminder time = start_datetime - reminder_minutes.
    Uses reminder_picked_up_at as a lock to prevent double-processing.
    """
    query = f"""
        UPDATE {MSG_MEETINGS_TABLE}
        SET reminder_picked_up_at = NOW()
        WHERE status = 'SCHEDULED'
            AND (start_datetime - (reminder_minutes * INTERVAL '1 minute')) <= NOW()
            AND reminder_picked_up_at IS NULL
            AND reminder_minutes IS NOT NULL
            AND reminder_minutes > 0
        RETURNING id, tenant_id, org_id, bus_id, title, description, location,
                  meeting_date, start_time, end_time, participant_type, reminder_channel;
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_meeting_participants(cursor, tenant_id: str, org_id: str, bus_id: str, meeting_id: str) -> list[dict]:
    """Get all participants for a meeting with their contact details."""
    query = f"""
        SELECT p.id, p.participant_type, p.participant_id,
               p.participant_name, p.participant_email, p.participant_contact
        FROM {MSG_MEETING_PARTICIPANTS_TABLE} p
        WHERE p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s AND p.meeting_id = %s
            AND p.reminder_status = 'PENDING';
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, meeting_id))
    return cursor.fetchall()


def update_participant_reminder_status(cursor, tenant_id: str, org_id: str, bus_id: str, participant_id: str, status: str, failure_reason: str | None = None):
    """Update the reminder delivery status of a single participant."""
    query = f"""
        UPDATE {MSG_MEETING_PARTICIPANTS_TABLE}
        SET reminder_status = %s, reminder_failure_reason = %s
        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s;
    """
    cursor.execute(query, (status, failure_reason, tenant_id, org_id, bus_id, participant_id))


def update_meeting_reminder_status(cursor, tenant_id: str, org_id: str, bus_id: str, meeting_id: str):
    """Mark the meeting as reminder sent."""
    query = f"""
        UPDATE {MSG_MEETINGS_TABLE}
        SET status = 'REMINDER_SENT', reminder_sent_at = NOW()
        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, meeting_id))
