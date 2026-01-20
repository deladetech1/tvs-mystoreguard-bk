from typing import Optional
from pydantic import BaseModel, Field
from datetime import time
from src.entities.store_configs.store_configs_base import StoreConfigBase


# =====================================================
# CREATE/UPDATE STORE CONFIG WRITE DTOs
# =====================================================

class CreateOrUpdateStoreConfigWriteBase(StoreConfigBase):
    """Base write DTO for creating or updating a store config"""
    pass


class CreateOrUpdateStoreConfigControllerWriteDto(CreateOrUpdateStoreConfigWriteBase):
    """Controller DTO for creating or updating a store config"""
    pass


class CreateOrUpdateStoreConfigServiceWriteDto(CreateOrUpdateStoreConfigWriteBase):
    """Service DTO for creating or updating a store config"""
    pass


