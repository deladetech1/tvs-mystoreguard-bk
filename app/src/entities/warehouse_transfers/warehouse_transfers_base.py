from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class WarehouseTransferItemInput(BaseModel):
    """A single product + quantity line within a warehouse transfer"""
    product_id: str = Field(..., description="Product ID to transfer")
    qty: int = Field(..., gt=0, description="Quantity to transfer")


class WarehouseTransferBase(BaseModel):
    """Base model for warehouse transfers"""
    items: List[WarehouseTransferItemInput] = Field(
        ..., min_length=1, description="Products and quantities to transfer (at least one)"
    )
    destination_type: Literal["STORE", "WAREHOUSE"] = Field(..., description="Destination type")
    destination_id: str = Field(..., description="Destination location ID")
    person_to_approve_id: str = Field(..., description="User ID of person to approve the transfer")
    description: Optional[str] = Field(None, description="Optional description for the transfer")
