from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.purchase_orders.purchase_orders_service import PurchaseOrdersService
from src.entities.purchase_orders.purchase_orders_write_dto import (
    CreatePurchaseOrderControllerWriteDto,
    UpdatePurchaseOrderControllerWriteDto,
    CancelPurchaseOrderControllerWriteDto,
    PermanentDeletePurchaseOrderControllerWriteDto,
    ReceivePurchaseOrderControllerWriteDto,
    UpdatePurchaseReceiptControllerWriteDto,
    DeletePurchaseReceiptControllerWriteDto,
)
from src.entities.purchase_orders.purchase_orders_read_dto import (
    CreatePurchaseOrderControllerReadDto,
    UpdatePurchaseOrderControllerReadDto,
    GetPurchaseOrderControllerReadDto,
    GetPurchaseOrdersControllerReadDto,
    CancelPurchaseOrderControllerReadDto,
    PermanentDeletePurchaseOrderControllerReadDto,
    ReceivePurchaseOrderControllerReadDto,
    GetPurchaseOrderStatisticsControllerReadDto,
    GetPurchaseReceiptControllerReadDto,
    GetPurchaseReceiptsControllerReadDto,
    UpdatePurchaseReceiptControllerReadDto,
    DeletePurchaseReceiptControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

purchase_orders_router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])
logger = get_logger("purchase_orders")


# 1. Create Purchase Order
@purchase_orders_router.post("/add", response_model=Respons[CreatePurchaseOrderControllerReadDto])
def create_purchase_order(
    data: CreatePurchaseOrderControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new purchase order with items (FLOW 1: No batches, no movements)"""
    with LogContext(
        "purchase_orders",
        "create_purchase_order",
        supplier_id=data.supplier_id,
    ):
        logger.info(
            "Processing create purchase order request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/add",
                    "supplier_id": data.supplier_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create purchase order failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.create_purchase_order(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Purchase order created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/add",
                        "purchase_order_id": (
                            service_result.data[0].purchase_order.id 
                            if service_result.data and len(service_result.data) > 0
                            else None
                        ),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase order creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Purchase Order
@purchase_orders_router.put("/update", response_model=Respons[UpdatePurchaseOrderControllerReadDto])
def update_purchase_order(
    data: UpdatePurchaseOrderControllerWriteDto,
    purchase_order_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a purchase order with optional items (qty_received cannot be updated directly)"""
    with LogContext(
        "purchase_orders",
        "update_purchase_order",
        purchase_order_id=purchase_order_id,
    ):
        logger.info(
            "Processing update purchase order request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/update",
                    "purchase_order_id": purchase_order_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update purchase order failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/update",
                        "purchase_order_id": purchase_order_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.update_purchase_order(
            data=data,
            purchase_order_id=purchase_order_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Purchase order updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/update",
                        "purchase_order_id": purchase_order_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase order update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/update",
                        "purchase_order_id": purchase_order_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Purchase Order
@purchase_orders_router.get("/get", response_model=Respons[GetPurchaseOrderControllerReadDto])
def get_purchase_order(
    purchase_order_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single purchase order by ID"""
    with LogContext(
        "purchase_orders",
        "get_purchase_order",
        purchase_order_id=purchase_order_id,
    ):
        logger.info(
            "Processing get purchase order request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/get",
                    "purchase_order_id": purchase_order_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get purchase order failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/get",
                        "purchase_order_id": purchase_order_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.get_purchase_order(
            purchase_order_id=purchase_order_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Purchase order retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/get",
                        "purchase_order_id": purchase_order_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase order retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/get",
                        "purchase_order_id": purchase_order_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Purchase Orders List
@purchase_orders_router.get("/list", response_model=Respons[GetPurchaseOrdersControllerReadDto])
def get_purchase_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    supplier_id: Optional[str] = Query(None, description="Filter by supplier ID"),
    search: Optional[str] = Query(None, description="Search by PO number or notes"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of purchase orders with filters and pagination"""
    with LogContext(
        "purchase_orders",
        "get_purchase_orders",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get purchase orders request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/list",
                    "filters": {
                        "status": status,
                        "supplier_id": supplier_id,
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
            required_permissions=["permission-msg-purchase-orders-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get purchase orders failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.get_purchase_orders(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            status=status,
            supplier_id=supplier_id,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Purchase orders retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase orders retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Cancel Purchase Order
@purchase_orders_router.put("/cancel", response_model=Respons[CancelPurchaseOrderControllerReadDto])
def cancel_purchase_order(
    data: CancelPurchaseOrderControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Cancel a purchase order by setting status to CANCELLED"""
    with LogContext(
        "purchase_orders",
        "cancel_purchase_order",
        purchase_order_id=data.purchase_order_id if hasattr(data, "purchase_order_id") else "unknown",
    ):
        logger.info(
            "Processing cancel purchase order request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/cancel",
                    "purchase_order_id": data.purchase_order_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-update"]
        )

        if not is_authorized:
            logger.warning(
                "Cancel purchase order failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/cancel",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.cancel_purchase_order(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            cancelled_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Purchase order cancelled successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/cancel",
                        "purchase_order_id": data.purchase_order_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase order cancellation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/cancel",
                        "purchase_order_id": data.purchase_order_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Permanent Delete Purchase Order
@purchase_orders_router.delete("/permanent-delete", response_model=Respons[PermanentDeletePurchaseOrderControllerReadDto])
def permanent_delete_purchase_order(
    data: PermanentDeletePurchaseOrderControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a purchase order and its related items from the database"""
    with LogContext(
        "purchase_orders",
        "permanent_delete_purchase_order",
        purchase_order_id=data.purchase_order_id if hasattr(data, "purchase_order_id") else "unknown",
    ):
        logger.info(
            "Processing permanent delete purchase order request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/permanent-delete",
                    "purchase_order_id": data.purchase_order_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Permanent delete purchase order failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/permanent-delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.permanent_delete_purchase_order(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Purchase order permanently deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/permanent-delete",
                        "purchase_order_id": data.purchase_order_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase order permanent deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/permanent-delete",
                        "purchase_order_id": data.purchase_order_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Receive Purchase Order (NEW API - FLOW 2)
@purchase_orders_router.post("/receive", response_model=Respons[ReceivePurchaseOrderControllerReadDto])
def receive_purchase_order(
    data: ReceivePurchaseOrderControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Receive a purchase order - creates receipt, batches, updates PO items, inserts movements, updates PO status (FLOW 2)"""
    with LogContext(
        "purchase_orders",
        "receive_purchase_order",
        purchase_order_id=data.purchase_order_id,
    ):
        logger.info(
            "Processing receive purchase order request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/receive",
                    "purchase_order_id": data.purchase_order_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-update"]
        )

        if not is_authorized:
            logger.warning(
                "Receive purchase order failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receive",
                        "purchase_order_id": data.purchase_order_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.receive_purchase_order(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Purchase order received successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receive",
                        "purchase_order_id": data.purchase_order_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Receive purchase order failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receive",
                        "purchase_order_id": data.purchase_order_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 8. Get Purchase Order Statistics
@purchase_orders_router.get("/statistics", response_model=Respons[GetPurchaseOrderStatisticsControllerReadDto])
def get_purchase_order_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get purchase order statistics"""
    with LogContext(
        "purchase_orders",
        "get_purchase_order_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get purchase order statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/statistics",
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get purchase order statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.get_purchase_order_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Purchase order statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase order statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 9. Get Purchase Receipt
@purchase_orders_router.get("/receipts/get", response_model=Respons[GetPurchaseReceiptControllerReadDto])
def get_purchase_receipt(
    receipt_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single purchase receipt by ID"""
    with LogContext(
        "purchase_orders",
        "get_purchase_receipt",
        receipt_id=receipt_id,
    ):
        logger.info(
            "Processing get purchase receipt request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/receipts/get",
                    "receipt_id": receipt_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get purchase receipt failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/get",
                        "receipt_id": receipt_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.get_purchase_receipt(
            receipt_id=receipt_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Purchase receipt retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/get",
                        "receipt_id": receipt_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase receipt retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/get",
                        "receipt_id": receipt_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 10. Get Purchase Receipts List
@purchase_orders_router.get("/receipts/list", response_model=Respons[GetPurchaseReceiptsControllerReadDto])
def get_purchase_receipts(
    purchase_order_id: Optional[str] = Query(None, description="Filter by purchase order ID"),
    search: Optional[str] = Query(None, description="Search by receipt number, description, or PO number"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of purchase receipts with filters and pagination"""
    with LogContext(
        "purchase_orders",
        "get_purchase_receipts",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get purchase receipts request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/receipts/list",
                    "filters": {
                        "purchase_order_id": purchase_order_id,
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
            required_permissions=["permission-msg-purchase-orders-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get purchase receipts failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.get_purchase_receipts(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            purchase_order_id=purchase_order_id,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Purchase receipts retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase receipts retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 11. Update Purchase Receipt
@purchase_orders_router.put("/receipts/update", response_model=Respons[UpdatePurchaseReceiptControllerReadDto])
def update_purchase_receipt(
    data: UpdatePurchaseReceiptControllerWriteDto,
    receipt_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a purchase receipt"""
    with LogContext(
        "purchase_orders",
        "update_purchase_receipt",
        receipt_id=receipt_id,
    ):
        logger.info(
            "Processing update purchase receipt request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/receipts/update",
                    "receipt_id": receipt_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update purchase receipt failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/update",
                        "receipt_id": receipt_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.update_purchase_receipt(
            data=data,
            receipt_id=receipt_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Purchase receipt updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/update",
                        "receipt_id": receipt_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase receipt update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/update",
                        "receipt_id": receipt_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 12. Delete Purchase Receipt
@purchase_orders_router.delete("/receipts/delete", response_model=Respons[DeletePurchaseReceiptControllerReadDto])
def delete_purchase_receipt(
    data: DeletePurchaseReceiptControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a purchase receipt"""
    with LogContext(
        "purchase_orders",
        "delete_purchase_receipt",
        receipt_id=data.receipt_id if hasattr(data, "receipt_id") else "unknown",
    ):
        logger.info(
            "Processing delete purchase receipt request",
            extra={
                "extra_fields": {
                    "endpoint": "/purchase-orders/receipts/delete",
                    "receipt_id": data.receipt_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-purchase-orders-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete purchase receipt failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = PurchaseOrdersService.delete_purchase_receipt(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Purchase receipt deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/delete",
                        "receipt_id": data.receipt_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Purchase receipt deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/purchase-orders/receipts/delete",
                        "receipt_id": data.receipt_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result
