from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.store_transfers.store_transfers_service import StoreTransfersService
from src.entities.store_transfers.store_transfers_write_dto import (
    CreateStoreTransferControllerWriteDto,
    ApproveStoreTransferControllerWriteDto,
    UpdateStoreTransferControllerWriteDto,
)
from src.entities.store_transfers.store_transfers_read_dto import (
    CreateStoreTransferControllerReadDto,
    GetStoreTransferControllerReadDto,
    GetStoreTransfersControllerReadDto,
    ApproveStoreTransferControllerReadDto,
    GetStoreTransferStatisticsControllerReadDto,
    UpdateStoreTransferControllerReadDto,
    DeleteStoreTransferControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

store_transfers_router = APIRouter(prefix="/store-transfers", tags=["Store Transfers"])
logger = get_logger("store_transfers")


# 1. Create Store Transfer
@store_transfers_router.post("/create", response_model=Respons[CreateStoreTransferControllerReadDto])
def create_store_transfer(
    data: CreateStoreTransferControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new store transfer request"""
    with LogContext(
        "store_transfers",
        "create_store_transfer",
        product_id=data.product_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing create store transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-transfers/create",
                    "product_id": data.product_id,
                    "loc_id": org_bus_loc["loc_id"],
                    "qty": data.qty,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-transfers-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create store transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/create",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreTransfersService.create_store_transfer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            source_loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Store transfer created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/create",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store transfer creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/create",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Approve/Reject Store Transfer
@store_transfers_router.put("/approve", response_model=Respons[ApproveStoreTransferControllerReadDto])
def approve_store_transfer(
    data: ApproveStoreTransferControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Approve or reject a store transfer"""
    with LogContext(
        "store_transfers",
        "approve_store_transfer",
        transfer_id=data.transfer_id,
    ):
        logger.info(
            "Processing approve/reject store transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-transfers/approve",
                    "transfer_id": data.transfer_id,
                    "action": data.action,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-transfers-approve"]
        )

        if not is_authorized:
            logger.warning(
                "Approve store transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/approve",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreTransfersService.approve_store_transfer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            approved_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Store transfer approval processed successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/approve",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store transfer approval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/approve",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Store Transfer
@store_transfers_router.get("/get", response_model=Respons[GetStoreTransferControllerReadDto])
def get_store_transfer(
    transfer_id: str = Query(..., description="Transfer ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single store transfer by ID"""
    with LogContext(
        "store_transfers",
        "get_store_transfer",
        transfer_id=transfer_id,
    ):
        logger.info(
            "Processing get store transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-transfers/get",
                    "transfer_id": transfer_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-transfers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get store transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/get",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreTransfersService.get_store_transfer(
            transfer_id=transfer_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Store transfer retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/get",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store transfer retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/get",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Store Transfers List
@store_transfers_router.get("/list", response_model=Respons[GetStoreTransfersControllerReadDto])
def get_store_transfers(
    status: Optional[str] = Query(None, description="Filter by status"),
    from_date: Optional[str] = Query(None, description="Filter transfers from this date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter transfers to this date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of store transfers with filters and pagination"""
    with LogContext(
        "store_transfers",
        "get_store_transfers",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get store transfers request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-transfers/list",
                    "status": status,
                    "from_date": from_date,
                    "to_date": to_date,
                    "page": page,
                    "size": size,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-transfers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get store transfers failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreTransfersService.get_store_transfers(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            source_loc_id=org_bus_loc["loc_id"],
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Store transfers retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store transfers retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Get Store Transfer Statistics
@store_transfers_router.get("/statistics", response_model=Respons[GetStoreTransferStatisticsControllerReadDto])
def get_store_transfer_statistics(
    from_date: Optional[str] = Query(None, description="Filter transfers from this date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter transfers to this date (YYYY-MM-DD)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get store transfer statistics with optional date filtering"""
    with LogContext(
        "store_transfers",
        "get_store_transfer_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get store transfer statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-transfers/statistics",
                    "from_date": from_date,
                    "to_date": to_date,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-transfers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get store transfer statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreTransfersService.get_store_transfer_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            source_loc_id=org_bus_loc["loc_id"],
            from_date=from_date,
            to_date=to_date,
        )

        if service_result.success:
            logger.info(
                "Store transfer statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store transfer statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Update Store Transfer
@store_transfers_router.put("/update", response_model=Respons[UpdateStoreTransferControllerReadDto])
def update_store_transfer(
    data: UpdateStoreTransferControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a store transfer (only allowed when status is PENDING_APPROVAL)"""
    with LogContext(
        "store_transfers",
        "update_store_transfer",
        transfer_id=data.transfer_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing update store transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-transfers/update",
                    "transfer_id": data.transfer_id,
                    "loc_id": org_bus_loc["loc_id"],
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-transfers-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update store transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/update",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreTransfersService.update_store_transfer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Store transfer updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/update",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store transfer update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/update",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Delete Store Transfer
@store_transfers_router.delete("/delete", response_model=Respons[DeleteStoreTransferControllerReadDto])
def delete_store_transfer(
    transfer_id: str = Query(..., description="Transfer ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a store transfer (only allowed when status is PENDING_APPROVAL)"""
    with LogContext(
        "store_transfers",
        "delete_store_transfer",
        transfer_id=transfer_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing delete store transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-transfers/delete",
                    "transfer_id": transfer_id,
                    "loc_id": org_bus_loc["loc_id"],
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-transfers-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete store transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        from src.entities.store_transfers.store_transfers_write_dto import DeleteStoreTransferServiceWriteDto
        
        service_result = StoreTransfersService.delete_store_transfer(
            data=DeleteStoreTransferServiceWriteDto(transfer_id=transfer_id),
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Store transfer deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/delete",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store transfer deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-transfers/delete",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


