from typing import Optional
from src.entities.clients.clients_read_dto import (
    CreateClientServiceReadDto,
    UpdateClientServiceReadDto,
    DeleteClientServiceReadDto,
    GetClientServiceReadDto,
    GetClientsServiceReadDto,
    PermanentDeleteClientServiceReadDto,
)
from src.entities.clients.clients_write_dto import (
    CreateClientServiceWriteDto,
    UpdateClientServiceWriteDto,
    DeleteClientServiceWriteDto,
    PermanentDeleteClientServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("clients_service")


class ClientsService:
    """Service class for clients operations"""

    @staticmethod
    def create_client(
        data: CreateClientServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateClientServiceReadDto]:
        """Create a new client"""
        logger.info(
            f"Processing client creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "fullname": data.fullname,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if client with same fullname already exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_CLIENTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND fullname = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.fullname),
                )
                existing_client = cursor.fetchone()

                if existing_client:
                    return Respons(
                        success=False,
                        detail=f"Client with fullname '{data.fullname}' already exists",
                        error="DUPLICATE_NAME",
                    )

                # Check if client with same email already exists (if email provided)
                if data.email:
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CLIENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND email = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.email),
                    )
                    existing_email = cursor.fetchone()

                    if existing_email:
                        return Respons(
                            success=False,
                            detail=f"Client with email '{data.email}' already exists",
                            error="DUPLICATE_EMAIL",
                        )

                # Check if client with same contact already exists (if contact provided)
                if data.contact:
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CLIENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND contact = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.contact),
                    )
                    existing_contact = cursor.fetchone()

                    if existing_contact:
                        return Respons(
                            success=False,
                            detail=f"Client with contact '{data.contact}' already exists",
                            error="DUPLICATE_CONTACT",
                        )

                # Generate client ID
                client_id = Helper.generate_unique_identifier(prefix="cli")

                # Insert into msg_clients table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_CLIENTS_TABLE}
                    (id, tenant_id, org_id, bus_id, fullname, email, 
                     contact, address, description, is_active, delete_status, 
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        client_id, tenant_id, org_id, bus_id,
                        data.fullname, data.email,
                        data.contact, data.address, data.description,
                        data.is_active, 'NOT_DELETED',
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                client_result = cursor.fetchone()

                if not client_result:
                    raise ValueError("Failed to create client")

                # Get client with user fullnames
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CLIENTS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE c.id = %s AND c.tenant_id = %s""",
                    (client_id, tenant_id),
                )
                client_with_users = cursor.fetchone()

                if client_with_users:
                    client_dict = dict(client_with_users)
                    # Replace user IDs with fullnames (or None if not found)
                    client_dict['created_by'] = client_dict.get('created_by') or None
                    client_dict['updated_by'] = client_dict.get('updated_by') or None
                    client_dict['deleted_by'] = client_dict.get('deleted_by') or None
                else:
                    client_dict = dict(client_result)
                    client_dict['created_by'] = None
                    client_dict['updated_by'] = None
                    client_dict['deleted_by'] = None

                client_read = CreateClientServiceReadDto(**client_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_CLIENTS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (client_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(client_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-clients",
                        resource_id=client_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Client {client_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Client created successfully: {client_id}",
                    extra={
                        "extra_fields": {
                            "client_id": client_id,
                            "fullname": data.fullname,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Client created successfully",
                    data=[client_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating client: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating client: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create client: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_client(
        data: UpdateClientServiceWriteDto,
        client_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateClientServiceReadDto]:
        """Update a client"""
        logger.info(
            f"Processing client update: {client_id}",
            extra={
                "extra_fields": {
                    "client_id": client_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data (for audit/activity log)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_CLIENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (client_id, tenant_id, org_id, bus_id),
                )
                existing_client = cursor.fetchone()

                if not existing_client:
                    raise ValueError("Client not found")
                
                # Store complete old data before update
                old_data = dict(existing_client)

                # If fullname is being updated, check for duplicates
                if data.fullname is not None and data.fullname != old_data.get('fullname'):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_CLIENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND fullname = %s AND id != %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.fullname, client_id),
                    )
                    duplicate = cursor.fetchone()
                    if duplicate:
                        raise ValueError(f"Client with fullname '{data.fullname}' already exists")

                # If email is being updated, check for duplicates (if email provided)
                if data.email is not None and data.email != old_data.get('email'):
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CLIENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND email = %s AND id != %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.email, client_id),
                    )
                    duplicate_email = cursor.fetchone()
                    if duplicate_email:
                        raise ValueError(f"Client with email '{data.email}' already exists")

                # If contact is being updated, check for duplicates (if contact provided)
                if data.contact is not None and data.contact != old_data.get('contact'):
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CLIENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND contact = %s AND id != %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.contact, client_id),
                    )
                    duplicate_contact = cursor.fetchone()
                    if duplicate_contact:
                        raise ValueError(f"Client with contact '{data.contact}' already exists")

                # Build update query dynamically
                update_fields = []
                params = []

                if data.fullname is not None:
                    update_fields.append("fullname = %s")
                    params.append(data.fullname)
                if data.email is not None:
                    update_fields.append("email = %s")
                    params.append(data.email)
                if data.contact is not None:
                    update_fields.append("contact = %s")
                    params.append(data.contact)
                if data.address is not None:
                    update_fields.append("address = %s")
                    params.append(data.address)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([client_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_CLIENTS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_client = cursor.fetchone()

                if not updated_client:
                    raise ValueError("Failed to update client")

                # Get client with user fullnames
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CLIENTS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE c.id = %s AND c.tenant_id = %s""",
                    (client_id, tenant_id),
                )
                client_with_users = cursor.fetchone()

                if client_with_users:
                    client_dict = dict(client_with_users)
                    client_dict['created_by'] = client_dict.get('created_by') or None
                    client_dict['updated_by'] = client_dict.get('updated_by') or None
                    client_dict['deleted_by'] = client_dict.get('deleted_by') or None
                else:
                    client_dict = dict(updated_client)
                    client_dict['created_by'] = None
                    client_dict['updated_by'] = None
                    client_dict['deleted_by'] = None

                client_read = UpdateClientServiceReadDto(**client_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_CLIENTS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (client_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(client_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-clients",
                        resource_id=client_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Client {client_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Client updated successfully: {client_id}")

                return Respons(
                    success=True,
                    detail="Client updated successfully",
                    data=[client_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating client: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating client: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update client: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_client(
        data: DeleteClientServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteClientServiceReadDto]:
        """Soft delete a client"""
        logger.info(
            f"Processing client soft delete: {data.client_id}",
            extra={
                "extra_fields": {
                    "client_id": data.client_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_CLIENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.client_id, tenant_id, org_id, bus_id),
                )
                existing_client = cursor.fetchone()

                if not existing_client:
                    return Respons(
                        success=False,
                        detail="Client not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                old_data = dict(existing_client)

                # Soft delete - update delete_status
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_CLIENTS_TABLE}
                    SET delete_status = 'DELETED', deleted_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    (deleted_by, data.client_id, tenant_id, org_id, bus_id),
                )
                deleted_client = cursor.fetchone()

                if not deleted_client:
                    raise ValueError("Failed to delete client")

                # Get client with user fullnames
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CLIENTS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE c.id = %s AND c.tenant_id = %s""",
                    (data.client_id, tenant_id),
                )
                client_with_users = cursor.fetchone()

                if client_with_users:
                    client_dict = dict(client_with_users)
                    client_dict['created_by'] = client_dict.get('created_by') or None
                    client_dict['updated_by'] = client_dict.get('updated_by') or None
                    client_dict['deleted_by'] = client_dict.get('deleted_by') or None
                else:
                    client_dict = dict(deleted_client)
                    client_dict['created_by'] = None
                    client_dict['updated_by'] = None
                    client_dict['deleted_by'] = None

                client_read = DeleteClientServiceReadDto(**client_dict)

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-clients",
                        resource_id=data.client_id,
                        action="delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Client {data.client_id} soft deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Client soft deleted successfully: {data.client_id}")

                return Respons(
                    success=True,
                    detail="Client deleted successfully",
                    data=[client_read],
                )

        except Exception as e:
            logger.error(f"Error deleting client: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete client: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_client(
        client_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetClientServiceReadDto]:
        """Get a single client by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CLIENTS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE c.id = %s AND c.tenant_id = %s AND c.org_id = %s 
                    AND c.bus_id = %s AND c.delete_status = 'NOT_DELETED'""",
                    (client_id, tenant_id, org_id, bus_id),
                )
                client = cursor.fetchone()

                if not client:
                    return Respons(
                        success=False,
                        detail="Client not found",
                        error="NOT_FOUND",
                    )

                client_dict = dict(client)
                client_dict['created_by'] = client_dict.get('created_by') or None
                client_dict['updated_by'] = client_dict.get('updated_by') or None
                client_dict['deleted_by'] = client_dict.get('deleted_by') or None
                client_read = GetClientServiceReadDto(**client_dict)

                return Respons(
                    success=True,
                    detail="Client retrieved successfully",
                    data=[client_read],
                )

        except Exception as e:
            logger.error(f"Error getting client: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get client: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_clients(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetClientsServiceReadDto]]:
        """Get list of clients with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "c.tenant_id = %s",
                    "c.org_id = %s",
                    "c.bus_id = %s",
                    "c.delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id, org_id, bus_id]

                if is_active is not None:
                    where_conditions.append("c.is_active = %s")
                    params.append(is_active)
                if search:
                    where_conditions.append(
                        "(c.fullname ILIKE %s OR c.email ILIKE %s OR c.contact ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_CLIENTS_TABLE} c WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get clients with user fullnames
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CLIENTS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY c.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                clients = cursor.fetchall()

                client_list = []
                for cli in clients:
                    cli_dict = dict(cli)
                    cli_dict['created_by'] = cli_dict.get('created_by') or None
                    cli_dict['updated_by'] = cli_dict.get('updated_by') or None
                    cli_dict['deleted_by'] = cli_dict.get('deleted_by') or None
                    client_list.append(GetClientsServiceReadDto(**cli_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Clients retrieved successfully",
                    data=client_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting clients: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get clients: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def permanent_delete_client(
        data: PermanentDeleteClientServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[PermanentDeleteClientServiceReadDto]:
        """Permanently delete a client"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get client details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_CLIENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.client_id, tenant_id, org_id, bus_id),
                )
                client = cursor.fetchone()

                if not client:
                    return Respons(
                        success=False,
                        detail="Client not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(client)

                # Log activity before permanent deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-clients",
                        resource_id=data.client_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Client {data.client_id} permanently deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Permanently delete
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_CLIENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.client_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Client permanently deleted successfully",
                    data=[PermanentDeleteClientServiceReadDto(
                        client_id=data.client_id,
                        message="Client permanently deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error permanently deleting client: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to permanently delete client: {str(e)}",
                error="INTERNAL_ERROR",
            )

