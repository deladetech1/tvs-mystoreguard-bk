from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# =====================================================
# CURRENCY READ DTOs
# =====================================================

class CurrencyReadBase(BaseModel):
    """Base read DTO for currency"""
    id: str
    tenant_id: str
    name: str
    code: str
    symbol: str
    country: Optional[str] = None
    decimal_places: int = Field(default=2, description="Number of decimal places")
    thousand_separator: Optional[str] = Field(default=',', description="Thousand separator")
    decimal_separator: Optional[str] = Field(default='.', description="Decimal separator")
    currency_position: str = Field(default='before', description="Currency position: 'before' or 'after'")
    locale: Optional[str] = None
    minor_unit_name: Optional[str] = None
    is_default: bool = Field(default=False, description="Whether this is the default currency")
    exchange_rate: Optional[Decimal] = Field(None, decimal_places=6, description="Exchange rate")
    exchange_rate_source: Optional[str] = Field(default='manual', description="Exchange rate source: 'manual' or 'auto'")
    delete_status: str
    is_active: bool = Field(default=True, description="Whether the currency is active")
    description: Optional[str] = None
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None


class GetCurrenciesControllerReadDto(CurrencyReadBase):
    """Controller DTO for get currencies read operations"""
    pass


class GetCurrenciesServiceReadDto(CurrencyReadBase):
    """Service DTO for get currencies read operations"""
    pass


# =====================================================
# SIMPLIFIED CURRENCY READ DTOs (for list and get endpoints)
# =====================================================

class CurrencySimpleReadBase(BaseModel):
    """Simplified read DTO for currency - includes id, name, code, symbol, decimal_places, currency_position, and is_default"""
    id: str = Field(..., description="Currency ID")
    name: str = Field(..., description="Currency name")
    code: str = Field(..., description="Currency code")
    symbol: str = Field(..., description="Currency symbol")
    decimal_places: int = Field(default=2, description="Number of decimal places")
    currency_position: str = Field(default='before', description="Currency position: 'before' or 'after'")
    is_default: bool = Field(default=False, description="Whether this is the default currency")


class GetCurrencySimpleControllerReadDto(CurrencySimpleReadBase):
    """Controller DTO for get currency (simplified) read operations"""
    pass


class GetCurrencySimpleServiceReadDto(CurrencySimpleReadBase):
    """Service DTO for get currency (simplified) read operations"""
    pass


class GetCurrenciesSimpleControllerReadDto(CurrencySimpleReadBase):
    """Controller DTO for get currencies list (simplified) read operations"""
    pass


class GetCurrenciesSimpleServiceReadDto(CurrencySimpleReadBase):
    """Service DTO for get currencies list (simplified) read operations"""
    pass

