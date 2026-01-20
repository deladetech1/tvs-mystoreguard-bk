from typing import Optional
from pydantic import BaseModel, Field
from datetime import time
from src.entities.warehouse_configs.warehouse_configs_base import WarehouseConfigBase


# =====================================================
# CREATE/UPDATE WAREHOUSE CONFIG WRITE DTOs
# =====================================================

class CreateOrUpdateWarehouseConfigWriteBase(WarehouseConfigBase):
    """Base write DTO for creating or updating a warehouse config"""
    pass


class CreateOrUpdateWarehouseConfigControllerWriteDto(CreateOrUpdateWarehouseConfigWriteBase):
    """Controller DTO for creating or updating a warehouse config"""
    pass


class CreateOrUpdateWarehouseConfigServiceWriteDto(CreateOrUpdateWarehouseConfigWriteBase):
    """Service DTO for creating or updating a warehouse config"""
    pass

