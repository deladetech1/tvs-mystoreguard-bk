from typing import Optional
from src.entities.suppliers.suppliers_read_dto import (
    CreateSupplierServiceReadDto,
    UpdateSupplierServiceReadDto,
    DeleteSupplierServiceReadDto,
    GetSupplierServiceReadDto,
    GetSuppliersServiceReadDto,
)
from src.entities.suppliers.suppliers_write_dto import (
    CreateSupplierServiceWriteDto,
    UpdateSupplierServiceWriteDto,
    DeleteSupplierServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("suppliers_service")


class SuppliersService:
    """Service class for suppliers operations"""

    @staticmethod
    def create_supplier(
        data: CreateSupplierServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateSupplierServiceReadDto]:
        """Create a new supplier"""
        logger.info(
            f"Processing supplier creation",
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
                # Check if supplier with same fullname already exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_SUPPLIERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND fullname = %s""",
                    (tenant_id, org_id, bus_id, data.fullname),
                )
                existing_supplier = cursor.fetchone()

                if existing_supplier:
                    return Respons(
                        success=False,
                        detail=f"Supplier with fullname '{data.fullname}' already exists",
                        error="DUPLICATE_NAME",
                    )

                # Check if supplier with same email already exists (if email provided)
                if data.email:
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND email = %s""",
                        (tenant_id, org_id, bus_id, data.email),
                    )
                    existing_email = cursor.fetchone()

                    if existing_email:
                        return Respons(
                            success=False,
                            detail=f"Supplier with email '{data.email}' already exists",
                            error="DUPLICATE_EMAIL",
                        )

                # Check if supplier with same contact already exists (if contact provided)
                if data.contact:
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND contact = %s""",
                        (tenant_id, org_id, bus_id, data.contact),
                    )
                    existing_contact = cursor.fetchone()

                    if existing_contact:
                        return Respons(
                            success=False,
                            detail=f"Supplier with contact '{data.contact}' already exists",
                            error="DUPLICATE_CONTACT",
                        )

                # Generate supplier ID
                supplier_id = Helper.generate_unique_identifier(prefix="sup")

                # Insert into msg_suppliers table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_SUPPLIERS_TABLE}
                    (id, tenant_id, org_id, bus_id, fullname, email, 
                     contact, address, description, is_active, delete_status, 
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        supplier_id, tenant_id, org_id, bus_id,
                        data.fullname, data.email,
                        data.contact, data.address, data.description,
                        data.is_active if data.is_active is not None else True, 'NOT_DELETED',
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                supplier_result = cursor.fetchone()

                if not supplier_result:
                    raise ValueError("Failed to create supplier")

                # Get supplier with user fullnames
                cursor.execute(
                    f"""SELECT s.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_SUPPLIERS_TABLE} s
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON s.created_by = creator.id AND s.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON s.updated_by = updater.id AND s.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON s.deleted_by = deleter.id AND s.tenant_id = deleter.tenant_id
                    WHERE s.id = %s AND s.tenant_id = %s""",
                    (supplier_id, tenant_id),
                )
                supplier_with_users = cursor.fetchone()

                if supplier_with_users:
                    supplier_dict = dict(supplier_with_users)
                    # Replace user IDs with fullnames (or None if not found)
                    supplier_dict['created_by'] = supplier_dict.get('created_by') or None
                    supplier_dict['updated_by'] = supplier_dict.get('updated_by') or None
                    supplier_dict['deleted_by'] = supplier_dict.get('deleted_by') or None
                else:
                    supplier_dict = dict(supplier_result)
                    supplier_dict['created_by'] = None
                    supplier_dict['updated_by'] = None
                    supplier_dict['deleted_by'] = None

                supplier_read = CreateSupplierServiceReadDto(**supplier_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (supplier_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(supplier_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-suppliers",
                        resource_id=supplier_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Supplier {supplier_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Supplier created successfully: {supplier_id}",
                    extra={
                        "extra_fields": {
                            "supplier_id": supplier_id,
                            "fullname": data.fullname,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Supplier created successfully",
                    data=[supplier_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating supplier: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating supplier: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create supplier: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_supplier(
        data: UpdateSupplierServiceWriteDto,
        supplier_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateSupplierServiceReadDto]:
        """Update a supplier"""
        logger.info(
            f"Processing supplier update: {supplier_id}",
            extra={
                "extra_fields": {
                    "supplier_id": supplier_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data (for audit/activity log)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SUPPLIERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (supplier_id, tenant_id, org_id, bus_id),
                )
                existing_supplier = cursor.fetchone()

                if not existing_supplier:
                    raise ValueError("Supplier not found")
                
                # Store complete old data before update
                old_data = dict(existing_supplier)

                # If fullname is being updated, check for duplicates
                if data.fullname is not None and data.fullname != old_data.get('fullname'):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND fullname = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.fullname, supplier_id),
                    )
                    duplicate = cursor.fetchone()
                    if duplicate:
                        raise ValueError(f"Supplier with fullname '{data.fullname}' already exists")

                # If email is being updated, check for duplicates (if email provided)
                if data.email is not None and data.email != old_data.get('email'):
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND email = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.email, supplier_id),
                    )
                    duplicate_email = cursor.fetchone()
                    if duplicate_email:
                        raise ValueError(f"Supplier with email '{data.email}' already exists")

                # If contact is being updated, check for duplicates (if contact provided)
                if data.contact is not None and data.contact != old_data.get('contact'):
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND contact = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.contact, supplier_id),
                    )
                    duplicate_contact = cursor.fetchone()
                    if duplicate_contact:
                        raise ValueError(f"Supplier with contact '{data.contact}' already exists")

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
                params.extend([supplier_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_SUPPLIERS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_supplier = cursor.fetchone()

                if not updated_supplier:
                    raise ValueError("Failed to update supplier")

                # Get supplier with user fullnames
                cursor.execute(
                    f"""SELECT s.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_SUPPLIERS_TABLE} s
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON s.created_by = creator.id AND s.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON s.updated_by = updater.id AND s.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON s.deleted_by = deleter.id AND s.tenant_id = deleter.tenant_id
                    WHERE s.id = %s AND s.tenant_id = %s""",
                    (supplier_id, tenant_id),
                )
                supplier_with_users = cursor.fetchone()

                if supplier_with_users:
                    supplier_dict = dict(supplier_with_users)
                    supplier_dict['created_by'] = supplier_dict.get('created_by') or None
                    supplier_dict['updated_by'] = supplier_dict.get('updated_by') or None
                    supplier_dict['deleted_by'] = supplier_dict.get('deleted_by') or None
                else:
                    supplier_dict = dict(updated_supplier)
                    supplier_dict['created_by'] = None
                    supplier_dict['updated_by'] = None
                    supplier_dict['deleted_by'] = None

                supplier_read = UpdateSupplierServiceReadDto(**supplier_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (supplier_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(supplier_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-suppliers",
                        resource_id=supplier_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Supplier {supplier_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Supplier updated successfully: {supplier_id}")

                return Respons(
                    success=True,
                    detail="Supplier updated successfully",
                    data=[supplier_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating supplier: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating supplier: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update supplier: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_supplier(
        supplier_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetSupplierServiceReadDto]:
        """Get a single supplier by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT s.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_SUPPLIERS_TABLE} s
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON s.created_by = creator.id AND s.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON s.updated_by = updater.id AND s.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON s.deleted_by = deleter.id AND s.tenant_id = deleter.tenant_id
                    WHERE s.id = %s AND s.tenant_id = %s AND s.org_id = %s 
                    AND s.bus_id = %s""",
                    (supplier_id, tenant_id, org_id, bus_id),
                )
                supplier = cursor.fetchone()

                if not supplier:
                    return Respons(
                        success=False,
                        detail="Supplier not found",
                        error="NOT_FOUND",
                    )

                supplier_dict = dict(supplier)
                supplier_dict['created_by'] = supplier_dict.get('created_by') or None
                supplier_dict['updated_by'] = supplier_dict.get('updated_by') or None
                supplier_dict['deleted_by'] = supplier_dict.get('deleted_by') or None
                supplier_read = GetSupplierServiceReadDto(**supplier_dict)

                return Respons(
                    success=True,
                    detail="Supplier retrieved successfully",
                    data=[supplier_read],
                )

        except Exception as e:
            logger.error(f"Error getting supplier: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get supplier: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_suppliers(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetSuppliersServiceReadDto]]:
        """Get list of suppliers with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "s.tenant_id = %s",
                    "s.org_id = %s",
                    "s.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if is_active is not None:
                    where_conditions.append("s.is_active = %s")
                    params.append(is_active)
                if search:
                    where_conditions.append(
                        "(s.fullname ILIKE %s OR s.email ILIKE %s OR s.contact ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_SUPPLIERS_TABLE} s WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get suppliers with user fullnames
                cursor.execute(
                    f"""SELECT s.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_SUPPLIERS_TABLE} s
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON s.created_by = creator.id AND s.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON s.updated_by = updater.id AND s.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON s.deleted_by = deleter.id AND s.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY s.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                suppliers = cursor.fetchall()

                supplier_list = []
                for sup in suppliers:
                    sup_dict = dict(sup)
                    sup_dict['created_by'] = sup_dict.get('created_by') or None
                    sup_dict['updated_by'] = sup_dict.get('updated_by') or None
                    sup_dict['deleted_by'] = sup_dict.get('deleted_by') or None
                    supplier_list.append(GetSuppliersServiceReadDto(**sup_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Suppliers retrieved successfully",
                    data=supplier_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting suppliers: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get suppliers: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_supplier(
        data: DeleteSupplierServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteSupplierServiceReadDto]:
        """Delete a supplier"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get supplier details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SUPPLIERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.supplier_id, tenant_id, org_id, bus_id),
                )
                supplier = cursor.fetchone()

                if not supplier:
                    return Respons(
                        success=False,
                        detail="Supplier not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(supplier)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-suppliers",
                        resource_id=data.supplier_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Supplier {data.supplier_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Delete
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_SUPPLIERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.supplier_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Supplier deleted successfully",
                    data=[DeleteSupplierServiceReadDto(
                        supplier_id=data.supplier_id,
                        message="Supplier deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting supplier: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete supplier: {str(e)}",
                error="INTERNAL_ERROR",
            )

