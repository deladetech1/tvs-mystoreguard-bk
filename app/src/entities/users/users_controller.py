from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService
from src.entities.users.users_service import UsersService
from src.entities.users.users_read_dto import (
    GetUsersControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

users_router = APIRouter(prefix="/users", tags=["Users"])
logger = get_logger("users")


# Get Users
@users_router.get("/list", response_model=Respons[GetUsersControllerReadDto])
def get_users(
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
):
    """Get list of all users for the tenant"""
    with LogContext(
        "users",
        "get_users",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get users request",
            extra={
                "extra_fields": {
                    "endpoint": "/users/list",
                    "tenant_id": current_user.data[0].tenant_id,
                    "is_active": is_active,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get users failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/users/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = UsersService.get_users(
            tenant_id=current_user.data[0].tenant_id,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Users retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/users/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Users retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/users/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

