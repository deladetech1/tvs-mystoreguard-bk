from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class StoreTransferItemInput(BaseModel):
    """A single product + quantity line within a store transfer"""
    product_id: str = Field(..., description="Product ID to transfer")
    qty: int = Field(..., gt=0, description="Quantity to transfer")


class StoreTransferBase(BaseModel):
    """Base model for store transfers"""
    items: List[StoreTransferItemInput] = Field(
        ..., min_length=1, description="Products and quantities to transfer (at least one)"
    )
    destination_type: Literal["STORE", "WAREHOUSE"] = Field(..., description="Destination type")
    destination_id: str = Field(..., description="Destination location ID")
    person_to_approve_id: str = Field(..., description="User ID of person to approve the transfer")
    description: Optional[str] = Field(None, description="Optional description for the transfer")
