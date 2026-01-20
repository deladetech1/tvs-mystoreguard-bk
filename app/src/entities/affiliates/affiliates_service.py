from typing import Optional, List
from decimal import Decimal
from src.entities.affiliates.affiliates_read_dto import (
    CreateAffiliateServiceReadDto,
    UpdateAffiliateServiceReadDto,
    DeleteAffiliateServiceReadDto,
    GetAffiliateServiceReadDto,
    GetAffiliatesServiceReadDto,
    GetAffiliatesStatisticsServiceReadDto,
)
from src.entities.affiliates.affiliates_write_dto import (
    CreateAffiliateServiceWriteDto,
    UpdateAffiliateServiceWriteDto,
    DeleteAffiliateServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("affiliates_service")


class AffiliatesService:
    """Service class for affiliates operations"""

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
    def _fetch_product_objects(product_ids: Optional[List[str]], tenant_id: str, org_id: str, bus_id: str, cursor) -> List[dict]:
        """Helper method to fetch product objects (id and name) from product IDs"""
        if not product_ids:
            return []
        
        try:
            # Convert to list if it's a string or array from database
            if isinstance(product_ids, str):
                import json
                product_ids = json.loads(product_ids)
            
            if isinstance(product_ids, (list, tuple)):
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
    def _fetch_product_metadata_objects(metadata_ids: Optional[List[str]], tenant_id: str, org_id: str, bus_id: str, cursor) -> List[dict]:
        """Helper method to fetch product metadata objects (id, name, and type) from metadata IDs"""
        if not metadata_ids:
            return []
        
        try:
            # Convert to list if it's a string or array from database
            if isinstance(metadata_ids, str):
                import json
                metadata_ids = json.loads(metadata_ids)
            
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
    def create_affiliate(
        data: CreateAffiliateServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateAffiliateServiceReadDto]:
        """Create a new affiliate"""
        logger.info(
            f"Processing affiliate creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "affiliate_code": data.affiliate_code,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if affiliate code already exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_AFFILIATES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND affiliate_code = %s""",
                    (tenant_id, org_id, bus_id, data.affiliate_code.upper()),
                )
                if cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"Affiliate with code '{data.affiliate_code}' already exists",
                        error="DUPLICATE_CODE",
                    )

                # Validate commission
                if data.commission_type == 'PERCENTAGE' and data.commission_rate > 100:
                    return Respons(
                        success=False,
                        detail="Commission rate cannot exceed 100%",
                        error="INVALID_COMMISSION_RATE",
                    )
                if data.commission_type == 'FIXED_AMOUNT' and not data.fixed_commission_amount:
                    return Respons(
                        success=False,
                        detail="fixed_commission_amount is required when commission_type is FIXED_AMOUNT",
                        error="MISSING_FIXED_COMMISSION",
                    )

                # Generate affiliate ID
                affiliate_id = Helper.generate_unique_identifier(prefix="aff")

                # Convert lists to PostgreSQL arrays
                applicable_locations = data.applicable_to_locations if data.applicable_to_locations else None
                applicable_products = data.applicable_to_products if data.applicable_to_products else None
                applicable_product_metadata = data.applicable_to_product_metadata if data.applicable_to_product_metadata else None

                # Insert into msg_affiliates table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_AFFILIATES_TABLE}
                    (id, tenant_id, org_id, bus_id, affiliate_code, affiliate_name,
                     contact_email, contact_phone, commission_rate, commission_type,
                     fixed_commission_amount, status, description, notes,
                     applicable_to_locations, applicable_to_products, applicable_to_product_metadata,
                     is_active, delete_status, total_referrals, total_conversions,
                     total_commission_earned, total_commission_paid,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        affiliate_id, tenant_id, org_id, bus_id,
                        data.affiliate_code.upper(), data.affiliate_name,
                        data.contact_email, data.contact_phone,
                        data.commission_rate, data.commission_type if data.commission_type else 'PERCENTAGE',
                        data.fixed_commission_amount,
                        data.status if data.status else 'ACTIVE',
                        data.description, data.notes,
                        applicable_locations, applicable_products, applicable_product_metadata,
                        data.is_active if data.is_active is not None else True, 'NOT_DELETED',
                        0, 0, Decimal('0'), Decimal('0'),  # Initialize stats
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                affiliate_result = cursor.fetchone()

                if not affiliate_result:
                    raise ValueError("Failed to create affiliate")

                # Get affiliate with user fullnames
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_AFFILIATES_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    WHERE a.id = %s AND a.tenant_id = %s""",
                    (affiliate_id, tenant_id),
                )
                affiliate_with_users = cursor.fetchone()

                if affiliate_with_users:
                    affiliate_dict = dict(affiliate_with_users)
                    affiliate_dict['created_by'] = affiliate_dict.get('created_by') or None
                    affiliate_dict['updated_by'] = affiliate_dict.get('updated_by') or None
                    affiliate_dict['deleted_by'] = affiliate_dict.get('deleted_by') or None
                else:
                    affiliate_dict = dict(affiliate_result)
                    affiliate_dict['created_by'] = None
                    affiliate_dict['updated_by'] = None
                    affiliate_dict['deleted_by'] = None

                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = affiliate_dict.get('applicable_to_locations')
                affiliate_dict['applicable_to_locations'] = AffiliatesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = affiliate_dict.get('applicable_to_products')
                affiliate_dict['applicable_to_products'] = AffiliatesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = affiliate_dict.get('applicable_to_product_metadata')
                affiliate_dict['applicable_to_product_metadata'] = AffiliatesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )

                affiliate_read = CreateAffiliateServiceReadDto(**affiliate_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_AFFILIATES_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (affiliate_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(affiliate_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-affiliates",
                        resource_id=affiliate_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Affiliate {data.affiliate_code} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Affiliate created successfully: {affiliate_id}",
                    extra={
                        "extra_fields": {
                            "affiliate_id": affiliate_id,
                            "affiliate_code": data.affiliate_code,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Affiliate created successfully",
                    data=[affiliate_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating affiliate: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating affiliate: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create affiliate: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_affiliate(
        data: UpdateAffiliateServiceWriteDto,
        affiliate_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateAffiliateServiceReadDto]:
        """Update an affiliate"""
        logger.info(
            f"Processing affiliate update: {affiliate_id}",
            extra={
                "extra_fields": {
                    "affiliate_id": affiliate_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_AFFILIATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (affiliate_id, tenant_id, org_id, bus_id),
                )
                existing_affiliate = cursor.fetchone()

                if not existing_affiliate:
                    raise ValueError("Affiliate not found")
                
                old_data = dict(existing_affiliate)

                # If code is being updated, check for duplicates
                if data.affiliate_code is not None and data.affiliate_code.upper() != old_data.get('affiliate_code'):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_AFFILIATES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND affiliate_code = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.affiliate_code.upper(), affiliate_id),
                    )
                    duplicate_code = cursor.fetchone()
                    if duplicate_code:
                        raise ValueError(f"Affiliate with code '{data.affiliate_code}' already exists")

                # Build update query dynamically
                update_fields = []
                params = []

                if data.affiliate_code is not None:
                    update_fields.append("affiliate_code = %s")
                    params.append(data.affiliate_code.upper())
                if data.affiliate_name is not None:
                    update_fields.append("affiliate_name = %s")
                    params.append(data.affiliate_name)
                if data.contact_email is not None:
                    update_fields.append("contact_email = %s")
                    params.append(data.contact_email)
                if data.contact_phone is not None:
                    update_fields.append("contact_phone = %s")
                    params.append(data.contact_phone)
                if data.commission_rate is not None:
                    update_fields.append("commission_rate = %s")
                    params.append(data.commission_rate)
                if data.commission_type is not None:
                    update_fields.append("commission_type = %s")
                    params.append(data.commission_type)
                if data.fixed_commission_amount is not None:
                    update_fields.append("fixed_commission_amount = %s")
                    params.append(data.fixed_commission_amount)
                if data.status is not None:
                    update_fields.append("status = %s")
                    params.append(data.status)
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
                params.extend([affiliate_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_AFFILIATES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_affiliate = cursor.fetchone()

                if not updated_affiliate:
                    raise ValueError("Failed to update affiliate")

                # Get affiliate with user fullnames
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_AFFILIATES_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    WHERE a.id = %s AND a.tenant_id = %s""",
                    (affiliate_id, tenant_id),
                )
                affiliate_with_users = cursor.fetchone()

                if affiliate_with_users:
                    affiliate_dict = dict(affiliate_with_users)
                    affiliate_dict['created_by'] = affiliate_dict.get('created_by') or None
                    affiliate_dict['updated_by'] = affiliate_dict.get('updated_by') or None
                    affiliate_dict['deleted_by'] = affiliate_dict.get('deleted_by') or None
                else:
                    affiliate_dict = dict(updated_affiliate)
                    affiliate_dict['created_by'] = None
                    affiliate_dict['updated_by'] = None
                    affiliate_dict['deleted_by'] = None

                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = affiliate_dict.get('applicable_to_locations')
                affiliate_dict['applicable_to_locations'] = AffiliatesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = affiliate_dict.get('applicable_to_products')
                affiliate_dict['applicable_to_products'] = AffiliatesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = affiliate_dict.get('applicable_to_product_metadata')
                affiliate_dict['applicable_to_product_metadata'] = AffiliatesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )

                affiliate_read = UpdateAffiliateServiceReadDto(**affiliate_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_AFFILIATES_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (affiliate_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(affiliate_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-affiliates",
                        resource_id=affiliate_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Affiliate {affiliate_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Affiliate updated successfully: {affiliate_id}")

                return Respons(
                    success=True,
                    detail="Affiliate updated successfully",
                    data=[affiliate_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating affiliate: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating affiliate: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update affiliate: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_affiliate(
        affiliate_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetAffiliateServiceReadDto]:
        """Get a single affiliate by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_AFFILIATES_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    WHERE a.id = %s AND a.tenant_id = %s AND a.org_id = %s 
                    AND a.bus_id = %s""",
                    (affiliate_id, tenant_id, org_id, bus_id),
                )
                affiliate = cursor.fetchone()

                if not affiliate:
                    return Respons(
                        success=False,
                        detail="Affiliate not found",
                        error="NOT_FOUND",
                    )

                affiliate_dict = dict(affiliate)
                affiliate_dict['created_by'] = affiliate_dict.get('created_by') or None
                affiliate_dict['updated_by'] = affiliate_dict.get('updated_by') or None
                affiliate_dict['deleted_by'] = affiliate_dict.get('deleted_by') or None
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = affiliate_dict.get('applicable_to_locations')
                affiliate_dict['applicable_to_locations'] = AffiliatesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = affiliate_dict.get('applicable_to_products')
                affiliate_dict['applicable_to_products'] = AffiliatesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = affiliate_dict.get('applicable_to_product_metadata')
                affiliate_dict['applicable_to_product_metadata'] = AffiliatesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )
                
                affiliate_read = GetAffiliateServiceReadDto(**affiliate_dict)

                return Respons(
                    success=True,
                    detail="Affiliate retrieved successfully",
                    data=[affiliate_read],
                )

        except Exception as e:
            logger.error(f"Error getting affiliate: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get affiliate: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_affiliate_by_code(
        affiliate_code: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetAffiliateServiceReadDto]:
        """Get an affiliate by code"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_AFFILIATES_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    WHERE a.affiliate_code = %s AND a.tenant_id = %s AND a.org_id = %s 
                    AND a.bus_id = %s""",
                    (affiliate_code.upper(), tenant_id, org_id, bus_id),
                )
                affiliate = cursor.fetchone()

                if not affiliate:
                    return Respons(
                        success=False,
                        detail="Affiliate not found",
                        error="NOT_FOUND",
                    )

                affiliate_dict = dict(affiliate)
                affiliate_dict['created_by'] = affiliate_dict.get('created_by') or None
                affiliate_dict['updated_by'] = affiliate_dict.get('updated_by') or None
                affiliate_dict['deleted_by'] = affiliate_dict.get('deleted_by') or None
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = affiliate_dict.get('applicable_to_locations')
                affiliate_dict['applicable_to_locations'] = AffiliatesService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                # Format applicable_to_products as objects with product_id and product_name
                applicable_product_ids = affiliate_dict.get('applicable_to_products')
                affiliate_dict['applicable_to_products'] = AffiliatesService._fetch_product_objects(
                    applicable_product_ids, tenant_id, org_id, bus_id, cursor
                )
                
                # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                applicable_metadata_ids = affiliate_dict.get('applicable_to_product_metadata')
                affiliate_dict['applicable_to_product_metadata'] = AffiliatesService._fetch_product_metadata_objects(
                    applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                )
                
                affiliate_read = GetAffiliateServiceReadDto(**affiliate_dict)

                return Respons(
                    success=True,
                    detail="Affiliate retrieved successfully",
                    data=[affiliate_read],
                )

        except Exception as e:
            logger.error(f"Error getting affiliate: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get affiliate: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_affiliates(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        is_active: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetAffiliatesServiceReadDto]]:
        """Get list of affiliates with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "a.tenant_id = %s",
                    "a.org_id = %s",
                    "a.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if is_active is not None:
                    where_conditions.append("a.is_active = %s")
                    params.append(is_active)
                if status:
                    where_conditions.append("a.status = %s")
                    params.append(status)
                if search:
                    where_conditions.append(
                        "(a.affiliate_code ILIKE %s OR a.affiliate_name ILIKE %s OR a.contact_email ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_AFFILIATES_TABLE} a WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get affiliates with user fullnames
                cursor.execute(
                    f"""SELECT a.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_AFFILIATES_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON a.updated_by = updater.id AND a.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON a.deleted_by = deleter.id AND a.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY a.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                affiliates = cursor.fetchall()

                affiliate_list = []
                for aff in affiliates:
                    aff_dict = dict(aff)
                    aff_dict['created_by'] = aff_dict.get('created_by') or None
                    aff_dict['updated_by'] = aff_dict.get('updated_by') or None
                    aff_dict['deleted_by'] = aff_dict.get('deleted_by') or None
                    
                    # Format applicable_to_locations as objects with location_id and location_name
                    applicable_location_ids = aff_dict.get('applicable_to_locations')
                    aff_dict['applicable_to_locations'] = AffiliatesService._fetch_location_objects(
                        applicable_location_ids, tenant_id, cursor
                    )
                    
                    # Format applicable_to_products as objects with product_id and product_name
                    applicable_product_ids = aff_dict.get('applicable_to_products')
                    aff_dict['applicable_to_products'] = AffiliatesService._fetch_product_objects(
                        applicable_product_ids, tenant_id, org_id, bus_id, cursor
                    )
                    
                    # Format applicable_to_product_metadata as objects with metadata_id, metadata_name, and metadata_type
                    applicable_metadata_ids = aff_dict.get('applicable_to_product_metadata')
                    aff_dict['applicable_to_product_metadata'] = AffiliatesService._fetch_product_metadata_objects(
                        applicable_metadata_ids, tenant_id, org_id, bus_id, cursor
                    )
                    
                    affiliate_list.append(GetAffiliatesServiceReadDto(**aff_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Affiliates retrieved successfully",
                    data=affiliate_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting affiliates: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get affiliates: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_affiliate(
        data: DeleteAffiliateServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteAffiliateServiceReadDto]:
        """Delete an affiliate"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get affiliate details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_AFFILIATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.affiliate_id, tenant_id, org_id, bus_id),
                )
                affiliate = cursor.fetchone()

                if not affiliate:
                    return Respons(
                        success=False,
                        detail="Affiliate not found",
                        error="NOT_FOUND",
                    )

                complete_old_data = dict(affiliate)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-affiliates",
                        resource_id=data.affiliate_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Affiliate {data.affiliate_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Delete
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_AFFILIATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.affiliate_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Affiliate deleted successfully",
                    data=[DeleteAffiliateServiceReadDto(
                        affiliate_id=data.affiliate_id,
                        message="Affiliate deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting affiliate: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete affiliate: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_affiliates_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetAffiliatesStatisticsServiceReadDto]:
        """Get affiliates statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_affiliates,
                        COUNT(CASE WHEN status = 'ACTIVE' AND is_active = TRUE THEN 1 END) as total_active,
                        COUNT(CASE WHEN status = 'INACTIVE' OR is_active = FALSE THEN 1 END) as total_inactive,
                        COALESCE(SUM(total_referrals), 0) as total_referrals,
                        COALESCE(SUM(total_conversions), 0) as total_conversions,
                        COALESCE(SUM(total_commission_earned), 0) as total_commission_earned,
                        COALESCE(SUM(total_commission_paid), 0) as total_commission_paid,
                        COALESCE(SUM(total_commission_earned - total_commission_paid), 0) as total_pending_commission
                    FROM {db_settings.MSG_AFFILIATES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id),
                )
                stats = cursor.fetchone()

                statistics = GetAffiliatesStatisticsServiceReadDto(
                    total_affiliates=int(stats['total_affiliates'] or 0),
                    total_active=int(stats['total_active'] or 0),
                    total_inactive=int(stats['total_inactive'] or 0),
                    total_referrals=int(stats['total_referrals'] or 0),
                    total_conversions=int(stats['total_conversions'] or 0),
                    total_commission_earned=float(stats['total_commission_earned'] or 0),
                    total_commission_paid=float(stats['total_commission_paid'] or 0),
                    total_pending_commission=float(stats['total_pending_commission'] or 0),
                )

                return Respons(
                    success=True,
                    detail="Affiliates statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting affiliates statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get affiliates statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

