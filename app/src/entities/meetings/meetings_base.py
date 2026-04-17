from typing import Optional, List
from typing_extensions import Literal
from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

MeetingParticipantType = Literal['SUPPLIER', 'CUSTOMER']
MeetingStatusType = Literal['SCHEDULED', 'REMINDER_SENT', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
ReminderChannelType = Literal['SMS', 'EMAIL', 'WHATSAPP']
RsvpStatusType = Literal['PENDING', 'ACCEPTED', 'DECLINED']
ReminderStatusType = Literal['PENDING', 'SENT', 'DELIVERED', 'FAILED']


# =====================================================
# PARTICIPANT BASE DTOs
# =====================================================

class MeetingParticipantInput(BaseModel):
    """Input DTO for a meeting participant"""
    participant_id: str = Field(..., description="ID of the supplier or customer")


# =====================================================
# MEETING BASE DTOs
# =====================================================

class MeetingBase(BaseModel):
    """Base DTO for meeting information"""
    title: str = Field(..., min_length=1, max_length=255, description="Meeting title")
    description: Optional[str] = Field(None, description="Meeting description")
    location: Optional[str] = Field(None, description="Meeting location")
    meeting_date: str = Field(..., description="Meeting date (YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: Optional[str] = Field(None, description="End time (HH:MM)")
    start_datetime: datetime = Field(..., description="Full start datetime")
    end_datetime: Optional[datetime] = Field(None, description="Full end datetime")
    participant_type: MeetingParticipantType = Field(..., description="Whether participants are suppliers or customers")
    reminder_minutes: int = Field(default=30, ge=0, description="How many minutes before the meeting to send a reminder. 0 = no reminder.")
    reminder_channel: ReminderChannelType = Field(default='EMAIL', description="Channel for reminder: SMS, EMAIL, or WHATSAPP")
    notes: Optional[str] = Field(None, description="Additional notes")
