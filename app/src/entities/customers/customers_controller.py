from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.customers.customers_service import CustomersService
from src.entities.customers.customers_write_dto import (
    CreateCustomerControllerWriteDto,
    UpdateCustomerControllerWriteDto,
    DeleteCustomerControllerWriteDto,
)
from src.entities.customers.customers_read_dto import (
    CreateCustomerControllerReadDto,
    UpdateCustomerControllerReadDto,
    DeleteCustomerControllerReadDto,
    GetCustomerControllerReadDto,
    GetCustomersControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

customers_router = APIRouter(prefix="/customers", tags=["Users Customers"])
logger = get_logger("customers")


# 1. Create Customer
@customers_router.post("/add", response_model=Respons[CreateCustomerControllerReadDto])
def create_customer(
    data: CreateCustomerControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new customer"""
    with LogContext(
        "customers",
        "create_customer",
        fullname=data.fullname,
    ):
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        required_permissions = ["permission-msg-customers-create"]
        
        logger.info(
            "Processing create customer request",
            extra={
                "extra_fields": {
                    "endpoint": "/customers/add",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "fullname": data.fullname,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=required_permissions
        )

        if not is_authorized:
            # Get user's actual permissions for debugging
            user_permissions = AuthService.get_user_permissions(current_user.data)
            logger.warning(
                "Create customer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/add",
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "required_permissions": required_permissions,
                        "user_permissions": user_permissions,
                        "error": "Unauthorized access - missing required permission",
                        "status": "failed",
                        "message": f"User is missing required permission: {', '.join(required_permissions)}",
                    }
                },
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized access - missing required permission: {', '.join(required_permissions)}"
            )

        service_result = CustomersService.create_customer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Customer created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/add",
                        "customer_id": (
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
                f"Customer creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Customer
@customers_router.put("/update", response_model=Respons[UpdateCustomerControllerReadDto])
def update_customer(
    data: UpdateCustomerControllerWriteDto,
    customer_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a customer"""
    with LogContext(
        "customers",
        "update_customer",
        customer_id=customer_id,
    ):
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        required_permissions = ["permission-msg-customers-update"]
        
        logger.info(
            "Processing update customer request",
            extra={
                "extra_fields": {
                    "endpoint": "/customers/update",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "customer_id": customer_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=required_permissions
        )

        if not is_authorized:
            # Get user's actual permissions for debugging
            user_permissions = AuthService.get_user_permissions(current_user.data)
            logger.warning(
                "Update customer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/update",
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "customer_id": customer_id,
                        "required_permissions": required_permissions,
                        "user_permissions": user_permissions,
                        "error": "Unauthorized access - missing required permission",
                        "status": "failed",
                        "message": f"User is missing required permission: {', '.join(required_permissions)}",
                    }
                },
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized access - missing required permission: {', '.join(required_permissions)}"
            )

        service_result = CustomersService.update_customer(
            data=data,
            customer_id=customer_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Customer updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/update",
                        "customer_id": customer_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Customer update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/update",
                        "customer_id": customer_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Customer
@customers_router.get("/get", response_model=Respons[GetCustomerControllerReadDto])
def get_customer(
    customer_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single customer by ID"""
    with LogContext(
        "customers",
        "get_customer",
        customer_id=customer_id,
    ):
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        required_permissions = ["permission-msg-customers-get"]
        
        logger.info(
            "Processing get customer request",
            extra={
                "extra_fields": {
                    "endpoint": "/customers/get",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "customer_id": customer_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=required_permissions
        )

        if not is_authorized:
            # Get user's actual permissions for debugging
            user_permissions = AuthService.get_user_permissions(current_user.data)
            logger.warning(
                "Get customer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/get",
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "customer_id": customer_id,
                        "required_permissions": required_permissions,
                        "user_permissions": user_permissions,
                        "error": "Unauthorized access - missing required permission",
                        "status": "failed",
                        "message": f"User is missing required permission: {', '.join(required_permissions)}",
                    }
                },
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized access - missing required permission: {', '.join(required_permissions)}"
            )

        service_result = CustomersService.get_customer(
            customer_id=customer_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Customer retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/get",
                        "customer_id": customer_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Customer retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/get",
                        "customer_id": customer_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Customers (List)
@customers_router.get("/list", response_model=Respons[GetCustomersControllerReadDto])
def get_customers(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by fullname, email, or contact"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of customers with filters and pagination"""
    with LogContext(
        "customers",
        "get_customers",
        tenant_id=current_user.data[0].tenant_id,
    ):
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        required_permissions = ["permission-msg-customers-get"]
        
        logger.info(
            "Processing get customers request",
            extra={
                "extra_fields": {
                    "endpoint": "/customers/list",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
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
            required_permissions=required_permissions
        )

        if not is_authorized:
            # Get user's actual permissions for debugging
            user_permissions = AuthService.get_user_permissions(current_user.data)
            logger.warning(
                "Get customers failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/list",
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "required_permissions": required_permissions,
                        "user_permissions": user_permissions,
                        "error": "Unauthorized access - missing required permission",
                        "status": "failed",
                        "message": f"User is missing required permission: {', '.join(required_permissions)}",
                    }
                },
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized access - missing required permission: {', '.join(required_permissions)}"
            )

        service_result = CustomersService.get_customers(
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
                "Customers retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Customers retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Delete Customer
@customers_router.delete("/delete", response_model=Respons[DeleteCustomerControllerReadDto])
def delete_customer(
    data: DeleteCustomerControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a customer"""
    with LogContext(
        "customers",
        "delete_customer",
        customer_id=data.customer_id if hasattr(data, "customer_id") else "unknown",
    ):
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        required_permissions = ["permission-msg-customers-delete"]
        
        logger.info(
            "Processing delete customer request",
            extra={
                "extra_fields": {
                    "endpoint": "/customers/delete",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "customer_id": data.customer_id,
                }
            },
        )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=required_permissions
        )

        if not is_authorized:
            # Get user's actual permissions for debugging
            user_permissions = AuthService.get_user_permissions(current_user.data)
            logger.warning(
                "Delete customer failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/customers/delete",
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "customer_id": data.customer_id,
                        "required_permissions": required_permissions,
                        "user_permissions": user_permissions,
                        "error": "Unauthorized access - missing required permission",
                        "status": "failed",
                        "message": f"User is missing required permission: {', '.join(required_permissions)}",
                    }
                },
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized access - missing required permission: {', '.join(required_permissions)}"
            )

        service_result = CustomersService.delete_customer(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result

