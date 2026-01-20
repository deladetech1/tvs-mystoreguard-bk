from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.products.products_base import (
    ProductBase,
    PurchaseBatchBase,
    BatchStatusType,
)


# =====================================================
# METADATA READ DTOs
# =====================================================

class MetadataReadDto(BaseModel):
    """Read DTO for metadata information"""
    id: str = Field(..., description="Metadata ID")
    name: str = Field(..., description="Metadata name")
    type: str = Field(..., description="Metadata type (TAG, LABEL, CATEGORY, BRAND, etc.)")


# =====================================================
# DOCUMENT READ DTOs
# =====================================================

class DocumentReadDto(BaseModel):
    """Read DTO for document information"""
    doc_id: str = Field(..., description="Document ID")
    description: Optional[str] = Field(None, description="Document description")
    name: Optional[str] = Field(None, description="Document name/file name")
    presigned_url: str = Field(..., description="Presigned URL for the document")


# =====================================================
# PRODUCT MOVEMENT READ DTOs
# =====================================================

class ProductMovementReadDto(BaseModel):
    """Read DTO for product movement"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    product_id: str
    batch_id: Optional[str] = None
    location_type: Optional[str] = None
    location_id: Optional[str] = None
    movement_type: str
    qty: int
    reason: Optional[str] = None
    reference_id: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = Field(None, description="User ID who created the movement")
    updated_by: Optional[str] = Field(None, description="User ID who updated the movement")
    deleted_by: Optional[str] = Field(None, description="User ID who deleted the movement")
    batch_number: Optional[str] = Field(None, description="Batch number from purchase batch")
    product_name: Optional[str] = Field(None, description="Product name")
    location_name: Optional[str] = Field(None, description="Location name")
    created_by_name: Optional[str] = Field(None, description="Fullname of user who created the movement")
    updated_by_name: Optional[str] = Field(None, description="Fullname of user who updated the movement")
    deleted_by_name: Optional[str] = Field(None, description="Fullname of user who deleted the movement")


# =====================================================
# PURCHASE BATCH READ DTOs
# =====================================================

class PurchaseBatchReadDto(PurchaseBatchBase):
    """Read DTO for purchase batch"""
    id: str = Field(..., description="Batch ID")
    batch_number: Optional[str] = Field(None, description="Batch number (auto-generated)")
    tenant_id: str
    org_id: str
    bus_id: str
    product_id: str
    delete_status: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    batch_type: Optional[str] = Field(None, description="Batch type: PURCHASE, OPENING_STOCK, or ADJUSTMENT")
    currency_name: Optional[str] = Field(None, description="Currency name")
    unit_of_measure_name: Optional[str] = Field(None, description="Unit of measure name")
    supplier_name: Optional[str] = Field(None, description="Supplier fullname")
    movements: Optional[List[ProductMovementReadDto]] = Field(default=None, description="List of movements for this batch")


# =====================================================
# PRICING RULE READ DTOs
# =====================================================

class PricingRuleAppliedReadDto(BaseModel):
    """Read DTO for applied pricing rule"""
    rule_id: Optional[str] = Field(None, description="Pricing rule ID")
    rule_name: Optional[str] = Field(None, description="Pricing rule name")
    rule_type: Optional[str] = Field(None, description="Rule type: FIXED_PRICE, PRICE_DISCOUNT, PERCENTAGE_DISCOUNT, PRICE_MARKUP, PERCENTAGE_MARKUP")
    rule_category: Optional[str] = Field(None, description="Rule category: PRICE_ADJUSTMENT or QUANTITY_BASED")
    rule_target_type: Optional[str] = Field(None, description="Rule target type: PRODUCT, ALL_PRODUCTS, SKU, LOCATION, CATEGORY, TAG, BRAND, LABEL")
    rule_target_id: Optional[str] = Field(None, description="Rule target ID")
    price_before: Optional[float] = Field(None, description="Price before rule was applied")
    price_after: Optional[float] = Field(None, description="Price after rule was applied")
    adjustment: Optional[float] = Field(None, description="Price adjustment amount")
    priority: Optional[int] = Field(None, description="Rule priority")


# =====================================================
# TAX RULE READ DTOs
# =====================================================

class TaxAppliedReadDto(BaseModel):
    """Read DTO for individual tax applied to a product"""
    tax_id: Optional[str] = Field(None, description="Tax ID")
    tax_name: Optional[str] = Field(None, description="Tax name")
    rate: Optional[float] = Field(None, description="Tax rate as a percentage")
    is_inclusive: Optional[bool] = Field(None, description="Whether tax is included in the price")
    amount: Optional[float] = Field(None, description="Tax amount in currency")


class TaxRuleAppliedReadDto(BaseModel):
    """Read DTO for applied tax rule"""
    tax_rule_id: Optional[str] = Field(None, description="Tax rule ID")
    tax_rule_name: Optional[str] = Field(None, description="Tax rule name")
    tax_rule_type: Optional[str] = Field(None, description="Tax rule target type: PRODUCT, ALL_PRODUCTS, SKU, LOCATION, CATEGORY, TAG, BRAND, LABEL")
    tax_rule_target_id: Optional[str] = Field(None, description="Tax rule target ID")
    tax_id: Optional[str] = Field(None, description="Tax ID")
    tax_name: Optional[str] = Field(None, description="Tax name")
    rate: Optional[float] = Field(None, description="Tax rate percentage")
    is_inclusive: Optional[bool] = Field(None, description="Whether tax is inclusive (True) or exclusive (False)")
    tax_amount: Optional[float] = Field(None, description="Tax amount applied")
    priority: Optional[int] = Field(None, description="Tax rule priority")


# =====================================================
# PRODUCT READ DTOs
# =====================================================

class ProductReadBase(ProductBase):
    """Base read DTO for product"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    delete_status: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    metadata: List[MetadataReadDto] = Field(default_factory=list, description="List of metadata objects with id, name, and type")
    documents: List[DocumentReadDto] = Field(default_factory=list, description="List of document objects with presigned URLs")
    batches: Optional[List[PurchaseBatchReadDto]] = Field(default=None, description="List of purchase batches")
    remaining_qty: int = Field(default=0, description="Total remaining quantity across all batches (sum of qty_remaining from all active batches, excludes VOID and CANCELLED)")
    specific_product_all_batch_remaining_qty: int = Field(default=0, description="Total remaining quantity across all batches for this product (sum of specific_product_per_batch_remaining_qty from all active batches, excludes VOID and CANCELLED)")
    
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
    taxes_applied: List[TaxAppliedReadDto] = Field(default_factory=list, description="List of taxes applied to the product")
    pricing_rule_applied: Optional[PricingRuleAppliedReadDto] = Field(None, description="Pricing rule applied to the product")
    tax_rule_applied: Optional[TaxRuleAppliedReadDto] = Field(None, description="Tax rule applied to the product")


class CreateProductControllerReadDto(ProductReadBase):
    """Controller DTO for create product read operations"""
    pass


class CreateProductServiceReadDto(ProductReadBase):
    """Service DTO for create product read operations"""
    pass


class UpdateProductControllerReadDto(ProductReadBase):
    """Controller DTO for update product read operations"""
    pass


class UpdateProductServiceReadDto(ProductReadBase):
    """Service DTO for update product read operations"""
    pass


class GetProductControllerReadDto(ProductReadBase):
    """Controller DTO for get product read operations"""
    pass


class GetProductServiceReadDto(ProductReadBase):
    """Service DTO for get product read operations"""
    pass


class GetProductsControllerReadDto(ProductReadBase):
    """Controller DTO for get products list read operations"""
    pass


class GetProductsServiceReadDto(ProductReadBase):
    """Service DTO for get products list read operations"""
    pass


class DeleteProductReadBase(BaseModel):
    """Base read DTO for delete product result"""
    product_id: str
    message: str


class DeleteProductControllerReadDto(DeleteProductReadBase):
    """Controller DTO for delete product read operations"""
    pass


class DeleteProductServiceReadDto(DeleteProductReadBase):
    """Service DTO for delete product read operations"""
    pass


# =====================================================
# PERMANENT DELETE PRODUCT READ DTOs
# =====================================================

class PermanentDeleteProductReadBase(BaseModel):
    """Base read DTO for permanent delete product result"""
    product_id: str
    message: str


class PermanentDeleteProductControllerReadDto(PermanentDeleteProductReadBase):
    """Controller DTO for permanent delete product read operations"""
    pass


class PermanentDeleteProductServiceReadDto(PermanentDeleteProductReadBase):
    """Service DTO for permanent delete product read operations"""
    pass


# =====================================================
# BATCH LOCATIONS READ DTOs
# =====================================================

class BatchLocationReadBase(BaseModel):
    """Base read DTO for batch location"""
    id: str = Field(..., description="Batch location ID")
    tenant_id: str = Field(..., description="Tenant ID")
    org_id: str = Field(..., description="Organization ID")
    bus_id: str = Field(..., description="Business ID")
    loc_id: str = Field(..., description="Location ID")
    purchase_batche_id: str = Field(..., description="Purchase batch ID")
    location_type: str = Field(..., description="Location type (STORE or WAREHOUSE)")
    qty: float = Field(..., description="Quantity")
    batch_number: Optional[str] = Field(None, description="Batch number")
    purchase_date: Optional[datetime] = Field(None, description="Purchase date")
    expiry_date: Optional[datetime] = Field(None, description="Expiry date")
    cost_price: Optional[float] = Field(None, description="Cost price")
    currency_id: Optional[str] = Field(None, description="Currency ID")
    currency_name: Optional[str] = Field(None, description="Currency name")
    unit_of_measure_id: Optional[str] = Field(None, description="Unit of measure ID")
    unit_of_measure_name: Optional[str] = Field(None, description="Unit of measure name")
    supplier_id: Optional[str] = Field(None, description="Supplier ID")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    location_name: Optional[str] = Field(None, description="Location name")
    cdate: str = Field(..., description="Creation date")
    ctime: str = Field(..., description="Creation time")
    cdatetime: datetime = Field(..., description="Creation datetime")


class GetBatchLocationsControllerReadDto(BatchLocationReadBase):
    """Controller DTO for get batch locations read operations"""
    pass


class GetBatchLocationsServiceReadDto(BatchLocationReadBase):
    """Service DTO for get batch locations read operations"""
    pass


# =====================================================
# DELETE BATCH READ DTOs
# =====================================================

class DeleteBatchReadBase(BaseModel):
    """Base read DTO for delete batch result"""
    batch_id: str
    message: str


class DeleteBatchControllerReadDto(DeleteBatchReadBase):
    """Controller DTO for delete batch read operations"""
    pass


class DeleteBatchServiceReadDto(DeleteBatchReadBase):
    """Service DTO for delete batch read operations"""
    pass


# =====================================================
# DELETE MOVEMENT READ DTOs
# =====================================================

class DeleteMovementReadBase(BaseModel):
    """Base read DTO for delete movement result"""
    movement_id: str
    message: str


class DeleteMovementControllerReadDto(DeleteMovementReadBase):
    """Controller DTO for delete movement read operations"""
    pass


class DeleteMovementServiceReadDto(DeleteMovementReadBase):
    """Service DTO for delete movement read operations"""
    pass


# =====================================================
# PRODUCT STATISTICS READ DTOs
# =====================================================

class ProductStatisticsReadBase(BaseModel):
    """Base read DTO for product statistics"""
    total_products: int = Field(default=0, description="Total number of products")
    active_products: int = Field(default=0, description="Number of active products")
    inactive_products: int = Field(default=0, description="Number of inactive products")
    products_with_batches: int = Field(default=0, description="Number of products that have batches")
    products_without_batches: int = Field(default=0, description="Number of products without batches")
    products_in_stock: int = Field(default=0, description="Number of products with remaining quantity > 0")
    products_out_of_stock: int = Field(default=0, description="Number of products with remaining quantity = 0")
    total_remaining_quantity: int = Field(default=0, description="Total remaining quantity across all products")


class GetProductStatisticsControllerReadDto(ProductStatisticsReadBase):
    """Controller DTO for product statistics"""
    pass


class GetProductStatisticsServiceReadDto(ProductStatisticsReadBase):
    """Service DTO for product statistics"""
    pass

