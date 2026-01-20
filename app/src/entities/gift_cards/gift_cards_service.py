from typing import Optional, List
from datetime import date
from decimal import Decimal
from src.entities.gift_cards.gift_cards_read_dto import (
    CreateGiftCardServiceReadDto,
    UpdateGiftCardServiceReadDto,
    DeleteGiftCardServiceReadDto,
    GetGiftCardServiceReadDto,
    GetGiftCardsServiceReadDto,
    GetGiftCardsStatisticsServiceReadDto,
)
from src.entities.gift_cards.gift_cards_write_dto import (
    CreateGiftCardServiceWriteDto,
    UpdateGiftCardServiceWriteDto,
    DeleteGiftCardServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper
import secrets
import string

logger = get_logger("gift_cards_service")


class GiftCardsService:
    """Service class for gift cards operations"""

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
    def _generate_gift_card_code(length: int = 12) -> str:
        """Generate a random gift card code"""
        # Use uppercase letters and numbers, excluding ambiguous characters (0, O, I, 1)
        chars = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
        return ''.join(secrets.choice(chars) for _ in range(length))

    @staticmethod
    def create_gift_card(
        data: CreateGiftCardServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateGiftCardServiceReadDto]:
        """Create a new gift card"""
        logger.info(
            f"Processing gift card creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Generate gift card code if not provided
                gift_card_code = data.gift_card_code
                if not gift_card_code:
                    max_attempts = 100
                    for _ in range(max_attempts):
                        gift_card_code = f"GC-{GiftCardsService._generate_gift_card_code()}"
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND gift_card_code = %s""",
                            (tenant_id, org_id, bus_id, gift_card_code),
                        )
                        if not cursor.fetchone():
                            break
                    else:
                        return Respons(
                            success=False,
                            detail="Failed to generate unique gift card code",
                            error="CODE_GENERATION_FAILED",
                        )
                else:
                    # Check if code already exists
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND gift_card_code = %s""",
                        (tenant_id, org_id, bus_id, gift_card_code),
                    )
                    if cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Gift card with code '{gift_card_code}' already exists",
                            error="DUPLICATE_CODE",
                        )

                # Set current_balance automatically from initial_value
                current_balance = data.initial_value
                purchase_date_value = data.purchase_date if data.purchase_date else date.today()

                # Generate gift card ID
                gift_card_id = Helper.generate_unique_identifier(prefix="gfc")

                # Convert lists to PostgreSQL arrays
                applicable_locations = data.applicable_to_locations if data.applicable_to_locations else None

                # Insert into msg_gift_cards table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_GIFT_CARDS_TABLE}
                    (id, tenant_id, org_id, bus_id, gift_card_code, initial_value, current_balance, currency_id,
                     status, expiry_date, purchase_date, purchased_by_customer_id, purchased_by_user_id,
                     description, notes, applicable_to_locations, is_active, delete_status, 
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        gift_card_id, tenant_id, org_id, bus_id,
                        gift_card_code, data.initial_value, current_balance, data.currency_id,
                        data.status if data.status else 'ACTIVE',
                        data.expiry_date, purchase_date_value,
                        data.purchased_by_customer_id, created_by,  # purchased_by_user_id set to created_by
                        data.description, data.notes, applicable_locations,
                        data.is_active if data.is_active is not None else True, 'NOT_DELETED',
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                gift_card_result = cursor.fetchone()

                if not gift_card_result:
                    raise ValueError("Failed to create gift card")

                # Create transaction record for purchase
                transaction_id = Helper.generate_unique_identifier(prefix="gft")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_GIFT_CARD_TRANSACTIONS_TABLE}
                    (id, tenant_id, org_id, bus_id, gift_card_id, transaction_type,
                     amount, balance_before, balance_after, description, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        transaction_id, tenant_id, org_id, bus_id, gift_card_id, 'PURCHASE',
                        data.initial_value, Decimal('0'), current_balance,
                        f"Gift card purchased with initial value {data.initial_value}",
                        cdate, ctime, cdatetime, created_by
                    ),
                )

                # Get gift card with user fullnames, currency info, and customer fullname
                cursor.execute(
                    f"""SELECT g.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol,
                           cust.fullname as purchased_by_customer_fullname
                    FROM {db_settings.MSG_GIFT_CARDS_TABLE} g
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON g.created_by = creator.id AND g.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON g.updated_by = updater.id AND g.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON g.deleted_by = deleter.id AND g.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON g.currency_id = c.id AND g.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} cust ON g.purchased_by_customer_id = cust.id 
                        AND g.tenant_id = cust.tenant_id 
                        AND g.org_id = cust.org_id 
                        AND g.bus_id = cust.bus_id
                    WHERE g.id = %s AND g.tenant_id = %s""",
                    (gift_card_id, tenant_id),
                )
                gift_card_with_users = cursor.fetchone()

                if gift_card_with_users:
                    gift_card_dict = dict(gift_card_with_users)
                    gift_card_dict['created_by'] = gift_card_dict.get('created_by') or None
                    gift_card_dict['updated_by'] = gift_card_dict.get('updated_by') or None
                    gift_card_dict['deleted_by'] = gift_card_dict.get('deleted_by') or None
                    gift_card_dict['currency_name'] = gift_card_dict.get('currency_name') or None
                    gift_card_dict['currency_symbol'] = gift_card_dict.get('currency_symbol') or None
                    gift_card_dict['purchased_by_customer_fullname'] = gift_card_dict.get('purchased_by_customer_fullname') or None
                else:
                    gift_card_dict = dict(gift_card_result)
                    gift_card_dict['created_by'] = None
                    gift_card_dict['updated_by'] = None
                    gift_card_dict['deleted_by'] = None
                    gift_card_dict['currency_name'] = None
                    gift_card_dict['currency_symbol'] = None
                    gift_card_dict['purchased_by_customer_fullname'] = None

                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = gift_card_dict.get('applicable_to_locations')
                gift_card_dict['applicable_to_locations'] = GiftCardsService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )

                gift_card_read = CreateGiftCardServiceReadDto(**gift_card_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (gift_card_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(gift_card_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-gift-cards",
                        resource_id=gift_card_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Gift card {gift_card_code} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Gift card created successfully: {gift_card_id}",
                    extra={
                        "extra_fields": {
                            "gift_card_id": gift_card_id,
                            "gift_card_code": gift_card_code,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Gift card created successfully",
                    data=[gift_card_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating gift card: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating gift card: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create gift card: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_gift_card(
        data: UpdateGiftCardServiceWriteDto,
        gift_card_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateGiftCardServiceReadDto]:
        """Update a gift card"""
        logger.info(
            f"Processing gift card update: {gift_card_id}",
            extra={
                "extra_fields": {
                    "gift_card_id": gift_card_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (gift_card_id, tenant_id, org_id, bus_id),
                )
                existing_gift_card = cursor.fetchone()

                if not existing_gift_card:
                    raise ValueError("Gift card not found")
                
                old_data = dict(existing_gift_card)

                # If code is being updated, check for duplicates
                if data.gift_card_code is not None and data.gift_card_code != old_data.get('gift_card_code'):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND gift_card_code = %s AND id != %s""",
                        (tenant_id, org_id, bus_id, data.gift_card_code, gift_card_id),
                    )
                    duplicate_code = cursor.fetchone()
                    if duplicate_code:
                        raise ValueError(f"Gift card with code '{data.gift_card_code}' already exists")

                # Build update query dynamically
                update_fields = []
                params = []

                if data.gift_card_code is not None:
                    update_fields.append("gift_card_code = %s")
                    params.append(data.gift_card_code)
                if data.status is not None:
                    update_fields.append("status = %s")
                    params.append(data.status)
                if data.expiry_date is not None:
                    update_fields.append("expiry_date = %s")
                    params.append(data.expiry_date)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.notes is not None:
                    update_fields.append("notes = %s")
                    params.append(data.notes)
                if data.applicable_to_locations is not None:
                    update_fields.append("applicable_to_locations = %s")
                    params.append(data.applicable_to_locations)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([gift_card_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_GIFT_CARDS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_gift_card = cursor.fetchone()

                if not updated_gift_card:
                    raise ValueError("Failed to update gift card")

                # Get gift card with user fullnames, currency info, and customer fullname
                cursor.execute(
                    f"""SELECT g.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol,
                           cust.fullname as purchased_by_customer_fullname
                    FROM {db_settings.MSG_GIFT_CARDS_TABLE} g
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON g.created_by = creator.id AND g.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON g.updated_by = updater.id AND g.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON g.deleted_by = deleter.id AND g.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON g.currency_id = c.id AND g.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} cust ON g.purchased_by_customer_id = cust.id 
                        AND g.tenant_id = cust.tenant_id 
                        AND g.org_id = cust.org_id 
                        AND g.bus_id = cust.bus_id
                    WHERE g.id = %s AND g.tenant_id = %s""",
                    (gift_card_id, tenant_id),
                )
                gift_card_with_users = cursor.fetchone()

                if gift_card_with_users:
                    gift_card_dict = dict(gift_card_with_users)
                    gift_card_dict['created_by'] = gift_card_dict.get('created_by') or None
                    gift_card_dict['updated_by'] = gift_card_dict.get('updated_by') or None
                    gift_card_dict['deleted_by'] = gift_card_dict.get('deleted_by') or None
                    gift_card_dict['currency_name'] = gift_card_dict.get('currency_name') or None
                    gift_card_dict['currency_symbol'] = gift_card_dict.get('currency_symbol') or None
                    gift_card_dict['purchased_by_customer_fullname'] = gift_card_dict.get('purchased_by_customer_fullname') or None
                else:
                    gift_card_dict = dict(updated_gift_card)
                    gift_card_dict['created_by'] = None
                    gift_card_dict['updated_by'] = None
                    gift_card_dict['deleted_by'] = None
                    gift_card_dict['currency_name'] = None
                    gift_card_dict['currency_symbol'] = None
                    gift_card_dict['purchased_by_customer_fullname'] = None

                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = gift_card_dict.get('applicable_to_locations')
                gift_card_dict['applicable_to_locations'] = GiftCardsService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )

                gift_card_read = UpdateGiftCardServiceReadDto(**gift_card_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (gift_card_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(gift_card_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-gift-cards",
                        resource_id=gift_card_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Gift card {gift_card_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Gift card updated successfully: {gift_card_id}")

                return Respons(
                    success=True,
                    detail="Gift card updated successfully",
                    data=[gift_card_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating gift card: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating gift card: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update gift card: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_gift_card(
        gift_card_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetGiftCardServiceReadDto]:
        """Get a single gift card by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT g.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol,
                           cust.fullname as purchased_by_customer_fullname
                    FROM {db_settings.MSG_GIFT_CARDS_TABLE} g
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON g.created_by = creator.id AND g.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON g.updated_by = updater.id AND g.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON g.deleted_by = deleter.id AND g.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON g.currency_id = c.id AND g.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} cust ON g.purchased_by_customer_id = cust.id 
                        AND g.tenant_id = cust.tenant_id 
                        AND g.org_id = cust.org_id 
                        AND g.bus_id = cust.bus_id
                    WHERE g.id = %s AND g.tenant_id = %s AND g.org_id = %s 
                    AND g.bus_id = %s""",
                    (gift_card_id, tenant_id, org_id, bus_id),
                )
                gift_card = cursor.fetchone()

                if not gift_card:
                    return Respons(
                        success=False,
                        detail="Gift card not found",
                        error="NOT_FOUND",
                    )

                gift_card_dict = dict(gift_card)
                gift_card_dict['created_by'] = gift_card_dict.get('created_by') or None
                gift_card_dict['updated_by'] = gift_card_dict.get('updated_by') or None
                gift_card_dict['deleted_by'] = gift_card_dict.get('deleted_by') or None
                gift_card_dict['currency_name'] = gift_card_dict.get('currency_name') or None
                gift_card_dict['currency_symbol'] = gift_card_dict.get('currency_symbol') or None
                gift_card_dict['purchased_by_customer_fullname'] = gift_card_dict.get('purchased_by_customer_fullname') or None
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = gift_card_dict.get('applicable_to_locations')
                gift_card_dict['applicable_to_locations'] = GiftCardsService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                gift_card_read = GetGiftCardServiceReadDto(**gift_card_dict)

                return Respons(
                    success=True,
                    detail="Gift card retrieved successfully",
                    data=[gift_card_read],
                )

        except Exception as e:
            logger.error(f"Error getting gift card: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get gift card: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_gift_card_by_code(
        gift_card_code: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetGiftCardServiceReadDto]:
        """Get a gift card by code"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT g.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol,
                           cust.fullname as purchased_by_customer_fullname
                    FROM {db_settings.MSG_GIFT_CARDS_TABLE} g
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON g.created_by = creator.id AND g.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON g.updated_by = updater.id AND g.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON g.deleted_by = deleter.id AND g.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON g.currency_id = c.id AND g.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} cust ON g.purchased_by_customer_id = cust.id 
                        AND g.tenant_id = cust.tenant_id 
                        AND g.org_id = cust.org_id 
                        AND g.bus_id = cust.bus_id
                    WHERE g.gift_card_code = %s AND g.tenant_id = %s AND g.org_id = %s 
                    AND g.bus_id = %s""",
                    (gift_card_code, tenant_id, org_id, bus_id),
                )
                gift_card = cursor.fetchone()

                if not gift_card:
                    return Respons(
                        success=False,
                        detail="Gift card not found",
                        error="NOT_FOUND",
                    )

                gift_card_dict = dict(gift_card)
                gift_card_dict['created_by'] = gift_card_dict.get('created_by') or None
                gift_card_dict['updated_by'] = gift_card_dict.get('updated_by') or None
                gift_card_dict['deleted_by'] = gift_card_dict.get('deleted_by') or None
                gift_card_dict['currency_name'] = gift_card_dict.get('currency_name') or None
                gift_card_dict['currency_symbol'] = gift_card_dict.get('currency_symbol') or None
                gift_card_dict['purchased_by_customer_fullname'] = gift_card_dict.get('purchased_by_customer_fullname') or None
                
                # Format applicable_to_locations as objects with location_id and location_name
                applicable_location_ids = gift_card_dict.get('applicable_to_locations')
                gift_card_dict['applicable_to_locations'] = GiftCardsService._fetch_location_objects(
                    applicable_location_ids, tenant_id, cursor
                )
                
                gift_card_read = GetGiftCardServiceReadDto(**gift_card_dict)

                return Respons(
                    success=True,
                    detail="Gift card retrieved successfully",
                    data=[gift_card_read],
                )

        except Exception as e:
            logger.error(f"Error getting gift card: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get gift card: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_gift_cards(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        is_active: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetGiftCardsServiceReadDto]]:
        """Get list of gift cards with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "g.tenant_id = %s",
                    "g.org_id = %s",
                    "g.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if is_active is not None:
                    where_conditions.append("g.is_active = %s")
                    params.append(is_active)
                if status:
                    where_conditions.append("g.status = %s")
                    params.append(status)
                if search:
                    where_conditions.append(
                        "(g.gift_card_code ILIKE %s OR g.description ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_GIFT_CARDS_TABLE} g WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get gift cards with user fullnames, currency info, and customer fullname
                cursor.execute(
                    f"""SELECT g.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol,
                           cust.fullname as purchased_by_customer_fullname
                    FROM {db_settings.MSG_GIFT_CARDS_TABLE} g
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON g.created_by = creator.id AND g.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON g.updated_by = updater.id AND g.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON g.deleted_by = deleter.id AND g.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON g.currency_id = c.id AND g.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} cust ON g.purchased_by_customer_id = cust.id 
                        AND g.tenant_id = cust.tenant_id 
                        AND g.org_id = cust.org_id 
                        AND g.bus_id = cust.bus_id
                    WHERE {where_clause}
                    ORDER BY g.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                gift_cards = cursor.fetchall()

                gift_card_list = []
                for gc in gift_cards:
                    gc_dict = dict(gc)
                    gc_dict['created_by'] = gc_dict.get('created_by') or None
                    gc_dict['updated_by'] = gc_dict.get('updated_by') or None
                    gc_dict['deleted_by'] = gc_dict.get('deleted_by') or None
                    gc_dict['currency_name'] = gc_dict.get('currency_name') or None
                    gc_dict['currency_symbol'] = gc_dict.get('currency_symbol') or None
                    gc_dict['purchased_by_customer_fullname'] = gc_dict.get('purchased_by_customer_fullname') or None
                    
                    # Format applicable_to_locations as objects with location_id and location_name
                    applicable_location_ids = gc_dict.get('applicable_to_locations')
                    gc_dict['applicable_to_locations'] = GiftCardsService._fetch_location_objects(
                        applicable_location_ids, tenant_id, cursor
                    )
                    
                    gift_card_list.append(GetGiftCardsServiceReadDto(**gc_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Gift cards retrieved successfully",
                    data=gift_card_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting gift cards: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get gift cards: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_gift_card(
        data: DeleteGiftCardServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteGiftCardServiceReadDto]:
        """Delete a gift card"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get gift card details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.gift_card_id, tenant_id, org_id, bus_id),
                )
                gift_card = cursor.fetchone()

                if not gift_card:
                    return Respons(
                        success=False,
                        detail="Gift card not found",
                        error="NOT_FOUND",
                    )

                complete_old_data = dict(gift_card)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-gift-cards",
                        resource_id=data.gift_card_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Gift card {data.gift_card_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Delete
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.gift_card_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Gift card deleted successfully",
                    data=[DeleteGiftCardServiceReadDto(
                        gift_card_id=data.gift_card_id,
                        message="Gift card deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting gift card: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete gift card: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_gift_cards_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetGiftCardsStatisticsServiceReadDto]:
        """Get gift cards statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_gift_cards,
                        COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as total_active,
                        COUNT(CASE WHEN status = 'USED' THEN 1 END) as total_used,
                        COUNT(CASE WHEN status = 'EXPIRED' THEN 1 END) as total_expired,
                        COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as total_cancelled,
                        COALESCE(SUM(initial_value), 0) as total_initial_value,
                        COALESCE(SUM(current_balance), 0) as total_current_balance,
                        COALESCE(SUM(initial_value - current_balance), 0) as total_redeemed_value
                    FROM {db_settings.MSG_GIFT_CARDS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id),
                )
                stats = cursor.fetchone()

                statistics = GetGiftCardsStatisticsServiceReadDto(
                    total_gift_cards=int(stats['total_gift_cards'] or 0),
                    total_active=int(stats['total_active'] or 0),
                    total_used=int(stats['total_used'] or 0),
                    total_expired=int(stats['total_expired'] or 0),
                    total_cancelled=int(stats['total_cancelled'] or 0),
                    total_initial_value=float(stats['total_initial_value'] or 0),
                    total_current_balance=float(stats['total_current_balance'] or 0),
                    total_redeemed_value=float(stats['total_redeemed_value'] or 0),
                )

                return Respons(
                    success=True,
                    detail="Gift cards statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting gift cards statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get gift cards statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

