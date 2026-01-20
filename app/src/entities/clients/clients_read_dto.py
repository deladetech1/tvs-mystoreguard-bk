from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.clients.clients_base import (
    ClientBase,
)


# =====================================================
# CLIENT READ DTOs
# =====================================================

class ClientReadBase(ClientBase):
    """Base read DTO for client"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    delete_status: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class CreateClientControllerReadDto(ClientReadBase):
    """Controller DTO for create client read operations"""
    pass


class CreateClientServiceReadDto(ClientReadBase):
    """Service DTO for create client read operations"""
    pass


class UpdateClientControllerReadDto(ClientReadBase):
    """Controller DTO for update client read operations"""
    pass


class UpdateClientServiceReadDto(ClientReadBase):
    """Service DTO for update client read operations"""
    pass


class DeleteClientControllerReadDto(ClientReadBase):
    """Controller DTO for delete client read operations"""
    pass


class DeleteClientServiceReadDto(ClientReadBase):
    """Service DTO for delete client read operations"""
    pass


class GetClientControllerReadDto(ClientReadBase):
    """Controller DTO for get client read operations"""
    pass


class GetClientServiceReadDto(ClientReadBase):
    """Service DTO for get client read operations"""
    pass


class GetClientsControllerReadDto(ClientReadBase):
    """Controller DTO for get clients read operations"""
    pass


class GetClientsServiceReadDto(ClientReadBase):
    """Service DTO for get clients read operations"""
    pass


class PermanentDeleteClientReadBase(BaseModel):
    """Base read DTO for permanent delete client result"""
    client_id: str
    message: str


class PermanentDeleteClientControllerReadDto(PermanentDeleteClientReadBase):
    """Controller DTO for permanent delete client read operations"""
    pass


class PermanentDeleteClientServiceReadDto(PermanentDeleteClientReadBase):
    """Service DTO for permanent delete client read operations"""
    pass


