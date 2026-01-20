from typing import Optional
from src.entities.currencies.currencies_read_dto import (
    GetCurrenciesServiceReadDto,
    GetCurrenciesSimpleServiceReadDto,
    GetCurrencySimpleServiceReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger

logger = get_logger("currencies_service")


class CurrenciesService:
    """Service class for currencies operations"""

    @staticmethod
    def get_currencies(
        tenant_id: str,
        is_active: Optional[bool] = None,
    ) -> Respons[list[GetCurrenciesSimpleServiceReadDto]]:
        """Get list of currencies for a tenant - returns id, name, code, symbol, decimal_places, currency_position, and is_default"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "tenant_id = %s",
                    "delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id]

                # Optional filter for active currencies
                if is_active is not None:
                    where_conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = " AND ".join(where_conditions)

                # Get currencies - select all required fields
                cursor.execute(
                    f"""SELECT 
                        id,
                        name,
                        code,
                        symbol,
                        decimal_places,
                        currency_position,
                        is_default
                    FROM {db_settings.CORE_PLATFORM_CURRENCY}
                    WHERE {where_clause}
                    ORDER BY is_default DESC, name ASC""",
                    tuple(params),
                )
                currencies = cursor.fetchall()

                currency_list = []
                for currency in currencies:
                    currency_dict = dict(currency)
                    currency_item = GetCurrenciesSimpleServiceReadDto(
                        id=currency_dict["id"],
                        name=currency_dict["name"],
                        code=currency_dict["code"],
                        symbol=currency_dict["symbol"],
                        decimal_places=currency_dict.get("decimal_places", 2),
                        currency_position=currency_dict.get("currency_position", "before"),
                        is_default=currency_dict.get("is_default", False),
                    )
                    currency_list.append(currency_item)

                logger.info(
                    f"Retrieved {len(currency_list)} currencies for tenant {tenant_id}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "count": len(currency_list),
                            "is_active_filter": is_active,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Currencies retrieved successfully",
                    data=currency_list,
                )

        except Exception as e:
            logger.error(f"Error getting currencies: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get currencies: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_currency(
        currency_id: str,
        tenant_id: str,
    ) -> Respons[GetCurrencySimpleServiceReadDto]:
        """Get a single currency by ID - returns id, name, code, symbol, decimal_places, currency_position, and is_default"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get currency - select all required fields
                cursor.execute(
                    f"""SELECT 
                        id,
                        name,
                        code,
                        symbol,
                        decimal_places,
                        currency_position,
                        is_default
                    FROM {db_settings.CORE_PLATFORM_CURRENCY}
                    WHERE id = %s AND tenant_id = %s AND delete_status = 'NOT_DELETED'""",
                    (currency_id, tenant_id),
                )
                currency = cursor.fetchone()

                if not currency:
                    return Respons(
                        success=False,
                        detail="Currency not found",
                        error="NOT_FOUND",
                    )

                currency_dict = dict(currency)
                currency_read = GetCurrencySimpleServiceReadDto(
                    id=currency_dict["id"],
                    name=currency_dict["name"],
                    code=currency_dict["code"],
                    symbol=currency_dict["symbol"],
                    decimal_places=currency_dict.get("decimal_places", 2),
                    currency_position=currency_dict.get("currency_position", "before"),
                    is_default=currency_dict.get("is_default", False),
                )

                logger.info(
                    f"Retrieved currency {currency_id} for tenant {tenant_id}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "currency_id": currency_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Currency retrieved successfully",
                    data=[currency_read],
                )

        except Exception as e:
            logger.error(f"Error getting currency: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get currency: {str(e)}",
                error="INTERNAL_ERROR",
            )

