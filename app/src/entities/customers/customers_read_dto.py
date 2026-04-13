from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.customers.customers_base import (
    CustomerBase,
)


# =====================================================
# CUSTOMER READ DTOs
# =====================================================

class CustomerReadBase(CustomerBase):
    """Base read DTO for customer"""
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


class CreateCustomerControllerReadDto(CustomerReadBase):
    """Controller DTO for create customer read operations"""
    pass


class CreateCustomerServiceReadDto(CustomerReadBase):
    """Service DTO for create customer read operations"""
    pass


class UpdateCustomerControllerReadDto(CustomerReadBase):
    """Controller DTO for update customer read operations"""
    pass


class UpdateCustomerServiceReadDto(CustomerReadBase):
    """Service DTO for update customer read operations"""
    pass


class GetCustomerControllerReadDto(CustomerReadBase):
    """Controller DTO for get customer read operations"""
    pass


class GetCustomerServiceReadDto(CustomerReadBase):
    """Service DTO for get customer read operations"""
    pass


class GetCustomersControllerReadDto(CustomerReadBase):
    """Controller DTO for get customers read operations"""
    pass


class GetCustomersServiceReadDto(CustomerReadBase):
    """Service DTO for get customers read operations"""
    pass


class DeleteCustomerReadBase(BaseModel):
    """Base read DTO for delete customer result"""
    customer_id: str
    message: str


class DeleteCustomerControllerReadDto(DeleteCustomerReadBase):
    """Controller DTO for delete customer read operations"""
    pass


class DeleteCustomerServiceReadDto(DeleteCustomerReadBase):
    """Service DTO for delete customer read operations"""
    pass


# =====================================================
# CUSTOMER STATISTICS READ DTOs
# =====================================================

class CustomerStatsOverviewReadDto(BaseModel):
    """Overview statistics for customers"""
    total_customers: int = 0
    active_customers: int = 0
    inactive_customers: int = 0
    recently_added: int = 0

