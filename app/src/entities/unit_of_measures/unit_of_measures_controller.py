from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService
from src.entities.unit_of_measures.unit_of_measures_service import UnitOfMeasuresService
from src.entities.unit_of_measures.unit_of_measures_read_dto import (
    GetUnitOfMeasuresControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

unit_of_measures_router = APIRouter(prefix="/unit-of-measures", tags=["Unit of Measures"])
logger = get_logger("unit_of_measures")


# Get Unit of Measures
@unit_of_measures_router.get("/list", response_model=Respons[GetUnitOfMeasuresControllerReadDto])
def get_unit_of_measures(
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
):
    """Get list of all unit of measures for the tenant"""
    with LogContext(
        "unit_of_measures",
        "get_unit_of_measures",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get unit of measures request",
            extra={
                "extra_fields": {
                    "endpoint": "/unit-of-measures/list",
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
                "Get unit of measures failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/unit-of-measures/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = UnitOfMeasuresService.get_unit_of_measures(
            tenant_id=current_user.data[0].tenant_id,
            is_active=is_active,
        )

        if service_result.success:
            logger.info(
                "Unit of measures retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/unit-of-measures/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Unit of measures retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/unit-of-measures/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

