from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field
from src.entities.deliveries.deliveries_base import (
    DeliveryBase,
    DeliveryItemBase,
)


# =====================================================
# DELIVERY ITEM READ DTOs
# =====================================================

class DeliveryItemReadBase(DeliveryItemBase):
    """Base read DTO for delivery item"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    delivery_id: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    product_name: Optional[str] = Field(None, description="Product name (joined from products table)")


# =====================================================
# DELIVERY READ DTOs
# =====================================================

class DeliveryReadBase(DeliveryBase):
    """Base read DTO for delivery"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    delivery_number: str
    scheduled_date: Optional[date] = None
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    sale_number: Optional[str] = Field(None, description="Sale number (joined from sales table)")
    customer_name: Optional[str] = Field(None, description="Customer name (joined from sales and customers)")
    driver_name: Optional[str] = Field(None, description="Driver name (joined from users table)")
    currency_name: Optional[str] = Field(None, description="Currency name (joined from currency table)")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol (joined from currency table)")
    items: List[DeliveryItemReadBase] = Field(default_factory=list, description="List of delivery items")


class CreateDeliveryControllerReadDto(DeliveryReadBase):
    """Controller DTO for create delivery read operations"""
    pass


class CreateDeliveryServiceReadDto(DeliveryReadBase):
    """Service DTO for create delivery read operations"""
    pass


class UpdateDeliveryControllerReadDto(DeliveryReadBase):
    """Controller DTO for update delivery read operations"""
    pass


class UpdateDeliveryServiceReadDto(DeliveryReadBase):
    """Service DTO for update delivery read operations"""
    pass


class GetDeliveryControllerReadDto(DeliveryReadBase):
    """Controller DTO for get delivery read operations"""
    pass


class GetDeliveryServiceReadDto(DeliveryReadBase):
    """Service DTO for get delivery read operations"""
    pass


class GetDeliveriesControllerReadDto(BaseModel):
    """Controller DTO for get deliveries list read operations"""
    deliveries: List[DeliveryReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


class GetDeliveriesServiceReadDto(BaseModel):
    """Service DTO for get deliveries list read operations"""
    deliveries: List[DeliveryReadBase] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


class UpdateDeliveryStatusControllerReadDto(DeliveryReadBase):
    """Controller DTO for update delivery status read operations"""
    pass


class UpdateDeliveryStatusServiceReadDto(DeliveryReadBase):
    """Service DTO for update delivery status read operations"""
    pass


class DispatchDeliveryControllerReadDto(DeliveryReadBase):
    """Controller DTO for dispatch delivery read operations"""
    pass


class DispatchDeliveryServiceReadDto(DeliveryReadBase):
    """Service DTO for dispatch delivery read operations"""
    pass


class CompleteDeliveryControllerReadDto(DeliveryReadBase):
    """Controller DTO for complete delivery read operations"""
    pass


class CompleteDeliveryServiceReadDto(DeliveryReadBase):
    """Service DTO for complete delivery read operations"""
    pass


class CancelDeliveryControllerReadDto(DeliveryReadBase):
    """Controller DTO for cancel delivery read operations"""
    pass


class CancelDeliveryServiceReadDto(DeliveryReadBase):
    """Service DTO for cancel delivery read operations"""
    pass


class DeleteDeliveryControllerReadDto(DeliveryReadBase):
    """Controller DTO for delete delivery read operations"""
    pass


class DeleteDeliveryServiceReadDto(DeliveryReadBase):
    """Service DTO for delete delivery read operations"""
    pass


# =====================================================
# DELIVERY STATISTICS READ DTOs
# =====================================================

class DeliveriesStatisticsReadDto(BaseModel):
    """Deliveries statistics DTO"""
    # Overall statistics
    total_deliveries: int = Field(default=0, description="Total number of deliveries")
    total_delivery_fee: float = Field(default=0, description="Total delivery fee collected")
    total_pending: int = Field(default=0, description="Total pending deliveries")
    total_delivered: int = Field(default=0, description="Total delivered deliveries")
    total_failed: int = Field(default=0, description="Total failed deliveries")
    total_cancelled: int = Field(default=0, description="Total cancelled deliveries")
    total_out_for_delivery: int = Field(default=0, description="Total out for delivery")
    average_delivery_fee: float = Field(default=0, description="Average delivery fee")
    
    # Date range (if provided)
    from_date: Optional[str] = Field(None, description="Start date of statistics period")
    to_date: Optional[str] = Field(None, description="End date of statistics period")


class GetDeliveriesStatisticsControllerReadDto(DeliveriesStatisticsReadDto):
    """Controller DTO for deliveries statistics"""
    pass


class GetDeliveriesStatisticsServiceReadDto(DeliveriesStatisticsReadDto):
    """Service DTO for deliveries statistics"""
    pass

