from typing import Optional
from pydantic import BaseModel, Field
from src.entities.suppliers.suppliers_base import (
    SupplierBase,
    DeleteStatusType,
)


# =====================================================
# CREATE SUPPLIER WRITE DTOs
# =====================================================

class CreateSupplierWriteBase(SupplierBase):
    """Base write DTO for creating a supplier"""
    pass


class CreateSupplierControllerWriteDto(CreateSupplierWriteBase):
    """Controller DTO for creating a supplier"""
    pass


class CreateSupplierServiceWriteDto(CreateSupplierWriteBase):
    """Service DTO for creating a supplier"""
    pass


# =====================================================
# UPDATE SUPPLIER WRITE DTOs
# =====================================================

class UpdateSupplierWriteBase(BaseModel):
    """Base write DTO for updating a supplier"""
    fullname: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateSupplierControllerWriteDto(UpdateSupplierWriteBase):
    """Controller DTO for updating a supplier"""
    pass


class UpdateSupplierServiceWriteDto(UpdateSupplierWriteBase):
    """Service DTO for updating a supplier"""
    pass


# =====================================================
# DELETE SUPPLIER WRITE DTOs
# =====================================================

class DeleteSupplierWriteBase(BaseModel):
    """Base write DTO for deleting a supplier"""
    supplier_id: str


class DeleteSupplierControllerWriteDto(DeleteSupplierWriteBase):
    """Controller DTO for deleting a supplier"""
    pass


class DeleteSupplierServiceWriteDto(DeleteSupplierWriteBase):
    """Service DTO for deleting a supplier"""
    pass

