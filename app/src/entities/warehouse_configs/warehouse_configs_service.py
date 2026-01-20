from typing import Optional
from src.entities.warehouse_configs.warehouse_configs_read_dto import (
    CreateOrUpdateWarehouseConfigServiceReadDto,
    GetWarehouseConfigServiceReadDto,
)
from src.entities.warehouse_configs.warehouse_configs_write_dto import (
    CreateOrUpdateWarehouseConfigServiceWriteDto,
)
from src.entities.shared.sh_response import Respons
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("warehouse_configs_service")


class WarehouseConfigsService:
    """Service class for warehouse configs operations"""

    @staticmethod
    def create_or_update_config(
        data: CreateOrUpdateWarehouseConfigServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        user_id: str
    ) -> Respons[CreateOrUpdateWarehouseConfigServiceReadDto]:
        """Create or update a warehouse config (upsert)"""
        logger.info(
            f"Processing warehouse config upsert",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "user_id": user_id,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if config exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                existing_config = cursor.fetchone()

                if existing_config:
                    # Update existing config
                    logger.info(f"Warehouse config exists, updating for tenant_id={tenant_id}, org_id={org_id}, bus_id={bus_id}, loc_id={loc_id}")
                    
                    # Store complete old data before update
                    old_data = dict(existing_config)

                    # Build update query dynamically
                    update_fields = []
                    params = []

                    # Optional fields - only update if not None
                    if data.warehouse_name is not None:
                        update_fields.append("warehouse_name = %s")
                        params.append(data.warehouse_name)
                    if data.description is not None:
                        update_fields.append("description = %s")
                        params.append(data.description)
                    if data.aadress is not None:
                        update_fields.append("aadress = %s")
                        params.append(data.aadress)
                    if data.manager_id is not None:
                        update_fields.append("manager_id = %s")
                        params.append(data.manager_id)
                    if data.openning_time is not None:
                        update_fields.append("openning_time = %s")
                        params.append(data.openning_time)
                    if data.closing_time is not None:
                        update_fields.append("closing_time = %s")
                        params.append(data.closing_time)
                    
                    # Fields with defaults - always update (they will always have values)
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                    update_fields.append("updated_by = %s")
                    params.append(user_id)
                    params.extend([tenant_id, org_id, bus_id, loc_id])

                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        RETURNING *""",
                        tuple(params),
                    )
                    updated_config = cursor.fetchone()

                    if not updated_config:
                        raise ValueError("Failed to update warehouse config")

                    # Get config with user fullnames
                    cursor.execute(
                        f"""SELECT wc.*,
                               creator.fullname as created_by,
                               updater.fullname as updated_by,
                               deleter.fullname as deleted_by,
                               manager_user.fullname as manager
                        FROM {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE} wc
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON wc.created_by = creator.id AND wc.tenant_id = creator.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON wc.updated_by = updater.id AND wc.tenant_id = updater.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON wc.deleted_by = deleter.id AND wc.tenant_id = deleter.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} manager_user ON wc.manager_id = manager_user.id AND wc.tenant_id = manager_user.tenant_id
                        WHERE wc.tenant_id = %s AND wc.org_id = %s AND wc.bus_id = %s AND wc.loc_id = %s""",
                        (tenant_id, org_id, bus_id, loc_id),
                    )
                    config_with_users = cursor.fetchone()

                    if config_with_users:
                        config_dict = dict(config_with_users)
                        config_dict['created_by'] = config_dict.get('created_by') or None
                        config_dict['updated_by'] = config_dict.get('updated_by') or None
                        config_dict['deleted_by'] = config_dict.get('deleted_by') or None
                        config_dict['manager'] = config_dict.get('manager') or None
                    else:
                        config_dict = dict(updated_config)
                        config_dict['created_by'] = None
                        config_dict['updated_by'] = None
                        config_dict['deleted_by'] = None
                        config_dict['manager'] = None

                    config_read = CreateOrUpdateWarehouseConfigServiceReadDto(**config_dict)

                    # Log activity
                    try:
                        cursor.execute(
                            f"""SELECT * FROM {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                            (tenant_id, org_id, bus_id, loc_id),
                        )
                        complete_new_data_record = cursor.fetchone()
                        if complete_new_data_record:
                            complete_new_data = dict(complete_new_data_record)
                            
                            ActivityLogService.log_activity(
                                tenant_id=tenant_id,
                                resource_type="rt-warehouse-configs",
                                resource_id=config_dict.get('id', ''),
                                action="update",
                                old_data=old_data,
                                new_data=complete_new_data,
                                description=f"Warehouse config updated for location {loc_id}",
                                performed_by=user_id,
                                org_id=org_id,
                                bus_id=bus_id,
                                loc_id=loc_id,
                                cursor=cursor
                            )
                    except Exception as log_err:
                        logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                    logger.info(f"Warehouse config updated successfully for location {loc_id}")

                    return Respons(
                        success=True,
                        detail="Warehouse config updated successfully",
                        data=[config_read],
                    )
                else:
                    # Create new config
                    logger.info(f"Warehouse config does not exist, creating new one for tenant_id={tenant_id}, org_id={org_id}, bus_id={bus_id}, loc_id={loc_id}")
                    
                    # Generate config ID
                    config_id = Helper.generate_unique_identifier(prefix="whc")

                    # Insert into msg_warehouse_configs table
                    logger.info(f"Inserting warehouse config {config_id} into {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE}")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, warehouse_name, description,
                         aadress, is_active, manager_id,
                         openning_time, closing_time,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            config_id, tenant_id, org_id, bus_id, loc_id,
                            data.warehouse_name, data.description,
                            data.aadress, data.is_active, data.manager_id,
                            data.openning_time, data.closing_time,
                            cdate, ctime, cdatetime, user_id
                        ),
                    )
                    config_result = cursor.fetchone()

                    if not config_result:
                        raise ValueError("Failed to create warehouse config")
                    
                    logger.info(f"Warehouse config {config_id} inserted successfully, rowcount: {cursor.rowcount}")

                    # Get config with user fullnames
                    cursor.execute(
                        f"""SELECT wc.*,
                               creator.fullname as created_by,
                               updater.fullname as updated_by,
                               deleter.fullname as deleted_by,
                               manager_user.fullname as manager
                        FROM {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE} wc
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON wc.created_by = creator.id AND wc.tenant_id = creator.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON wc.updated_by = updater.id AND wc.tenant_id = updater.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON wc.deleted_by = deleter.id AND wc.tenant_id = deleter.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} manager_user ON wc.manager_id = manager_user.id AND wc.tenant_id = manager_user.tenant_id
                        WHERE wc.id = %s AND wc.tenant_id = %s AND wc.org_id = %s AND wc.bus_id = %s AND wc.loc_id = %s""",
                        (config_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    config_with_users = cursor.fetchone()

                    if config_with_users:
                        config_dict = dict(config_with_users)
                        config_dict['created_by'] = config_dict.get('created_by') or None
                        config_dict['updated_by'] = config_dict.get('updated_by') or None
                        config_dict['deleted_by'] = config_dict.get('deleted_by') or None
                        config_dict['manager'] = config_dict.get('manager') or None
                    else:
                        config_dict = dict(config_result)
                        config_dict['created_by'] = None
                        config_dict['updated_by'] = None
                        config_dict['deleted_by'] = None
                        config_dict['manager'] = None

                    # Create DTO
                    try:
                        config_read = CreateOrUpdateWarehouseConfigServiceReadDto(**config_dict)
                    except Exception as dto_err:
                        logger.error(f"Failed to create DTO: {dto_err}", exc_info=True)
                        logger.error(f"Config dict keys: {list(config_dict.keys()) if config_dict else 'None'}")
                        logger.error(f"Config dict: {config_dict}")
                        raise ValueError(f"Failed to create response DTO: {str(dto_err)}")

                    logger.info(
                        f"Warehouse config created successfully: {config_id}",
                        extra={
                            "extra_fields": {
                                "config_id": config_id,
                                "loc_id": loc_id,
                            }
                        },
                    )

                    # Get complete data for activity log (before committing)
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (config_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else None

                    # Log activity
                    if complete_new_data:
                        try:
                            cursor.execute("SAVEPOINT before_activity_log")
                            try:
                                ActivityLogService.log_activity(
                                    tenant_id=tenant_id,
                                    resource_type="rt-warehouse-configs",
                                    resource_id=config_id,
                                    action="create",
                                    old_data=None,
                                    new_data=complete_new_data,
                                    description=f"Warehouse config {config_id} created successfully",
                                    performed_by=user_id,
                                    org_id=org_id,
                                    bus_id=bus_id,
                                    loc_id=loc_id,
                                    cursor=cursor
                                )
                                cursor.execute("RELEASE SAVEPOINT before_activity_log")
                            except Exception as log_err:
                                try:
                                    cursor.execute("ROLLBACK TO SAVEPOINT before_activity_log")
                                    logger.warning(f"Activity log failed (rolled back to savepoint): {log_err}")
                                except Exception as rollback_err:
                                    logger.error(f"Failed to rollback to savepoint: {rollback_err}", exc_info=True)
                                    raise
                        except Exception as savepoint_err:
                            logger.warning(f"Failed to create savepoint for activity log: {savepoint_err}", exc_info=True)

                    logger.info(f"About to return success response for config {config_id} - transaction should commit")

                    return Respons(
                        success=True,
                        detail="Warehouse config created successfully",
                        data=[config_read],
                    )

        except ValueError as e:
            logger.error(f"Validation error creating/updating warehouse config: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating/updating warehouse config: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create/update warehouse config: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_config(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetWarehouseConfigServiceReadDto]:
        """Get a warehouse config by tenant_id, org_id, bus_id, loc_id"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT wc.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           manager_user.fullname as manager
                    FROM {db_settings.MSG_WAREHOUSE_CONFIGS_TABLE} wc
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON wc.created_by = creator.id AND wc.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON wc.updated_by = updater.id AND wc.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON wc.deleted_by = deleter.id AND wc.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} manager_user ON wc.manager_id = manager_user.id AND wc.tenant_id = manager_user.tenant_id
                    WHERE wc.tenant_id = %s AND wc.org_id = %s AND wc.bus_id = %s AND wc.loc_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                config = cursor.fetchone()

                if not config:
                    return Respons(
                        success=False,
                        detail="Warehouse config not found",
                        error="NOT_FOUND",
                    )

                config_dict = dict(config)
                config_dict['created_by'] = config_dict.get('created_by') or None
                config_dict['updated_by'] = config_dict.get('updated_by') or None
                config_dict['deleted_by'] = config_dict.get('deleted_by') or None
                config_dict['manager'] = config_dict.get('manager') or None
                config_read = GetWarehouseConfigServiceReadDto(**config_dict)

                return Respons(
                    success=True,
                    detail="Warehouse config retrieved successfully",
                    data=[config_read],
                )

        except Exception as e:
            logger.error(f"Error getting warehouse config: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get warehouse config: {str(e)}",
                error="INTERNAL_ERROR",
            )

