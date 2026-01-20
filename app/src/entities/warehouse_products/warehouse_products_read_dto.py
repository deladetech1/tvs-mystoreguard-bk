from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.warehouse_products.warehouse_products_base import (
    WarehouseProductBase,
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
# WAREHOUSE PRODUCT READ DTOs
# =====================================================

class WarehouseProductReadBase(WarehouseProductBase):
    """Base read DTO for warehouse product"""
    # Product fields (from related product)
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    sku: Optional[str] = Field(None, description="Product SKU")
    bar_code: Optional[str] = Field(None, description="Product barcode")
    is_active: bool = Field(default=True, description="Whether the product is active")
    
    # Warehouse product fields
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
    remaining_qty: int = Field(default=0, description="Total quantity at this warehouse location (sum of qty_at_location from all active batches, excludes VOID and CANCELLED). Should match current_qty.")
    specific_product_all_batch_remaining_qty: int = Field(default=0, description="Total remaining quantity across all batches for this product at this warehouse location (sum of qty_at_location from all active batches, excludes VOID and CANCELLED)")
    
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
    pricing_rule_applied: Optional[PricingRuleAppliedDto] = Field(None, description="Pricing rule applied to the product")
    tax_rule_applied: Optional[TaxRuleAppliedDto] = Field(None, description="Tax rule applied to the product")


class CreateWarehouseProductControllerReadDto(WarehouseProductReadBase):
    """Controller DTO for create warehouse product read operations"""
    pass


class CreateWarehouseProductServiceReadDto(WarehouseProductReadBase):
    """Service DTO for create warehouse product read operations"""
    pass


class AddStockWarehouseProductControllerReadDto(WarehouseProductReadBase):
    """Controller DTO for add stock warehouse product read operations"""
    pass


class AddStockWarehouseProductServiceReadDto(WarehouseProductReadBase):
    """Service DTO for add stock warehouse product read operations"""
    pass


class UpdateWarehouseProductControllerReadDto(WarehouseProductReadBase):
    """Controller DTO for update warehouse product read operations"""
    pass


class UpdateWarehouseProductServiceReadDto(WarehouseProductReadBase):
    """Service DTO for update warehouse product read operations"""
    pass


class GetWarehouseProductControllerReadDto(WarehouseProductReadBase):
    """Controller DTO for get warehouse product read operations"""
    pass


class GetWarehouseProductServiceReadDto(WarehouseProductReadBase):
    """Service DTO for get warehouse product read operations"""
    pass


class GetWarehouseProductsControllerReadDto(WarehouseProductReadBase):
    """Controller DTO for get warehouse products list read operations"""
    pass


class GetWarehouseProductsServiceReadDto(WarehouseProductReadBase):
    """Service DTO for get warehouse products list read operations"""
    pass


class DeleteWarehouseProductReadBase(BaseModel):
    """Base read DTO for soft delete warehouse product result"""
    loc_id: str
    product_id: str
    message: str


class DeleteWarehouseProductControllerReadDto(DeleteWarehouseProductReadBase):
    """Controller DTO for soft delete warehouse product read operations"""
    pass


class DeleteWarehouseProductServiceReadDto(DeleteWarehouseProductReadBase):
    """Service DTO for soft delete warehouse product read operations"""
    pass


class PermanentDeleteWarehouseProductReadBase(BaseModel):
    """Base read DTO for permanent delete warehouse product result"""
    loc_id: str
    product_id: str
    message: str


class PermanentDeleteWarehouseProductControllerReadDto(PermanentDeleteWarehouseProductReadBase):
    """Controller DTO for permanent delete warehouse product read operations"""
    pass


class PermanentDeleteWarehouseProductServiceReadDto(PermanentDeleteWarehouseProductReadBase):
    """Service DTO for permanent delete warehouse product read operations"""
    pass


# =====================================================
# REVERSE BATCH WAREHOUSE PRODUCT READ DTOs
# =====================================================

class ReverseBatchWarehouseProductReadBase(BaseModel):
    """Base read DTO for reverse batch warehouse product result"""
    loc_id: str
    product_id: str
    batch_number: str
    qty_reversed: int
    message: str


class ReverseBatchWarehouseProductControllerReadDto(ReverseBatchWarehouseProductReadBase):
    """Controller DTO for reverse batch warehouse product read operations"""
    pass


class ReverseBatchWarehouseProductServiceReadDto(ReverseBatchWarehouseProductReadBase):
    """Service DTO for reverse batch warehouse product read operations"""
    pass


# =====================================================
# WAREHOUSE PRODUCT STATISTICS READ DTOs
# =====================================================

class WarehouseProductStatisticsReadBase(BaseModel):
    """Base read DTO for warehouse product statistics"""
    total_products: int = Field(default=0, description="Total number of warehouse products")
    total_quantity: int = Field(default=0, description="Total quantity of all warehouse products")
    active_products: int = Field(default=0, description="Number of active warehouse products")
    low_stock_products: int = Field(default=0, description="Number of products at or below reorder level")
    out_of_stock_products: int = Field(default=0, description="Number of products with zero quantity")
    average_quantity: float = Field(default=0.0, description="Average quantity per product")
    products_needing_reorder: int = Field(default=0, description="Number of products that need reordering")
    well_stocked_products: int = Field(default=0, description="Number of products above reorder level")


class GetWarehouseProductStatisticsControllerReadDto(WarehouseProductStatisticsReadBase):
    """Controller DTO for warehouse product statistics"""
    pass


class GetWarehouseProductStatisticsServiceReadDto(WarehouseProductStatisticsReadBase):
    """Service DTO for warehouse product statistics"""
    pass

