from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
from src.entities.invoices.invoices_base import (
    InvoiceBase,
    InvoiceItemBase,
    InvoicePaymentInputBase,
    InvoiceStatusType,
)


# =====================================================
# CREATE INVOICE WRITE DTOs
# =====================================================

class CreateInvoiceWriteBase(BaseModel):
    """Base write DTO for creating an invoice"""
    customer_id: str = Field(..., description="Customer ID")
    sale_date: Optional[str] = Field(None, description="Sale date (YYYY-MM-DD)")
    invoice_date: Optional[str] = Field(None, description="Invoice date (YYYY-MM-DD) - deprecated, use sale_date instead")
    due_date: Optional[str] = Field(None, description="Due date (YYYY-MM-DD)")
    status: Optional[InvoiceStatusType] = Field(None, description="Invoice status. If not provided, will be determined automatically based on sale_mode.")
    sale_mode: str = Field(default='INSTANT', description="Sale mode: INSTANT, DEPOSIT, or CREDIT")
    description: Optional[str] = Field(None, description="Invoice description/notes")
    
    @model_validator(mode='after')
    def validate_sale_date(self):
        """Ensure sale_date is set (from either sale_date or invoice_date)"""
        if not self.sale_date and self.invoice_date:
            # Use invoice_date if sale_date is not provided (backward compatibility)
            self.sale_date = self.invoice_date
        if not self.sale_date:
            raise ValueError("Either sale_date or invoice_date must be provided")
        return self
    items: List[InvoiceItemBase] = Field(..., min_items=1, description="List of invoice items with verified prices from verify_price endpoint")
    # Gift Card, Promo Code, and Affiliate codes (for validation only)
    gift_card_code: Optional[str] = Field(None, description="Gift card code to use for payment (optional, should match verify_price response)")
    promo_code: Optional[str] = Field(None, description="Promo code that was verified (optional, should match verify_price response)")
    affiliate_code: Optional[str] = Field(None, description="Affiliate code that was verified (optional, should match verify_price response)")
    # Verified totals from verify_price endpoint (use these instead of recalculating)
    verified_total_amount: Optional[float] = Field(None, ge=0, description="Total amount from verify_price (before promo discount)")
    verified_promo_discount_amount: Optional[float] = Field(None, ge=0, description="Promo discount amount from verify_price")
    verified_final_total_amount: Optional[float] = Field(None, ge=0, description="Final total amount from verify_price (after promo discount)")
    verified_promo_code_id: Optional[str] = Field(None, description="Promo code ID from verify_price")
    verified_gift_card_id: Optional[str] = Field(None, description="Gift card ID from verify_price")
    verified_affiliate_id: Optional[str] = Field(None, description="Affiliate ID from verify_price")


class CreateInvoiceControllerWriteDto(CreateInvoiceWriteBase):
    """Controller DTO for creating an invoice"""
    pass


class CreateInvoiceServiceWriteDto(CreateInvoiceWriteBase):
    """Service DTO for creating an invoice"""
    pass


# =====================================================
# UPDATE INVOICE WRITE DTOs
# =====================================================

class UpdateInvoiceWriteBase(BaseModel):
    """Base write DTO for updating an invoice"""
    customer_id: Optional[str] = None
    sale_date: Optional[str] = Field(None, description="Sale date (YYYY-MM-DD)")
    status: Optional[InvoiceStatusType] = None
    sale_mode: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[InvoiceItemBase]] = Field(None, description="Optional list of invoice items to update (replaces existing items)")


class UpdateInvoiceControllerWriteDto(UpdateInvoiceWriteBase):
    """Controller DTO for updating an invoice"""
    pass


class UpdateInvoiceServiceWriteDto(UpdateInvoiceWriteBase):
    """Service DTO for updating an invoice"""
    pass


# =====================================================
# CREATE PAYMENT WRITE DTOs
# =====================================================

class CreateInvoicePaymentWriteBase(BaseModel):
    """Base write DTO for creating invoice payments"""
    invoice_id: str = Field(..., description="Invoice ID")
    payments: List[InvoicePaymentInputBase] = Field(..., min_items=1, description="List of payments to add. Each payment should include payment_method, paid_amount, and optional description.")


class CreateInvoicePaymentControllerWriteDto(CreateInvoicePaymentWriteBase):
    """Controller DTO for creating an invoice payment"""
    pass


class CreateInvoicePaymentServiceWriteDto(CreateInvoicePaymentWriteBase):
    """Service DTO for creating an invoice payment"""
    pass


# =====================================================
# DELETE INVOICE WRITE DTOs
# =====================================================

class DeleteInvoiceWriteBase(BaseModel):
    """Base write DTO for deleting an invoice"""
    invoice_id: str


class DeleteInvoiceControllerWriteDto(DeleteInvoiceWriteBase):
    """Controller DTO for deleting an invoice"""
    pass


class DeleteInvoiceServiceWriteDto(DeleteInvoiceWriteBase):
    """Service DTO for deleting an invoice"""
    pass

