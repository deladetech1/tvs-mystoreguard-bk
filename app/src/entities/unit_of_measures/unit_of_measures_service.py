from typing import Optional
from src.entities.unit_of_measures.unit_of_measures_read_dto import (
    GetUnitOfMeasuresServiceReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger

logger = get_logger("unit_of_measures_service")


class UnitOfMeasuresService:
    """Service class for unit of measures operations"""

    @staticmethod
    def get_unit_of_measures(
        tenant_id: str,
        is_active: Optional[bool] = None,
    ) -> Respons[list[GetUnitOfMeasuresServiceReadDto]]:
        """Get list of unit of measures for a tenant"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "tenant_id = %s",
                    "delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id]

                # Optional filter for active unit of measures
                if is_active is not None:
                    where_conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get unit of measures
                cursor.execute(
                    f"""SELECT * FROM {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE}
                    WHERE {where_clause}
                    ORDER BY name ASC""",
                    tuple(params),
                )
                unit_of_measures = cursor.fetchall()

                uom_list = []
                for uom in unit_of_measures:
                    uom_dict = dict(uom)
                    uom_list.append(GetUnitOfMeasuresServiceReadDto(**uom_dict))

                logger.info(
                    f"Retrieved {len(uom_list)} unit of measures for tenant {tenant_id}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "count": len(uom_list),
                            "is_active_filter": is_active,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Unit of measures retrieved successfully",
                    data=uom_list,
                )

        except Exception as e:
            logger.error(f"Error getting unit of measures: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get unit of measures: {str(e)}",
                error="INTERNAL_ERROR",
            )

