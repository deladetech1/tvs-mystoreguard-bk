from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import date
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.invoices.invoices_service import InvoicesService
from src.entities.invoices.invoices_write_dto import (
    CreateInvoiceControllerWriteDto,
    UpdateInvoiceControllerWriteDto,
    DeleteInvoiceControllerWriteDto,
    CreateInvoicePaymentControllerWriteDto,
)
from src.entities.invoices.invoices_read_dto import (
    CreateInvoiceControllerReadDto,
    UpdateInvoiceControllerReadDto,
    GetInvoiceControllerReadDto,
    GetInvoicesControllerReadDto,
    DeleteInvoiceControllerReadDto,
    GetInvoiceStatisticsControllerReadDto,
    CreateInvoicePaymentControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

invoices_router = APIRouter(prefix="/invoices", tags=["Invoices"])
logger = get_logger("invoices")


# 1. Create Invoice
@invoices_router.post("/add", response_model=Respons[CreateInvoiceControllerReadDto])
def create_invoice(
    data: CreateInvoiceControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new invoice with items"""
    with LogContext(
        "invoices",
        "create_invoice",
        customer_id=data.customer_id if hasattr(data, "customer_id") else "unknown",
    ):
        logger.info(
            "Processing create invoice request",
            extra={
                "extra_fields": {
                    "endpoint": "/invoices/add",
                    "customer_id": data.customer_id,
                    "items_count": len(data.items),
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-invoices-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create invoice failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = InvoicesService.create_invoice(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Invoice created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/add",
                        "invoice_id": (
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
                f"Invoice creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Invoice
@invoices_router.put("/update", response_model=Respons[UpdateInvoiceControllerReadDto])
def update_invoice(
    data: UpdateInvoiceControllerWriteDto,
    invoice_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update an invoice"""
    with LogContext(
        "invoices",
        "update_invoice",
        invoice_id=invoice_id,
    ):
        logger.info(
            "Processing update invoice request",
            extra={
                "extra_fields": {
                    "endpoint": "/invoices/update",
                    "invoice_id": invoice_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-invoices-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update invoice failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/update",
                        "invoice_id": invoice_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = InvoicesService.update_invoice(
            data=data,
            invoice_id=invoice_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Invoice updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/update",
                        "invoice_id": invoice_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Invoice update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/update",
                        "invoice_id": invoice_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Invoice
@invoices_router.get("/get", response_model=Respons[GetInvoiceControllerReadDto])
def get_invoice(
    invoice_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single invoice by ID"""
    with LogContext(
        "invoices",
        "get_invoice",
        invoice_id=invoice_id,
    ):
        logger.info(
            "Processing get invoice request",
            extra={
                "extra_fields": {
                    "endpoint": "/invoices/get",
                    "invoice_id": invoice_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-invoices-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get invoice failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/get",
                        "invoice_id": invoice_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = InvoicesService.get_invoice(
            invoice_id=invoice_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
        )

        if service_result.success:
            logger.info(
                "Invoice retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/get",
                        "invoice_id": invoice_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Invoice retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/get",
                        "invoice_id": invoice_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Invoices (List)
@invoices_router.get("/list", response_model=Respons[GetInvoicesControllerReadDto])
def get_invoices(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, COMPLETED, PARTIALLY_PAID, OVERDUE, CANCELLED)"),
    from_date: Optional[str] = Query(None, description="Filter invoices from this date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter invoices to this date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of invoices with filters and pagination"""
    with LogContext(
        "invoices",
        "get_invoices",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get invoices request",
            extra={
                "extra_fields": {
                    "endpoint": "/invoices/list",
                    "filters": {
                        "customer_id": customer_id,
                        "status": status,
                        "from_date": from_date,
                        "to_date": to_date,
                        "page": page,
                        "size": size,
                    },
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-invoices-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get invoices failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = InvoicesService.get_invoices(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            customer_id=customer_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Invoices retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/list",
                        "count": len(service_result.data[0].invoices) if service_result.data and isinstance(service_result.data, list) and service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Invoices retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Invoice
@invoices_router.delete("/delete", response_model=Respons[DeleteInvoiceControllerReadDto])
def delete_invoice(
    data: DeleteInvoiceControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete an invoice (cascade deletes items)"""
    with LogContext(
        "invoices",
        "delete_invoice",
        invoice_id=data.invoice_id if hasattr(data, "invoice_id") else "unknown",
    ):
        logger.info(
            "Processing delete invoice request",
            extra={
                "extra_fields": {
                    "endpoint": "/invoices/delete",
                    "invoice_id": data.invoice_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-invoices-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete invoice failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = InvoicesService.delete_invoice(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Invoice deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/delete",
                        "invoice_id": data.invoice_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Invoice deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/delete",
                        "invoice_id": data.invoice_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Create Payment (for invoices)
@invoices_router.post("/payments/add", response_model=Respons[CreateInvoicePaymentControllerReadDto])
def create_payment(
    data: CreateInvoicePaymentControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Add payments to an existing invoice"""
    loc_id = org_bus_loc["loc_id"]
    total_payment_amount = sum(payment.paid_amount for payment in data.payments)
    with LogContext(
        "invoices",
        "create_payment",
        loc_id=loc_id,
        invoice_id=data.invoice_id,
    ):
        logger.info(
            "Processing create payment request",
            extra={
                "extra_fields": {
                    "endpoint": "/invoices/payments/add",
                    "loc_id": loc_id,
                    "invoice_id": data.invoice_id,
                    "payments_count": len(data.payments),
                    "total_paid_amount": total_payment_amount,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-invoices-update"]
        )

        if not is_authorized:
            logger.warning(
                "Create payment failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/payments/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = InvoicesService.create_payment(
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
                        "endpoint": "/invoices/payments/add",
                        "loc_id": loc_id,
                        "invoice_id": data.invoice_id,
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
                        "endpoint": "/invoices/payments/add",
                        "loc_id": loc_id,
                        "invoice_id": data.invoice_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Get Invoice Statistics
@invoices_router.get("/statistics", response_model=Respons[GetInvoiceStatisticsControllerReadDto])
def get_invoice_statistics(
    from_date: Optional[date] = Query(None, description="Filter invoices from this date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter invoices to this date (YYYY-MM-DD)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get invoice statistics with optional date filtering on sale_date field"""
    with LogContext(
        "invoices",
        "get_invoice_statistics",
    ):
        logger.info(
            "Processing get invoice statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/invoices/statistics",
                    "from_date": str(from_date) if from_date else None,
                    "to_date": str(to_date) if to_date else None,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-invoices-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get invoice statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/invoices/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = InvoicesService.get_invoice_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            from_date=from_date,
            to_date=to_date,
        )

        return service_result

