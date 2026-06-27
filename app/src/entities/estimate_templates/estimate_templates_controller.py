from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.estimate_templates.estimate_templates_service import EstimateTemplatesService
from src.entities.estimate_templates.estimate_templates_write_dto import (
    CreateEstimateTemplateControllerWriteDto,
    UpdateEstimateTemplateControllerWriteDto,
    DeleteEstimateTemplateControllerWriteDto,
)
from src.entities.estimate_templates.estimate_templates_read_dto import (
    CreateEstimateTemplateControllerReadDto,
    UpdateEstimateTemplateControllerReadDto,
    GetEstimateTemplateControllerReadDto,
    GetEstimateTemplateListControllerReadDto,
    DeleteEstimateTemplateControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

estimate_templates_router = APIRouter(prefix="/estimate-templates", tags=["Estimate Templates"])
logger = get_logger("estimate_templates")


# 1. Create
@estimate_templates_router.post("/add", response_model=Respons[CreateEstimateTemplateControllerReadDto])
def create_estimate_template(
    data: CreateEstimateTemplateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new estimate template (the per-domain blueprint)."""
    with LogContext("estimate_templates", "create_estimate_template", name=data.name):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimate-templates-create"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimateTemplatesService.create_template(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )


# 2. Update
@estimate_templates_router.put("/update", response_model=Respons[UpdateEstimateTemplateControllerReadDto])
def update_estimate_template(
    data: UpdateEstimateTemplateControllerWriteDto,
    template_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update an estimate template. Changing its definition bumps the version."""
    with LogContext("estimate_templates", "update_estimate_template", template_id=template_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimate-templates-update"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimateTemplatesService.update_template(
            data=data,
            template_id=template_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )


# 3. Get
@estimate_templates_router.get("/get", response_model=Respons[GetEstimateTemplateControllerReadDto])
def get_estimate_template(
    template_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single estimate template by ID."""
    with LogContext("estimate_templates", "get_estimate_template", template_id=template_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimate-templates-get"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimateTemplatesService.get_template(
            template_id=template_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )


# 4. List
@estimate_templates_router.get("/list", response_model=Respons[GetEstimateTemplateListControllerReadDto])
def list_estimate_templates(
    domain: Optional[str] = Query(None, description="Filter by domain label"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by template name"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """List estimate templates with filters and pagination."""
    with LogContext("estimate_templates", "list_estimate_templates", tenant_id=current_user.data[0].tenant_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimate-templates-get"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimateTemplatesService.list_templates(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            domain=domain,
            is_active=is_active,
            search=search,
            page=page,
            size=size,
        )


# 5. Delete
@estimate_templates_router.delete("/delete", response_model=Respons[DeleteEstimateTemplateControllerReadDto])
def delete_estimate_template(
    data: DeleteEstimateTemplateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Soft-delete an estimate template."""
    with LogContext("estimate_templates", "delete_estimate_template", template_id=data.template_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-estimate-templates-delete"],
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return EstimateTemplatesService.delete_template(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )
