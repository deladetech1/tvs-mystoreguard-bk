"""
Pricing Calculator Utility

Thin wrapper around ProductPriceCalculator and SalesPriceCalculator.
Provides calculate_all_prices (with currency info) and get_currency_info.

All pricing, tax, and price-lookup logic is delegated to avoid duplication.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from datetime import datetime
from src.configs.settings import db_settings
from src.configs.logging import get_logger
from src.utils.product_price_calculator import ProductPriceCalculator, round_money
from src.utils.sales_price_calculator import SalesPriceCalculator

logger = get_logger("pricing_calculator")


class PricingCalculator:
    """Utility class for calculating product prices.

    Delegates to ProductPriceCalculator (cost/base/actual prices)
    and SalesPriceCalculator (pricing rules with quantity, tax with conditions).
    """

    # Delegate price lookups to ProductPriceCalculator
    get_cost_price = ProductPriceCalculator.get_cost_price
    get_base_selling_price = ProductPriceCalculator.get_base_selling_price
    get_actual_price = ProductPriceCalculator.get_actual_price

    # Delegate pricing rules and tax to SalesPriceCalculator (includes quantity-based rules and tax conditions)
    apply_pricing_rules = SalesPriceCalculator.apply_pricing_rules
    apply_tax_rules = SalesPriceCalculator.apply_tax_rules

    @staticmethod
    def get_currency_info(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        batch_id: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Get currency information from latest batch.

        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            batch_id: Optional batch ID to get specific batch currency

        Returns:
            Dict with currency_id, currency_name, currency_symbol
        """
        try:
            if batch_id:
                cursor.execute(
                    f"""SELECT pb.currency_id, c.name as currency_name, c.symbol as currency_symbol
                    FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c
                        ON pb.currency_id = c.id AND pb.tenant_id = c.tenant_id
                    WHERE pb.id = %s AND pb.product_id = %s
                    AND pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s
                    AND pb.delete_status = 'NOT_DELETED'""",
                    (batch_id, product_id, tenant_id, org_id, bus_id)
                )
                batch = cursor.fetchone()
                if batch:
                    return {
                        'currency_id': batch.get('currency_id'),
                        'currency_name': batch.get('currency_name'),
                        'currency_symbol': batch.get('currency_symbol')
                    }

            cursor.execute(
                f"""SELECT pb.currency_id, c.name as currency_name, c.symbol as currency_symbol
                FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c
                    ON pb.currency_id = c.id AND pb.tenant_id = c.tenant_id
                WHERE pb.product_id = %s AND pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s
                AND pb.delete_status = 'NOT_DELETED'
                ORDER BY pb.cdatetime DESC
                LIMIT 1""",
                (product_id, tenant_id, org_id, bus_id)
            )
            batch = cursor.fetchone()
            if batch:
                return {
                    'currency_id': batch.get('currency_id'),
                    'currency_name': batch.get('currency_name'),
                    'currency_symbol': batch.get('currency_symbol')
                }

            return {
                'currency_id': None,
                'currency_name': None,
                'currency_symbol': None
            }
        except Exception as e:
            logger.error(f"Error getting currency info: {str(e)}", exc_info=True)
            return {
                'currency_id': None,
                'currency_name': None,
                'currency_symbol': None
            }

    @staticmethod
    def calculate_all_prices(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        quantity: int = 1,
        location_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        sku: Optional[str] = None,
        product_metadata: Optional[Dict[str, str]] = None,
        current_datetime: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate all price values for a product.

        Returns:
            Dict with:
            - cost_price: Cost price
            - base_selling_price: Base selling price
            - actual_price: Actual price from msg_product_prices
            - price_after_pricing_rule: Price after pricing rules
            - price_after_tax: Final price after tax
            - tax_details: Tax calculation details
            - currency_id, currency_name, currency_symbol
        """
        try:
            # 1. Get Cost Price
            cost_price = ProductPriceCalculator.get_cost_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )

            # 2. Get Base Selling Price (from latest batch)
            base_selling_price = ProductPriceCalculator.get_base_selling_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )

            # 3. Get Actual Price
            actual_price = ProductPriceCalculator.get_actual_price(
                cursor, product_id, tenant_id, org_id, bus_id,
                location_id, sku, product_metadata, batch_id
            )

            if actual_price is None:
                actual_price = base_selling_price or Decimal('0')

            # 4. Apply Pricing Rules (including quantity-based)
            pricing_result = SalesPriceCalculator.apply_pricing_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                actual_price, quantity, location_id, sku, product_metadata, current_datetime
            )

            price_after_pricing_rule = pricing_result['price'] if isinstance(pricing_result, dict) else pricing_result
            pricing_rule_applied = pricing_result.get('pricing_rule_applied') if isinstance(pricing_result, dict) else None

            if price_after_pricing_rule is not None:
                price_after_pricing_rule = round_money(max(Decimal('0'), price_after_pricing_rule))

            # 5. Apply Tax Rules (with conditions)
            tax_result = SalesPriceCalculator.apply_tax_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                price_after_pricing_rule, quantity, price_after_pricing_rule,
                location_id, sku, product_metadata
            )

            final_price = tax_result['final_price'] if tax_result['final_price'] is not None else None
            if final_price is not None:
                final_price = round_money(max(Decimal('0'), final_price))

            price_after_tax = tax_result['final_price'] if tax_result['final_price'] is not None else None
            if price_after_tax is not None:
                price_after_tax = round_money(max(Decimal('0'), price_after_tax))

            # 6. Get currency information from latest batch
            currency_info = PricingCalculator.get_currency_info(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )

            def decimal_to_float(value):
                if value is None:
                    return None
                return float(round_money(value))

            return {
                'cost_price': decimal_to_float(cost_price),
                'base_selling_price': decimal_to_float(base_selling_price),
                'actual_price': decimal_to_float(actual_price),
                'price_after_pricing_rule': decimal_to_float(price_after_pricing_rule),
                'price_after_tax': decimal_to_float(price_after_tax),
                'tax_amount': decimal_to_float(tax_result['tax_amount']),
                'final_price': decimal_to_float(final_price),
                'currency_id': currency_info.get('currency_id'),
                'currency_name': currency_info.get('currency_name'),
                'currency_symbol': currency_info.get('currency_symbol'),
                'taxes_applied': tax_result['taxes_applied'],
                'pricing_rule_applied': pricing_rule_applied,
                'tax_rule_applied': tax_result.get('tax_rule_applied')
            }

        except Exception as e:
            logger.error(f"Error calculating all prices: {str(e)}", exc_info=True)
            return {
                'cost_price': None,
                'base_selling_price': None,
                'actual_price': None,
                'price_after_pricing_rule': None,
                'price_after_tax': None,
                'tax_amount': None,
                'final_price': None,
                'currency_id': None,
                'currency_name': None,
                'currency_symbol': None,
                'taxes_applied': [],
                'pricing_rule_applied': None,
                'tax_rule_applied': None
            }
