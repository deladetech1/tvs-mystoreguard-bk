from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.meetings.meetings_base import (
    MeetingParticipantType,
    MeetingStatusType,
    ReminderChannelType,
    RsvpStatusType,
    ReminderStatusType,
)


# =====================================================
# PARTICIPANT READ DTOs
# =====================================================

class MeetingParticipantReadBase(BaseModel):
    """Base read DTO for meeting participant"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    meeting_id: str
    participant_type: MeetingParticipantType
    participant_id: str
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None
    participant_contact: Optional[str] = None
    rsvp_status: RsvpStatusType = Field(default='PENDING')
    reminder_status: ReminderStatusType = Field(default='PENDING')
    reminder_failure_reason: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None


# =====================================================
# MEETING READ DTOs
# =====================================================

class MeetingReadBase(BaseModel):
    """Base read DTO for meeting"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    meeting_date: str
    start_time: str
    end_time: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    participant_type: MeetingParticipantType
    reminder_minutes: int = Field(default=30)
    reminder_channel: ReminderChannelType = Field(default='EMAIL')
    status: MeetingStatusType
    reminder_sent_at: Optional[datetime] = None
    notes: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    # Participants
    participants: List[MeetingParticipantReadBase] = Field(default_factory=list)
    total_participants: int = Field(default=0)
    total_accepted: int = Field(default=0)
    total_declined: int = Field(default=0)


class CreateMeetingControllerReadDto(MeetingReadBase):
    pass


class CreateMeetingServiceReadDto(MeetingReadBase):
    pass


class UpdateMeetingControllerReadDto(MeetingReadBase):
    pass


class UpdateMeetingServiceReadDto(MeetingReadBase):
    pass


class CancelMeetingControllerReadDto(MeetingReadBase):
    pass


class CancelMeetingServiceReadDto(MeetingReadBase):
    pass


class CompleteMeetingControllerReadDto(MeetingReadBase):
    pass


class CompleteMeetingServiceReadDto(MeetingReadBase):
    pass


class GetMeetingControllerReadDto(MeetingReadBase):
    pass


class GetMeetingServiceReadDto(MeetingReadBase):
    pass


class GetMeetingsControllerReadDto(MeetingReadBase):
    pass


class GetMeetingsServiceReadDto(MeetingReadBase):
    pass


class DeleteMeetingReadBase(BaseModel):
    meeting_id: str
    message: str


class DeleteMeetingControllerReadDto(DeleteMeetingReadBase):
    pass


class DeleteMeetingServiceReadDto(DeleteMeetingReadBase):
    pass


# =====================================================
# MEETING STATISTICS READ DTOs
# =====================================================

class MeetingStatisticsReadBase(BaseModel):
    """Meeting statistics"""
    total_meetings: int = Field(default=0)
    total_scheduled: int = Field(default=0)
    total_completed: int = Field(default=0)
    total_cancelled: int = Field(default=0)
    total_reminder_sent: int = Field(default=0)
    total_participants: int = Field(default=0)
    total_accepted: int = Field(default=0)
    total_declined: int = Field(default=0)


class GetMeetingStatisticsControllerReadDto(MeetingStatisticsReadBase):
    pass


class GetMeetingStatisticsServiceReadDto(MeetingStatisticsReadBase):
    pass
