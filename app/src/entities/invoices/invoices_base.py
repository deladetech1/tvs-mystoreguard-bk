from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

InvoiceStatusType = Literal[
    'DRAFT', 'COMPLETED', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED'
]

PaymentMethodType = Literal[
    'CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'GIFT_CARD', 'OTHERS'
]

PaymentStatusType = Literal[
    'SUCCESS', 'FAILED', 'PENDING', 'REFUNDED'
]


# =====================================================
# INVOICE BASE DTOs
# =====================================================

class InvoiceBase(BaseModel):
    """Base DTO for invoice information"""
    customer_id: str = Field(..., description="Customer ID")
    sale_date: date = Field(..., description="Sale date")
    due_date: Optional[date] = Field(None, description="Due date (optional)")
    status: InvoiceStatusType = Field(default='DRAFT', description="Invoice status")
    sale_mode: str = Field(default='INSTANT', description="Sale mode: INSTANT, DEPOSIT, or CREDIT")
    description: Optional[str] = Field(None, description="Invoice description/notes")


# =====================================================
# INVOICE ITEM BASE DTOs
# =====================================================

class TaxAppliedItem(BaseModel):
    """DTO for tax applied to an item"""
    tax_id: str = Field(..., description="Tax ID")
    tax_name: str = Field(..., description="Tax name")
    rate: float = Field(..., ge=0, description="Tax rate")
    is_inclusive: bool = Field(..., description="Whether tax is inclusive")
    amount: float = Field(..., ge=0, description="Tax amount")


class InvoiceItemBase(BaseModel):
    """Base DTO for invoice item information"""
    product_id: str = Field(..., description="Product ID")
    quantity: float = Field(..., gt=0, description="Quantity (must be greater than 0)")
    base_selling_price: Optional[float] = Field(None, ge=0, description="Base selling price (optional, will be calculated if not provided)")
    actual_price: Optional[float] = Field(None, ge=0, description="Actual price (optional, will be calculated if not provided)")
    price_after_pricing_rule: Optional[float] = Field(None, ge=0, description="Price after pricing rule (optional, will be calculated if not provided)")
    price_after_tax: Optional[float] = Field(None, ge=0, description="Price after tax (optional, will be calculated if not provided)")
    final_price: Optional[float] = Field(None, ge=0, description="Final price (optional, will be calculated if not provided)")
    taxes_applied: List[TaxAppliedItem] = Field(default_factory=list, description="List of taxes applied to this item")
    tax_rate: Optional[float] = Field(None, ge=0, description="Sum of all tax rates (calculated from taxes_applied)")
    tax_amount: Optional[float] = Field(None, ge=0, description="Total tax amount for the item")
    is_inclusive: Optional[bool] = Field(None, description="Whether tax is inclusive")
    description: Optional[str] = Field(None, description="Item description")


# =====================================================
# INVOICE PAYMENT BASE DTOs
# =====================================================

class InvoicePaymentBase(BaseModel):
    """Base DTO for invoice payment information"""
    invoice_id: str = Field(..., description="Invoice ID")
    payment_method: PaymentMethodType = Field(..., description="Payment method")
    payment_status: PaymentStatusType = Field(..., description="Payment status")
    paid_amount: float = Field(..., gt=0, description="Amount paid (must be greater than 0)")
    description: Optional[str] = Field(None, description="Payment description/notes")


class InvoicePaymentInputBase(BaseModel):
    """Base DTO for payment input (without invoice_id, used in invoice creation/update)"""
    payment_method: PaymentMethodType = Field(..., description="Payment method: CASH, CARD, BANK_TRANSFER, MOBILE_MONEY, CHEQUE, BITCOIN, GIFT_CARD, or OTHERS")
    paid_amount: float = Field(..., gt=0, description="Amount paid (must be greater than 0)")
    description: Optional[str] = Field(None, description="Payment description/notes")

