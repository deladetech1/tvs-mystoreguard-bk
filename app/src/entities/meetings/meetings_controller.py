from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.meetings.meetings_service import MeetingsService
from src.entities.meetings.meetings_write_dto import *
from src.entities.meetings.meetings_read_dto import *
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

meetings_router = APIRouter(prefix="/meetings", tags=["Meetings"])
logger = get_logger("meetings")


def check_meetings_permission(current_user, permission: str):
    is_authorized = AuthService.has_any_permission(
        user_roles=current_user.data, required_permissions=[permission]
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Unauthorized access")


# 1. Schedule Meeting
@meetings_router.post("/add", response_model=Respons[CreateMeetingControllerReadDto])
def create_meeting(
    data: CreateMeetingControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Schedule a new meeting with suppliers or customers"""
    with LogContext("meetings", "create_meeting"):
        check_meetings_permission(current_user, "permission-msg-meetings-create")
        return MeetingsService.create_meeting(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )


# 2. Update Meeting
@meetings_router.put("/update", response_model=Respons[UpdateMeetingControllerReadDto])
def update_meeting(
    data: UpdateMeetingControllerWriteDto,
    meeting_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a scheduled meeting"""
    with LogContext("meetings", "update_meeting", meeting_id=meeting_id):
        check_meetings_permission(current_user, "permission-msg-meetings-update")
        return MeetingsService.update_meeting(
            data=data,
            meeting_id=meeting_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )


# 3. Cancel Meeting
@meetings_router.put("/cancel", response_model=Respons[CancelMeetingControllerReadDto])
def cancel_meeting(
    data: CancelMeetingControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Cancel a scheduled meeting"""
    with LogContext("meetings", "cancel_meeting", meeting_id=data.meeting_id):
        check_meetings_permission(current_user, "permission-msg-meetings-update")
        return MeetingsService.cancel_meeting(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            cancelled_by=current_user.data[0].user_id,
        )


# 4. Complete Meeting
@meetings_router.put("/complete", response_model=Respons[CompleteMeetingControllerReadDto])
def complete_meeting(
    data: CompleteMeetingControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Mark a meeting as completed"""
    with LogContext("meetings", "complete_meeting", meeting_id=data.meeting_id):
        check_meetings_permission(current_user, "permission-msg-meetings-update")
        return MeetingsService.complete_meeting(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            completed_by=current_user.data[0].user_id,
        )


# 5. Get Meeting
@meetings_router.get("/get", response_model=Respons[GetMeetingControllerReadDto])
def get_meeting(
    meeting_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single meeting with participants"""
    with LogContext("meetings", "get_meeting", meeting_id=meeting_id):
        check_meetings_permission(current_user, "permission-msg-meetings-get")
        return MeetingsService.get_meeting(
            meeting_id=meeting_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )


# 6. Get Meetings List
@meetings_router.get("/list", response_model=Respons[GetMeetingsControllerReadDto])
def get_meetings(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: str = Query(None, description="Filter by status (SCHEDULED, REMINDER_SENT, IN_PROGRESS, COMPLETED, CANCELLED)"),
    participant_type: str = Query(None, description="Filter by participant type (SUPPLIER, CUSTOMER)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of meetings with pagination and filters"""
    with LogContext("meetings", "get_meetings"):
        check_meetings_permission(current_user, "permission-msg-meetings-get")
        return MeetingsService.get_meetings(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            page=page, size=size, status=status, participant_type=participant_type,
        )


# 7. Delete Meeting
@meetings_router.delete("/delete", response_model=Respons[DeleteMeetingControllerReadDto])
def delete_meeting(
    data: DeleteMeetingControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a meeting and its participants"""
    with LogContext("meetings", "delete_meeting", meeting_id=data.meeting_id):
        check_meetings_permission(current_user, "permission-msg-meetings-delete")
        return MeetingsService.delete_meeting(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )


# 8. Get Meeting Statistics
@meetings_router.get("/statistics", response_model=Respons[GetMeetingStatisticsControllerReadDto])
def get_meeting_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get meeting statistics"""
    with LogContext("meetings", "get_meeting_statistics"):
        check_meetings_permission(current_user, "permission-msg-meetings-get")
        return MeetingsService.get_meeting_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )
