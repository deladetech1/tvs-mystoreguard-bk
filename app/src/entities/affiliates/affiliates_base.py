from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

AffiliateStatusType = Literal['ACTIVE', 'INACTIVE', 'SUSPENDED']
AffiliateCommissionType = Literal['PERCENTAGE', 'FIXED_AMOUNT']
DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']
ReferralConversionStatusType = Literal['PENDING', 'CONVERTED', 'FAILED', 'CANCELLED']
CommissionPaymentStatusType = Literal['PENDING', 'PAID', 'CANCELLED']


# =====================================================
# AFFILIATE BASE DTOs
# =====================================================

class AffiliateBase(BaseModel):
    """Base DTO for affiliate information"""
    affiliate_code: str = Field(..., min_length=1, description="Unique affiliate code")
    affiliate_name: str = Field(..., min_length=1, description="Affiliate name")
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    commission_rate: Decimal = Field(..., ge=0, le=100, decimal_places=2, description="Commission rate as percentage (0-100)")
    commission_type: AffiliateCommissionType = Field(default='PERCENTAGE', description="Commission type: PERCENTAGE or FIXED_AMOUNT")
    fixed_commission_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Fixed commission amount (if commission_type is FIXED_AMOUNT)")
    status: AffiliateStatusType = Field(default='ACTIVE', description="Affiliate status")
    description: Optional[str] = Field(None, description="Description")
    notes: Optional[str] = Field(None, description="Additional notes")
    applicable_to_locations: Optional[List[str]] = Field(None, description="List of location IDs this affiliate applies to (null = all locations)")
    applicable_to_products: Optional[List[str]] = Field(None, description="List of product IDs this affiliate applies to (null = all products)")
    applicable_to_product_metadata: Optional[List[str]] = Field(None, description="List of product metadata IDs this affiliate applies to (null = all metadata). Includes categories, brands, tags, labels, etc.")
    is_active: bool = Field(default=True, description="Whether the affiliate is active")

