from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.affiliates.affiliates_service import AffiliatesService
from src.entities.affiliates.affiliates_write_dto import (
    CreateAffiliateControllerWriteDto,
    UpdateAffiliateControllerWriteDto,
    DeleteAffiliateControllerWriteDto,
)
from src.entities.affiliates.affiliates_read_dto import (
    CreateAffiliateControllerReadDto,
    UpdateAffiliateControllerReadDto,
    DeleteAffiliateControllerReadDto,
    GetAffiliateControllerReadDto,
    GetAffiliatesControllerReadDto,
    GetAffiliatesStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

affiliates_router = APIRouter(prefix="/affiliates", tags=["Affiliates"])
logger = get_logger("affiliates")


# 1. Create Affiliate
@affiliates_router.post("/add", response_model=Respons[CreateAffiliateControllerReadDto])
def create_affiliate(
    data: CreateAffiliateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new affiliate"""
    with LogContext(
        "affiliates",
        "create_affiliate",
        affiliate_code=data.affiliate_code,
    ):
        logger.info(
            "Processing create affiliate request",
            extra={
                "extra_fields": {
                    "endpoint": "/affiliates/add",
                    "affiliate_code": data.affiliate_code,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-affiliates-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create affiliate failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/affiliates/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AffiliatesService.create_affiliate(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Affiliate created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/affiliates/add",
                        "affiliate_id": (
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
                f"Affiliate creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/affiliates/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Affiliate
@affiliates_router.put("/update", response_model=Respons[UpdateAffiliateControllerReadDto])
def update_affiliate(
    data: UpdateAffiliateControllerWriteDto,
    affiliate_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update an affiliate"""
    with LogContext(
        "affiliates",
        "update_affiliate",
        affiliate_id=affiliate_id,
    ):
        logger.info(
            "Processing update affiliate request",
            extra={
                "extra_fields": {
                    "endpoint": "/affiliates/update",
                    "affiliate_id": affiliate_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-affiliates-update"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AffiliatesService.update_affiliate(
            data=data,
            affiliate_id=affiliate_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        return service_result


# 3. Get Affiliate by ID
@affiliates_router.get("/get", response_model=Respons[GetAffiliateControllerReadDto])
def get_affiliate(
    affiliate_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single affiliate by ID"""
    with LogContext(
        "affiliates",
        "get_affiliate",
        affiliate_id=affiliate_id,
    ):
        logger.info(
            "Processing get affiliate request",
            extra={
                "extra_fields": {
                    "endpoint": "/affiliates/get",
                    "affiliate_id": affiliate_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-affiliates-get"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AffiliatesService.get_affiliate(
            affiliate_id=affiliate_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result


# 4. Get Affiliate by Code
@affiliates_router.get("/get-by-code", response_model=Respons[GetAffiliateControllerReadDto])
def get_affiliate_by_code(
    affiliate_code: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get an affiliate by code"""
    with LogContext(
        "affiliates",
        "get_affiliate_by_code",
        affiliate_code=affiliate_code,
    ):
        logger.info(
            "Processing get affiliate by code request",
            extra={
                "extra_fields": {
                    "endpoint": "/affiliates/get-by-code",
                    "affiliate_code": affiliate_code,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-affiliates-get"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AffiliatesService.get_affiliate_by_code(
            affiliate_code=affiliate_code,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result


# 5. Get Affiliates (List)
@affiliates_router.get("/list", response_model=Respons[GetAffiliatesControllerReadDto])
def get_affiliates(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE, SUSPENDED)"),
    search: Optional[str] = Query(None, description="Search by affiliate code, name, or email"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of affiliates with filters and pagination"""
    with LogContext(
        "affiliates",
        "get_affiliates",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get affiliates request",
            extra={
                "extra_fields": {
                    "endpoint": "/affiliates/list",
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-affiliates-get"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AffiliatesService.get_affiliates(
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


# 6. Delete Affiliate
@affiliates_router.delete("/delete", response_model=Respons[DeleteAffiliateControllerReadDto])
def delete_affiliate(
    data: DeleteAffiliateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete an affiliate"""
    with LogContext(
        "affiliates",
        "delete_affiliate",
        affiliate_id=data.affiliate_id if hasattr(data, "affiliate_id") else "unknown",
    ):
        logger.info(
            "Processing delete affiliate request",
            extra={
                "extra_fields": {
                    "endpoint": "/affiliates/delete",
                    "affiliate_id": data.affiliate_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-affiliates-delete"]
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AffiliatesService.delete_affiliate(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 7. Get Affiliates Statistics
@affiliates_router.get("/statistics", response_model=Respons[GetAffiliatesStatisticsControllerReadDto])
def get_affiliates_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get affiliates statistics"""
    with LogContext(
        "affiliates",
        "get_affiliates_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get affiliates statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/affiliates/statistics",
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-affiliates-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get affiliates statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/affiliates/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AffiliatesService.get_affiliates_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result

