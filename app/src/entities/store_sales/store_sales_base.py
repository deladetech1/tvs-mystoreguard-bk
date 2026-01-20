from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import date


# =====================================================
# ENUMS AND LITERALS
# =====================================================

SaleStatusType = Literal[
    'ON_HOLD', 'PAID', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED', 'QUEUED'
]

SaleModeType = Literal[
    'INSTANT', 'DEPOSIT', 'CREDIT'
]

FulfillmentStatusType = Literal[
    'PENDING', 'PARTIALLY_FULFILLED', 'FULFILLED'
]

PaymentMethodType = Literal[
    'CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'GIFT_CARD', 'OTHERS'
]

PaymentStatusType = Literal[
    'SUCCESS', 'FAILED', 'PENDING', 'REFUNDED'
]


# =====================================================
# SALE BASE DTOs
# =====================================================

class SaleBase(BaseModel):
    """Base DTO for sale information"""
    customer_id: Optional[str] = Field(None, description="Customer ID (optional)")
    sale_date: date = Field(..., description="Sale date")
    status: SaleStatusType = Field(default='ON_HOLD', description="Sale status")
    sale_mode: SaleModeType = Field(default='INSTANT', description="Sale mode: INSTANT, DEPOSIT, or CREDIT")
    fulfillment_status: FulfillmentStatusType = Field(default='PENDING', description="Fulfillment status")
    description: Optional[str] = Field(None, description="Sale description/notes")


# =====================================================
# SALE ITEM BASE DTOs
# =====================================================

class TaxAppliedItem(BaseModel):
    """DTO for tax applied to an item"""
    tax_id: str = Field(..., description="Tax ID")
    tax_name: str = Field(..., description="Tax name")
    rate: float = Field(..., ge=0, description="Tax rate")
    is_inclusive: bool = Field(..., description="Whether tax is inclusive")
    amount: float = Field(..., ge=0, description="Tax amount")


class SaleItemBase(BaseModel):
    """Base DTO for sale item information"""
    model_config = ConfigDict(extra='forbid')  # Reject any extra fields like batch_id (batch_id is determined by FIFO)
    
    product_id: str = Field(..., description="Product ID")
    quantity: float = Field(..., gt=0, description="Quantity to sell (must be greater than 0)")
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
# SALE PAYMENT BASE DTOs
# =====================================================

class SalePaymentBase(BaseModel):
    """Base DTO for sale payment information"""
    sale_id: str = Field(..., description="Sale ID")
    payment_method: PaymentMethodType = Field(..., description="Payment method")
    payment_status: PaymentStatusType = Field(..., description="Payment status")
    paid_amount: float = Field(..., gt=0, description="Amount paid (must be greater than 0)")
    description: Optional[str] = Field(None, description="Payment description/notes")


class SalePaymentInputBase(BaseModel):
    """Base DTO for payment input (without sale_id, used in sale creation/update)"""
    payment_method: PaymentMethodType = Field(..., description="Payment method: CASH, CARD, BANK_TRANSFER, MOBILE_MONEY, CHEQUE, BITCOIN, or OTHERS")
    paid_amount: float = Field(..., gt=0, description="Amount paid (must be greater than 0)")
    description: Optional[str] = Field(None, description="Payment description/notes")

