from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.suppliers.suppliers_service import SuppliersService
from src.entities.suppliers.suppliers_write_dto import (
    CreateSupplierControllerWriteDto,
    UpdateSupplierControllerWriteDto,
    DeleteSupplierControllerWriteDto,
)
from src.entities.suppliers.suppliers_read_dto import (
    CreateSupplierControllerReadDto,
    UpdateSupplierControllerReadDto,
    DeleteSupplierControllerReadDto,
    GetSupplierControllerReadDto,
    GetSuppliersControllerReadDto,
    SupplierStatsOverviewReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

suppliers_router = APIRouter(prefix="/suppliers", tags=["Users Suppliers"])
logger = get_logger("suppliers")


# 1. Create Supplier
@suppliers_router.post("/add", response_model=Respons[CreateSupplierControllerReadDto])
def create_supplier(
    data: CreateSupplierControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new supplier"""
    with LogContext(
        "suppliers",
        "create_supplier",
        fullname=data.fullname,
    ):
        logger.info(
            "Processing create supplier request",
            extra={
                "extra_fields": {
                    "endpoint": "/suppliers/add",
                    "fullname": data.fullname,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-suppliers-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create supplier failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = SuppliersService.create_supplier(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Supplier created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/add",
                        "supplier_id": (
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
                f"Supplier creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Supplier
@suppliers_router.put("/update", response_model=Respons[UpdateSupplierControllerReadDto])
def update_supplier(
    data: UpdateSupplierControllerWriteDto,
    supplier_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a supplier"""
    with LogContext(
        "suppliers",
        "update_supplier",
        supplier_id=supplier_id,
    ):
        logger.info(
            "Processing update supplier request",
            extra={
                "extra_fields": {
                    "endpoint": "/suppliers/update",
                    "supplier_id": supplier_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-suppliers-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update supplier failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/update",
                        "supplier_id": supplier_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = SuppliersService.update_supplier(
            data=data,
            supplier_id=supplier_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Supplier updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/update",
                        "supplier_id": supplier_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Supplier update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/update",
                        "supplier_id": supplier_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Supplier
@suppliers_router.get("/get", response_model=Respons[GetSupplierControllerReadDto])
def get_supplier(
    supplier_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single supplier by ID"""
    with LogContext(
        "suppliers",
        "get_supplier",
        supplier_id=supplier_id,
    ):
        logger.info(
            "Processing get supplier request",
            extra={
                "extra_fields": {
                    "endpoint": "/suppliers/get",
                    "supplier_id": supplier_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-suppliers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get supplier failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/get",
                        "supplier_id": supplier_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = SuppliersService.get_supplier(
            supplier_id=supplier_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Supplier retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/get",
                        "supplier_id": supplier_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Supplier retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/get",
                        "supplier_id": supplier_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Suppliers (List)
@suppliers_router.get("/list", response_model=Respons[GetSuppliersControllerReadDto])
def get_suppliers(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by fullname, email, or contact"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of suppliers with filters and pagination"""
    with LogContext(
        "suppliers",
        "get_suppliers",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get suppliers request",
            extra={
                "extra_fields": {
                    "endpoint": "/suppliers/list",
                    "filters": {
                        "is_active": is_active,
                        "search": search,
                        "page": page,
                        "size": size,
                    },
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-suppliers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get suppliers failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = SuppliersService.get_suppliers(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            is_active=is_active,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Suppliers retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Suppliers retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Supplier
@suppliers_router.delete("/delete", response_model=Respons[DeleteSupplierControllerReadDto])
def delete_supplier(
    data: DeleteSupplierControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a supplier"""
    with LogContext(
        "suppliers",
        "delete_supplier",
        supplier_id=data.supplier_id if hasattr(data, "supplier_id") else "unknown",
    ):
        logger.info(
            "Processing delete supplier request",
            extra={
                "extra_fields": {
                    "endpoint": "/suppliers/delete",
                    "supplier_id": data.supplier_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-suppliers-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete supplier failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = SuppliersService.delete_supplier(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Supplier Stats
@suppliers_router.get("/stats", response_model=Respons[SupplierStatsOverviewReadDto])
def get_supplier_stats(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get supplier statistics: total, active, inactive, recently added"""
    with LogContext(
        "suppliers",
        "get_supplier_stats",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing supplier stats request",
            extra={
                "extra_fields": {
                    "endpoint": "/suppliers/stats",
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-suppliers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Supplier stats failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/suppliers/stats",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = SuppliersService.get_stats_overview(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result

