from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.estimates.estimates_service import EstimatesService
from src.entities.estimates.estimates_write_dto import (
    CreateEstimateControllerWriteDto,
    UpdateEstimateControllerWriteDto,
    UpdateEstimateStatusControllerWriteDto,
    DeleteEstimateControllerWriteDto,
)
from src.entities.estimates.estimates_read_dto import (
    CreateEstimateControllerReadDto,
    UpdateEstimateControllerReadDto,
    GetEstimateControllerReadDto,
    GetEstimateListControllerReadDto,
    UpdateEstimateStatusControllerReadDto,
    DeleteEstimateControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

estimates_router = APIRouter(prefix="/estimates", tags=["Estimates"])
logger = get_logger("estimates")


# 1. Create
@estimates_router.post("/add", response_model=Respons[CreateEstimateControllerReadDto])
def create_estimate(
    data: CreateEstimateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create an estimate from a template, pricing each captured line item."""
    with LogContext("estimates", "create_estimate", template_id=data.template_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimates-create"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimatesService.create_estimate(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )


# 2. Update (edit a draft/sent estimate; re-prices against its snapshot)
@estimates_router.put("/update", response_model=Respons[UpdateEstimateControllerReadDto])
def update_estimate(
    data: UpdateEstimateControllerWriteDto,
    estimate_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Edit an estimate and (when items are supplied) re-price it."""
    with LogContext("estimates", "update_estimate", estimate_id=estimate_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimates-update"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimatesService.update_estimate(
            data=data,
            estimate_id=estimate_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            updated_by=current_user.data[0].user_id,
        )


# 3. Update status
@estimates_router.patch("/status", response_model=Respons[UpdateEstimateStatusControllerReadDto])
def update_estimate_status(
    data: UpdateEstimateStatusControllerWriteDto,
    estimate_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Move an estimate through its lifecycle (DRAFT -> SENT -> ACCEPTED, etc.)."""
    with LogContext("estimates", "update_estimate_status", estimate_id=estimate_id, status=data.status):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimates-update"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimatesService.update_status(
            data=data,
            estimate_id=estimate_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            updated_by=current_user.data[0].user_id,
        )


# 4. Get
@estimates_router.get("/get", response_model=Respons[GetEstimateControllerReadDto])
def get_estimate(
    estimate_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single estimate with its priced line items."""
    with LogContext("estimates", "get_estimate", estimate_id=estimate_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimates-get"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimatesService.get_estimate(
            estimate_id=estimate_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )


# 5. List
@estimates_router.get("/list", response_model=Respons[GetEstimateListControllerReadDto])
def list_estimates(
    status: Optional[str] = Query(None, description="Filter by status"),
    customer_id: Optional[str] = Query(None, description="Filter by customer"),
    template_id: Optional[str] = Query(None, description="Filter by template"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """List estimates with filters and pagination."""
    with LogContext("estimates", "list_estimates", tenant_id=current_user.data[0].tenant_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimates-get"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimatesService.list_estimates(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            status=status,
            customer_id=customer_id,
            template_id=template_id,
            page=page,
            size=size,
        )


# 6. Delete
@estimates_router.delete("/delete", response_model=Respons[DeleteEstimateControllerReadDto])
def delete_estimate(
    data: DeleteEstimateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Soft-delete an estimate."""
    with LogContext("estimates", "delete_estimate", estimate_id=data.estimate_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimates-delete"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimatesService.delete_estimate(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            deleted_by=current_user.data[0].user_id,
        )
