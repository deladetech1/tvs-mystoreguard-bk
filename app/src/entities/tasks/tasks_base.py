from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

TaskType = Literal['SALES', 'SERVICE', 'DELIVERY', 'INSTALLATION', 'CONSULTATION', 'OTHERS']
TaskStatus = Literal['ACTIVE', 'COMPLETED', 'CANCELLED']
StepStatus = Literal['TODO', 'IN_PROGRESS', 'DONE', 'COMPLETED', 'CANCELLED']


# =====================================================
# TASK BASE DTO
# =====================================================

class TaskBase(BaseModel):
    """Base DTO for a task (multi-step job)."""
    title: str = Field(..., min_length=1, max_length=255, description="Job title, e.g. 'Fix curtains for Mr. Mensah'")
    task_type: TaskType = Field(default='OTHERS', description="Category of job")
    description: Optional[str] = Field(None, description="Job details")
    customer_id: Optional[str] = Field(None, description="Customer this job is for (optional)")
    origin_location_id: Optional[str] = Field(None, description="Branch where the job was logged (optional, metadata only)")
