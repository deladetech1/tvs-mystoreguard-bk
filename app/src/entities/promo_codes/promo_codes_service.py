from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from src.entities.promo_codes.promo_codes_read_dto import (
    CreatePromoCodeServiceReadDto,
    UpdatePromoCodeServiceReadDto,
    DeletePromoCodeServiceReadDto,
    GetPromoCodeServiceReadDto,
    GetPromoCodesServiceReadDto,
    GetPromoCodesStatisticsServiceReadDto,
)
from src.entities.promo_codes.promo_codes_write_dto import (
    CreatePromoCodeServiceWriteDto,
    UpdatePromoCodeServiceWriteDto,
    DeletePromoCodeServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("promo_codes_service")


class PromoCodesService:
    """Service class for promo codes operations"""

    @staticmethod
    def _fetch_product_objects(product_ids: Optional[List[str]], tenant_id: str, org_id: str, bus_id: str, cursor) -> List[dict]:
        """Helper method to fetch product objects (id and name) from product IDs"""
        if not product_ids:
            return []
        
        try:
            # Convert to list if it's a string or array from database
            if isinstance(product_ids, str):
                import json
                product_ids = json.loads(product_ids)
            
            # Handle PostgreSQL array format
            if isinstance(product_ids, (list, tuple)):
                # Convert to list if needed
                product_ids = list(product_ids)
            else:
                return []
            
            if len(product_ids) == 0:
                return []
            
            # Fetch product IDs and names
            placeholders = ','.join(['%s'] * len(product_ids))
            cursor.execute(
                f"""SELECT id, name 
                FROM {db_settings.MSG_PRODUCTS_TABLE}
                WHERE id IN ({placeholders}) 
                AND tenant_id = %s AND org_id = %s AND bus_id = %s
                AND delete_status = 'NOT_DELETED'""",
                tuple(product_ids) + (tenant_id, org_id, bus_id),
            )
            products = cursor.fetchall()
            return [
                {"product_id": product['id'], "product_name": product['name']}
                for product in products if product.get('id') and product.get('name')
            ]
        except Exception as e:
            logger.warning(f"Error fetching product objects: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def _fetch_category_objects(category_ids: Optional[List[str]], tenant_id: str, org_id: str, bus_id: str, cursor) -> List[dict]:
        """Helper method to fetch category objects (id and name) from category IDs"""
        if not category_ids:
            return []
        
        try:
            # Convert to list if it's a string or array from database
            if isinstance(category_ids, str):
                import json
                category_ids = json.loads(category_ids)
            
            # Handle PostgreSQL array format
            if isinstance(category_ids, (list, tuple)):
                # Convert to list if needed
                category_ids = list(category_ids)
            else:
                return []
            
            if len(category_ids) == 0:
                return []
            
            # Fetch category IDs and names from msg_product_metadata where of_type = 'CATEGORY'
            placeholders = ','.join(['%s'] * len(category_ids))
            cursor.execute(
                f"""SELECT id, name 
                FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                WHERE id IN ({placeholders}) 
                AND tenant_id = %s AND org_id = %s AND bus_id = %s
                AND of_type = 'CATEGORY'
                AND delete_status = 'NOT_DELETED'""",
                tuple(category_ids) + (tenant_id, org_id, bus_id),
            )
            categories = cursor.fetchall()
            return [
                {"category_id": category['id'], "category_name": category['name']}
                for category in categories if category.get('id') and category.get('name')
            ]
        except Exception as e:
            logger.warning(f"Error fetching category objects: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def _fetch_product_metadata_objects(metadata_ids: Optional[List[str]], tenant_id: str, org_id: str, bus_id: str, cursor) -> List[dict]:
        """Helper method to fetch product metadata objects (id, name, and type) from metadata IDs"""
        if not metadata_ids:
            return []
        
        try:
            # Convert to list if it's a string or array from database
            if isinstance(metadata_ids, str):
                import json
                metadata_ids = json.loads(metadata_ids)
            
            # Handle PostgreSQL array format
            if isinstance(metadata_ids, (list, tuple)):
                metadata_ids = list(metadata_ids)
            else:
                return []
            
            if len(metadata_ids) == 0:
                return []
            
            # Fetch metadata IDs, names, and types from msg_product_metadata
            placeholders = ','.join(['%s'] * len(metadata_ids))
            cursor.execute(
                f"""SELECT id, name, of_type 
                FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                WHERE id IN ({placeholders}) 
                AND tenant_id = %s AND org_id = %s AND bus_id = %s
                AND delete_status = 'NOT_DELETED'""",
                tuple(metadata_ids) + (tenant_id, org_id, bus_id),
            )
            metadata_records = cursor.fetchall()
            return [
                {"metadata_id": meta['id'], "metadata_name": meta['name'], "metadata_type": meta['of_type']}
                for meta in metadata_records if meta.get('id') and meta.get('name') and meta.get('of_type')
            ]
        except Exception as e:
            logger.warning(f"Error fetching product metadata objects: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def _fetch_location_objects(location_ids: Optional[List[str]], tenant_id: str, cursor) -> List[dict]:
        """Helper method to fetch location objects (id and name) from location IDs"""
        if not location_ids:
            return []
        
        try:
            # Convert to list if it's a string or array from database
            if isinstance(location_ids, str):
                import json
                location_ids = json.loads(location_ids)
            
            # Handle PostgreSQL array format
            if isinstance(location_ids, (list, tuple)):
                # Convert to list if needed
                location_ids = list(location_ids)
            else:
                return []
            
            if len(location_ids) == 0:
                return []
            
            # Fetch location IDs and names from cp_locations
            placeholders = ','.join(['%s'] * len(location_ids))
            cursor.execute(
                f"""SELECT id, loc_name 
                FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                WHERE id IN ({placeholders}) 
                AND tenant_id = %s
                AND is_active = true
                AND delete_status = 'NOT_DELETED'""",
                tuple(location_ids) + (tenant_id,),
            )
            locations = cursor.fetchall()
            return [
                {"location_id": location['id'], "location_name": location['loc_name']}
                for location in locations if location.get('id') and location.get('loc_name')
            ]
        except Exception as e:
            logger.warning(f"Error fetching location objects: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def create_promo_code(
        data: CreatePromoCodeServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreatePromoCodeServiceReadDto]:
        """Create a new promo code"""
        logger.info(
            f"Processing promo code creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "promo_code": data.promo_code,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if promo code already exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PROMO_CODES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND promo_code = %s""",
                    (tenant_id, org_id, bus_id, data.promo_code.upper()),
                )
                if cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"Promo code '{data.promo_code}' already exists",
                        error="DUPLICATE_CODE",
                    )

                # Validate discount type and value
                if data.discount_type == 'PERCENTAGE':
                    if data.discount_value > 100:
                        return Respons(
                            success=False,
                            detail="Percentage discount cannot exceed 100%",
                            error="INVALID_DISCOUNT_VALUE",
                        )
                    if data.discount_value <= 0:
                        return Respons(
                            success=False,
                            detail="Percentage discount must be greater than 0",
                            error="INVALID_DISCOUNT_VALUE",
                        )
                elif data.discount_type == 'FIXED_AMOUNT':
                    if data.discount_value <= 0:
                        return Respons(
                            success=False,
                            detail="Fixed amount discount must be greater than 0",
                            error="INVALID_DISCOUNT_VALUE",
                        )

                start_date_value = data.start_date if data.start_date else date.today()

                # Generate promo code ID
                promo_code_id = Helper.generate_unique_identifier(prefix="prm")

                # Validate locations are provided (required)
                if not data.applicable_to_locations or len(data.applicable_to_locations) == 0:
                    return Respons(
                        success=False,
                        detail="At least one location must be selected for the promo code",
                        error="INVALID_LOCATIONS",
                    )
                
                # Validate that either products OR product_metadata is set, not both
                if data.applicable_to_products and data.applicable_to_product_metadata:
                    return Respons(
                        success=False,
                        detail="Cannot set both applicable_to_products and applicable_to_product_metadata. Choose one.",
                        error="INVALID_RESTRICTIONS",
                    )
                
                if not data.applicable_to_products and not data.applicable_to_product_metadata:
                    return Respons(
                        success=False,
                        detail="Must set either applicable_to_products or applicable_to_product_metadata",
                        error="INVALID_RESTRICTIONS",
                    )
                
                # Convert lists to PostgreSQL arrays
                applicable_products = data.applicable_to_products if data.applicable_to_products else None
                applicable_product_metadata = data.applicable_to_product_metadata if data.applicable_to_product_metadata else None
                applicable_locations = data.applicable_to_locations
                
                # Validate that applicable product IDs exist in the products table
                if applicable_products:
                    # Check if all product IDs exist
                    placeholders = ','.join(['%s'] * len(applicable_products))
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND id = ANY(%s)
                        AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, applicable_products),
                    )
                    existing_products = [row['id'] for row in cursor.fetchall()]
                    missing_products = [pid for pid in applicable_products if pid not in existing_products]
                    
                    if missing_products:
                        logger.warning(
                            f"Some product IDs in applicable_to_products do not exist: {missing_products}",
                            extra={
                                "extra_fields": {
                                    "missing_product_ids": missing_products,
                                    "applicable_products": applicable_products,
                                }
                            }
                        )
                        # Don't fail - just log a warning. The validation during use will catch it.

                # Insert into msg_promo_codes table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PROMO_CODES_TABLE}
                    (id, tenant_id, org_id, bus_id, promo_code, currency_id, discount_type, discount_value,
                     min_purchase_amount, max_discount_amount, usage_limit_per_customer, total_usage_limit,
                     start_date, end_date, status, applicable_to_customers_only,
                     applicable_to_products, applicable_to_product_metadata, applicable_to_locations, description, notes,
                     is_active, delete_status, current_usage_count,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        promo_code_id, tenant_id, org_id, bus_id,
                        data.promo_code.upper(), data.currency_id, data.discount_type, data.discount_value,
                        data.min_purchase_amount if data.min_purchase_amount else 0,
                        data.max_discount_amount, data.usage_limit_per_customer, data.total_usage_limit,
                        start_date_value, data.end_date,
                        data.status if data.status else 'ACTIVE',
                        data.applicable_to_customers_only if data.applicable_to_customers_only else False,
                        applicable_products, applicable_product_metadata, applicable_locations,
                        data.description, data.notes,
                        data.is_active if data.is_active is not None else True, 'NOT_DELETED', 0,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                promo_code_result = cursor.fetchone()

                if not promo_code_result:
                    raise ValueError("Failed to create promo code")

                # Get promo code with user fullnames and currency info
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol
                    FROM {db_settings.MSG_PROMO_CODES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency_id = c.id AND p.tenant_id = c.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s""",
                    (promo_code_id, tenant_id),
                )
                promo_code_with_users = cursor.fetchone()

                if promo_code_with_users:
                    promo_code_dict = dict(promo_code_with_users)
                    promo_code_dict['created_by'] = promo_code_dict.get('created_by') or None
                    promo_code_dict['updated_by'] = promo_code_dict.get('updated_by') or None
                    promo_code_dict['deleted_by'] = promo_code_dict.get('deleted_by') or None
                    promo_code_dict['currency_name'] = promo_code_dict.get('currency_name') or None
                    promo_code_dict['currency_symbol'] = promo_code_dict.get('currency_symbol') or None
                else:
                    promo_code_dict = dict(promo_code_result)
                    promo_code_dict['created_by'] = None
                    promo_code_dict['updated_by'] = None
                    promo_code_dict['deleted_by'] = None
                    promo_code_dict['currency_name'] = None
                    promo_code_dict['currency_symbol'] = None

                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = promo_code_dict.get('applicable_to_products')
                promo_code_dict['applicable_to_products'] = PromoCodesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = promo_code_dict.get('applicable_to_product_metadata')
                promo_code_dict['applicable_to_product_metadata'] = PromoCodesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = promo_code_dict.get('applicable_to_locations')
                promo_code_dict['applicable_to_locations'] = PromoCodesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )

                promo_code_read = CreatePromoCodeServiceReadDto(**promo_code_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PROMO_CODES_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (promo_code_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(promo_code_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-promo-codes",
                        resource_id=promo_code_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Promo code {data.promo_code} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Promo code created successfully: {promo_code_id}",
                    extra={
                        "extra_fields": {
                            "promo_code_id": promo_code_id,
                            "promo_code": data.promo_code,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Promo code created successfully",
                    data=[promo_code_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating promo code: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating promo code: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create promo code: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_promo_code(
        data: UpdatePromoCodeServiceWriteDto,
        promo_code_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdatePromoCodeServiceReadDto]:
        """Update a promo code"""
        logger.info(
            f"Processing promo code update: {promo_code_id}",
            extra={
                "extra_fields": {
                    "promo_code_id": promo_code_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PROMO_CODES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (promo_code_id, tenant_id, org_id, bus_id),
                )
                existing_promo_code = cursor.fetchone()

                if not existing_promo_code:
                    raise ValueError("Promo code not found")
                
                old_data = dict(existing_promo_code)

                # If code is being updated, check for duplicates
                if data.promo_code is not None and data.promo_code.upper() != old_data.get('promo_code'):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_PROMO_CODES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND promo_code = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.promo_code.upper(), promo_code_id),
                    )
                    duplicate_code = cursor.fetchone()
                    if duplicate_code:
                        raise ValueError(f"Promo code '{data.promo_code}' already exists")

                # Build update query dynamically
                update_fields = []
                params = []

                if data.promo_code is not None:
                    update_fields.append("promo_code = %s")
                    params.append(data.promo_code.upper())
                if data.discount_type is not None:
                    update_fields.append("discount_type = %s")
                    params.append(data.discount_type)
                if data.discount_value is not None:
                    update_fields.append("discount_value = %s")
                    params.append(data.discount_value)
                if data.min_purchase_amount is not None:
                    update_fields.append("min_purchase_amount = %s")
                    params.append(data.min_purchase_amount)
                if data.max_discount_amount is not None:
                    update_fields.append("max_discount_amount = %s")
                    params.append(data.max_discount_amount)
                if data.usage_limit_per_customer is not None:
                    update_fields.append("usage_limit_per_customer = %s")
                    params.append(data.usage_limit_per_customer)
                if data.total_usage_limit is not None:
                    update_fields.append("total_usage_limit = %s")
                    params.append(data.total_usage_limit)
                if data.start_date is not None:
                    update_fields.append("start_date = %s")
                    params.append(data.start_date)
                if data.end_date is not None:
                    update_fields.append("end_date = %s")
                    params.append(data.end_date)
                if data.status is not None:
                    update_fields.append("status = %s")
                    params.append(data.status)
                if data.applicable_to_customers_only is not None:
                    update_fields.append("applicable_to_customers_only = %s")
                    params.append(data.applicable_to_customers_only)
                if data.applicable_to_products is not None:
                    update_fields.append("applicable_to_products = %s")
                    params.append(data.applicable_to_products)
                if data.applicable_to_product_metadata is not None:
                    update_fields.append("applicable_to_product_metadata = %s")
                    params.append(data.applicable_to_product_metadata)
                if data.applicable_to_locations is not None:
                    update_fields.append("applicable_to_locations = %s")
                    params.append(data.applicable_to_locations)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.notes is not None:
                    update_fields.append("notes = %s")
                    params.append(data.notes)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([promo_code_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PROMO_CODES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_promo_code = cursor.fetchone()

                if not updated_promo_code:
                    raise ValueError("Failed to update promo code")

                # Get promo code with user fullnames and currency info
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol
                    FROM {db_settings.MSG_PROMO_CODES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency_id = c.id AND p.tenant_id = c.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s""",
                    (promo_code_id, tenant_id),
                )
                promo_code_with_users = cursor.fetchone()

                if promo_code_with_users:
                    promo_code_dict = dict(promo_code_with_users)
                    promo_code_dict['created_by'] = promo_code_dict.get('created_by') or None
                    promo_code_dict['updated_by'] = promo_code_dict.get('updated_by') or None
                    promo_code_dict['deleted_by'] = promo_code_dict.get('deleted_by') or None
                    promo_code_dict['currency_name'] = promo_code_dict.get('currency_name') or None
                    promo_code_dict['currency_symbol'] = promo_code_dict.get('currency_symbol') or None
                else:
                    promo_code_dict = dict(updated_promo_code)
                    promo_code_dict['created_by'] = None
                    promo_code_dict['updated_by'] = None
                    promo_code_dict['deleted_by'] = None
                    promo_code_dict['currency_name'] = None
                    promo_code_dict['currency_symbol'] = None

                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = promo_code_dict.get('applicable_to_products')
                promo_code_dict['applicable_to_products'] = PromoCodesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = promo_code_dict.get('applicable_to_product_metadata')
                promo_code_dict['applicable_to_product_metadata'] = PromoCodesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = promo_code_dict.get('applicable_to_locations')
                promo_code_dict['applicable_to_locations'] = PromoCodesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )

                promo_code_read = UpdatePromoCodeServiceReadDto(**promo_code_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PROMO_CODES_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (promo_code_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(promo_code_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-promo-codes",
                        resource_id=promo_code_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Promo code {promo_code_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Promo code updated successfully: {promo_code_id}")

                return Respons(
                    success=True,
                    detail="Promo code updated successfully",
                    data=[promo_code_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating promo code: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating promo code: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update promo code: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_promo_code(
        promo_code_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPromoCodeServiceReadDto]:
        """Get a single promo code by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol
                    FROM {db_settings.MSG_PROMO_CODES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency_id = c.id AND p.tenant_id = c.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s AND p.org_id = %s 
                    AND p.bus_id = %s""",
                    (promo_code_id, tenant_id, org_id, bus_id),
                )
                promo_code = cursor.fetchone()

                if not promo_code:
                    return Respons(
                        success=False,
                        detail="Promo code not found",
                        error="NOT_FOUND",
                    )

                promo_code_dict = dict(promo_code)
                promo_code_dict['created_by'] = promo_code_dict.get('created_by') or None
                promo_code_dict['updated_by'] = promo_code_dict.get('updated_by') or None
                promo_code_dict['deleted_by'] = promo_code_dict.get('deleted_by') or None
                promo_code_dict['currency_name'] = promo_code_dict.get('currency_name') or None
                promo_code_dict['currency_symbol'] = promo_code_dict.get('currency_symbol') or None
                
                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = promo_code_dict.get('applicable_to_products')
                promo_code_dict['applicable_to_products'] = PromoCodesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = promo_code_dict.get('applicable_to_product_metadata')
                promo_code_dict['applicable_to_product_metadata'] = PromoCodesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = promo_code_dict.get('applicable_to_locations')
                promo_code_dict['applicable_to_locations'] = PromoCodesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                promo_code_read = GetPromoCodeServiceReadDto(**promo_code_dict)

                return Respons(
                    success=True,
                    detail="Promo code retrieved successfully",
                    data=[promo_code_read],
                )

        except Exception as e:
            logger.error(f"Error getting promo code: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get promo code: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_promo_code_by_code(
        promo_code: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPromoCodeServiceReadDto]:
        """Get a promo code by code string"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol
                    FROM {db_settings.MSG_PROMO_CODES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency_id = c.id AND p.tenant_id = c.tenant_id
                    WHERE p.promo_code = %s AND p.tenant_id = %s AND p.org_id = %s 
                    AND p.bus_id = %s""",
                    (promo_code.upper(), tenant_id, org_id, bus_id),
                )
                promo_code_result = cursor.fetchone()

                if not promo_code_result:
                    return Respons(
                        success=False,
                        detail="Promo code not found",
                        error="NOT_FOUND",
                    )

                promo_code_dict = dict(promo_code_result)
                promo_code_dict['created_by'] = promo_code_dict.get('created_by') or None
                promo_code_dict['updated_by'] = promo_code_dict.get('updated_by') or None
                promo_code_dict['deleted_by'] = promo_code_dict.get('deleted_by') or None
                promo_code_dict['currency_name'] = promo_code_dict.get('currency_name') or None
                promo_code_dict['currency_symbol'] = promo_code_dict.get('currency_symbol') or None
                
                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = promo_code_dict.get('applicable_to_products')
                promo_code_dict['applicable_to_products'] = PromoCodesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = promo_code_dict.get('applicable_to_product_metadata')
                promo_code_dict['applicable_to_product_metadata'] = PromoCodesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = promo_code_dict.get('applicable_to_locations')
                promo_code_dict['applicable_to_locations'] = PromoCodesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                promo_code_read = GetPromoCodeServiceReadDto(**promo_code_dict)

                return Respons(
                    success=True,
                    detail="Promo code retrieved successfully",
                    data=[promo_code_read],
                )

        except Exception as e:
            logger.error(f"Error getting promo code: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get promo code: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_promo_codes(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        is_active: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetPromoCodesServiceReadDto]]:
        """Get list of promo codes with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "p.tenant_id = %s",
                    "p.org_id = %s",
                    "p.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if is_active is not None:
                    where_conditions.append("p.is_active = %s")
                    params.append(is_active)
                if status:
                    where_conditions.append("p.status = %s")
                    params.append(status)
                if search:
                    where_conditions.append(
                        "(p.promo_code ILIKE %s OR p.description ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_PROMO_CODES_TABLE} p WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get promo codes with user fullnames and currency info
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol
                    FROM {db_settings.MSG_PROMO_CODES_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON p.currency_id = c.id AND p.tenant_id = c.tenant_id
                    WHERE {where_clause}
                    ORDER BY p.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                promo_codes = cursor.fetchall()

                promo_code_list = []
                for pc in promo_codes:
                    pc_dict = dict(pc)
                    pc_dict['created_by'] = pc_dict.get('created_by') or None
                    pc_dict['updated_by'] = pc_dict.get('updated_by') or None
                    pc_dict['deleted_by'] = pc_dict.get('deleted_by') or None
                    pc_dict['currency_name'] = pc_dict.get('currency_name') or None
                    pc_dict['currency_symbol'] = pc_dict.get('currency_symbol') or None
                    
                    # Format applicable_to_products as objects with product_id and product_name
                    applicable_product_ids = pc_dict.get('applicable_to_products')
                    pc_dict['applicable_to_products'] = PromoCodesService._fetch_product_objects(
                        applicable_product_ids, tenant_id, org_id, bus_id, cursor
                    )
                    
                    # Format applicable_to_categories as objects with category_id and category_name
                    applicable_category_ids = pc_dict.get('applicable_to_categories')
                    pc_dict['applicable_to_categories'] = PromoCodesService._fetch_category_objects(
                        applicable_category_ids, tenant_id, org_id, bus_id, cursor
                    )
                    
                    # Format applicable_to_locations as objects with location_id and location_name
                    applicable_location_ids = pc_dict.get('applicable_to_locations')
                    pc_dict['applicable_to_locations'] = PromoCodesService._fetch_location_objects(
                        applicable_location_ids, tenant_id, cursor
                    )
                    
                    promo_code_list.append(GetPromoCodesServiceReadDto(**pc_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Promo codes retrieved successfully",
                    data=promo_code_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting promo codes: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get promo codes: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_promo_code(
        data: DeletePromoCodeServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeletePromoCodeServiceReadDto]:
        """Delete a promo code"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get promo code details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PROMO_CODES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.promo_code_id, tenant_id, org_id, bus_id),
                )
                promo_code = cursor.fetchone()

                if not promo_code:
                    return Respons(
                        success=False,
                        detail="Promo code not found",
                        error="NOT_FOUND",
                    )

                complete_old_data = dict(promo_code)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-promo-codes",
                        resource_id=data.promo_code_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Promo code {data.promo_code_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Delete
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PROMO_CODES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.promo_code_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Promo code deleted successfully",
                    data=[DeletePromoCodeServiceReadDto(
                        promo_code_id=data.promo_code_id,
                        message="Promo code deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting promo code: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete promo code: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def validate_and_calculate_discount(
        promo_code: str,
        item_line_totals: Optional[List[Decimal]] = None,
        customer_id: Optional[str] = None,
        tenant_id: str = None,
        org_id: str = None,
        bus_id: str = None,
        cursor = None,
        product_ids: Optional[List[str]] = None,
        product_metadata: Optional[Dict[str, List[str]]] = None,
        location_id: Optional[str] = None
    ) -> tuple[bool, Optional[str], Optional[Decimal], Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate promo code for per-item discount application
        Returns: (is_valid, error_message, discount_amount_for_cart_total, promo_code_id, promo_details)
        
        Args:
            item_line_totals: List of line totals (price_after_pricing_rule × quantity) for each item in cart.
                             Used to check if ANY item meets min_purchase_amount requirement.
            product_ids: List of product IDs in the cart (for checking applicable_to_products)
            product_metadata: Dict with keys like 'category_ids', 'tag_ids', 'brand_ids', 'label_ids' (for checking applicable_to_product_metadata)
            location_id: Location ID where the sale is being made (for checking applicable_to_locations)
        
        Note: Discounts are now ALWAYS applied per-item (before tax). The discount_amount returned is None 
        since calculation happens per-item. promo_details contains discount_type, discount_value, max_discount_amount.
        min_purchase_amount is checked against individual item line totals (price_after_pricing_rule × quantity), not cart total.
        """
        try:
            # Get promo code
            cursor.execute(
                f"""SELECT * FROM {db_settings.MSG_PROMO_CODES_TABLE}
                WHERE promo_code = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                AND is_active = true AND delete_status = 'NOT_DELETED'""",
                (promo_code.upper(), tenant_id, org_id, bus_id),
            )
            promo_code_data = cursor.fetchone()

            if not promo_code_data:
                return False, "Promo code not found", None, None, None

            promo_dict = dict(promo_code_data)

            # Check status
            if promo_dict.get('status') != 'ACTIVE':
                return False, "Promo code is not active", None, None, None

            # Check date range
            today = date.today()
            if promo_dict.get('start_date') and promo_dict['start_date'] > today:
                return False, "Promo code has not started yet", None, None, None
            if promo_dict.get('end_date') and promo_dict['end_date'] < today:
                return False, "Promo code has expired", None, None, None

            # Check minimum purchase amount against individual item line totals (price_after_pricing_rule × quantity)
            # The promo code is valid if ANY item's line total meets the minimum purchase amount
            min_purchase = Decimal(str(promo_dict.get('min_purchase_amount', 0)))
            if min_purchase > 0:
                if not item_line_totals or len(item_line_totals) == 0:
                    return False, f"Minimum purchase amount of {min_purchase} required per item", None, None, None
                
                # Check if any item's line total meets the minimum purchase amount
                any_item_meets_minimum = any(line_total >= min_purchase for line_total in item_line_totals if line_total is not None)
                
                if not any_item_meets_minimum:
                    max_line_total = max(item_line_totals) if item_line_totals else Decimal('0')
                    return False, f"Minimum purchase amount of {min_purchase} required per item. Highest item total is {max_line_total}", None, None, None

            # Check if customer-only and customer provided
            if promo_dict.get('applicable_to_customers_only') and not customer_id:
                return False, "This promo code is only available for registered customers", None, None, None

            # Check usage limits
            if promo_dict.get('total_usage_limit'):
                if promo_dict.get('current_usage_count', 0) >= promo_dict['total_usage_limit']:
                    return False, "Promo code usage limit reached", None, None, None

            if promo_dict.get('usage_limit_per_customer') and customer_id:
                cursor.execute(
                    f"""SELECT COUNT(*) as usage_count FROM {db_settings.MSG_PROMO_CODE_USAGE_TABLE}
                    WHERE promo_code_id = %s AND customer_id = %s
                    AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (promo_dict['id'], customer_id, tenant_id, org_id, bus_id),
                )
                usage_result = cursor.fetchone()
                usage_count = usage_result['usage_count'] if usage_result else 0
                if usage_count >= promo_dict['usage_limit_per_customer']:
                    return False, "You have reached the usage limit for this promo code", None, None, None

            # =====================================================
            # NEW VALIDATION FLOW: Location-first, then Products OR Metadata
            # =====================================================
            
            # STEP 1: Check location FIRST (required, must match)
            applicable_locations = promo_dict.get('applicable_to_locations')
            if not applicable_locations:
                return False, "Promo code is not configured for any locations. At least one location must be selected.", None, None, None
            
            # Convert PostgreSQL array to Python list if needed
            if isinstance(applicable_locations, str):
                import ast
                try:
                    applicable_locations = ast.literal_eval(applicable_locations)
                except:
                    applicable_locations = [applicable_locations]
            elif not isinstance(applicable_locations, list):
                applicable_locations = list(applicable_locations) if applicable_locations else []
            
            if not location_id:
                return False, "Promo code requires a valid location", None, None, None
            
            # Normalize for comparison
            applicable_locations_normalized = [str(loc).strip() for loc in applicable_locations if loc]
            location_id_normalized = str(location_id).strip()
            
            if location_id_normalized not in applicable_locations_normalized:
                return False, "Promo code is not valid for this location", None, None, None
            
            # STEP 2: Check products OR metadata (one must be set and match)
            applicable_products = promo_dict.get('applicable_to_products')
            applicable_product_metadata = promo_dict.get('applicable_to_product_metadata')
            
            # Validate that either products OR metadata is set (not both, not neither)
            if applicable_products and applicable_product_metadata:
                return False, "Promo code cannot have both products and product metadata restrictions. Choose one.", None, None, None
            
            if not applicable_products and not applicable_product_metadata:
                return False, "Promo code must have either product or product metadata restrictions configured", None, None, None
            
            # Check products OR metadata match
            if applicable_products:
                # Convert PostgreSQL array to Python list if needed
                # PostgreSQL arrays can be returned as list, tuple, or string depending on psycopg2 version
                if isinstance(applicable_products, str):
                    # Handle string representation of array like "{id1,id2}" or "[id1,id2]"
                    import ast
                    import re
                    try:
                        # Try to parse as Python list
                        applicable_products = ast.literal_eval(applicable_products)
                    except:
                        # Try to parse PostgreSQL array format {id1,id2}
                        if applicable_products.startswith('{') and applicable_products.endswith('}'):
                            applicable_products = [p.strip() for p in applicable_products[1:-1].split(',') if p.strip()]
                        else:
                            applicable_products = [applicable_products]
                elif isinstance(applicable_products, (tuple, set)):
                    applicable_products = list(applicable_products)
                elif not isinstance(applicable_products, list):
                    applicable_products = [applicable_products] if applicable_products else []
                
                # Filter out None/empty values
                applicable_products = [p for p in applicable_products if p]
                
                logger.info(
                    f"Checking product restrictions for promo code '{promo_code}': applicable_products={applicable_products} (type={type(applicable_products)}), cart_product_ids={product_ids}",
                    extra={
                        "extra_fields": {
                            "promo_code": promo_code,
                            "applicable_products": applicable_products,
                            "applicable_products_type": str(type(applicable_products)),
                            "cart_product_ids": product_ids,
                        }
                    }
                )
                
                # If promo code is restricted to specific products, check if cart matches
                if product_ids and applicable_products:
                    # Normalize both lists to strings for comparison
                    applicable_products_normalized = [str(p).strip() for p in applicable_products]
                    cart_product_ids_normalized = [str(p).strip() for p in product_ids]
                    
                    # Check if any product in cart matches the applicable products
                    product_match = any(pid in applicable_products_normalized for pid in cart_product_ids_normalized)
                    
                    logger.info(
                        f"Product match check: applicable_products_normalized={applicable_products_normalized}, cart_product_ids_normalized={cart_product_ids_normalized}, match={product_match}",
                        extra={
                            "extra_fields": {
                                "applicable_products_normalized": applicable_products_normalized,
                                "cart_product_ids_normalized": cart_product_ids_normalized,
                                "product_match": product_match,
                            }
                        }
                    )
                    
                    if not product_match:
                        # Cart doesn't contain any of the restricted products
                        logger.warning(f"Cart doesn't contain any restricted products. Applicable: {applicable_products_normalized}, Cart: {cart_product_ids_normalized}")
                        return False, "Promo code is not applicable to any products in your cart", None, None, None
                elif not product_ids:
                    # No products in cart but promo code is restricted
                    logger.warning(f"No products in cart but promo code is restricted to products: {applicable_products}")
                    return False, "Promo code requires specific products to be in cart", None, None, None
                    
            elif applicable_product_metadata:
                # Check product metadata (categories, tags, brands, labels)
                # Convert PostgreSQL array to Python list if needed
                if isinstance(applicable_product_metadata, str):
                    import ast
                    try:
                        applicable_product_metadata = ast.literal_eval(applicable_product_metadata)
                    except:
                        applicable_product_metadata = [applicable_product_metadata]
                elif not isinstance(applicable_product_metadata, list):
                    applicable_product_metadata = list(applicable_product_metadata) if applicable_product_metadata else []
                
                # Filter out None/empty values
                applicable_metadata_ids = [m for m in applicable_product_metadata if m]
                
                if not applicable_metadata_ids:
                    return False, "Promo code has no valid product metadata configured", None, None, None
                
                # Check if product_metadata is provided and matches
                if not product_metadata:
                    return False, "Promo code requires products with specific metadata (categories, tags, brands, or labels)", None, None, None
                
                # Check if any product's metadata matches the applicable metadata
                # product_metadata is a dict with keys like 'category_ids', 'tag_ids', 'brand_ids', 'label_ids'
                metadata_match = False
                all_metadata_ids = []
                for key, ids in product_metadata.items():
                    if isinstance(ids, list):
                        all_metadata_ids.extend(ids)
                    elif ids:
                        all_metadata_ids.append(ids)
                
                applicable_metadata_normalized = [str(m).strip() for m in applicable_metadata_ids]
                cart_metadata_normalized = [str(m).strip() for m in all_metadata_ids if m]
                
                metadata_match = any(mid in applicable_metadata_normalized for mid in cart_metadata_normalized)
                
                logger.info(
                    f"Product metadata match check: applicable_metadata={applicable_metadata_normalized}, cart_metadata={cart_metadata_normalized}, match={metadata_match}",
                    extra={
                        "extra_fields": {
                            "applicable_metadata": applicable_metadata_normalized,
                            "cart_metadata": cart_metadata_normalized,
                            "metadata_match": metadata_match,
                        }
                    }
                )
                
                if not metadata_match:
                    return False, "Promo code is not applicable to any product metadata (categories, tags, brands, labels) in your cart", None, None, None

            # Validation passed - return promo code details for per-item application
            # Discounts are now ALWAYS applied per-item (before tax), so we return None for discount_amount
            # and return promo details for the price calculator to apply per-item
            discount_type = promo_dict.get('discount_type')
            discount_value = Decimal(str(promo_dict.get('discount_value', 0)))
            max_discount_amount = Decimal(str(promo_dict.get('max_discount_amount'))) if promo_dict.get('max_discount_amount') else None
            
            # Ensure applicable_products is a normalized list (not string/None) for per-item checking
            # It should already be a list from the parsing above, but ensure it's properly formatted
            normalized_applicable_products = None
            if applicable_products:
                if isinstance(applicable_products, list):
                    # Already a list, just normalize the values
                    normalized_applicable_products = [str(p).strip() for p in applicable_products if p]
                elif isinstance(applicable_products, str):
                    # Parse again if somehow it's still a string
                    import ast
                    try:
                        parsed = ast.literal_eval(applicable_products)
                        normalized_applicable_products = [str(p).strip() for p in (parsed if isinstance(parsed, list) else [parsed]) if p]
                    except:
                        if applicable_products.startswith('{') and applicable_products.endswith('}'):
                            normalized_applicable_products = [p.strip() for p in applicable_products[1:-1].split(',') if p.strip()]
                        else:
                            normalized_applicable_products = [applicable_products.strip()] if applicable_products.strip() else None
            
            # Normalize applicable_product_metadata similarly
            normalized_applicable_metadata = None
            if applicable_product_metadata:
                if isinstance(applicable_product_metadata, list):
                    normalized_applicable_metadata = [str(m).strip() for m in applicable_product_metadata if m]
                elif isinstance(applicable_product_metadata, str):
                    import ast
                    try:
                        parsed = ast.literal_eval(applicable_product_metadata)
                        normalized_applicable_metadata = [str(m).strip() for m in (parsed if isinstance(parsed, list) else [parsed]) if m]
                    except:
                        if applicable_product_metadata.startswith('{') and applicable_product_metadata.endswith('}'):
                            normalized_applicable_metadata = [m.strip() for m in applicable_product_metadata[1:-1].split(',') if m.strip()]
                        else:
                            normalized_applicable_metadata = [applicable_product_metadata.strip()] if applicable_product_metadata.strip() else None
            
            promo_details = {
                'discount_type': discount_type,
                'discount_value': discount_value,
                'max_discount_amount': max_discount_amount,
                'applicable_to_products': normalized_applicable_products,  # Always a list of normalized strings or None
                'applicable_to_product_metadata': normalized_applicable_metadata,  # Always a list of normalized strings or None
            }
            
            logger.info(
                f"Promo code '{promo_code}' validated successfully. Will be applied per-item. Details: {promo_details}",
                extra={
                    "extra_fields": {
                        "promo_code": promo_code,
                        "promo_id": promo_dict['id'],
                        "discount_type": discount_type,
                        "discount_value": float(discount_value),
                    }
                }
            )
            
            return True, None, None, promo_dict['id'], promo_details

        except Exception as e:
            logger.error(f"Error validating promo code: {str(e)}", exc_info=True)
            return False, f"Error validating promo code: {str(e)}", None, None, None

    @staticmethod
    def get_promo_codes_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPromoCodesStatisticsServiceReadDto]:
        """Get promo codes statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get promo codes statistics
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_promo_codes,
                        COUNT(CASE WHEN status = 'ACTIVE' AND is_active = TRUE THEN 1 END) as total_active,
                        COUNT(CASE WHEN status = 'INACTIVE' OR is_active = FALSE THEN 1 END) as total_inactive,
                        COUNT(CASE WHEN status = 'EXPIRED' THEN 1 END) as total_expired,
                        COALESCE(SUM(current_usage_count), 0) as total_usage_count
                    FROM {db_settings.MSG_PROMO_CODES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id),
                )
                promo_stats = cursor.fetchone()

                # Get discount statistics from usage table
                cursor.execute(
                    f"""SELECT 
                        COALESCE(SUM(discount_amount), 0) as total_discount_given,
                        COUNT(*) as total_sales_using_promo_codes
                    FROM {db_settings.MSG_PROMO_CODE_USAGE_TABLE} pcu
                    INNER JOIN {db_settings.MSG_PROMO_CODES_TABLE} pc
                        ON pcu.promo_code_id = pc.id 
                        AND pcu.tenant_id = pc.tenant_id 
                        AND pcu.org_id = pc.org_id 
                        AND pcu.bus_id = pc.bus_id
                    WHERE pcu.tenant_id = %s AND pcu.org_id = %s AND pcu.bus_id = %s""",
                    (tenant_id, org_id, bus_id),
                )
                usage_stats = cursor.fetchone()

                total_usage_count = int(promo_stats['total_usage_count'] or 0)
                total_discount_given = float(usage_stats['total_discount_given'] or 0)
                average_discount_per_usage = (
                    total_discount_given / total_usage_count if total_usage_count > 0 else 0
                )

                statistics = GetPromoCodesStatisticsServiceReadDto(
                    total_promo_codes=int(promo_stats['total_promo_codes'] or 0),
                    total_active=int(promo_stats['total_active'] or 0),
                    total_inactive=int(promo_stats['total_inactive'] or 0),
                    total_expired=int(promo_stats['total_expired'] or 0),
                    total_usage_count=total_usage_count,
                    total_discount_given=total_discount_given,
                    average_discount_per_usage=average_discount_per_usage,
                    total_sales_using_promo_codes=int(usage_stats['total_sales_using_promo_codes'] or 0),
                )

                return Respons(
                    success=True,
                    detail="Promo codes statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting promo codes statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get promo codes statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

