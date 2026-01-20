from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']
ExpenseSourceType = Literal['ALLOCATED', 'CONTIGENCY', 'FIXED', 'REIMBURSABLE']


# =====================================================
# EXPENSE BASE DTOs
# =====================================================

class ExpenseBase(BaseModel):
    """Base DTO for expense information"""
    amount: Decimal = Field(..., decimal_places=6, description="Expense amount")
    currency_id: str = Field(..., description="Currency ID")
    used_by: Optional[str] = Field(None, description="User ID who used the expense")
    used_for: Optional[str] = Field(None, description="Purpose or description of what the expense was used for")
    source: ExpenseSourceType = Field(default='ALLOCATED', description="Source of expense: ALLOCATED, CONTIGENCY, FIXED, or REIMBURSABLE")
    description: Optional[str] = Field(None, description="Additional description")

