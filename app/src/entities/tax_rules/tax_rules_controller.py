from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.tax_rules.tax_rules_service import TaxRulesService
from src.entities.tax_rules.tax_rules_write_dto import (
    CreateTaxRuleControllerWriteDto,
    UpdateTaxRuleControllerWriteDto,
    DeleteTaxRuleControllerWriteDto,
)
from src.entities.tax_rules.tax_rules_read_dto import (
    CreateTaxRuleControllerReadDto,
    UpdateTaxRuleControllerReadDto,
    GetTaxRuleControllerReadDto,
    GetTaxRulesControllerReadDto,
    DeleteTaxRuleControllerReadDto,
    GetTaxRuleStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

tax_rules_router = APIRouter(prefix="/tax-rules", tags=["Settings Tax Rules"])
logger = get_logger("tax_rules")


# 1. Create Tax Rule
@tax_rules_router.post("/add", response_model=Respons[CreateTaxRuleControllerReadDto])
def create_rule(
    data: CreateTaxRuleControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new tax rule"""
    with LogContext(
        "tax_rules",
        "create_rule",
        name=data.name,
        tax_id=data.tax_id,
        rule_type=data.rule_type,
    ):
        logger.info(
            "Processing create tax rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/tax-rules/add",
                    "name": data.name,
                    "tax_id": data.tax_id,
                    "rule_type": data.rule_type,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-tax-rule-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create tax rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxRulesService.create_rule(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Tax rule created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/add",
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
                f"Tax rule creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Tax Rule
@tax_rules_router.put("/update", response_model=Respons[UpdateTaxRuleControllerReadDto])
def update_rule(
    data: UpdateTaxRuleControllerWriteDto,
    rule_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a tax rule"""
    with LogContext(
        "tax_rules",
        "update_rule",
        rule_id=rule_id,
    ):
        logger.info(
            "Processing update tax rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/tax-rules/update",
                    "rule_id": rule_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-tax-rule-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update tax rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/update",
                        "rule_id": rule_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxRulesService.update_rule(
            data=data,
            rule_id=rule_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Tax rule updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/update",
                        "rule_id": rule_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax rule update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/update",
                        "rule_id": rule_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Tax Rule
@tax_rules_router.get("/get", response_model=Respons[GetTaxRuleControllerReadDto])
def get_rule(
    rule_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single tax rule by ID"""
    with LogContext(
        "tax_rules",
        "get_rule",
        rule_id=rule_id,
    ):
        logger.info(
            "Processing get tax rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/tax-rules/get",
                    "rule_id": rule_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-tax-rule-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get tax rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/get",
                        "rule_id": rule_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxRulesService.get_rule(
            rule_id=rule_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Tax rule retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/get",
                        "rule_id": rule_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax rule retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/get",
                        "rule_id": rule_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Tax Rules List
@tax_rules_router.get("/list", response_model=Respons[GetTaxRulesControllerReadDto])
def get_rules(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    tax_id: str = Query(None, description="Filter by tax ID"),
    rule_type: str = Query(None, description="Filter by rule type (PRODUCT, ALL_PRODUCTS, CATEGORY, TAG, BRAND, LABEL, LOCATION, SKU)"),
    is_active: bool = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of tax rules with pagination"""
    with LogContext(
        "tax_rules",
        "get_rules",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get tax rules request",
            extra={
                "extra_fields": {
                    "endpoint": "/tax-rules/list",
                    "page": page,
                    "size": size,
                    "tax_id": tax_id,
                    "rule_type": rule_type,
                    "is_active": is_active,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-tax-rule-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get tax rules failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxRulesService.get_rules(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            page=page,
            size=size,
            tax_id=tax_id,
            rule_type=rule_type,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Tax rules retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax rules retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Tax Rule
@tax_rules_router.delete("/delete", response_model=Respons[DeleteTaxRuleControllerReadDto])
def delete_rule(
    data: DeleteTaxRuleControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a tax rule (hard delete)"""
    with LogContext(
        "tax_rules",
        "delete_rule",
        rule_id=data.rule_id,
    ):
        logger.info(
            "Processing delete tax rule request",
            extra={
                "extra_fields": {
                    "endpoint": "/tax-rules/delete",
                    "rule_id": data.rule_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-tax-rule-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete tax rule failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxRulesService.delete_rule(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Tax rule deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/delete",
                        "rule_id": data.rule_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax rule deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/delete",
                        "rule_id": data.rule_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Get Tax Rules Statistics
@tax_rules_router.get("/statistics", response_model=Respons[GetTaxRuleStatisticsControllerReadDto])
def get_tax_rules_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get comprehensive statistics for tax rules"""
    with LogContext(
        "tax_rules",
        "get_tax_rules_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get tax rules statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/tax-rules/statistics",
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-tax-rule-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get tax rules statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxRulesService.get_tax_rules_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Tax rules statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax rules statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/tax-rules/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

