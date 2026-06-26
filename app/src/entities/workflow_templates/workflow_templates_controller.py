from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_with_permission, verify_subscription_active
from src.entities.workflow_templates.workflow_templates_service import WorkflowTemplatesService
from src.entities.workflow_templates.workflow_templates_write_dto import (
    CreateWorkflowTemplateControllerWriteDto,
    UpdateWorkflowTemplateControllerWriteDto,
    DeleteWorkflowTemplateControllerWriteDto,
)
from src.entities.workflow_templates.workflow_templates_read_dto import (
    CreateWorkflowTemplateControllerReadDto,
    UpdateWorkflowTemplateControllerReadDto,
    DeleteWorkflowTemplateControllerReadDto,
    GetWorkflowTemplateControllerReadDto,
    GetWorkflowTemplatesControllerReadDto,
    WorkflowTemplateStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

workflow_templates_router = APIRouter(prefix="/workflow-templates", tags=["Workflow Templates"])
logger = get_logger("workflow_templates")

MANAGE_PERMISSION = "permission-msg-tasks-manage-templates"
GET_PERMISSION = "permission-msg-tasks-get"


def _require(current_user, permissions):
    if not AuthService.has_any_permission(user_roles=current_user.data, required_permissions=permissions):
        raise HTTPException(status_code=403, detail="Unauthorized access")


@workflow_templates_router.post("/add", response_model=Respons[CreateWorkflowTemplateControllerReadDto])
def create_workflow_template(
    data: CreateWorkflowTemplateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Create a reusable workflow template (manager-gated)."""
    with LogContext("workflow_templates", "create_workflow_template", name=data.name):
        _require(current_user, [MANAGE_PERMISSION])
        return WorkflowTemplatesService.create_template(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus["org_id"],
            bus_id=org_bus["bus_id"],
            created_by=current_user.data[0].user_id,
        )


@workflow_templates_router.put("/update", response_model=Respons[UpdateWorkflowTemplateControllerReadDto])
def update_workflow_template(
    data: UpdateWorkflowTemplateControllerWriteDto,
    template_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Update a workflow template; passing `steps` fully replaces its steps."""
    with LogContext("workflow_templates", "update_workflow_template", template_id=template_id):
        _require(current_user, [MANAGE_PERMISSION])
        return WorkflowTemplatesService.update_template(
            data=data,
            template_id=template_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus["org_id"],
            bus_id=org_bus["bus_id"],
            updated_by=current_user.data[0].user_id,
        )


@workflow_templates_router.get("/get", response_model=Respons[GetWorkflowTemplateControllerReadDto])
def get_workflow_template(
    template_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Get a single workflow template with its steps."""
    with LogContext("workflow_templates", "get_workflow_template", template_id=template_id):
        _require(current_user, [GET_PERMISSION, MANAGE_PERMISSION])
        return WorkflowTemplatesService.get_template(
            template_id=template_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus["org_id"],
            bus_id=org_bus["bus_id"],
        )


@workflow_templates_router.get("/statistics", response_model=Respons[WorkflowTemplateStatisticsControllerReadDto])
def get_workflow_template_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Aggregate workflow-template statistics for the business."""
    with LogContext("workflow_templates", "get_workflow_template_statistics", tenant_id=current_user.data[0].tenant_id):
        _require(current_user, [GET_PERMISSION, MANAGE_PERMISSION])
        return WorkflowTemplatesService.get_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus["org_id"],
            bus_id=org_bus["bus_id"],
        )


@workflow_templates_router.get("/list", response_model=Respons[GetWorkflowTemplatesControllerReadDto])
def get_workflow_templates(
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    is_active: Optional[bool] = Query(None, description="Filter by active state"),
    search: Optional[str] = Query(None, description="Search in name"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """List workflow templates for the business."""
    with LogContext("workflow_templates", "get_workflow_templates", tenant_id=current_user.data[0].tenant_id):
        _require(current_user, [GET_PERMISSION, MANAGE_PERMISSION])
        return WorkflowTemplatesService.get_templates(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus["org_id"],
            bus_id=org_bus["bus_id"],
            template_type=template_type,
            is_active=is_active,
            search=search,
            page=page,
            size=size,
        )


@workflow_templates_router.delete("/delete", response_model=Respons[DeleteWorkflowTemplateControllerReadDto])
def delete_workflow_template(
    data: DeleteWorkflowTemplateControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Soft-delete a workflow template (manager-gated)."""
    with LogContext("workflow_templates", "delete_workflow_template", template_id=data.template_id):
        _require(current_user, [MANAGE_PERMISSION])
        return WorkflowTemplatesService.delete_template(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus["org_id"],
            bus_id=org_bus["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )
