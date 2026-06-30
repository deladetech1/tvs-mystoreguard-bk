from typing import Optional, List, Any, Dict
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']

# Lifecycle of an estimate.
EstimateStatus = Literal['DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'CONVERTED']


# =====================================================
# INPUT MODELS
# =====================================================

class EstimateLineItemInput(BaseModel):
    """One captured line on an estimate. `line_def_key` selects which line-item
    definition (from the template) to price; `field_values` are the measurements."""
    line_def_key: str = Field(..., description="Key of the line item definition in the template, e.g. 'window'")
    label: Optional[str] = Field(None, max_length=255, description="Optional label for this specific line, e.g. 'Living room window'")
    quantity: float = Field(default=1.0, gt=0, description="How many identical units of this line")
    field_values: Dict[str, Any] = Field(default_factory=dict, description="Captured values keyed by field key, e.g. {height:1.2, width:0.9}")


# =====================================================
# ESTIMATE BASE DTO
# =====================================================

class EstimateBase(BaseModel):
    """Base DTO for an estimate (an instance created from a template for a client)."""
    template_id: str = Field(..., description="Estimate template this estimate is built from")
    customer_id: Optional[str] = Field(None, description="msg_customers.id this estimate is for")
    title: Optional[str] = Field(None, max_length=255, description="Short title, e.g. 'Curtains for Mr. Mensah'")
    notes: Optional[str] = Field(None, max_length=2000, description="Free-text notes shown on the estimate")
