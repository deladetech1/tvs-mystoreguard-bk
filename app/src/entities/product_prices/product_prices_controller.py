from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.product_prices.product_prices_service import ProductPricesService
from src.entities.product_prices.product_prices_write_dto import (
    CreateProductPriceControllerWriteDto,
    UpdateProductPriceControllerWriteDto,
    DeleteProductPriceControllerWriteDto,
)
from src.entities.product_prices.product_prices_read_dto import (
    CreateProductPriceControllerReadDto,
    UpdateProductPriceControllerReadDto,
    GetProductPriceControllerReadDto,
    GetProductPricesControllerReadDto,
    DeleteProductPriceControllerReadDto,
    GetProductPriceStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

product_prices_router = APIRouter(prefix="/product-prices", tags=["Settings Product Prices"])
logger = get_logger("product_prices")


# 1. Create Product Price
@product_prices_router.post("/add", response_model=Respons[CreateProductPriceControllerReadDto])
def create_price(
    data: CreateProductPriceControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new product price"""
    with LogContext(
        "product_prices",
        "create_price",
        product_id=data.product_id,
        of_type=data.of_type,
    ):
        logger.info(
            "Processing create product price request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-prices/add",
                    "product_id": data.product_id,
                    "of_type": data.of_type,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-price-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create product price failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductPricesService.create_price(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Product price created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/add",
                        "price_id": (
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
                f"Product price creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Product Price
@product_prices_router.put("/update", response_model=Respons[UpdateProductPriceControllerReadDto])
def update_price(
    data: UpdateProductPriceControllerWriteDto,
    price_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a product price"""
    with LogContext(
        "product_prices",
        "update_price",
        price_id=price_id,
    ):
        logger.info(
            "Processing update product price request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-prices/update",
                    "price_id": price_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-price-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update product price failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/update",
                        "price_id": price_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductPricesService.update_price(
            data=data,
            price_id=price_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Product price updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/update",
                        "price_id": price_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product price update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/update",
                        "price_id": price_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Product Price
@product_prices_router.get("/get", response_model=Respons[GetProductPriceControllerReadDto])
def get_price(
    price_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single product price by ID"""
    with LogContext(
        "product_prices",
        "get_price",
        price_id=price_id,
    ):
        logger.info(
            "Processing get product price request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-prices/get",
                    "price_id": price_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-price-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get product price failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/get",
                        "price_id": price_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductPricesService.get_price(
            price_id=price_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Product price retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/get",
                        "price_id": price_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product price retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/get",
                        "price_id": price_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Product Prices List
@product_prices_router.get("/list", response_model=Respons[GetProductPricesControllerReadDto])
def get_prices(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    product_id: str = Query(None, description="Filter by product ID"),
    of_type: str = Query(None, description="Filter by price type (SKU, GLOBAL, LOCATION, TAG, CATEGORY, BRAND, LABEL)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of product prices with pagination"""
    with LogContext(
        "product_prices",
        "get_prices",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get product prices request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-prices/list",
                    "page": page,
                    "size": size,
                    "product_id": product_id,
                    "of_type": of_type,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-price-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get product prices failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductPricesService.get_prices(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            page=page,
            size=size,
            product_id=product_id,
            of_type=of_type,
        )

        if service_result.success:
            logger.info(
                "Product prices retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product prices retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Product Price
@product_prices_router.delete("/delete", response_model=Respons[DeleteProductPriceControllerReadDto])
def delete_price(
    data: DeleteProductPriceControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a product price"""
    with LogContext(
        "product_prices",
        "delete_price",
        price_id=data.price_id,
    ):
        logger.info(
            "Processing delete product price request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-prices/delete",
                    "price_id": data.price_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-price-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete product price failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductPricesService.delete_price(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Get Product Prices Statistics
@product_prices_router.get("/statistics", response_model=Respons[GetProductPriceStatisticsControllerReadDto])
def get_product_prices_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get comprehensive statistics for product prices"""
    with LogContext(
        "product_prices",
        "get_product_prices_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get product prices statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/product-prices/statistics",
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-product-price-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get product prices statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ProductPricesService.get_product_prices_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Product prices statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Product prices statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/product-prices/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

