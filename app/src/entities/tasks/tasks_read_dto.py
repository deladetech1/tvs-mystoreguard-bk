from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.tasks.tasks_base import TaskBase


# =====================================================
# NESTED READ MODELS
# =====================================================

class GroupMemberDetail(BaseModel):
    """A member of a group target (only populated when target_type == GROUP)."""
    user_id: str
    fullname: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None


class TaskStepTargetRead(BaseModel):
    id: str
    target_kind: str
    target_type: str
    target_id: str
    target_name: Optional[str] = None
    members: List[GroupMemberDetail] = Field(
        default_factory=list, description="Group members (fullname/email/contact); empty for USER targets")


class TaskStepRead(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    display_order: int = 0
    location_id: Optional[str] = None
    status: str
    is_available: bool = Field(False, description="All prerequisite steps are COMPLETED")
    claimed_by: Optional[str] = None
    claimed_by_name: Optional[str] = None
    claimed_at: Optional[datetime] = None
    done_by: Optional[str] = None
    done_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    depends_on: List[str] = Field(default_factory=list)
    targets: List[TaskStepTargetRead] = Field(default_factory=list)


# =====================================================
# TASK READ DTOs
# =====================================================

class TaskReadBase(TaskBase):
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    template_id: Optional[str] = None
    status: str
    due_date: Optional[datetime] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    customer_name: Optional[str] = None
    steps: List[TaskStepRead] = Field(default_factory=list)


class CreateTaskControllerReadDto(TaskReadBase):
    pass


class CreateTaskServiceReadDto(TaskReadBase):
    pass


class UpdateTaskControllerReadDto(TaskReadBase):
    pass


class UpdateTaskServiceReadDto(TaskReadBase):
    pass


class GetTaskControllerReadDto(TaskReadBase):
    pass


class GetTaskServiceReadDto(TaskReadBase):
    pass


class GetTasksControllerReadDto(TaskReadBase):
    pass


class GetTasksServiceReadDto(TaskReadBase):
    pass


# Step actions and cancel all return the updated task.
class StepActionControllerReadDto(TaskReadBase):
    pass


class StepActionServiceReadDto(TaskReadBase):
    pass


class CancelTaskControllerReadDto(TaskReadBase):
    pass


class DeleteTaskReadBase(BaseModel):
    task_id: str
    message: str


class DeleteTaskControllerReadDto(DeleteTaskReadBase):
    pass


class DeleteTaskServiceReadDto(DeleteTaskReadBase):
    pass


# =====================================================
# NOTIFICATION SETTINGS READ DTOs
# =====================================================

class TaskNotificationSettingsReadBase(BaseModel):
    user_id: str
    opt_in: bool = True
    reminder_interval_minutes: int = 120


class TaskNotificationSettingsControllerReadDto(TaskNotificationSettingsReadBase):
    pass


class TaskNotificationSettingsServiceReadDto(TaskNotificationSettingsReadBase):
    pass


# =====================================================
# STATISTICS
# =====================================================

class TaskStatisticsReadBase(BaseModel):
    """Aggregate task/job statistics for the business."""
    # Jobs
    total_tasks: int = 0
    active: int = 0
    completed: int = 0
    cancelled: int = 0
    overdue: int = Field(0, description="ACTIVE jobs past their due_date")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Job count per task_type")
    # Steps
    total_steps: int = 0
    steps_todo: int = 0
    steps_in_progress: int = 0
    steps_done: int = 0
    steps_completed: int = 0
    steps_cancelled: int = 0
    pending_approvals: int = Field(0, description="DONE steps in active jobs awaiting approval")


class TaskStatisticsControllerReadDto(TaskStatisticsReadBase):
    pass


class TaskStatisticsServiceReadDto(TaskStatisticsReadBase):
    pass
