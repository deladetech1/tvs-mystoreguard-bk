from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.appointments.appointments_service import AppointmentsService
from src.entities.appointments.appointments_write_dto import (
    CreateAppointmentControllerWriteDto,
    UpdateAppointmentControllerWriteDto,
    DeleteAppointmentControllerWriteDto,
)
from src.entities.appointments.appointments_read_dto import (
    CreateAppointmentControllerReadDto,
    UpdateAppointmentControllerReadDto,
    DeleteAppointmentControllerReadDto,
    GetAppointmentControllerReadDto,
    GetAppointmentsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

appointments_router = APIRouter(prefix="/appointments", tags=["Appointments"])
logger = get_logger("appointments")


# 1. Create Appointment
@appointments_router.post("/add", response_model=Respons[CreateAppointmentControllerReadDto])
def create_appointment(
    data: CreateAppointmentControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new appointment"""
    with LogContext(
        "appointments",
        "create_appointment",
        appointment_type=data.appointment_type,
    ):
        logger.info(
            "Processing create appointment request",
            extra={
                "extra_fields": {
                    "endpoint": "/appointments/add",
                    "appointment_type": data.appointment_type,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-appointments-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create appointment failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AppointmentsService.create_appointment(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Appointment created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/add",
                        "appointment_id": (
                            service_result.data.id 
                            if service_result.data and hasattr(service_result.data, 'id')
                            else (service_result.data[0].id if isinstance(service_result.data, list) and service_result.data else None)
                        ),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Appointment creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Appointment
@appointments_router.put("/update", response_model=Respons[UpdateAppointmentControllerReadDto])
def update_appointment(
    data: UpdateAppointmentControllerWriteDto,
    appointment_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update an appointment"""
    with LogContext(
        "appointments",
        "update_appointment",
        appointment_id=appointment_id,
    ):
        logger.info(
            "Processing update appointment request",
            extra={
                "extra_fields": {
                    "endpoint": "/appointments/update",
                    "appointment_id": appointment_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-appointments-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update appointment failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/update",
                        "appointment_id": appointment_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AppointmentsService.update_appointment(
            data=data,
            appointment_id=appointment_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Appointment updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/update",
                        "appointment_id": appointment_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Appointment update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/update",
                        "appointment_id": appointment_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Appointment
@appointments_router.get("/get", response_model=Respons[GetAppointmentControllerReadDto])
def get_appointment(
    appointment_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single appointment by ID"""
    with LogContext(
        "appointments",
        "get_appointment",
        appointment_id=appointment_id,
    ):
        logger.info(
            "Processing get appointment request",
            extra={
                "extra_fields": {
                    "endpoint": "/appointments/get",
                    "appointment_id": appointment_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-appointments-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get appointment failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/get",
                        "appointment_id": appointment_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AppointmentsService.get_appointment(
            appointment_id=appointment_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
        )

        if service_result.success:
            logger.info(
                "Appointment retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/get",
                        "appointment_id": appointment_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Appointment retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/get",
                        "appointment_id": appointment_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Appointments (List)
@appointments_router.get("/list", response_model=Respons[GetAppointmentsControllerReadDto])
def get_appointments(
    status: Optional[str] = Query(None, description="Filter by status"),
    appointment_type: Optional[str] = Query(None, description="Filter by appointment type"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user ID"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    search: Optional[str] = Query(None, description="Search in description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of appointments with filters and pagination"""
    with LogContext(
        "appointments",
        "get_appointments",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get appointments request",
            extra={
                "extra_fields": {
                    "endpoint": "/appointments/list",
                    "filters": {
                        "status": status,
                        "appointment_type": appointment_type,
                        "assigned_to": assigned_to,
                        "customer_id": customer_id,
                        "search": search,
                        "page": page,
                        "size": size,
                    },
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-appointments-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get appointments failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AppointmentsService.get_appointments(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            status=status,
            appointment_type=appointment_type,
            assigned_to=assigned_to,
            customer_id=customer_id,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Appointments retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Appointments retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Appointment
@appointments_router.delete("/delete", response_model=Respons[DeleteAppointmentControllerReadDto])
def delete_appointment(
    data: DeleteAppointmentControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete an appointment"""
    with LogContext(
        "appointments",
        "delete_appointment",
        appointment_id=data.appointment_id if hasattr(data, "appointment_id") else "unknown",
    ):
        logger.info(
            "Processing delete appointment request",
            extra={
                "extra_fields": {
                    "endpoint": "/appointments/delete",
                    "appointment_id": data.appointment_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-appointments-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete appointment failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/appointments/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = AppointmentsService.delete_appointment(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result



