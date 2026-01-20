from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.warehouse_transfers.warehouse_transfers_service import WarehouseTransfersService
from src.entities.warehouse_transfers.warehouse_transfers_write_dto import (
    CreateWarehouseTransferControllerWriteDto,
    ApproveWarehouseTransferControllerWriteDto,
    UpdateWarehouseTransferControllerWriteDto,
)
from src.entities.warehouse_transfers.warehouse_transfers_read_dto import (
    CreateWarehouseTransferControllerReadDto,
    GetWarehouseTransferControllerReadDto,
    GetWarehouseTransfersControllerReadDto,
    ApproveWarehouseTransferControllerReadDto,
    GetWarehouseTransferStatisticsControllerReadDto,
    UpdateWarehouseTransferControllerReadDto,
    DeleteWarehouseTransferControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

warehouse_transfers_router = APIRouter(prefix="/warehouse-transfers", tags=["Warehouse Transfers"])
logger = get_logger("warehouse_transfers")


# 1. Create Warehouse Transfer
@warehouse_transfers_router.post("/create", response_model=Respons[CreateWarehouseTransferControllerReadDto])
def create_warehouse_transfer(
    data: CreateWarehouseTransferControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new warehouse transfer request"""
    with LogContext(
        "warehouse_transfers",
        "create_warehouse_transfer",
        product_id=data.product_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing create warehouse transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-transfers/create",
                    "product_id": data.product_id,
                    "loc_id": org_bus_loc["loc_id"],
                    "qty": data.qty,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-transfers-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create warehouse transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/create",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseTransfersService.create_warehouse_transfer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            source_loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse transfer created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/create",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse transfer creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/create",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Approve/Reject Warehouse Transfer
@warehouse_transfers_router.put("/approve", response_model=Respons[ApproveWarehouseTransferControllerReadDto])
def approve_warehouse_transfer(
    data: ApproveWarehouseTransferControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Approve or reject a warehouse transfer"""
    with LogContext(
        "warehouse_transfers",
        "approve_warehouse_transfer",
        transfer_id=data.transfer_id,
    ):
        logger.info(
            "Processing approve/reject warehouse transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-transfers/approve",
                    "transfer_id": data.transfer_id,
                    "action": data.action,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-transfers-approve"]
        )

        if not is_authorized:
            logger.warning(
                "Approve warehouse transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/approve",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseTransfersService.approve_warehouse_transfer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            approved_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse transfer approval processed successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/approve",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse transfer approval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/approve",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Warehouse Transfer
@warehouse_transfers_router.get("/get", response_model=Respons[GetWarehouseTransferControllerReadDto])
def get_warehouse_transfer(
    transfer_id: str = Query(..., description="Transfer ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single warehouse transfer by ID"""
    with LogContext(
        "warehouse_transfers",
        "get_warehouse_transfer",
        transfer_id=transfer_id,
    ):
        logger.info(
            "Processing get warehouse transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-transfers/get",
                    "transfer_id": transfer_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-transfers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get warehouse transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/get",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseTransfersService.get_warehouse_transfer(
            transfer_id=transfer_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Warehouse transfer retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/get",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse transfer retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/get",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Warehouse Transfers List
@warehouse_transfers_router.get("/list", response_model=Respons[GetWarehouseTransfersControllerReadDto])
def get_warehouse_transfers(
    status: Optional[str] = Query(None, description="Filter by status"),
    from_date: Optional[str] = Query(None, description="Filter transfers from this date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter transfers to this date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of warehouse transfers with filters and pagination"""
    with LogContext(
        "warehouse_transfers",
        "get_warehouse_transfers",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get warehouse transfers request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-transfers/list",
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
            required_permissions=["permission-msg-warehouse-transfers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get warehouse transfers failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseTransfersService.get_warehouse_transfers(
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
                "Warehouse transfers retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse transfers retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Get Warehouse Transfer Statistics
@warehouse_transfers_router.get("/statistics", response_model=Respons[GetWarehouseTransferStatisticsControllerReadDto])
def get_warehouse_transfer_statistics(
    from_date: Optional[str] = Query(None, description="Filter transfers from this date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter transfers to this date (YYYY-MM-DD)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get warehouse transfer statistics with optional date filtering"""
    with LogContext(
        "warehouse_transfers",
        "get_warehouse_transfer_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get warehouse transfer statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-transfers/statistics",
                    "from_date": from_date,
                    "to_date": to_date,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-transfers-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get warehouse transfer statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseTransfersService.get_warehouse_transfer_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            source_loc_id=org_bus_loc["loc_id"],
            from_date=from_date,
            to_date=to_date,
        )

        if service_result.success:
            logger.info(
                "Warehouse transfer statistics retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/statistics",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse transfer statistics retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/statistics",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Update Warehouse Transfer
@warehouse_transfers_router.put("/update", response_model=Respons[UpdateWarehouseTransferControllerReadDto])
def update_warehouse_transfer(
    data: UpdateWarehouseTransferControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a warehouse transfer (only allowed when status is PENDING_APPROVAL)"""
    with LogContext(
        "warehouse_transfers",
        "update_warehouse_transfer",
        transfer_id=data.transfer_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing update warehouse transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-transfers/update",
                    "transfer_id": data.transfer_id,
                    "loc_id": org_bus_loc["loc_id"],
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-transfers-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update warehouse transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/update",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseTransfersService.update_warehouse_transfer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse transfer updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/update",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse transfer update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/update",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 7. Delete Warehouse Transfer
@warehouse_transfers_router.delete("/delete", response_model=Respons[DeleteWarehouseTransferControllerReadDto])
def delete_warehouse_transfer(
    transfer_id: str = Query(..., description="Transfer ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a warehouse transfer (only allowed when status is PENDING_APPROVAL)"""
    with LogContext(
        "warehouse_transfers",
        "delete_warehouse_transfer",
        transfer_id=transfer_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing delete warehouse transfer request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-transfers/delete",
                    "transfer_id": transfer_id,
                    "loc_id": org_bus_loc["loc_id"],
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-transfers-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete warehouse transfer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        from src.entities.warehouse_transfers.warehouse_transfers_write_dto import DeleteWarehouseTransferServiceWriteDto
        
        service_result = WarehouseTransfersService.delete_warehouse_transfer(
            data=DeleteWarehouseTransferServiceWriteDto(transfer_id=transfer_id),
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse transfer deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/delete",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse transfer deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-transfers/delete",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


