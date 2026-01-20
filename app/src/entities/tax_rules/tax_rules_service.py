from decimal import Decimal
from src.entities.tax_rules.tax_rules_read_dto import (
    CreateTaxRuleServiceReadDto,
    UpdateTaxRuleServiceReadDto,
    GetTaxRuleServiceReadDto,
    GetTaxRulesServiceReadDto,
    DeleteTaxRuleServiceReadDto,
    GetTaxRuleStatisticsServiceReadDto,
)
from src.entities.tax_rules.tax_rules_write_dto import (
    CreateTaxRuleServiceWriteDto,
    UpdateTaxRuleServiceWriteDto,
    DeleteTaxRuleServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("tax_rules_service")


class TaxRulesService:
    """Service class for tax rules operations"""

    @staticmethod
    def _get_rule_target_name_subquery() -> str:
        """Get SQL subquery to fetch rule_target_name based on rule_type"""
        return f"""
            CASE 
                WHEN r.rule_type = 'ALL_PRODUCTS' THEN NULL
                WHEN r.rule_type = 'PRODUCT' THEN (
                    SELECT p.name 
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p 
                    WHERE p.id = r.rule_target_id 
                    AND p.tenant_id = r.tenant_id 
                    AND p.org_id = r.org_id 
                    AND p.bus_id = r.bus_id
                    LIMIT 1
                )
                WHEN r.rule_type = 'SKU' THEN (
                    SELECT p.sku 
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p 
                    WHERE p.sku = r.rule_target_id 
                    AND p.tenant_id = r.tenant_id 
                    AND p.org_id = r.org_id 
                    AND p.bus_id = r.bus_id
                    LIMIT 1
                )
                WHEN r.rule_type = 'LOCATION' THEN (
                    SELECT l.loc_name 
                    FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l 
                    WHERE l.id = r.rule_target_id 
                    AND l.tenant_id = r.tenant_id
                    LIMIT 1
                )
                WHEN r.rule_type IN ('CATEGORY', 'TAG', 'BRAND', 'LABEL') THEN (
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
    def _validate_tax_exists(
        cursor,
        tax_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str
    ) -> tuple[bool, str]:
        """Validate tax exists"""
        cursor.execute(
            f"""SELECT id FROM {db_settings.MSG_TAXES_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
            AND id = %s""",
            (tenant_id, org_id, bus_id, tax_id),
        )
        tax = cursor.fetchone()
        if not tax:
            return False, f"Tax with ID '{tax_id}' not found"
        return True, ""

    @staticmethod
    def _validate_rule_target(
        cursor,
        rule_type: str,
        rule_target_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str
    ) -> tuple[bool, str]:
        """Validate rule target exists"""
        if rule_type == 'ALL_PRODUCTS':
            if rule_target_id:
                return False, "rule_target_id should be null for rule_type 'ALL_PRODUCTS'"
            return True, ""

        if not rule_target_id:
            return False, f"rule_target_id is required for rule_type '{rule_type}'"

        if rule_type == 'PRODUCT':
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND id = %s""",
                (tenant_id, org_id, bus_id, rule_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product with ID '{rule_target_id}' not found"
        
        elif rule_type == 'SKU':
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND sku = %s""",
                (tenant_id, org_id, bus_id, rule_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product with SKU '{rule_target_id}' not found"

        elif rule_type == 'LOCATION':
            cursor.execute(
                f"""SELECT id FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                WHERE tenant_id = %s AND id = %s""",
                (tenant_id, rule_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Location not found"

        elif rule_type in ['TAG', 'CATEGORY', 'BRAND', 'LABEL']:
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
    def create_rule(
        data: CreateTaxRuleServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateTaxRuleServiceReadDto]:
        """Create a new tax rule"""
        logger.info(
            f"Processing tax rule creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "name": data.name,
                    "tax_id": data.tax_id,
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
                # Validate tax exists
                is_valid, error_msg = TaxRulesService._validate_tax_exists(
                    cursor, data.tax_id, tenant_id, org_id, bus_id
                )
                if not is_valid:
                    raise ValueError(error_msg)

                # Validate rule target
                is_valid, error_msg = TaxRulesService._validate_rule_target(
                    cursor, data.rule_type, data.rule_target_id,
                    tenant_id, org_id, bus_id
                )
                if not is_valid:
                    raise ValueError(error_msg)

                # Generate rule ID
                rule_id = Helper.generate_unique_identifier(prefix="txr")

                # Insert into msg_tax_rule table
                logger.info(f"Inserting tax rule {rule_id} into {db_settings.MSG_TAX_RULES_TABLE}")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_TAX_RULES_TABLE}
                    (id, tenant_id, org_id, bus_id, name, description, tax_id, rule_type, rule_target_id, priority, is_active,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        rule_id, tenant_id, org_id, bus_id,
                        data.name, data.description, data.tax_id, data.rule_type, data.rule_target_id, data.priority, data.is_active,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                rule_result = cursor.fetchone()

                if not rule_result:
                    raise ValueError("Failed to create tax rule")
                
                logger.info(f"Tax rule {rule_id} inserted successfully, rowcount: {cursor.rowcount}")

                # Insert conditions if provided
                if data.conditions and len(data.conditions) > 0:
                    logger.info(f"Inserting {len(data.conditions)} conditions for tax rule {rule_id}")
                    for condition in data.conditions:
                        # Validate condition for TAX_REDUCTION type
                        if condition.condition_type == 'TAX_REDUCTION':
                            if condition.adjustment_value is None and condition.adjustment_percentage is None:
                                raise ValueError(
                                    f"For TAX_REDUCTION condition type, either adjustment_value or "
                                    f"adjustment_percentage must be provided"
                                )
                        
                        condition_id = Helper.generate_unique_identifier(prefix="txrc")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_TAX_RULE_CONDITIONS_TABLE}
                            (id, tenant_id, org_id, bus_id, name, description, tax_id, tax_rule_id, priority,
                             condition_type, condition, comparison_operator, comparison_value,
                             adjustment_value, adjustment_percentage, logical_operator,
                             cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id""",
                            (
                                condition_id, tenant_id, org_id, bus_id,
                                '', condition.description, data.tax_id, rule_id, condition.priority,
                                condition.condition_type, condition.condition, condition.comparison_operator,
                                condition.comparison_value, condition.adjustment_value, condition.adjustment_percentage,
                                condition.logical_operator,
                                cdate, ctime, cdatetime, created_by
                            ),
                        )
                        condition_result = cursor.fetchone()
                        if not condition_result:
                            raise ValueError(f"Failed to create condition for tax rule {rule_id}")
                        logger.info(f"Condition {condition_id} inserted successfully for tax rule {rule_id}")
                    
                    logger.info(f"All {len(data.conditions)} conditions inserted successfully for tax rule {rule_id}")

                # Get rule with user fullnames and rule_target_name
                rule_target_name_subquery = TaxRulesService._get_rule_target_name_subquery()
                cursor.execute(
                    f"""SELECT r.*,
                           {rule_target_name_subquery},
                           t.name as tax_name,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAX_RULES_TABLE} r
                    LEFT JOIN {db_settings.MSG_TAXES_TABLE} t ON r.tax_id = t.id AND r.tenant_id = t.tenant_id AND r.org_id = t.org_id AND r.bus_id = t.bus_id
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
                    rule_dict['rule_target_name'] = rule_dict.get('rule_target_name') or None
                    rule_dict['tax_name'] = rule_dict.get('tax_name') or None
                else:
                    if isinstance(rule_result, dict):
                        rule_dict = rule_result.copy()
                    else:
                        rule_dict = dict(rule_result)
                    rule_dict['created_by'] = None
                    rule_dict['updated_by'] = None
                    rule_dict['deleted_by'] = None
                    rule_dict['rule_target_name'] = None
                    rule_dict['tax_name'] = None

                # Create DTO
                try:
                    rule_read = CreateTaxRuleServiceReadDto(**rule_dict)
                except Exception as dto_err:
                    logger.error(f"Failed to create DTO: {dto_err}", exc_info=True)
                    logger.error(f"Rule dict keys: {list(rule_dict.keys()) if rule_dict else 'None'}")
                    logger.error(f"Rule dict: {rule_dict}")
                    raise ValueError(f"Failed to create response DTO: {str(dto_err)}")

                logger.info(
                    f"Tax rule created successfully: {rule_id}",
                    extra={
                        "extra_fields": {
                            "rule_id": rule_id,
                            "tax_id": data.tax_id,
                            "rule_type": data.rule_type,
                        }
                    },
                )

                # Get complete data for activity log (before committing)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_TAX_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (rule_id, tenant_id, org_id, bus_id),
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
                                resource_type="rt-tax-rules",
                                resource_id=rule_id,
                                action="create",
                                old_data=None,
                                new_data=complete_new_data,
                                description=f"Tax rule {rule_id} created successfully",
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

                logger.info(f"About to return success response for rule {rule_id} - transaction should commit")

                return Respons(
                    success=True,
                    detail="Tax rule created successfully",
                    data=[rule_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating tax rule: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating tax rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create tax rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_rule(
        data: UpdateTaxRuleServiceWriteDto,
        rule_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateTaxRuleServiceReadDto]:
        """Update a tax rule"""
        logger.info(
            f"Processing tax rule update: {rule_id}",
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
                    f"""SELECT * FROM {db_settings.MSG_TAX_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (rule_id, tenant_id, org_id, bus_id),
                )
                existing_rule = cursor.fetchone()

                if not existing_rule:
                    raise ValueError("Tax rule not found")
                
                # Store complete old data before update
                old_data = dict(existing_rule)

                # Determine final values for validation
                final_tax_id = data.tax_id if data.tax_id is not None else old_data.get('tax_id')
                final_rule_type = data.rule_type if data.rule_type is not None else old_data.get('rule_type')
                final_rule_target_id = data.rule_target_id if data.rule_target_id is not None else old_data.get('rule_target_id')

                # Validate tax exists if being updated
                if data.tax_id is not None:
                    is_valid, error_msg = TaxRulesService._validate_tax_exists(
                        cursor, final_tax_id, tenant_id, org_id, bus_id
                    )
                    if not is_valid:
                        return Respons(
                            success=False,
                            detail=error_msg,
                            error="VALIDATION_ERROR",
                        )

                # Validate rule target if being updated
                if data.rule_type is not None or data.rule_target_id is not None:
                    is_valid, error_msg = TaxRulesService._validate_rule_target(
                        cursor, final_rule_type, final_rule_target_id,
                        tenant_id, org_id, bus_id
                    )
                    if not is_valid:
                        return Respons(
                            success=False,
                            detail=error_msg,
                            error="VALIDATION_ERROR",
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
                if data.tax_id is not None:
                    update_fields.append("tax_id = %s")
                    params.append(data.tax_id)
                if data.rule_type is not None:
                    update_fields.append("rule_type = %s")
                    params.append(data.rule_type)
                if data.rule_target_id is not None:
                    update_fields.append("rule_target_id = %s")
                    params.append(data.rule_target_id)
                if data.priority is not None:
                    update_fields.append("priority = %s")
                    params.append(data.priority)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([rule_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_TAX_RULES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_rule = cursor.fetchone()

                if not updated_rule:
                    raise ValueError("Failed to update tax rule")

                # Handle conditions update if provided
                if data.conditions is not None:
                    logger.info(f"Updating conditions for tax rule {rule_id}")
                    
                    # Delete all existing conditions
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_TAX_RULE_CONDITIONS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND tax_rule_id = %s""",
                        (tenant_id, org_id, bus_id, rule_id),
                    )
                    deleted_count = cursor.rowcount
                    logger.info(f"Deleted {deleted_count} existing conditions for tax rule {rule_id}")
                    
                    # Insert new conditions if provided
                    if len(data.conditions) > 0:
                        logger.info(f"Inserting {len(data.conditions)} new conditions for tax rule {rule_id}")
                        cdate = Helper.current_date_time()["cdate"]
                        ctime = Helper.current_date_time()["ctime"]
                        cdatetime = Helper.current_date_time()["cdatetime"]
                        
                        # Use final_tax_id from the rule (either updated or existing)
                        final_tax_id_for_conditions = data.tax_id if data.tax_id is not None else old_data.get('tax_id')
                        
                        for condition in data.conditions:
                            # Validate condition for TAX_REDUCTION type
                            if condition.condition_type == 'TAX_REDUCTION':
                                if condition.adjustment_value is None and condition.adjustment_percentage is None:
                                    raise ValueError(
                                        f"For TAX_REDUCTION condition type, either adjustment_value or "
                                        f"adjustment_percentage must be provided"
                                    )
                            
                            condition_id = Helper.generate_unique_identifier(prefix="txrc")
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_TAX_RULE_CONDITIONS_TABLE}
                                (id, tenant_id, org_id, bus_id, name, description, tax_id, tax_rule_id, priority,
                                 condition_type, condition, comparison_operator, comparison_value,
                                 adjustment_value, adjustment_percentage, logical_operator,
                                 cdate, ctime, cdatetime, created_by, updated_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id""",
                                (
                                    condition_id, tenant_id, org_id, bus_id,
                                    '', condition.description, final_tax_id_for_conditions, rule_id, condition.priority,
                                    condition.condition_type, condition.condition, condition.comparison_operator,
                                    condition.comparison_value, condition.adjustment_value, condition.adjustment_percentage,
                                    condition.logical_operator,
                                    cdate, ctime, cdatetime, updated_by, updated_by
                                ),
                            )
                            condition_result = cursor.fetchone()
                            if not condition_result:
                                raise ValueError(f"Failed to create condition for tax rule {rule_id}")
                            logger.info(f"Condition {condition_id} inserted successfully for tax rule {rule_id}")
                        
                        logger.info(f"All {len(data.conditions)} conditions inserted successfully for tax rule {rule_id}")
                    else:
                        logger.info(f"Empty conditions list provided, all conditions removed for tax rule {rule_id}")

                # Get rule with user fullnames and rule_target_name
                rule_target_name_subquery = TaxRulesService._get_rule_target_name_subquery()
                cursor.execute(
                    f"""SELECT r.*,
                           {rule_target_name_subquery},
                           t.name as tax_name,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAX_RULES_TABLE} r
                    LEFT JOIN {db_settings.MSG_TAXES_TABLE} t ON r.tax_id = t.id AND r.tenant_id = t.tenant_id AND r.org_id = t.org_id AND r.bus_id = t.bus_id
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
                    rule_dict['rule_target_name'] = rule_dict.get('rule_target_name') or None
                    rule_dict['tax_name'] = rule_dict.get('tax_name') or None
                else:
                    rule_dict = dict(updated_rule)
                    rule_dict['created_by'] = None
                    rule_dict['updated_by'] = None
                    rule_dict['deleted_by'] = None
                    rule_dict['rule_target_name'] = None
                    rule_dict['tax_name'] = None

                rule_read = UpdateTaxRuleServiceReadDto(**rule_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_TAX_RULES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (rule_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")
                    
                    complete_new_data = dict(complete_new_data_record)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-tax-rules",
                        resource_id=rule_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Tax rule {rule_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Tax rule updated successfully: {rule_id}")

                return Respons(
                    success=True,
                    detail="Tax rule updated successfully",
                    data=[rule_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating tax rule: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating tax rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update tax rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_rule(
        rule_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetTaxRuleServiceReadDto]:
        """Get a single tax rule by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                rule_target_name_subquery = TaxRulesService._get_rule_target_name_subquery()
                cursor.execute(
                    f"""SELECT r.*,
                           {rule_target_name_subquery},
                           t.name as tax_name,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAX_RULES_TABLE} r
                    LEFT JOIN {db_settings.MSG_TAXES_TABLE} t ON r.tax_id = t.id AND r.tenant_id = t.tenant_id AND r.org_id = t.org_id AND r.bus_id = t.bus_id
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
                        detail="Tax rule not found",
                        error="NOT_FOUND",
                    )

                rule_dict = dict(rule)
                rule_dict['created_by'] = rule_dict.get('created_by') or None
                rule_dict['updated_by'] = rule_dict.get('updated_by') or None
                rule_dict['deleted_by'] = rule_dict.get('deleted_by') or None
                rule_dict['rule_target_name'] = rule_dict.get('rule_target_name') or None
                rule_dict['tax_name'] = rule_dict.get('tax_name') or None
                rule_read = GetTaxRuleServiceReadDto(**rule_dict)

                return Respons(
                    success=True,
                    detail="Tax rule retrieved successfully",
                    data=[rule_read],
                )

        except Exception as e:
            logger.error(f"Error getting tax rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get tax rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_rules(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        page: int = 1,
        size: int = 10,
        tax_id: str = None,
        rule_type: str = None,
        is_active: bool = None,
    ) -> Respons[list[GetTaxRulesServiceReadDto]]:
        """Get list of tax rules with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "r.tenant_id = %s",
                    "r.org_id = %s",
                    "r.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if tax_id:
                    where_conditions.append("r.tax_id = %s")
                    params.append(tax_id)

                if rule_type:
                    where_conditions.append("r.rule_type = %s")
                    params.append(rule_type)

                if is_active is not None:
                    where_conditions.append("r.is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_TAX_RULES_TABLE} r WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get rules with user fullnames and rule_target_name
                rule_target_name_subquery = TaxRulesService._get_rule_target_name_subquery()
                cursor.execute(
                    f"""SELECT r.*,
                           {rule_target_name_subquery},
                           t.name as tax_name,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_TAX_RULES_TABLE} r
                    LEFT JOIN {db_settings.MSG_TAXES_TABLE} t ON r.tax_id = t.id AND r.tenant_id = t.tenant_id AND r.org_id = t.org_id AND r.bus_id = t.bus_id
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
                    r_dict['rule_target_name'] = r_dict.get('rule_target_name') or None
                    r_dict['tax_name'] = r_dict.get('tax_name') or None
                    rule_list.append(GetTaxRulesServiceReadDto(**r_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Tax rules retrieved successfully",
                    data=rule_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting tax rules: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get tax rules: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_rule(
        data: DeleteTaxRuleServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteTaxRuleServiceReadDto]:
        """Delete tax rule (hard delete - no soft delete)"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get rule before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_TAX_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.rule_id, tenant_id, org_id, bus_id),
                )
                rule = cursor.fetchone()

                if not rule:
                    return Respons(
                        success=False,
                        detail="Tax rule not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(rule)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-tax-rules",
                        resource_id=data.rule_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Tax rule {data.rule_id} deleted",
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
                    f"""DELETE FROM {db_settings.MSG_TAX_RULES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.rule_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Tax rule deleted successfully",
                    data=[DeleteTaxRuleServiceReadDto(
                        rule_id=data.rule_id,
                        message="Tax rule deleted successfully",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting tax rule: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete tax rule: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_tax_rules_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetTaxRuleStatisticsServiceReadDto]:
        """Get comprehensive statistics for tax rules"""
        try:
            with DatabaseManager.transaction() as cursor:
                params = (tenant_id, org_id, bus_id)
                
                # Get key statistics using a single query with conditional aggregation
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_rules,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as total_active,
                        COUNT(CASE WHEN is_active = FALSE THEN 1 END) as total_inactive,
                        
                        -- By rule type
                        COUNT(CASE WHEN rule_type = 'PRODUCT' THEN 1 END) as total_product,
                        COUNT(CASE WHEN rule_type = 'ALL_PRODUCTS' THEN 1 END) as total_all_products,
                        COUNT(CASE WHEN rule_type = 'CATEGORY' THEN 1 END) as total_category,
                        COUNT(CASE WHEN rule_type = 'TAG' THEN 1 END) as total_tag,
                        COUNT(CASE WHEN rule_type = 'BRAND' THEN 1 END) as total_brand,
                        COUNT(CASE WHEN rule_type = 'LABEL' THEN 1 END) as total_label,
                        COUNT(CASE WHEN rule_type = 'LOCATION' THEN 1 END) as total_location,
                        COUNT(CASE WHEN rule_type = 'SKU' THEN 1 END) as total_sku,
                        
                        -- Priority statistics
                        AVG(priority) as average_priority,
                        MAX(priority) as highest_priority,
                        MIN(priority) as lowest_priority,
                        
                        -- Unique taxes count
                        COUNT(DISTINCT tax_id) as unique_taxes_count
                    FROM {db_settings.MSG_TAX_RULES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    params,
                )
                result = cursor.fetchone()

                if not result:
                    # If no results, return zeros
                    statistics = GetTaxRuleStatisticsServiceReadDto(
                        total_rules=0,
                        total_active=0,
                        total_inactive=0,
                        total_product=0,
                        total_all_products=0,
                        total_category=0,
                        total_tag=0,
                        total_brand=0,
                        total_label=0,
                        total_location=0,
                        total_sku=0,
                        average_priority=None,
                        highest_priority=None,
                        lowest_priority=None,
                        unique_taxes_count=0,
                    )
                else:
                    avg_priority = result.get('average_priority')
                    if avg_priority is not None:
                        avg_priority = Decimal(str(avg_priority)).quantize(Decimal('0.01'))
                    
                    highest_priority = result.get('highest_priority')
                    if highest_priority is not None:
                        highest_priority = int(highest_priority)
                    
                    lowest_priority = result.get('lowest_priority')
                    if lowest_priority is not None:
                        lowest_priority = int(lowest_priority)
                    
                    statistics = GetTaxRuleStatisticsServiceReadDto(
                        total_rules=result.get('total_rules', 0) or 0,
                        total_active=result.get('total_active', 0) or 0,
                        total_inactive=result.get('total_inactive', 0) or 0,
                        total_product=result.get('total_product', 0) or 0,
                        total_all_products=result.get('total_all_products', 0) or 0,
                        total_category=result.get('total_category', 0) or 0,
                        total_tag=result.get('total_tag', 0) or 0,
                        total_brand=result.get('total_brand', 0) or 0,
                        total_label=result.get('total_label', 0) or 0,
                        total_location=result.get('total_location', 0) or 0,
                        total_sku=result.get('total_sku', 0) or 0,
                        average_priority=avg_priority,
                        highest_priority=highest_priority,
                        lowest_priority=lowest_priority,
                        unique_taxes_count=result.get('unique_taxes_count', 0) or 0,
                    )

                logger.info(
                    f"Tax rules statistics retrieved",
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
                    detail="Tax rules statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting tax rules statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get tax rules statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

