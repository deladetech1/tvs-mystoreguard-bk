from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.entities.appointments.appointments_base import (
    AppointmentBase,
    AppointmentType,
    AppointmentStatus,
)


# =====================================================
# CREATE APPOINTMENT WRITE DTOs
# =====================================================

class CreateAppointmentWriteBase(AppointmentBase):
    """Base write DTO for creating an appointment"""
    pass


class CreateAppointmentControllerWriteDto(CreateAppointmentWriteBase):
    """Controller DTO for creating an appointment"""
    pass


class CreateAppointmentServiceWriteDto(CreateAppointmentWriteBase):
    """Service DTO for creating an appointment"""
    pass


# =====================================================
# UPDATE APPOINTMENT WRITE DTOs
# =====================================================

class UpdateAppointmentWriteBase(BaseModel):
    """Base write DTO for updating an appointment"""
    appointment_type: Optional[AppointmentType] = None
    status: Optional[AppointmentStatus] = None
    is_walk_in: Optional[bool] = None
    customer_id: Optional[str] = None
    assigned_to: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    description: Optional[str] = None


class UpdateAppointmentControllerWriteDto(UpdateAppointmentWriteBase):
    """Controller DTO for updating an appointment"""
    pass


class UpdateAppointmentServiceWriteDto(UpdateAppointmentWriteBase):
    """Service DTO for updating an appointment"""
    pass


# =====================================================
# DELETE APPOINTMENT WRITE DTOs
# =====================================================

class DeleteAppointmentWriteBase(BaseModel):
    """Base write DTO for deleting an appointment"""
    appointment_id: str


class DeleteAppointmentControllerWriteDto(DeleteAppointmentWriteBase):
    """Controller DTO for deleting an appointment"""
    pass


class DeleteAppointmentServiceWriteDto(DeleteAppointmentWriteBase):
    """Service DTO for deleting an appointment"""
    pass



