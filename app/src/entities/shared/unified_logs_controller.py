from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.shared.sh_activity_dto import (
    ActivityLogReadDto,
    ActivityResourceTypeReadDto,
    DeleteActivityLogsWriteDto,
    DeleteActivityLogsReadDto,
)
from src.entities.shared.sh_response import Respons
from src.entities.shared.sh_service import ActivityLogService
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService


unified_logs_router = APIRouter(prefix="/logs", tags=["Unified Logs"])
logger = get_logger("unified_logs")


@unified_logs_router.get("/unified", response_model=Respons[ActivityLogReadDto])
def get_unified_activity_logs(
    resource_types: Optional[List[str]] = Query(
        None,
        description="Optional list of resource types to filter by (e.g., rt-expenses, rt-warehouse, rt-shop, rt-clients, rt-creditors, rt-depositors, rt-returns, rt-invoice, rt-sales, rt-suppliers). If omitted, all logs will be returned.",
    ),
    actions: Optional[List[str]] = Query(
        None,
        description="Actions to include (create, update, delete). Case-insensitive. If omitted, all actions are returned.",
    ),
    tenant_id: Optional[str] = Query(
        None,
        description="Filter by tenant ID. If omitted, uses the current user's tenant_id.",
    ),
    org_id: Optional[str] = Query(
        None,
        description="Filter by organization ID. If omitted, uses the org_id from request headers.",
    ),
    bus_id: Optional[str] = Query(
        None,
        description="Filter by business ID. If omitted, uses the bus_id from request headers.",
    ),
    loc_id: Optional[str] = Query(
        None,
        description="Filter by location ID. If omitted, uses the loc_id from request headers. Use empty string to filter for logs with empty loc_id.",
    ),
    from_datetime: Optional[str] = Query(
        None,
        description="Filter logs from this date/time (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)",
    ),
    to_datetime: Optional[str] = Query(
        None,
        description="Filter logs to this date/time (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)",
    ),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Unified activity log listing with multi-resource and multi-action filters.
    If resource_types is not provided, all logs will be returned."""
    normalized_resource_types = [
        rt.strip() for rt in (resource_types or []) if rt and rt.strip()
    ] if resource_types else None
    
    # Use provided filter values or fall back to context values
    # Note: Empty string is a valid filter value (to filter for empty/null values)
    filter_tenant_id = tenant_id if tenant_id is not None else current_user.data[0].tenant_id
    filter_org_id = org_id if org_id is not None else org_bus_loc["org_id"]
    filter_bus_id = bus_id if bus_id is not None else org_bus_loc["bus_id"]
    # For loc_id, empty string is a valid filter (means filter for empty loc_id)
    filter_loc_id = loc_id if loc_id is not None else org_bus_loc["loc_id"]
    
    with LogContext(
        "unified_logs",
        "get_unified_activity_logs",
        resource_types=",".join(normalized_resource_types) if normalized_resource_types else "all",
        actions=",".join(actions) if actions else "all",
        tenant_id=filter_tenant_id,
        org_id=filter_org_id,
        bus_id=filter_bus_id,
        loc_id=filter_loc_id,
    ):

        normalized_actions = [
            act.strip().lower()
            for act in actions
            if act and act.strip()
        ] if actions else None

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-logs-get"]
        )

        if not is_authorized:
            logger.warning(
                "Unified activity logs request denied - unauthorized",
                extra={
                    "extra_fields": {
                        "endpoint": "/logs/unified",
                        "error": "Unauthorized access",
                        "resource_types": normalized_resource_types,
                        "actions": normalized_actions or "all",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ActivityLogService.get_activity_logs(
            tenant_id=filter_tenant_id,
            resource_types=normalized_resource_types,
            actions=normalized_actions,
            org_id=filter_org_id,
            bus_id=filter_bus_id,
            loc_id=filter_loc_id,
            app_id=org_bus_loc["app_id"],
            from_date=from_datetime,
            to_date=to_datetime,
            page=page,
            size=size,
        )

        return service_result


@unified_logs_router.get("/resource-types", response_model=Respons[ActivityResourceTypeReadDto])
def get_activity_resource_types(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Return the available resource types present in the activity log table"""
    with LogContext("unified_logs", "get_activity_resource_types"):
        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-logs-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get activity resource types denied - unauthorized",
                extra={
                    "extra_fields": {
                        "endpoint": "/logs/resource-types",
                        "error": "Unauthorized access",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ActivityLogService.get_activity_resource_types(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            app_id=org_bus_loc["app_id"],
        )

        return service_result


@unified_logs_router.delete("/unified", response_model=Respons[DeleteActivityLogsReadDto])
def delete_unified_activity_logs(
    data: DeleteActivityLogsWriteDto = Body(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete activity logs by their IDs"""
    with LogContext(
        "unified_logs",
        "delete_unified_activity_logs",
        log_ids_count=len(data.log_ids),
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        loc_id=org_bus_loc["loc_id"],
    ):
        if not data.log_ids or len(data.log_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one log_id must be provided",
            )

        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-logs-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete unified activity logs denied - unauthorized",
                extra={
                    "extra_fields": {
                        "endpoint": "/logs/unified",
                        "error": "Unauthorized access",
                        "log_ids_count": len(data.log_ids),
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ActivityLogService.delete_activity_logs(
            tenant_id=current_user.data[0].tenant_id,
            log_ids=data.log_ids,
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                f"Successfully deleted {service_result.data[0].get('deleted_count', 0) if service_result.data else 0} activity logs",
                extra={
                    "extra_fields": {
                        "endpoint": "/logs/unified",
                        "deleted_count": service_result.data[0].get("deleted_count", 0) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Delete activity logs failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/logs/unified",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

