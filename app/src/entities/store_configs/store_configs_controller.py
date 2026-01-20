from fastapi import APIRouter, Depends, HTTPException
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.store_configs.store_configs_service import StoreConfigsService
from src.entities.store_configs.store_configs_write_dto import (
    CreateOrUpdateStoreConfigControllerWriteDto,
)
from src.entities.store_configs.store_configs_read_dto import (
    CreateOrUpdateStoreConfigControllerReadDto,
    GetStoreConfigControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

store_configs_router = APIRouter(prefix="/store-configs", tags=["Store Configs"])
logger = get_logger("store_configs")


# 1. Create or Update Store Config (Upsert)
@store_configs_router.post("/setup", response_model=Respons[CreateOrUpdateStoreConfigControllerReadDto])
def create_or_update_config(
    data: CreateOrUpdateStoreConfigControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create or update a store config. If config exists (based on tenant_id, org_id, bus_id, loc_id), it will be updated. Otherwise, a new config will be created."""
    with LogContext(
        "store_configs",
        "create_or_update_config",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing create/update store config request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-configs/setup",
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
            required_permissions=["permission-msg-store-config-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create/update store config failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-configs/setup",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreConfigsService.create_or_update_config(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            user_id=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Store config created/updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-configs/setup",
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
                f"Store config creation/update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-configs/setup",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Get Store Config
@store_configs_router.get("/get", response_model=Respons[GetStoreConfigControllerReadDto])
def get_config(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a store config by tenant_id, org_id, bus_id, loc_id"""
    with LogContext(
        "store_configs",
        "get_config",
        tenant_id=current_user.data[0].tenant_id,
        loc_id=org_bus_loc["loc_id"],
    ):
        logger.info(
            "Processing get store config request",
            extra={
                "extra_fields": {
                    "endpoint": "/store-configs/get",
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
            required_permissions=["permission-msg-store-config-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get store config failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-configs/get",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreConfigsService.get_config(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
        )

        if service_result.success:
            logger.info(
                "Store config retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-configs/get",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Store config retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/store-configs/get",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


