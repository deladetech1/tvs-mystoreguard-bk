from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.suppliers.suppliers_base import (
    SupplierBase,
)


# =====================================================
# SUPPLIER READ DTOs
# =====================================================

class SupplierReadBase(SupplierBase):
    """Base read DTO for supplier"""
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


class CreateSupplierControllerReadDto(SupplierReadBase):
    """Controller DTO for create supplier read operations"""
    pass


class CreateSupplierServiceReadDto(SupplierReadBase):
    """Service DTO for create supplier read operations"""
    pass


class UpdateSupplierControllerReadDto(SupplierReadBase):
    """Controller DTO for update supplier read operations"""
    pass


class UpdateSupplierServiceReadDto(SupplierReadBase):
    """Service DTO for update supplier read operations"""
    pass


class GetSupplierControllerReadDto(SupplierReadBase):
    """Controller DTO for get supplier read operations"""
    pass


class GetSupplierServiceReadDto(SupplierReadBase):
    """Service DTO for get supplier read operations"""
    pass


class GetSuppliersControllerReadDto(SupplierReadBase):
    """Controller DTO for get suppliers read operations"""
    pass


class GetSuppliersServiceReadDto(SupplierReadBase):
    """Service DTO for get suppliers read operations"""
    pass


class DeleteSupplierReadBase(BaseModel):
    """Base read DTO for delete supplier result"""
    supplier_id: str
    message: str


class DeleteSupplierControllerReadDto(DeleteSupplierReadBase):
    """Controller DTO for delete supplier read operations"""
    pass


class DeleteSupplierServiceReadDto(DeleteSupplierReadBase):
    """Service DTO for delete supplier read operations"""
    pass

