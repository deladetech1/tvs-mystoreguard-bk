from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.invoices.invoices_base import (
    InvoiceBase,
    InvoiceItemBase,
    TaxAppliedItem,
    InvoicePaymentBase,
    InvoiceStatusType,
)


# =====================================================
# INVOICE PAYMENT READ DTOs
# =====================================================

class InvoicePaymentReadBase(InvoicePaymentBase):
    """Base read DTO for invoice payment"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    invoice_id: str
    gift_card_id: Optional[str] = None
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    deleted_at: Optional[datetime] = None


# =====================================================
# INVOICE ITEM READ DTOs
# =====================================================

class TaxAppliedReadDto(TaxAppliedItem):
    """Read DTO for tax applied to an item"""
    pass


class InvoiceItemReadBase(InvoiceItemBase):
    """Base read DTO for invoice item"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    invoice_id: str
    batch_id: Optional[str] = None
    product_id: str
    product_name: str
    taxes_applied: List[TaxAppliedReadDto] = Field(default_factory=list, description="List of taxes applied to this item")
    tax_rate: Optional[float] = Field(None, description="Sum of all tax rates (calculated from taxes_applied)")
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


# =====================================================
# INVOICE READ DTOs
# =====================================================

class InvoiceReadBase(InvoiceBase):
    """Base read DTO for invoice"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    invoice_number: str
    customer_id: str
    sale_date: date
    due_date: Optional[date] = None
    status: str
    sale_mode: str
    description: Optional[str] = None
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    customer_name: Optional[str] = Field(None, description="Customer name from JOIN")
    business_name: Optional[str] = Field(None, description="Business name from JOIN")
    currency_id: Optional[str] = Field(None, description="Currency ID from JOIN")
    currency_name: Optional[str] = Field(None, description="Currency name from JOIN")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol from JOIN")
    items: List[InvoiceItemReadBase] = Field(default_factory=list, description="List of invoice items")
    payments: List['InvoicePaymentReadBase'] = Field(default_factory=list, description="List of payments")
    total_amount: Decimal = Field(default=Decimal('0'), description="Total invoice amount")
    paid_amount: Decimal = Field(default=Decimal('0'), description="Total amount paid")
    balance_amount: Decimal = Field(default=Decimal('0'), description="Outstanding balance")
    gift_card_amount_used: Optional[Decimal] = Field(default=Decimal('0'), description="Gift card amount used")
    promo_code_id: Optional[str] = Field(None, description="Promo code ID")
    promo_discount_amount: Optional[Decimal] = Field(default=Decimal('0'), description="Promo discount amount")
    affiliate_id: Optional[str] = Field(None, description="Affiliate ID")


class CreateInvoiceControllerReadDto(InvoiceReadBase):
    """Controller DTO for create invoice read operations"""
    pass


class CreateInvoiceServiceReadDto(InvoiceReadBase):
    """Service DTO for create invoice read operations"""
    pass


class UpdateInvoiceControllerReadDto(InvoiceReadBase):
    """Controller DTO for update invoice read operations"""
    pass


class UpdateInvoiceServiceReadDto(InvoiceReadBase):
    """Service DTO for update invoice read operations"""
    pass


class DeleteInvoiceControllerReadDto(InvoiceReadBase):
    """Controller DTO for delete invoice read operations"""
    pass


class DeleteInvoiceServiceReadDto(InvoiceReadBase):
    """Service DTO for delete invoice read operations"""
    pass


class GetInvoiceControllerReadDto(InvoiceReadBase):
    """Controller DTO for get invoice read operations"""
    pass


class GetInvoiceServiceReadDto(InvoiceReadBase):
    """Service DTO for get invoice read operations"""
    pass


class GetInvoicesControllerReadDto(BaseModel):
    """Controller DTO for get invoices list read operations"""
    invoices: List[InvoiceReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


class GetInvoicesServiceReadDto(BaseModel):
    """Service DTO for get invoices list read operations"""
    invoices: List[InvoiceReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


# =====================================================
# INVOICE STATISTICS READ DTOs
# =====================================================

class InvoiceStatisticsReadBase(BaseModel):
    """Base read DTO for invoice statistics"""
    total_invoices: int = 0
    total_amount: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_draft: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_completed: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_partially_paid: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_overdue: Decimal = Field(default=Decimal('0'), decimal_places=2)
    total_cancelled: Decimal = Field(default=Decimal('0'), decimal_places=2)
    count_draft: int = 0
    count_completed: int = 0
    count_partially_paid: int = 0
    count_overdue: int = 0
    count_cancelled: int = 0


class GetInvoiceStatisticsControllerReadDto(InvoiceStatisticsReadBase):
    """Controller DTO for invoice statistics"""
    pass


class GetInvoiceStatisticsServiceReadDto(InvoiceStatisticsReadBase):
    """Service DTO for invoice statistics"""
    pass


# =====================================================
# CREATE PAYMENT READ DTOs
# =====================================================

class CreateInvoicePaymentControllerReadDto(InvoicePaymentReadBase):
    """Controller DTO for create invoice payment read operations"""
    pass


class CreateInvoicePaymentServiceReadDto(InvoicePaymentReadBase):
    """Service DTO for create invoice payment read operations"""
    pass

