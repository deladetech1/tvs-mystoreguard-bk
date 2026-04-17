from src.entities.meetings.meetings_read_dto import (
    CreateMeetingServiceReadDto,
    UpdateMeetingServiceReadDto,
    CancelMeetingServiceReadDto,
    CompleteMeetingServiceReadDto,
    GetMeetingServiceReadDto,
    GetMeetingsServiceReadDto,
    DeleteMeetingServiceReadDto,
    GetMeetingStatisticsServiceReadDto,
    MeetingParticipantReadBase,
)
from src.entities.meetings.meetings_write_dto import (
    CreateMeetingServiceWriteDto,
    UpdateMeetingServiceWriteDto,
    CancelMeetingServiceWriteDto,
    CompleteMeetingServiceWriteDto,
    DeleteMeetingServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("meetings_service")


class MeetingsService:
    """Service class for meetings operations"""

    @staticmethod
    def _get_participant_table(participant_type: str) -> str:
        if participant_type == 'SUPPLIER':
            return db_settings.MSG_SUPPLIERS_TABLE
        return db_settings.MSG_CUSTOMERS_TABLE

    @staticmethod
    def _build_meeting_read_dto(cursor, meeting_id: str, tenant_id: str, org_id: str, bus_id: str) -> dict | None:
        """Build a complete meeting read DTO with participants"""
        cursor.execute(
            f"""SELECT m.*,
                   creator.fullname as created_by_name,
                   updater.fullname as updated_by_name
            FROM {db_settings.MSG_MEETINGS_TABLE} m
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON m.updated_by = updater.id AND m.tenant_id = updater.tenant_id
            WHERE m.id = %s AND m.tenant_id = %s AND m.org_id = %s AND m.bus_id = %s""",
            (meeting_id, tenant_id, org_id, bus_id),
        )
        mtg = cursor.fetchone()
        if not mtg:
            return None

        mtg_dict = dict(mtg)
        mtg_dict['created_by'] = mtg_dict.pop('created_by_name', None) or mtg_dict.get('created_by')
        mtg_dict['updated_by'] = mtg_dict.pop('updated_by_name', None) or mtg_dict.get('updated_by')

        # Get participants
        cursor.execute(
            f"""SELECT * FROM {db_settings.MSG_MEETING_PARTICIPANTS_TABLE}
            WHERE meeting_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
            ORDER BY cdatetime ASC""",
            (meeting_id, tenant_id, org_id, bus_id),
        )
        participants = cursor.fetchall()
        mtg_dict['participants'] = [MeetingParticipantReadBase(**dict(p)) for p in participants]
        mtg_dict['total_participants'] = len(participants)
        mtg_dict['total_accepted'] = sum(1 for p in participants if dict(p).get('rsvp_status') == 'ACCEPTED')
        mtg_dict['total_declined'] = sum(1 for p in participants if dict(p).get('rsvp_status') == 'DECLINED')

        return mtg_dict

    @staticmethod
    def create_meeting(
        data: CreateMeetingServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateMeetingServiceReadDto]:
        """Schedule a new meeting"""
        logger.info(f"Creating meeting: {data.title}")

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                meeting_id = Helper.generate_unique_identifier(prefix="mtg")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_MEETINGS_TABLE}
                    (id, tenant_id, org_id, bus_id, title, description, location,
                     meeting_date, start_time, end_time, start_datetime, end_datetime,
                     participant_type, reminder_minutes, reminder_channel, status, notes,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        meeting_id, tenant_id, org_id, bus_id,
                        data.title, data.description, data.location,
                        data.meeting_date, data.start_time, data.end_time,
                        data.start_datetime, data.end_datetime,
                        data.participant_type, data.reminder_minutes, data.reminder_channel,
                        'SCHEDULED', data.notes,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                cursor.fetchone()

                # Look up participant details and insert
                participant_table = MeetingsService._get_participant_table(data.participant_type)

                for participant in data.participants:
                    cursor.execute(
                        f"""SELECT id, fullname as name, email, contact
                        FROM {participant_table}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (participant.participant_id, tenant_id, org_id, bus_id),
                    )
                    p_info = cursor.fetchone()

                    if not p_info:
                        return Respons(
                            success=False,
                            detail=f"{data.participant_type.capitalize()} with ID '{participant.participant_id}' not found",
                            error="PARTICIPANT_NOT_FOUND",
                        )

                    p_dict = dict(p_info)
                    part_id = Helper.generate_unique_identifier(prefix="mpt")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_MEETING_PARTICIPANTS_TABLE}
                        (id, tenant_id, org_id, bus_id, meeting_id, participant_type, participant_id,
                         participant_name, participant_email, participant_contact,
                         rsvp_status, reminder_status,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            part_id, tenant_id, org_id, bus_id, meeting_id,
                            data.participant_type, participant.participant_id,
                            p_dict.get('name'), p_dict.get('email'), p_dict.get('contact'),
                            'PENDING', 'PENDING',
                            cdate, ctime, cdatetime, created_by
                        ),
                    )

                mtg_dict = MeetingsService._build_meeting_read_dto(cursor, meeting_id, tenant_id, org_id, bus_id)
                mtg_read = CreateMeetingServiceReadDto(**mtg_dict)

                # Log activity
                try:
                    cursor.execute("SAVEPOINT before_activity_log")
                    try:
                        ActivityLogService.log_activity(
                            tenant_id=tenant_id, resource_type="rt-meetings",
                            resource_id=meeting_id, action="create",
                            old_data=None, new_data=mtg_dict,
                            description=f"Meeting '{data.title}' scheduled for {data.meeting_date}",
                            performed_by=created_by, org_id=org_id, bus_id=bus_id, loc_id="", cursor=cursor
                        )
                        cursor.execute("RELEASE SAVEPOINT before_activity_log")
                    except Exception:
                        try:
                            cursor.execute("ROLLBACK TO SAVEPOINT before_activity_log")
                        except Exception:
                            raise
                except Exception:
                    pass

                return Respons(success=True, detail="Meeting scheduled successfully", data=[mtg_read])

        except Exception as e:
            logger.error(f"Error creating meeting: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to create meeting: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def update_meeting(
        data: UpdateMeetingServiceWriteDto,
        meeting_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateMeetingServiceReadDto]:
        """Update a scheduled meeting"""
        logger.info(f"Updating meeting: {meeting_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MEETINGS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (meeting_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Meeting not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] in ('COMPLETED', 'CANCELLED'):
                    return Respons(
                        success=False,
                        detail=f"Cannot update meeting with status '{old_data['status']}'",
                        error="INVALID_STATUS",
                    )

                update_fields = []
                params = []

                for field in ['title', 'description', 'location', 'meeting_date', 'start_time',
                              'end_time', 'start_datetime', 'end_datetime', 'reminder_minutes',
                              'reminder_channel', 'notes']:
                    value = getattr(data, field, None)
                    if value is not None:
                        update_fields.append(f"{field} = %s")
                        params.append(value)

                if not update_fields:
                    return Respons(success=False, detail="No fields to update", error="VALIDATION_ERROR")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([meeting_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_MEETINGS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                cursor.fetchone()

                mtg_dict = MeetingsService._build_meeting_read_dto(cursor, meeting_id, tenant_id, org_id, bus_id)
                mtg_read = UpdateMeetingServiceReadDto(**mtg_dict)

                return Respons(success=True, detail="Meeting updated successfully", data=[mtg_read])

        except Exception as e:
            logger.error(f"Error updating meeting: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update meeting: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def cancel_meeting(
        data: CancelMeetingServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        cancelled_by: str
    ) -> Respons[CancelMeetingServiceReadDto]:
        """Cancel a meeting"""
        logger.info(f"Cancelling meeting: {data.meeting_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MEETINGS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.meeting_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Meeting not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] in ('COMPLETED', 'CANCELLED'):
                    return Respons(
                        success=False,
                        detail=f"Meeting is already '{old_data['status']}'",
                        error="INVALID_STATUS",
                    )

                notes_update = data.cancellation_reason or 'Cancelled'
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_MEETINGS_TABLE}
                    SET status = 'CANCELLED', updated_by = %s,
                        notes = CASE WHEN notes IS NULL THEN %s ELSE notes || ' | Cancelled: ' || %s END
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    (cancelled_by, notes_update, notes_update, data.meeting_id, tenant_id, org_id, bus_id),
                )
                cursor.fetchone()

                mtg_dict = MeetingsService._build_meeting_read_dto(cursor, data.meeting_id, tenant_id, org_id, bus_id)
                mtg_read = CancelMeetingServiceReadDto(**mtg_dict)

                return Respons(success=True, detail="Meeting cancelled", data=[mtg_read])

        except Exception as e:
            logger.error(f"Error cancelling meeting: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to cancel meeting: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def complete_meeting(
        data: CompleteMeetingServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        completed_by: str
    ) -> Respons[CompleteMeetingServiceReadDto]:
        """Mark a meeting as completed"""
        logger.info(f"Completing meeting: {data.meeting_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MEETINGS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.meeting_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Meeting not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] == 'CANCELLED':
                    return Respons(success=False, detail="Cannot complete a cancelled meeting", error="INVALID_STATUS")
                if old_data['status'] == 'COMPLETED':
                    return Respons(success=False, detail="Meeting is already completed", error="ALREADY_COMPLETED")

                notes_update = data.notes
                if notes_update:
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_MEETINGS_TABLE}
                        SET status = 'COMPLETED', updated_by = %s,
                            notes = CASE WHEN notes IS NULL THEN %s ELSE notes || ' | Notes: ' || %s END
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        RETURNING *""",
                        (completed_by, notes_update, notes_update, data.meeting_id, tenant_id, org_id, bus_id),
                    )
                else:
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_MEETINGS_TABLE}
                        SET status = 'COMPLETED', updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        RETURNING *""",
                        (completed_by, data.meeting_id, tenant_id, org_id, bus_id),
                    )
                cursor.fetchone()

                mtg_dict = MeetingsService._build_meeting_read_dto(cursor, data.meeting_id, tenant_id, org_id, bus_id)
                mtg_read = CompleteMeetingServiceReadDto(**mtg_dict)

                return Respons(success=True, detail="Meeting completed", data=[mtg_read])

        except Exception as e:
            logger.error(f"Error completing meeting: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to complete meeting: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_meeting(
        meeting_id: str, tenant_id: str, org_id: str, bus_id: str,
    ) -> Respons[GetMeetingServiceReadDto]:
        """Get a single meeting by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                mtg_dict = MeetingsService._build_meeting_read_dto(cursor, meeting_id, tenant_id, org_id, bus_id)
                if not mtg_dict:
                    return Respons(success=False, detail="Meeting not found", error="NOT_FOUND")
                return Respons(success=True, detail="Meeting retrieved successfully", data=[GetMeetingServiceReadDto(**mtg_dict)])
        except Exception as e:
            logger.error(f"Error getting meeting: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get meeting: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_meetings(
        tenant_id: str, org_id: str, bus_id: str,
        page: int = 1, size: int = 10,
        status: str = None, participant_type: str = None,
    ) -> Respons[list[GetMeetingsServiceReadDto]]:
        """Get list of meetings with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["m.tenant_id = %s", "m.org_id = %s", "m.bus_id = %s"]
                params = [tenant_id, org_id, bus_id]

                if status:
                    conditions.append("m.status = %s")
                    params.append(status)
                if participant_type:
                    conditions.append("m.participant_type = %s")
                    params.append(participant_type)

                where_clause = " AND ".join(conditions)

                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_MEETINGS_TABLE} m WHERE {where_clause}",
                    tuple(params),
                )
                total = cursor.fetchone()['total'] or 0

                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT m.*,
                           creator.fullname as created_by_name,
                           (SELECT COUNT(*) FROM {db_settings.MSG_MEETING_PARTICIPANTS_TABLE} p
                            WHERE p.meeting_id = m.id AND p.tenant_id = m.tenant_id AND p.org_id = m.org_id AND p.bus_id = m.bus_id) as total_participants,
                           (SELECT COUNT(*) FROM {db_settings.MSG_MEETING_PARTICIPANTS_TABLE} p
                            WHERE p.meeting_id = m.id AND p.tenant_id = m.tenant_id AND p.org_id = m.org_id AND p.bus_id = m.bus_id AND p.rsvp_status = 'ACCEPTED') as total_accepted,
                           (SELECT COUNT(*) FROM {db_settings.MSG_MEETING_PARTICIPANTS_TABLE} p
                            WHERE p.meeting_id = m.id AND p.tenant_id = m.tenant_id AND p.org_id = m.org_id AND p.bus_id = m.bus_id AND p.rsvp_status = 'DECLINED') as total_declined
                    FROM {db_settings.MSG_MEETINGS_TABLE} m
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
                    WHERE {where_clause}
                    ORDER BY m.start_datetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                meetings = cursor.fetchall()

                mtg_list = []
                for mtg in meetings:
                    m = dict(mtg)
                    m['created_by'] = m.pop('created_by_name', None) or m.get('created_by')
                    m['participants'] = []
                    mtg_list.append(GetMeetingsServiceReadDto(**m))

                pagination = PaginationMeta(page=page, size=size, total=total, has_next=(page * size) < total)
                return Respons(success=True, detail="Meetings retrieved successfully", data=mtg_list, pagination=pagination)

        except Exception as e:
            logger.error(f"Error getting meetings: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get meetings: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def delete_meeting(
        data: DeleteMeetingServiceWriteDto, tenant_id: str, org_id: str, bus_id: str, deleted_by: str
    ) -> Respons[DeleteMeetingServiceReadDto]:
        """Delete a meeting"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_MEETINGS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.meeting_id, tenant_id, org_id, bus_id),
                )
                if not cursor.fetchone():
                    return Respons(success=False, detail="Meeting not found", error="NOT_FOUND")

                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_MEETING_PARTICIPANTS_TABLE}
                    WHERE meeting_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.meeting_id, tenant_id, org_id, bus_id),
                )
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_MEETINGS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.meeting_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True, detail="Meeting deleted successfully",
                    data=[DeleteMeetingServiceReadDto(meeting_id=data.meeting_id, message="Meeting deleted")],
                )
        except Exception as e:
            logger.error(f"Error deleting meeting: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to delete meeting: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_meeting_statistics(
        tenant_id: str, org_id: str, bus_id: str,
    ) -> Respons[GetMeetingStatisticsServiceReadDto]:
        """Get meeting statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_meetings,
                        COUNT(CASE WHEN status = 'SCHEDULED' THEN 1 END) as total_scheduled,
                        COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as total_completed,
                        COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as total_cancelled,
                        COUNT(CASE WHEN status = 'REMINDER_SENT' THEN 1 END) as total_reminder_sent
                    FROM {db_settings.MSG_MEETINGS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (tenant_id, org_id, bus_id),
                )
                result = cursor.fetchone()

                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_participants,
                        COUNT(CASE WHEN rsvp_status = 'ACCEPTED' THEN 1 END) as total_accepted,
                        COUNT(CASE WHEN rsvp_status = 'DECLINED' THEN 1 END) as total_declined
                    FROM {db_settings.MSG_MEETING_PARTICIPANTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (tenant_id, org_id, bus_id),
                )
                p_result = cursor.fetchone()

                stats = GetMeetingStatisticsServiceReadDto(
                    total_meetings=result.get('total_meetings', 0) or 0 if result else 0,
                    total_scheduled=result.get('total_scheduled', 0) or 0 if result else 0,
                    total_completed=result.get('total_completed', 0) or 0 if result else 0,
                    total_cancelled=result.get('total_cancelled', 0) or 0 if result else 0,
                    total_reminder_sent=result.get('total_reminder_sent', 0) or 0 if result else 0,
                    total_participants=p_result.get('total_participants', 0) or 0 if p_result else 0,
                    total_accepted=p_result.get('total_accepted', 0) or 0 if p_result else 0,
                    total_declined=p_result.get('total_declined', 0) or 0 if p_result else 0,
                )
                return Respons(success=True, detail="Meeting statistics retrieved successfully", data=[stats])

        except Exception as e:
            logger.error(f"Error getting meeting statistics: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get meeting statistics: {str(e)}", error="INTERNAL_ERROR")
