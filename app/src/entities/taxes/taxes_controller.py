from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.taxes.taxes_service import TaxesService
from src.entities.taxes.taxes_write_dto import (
    CreateTaxControllerWriteDto,
    UpdateTaxControllerWriteDto,
    DeleteTaxControllerWriteDto,
)
from src.entities.taxes.taxes_read_dto import (
    CreateTaxControllerReadDto,
    UpdateTaxControllerReadDto,
    GetTaxControllerReadDto,
    GetTaxesControllerReadDto,
    DeleteTaxControllerReadDto,
    GetTaxStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

taxes_router = APIRouter(prefix="/taxes", tags=["Settings Taxes"])
logger = get_logger("taxes")


# 1. Create Tax
@taxes_router.post("/add", response_model=Respons[CreateTaxControllerReadDto])
def create_tax(
    data: CreateTaxControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new tax"""
    with LogContext(
        "taxes",
        "create_tax",
        name=data.name,
        rate=data.rate,
    ):
        logger.info(
            "Processing create tax request",
            extra={
                "extra_fields": {
                    "endpoint": "/taxes/add",
                    "name": data.name,
                    "rate": data.rate,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-taxes-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create tax failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxesService.create_tax(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Tax created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/add",
                        "tax_id": (
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
                f"Tax creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Tax
@taxes_router.put("/update", response_model=Respons[UpdateTaxControllerReadDto])
def update_tax(
    data: UpdateTaxControllerWriteDto,
    tax_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a tax"""
    with LogContext(
        "taxes",
        "update_tax",
        tax_id=tax_id,
    ):
        logger.info(
            "Processing update tax request",
            extra={
                "extra_fields": {
                    "endpoint": "/taxes/update",
                    "tax_id": tax_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-taxes-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update tax failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/update",
                        "tax_id": tax_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxesService.update_tax(
            data=data,
            tax_id=tax_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Tax updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/update",
                        "tax_id": tax_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/update",
                        "tax_id": tax_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Tax
@taxes_router.get("/get", response_model=Respons[GetTaxControllerReadDto])
def get_tax(
    tax_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single tax by ID"""
    with LogContext(
        "taxes",
        "get_tax",
        tax_id=tax_id,
    ):
        logger.info(
            "Processing get tax request",
            extra={
                "extra_fields": {
                    "endpoint": "/taxes/get",
                    "tax_id": tax_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-taxes-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get tax failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/get",
                        "tax_id": tax_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxesService.get_tax(
            tax_id=tax_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Tax retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/get",
                        "tax_id": tax_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/get",
                        "tax_id": tax_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Taxes List
@taxes_router.get("/list", response_model=Respons[GetTaxesControllerReadDto])
def get_taxes(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    is_active: bool = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of taxes with pagination"""
    with LogContext(
        "taxes",
        "get_taxes",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get taxes request",
            extra={
                "extra_fields": {
                    "endpoint": "/taxes/list",
                    "page": page,
                    "size": size,
                    "is_active": is_active,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-taxes-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get taxes failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxesService.get_taxes(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            page=page,
            size=size,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Taxes retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Taxes retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Tax
@taxes_router.delete("/delete", response_model=Respons[DeleteTaxControllerReadDto])
def delete_tax(
    data: DeleteTaxControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a tax (hard delete)"""
    with LogContext(
        "taxes",
        "delete_tax",
        tax_id=data.tax_id,
    ):
        logger.info(
            "Processing delete tax request",
            extra={
                "extra_fields": {
                    "endpoint": "/taxes/delete",
                    "tax_id": data.tax_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-taxes-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete tax failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxesService.delete_tax(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Tax deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/delete",
                        "tax_id": data.tax_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Tax deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/delete",
                        "tax_id": data.tax_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Get Taxes Statistics
@taxes_router.get("/statistics", response_model=Respons[GetTaxStatisticsControllerReadDto])
def get_taxes_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get comprehensive statistics for taxes"""
    with LogContext(
        "taxes",
        "get_taxes_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get taxes statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/taxes/statistics",
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-taxes-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get taxes statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = TaxesService.get_taxes_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Taxes statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Taxes statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/taxes/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

