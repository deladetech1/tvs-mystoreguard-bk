from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.messaging.messaging_base import (
    MessageChannelType,
    MessageRecipientType,
    MessageStatusType,
    RecipientStatusType,
)


# =====================================================
# RECIPIENT READ DTOs
# =====================================================

class MessageRecipientReadBase(BaseModel):
    """Base read DTO for message recipient"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    message_id: str
    recipient_type: MessageRecipientType
    recipient_id: str
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_contact: Optional[str] = None
    status: RecipientStatusType = Field(default='PENDING')
    failure_reason: Optional[str] = None
    delivered_at: Optional[datetime] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None


# =====================================================
# MESSAGE READ DTOs
# =====================================================

class MessageReadBase(BaseModel):
    """Base read DTO for message"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    subject: str
    body: str
    channel: MessageChannelType
    recipient_type: MessageRecipientType
    scheduled_at: Optional[datetime] = None
    status: MessageStatusType
    sent_at: Optional[datetime] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    # Recipients
    recipients: List[MessageRecipientReadBase] = Field(default_factory=list)
    total_recipients: int = Field(default=0)
    total_delivered: int = Field(default=0)
    total_failed: int = Field(default=0)


class CreateMessageControllerReadDto(MessageReadBase):
    pass


class CreateMessageServiceReadDto(MessageReadBase):
    pass


class UpdateMessageControllerReadDto(MessageReadBase):
    pass


class UpdateMessageServiceReadDto(MessageReadBase):
    pass


class SendMessageControllerReadDto(MessageReadBase):
    pass


class SendMessageServiceReadDto(MessageReadBase):
    pass


class CancelMessageControllerReadDto(MessageReadBase):
    pass


class CancelMessageServiceReadDto(MessageReadBase):
    pass


class ResendMessageControllerReadDto(MessageReadBase):
    pass


class ResendMessageServiceReadDto(MessageReadBase):
    pass


class GetMessageControllerReadDto(MessageReadBase):
    pass


class GetMessageServiceReadDto(MessageReadBase):
    pass


class GetMessagesControllerReadDto(MessageReadBase):
    pass


class GetMessagesServiceReadDto(MessageReadBase):
    pass


class DeleteMessageReadBase(BaseModel):
    message_id: str
    message: str


class DeleteMessageControllerReadDto(DeleteMessageReadBase):
    pass


class DeleteMessageServiceReadDto(DeleteMessageReadBase):
    pass


# =====================================================
# MESSAGE STATISTICS READ DTOs
# =====================================================

class MessageStatisticsReadBase(BaseModel):
    """Message statistics"""
    total_messages: int = Field(default=0)
    total_draft: int = Field(default=0)
    total_scheduled: int = Field(default=0)
    total_sent: int = Field(default=0)
    total_failed: int = Field(default=0)
    total_cancelled: int = Field(default=0)
    total_recipients: int = Field(default=0)
    total_delivered: int = Field(default=0)
    total_delivery_failed: int = Field(default=0)


class GetMessageStatisticsControllerReadDto(MessageStatisticsReadBase):
    pass


class GetMessageStatisticsServiceReadDto(MessageStatisticsReadBase):
    pass
