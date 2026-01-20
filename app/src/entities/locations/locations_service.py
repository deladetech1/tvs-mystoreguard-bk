from typing import Optional
from src.entities.locations.locations_read_dto import (
    GetLocationsServiceReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger

logger = get_logger("locations_service")


class LocationsService:
    """Service class for locations operations"""

    @staticmethod
    def get_locations(
        tenant_id: str,
        is_active: Optional[bool] = None,
    ) -> Respons[list[GetLocationsServiceReadDto]]:
        """Get list of locations for a tenant"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "tenant_id = %s",
                    "delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id]

                # Optional filter for active locations
                if is_active is not None:
                    where_conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get locations
                cursor.execute(
                    f"""SELECT * FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                    WHERE {where_clause}
                    ORDER BY loc_name ASC""",
                    tuple(params),
                )
                locations = cursor.fetchall()

                location_list = []
                for location in locations:
                    location_dict = dict(location)
                    location_list.append(GetLocationsServiceReadDto(**location_dict))

                logger.info(
                    f"Retrieved {len(location_list)} locations for tenant {tenant_id}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "count": len(location_list),
                            "is_active_filter": is_active,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Locations retrieved successfully",
                    data=location_list,
                )

        except Exception as e:
            logger.error(f"Error getting locations: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get locations: {str(e)}",
                error="INTERNAL_ERROR",
            )

