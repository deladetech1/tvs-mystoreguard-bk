from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService
from src.entities.currencies.currencies_service import CurrenciesService
from src.entities.currencies.currencies_read_dto import (
    GetCurrenciesSimpleControllerReadDto,
    GetCurrencySimpleControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

currencies_router = APIRouter(prefix="/currencies", tags=["Currencies"])
logger = get_logger("currencies")


# Get Currencies List
@currencies_router.get("/list", response_model=Respons[GetCurrenciesSimpleControllerReadDto])
def get_currencies(
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
):
    """Get list of all currencies for the tenant - returns id, name, code, symbol, decimal_places, currency_position, and is_default"""
    with LogContext(
        "currencies",
        "get_currencies",
        tenant_id=current_user.data[0].tenant_id,
    ):
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        required_permissions = ["permission-currency-get"]
        
        logger.info(
            "Processing get currencies request",
            extra={
                "extra_fields": {
                    "endpoint": "/currencies/list",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "is_active": is_active,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=required_permissions
        )

        if not is_authorized:
            # Get user's actual permissions for debugging
            user_permissions = AuthService.get_user_permissions(current_user.data)
            logger.warning(
                "Get currencies failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/currencies/list",
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "required_permissions": required_permissions,
                        "user_permissions": user_permissions,
                        "error": "Unauthorized access - missing required permission",
                        "status": "failed",
                        "message": f"User is missing required permission: {', '.join(required_permissions)}",
                    }
                },
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized access - missing required permission: {', '.join(required_permissions)}"
            )

        service_result = CurrenciesService.get_currencies(
            tenant_id=current_user.data[0].tenant_id,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Currencies retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/currencies/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Currencies retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/currencies/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# Get Currency (Single)
@currencies_router.get("/get", response_model=Respons[GetCurrencySimpleControllerReadDto])
def get_currency(
    currency_id: str = Query(..., description="Currency ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
):
    """Get a single currency by ID - returns id, name, code, symbol, decimal_places, currency_position, and is_default"""
    with LogContext(
        "currencies",
        "get_currency",
        tenant_id=current_user.data[0].tenant_id,
        currency_id=currency_id,
    ):
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        required_permissions = ["permission-currency-get"]
        
        logger.info(
            "Processing get currency request",
            extra={
                "extra_fields": {
                    "endpoint": "/currencies/get",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "currency_id": currency_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=required_permissions
        )

        if not is_authorized:
            # Get user's actual permissions for debugging
            user_permissions = AuthService.get_user_permissions(current_user.data)
            logger.warning(
                "Get currency failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/currencies/get",
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "currency_id": currency_id,
                        "required_permissions": required_permissions,
                        "user_permissions": user_permissions,
                        "error": "Unauthorized access - missing required permission",
                        "status": "failed",
                        "message": f"User is missing required permission: {', '.join(required_permissions)}",
                    }
                },
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized access - missing required permission: {', '.join(required_permissions)}"
            )

        service_result = CurrenciesService.get_currency(
            currency_id=currency_id,
            tenant_id=current_user.data[0].tenant_id,
        )

        if service_result.success:
            logger.info(
                "Currency retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/currencies/get",
                        "currency_id": currency_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Currency retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/currencies/get",
                        "currency_id": currency_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

