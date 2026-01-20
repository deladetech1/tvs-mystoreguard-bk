from typing import Optional
from pydantic import BaseModel, Field
from src.entities.customers.customers_base import (
    CustomerBase,
    DeleteStatusType,
)


# =====================================================
# CREATE CUSTOMER WRITE DTOs
# =====================================================

class CreateCustomerWriteBase(CustomerBase):
    """Base write DTO for creating a customer"""
    pass


class CreateCustomerControllerWriteDto(CreateCustomerWriteBase):
    """Controller DTO for creating a customer"""
    pass


class CreateCustomerServiceWriteDto(CreateCustomerWriteBase):
    """Service DTO for creating a customer"""
    pass


# =====================================================
# UPDATE CUSTOMER WRITE DTOs
# =====================================================

class UpdateCustomerWriteBase(BaseModel):
    """Base write DTO for updating a customer"""
    fullname: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateCustomerControllerWriteDto(UpdateCustomerWriteBase):
    """Controller DTO for updating a customer"""
    pass


class UpdateCustomerServiceWriteDto(UpdateCustomerWriteBase):
    """Service DTO for updating a customer"""
    pass


# =====================================================
# DELETE CUSTOMER WRITE DTOs
# =====================================================

class DeleteCustomerWriteBase(BaseModel):
    """Base write DTO for deleting a customer"""
    customer_id: str


class DeleteCustomerControllerWriteDto(DeleteCustomerWriteBase):
    """Controller DTO for deleting a customer"""
    pass


class DeleteCustomerServiceWriteDto(DeleteCustomerWriteBase):
    """Service DTO for deleting a customer"""
    pass

