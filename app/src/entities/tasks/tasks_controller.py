from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_with_permission, verify_subscription_active
from src.entities.tasks.tasks_service import TasksService
from src.entities.tasks.tasks_write_dto import (
    CreateTaskControllerWriteDto,
    UpdateTaskControllerWriteDto,
    ClaimStepControllerWriteDto,
    StartStepControllerWriteDto,
    DoneStepControllerWriteDto,
    ApproveStepControllerWriteDto,
    RejectStepControllerWriteDto,
    CancelTaskControllerWriteDto,
    TaskNotificationSettingsWriteDto,
    RemoveStepControllerWriteDto,
)
from src.entities.tasks.tasks_read_dto import (
    CreateTaskControllerReadDto,
    UpdateTaskControllerReadDto,
    GetTaskControllerReadDto,
    GetTasksControllerReadDto,
    StepActionControllerReadDto,
    CancelTaskControllerReadDto,
    TaskNotificationSettingsControllerReadDto,
    TaskStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

tasks_router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = get_logger("tasks")

GET = "permission-msg-tasks-get"
CREATE = "permission-msg-tasks-create"
UPDATE = "permission-msg-tasks-update"
DELETE = "permission-msg-tasks-delete"
APPROVE = "permission-msg-tasks-approve"


def _require(current_user, permissions):
    if not AuthService.has_any_permission(user_roles=current_user.data, required_permissions=permissions):
        raise HTTPException(status_code=403, detail="Unauthorized access")


def _ctx(current_user, org_bus):
    return {
        "tenant_id": current_user.data[0].tenant_id,
        "org_id": org_bus["org_id"],
        "bus_id": org_bus["bus_id"],
        "user_id": current_user.data[0].user_id,
    }


# ---------------- task CRUD ----------------

@tasks_router.post("/add", response_model=Respons[CreateTaskControllerReadDto])
def create_task(
    data: CreateTaskControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _sub: dict = Depends(verify_subscription_active),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Create a job, from a template or with ad-hoc steps."""
    with LogContext("tasks", "create_task", title=data.title):
        _require(current_user, [CREATE])
        c = _ctx(current_user, org_bus)
        return TasksService.create_task(data=data, tenant_id=c["tenant_id"], org_id=c["org_id"],
                                        bus_id=c["bus_id"], created_by=c["user_id"])


@tasks_router.put("/update", response_model=Respons[UpdateTaskControllerReadDto])
def update_task(
    data: UpdateTaskControllerWriteDto,
    task_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _sub: dict = Depends(verify_subscription_active),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Update task metadata (lifecycle is driven by step actions)."""
    with LogContext("tasks", "update_task", task_id=task_id):
        _require(current_user, [UPDATE])
        c = _ctx(current_user, org_bus)
        return TasksService.update_task(data=data, task_id=task_id, tenant_id=c["tenant_id"],
                                        org_id=c["org_id"], bus_id=c["bus_id"], updated_by=c["user_id"])


@tasks_router.get("/statistics", response_model=Respons[TaskStatisticsControllerReadDto])
def get_task_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Aggregate job + step statistics for the business."""
    with LogContext("tasks", "get_task_statistics", tenant_id=current_user.data[0].tenant_id):
        _require(current_user, [GET])
        c = _ctx(current_user, org_bus)
        return TasksService.get_statistics(c["tenant_id"], c["org_id"], c["bus_id"])


@tasks_router.get("/get", response_model=Respons[GetTaskControllerReadDto])
def get_task(
    task_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Get a single job with its steps."""
    with LogContext("tasks", "get_task", task_id=task_id):
        _require(current_user, [GET])
        c = _ctx(current_user, org_bus)
        return TasksService.get_task(task_id, c["tenant_id"], c["org_id"], c["bus_id"])


@tasks_router.get("/list", response_model=Respons[GetTasksControllerReadDto])
def get_tasks(
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    template_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """List jobs for the business with filters and pagination."""
    with LogContext("tasks", "get_tasks", tenant_id=current_user.data[0].tenant_id):
        _require(current_user, [GET])
        c = _ctx(current_user, org_bus)
        return TasksService.get_tasks(
            c["tenant_id"], c["org_id"], c["bus_id"], status=status, task_type=task_type,
            template_id=template_id, customer_id=customer_id, search=search, page=page, size=size)


@tasks_router.post("/cancel", response_model=Respons[CancelTaskControllerReadDto])
def cancel_task(
    data: CancelTaskControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _sub: dict = Depends(verify_subscription_active),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Cancel a job and all its non-terminal steps."""
    with LogContext("tasks", "cancel_task", task_id=data.task_id):
        _require(current_user, [UPDATE, DELETE])
        c = _ctx(current_user, org_bus)
        return TasksService.cancel_task(data.task_id, c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])


# ---------------- step removal (single-step convenience) ----------------

@tasks_router.delete("/steps/remove", response_model=Respons[StepActionControllerReadDto])
def remove_step(
    data: RemoveStepControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _sub: dict = Depends(verify_subscription_active),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Remove a single unfinished step from an active job."""
    with LogContext("tasks", "remove_step", step_id=data.step_id):
        _require(current_user, [UPDATE])
        c = _ctx(current_user, org_bus)
        return TasksService.remove_step(
            data.task_id, data.step_id, c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])


# ---------------- step actions ----------------

@tasks_router.post("/steps/claim", response_model=Respons[StepActionControllerReadDto])
def claim_step(
    data: ClaimStepControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Reserve an available step for yourself (first eligible assignee wins)."""
    with LogContext("tasks", "claim_step", step_id=data.step_id):
        _require(current_user, [UPDATE])
        c = _ctx(current_user, org_bus)
        return TasksService.claim_step(data.task_id, data.step_id, c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])


@tasks_router.post("/steps/start", response_model=Respons[StepActionControllerReadDto])
def start_step(
    data: StartStepControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Begin work on a step (auto-claims it to you if unclaimed)."""
    with LogContext("tasks", "start_step", step_id=data.step_id):
        _require(current_user, [UPDATE])
        c = _ctx(current_user, org_bus)
        return TasksService.start_step(data.task_id, data.step_id, c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])


@tasks_router.post("/steps/done", response_model=Respons[StepActionControllerReadDto])
def done_step(
    data: DoneStepControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Mark your in-progress step DONE; its approvers get notified."""
    with LogContext("tasks", "done_step", step_id=data.step_id):
        _require(current_user, [UPDATE])
        c = _ctx(current_user, org_bus)
        return TasksService.done_step(data.task_id, data.step_id, c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])


@tasks_router.post("/steps/approve", response_model=Respons[StepActionControllerReadDto])
def approve_step(
    data: ApproveStepControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Approve a DONE step (approvers only); activates downstream steps."""
    with LogContext("tasks", "approve_step", step_id=data.step_id):
        _require(current_user, [APPROVE])
        c = _ctx(current_user, org_bus)
        return TasksService.approve_step(data.task_id, data.step_id, c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])


@tasks_router.post("/steps/reject", response_model=Respons[StepActionControllerReadDto])
def reject_step(
    data: RejectStepControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Send a DONE step back to IN_PROGRESS (approvers only)."""
    with LogContext("tasks", "reject_step", step_id=data.step_id):
        _require(current_user, [APPROVE])
        c = _ctx(current_user, org_bus)
        return TasksService.reject_step(data.task_id, data.step_id, c["tenant_id"], c["org_id"], c["bus_id"],
                                        c["user_id"], reason=data.reason)


# ---------------- per-user notification settings ----------------

@tasks_router.get("/notification-settings", response_model=Respons[TaskNotificationSettingsControllerReadDto])
def get_notification_settings(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Get the current user's task notification settings."""
    with LogContext("tasks", "get_notification_settings", tenant_id=current_user.data[0].tenant_id):
        c = _ctx(current_user, org_bus)
        return TasksService.get_notification_settings(c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])


@tasks_router.put("/notification-settings", response_model=Respons[TaskNotificationSettingsControllerReadDto])
def update_notification_settings(
    data: TaskNotificationSettingsWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus: dict = Depends(get_org_bus_with_permission),
):
    """Update the current user's task notification settings."""
    with LogContext("tasks", "update_notification_settings", tenant_id=current_user.data[0].tenant_id):
        c = _ctx(current_user, org_bus)
        return TasksService.upsert_notification_settings(data, c["tenant_id"], c["org_id"], c["bus_id"], c["user_id"])
