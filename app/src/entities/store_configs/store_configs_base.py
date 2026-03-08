from typing import Optional
from pydantic import BaseModel, Field
from datetime import time


# =====================================================
# STORE CONFIG BASE DTOs
# =====================================================

class StoreConfigBase(BaseModel):
    """Base DTO for store config information"""
    store_name: Optional[str] = Field(None, max_length=255, description="Name of the store")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the store")
    is_visible_on_ecommerce: bool = Field(default=False, description="Whether the store is visible on ecommerce")
    address: Optional[str] = Field(None, description="Store address")
    is_active: bool = Field(default=True, description="Whether the store is active")
    manager_id: Optional[str] = Field(None, description="Store manager user ID")
    enable_auto_stock_take: bool = Field(default=False, description="Whether to enable automatic stock take")
    num_of_days_to_take_stock: int = Field(default=0, ge=0, description="Number of days to take stock")
    enable_daily_reports: bool = Field(default=False, description="Whether to enable daily reports")
    openning_time: Optional[time] = Field(None, description="Store opening time")
    closing_time: Optional[time] = Field(None, description="Store closing time")
    lock_based_on_closing_time: bool = Field(default=False, description="Whether to lock based on closing time")
    change_to_card: bool = Field(default=False, description="Show products in card form when true, table form when false")

