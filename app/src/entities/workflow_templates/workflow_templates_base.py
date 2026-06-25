from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

WorkflowType = Literal['SALES', 'SERVICE', 'DELIVERY', 'INSTALLATION', 'CONSULTATION', 'OTHERS']
TargetKind = Literal['ASSIGNEE', 'APPROVER']
TargetType = Literal['USER', 'GROUP']


# =====================================================
# SHARED INPUT MODELS (reused by tasks for ad-hoc steps)
# =====================================================

class StepTargetInput(BaseModel):
    """A person (USER) or core-platform group (GROUP) attached to a step."""
    target_kind: TargetKind = Field(..., description="ASSIGNEE (does the work) or APPROVER (closes it)")
    target_type: TargetType = Field(..., description="USER or GROUP")
    target_id: str = Field(..., description="cp_users.id when USER, cp_groups.id when GROUP")


class StepInput(BaseModel):
    """A step definition. `ref` is a client-supplied key used to wire up
    `depends_on` between steps before server-side ids exist."""
    ref: str = Field(..., description="Client-side key for this step, unique within the payload")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    display_order: int = Field(default=0, ge=0)
    location_id: Optional[str] = Field(None, description="Where this step happens (optional)")
    depends_on: List[str] = Field(default_factory=list, description="refs of steps that must COMPLETE first")
    targets: List[StepTargetInput] = Field(default_factory=list)


# =====================================================
# WORKFLOW TEMPLATE BASE DTO
# =====================================================

class WorkflowTemplateBase(BaseModel):
    """Base DTO for a workflow template"""
    name: str = Field(..., min_length=1, max_length=255, description="Template name, e.g. 'Curtain Installation'")
    template_type: WorkflowType = Field(default='OTHERS', description="Category of workflow")
    description: Optional[str] = Field(None, description="What this workflow is for")
    is_active: bool = Field(default=True, description="Whether the template can be used to create jobs")
