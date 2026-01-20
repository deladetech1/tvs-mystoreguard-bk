from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.promo_codes.promo_codes_service import PromoCodesService
from src.entities.promo_codes.promo_codes_write_dto import (
    CreatePromoCodeControllerWriteDto,
    UpdatePromoCodeControllerWriteDto,
    DeletePromoCodeControllerWriteDto,
)
from src.entities.promo_codes.promo_codes_read_dto import (
    CreatePromoCodeControllerReadDto,
    UpdatePromoCodeControllerReadDto,
    DeletePromoCodeControllerReadDto,
    GetPromoCodeControllerReadDto,
    GetPromoCodesControllerReadDto,
    GetPromoCodesStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

promo_codes_router = APIRouter(prefix="/promo-codes", tags=["Promo Codes"])
logger = get_logger("promo_codes")


# 1. Create Promo Code
@promo_codes_router.post("/add", response_model=Respons[CreatePromoCodeControllerReadDto])
def create_promo_code(
    data: CreatePromoCodeControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new promo code"""
    with LogContext(
        "promo_codes",
        "create_promo_code",
        promo_code=data.promo_code,
    ):
        logger.info(
            "Processing create promo code request",
            extra={
                "extra_fields": {
                    "endpoint": "/promo-codes/add",
                    "promo_code": data.promo_code,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-promo-codes-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create promo code failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/promo-codes/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PromoCodesService.create_promo_code(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Promo code created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/promo-codes/add",
                        "promo_code_id": (
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
                f"Promo code creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/promo-codes/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Promo Code
@promo_codes_router.put("/update", response_model=Respons[UpdatePromoCodeControllerReadDto])
def update_promo_code(
    data: UpdatePromoCodeControllerWriteDto,
    promo_code_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a promo code"""
    with LogContext(
        "promo_codes",
        "update_promo_code",
        promo_code_id=promo_code_id,
    ):
        logger.info(
            "Processing update promo code request",
            extra={
                "extra_fields": {
                    "endpoint": "/promo-codes/update",
                    "promo_code_id": promo_code_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-promo-codes-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update promo code failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/promo-codes/update",
                        "promo_code_id": promo_code_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PromoCodesService.update_promo_code(
            data=data,
            promo_code_id=promo_code_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        return service_result


# 3. Get Promo Code by ID
@promo_codes_router.get("/get", response_model=Respons[GetPromoCodeControllerReadDto])
def get_promo_code(
    promo_code_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single promo code by ID"""
    with LogContext(
        "promo_codes",
        "get_promo_code",
        promo_code_id=promo_code_id,
    ):
        logger.info(
            "Processing get promo code request",
            extra={
                "extra_fields": {
                    "endpoint": "/promo-codes/get",
                    "promo_code_id": promo_code_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-promo-codes-get"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PromoCodesService.get_promo_code(
            promo_code_id=promo_code_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result


# 4. Get Promo Code by Code String
@promo_codes_router.get("/get-by-code", response_model=Respons[GetPromoCodeControllerReadDto])
def get_promo_code_by_code(
    promo_code: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a promo code by code string"""
    with LogContext(
        "promo_codes",
        "get_promo_code_by_code",
        promo_code=promo_code,
    ):
        logger.info(
            "Processing get promo code by code request",
            extra={
                "extra_fields": {
                    "endpoint": "/promo-codes/get-by-code",
                    "promo_code": promo_code,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-promo-codes-get"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PromoCodesService.get_promo_code_by_code(
            promo_code=promo_code,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result


# 5. Get Promo Codes (List)
@promo_codes_router.get("/list", response_model=Respons[GetPromoCodesControllerReadDto])
def get_promo_codes(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE, EXPIRED)"),
    search: Optional[str] = Query(None, description="Search by promo code or description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of promo codes with filters and pagination"""
    with LogContext(
        "promo_codes",
        "get_promo_codes",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get promo codes request",
            extra={
                "extra_fields": {
                    "endpoint": "/promo-codes/list",
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-promo-codes-get"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PromoCodesService.get_promo_codes(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            is_active=is_active,
            status=status,
            search=search,
            page=page,
            size=size,
        )

        return service_result


# 6. Delete Promo Code
@promo_codes_router.delete("/delete", response_model=Respons[DeletePromoCodeControllerReadDto])
def delete_promo_code(
    data: DeletePromoCodeControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a promo code"""
    with LogContext(
        "promo_codes",
        "delete_promo_code",
        promo_code_id=data.promo_code_id if hasattr(data, "promo_code_id") else "unknown",
    ):
        logger.info(
            "Processing delete promo code request",
            extra={
                "extra_fields": {
                    "endpoint": "/promo-codes/delete",
                    "promo_code_id": data.promo_code_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-promo-codes-delete"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PromoCodesService.delete_promo_code(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 7. Get Promo Codes Statistics
@promo_codes_router.get("/statistics", response_model=Respons[GetPromoCodesStatisticsControllerReadDto])
def get_promo_codes_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get promo codes statistics"""
    with LogContext(
        "promo_codes",
        "get_promo_codes_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get promo codes statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/promo-codes/statistics",
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-promo-codes-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get promo codes statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/promo-codes/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PromoCodesService.get_promo_codes_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result

