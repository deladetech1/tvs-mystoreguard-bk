from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.products.products_service import ProductsService
from src.entities.products.products_write_dto import (
    CreateProductControllerWriteDto,
    UpdateProductControllerWriteDto,
    AddBatchToProductControllerWriteDto,
    ReverseBatchControllerWriteDto,
    DeleteBatchControllerWriteDto,
    DeleteMovementControllerWriteDto,
    PermanentDeleteProductControllerWriteDto,
    CreateSplitControllerWriteDto,
    ReverseSplitControllerWriteDto,
    ReverseSplitItemControllerWriteDto,
)
from src.entities.products.products_read_dto import (
    CreateProductControllerReadDto,
    UpdateProductControllerReadDto,
    GetProductControllerReadDto,
    GetProductsControllerReadDto,
    GetBatchLocationsControllerReadDto,
    PurchaseBatchReadDto,
    DeleteBatchControllerReadDto,
    DeleteMovementControllerReadDto,
    PermanentDeleteProductControllerReadDto,
    GetProductStatisticsControllerReadDto,
    CreateSplitControllerReadDto,
    GetSplitControllerReadDto,
    GetSplitsControllerReadDto,
    GetSplitStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

products_router = APIRouter(prefix="/products", tags=["Products"])
logger = get_logger("products")


# 1. Create Product
@products_router.post("/add", response_model=Respons[CreateProductControllerReadDto])
def create_product(
    data: CreateProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new product with optional batches"""
    with LogContext(
        "products",
        "create_product",
        name=data.name if data.name else "N/A",
    ):
        logger.info(
            "Processing create product request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/add",
                    "name": data.name if data.name else None,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.create_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Product created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/add",
                        "product_id": (
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
                f"Product creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Product
@products_router.put("/update", response_model=Respons[UpdateProductControllerReadDto])
def update_product(
    data: UpdateProductControllerWriteDto,
    product_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a product with optional batches"""
    with LogContext(
        "products",
        "update_product",
        product_id=product_id,
    ):
        logger.info(
            "Processing update product request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/update",
                    "product_id": product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/update",
                        "product_id": product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.update_product(
            data=data,
            product_id=product_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Product updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/update",
                        "product_id": product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/update",
                        "product_id": product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Product
@products_router.get("/get", response_model=Respons[GetProductControllerReadDto])
def get_product(
    product_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single product by ID"""
    with LogContext(
        "products",
        "get_product",
        product_id=product_id,
    ):
        logger.info(
            "Processing get product request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/get",
                    "product_id": product_id,
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
                "Get product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/get",
                        "product_id": product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.get_product(
            product_id=product_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Product retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/get",
                        "product_id": product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/get",
                        "product_id": product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Products List
@products_router.get("/list", response_model=Respons[GetProductsControllerReadDto])
def get_products(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name, description, SKU, or barcode"),
    metadata_ids: Optional[List[str]] = Query(None, description="Filter by product metadata IDs (e.g. category, tag, brand). Product must have at least one of these metadata"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of products with filters and pagination"""
    with LogContext(
        "products",
        "get_products",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get products request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/list",
                    "filters": {
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
            required_permissions=["permission-msg-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get products failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.get_products(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            is_active=is_active,
            search=search,
            metadata_ids=metadata_ids,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Products retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Products retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Get Batch Locations
@products_router.get("/batch-locations", response_model=Respons[GetBatchLocationsControllerReadDto])
def get_batch_locations(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    location_type: Optional[str] = Query(None, description="Filter by location type (STORE or WAREHOUSE)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get batch locations for a location with optional filters"""
    with LogContext(
        "products",
        "get_batch_locations",
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing get batch locations request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/batch-locations",
                    "loc_id": org_bus_loc["loc_id"],
                    "product_id": product_id,
                    "location_type": location_type,
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
                "Get batch locations failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/batch-locations",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.get_batch_locations(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            product_id=product_id,
            location_type=location_type,
        )

        if service_result.success:
            logger.info(
                "Batch locations retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/batch-locations",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Batch locations retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/batch-locations",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 8. Add Batch to Product
@products_router.post("/add-batch", response_model=Respons[PurchaseBatchReadDto])
def add_batch_to_product(
    data: AddBatchToProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Add a batch to an existing product"""
    with LogContext(
        "products",
        "add_batch_to_product",
        product_id=data.product_id,
    ):
        logger.info(
            "Processing add batch to product request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/add-batch",
                    "product_id": data.product_id,
                    "qty_received": data.qty_received,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Add batch to product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/add-batch",
                        "product_id": data.product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.add_batch_to_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Batch added to product successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/add-batch",
                        "product_id": data.product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Add batch to product failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/add-batch",
                        "product_id": data.product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 10. Delete Batch
@products_router.delete("/delete-batch", response_model=Respons[DeleteBatchControllerReadDto])
def delete_batch(
    data: DeleteBatchControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a batch"""
    with LogContext(
        "products",
        "delete_batch",
        product_id=data.product_id,
        batch_id=data.batch_id,
    ):
        logger.info(
            "Processing delete batch request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/delete-batch",
                    "product_id": data.product_id,
                    "batch_id": data.batch_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Delete batch failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/delete-batch",
                        "batch_id": data.batch_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.delete_batch(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Batch deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/delete-batch",
                        "batch_id": data.batch_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Batch deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/delete-batch",
                        "batch_id": data.batch_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 11. Delete Movement
@products_router.delete("/delete-movement", response_model=Respons[DeleteMovementControllerReadDto])
def delete_movement(
    data: DeleteMovementControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a movement"""
    with LogContext(
        "products",
        "delete_movement",
        product_id=data.product_id,
        movement_id=data.movement_id,
    ):
        logger.info(
            "Processing delete movement request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/delete-movement",
                    "product_id": data.product_id,
                    "movement_id": data.movement_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Delete movement failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/delete-movement",
                        "movement_id": data.movement_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.delete_movement(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Movement deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/delete-movement",
                        "movement_id": data.movement_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Movement deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/delete-movement",
                        "movement_id": data.movement_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 12. Reverse Batch
@products_router.put("/reverse-batch", response_model=Respons[PurchaseBatchReadDto])
def reverse_batch(
    data: ReverseBatchControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Reverse a batch by setting remaining_qty to 0 and status to VOID"""
    with LogContext(
        "products",
        "reverse_batch",
        batch_number=data.batch_number,
    ):
        logger.info(
            "Processing reverse batch request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/reverse-batch",
                    "batch_number": data.batch_number,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-update"]
        )

        if not is_authorized:
            logger.warning(
                "Reverse batch failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/reverse-batch",
                        "batch_number": data.batch_number,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.reverse_batch(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Batch reversed successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/reverse-batch",
                        "batch_number": data.batch_number,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Batch reversal failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/reverse-batch",
                        "batch_number": data.batch_number,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 9. Permanent Delete Product
@products_router.delete("/permanent-delete", response_model=Respons[PermanentDeleteProductControllerReadDto])
def permanent_delete_product(
    data: PermanentDeleteProductControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a product"""
    with LogContext(
        "products",
        "permanent_delete_product",
        product_id=data.product_id,
    ):
        logger.info(
            "Processing permanent delete product request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/permanent-delete",
                    "product_id": data.product_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Permanent delete product failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/permanent-delete",
                        "product_id": data.product_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.permanent_delete_product(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Product permanently deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/permanent-delete",
                        "product_id": data.product_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product permanent deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/permanent-delete",
                        "product_id": data.product_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 10. Get Product Statistics
@products_router.get("/statistics", response_model=Respons[GetProductStatisticsControllerReadDto])
def get_product_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get product statistics"""
    with LogContext(
        "products",
        "get_product_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get product statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/products/statistics",
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
                "Get product statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.get_product_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Product statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/products/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# =====================================================
# SPLIT (BREAK-BULK) ENDPOINTS
# =====================================================

# Create a split (one parent with one or more product items, all-or-none)
@products_router.post("/split", response_model=Respons[CreateSplitControllerReadDto])
def create_split(
    data: CreateSplitControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a split with one or more product items. All-or-none."""
    with LogContext("products", "create_split", item_count=len(data.items or [])):
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-split"],
        )
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.create_split(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
            loc_id=org_bus_loc.get("loc_id"),
        )
        if not service_result.success:
            logger.warning(
                f"Create split failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/products/split", "error": service_result.error, "status": "failed"}},
            )
        return service_result


# Reverse a whole split (all its active items)
@products_router.put("/reverse-split", response_model=Respons[GetSplitControllerReadDto])
def reverse_split(
    data: ReverseSplitControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Reverse a whole split (all of its still-active items)."""
    with LogContext("products", "reverse_split", split_id=data.split_id):
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-split"],
        )
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.reverse_split(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )
        if not service_result.success:
            logger.warning(
                f"Reverse split failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/products/reverse-split", "error": service_result.error, "status": "failed"}},
            )
        return service_result


# Reverse a single product item within a split (others stay)
@products_router.put("/reverse-split-item", response_model=Respons[GetSplitControllerReadDto])
def reverse_split_item(
    data: ReverseSplitItemControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Reverse one product item within a split; the rest stay. Returns the updated split."""
    with LogContext("products", "reverse_split_item", item_id=data.item_id):
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-split"],
        )
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductsService.reverse_split_item(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )
        if not service_result.success:
            logger.warning(
                f"Reverse split item failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/products/reverse-split-item", "error": service_result.error, "status": "failed"}},
            )
        return service_result


# List splits (headers with their items)
@products_router.get("/splits", response_model=Respons[GetSplitsControllerReadDto])
def get_splits(
    status: Optional[str] = Query(None, description="Filter by split status (ACTIVE, PARTIALLY_REVERSED, REVERSED)"),
    source_scope: Optional[str] = Query(None, description="Filter by source scope (PRODUCT, STORE, or WAREHOUSE)"),
    source_product_id: Optional[str] = Query(None, description="Filter to splits that include this source product"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """List splits with their items, newest first."""
    with LogContext("products", "get_splits", tenant_id=current_user.data[0].tenant_id):
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-split", "permission-msg-products-get"],
        )
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return ProductsService.get_splits(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            status=status,
            source_scope=source_scope,
            source_product_id=source_product_id,
            page=page,
            size=size,
        )


# Get one split with its items
@products_router.get("/split-detail", response_model=Respons[GetSplitControllerReadDto])
def get_split(
    split_id: str = Query(..., description="Split ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single split with its product items."""
    with LogContext("products", "get_split", split_id=split_id):
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-split", "permission-msg-products-get"],
        )
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return ProductsService.get_split(
            split_id=split_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )


# Split statistics for the current location
@products_router.get("/split-statistics", response_model=Respons[GetSplitStatisticsControllerReadDto])
def get_split_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Split statistics for the caller's current location."""
    with LogContext("products", "get_split_statistics", tenant_id=current_user.data[0].tenant_id):
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-split", "permission-msg-products-get"],
        )
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return ProductsService.get_split_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc.get("loc_id"),
        )
