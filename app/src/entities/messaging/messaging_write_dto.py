from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.messaging.messaging_base import MessageBase, MessageRecipientInput


# =====================================================
# CREATE MESSAGE WRITE DTOs
# =====================================================

class CreateMessageWriteBase(MessageBase):
    """Base write DTO for creating a message"""
    recipients: List[MessageRecipientInput] = Field(..., min_length=1, description="List of recipients (at least one)")


class CreateMessageControllerWriteDto(CreateMessageWriteBase):
    """Controller DTO for creating a message"""
    pass


class CreateMessageServiceWriteDto(CreateMessageWriteBase):
    """Service DTO for creating a message"""
    pass


# =====================================================
# UPDATE MESSAGE WRITE DTOs (only DRAFT messages)
# =====================================================

class UpdateMessageWriteBase(BaseModel):
    """Base write DTO for updating a draft message"""
    subject: Optional[str] = Field(None, min_length=1, max_length=255, description="Message subject")
    body: Optional[str] = Field(None, min_length=1, description="Message body content")
    channel: Optional[str] = Field(None, description="Delivery channel")
    scheduled_at: Optional[datetime] = Field(None, description="When to send the message")


class UpdateMessageControllerWriteDto(UpdateMessageWriteBase):
    """Controller DTO for updating a message"""
    pass


class UpdateMessageServiceWriteDto(UpdateMessageWriteBase):
    """Service DTO for updating a message"""
    pass


# =====================================================
# SEND / CANCEL / RESEND WRITE DTOs
# =====================================================

class SendMessageWriteBase(BaseModel):
    """Base write DTO for sending a draft message"""
    message_id: str = Field(..., description="ID of the draft message to send/schedule")


class SendMessageControllerWriteDto(SendMessageWriteBase):
    pass


class SendMessageServiceWriteDto(SendMessageWriteBase):
    pass


class CancelMessageWriteBase(BaseModel):
    """Base write DTO for cancelling a scheduled message"""
    message_id: str = Field(..., description="ID of the message to cancel")


class CancelMessageControllerWriteDto(CancelMessageWriteBase):
    pass


class CancelMessageServiceWriteDto(CancelMessageWriteBase):
    pass


class ResendMessageWriteBase(BaseModel):
    """Base write DTO for resending a failed message"""
    message_id: str = Field(..., description="ID of the failed message to resend")


class ResendMessageControllerWriteDto(ResendMessageWriteBase):
    pass


class ResendMessageServiceWriteDto(ResendMessageWriteBase):
    pass


# =====================================================
# DELETE MESSAGE WRITE DTOs
# =====================================================

class DeleteMessageWriteBase(BaseModel):
    """Base write DTO for deleting a message"""
    message_id: str = Field(..., description="ID of the message to delete")


class DeleteMessageControllerWriteDto(DeleteMessageWriteBase):
    pass


class DeleteMessageServiceWriteDto(DeleteMessageWriteBase):
    pass
