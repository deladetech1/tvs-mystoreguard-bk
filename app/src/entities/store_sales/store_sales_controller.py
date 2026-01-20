from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.store_sales.store_sales_service import StoreSalesService
from src.entities.store_sales.store_sales_write_dto import (
    CreateSaleControllerWriteDto,
    UpdateSaleControllerWriteDto,
    CancelSaleControllerWriteDto,
    DeleteSaleControllerWriteDto,
    RefundPaymentControllerWriteDto,
    CreatePaymentControllerWriteDto,
    VerifyPriceControllerWriteDto,
)
from src.entities.store_sales.store_sales_read_dto import (
    CreateSaleControllerReadDto,
    UpdateSaleControllerReadDto,
    GetSaleControllerReadDto,
    GetSalesControllerReadDto,
    CancelSaleControllerReadDto,
    DeleteSaleControllerReadDto,
    RefundPaymentControllerReadDto,
    GetSalesStatisticsControllerReadDto,
    CreatePaymentControllerReadDto,
    VerifyPriceControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

store_sales_router = APIRouter(prefix="/store-sales", tags=["Store Sales"])
logger = get_logger("store_sales")


# 1. Create Sale
@store_sales_router.post("/add", response_model=Respons[CreateSaleControllerReadDto])
def create_sale(
    data: CreateSaleControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new sale with FIFO inventory deduction"""
    with LogContext(
        "store_sales",
        "create_sale",
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing create sale request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/add",
                    "loc_id": org_bus_loc["loc_id"],
                    "items_count": len(data.items),
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create sale failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.create_sale(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Sale created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/add",
                        "loc_id": org_bus_loc["loc_id"],
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Sale creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Get Sale
@store_sales_router.get("/get", response_model=Respons[GetSaleControllerReadDto])
def get_sale(
    sale_id: str = Query(..., description="Sale ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single sale by ID"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "get_sale",
        loc_id=loc_id,
        sale_id=sale_id,
    ):
        logger.info(
            "Processing get sale request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/get",
                    "loc_id": loc_id,
                    "sale_id": sale_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get sale failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/get",
                        "loc_id": loc_id,
                        "sale_id": sale_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.get_sale(
            sale_id=sale_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
        )

        if service_result.success:
            logger.info(
                "Sale retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/get",
                        "loc_id": loc_id,
                        "sale_id": sale_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Sale retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/get",
                        "loc_id": loc_id,
                        "sale_id": sale_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Sales List
@store_sales_router.get("/list", response_model=Respons[GetSalesControllerReadDto])
def get_sales(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sale_mode: Optional[str] = Query(None, description="Filter by sale mode (INSTANT, DEPOSIT, CREDIT)"),
    fulfillment_status: Optional[str] = Query(None, description="Filter by fulfillment status (PENDING, PARTIALLY_FULFILLED, FULFILLED)"),
    from_date: Optional[str] = Query(None, description="Filter by sale date from (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter by sale date to (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search by sale number or customer name"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of sales with filters and pagination"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "get_sales",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=loc_id,
    ):
        logger.info(
            "Processing get sales request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/list",
                    "filters": {
                        "loc_id": loc_id,
                        "customer_id": customer_id,
                        "status": status,
                        "sale_mode": sale_mode,
                        "fulfillment_status": fulfillment_status,
                        "from_date": from_date,
                        "to_date": to_date,
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
            required_permissions=["permission-msg-store-sales-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get sales failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.get_sales(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            customer_id=customer_id,
            status=status,
            sale_mode=sale_mode,
            fulfillment_status=fulfillment_status,
            from_date=from_date,
            to_date=to_date,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Sales retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/list",
                        "count": len(service_result.data[0].sales) if service_result.data and service_result.data[0].sales else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Sales retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Update Sale
@store_sales_router.put("/update", response_model=Respons[UpdateSaleControllerReadDto])
def update_sale(
    data: UpdateSaleControllerWriteDto,
    sale_id: str = Query(..., description="Sale ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a sale"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "update_sale",
        loc_id=loc_id,
        sale_id=sale_id,
    ):
        logger.info(
            "Processing update sale request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/update",
                    "loc_id": loc_id,
                    "sale_id": sale_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update sale failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/update",
                        "loc_id": loc_id,
                        "sale_id": sale_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.update_sale(
            data=data,
            sale_id=sale_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Sale updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/update",
                        "loc_id": loc_id,
                        "sale_id": sale_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Sale update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/update",
                        "loc_id": loc_id,
                        "sale_id": sale_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Cancel Sale
@store_sales_router.put("/cancel", response_model=Respons[CancelSaleControllerReadDto])
def cancel_sale(
    data: CancelSaleControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Cancel a sale and restore inventory"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "cancel_sale",
        loc_id=loc_id,
        sale_id=data.sale_id,
    ):
        logger.info(
            "Processing cancel sale request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/cancel",
                    "loc_id": loc_id,
                    "sale_id": data.sale_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-cancel"]
        )

        if not is_authorized:
            logger.warning(
                "Cancel sale failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/cancel",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.cancel_sale(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            cancelled_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Sale cancelled successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/cancel",
                        "loc_id": loc_id,
                        "sale_id": data.sale_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Sale cancellation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/cancel",
                        "loc_id": loc_id,
                        "sale_id": data.sale_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Delete Sale
@store_sales_router.delete("/delete", response_model=Respons[DeleteSaleControllerReadDto])
def delete_sale(
    data: DeleteSaleControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a sale and all related records"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "delete_sale",
        loc_id=loc_id,
        sale_id=data.sale_id,
    ):
        logger.info(
            "Processing delete sale request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/delete",
                    "loc_id": loc_id,
                    "sale_id": data.sale_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete sale failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.delete_sale(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Sale deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/delete",
                        "loc_id": loc_id,
                        "sale_id": data.sale_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Sale deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/delete",
                        "loc_id": loc_id,
                        "sale_id": data.sale_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Get Sales Statistics
@store_sales_router.get("/statistics", response_model=Respons[GetSalesStatisticsControllerReadDto])
def get_sales_statistics(
    from_date: Optional[str] = Query(None, description="Start date for statistics (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date for statistics (YYYY-MM-DD)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get sales statistics"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "get_sales_statistics",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=loc_id,
    ):
        logger.info(
            "Processing get sales statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/statistics",
                    "loc_id": loc_id,
                    "from_date": from_date,
                    "to_date": to_date,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get sales statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.get_sales_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            from_date=from_date,
            to_date=to_date,
        )

        if service_result.success:
            logger.info(
                "Sales statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/statistics",
                        "loc_id": loc_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Sales statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Create Payment (for CREDIT and DEPOSIT sales)
@store_sales_router.post("/payments/add", response_model=Respons[CreatePaymentControllerReadDto])
def create_payment(
    data: CreatePaymentControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Add payments to an existing sale (for CREDIT and DEPOSIT modes)"""
    loc_id = org_bus_loc["loc_id"]
    total_payment_amount = sum(payment.paid_amount for payment in data.payments)
    with LogContext(
        "store_sales",
        "create_payment",
        loc_id=loc_id,
        sale_id=data.sale_id,
    ):
        logger.info(
            "Processing create payment request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/payments/add",
                    "loc_id": loc_id,
                    "sale_id": data.sale_id,
                    "payments_count": len(data.payments),
                    "total_paid_amount": total_payment_amount,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-update"]
        )

        if not is_authorized:
            logger.warning(
                "Create payment failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/payments/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.create_payment(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Payments created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/payments/add",
                        "loc_id": loc_id,
                        "sale_id": data.sale_id,
                        "payments_count": len(data.payments),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Payment creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/payments/add",
                        "loc_id": loc_id,
                        "sale_id": data.sale_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 8. Refund Payment
@store_sales_router.put("/payments/refund", response_model=Respons[RefundPaymentControllerReadDto])
def refund_payment(
    data: RefundPaymentControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Refund a payment (soft delete)"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "refund_payment",
        loc_id=loc_id,
        payment_id=data.payment_id,
    ):
        logger.info(
            "Processing refund payment request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/payments/refund",
                    "loc_id": loc_id,
                    "payment_id": data.payment_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-update"]
        )

        if not is_authorized:
            logger.warning(
                "Refund payment failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/payments/refund",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.refund_payment(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            refunded_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Payment refunded successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/payments/refund",
                        "loc_id": loc_id,
                        "payment_id": data.payment_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Payment refund failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/payments/refund",
                        "loc_id": loc_id,
                        "payment_id": data.payment_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 9. Verify Price (for checkout)
@store_sales_router.post("/verify-price", response_model=Respons[VerifyPriceControllerReadDto])
def verify_price(
    data: VerifyPriceControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """
    Verify prices for items during checkout.
    
    This endpoint recalculates all prices including taxes with conditions based on
    the items being purchased with their quantities and base selling prices.
    Called when user clicks 'confirm prices' button during checkout.
    """
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "store_sales",
        "verify_price",
        loc_id=loc_id,
    ):
        logger.info(
            "Processing verify price request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-sales/verify-price",
                    "loc_id": loc_id,
                    "items_count": len(data.items),
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-sales-create"]
        )

        if not is_authorized:
            logger.warning(
                "Verify price failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/verify-price",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreSalesService.verify_price(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
        )

        if service_result.success:
            logger.info(
                "Prices verified successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/verify-price",
                        "loc_id": loc_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Price verification failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-sales/verify-price",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result
