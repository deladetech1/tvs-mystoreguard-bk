from decimal import Decimal
from src.entities.product_prices.product_prices_read_dto import (
    CreateProductPriceServiceReadDto,
    UpdateProductPriceServiceReadDto,
    GetProductPriceServiceReadDto,
    GetProductPricesServiceReadDto,
    DeleteProductPriceServiceReadDto,
    GetProductPriceStatisticsServiceReadDto,
)
from src.entities.product_prices.product_prices_write_dto import (
    CreateProductPriceServiceWriteDto,
    UpdateProductPriceServiceWriteDto,
    DeleteProductPriceServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("product_prices_service")


class ProductPricesService:
    """Service class for product prices operations"""

    @staticmethod
    def _get_target_name_subquery() -> str:
        """Get SQL subquery to fetch target_name based on of_type"""
        return f"""
            CASE 
                WHEN p.of_type = 'GLOBAL' THEN NULL
                WHEN p.of_type = 'SKU' THEN (
                    SELECT p2.name 
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p2 
                    WHERE p2.sku = p.target_id 
                    AND p2.tenant_id = p.tenant_id 
                    AND p2.org_id = p.org_id 
                    AND p2.bus_id = p.bus_id
                    LIMIT 1
                )
                WHEN p.of_type = 'LOCATION' THEN (
                    SELECT l.loc_name 
                    FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l 
                    WHERE l.id = p.target_id 
                    AND l.tenant_id = p.tenant_id
                    LIMIT 1
                )
                WHEN p.of_type IN ('TAG', 'CATEGORY', 'BRAND', 'LABEL') THEN (
                    SELECT m.name 
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m 
                    WHERE m.id = p.target_id 
                    AND m.tenant_id = p.tenant_id 
                    AND m.org_id = p.org_id 
                    AND m.bus_id = p.bus_id
                    LIMIT 1
                )
                ELSE NULL
            END as target_name
        """

    @staticmethod
    def create_price(
        data: CreateProductPriceServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateProductPriceServiceReadDto]:
        """Create a new product price"""
        logger.info(
            f"Processing product price creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "product_id": data.product_id,
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
                # Validate product exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s""",
                    (tenant_id, org_id, bus_id, data.product_id),
                )
                product = cursor.fetchone()

                if not product:
                    return Respons(
                        success=False,
                        detail=f"Product with ID '{data.product_id}' not found",
                        error="NOT_FOUND",
                    )

                # Validate currency exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                    WHERE tenant_id = %s AND id = %s""",
                    (tenant_id, data.currency),
                )
                currency = cursor.fetchone()

                if not currency:
                    return Respons(
                        success=False,
                        detail=f"Currency with ID '{data.currency}' not found",
                        error="NOT_FOUND",
                    )

                # Validate target_id based on of_type
                if data.of_type == 'SKU':
                    # For SKU, target_id should contain the SKU value
                    if not data.target_id:
                        return Respons(
                            success=False,
                            detail=f"target_id is required for of_type 'SKU' (should contain the SKU value)",
                            error="VALIDATION_ERROR",
                        )
                    # Validate product with SKU exists
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND sku = %s""",
                        (tenant_id, org_id, bus_id, data.target_id),
                    )
                    target = cursor.fetchone()
                    if not target:
                        return Respons(
                            success=False,
                            detail=f"Product with SKU '{data.target_id}' not found",
                            error="NOT_FOUND",
                        )
                elif data.of_type in ['LOCATION', 'TAG', 'CATEGORY', 'BRAND', 'LABEL']:
                    if not data.target_id:
                        return Respons(
                            success=False,
                            detail=f"target_id is required for of_type '{data.of_type}'",
                            error="VALIDATION_ERROR",
                        )

                    if data.of_type == 'LOCATION':
                        # Validate location exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                            WHERE tenant_id = %s AND id = %s""",
                            (tenant_id, data.target_id),
                        )
                        target = cursor.fetchone()
                        if not target:
                            return Respons(
                                success=False,
                                detail=f"Location with ID '{data.target_id}' not found",
                                error="NOT_FOUND",
                            )
                    else:
                        # Validate product metadata exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s""",
                            (tenant_id, org_id, bus_id, data.target_id),
                        )
                        target = cursor.fetchone()
                        if not target:
                            return Respons(
                                success=False,
                                detail=f"Product metadata with ID '{data.target_id}' not found",
                                error="NOT_FOUND",
                            )
                elif data.of_type == 'GLOBAL':
                    # target_id should be None for GLOBAL
                    if data.target_id:
                        return Respons(
                            success=False,
                            detail=f"target_id should be null for of_type 'GLOBAL'",
                            error="VALIDATION_ERROR",
                        )

                # Generate price ID
                price_id = Helper.generate_unique_identifier(prefix="prc")

                # Insert into msg_product_prices table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRODUCT_PRICES_TABLE}
                    (id, tenant_id, org_id, bus_id, product_id, of_type, target_id,
                     price, currency, priority, stops_other_prices, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        price_id, tenant_id, org_id, bus_id,
                        data.product_id, data.of_type, data.target_id,
                        data.price, data.currency, data.priority, data.stops_other_prices,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                price_result = cursor.fetchone()

                if not price_result:
                    raise ValueError("Failed to create product price")
                
                logger.info(f"Product price {price_id} inserted successfully, rowcount: {cursor.rowcount}")

                # Convert price_result to dict
                if isinstance(price_result, dict):
                    price_dict = price_result.copy()
                else:
                    price_dict = dict(price_result)

                # Try to get price with user fullnames, target_name, currency_name and currency validation
                # If currency doesn't meet conditions, we'll use the INSERT result
                try:
                    cursor.execute(
                        f"""SELECT p.*,
                               creator.fullname as created_by,
                               updater.fullname as updated_by,
                               deleter.fullname as deleted_by,
                               c.symbol as currency_name,
                               {ProductPricesService._get_target_name_subquery()}
                        FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} p
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                        LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                        INNER JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency = c.id AND p.tenant_id = c.tenant_id
                        WHERE p.id = %s AND p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s
                        AND c.delete_status = 'NOT_DELETED' AND c.is_active = true""",
                        (price_id, tenant_id, org_id, bus_id),
                    )
                    price_with_users = cursor.fetchone()

                    if price_with_users:
                        if isinstance(price_with_users, dict):
                            price_dict = price_with_users.copy()
                        else:
                            price_dict = dict(price_with_users)
                        # Replace user IDs with fullnames (or None if not found)
                        price_dict['created_by'] = price_dict.get('created_by') or None
                        price_dict['updated_by'] = price_dict.get('updated_by') or None
                        price_dict['deleted_by'] = price_dict.get('deleted_by') or None
                        # Replace currency ID with currency name if available
                        if 'currency_name' in price_dict and price_dict.get('currency_name'):
                            price_dict['currency'] = price_dict['currency_name']
                            # Remove currency_name since we only expose currency
                            del price_dict['currency_name']
                    else:
                        # Currency doesn't meet conditions, try to get target_name and currency_name separately
                        price_dict['created_by'] = None
                        price_dict['updated_by'] = None
                        price_dict['deleted_by'] = None
                        
                        # Try to get currency name even if it doesn't meet active/delete_status conditions
                        try:
                            cursor.execute(
                                f"""SELECT symbol as currency_name
                                FROM {db_settings.CORE_PLATFORM_CURRENCY}
                                WHERE id = %s AND tenant_id = %s""",
                                (data.currency, tenant_id),
                            )
                            currency_result = cursor.fetchone()
                            price_dict['currency_name'] = currency_result.get('currency_name') if currency_result else None
                        except Exception:
                            price_dict['currency_name'] = None
                        
                        # Replace currency ID with currency name if available
                        if price_dict.get('currency_name'):
                            price_dict['currency'] = price_dict['currency_name']
                            # Remove currency_name since we only expose currency
                            del price_dict['currency_name']
                        
                        # Try to get target_name based on of_type
                        try:
                            if data.of_type == 'SKU' and data.target_id:
                                cursor.execute(
                                    f"""SELECT name as target_name
                                    FROM {db_settings.MSG_PRODUCTS_TABLE}
                                    WHERE sku = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                    (data.target_id, tenant_id, org_id, bus_id),
                                )
                                target_result = cursor.fetchone()
                                price_dict['target_name'] = target_result.get('target_name') if target_result else None
                            elif data.of_type == 'LOCATION' and data.target_id:
                                cursor.execute(
                                    f"""SELECT loc_name as target_name
                                    FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                                    WHERE id = %s AND tenant_id = %s""",
                                    (data.target_id, tenant_id),
                                )
                                target_result = cursor.fetchone()
                                price_dict['target_name'] = target_result.get('target_name') if target_result else None
                            elif data.of_type in ['TAG', 'CATEGORY', 'BRAND', 'LABEL'] and data.target_id:
                                cursor.execute(
                                    f"""SELECT name as target_name
                                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                    (data.target_id, tenant_id, org_id, bus_id),
                                )
                                target_result = cursor.fetchone()
                                price_dict['target_name'] = target_result.get('target_name') if target_result else None
                            else:
                                price_dict['target_name'] = None
                        except Exception:
                            price_dict['target_name'] = None
                except Exception as fetch_err:
                    # If fetching with joins fails, try to get target_name and currency_name separately
                    logger.warning(f"Failed to fetch price with joins, trying fallback: {fetch_err}")
                    price_dict['created_by'] = None
                    price_dict['updated_by'] = None
                    price_dict['deleted_by'] = None
                    
                    # Try to get currency name
                    try:
                        cursor.execute(
                            f"""SELECT symbol as currency_name
                            FROM {db_settings.CORE_PLATFORM_CURRENCY}
                            WHERE id = %s AND tenant_id = %s""",
                            (data.currency, tenant_id),
                        )
                        currency_result = cursor.fetchone()
                        price_dict['currency_name'] = currency_result.get('currency_name') if currency_result else None
                    except Exception:
                        price_dict['currency_name'] = None
                    
                    # Replace currency ID with currency name if available
                    if price_dict.get('currency_name'):
                        price_dict['currency'] = price_dict['currency_name']
                        # Remove currency_name since we only expose currency
                        del price_dict['currency_name']
                    
                    # Try to get target_name based on of_type
                    try:
                        if data.of_type == 'SKU' and data.target_id:
                            cursor.execute(
                                f"""SELECT name as target_name
                                FROM {db_settings.MSG_PRODUCTS_TABLE}
                                WHERE sku = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (data.target_id, tenant_id, org_id, bus_id),
                            )
                            target_result = cursor.fetchone()
                            price_dict['target_name'] = target_result.get('target_name') if target_result else None
                        elif data.of_type == 'LOCATION' and data.target_id:
                            cursor.execute(
                                f"""SELECT loc_name as target_name
                                FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                                WHERE id = %s AND tenant_id = %s""",
                                (data.target_id, tenant_id),
                            )
                            target_result = cursor.fetchone()
                            price_dict['target_name'] = target_result.get('target_name') if target_result else None
                        elif data.of_type in ['TAG', 'CATEGORY', 'BRAND', 'LABEL'] and data.target_id:
                            cursor.execute(
                                f"""SELECT name as target_name
                                FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (data.target_id, tenant_id, org_id, bus_id),
                            )
                            target_result = cursor.fetchone()
                            price_dict['target_name'] = target_result.get('target_name') if target_result else None
                        else:
                            price_dict['target_name'] = None
                    except Exception:
                        price_dict['target_name'] = None

                # Create DTO - wrap in try-except to catch validation errors
                try:
                    price_read = CreateProductPriceServiceReadDto(**price_dict)
                except Exception as dto_err:
                    logger.error(f"Failed to create DTO: {dto_err}", exc_info=True)
                    logger.error(f"Price dict keys: {list(price_dict.keys()) if price_dict else 'None'}")
                    logger.error(f"Price dict: {price_dict}")
                    raise ValueError(f"Failed to create response DTO: {str(dto_err)}")

                # Log activity (wrapped in savepoint to prevent rollback on failure)
                try:
                    cursor.execute("SAVEPOINT before_activity_log")
                    try:
                        cursor.execute(
                            f"""SELECT * FROM {db_settings.MSG_PRODUCT_PRICES_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (price_id, tenant_id, org_id, bus_id),
                        )
                        complete_new_data_record = cursor.fetchone()
                        if not complete_new_data_record:
                            raise ValueError("Failed to fetch complete data for activity log")
                        
                        complete_new_data = dict(complete_new_data_record)
                        
                        ActivityLogService.log_activity(
                            tenant_id=tenant_id,
                            resource_type="rt-product-prices",
                            resource_id=price_id,
                            action="create",
                            old_data=None,
                            new_data=complete_new_data,
                            description=f"Product price {price_id} created successfully",
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

                logger.info(
                    f"Product price created successfully: {price_id}",
                    extra={
                        "extra_fields": {
                            "price_id": price_id,
                            "product_id": data.product_id,
                            "of_type": data.of_type,
                            "rowcount": cursor.rowcount,
                        }
                    },
                )

                logger.info(f"About to return success response for price {price_id} - transaction should commit")

                return Respons(
                    success=True,
                    detail="Product price created successfully",
                    data=[price_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating product price: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating product price: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create product price: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_price(
        data: UpdateProductPriceServiceWriteDto,
        price_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateProductPriceServiceReadDto]:
        """Update a product price"""
        logger.info(
            f"Processing product price update: {price_id}",
            extra={
                "extra_fields": {
                    "price_id": price_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_PRICES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (price_id, tenant_id, org_id, bus_id),
                )
                existing_price = cursor.fetchone()

                if not existing_price:
                    raise ValueError("Product price not found")
                
                # Store complete old data before update
                old_data = dict(existing_price)

                # Validate product if being updated
                if data.product_id is not None:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND id = %s""",
                        (tenant_id, org_id, bus_id, data.product_id),
                    )
                    product = cursor.fetchone()
                    if not product:
                        return Respons(
                            success=False,
                            detail=f"Product with ID '{data.product_id}' not found",
                            error="NOT_FOUND",
                        )

                # Validate currency if being updated
                if data.currency is not None:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.currency),
                    )
                    currency = cursor.fetchone()
                    if not currency:
                        return Respons(
                            success=False,
                            detail=f"Currency with ID '{data.currency}' not found",
                            error="NOT_FOUND",
                        )

                # Determine final of_type and target_id for validation
                final_of_type = data.of_type if data.of_type is not None else old_data.get('of_type')
                final_target_id = data.target_id if data.target_id is not None else old_data.get('target_id')

                # Validate target_id based on of_type if of_type is being updated
                if data.of_type is not None or data.target_id is not None:
                    if final_of_type == 'SKU':
                        # For SKU, target_id should contain the SKU value
                        if not final_target_id:
                            return Respons(
                                success=False,
                                detail=f"target_id is required for of_type 'SKU' (should contain the SKU value)",
                                error="VALIDATION_ERROR",
                            )
                        # Validate product with SKU exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND sku = %s""",
                            (tenant_id, org_id, bus_id, final_target_id),
                        )
                        target = cursor.fetchone()
                        if not target:
                            return Respons(
                                success=False,
                                detail=f"Product with SKU '{final_target_id}' not found",
                                error="NOT_FOUND",
                            )
                    elif final_of_type in ['LOCATION', 'TAG', 'CATEGORY', 'BRAND', 'LABEL']:
                        if not final_target_id:
                            return Respons(
                                success=False,
                                detail=f"target_id is required for of_type '{final_of_type}'",
                                error="VALIDATION_ERROR",
                            )

                        if final_of_type == 'LOCATION':
                            cursor.execute(
                                f"""SELECT id FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                                WHERE tenant_id = %s AND id = %s""",
                                (tenant_id, final_target_id),
                            )
                            target = cursor.fetchone()
                            if not target:
                                return Respons(
                                    success=False,
                                    detail=f"Location with ID '{final_target_id}' not found",
                                    error="NOT_FOUND",
                                )
                        else:
                            cursor.execute(
                                f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                AND id = %s""",
                                (tenant_id, org_id, bus_id, final_target_id),
                            )
                            target = cursor.fetchone()
                            if not target:
                                return Respons(
                                    success=False,
                                    detail=f"Product metadata with ID '{final_target_id}' not found",
                                    error="NOT_FOUND",
                                )
                    elif final_of_type == 'GLOBAL':
                        # target_id should be None for GLOBAL
                        if final_target_id:
                            return Respons(
                                success=False,
                                detail=f"target_id should be null for of_type 'GLOBAL'",
                                error="VALIDATION_ERROR",
                            )

                # Build update query dynamically
                update_fields = []
                params = []

                if data.product_id is not None:
                    update_fields.append("product_id = %s")
                    params.append(data.product_id)
                if data.of_type is not None:
                    update_fields.append("of_type = %s")
                    params.append(data.of_type)
                if data.target_id is not None:
                    update_fields.append("target_id = %s")
                    params.append(data.target_id)
                if data.price is not None:
                    update_fields.append("price = %s")
                    params.append(data.price)
                if data.currency is not None:
                    update_fields.append("currency = %s")
                    params.append(data.currency)
                if data.priority is not None:
                    update_fields.append("priority = %s")
                    params.append(data.priority)
                if data.stops_other_prices is not None:
                    update_fields.append("stops_other_prices = %s")
                    params.append(data.stops_other_prices)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([price_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PRODUCT_PRICES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_price = cursor.fetchone()

                if not updated_price:
                    raise ValueError("Failed to update product price")

                # Get price with user fullnames, target_name, currency_name, filtered by valid currency
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.symbol as currency_name,
                           {ProductPricesService._get_target_name_subquery()}
                    FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    INNER JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency = c.id AND p.tenant_id = c.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s
                    AND c.delete_status = 'NOT_DELETED' AND c.is_active = true""",
                    (price_id, tenant_id),
                )
                price_with_users = cursor.fetchone()

                if price_with_users:
                    price_dict = dict(price_with_users)
                    price_dict['created_by'] = price_dict.get('created_by') or None
                    price_dict['updated_by'] = price_dict.get('updated_by') or None
                    price_dict['deleted_by'] = price_dict.get('deleted_by') or None
                    # Replace currency ID with currency name if available
                    if 'currency_name' in price_dict and price_dict.get('currency_name'):
                        price_dict['currency'] = price_dict['currency_name']
                        # Remove currency_name since we only expose currency
                        del price_dict['currency_name']
                else:
                    price_dict = dict(updated_price)
                    price_dict['created_by'] = None
                    price_dict['updated_by'] = None
                    price_dict['deleted_by'] = None
                    price_dict['target_name'] = None
                    price_dict['currency_name'] = None

                price_read = UpdateProductPriceServiceReadDto(**price_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PRODUCT_PRICES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (price_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")
                    
                    complete_new_data = dict(complete_new_data_record)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-prices",
                        resource_id=price_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Product price {price_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Product price updated successfully: {price_id}")

                return Respons(
                    success=True,
                    detail="Product price updated successfully",
                    data=[price_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating product price: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating product price: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update product price: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_price(
        price_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetProductPriceServiceReadDto]:
        """Get a single product price by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.symbol as currency_name,
                           p.currency as currency_id,
                           prod.name as product_name,
                           {ProductPricesService._get_target_name_subquery()}
                    FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    INNER JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency = c.id AND p.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} prod ON p.product_id = prod.id AND p.tenant_id = prod.tenant_id AND p.org_id = prod.org_id AND p.bus_id = prod.bus_id
                    WHERE p.id = %s AND p.tenant_id = %s AND p.org_id = %s 
                    AND p.bus_id = %s
                    AND c.delete_status = 'NOT_DELETED' AND c.is_active = true""",
                    (price_id, tenant_id, org_id, bus_id),
                )
                price = cursor.fetchone()

                if not price:
                    return Respons(
                        success=False,
                        detail="Product price not found",
                        error="NOT_FOUND",
                    )

                price_dict = dict(price)
                price_dict['created_by'] = price_dict.get('created_by') or None
                price_dict['updated_by'] = price_dict.get('updated_by') or None
                price_dict['deleted_by'] = price_dict.get('deleted_by') or None
                # Store currency_id before replacing currency with symbol
                price_dict['currency_id'] = price_dict.get('currency_id') or price_dict.get('currency')
                # Replace currency ID with currency name if available
                if 'currency_name' in price_dict and price_dict.get('currency_name'):
                    price_dict['currency'] = price_dict['currency_name']
                # Ensure product_name is set
                price_dict['product_name'] = price_dict.get('product_name') or None
                price_read = GetProductPriceServiceReadDto(**price_dict)

                return Respons(
                    success=True,
                    detail="Product price retrieved successfully",
                    data=[price_read],
                )

        except Exception as e:
            logger.error(f"Error getting product price: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product price: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_prices(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        page: int = 1,
        size: int = 10,
        product_id: str = None,
        of_type: str = None,
    ) -> Respons[list[GetProductPricesServiceReadDto]]:
        """Get list of product prices with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "p.tenant_id = %s",
                    "p.org_id = %s",
                    "p.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if product_id:
                    where_conditions.append("p.product_id = %s")
                    params.append(product_id)

                if of_type:
                    where_conditions.append("p.of_type = %s")
                    params.append(of_type)

                where_clause = " AND ".join(where_conditions)

                # Get total count (filtered by valid currency)
                cursor.execute(
                    f"""SELECT COUNT(*) as total FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} p
                    INNER JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency = c.id AND p.tenant_id = c.tenant_id
                    WHERE {where_clause}
                    AND c.delete_status = 'NOT_DELETED' AND c.is_active = true""",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get prices with user fullnames, target_name, currency_name, filtered by valid currency
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.symbol as currency_name,
                           p.currency as currency_id,
                           prod.name as product_name,
                           {ProductPricesService._get_target_name_subquery()}
                    FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    INNER JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency = c.id AND p.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} prod ON p.product_id = prod.id AND p.tenant_id = prod.tenant_id AND p.org_id = prod.org_id AND p.bus_id = prod.bus_id
                    WHERE {where_clause}
                    AND c.delete_status = 'NOT_DELETED' AND c.is_active = true
                    ORDER BY p.priority DESC, p.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                prices = cursor.fetchall()

                price_list = []
                for prc in prices:
                    prc_dict = dict(prc)
                    prc_dict['created_by'] = prc_dict.get('created_by') or None
                    prc_dict['updated_by'] = prc_dict.get('updated_by') or None
                    prc_dict['deleted_by'] = prc_dict.get('deleted_by') or None
                    # Store currency_id before replacing currency with symbol
                    prc_dict['currency_id'] = prc_dict.get('currency_id') or prc_dict.get('currency')
                    # Replace currency ID with currency name if available
                    if 'currency_name' in prc_dict and prc_dict.get('currency_name'):
                        prc_dict['currency'] = prc_dict['currency_name']
                        # Remove currency_name since we only expose currency
                        del prc_dict['currency_name']
                    # Ensure product_name is set
                    prc_dict['product_name'] = prc_dict.get('product_name') or None
                    price_list.append(GetProductPricesServiceReadDto(**prc_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Product prices retrieved successfully",
                    data=price_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting product prices: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product prices: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_price(
        data: DeleteProductPriceServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteProductPriceServiceReadDto]:
        """Delete product price"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get price before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_PRICES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.price_id, tenant_id, org_id, bus_id),
                )
                price = cursor.fetchone()

                if not price:
                    return Respons(
                        success=False,
                        detail="Product price not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(price)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-prices",
                        resource_id=data.price_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Product price {data.price_id} deleted",
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
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_PRICES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.price_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Product price deleted successfully",
                    data=[DeleteProductPriceServiceReadDto(
                        price_id=data.price_id,
                        message="Product price deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting product price: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete product price: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_prices_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetProductPriceStatisticsServiceReadDto]:
        """Get comprehensive statistics for product prices"""
        try:
            with DatabaseManager.transaction() as cursor:
                params = (tenant_id, org_id, bus_id)
                
                # Get key statistics using a single query with conditional aggregation
                # Filter by valid currency (same as in get_prices)
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_prices,
                        
                        -- By type
                        COUNT(CASE WHEN p.of_type = 'SKU' THEN 1 END) as total_sku,
                        COUNT(CASE WHEN p.of_type = 'GLOBAL' THEN 1 END) as total_global,
                        COUNT(CASE WHEN p.of_type = 'LOCATION' THEN 1 END) as total_location,
                        COUNT(CASE WHEN p.of_type = 'TAG' THEN 1 END) as total_tag,
                        COUNT(CASE WHEN p.of_type = 'CATEGORY' THEN 1 END) as total_category,
                        COUNT(CASE WHEN p.of_type = 'BRAND' THEN 1 END) as total_brand,
                        COUNT(CASE WHEN p.of_type = 'LABEL' THEN 1 END) as total_label,
                        
                        -- Additional statistics
                        COUNT(CASE WHEN p.stops_other_prices = TRUE THEN 1 END) as total_stops_other_prices,
                        AVG(p.priority) as average_priority
                    FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} p
                    INNER JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency = c.id AND p.tenant_id = c.tenant_id
                    WHERE p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s
                    AND c.delete_status = 'NOT_DELETED' AND c.is_active = true""",
                    params,
                )
                result = cursor.fetchone()

                if not result:
                    # If no results, return zeros
                    statistics = GetProductPriceStatisticsServiceReadDto(
                        total_prices=0,
                        total_sku=0,
                        total_global=0,
                        total_location=0,
                        total_tag=0,
                        total_category=0,
                        total_brand=0,
                        total_label=0,
                        total_stops_other_prices=0,
                        average_priority=None,
                    )
                else:
                    avg_priority = result.get('average_priority')
                    if avg_priority is not None:
                        avg_priority = Decimal(str(avg_priority)).quantize(Decimal('0.01'))
                    
                    statistics = GetProductPriceStatisticsServiceReadDto(
                        total_prices=result.get('total_prices', 0) or 0,
                        total_sku=result.get('total_sku', 0) or 0,
                        total_global=result.get('total_global', 0) or 0,
                        total_location=result.get('total_location', 0) or 0,
                        total_tag=result.get('total_tag', 0) or 0,
                        total_category=result.get('total_category', 0) or 0,
                        total_brand=result.get('total_brand', 0) or 0,
                        total_label=result.get('total_label', 0) or 0,
                        total_stops_other_prices=result.get('total_stops_other_prices', 0) or 0,
                        average_priority=avg_priority,
                    )

                logger.info(
                    f"Product prices statistics retrieved",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "total_prices": statistics.total_prices,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Product prices statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting product prices statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product prices statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

