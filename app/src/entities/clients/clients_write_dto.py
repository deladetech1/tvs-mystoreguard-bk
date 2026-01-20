from typing import Optional
from pydantic import BaseModel, Field
from src.entities.clients.clients_base import (
    ClientBase,
    DeleteStatusType,
)


# =====================================================
# CREATE CLIENT WRITE DTOs
# =====================================================

class CreateClientWriteBase(ClientBase):
    """Base write DTO for creating a client"""
    pass


class CreateClientControllerWriteDto(CreateClientWriteBase):
    """Controller DTO for creating a client"""
    pass


class CreateClientServiceWriteDto(CreateClientWriteBase):
    """Service DTO for creating a client"""
    pass


# =====================================================
# UPDATE CLIENT WRITE DTOs
# =====================================================

class UpdateClientWriteBase(BaseModel):
    """Base write DTO for updating a client"""
    fullname: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateClientControllerWriteDto(UpdateClientWriteBase):
    """Controller DTO for updating a client"""
    pass


class UpdateClientServiceWriteDto(UpdateClientWriteBase):
    """Service DTO for updating a client"""
    pass


# =====================================================
# DELETE CLIENT WRITE DTOs
# =====================================================

class DeleteClientWriteBase(BaseModel):
    """Base write DTO for deleting a client (soft delete)"""
    client_id: str


class DeleteClientControllerWriteDto(DeleteClientWriteBase):
    """Controller DTO for deleting a client"""
    pass


class DeleteClientServiceWriteDto(DeleteClientWriteBase):
    """Service DTO for deleting a client"""
    pass


# =====================================================
# PERMANENT DELETE CLIENT WRITE DTOs
# =====================================================

class PermanentDeleteClientWriteBase(BaseModel):
    """Base write DTO for permanently deleting a client"""
    client_id: str


class PermanentDeleteClientControllerWriteDto(PermanentDeleteClientWriteBase):
    """Controller DTO for permanently deleting a client"""
    pass


class PermanentDeleteClientServiceWriteDto(PermanentDeleteClientWriteBase):
    """Service DTO for permanently deleting a client"""
    pass


