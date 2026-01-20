from typing import Optional
from src.entities.appointments.appointments_read_dto import (
    CreateAppointmentServiceReadDto,
    UpdateAppointmentServiceReadDto,
    DeleteAppointmentServiceReadDto,
    GetAppointmentServiceReadDto,
    GetAppointmentsServiceReadDto,
)
from src.entities.appointments.appointments_write_dto import (
    CreateAppointmentServiceWriteDto,
    UpdateAppointmentServiceWriteDto,
    DeleteAppointmentServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("appointments_service")


class AppointmentsService:
    """Service class for appointments operations"""

    @staticmethod
    def create_appointment(
        data: CreateAppointmentServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateAppointmentServiceReadDto]:
        """Create a new appointment"""
        logger.info(
            f"Processing appointment creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "appointment_type": data.appointment_type,
                    "created_by": created_by,
                }
            },
        )

        # Validate end_datetime > start_datetime
        if data.end_datetime <= data.start_datetime:
            return Respons(
                success=False,
                detail="End datetime must be after start datetime",
                error="VALIDATION_ERROR",
            )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check for overlapping appointments with the same assigned_to user
                if data.assigned_to:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_APPOINTMENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND assigned_to = %s
                        AND status NOT IN ('CANCELLED', 'NO_SHOW', 'COMPLETED')
                        AND (
                            (start_datetime <= %s AND end_datetime > %s) OR
                            (start_datetime < %s AND end_datetime >= %s) OR
                            (start_datetime >= %s AND end_datetime <= %s)
                        )""",
                        (
                            tenant_id, org_id, bus_id, loc_id, data.assigned_to,
                            data.start_datetime, data.start_datetime,
                            data.end_datetime, data.end_datetime,
                            data.start_datetime, data.end_datetime
                        ),
                    )
                    overlapping = cursor.fetchone()
                    if overlapping:
                        return Respons(
                            success=False,
                            detail="Appointment overlaps with an existing appointment for the assigned user",
                            error="OVERLAPPING_APPOINTMENT",
                        )

                # Generate appointment ID
                appointment_id = Helper.generate_unique_identifier(prefix="apt")

                # Insert into msg_appointments table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_APPOINTMENTS_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, appointment_type, status,
                     is_walk_in, customer_id, assigned_to, start_datetime, end_datetime,
                     description, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        appointment_id, tenant_id, org_id, bus_id, loc_id,
                        data.appointment_type, data.status,
                        data.is_walk_in, data.customer_id, data.assigned_to,
                        data.start_datetime, data.end_datetime, data.description,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                appointment_result = cursor.fetchone()

                if not appointment_result:
                    raise ValueError("Failed to create appointment")

                # Get appointment with user fullnames, customer name, and assigned_to name
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.fullname as customer_name,
                           assigned_user.fullname as assigned_to_name
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c ON a.customer_id = c.id AND a.tenant_id = c.tenant_id AND a.org_id = c.org_id AND a.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assigned_user ON a.assigned_to = assigned_user.id AND a.tenant_id = assigned_user.tenant_id
                    WHERE a.id = %s AND a.tenant_id = %s""",
                    (appointment_id, tenant_id),
                )
                appointment_with_users = cursor.fetchone()

                if appointment_with_users:
                    appointment_dict = dict(appointment_with_users)
                    appointment_dict['created_by'] = appointment_dict.get('created_by') or None
                    appointment_dict['updated_by'] = appointment_dict.get('updated_by') or None
                    appointment_dict['deleted_by'] = appointment_dict.get('deleted_by') or None
                    appointment_dict['customer_name'] = appointment_dict.get('customer_name') or None
                    appointment_dict['assigned_to_name'] = appointment_dict.get('assigned_to_name') or None
                    appointment_dict['assigned_to_id'] = appointment_dict.get('assigned_to') or None
                else:
                    appointment_dict = dict(appointment_result)
                    appointment_dict['created_by'] = None
                    appointment_dict['updated_by'] = None
                    appointment_dict['deleted_by'] = None
                    appointment_dict['customer_name'] = None
                    appointment_dict['assigned_to_name'] = None
                    appointment_dict['assigned_to_id'] = appointment_dict.get('assigned_to') or None

                appointment_read = CreateAppointmentServiceReadDto(**appointment_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_APPOINTMENTS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (appointment_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(appointment_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-appointments",
                        resource_id=appointment_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Appointment {appointment_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Appointment created successfully: {appointment_id}",
                    extra={
                        "extra_fields": {
                            "appointment_id": appointment_id,
                            "appointment_type": data.appointment_type,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Appointment created successfully",
                    data=[appointment_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating appointment: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create appointment: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_appointment(
        data: UpdateAppointmentServiceWriteDto,
        appointment_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[UpdateAppointmentServiceReadDto]:
        """Update an appointment"""
        logger.info(
            f"Processing appointment update: {appointment_id}",
            extra={
                "extra_fields": {
                    "appointment_id": appointment_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data (for audit/activity log)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_APPOINTMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s""",
                    (appointment_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_appointment = cursor.fetchone()

                if not existing_appointment:
                    raise ValueError("Appointment not found")
                
                # Store complete old data before update
                old_data = dict(existing_appointment)

                # Validate end_datetime > start_datetime if both are being updated
                start_dt = data.start_datetime if data.start_datetime is not None else old_data.get('start_datetime')
                end_dt = data.end_datetime if data.end_datetime is not None else old_data.get('end_datetime')
                
                if end_dt <= start_dt:
                    raise ValueError("End datetime must be after start datetime")

                # Check for overlapping appointments if time or assigned_to is being changed
                assigned_to = data.assigned_to if data.assigned_to is not None else old_data.get('assigned_to')
                if assigned_to and (data.start_datetime is not None or data.end_datetime is not None or data.assigned_to is not None):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_APPOINTMENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND assigned_to = %s
                        AND id != %s
                        AND status NOT IN ('CANCELLED', 'NO_SHOW', 'COMPLETED')
                        AND (
                            (start_datetime <= %s AND end_datetime > %s) OR
                            (start_datetime < %s AND end_datetime >= %s) OR
                            (start_datetime >= %s AND end_datetime <= %s)
                        )""",
                        (
                            tenant_id, org_id, bus_id, loc_id, assigned_to, appointment_id,
                            start_dt, start_dt,
                            end_dt, end_dt,
                            start_dt, end_dt
                        ),
                    )
                    overlapping = cursor.fetchone()
                    if overlapping:
                        raise ValueError("Appointment overlaps with an existing appointment for the assigned user")

                # Build update query dynamically
                update_fields = []
                update_params = []

                if data.appointment_type is not None:
                    update_fields.append("appointment_type = %s")
                    update_params.append(data.appointment_type)
                if data.status is not None:
                    update_fields.append("status = %s")
                    update_params.append(data.status)
                if data.is_walk_in is not None:
                    update_fields.append("is_walk_in = %s")
                    update_params.append(data.is_walk_in)
                if data.customer_id is not None:
                    update_fields.append("customer_id = %s")
                    update_params.append(data.customer_id)
                if data.assigned_to is not None:
                    update_fields.append("assigned_to = %s")
                    update_params.append(data.assigned_to)
                if data.start_datetime is not None:
                    update_fields.append("start_datetime = %s")
                    update_params.append(data.start_datetime)
                if data.end_datetime is not None:
                    update_fields.append("end_datetime = %s")
                    update_params.append(data.end_datetime)
                if data.description is not None:
                    update_fields.append("description = %s")
                    update_params.append(data.description)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                update_params.append(updated_by)

                update_params.extend([appointment_id, tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_APPOINTMENTS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    tuple(update_params),
                )
                updated_appointment = cursor.fetchone()

                if not updated_appointment:
                    raise ValueError("Failed to update appointment")

                # Get appointment with user fullnames, customer name, and assigned_to name
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.fullname as customer_name,
                           assigned_user.fullname as assigned_to_name
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c ON a.customer_id = c.id AND a.tenant_id = c.tenant_id AND a.org_id = c.org_id AND a.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assigned_user ON a.assigned_to = assigned_user.id AND a.tenant_id = assigned_user.tenant_id
                    WHERE a.id = %s AND a.tenant_id = %s""",
                    (appointment_id, tenant_id),
                )
                appointment_with_users = cursor.fetchone()

                if appointment_with_users:
                    appointment_dict = dict(appointment_with_users)
                    appointment_dict['created_by'] = appointment_dict.get('created_by') or None
                    appointment_dict['updated_by'] = appointment_dict.get('updated_by') or None
                    appointment_dict['deleted_by'] = appointment_dict.get('deleted_by') or None
                    appointment_dict['customer_name'] = appointment_dict.get('customer_name') or None
                    appointment_dict['assigned_to_name'] = appointment_dict.get('assigned_to_name') or None
                    appointment_dict['assigned_to_id'] = appointment_dict.get('assigned_to') or None
                else:
                    appointment_dict = dict(updated_appointment)
                    appointment_dict['created_by'] = None
                    appointment_dict['updated_by'] = None
                    appointment_dict['deleted_by'] = None
                    appointment_dict['customer_name'] = None
                    appointment_dict['assigned_to_name'] = None
                    appointment_dict['assigned_to_id'] = appointment_dict.get('assigned_to') or None

                appointment_read = UpdateAppointmentServiceReadDto(**appointment_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_APPOINTMENTS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (appointment_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(appointment_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-appointments",
                        resource_id=appointment_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Appointment {appointment_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Appointment updated successfully: {appointment_id}")

                return Respons(
                    success=True,
                    detail="Appointment updated successfully",
                    data=[appointment_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating appointment: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating appointment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update appointment: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_appointment(
        appointment_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetAppointmentServiceReadDto]:
        """Get a single appointment by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.fullname as customer_name,
                           assigned_user.fullname as assigned_to_name
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c ON a.customer_id = c.id AND a.tenant_id = c.tenant_id AND a.org_id = c.org_id AND a.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assigned_user ON a.assigned_to = assigned_user.id AND a.tenant_id = assigned_user.tenant_id
                    WHERE a.id = %s AND a.tenant_id = %s AND a.org_id = %s 
                    AND a.bus_id = %s AND a.loc_id = %s""",
                    (appointment_id, tenant_id, org_id, bus_id, loc_id),
                )
                appointment = cursor.fetchone()

                if not appointment:
                    return Respons(
                        success=False,
                        detail="Appointment not found",
                        error="NOT_FOUND",
                    )

                appointment_dict = dict(appointment)
                appointment_dict['created_by'] = appointment_dict.get('created_by') or None
                appointment_dict['updated_by'] = appointment_dict.get('updated_by') or None
                appointment_dict['deleted_by'] = appointment_dict.get('deleted_by') or None
                appointment_dict['customer_name'] = appointment_dict.get('customer_name') or None
                appointment_dict['customer_id'] = appointment_dict.get('customer_id') or None
                appointment_dict['assigned_to_name'] = appointment_dict.get('assigned_to_name') or None
                appointment_dict['assigned_to_id'] = appointment_dict.get('assigned_to') or None
                appointment_read = GetAppointmentServiceReadDto(**appointment_dict)

                return Respons(
                    success=True,
                    detail="Appointment retrieved successfully",
                    data=[appointment_read],
                )

        except Exception as e:
            logger.error(f"Error getting appointment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get appointment: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_appointments(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        status: Optional[str] = None,
        appointment_type: Optional[str] = None,
        assigned_to: Optional[str] = None,
        customer_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetAppointmentsServiceReadDto]]:
        """Get list of appointments with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "a.tenant_id = %s",
                    "a.org_id = %s",
                    "a.bus_id = %s",
                    "a.loc_id = %s",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if status:
                    where_conditions.append("a.status = %s")
                    params.append(status)
                if appointment_type:
                    where_conditions.append("a.appointment_type = %s")
                    params.append(appointment_type)
                if assigned_to:
                    where_conditions.append("a.assigned_to = %s")
                    params.append(assigned_to)
                if customer_id:
                    where_conditions.append("a.customer_id = %s")
                    params.append(customer_id)
                if search:
                    where_conditions.append("a.description ILIKE %s")
                    search_pattern = f"%{search}%"
                    params.append(search_pattern)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_APPOINTMENTS_TABLE} a WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get appointments with user fullnames, customer name, and assigned_to name
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.fullname as customer_name,
                           assigned_user.fullname as assigned_to_name
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c ON a.customer_id = c.id AND a.tenant_id = c.tenant_id AND a.org_id = c.org_id AND a.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assigned_user ON a.assigned_to = assigned_user.id AND a.tenant_id = assigned_user.tenant_id
                    WHERE {where_clause}
                    ORDER BY a.start_datetime ASC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                appointments = cursor.fetchall()

                appointment_list = []
                for apt in appointments:
                    apt_dict = dict(apt)
                    apt_dict['created_by'] = apt_dict.get('created_by') or None
                    apt_dict['updated_by'] = apt_dict.get('updated_by') or None
                    apt_dict['deleted_by'] = apt_dict.get('deleted_by') or None
                    apt_dict['customer_name'] = apt_dict.get('customer_name') or None
                    apt_dict['customer_id'] = apt_dict.get('customer_id') or None
                    apt_dict['assigned_to_name'] = apt_dict.get('assigned_to_name') or None
                    apt_dict['assigned_to_id'] = apt_dict.get('assigned_to') or None
                    appointment_list.append(GetAppointmentsServiceReadDto(**apt_dict))

                pagination_meta = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Appointments retrieved successfully",
                    data=appointment_list,
                    pagination=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting appointments: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get appointments: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_appointment(
        data: DeleteAppointmentServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        deleted_by: str
    ) -> Respons[DeleteAppointmentServiceReadDto]:
        """Delete an appointment (hard delete)"""
        logger.info(
            f"Processing appointment deletion: {data.appointment_id}",
            extra={
                "extra_fields": {
                    "appointment_id": data.appointment_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if appointment exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_APPOINTMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s""",
                    (data.appointment_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_appointment = cursor.fetchone()

                if not existing_appointment:
                    raise ValueError("Appointment not found")

                # Hard delete - permanently remove the appointment
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_APPOINTMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s""",
                    (data.appointment_id, tenant_id, org_id, bus_id, loc_id),
                )
                
                # Check if deletion was successful (rowcount tells us how many rows were affected)
                if cursor.rowcount == 0:
                    raise ValueError("Failed to delete appointment")

                # Log activity
                try:
                    old_data = dict(existing_appointment)
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-appointments",
                        resource_id=data.appointment_id,
                        action="delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Appointment {data.appointment_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Appointment deleted successfully: {data.appointment_id}")

                return Respons(
                    success=True,
                    detail="Appointment deleted successfully",
                    data=[DeleteAppointmentServiceReadDto(
                        appointment_id=data.appointment_id,
                        message="Appointment deleted successfully"
                    )],
                )

        except ValueError as e:
            logger.error(f"Validation error deleting appointment: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error deleting appointment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete appointment: {str(e)}",
                error="INTERNAL_ERROR",
            )


