from fastapi import APIRouter, Depends, HTTPException
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.warehouse_configs.warehouse_configs_service import WarehouseConfigsService
from src.entities.warehouse_configs.warehouse_configs_write_dto import (
    CreateOrUpdateWarehouseConfigControllerWriteDto,
)
from src.entities.warehouse_configs.warehouse_configs_read_dto import (
    CreateOrUpdateWarehouseConfigControllerReadDto,
    GetWarehouseConfigControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

warehouse_configs_router = APIRouter(prefix="/warehouse-configs", tags=["Warehouse Configs"])
logger = get_logger("warehouse_configs")


# 1. Create or Update Warehouse Config (Upsert)
@warehouse_configs_router.post("/setup", response_model=Respons[CreateOrUpdateWarehouseConfigControllerReadDto])
def create_or_update_config(
    data: CreateOrUpdateWarehouseConfigControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create or update a warehouse config. If config exists (based on tenant_id, org_id, bus_id, loc_id), it will be updated. Otherwise, a new config will be created."""
    with LogContext(
        "warehouse_configs",
        "create_or_update_config",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing create/update warehouse config request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-configs/setup",
                    "tenant_id": current_user.data[0].tenant_id,
                    "org_id": org_bus_loc["org_id"],
                    "bus_id": org_bus_loc["bus_id"],
                    "loc_id": org_bus_loc["loc_id"],
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-config-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create/update warehouse config failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-configs/setup",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseConfigsService.create_or_update_config(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            user_id=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Warehouse config created/updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-configs/setup",
                        "config_id": (
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
                f"Warehouse config creation/update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-configs/setup",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Get Warehouse Config
@warehouse_configs_router.get("/get", response_model=Respons[GetWarehouseConfigControllerReadDto])
def get_config(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a warehouse config by tenant_id, org_id, bus_id, loc_id"""
    with LogContext(
        "warehouse_configs",
        "get_config",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing get warehouse config request",
            extra={
                "extra_fields": {
                    "endpoint": "/warehouse-configs/get",
                    "tenant_id": current_user.data[0].tenant_id,
                    "org_id": org_bus_loc["org_id"],
                    "bus_id": org_bus_loc["bus_id"],
                    "loc_id": org_bus_loc["loc_id"],
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-warehouse-config-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get warehouse config failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-configs/get",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = WarehouseConfigsService.get_config(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
        )

        if service_result.success:
            logger.info(
                "Warehouse config retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-configs/get",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Warehouse config retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/warehouse-configs/get",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

