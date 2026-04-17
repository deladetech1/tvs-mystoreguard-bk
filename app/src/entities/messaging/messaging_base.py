from typing import Optional, List
from typing_extensions import Literal
from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

MessageChannelType = Literal['SMS', 'EMAIL', 'WHATSAPP']
MessageRecipientType = Literal['SUPPLIER', 'CUSTOMER']
MessageStatusType = Literal['DRAFT', 'SCHEDULED', 'QUEUED', 'SENDING', 'SENT', 'FAILED', 'CANCELLED']
RecipientStatusType = Literal['PENDING', 'SENT', 'DELIVERED', 'FAILED']


# =====================================================
# RECIPIENT BASE DTOs
# =====================================================

class MessageRecipientInput(BaseModel):
    """Input DTO for a message recipient"""
    recipient_id: str = Field(..., description="ID of the supplier or customer")


# =====================================================
# MESSAGE BASE DTOs
# =====================================================

class MessageBase(BaseModel):
    """Base DTO for message information"""
    subject: str = Field(..., min_length=1, max_length=255, description="Message subject")
    body: str = Field(..., min_length=1, description="Message body content")
    channel: MessageChannelType = Field(default='EMAIL', description="Delivery channel: SMS, EMAIL, or WHATSAPP")
    recipient_type: MessageRecipientType = Field(..., description="Whether recipients are suppliers or customers")
    scheduled_at: Optional[datetime] = Field(None, description="When to send the message. NULL = send immediately (status becomes SCHEDULED right away)")
