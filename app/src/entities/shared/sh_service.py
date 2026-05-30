from typing import Optional, List
import json
from datetime import datetime, date
from decimal import Decimal
import psycopg2
from psycopg2 import DatabaseError, IntegrityError
from src.configs.database import DatabaseManager
from src.configs.settings import db_settings
from src.configs.logging import get_logger
from src.entities.shared.sh_response import Respons, PaginationMeta
from trovesuite.utils import Helper

logger = get_logger("shared_service")


def _make_json_serializable(data):
    """Recursively convert data to JSON-serializable format"""
    if data is None:
        return None
    
    if isinstance(data, dict):
        
        return {key: _make_json_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_make_json_serializable(item) for item in data]

    elif isinstance(data, (datetime, date)):
        return data.isoformat()

    elif isinstance(data, Decimal):
        return float(data)
    else:
        # For other types, try to convert if possible
        try:
            json.dumps(data)  # Test if serializable
            return data
        except (TypeError, ValueError):
            # If not serializable, convert to string
            return str(data)


class ActivityLogService:
    """Service for activity log operations"""

    @staticmethod
    def get_activity_logs(
        tenant_id: str,
        resource_types: Optional[List[str]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actions: Optional[List[str]] = None,
        action: Optional[str] = None,
        org_id: Optional[str] = None,
        bus_id: Optional[str] = None,
        loc_id: Optional[str] = None,
        app_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        size: int = 10
    ) -> Respons:
        """Get activity logs with pagination and date/time filtering"""
        try:
            offset = (page - 1) * size

            # Filter by tenant_id (required parameter)
            if tenant_id and tenant_id.strip():
                conditions = ["tenant_id = %s"]
                params = [tenant_id.strip()]
            else:
                # If tenant_id is empty, filter for logs with empty tenant_id (unlikely but handled)
                conditions = ["(tenant_id IS NULL OR tenant_id = '')"]
                params = []

            # Normalize resource types (support single or multiple)
            # If resource_types is None or empty, return all logs (don't filter by resource_type)
            resource_types_list = [
                rt.strip() for rt in (resource_types or []) if rt and rt.strip()
            ]
            if resource_type:
                resource_types_list.append(resource_type.strip())

            # Only filter by resource_type if at least one is provided
            if resource_types_list:
                resource_placeholders = ", ".join(["%s"] * len(resource_types_list))
                conditions.append(f"resource_type IN ({resource_placeholders})")
                params.extend(resource_types_list)

            # Use mystoreguard activity logs table
            # Schema: id, tenant_id, org_id, bus_id, loc_id, action, resource_type, old_data (JSONB), new_data (JSONB),
            # description, performed_by_email, performed_by_contact, performed_by_fullname, cdate, ctime, cdatetime
            activity_logs_table = db_settings.MSG_ACTIVITY_LOGS_TABLE
            
            # Note: resource_id filter is intentionally omitted
            # We don't filter by JSONB fields (new_data/old_data) as they may not exist in all logs

            # Normalize actions (support single or multiple)
            actions_list = [
                act.strip().lower() for act in (actions or []) if act and act.strip()
            ]
            if action:
                actions_list.append(action.strip().lower())

            if actions_list:
                action_placeholders = ", ".join(["%s"] * len(actions_list))
                conditions.append(f"action IN ({action_placeholders})")
                params.extend(actions_list)

            # Filter by org_id, bus_id, loc_id if provided (these are actual columns in msg_activity_logs table)
            if org_id is not None:
                org_id_clean = org_id.strip() if org_id else ""
                if org_id_clean == "":
                    # Filter for logs with empty org_id
                    conditions.append("(org_id IS NULL OR org_id = '')")
                else:
                    conditions.append("org_id = %s")
                    params.append(org_id_clean)
            if bus_id is not None:
                bus_id_clean = bus_id.strip() if bus_id else ""
                if bus_id_clean == "":
                    # Filter for logs with empty bus_id
                    conditions.append("(bus_id IS NULL OR bus_id = '')")
                else:
                    conditions.append("bus_id = %s")
                    params.append(bus_id_clean)
            if loc_id is not None:
                loc_id_clean = loc_id.strip() if loc_id else ""
                if loc_id_clean == "":
                    # Filter for logs with empty loc_id
                    conditions.append("(loc_id IS NULL OR loc_id = '')")
                else:
                    conditions.append("loc_id = %s")
                    params.append(loc_id_clean)

            # Filter by date/time using cdatetime
            # Support both date-only (YYYY-MM-DD) and datetime (YYYY-MM-DD HH:MM:SS) formats
            if from_date:
                from_date_clean = from_date.strip()
                # Check if it's date-only (YYYY-MM-DD) or includes time (has space or colon)
                if len(from_date_clean) == 10 and ' ' not in from_date_clean:  # Date only: YYYY-MM-DD
                    conditions.append("DATE(cdatetime) >= DATE(%s)")
                else:  # Datetime: YYYY-MM-DD HH:MM:SS or similar formats
                    conditions.append("cdatetime >= %s")
                params.append(from_date_clean)

            if to_date:
                to_date_clean = to_date.strip()
                # Check if it's date-only (YYYY-MM-DD) or includes time (has space or colon)
                if len(to_date_clean) == 10 and ' ' not in to_date_clean:  # Date only: YYYY-MM-DD
                    conditions.append("DATE(cdatetime) <= DATE(%s)")
                else:  # Datetime: YYYY-MM-DD HH:MM:SS or similar formats
                    conditions.append("cdatetime <= %s")
                params.append(to_date_clean)

            where_clause = " AND ".join(conditions)

            # Debug logging
            logger.debug(
                f"Querying activity logs",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "resource_types": resource_types_list,
                        "actions": actions_list if actions_list else "all",
                        "org_id": org_id,
                        "bus_id": bus_id,
                        "loc_id": loc_id,
                        "where_clause": where_clause,
                        "params": params[:len(params)-2] if len(params) > 2 else params,  # Exclude LIMIT/OFFSET params
                    }
                }
            )

            # Count total
            count_query = f"""
                SELECT COUNT(1) as total
                FROM {activity_logs_table}
                WHERE {where_clause}
            """
            
            count_params = tuple(params)  # Exclude LIMIT/OFFSET for count
            count_result = DatabaseManager.execute_query(count_query, count_params)
            total = count_result[0].get('total', 0) if count_result else 0
            
            logger.debug(
                "Activity logs count result",
                extra={
                    "extra_fields": {
                        "total": total,
                        "count_query": count_query,
                        "count_params": count_params,
                    }
                }
            )

            # Query with only the requested fields
            query = f"""
                SELECT id, action, old_data, new_data,
                       performed_by_fullname, performed_by_email, performed_by_contact,
                       cdate, ctime, cdatetime
                FROM {activity_logs_table}
                WHERE {where_clause}
                ORDER BY cdatetime DESC
                LIMIT %s OFFSET %s
            """
            params.extend([size, offset])
            logs = DatabaseManager.execute_query(query, tuple(params))
            
            # Transform logs to return only the requested fields
            transformed_logs = []
            for log in logs:
                new_data = log.get('new_data', {})
                old_data = log.get('old_data', {})
                
                # Parse JSONB if it's a string
                if isinstance(new_data, str):
                    try:
                        new_data = json.loads(new_data) if new_data else None
                    except:
                        new_data = None
                if isinstance(old_data, str):
                    try:
                        old_data = json.loads(old_data) if old_data else None
                    except:
                        old_data = None
                
                transformed_log = {
                    'log_id': log.get('id'),
                    'new_data': new_data,
                    'old_data': old_data,
                    'action': log.get('action'),
                    'performed_by_fullname': log.get('performed_by_fullname'),
                    'performed_by_email': log.get('performed_by_email'),
                    'performed_by_contact': log.get('performed_by_contact'),
                    'cdate': log.get('cdate'),
                    'ctime': log.get('ctime'),
                    'cdatetime': log.get('cdatetime'),
                }
                transformed_logs.append(transformed_log)
            
            logs = transformed_logs

            pagination = PaginationMeta(
                page=page,
                size=size,
                total=total,
                has_next=(page * size) < total
            )

            return Respons(
                detail="Activity logs retrieved successfully",
                data=logs,
                success=True,
                status_code=200,
                pagination=pagination
            )
        except Exception as e:
            logger.error(f"Error getting activity logs: {str(e)}")
            return Respons(
                detail="Failed to retrieve activity logs",
                error=str(e),
                data=[],
                success=False,
                status_code=500
            )

    @staticmethod
    def get_activity_resource_types(
        tenant_id: str,
        org_id: Optional[str] = None,
        bus_id: Optional[str] = None,
        loc_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> Respons:
        """List resource types from cp_resource_types table filtered by parent_resource_id.
        
        This endpoint returns resource types from the cp_resource_types table where parent_resource_id
        matches 'rt-subscribed-app-msgus'. This allows users to select resource types for the
        mystoreguard application.
        """
        try:
            resource_types_table = db_settings.CORE_PLATFORM_RESOURCE_TYPES_TABLE
            parent_resource_id = "rt-subscribed-app-msg"

            conditions = [
                "delete_status = 'NOT_DELETED'",
                "is_active = true",
                "parent_resource_id = %s"
            ]
            params = [parent_resource_id]

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT id, resource_type_name, parent_resource_id, description
                FROM {resource_types_table}
                WHERE {where_clause}
                ORDER BY resource_type_name
            """

            logger.debug(
                "Fetching activity resource types from cp_resource_types",
                extra={
                    "extra_fields": {
                        "parent_resource_id": parent_resource_id,
                        "query": query,
                    }
                }
            )

            results = DatabaseManager.execute_query(query, tuple(params))

            logger.debug(
                f"Found {len(results)} resource types",
                extra={"extra_fields": {"resource_types_count": len(results), "parent_resource_id": parent_resource_id}}
            )

            return Respons(
                detail="Resource types retrieved successfully",
                data=[
                    {
                        "id": row.get("id"),
                        "resource_type_name": row.get("resource_type_name"),
                        "parent_resource_id": row.get("parent_resource_id"),
                        "description": row.get("description"),
                    }
                    for row in results
                ],
                success=True,
                status_code=200,
            )
        except Exception as e:
            logger.error(
                f"Error fetching activity resource types: {str(e)}",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "parent_resource_id": "rt-subscribed-app-msgus",
                        "error": str(e),
                    }
                },
                exc_info=True
            )
            return Respons(
                detail="Failed to retrieve activity resource types",
                error=str(e),
                data=[],
                success=False,
                status_code=500,
            )

    @staticmethod
    def delete_activity_logs(
        tenant_id: str,
        log_ids: List[str],
        deleted_by: str
    ) -> Respons:
        """Delete activity logs by IDs"""
        try:
            if not log_ids:
                return Respons(
                    detail="No log IDs provided",
                    data=[],
                    success=False,
                    status_code=400
                )

            # Use mystoreguard activity logs table
            activity_logs_table = db_settings.MSG_ACTIVITY_LOGS_TABLE
            
            placeholders = ', '.join(['%s'] * len(log_ids))
            query = f"""
                DELETE FROM {activity_logs_table}
                WHERE id IN ({placeholders})
                AND tenant_id = %s
            """
            params = (*log_ids, tenant_id)

            deleted_count = DatabaseManager.execute_update(query, params)

            return Respons(
                detail=f"Successfully deleted {deleted_count} activity logs",
                data=[{"deleted_count": deleted_count}],
                success=True,
                status_code=200
            )
        except Exception as e:
            logger.error(f"Error deleting activity logs: {str(e)}")
            return Respons(
                detail="Failed to delete activity logs",
                error=str(e),
                data=[],
                success=False,
                status_code=500
            )

    @staticmethod
    def log_activity(
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        description: Optional[str] = None,
        performed_by: str = None,
        org_id: str = "",
        bus_id: str = "",
        loc_id: str = "",
        cursor = None  # Optional: Use same transaction cursor if provided
    ) -> bool:
        """Log an activity to msg_activity_logs table

        Args:
            tenant_id: The tenant ID
            resource_type: The type of resource (e.g., 'rt-expenses', 'rt-warehouse', 'rt-shop', 'rt-clients', 'rt-invoice', 'rt-sales', 'rt-suppliers')
            resource_id: The ID of the resource
            action: The action performed (e.g., 'create', 'update', 'delete')
            old_data: The old data before the change (optional, for updates/deletes)
            new_data: The new data after the change (optional, for creates/updates)
            description: Additional description (optional)
            performed_by: User ID who performed the action
            org_id: Organization ID (required for mystoreguard)
            bus_id: Business ID (required for mystoreguard)
            loc_id: Location ID (required for mystoreguard)
            cursor: Optional database cursor to use same transaction (if None, creates new transaction)

        Returns:
            bool: True if logging was successful, False otherwise

        Note: msg_activity_logs table schema:
        - id, tenant_id, org_id, bus_id, loc_id, action, resource_type
        - old_data (JSONB), new_data (JSONB), description (TEXT)
        - performed_by_email, performed_by_contact, performed_by_fullname
        - cdate, ctime, cdatetime

        When called inside a DatabaseManager.transaction(), pass the cursor parameter
        to ensure the activity log is part of the same transaction.
        """
        try:
            cdate = Helper.current_date_time()["cdate"]
            ctime = Helper.current_date_time()["ctime"]
            cdatetime = Helper.current_date_time()["cdatetime"]

            log_id = Helper.generate_unique_identifier(prefix="log")

            # Prepare old_data and new_data JSONB - convert datetime and other non-serializable types
            old_data_serializable = _make_json_serializable(old_data) if old_data else None
            new_data_serializable = _make_json_serializable(new_data) if new_data else None
            
            # Now safe to serialize - all datetime objects have been converted to ISO format strings
            old_data_json = json.dumps(old_data_serializable) if old_data_serializable else None
            new_data_json = json.dumps(new_data_serializable) if new_data_serializable else None

            # Generate description if not provided
            if not description:
                description = f"{action} {resource_type} {resource_id}" if resource_id else f"{action} {resource_type}"

            # Try to get user info for performed_by fields (optional, won't fail if not found)
            performed_by_email = None
            performed_by_contact = None
            performed_by_fullname = None
            
            if performed_by:
                try:
                    # Try to fetch user details if performed_by is a user_id
                    user_query = f"""
                        SELECT email, contact, fullname 
                        FROM {db_settings.CORE_PLATFORM_USERS_TABLE} 
                        WHERE id = %s AND tenant_id = %s AND delete_status = 'NOT_DELETED' AND is_active = true
                        LIMIT 1
                    """
                    # Use cursor if provided (same transaction), otherwise create new query
                    if cursor:
                        cursor.execute(user_query, (performed_by, tenant_id))
                        user_result = cursor.fetchone()
                        if user_result:
                            performed_by_email = user_result.get('email')
                            performed_by_contact = user_result.get('contact')
                            performed_by_fullname = user_result.get('fullname')
                    else:
                        user_result = DatabaseManager.execute_query(user_query, (performed_by, tenant_id))
                        if user_result:
                            user = user_result[0]
                            performed_by_email = user.get('email')
                            performed_by_contact = user.get('contact')
                            performed_by_fullname = user.get('fullname')
                except Exception as user_error:
                    # If user lookup fails, continue without user details
                    logger.debug(f"Could not fetch user details for performed_by {performed_by}: {str(user_error)}")

            # Use mystoreguard activity logs table
            activity_logs_table = db_settings.MSG_ACTIVITY_LOGS_TABLE

            # Insert into msg_activity_logs table with actual schema (includes org_id, bus_id, loc_id columns)
            query = f"""
                INSERT INTO {activity_logs_table}
                (id, tenant_id, org_id, bus_id, loc_id, resource_type, action, old_data, new_data, description,
                 performed_by_email, performed_by_contact, performed_by_fullname,
                 cdate, ctime, cdatetime)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                log_id, tenant_id, org_id, bus_id, loc_id, resource_type, action,
                old_data_json, new_data_json, description,
                performed_by_email, performed_by_contact, performed_by_fullname,
                cdate, ctime, cdatetime
            )
            
            # If cursor is provided, use the same transaction; otherwise create a new one
            if cursor:
                cursor.execute(query, params)
                logger.debug(f"Activity logged successfully within transaction: {resource_type} {resource_id} {action}")
            else:
                DatabaseManager.execute_update(query, params)
                logger.debug(f"Activity logged successfully with new transaction: {resource_type} {resource_id} {action}")
            
            return True
        except (DatabaseError, IntegrityError) as db_err:
            # If using a cursor (within a transaction), database errors abort the transaction
            # We must re-raise so the transaction can be rolled back properly
            if cursor:
                logger.error(
                    f"Database error logging activity (transaction will be rolled back): {str(db_err)}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                            "action": action,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "loc_id": loc_id,
                            "error": str(db_err),
                            "error_type": type(db_err).__name__,
                        }
                    },
                    exc_info=True
                )
                # Re-raise database errors when using a cursor so transaction can be rolled back
                raise
            else:
                # Not using a cursor, so transaction is isolated - log and return False
                logger.error(
                    f"Database error logging activity: {str(db_err)}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                            "action": action,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "loc_id": loc_id,
                            "error": str(db_err),
                            "error_type": type(db_err).__name__,
                        }
                    },
                    exc_info=True
                )
                return False
        except Exception as e:
            logger.error(
                f"Error logging activity: {str(e)}",
                extra={
                    "extra_fields": {
                        "tenant_id": tenant_id,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "action": action,
                        "org_id": org_id,
                        "bus_id": bus_id,
                        "loc_id": loc_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True
            )
            return False


class DeletionApprovalService:
    """Service for handling deletion approvals"""

    @staticmethod
    def approve_deletion(
        tenant_id: str,
        resource_type: str,
        table_name: str,
        resource_id: str,
        action: str,
        approved_by: str,
        reason: Optional[str] = None,
    ) -> Respons:
        """
        Approve or reject a pending deletion request.

        Args:
            tenant_id: The tenant ID
            resource_type: The type of resource (e.g., rt-expenses, rt-warehouse, rt-shop, rt-clients)
            table_name: The database table name for the resource
            resource_id: The ID of the resource to approve/reject deletion
            action: Either 'approve' (permanent delete) or 'reject' (restore)
            approved_by: User ID performing the approval
            reason: Optional reason for the approval/rejection

        Returns:
            Respons with the result of the operation
        """
        try:
            cdate = Helper.current_date_time()["cdate"]
            ctime = Helper.current_date_time()["ctime"]
            cdatetime = Helper.current_date_time()["cdatetime"]

            # Check if resource exists and is in PENDING state
            # Try to get org_id, bus_id, loc_id if they exist in the table
            try:
                check_query = f"""
                    SELECT id, delete_status, org_id, bus_id, loc_id FROM {table_name}
                    WHERE tenant_id = %s AND id = %s AND delete_status = 'PENDING'
                """
                existing = DatabaseManager.execute_query(check_query, (tenant_id, resource_id))
            except Exception:
                # Fallback: table doesn't have org_id, bus_id, loc_id columns
                check_query = f"""
                    SELECT id, delete_status FROM {table_name}
                    WHERE tenant_id = %s AND id = %s AND delete_status = 'PENDING'
                """
                existing = DatabaseManager.execute_query(check_query, (tenant_id, resource_id))

            if not existing or len(existing) == 0:
                return Respons(
                    detail="Resource not found or not in pending deletion state",
                    data=[],
                    success=False,
                    status_code=404,
                    error=None,
                )

            if action == "approve":
                # Permanent delete the resource
                delete_query = f"""
                    DELETE FROM {table_name}
                    WHERE tenant_id = %s AND id = %s AND delete_status = 'PENDING'
                """
                DatabaseManager.execute_update(delete_query, (tenant_id, resource_id))

                # If this is a clients deletion, handle any client-specific cleanup if needed
                if resource_type == "rt-clients" and table_name == db_settings.MSG_CLIENTS_TABLE:
                    # Add any client-specific cleanup logic here if needed
                    pass

                message = "Deletion approved and resource permanently deleted"

                # Extract org_id, bus_id, loc_id from existing record
                existing_dict = dict(existing[0]) if existing and len(existing) > 0 and hasattr(existing[0], 'keys') else {}
                org_id = existing_dict.get('org_id', '')
                bus_id = existing_dict.get('bus_id', '')
                loc_id = existing_dict.get('loc_id', '')

                # Log activity
                try:
                    old_data = dict(existing[0]) if existing and len(existing) > 0 else {}
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action="approve_deletion",
                        old_data=old_data,
                        new_data=None,
                        description=f"Deletion approved for {resource_type} {resource_id} (reason: {reason})",
                        performed_by=approved_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}")

            elif action == "reject":
                # Restore the resource (change delete_status back to NOT_DELETED)
                restore_query = f"""
                    UPDATE {table_name}
                    SET delete_status = 'NOT_DELETED', is_active = true, updated_by = %s
                    WHERE tenant_id = %s AND id = %s AND delete_status = 'PENDING'
                """
                DatabaseManager.execute_update(restore_query, (approved_by, tenant_id, resource_id))

                message = "Deletion rejected and resource restored"

                # Extract org_id, bus_id, loc_id from existing record
                existing_dict = dict(existing[0]) if existing and len(existing) > 0 and hasattr(existing[0], 'keys') else {}
                org_id = existing_dict.get('org_id', '')
                bus_id = existing_dict.get('bus_id', '')
                loc_id = existing_dict.get('loc_id', '')

                # Log activity
                try:
                    old_data = dict(existing[0]) if existing and len(existing) > 0 else {}
                    # After restore, the data is the same as old_data but with delete_status='NOT_DELETED'
                    new_data = old_data.copy() if old_data else {}
                    if new_data:
                        new_data['delete_status'] = 'NOT_DELETED'
                        new_data['is_active'] = True
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action="reject_deletion",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Deletion rejected for {resource_type} {resource_id} (reason: {reason})",
                        performed_by=approved_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}")
            else:
                return Respons(
                    detail="Invalid action. Use 'approve' or 'reject'",
                    data=[],
                    success=False,
                    status_code=400,
                    error=None,
                )

            # Log the approval/rejection in chat history (only if reason is provided)
            logger.info(
                f"Checking reason for chat history insertion",
                extra={
                    "extra_fields": {
                        "resource_id": resource_id,
                        "action": action,
                        "reason_value": reason,
                        "reason_type": type(reason).__name__,
                        "reason_is_truthy": bool(reason),
                        "reason_stripped": reason.strip() if reason else None,
                    }
                },
            )
            
            if reason and reason.strip():
                try:
                    chat_history_id = Helper.generate_unique_identifier(prefix="rdchid")
                    chat_message = f"[{action.upper()}] {reason.strip()}"
                    chat_query = f"""
                        INSERT INTO {db_settings.MSG_RESOURCE_DELETION_CHAT_HISTORIES_TABLE}
                        (id, tenant_id, resource_id, message, sent_by, cdate, ctime, cdatetime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    logger.info(
                        f"Attempting to insert chat history",
                        extra={
                            "extra_fields": {
                                "resource_id": resource_id,
                                "chat_history_id": chat_history_id,
                                "chat_message": chat_message,
                                "table": db_settings.MSG_RESOURCE_DELETION_CHAT_HISTORIES_TABLE,
                            }
                        },
                    )
                    rows_affected = DatabaseManager.execute_update(
                        chat_query,
                        (chat_history_id, tenant_id, resource_id, chat_message, approved_by, cdate, ctime, cdatetime)
                    )
                    
                    # Verify the insertion by querying the record
                    verify_query = f"""
                        SELECT id, resource_id, message, sent_by
                        FROM {db_settings.MSG_RESOURCE_DELETION_CHAT_HISTORIES_TABLE}
                        WHERE id = %s AND tenant_id = %s
                    """
                    verify_result = DatabaseManager.execute_query(verify_query, (chat_history_id, tenant_id))
                    
                    if rows_affected == 0 or not verify_result:
                        logger.error(
                            f"Chat history INSERT failed or verification failed",
                            extra={
                                "extra_fields": {
                                    "resource_id": resource_id,
                                    "action": action,
                                    "chat_history_id": chat_history_id,
                                    "chat_message": chat_message,
                                    "table": db_settings.MSG_RESOURCE_DELETION_CHAT_HISTORIES_TABLE,
                                    "rows_affected": rows_affected,
                                    "verification_result": verify_result,
                                    "query": chat_query,
                                    "params": (chat_history_id, tenant_id, resource_id, chat_message, approved_by, cdate, ctime, cdatetime),
                                }
                            },
                        )
                    else:
                        logger.info(
                            f"Chat history inserted and verified successfully for {action} action",
                            extra={
                                "extra_fields": {
                                    "resource_id": resource_id,
                                    "action": action,
                                    "rows_affected": rows_affected,
                                    "chat_history_id": chat_history_id,
                                    "chat_message": chat_message,
                                    "table": db_settings.MSG_RESOURCE_DELETION_CHAT_HISTORIES_TABLE,
                                    "verified": True,
                                }
                            },
                        )
                except Exception as chat_error:
                    # Log error but don't fail the approval/rejection
                    logger.error(
                        f"Error inserting chat history: {str(chat_error)}",
                        extra={
                            "extra_fields": {
                                "resource_id": resource_id,
                                "action": action,
                                "error": str(chat_error),
                                "error_type": type(chat_error).__name__,
                                "chat_query": chat_query,
                                "params": (chat_history_id, tenant_id, resource_id, chat_message, approved_by, cdate, ctime, cdatetime),
                            }
                        },
                        exc_info=True,
                    )
            else:
                logger.info(
                    f"Skipping chat history insertion - no reason provided",
                    extra={
                        "extra_fields": {
                            "resource_id": resource_id,
                            "action": action,
                            "reason_value": reason,
                        }
                    },
                )

            return Respons(
                detail=message,
                data=[{"resource_id": resource_id, "action": action}],
                success=True,
                status_code=200,
                error=None,
            )

        except Exception as e:
            logger.error(f"Error in approve_deletion: {str(e)}")
            return Respons(
                detail=f"Failed to process deletion approval: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )


class DeletionChatHistoryService:
    """Service for deletion chat history operations"""

    @staticmethod
    def get_deletion_chat_history(
        tenant_id: str,
        resource_id: str,
        page: int = 1,
        size: int = 10
    ) -> Respons:
        """Get deletion chat history for a resource"""
        try:
            offset = (page - 1) * size

            # Count total
            count_query = f"""
                SELECT COUNT(1) as total
                FROM {db_settings.MSG_RESOURCE_DELETION_CHAT_HISTORIES_TABLE}
                WHERE tenant_id = %s AND resource_id = %s
            """
            count_result = DatabaseManager.execute_query(count_query, (tenant_id, resource_id))
            total = count_result[0].get('total', 0) if count_result else 0

            # Get chat history
            query = f"""
                SELECT id, resource_id, message, sent_by, cdate, ctime, cdatetime
                FROM {db_settings.MSG_RESOURCE_DELETION_CHAT_HISTORIES_TABLE}
                WHERE tenant_id = %s AND resource_id = %s
                ORDER BY cdatetime DESC
                LIMIT %s OFFSET %s
            """
            params = (tenant_id, resource_id, size, offset)

            chat_history = DatabaseManager.execute_query(query, params)

            pagination = PaginationMeta(
                page=page,
                size=size,
                total=total,
                has_next=(page * size) < total
            )

            return Respons(
                detail="Deletion chat history retrieved successfully",
                data=chat_history,
                success=True,
                status_code=200,
                pagination=pagination
            )
        except Exception as e:
            logger.error(f"Error getting deletion chat history: {str(e)}")
            return Respons(
                detail="Failed to retrieve deletion chat history",
                error=str(e),
                data=[],
                success=False,
                status_code=500
            )
