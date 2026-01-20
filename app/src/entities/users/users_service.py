from typing import Optional
from src.entities.users.users_read_dto import (
    GetUsersServiceReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger

logger = get_logger("users_service")


class UsersService:
    """Service class for users operations"""

    @staticmethod
    def get_users(
        tenant_id: str,
        is_active: Optional[bool] = None,
    ) -> Respons[list[GetUsersServiceReadDto]]:
        """Get list of all users for a tenant"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "tenant_id = %s",
                    "delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id]

                # Optional filter for active users
                if is_active is not None:
                    where_conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get all users - select all fields
                cursor.execute(
                    f"""SELECT * FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                    WHERE {where_clause}
                    ORDER BY fullname ASC, email ASC""",
                    tuple(params),
                )
                users = cursor.fetchall()

                user_list = []
                for user in users:
                    user_dict = dict(user)
                    # Remove password from response for security
                    if 'password' in user_dict:
                        user_dict['password'] = None
                    user_list.append(GetUsersServiceReadDto(**user_dict))

                logger.info(
                    f"Retrieved {len(user_list)} users for tenant {tenant_id}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "count": len(user_list),
                            "is_active_filter": is_active,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Users retrieved successfully",
                    data=user_list,
                )

        except Exception as e:
            logger.error(f"Error getting users: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get users: {str(e)}",
                error="INTERNAL_ERROR",
            )

