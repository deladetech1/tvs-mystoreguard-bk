from typing import Optional
from src.entities.groups.groups_read_dto import GetGroupsServiceReadDto
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger

logger = get_logger("groups_service")


class GroupsService:
    """Read-only access to core-platform groups (and their members) for the
    workflow UI. Groups are tenant-scoped in core_platform; we read them
    cross-schema and never mutate them here."""

    @staticmethod
    def get_groups(
        tenant_id: str,
        group_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetGroupsServiceReadDto]]:
        try:
            with DatabaseManager.transaction() as cursor:
                where = [
                    "tenant_id = %s",
                    "(is_system = false OR is_system IS NULL)",
                    "delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id]
                if is_active is not None:
                    where.append("is_active = %s")
                    params.append(is_active)
                if group_name:
                    where.append("group_name ILIKE %s")
                    params.append(f"%{group_name}%")
                where_clause = " AND ".join(where)

                cursor.execute(
                    f"SELECT COUNT(*) AS total FROM {db_settings.CORE_PLATFORM_GROUPS_TABLE} WHERE {where_clause}",
                    tuple(params),
                )
                total = (cursor.fetchone() or {}).get("total", 0)

                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT id, group_name, description, is_active
                    FROM {db_settings.CORE_PLATFORM_GROUPS_TABLE}
                    WHERE {where_clause}
                    ORDER BY group_name ASC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                groups = [dict(r) for r in cursor.fetchall()]

                for g in groups:
                    cursor.execute(
                        f"""SELECT ug.user_id, u.fullname
                        FROM {db_settings.CORE_PLATFORM_USER_GROUPS_TABLE} ug
                        INNER JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} u
                            ON ug.user_id = u.id AND ug.tenant_id = u.tenant_id
                        WHERE ug.tenant_id = %s AND ug.group_id = %s
                            AND u.delete_status = 'NOT_DELETED' AND u.is_active = true
                            AND (ug.is_system = false OR ug.is_system IS NULL)""",
                        (tenant_id, g["id"]),
                    )
                    g["users"] = [
                        {"user_id": r["user_id"], "fullname": r.get("fullname")}
                        for r in cursor.fetchall()
                    ]

                items = [GetGroupsServiceReadDto(**g) for g in groups]
                pagination = PaginationMeta(
                    page=page, size=size, total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total,
                )
                return Respons(success=True, detail="Groups retrieved successfully",
                               data=items, pagination=pagination)
        except Exception as e:
            logger.error(f"Error listing groups: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to list groups: {str(e)}", error="INTERNAL_ERROR")
