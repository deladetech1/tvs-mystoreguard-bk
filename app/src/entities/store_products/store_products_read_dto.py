from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.store_products.store_products_base import (
    StoreProductBase,
)
from src.entities.products.products_read_dto import PurchaseBatchReadDto
from src.entities.products.products_read_dto import DocumentReadDto
from src.entities.products.products_read_dto import MetadataReadDto


# =====================================================
# PRICE CALCULATOR DETAIL DTOs
# =====================================================

class TaxAppliedDto(BaseModel):
    """DTO for individual tax applied to a product"""
    tax_id: Optional[str] = Field(None, description="Tax ID")
    tax_name: Optional[str] = Field(None, description="Tax name")
    rate: Optional[float] = Field(None, description="Tax rate as a percentage")
    is_inclusive: Optional[bool] = Field(None, description="Whether tax is included in the price")
    amount: Optional[float] = Field(None, description="Tax amount in currency")


class PricingRuleAppliedDto(BaseModel):
    """DTO for pricing rule applied to a product"""
    rule_id: Optional[str] = Field(None, description="Pricing rule ID")
    rule_name: Optional[str] = Field(None, description="Pricing rule name")
    rule_type: Optional[str] = Field(None, description="Type of pricing rule (e.g., PERCENTAGE_DISCOUNT, FIXED_AMOUNT)")
    rule_category: Optional[str] = Field(None, description="Category of pricing rule")
    rule_target_type: Optional[str] = Field(None, description="Target type for the rule (e.g., PRODUCT, LOCATION, SKU)")
    rule_target_id: Optional[str] = Field(None, description="Target ID for the rule")
    price_before: Optional[float] = Field(None, description="Price before applying the rule")
    price_after: Optional[float] = Field(None, description="Price after applying the rule")
    adjustment: Optional[float] = Field(None, description="Price adjustment amount")
    priority: Optional[int] = Field(None, description="Rule priority")


class TaxRuleAppliedDto(BaseModel):
    """DTO for tax rule applied to a product"""
    tax_rule_id: Optional[str] = Field(None, description="Tax rule ID")
    tax_rule_name: Optional[str] = Field(None, description="Tax rule name")
    tax_rule_type: Optional[str] = Field(None, description="Type of tax rule target (e.g., PRODUCT, LOCATION)")
    tax_rule_target_id: Optional[str] = Field(None, description="Target ID for the tax rule")
    tax_id: Optional[str] = Field(None, description="Tax ID")
    tax_name: Optional[str] = Field(None, description="Tax name")
    rate: Optional[float] = Field(None, description="Tax rate as a percentage")
    is_inclusive: Optional[bool] = Field(None, description="Whether tax is included in the price")
    tax_amount: Optional[float] = Field(None, description="Tax amount in currency")
    priority: Optional[int] = Field(None, description="Tax rule priority")


# =====================================================
# STORE PRODUCT READ DTOs
# =====================================================

class StoreProductReadBase(StoreProductBase):
    """Base read DTO for store product"""
    # Product fields (from related product)
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    sku: Optional[str] = Field(None, description="Product SKU")
    bar_code: Optional[str] = Field(None, description="Product barcode")
    is_active: bool = Field(default=True, description="Whether the product is active")
    
    # Store product fields
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    delete_status: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    product_name: Optional[str] = Field(None, description="Product name (alias, kept for backward compatibility)")
    location_name: Optional[str] = Field(None, description="Location name")
    metadata: List[MetadataReadDto] = Field(default_factory=list, description="List of metadata objects with id, name, and type")
    documents: List[DocumentReadDto] = Field(default_factory=list, description="List of document objects with presigned URLs")
    batches: Optional[List[PurchaseBatchReadDto]] = Field(default=None, description="List of purchase batches")
    remaining_qty: int = Field(default=0, description="Total quantity at this store location (sum of qty_at_location from all active batches, excludes VOID and CANCELLED). Should match current_qty.")
    specific_product_all_batch_remaining_qty: int = Field(default=0, description="Total remaining quantity across all batches for this product at this store location (sum of qty_at_location from all active batches, excludes VOID and CANCELLED)")
    
    # Price fields
    cost_price: Optional[float] = Field(None, description="Cost price from latest batch")
    base_selling_price: Optional[float] = Field(None, description="Base selling price from latest batch")
    actual_price: Optional[float] = Field(None, description="Actual price from msg_product_prices")
    price_after_pricing_rule: Optional[float] = Field(None, description="Price after applying pricing rules")
    price_after_tax: Optional[float] = Field(None, description="Price after applying tax rules")
    tax_amount: Optional[float] = Field(None, description="Total tax amount applied")
    final_price: Optional[float] = Field(None, description="Final price after all calculations")
    
    # Currency fields
    currency_id: Optional[str] = Field(None, description="Currency ID from latest batch")
    currency_name: Optional[str] = Field(None, description="Currency name from latest batch")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol from latest batch")
    
    # Price calculator details
    taxes_applied: List[TaxAppliedDto] = Field(default_factory=list, description="List of taxes applied to the product")
    pricing_rules_applied: List[PricingRuleAppliedDto] = Field(default_factory=list, description="List of pricing rules that match this product")
    tax_rules_applied: List[TaxRuleAppliedDto] = Field(default_factory=list, description="List of tax rules applied to the product")


class CreateStoreProductControllerReadDto(StoreProductReadBase):
    """Controller DTO for create store product read operations"""
    pass


class CreateStoreProductServiceReadDto(StoreProductReadBase):
    """Service DTO for create store product read operations"""
    pass


# =====================================================
# BULK CREATE STORE PRODUCT READ DTOs
# =====================================================

class BulkCreateStoreProductItemResultBase(BaseModel):
    """Per-item result for a bulk create store products request (best-effort).

    One of these is returned for every item in the request, in the same order,
    so callers can tell exactly which items were added and which failed.
    """
    index: int = Field(..., description="Zero-based position of the item in the request array")
    product_id: str = Field(..., description="Product ID this result refers to")
    success: bool = Field(..., description="Whether this item was added/updated successfully")
    detail: Optional[str] = Field(None, description="Human-readable outcome message for this item")
    error: Optional[str] = Field(None, description="Error code when this item failed (None on success)")
    store_product: Optional[StoreProductReadBase] = Field(None, description="The created/updated store product when successful")


class BulkCreateStoreProductControllerReadDto(BulkCreateStoreProductItemResultBase):
    """Controller DTO for bulk create store products read operations"""
    pass


class BulkCreateStoreProductServiceReadDto(BulkCreateStoreProductItemResultBase):
    """Service DTO for bulk create store products read operations"""
    pass


class AddStockStoreProductControllerReadDto(StoreProductReadBase):
    """Controller DTO for add stock store product read operations"""
    pass


class AddStockStoreProductServiceReadDto(StoreProductReadBase):
    """Service DTO for add stock store product read operations"""
    pass


class UpdateStoreProductControllerReadDto(StoreProductReadBase):
    """Controller DTO for update store product read operations"""
    pass


class UpdateStoreProductServiceReadDto(StoreProductReadBase):
    """Service DTO for update store product read operations"""
    pass


class GetStoreProductControllerReadDto(StoreProductReadBase):
    """Controller DTO for get store product read operations"""
    pass


class GetStoreProductServiceReadDto(StoreProductReadBase):
    """Service DTO for get store product read operations"""
    pass


class GetStoreProductsControllerReadDto(StoreProductReadBase):
    """Controller DTO for get store products list read operations"""
    pass


class GetStoreProductsServiceReadDto(StoreProductReadBase):
    """Service DTO for get store products list read operations"""
    pass


class DeleteStoreProductReadBase(BaseModel):
    """Base read DTO for soft delete store product result"""
    loc_id: str
    product_id: str
    message: str


class DeleteStoreProductControllerReadDto(DeleteStoreProductReadBase):
    """Controller DTO for soft delete store product read operations"""
    pass


class DeleteStoreProductServiceReadDto(DeleteStoreProductReadBase):
    """Service DTO for soft delete store product read operations"""
    pass


class PermanentDeleteStoreProductReadBase(BaseModel):
    """Base read DTO for permanent delete store product result"""
    loc_id: str
    product_id: str
    message: str


class PermanentDeleteStoreProductControllerReadDto(PermanentDeleteStoreProductReadBase):
    """Controller DTO for permanent delete store product read operations"""
    pass


class PermanentDeleteStoreProductServiceReadDto(PermanentDeleteStoreProductReadBase):
    """Service DTO for permanent delete store product read operations"""
    pass


# =====================================================
# REVERSE BATCH STORE PRODUCT READ DTOs
# =====================================================

class ReverseBatchStoreProductReadBase(BaseModel):
    """Base read DTO for reverse batch store product result"""
    loc_id: str
    product_id: str
    batch_number: str
    qty_reversed: int
    message: str


class ReverseBatchStoreProductControllerReadDto(ReverseBatchStoreProductReadBase):
    """Controller DTO for reverse batch store product read operations"""
    pass


class ReverseBatchStoreProductServiceReadDto(ReverseBatchStoreProductReadBase):
    """Service DTO for reverse batch store product read operations"""
    pass


# =====================================================
# STORE PRODUCT STATISTICS READ DTOs
# =====================================================

class StoreProductStatisticsReadBase(BaseModel):
    """Base read DTO for store product statistics"""
    total_products: int = Field(default=0, description="Total number of store products")
    total_quantity: int = Field(default=0, description="Total quantity of all store products")
    active_products: int = Field(default=0, description="Number of active store products")
    low_stock_products: int = Field(default=0, description="Number of products at or below reorder level")
    out_of_stock_products: int = Field(default=0, description="Number of products with zero quantity")
    average_quantity: float = Field(default=0.0, description="Average quantity per product")
    products_needing_reorder: int = Field(default=0, description="Number of products that need reordering")
    well_stocked_products: int = Field(default=0, description="Number of products above reorder level")


class GetStoreProductStatisticsControllerReadDto(StoreProductStatisticsReadBase):
    """Controller DTO for store product statistics"""
    pass


class GetStoreProductStatisticsServiceReadDto(StoreProductStatisticsReadBase):
    """Service DTO for store product statistics"""
    pass

