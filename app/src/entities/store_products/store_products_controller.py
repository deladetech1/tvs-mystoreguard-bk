from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.store_products.store_products_service import StoreProductsService
from src.entities.store_products.store_products_write_dto import (
    CreateStoreProductControllerWriteDto,
    UpdateStoreProductControllerWriteDto,
    DeleteStoreProductControllerWriteDto,
    PermanentDeleteStoreProductControllerWriteDto,
    ReverseBatchStoreProductControllerWriteDto,
    AddStockStoreProductControllerWriteDto,
)
from src.entities.store_products.store_products_read_dto import (
    BulkCreateStoreProductControllerReadDto,
    UpdateStoreProductControllerReadDto,
    DeleteStoreProductControllerReadDto,
    PermanentDeleteStoreProductControllerReadDto,
    ReverseBatchStoreProductControllerReadDto,
    GetStoreProductControllerReadDto,
    GetStoreProductsControllerReadDto,
    GetStoreProductStatisticsControllerReadDto,
    AddStockStoreProductControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

store_products_router = APIRouter(prefix="/store-products", tags=["Store Products"])
logger = get_logger("store_products")


# 1. Create Store Products (one or more)
@store_products_router.post("/add", response_model=Respons[BulkCreateStoreProductControllerReadDto])
def create_store_products(
    data: List[CreateStoreProductControllerWriteDto],
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create one or more store products with FIFO batch allocation.

    Accepts an array of items so multiple products can be added to a store in a
    single request. Pass a single object in an array to add just one. Each item is
    processed independently (best-effort): items that succeed are saved even if
    others fail, and the response carries a per-item result for every item.
    """
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_products",
        "create_store_products",
        item_count=len(data),
        product_ids=[item.product_id for item in data],
        loc_id=loc_id,
    ):
        logger.info(
            "Processing create store products request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/add",
                    "item_count": len(data),
                    "product_ids": [item.product_id for item in data],
                    "loc_id": loc_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create store products failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.create_store_products(
            items=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,  # Use loc_id from header
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            succeeded = sum(1 for item in (service_result.data or []) if item.success)
            logger.info(
                "Store products processed successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/add",
                        "item_count": len(data),
                        "succeeded": succeeded,
                        "loc_id": loc_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store products creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Add Stock to Store Product
@store_products_router.post("/add-stock", response_model=Respons[AddStockStoreProductControllerReadDto])
def add_stock_store_product(
    data: AddStockStoreProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Add stock to an existing store product with FIFO batch allocation"""
    with LogContext(
        "store_products",
        "add_stock_store_product",
        product_id=data.product_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing add stock to store product request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/add-stock",
                    "product_id": data.product_id,
                    "loc_id": org_bus_loc["loc_id"],
                    "qty": data.qty,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-create"]
        )

        if not is_authorized:
            logger.warning(
                "Add stock to store product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/add-stock",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.add_stock_store_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Stock added to store product successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/add-stock",
                        "product_id": data.product_id,
                        "loc_id": org_bus_loc["loc_id"],
                        "qty": data.qty,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Add stock to store product failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/add-stock",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Update Store Product
@store_products_router.put("/update", response_model=Respons[UpdateStoreProductControllerReadDto])
def update_store_product(
    data: UpdateStoreProductControllerWriteDto,
    product_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a store product"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_products",
        "update_store_product",
        loc_id=loc_id,
        product_id=product_id,
    ):
        logger.info(
            "Processing update store product request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/update",
                    "loc_id": loc_id,
                    "product_id": product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update store product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/update",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.update_store_product(
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
                "Store product updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/update",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store product update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/update",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Store Product
@store_products_router.get("/get", response_model=Respons[GetStoreProductControllerReadDto])
def get_store_product(
    product_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single store product by location and product ID"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_products",
        "get_store_product",
        loc_id=loc_id,
        product_id=product_id,
    ):
        logger.info(
            "Processing get store product request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/get",
                    "loc_id": loc_id,
                    "product_id": product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get store product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/get",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.get_store_product(
            loc_id=loc_id,
            product_id=product_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Store product retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/get",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store product retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/get",
                        "loc_id": loc_id,
                        "product_id": product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Store Products List
@store_products_router.get("/list", response_model=Respons[GetStoreProductsControllerReadDto])
def get_store_products(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by product name, description, location name, or barcode"),
    metadata_ids: Optional[List[str]] = Query(None, description="Filter by product metadata IDs (e.g. category, tag, brand). Product must have at least one of these metadata"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of store products with filters and pagination"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_products",
        "get_store_products",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get store products request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/list",
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
            required_permissions=["permission-msg-store-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get store products failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.get_store_products(
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
                "Store products retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store products retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Store Product
@store_products_router.delete("/delete", response_model=Respons[DeleteStoreProductControllerReadDto])
def delete_store_product(
    data: DeleteStoreProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a store product"""
    with LogContext(
        "store_products",
        "delete_store_product",
        loc_id=data.loc_id if hasattr(data, "loc_id") else "unknown",
        product_id=data.product_id if hasattr(data, "product_id") else "unknown",
    ):
        logger.info(
            "Processing delete store product request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/delete",
                    "loc_id": data.loc_id,
                    "product_id": data.product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete store product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.delete_store_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Permanent Delete Store Product
@store_products_router.delete("/permanent-delete", response_model=Respons[PermanentDeleteStoreProductControllerReadDto])
def permanent_delete_store_product(
    data: PermanentDeleteStoreProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a store product from the database"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_products",
        "permanent_delete_store_product",
        loc_id=loc_id,
        product_id=data.product_id,
    ):
        logger.info(
            "Processing permanent delete store product request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/permanent-delete",
                    "loc_id": loc_id,
                    "product_id": data.product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Permanent delete store product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/permanent-delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.permanent_delete_store_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Store product permanently deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/permanent-delete",
                        "loc_id": loc_id,
                        "product_id": data.product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store product permanent deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/permanent-delete",
                        "loc_id": loc_id,
                        "product_id": data.product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Reverse Batch Store Product
@store_products_router.put("/reverse-batch", response_model=Respons[ReverseBatchStoreProductControllerReadDto])
def reverse_batch_store_product(
    data: ReverseBatchStoreProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Reverse a batch allocation from a store product"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_products",
        "reverse_batch_store_product",
        loc_id=loc_id,
        product_id=data.product_id if hasattr(data, "product_id") else "unknown",
        batch_number=data.batch_number if hasattr(data, "batch_number") else "unknown",
    ):
        logger.info(
            "Processing reverse batch store product request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/reverse-batch",
                    "loc_id": loc_id,
                    "product_id": data.product_id,
                    "batch_number": data.batch_number,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Reverse batch store product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/reverse-batch",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.reverse_batch_store_product(
            data=data,
            loc_id=loc_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Batch reversed successfully for store product",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/reverse-batch",
                        "loc_id": loc_id,
                        "product_id": data.product_id,
                        "batch_number": data.batch_number,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Reverse batch store product failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/reverse-batch",
                        "loc_id": loc_id,
                        "product_id": data.product_id,
                        "batch_number": data.batch_number,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 8. Get Store Products Statistics
@store_products_router.get("/statistics", response_model=Respons[GetStoreProductStatisticsControllerReadDto])
def get_store_product_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get store product statistics"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_products",
        "get_store_product_statistics",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=loc_id,
    ):
        logger.info(
            "Processing get store product statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-products/statistics",
                    "loc_id": loc_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get store product statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreProductsService.get_store_product_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
        )

        if service_result.success:
            logger.info(
                "Store product statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store product statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-products/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

