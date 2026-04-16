from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.return_policies.return_policies_service import ReturnPoliciesService
from src.entities.return_policies.return_policies_write_dto import (
    CreateReturnPolicyControllerWriteDto,
    UpdateReturnPolicyControllerWriteDto,
    DeleteReturnPolicyControllerWriteDto,
)
from src.entities.return_policies.return_policies_read_dto import (
    CreateReturnPolicyControllerReadDto,
    UpdateReturnPolicyControllerReadDto,
    GetReturnPolicyControllerReadDto,
    GetReturnPoliciesControllerReadDto,
    DeleteReturnPolicyControllerReadDto,
    GetReturnPolicyStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

return_policies_router = APIRouter(prefix="/return-policies", tags=["Settings Return Policies"])
logger = get_logger("return_policies")


# 1. Create Return Policy
@return_policies_router.post("/add", response_model=Respons[CreateReturnPolicyControllerReadDto])
def create_policy(
    data: CreateReturnPolicyControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new return policy"""
    with LogContext(
        "return_policies",
        "create_policy",
        name=data.name,
        policy_target_type=data.policy_target_type,
    ):
        logger.info(
            "Processing create return policy request",
            extra={
                "extra_fields": {
                    "endpoint": "/return-policies/add",
                    "name": data.name,
                    "policy_target_type": data.policy_target_type,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-return-policy-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create return policy failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ReturnPoliciesService.create_policy(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Return policy created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/add",
                        "policy_id": (
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
                f"Return policy creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Return Policy
@return_policies_router.put("/update", response_model=Respons[UpdateReturnPolicyControllerReadDto])
def update_policy(
    data: UpdateReturnPolicyControllerWriteDto,
    policy_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a return policy"""
    with LogContext(
        "return_policies",
        "update_policy",
        policy_id=policy_id,
    ):
        logger.info(
            "Processing update return policy request",
            extra={
                "extra_fields": {
                    "endpoint": "/return-policies/update",
                    "policy_id": policy_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-return-policy-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update return policy failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/update",
                        "policy_id": policy_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ReturnPoliciesService.update_policy(
            data=data,
            policy_id=policy_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Return policy updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/update",
                        "policy_id": policy_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Return policy update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/update",
                        "policy_id": policy_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Return Policy
@return_policies_router.get("/get", response_model=Respons[GetReturnPolicyControllerReadDto])
def get_policy(
    policy_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single return policy by ID"""
    with LogContext(
        "return_policies",
        "get_policy",
        policy_id=policy_id,
    ):
        logger.info(
            "Processing get return policy request",
            extra={
                "extra_fields": {
                    "endpoint": "/return-policies/get",
                    "policy_id": policy_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-return-policy-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get return policy failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/get",
                        "policy_id": policy_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ReturnPoliciesService.get_policy(
            policy_id=policy_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Return policy retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/get",
                        "policy_id": policy_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Return policy retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/get",
                        "policy_id": policy_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Return Policies List
@return_policies_router.get("/list", response_model=Respons[GetReturnPoliciesControllerReadDto])
def get_policies(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    policy_target_type: str = Query(None, description="Filter by policy target type"),
    is_active: bool = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of return policies with pagination"""
    with LogContext(
        "return_policies",
        "get_policies",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get return policies request",
            extra={
                "extra_fields": {
                    "endpoint": "/return-policies/list",
                    "page": page,
                    "size": size,
                    "policy_target_type": policy_target_type,
                    "is_active": is_active,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-return-policy-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get return policies failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ReturnPoliciesService.get_policies(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            page=page,
            size=size,
            policy_target_type=policy_target_type,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Return policies retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Return policies retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Return Policy
@return_policies_router.delete("/delete", response_model=Respons[DeleteReturnPolicyControllerReadDto])
def delete_policy(
    data: DeleteReturnPolicyControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a return policy"""
    with LogContext(
        "return_policies",
        "delete_policy",
        policy_id=data.policy_id,
    ):
        logger.info(
            "Processing delete return policy request",
            extra={
                "extra_fields": {
                    "endpoint": "/return-policies/delete",
                    "policy_id": data.policy_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-return-policy-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete return policy failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ReturnPoliciesService.delete_policy(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Get Return Policies Statistics
@return_policies_router.get("/statistics", response_model=Respons[GetReturnPolicyStatisticsControllerReadDto])
def get_return_policies_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get comprehensive statistics for return policies"""
    with LogContext(
        "return_policies",
        "get_return_policies_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get return policies statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/return-policies/statistics",
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-return-policy-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get return policies statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ReturnPoliciesService.get_return_policies_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Return policies statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Return policies statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/return-policies/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result
