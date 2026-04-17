from src.entities.messaging.messaging_read_dto import (
    CreateMessageServiceReadDto,
    UpdateMessageServiceReadDto,
    SendMessageServiceReadDto,
    CancelMessageServiceReadDto,
    ResendMessageServiceReadDto,
    GetMessageServiceReadDto,
    GetMessagesServiceReadDto,
    DeleteMessageServiceReadDto,
    GetMessageStatisticsServiceReadDto,
    MessageRecipientReadBase,
)
from src.entities.messaging.messaging_write_dto import (
    CreateMessageServiceWriteDto,
    UpdateMessageServiceWriteDto,
    SendMessageServiceWriteDto,
    CancelMessageServiceWriteDto,
    ResendMessageServiceWriteDto,
    DeleteMessageServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("messaging_service")


class MessagingService:
    """Service class for messaging operations"""

    @staticmethod
    def _get_recipient_table(recipient_type: str) -> str:
        """Get the table name for looking up recipient details"""
        if recipient_type == 'SUPPLIER':
            return db_settings.MSG_SUPPLIERS_TABLE
        return db_settings.MSG_CUSTOMERS_TABLE

    @staticmethod
    def _build_message_read_dto(cursor, message_id: str, tenant_id: str, org_id: str, bus_id: str) -> dict | None:
        """Build a complete message read DTO with recipients"""
        cursor.execute(
            f"""SELECT m.*,
                   creator.fullname as created_by_name,
                   updater.fullname as updated_by_name
            FROM {db_settings.MSG_MESSAGES_TABLE} m
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON m.updated_by = updater.id AND m.tenant_id = updater.tenant_id
            WHERE m.id = %s AND m.tenant_id = %s AND m.org_id = %s AND m.bus_id = %s""",
            (message_id, tenant_id, org_id, bus_id),
        )
        msg = cursor.fetchone()
        if not msg:
            return None

        msg_dict = dict(msg)
        msg_dict['created_by'] = msg_dict.pop('created_by_name', None) or msg_dict.get('created_by')
        msg_dict['updated_by'] = msg_dict.pop('updated_by_name', None) or msg_dict.get('updated_by')

        # Get recipients
        cursor.execute(
            f"""SELECT * FROM {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE}
            WHERE message_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
            ORDER BY cdatetime ASC""",
            (message_id, tenant_id, org_id, bus_id),
        )
        recipients = cursor.fetchall()
        msg_dict['recipients'] = [MessageRecipientReadBase(**dict(r)) for r in recipients]
        msg_dict['total_recipients'] = len(recipients)
        msg_dict['total_delivered'] = sum(1 for r in recipients if dict(r).get('status') == 'DELIVERED')
        msg_dict['total_failed'] = sum(1 for r in recipients if dict(r).get('status') == 'FAILED')

        return msg_dict

    @staticmethod
    def create_message(
        data: CreateMessageServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateMessageServiceReadDto]:
        """Create a new message (as DRAFT or SCHEDULED)"""
        logger.info(f"Creating message: subject={data.subject}, channel={data.channel}")

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Determine initial status
                status = 'SCHEDULED' if data.scheduled_at else 'DRAFT'

                # Insert message
                message_id = Helper.generate_unique_identifier(prefix="msg")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_MESSAGES_TABLE}
                    (id, tenant_id, org_id, bus_id, subject, body, channel, recipient_type,
                     scheduled_at, status, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        message_id, tenant_id, org_id, bus_id,
                        data.subject, data.body, data.channel, data.recipient_type,
                        data.scheduled_at, status,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                cursor.fetchone()

                # Look up recipient details and insert recipients
                recipient_table = MessagingService._get_recipient_table(data.recipient_type)
                name_field = 'fullname' if data.recipient_type == 'SUPPLIER' else 'fullname'

                for recipient in data.recipients:
                    # Fetch recipient contact info
                    cursor.execute(
                        f"""SELECT id, {name_field} as name, email, contact
                        FROM {recipient_table}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (recipient.recipient_id, tenant_id, org_id, bus_id),
                    )
                    recipient_info = cursor.fetchone()

                    if not recipient_info:
                        return Respons(
                            success=False,
                            detail=f"{data.recipient_type.capitalize()} with ID '{recipient.recipient_id}' not found",
                            error="RECIPIENT_NOT_FOUND",
                        )

                    r_dict = dict(recipient_info)
                    rec_id = Helper.generate_unique_identifier(prefix="mrc")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, message_id, recipient_type, recipient_id,
                         recipient_name, recipient_email, recipient_contact, status,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            rec_id, tenant_id, org_id, bus_id, message_id,
                            data.recipient_type, recipient.recipient_id,
                            r_dict.get('name'), r_dict.get('email'), r_dict.get('contact'),
                            'PENDING',
                            cdate, ctime, cdatetime, created_by
                        ),
                    )

                # Build response
                msg_dict = MessagingService._build_message_read_dto(cursor, message_id, tenant_id, org_id, bus_id)
                msg_read = CreateMessageServiceReadDto(**msg_dict)

                # Log activity
                try:
                    cursor.execute("SAVEPOINT before_activity_log")
                    try:
                        ActivityLogService.log_activity(
                            tenant_id=tenant_id, resource_type="rt-messaging",
                            resource_id=message_id, action="create",
                            old_data=None, new_data=msg_dict,
                            description=f"Message '{data.subject}' created ({status})",
                            performed_by=created_by, org_id=org_id, bus_id=bus_id, loc_id="", cursor=cursor
                        )
                        cursor.execute("RELEASE SAVEPOINT before_activity_log")
                    except Exception as log_err:
                        try:
                            cursor.execute("ROLLBACK TO SAVEPOINT before_activity_log")
                        except Exception:
                            raise
                except Exception:
                    pass

                return Respons(success=True, detail=f"Message created as {status}", data=[msg_read])

        except Exception as e:
            logger.error(f"Error creating message: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to create message: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def update_message(
        data: UpdateMessageServiceWriteDto,
        message_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateMessageServiceReadDto]:
        """Update a draft message"""
        logger.info(f"Updating message: {message_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MESSAGES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (message_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Message not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] not in ('DRAFT', 'SCHEDULED'):
                    return Respons(
                        success=False,
                        detail=f"Cannot update message with status '{old_data['status']}'. Only DRAFT or SCHEDULED messages can be updated.",
                        error="INVALID_STATUS",
                    )

                update_fields = []
                params = []

                if data.subject is not None:
                    update_fields.append("subject = %s")
                    params.append(data.subject)
                if data.body is not None:
                    update_fields.append("body = %s")
                    params.append(data.body)
                if data.channel is not None:
                    update_fields.append("channel = %s")
                    params.append(data.channel)
                if data.scheduled_at is not None:
                    update_fields.append("scheduled_at = %s")
                    params.append(data.scheduled_at)
                    update_fields.append("status = 'SCHEDULED'")

                if not update_fields:
                    return Respons(success=False, detail="No fields to update", error="VALIDATION_ERROR")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([message_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_MESSAGES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                cursor.fetchone()

                msg_dict = MessagingService._build_message_read_dto(cursor, message_id, tenant_id, org_id, bus_id)
                msg_read = UpdateMessageServiceReadDto(**msg_dict)

                return Respons(success=True, detail="Message updated successfully", data=[msg_read])

        except Exception as e:
            logger.error(f"Error updating message: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update message: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def send_message(
        data: SendMessageServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        sent_by: str
    ) -> Respons[SendMessageServiceReadDto]:
        """Send a draft message (sets status to SCHEDULED for Azure Function to pick up)"""
        logger.info(f"Sending message: {data.message_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MESSAGES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.message_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Message not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] != 'DRAFT':
                    return Respons(
                        success=False,
                        detail=f"Cannot send message with status '{old_data['status']}'. Only DRAFT messages can be sent.",
                        error="INVALID_STATUS",
                    )

                # Set to SCHEDULED with immediate scheduled_at so Azure Function picks it up
                cdatetime = Helper.current_date_time()["cdatetime"]
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_MESSAGES_TABLE}
                    SET status = 'SCHEDULED', scheduled_at = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    (cdatetime, sent_by, data.message_id, tenant_id, org_id, bus_id),
                )
                cursor.fetchone()

                msg_dict = MessagingService._build_message_read_dto(cursor, data.message_id, tenant_id, org_id, bus_id)
                msg_read = SendMessageServiceReadDto(**msg_dict)

                return Respons(success=True, detail="Message scheduled for sending", data=[msg_read])

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to send message: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def cancel_message(
        data: CancelMessageServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        cancelled_by: str
    ) -> Respons[CancelMessageServiceReadDto]:
        """Cancel a scheduled message"""
        logger.info(f"Cancelling message: {data.message_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MESSAGES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.message_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Message not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] not in ('DRAFT', 'SCHEDULED'):
                    return Respons(
                        success=False,
                        detail=f"Cannot cancel message with status '{old_data['status']}'. Only DRAFT or SCHEDULED messages can be cancelled.",
                        error="INVALID_STATUS",
                    )

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_MESSAGES_TABLE}
                    SET status = 'CANCELLED', updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    (cancelled_by, data.message_id, tenant_id, org_id, bus_id),
                )
                cursor.fetchone()

                msg_dict = MessagingService._build_message_read_dto(cursor, data.message_id, tenant_id, org_id, bus_id)
                msg_read = CancelMessageServiceReadDto(**msg_dict)

                return Respons(success=True, detail="Message cancelled", data=[msg_read])

        except Exception as e:
            logger.error(f"Error cancelling message: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to cancel message: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def resend_message(
        data: ResendMessageServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        resent_by: str
    ) -> Respons[ResendMessageServiceReadDto]:
        """Resend a failed message (resets to SCHEDULED)"""
        logger.info(f"Resending message: {data.message_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MESSAGES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.message_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Message not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] != 'FAILED':
                    return Respons(
                        success=False,
                        detail=f"Cannot resend message with status '{old_data['status']}'. Only FAILED messages can be resent.",
                        error="INVALID_STATUS",
                    )

                cdatetime = Helper.current_date_time()["cdatetime"]

                # Reset message status
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_MESSAGES_TABLE}
                    SET status = 'SCHEDULED', scheduled_at = %s, picked_up_at = NULL, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    (cdatetime, resent_by, data.message_id, tenant_id, org_id, bus_id),
                )
                cursor.fetchone()

                # Reset failed recipients to PENDING
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE}
                    SET status = 'PENDING', failure_reason = NULL
                    WHERE message_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND status = 'FAILED'""",
                    (data.message_id, tenant_id, org_id, bus_id),
                )

                msg_dict = MessagingService._build_message_read_dto(cursor, data.message_id, tenant_id, org_id, bus_id)
                msg_read = ResendMessageServiceReadDto(**msg_dict)

                return Respons(success=True, detail="Message rescheduled for resending", data=[msg_read])

        except Exception as e:
            logger.error(f"Error resending message: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to resend message: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_message(
        message_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetMessageServiceReadDto]:
        """Get a single message by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                msg_dict = MessagingService._build_message_read_dto(cursor, message_id, tenant_id, org_id, bus_id)
                if not msg_dict:
                    return Respons(success=False, detail="Message not found", error="NOT_FOUND")

                msg_read = GetMessageServiceReadDto(**msg_dict)
                return Respons(success=True, detail="Message retrieved successfully", data=[msg_read])

        except Exception as e:
            logger.error(f"Error getting message: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get message: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_messages(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        page: int = 1,
        size: int = 10,
        status: str = None,
        channel: str = None,
        recipient_type: str = None,
    ) -> Respons[list[GetMessagesServiceReadDto]]:
        """Get list of messages with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["m.tenant_id = %s", "m.org_id = %s", "m.bus_id = %s"]
                params = [tenant_id, org_id, bus_id]

                if status:
                    conditions.append("m.status = %s")
                    params.append(status)
                if channel:
                    conditions.append("m.channel = %s")
                    params.append(channel)
                if recipient_type:
                    conditions.append("m.recipient_type = %s")
                    params.append(recipient_type)

                where_clause = " AND ".join(conditions)

                # Count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_MESSAGES_TABLE} m WHERE {where_clause}",
                    tuple(params),
                )
                total = cursor.fetchone()['total'] or 0

                offset = (page - 1) * size

                cursor.execute(
                    f"""SELECT m.*,
                           creator.fullname as created_by_name,
                           (SELECT COUNT(*) FROM {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE} r
                            WHERE r.message_id = m.id AND r.tenant_id = m.tenant_id AND r.org_id = m.org_id AND r.bus_id = m.bus_id) as total_recipients,
                           (SELECT COUNT(*) FROM {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE} r
                            WHERE r.message_id = m.id AND r.tenant_id = m.tenant_id AND r.org_id = m.org_id AND r.bus_id = m.bus_id AND r.status = 'DELIVERED') as total_delivered,
                           (SELECT COUNT(*) FROM {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE} r
                            WHERE r.message_id = m.id AND r.tenant_id = m.tenant_id AND r.org_id = m.org_id AND r.bus_id = m.bus_id AND r.status = 'FAILED') as total_failed
                    FROM {db_settings.MSG_MESSAGES_TABLE} m
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
                    WHERE {where_clause}
                    ORDER BY m.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                messages = cursor.fetchall()

                msg_list = []
                for msg in messages:
                    m = dict(msg)
                    m['created_by'] = m.pop('created_by_name', None) or m.get('created_by')
                    m['recipients'] = []
                    msg_list.append(GetMessagesServiceReadDto(**m))

                pagination = PaginationMeta(page=page, size=size, total=total, has_next=(page * size) < total)

                return Respons(success=True, detail="Messages retrieved successfully", data=msg_list, pagination=pagination)

        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get messages: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def delete_message(
        data: DeleteMessageServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteMessageServiceReadDto]:
        """Delete a message"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MESSAGES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.message_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Message not found", error="NOT_FOUND")

                # Delete recipients first (CASCADE should handle this but being explicit)
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE}
                    WHERE message_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.message_id, tenant_id, org_id, bus_id),
                )

                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_MESSAGES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.message_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Message deleted successfully",
                    data=[DeleteMessageServiceReadDto(message_id=data.message_id, message="Message deleted")],
                )

        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to delete message: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_message_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetMessageStatisticsServiceReadDto]:
        """Get message statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_messages,
                        COUNT(CASE WHEN status = 'DRAFT' THEN 1 END) as total_draft,
                        COUNT(CASE WHEN status = 'SCHEDULED' THEN 1 END) as total_scheduled,
                        COUNT(CASE WHEN status = 'SENT' THEN 1 END) as total_sent,
                        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as total_failed,
                        COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as total_cancelled
                    FROM {db_settings.MSG_MESSAGES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (tenant_id, org_id, bus_id),
                )
                result = cursor.fetchone()

                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_recipients,
                        COUNT(CASE WHEN status = 'DELIVERED' THEN 1 END) as total_delivered,
                        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as total_delivery_failed
                    FROM {db_settings.MSG_MESSAGE_RECIPIENTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (tenant_id, org_id, bus_id),
                )
                rec_result = cursor.fetchone()

                stats = GetMessageStatisticsServiceReadDto(
                    total_messages=result.get('total_messages', 0) or 0 if result else 0,
                    total_draft=result.get('total_draft', 0) or 0 if result else 0,
                    total_scheduled=result.get('total_scheduled', 0) or 0 if result else 0,
                    total_sent=result.get('total_sent', 0) or 0 if result else 0,
                    total_failed=result.get('total_failed', 0) or 0 if result else 0,
                    total_cancelled=result.get('total_cancelled', 0) or 0 if result else 0,
                    total_recipients=rec_result.get('total_recipients', 0) or 0 if rec_result else 0,
                    total_delivered=rec_result.get('total_delivered', 0) or 0 if rec_result else 0,
                    total_delivery_failed=rec_result.get('total_delivery_failed', 0) or 0 if rec_result else 0,
                )

                return Respons(success=True, detail="Message statistics retrieved successfully", data=[stats])

        except Exception as e:
            logger.error(f"Error getting message statistics: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get message statistics: {str(e)}", error="INTERNAL_ERROR")
