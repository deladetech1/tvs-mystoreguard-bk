from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from src.entities.tasks.tasks_base import TaskBase, TaskType
from src.entities.workflow_templates.workflow_templates_base import StepInput, StepTargetInput


# =====================================================
# CREATE TASK WRITE DTOs
# =====================================================

class CreateTaskWriteBase(TaskBase):
    template_id: Optional[str] = Field(None, description="Spin the job from this template")
    due_date: Optional[datetime] = Field(None, description="When the whole job is due")
    # Ad-hoc steps (when no template) OR per-job overrides (replace the template's steps).
    steps: Optional[List[StepInput]] = Field(None, description="Steps for an ad-hoc job, or to override the template")

    @model_validator(mode="after")
    def _require_steps_or_template(self):
        if not self.template_id and not self.steps:
            raise ValueError("Provide either template_id or steps")
        return self


class CreateTaskControllerWriteDto(CreateTaskWriteBase):
    pass


class CreateTaskServiceWriteDto(CreateTaskWriteBase):
    pass


# =====================================================
# UPDATE TASK WRITE DTOs (metadata only; lifecycle via step actions)
# =====================================================

class UpdateTaskWriteBase(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    task_type: Optional[TaskType] = None
    description: Optional[str] = None
    customer_id: Optional[str] = None
    origin_location_id: Optional[str] = None
    due_date: Optional[datetime] = None


class UpdateTaskControllerWriteDto(UpdateTaskWriteBase):
    pass


class UpdateTaskServiceWriteDto(UpdateTaskWriteBase):
    pass


# =====================================================
# STEP ACTION WRITE DTOs
# =====================================================

class StepActionWriteBase(BaseModel):
    task_id: str
    step_id: str


class ClaimStepControllerWriteDto(StepActionWriteBase):
    pass


class StartStepControllerWriteDto(StepActionWriteBase):
    pass


class DoneStepControllerWriteDto(StepActionWriteBase):
    pass


class ApproveStepControllerWriteDto(StepActionWriteBase):
    pass


class RejectStepControllerWriteDto(StepActionWriteBase):
    reason: Optional[str] = Field(None, description="Why the step was sent back")


# =====================================================
# STEP EDITING WRITE DTOs (per-job tweaks; only while step is TODO/IN_PROGRESS)
# =====================================================

class UpdateStepControllerWriteDto(BaseModel):
    task_id: str
    step_id: str
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    location_id: Optional[str] = None
    targets: Optional[List[StepTargetInput]] = Field(
        None, description="When provided, fully replaces this step's assignees/approvers")


class AddStepControllerWriteDto(BaseModel):
    task_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location_id: Optional[str] = None
    display_order: int = Field(0, ge=0)
    depends_on: List[str] = Field(default_factory=list, description="ids of existing job steps that must complete first")
    targets: List[StepTargetInput] = Field(default_factory=list)


class RemoveStepControllerWriteDto(BaseModel):
    task_id: str
    step_id: str


class SetStepDependenciesControllerWriteDto(BaseModel):
    task_id: str
    step_id: str
    depends_on: List[str] = Field(default_factory=list, description="ids of job steps this step must wait for")


# =====================================================
# CANCEL TASK WRITE DTOs
# =====================================================

class CancelTaskControllerWriteDto(BaseModel):
    task_id: str


# =====================================================
# NOTIFICATION SETTINGS WRITE DTOs
# =====================================================

class TaskNotificationSettingsWriteDto(BaseModel):
    opt_in: Optional[bool] = Field(None, description="Receive task emails")
    reminder_interval_minutes: Optional[int] = Field(
        None, ge=15, description="Minutes between 'still pending' reminders (min 15)")
