from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.pricing_rules.pricing_rules_service import PricingRulesService
from src.entities.pricing_rules.pricing_rules_write_dto import (
    CreatePricingRuleControllerWriteDto,
    UpdatePricingRuleControllerWriteDto,
    DeletePricingRuleControllerWriteDto,
)
from src.entities.pricing_rules.pricing_rules_read_dto import (
    CreatePricingRuleControllerReadDto,
    UpdatePricingRuleControllerReadDto,
    GetPricingRuleControllerReadDto,
    GetPricingRulesControllerReadDto,
    DeletePricingRuleControllerReadDto,
    GetPricingRuleStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

pricing_rules_router = APIRouter(prefix="/pricing-rules", tags=["Settings Pricing Rules"])
logger = get_logger("pricing_rules")


# 1. Create Pricing Rule
@pricing_rules_router.post("/add", response_model=Respons[CreatePricingRuleControllerReadDto])
def create_rule(
    data: CreatePricingRuleControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new pricing rule"""
    with LogContext(
        "pricing_rules",
        "create_rule",
        name=data.name,
        rule_type=data.rule_type,
    ):
        logger.info(
            "Processing create pricing rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/pricing-rules/add",
                    "name": data.name,
                    "rule_type": data.rule_type,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-pricing-rule-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create pricing rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PricingRulesService.create_rule(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Pricing rule created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/add",
                        "rule_id": (
                            service_result.data.id 
                            if service_result.data and hasattr(service_result.data, 'id')
                            else (service_result.data[0].id if isinstance(service_result.data, list) and service_result.data else None)
                        ),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Pricing rule creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Pricing Rule
@pricing_rules_router.put("/update", response_model=Respons[UpdatePricingRuleControllerReadDto])
def update_rule(
    data: UpdatePricingRuleControllerWriteDto,
    rule_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a pricing rule"""
    with LogContext(
        "pricing_rules",
        "update_rule",
        rule_id=rule_id,
    ):
        logger.info(
            "Processing update pricing rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/pricing-rules/update",
                    "rule_id": rule_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-pricing-rule-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update pricing rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/update",
                        "rule_id": rule_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PricingRulesService.update_rule(
            data=data,
            rule_id=rule_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Pricing rule updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/update",
                        "rule_id": rule_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Pricing rule update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/update",
                        "rule_id": rule_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Pricing Rule
@pricing_rules_router.get("/get", response_model=Respons[GetPricingRuleControllerReadDto])
def get_rule(
    rule_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single pricing rule by ID"""
    with LogContext(
        "pricing_rules",
        "get_rule",
        rule_id=rule_id,
    ):
        logger.info(
            "Processing get pricing rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/pricing-rules/get",
                    "rule_id": rule_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-pricing-rule-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get pricing rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/get",
                        "rule_id": rule_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PricingRulesService.get_rule(
            rule_id=rule_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Pricing rule retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/get",
                        "rule_id": rule_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Pricing rule retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/get",
                        "rule_id": rule_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Pricing Rules List
@pricing_rules_router.get("/list", response_model=Respons[GetPricingRulesControllerReadDto])
def get_rules(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    rule_category: str = Query(None, description="Filter by rule category (PRICE_ADJUSTMENT, QUANTITY_BASED)"),
    rule_type: str = Query(None, description="Filter by rule type"),
    rule_target_type: str = Query(None, description="Filter by rule target type"),
    is_active: bool = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of pricing rules with pagination"""
    with LogContext(
        "pricing_rules",
        "get_rules",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get pricing rules request",
            extra={
                "extra_fields": {
                    "endpoint": "/pricing-rules/list",
                    "page": page,
                    "size": size,
                    "rule_category": rule_category,
                    "rule_type": rule_type,
                    "rule_target_type": rule_target_type,
                    "is_active": is_active,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-pricing-rule-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get pricing rules failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PricingRulesService.get_rules(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            page=page,
            size=size,
            rule_category=rule_category,
            rule_type=rule_type,
            rule_target_type=rule_target_type,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Pricing rules retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Pricing rules retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Pricing Rule
@pricing_rules_router.delete("/delete", response_model=Respons[DeletePricingRuleControllerReadDto])
def delete_rule(
    data: DeletePricingRuleControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a pricing rule"""
    with LogContext(
        "pricing_rules",
        "delete_rule",
        rule_id=data.rule_id,
    ):
        logger.info(
            "Processing delete pricing rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/pricing-rules/delete",
                    "rule_id": data.rule_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-pricing-rule-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete pricing rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PricingRulesService.delete_rule(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Get Pricing Rules Statistics
@pricing_rules_router.get("/statistics", response_model=Respons[GetPricingRuleStatisticsControllerReadDto])
def get_pricing_rules_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get comprehensive statistics for pricing rules"""
    with LogContext(
        "pricing_rules",
        "get_pricing_rules_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get pricing rules statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/pricing-rules/statistics",
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-pricing-rule-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get pricing rules statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PricingRulesService.get_pricing_rules_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Pricing rules statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Pricing rules statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/pricing-rules/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

