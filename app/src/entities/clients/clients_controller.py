from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.clients.clients_service import ClientsService
from src.entities.clients.clients_write_dto import (
    CreateClientControllerWriteDto,
    UpdateClientControllerWriteDto,
    DeleteClientControllerWriteDto,
    PermanentDeleteClientControllerWriteDto,
)
from src.entities.clients.clients_read_dto import (
    CreateClientControllerReadDto,
    UpdateClientControllerReadDto,
    DeleteClientControllerReadDto,
    GetClientControllerReadDto,
    GetClientsControllerReadDto,
    PermanentDeleteClientControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

clients_router = APIRouter(prefix="/clients", tags=["Clients", "Users"])
logger = get_logger("clients")


# 1. Create Client
@clients_router.post("/add", response_model=Respons[CreateClientControllerReadDto])
def create_client(
    data: CreateClientControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new client"""
    with LogContext(
        "clients",
        "create_client",
        fullname=data.fullname,
    ):
        logger.info(
            "Processing create client request",
            extra={
                "extra_fields": {
                    "endpoint": "/clients/add",
                    "fullname": data.fullname,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-clients-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create client failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ClientsService.create_client(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Client created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/add",
                        "client_id": (
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
                f"Client creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Client
@clients_router.put("/update", response_model=Respons[UpdateClientControllerReadDto])
def update_client(
    data: UpdateClientControllerWriteDto,
    client_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a client"""
    with LogContext(
        "clients",
        "update_client",
        client_id=client_id,
    ):
        logger.info(
            "Processing update client request",
            extra={
                "extra_fields": {
                    "endpoint": "/clients/update",
                    "client_id": client_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-clients-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update client failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/update",
                        "client_id": client_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ClientsService.update_client(
            data=data,
            client_id=client_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Client updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/update",
                        "client_id": client_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Client update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/update",
                        "client_id": client_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Delete Client (Soft Delete)
@clients_router.delete("/delete", response_model=Respons[DeleteClientControllerReadDto])
def delete_client(
    client_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Soft delete a client"""
    with LogContext(
        "clients",
        "delete_client",
        client_id=client_id,
    ):
        logger.info(
            "Processing delete client request",
            extra={
                "extra_fields": {
                    "endpoint": "/clients/delete",
                    "client_id": client_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-clients-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete client failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/delete",
                        "client_id": client_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        from src.entities.clients.clients_write_dto import DeleteClientServiceWriteDto
        service_result = ClientsService.delete_client(
            data=DeleteClientServiceWriteDto(client_id=client_id),
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Client deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/delete",
                        "client_id": client_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Client deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/delete",
                        "client_id": client_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Client
@clients_router.get("/get", response_model=Respons[GetClientControllerReadDto])
def get_client(
    client_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single client by ID"""
    with LogContext(
        "clients",
        "get_client",
        client_id=client_id,
    ):
        logger.info(
            "Processing get client request",
            extra={
                "extra_fields": {
                    "endpoint": "/clients/get",
                    "client_id": client_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-clients-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get client failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/get",
                        "client_id": client_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ClientsService.get_client(
            client_id=client_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Client retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/get",
                        "client_id": client_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Client retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/get",
                        "client_id": client_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Get Clients (List)
@clients_router.get("/list", response_model=Respons[GetClientsControllerReadDto])
def get_clients(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by fullname, email, or contact"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of clients with filters and pagination"""
    with LogContext(
        "clients",
        "get_clients",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get clients request",
            extra={
                "extra_fields": {
                    "endpoint": "/clients/list",
                    "filters": {
                        "is_active": is_active,
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
            required_permissions=["permission-msg-clients-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get clients failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ClientsService.get_clients(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            is_active=is_active,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Clients retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Clients retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Permanent Delete Client
@clients_router.delete("/permanent-delete", response_model=Respons[PermanentDeleteClientControllerReadDto])
def permanent_delete_client(
    data: PermanentDeleteClientControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete a client"""
    with LogContext(
        "clients",
        "permanent_delete_client",
        client_id=data.client_id if hasattr(data, "client_id") else "unknown",
    ):
        logger.info(
            "Processing permanent delete client request",
            extra={
                "extra_fields": {
                    "endpoint": "/clients/permanent-delete",
                    "client_id": data.client_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-clients-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Permanent delete client failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/clients/permanent-delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ClientsService.permanent_delete_client(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result

