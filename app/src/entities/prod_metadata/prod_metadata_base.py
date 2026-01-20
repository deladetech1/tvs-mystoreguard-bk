from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']
ProductMetadataType = Literal['TAG', 'CATEGORY', 'BRAND', 'LABEL']


# =====================================================
# PRODUCT METADATA BASE DTOs
# =====================================================

class ProductMetadataBase(BaseModel):
    """Base DTO for product metadata information"""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the metadata (tag, category, brand, or label)")
    of_type: ProductMetadataType = Field(..., description="Type of metadata: TAG, CATEGORY, BRAND, or LABEL")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the metadata")

