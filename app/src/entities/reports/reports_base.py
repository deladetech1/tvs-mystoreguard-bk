from typing import Optional, List
from typing_extensions import Literal
from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal


# =====================================================
# ENUMS AND LITERALS
# =====================================================

ReportPeriodType = Literal['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY', 'CUSTOM']
ReportFormatType = Literal['SUMMARY', 'DETAILED', 'GRAPHICAL']
ReportGroupByType = Literal['DAY', 'WEEK', 'MONTH', 'YEAR', 'PRODUCT', 'CATEGORY', 'LOCATION', 'CUSTOMER', 'SUPPLIER']


# =====================================================
# REPORT BASE DTOs
# =====================================================

class ReportBase(BaseModel):
    """Base DTO for report information"""
    pass


class DateRangeFilter(BaseModel):
    """Date range filter for reports"""
    from_date: Optional[date] = Field(None, description="Start date for the report")
    to_date: Optional[date] = Field(None, description="End date for the report")
    period: Optional[ReportPeriodType] = Field('CUSTOM', description="Report period type")


class LocationFilter(BaseModel):
    """Location filter for reports"""
    loc_id: Optional[str] = Field(None, description="Specific location ID filter")
    location_ids: Optional[List[str]] = Field(None, description="List of location IDs to include")


class ProductFilter(BaseModel):
    """Product filter for reports"""
    product_id: Optional[str] = Field(None, description="Specific product ID filter")
    product_ids: Optional[List[str]] = Field(None, description="List of product IDs to include")


class CustomerFilter(BaseModel):
    """Customer filter for reports"""
    customer_id: Optional[str] = Field(None, description="Specific customer ID filter")
    customer_ids: Optional[List[str]] = Field(None, description="List of customer IDs to include")


class SupplierFilter(BaseModel):
    """Supplier filter for reports"""
    supplier_id: Optional[str] = Field(None, description="Specific supplier ID filter")
    supplier_ids: Optional[List[str]] = Field(None, description="List of supplier IDs to include")

