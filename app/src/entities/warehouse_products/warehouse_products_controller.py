from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.warehouse_products.warehouse_products_service import WarehouseProductsService
from src.entities.warehouse_products.warehouse_products_write_dto import (
    CreateWarehouseProductControllerWriteDto,
    UpdateWarehouseProductControllerWriteDto,
    DeleteWarehouseProductControllerWriteDto,
    PermanentDeleteWarehouseProductControllerWriteDto,
    ReverseBatchWarehouseProductControllerWriteDto,
    AddStockWarehouseProductControllerWriteDto,
)
from src.entities.warehouse_products.warehouse_products_read_dto import (
    CreateWarehouseProductControllerReadDto,
    UpdateWarehouseProductControllerReadDto,
    DeleteWarehouseProductControllerReadDto,
    PermanentDeleteWarehouseProductControllerReadDto,
    ReverseBatchWarehouseProductControllerReadDto,
    GetWarehouseProductControllerReadDto,
    GetWarehouseProductsControllerReadDto,
    GetWarehouseProductStatisticsControllerReadDto,
    AddStockWarehouseProductControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

warehouse_products_router = APIRouter(prefix="/warehouse-products", tags=["Warehouse Products"])
logger = get_logger("warehouse_products")


# 1. Create Store Product
@warehouse_products_router.post("/add", response_model=Respons[CreateWarehouseProductControllerReadDto])
def create_warehouse_product(
    data: CreateWarehouseProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new warehouse product with FIFO batch allocation"""
    with LogContext(
        "warehouse_products",
        "create_warehouse_product",
        product_id=data.product_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing create warehouse product request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/add",
                    "product_id": data.product_id,
                    "loc_id": org_bus_loc["loc_id"],
                    "current_qty": data.current_qty,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create warehouse product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.create_warehouse_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],  # Use loc_id from header
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse product created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/add",
                        "product_id": data.product_id,
                        "loc_id": org_bus_loc["loc_id"],
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse product creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Add Stock to Warehouse Product
@warehouse_products_router.post("/add-stock", response_model=Respons[AddStockWarehouseProductControllerReadDto])
def add_stock_warehouse_product(
    data: AddStockWarehouseProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Add stock to an existing warehouse product with FIFO batch allocation"""
    with LogContext(
        "warehouse_products",
        "add_stock_warehouse_product",
        product_id=data.product_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing add stock to warehouse product request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/add-stock",
                    "product_id": data.product_id,
                    "loc_id": org_bus_loc["loc_id"],
                    "qty": data.qty,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-create"]
        )

        if not is_authorized:
            logger.warning(
                "Add stock to warehouse product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/add-stock",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.add_stock_warehouse_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Stock added to warehouse product successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/add-stock",
                        "product_id": data.product_id,
                        "loc_id": org_bus_loc["loc_id"],
                        "qty": data.qty,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Add stock to warehouse product failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/add-stock",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Update Warehouse Product
@warehouse_products_router.put("/update", response_model=Respons[UpdateWarehouseProductControllerReadDto])
def update_warehouse_product(
    data: UpdateWarehouseProductControllerWriteDto,
    product_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a warehouse product"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "warehouse_products",
        "update_warehouse_product",
        loc_id=loc_id,
        product_id=product_id,
    ):
        logger.info(
            "Processing update warehouse product request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/update",
                    "loc_id": loc_id,
                    "product_id": product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update warehouse product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/update",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.update_warehouse_product(
            data=data,
            loc_id=loc_id,
            product_id=product_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse product updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/update",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse product update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/update",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Store Product
@warehouse_products_router.get("/get", response_model=Respons[GetWarehouseProductControllerReadDto])
def get_warehouse_product(
    product_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single warehouse product by location and product ID"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "warehouse_products",
        "get_warehouse_product",
        loc_id=loc_id,
        product_id=product_id,
    ):
        logger.info(
            "Processing get warehouse product request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/get",
                    "loc_id": loc_id,
                    "product_id": product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get warehouse product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/get",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.get_warehouse_product(
            loc_id=loc_id,
            product_id=product_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Warehouse product retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/get",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse product retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/get",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Store Products List
@warehouse_products_router.get("/list", response_model=Respons[GetWarehouseProductsControllerReadDto])
def get_warehouse_products(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by product name, description, location name, or barcode"),
    metadata_ids: Optional[List[str]] = Query(None, description="Filter by product metadata IDs (e.g. category, tag, brand). Product must have at least one of these metadata"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of warehouse products with filters and pagination"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "warehouse_products",
        "get_warehouse_products",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get warehouse products request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/list",
                    "filters": {
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "is_active": is_active,
                        "search": search,
                        "metadata_ids": metadata_ids,
                        "page": page,
                        "size": size,
                    },
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get warehouse products failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.get_warehouse_products(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            product_id=product_id,
            is_active=is_active,
            search=search,
            metadata_ids=metadata_ids,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Warehouse products retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse products retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Store Product
@warehouse_products_router.delete("/delete", response_model=Respons[DeleteWarehouseProductControllerReadDto])
def delete_warehouse_product(
    data: DeleteWarehouseProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a warehouse product"""
    with LogContext(
        "warehouse_products",
        "delete_warehouse_product",
        loc_id=org_bus_loc["loc_id"] if hasattr(data, "loc_id") else "unknown",
        product_id=data.product_id if hasattr(data, "product_id") else "unknown",
    ):
        logger.info(
            "Processing delete warehouse product request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/delete",
                    "loc_id": org_bus_loc["loc_id"],
                    "product_id": data.product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete warehouse product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.delete_warehouse_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Permanent Delete Warehouse Product
@warehouse_products_router.delete("/permanent-delete", response_model=Respons[PermanentDeleteWarehouseProductControllerReadDto])
def permanent_delete_warehouse_product(
    data: PermanentDeleteWarehouseProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a warehouse product from the database"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "warehouse_products",
        "permanent_delete_warehouse_product",
        loc_id=loc_id,
        product_id=data.product_id,
    ):
        logger.info(
            "Processing permanent delete warehouse product request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/permanent-delete",
                    "loc_id": loc_id,
                    "product_id": data.product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Permanent delete warehouse product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/permanent-delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.permanent_delete_warehouse_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse product permanently deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/permanent-delete",
                        "loc_id": loc_id,
                        "product_id": data.product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse product permanent deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/permanent-delete",
                        "loc_id": loc_id,
                        "product_id": data.product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Reverse Batch Warehouse Product
@warehouse_products_router.put("/reverse-batch", response_model=Respons[ReverseBatchWarehouseProductControllerReadDto])
def reverse_batch_warehouse_product(
    data: ReverseBatchWarehouseProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Reverse a batch allocation from a warehouse product"""
    with LogContext(
        "warehouse_products",
        "reverse_batch_warehouse_product",
        loc_id=data.loc_id if hasattr(data, "loc_id") else "unknown",
        product_id=data.product_id if hasattr(data, "product_id") else "unknown",
        batch_number=data.batch_number if hasattr(data, "batch_number") else "unknown",
    ):
        logger.info(
            "Processing reverse batch warehouse product request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/reverse-batch",
                    "loc_id": data.loc_id,
                    "product_id": data.product_id,
                    "batch_number": data.batch_number,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Reverse batch warehouse product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/reverse-batch",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.reverse_batch_warehouse_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Batch reversed successfully for warehouse product",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/reverse-batch",
                        "loc_id": data.loc_id,
                        "product_id": data.product_id,
                        "batch_number": data.batch_number,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Reverse batch warehouse product failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/reverse-batch",
                        "loc_id": data.loc_id,
                        "product_id": data.product_id,
                        "batch_number": data.batch_number,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 8. Get Warehouse Products Statistics
@warehouse_products_router.get("/statistics", response_model=Respons[GetWarehouseProductStatisticsControllerReadDto])
def get_warehouse_product_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get warehouse product statistics"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "warehouse_products",
        "get_warehouse_product_statistics",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=loc_id,
    ):
        logger.info(
            "Processing get warehouse product statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-products/statistics",
                    "loc_id": loc_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get warehouse product statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseProductsService.get_warehouse_product_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse product statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse product statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-products/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

