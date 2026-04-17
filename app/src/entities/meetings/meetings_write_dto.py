from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.meetings.meetings_base import MeetingBase, MeetingParticipantInput


# =====================================================
# CREATE MEETING WRITE DTOs
# =====================================================

class CreateMeetingWriteBase(MeetingBase):
    """Base write DTO for scheduling a meeting"""
    participants: List[MeetingParticipantInput] = Field(..., min_length=1, description="List of participants (at least one)")


class CreateMeetingControllerWriteDto(CreateMeetingWriteBase):
    pass


class CreateMeetingServiceWriteDto(CreateMeetingWriteBase):
    pass


# =====================================================
# UPDATE MEETING WRITE DTOs
# =====================================================

class UpdateMeetingWriteBase(BaseModel):
    """Base write DTO for updating a meeting"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Meeting title")
    description: Optional[str] = Field(None, description="Meeting description")
    location: Optional[str] = Field(None, description="Meeting location")
    meeting_date: Optional[str] = Field(None, description="Meeting date")
    start_time: Optional[str] = Field(None, description="Start time")
    end_time: Optional[str] = Field(None, description="End time")
    start_datetime: Optional[datetime] = Field(None, description="Full start datetime")
    end_datetime: Optional[datetime] = Field(None, description="Full end datetime")
    reminder_minutes: Optional[int] = Field(None, ge=0, description="Minutes before to send reminder")
    reminder_channel: Optional[str] = Field(None, description="Reminder channel")
    notes: Optional[str] = Field(None, description="Additional notes")


class UpdateMeetingControllerWriteDto(UpdateMeetingWriteBase):
    pass


class UpdateMeetingServiceWriteDto(UpdateMeetingWriteBase):
    pass


# =====================================================
# CANCEL / COMPLETE MEETING WRITE DTOs
# =====================================================

class CancelMeetingWriteBase(BaseModel):
    meeting_id: str = Field(..., description="ID of the meeting to cancel")
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")


class CancelMeetingControllerWriteDto(CancelMeetingWriteBase):
    pass


class CancelMeetingServiceWriteDto(CancelMeetingWriteBase):
    pass


class CompleteMeetingWriteBase(BaseModel):
    meeting_id: str = Field(..., description="ID of the meeting to mark as completed")
    notes: Optional[str] = Field(None, description="Meeting notes/minutes")


class CompleteMeetingControllerWriteDto(CompleteMeetingWriteBase):
    pass


class CompleteMeetingServiceWriteDto(CompleteMeetingWriteBase):
    pass


# =====================================================
# DELETE MEETING WRITE DTOs
# =====================================================

class DeleteMeetingWriteBase(BaseModel):
    meeting_id: str = Field(..., description="ID of the meeting to delete")


class DeleteMeetingControllerWriteDto(DeleteMeetingWriteBase):
    pass


class DeleteMeetingServiceWriteDto(DeleteMeetingWriteBase):
    pass
