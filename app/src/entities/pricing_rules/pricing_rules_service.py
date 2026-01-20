from decimal import Decimal
from src.entities.pricing_rules.pricing_rules_read_dto import (
    CreatePricingRuleServiceReadDto,
    UpdatePricingRuleServiceReadDto,
    GetPricingRuleServiceReadDto,
    GetPricingRulesServiceReadDto,
    DeletePricingRuleServiceReadDto,
    GetPricingRuleStatisticsServiceReadDto,
)
from src.entities.pricing_rules.pricing_rules_write_dto import (
    CreatePricingRuleServiceWriteDto,
    UpdatePricingRuleServiceWriteDto,
    DeletePricingRuleServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("pricing_rules_service")


class PricingRulesService:
    """Service class for pricing rules operations"""

    @staticmethod
    def _get_rule_target_name_subquery() -> str:
        """Get SQL subquery to fetch rule_target_name based on rule_target_type"""
        return f"""
            CASE 
                WHEN r.rule_target_type = 'ALL_PRODUCTS' THEN 'All Products'
                WHEN r.rule_target_type = 'PRODUCT' THEN (
                    SELECT p.name 
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p 
                    WHERE p.id = r.rule_target_id 
                    AND p.tenant_id = r.tenant_id 
                    AND p.org_id = r.org_id 
                    AND p.bus_id = r.bus_id
                    LIMIT 1
                )
                WHEN r.rule_target_type = 'SKU' THEN (
                    SELECT p.name 
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p 
                    WHERE p.sku = r.rule_target_id 
                    AND p.tenant_id = r.tenant_id 
                    AND p.org_id = r.org_id 
                    AND p.bus_id = r.bus_id
                    LIMIT 1
                )
                WHEN r.rule_target_type = 'LOCATION' THEN (
                    SELECT l.loc_name 
                    FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l 
                    WHERE l.id = r.rule_target_id 
                    AND l.tenant_id = r.tenant_id
                    LIMIT 1
                )
                WHEN r.rule_target_type IN ('CATEGORY', 'TAG', 'BRAND', 'LABEL') THEN (
                    SELECT m.name 
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m 
                    WHERE m.id = r.rule_target_id 
                    AND m.tenant_id = r.tenant_id 
                    AND m.org_id = r.org_id 
                    AND m.bus_id = r.bus_id
                    LIMIT 1
                )
                ELSE NULL
            END as rule_target_name
        """

    @staticmethod
    def _validate_rule_target(
        cursor,
        rule_target_type: str,
        rule_target_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str
    ) -> tuple[bool, str]:
        """Validate rule target exists"""
        if rule_target_type == 'ALL_PRODUCTS':
            if rule_target_id:
                return False, "rule_target_id should be null for rule_target_type 'ALL_PRODUCTS'"
            return True, ""

        if not rule_target_id:
            return False, f"rule_target_id is required for rule_target_type '{rule_target_type}'"

        if rule_target_type == 'PRODUCT':
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND id = %s""",
                (tenant_id, org_id, bus_id, rule_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product with ID '{rule_target_id}' not found"
        
        elif rule_target_type == 'SKU':
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND sku = %s""",
                (tenant_id, org_id, bus_id, rule_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product with SKU '{rule_target_id}' not found"

        elif rule_target_type == 'LOCATION':
            cursor.execute(
                f"""SELECT id FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                WHERE tenant_id = %s AND id = %s""",
                (tenant_id, rule_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Location not found"

        elif rule_target_type in ['TAG', 'CATEGORY', 'BRAND', 'LABEL']:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND id = %s""",
                (tenant_id, org_id, bus_id, rule_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product metadata with ID '{rule_target_id}' not found"

        return True, ""

    @staticmethod
    def _validate_rule_data(data) -> tuple[bool, str]:
        """Validate rule data based on rule_category and rule_type"""
        # Validate PRICE_ADJUSTMENT rules
        if data.rule_category == 'PRICE_ADJUSTMENT':
            if data.rule_type in ['FIXED_PRICE', 'FIXED_AMOUNT', 'PRICE_DISCOUNT', 'PRICE_MARKUP']:
                if data.discount_value is None:
                    return False, f"discount_value is required for rule_type '{data.rule_type}'"
            elif data.rule_type in ['PERCENTAGE_DISCOUNT', 'PERCENTAGE_MARKUP']:
                if data.discount_percent is None:
                    return False, f"discount_percent is required for rule_type '{data.rule_type}'"
            elif data.rule_type in ['BUNDLE', 'BOGO', 'QUANTITY_BREAK']:
                return False, f"rule_type '{data.rule_type}' requires rule_category 'QUANTITY_BASED'"

        # Validate QUANTITY_BASED rules
        elif data.rule_category == 'QUANTITY_BASED':
            if data.rule_type not in ['BUNDLE', 'BOGO', 'QUANTITY_BREAK']:
                return False, f"rule_type '{data.rule_type}' requires rule_category 'PRICE_ADJUSTMENT'"
            
            if data.quantity_min is None and data.quantity_max is None:
                return False, "At least one of quantity_min or quantity_max is required for QUANTITY_BASED rules"

        # Validate time range
        if data.start_datetime and data.end_datetime:
            if data.start_datetime >= data.end_datetime:
                return False, "start_datetime must be before end_datetime"

        return True, ""

    @staticmethod
    def create_rule(
        data: CreatePricingRuleServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreatePricingRuleServiceReadDto]:
        """Create a new pricing rule"""
        logger.info(
            f"Processing pricing rule creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "name": data.name,
                    "rule_type": data.rule_type,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Validate rule data
                is_valid, error_msg = PricingRulesService._validate_rule_data(data)
                if not is_valid:
                    raise ValueError(error_msg)

                # Validate rule target
                is_valid, error_msg = PricingRulesService._validate_rule_target(
                    cursor, data.rule_target_type, data.rule_target_id,
                    tenant_id, org_id, bus_id
                )
                if not is_valid:
                    raise ValueError(error_msg)

                # Generate rule ID
                rule_id = Helper.generate_unique_identifier(prefix="prr")

                # Insert into msg_pricing_rule table
                logger.info(f"Inserting pricing rule {rule_id} into {db_settings.MSG_PRICING_RULES_TABLE}")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRICING_RULES_TABLE}
                    (id, tenant_id, org_id, bus_id, name, rule_category, rule_type,
                     rule_target_type, rule_target_id, quantity_min, quantity_max,
                     discount_value, discount_percent, free_qty, stops_other_rules,
                     priority, start_datetime, end_datetime, is_active,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        rule_id, tenant_id, org_id, bus_id,
                        data.name, data.rule_category, data.rule_type,
                        data.rule_target_type, data.rule_target_id,
                        data.quantity_min, data.quantity_max,
                        data.discount_value, data.discount_percent, data.free_qty,
                        data.stops_other_rules, data.priority,
                        data.start_datetime, data.end_datetime, data.is_active,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                rule_result = cursor.fetchone()

                if not rule_result:
                    raise ValueError("Failed to create pricing rule")
                
                logger.info(f"Pricing rule {rule_id} inserted successfully, rowcount: {cursor.rowcount}")

                # Get rule with user fullnames and rule_target_name
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {PricingRulesService._get_rule_target_name_subquery()}
                    FROM {db_settings.MSG_PRICING_RULES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE r.id = %s AND r.tenant_id = %s AND r.org_id = %s AND r.bus_id = %s""",
                    (rule_id, tenant_id, org_id, bus_id),
                )
                rule_with_users = cursor.fetchone()

                if rule_with_users:
                    if isinstance(rule_with_users, dict):
                        rule_dict = rule_with_users.copy()
                    else:
                        rule_dict = dict(rule_with_users)
                    rule_dict['created_by'] = rule_dict.get('created_by') or None
                    rule_dict['updated_by'] = rule_dict.get('updated_by') or None
                    rule_dict['deleted_by'] = rule_dict.get('deleted_by') or None
                else:
                    if isinstance(rule_result, dict):
                        rule_dict = rule_result.copy()
                    else:
                        rule_dict = dict(rule_result)
                    rule_dict['created_by'] = None
                    rule_dict['updated_by'] = None
                    rule_dict['deleted_by'] = None

                # Create DTO - wrap in try-except to catch validation errors
                try:
                    rule_read = CreatePricingRuleServiceReadDto(**rule_dict)
                except Exception as dto_err:
                    logger.error(f"Failed to create DTO: {dto_err}", exc_info=True)
                    logger.error(f"Rule dict keys: {list(rule_dict.keys()) if rule_dict else 'None'}")
                    logger.error(f"Rule dict: {rule_dict}")
                    raise ValueError(f"Failed to create response DTO: {str(dto_err)}")

                logger.info(
                    f"Pricing rule created successfully: {rule_id}",
                    extra={
                        "extra_fields": {
                            "rule_id": rule_id,
                            "name": data.name,
                            "rule_type": data.rule_type,
                        }
                    },
                )

                # Get complete data for activity log (before committing)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRICING_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (rule_id, tenant_id, org_id, bus_id),
                )
                complete_new_data_record = cursor.fetchone()
                complete_new_data = dict(complete_new_data_record) if complete_new_data_record else None

                # Log activity - use correct resource type name 'rt-pricing-rules' (with 's')
                if complete_new_data:
                    try:
                        # Create savepoint before activity logging
                        cursor.execute("SAVEPOINT before_activity_log")
                        try:
                            ActivityLogService.log_activity(
                                tenant_id=tenant_id,
                                resource_type="rt-pricing-rules",
                                resource_id=rule_id,
                                action="create",
                                old_data=None,
                                new_data=complete_new_data,
                                description=f"Pricing rule {rule_id} created successfully",
                                performed_by=created_by,
                                org_id=org_id,
                                bus_id=bus_id,
                                loc_id="",
                                cursor=cursor
                            )
                            # Release savepoint if successful
                            cursor.execute("RELEASE SAVEPOINT before_activity_log")
                        except Exception as log_err:
                            # Rollback to savepoint if activity logging fails
                            try:
                                cursor.execute("ROLLBACK TO SAVEPOINT before_activity_log")
                                logger.warning(f"Activity log failed (rolled back to savepoint): {log_err}")
                            except Exception as rollback_err:
                                logger.error(f"Failed to rollback to savepoint: {rollback_err}", exc_info=True)
                                # If we can't rollback to savepoint, the transaction will be aborted
                                # Re-raise to prevent commit
                                raise
                    except Exception as savepoint_err:
                        logger.warning(f"Failed to create savepoint for activity log: {savepoint_err}", exc_info=True)
                        # Don't re-raise - allow transaction to continue without activity log

                # Log that we're about to return and commit
                logger.info(f"About to return success response for rule {rule_id} - transaction should commit")

                # Return success - transaction will commit when context exits
                return Respons(
                    success=True,
                    detail="Pricing rule created successfully",
                    data=[rule_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating pricing rule: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating pricing rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create pricing rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_rule(
        data: UpdatePricingRuleServiceWriteDto,
        rule_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdatePricingRuleServiceReadDto]:
        """Update a pricing rule"""
        logger.info(
            f"Processing pricing rule update: {rule_id}",
            extra={
                "extra_fields": {
                    "rule_id": rule_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRICING_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (rule_id, tenant_id, org_id, bus_id),
                )
                existing_rule = cursor.fetchone()

                if not existing_rule:
                    raise ValueError("Pricing rule not found")
                
                # Store complete old data before update
                old_data = dict(existing_rule)

                # Determine final values for validation
                final_rule_category = data.rule_category if data.rule_category is not None else old_data.get('rule_category')
                final_rule_type = data.rule_type if data.rule_type is not None else old_data.get('rule_type')
                final_rule_target_type = data.rule_target_type if data.rule_target_type is not None else old_data.get('rule_target_type')
                final_rule_target_id = data.rule_target_id if data.rule_target_id is not None else old_data.get('rule_target_id')
                final_quantity_min = data.quantity_min if data.quantity_min is not None else old_data.get('quantity_min')
                final_quantity_max = data.quantity_max if data.quantity_max is not None else old_data.get('quantity_max')
                final_start_datetime = data.start_datetime if data.start_datetime is not None else old_data.get('start_datetime')
                final_end_datetime = data.end_datetime if data.end_datetime is not None else old_data.get('end_datetime')

                # Validate rule target if being updated
                if data.rule_target_type is not None or data.rule_target_id is not None:
                    is_valid, error_msg = PricingRulesService._validate_rule_target(
                        cursor, final_rule_target_type, final_rule_target_id,
                        tenant_id, org_id, bus_id
                    )
                    if not is_valid:
                        return Respons(
                            success=False,
                            detail=error_msg,
                            error="VALIDATION_ERROR",
                        )

                # Validate rule data if category or type is being updated
                if data.rule_category is not None or data.rule_type is not None:
                    # Create a temporary object for validation
                    from src.entities.pricing_rules.pricing_rules_base import PricingRuleBase
                    temp_data = PricingRuleBase(
                        name=old_data.get('name'),
                        rule_category=final_rule_category,
                        rule_type=final_rule_type,
                        rule_target_type=final_rule_target_type,
                        rule_target_id=final_rule_target_id,
                        quantity_min=final_quantity_min,
                        quantity_max=final_quantity_max,
                        discount_value=data.discount_value if data.discount_value is not None else old_data.get('discount_value'),
                        discount_percent=data.discount_percent if data.discount_percent is not None else old_data.get('discount_percent'),
                        free_qty=data.free_qty if data.free_qty is not None else old_data.get('free_qty'),
                        stops_other_rules=data.stops_other_rules if data.stops_other_rules is not None else old_data.get('stops_other_rules'),
                        priority=data.priority if data.priority is not None else old_data.get('priority'),
                        start_datetime=final_start_datetime,
                        end_datetime=final_end_datetime,
                    )
                    is_valid, error_msg = PricingRulesService._validate_rule_data(temp_data)
                    if not is_valid:
                        return Respons(
                            success=False,
                            detail=error_msg,
                            error="VALIDATION_ERROR",
                        )

                # Validate time range if being updated
                if data.start_datetime is not None or data.end_datetime is not None:
                    if final_start_datetime and final_end_datetime:
                        if final_start_datetime >= final_end_datetime:
                            return Respons(
                                success=False,
                                detail="start_datetime must be before end_datetime",
                                error="VALIDATION_ERROR",
                            )

                # Build update query dynamically
                update_fields = []
                params = []

                if data.name is not None:
                    update_fields.append("name = %s")
                    params.append(data.name)
                if data.rule_category is not None:
                    update_fields.append("rule_category = %s")
                    params.append(data.rule_category)
                if data.rule_type is not None:
                    update_fields.append("rule_type = %s")
                    params.append(data.rule_type)
                if data.rule_target_type is not None:
                    update_fields.append("rule_target_type = %s")
                    params.append(data.rule_target_type)
                if data.rule_target_id is not None:
                    update_fields.append("rule_target_id = %s")
                    params.append(data.rule_target_id)
                if data.quantity_min is not None:
                    update_fields.append("quantity_min = %s")
                    params.append(data.quantity_min)
                if data.quantity_max is not None:
                    update_fields.append("quantity_max = %s")
                    params.append(data.quantity_max)
                if data.discount_value is not None:
                    update_fields.append("discount_value = %s")
                    params.append(data.discount_value)
                if data.discount_percent is not None:
                    update_fields.append("discount_percent = %s")
                    params.append(data.discount_percent)
                if data.free_qty is not None:
                    update_fields.append("free_qty = %s")
                    params.append(data.free_qty)
                if data.stops_other_rules is not None:
                    update_fields.append("stops_other_rules = %s")
                    params.append(data.stops_other_rules)
                if data.priority is not None:
                    update_fields.append("priority = %s")
                    params.append(data.priority)
                if data.start_datetime is not None:
                    update_fields.append("start_datetime = %s")
                    params.append(data.start_datetime)
                if data.end_datetime is not None:
                    update_fields.append("end_datetime = %s")
                    params.append(data.end_datetime)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([rule_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PRICING_RULES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_rule = cursor.fetchone()

                if not updated_rule:
                    raise ValueError("Failed to update pricing rule")

                # Get rule with user fullnames and rule_target_name
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {PricingRulesService._get_rule_target_name_subquery()}
                    FROM {db_settings.MSG_PRICING_RULES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE r.id = %s AND r.tenant_id = %s""",
                    (rule_id, tenant_id),
                )
                rule_with_users = cursor.fetchone()

                if rule_with_users:
                    rule_dict = dict(rule_with_users)
                    rule_dict['created_by'] = rule_dict.get('created_by') or None
                    rule_dict['updated_by'] = rule_dict.get('updated_by') or None
                    rule_dict['deleted_by'] = rule_dict.get('deleted_by') or None
                else:
                    rule_dict = dict(updated_rule)
                    rule_dict['created_by'] = None
                    rule_dict['updated_by'] = None
                    rule_dict['deleted_by'] = None

                rule_read = UpdatePricingRuleServiceReadDto(**rule_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PRICING_RULES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (rule_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")
                    
                    complete_new_data = dict(complete_new_data_record)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-pricing-rules",
                        resource_id=rule_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Pricing rule {rule_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Pricing rule updated successfully: {rule_id}")

                return Respons(
                    success=True,
                    detail="Pricing rule updated successfully",
                    data=[rule_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating pricing rule: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating pricing rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update pricing rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_rule(
        rule_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPricingRuleServiceReadDto]:
        """Get a single pricing rule by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {PricingRulesService._get_rule_target_name_subquery()}
                    FROM {db_settings.MSG_PRICING_RULES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE r.id = %s AND r.tenant_id = %s AND r.org_id = %s 
                    AND r.bus_id = %s""",
                    (rule_id, tenant_id, org_id, bus_id),
                )
                rule = cursor.fetchone()

                if not rule:
                    return Respons(
                        success=False,
                        detail="Pricing rule not found",
                        error="NOT_FOUND",
                    )

                rule_dict = dict(rule)
                rule_dict['created_by'] = rule_dict.get('created_by') or None
                rule_dict['updated_by'] = rule_dict.get('updated_by') or None
                rule_dict['deleted_by'] = rule_dict.get('deleted_by') or None
                rule_read = GetPricingRuleServiceReadDto(**rule_dict)

                return Respons(
                    success=True,
                    detail="Pricing rule retrieved successfully",
                    data=[rule_read],
                )

        except Exception as e:
            logger.error(f"Error getting pricing rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get pricing rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_rules(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        page: int = 1,
        size: int = 10,
        rule_category: str = None,
        rule_type: str = None,
        rule_target_type: str = None,
        is_active: bool = None,
    ) -> Respons[list[GetPricingRulesServiceReadDto]]:
        """Get list of pricing rules with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "r.tenant_id = %s",
                    "r.org_id = %s",
                    "r.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if rule_category:
                    where_conditions.append("r.rule_category = %s")
                    params.append(rule_category)

                if rule_type:
                    where_conditions.append("r.rule_type = %s")
                    params.append(rule_type)

                if rule_target_type:
                    where_conditions.append("r.rule_target_type = %s")
                    params.append(rule_target_type)

                if is_active is not None:
                    where_conditions.append("r.is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_PRICING_RULES_TABLE} r WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get rules with user fullnames and rule_target_name
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {PricingRulesService._get_rule_target_name_subquery()}
                    FROM {db_settings.MSG_PRICING_RULES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY r.priority DESC, r.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                rules = cursor.fetchall()

                rule_list = []
                for r in rules:
                    r_dict = dict(r)
                    r_dict['created_by'] = r_dict.get('created_by') or None
                    r_dict['updated_by'] = r_dict.get('updated_by') or None
                    r_dict['deleted_by'] = r_dict.get('deleted_by') or None
                    rule_list.append(GetPricingRulesServiceReadDto(**r_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Pricing rules retrieved successfully",
                    data=rule_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting pricing rules: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get pricing rules: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_rule(
        data: DeletePricingRuleServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeletePricingRuleServiceReadDto]:
        """Delete pricing rule"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get rule before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRICING_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.rule_id, tenant_id, org_id, bus_id),
                )
                rule = cursor.fetchone()

                if not rule:
                    return Respons(
                        success=False,
                        detail="Pricing rule not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(rule)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-pricing-rules",
                        resource_id=data.rule_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Pricing rule {data.rule_id} deleted",
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
                    f"""DELETE FROM {db_settings.MSG_PRICING_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.rule_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Pricing rule deleted successfully",
                    data=[DeletePricingRuleServiceReadDto(
                        rule_id=data.rule_id,
                        message="Pricing rule deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting pricing rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete pricing rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_pricing_rules_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPricingRuleStatisticsServiceReadDto]:
        """Get comprehensive statistics for pricing rules"""
        try:
            with DatabaseManager.transaction() as cursor:
                params = (tenant_id, org_id, bus_id)
                
                # Get key statistics using a single query with conditional aggregation
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_rules,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as total_active,
                        COUNT(CASE WHEN is_active = FALSE THEN 1 END) as total_inactive,
                        
                        -- By category
                        COUNT(CASE WHEN rule_category = 'PRICE_ADJUSTMENT' THEN 1 END) as total_price_adjustment,
                        COUNT(CASE WHEN rule_category = 'QUANTITY_BASED' THEN 1 END) as total_quantity_based,
                        
                        -- By target type (most important)
                        COUNT(CASE WHEN rule_target_type = 'ALL_PRODUCTS' THEN 1 END) as total_target_all_products,
                        COUNT(CASE WHEN rule_target_type = 'CATEGORY' THEN 1 END) as total_target_category,
                        COUNT(CASE WHEN rule_target_type = 'LOCATION' THEN 1 END) as total_target_location,
                        
                        -- Additional statistics
                        COUNT(CASE WHEN stops_other_rules = TRUE THEN 1 END) as total_stops_other_rules,
                        AVG(priority) as average_priority
                    FROM {db_settings.MSG_PRICING_RULES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    params,
                )
                result = cursor.fetchone()

                if not result:
                    # If no results, return zeros
                    statistics = GetPricingRuleStatisticsServiceReadDto(
                        total_rules=0,
                        total_active=0,
                        total_inactive=0,
                        total_price_adjustment=0,
                        total_quantity_based=0,
                        total_target_all_products=0,
                        total_target_category=0,
                        total_target_location=0,
                        total_stops_other_rules=0,
                        average_priority=None,
                    )
                else:
                    avg_priority = result.get('average_priority')
                    if avg_priority is not None:
                        avg_priority = Decimal(str(avg_priority)).quantize(Decimal('0.01'))
                    
                    statistics = GetPricingRuleStatisticsServiceReadDto(
                        total_rules=result.get('total_rules', 0) or 0,
                        total_active=result.get('total_active', 0) or 0,
                        total_inactive=result.get('total_inactive', 0) or 0,
                        total_price_adjustment=result.get('total_price_adjustment', 0) or 0,
                        total_quantity_based=result.get('total_quantity_based', 0) or 0,
                        total_target_all_products=result.get('total_target_all_products', 0) or 0,
                        total_target_category=result.get('total_target_category', 0) or 0,
                        total_target_location=result.get('total_target_location', 0) or 0,
                        total_stops_other_rules=result.get('total_stops_other_rules', 0) or 0,
                        average_priority=avg_priority,
                    )

                logger.info(
                    f"Pricing rules statistics retrieved",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "total_rules": statistics.total_rules,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Pricing rules statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting pricing rules statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get pricing rules statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

