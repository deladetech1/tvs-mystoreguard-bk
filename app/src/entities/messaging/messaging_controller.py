from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.messaging.messaging_service import MessagingService
from src.entities.messaging.messaging_write_dto import *
from src.entities.messaging.messaging_read_dto import *
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

messaging_router = APIRouter(prefix="/messaging", tags=["Messaging"])
logger = get_logger("messaging")


def check_messaging_permission(current_user, permission: str):
    is_authorized = AuthService.has_any_permission(
        user_roles=current_user.data, required_permissions=[permission]
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Unauthorized access")


# 1. Create Message
@messaging_router.post("/add", response_model=Respons[CreateMessageControllerReadDto])
def create_message(
    data: CreateMessageControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new message (DRAFT or SCHEDULED if scheduled_at is set)"""
    with LogContext("messaging", "create_message"):
        check_messaging_permission(current_user, "permission-msg-messaging-create")
        return MessagingService.create_message(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )


# 2. Update Message (DRAFT/SCHEDULED only)
@messaging_router.put("/update", response_model=Respons[UpdateMessageControllerReadDto])
def update_message(
    data: UpdateMessageControllerWriteDto,
    message_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a draft or scheduled message"""
    with LogContext("messaging", "update_message", message_id=message_id):
        check_messaging_permission(current_user, "permission-msg-messaging-update")
        return MessagingService.update_message(
            data=data,
            message_id=message_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )


# 3. Send Message (DRAFT -> SCHEDULED)
@messaging_router.put("/send", response_model=Respons[SendMessageControllerReadDto])
def send_message(
    data: SendMessageControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Send a draft message immediately (schedules it for the Azure Function to pick up)"""
    with LogContext("messaging", "send_message", message_id=data.message_id):
        check_messaging_permission(current_user, "permission-msg-messaging-update")
        return MessagingService.send_message(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            sent_by=current_user.data[0].user_id,
        )


# 4. Cancel Message (DRAFT/SCHEDULED -> CANCELLED)
@messaging_router.put("/cancel", response_model=Respons[CancelMessageControllerReadDto])
def cancel_message(
    data: CancelMessageControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Cancel a draft or scheduled message"""
    with LogContext("messaging", "cancel_message", message_id=data.message_id):
        check_messaging_permission(current_user, "permission-msg-messaging-update")
        return MessagingService.cancel_message(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            cancelled_by=current_user.data[0].user_id,
        )


# 5. Resend Failed Message (FAILED -> SCHEDULED)
@messaging_router.put("/resend", response_model=Respons[ResendMessageControllerReadDto])
def resend_message(
    data: ResendMessageControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Resend a failed message (resets to SCHEDULED for retry)"""
    with LogContext("messaging", "resend_message", message_id=data.message_id):
        check_messaging_permission(current_user, "permission-msg-messaging-update")
        return MessagingService.resend_message(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            resent_by=current_user.data[0].user_id,
        )


# 6. Get Message
@messaging_router.get("/get", response_model=Respons[GetMessageControllerReadDto])
def get_message(
    message_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single message with recipients"""
    with LogContext("messaging", "get_message", message_id=message_id):
        check_messaging_permission(current_user, "permission-msg-messaging-get")
        return MessagingService.get_message(
            message_id=message_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )


# 7. Get Messages List
@messaging_router.get("/list", response_model=Respons[GetMessagesControllerReadDto])
def get_messages(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: str = Query(None, description="Filter by status"),
    channel: str = Query(None, description="Filter by channel (SMS, EMAIL, WHATSAPP)"),
    recipient_type: str = Query(None, description="Filter by recipient type (SUPPLIER, CUSTOMER)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of messages with pagination and filters"""
    with LogContext("messaging", "get_messages"):
        check_messaging_permission(current_user, "permission-msg-messaging-get")
        return MessagingService.get_messages(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            page=page, size=size, status=status, channel=channel, recipient_type=recipient_type,
        )


# 8. Delete Message
@messaging_router.delete("/delete", response_model=Respons[DeleteMessageControllerReadDto])
def delete_message(
    data: DeleteMessageControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a message and its recipients"""
    with LogContext("messaging", "delete_message", message_id=data.message_id):
        check_messaging_permission(current_user, "permission-msg-messaging-delete")
        return MessagingService.delete_message(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )


# 9. Get Message Statistics
@messaging_router.get("/statistics", response_model=Respons[GetMessageStatisticsControllerReadDto])
def get_message_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get messaging statistics"""
    with LogContext("messaging", "get_message_statistics"):
        check_messaging_permission(current_user, "permission-msg-messaging-get")
        return MessagingService.get_message_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )
