from fastapi.params import Depends
from fastapi.security import HTTPBearer
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException, Header
from typing import Optional, List, Set, Tuple
from datetime import datetime
from trovesuite import AuthService
from trovesuite.auth.auth_read_dto import AuthServiceReadDto
from src.entities.shared.sh_base import AuthBaseWriteDto
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.configs.database import DatabaseManager
from src.configs.settings import db_settings

security = HTTPBearer()
logger = get_logger("auth")

# This service's own app_id in the core-platform cp_apps catalog.
# Used by check_subscription_active / verify_subscription_active to look up
# the per-app subscription for the calling tenant.
APP_ID = "app-mystoreguard"

class CustomAuthService:

    # Trovesuite errors that should block service execution
    BLOCKING_ERRORS = {
        "TENANT_NOT_VERIFIED",
        "TENANT_NOT_FOUND",
        "INVALID_TENANT_ID",
        "USER_SUSPENDED",
        "LOGIN_TIME_RESTRICTED",
        "LOGIN_DAY_RESTRICTED"
    }

    @staticmethod
    def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):

        token = credentials.credentials
        user = AuthService.decode_token(token=token)
        
        user_id = user.get("user_id")
        tenant_id = user.get("tenant_id")
        
        # Validate that user_id and tenant_id are present
        if not user_id or not tenant_id:
            logger.error(
                "Missing user_id or tenant_id in token",
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                    }
                },
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user_id or tenant_id"
            )
        
        # Always call AuthService.authorize to get user roles and permissions
        # Permissions are returned in the login response (permission_details), not in JWT token
        data = AuthBaseWriteDto(user_id=user_id, tenant_id=tenant_id)
        auth_result = AuthService.authorize(data=data)

        # Debug: Log what AuthService.authorize returned to understand permission issues
        try:
            data_count = len(auth_result.data) if hasattr(auth_result, 'data') and auth_result.data else 0
            data_sample = []
            all_permissions = []
            
            if hasattr(auth_result, 'data') and auth_result.data:
                for dto in auth_result.data[:3]:
                    try:
                        dto_dict = {
                            "user_id": getattr(dto, "user_id", None),
                            "role_id": getattr(dto, "role_id", None),
                            "permissions_count": len(getattr(dto, "permissions", [])) if getattr(dto, "permissions", None) else 0,
                            "permissions_sample": list(getattr(dto, "permissions", []))[:5] if getattr(dto, "permissions", None) else [],
                            "resource_type": getattr(dto, "resource_type", None),
                        }
                        data_sample.append(dto_dict)
                        
                        # Collect all permissions
                        perms = getattr(dto, "permissions", [])
                        if perms:
                            all_permissions.extend(perms)
                    except Exception as e:
                        logger.debug(f"Error extracting dto data: {str(e)}")
            
            logger.info(
                "AuthService.authorize result",
                extra={
                    "extra_fields": {
                        "user_id": user.get("user_id"),
                        "tenant_id": user.get("tenant_id"),
                        "auth_success": getattr(auth_result, 'success', None),
                        "auth_error": getattr(auth_result, 'error', None),
                        "data_count": data_count,
                        "data_sample": data_sample,
                        "all_permissions": list(set(all_permissions)),  # Unique permissions
                        "total_unique_permissions": len(set(all_permissions)),
                    }
                },
            )
        except Exception as e:
            logger.warning(f"Error logging auth result: {str(e)}")

        # Check if authorization returned a blocking error with empty data
        if (hasattr(auth_result, 'error') and
            auth_result.error in CustomAuthService.BLOCKING_ERRORS and
            (not hasattr(auth_result, 'data') or not auth_result.data or auth_result.data == [])):

            # Map errors to appropriate HTTP status codes
            status_code_map = {
                "TENANT_NOT_VERIFIED": 403,  # Forbidden
                "TENANT_NOT_FOUND": 404,     # Not Found
                "INVALID_TENANT_ID": 400,    # Bad Request
                "USER_SUSPENDED": 403,       # Forbidden
                "LOGIN_TIME_RESTRICTED": 403, # Forbidden
                "LOGIN_DAY_RESTRICTED": 403   # Forbidden
            }

            status_code = status_code_map.get(auth_result.error, 403)

            raise HTTPException(
                status_code=status_code,
                detail=auth_result.error
            )

        # Core-platform membership gate. Mystoreguard authenticates via core platform,
        # so only users with an active cp_members row can access this app. HR-only
        # employees (cp_users + hr_employees, no cp_members) must not be allowed in.
        is_core_platform_member = DatabaseManager.execute_scalar(
            f"""SELECT COUNT(1) FROM {db_settings.CORE_PLATFORM_MEMBERS_TABLE}
                WHERE tenant_id = %s AND user_id = %s
                AND is_active = true AND delete_status = 'NOT_DELETED'""",
            (tenant_id, user_id),
        )
        if not is_core_platform_member:
            logger.warning(
                "Authorization failed - user is not a core-platform member",
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                    }
                },
            )
            raise HTTPException(
                status_code=403,
                detail="Not a core-platform member",
            )

        return auth_result


# Header dependencies for org_id, bus_id, loc_id
def get_org_id(org_id: str = Header(..., description="Organization ID")):
    """Extract org_id from request headers"""
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id header is required")
    return org_id


def get_bus_id(bus_id: str = Header(..., description="Business ID")):
    """Extract bus_id from request headers"""
    if not bus_id:
        raise HTTPException(status_code=400, detail="bus_id header is required")
    return bus_id


def get_loc_id(loc_id: str = Header(..., description="Location ID")):
    """Extract loc_id from request headers"""
    if not loc_id:
        raise HTTPException(status_code=400, detail="loc_id header is required")
    return loc_id


def get_org_bus_loc(
    org_id: str = Header(..., alias="org-id", description="Organization ID"),
    bus_id: str = Header(..., alias="bus-id", description="Business ID"),
    loc_id: str = Header(..., alias="loc-id", description="Location ID"),
):
    """Extract org_id, bus_id, and loc_id from request headers"""
    return {
        "org_id": org_id,
        "bus_id": bus_id,
        "loc_id": loc_id,
    }


def get_app_id(app_id: str = Header(..., alias="app-id", description="Application ID")):
    """Extract app_id from request headers"""
    if not app_id:
        raise HTTPException(status_code=400, detail="app_id header is required")
    return app_id


def get_location_name(tenant_id: str, loc_id: str) -> Optional[str]:
    """
    Get the location name from cp_locations table by location ID.
    
    Args:
        tenant_id: Tenant ID
        loc_id: Location ID
    
    Returns:
        Location name if found, None otherwise
    """
    try:
        query = f'''
            SELECT loc_name 
            FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
            WHERE tenant_id = %s
            AND id = %s
            AND is_active = true
            AND delete_status = 'NOT_DELETED'
            LIMIT 1
        '''
        
        result = DatabaseManager.execute_scalar(query, (tenant_id, loc_id))
        return result if result else None
            
    except Exception as e:
        logger.error(
            f"Error fetching location name: {str(e)}",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "loc_id": loc_id,
                    "error": str(e),
                }
            },
        )
        return None


def get_user_group_ids(tenant_id: str, user_id: str) -> List[str]:
    """
    Get all group IDs that the user belongs to.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        List of group IDs
    """
    try:
        query = f'''
            SELECT group_id 
            FROM {db_settings.CORE_PLATFORM_USER_GROUPS_TABLE}
            WHERE tenant_id = %s 
            AND user_id = %s
            AND is_active = true
            AND delete_status = 'NOT_DELETED'
        '''
        
        results = DatabaseManager.execute_query(query, (tenant_id, user_id))
        if not results:
            return []
        # Support dict-like and attribute access; normalize key case
        ids = []
        for row in results:
            gid = row.get("group_id") if hasattr(row, "get") else getattr(row, "group_id", None)
            if gid is None and hasattr(row, "get"):
                gid = row.get("GROUP_ID")  # some drivers return uppercase
            if gid is not None:
                ids.append(str(gid))
        return ids
    except Exception as e:
        logger.error(
            f"Error fetching user groups: {str(e)}",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "error": str(e),
                }
            },
        )
        return []


def verify_app_deployment_to_location(
    tenant_id: str,
    loc_id: str,
    app_id: Optional[str],
    org_id: Optional[str] = None,
    bus_id: Optional[str] = None
) -> bool:
    """
    Verify if the application is deployed to the specified location for the given business context.
    
    Checks if the app is assigned to the location in cp_business_app_locations table.
    IMPORTANT: We check tenant_id, org_id, bus_id, and loc_id to prevent cross-business access.
    If org_id/bus_id in the table is NULL, it applies to all orgs/businesses.
    If org_id/bus_id has a value, it must match the request's org_id/bus_id.
    
    Args:
        tenant_id: Tenant ID
        loc_id: Location ID to check
        app_id: Application ID (can be None if not found in database)
        org_id: Optional organization ID (required for proper access control)
        bus_id: Optional business ID (required for proper access control)
    
    Returns:
        bool: True if app is deployed to location for the given context, False otherwise
    """
    try:
        if not app_id:
            logger.warning(
                "App ID not found - cannot verify app deployment",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "loc_id": loc_id,
                        "message": "App ID not found in cp_apps table. App deployment verification will fail."
                    }
                }
            )
            # If app_id is not found, we cannot verify app deployment
            # Fail securely - deny access when we can't verify
            return False
        
        # Do not filter by org_id/bus_id: if the app is deployed to this (tenant, loc_id, app_id),
        # allow access regardless of request headers. This avoids denial when frontend sends
        # different org-id/bus-id and matches location access behavior.
        query = f'''
            SELECT COUNT(*) as deployment_count
            FROM {db_settings.CORE_PLATFORM_BUSINESS_APP_LOCATIONS_TABLE}
            WHERE tenant_id = %s
            AND loc_id = %s
            AND app_id = %s
            AND is_active = true
            AND delete_status = 'NOT_DELETED'
        '''
        params = [tenant_id, loc_id, app_id]
        count = DatabaseManager.execute_scalar(query, tuple(params))
        is_deployed = count > 0 if count is not None else False
        
        if not is_deployed:
            logger.warning(
                "App not deployed to location",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "loc_id": loc_id,
                        "app_id": app_id,
                        "org_id": org_id,
                        "bus_id": bus_id,
                    }
                },
            )
        
        return is_deployed
        
    except Exception as e:
        logger.error(
            f"Error verifying app deployment to location: {str(e)}",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "loc_id": loc_id,
                    "app_id": app_id,
                    "error": str(e),
                }
            },
        )
        # Fail securely - deny access on error
        return False


def verify_location_access(
    current_user: dict,
    loc_id: str,
    app_id: str,
    org_id: Optional[str] = None,
    bus_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Verify if the user has access to the specified location AND if the app is deployed to that location.
    
    Checks both:
    1. User location access: direct user assignments (cp_user_locations) and group assignments (cp_group_locations)
    2. App deployment: verifies app is assigned to the location in cp_business_app_locations
    
    IMPORTANT: We MUST check tenant_id, org_id, bus_id, and loc_id to prevent users from accessing
    other businesses in the same location. This ensures proper business isolation.
    
    Logic for org_id/bus_id matching:
    - If the assignment/deployment has NULL org_id/bus_id, it applies to all orgs/businesses
    - If the assignment/deployment has a specific org_id/bus_id, it must match the request's org_id/bus_id
    
    Args:
        current_user: User data from CustomAuthService.get_current_user
        loc_id: Location ID to check
        app_id: Application ID
        org_id: Optional organization ID (required for proper access control)
        bus_id: Optional business ID (required for proper access control)
    
    Returns:
        tuple[bool, Optional[str]]: (has_access, error_message)
            - If True: (True, None)
            - If False: (False, error_message describing why access was denied)
    """
    try:
        if not current_user.data or len(current_user.data) == 0:
            logger.warning(
                "verify_location_access: Empty user data",
                extra={"extra_fields": {"loc_id": loc_id}}
            )
            return False, "Invalid user data"
        
        # Prefer JWT-derived values (set by get_current_user); role DTOs can have user_id=None for group roles
        tenant_id = getattr(current_user, "tenant_id", None) or (current_user.data[0].tenant_id if current_user.data else None)
        user_id = getattr(current_user, "user_id", None) or (current_user.data[0].user_id if current_user.data else None)
        if not user_id or not tenant_id:
            logger.warning(
                "verify_location_access: Missing user_id or tenant_id",
                extra={"extra_fields": {"loc_id": loc_id, "user_id": user_id, "tenant_id": tenant_id}}
            )
            return False, "Invalid user data"
        
        # Get user's group IDs
        group_ids = get_user_group_ids(tenant_id, user_id)
        
        # Build query to check location access
        # Check for direct user assignment OR group assignment
        # Join with cp_business_app_locations to match loc_id
        query_parts = []
        params = []
        
        # Build user assignment query part
        # IMPORTANT: We MUST check tenant_id, org_id, bus_id, and loc_id to prevent
        # users from accessing other businesses in the same location.
        # Logic: If bal.org_id/bus_id is NULL, it applies to all orgs/businesses.
        #        If bal.org_id/bus_id has a value, it must match the request's org_id/bus_id.
        user_query = f'''
            SELECT ul.id
            FROM {db_settings.CORE_PLATFORM_USER_LOCATIONS_TABLE} ul
            INNER JOIN {db_settings.CORE_PLATFORM_BUSINESS_APP_LOCATIONS_TABLE} bal
                ON ul.bus_app_loc_id = bal.id
                AND ul.tenant_id = bal.tenant_id
            WHERE ul.tenant_id = %s
            AND bal.loc_id = %s
            AND ul.user_id = %s
            AND ul.is_active = true
            AND ul.delete_status = 'NOT_DELETED'
            AND bal.is_active = true
            AND bal.delete_status = 'NOT_DELETED'
        '''
        query_parts.append(user_query)
        params.extend([tenant_id, loc_id, user_id])
        
        # Do not filter by org_id/bus_id for direct user assignment: if the user has
        # any assignment to this (tenant, loc_id), they have access. This avoids
        # "location unauthorized" when the frontend sends a different org-id/bus-id.
        
        # Build group assignment query part if user has groups
        if group_ids:
            placeholders = ','.join(['%s'] * len(group_ids))
            group_query = f'''
                SELECT gl.id
                FROM {db_settings.CORE_PLATFORM_GROUP_LOCATIONS_TABLE} gl
                INNER JOIN {db_settings.CORE_PLATFORM_BUSINESS_APP_LOCATIONS_TABLE} bal
                    ON gl.bus_app_loc_id = bal.id
                    AND gl.tenant_id = bal.tenant_id
                WHERE gl.tenant_id = %s
                AND bal.loc_id = %s
                AND gl.group_id IN ({placeholders})
                AND gl.is_active = true
                AND gl.delete_status = 'NOT_DELETED'
                AND bal.is_active = true
                AND bal.delete_status = 'NOT_DELETED'
            '''
            query_parts.append(group_query)
            params.extend([tenant_id, loc_id] + group_ids)
            
            # Do not filter by org_id/bus_id for group assignment (same as direct assignment).
        
        # Combine query parts with UNION and wrap in COUNT
        query = f'''
            SELECT COUNT(*) as access_count
            FROM (
                {' UNION '.join(query_parts)}
            ) AS location_access
        '''
        
        raw_count = DatabaseManager.execute_scalar(query, tuple(params))
        # Coerce to int (DB may return Decimal or str)
        try:
            access_count = int(raw_count) if raw_count is not None else 0
        except (TypeError, ValueError):
            access_count = 0
        has_user_access = access_count > 0
        
        if not has_user_access:
            # Log key values in message so they appear in stdout (e.g. Azure logs)
            logger.info(
                "User location access denied | user_id=%s tenant_id=%s loc_id=%s app_id=%s access_count=%s group_count=%s group_ids=%s",
                user_id,
                tenant_id,
                loc_id,
                app_id,
                access_count,
                len(group_ids),
                group_ids,
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "loc_id": loc_id,
                        "org_id": org_id,
                        "bus_id": bus_id,
                        "user_group_count": len(group_ids),
                        "group_ids": group_ids,
                        "access_count": access_count,
                    }
                },
            )
            return False, "You do not have permission to access this location"
        
        # Now verify app is deployed to this location
        is_app_deployed = verify_app_deployment_to_location(
            tenant_id=tenant_id,
            loc_id=loc_id,
            app_id=app_id,
            org_id=org_id,
            bus_id=bus_id
        )
        
        if not is_app_deployed:
            logger.warning(
                "App not deployed to location - access denied",
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "loc_id": loc_id,
                        "app_id": app_id,
                        "org_id": org_id,
                        "bus_id": bus_id,
                    }
                },
            )
            return False, "Application is not deployed to this location"
        
        return True, None
        
    except Exception as e:
        logger.error(
            f"Error verifying location access: {str(e)}",
            extra={
                "extra_fields": {
                    "user_id": getattr(current_user.data[0], 'user_id', None) if current_user.data else None,
                    "loc_id": loc_id,
                    "error": str(e),
                }
            },
        )
        # Fail securely - deny access on error
        return False, "Error verifying location access"


def get_org_bus_loc_with_permission(
    org_id: str = Header(..., alias="org-id", description="Organization ID"),
    bus_id: str = Header(..., alias="bus-id", description="Business ID"),
    loc_id: str = Header(..., alias="loc-id", description="Location ID"),
    app_id: str = Header(..., alias="app-id", description="Application ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
):
    """
    Extract org_id, bus_id, loc_id, and app_id from request headers AND verify location permissions.
    
    This enhanced dependency automatically verifies:
    1. User has access to the location (via direct user assignments or group assignments)
    2. Application is deployed to the location
    
    It checks:
    - Direct user location assignments (cp_user_locations)
    - Group-based location assignments (cp_group_locations)
    - App deployment to location (cp_business_app_locations)
    
    Raises:
        HTTPException: 400 if headers are invalid (e.g., "undefined" values)
        HTTPException: 403 if user doesn't have access to the location OR app is not deployed
    
    Returns:
        dict: Contains org_id, bus_id, loc_id, and app_id
    """
    # Validate that headers are not "undefined" (common frontend issue)
    invalid_values = ["undefined", "null", "None", ""]
    
    if org_id in invalid_values or not org_id or org_id.strip() in invalid_values:
        logger.error(
            "Invalid org_id header value",
            extra={
                "extra_fields": {
                    "org_id": org_id,
                    "org_id_type": type(org_id).__name__,
                }
            },
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid org_id header: '{org_id}'. Please provide a valid organization ID."
        )
    
    if bus_id in invalid_values or not bus_id or bus_id.strip() in invalid_values:
        logger.error(
            "Invalid bus_id header value",
            extra={
                "extra_fields": {
                    "bus_id": bus_id,
                    "bus_id_type": type(bus_id).__name__,
                }
            },
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bus_id header: '{bus_id}'. Please provide a valid business ID."
        )
    
    if loc_id in invalid_values or not loc_id or loc_id.strip() in invalid_values:
        logger.error(
            "Invalid loc_id header value",
            extra={
                "extra_fields": {
                    "loc_id": loc_id,
                    "loc_id_type": type(loc_id).__name__,
                }
            },
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid loc_id header: '{loc_id}'. Please provide a valid location ID."
        )
    
    if app_id in invalid_values or not app_id or app_id.strip() in invalid_values:
        logger.error(
            "Invalid app_id header value",
            extra={
                "extra_fields": {
                    "app_id": app_id,
                    "app_id_type": type(app_id).__name__,
                }
            },
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid app_id header: '{app_id}'. Please provide a valid application ID."
        )
    
    # Normalize values (strip whitespace)
    org_id = org_id.strip()
    bus_id = bus_id.strip()
    loc_id = loc_id.strip()
    app_id = app_id.strip()
    
    # Verify location access
    has_access, error_message = verify_location_access(
        current_user=current_user,
        loc_id=loc_id,
        app_id=app_id,
        org_id=org_id,
        bus_id=bus_id
    )
    
    if not has_access:
        user_id = getattr(current_user, "user_id", None) or (current_user.data[0].user_id if current_user.data else None) or "unknown"
        tenant_id = getattr(current_user, "tenant_id", None) or (current_user.data[0].tenant_id if current_user.data else None) or "unknown"
        
        # Get location name for logging purposes
        location_name = get_location_name(tenant_id=tenant_id, loc_id=loc_id)
        
        logger.warning(
            "Location access denied - request blocked",
            extra={
                "extra_fields": {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "loc_id": loc_id,
                    "location_name": location_name,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "app_id": app_id,
                    "error_reason": error_message,
                    "endpoint": "get_org_bus_loc_with_permission",
                    "headers_provided": {
                        "org_id": bool(org_id),
                        "bus_id": bool(bus_id),
                        "loc_id": bool(loc_id),
                        "app_id": bool(app_id),
                    },
                }
            },
        )
        
        # Return distinct message so client/logs can tell location denial from permission denial
        raise HTTPException(
            status_code=403,
            detail="Location access denied. You do not have access to this location, or the app is not deployed here."
        )
    
    return {
        "org_id": org_id,
        "bus_id": bus_id,
        "loc_id": loc_id,
        "app_id": app_id,
    }


def check_subscription_active(
    tenant_id: str, business_id: str, user_id: str
) -> Tuple[bool, Optional[str]]:
    """
    Check whether the (tenant, business, app=mystoreguard) subscription is
    active and not expired. Queries cp_app_subscription_histories filtered by
    app_id = APP_ID and business_id.

    Returns:
        tuple[bool, Optional[str]]: (is_active, error_message)
            - If active: (True, None)
            - If expired/not found: (False, error_message describing why subscription is inactive)
    """
    try:
        # 1) Tenant-wide free trial window. The first subscription opens one
        #    lifetime window on cp_tenants; while it is open EVERY app is usable
        #    for free, no card required.
        trial_rows = DatabaseManager.execute_query(
            f'''SELECT (free_trial_ends_at IS NOT NULL AND free_trial_ends_at > now()) AS in_window
                FROM {db_settings.CORE_PLATFORM_TENANTS_TABLE}
                WHERE id = %s''',
            (tenant_id,),
        )
        if trial_rows and trial_rows[0].get("in_window"):
            logger.debug(
                "Access allowed via active tenant free-trial window",
                extra={"extra_fields": {"tenant_id": tenant_id, "user_id": user_id}},
            )
            return True, None

        # 2) Otherwise require a paid (ACTIVE) subscription for this
        #    (tenant, business, app). status lives on the live cp_app_subscriptions
        #    row and is the source of truth: ACTIVE allows; anything else blocks.
        result = DatabaseManager.execute_query(
            f'''SELECT id, status
                FROM {db_settings.CORE_PLATFORM_APP_SUBSCRIPTIONS_TABLE}
                WHERE tenant_id = %s AND business_id = %s AND app_id = %s
                  AND delete_status = 'NOT_DELETED'
                ORDER BY cdatetime DESC NULLS LAST
                LIMIT 1''',
            (tenant_id, business_id, APP_ID),
        )

        if not result or len(result) == 0:
            logger.warning(
                "No subscription found for (tenant, business, app)",
                extra={"extra_fields": {
                    "tenant_id": tenant_id, "business_id": business_id,
                    "user_id": user_id, "app_id": APP_ID,
                }},
            )
            return False, (
                "This business has not subscribed to this app. "
                "Visit the App Store to get started."
            )

        status = (result[0].get("status") or "").upper()
        logger.debug(
            "Subscription status resolved",
            extra={"extra_fields": {
                "tenant_id": tenant_id, "user_id": user_id,
                "subscription_id": result[0].get("id"), "status": status,
            }},
        )

        if status == "ACTIVE":
            return True, None
        if status == "TRIALING":
            # Trial window has closed (step 1 already returned for open windows)
            # and no payment has been made yet.
            return False, "Your free trial has ended. Add a payment card to continue."
        if status == "PENDING_PAYMENT":
            return False, "Payment is required before you can use this app. Please add a card to activate."
        if status == "PAST_DUE":
            return False, "Your last payment failed. Please update your card to continue."
        if status == "SUSPENDED":
            return False, "Your subscription is suspended. Please contact support."
        if status == "CANCELLED":
            return False, "Your subscription was cancelled. Resubscribe to continue."
        return False, "Your subscription is not active. Please renew to continue."

    except Exception as e:
        logger.error(
            f"Error checking subscription status: {str(e)}",
            extra={"extra_fields": {"tenant_id": tenant_id, "user_id": user_id, "error": str(e)}},
        )
        # Fail securely - deny access on error to prevent unauthorized operations
        return False, "Error verifying subscription status. Please contact support."


def verify_subscription_active(
    bus_id: str = Header(..., alias="bus-id", description="Business ID"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
) -> dict:
    """
    FastAPI dependency to verify that the active business's subscription for
    this app is active before allowing data modifications.

    Subscription is per (tenant, business, app). The bus-id header tells us
    which business the request is acting on. If that (tenant, business, app)
    has no subscription (or it expired), we 403.

    GET and LIST operations should NOT use this dependency.
    """
    if not current_user or not hasattr(current_user, 'data') or not current_user.data or len(current_user.data) == 0:
        logger.warning(
            "verify_subscription_active: Empty or invalid user data",
            extra={"extra_fields": {"current_user_type": type(current_user).__name__}}
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid user data"
        )

    tenant_id = getattr(current_user, "tenant_id", None) or (current_user.data[0].tenant_id if current_user.data else None)
    user_id = getattr(current_user, "user_id", None) or (current_user.data[0].user_id if current_user.data else None)

    logger.debug(
        "Checking subscription status",
        extra={
            "extra_fields": {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "business_id": bus_id,
            }
        },
    )

    is_active, error_message = check_subscription_active(tenant_id, bus_id, user_id)
    
    if not is_active:
        logger.warning(
            "Subscription check failed - request blocked",
            extra={
                "extra_fields": {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "error_reason": error_message,
                    "endpoint": "verify_subscription_active",
                }
            },
        )
        
        raise HTTPException(
            status_code=403,
            detail=error_message or "Your subscription has ended. Please renew to continue."
        )
    
    logger.debug(
        "Subscription check passed",
        extra={
            "extra_fields": {
                "user_id": user_id,
                "tenant_id": tenant_id,
            }
        },
    )
    
    return {"status": "active"}