from typing import Optional, List
from typing_extensions import Literal
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

ReturnStatusType = Literal[
    'PENDING', 'APPROVED', 'REJECTED', 'COMPLETED'
]

ReturnType = Literal[
    'REFUND', 'EXCHANGE', 'STORE_CREDIT'
]

ReturnReasonType = Literal[
    'DEFECTIVE', 'WRONG_ITEM', 'CUSTOMER_CHANGED_MIND', 'EXPIRED', 'DAMAGED_IN_TRANSIT', 'OTHER'
]

ReturnItemConditionType = Literal[
    'RESALABLE', 'DAMAGED', 'EXPIRED', 'OPENED', 'WRITE_OFF'
]

RefundMethodType = Literal[
    'ORIGINAL_PAYMENT', 'STORE_CREDIT', 'CASH', 'ANY'
]


# =====================================================
# RETURN ITEM BASE DTOs
# =====================================================

class ReturnItemBase(BaseModel):
    """Base DTO for a return item"""
    sale_item_id: str = Field(..., description="ID of the original sale item being returned")
    quantity_returned: float = Field(..., gt=0, description="Quantity being returned (can be partial)")
    condition: ReturnItemConditionType = Field(default='RESALABLE', description="Condition of the returned item")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for returning this specific item")


# =====================================================
# RETURN BASE DTOs
# =====================================================

class ReturnBase(BaseModel):
    """Base DTO for return information"""
    sale_id: str = Field(..., description="ID of the original sale")
    return_type: ReturnType = Field(default='REFUND', description="Type of return: REFUND, EXCHANGE, or STORE_CREDIT")
    reason: ReturnReasonType = Field(default='CUSTOMER_CHANGED_MIND', description="Reason for the return")
    reason_notes: Optional[str] = Field(None, max_length=1000, description="Additional notes about the reason")
    refund_method: RefundMethodType = Field(default='ORIGINAL_PAYMENT', description="How the refund should be issued")
