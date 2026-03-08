from datetime import datetime, timedelta, time as dt_time, timezone
from typing import Optional
from src.entities.store_configs.store_configs_read_dto import (
    CreateOrUpdateStoreConfigServiceReadDto,
    GetStoreConfigServiceReadDto,
)
from src.entities.store_configs.store_configs_write_dto import (
    CreateOrUpdateStoreConfigServiceWriteDto,
)
from src.entities.shared.sh_response import Respons
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("store_configs_service")


class StoreConfigsService:
    """Service class for store configs operations"""

    @staticmethod
    def _calculate_next_stock_take_datetime(
        closing_time: Optional[dt_time],
        num_of_days: int
    ) -> Optional[datetime]:
        """Calculate next stock take datetime based on closing time and number of days"""
        if not closing_time or num_of_days <= 0:
            return None
        
        # Get current datetime (timezone-aware, UTC)
        now = datetime.now(timezone.utc)
        
        # Create datetime for today with the closing time (timezone-aware, UTC)
        closing_datetime = datetime.combine(now.date(), closing_time, tzinfo=timezone.utc)
        
        # If closing time has already passed today, use tomorrow's date
        if closing_datetime < now:
            closing_datetime = datetime.combine(now.date() + timedelta(days=1), closing_time, tzinfo=timezone.utc)
        
        # Add the number of days to get the next stock take datetime
        next_stock_take = closing_datetime + timedelta(days=num_of_days)
        
        return next_stock_take

    @staticmethod
    def _create_or_update_stock_taking_audit(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        enable_auto_stock_take: bool,
        num_of_days_to_take_stock: int,
        closing_time: Optional[dt_time],
        user_id: str
    ) -> None:
        """Create or update stock taking audit record if auto stock take is enabled"""
        if not enable_auto_stock_take or num_of_days_to_take_stock <= 0:
            # If auto stock take is disabled, deactivate any active audit records
            cursor.execute(
                f"""UPDATE {db_settings.MSG_STOCK_TAKING_AUDIT_TABLE}
                SET is_active = FALSE,
                    updated_by = %s
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                  AND is_active = TRUE""",
                (user_id, tenant_id, org_id, bus_id, loc_id),
            )
            deactivated_count = cursor.rowcount
            if deactivated_count > 0:
                logger.info(f"Auto stock take disabled, deactivated {deactivated_count} active audit record(s)")
            return
        
        if not closing_time:
            logger.warning(
                f"Cannot create stock taking audit: closing_time is required when auto stock take is enabled"
            )
            return
        
        # Calculate next stock take datetime
        next_stock_take_datetime = StoreConfigsService._calculate_next_stock_take_datetime(
            closing_time, num_of_days_to_take_stock
        )
        
        if not next_stock_take_datetime:
            logger.warning(f"Failed to calculate next stock take datetime")
            return
        
        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        current_datetime = Helper.current_date_time()["cdatetime"]
        
        # Always create a new audit record and deactivate previous ones
        # This allows multiple entries per location, with only one active at a time
        # First, deactivate all previous active audit records for this location
        logger.info(f"Deactivating previous stock taking audit records for tenant_id={tenant_id}, org_id={org_id}, bus_id={bus_id}, loc_id={loc_id}")
        cursor.execute(
            f"""UPDATE {db_settings.MSG_STOCK_TAKING_AUDIT_TABLE}
            SET is_active = FALSE,
                updated_by = %s
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
              AND is_active = TRUE""",
            (user_id, tenant_id, org_id, bus_id, loc_id),
        )
        deactivated_count = cursor.rowcount
        if deactivated_count > 0:
            logger.info(f"Deactivated {deactivated_count} previous stock taking audit record(s)")
        
        # Create new active audit record
        logger.info(f"Creating new stock taking audit for tenant_id={tenant_id}, org_id={org_id}, bus_id={bus_id}, loc_id={loc_id}")
        audit_id = Helper.generate_unique_identifier(prefix="sta")
        cursor.execute(
            f"""INSERT INTO {db_settings.MSG_STOCK_TAKING_AUDIT_TABLE}
            (id, tenant_id, org_id, bus_id, loc_id, start_datetime, next_stock_take_datetime,
             is_active, cdate, ctime, cdatetime, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *""",
            (
                audit_id, tenant_id, org_id, bus_id, loc_id,
                current_datetime, next_stock_take_datetime,
                True,  # is_active = TRUE for new record
                cdate, ctime, current_datetime, user_id
            ),
        )
        new_audit = cursor.fetchone()
        if new_audit:
            logger.info(f"Stock taking audit created successfully: {audit_id}")
        else:
            logger.warning(f"Failed to create stock taking audit")

    @staticmethod
    def create_or_update_config(
        data: CreateOrUpdateStoreConfigServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        user_id: str
    ) -> Respons[CreateOrUpdateStoreConfigServiceReadDto]:
        """Create or update a store config (upsert)"""
        logger.info(
            f"Processing store config upsert",
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
                    f"""SELECT * FROM {db_settings.MSG_STORE_CONFIGS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                existing_config = cursor.fetchone()

                if existing_config:
                    # Update existing config
                    logger.info(f"Store config exists, updating for tenant_id={tenant_id}, org_id={org_id}, bus_id={bus_id}, loc_id={loc_id}")
                    
                    # Store complete old data before update
                    old_data = dict(existing_config)

                    # Build update query dynamically
                    # For upsert, we update all fields that are provided
                    # Optional fields (store_name, description, times) can be None
                    # Fields with defaults (booleans, int) will always have values
                    update_fields = []
                    params = []

                    # Optional fields - only update if not None
                    if data.store_name is not None:
                        update_fields.append("store_name = %s")
                        params.append(data.store_name)
                    if data.description is not None:
                        update_fields.append("description = %s")
                        params.append(data.description)
                    if data.address is not None:
                        update_fields.append("address = %s")
                        params.append(data.address)
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
                    update_fields.append("is_visible_on_ecommerce = %s")
                    params.append(data.is_visible_on_ecommerce)
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)
                    update_fields.append("enable_auto_stock_take = %s")
                    params.append(data.enable_auto_stock_take)
                    update_fields.append("num_of_days_to_take_stock = %s")
                    params.append(data.num_of_days_to_take_stock)
                    update_fields.append("enable_daily_reports = %s")
                    params.append(data.enable_daily_reports)
                    update_fields.append("lock_based_on_closing_time = %s")
                    params.append(data.lock_based_on_closing_time)
                    update_fields.append("change_to_card = %s")
                    params.append(data.change_to_card)

                    update_fields.append("updated_by = %s")
                    params.append(user_id)
                    params.extend([tenant_id, org_id, bus_id, loc_id])

                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_STORE_CONFIGS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        RETURNING *""",
                        tuple(params),
                    )
                    updated_config = cursor.fetchone()

                    if not updated_config:
                        raise ValueError("Failed to update store config")

                    # Get config with user fullnames and next_stock_take_datetime from active audit
                    cursor.execute(
                        f"""SELECT sc.*,
                               creator.fullname as created_by,
                               updater.fullname as updated_by,
                               deleter.fullname as deleted_by,
                               manager_user.fullname as manager,
                               sta.next_stock_take_datetime
                        FROM {db_settings.MSG_STORE_CONFIGS_TABLE} sc
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sc.created_by = creator.id AND sc.tenant_id = creator.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sc.updated_by = updater.id AND sc.tenant_id = updater.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sc.deleted_by = deleter.id AND sc.tenant_id = deleter.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} manager_user ON sc.manager_id = manager_user.id AND sc.tenant_id = manager_user.tenant_id
                        LEFT JOIN {db_settings.MSG_STOCK_TAKING_AUDIT_TABLE} sta ON sc.tenant_id = sta.tenant_id 
                            AND sc.org_id = sta.org_id 
                            AND sc.bus_id = sta.bus_id 
                            AND sc.loc_id = sta.loc_id 
                            AND sta.is_active = TRUE
                        WHERE sc.tenant_id = %s AND sc.org_id = %s AND sc.bus_id = %s AND sc.loc_id = %s""",
                        (tenant_id, org_id, bus_id, loc_id),
                    )
                    config_with_users = cursor.fetchone()

                    if config_with_users:
                        config_dict = dict(config_with_users)
                        config_dict['created_by'] = config_dict.get('created_by') or None
                        config_dict['updated_by'] = config_dict.get('updated_by') or None
                        config_dict['deleted_by'] = config_dict.get('deleted_by') or None
                        config_dict['manager'] = config_dict.get('manager') or None
                        config_dict['next_stock_take_datetime'] = config_dict.get('next_stock_take_datetime') or None
                    else:
                        config_dict = dict(updated_config)
                        config_dict['created_by'] = None
                        config_dict['updated_by'] = None
                        config_dict['deleted_by'] = None
                        config_dict['manager'] = None
                        config_dict['next_stock_take_datetime'] = None

                    config_read = CreateOrUpdateStoreConfigServiceReadDto(**config_dict)

                    # Log activity
                    try:
                        cursor.execute(
                            f"""SELECT * FROM {db_settings.MSG_STORE_CONFIGS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                            (tenant_id, org_id, bus_id, loc_id),
                        )
                        complete_new_data_record = cursor.fetchone()
                        if complete_new_data_record:
                            complete_new_data = dict(complete_new_data_record)
                            
                            ActivityLogService.log_activity(
                                tenant_id=tenant_id,
                                resource_type="rt-store-configs",
                                resource_id=config_dict.get('id', ''),
                                action="update",
                                old_data=old_data,
                                new_data=complete_new_data,
                                description=f"Store config updated for location {loc_id}",
                                performed_by=user_id,
                                org_id=org_id,
                                bus_id=bus_id,
                                loc_id=loc_id,
                                cursor=cursor
                            )
                    except Exception as log_err:
                        logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                    # Handle stock taking audit if auto stock take is enabled
                    try:
                        # Get final values for stock taking audit
                        final_enable_auto_stock_take = data.enable_auto_stock_take
                        final_num_of_days = data.num_of_days_to_take_stock
                        # Use updated closing_time if provided, otherwise use existing
                        existing_config_dict = dict(existing_config) if existing_config else {}
                        final_closing_time = data.closing_time if data.closing_time is not None else existing_config_dict.get('closing_time')
                        
                        StoreConfigsService._create_or_update_stock_taking_audit(
                            cursor=cursor,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            loc_id=loc_id,
                            enable_auto_stock_take=final_enable_auto_stock_take,
                            num_of_days_to_take_stock=final_num_of_days,
                            closing_time=final_closing_time,
                            user_id=user_id
                        )
                    except Exception as audit_err:
                        logger.warning(f"Stock taking audit failed: {audit_err}", exc_info=True)
                        # Don't fail the whole operation if audit fails

                    logger.info(f"Store config updated successfully for location {loc_id}")

                    return Respons(
                        success=True,
                        detail="Store config updated successfully",
                        data=[config_read],
                    )
                else:
                    # Create new config
                    logger.info(f"Store config does not exist, creating new one for tenant_id={tenant_id}, org_id={org_id}, bus_id={bus_id}, loc_id={loc_id}")
                    
                    # Generate config ID
                    config_id = Helper.generate_unique_identifier(prefix="stc")

                    # Insert into msg_store_configs table
                    logger.info(f"Inserting store config {config_id} into {db_settings.MSG_STORE_CONFIGS_TABLE}")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_STORE_CONFIGS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, store_name, description,
                         is_visible_on_ecommerce, address, is_active, manager_id,
                         enable_auto_stock_take, num_of_days_to_take_stock,
                         enable_daily_reports, openning_time, closing_time, lock_based_on_closing_time, change_to_card,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            config_id, tenant_id, org_id, bus_id, loc_id,
                            data.store_name, data.description,
                            data.is_visible_on_ecommerce, data.address, data.is_active, data.manager_id,
                            data.enable_auto_stock_take, data.num_of_days_to_take_stock,
                            data.enable_daily_reports, data.openning_time, data.closing_time, data.lock_based_on_closing_time, data.change_to_card,
                            cdate, ctime, cdatetime, user_id
                        ),
                    )
                    config_result = cursor.fetchone()

                    if not config_result:
                        raise ValueError("Failed to create store config")
                    
                    logger.info(f"Store config {config_id} inserted successfully, rowcount: {cursor.rowcount}")

                    # Get config with user fullnames and next_stock_take_datetime from active audit
                    cursor.execute(
                        f"""SELECT sc.*,
                               creator.fullname as created_by,
                               updater.fullname as updated_by,
                               deleter.fullname as deleted_by,
                               manager_user.fullname as manager,
                               sta.next_stock_take_datetime
                        FROM {db_settings.MSG_STORE_CONFIGS_TABLE} sc
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sc.created_by = creator.id AND sc.tenant_id = creator.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sc.updated_by = updater.id AND sc.tenant_id = updater.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sc.deleted_by = deleter.id AND sc.tenant_id = deleter.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} manager_user ON sc.manager_id = manager_user.id AND sc.tenant_id = manager_user.tenant_id
                        LEFT JOIN {db_settings.MSG_STOCK_TAKING_AUDIT_TABLE} sta ON sc.tenant_id = sta.tenant_id 
                            AND sc.org_id = sta.org_id 
                            AND sc.bus_id = sta.bus_id 
                            AND sc.loc_id = sta.loc_id 
                            AND sta.is_active = TRUE
                        WHERE sc.id = %s AND sc.tenant_id = %s AND sc.org_id = %s AND sc.bus_id = %s AND sc.loc_id = %s""",
                        (config_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    config_with_users = cursor.fetchone()

                    if config_with_users:
                        config_dict = dict(config_with_users)
                        config_dict['created_by'] = config_dict.get('created_by') or None
                        config_dict['updated_by'] = config_dict.get('updated_by') or None
                        config_dict['deleted_by'] = config_dict.get('deleted_by') or None
                        config_dict['manager'] = config_dict.get('manager') or None
                        config_dict['next_stock_take_datetime'] = config_dict.get('next_stock_take_datetime') or None
                    else:
                        config_dict = dict(config_result)
                        config_dict['created_by'] = None
                        config_dict['updated_by'] = None
                        config_dict['deleted_by'] = None
                        config_dict['manager'] = None
                        config_dict['next_stock_take_datetime'] = None

                    # Create DTO
                    try:
                        config_read = CreateOrUpdateStoreConfigServiceReadDto(**config_dict)
                    except Exception as dto_err:
                        logger.error(f"Failed to create DTO: {dto_err}", exc_info=True)
                        logger.error(f"Config dict keys: {list(config_dict.keys()) if config_dict else 'None'}")
                        logger.error(f"Config dict: {config_dict}")
                        raise ValueError(f"Failed to create response DTO: {str(dto_err)}")

                    logger.info(
                        f"Store config created successfully: {config_id}",
                        extra={
                            "extra_fields": {
                                "config_id": config_id,
                                "loc_id": loc_id,
                            }
                        },
                    )

                    # Get complete data for activity log (before committing)
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_STORE_CONFIGS_TABLE}
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
                                    resource_type="rt-store-configs",
                                    resource_id=config_id,
                                    action="create",
                                    old_data=None,
                                    new_data=complete_new_data,
                                    description=f"Store config {config_id} created successfully",
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

                    # Handle stock taking audit if auto stock take is enabled
                    try:
                        StoreConfigsService._create_or_update_stock_taking_audit(
                            cursor=cursor,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            loc_id=loc_id,
                            enable_auto_stock_take=data.enable_auto_stock_take,
                            num_of_days_to_take_stock=data.num_of_days_to_take_stock,
                            closing_time=data.closing_time,
                            user_id=user_id
                        )
                    except Exception as audit_err:
                        logger.warning(f"Stock taking audit failed: {audit_err}", exc_info=True)
                        # Don't fail the whole operation if audit fails

                    logger.info(f"About to return success response for config {config_id} - transaction should commit")

                    return Respons(
                        success=True,
                        detail="Store config created successfully",
                        data=[config_read],
                    )

        except ValueError as e:
            logger.error(f"Validation error creating/updating store config: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating/updating store config: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create/update store config: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_config(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetStoreConfigServiceReadDto]:
        """Get a store config by tenant_id, org_id, bus_id, loc_id"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT sc.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           manager_user.fullname as manager,
                           sta.next_stock_take_datetime
                    FROM {db_settings.MSG_STORE_CONFIGS_TABLE} sc
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sc.created_by = creator.id AND sc.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sc.updated_by = updater.id AND sc.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sc.deleted_by = deleter.id AND sc.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} manager_user ON sc.manager_id = manager_user.id AND sc.tenant_id = manager_user.tenant_id
                    LEFT JOIN {db_settings.MSG_STOCK_TAKING_AUDIT_TABLE} sta ON sc.tenant_id = sta.tenant_id 
                        AND sc.org_id = sta.org_id 
                        AND sc.bus_id = sta.bus_id 
                        AND sc.loc_id = sta.loc_id 
                        AND sta.is_active = TRUE
                    WHERE sc.tenant_id = %s AND sc.org_id = %s AND sc.bus_id = %s AND sc.loc_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                config = cursor.fetchone()

                if not config:
                    return Respons(
                        success=False,
                        detail="Store config not found",
                        error="NOT_FOUND",
                    )

                config_dict = dict(config)
                config_dict['created_by'] = config_dict.get('created_by') or None
                config_dict['updated_by'] = config_dict.get('updated_by') or None
                config_dict['deleted_by'] = config_dict.get('deleted_by') or None
                config_dict['manager'] = config_dict.get('manager') or None
                config_dict['next_stock_take_datetime'] = config_dict.get('next_stock_take_datetime') or None
                config_read = GetStoreConfigServiceReadDto(**config_dict)

                return Respons(
                    success=True,
                    detail="Store config retrieved successfully",
                    data=[config_read],
                )

        except Exception as e:
            logger.error(f"Error getting store config: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get store config: {str(e)}",
                error="INTERNAL_ERROR",
            )

