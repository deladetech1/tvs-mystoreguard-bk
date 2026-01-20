from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.deliveries.deliveries_service import DeliveriesService
from src.entities.deliveries.deliveries_write_dto import (
    CreateDeliveryControllerWriteDto,
    UpdateDeliveryControllerWriteDto,
    UpdateDeliveryStatusControllerWriteDto,
    DispatchDeliveryControllerWriteDto,
    CompleteDeliveryControllerWriteDto,
    CancelDeliveryControllerWriteDto,
    DeleteDeliveryControllerWriteDto,
)
from src.entities.deliveries.deliveries_read_dto import (
    CreateDeliveryControllerReadDto,
    UpdateDeliveryControllerReadDto,
    GetDeliveryControllerReadDto,
    GetDeliveriesControllerReadDto,
    UpdateDeliveryStatusControllerReadDto,
    DispatchDeliveryControllerReadDto,
    CompleteDeliveryControllerReadDto,
    CancelDeliveryControllerReadDto,
    DeleteDeliveryControllerReadDto,
    GetDeliveriesStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

deliveries_router = APIRouter(prefix="/deliveries", tags=["Deliveries"])
logger = get_logger("deliveries")


# 1. Create Delivery
@deliveries_router.post("/add", response_model=Respons[CreateDeliveryControllerReadDto])
def create_delivery(
    data: CreateDeliveryControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new delivery"""
    with LogContext(
        "deliveries",
        "create_delivery",
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing create delivery request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/add",
                    "loc_id": org_bus_loc["loc_id"],
                    "sale_id": data.sale_id,
                    "items_count": len(data.items),
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create delivery failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.create_delivery(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Delivery created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/add",
                        "loc_id": org_bus_loc["loc_id"],
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Get Delivery
@deliveries_router.get("/get", response_model=Respons[GetDeliveryControllerReadDto])
def get_delivery(
    delivery_id: str = Query(..., description="Delivery ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single delivery by ID"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "get_delivery",
        loc_id=loc_id,
        delivery_id=delivery_id,
    ):
        logger.info(
            "Processing get delivery request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/get",
                    "loc_id": loc_id,
                    "delivery_id": delivery_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get delivery failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/get",
                        "loc_id": loc_id,
                        "delivery_id": delivery_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.get_delivery(
            delivery_id=delivery_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
        )

        if service_result.success:
            logger.info(
                "Delivery retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/get",
                        "loc_id": loc_id,
                        "delivery_id": delivery_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/get",
                        "loc_id": loc_id,
                        "delivery_id": delivery_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Deliveries List
@deliveries_router.get("/list", response_model=Respons[GetDeliveriesControllerReadDto])
def get_deliveries(
    sale_id: Optional[str] = Query(None, description="Filter by sale ID"),
    delivery_status: Optional[str] = Query(None, description="Filter by delivery status"),
    delivery_type: Optional[str] = Query(None, description="Filter by delivery type (INTERNAL, THIRD_PARTY, CUSTOMER_PICKUP)"),
    from_date: Optional[str] = Query(None, description="Filter by date from (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter by date to (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search by delivery number, recipient name, phone, address, or sale number"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of deliveries with filters and pagination"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "get_deliveries",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=loc_id,
    ):
        logger.info(
            "Processing get deliveries request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/list",
                    "filters": {
                        "loc_id": loc_id,
                        "sale_id": sale_id,
                        "delivery_status": delivery_status,
                        "delivery_type": delivery_type,
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
            required_permissions=["permission-msg-deliveries-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get deliveries failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.get_deliveries(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            sale_id=sale_id,
            delivery_status=delivery_status,
            delivery_type=delivery_type,
            from_date=from_date,
            to_date=to_date,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Deliveries retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/list",
                        "loc_id": loc_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Deliveries retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Update Delivery
@deliveries_router.put("/update", response_model=Respons[UpdateDeliveryControllerReadDto])
def update_delivery(
    delivery_id: str = Query(..., description="Delivery ID"),
    data: UpdateDeliveryControllerWriteDto = ...,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a delivery"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "update_delivery",
        loc_id=loc_id,
        delivery_id=delivery_id,
    ):
        logger.info(
            "Processing update delivery request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/update",
                    "loc_id": loc_id,
                    "delivery_id": delivery_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update delivery failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/update",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.update_delivery(
            data=data,
            delivery_id=delivery_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Delivery updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/update",
                        "loc_id": loc_id,
                        "delivery_id": delivery_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/update",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Update Delivery Status
@deliveries_router.put("/update-status", response_model=Respons[UpdateDeliveryStatusControllerReadDto])
def update_delivery_status(
    data: UpdateDeliveryStatusControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update delivery status"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "update_delivery_status",
        loc_id=loc_id,
        delivery_id=data.delivery_id,
    ):
        logger.info(
            "Processing update delivery status request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/update-status",
                    "loc_id": loc_id,
                    "delivery_id": data.delivery_id,
                    "new_status": data.delivery_status,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update delivery status failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/update-status",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.update_delivery_status(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Delivery status updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/update-status",
                        "loc_id": loc_id,
                        "delivery_id": data.delivery_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery status update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/update-status",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Dispatch Delivery
@deliveries_router.put("/dispatch", response_model=Respons[DispatchDeliveryControllerReadDto])
def dispatch_delivery(
    data: DispatchDeliveryControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Dispatch a delivery (mark as OUT_FOR_DELIVERY)"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "dispatch_delivery",
        loc_id=loc_id,
        delivery_id=data.delivery_id,
    ):
        logger.info(
            "Processing dispatch delivery request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/dispatch",
                    "loc_id": loc_id,
                    "delivery_id": data.delivery_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-update"]
        )

        if not is_authorized:
            logger.warning(
                "Dispatch delivery failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/dispatch",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.dispatch_delivery(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Delivery dispatched successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/dispatch",
                        "loc_id": loc_id,
                        "delivery_id": data.delivery_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery dispatch failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/dispatch",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Complete Delivery
@deliveries_router.put("/complete", response_model=Respons[CompleteDeliveryControllerReadDto])
def complete_delivery(
    data: CompleteDeliveryControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Complete a delivery (mark as DELIVERED)"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "complete_delivery",
        loc_id=loc_id,
        delivery_id=data.delivery_id,
    ):
        logger.info(
            "Processing complete delivery request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/complete",
                    "loc_id": loc_id,
                    "delivery_id": data.delivery_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-update"]
        )

        if not is_authorized:
            logger.warning(
                "Complete delivery failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/complete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.complete_delivery(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Delivery completed successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/complete",
                        "loc_id": loc_id,
                        "delivery_id": data.delivery_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery completion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/complete",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 8. Cancel Delivery
@deliveries_router.put("/cancel", response_model=Respons[CancelDeliveryControllerReadDto])
def cancel_delivery(
    data: CancelDeliveryControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Cancel a delivery"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "cancel_delivery",
        loc_id=loc_id,
        delivery_id=data.delivery_id,
    ):
        logger.info(
            "Processing cancel delivery request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/cancel",
                    "loc_id": loc_id,
                    "delivery_id": data.delivery_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-update"]
        )

        if not is_authorized:
            logger.warning(
                "Cancel delivery failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/cancel",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.cancel_delivery(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Delivery cancelled successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/cancel",
                        "loc_id": loc_id,
                        "delivery_id": data.delivery_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery cancellation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/cancel",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 9. Delete Delivery
@deliveries_router.delete("/delete", response_model=Respons[DeleteDeliveryControllerReadDto])
def delete_delivery(
    delivery_id: str = Query(..., description="Delivery ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Hard delete a delivery"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "delete_delivery",
        loc_id=loc_id,
        delivery_id=delivery_id,
    ):
        logger.info(
            "Processing delete delivery request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/delete",
                    "loc_id": loc_id,
                    "delivery_id": delivery_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete delivery failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        from src.entities.deliveries.deliveries_write_dto import DeleteDeliveryServiceWriteDto
        delete_data = DeleteDeliveryServiceWriteDto(delivery_id=delivery_id)

        service_result = DeliveriesService.delete_delivery(
            data=delete_data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Delivery deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/delete",
                        "loc_id": loc_id,
                        "delivery_id": delivery_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delivery deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/delete",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 10. Get Deliveries Statistics
@deliveries_router.get("/statistics", response_model=Respons[GetDeliveriesStatisticsControllerReadDto])
def get_deliveries_statistics(
    from_date: Optional[str] = Query(None, description="Filter by date from (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter by date to (YYYY-MM-DD)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get delivery statistics"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext(
        "deliveries",
        "get_deliveries_statistics",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=loc_id,
    ):
        logger.info(
            "Processing get deliveries statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/deliveries/statistics",
                    "loc_id": loc_id,
                    "from_date": from_date,
                    "to_date": to_date,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-deliveries-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get deliveries statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = DeliveriesService.get_deliveries_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            from_date=from_date,
            to_date=to_date,
        )

        if service_result.success:
            logger.info(
                "Deliveries statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/statistics",
                        "loc_id": loc_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Deliveries statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/deliveries/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

