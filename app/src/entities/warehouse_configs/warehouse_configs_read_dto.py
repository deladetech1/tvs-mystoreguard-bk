from typing import Optional
from datetime import datetime, time
from pydantic import BaseModel, Field
from src.entities.warehouse_configs.warehouse_configs_base import WarehouseConfigBase


# =====================================================
# WAREHOUSE CONFIG READ DTOs
# =====================================================

class WarehouseConfigReadBase(WarehouseConfigBase):
    """Base read DTO for warehouse config"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    cdate: Optional[str] = None
    ctime: Optional[str] = None
    cdatetime: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    manager: Optional[str] = Field(None, description="Warehouse manager fullname")


class CreateOrUpdateWarehouseConfigControllerReadDto(WarehouseConfigReadBase):
    """Controller DTO for create/update warehouse config read operations"""
    pass


class CreateOrUpdateWarehouseConfigServiceReadDto(WarehouseConfigReadBase):
    """Service DTO for create/update warehouse config read operations"""
    pass


class GetWarehouseConfigControllerReadDto(WarehouseConfigReadBase):
    """Controller DTO for get warehouse config read operations"""
    pass


class GetWarehouseConfigServiceReadDto(WarehouseConfigReadBase):
    """Service DTO for get warehouse config read operations"""
    pass

