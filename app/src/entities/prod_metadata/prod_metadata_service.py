from typing import Optional
from src.entities.prod_metadata.prod_metadata_read_dto import (
    CreateProductMetadataServiceReadDto,
    UpdateProductMetadataServiceReadDto,
    GetProductMetadataServiceReadDto,
    GetProductMetadataListServiceReadDto,
    DeleteProductMetadataServiceReadDto,
    GetProductMetadataStatisticsServiceReadDto,
)
from src.entities.prod_metadata.prod_metadata_write_dto import (
    CreateProductMetadataServiceWriteDto,
    UpdateProductMetadataServiceWriteDto,
    DeleteProductMetadataServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("prod_metadata_service")


class ProductMetadataService:
    """Service class for product metadata operations"""

    @staticmethod
    def create_product_metadata(
        data: CreateProductMetadataServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateProductMetadataServiceReadDto]:
        """Create a new product metadata entry"""
        logger.info(
            f"Processing product metadata creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "name": data.name,
                    "of_type": data.of_type,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if metadata with same name and type already exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND name = %s AND of_type = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.name, data.of_type),
                )
                existing = cursor.fetchone()

                if existing:
                    return Respons(
                        success=False,
                        detail=f"Product metadata with name '{data.name}' and type '{data.of_type}' already exists",
                        error="DUPLICATE_ENTRY",
                    )

                # Generate metadata ID
                metadata_id = Helper.generate_unique_identifier(prefix="pmd")

                # Insert into msg_product_metadata table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRODUCT_METADATA_TABLE}
                    (id, tenant_id, org_id, bus_id, name, of_type, description,
                     delete_status, is_active, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        metadata_id, tenant_id, org_id, bus_id,
                        data.name, data.of_type, data.description,
                        'NOT_DELETED', True,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                metadata_result = cursor.fetchone()

                if not metadata_result:
                    raise ValueError("Failed to create product metadata")

                # Get metadata with user fullnames
                cursor.execute(
                    f"""SELECT m.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON m.updated_by = updater.id AND m.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON m.deleted_by = deleter.id AND m.tenant_id = deleter.tenant_id
                    WHERE m.id = %s AND m.tenant_id = %s AND m.org_id = %s AND m.bus_id = %s""",
                    (metadata_id, tenant_id, org_id, bus_id),
                )
                metadata_with_users = cursor.fetchone()

                if metadata_with_users:
                    if isinstance(metadata_with_users, dict):
                        metadata_dict = metadata_with_users.copy()
                    else:
                        metadata_dict = dict(metadata_with_users)
                    # Replace user IDs with fullnames (or None if not found)
                    metadata_dict['created_by'] = metadata_dict.get('created_by') or None
                    metadata_dict['updated_by'] = metadata_dict.get('updated_by') or None
                    metadata_dict['deleted_by'] = metadata_dict.get('deleted_by') or None
                else:
                    if isinstance(metadata_result, dict):
                        metadata_dict = metadata_result.copy()
                    else:
                        metadata_dict = dict(metadata_result)
                    metadata_dict['created_by'] = None
                    metadata_dict['updated_by'] = None
                    metadata_dict['deleted_by'] = None

                metadata_read = CreateProductMetadataServiceReadDto(**metadata_dict)

                # Log activity - get ALL data from table after insert
                try:
                    # Get complete record with ALL columns from database (raw data with user IDs)
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (metadata_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")
                    
                    # Use raw database data (with user IDs, not fullnames)
                    complete_new_data = dict(complete_new_data_record)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-metadata",
                        resource_id=metadata_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,  # All data from table after insert
                        description=f"Product metadata {metadata_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",  # Product metadata doesn't have loc_id
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Product metadata created successfully: {metadata_id}",
                    extra={
                        "extra_fields": {
                            "metadata_id": metadata_id,
                            "name": data.name,
                            "of_type": data.of_type,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Product metadata created successfully",
                    data=[metadata_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating product metadata: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating product metadata: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create product metadata: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_product_metadata(
        data: UpdateProductMetadataServiceWriteDto,
        metadata_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateProductMetadataServiceReadDto]:
        """Update product metadata"""
        logger.info(
            f"Processing product metadata update: {metadata_id}",
            extra={
                "extra_fields": {
                    "metadata_id": metadata_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data (for audit/activity log)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (metadata_id, tenant_id, org_id, bus_id),
                )
                existing_metadata = cursor.fetchone()

                if not existing_metadata:
                    raise ValueError("Product metadata not found")
                
                # Store complete old data before update
                old_data = dict(existing_metadata)

                # Check for duplicate name if name is being updated
                if data.name is not None and data.name != old_data.get('name'):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND name = %s AND of_type = %s AND id != %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.name, old_data.get('of_type'), metadata_id),
                    )
                    duplicate = cursor.fetchone()
                    if duplicate:
                        return Respons(
                            success=False,
                            detail=f"Product metadata with name '{data.name}' and type '{old_data.get('of_type')}' already exists",
                            error="DUPLICATE_ENTRY",
                        )

                # Build update query dynamically
                update_fields = []
                params = []

                if data.name is not None:
                    update_fields.append("name = %s")
                    params.append(data.name)
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
                params.extend([metadata_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PRODUCT_METADATA_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_metadata = cursor.fetchone()

                if not updated_metadata:
                    raise ValueError("Failed to update product metadata")

                # Get metadata with user fullnames
                cursor.execute(
                    f"""SELECT m.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON m.updated_by = updater.id AND m.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON m.deleted_by = deleter.id AND m.tenant_id = deleter.tenant_id
                    WHERE m.id = %s AND m.tenant_id = %s""",
                    (metadata_id, tenant_id),
                )
                metadata_with_users = cursor.fetchone()

                if metadata_with_users:
                    metadata_dict = dict(metadata_with_users)
                    metadata_dict['created_by'] = metadata_dict.get('created_by') or None
                    metadata_dict['updated_by'] = metadata_dict.get('updated_by') or None
                    metadata_dict['deleted_by'] = metadata_dict.get('deleted_by') or None
                else:
                    metadata_dict = dict(updated_metadata)
                    metadata_dict['created_by'] = None
                    metadata_dict['updated_by'] = None
                    metadata_dict['deleted_by'] = None

                metadata_read = UpdateProductMetadataServiceReadDto(**metadata_dict)

                # Log activity - get ALL data from table after update
                try:
                    # Get complete record with ALL columns from database after update (raw data with user IDs)
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (metadata_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")
                    
                    # Use raw database data (with user IDs, not fullnames)
                    complete_new_data = dict(complete_new_data_record)
                    
                    # old_data was captured before update (line 223) - contains ALL columns
                    # new_data captured after update - contains ALL columns
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-metadata",
                        resource_id=metadata_id,
                        action="update",
                        old_data=old_data,  # All data before update
                        new_data=complete_new_data,  # All data after update
                        description=f"Product metadata {metadata_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Product metadata updated successfully: {metadata_id}")

                return Respons(
                    success=True,
                    detail="Product metadata updated successfully",
                    data=[metadata_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating product metadata: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating product metadata: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update product metadata: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_metadata(
        metadata_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetProductMetadataServiceReadDto]:
        """Get a single product metadata by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT m.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON m.updated_by = updater.id AND m.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON m.deleted_by = deleter.id AND m.tenant_id = deleter.tenant_id
                    WHERE m.id = %s AND m.tenant_id = %s AND m.org_id = %s 
                    AND m.bus_id = %s AND m.delete_status = 'NOT_DELETED'""",
                    (metadata_id, tenant_id, org_id, bus_id),
                )
                metadata = cursor.fetchone()

                if not metadata:
                    return Respons(
                        success=False,
                        detail="Product metadata not found",
                        error="NOT_FOUND",
                    )

                metadata_dict = dict(metadata)
                metadata_dict['created_by'] = metadata_dict.get('created_by') or None
                metadata_dict['updated_by'] = metadata_dict.get('updated_by') or None
                metadata_dict['deleted_by'] = metadata_dict.get('deleted_by') or None
                metadata_read = GetProductMetadataServiceReadDto(**metadata_dict)

                return Respons(
                    success=True,
                    detail="Product metadata retrieved successfully",
                    data=[metadata_read],
                )

        except Exception as e:
            logger.error(f"Error getting product metadata: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product metadata: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_metadata_list(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        of_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetProductMetadataListServiceReadDto]]:
        """Get list of product metadata with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "m.tenant_id = %s",
                    "m.org_id = %s",
                    "m.bus_id = %s",
                    "m.delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id, org_id, bus_id]

                if of_type:
                    where_conditions.append("m.of_type = %s")
                    params.append(of_type)
                if is_active is not None:
                    where_conditions.append("m.is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get metadata with user fullnames
                cursor.execute(
                    f"""SELECT m.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON m.created_by = creator.id AND m.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON m.updated_by = updater.id AND m.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON m.deleted_by = deleter.id AND m.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY m.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                metadata_list = cursor.fetchall()

                metadata_result_list = []
                for meta in metadata_list:
                    meta_dict = dict(meta)
                    meta_dict['created_by'] = meta_dict.get('created_by') or None
                    meta_dict['updated_by'] = meta_dict.get('updated_by') or None
                    meta_dict['deleted_by'] = meta_dict.get('deleted_by') or None
                    metadata_result_list.append(GetProductMetadataListServiceReadDto(**meta_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Product metadata list retrieved successfully",
                    data=metadata_result_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting product metadata list: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product metadata list: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_product_metadata(
        data: DeleteProductMetadataServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteProductMetadataServiceReadDto]:
        """Delete product metadata"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get metadata before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.metadata_id, tenant_id, org_id, bus_id),
                )
                metadata = cursor.fetchone()

                if not metadata:
                    return Respons(
                        success=False,
                        detail="Product metadata not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion - get ALL columns from database
                # This SELECT * gets all data including all columns
                complete_old_data = dict(metadata)

                # Log activity before deletion - old_data contains ALL columns from table
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-metadata",
                        resource_id=data.metadata_id,
                        action="delete",
                        old_data=complete_old_data,  # All data from table before deletion
                        new_data=None,
                        description=f"Product metadata {data.metadata_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Delete from database
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.metadata_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Product metadata deleted successfully",
                    data=[DeleteProductMetadataServiceReadDto(
                        metadata_id=data.metadata_id,
                        message="Product metadata deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting product metadata: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete product metadata: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_metadata_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetProductMetadataStatisticsServiceReadDto]:
        """Get statistics for product metadata (total counts of tags, categories, labels, and brands)"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get counts for each type using a single query with conditional aggregation
                cursor.execute(
                    f"""SELECT 
                        COUNT(CASE WHEN of_type = 'TAG' THEN 1 END) as total_tags,
                        COUNT(CASE WHEN of_type = 'CATEGORY' THEN 1 END) as total_categories,
                        COUNT(CASE WHEN of_type = 'LABEL' THEN 1 END) as total_labels,
                        COUNT(CASE WHEN of_type = 'BRAND' THEN 1 END) as total_brands
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id),
                )
                result = cursor.fetchone()

                total_tags = result.get('total_tags', 0) if result else 0
                total_categories = result.get('total_categories', 0) if result else 0
                total_labels = result.get('total_labels', 0) if result else 0
                total_brands = result.get('total_brands', 0) if result else 0

                logger.info(
                    f"Product metadata statistics retrieved",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "total_tags": total_tags,
                            "total_categories": total_categories,
                            "total_labels": total_labels,
                            "total_brands": total_brands,
                        }
                    },
                )

                statistics = GetProductMetadataStatisticsServiceReadDto(
                    total_tags=total_tags,
                    total_categories=total_categories,
                    total_labels=total_labels,
                    total_brands=total_brands,
                )

                return Respons(
                    success=True,
                    detail="Product metadata statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting product metadata statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product metadata statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

