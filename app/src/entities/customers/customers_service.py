from typing import Optional
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from src.entities.customers.customers_read_dto import (
    CreateCustomerServiceReadDto,
    UpdateCustomerServiceReadDto,
    DeleteCustomerServiceReadDto,
    GetCustomerServiceReadDto,
    GetCustomersServiceReadDto,
    CustomerStatsOverviewReadDto,
)
from src.entities.customers.customers_write_dto import (
    CreateCustomerServiceWriteDto,
    UpdateCustomerServiceWriteDto,
    DeleteCustomerServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("customers_service")


class CustomersService:
    """Service class for customers operations"""

    @staticmethod
    def create_customer(
        data: CreateCustomerServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateCustomerServiceReadDto]:
        """Create a new customer"""
        logger.info(
            f"Processing customer creation",
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
                # Check if customer with same email already exists (if email provided)
                # Email is unique per tenant/org/bus
                if data.email:
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND email = %s""",
                        (tenant_id, org_id, bus_id, data.email),
                    )
                    existing_email = cursor.fetchone()

                    if existing_email:
                        return Respons(
                            success=False,
                            detail=f"Customer with email '{data.email}' already exists",
                            error="DUPLICATE_EMAIL",
                        )

                # Check if customer with same contact already exists (if contact provided)
                # Contact is unique per tenant/org/bus
                if data.contact:
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND contact = %s""",
                        (tenant_id, org_id, bus_id, data.contact),
                    )
                    existing_contact = cursor.fetchone()

                    if existing_contact:
                        return Respons(
                            success=False,
                            detail=f"Customer with contact '{data.contact}' already exists",
                            error="DUPLICATE_CONTACT",
                        )

                # Generate customer ID
                customer_id = Helper.generate_unique_identifier(prefix="cus")

                # Insert into msg_customers table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_CUSTOMERS_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, fullname, email, 
                     contact, address, description, is_active, delete_status, 
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        customer_id, tenant_id, org_id, bus_id, loc_id,
                        data.fullname, data.email,
                        data.contact, data.address, data.description,
                        data.is_active if data.is_active is not None else True, 'NOT_DELETED',
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                customer_result = cursor.fetchone()

                if not customer_result:
                    raise ValueError("Failed to create customer")

                # Get customer with user fullnames
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE c.id = %s AND c.tenant_id = %s""",
                    (customer_id, tenant_id),
                )
                customer_with_users = cursor.fetchone()

                if customer_with_users:
                    customer_dict = dict(customer_with_users)
                    # Replace user IDs with fullnames (or None if not found)
                    customer_dict['created_by'] = customer_dict.get('created_by') or None
                    customer_dict['updated_by'] = customer_dict.get('updated_by') or None
                    customer_dict['deleted_by'] = customer_dict.get('deleted_by') or None
                else:
                    customer_dict = dict(customer_result)
                    customer_dict['created_by'] = None
                    customer_dict['updated_by'] = None
                    customer_dict['deleted_by'] = None

                customer_read = CreateCustomerServiceReadDto(**customer_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (customer_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(customer_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-customers",
                        resource_id=customer_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Customer {customer_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Customer created successfully: {customer_id}",
                    extra={
                        "extra_fields": {
                            "customer_id": customer_id,
                            "fullname": data.fullname,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Customer created successfully",
                    data=[customer_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating customer: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create customer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_customer(
        data: UpdateCustomerServiceWriteDto,
        customer_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateCustomerServiceReadDto]:
        """Update a customer"""
        logger.info(
            f"Processing customer update: {customer_id}",
            extra={
                "extra_fields": {
                    "customer_id": customer_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data (for audit/activity log)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_CUSTOMERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (customer_id, tenant_id, org_id, bus_id),
                )
                existing_customer = cursor.fetchone()

                if not existing_customer:
                    raise ValueError("Customer not found")
                
                # Store complete old data before update
                old_data = dict(existing_customer)

                # If email is being updated, check for duplicates (if email provided)
                # Email is unique per tenant/org/bus
                if data.email is not None and data.email != old_data.get('email'):
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND email = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.email, customer_id),
                    )
                    duplicate_email = cursor.fetchone()
                    if duplicate_email:
                        raise ValueError(f"Customer with email '{data.email}' already exists")

                # If contact is being updated, check for duplicates (if contact provided)
                # Contact is unique per tenant/org/bus
                if data.contact is not None and data.contact != old_data.get('contact'):
                    cursor.execute(
                        f"""SELECT id, fullname FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND contact = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.contact, customer_id),
                    )
                    duplicate_contact = cursor.fetchone()
                    if duplicate_contact:
                        raise ValueError(f"Customer with contact '{data.contact}' already exists")

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
                params.extend([customer_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_CUSTOMERS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_customer = cursor.fetchone()

                if not updated_customer:
                    raise ValueError("Failed to update customer")

                # Get customer with user fullnames
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE c.id = %s AND c.tenant_id = %s""",
                    (customer_id, tenant_id),
                )
                customer_with_users = cursor.fetchone()

                if customer_with_users:
                    customer_dict = dict(customer_with_users)
                    customer_dict['created_by'] = customer_dict.get('created_by') or None
                    customer_dict['updated_by'] = customer_dict.get('updated_by') or None
                    customer_dict['deleted_by'] = customer_dict.get('deleted_by') or None
                else:
                    customer_dict = dict(updated_customer)
                    customer_dict['created_by'] = None
                    customer_dict['updated_by'] = None
                    customer_dict['deleted_by'] = None

                customer_read = UpdateCustomerServiceReadDto(**customer_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (customer_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(customer_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-customers",
                        resource_id=customer_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Customer {customer_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Customer updated successfully: {customer_id}")

                return Respons(
                    success=True,
                    detail="Customer updated successfully",
                    data=[customer_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating customer: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating customer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update customer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_customer(
        customer_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetCustomerServiceReadDto]:
        """Get a single customer by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE c.id = %s AND c.tenant_id = %s AND c.org_id = %s 
                    AND c.bus_id = %s""",
                    (customer_id, tenant_id, org_id, bus_id),
                )
                customer = cursor.fetchone()

                if not customer:
                    return Respons(
                        success=False,
                        detail="Customer not found",
                        error="NOT_FOUND",
                    )

                customer_dict = dict(customer)
                customer_dict['created_by'] = customer_dict.get('created_by') or None
                customer_dict['updated_by'] = customer_dict.get('updated_by') or None
                customer_dict['deleted_by'] = customer_dict.get('deleted_by') or None
                customer_read = GetCustomerServiceReadDto(**customer_dict)

                return Respons(
                    success=True,
                    detail="Customer retrieved successfully",
                    data=[customer_read],
                )

        except Exception as e:
            logger.error(f"Error getting customer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get customer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_customers(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetCustomersServiceReadDto]]:
        """Get list of customers with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "c.tenant_id = %s",
                    "c.org_id = %s",
                    "c.bus_id = %s",
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
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_CUSTOMERS_TABLE} c WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get customers with user fullnames
                cursor.execute(
                    f"""SELECT c.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON c.created_by = creator.id AND c.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON c.updated_by = updater.id AND c.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON c.deleted_by = deleter.id AND c.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY c.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                customers = cursor.fetchall()

                customer_list = []
                for cus in customers:
                    cus_dict = dict(cus)
                    cus_dict['created_by'] = cus_dict.get('created_by') or None
                    cus_dict['updated_by'] = cus_dict.get('updated_by') or None
                    cus_dict['deleted_by'] = cus_dict.get('deleted_by') or None
                    customer_list.append(GetCustomersServiceReadDto(**cus_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Customers retrieved successfully",
                    data=customer_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting customers: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get customers: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_customer(
        data: DeleteCustomerServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteCustomerServiceReadDto]:
        """Delete a customer"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get customer details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_CUSTOMERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.customer_id, tenant_id, org_id, bus_id),
                )
                customer = cursor.fetchone()

                if not customer:
                    return Respons(
                        success=False,
                        detail="Customer not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(customer)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-customers",
                        resource_id=data.customer_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Customer {data.customer_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Delete
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_CUSTOMERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.customer_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Customer deleted successfully",
                    data=[DeleteCustomerServiceReadDto(
                        customer_id=data.customer_id,
                        message="Customer deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting customer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete customer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_stats_overview(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[CustomerStatsOverviewReadDto]:
        """Get customer overview statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_customers,
                        COUNT(*) FILTER (WHERE is_active = true) as active_customers,
                        COUNT(*) FILTER (WHERE is_active = false) as inactive_customers,
                        COUNT(*) FILTER (WHERE cdate >= %s) as recently_added
                    FROM {db_settings.MSG_CUSTOMERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (
                        (date.today() - timedelta(days=30)).isoformat(),
                        tenant_id, org_id, bus_id,
                    ),
                )
                row = cursor.fetchone()

                stats = CustomerStatsOverviewReadDto(
                    total_customers=row['total_customers'] if row else 0,
                    active_customers=row['active_customers'] if row else 0,
                    inactive_customers=row['inactive_customers'] if row else 0,
                    recently_added=row['recently_added'] if row else 0,
                )

                return Respons(
                    success=True,
                    detail="Customer statistics retrieved successfully",
                    data=[stats],
                )

        except Exception as e:
            logger.error(f"Error getting customer stats: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get customer stats: {str(e)}",
                error="INTERNAL_ERROR",
            )

