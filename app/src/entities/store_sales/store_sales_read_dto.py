from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field
from src.entities.store_sales.store_sales_base import (
    SaleBase,
    SaleItemBase,
    SalePaymentBase,
)


# =====================================================
# SALE ITEM READ DTOs
# =====================================================

class SaleItemReadBase(SaleItemBase):
    """Base read DTO for sale item"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    sale_id: str
    batch_id: str
    product_name: str
    price: float  # Unit price
    tax_rate: float = Field(default=0, description="Sum of all tax rates (calculated from taxes_applied)")
    line_total: float
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


# =====================================================
# SALE READ DTOs
# =====================================================

class SaleReadBase(SaleBase):
    """Base read DTO for sale"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    sale_number: str
    total_amount: float = Field(default=0, description="Total sale amount")
    paid_amount: float = Field(default=0, description="Total amount paid")
    balance_amount: float = Field(default=0, description="Outstanding balance")
    # Gift Card, Promo Code, and Affiliate tracking
    gift_card_amount_used: Optional[float] = Field(None, description="Amount used from gift card")
    promo_code_id: Optional[str] = Field(None, description="Promo code ID used")
    promo_discount_amount: Optional[float] = Field(None, description="Discount amount from promo code")
    affiliate_id: Optional[str] = Field(None, description="Affiliate ID that referred this sale")
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    customer_name: Optional[str] = Field(None, description="Customer name")
    items: List[SaleItemReadBase] = Field(default_factory=list, description="List of sale items")
    payments: List['PaymentReadBase'] = Field(default_factory=list, description="List of payments")
    total_paid: float = Field(default=0, description="Total amount paid (excluding refunded) - for backward compatibility")
    sale_total: float = Field(default=0, description="Total sale amount from items - for backward compatibility")


class CreateSaleControllerReadDto(SaleReadBase):
    """Controller DTO for create sale read operations"""
    pass


class CreateSaleServiceReadDto(SaleReadBase):
    """Service DTO for create sale read operations"""
    pass


class UpdateSaleControllerReadDto(SaleReadBase):
    """Controller DTO for update sale read operations"""
    pass


class UpdateSaleServiceReadDto(SaleReadBase):
    """Service DTO for update sale read operations"""
    pass


class GetSaleControllerReadDto(SaleReadBase):
    """Controller DTO for get sale read operations"""
    pass


class GetSaleServiceReadDto(SaleReadBase):
    """Service DTO for get sale read operations"""
    pass


class GetSalesControllerReadDto(BaseModel):
    """Controller DTO for get sales list read operations"""
    sales: List[SaleReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


class GetSalesServiceReadDto(BaseModel):
    """Service DTO for get sales list read operations"""
    sales: List[SaleReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


class CancelSaleControllerReadDto(SaleReadBase):
    """Controller DTO for cancel sale read operations"""
    pass


class CancelSaleServiceReadDto(SaleReadBase):
    """Service DTO for cancel sale read operations"""
    pass


class DeleteSaleControllerReadDto(SaleReadBase):
    """Controller DTO for delete sale read operations"""
    pass


class DeleteSaleServiceReadDto(SaleReadBase):
    """Service DTO for delete sale read operations"""
    pass


# =====================================================
# PAYMENT READ DTOs
# =====================================================

class PaymentReadBase(SalePaymentBase):
    """Base read DTO for payment"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")


class CreatePaymentControllerReadDto(PaymentReadBase):
    """Controller DTO for create payment read operations"""
    pass


class CreatePaymentServiceReadDto(PaymentReadBase):
    """Service DTO for create payment read operations"""
    pass


class UpdatePaymentControllerReadDto(PaymentReadBase):
    """Controller DTO for update payment read operations"""
    pass


class UpdatePaymentServiceReadDto(PaymentReadBase):
    """Service DTO for update payment read operations"""
    pass


class GetPaymentControllerReadDto(PaymentReadBase):
    """Controller DTO for get payment read operations"""
    pass


class GetPaymentServiceReadDto(PaymentReadBase):
    """Service DTO for get payment read operations"""
    pass


class GetPaymentsControllerReadDto(BaseModel):
    """Controller DTO for get payments list read operations"""
    payments: List[PaymentReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)
    total_paid: float = Field(default=0, description="Total amount paid (excluding refunded)")
    sale_total: float = Field(default=0, description="Total sale amount")


class GetPaymentsServiceReadDto(BaseModel):
    """Service DTO for get payments list read operations"""
    payments: List[PaymentReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)
    total_paid: float = Field(default=0, description="Total amount paid (excluding refunded)")
    sale_total: float = Field(default=0, description="Total sale amount")


class RefundPaymentControllerReadDto(PaymentReadBase):
    """Controller DTO for refund payment read operations"""
    pass


class RefundPaymentServiceReadDto(PaymentReadBase):
    """Service DTO for refund payment read operations"""
    pass


# =====================================================
# SALES STATISTICS READ DTOs
# =====================================================

class SalesStatusStats(BaseModel):
    """Statistics by sale status"""
    status: str
    count: int = Field(default=0)
    total_amount: float = Field(default=0, description="Total sale amount for this status")
    total_paid: float = Field(default=0, description="Total paid amount for this status")


class PaymentMethodStats(BaseModel):
    """Statistics by payment method"""
    payment_method: str
    count: int = Field(default=0)
    total_amount: float = Field(default=0, description="Total amount paid via this method")


class SalesStatisticsReadDto(BaseModel):
    """Sales statistics DTO"""
    # Overall statistics
    total_sales: int = Field(default=0, description="Total number of sales")
    total_paid: float = Field(default=0, description="Total amount paid (excluding refunded)")
    total_outstanding: float = Field(default=0, description="Total outstanding amount")
    average_sale_amount: float = Field(default=0, description="Average sale amount")
    
    # Statistics by status
    status_breakdown: List[SalesStatusStats] = Field(default_factory=list, description="Statistics by sale status")
    
    # Statistics by payment method
    payment_method_breakdown: List[PaymentMethodStats] = Field(default_factory=list, description="Statistics by payment method")
    
    # Date range (if provided)
    from_date: Optional[str] = Field(None, description="Start date of statistics period")
    to_date: Optional[str] = Field(None, description="End date of statistics period")


class GetSalesStatisticsControllerReadDto(SalesStatisticsReadDto):
    """Controller DTO for sales statistics"""
    pass


class GetSalesStatisticsServiceReadDto(SalesStatisticsReadDto):
    """Service DTO for sales statistics"""
    pass


# =====================================================
# VERIFY PRICE READ DTOs
# =====================================================

class TaxAppliedReadDto(BaseModel):
    """Read DTO for tax applied to an item"""
    tax_id: Optional[str] = None
    tax_name: Optional[str] = None
    rate: Optional[float] = None
    is_inclusive: Optional[bool] = None
    amount: Optional[float] = None


class PricingRuleAppliedReadDto(BaseModel):
    """Read DTO for pricing rule applied to an item"""
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    rule_category: Optional[str] = None
    rule_target_type: Optional[str] = None
    rule_target_id: Optional[str] = None
    price_before: Optional[float] = None
    price_after: Optional[float] = None
    adjustment: Optional[float] = None
    priority: Optional[int] = None


class TaxRuleAppliedReadDto(BaseModel):
    """Read DTO for tax rule applied to an item"""
    tax_rule_id: Optional[str] = None
    tax_rule_name: Optional[str] = None
    tax_rule_type: Optional[str] = None
    tax_rule_target_id: Optional[str] = None
    tax_id: Optional[str] = None
    tax_name: Optional[str] = None
    rate: Optional[float] = None
    is_inclusive: Optional[bool] = None
    tax_amount: Optional[float] = None
    priority: Optional[int] = None


class VerifiedPriceItemReadDto(BaseModel):
    """Read DTO for verified price item"""
    product_id: str
    product_name: str = Field(..., description="Product name for receipt display")
    quantity: float
    base_selling_price: float
    actual_price: Optional[float] = None
    price_after_pricing_rule: Optional[float] = None
    price_after_tax: Optional[float] = None
    tax_amount: Optional[float] = None
    final_price: Optional[float] = None
    line_total: Optional[float] = None
    taxes_applied: List[TaxAppliedReadDto] = Field(default_factory=list)
    tax_rate: Optional[float] = Field(None, description="Sum of all tax rates (calculated from taxes_applied)")
    pricing_rule_applied: Optional[PricingRuleAppliedReadDto] = None
    tax_rule_applied: Optional[TaxRuleAppliedReadDto] = None


class VerifyPriceReadDto(BaseModel):
    """Read DTO for verified prices"""
    items: List[VerifiedPriceItemReadDto]
    business_name: str = Field(..., description="Business name for receipt display")
    subtotal_before_discount: Optional[float] = Field(None, description="Total amount before promo discount (sum of line totals without promo). Only present when a promo code is applied.")
    total_amount: float = Field(default=0, description="Total amount for all items (promo discount already applied per-item in final_price)")
    total_tax_amount: float = Field(default=0, description="Total tax amount for all items")
    # Promo code discount info
    promo_code_id: Optional[str] = Field(None, description="Promo code ID if valid promo code provided")
    promo_discount_amount: Optional[float] = Field(None, description="Total promo discount amount across all eligible items (for display only — already deducted from total_amount)")
    promo_code_error: Optional[str] = Field(None, description="Error message if promo code validation failed")
    final_total_amount: float = Field(default=0, description="Final total amount the customer pays (same as total_amount — promo already applied)")
    # Gift card info
    gift_card_id: Optional[str] = Field(None, description="Gift card ID if valid gift card code provided")
    gift_card_balance_available: Optional[float] = Field(None, description="Available balance on gift card")
    gift_card_amount_usable: Optional[float] = Field(None, description="Amount that can be used from gift card (min of balance and final_total_amount)")
    # Affiliate info
    affiliate_id: Optional[str] = Field(None, description="Affiliate ID if valid affiliate code provided")


class VerifyPriceControllerReadDto(VerifyPriceReadDto):
    """Controller DTO for verified prices"""
    pass


class VerifyPriceServiceReadDto(VerifyPriceReadDto):
    """Service DTO for verified prices"""
    pass

