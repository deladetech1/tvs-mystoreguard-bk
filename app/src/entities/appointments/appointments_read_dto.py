from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.entities.appointments.appointments_base import (
    AppointmentBase,
)


# =====================================================
# APPOINTMENT READ DTOs
# =====================================================

class AppointmentReadBase(AppointmentBase):
    """Base read DTO for appointment"""
    id: str
    tenant_id: str
    org_id: str
    bus_id: str
    loc_id: str
    cdate: str
    ctime: str
    cdatetime: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    customer_name: Optional[str] = Field(None, description="Customer fullname")
    assigned_to_name: Optional[str] = Field(None, description="Assigned user fullname")
    assigned_to_id: Optional[str] = Field(None, description="Assigned user ID (alias for assigned_to field)")


class CreateAppointmentControllerReadDto(AppointmentReadBase):
    """Controller DTO for create appointment read operations"""
    pass


class CreateAppointmentServiceReadDto(AppointmentReadBase):
    """Service DTO for create appointment read operations"""
    pass


class UpdateAppointmentControllerReadDto(AppointmentReadBase):
    """Controller DTO for update appointment read operations"""
    pass


class UpdateAppointmentServiceReadDto(AppointmentReadBase):
    """Service DTO for update appointment read operations"""
    pass


class GetAppointmentControllerReadDto(AppointmentReadBase):
    """Controller DTO for get appointment read operations"""
    pass


class GetAppointmentServiceReadDto(AppointmentReadBase):
    """Service DTO for get appointment read operations"""
    pass


class GetAppointmentsControllerReadDto(AppointmentReadBase):
    """Controller DTO for get appointments read operations"""
    pass


class GetAppointmentsServiceReadDto(AppointmentReadBase):
    """Service DTO for get appointments read operations"""
    pass


class DeleteAppointmentReadBase(BaseModel):
    """Base read DTO for delete appointment result"""
    appointment_id: str
    message: str


class DeleteAppointmentControllerReadDto(DeleteAppointmentReadBase):
    """Controller DTO for delete appointment read operations"""
    pass


class DeleteAppointmentServiceReadDto(DeleteAppointmentReadBase):
    """Service DTO for delete appointment read operations"""
    pass



