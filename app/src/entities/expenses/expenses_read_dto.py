from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.expenses.expenses_base import (
    ExpenseBase,
    ExpenseSourceType,
)


# =====================================================
# EXPENSE READ DTOs
# =====================================================

class ExpenseReadBase(ExpenseBase):
    """Base read DTO for expense"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    balance: Optional[Decimal] = Field(None, decimal_places=6, description="Remaining allocated balance after this expense (only for ALLOCATED expenses)")
    delete_status: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    currency_name: Optional[str] = Field(None, description="Currency name from JOIN")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol from JOIN")


class CreateExpenseControllerReadDto(ExpenseReadBase):
    """Controller DTO for create expense read operations"""
    pass


class CreateExpenseServiceReadDto(ExpenseReadBase):
    """Service DTO for create expense read operations"""
    pass


class UpdateExpenseControllerReadDto(ExpenseReadBase):
    """Controller DTO for update expense read operations"""
    pass


class UpdateExpenseServiceReadDto(ExpenseReadBase):
    """Service DTO for update expense read operations"""
    pass


class DeleteExpenseControllerReadDto(ExpenseReadBase):
    """Controller DTO for delete expense read operations"""
    pass


class DeleteExpenseServiceReadDto(ExpenseReadBase):
    """Service DTO for delete expense read operations"""
    pass


class GetExpenseControllerReadDto(ExpenseReadBase):
    """Controller DTO for get expense read operations"""
    pass


class GetExpenseServiceReadDto(ExpenseReadBase):
    """Service DTO for get expense read operations"""
    pass


class GetExpensesControllerReadDto(ExpenseReadBase):
    """Controller DTO for get expenses read operations"""
    pass


class GetExpensesServiceReadDto(ExpenseReadBase):
    """Service DTO for get expenses read operations"""
    pass


class PermanentDeleteExpenseReadBase(BaseModel):
    """Base read DTO for permanent delete expense result"""
    expense_id: str
    message: str


class PermanentDeleteExpenseControllerReadDto(PermanentDeleteExpenseReadBase):
    """Controller DTO for permanent delete expense read operations"""
    pass


class PermanentDeleteExpenseServiceReadDto(PermanentDeleteExpenseReadBase):
    """Service DTO for permanent delete expense read operations"""
    pass


# =====================================================
# REVERSE EXPENSE READ DTOs
# =====================================================

class ReverseExpenseReadBase(BaseModel):
    """Base read DTO for reverse expense result"""
    expense_id: str
    message: str
    refunded_amount: Optional[Decimal] = Field(default=None, decimal_places=6)


class ReverseExpenseControllerReadDto(ReverseExpenseReadBase):
    """Controller DTO for reverse expense read operations"""
    pass


class ReverseExpenseServiceReadDto(ReverseExpenseReadBase):
    """Service DTO for reverse expense read operations"""
    pass


# =====================================================
# EXPENSE STATISTICS READ DTOs
# =====================================================

class ExpenseStatisticsReadBase(BaseModel):
    """Base read DTO for expense statistics"""
    total_expenses: int = 0
    total_amount: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_allocated: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_contigency: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_fixed: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_reimbursable: Decimal = Field(default=Decimal('0'), decimal_places=2)
    available_allocated: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_amount_without_fixed: Decimal = Field(default=Decimal('0'), decimal_places=2)


class GetExpenseStatisticsControllerReadDto(ExpenseStatisticsReadBase):
    """Controller DTO for expense statistics"""
    pass


class GetExpenseStatisticsServiceReadDto(ExpenseStatisticsReadBase):
    """Service DTO for expense statistics"""
    pass

