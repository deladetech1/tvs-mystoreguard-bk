from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Tuple, List
from datetime import date
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission
from src.entities.dashboard.dashboard_service import DashboardService
from src.entities.dashboard.dashboard_read_dto import (
    GetDashboardDataControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = get_logger("dashboard")


def check_dashboard_permissions(current_user: dict) -> Tuple[bool, List[str]]:
    """Check if user has required permissions for dashboard access
    
    Dashboard displays data from multiple entities, so we check if user has
    'get' permissions for all entities used by the dashboard.
    
    Returns:
        tuple[bool, list[str]]: (is_authorized, missing_permissions)
            - is_authorized: True if user has all required permissions
            - missing_permissions: List of missing permission names
    """
    # All entity permissions required for dashboard access
    required_permissions = [
        "permission-msg-store-sales-get",     # For sales data
        "permission-msg-invoices-get",         # For invoice data
        "permission-expense-get",             # For expense data
        "permission-msg-products-get",        # For products data
        "permission-msg-customers-get",        # For customers data
        "permission-msg-appointments-get",    # For appointments data
    ]
    
    user_id = current_user.data[0].user_id if current_user.data else "unknown"
    tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
    
    missing_permissions = []
    has_all_permissions = True
    
    for permission in required_permissions:
        # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=[permission]
        )
        if not is_authorized:
            has_all_permissions = False
            missing_permissions.append(permission)
    
    if not has_all_permissions:
        logger.warning(
            "Dashboard access denied - missing required entity permissions",
            extra={
                "extra_fields": {
                    "status": "unauthorized",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "required_permissions": required_permissions,
                    "missing_permissions": missing_permissions,
                    "message": f"User is missing required permissions: {', '.join(missing_permissions)}",
                }
            },
        )
    
    return has_all_permissions, missing_permissions


# Get Dashboard Data
@dashboard_router.get("/data", response_model=Respons[GetDashboardDataControllerReadDto])
def get_dashboard_data(
    from_date: Optional[date] = Query(None, description="Filter data from this date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter data to this date (YYYY-MM-DD)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """
    Get complete dashboard data including stats overview, charts, and trends with optional date filtering.
    
    **Authentication Required:**
    - JWT token in Authorization header (tenant_id and user_id extracted from token)
    - Headers required: `org-id`, `bus-id`, `loc-id`, `app-id`
    
    **Permissions Required:**
    - permission-msg-store-sales-get
    - permission-msg-invoices-get
    - permission-expense-get
    - permission-msg-products-get
    - permission-msg-customers-get
    - permission-msg-appointments-get
    """
    with LogContext(
        "dashboard",
        "get_dashboard_data",
        tenant_id=current_user.data[0].tenant_id if current_user.data else "unknown",
    ):
        logger.info(
            "Processing get dashboard data request",
            extra={
                "extra_fields": {
                    "endpoint": "/dashboard/data",
                    "from_date": str(from_date) if from_date else None,
                    "to_date": str(to_date) if to_date else None,
                }
            },
        )

        is_authorized, missing_permissions = check_dashboard_permissions(current_user)
        if not is_authorized:
            missing_perms_str = ", ".join(missing_permissions)
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized access: Missing required entity permissions: {missing_perms_str}"
            )

        service_result = DashboardService.get_dashboard_data(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            from_date=from_date,
            to_date=to_date,
        )

        if service_result.success:
            logger.info(
                "Dashboard data retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/dashboard/data",
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Dashboard data retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/dashboard/data",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result

