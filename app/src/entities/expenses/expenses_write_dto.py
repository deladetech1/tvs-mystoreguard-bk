from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.expenses.expenses_base import (
    ExpenseBase,
    ExpenseSourceType,
    DeleteStatusType,
)


# =====================================================
# CREATE EXPENSE WRITE DTOs
# =====================================================

class CreateExpenseWriteBase(ExpenseBase):
    """Base write DTO for creating an expense"""
    pass


class CreateExpenseControllerWriteDto(CreateExpenseWriteBase):
    """Controller DTO for creating an expense"""
    pass


class CreateExpenseServiceWriteDto(CreateExpenseWriteBase):
    """Service DTO for creating an expense"""
    pass


# =====================================================
# UPDATE EXPENSE WRITE DTOs
# =====================================================

class UpdateExpenseWriteBase(BaseModel):
    """Base write DTO for updating an expense - only used_by, used_for, and description can be updated"""
    used_by: Optional[str] = None
    used_for: Optional[str] = None
    description: Optional[str] = None


class UpdateExpenseControllerWriteDto(UpdateExpenseWriteBase):
    """Controller DTO for updating an expense"""
    pass


class UpdateExpenseServiceWriteDto(UpdateExpenseWriteBase):
    """Service DTO for updating an expense"""
    pass


# =====================================================
# DELETE EXPENSE WRITE DTOs
# =====================================================

class DeleteExpenseWriteBase(BaseModel):
    """Base write DTO for deleting an expense"""
    expense_id: str


class DeleteExpenseControllerWriteDto(DeleteExpenseWriteBase):
    """Controller DTO for deleting an expense"""
    pass


class DeleteExpenseServiceWriteDto(DeleteExpenseWriteBase):
    """Service DTO for deleting an expense"""
    pass


# =====================================================
# PERMANENT DELETE EXPENSE WRITE DTOs
# =====================================================

class PermanentDeleteExpenseWriteBase(BaseModel):
    """Base write DTO for permanently deleting an expense"""
    expense_id: str


class PermanentDeleteExpenseControllerWriteDto(PermanentDeleteExpenseWriteBase):
    """Controller DTO for permanently deleting an expense"""
    pass


class PermanentDeleteExpenseServiceWriteDto(PermanentDeleteExpenseWriteBase):
    """Service DTO for permanently deleting an expense"""
    pass


# =====================================================
# REVERSE EXPENSE WRITE DTOs
# =====================================================

class ReverseExpenseWriteBase(BaseModel):
    """Base write DTO for reversing an expense"""
    expense_id: str


class ReverseExpenseControllerWriteDto(ReverseExpenseWriteBase):
    """Controller DTO for reversing an expense"""
    pass


class ReverseExpenseServiceWriteDto(ReverseExpenseWriteBase):
    """Service DTO for reversing an expense"""
    pass


