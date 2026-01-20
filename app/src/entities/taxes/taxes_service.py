from decimal import Decimal
from src.entities.taxes.taxes_read_dto import (
    CreateTaxServiceReadDto,
    UpdateTaxServiceReadDto,
    GetTaxServiceReadDto,
    GetTaxesServiceReadDto,
    DeleteTaxServiceReadDto,
    GetTaxStatisticsServiceReadDto,
)
from src.entities.taxes.taxes_write_dto import (
    CreateTaxServiceWriteDto,
    UpdateTaxServiceWriteDto,
    DeleteTaxServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("taxes_service")


class TaxesService:
    """Service class for taxes operations"""

    @staticmethod
    def create_tax(
        data: CreateTaxServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateTaxServiceReadDto]:
        """Create a new tax"""
        logger.info(
            f"Processing tax creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "name": data.name,
                    "rate": data.rate,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Generate tax ID
                tax_id = Helper.generate_unique_identifier(prefix="tax")

                # Insert into msg_taxes table
                logger.info(f"Inserting tax {tax_id} into {db_settings.MSG_TAXES_TABLE}")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_TAXES_TABLE}
                    (id, tenant_id, org_id, bus_id, name, rate, description, is_active, is_inclusive,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        tax_id, tenant_id, org_id, bus_id,
                        data.name, data.rate, data.description,
                        data.is_active, data.is_inclusive,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                tax_result = cursor.fetchone()

                if not tax_result:
                    raise ValueError("Failed to create tax")
                
                logger.info(f"Tax {tax_id} inserted successfully, rowcount: {cursor.rowcount}")

                # Get tax with user fullnames
                cursor.execute(
                    f"""SELECT t.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAXES_TABLE} t
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON t.created_by = creator.id AND t.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON t.updated_by = updater.id AND t.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON t.deleted_by = deleter.id AND t.tenant_id = deleter.tenant_id
                    WHERE t.id = %s AND t.tenant_id = %s AND t.org_id = %s AND t.bus_id = %s""",
                    (tax_id, tenant_id, org_id, bus_id),
                )
                tax_with_users = cursor.fetchone()

                if tax_with_users:
                    if isinstance(tax_with_users, dict):
                        tax_dict = tax_with_users.copy()
                    else:
                        tax_dict = dict(tax_with_users)
                    tax_dict['created_by'] = tax_dict.get('created_by') or None
                    tax_dict['updated_by'] = tax_dict.get('updated_by') or None
                    tax_dict['deleted_by'] = tax_dict.get('deleted_by') or None
                else:
                    if isinstance(tax_result, dict):
                        tax_dict = tax_result.copy()
                    else:
                        tax_dict = dict(tax_result)
                    tax_dict['created_by'] = None
                    tax_dict['updated_by'] = None
                    tax_dict['deleted_by'] = None

                # Create DTO
                try:
                    tax_read = CreateTaxServiceReadDto(**tax_dict)
                except Exception as dto_err:
                    logger.error(f"Failed to create DTO: {dto_err}", exc_info=True)
                    logger.error(f"Tax dict keys: {list(tax_dict.keys()) if tax_dict else 'None'}")
                    logger.error(f"Tax dict: {tax_dict}")
                    raise ValueError(f"Failed to create response DTO: {str(dto_err)}")

                logger.info(
                    f"Tax created successfully: {tax_id}",
                    extra={
                        "extra_fields": {
                            "tax_id": tax_id,
                            "name": data.name,
                            "rate": data.rate,
                        }
                    },
                )

                # Get complete data for activity log (before committing)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_TAXES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (tax_id, tenant_id, org_id, bus_id),
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
                                resource_type="rt-taxes",
                                resource_id=tax_id,
                                action="create",
                                old_data=None,
                                new_data=complete_new_data,
                                description=f"Tax {tax_id} created successfully",
                                performed_by=created_by,
                                org_id=org_id,
                                bus_id=bus_id,
                                loc_id="",
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

                logger.info(f"About to return success response for tax {tax_id} - transaction should commit")

                return Respons(
                    success=True,
                    detail="Tax created successfully",
                    data=[tax_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating tax: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating tax: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create tax: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_tax(
        data: UpdateTaxServiceWriteDto,
        tax_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateTaxServiceReadDto]:
        """Update a tax"""
        logger.info(
            f"Processing tax update: {tax_id}",
            extra={
                "extra_fields": {
                    "tax_id": tax_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_TAXES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (tax_id, tenant_id, org_id, bus_id),
                )
                existing_tax = cursor.fetchone()

                if not existing_tax:
                    raise ValueError("Tax not found")
                
                # Store complete old data before update
                old_data = dict(existing_tax)

                # Build update query dynamically
                update_fields = []
                params = []

                if data.name is not None:
                    update_fields.append("name = %s")
                    params.append(data.name)
                if data.rate is not None:
                    update_fields.append("rate = %s")
                    params.append(data.rate)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)
                if data.is_inclusive is not None:
                    update_fields.append("is_inclusive = %s")
                    params.append(data.is_inclusive)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([tax_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_TAXES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_tax = cursor.fetchone()

                if not updated_tax:
                    raise ValueError("Failed to update tax")

                # Get tax with user fullnames
                cursor.execute(
                    f"""SELECT t.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAXES_TABLE} t
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON t.created_by = creator.id AND t.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON t.updated_by = updater.id AND t.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON t.deleted_by = deleter.id AND t.tenant_id = deleter.tenant_id
                    WHERE t.id = %s AND t.tenant_id = %s""",
                    (tax_id, tenant_id),
                )
                tax_with_users = cursor.fetchone()

                if tax_with_users:
                    tax_dict = dict(tax_with_users)
                    tax_dict['created_by'] = tax_dict.get('created_by') or None
                    tax_dict['updated_by'] = tax_dict.get('updated_by') or None
                    tax_dict['deleted_by'] = tax_dict.get('deleted_by') or None
                else:
                    tax_dict = dict(updated_tax)
                    tax_dict['created_by'] = None
                    tax_dict['updated_by'] = None
                    tax_dict['deleted_by'] = None

                tax_read = UpdateTaxServiceReadDto(**tax_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_TAXES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (tax_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")
                    
                    complete_new_data = dict(complete_new_data_record)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-taxes",
                        resource_id=tax_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Tax {tax_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Tax updated successfully: {tax_id}")

                return Respons(
                    success=True,
                    detail="Tax updated successfully",
                    data=[tax_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating tax: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating tax: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update tax: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_tax(
        tax_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetTaxServiceReadDto]:
        """Get a single tax by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT t.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAXES_TABLE} t
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON t.created_by = creator.id AND t.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON t.updated_by = updater.id AND t.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON t.deleted_by = deleter.id AND t.tenant_id = deleter.tenant_id
                    WHERE t.id = %s AND t.tenant_id = %s AND t.org_id = %s 
                    AND t.bus_id = %s""",
                    (tax_id, tenant_id, org_id, bus_id),
                )
                tax = cursor.fetchone()

                if not tax:
                    return Respons(
                        success=False,
                        detail="Tax not found",
                        error="NOT_FOUND",
                    )

                tax_dict = dict(tax)
                tax_dict['created_by'] = tax_dict.get('created_by') or None
                tax_dict['updated_by'] = tax_dict.get('updated_by') or None
                tax_dict['deleted_by'] = tax_dict.get('deleted_by') or None
                tax_read = GetTaxServiceReadDto(**tax_dict)

                return Respons(
                    success=True,
                    detail="Tax retrieved successfully",
                    data=[tax_read],
                )

        except Exception as e:
            logger.error(f"Error getting tax: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get tax: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_taxes(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        page: int = 1,
        size: int = 10,
        is_active: bool = None,
    ) -> Respons[list[GetTaxesServiceReadDto]]:
        """Get list of taxes with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "t.tenant_id = %s",
                    "t.org_id = %s",
                    "t.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if is_active is not None:
                    where_conditions.append("t.is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_TAXES_TABLE} t WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get taxes with user fullnames
                cursor.execute(
                    f"""SELECT t.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAXES_TABLE} t
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON t.created_by = creator.id AND t.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON t.updated_by = updater.id AND t.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON t.deleted_by = deleter.id AND t.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY t.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                taxes = cursor.fetchall()

                tax_list = []
                for t in taxes:
                    t_dict = dict(t)
                    t_dict['created_by'] = t_dict.get('created_by') or None
                    t_dict['updated_by'] = t_dict.get('updated_by') or None
                    t_dict['deleted_by'] = t_dict.get('deleted_by') or None
                    tax_list.append(GetTaxesServiceReadDto(**t_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Taxes retrieved successfully",
                    data=tax_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting taxes: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get taxes: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_tax(
        data: DeleteTaxServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteTaxServiceReadDto]:
        """Delete tax (hard delete - no soft delete)"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get tax before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_TAXES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.tax_id, tenant_id, org_id, bus_id),
                )
                tax = cursor.fetchone()

                if not tax:
                    return Respons(
                        success=False,
                        detail="Tax not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(tax)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-taxes",
                        resource_id=data.tax_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Tax {data.tax_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Hard delete from database
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_TAXES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.tax_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Tax deleted successfully",
                    data=[DeleteTaxServiceReadDto(
                        tax_id=data.tax_id,
                        message="Tax deleted successfully",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting tax: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete tax: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_taxes_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetTaxStatisticsServiceReadDto]:
        """Get comprehensive statistics for taxes"""
        try:
            with DatabaseManager.transaction() as cursor:
                params = (tenant_id, org_id, bus_id)
                
                # Get key statistics using a single query with conditional aggregation
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_taxes,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as total_active,
                        COUNT(CASE WHEN is_active = FALSE THEN 1 END) as total_inactive,
                        AVG(rate) as average_rate,
                        MAX(rate) as highest_rate,
                        MIN(rate) as lowest_rate,
                        COUNT(CASE WHEN is_inclusive = TRUE THEN 1 END) as total_inclusive,
                        COUNT(CASE WHEN is_inclusive = FALSE THEN 1 END) as total_exclusive
                    FROM {db_settings.MSG_TAXES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    params,
                )
                result = cursor.fetchone()

                if not result:
                    # If no results, return zeros
                    statistics = GetTaxStatisticsServiceReadDto(
                        total_taxes=0,
                        total_active=0,
                        total_inactive=0,
                        average_rate=None,
                        highest_rate=None,
                        lowest_rate=None,
                        total_inclusive=0,
                        total_exclusive=0,
                    )
                else:
                    avg_rate = result.get('average_rate')
                    if avg_rate is not None:
                        avg_rate = Decimal(str(avg_rate)).quantize(Decimal('0.01'))
                    
                    highest_rate = result.get('highest_rate')
                    if highest_rate is not None:
                        highest_rate = Decimal(str(highest_rate)).quantize(Decimal('0.01'))
                    
                    lowest_rate = result.get('lowest_rate')
                    if lowest_rate is not None:
                        lowest_rate = Decimal(str(lowest_rate)).quantize(Decimal('0.01'))
                    
                    statistics = GetTaxStatisticsServiceReadDto(
                        total_taxes=result.get('total_taxes', 0) or 0,
                        total_active=result.get('total_active', 0) or 0,
                        total_inactive=result.get('total_inactive', 0) or 0,
                        average_rate=avg_rate,
                        highest_rate=highest_rate,
                        lowest_rate=lowest_rate,
                        total_inclusive=result.get('total_inclusive', 0) or 0,
                        total_exclusive=result.get('total_exclusive', 0) or 0,
                    )

                logger.info(
                    f"Taxes statistics retrieved",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "total_taxes": statistics.total_taxes,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Taxes statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting taxes statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get taxes statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

