from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService
from src.entities.groups.groups_service import GroupsService
from src.entities.groups.groups_read_dto import GetGroupsControllerReadDto
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

groups_router = APIRouter(prefix="/groups", tags=["Groups"])
logger = get_logger("groups")

# Anyone who can build or run a workflow may pick a group target.
GROUP_PICK_PERMISSIONS = [
    "permission-msg-tasks-get",
    "permission-msg-tasks-create",
    "permission-msg-tasks-manage-templates",
]


@groups_router.get("/list", response_model=Respons[GetGroupsControllerReadDto])
def list_groups(
    group_name: Optional[str] = Query(None, description="Filter by group name (partial match)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
):
    """List the tenant's groups with their members, for assigning a workflow
    step to a group. Read-only — group management lives in core-platform."""
    with LogContext("groups", "list_groups", tenant_id=current_user.data[0].tenant_id):
        if not AuthService.has_any_permission(
            user_roles=current_user.data, required_permissions=GROUP_PICK_PERMISSIONS
        ):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        return GroupsService.get_groups(
            tenant_id=current_user.data[0].tenant_id,
            group_name=group_name,
            is_active=is_active,
            page=page,
            size=size,
        )
