from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.store_sales.store_sales_base import (
    SaleBase,
    SaleItemBase,
    SalePaymentBase,
    SalePaymentInputBase,
    SaleStatusType,
)


# =====================================================
# CREATE SALE WRITE DTOs
# =====================================================

class CreateSaleWriteBase(BaseModel):
    """Base write DTO for creating a sale"""
    customer_id: Optional[str] = Field(None, description="Customer ID (optional)")
    sale_date: str = Field(..., description="Sale date (YYYY-MM-DD)")
    status: Optional[SaleStatusType] = Field(None, description="Sale status. If not provided, will be determined automatically based on sale_mode and payments. If ON_HOLD is explicitly provided, no payments will be processed and inventory will not be deducted.")
    sale_mode: str = Field(default='INSTANT', description="Sale mode: INSTANT, DEPOSIT, or CREDIT")
    description: Optional[str] = Field(None, description="Sale description/notes")
    items: List[SaleItemBase] = Field(..., min_items=1, description="List of sale items with verified prices from verify_price endpoint")
    payments: Optional[List[SalePaymentInputBase]] = Field(
        default=None, 
        description="List of payments for this sale. Each payment should include payment_method, payment_status, and paid_amount. Can be added during sale creation or later. Payments will be ignored if status is explicitly set to ON_HOLD."
    )
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
    # Backdating: owners, admins, and mystoreguard admins only
    occurred_at: Optional[str] = Field(None, description="Backdate the sale to this datetime (owners, admins, and mystoreguard admins only). Accepts ISO format (2025-01-02T10:00:00), date only (2025-01-02), or natural language (2 January 2025). Ignored for users without the required role.")


class CreateSaleControllerWriteDto(CreateSaleWriteBase):
    """Controller DTO for creating a sale"""
    pass


class CreateSaleServiceWriteDto(CreateSaleWriteBase):
    """Service DTO for creating a sale"""
    pass


# =====================================================
# UPDATE SALE WRITE DTOs
# =====================================================

class UpdateSaleWriteBase(BaseModel):
    """Base write DTO for updating a sale"""
    customer_id: Optional[str] = None
    sale_date: Optional[str] = Field(None, description="Sale date (YYYY-MM-DD)")
    status: Optional[str] = None
    sale_mode: Optional[str] = None
    fulfillment_status: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[SaleItemBase]] = Field(None, description="Optional list of sale items to update (replaces existing items)")
    payments: Optional[List[SalePaymentInputBase]] = Field(
        default=None,
        description="List of additional payments to add to this sale. Each payment should include payment_method, payment_status, and paid_amount. Existing payments are not replaced."
    )


class UpdateSaleControllerWriteDto(UpdateSaleWriteBase):
    """Controller DTO for updating a sale"""
    pass


class UpdateSaleServiceWriteDto(UpdateSaleWriteBase):
    """Service DTO for updating a sale"""
    pass


# =====================================================
# CANCEL SALE WRITE DTOs
# =====================================================

class CancelSaleWriteBase(BaseModel):
    """Base write DTO for cancelling a sale"""
    sale_id: str = Field(..., description="Sale ID")


class CancelSaleControllerWriteDto(CancelSaleWriteBase):
    """Controller DTO for cancelling a sale"""
    pass


class CancelSaleServiceWriteDto(CancelSaleWriteBase):
    """Service DTO for cancelling a sale"""
    pass


# =====================================================
# DELETE SALE WRITE DTOs
# =====================================================

class DeleteSaleWriteBase(BaseModel):
    """Base write DTO for deleting a sale"""
    sale_id: str = Field(..., description="Sale ID")


class DeleteSaleControllerWriteDto(DeleteSaleWriteBase):
    """Controller DTO for deleting a sale"""
    pass


class DeleteSaleServiceWriteDto(DeleteSaleWriteBase):
    """Service DTO for deleting a sale"""
    pass


# =====================================================
# CREATE PAYMENT WRITE DTOs
# =====================================================

class CreatePaymentWriteBase(BaseModel):
    """Base write DTO for creating payments"""
    sale_id: str = Field(..., description="Sale ID")
    payments: List[SalePaymentInputBase] = Field(..., min_items=1, description="List of payments to add. Each payment should include payment_method, paid_amount, and optional description.")


class CreatePaymentControllerWriteDto(CreatePaymentWriteBase):
    """Controller DTO for creating a payment"""
    pass


class CreatePaymentServiceWriteDto(CreatePaymentWriteBase):
    """Service DTO for creating a payment"""
    pass


# =====================================================
# UPDATE PAYMENT WRITE DTOs
# =====================================================

class UpdatePaymentWriteBase(BaseModel):
    """Base write DTO for updating a payment"""
    payment_status: Optional[str] = Field(None, description="Payment status (SUCCESS, FAILED, PENDING, REFUNDED)")
    paid_amount: Optional[float] = Field(None, gt=0, description="Amount paid (must be greater than 0)")
    description: Optional[str] = Field(None, description="Payment description/notes")


class UpdatePaymentControllerWriteDto(UpdatePaymentWriteBase):
    """Controller DTO for updating a payment"""
    pass


class UpdatePaymentServiceWriteDto(UpdatePaymentWriteBase):
    """Service DTO for updating a payment"""
    pass


# =====================================================
# REFUND PAYMENT WRITE DTOs
# =====================================================

class RefundPaymentWriteBase(BaseModel):
    """Base write DTO for refunding a payment"""
    payment_id: str = Field(..., description="Payment ID to refund")
    description: Optional[str] = Field(None, description="Refund description/notes")


class RefundPaymentControllerWriteDto(RefundPaymentWriteBase):
    """Controller DTO for refunding a payment"""
    pass


class RefundPaymentServiceWriteDto(RefundPaymentWriteBase):
    """Service DTO for refunding a payment"""
    pass


# =====================================================
# VERIFY PRICE WRITE DTOs
# =====================================================

class VerifyPriceItemBase(BaseModel):
    """Base DTO for price verification item"""
    product_id: str = Field(..., description="Product ID")
    quantity: float = Field(..., gt=0, description="Quantity being purchased")
    base_selling_price: float = Field(..., ge=0, description="Base selling price from client")


class VerifyPriceWriteBase(BaseModel):
    """Base write DTO for verifying prices"""
    items: List[VerifyPriceItemBase] = Field(..., min_items=1, description="List of items with product_id, quantity, and base_selling_price")
    customer_id: Optional[str] = Field(None, description="Customer ID (optional, used for promo code validation)")
    promo_code: Optional[str] = Field(None, description="Promo code to apply discount (optional)")
    gift_card_code: Optional[str] = Field(None, description="Gift card code to check balance (optional)")
    affiliate_code: Optional[str] = Field(None, description="Affiliate code for tracking (optional, doesn't affect price)")


class VerifyPriceControllerWriteDto(VerifyPriceWriteBase):
    """Controller DTO for verifying prices"""
    pass


class VerifyPriceServiceWriteDto(VerifyPriceWriteBase):
    """Service DTO for verifying prices"""
    pass

