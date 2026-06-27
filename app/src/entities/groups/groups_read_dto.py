from typing import Optional, List
from pydantic import BaseModel, Field


class GroupMemberDto(BaseModel):
    """A user that belongs to the group."""
    user_id: str
    fullname: Optional[str] = None


class GroupReadBase(BaseModel):
    """A core-platform group with its members (no roles/permissions)."""
    id: str
    group_name: str
    description: Optional[str] = None
    is_active: bool = True
    users: List[GroupMemberDto] = Field(default_factory=list, description="Members of the group")


class GetGroupsControllerReadDto(GroupReadBase):
    pass


class GetGroupsServiceReadDto(GroupReadBase):
    pass
