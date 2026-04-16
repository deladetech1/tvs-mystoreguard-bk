from decimal import Decimal
from src.entities.return_policies.return_policies_read_dto import (
    CreateReturnPolicyServiceReadDto,
    UpdateReturnPolicyServiceReadDto,
    GetReturnPolicyServiceReadDto,
    GetReturnPoliciesServiceReadDto,
    DeleteReturnPolicyServiceReadDto,
    GetReturnPolicyStatisticsServiceReadDto,
)
from src.entities.return_policies.return_policies_write_dto import (
    CreateReturnPolicyServiceWriteDto,
    UpdateReturnPolicyServiceWriteDto,
    DeleteReturnPolicyServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("return_policies_service")


class ReturnPoliciesService:
    """Service class for return policies operations"""

    @staticmethod
    def _get_policy_target_name_subquery() -> str:
        """Get SQL subquery to fetch policy_target_name based on policy_target_type"""
        return f"""
            CASE
                WHEN r.policy_target_type = 'ALL_PRODUCTS' THEN 'All Products'
                WHEN r.policy_target_type = 'PRODUCT' THEN (
                    SELECT p.name
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    WHERE p.id = r.policy_target_id
                    AND p.tenant_id = r.tenant_id
                    AND p.org_id = r.org_id
                    AND p.bus_id = r.bus_id
                    LIMIT 1
                )
                WHEN r.policy_target_type = 'SKU' THEN (
                    SELECT p.name
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    WHERE p.sku = r.policy_target_id
                    AND p.tenant_id = r.tenant_id
                    AND p.org_id = r.org_id
                    AND p.bus_id = r.bus_id
                    LIMIT 1
                )
                WHEN r.policy_target_type = 'LOCATION' THEN (
                    SELECT l.loc_name
                    FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                    WHERE l.id = r.policy_target_id
                    AND l.tenant_id = r.tenant_id
                    LIMIT 1
                )
                WHEN r.policy_target_type IN ('CATEGORY', 'TAG', 'BRAND', 'LABEL') THEN (
                    SELECT m.name
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} m
                    WHERE m.id = r.policy_target_id
                    AND m.tenant_id = r.tenant_id
                    AND m.org_id = r.org_id
                    AND m.bus_id = r.bus_id
                    LIMIT 1
                )
                ELSE NULL
            END as policy_target_name
        """

    @staticmethod
    def _validate_policy_target(
        cursor,
        policy_target_type: str,
        policy_target_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str
    ) -> tuple[bool, str]:
        """Validate policy target exists"""
        if policy_target_type == 'ALL_PRODUCTS':
            if policy_target_id:
                return False, "policy_target_id should be null for policy_target_type 'ALL_PRODUCTS'"
            return True, ""

        if not policy_target_id:
            return False, f"policy_target_id is required for policy_target_type '{policy_target_type}'"

        if policy_target_type == 'PRODUCT':
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                AND id = %s""",
                (tenant_id, org_id, bus_id, policy_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product with ID '{policy_target_id}' not found"

        elif policy_target_type == 'SKU':
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                AND sku = %s""",
                (tenant_id, org_id, bus_id, policy_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product with SKU '{policy_target_id}' not found"

        elif policy_target_type == 'LOCATION':
            cursor.execute(
                f"""SELECT id FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                WHERE tenant_id = %s AND id = %s""",
                (tenant_id, policy_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Location not found"

        elif policy_target_type in ['TAG', 'CATEGORY', 'BRAND', 'LABEL']:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                AND id = %s""",
                (tenant_id, org_id, bus_id, policy_target_id),
            )
            target = cursor.fetchone()
            if not target:
                return False, f"Product metadata with ID '{policy_target_id}' not found"

        return True, ""

    @staticmethod
    def _validate_policy_data(data) -> tuple[bool, str]:
        """Validate return policy data"""
        # Validate time range
        if data.start_datetime and data.end_datetime:
            if data.start_datetime >= data.end_datetime:
                return False, "start_datetime must be before end_datetime"

        # Validate approval threshold makes sense
        if hasattr(data, 'approval_threshold_amount') and data.approval_threshold_amount is not None:
            if hasattr(data, 'approval_required') and data.approval_required is False:
                return False, "approval_threshold_amount requires approval_required to be true"

        return True, ""

    @staticmethod
    def create_policy(
        data: CreateReturnPolicyServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateReturnPolicyServiceReadDto]:
        """Create a new return policy"""
        logger.info(
            f"Processing return policy creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "name": data.name,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Validate policy data
                is_valid, error_msg = ReturnPoliciesService._validate_policy_data(data)
                if not is_valid:
                    raise ValueError(error_msg)

                # Validate policy target
                is_valid, error_msg = ReturnPoliciesService._validate_policy_target(
                    cursor, data.policy_target_type, data.policy_target_id,
                    tenant_id, org_id, bus_id
                )
                if not is_valid:
                    raise ValueError(error_msg)

                # Generate policy ID
                policy_id = Helper.generate_unique_identifier(prefix="rtp")

                # Insert into msg_return_policies table
                logger.info(f"Inserting return policy {policy_id} into {db_settings.MSG_RETURN_POLICIES_TABLE}")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_RETURN_POLICIES_TABLE}
                    (id, tenant_id, org_id, bus_id, name, description,
                     policy_target_type, policy_target_id,
                     return_window_days, condition_required, receipt_required, allow_expired_returns,
                     restocking_fee_percent, refund_method,
                     approval_required, approval_threshold_amount,
                     stops_other_policies, priority, start_datetime, end_datetime, is_active,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        policy_id, tenant_id, org_id, bus_id,
                        data.name, data.description,
                        data.policy_target_type, data.policy_target_id,
                        data.return_window_days, data.condition_required, data.receipt_required, data.allow_expired_returns,
                        float(data.restocking_fee_percent), data.refund_method,
                        data.approval_required, float(data.approval_threshold_amount) if data.approval_threshold_amount is not None else None,
                        data.stops_other_policies, data.priority,
                        data.start_datetime, data.end_datetime, data.is_active,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                policy_result = cursor.fetchone()

                if not policy_result:
                    raise ValueError("Failed to create return policy")

                logger.info(f"Return policy {policy_id} inserted successfully, rowcount: {cursor.rowcount}")

                # Get policy with user fullnames and policy_target_name
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {ReturnPoliciesService._get_policy_target_name_subquery()}
                    FROM {db_settings.MSG_RETURN_POLICIES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE r.id = %s AND r.tenant_id = %s AND r.org_id = %s AND r.bus_id = %s""",
                    (policy_id, tenant_id, org_id, bus_id),
                )
                policy_with_users = cursor.fetchone()

                if policy_with_users:
                    if isinstance(policy_with_users, dict):
                        policy_dict = policy_with_users.copy()
                    else:
                        policy_dict = dict(policy_with_users)
                    policy_dict['created_by'] = policy_dict.get('created_by') or None
                    policy_dict['updated_by'] = policy_dict.get('updated_by') or None
                    policy_dict['deleted_by'] = policy_dict.get('deleted_by') or None
                else:
                    if isinstance(policy_result, dict):
                        policy_dict = policy_result.copy()
                    else:
                        policy_dict = dict(policy_result)
                    policy_dict['created_by'] = None
                    policy_dict['updated_by'] = None
                    policy_dict['deleted_by'] = None

                # Create DTO
                try:
                    policy_read = CreateReturnPolicyServiceReadDto(**policy_dict)
                except Exception as dto_err:
                    logger.error(f"Failed to create DTO: {dto_err}", exc_info=True)
                    logger.error(f"Policy dict keys: {list(policy_dict.keys()) if policy_dict else 'None'}")
                    raise ValueError(f"Failed to create response DTO: {str(dto_err)}")

                logger.info(
                    f"Return policy created successfully: {policy_id}",
                    extra={
                        "extra_fields": {
                            "policy_id": policy_id,
                            "name": data.name,
                        }
                    },
                )

                # Get complete data for activity log
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (policy_id, tenant_id, org_id, bus_id),
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
                                resource_type="rt-return-policies",
                                resource_id=policy_id,
                                action="create",
                                old_data=None,
                                new_data=complete_new_data,
                                description=f"Return policy {policy_id} created successfully",
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

                logger.info(f"About to return success response for policy {policy_id} - transaction should commit")

                return Respons(
                    success=True,
                    detail="Return policy created successfully",
                    data=[policy_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating return policy: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating return policy: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create return policy: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_policy(
        data: UpdateReturnPolicyServiceWriteDto,
        policy_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateReturnPolicyServiceReadDto]:
        """Update a return policy"""
        logger.info(
            f"Processing return policy update: {policy_id}",
            extra={
                "extra_fields": {
                    "policy_id": policy_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s""",
                    (policy_id, tenant_id, org_id, bus_id),
                )
                existing_policy = cursor.fetchone()

                if not existing_policy:
                    raise ValueError("Return policy not found")

                # Store complete old data before update
                old_data = dict(existing_policy)

                # Determine final values for validation
                final_policy_target_type = data.policy_target_type if data.policy_target_type is not None else old_data.get('policy_target_type')
                final_policy_target_id = data.policy_target_id if data.policy_target_id is not None else old_data.get('policy_target_id')
                final_start_datetime = data.start_datetime if data.start_datetime is not None else old_data.get('start_datetime')
                final_end_datetime = data.end_datetime if data.end_datetime is not None else old_data.get('end_datetime')

                # Validate policy target if being updated
                if data.policy_target_type is not None or data.policy_target_id is not None:
                    is_valid, error_msg = ReturnPoliciesService._validate_policy_target(
                        cursor, final_policy_target_type, final_policy_target_id,
                        tenant_id, org_id, bus_id
                    )
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
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.policy_target_type is not None:
                    update_fields.append("policy_target_type = %s")
                    params.append(data.policy_target_type)
                if data.policy_target_id is not None:
                    update_fields.append("policy_target_id = %s")
                    params.append(data.policy_target_id)
                if data.return_window_days is not None:
                    update_fields.append("return_window_days = %s")
                    params.append(data.return_window_days)
                if data.condition_required is not None:
                    update_fields.append("condition_required = %s")
                    params.append(data.condition_required)
                if data.receipt_required is not None:
                    update_fields.append("receipt_required = %s")
                    params.append(data.receipt_required)
                if data.allow_expired_returns is not None:
                    update_fields.append("allow_expired_returns = %s")
                    params.append(data.allow_expired_returns)
                if data.restocking_fee_percent is not None:
                    update_fields.append("restocking_fee_percent = %s")
                    params.append(float(data.restocking_fee_percent))
                if data.refund_method is not None:
                    update_fields.append("refund_method = %s")
                    params.append(data.refund_method)
                if data.approval_required is not None:
                    update_fields.append("approval_required = %s")
                    params.append(data.approval_required)
                if data.approval_threshold_amount is not None:
                    update_fields.append("approval_threshold_amount = %s")
                    params.append(float(data.approval_threshold_amount))
                if data.stops_other_policies is not None:
                    update_fields.append("stops_other_policies = %s")
                    params.append(data.stops_other_policies)
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
                params.extend([policy_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_RETURN_POLICIES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_policy = cursor.fetchone()

                if not updated_policy:
                    raise ValueError("Failed to update return policy")

                # Get policy with user fullnames and policy_target_name
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {ReturnPoliciesService._get_policy_target_name_subquery()}
                    FROM {db_settings.MSG_RETURN_POLICIES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE r.id = %s AND r.tenant_id = %s""",
                    (policy_id, tenant_id),
                )
                policy_with_users = cursor.fetchone()

                if policy_with_users:
                    policy_dict = dict(policy_with_users)
                    policy_dict['created_by'] = policy_dict.get('created_by') or None
                    policy_dict['updated_by'] = policy_dict.get('updated_by') or None
                    policy_dict['deleted_by'] = policy_dict.get('deleted_by') or None
                else:
                    policy_dict = dict(updated_policy)
                    policy_dict['created_by'] = None
                    policy_dict['updated_by'] = None
                    policy_dict['deleted_by'] = None

                policy_read = UpdateReturnPolicyServiceReadDto(**policy_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (policy_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")

                    complete_new_data = dict(complete_new_data_record)

                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-return-policies",
                        resource_id=policy_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Return policy {policy_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Return policy updated successfully: {policy_id}")

                return Respons(
                    success=True,
                    detail="Return policy updated successfully",
                    data=[policy_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating return policy: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating return policy: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update return policy: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_policy(
        policy_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetReturnPolicyServiceReadDto]:
        """Get a single return policy by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {ReturnPoliciesService._get_policy_target_name_subquery()}
                    FROM {db_settings.MSG_RETURN_POLICIES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE r.id = %s AND r.tenant_id = %s AND r.org_id = %s
                    AND r.bus_id = %s""",
                    (policy_id, tenant_id, org_id, bus_id),
                )
                policy = cursor.fetchone()

                if not policy:
                    return Respons(
                        success=False,
                        detail="Return policy not found",
                        error="NOT_FOUND",
                    )

                policy_dict = dict(policy)
                policy_dict['created_by'] = policy_dict.get('created_by') or None
                policy_dict['updated_by'] = policy_dict.get('updated_by') or None
                policy_dict['deleted_by'] = policy_dict.get('deleted_by') or None
                policy_read = GetReturnPolicyServiceReadDto(**policy_dict)

                return Respons(
                    success=True,
                    detail="Return policy retrieved successfully",
                    data=[policy_read],
                )

        except Exception as e:
            logger.error(f"Error getting return policy: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get return policy: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_policies(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        page: int = 1,
        size: int = 10,
        policy_target_type: str = None,
        is_active: bool = None,
    ) -> Respons[list[GetReturnPoliciesServiceReadDto]]:
        """Get list of return policies with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "r.tenant_id = %s",
                    "r.org_id = %s",
                    "r.bus_id = %s",
                ]
                params = [tenant_id, org_id, bus_id]

                if policy_target_type:
                    where_conditions.append("r.policy_target_type = %s")
                    params.append(policy_target_type)

                if is_active is not None:
                    where_conditions.append("r.is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_RETURN_POLICIES_TABLE} r WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get policies with user fullnames and policy_target_name
                cursor.execute(
                    f"""SELECT r.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           {ReturnPoliciesService._get_policy_target_name_subquery()}
                    FROM {db_settings.MSG_RETURN_POLICIES_TABLE} r
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON r.updated_by = updater.id AND r.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON r.deleted_by = deleter.id AND r.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY r.priority DESC, r.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                policies = cursor.fetchall()

                policy_list = []
                for p in policies:
                    p_dict = dict(p)
                    p_dict['created_by'] = p_dict.get('created_by') or None
                    p_dict['updated_by'] = p_dict.get('updated_by') or None
                    p_dict['deleted_by'] = p_dict.get('deleted_by') or None
                    policy_list.append(GetReturnPoliciesServiceReadDto(**p_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Return policies retrieved successfully",
                    data=policy_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting return policies: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get return policies: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_policy(
        data: DeleteReturnPolicyServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteReturnPolicyServiceReadDto]:
        """Delete return policy"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get policy before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s""",
                    (data.policy_id, tenant_id, org_id, bus_id),
                )
                policy = cursor.fetchone()

                if not policy:
                    return Respons(
                        success=False,
                        detail="Return policy not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                complete_old_data = dict(policy)

                # Log activity before deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-return-policies",
                        resource_id=data.policy_id,
                        action="delete",
                        old_data=complete_old_data,
                        new_data=None,
                        description=f"Return policy {data.policy_id} deleted",
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
                    f"""DELETE FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.policy_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Return policy deleted successfully",
                    data=[DeleteReturnPolicyServiceReadDto(
                        policy_id=data.policy_id,
                        message="Return policy deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting return policy: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete return policy: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_return_policies_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetReturnPolicyStatisticsServiceReadDto]:
        """Get comprehensive statistics for return policies"""
        try:
            with DatabaseManager.transaction() as cursor:
                params = (tenant_id, org_id, bus_id)

                # Get key statistics using a single query with conditional aggregation
                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_policies,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as total_active,
                        COUNT(CASE WHEN is_active = FALSE THEN 1 END) as total_inactive,

                        -- By target type
                        COUNT(CASE WHEN policy_target_type = 'ALL_PRODUCTS' THEN 1 END) as total_target_all_products,
                        COUNT(CASE WHEN policy_target_type = 'CATEGORY' THEN 1 END) as total_target_category,
                        COUNT(CASE WHEN policy_target_type = 'PRODUCT' THEN 1 END) as total_target_product,
                        COUNT(CASE WHEN policy_target_type = 'LOCATION' THEN 1 END) as total_target_location,

                        -- By return window
                        COUNT(CASE WHEN return_window_days = 0 THEN 1 END) as total_non_returnable,
                        COUNT(CASE WHEN restocking_fee_percent > 0 THEN 1 END) as total_with_restocking_fee,
                        COUNT(CASE WHEN approval_required = TRUE THEN 1 END) as total_approval_required,

                        -- Additional statistics
                        COUNT(CASE WHEN stops_other_policies = TRUE THEN 1 END) as total_stops_other_policies,
                        AVG(priority) as average_priority,
                        AVG(return_window_days) as average_return_window_days
                    FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    params,
                )
                result = cursor.fetchone()

                if not result:
                    statistics = GetReturnPolicyStatisticsServiceReadDto(
                        total_policies=0,
                        total_active=0,
                        total_inactive=0,
                        total_target_all_products=0,
                        total_target_category=0,
                        total_target_product=0,
                        total_target_location=0,
                        total_non_returnable=0,
                        total_with_restocking_fee=0,
                        total_approval_required=0,
                        total_stops_other_policies=0,
                        average_priority=None,
                        average_return_window_days=None,
                    )
                else:
                    avg_priority = result.get('average_priority')
                    if avg_priority is not None:
                        avg_priority = Decimal(str(avg_priority)).quantize(Decimal('0.01'))

                    avg_return_window = result.get('average_return_window_days')
                    if avg_return_window is not None:
                        avg_return_window = Decimal(str(avg_return_window)).quantize(Decimal('0.01'))

                    statistics = GetReturnPolicyStatisticsServiceReadDto(
                        total_policies=result.get('total_policies', 0) or 0,
                        total_active=result.get('total_active', 0) or 0,
                        total_inactive=result.get('total_inactive', 0) or 0,
                        total_target_all_products=result.get('total_target_all_products', 0) or 0,
                        total_target_category=result.get('total_target_category', 0) or 0,
                        total_target_product=result.get('total_target_product', 0) or 0,
                        total_target_location=result.get('total_target_location', 0) or 0,
                        total_non_returnable=result.get('total_non_returnable', 0) or 0,
                        total_with_restocking_fee=result.get('total_with_restocking_fee', 0) or 0,
                        total_approval_required=result.get('total_approval_required', 0) or 0,
                        total_stops_other_policies=result.get('total_stops_other_policies', 0) or 0,
                        average_priority=avg_priority,
                        average_return_window_days=avg_return_window,
                    )

                return Respons(
                    success=True,
                    detail="Return policy statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting return policy statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get return policy statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )
