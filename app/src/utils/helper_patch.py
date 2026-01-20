"""
Patch Helper class to add current_date_time method and update generate_unique_resource_identifier
to use the package's generate_unique_identifier method.
This should be imported early in the application startup
"""
from datetime import datetime
from typing import Optional, List, Callable
from trovesuite.utils import Helper


def current_date_time():
    """Get current date and time in the required format"""
    now = datetime.now()
    return {
        "cdate": now.strftime("%Y-%m-%d"),
        "ctime": now.strftime("%H:%M:%S"),
        "cdatetime": now
    }


def generate_unique_resource_identifier(
    prefix: str,
    tenant_id: Optional[str],
    extra_check_functions: Optional[List[Callable[[str], Optional[int]]]] = None,
) -> str:
    """Generate a unique identifier that does not already exist in the resource_ids table.
    
    Uses the package's generate_unique_identifier method to create the base ID,
    then checks against resource_ids table and any extra_check_functions.

    Args:
        prefix: Prefix for the identifier (e.g., 'grp', 'uid', 'client', 'loan').
        tenant_id: Tenant ID. If None, the main resource_ids table is checked.
        extra_check_functions: Optional list of callables that receive the candidate
            identifier and return a truthy value if the identifier already exists in
            another table that should be considered.

    Returns:
        A unique identifier that does not exist in the resource_ids table (and passes
        any additional uniqueness checks).
    """
    from src.configs.database import DatabaseManager
    from src.configs.settings import db_settings
    from src.configs.logging import get_logger
    
    logger = get_logger("helper_patch")
    extra_checks = extra_check_functions or []

    while True:
        # Use the package's generate_unique_identifier to create the base ID
        candidate = Helper.generate_unique_identifier(prefix=prefix)

        try:
            if tenant_id:
                # For tenant-specific resource IDs, use CORE_PLATFORM_RESOURCE_ID_TABLE
                # This table has tenant_id column for filtering
                resource_table = getattr(db_settings, 'CORE_PLATFORM_RESOURCE_ID_TABLE', None)
                if resource_table:
                    resource_exists = DatabaseManager.execute_scalar(
                        f"""SELECT COUNT(1) FROM {resource_table}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, candidate,),
                    )
                else:
                    # Fallback: assume no conflict if table not configured
                    resource_exists = 0
            else:
                # For main/shared schema resource IDs (no tenant_id)
                main_resource_table = getattr(db_settings, 'CORE_PLATFORM_RESOURCE_ID_TABLE', None)
                if main_resource_table:
                    resource_exists = DatabaseManager.execute_scalar(
                        f"""SELECT COUNT(1) FROM {main_resource_table}
                        WHERE id = %s""",
                        (candidate,),
                    )
                else:
                    # Fallback: assume no conflict if table not configured
                    resource_exists = 0
        except Exception as e:
            logger.error(
                f"Failed to validate uniqueness for resource identifier {candidate}: {str(e)}",
                exc_info=True,
            )
            raise

        if resource_exists and int(resource_exists or 0) > 0:
            continue

        duplicate_found = False
        for check in extra_checks:
            try:
                result = check(candidate)
            except Exception as e:
                logger.error(
                    f"Error while executing additional uniqueness check for {candidate}: {str(e)}",
                    exc_info=True,
                )
                duplicate_found = True
                break

            if result and int(result or 0) > 0:
                duplicate_found = True
                break

        if duplicate_found:
            continue

        return candidate


# Monkey patch Helper class to add/update the methods
Helper.current_date_time = staticmethod(current_date_time)
Helper.generate_unique_resource_identifier = staticmethod(generate_unique_resource_identifier)

