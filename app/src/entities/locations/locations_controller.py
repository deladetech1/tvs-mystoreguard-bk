from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService
from src.entities.locations.locations_service import LocationsService
from src.entities.locations.locations_read_dto import (
    GetLocationsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

locations_router = APIRouter(prefix="/locations", tags=["Locations"])
logger = get_logger("locations")


# Get Locations
@locations_router.get("/list", response_model=Respons[GetLocationsControllerReadDto])
def get_locations(
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
):
    """Get list of all locations for the tenant"""
    with LogContext(
        "locations",
        "get_locations",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get locations request",
            extra={
                "extra_fields": {
                    "endpoint": "/locations/list",
                    "tenant_id": current_user.data[0].tenant_id,
                    "is_active": is_active,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-products-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get locations failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/locations/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = LocationsService.get_locations(
            tenant_id=current_user.data[0].tenant_id,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Locations retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/locations/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Locations retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/locations/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

