from typing import Optional
from datetime import datetime, time
from pydantic import BaseModel, Field
from src.entities.store_configs.store_configs_base import StoreConfigBase


# =====================================================
# STORE CONFIG READ DTOs
# =====================================================

class StoreConfigReadBase(StoreConfigBase):
    """Base read DTO for store config"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    next_stock_take_datetime: Optional[datetime] = Field(None, description="Next scheduled stock take datetime from active audit record")
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    manager: Optional[str] = Field(None, description="Store manager fullname")


class CreateOrUpdateStoreConfigControllerReadDto(StoreConfigReadBase):
    """Controller DTO for create/update store config read operations"""
    pass


class CreateOrUpdateStoreConfigServiceReadDto(StoreConfigReadBase):
    """Service DTO for create/update store config read operations"""
    pass


class GetStoreConfigControllerReadDto(StoreConfigReadBase):
    """Controller DTO for get store config read operations"""
    pass


class GetStoreConfigServiceReadDto(StoreConfigReadBase):
    """Service DTO for get store config read operations"""
    pass

