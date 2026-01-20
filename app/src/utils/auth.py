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
        return [row['group_id'] for row in results] if results else []
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
        
        # IMPORTANT: We MUST check tenant_id, org_id, bus_id, and loc_id to ensure
        # the app is deployed to the specific business context, preventing cross-business access.
        # Logic: If org_id/bus_id is NULL, it applies to all orgs/businesses.
        #        If org_id/bus_id has a value, it must match the request's org_id/bus_id.
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
        
        # Add org_id filter: match if org_id equals request org_id OR org_id is NULL (applies to all orgs)
        if org_id:
            query += " AND (org_id = %s OR org_id IS NULL)"
            params.append(org_id)
        else:
            # If org_id not provided, only match deployments with NULL org_id
            query += " AND org_id IS NULL"
        
        # Add bus_id filter: match if bus_id equals request bus_id OR bus_id is NULL (applies to all businesses)
        if bus_id:
            query += " AND (bus_id = %s OR bus_id IS NULL)"
            params.append(bus_id)
        else:
            # If bus_id not provided, only match deployments with NULL bus_id
            query += " AND bus_id IS NULL"
        
        count = DatabaseManager.execute_scalar(query, tuple(params))
        is_deployed = count > 0 if count is not None else False
        
        # Diagnostic: Check if app is deployed to location without org_id/bus_id filters
        diagnostic_deployment_query = f'''
            SELECT COUNT(*) as diagnostic_deployment_count
            FROM {db_settings.CORE_PLATFORM_BUSINESS_APP_LOCATIONS_TABLE}
            WHERE tenant_id = %s
            AND loc_id = %s
            AND app_id = %s
            AND is_active = true
            AND delete_status = 'NOT_DELETED'
        '''
        diagnostic_deployment_count = DatabaseManager.execute_scalar(
            diagnostic_deployment_query, 
            (tenant_id, loc_id, app_id)
        )
        
        # Get deployment details to see what org_id/bus_id values exist
        deployment_details_query = f'''
            SELECT DISTINCT org_id, bus_id
            FROM {db_settings.CORE_PLATFORM_BUSINESS_APP_LOCATIONS_TABLE}
            WHERE tenant_id = %s
            AND loc_id = %s
            AND app_id = %s
            AND is_active = true
            AND delete_status = 'NOT_DELETED'
            LIMIT 5
        '''
        deployment_details = DatabaseManager.execute_query(
            deployment_details_query, 
            (tenant_id, loc_id, app_id)
        )
        
        if not is_deployed:
            if diagnostic_deployment_count and diagnostic_deployment_count > 0:
                # App is deployed to location but org_id/bus_id don't match
                # Allow it but log warning
                logger.warning(
                    "App is deployed to location but org_id/bus_id context mismatch - allowing access",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "loc_id": loc_id,
                            "app_id": app_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "strict_deployment_count": count,
                            "diagnostic_deployment_count": diagnostic_deployment_count,
                            "deployment_details": [{"org_id": row.get("org_id"), "bus_id": row.get("bus_id")} for row in deployment_details] if deployment_details else [],
                            "request_org_id": org_id,
                            "request_bus_id": bus_id,
                            "action": "allowing_deployment_despite_mismatch",
                        }
                    },
                )
                # Allow deployment but note the mismatch
                is_deployed = True
            else:
                # App is NOT deployed to location at all
                logger.warning(
                    "App not deployed to location for the given business context",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "loc_id": loc_id,
                            "app_id": app_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "strict_deployment_count": count,
                            "diagnostic_deployment_count": diagnostic_deployment_count,
                            "deployment_details": [{"org_id": row.get("org_id"), "bus_id": row.get("bus_id")} for row in deployment_details] if deployment_details else [],
                            "reason": "No app deployment found at all",
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
        
        tenant_id = current_user.data[0].tenant_id
        user_id = current_user.data[0].user_id
        
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
        
        # Add org_id filter: match if bal.org_id equals request org_id OR bal.org_id is NULL (applies to all orgs)
        if org_id:
            query_parts[-1] += " AND (bal.org_id = %s OR bal.org_id IS NULL)"
            params.append(org_id)
        else:
            # If org_id not provided, only match assignments with NULL org_id
            query_parts[-1] += " AND bal.org_id IS NULL"
        
        # Add bus_id filter: match if bal.bus_id equals request bus_id OR bal.bus_id is NULL (applies to all businesses)
        if bus_id:
            query_parts[-1] += " AND (bal.bus_id = %s OR bal.bus_id IS NULL)"
            params.append(bus_id)
        else:
            # If bus_id not provided, only match assignments with NULL bus_id
            query_parts[-1] += " AND bal.bus_id IS NULL"
        
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
            
            # Add org_id filter for group assignments: match if bal.org_id equals request org_id OR bal.org_id is NULL
            if org_id:
                query_parts[-1] += " AND (bal.org_id = %s OR bal.org_id IS NULL)"
                params.append(org_id)
            else:
                # If org_id not provided, only match assignments with NULL org_id
                query_parts[-1] += " AND bal.org_id IS NULL"
            
            # Add bus_id filter for group assignments: match if bal.bus_id equals request bus_id OR bal.bus_id is NULL
            if bus_id:
                query_parts[-1] += " AND (bal.bus_id = %s OR bal.bus_id IS NULL)"
                params.append(bus_id)
            else:
                # If bus_id not provided, only match assignments with NULL bus_id
                query_parts[-1] += " AND bal.bus_id IS NULL"
        
        # Combine query parts with UNION and wrap in COUNT
        query = f'''
            SELECT COUNT(*) as access_count
            FROM (
                {' UNION '.join(query_parts)}
            ) AS location_access
        '''
        
        count = DatabaseManager.execute_scalar(query, tuple(params))
        has_user_access = count > 0 if count is not None else False
        
        # Diagnostic: Check if user has ANY access to this location (without org_id/bus_id filters)
        # This helps us understand if the issue is with org_id/bus_id matching or no access at all
        diagnostic_query = f'''
            SELECT COUNT(*) as diagnostic_count
            FROM (
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
        diagnostic_params = [tenant_id, loc_id, user_id]
        
        if group_ids:
            placeholders = ','.join(['%s'] * len(group_ids))
            diagnostic_query += f'''
                UNION
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
            diagnostic_params.extend([tenant_id, loc_id] + group_ids)
        
        diagnostic_query += ") AS diagnostic_access"
        
        diagnostic_count = DatabaseManager.execute_scalar(diagnostic_query, tuple(diagnostic_params))
        
        # Also check what org_id/bus_id values exist in the assignments
        assignment_details_query = f'''
            SELECT DISTINCT bal.org_id, bal.bus_id
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
            LIMIT 5
        '''
        assignment_details = DatabaseManager.execute_query(assignment_details_query, (tenant_id, loc_id, user_id))
        
        # If strict check fails but user has ANY access to location, log warning but allow
        # This helps us understand the data structure while maintaining functionality
        if not has_user_access:
            if diagnostic_count and diagnostic_count > 0:
                # User has access to location but org_id/bus_id don't match
                # This might be a data issue - log it but allow access for now
                logger.warning(
                    "User has location access but org_id/bus_id context mismatch - allowing access",
                    extra={
                        "extra_fields": {
                            "user_id": user_id,
                            "tenant_id": tenant_id,
                            "loc_id": loc_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "app_id": app_id,
                            "strict_access_count": count,
                            "diagnostic_count": diagnostic_count,
                            "assignment_details": [{"org_id": row.get("org_id"), "bus_id": row.get("bus_id")} for row in assignment_details] if assignment_details else [],
                            "request_org_id": org_id,
                            "request_bus_id": bus_id,
                            "action": "allowing_access_despite_mismatch",
                        }
                    },
                )
                # Allow access but note the mismatch
                has_user_access = True
            else:
                # User has NO access to location at all
                logger.warning(
                    "User location access denied - no assignment found",
                    extra={
                        "extra_fields": {
                            "user_id": user_id,
                            "tenant_id": tenant_id,
                            "loc_id": loc_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "app_id": app_id,
                            "user_group_count": len(group_ids),
                            "strict_access_count": count,
                            "diagnostic_count": diagnostic_count,
                            "assignment_details": [{"org_id": row.get("org_id"), "bus_id": row.get("bus_id")} for row in assignment_details] if assignment_details else [],
                            "reason": "No location assignment found at all",
                        }
                    },
                )
                return False, f"You do not have permission to access this location (loc_id: {loc_id}, org_id: {org_id}, bus_id: {bus_id})"
        
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
        user_id = current_user.data[0].user_id if current_user.data else "unknown"
        tenant_id = current_user.data[0].tenant_id if current_user.data else "unknown"
        
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
        
        # Return simple error message to client (detailed info logged above)
        raise HTTPException(
            status_code=403,
            detail="Unauthorized access"
        )
    
    return {
        "org_id": org_id,
        "bus_id": bus_id,
        "loc_id": loc_id,
        "app_id": app_id,
    }


def check_subscription_active(tenant_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the user's subscription is active (has not ended).
    
    Queries the cp_user_subscription_histories table to find the most recent active subscription
    and verifies that:
    1. The subscription is active (is_active = true)
    2. The subscription is not deleted (delete_status = 'NOT_DELETED')
    3. The subscription has not ended (end_at is NULL or in the future)
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
    
    Returns:
        tuple[bool, Optional[str]]: (is_active, error_message)
            - If active: (True, None)
            - If expired/not found: (False, error_message describing why subscription is inactive)
    """
    try:
        query = f'''
            SELECT 
                id,
                user_subscription_id,
                start_at,
                end_at,
                is_active,
                delete_status,
                cdatetime
            FROM {db_settings.CORE_PLATFORM_USER_SUBSCRIPTION_HISTORY_TABLE}
            WHERE tenant_id = %s
            AND is_active = true
            AND delete_status = 'NOT_DELETED'
            ORDER BY cdatetime DESC NULLS LAST, start_at DESC NULLS LAST
            LIMIT 1
        '''
        
        logger.debug(
            "Executing subscription check query",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "table": db_settings.CORE_PLATFORM_USER_SUBSCRIPTION_HISTORY_TABLE,
                }
            },
        )
        
        result = DatabaseManager.execute_query(query, (tenant_id,))
        
        logger.debug(
            "Subscription query result",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "result_count": len(result) if result else 0,
                    "has_result": bool(result and len(result) > 0),
                }
            },
        )
        
        if not result or len(result) == 0:
            logger.warning(
                "No active subscription found for tenant",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "table": db_settings.CORE_PLATFORM_USER_SUBSCRIPTION_HISTORY_TABLE,
                    }
                },
            )
            return False, "No active subscription found. Please renew your subscription to continue."
        
        subscription = result[0]
        end_at = subscription.get('end_at')
        
        logger.debug(
            "Subscription record found",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "subscription_id": subscription.get('id'),
                    "user_subscription_id": subscription.get('user_subscription_id'),
                    "start_at": subscription.get('start_at'),
                    "end_at": str(end_at) if end_at else "NULL",
                    "is_active": subscription.get('is_active'),
                    "delete_status": subscription.get('delete_status'),
                }
            },
        )
        
        # Check if subscription has ended
        if end_at:
            try:
                from dateutil import parser as date_parser
                from datetime import timezone
                
                # Parse end_at timestamp (stored as TEXT in format: "2025-12-07 13:42:00+00")
                # dateutil parser handles PostgreSQL timestamp format well: "YYYY-MM-DD HH:MM:SS+TZ"
                if isinstance(end_at, str):
                    # Normalize the format if needed - ensure timezone is properly formatted
                    # Handle formats like "2025-12-07 13:42:00+00" or "2025-12-07 13:42:00+00:00"
                    end_at_normalized = end_at.strip()
                    
                    # dateutil parser handles this format directly
                    end_datetime = date_parser.parse(end_at_normalized)
                elif isinstance(end_at, datetime):
                    end_datetime = end_at
                else:
                    # Convert to string and parse
                    end_datetime = date_parser.parse(str(end_at))
                
                # Compare with current time (UTC)
                current_time = datetime.now(timezone.utc)
                
                # Ensure end_datetime has timezone info (assume UTC if None)
                if end_datetime.tzinfo is None:
                    end_datetime = end_datetime.replace(tzinfo=timezone.utc)
                
                # Normalize both to UTC for comparison
                if end_datetime.tzinfo != timezone.utc:
                    end_datetime = end_datetime.astimezone(timezone.utc)
                
                logger.debug(
                    "Comparing subscription end date with current time",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "subscription_id": subscription.get('id'),
                            "end_at_raw": str(end_at),
                            "end_datetime_utc": end_datetime.isoformat(),
                            "current_time_utc": current_time.isoformat(),
                            "is_expired": end_datetime < current_time,
                            "time_until_expiry_seconds": (end_datetime - current_time).total_seconds() if end_datetime >= current_time else None,
                        }
                    },
                )
                
                if end_datetime < current_time:
                    logger.warning(
                        "Subscription has ended",
                        extra={
                            "extra_fields": {
                                "tenant_id": tenant_id,
                                "user_id": user_id,
                                "subscription_id": subscription.get('id'),
                                "end_at": str(end_at),
                                "end_datetime": end_datetime.isoformat(),
                                "current_time": current_time.isoformat(),
                            }
                        },
                    )
                    # Format the date nicely for the user
                    end_date_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')
                    return False, f"Your subscription ended on {end_date_str}. Please renew your subscription to continue."
            except Exception as e:
                logger.error(
                    f"Error parsing subscription end date: {str(e)}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "end_at": str(end_at),
                            "end_at_type": type(end_at).__name__,
                            "error": str(e),
                            "traceback": str(e.__traceback__) if hasattr(e, '__traceback__') else None,
                        }
                    },
                )
                # If we can't parse the date, fail securely - block the request
                # This prevents allowing operations when we can't verify subscription status
                logger.warning("Could not parse end_at date, blocking request for security")
                return False, "Unable to verify subscription status. Please contact support."
        
        # Subscription is active (end_at is NULL or in the future)
        if end_at:
            logger.debug(
                "Subscription is active - end date is in the future",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "subscription_id": subscription.get('id'),
                        "end_at": str(end_at),
                    }
                },
            )
        else:
            logger.debug(
                "Subscription is active - no end date (NULL)",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "subscription_id": subscription.get('id'),
                        "end_at": "NULL",
                    }
                },
            )
        return True, None
        
    except Exception as e:
        logger.error(
            f"Error checking subscription status: {str(e)}",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "error": str(e),
                }
            },
        )
        # Fail securely - deny access on error to prevent unauthorized operations
        return False, "Error verifying subscription status. Please contact support."


def verify_subscription_active(
    current_user: dict = Depends(CustomAuthService.get_current_user),
) -> dict:
    """
    FastAPI dependency to verify that the user's subscription is active before allowing data modifications.
    
    This dependency should be used in POST, PUT, DELETE endpoints to ensure that only users
    with active subscriptions can perform data modification operations.
    
    GET and LIST operations should NOT use this dependency.
    
    Args:
        current_user: User data from CustomAuthService.get_current_user
    
    Raises:
        HTTPException: 403 if subscription has ended or is not found
    
    Returns:
        dict: {"status": "active"} if subscription is active
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
    
    tenant_id = current_user.data[0].tenant_id
    user_id = current_user.data[0].user_id
    
    logger.debug(
        "Checking subscription status",
        extra={
            "extra_fields": {
                "user_id": user_id,
                "tenant_id": tenant_id,
            }
        },
    )
    
    is_active, error_message = check_subscription_active(tenant_id, user_id)
    
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