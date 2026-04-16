from fastapi import APIRouter, Depends, HTTPException, Query
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.store_returns.store_returns_service import StoreReturnsService
from src.entities.store_returns.store_returns_write_dto import (
    CreateReturnControllerWriteDto,
    ApproveReturnControllerWriteDto,
    RejectReturnControllerWriteDto,
    ProcessReturnControllerWriteDto,
)
from src.entities.store_returns.store_returns_read_dto import (
    CreateReturnControllerReadDto,
    ApproveReturnControllerReadDto,
    RejectReturnControllerReadDto,
    ProcessReturnControllerReadDto,
    GetReturnControllerReadDto,
    GetReturnsControllerReadDto,
    GetReturnStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

store_returns_router = APIRouter(prefix="/store-returns", tags=["Store Returns"])
logger = get_logger("store_returns")


# 1. Create Return
@store_returns_router.post("/add", response_model=Respons[CreateReturnControllerReadDto])
def create_return(
    data: CreateReturnControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new return request"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext("store_returns", "create_return", loc_id=loc_id, sale_id=data.sale_id):
        logger.info(
            "Processing create return request",
            extra={"extra_fields": {"endpoint": "/store-returns/add", "loc_id": loc_id, "sale_id": data.sale_id}},
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-returns-create"]
        )
        if not is_authorized:
            logger.warning("Create return failed - unauthorized access",
                extra={"extra_fields": {"endpoint": "/store-returns/add", "error": "Unauthorized access", "status": "failed"}})
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreReturnsService.create_return(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info("Return created successfully",
                extra={"extra_fields": {"endpoint": "/store-returns/add", "status": "success"}})
        else:
            logger.warning(f"Return creation failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/store-returns/add", "error": service_result.error, "status": "failed"}})

        return service_result


# 2. Approve Return
@store_returns_router.put("/approve", response_model=Respons[ApproveReturnControllerReadDto])
def approve_return(
    data: ApproveReturnControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Approve a pending return"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext("store_returns", "approve_return", loc_id=loc_id, return_id=data.return_id):
        logger.info("Processing approve return request",
            extra={"extra_fields": {"endpoint": "/store-returns/approve", "return_id": data.return_id}})

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-returns-approve"]
        )
        if not is_authorized:
            logger.warning("Approve return failed - unauthorized access",
                extra={"extra_fields": {"endpoint": "/store-returns/approve", "error": "Unauthorized access", "status": "failed"}})
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreReturnsService.approve_return(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            approved_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info("Return approved successfully",
                extra={"extra_fields": {"endpoint": "/store-returns/approve", "return_id": data.return_id, "status": "success"}})
        else:
            logger.warning(f"Return approval failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/store-returns/approve", "error": service_result.error, "status": "failed"}})

        return service_result


# 3. Reject Return
@store_returns_router.put("/reject", response_model=Respons[RejectReturnControllerReadDto])
def reject_return(
    data: RejectReturnControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Reject a pending return"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext("store_returns", "reject_return", loc_id=loc_id, return_id=data.return_id):
        logger.info("Processing reject return request",
            extra={"extra_fields": {"endpoint": "/store-returns/reject", "return_id": data.return_id}})

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-returns-approve"]
        )
        if not is_authorized:
            logger.warning("Reject return failed - unauthorized access",
                extra={"extra_fields": {"endpoint": "/store-returns/reject", "error": "Unauthorized access", "status": "failed"}})
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreReturnsService.reject_return(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            rejected_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info("Return rejected",
                extra={"extra_fields": {"endpoint": "/store-returns/reject", "return_id": data.return_id, "status": "success"}})
        else:
            logger.warning(f"Return rejection failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/store-returns/reject", "error": service_result.error, "status": "failed"}})

        return service_result


# 4. Process Return (restock + refund)
@store_returns_router.put("/process", response_model=Respons[ProcessReturnControllerReadDto])
def process_return(
    data: ProcessReturnControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Process an approved return - restock items and issue refund"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext("store_returns", "process_return", loc_id=loc_id, return_id=data.return_id):
        logger.info("Processing return request",
            extra={"extra_fields": {"endpoint": "/store-returns/process", "return_id": data.return_id}})

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-returns-update"]
        )
        if not is_authorized:
            logger.warning("Process return failed - unauthorized access",
                extra={"extra_fields": {"endpoint": "/store-returns/process", "error": "Unauthorized access", "status": "failed"}})
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreReturnsService.process_return(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            processed_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info("Return processed successfully",
                extra={"extra_fields": {"endpoint": "/store-returns/process", "return_id": data.return_id, "status": "success"}})
        else:
            logger.warning(f"Return processing failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/store-returns/process", "error": service_result.error, "status": "failed"}})

        return service_result


# 5. Get Return
@store_returns_router.get("/get", response_model=Respons[GetReturnControllerReadDto])
def get_return(
    return_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single return by ID"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext("store_returns", "get_return", loc_id=loc_id, return_id=return_id):
        logger.info("Processing get return request",
            extra={"extra_fields": {"endpoint": "/store-returns/get", "return_id": return_id}})

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-returns-get"]
        )
        if not is_authorized:
            logger.warning("Get return failed - unauthorized access",
                extra={"extra_fields": {"endpoint": "/store-returns/get", "error": "Unauthorized access", "status": "failed"}})
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreReturnsService.get_return(
            return_id=return_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
        )

        if service_result.success:
            logger.info("Return retrieved successfully",
                extra={"extra_fields": {"endpoint": "/store-returns/get", "return_id": return_id, "status": "success"}})
        else:
            logger.warning(f"Return retrieval failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/store-returns/get", "error": service_result.error, "status": "failed"}})

        return service_result


# 6. Get Returns List
@store_returns_router.get("/list", response_model=Respons[GetReturnsControllerReadDto])
def get_returns(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    status: str = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED, COMPLETED)"),
    sale_id: str = Query(None, description="Filter by sale ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of returns with pagination"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext("store_returns", "get_returns", loc_id=loc_id):
        logger.info("Processing get returns request",
            extra={"extra_fields": {"endpoint": "/store-returns/list", "page": page, "size": size, "status": status}})

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-returns-get"]
        )
        if not is_authorized:
            logger.warning("Get returns failed - unauthorized access",
                extra={"extra_fields": {"endpoint": "/store-returns/list", "error": "Unauthorized access", "status": "failed"}})
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreReturnsService.get_returns(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
            page=page,
            size=size,
            status=status,
            sale_id=sale_id,
        )

        if service_result.success:
            logger.info("Returns retrieved successfully",
                extra={"extra_fields": {"endpoint": "/store-returns/list", "count": len(service_result.data) if service_result.data else 0, "status": "success"}})
        else:
            logger.warning(f"Returns retrieval failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/store-returns/list", "error": service_result.error, "status": "failed"}})

        return service_result


# 7. Get Returns Statistics
@store_returns_router.get("/statistics", response_model=Respons[GetReturnStatisticsControllerReadDto])
def get_returns_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get return statistics"""
    loc_id = org_bus_loc["loc_id"]
    with LogContext("store_returns", "get_returns_statistics", loc_id=loc_id):
        logger.info("Processing get returns statistics request",
            extra={"extra_fields": {"endpoint": "/store-returns/statistics"}})

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-store-returns-get"]
        )
        if not is_authorized:
            logger.warning("Get returns statistics failed - unauthorized access",
                extra={"extra_fields": {"endpoint": "/store-returns/statistics", "error": "Unauthorized access", "status": "failed"}})
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = StoreReturnsService.get_returns_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=loc_id,
        )

        if service_result.success:
            logger.info("Returns statistics retrieved successfully",
                extra={"extra_fields": {"endpoint": "/store-returns/statistics", "status": "success"}})
        else:
            logger.warning(f"Returns statistics retrieval failed: {service_result.detail}",
                extra={"extra_fields": {"endpoint": "/store-returns/statistics", "error": service_result.error, "status": "failed"}})

        return service_result
