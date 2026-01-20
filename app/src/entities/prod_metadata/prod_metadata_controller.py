from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.prod_metadata.prod_metadata_service import ProductMetadataService
from src.entities.prod_metadata.prod_metadata_write_dto import (
    CreateProductMetadataControllerWriteDto,
    UpdateProductMetadataControllerWriteDto,
    DeleteProductMetadataControllerWriteDto,
)
from src.entities.prod_metadata.prod_metadata_read_dto import (
    CreateProductMetadataControllerReadDto,
    UpdateProductMetadataControllerReadDto,
    GetProductMetadataControllerReadDto,
    GetProductMetadataListControllerReadDto,
    DeleteProductMetadataControllerReadDto,
    GetProductMetadataStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

prod_metadata_router = APIRouter(prefix="/product-metadata", tags=["Settings Product Metadata"])
logger = get_logger("prod_metadata")


# 1. Create Product Metadata
@prod_metadata_router.post("/add", response_model=Respons[CreateProductMetadataControllerReadDto])
def create_product_metadata(
    data: CreateProductMetadataControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new product metadata entry (tag, category, brand, or label)"""
    with LogContext(
        "prod_metadata",
        "create_product_metadata",
        name=data.name,
        of_type=data.of_type,
    ):
        logger.info(
            "Processing create product metadata request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-metadata/add",
                    "name": data.name,
                    "of_type": data.of_type,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-metadata-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create product metadata failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductMetadataService.create_product_metadata(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Product metadata created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/add",
                        "metadata_id": (
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
                f"Product metadata creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Product Metadata
@prod_metadata_router.put("/update", response_model=Respons[UpdateProductMetadataControllerReadDto])
def update_product_metadata(
    data: UpdateProductMetadataControllerWriteDto,
    metadata_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update product metadata"""
    with LogContext(
        "prod_metadata",
        "update_product_metadata",
        metadata_id=metadata_id,
    ):
        logger.info(
            "Processing update product metadata request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-metadata/update",
                    "metadata_id": metadata_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-metadata-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update product metadata failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/update",
                        "metadata_id": metadata_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductMetadataService.update_product_metadata(
            data=data,
            metadata_id=metadata_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Product metadata updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/update",
                        "metadata_id": metadata_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product metadata update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/update",
                        "metadata_id": metadata_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Product Metadata
@prod_metadata_router.get("/get", response_model=Respons[GetProductMetadataControllerReadDto])
def get_product_metadata(
    metadata_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single product metadata by ID"""
    with LogContext(
        "prod_metadata",
        "get_product_metadata",
        metadata_id=metadata_id,
    ):
        logger.info(
            "Processing get product metadata request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-metadata/get",
                    "metadata_id": metadata_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-metadata-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get product metadata failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/get",
                        "metadata_id": metadata_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductMetadataService.get_product_metadata(
            metadata_id=metadata_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Product metadata retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/get",
                        "metadata_id": metadata_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product metadata retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/get",
                        "metadata_id": metadata_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Product Metadata List
@prod_metadata_router.get("/list", response_model=Respons[GetProductMetadataListControllerReadDto])
def get_product_metadata_list(
    of_type: Optional[str] = Query(None, description="Filter by type (TAG, CATEGORY, BRAND, LABEL)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of product metadata with filters and pagination"""
    with LogContext(
        "prod_metadata",
        "get_product_metadata_list",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get product metadata list request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-metadata/list",
                    "filters": {
                        "of_type": of_type,
                        "is_active": is_active,
                        "page": page,
                        "size": size,
                    },
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-metadata-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get product metadata list failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductMetadataService.get_product_metadata_list(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            of_type=of_type,
            is_active=is_active,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Product metadata list retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product metadata list retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Product Metadata
@prod_metadata_router.delete("/delete", response_model=Respons[DeleteProductMetadataControllerReadDto])
def delete_product_metadata(
    data: DeleteProductMetadataControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete product metadata"""
    with LogContext(
        "prod_metadata",
        "delete_product_metadata",
        metadata_id=data.metadata_id,
    ):
        logger.info(
            "Processing delete product metadata request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-metadata/delete",
                    "metadata_id": data.metadata_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-metadata-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete product metadata failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductMetadataService.delete_product_metadata(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Get Product Metadata Statistics
@prod_metadata_router.get("/statistics", response_model=Respons[GetProductMetadataStatisticsControllerReadDto])
def get_product_metadata_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get statistics for product metadata (total counts of tags, categories, labels, and brands)"""
    with LogContext(
        "prod_metadata",
        "get_product_metadata_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get product metadata statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-metadata/statistics",
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-metadata-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get product metadata statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductMetadataService.get_product_metadata_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Product metadata statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product metadata statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-metadata/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

