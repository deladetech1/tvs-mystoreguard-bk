from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =====================================================
# ENUMS AND LITERALS
# =====================================================

AppointmentType = Literal['SALES', 'SERVICE', 'DELIVERY', 'INSTALLATION', 'CONSULTATION', 'OTHERS']
AppointmentStatus = Literal['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'NO_SHOW', 'CANCELLED', 'RESCHEDULED']


# =====================================================
# APPOINTMENT BASE DTOs
# =====================================================

class AppointmentBase(BaseModel):
    """Base DTO for appointment information"""
    appointment_type: AppointmentType = Field(..., description="Type of appointment")
    status: AppointmentStatus = Field(default='PENDING', description="Status of the appointment")
    is_walk_in: bool = Field(default=False, description="Whether this is a walk-in appointment")
    customer_id: Optional[str] = Field(None, description="Customer ID (optional for walk-ins)")
    assigned_to: Optional[str] = Field(None, description="User ID assigned to handle the appointment")
    start_datetime: datetime = Field(..., description="Start date and time of the appointment")
    end_datetime: datetime = Field(..., description="End date and time of the appointment")
    description: Optional[str] = Field(None, description="Additional description or notes")



