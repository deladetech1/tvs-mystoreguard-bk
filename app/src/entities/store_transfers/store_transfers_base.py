from typing import Optional, Literal
from pydantic import BaseModel, Field


class StoreTransferBase(BaseModel):
    """Base model for store transfers"""
    product_id: str = Field(..., description="Product ID to transfer")
    qty: int = Field(..., gt=0, description="Quantity to transfer")
    destination_type: Literal["STORE", "WAREHOUSE"] = Field(..., description="Destination type")
    destination_id: str = Field(..., description="Destination location ID")
    person_to_approve_id: str = Field(..., description="User ID of person to approve the transfer")
    description: Optional[str] = Field(None, description="Optional description for the transfer")



