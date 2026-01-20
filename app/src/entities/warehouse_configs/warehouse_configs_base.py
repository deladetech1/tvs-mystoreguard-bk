from typing import Optional
from pydantic import BaseModel, Field
from datetime import time


# =====================================================
# WAREHOUSE CONFIG BASE DTOs
# =====================================================

class WarehouseConfigBase(BaseModel):
    """Base DTO for warehouse config information"""
    warehouse_name: Optional[str] = Field(None, max_length=255, description="Name of the warehouse")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the warehouse")
    aadress: Optional[str] = Field(None, description="Warehouse address")
    is_active: bool = Field(default=True, description="Whether the warehouse is active")
    manager_id: Optional[str] = Field(None, description="Warehouse manager user ID")
    openning_time: Optional[time] = Field(None, description="Warehouse opening time")
    closing_time: Optional[time] = Field(None, description="Warehouse closing time")

