"""
Product Price Calculator Utility

This module provides a price calculator for store/warehouse products.
It calculates prices with simple tax calculation (NO TAX CONDITIONS).

This calculator is used for:
- Store products display
- Warehouse products display
- Product listings

It provides:
1. Cost Price - from product or purchase batch
2. Base Selling Price - from product
3. Actual Price - from msg_product_prices table (with priority logic)
4. Price After Pricing Rule - after applying pricing rules
5. Price After Tax - after applying tax rules (NO CONDITIONS - simple tax calculation)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from datetime import datetime
from src.configs.settings import db_settings
from src.configs.logging import get_logger

logger = get_logger("product_price_calculator")


def round_money(value: Optional[Decimal]) -> Optional[Decimal]:
    """Round money value to 2 decimal places"""
    if value is None:
        return None
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class ProductPriceCalculator:
    """Price calculator for store/warehouse products (SIMPLE TAX - NO CONDITIONS)"""

    @staticmethod
    def get_cost_price(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        batch_id: Optional[str] = None
    ) -> Optional[Decimal]:
        """
        Get cost price for a product.
        
        Priority:
        1. If batch_id provided, get from purchase batch
        2. Otherwise, get from latest purchase batch
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            batch_id: Optional batch ID to get specific batch cost price
            
        Returns:
            Cost price as Decimal or None if not found
        """
        try:
            if batch_id:
                cursor.execute(
                    f"""SELECT cost_price FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    WHERE id = %s AND product_id = %s 
                    AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (batch_id, product_id, tenant_id, org_id, bus_id)
                )
                batch = cursor.fetchone()
                if batch and batch.get('cost_price') is not None:
                    return round_money(Decimal(str(batch['cost_price'])))
            
            cursor.execute(
                f"""SELECT cost_price FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                WHERE product_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                AND delete_status = 'NOT_DELETED'
                ORDER BY cdatetime DESC
                LIMIT 1""",
                (product_id, tenant_id, org_id, bus_id)
            )
            batch = cursor.fetchone()
            if batch and batch.get('cost_price') is not None:
                return round_money(Decimal(str(batch['cost_price'])))
            
            return None
        except Exception as e:
            logger.error(f"Error getting cost price: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_base_selling_price(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        batch_id: Optional[str] = None
    ) -> Optional[Decimal]:
        """
        Get base selling price from latest batch.
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            batch_id: Optional batch ID to get specific batch base selling price
            
        Returns:
            Base selling price as Decimal or None if not found
        """
        try:
            if batch_id:
                cursor.execute(
                    f"""SELECT base_selling_price FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    WHERE id = %s AND product_id = %s 
                    AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (batch_id, product_id, tenant_id, org_id, bus_id)
                )
                batch = cursor.fetchone()
                if batch and batch.get('base_selling_price') is not None:
                    return round_money(Decimal(str(batch['base_selling_price'])))
            
            cursor.execute(
                f"""SELECT base_selling_price FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                WHERE product_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                AND delete_status = 'NOT_DELETED'
                ORDER BY cdatetime DESC
                LIMIT 1""",
                (product_id, tenant_id, org_id, bus_id)
            )
            batch = cursor.fetchone()
            if batch and batch.get('base_selling_price') is not None:
                return round_money(Decimal(str(batch['base_selling_price'])))
            return None
        except Exception as e:
            logger.error(f"Error getting base selling price: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_actual_price(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        location_id: Optional[str] = None,
        sku: Optional[str] = None,
        product_metadata: Optional[Dict[str, str]] = None,
        batch_id: Optional[str] = None
    ) -> Optional[Decimal]:
        """
        Get actual price from msg_product_prices table.
        
        Priority logic:
        1. Prices with stops_other_prices = TRUE are checked first (by priority DESC)
        2. If no stopping price found, check all prices by priority DESC
        3. Priority order: SKU > LOCATION > TAG/CATEGORY/BRAND/LABEL > GLOBAL
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            location_id: Optional location ID for location-based pricing
            sku: Optional SKU for SKU-based pricing
            product_metadata: Optional dict with keys like 'category_id', 'tag_id', 'brand_id', 'label_id'
            
        Returns:
            Actual price as Decimal or None if not found
        """
        try:
            logger.debug(f"Getting actual price for product_id={product_id}, location_id={location_id}, sku={sku}, metadata={product_metadata}")
            
            price_conditions = [
                "product_id = %s",
                "tenant_id = %s",
                "org_id = %s",
                "bus_id = %s",
                "(deleted_by IS NULL OR deleted_by = '')"
            ]
            params = [product_id, tenant_id, org_id, bus_id]
            
            type_conditions = []
            
            if sku:
                type_conditions.append("(of_type = 'SKU' AND target_id = %s)")
                params.append(sku)
            
            if location_id:
                type_conditions.append("(of_type = 'LOCATION' AND target_id = %s)")
                params.append(location_id)
                logger.debug(f"Added LOCATION condition with target_id={location_id}")
            
            if product_metadata:
                for meta_type, meta_id in product_metadata.items():
                    if meta_id:
                        type_map = {
                            'category_id': 'CATEGORY',
                            'tag_id': 'TAG',
                            'brand_id': 'BRAND',
                            'label_id': 'LABEL'
                        }
                        if meta_type in type_map:
                            type_conditions.append(f"(of_type = '{type_map[meta_type]}' AND target_id = %s)")
                            params.append(meta_id)
            
            type_conditions.append("of_type = 'GLOBAL'")
            
            if type_conditions:
                price_conditions.append(f"({' OR '.join(type_conditions)})")
            
            where_clause = " AND ".join(price_conditions)
            
            # First check for prices with stops_other_prices = TRUE
            cursor.execute(
                f"""SELECT price, of_type, priority, stops_other_prices, target_id
                FROM {db_settings.MSG_PRODUCT_PRICES_TABLE}
                WHERE {where_clause} AND stops_other_prices = TRUE
                ORDER BY 
                    CASE of_type
                        WHEN 'SKU' THEN 1
                        WHEN 'LOCATION' THEN 2
                        WHEN 'TAG' THEN 3
                        WHEN 'CATEGORY' THEN 3
                        WHEN 'BRAND' THEN 3
                        WHEN 'LABEL' THEN 3
                        WHEN 'GLOBAL' THEN 4
                    END,
                    priority DESC
                LIMIT 1""",
                tuple(params)
            )
            stopping_price = cursor.fetchone()
            
            if stopping_price:
                logger.info(f"Selected stopping price: type={stopping_price.get('of_type')}, price={stopping_price.get('price')}")
                return round_money(Decimal(str(stopping_price['price'])))
            
            # If no stopping price, get highest priority price
            cursor.execute(
                f"""SELECT price, of_type, priority, target_id
                FROM {db_settings.MSG_PRODUCT_PRICES_TABLE}
                WHERE {where_clause}
                ORDER BY 
                    CASE of_type
                        WHEN 'SKU' THEN 1
                        WHEN 'LOCATION' THEN 2
                        WHEN 'TAG' THEN 3
                        WHEN 'CATEGORY' THEN 3
                        WHEN 'BRAND' THEN 3
                        WHEN 'LABEL' THEN 3
                        WHEN 'GLOBAL' THEN 4
                    END,
                    priority DESC
                LIMIT 1""",
                tuple(params)
            )
            price = cursor.fetchone()
            
            if price:
                logger.info(f"Selected price: type={price.get('of_type')}, price={price.get('price')}")
                return round_money(Decimal(str(price['price'])))
            
            # Fallback to base_selling_price from latest batch
            logger.debug(f"No price found in msg_product_prices. Falling back to base_selling_price.")
            return ProductPriceCalculator.get_base_selling_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )
            
        except Exception as e:
            logger.error(f"Error getting actual price: {str(e)}", exc_info=True)
            return ProductPriceCalculator.get_base_selling_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )

    @staticmethod
    def apply_pricing_rules(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        base_price: Decimal,
        quantity: int = 1,
        location_id: Optional[str] = None,
        sku: Optional[str] = None,
        product_metadata: Optional[Dict[str, str]] = None,
        current_datetime: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Apply pricing rules to base price (NO TAX CONDITIONS, NO QUANTITY-BASED RULES).
        
        Rules are evaluated in priority order (highest first).
        If a rule has stops_other_rules = TRUE, no further rules are applied.
        
        NOTE: Quantity-based pricing rules are SKIPPED in this calculator.
        They are only applied in SalesPriceCalculator during checkout.
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            base_price: Base price to apply rules to
            quantity: Quantity (not used for filtering, quantity-based rules are skipped)
            location_id: Optional location ID
            sku: Optional SKU
            product_metadata: Optional dict with metadata IDs
            current_datetime: Current datetime for time-based rule validation
            
        Returns:
            Dict with:
            - price: Price after applying pricing rules
            - pricing_rule_applied: Details of the rule applied
        """
        try:
            if current_datetime is None:
                current_datetime = datetime.now()
            
            rule_conditions = [
                "tenant_id = %s",
                "org_id = %s",
                "bus_id = %s",
                "is_active = TRUE",
                "(start_datetime IS NULL OR start_datetime <= %s)",
                "(end_datetime IS NULL OR end_datetime >= %s)",
                "rule_category != 'QUANTITY_BASED'"  # Skip quantity-based rules in product price calculator
            ]
            params = [tenant_id, org_id, bus_id, current_datetime, current_datetime]
            
            target_conditions = ["rule_target_type = 'ALL_PRODUCTS'"]
            
            if product_id:
                target_conditions.append("(rule_target_type = 'PRODUCT' AND rule_target_id = %s)")
                params.append(product_id)
            
            if sku:
                target_conditions.append("(rule_target_type = 'SKU' AND rule_target_id = %s)")
                params.append(sku)
            
            if location_id:
                target_conditions.append("(rule_target_type = 'LOCATION' AND rule_target_id = %s)")
                params.append(location_id)
            
            if product_metadata:
                for meta_type, meta_id in product_metadata.items():
                    if meta_id:
                        type_map = {
                            'category_id': 'CATEGORY',
                            'tag_id': 'TAG',
                            'brand_id': 'BRAND',
                            'label_id': 'LABEL'
                        }
                        if meta_type in type_map:
                            target_conditions.append(
                                f"(rule_target_type = '{type_map[meta_type]}' AND rule_target_id = %s)"
                            )
                            params.append(meta_id)
            
            rule_conditions.append(f"({' OR '.join(target_conditions)})")
            where_clause = " AND ".join(rule_conditions)
            
            # Order by specificity first, then priority within same specificity level
            # Specificity: SKU (1) > PRODUCT (2) > TAG (3) > LABEL (3) > CATEGORY (3) > BRAND (3) > LOCATION (4) > ALL_PRODUCTS (5)
            # Within the same specificity level, higher priority wins
            # Only the single most specific, highest priority rule is applied
            cursor.execute(
                f"""SELECT id, name, rule_type, rule_category, rule_target_type, rule_target_id,
                       discount_value, discount_percent,
                       quantity_min, quantity_max, free_qty, stops_other_rules, priority
                FROM {db_settings.MSG_PRICING_RULES_TABLE}
                WHERE {where_clause}
                ORDER BY
                    CASE rule_target_type
                        WHEN 'SKU' THEN 1
                        WHEN 'PRODUCT' THEN 2
                        WHEN 'TAG' THEN 3
                        WHEN 'LABEL' THEN 3
                        WHEN 'CATEGORY' THEN 3
                        WHEN 'BRAND' THEN 3
                        WHEN 'LOCATION' THEN 4
                        WHEN 'ALL_PRODUCTS' THEN 5
                    END,
                    priority DESC,
                    cdatetime DESC
                LIMIT 1""",
                tuple(params)
            )
            rule = cursor.fetchone()

            no_rule_result = {
                'rule_id': None,
                'rule_name': None,
                'rule_type': None,
                'rule_category': None,
                'rule_target_type': None,
                'rule_target_id': None,
                'price_before': None,
                'price_after': None,
                'adjustment': None,
                'priority': None
            }

            if not rule:
                return {
                    'price': round_money(base_price),
                    'pricing_rule_applied': no_rule_result
                }

            # Skip quantity-based rules (they are only applied in SalesPriceCalculator)
            if rule['rule_category'] == 'QUANTITY_BASED':
                return {
                    'price': round_money(base_price),
                    'pricing_rule_applied': no_rule_result
                }

            # Apply the single selected rule
            result_price = base_price
            rule_type = rule['rule_type']

            if rule_type == 'FIXED_PRICE':
                result_price = max(Decimal('0'), Decimal(str(rule['discount_value'])))

            elif rule_type == 'FIXED_AMOUNT':
                # Set price to a fixed amount (not subtract)
                result_price = max(Decimal('0'), Decimal(str(rule['discount_value'])))

            elif rule_type == 'PRICE_DISCOUNT':
                discount = Decimal(str(rule['discount_value']))
                result_price = max(Decimal('0'), result_price - discount)

            elif rule_type == 'PERCENTAGE_DISCOUNT':
                discount_percent = Decimal(str(rule['discount_percent']))
                discount_amount = (result_price * discount_percent) / Decimal('100')
                result_price = max(Decimal('0'), result_price - discount_amount)

            elif rule_type == 'PRICE_MARKUP':
                markup = Decimal(str(rule['discount_value']))
                result_price = result_price + markup

            elif rule_type == 'PERCENTAGE_MARKUP':
                markup_percent = Decimal(str(rule['discount_percent']))
                markup_amount = (result_price * markup_percent) / Decimal('100')
                result_price = result_price + markup_amount

            primary_rule_applied = {
                'rule_id': rule.get('id'),
                'rule_name': rule.get('name'),
                'rule_type': rule_type,
                'rule_category': rule.get('rule_category'),
                'rule_target_type': rule.get('rule_target_type'),
                'rule_target_id': rule.get('rule_target_id'),
                'price_before': float(round_money(base_price)),
                'price_after': float(round_money(result_price)),
                'adjustment': float(round_money(result_price - base_price)),
                'priority': rule.get('priority', 0)
            }

            # Round only at the end after all calculations
            return {
                'price': round_money(result_price),
                'pricing_rule_applied': primary_rule_applied
            }
            
        except Exception as e:
            logger.error(
                f"Error applying pricing rules for product {product_id}: {str(e)}. "
                f"Returning original price {base_price} without pricing rule applied.",
                exc_info=True
            )
            return {
                'price': base_price,
                'pricing_rule_applied': {
                    'rule_id': None,
                    'rule_name': None,
                    'rule_type': None,
                    'rule_category': None,
                    'rule_target_type': None,
                    'rule_target_id': None,
                    'price_before': None,
                    'price_after': None,
                    'adjustment': None,
                    'priority': None
                },
                'error': f"Pricing rule error: {str(e)}"
            }

    @staticmethod
    def apply_tax_rules(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        base_price: Decimal,
        quantity: int = 1,
        item_price: Optional[Decimal] = None,
        location_id: Optional[str] = None,
        sku: Optional[str] = None,
        product_metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Apply tax rules to price (SIMPLE - NO CONDITIONS).
        
        This is a simple tax calculation for products display.
        It applies taxes directly without evaluating conditions.
        For tax conditions, use SalesPriceCalculator.apply_tax_rules.
        
        Returns a dict with:
        - final_price: Price after tax
        - tax_amount: Total tax amount
        - taxes_applied: List of taxes applied
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            base_price: Price before tax
            quantity: Quantity (not used, kept for compatibility)
            item_price: Item price (not used, kept for compatibility)
            location_id: Optional location ID
            sku: Optional SKU
            product_metadata: Optional dict with metadata IDs
            
        Returns:
            Dict with final_price, tax_amount, and taxes_applied
        """
        try:
            # Get applicable tax rules
            rule_conditions = [
                "r.tenant_id = %s",
                "r.org_id = %s",
                "r.bus_id = %s",
                "r.is_active = TRUE",
                "t.is_active = TRUE"
            ]
            params = [tenant_id, org_id, bus_id]
            
            # Build target matching conditions
            target_conditions = ["r.rule_type = 'ALL_PRODUCTS'"]
            
            if product_id:
                target_conditions.append("(r.rule_type = 'PRODUCT' AND r.rule_target_id = %s)")
                params.append(product_id)
            
            if sku:
                target_conditions.append("(r.rule_type = 'SKU' AND r.rule_target_id = %s)")
                params.append(sku)
            
            if location_id:
                target_conditions.append("(r.rule_type = 'LOCATION' AND r.rule_target_id = %s)")
                params.append(location_id)
            
            if product_metadata:
                for meta_type, meta_id in product_metadata.items():
                    if meta_id:
                        type_map = {
                            'category_id': 'CATEGORY',
                            'tag_id': 'TAG',
                            'brand_id': 'BRAND',
                            'label_id': 'LABEL'
                        }
                        if meta_type in type_map:
                            target_conditions.append(
                                f"(r.rule_type = '{type_map[meta_type]}' AND r.rule_target_id = %s)"
                            )
                            params.append(meta_id)
            
            rule_conditions.append(f"({' OR '.join(target_conditions)})")
            where_clause = " AND ".join(rule_conditions)
            
            # Get applicable tax rules with tax details (NO CONDITIONS CHECK)
            cursor.execute(
                f"""SELECT r.id as tax_rule_id, r.name as tax_rule_name, r.rule_type, r.rule_target_id, r.priority,
                       r.tax_id, t.rate, t.is_inclusive, t.name as tax_name
                FROM {db_settings.MSG_TAX_RULES_TABLE} r
                INNER JOIN {db_settings.MSG_TAXES_TABLE} t 
                    ON r.tax_id = t.id 
                    AND r.tenant_id = t.tenant_id 
                    AND r.org_id = t.org_id 
                    AND r.bus_id = t.bus_id
                WHERE {where_clause}
                ORDER BY r.priority DESC""",
                tuple(params)
            )
            tax_rules = cursor.fetchall()
            
            if not tax_rules:
                return {
                    'final_price': round_money(base_price),
                    'tax_amount': Decimal('0'),
                    'taxes_applied': [],
                    'tax_rule_applied': {
                        'tax_rule_id': None,
                        'tax_rule_name': None,
                        'tax_rule_type': None,
                        'tax_rule_target_id': None,
                        'tax_id': None,
                        'tax_name': None,
                        'rate': None,
                        'is_inclusive': None,
                        'tax_amount': None,
                        'priority': None
                    }
                }
            
            total_tax_amount = Decimal('0')
            taxes_applied = []
            tax_rules_applied = []
            # Keep full precision during calculations - round only at the end
            current_price = base_price

            # First pass: compute combined inclusive rate for correct extraction
            combined_inclusive_rate = Decimal('0')
            for rule in tax_rules:
                if rule.get('is_inclusive', False):
                    combined_inclusive_rate += Decimal(str(rule['rate']))

            # Pre-tax base for inclusive taxes (extract all inclusive taxes together)
            if combined_inclusive_rate > Decimal('0'):
                pre_tax_base = base_price / (Decimal('1') + (combined_inclusive_rate / Decimal('100')))
            else:
                pre_tax_base = base_price

            # Second pass: calculate individual tax amounts
            for rule in tax_rules:
                tax_rule_id = rule.get('tax_rule_id')
                tax_rule_name = rule.get('tax_rule_name')
                tax_rule_type = rule.get('rule_type')
                tax_rule_target_id = rule.get('rule_target_id')
                tax_id = rule['tax_id']
                tax_rate = Decimal(str(rule['rate']))
                is_inclusive = rule.get('is_inclusive', False)
                tax_name = rule.get('tax_name', 'Unknown Tax')

                # Inclusive taxes: calculate on pre_tax_base (extract from shelf price)
                # Exclusive taxes: calculate on base_price (the shelf price customers see)
                if is_inclusive:
                    tax_amount = (pre_tax_base * tax_rate) / Decimal('100')
                else:
                    tax_amount = (base_price * tax_rate) / Decimal('100')

                # Keep full precision during calculation
                tax_amount = max(Decimal('0'), tax_amount)
                total_tax_amount += tax_amount

                # Track ALL applied tax rules (not just the first)
                if tax_amount > 0:
                    tax_rules_applied.append({
                        'tax_rule_id': tax_rule_id,
                        'tax_rule_name': tax_rule_name,
                        'tax_rule_type': tax_rule_type,
                        'tax_rule_target_id': tax_rule_target_id,
                        'tax_id': tax_id,
                        'tax_name': tax_name,
                        'rate': float(tax_rate),
                        'is_inclusive': is_inclusive,
                        'tax_amount': float(round_money(tax_amount)),
                        'priority': rule.get('priority', 0)
                    })

                taxes_applied.append({
                    'tax_id': tax_id,
                    'tax_name': tax_name,
                    'rate': float(tax_rate),
                    'is_inclusive': is_inclusive,
                    'amount': float(round_money(tax_amount))  # Round only for display
                })

                # Add tax to current price with full precision (no rounding yet)
                if not is_inclusive:
                    current_price = current_price + tax_amount

            # Round only at the end after all tax calculations
            final_price = round_money(max(Decimal('0'), current_price))

            # Return the first applied rule as primary for backward compatibility,
            # plus all applied rules in tax_rules_applied list
            primary_tax_rule_applied = tax_rules_applied[0] if tax_rules_applied else {
                'tax_rule_id': None,
                'tax_rule_name': None,
                'tax_rule_type': None,
                'tax_rule_target_id': None,
                'tax_id': None,
                'tax_name': None,
                'rate': None,
                'is_inclusive': None,
                'tax_amount': None,
                'priority': None
            }

            return {
                'final_price': final_price,
                'tax_amount': round_money(total_tax_amount),
                'taxes_applied': taxes_applied,
                'tax_rule_applied': primary_tax_rule_applied,
                'tax_rules_applied': tax_rules_applied,
            }
            
        except Exception as e:
            logger.error(
                f"Error applying tax rules for product {product_id}: {str(e)}. "
                f"Returning price {base_price} without tax applied.",
                exc_info=True
            )
            return {
                'final_price': round_money(base_price),
                'tax_amount': Decimal('0'),
                'taxes_applied': [],
                'tax_rule_applied': {
                    'tax_rule_id': None,
                    'tax_rule_name': None,
                    'tax_rule_type': None,
                    'tax_rule_target_id': None,
                    'tax_id': None,
                    'tax_name': None,
                    'rate': None,
                    'is_inclusive': None,
                    'tax_amount': None,
                    'priority': None
                },
                'tax_rules_applied': [],
                'error': f"Tax rule error: {str(e)}"
            }

    @staticmethod
    def calculate_product_prices(
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
        Calculate prices for store/warehouse products (SIMPLE TAX - NO CONDITIONS).
        
        This calculator applies tax rules WITHOUT conditions (simple tax calculation).
        For tax conditions, use SalesPriceCalculator.calculate_sale_prices.
        
        Returns:
            Dict with:
            - cost_price: Cost price
            - base_selling_price: Base selling price
            - actual_price: Actual price from msg_product_prices
            - price_after_pricing_rule: Price after pricing rules
            - price_after_tax: Price after tax (simple calculation, no conditions)
            - final_price: Final price after tax
            - tax_amount: Total tax amount
            - taxes_applied: List of taxes applied
            - pricing_rule_applied: Details of pricing rule applied
            - tax_rule_applied: Details of tax rule applied
        """
        try:
            # 1. Get Cost Price
            cost_price = ProductPriceCalculator.get_cost_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )
            
            # 2. Get Base Selling Price
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
            
            # 4. Apply Pricing Rules (NO TAX)
            pricing_result = ProductPriceCalculator.apply_pricing_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                actual_price, quantity, location_id, sku, product_metadata, current_datetime
            )
            
            price_after_pricing_rule = pricing_result['price'] if isinstance(pricing_result, dict) else pricing_result
            pricing_rule_applied = pricing_result.get('pricing_rule_applied') if isinstance(pricing_result, dict) else None
            
            if price_after_pricing_rule is not None:
                price_after_pricing_rule = round_money(max(Decimal('0'), price_after_pricing_rule))
            
            # 5. Apply Tax Rules (SIMPLE - NO CONDITIONS)
            tax_result = ProductPriceCalculator.apply_tax_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                price_after_pricing_rule, quantity, price_after_pricing_rule,
                location_id, sku, product_metadata
            )
            
            # Final price is the price after tax
            final_price = tax_result['final_price'] if tax_result['final_price'] is not None else None
            if final_price is not None:
                final_price = round_money(max(Decimal('0'), final_price))
            
            price_after_tax = tax_result['final_price'] if tax_result['final_price'] is not None else None
            if price_after_tax is not None:
                price_after_tax = round_money(max(Decimal('0'), price_after_tax))
            
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
                'taxes_applied': tax_result['taxes_applied'],
                'pricing_rule_applied': pricing_rule_applied,
                'tax_rule_applied': tax_result.get('tax_rule_applied'),
                'tax_rules_applied': tax_result.get('tax_rules_applied', []),
            }
            
        except Exception as e:
            logger.error(
                f"Error calculating product prices for product {product_id}: {str(e)}. "
                f"Returning empty price result.",
                exc_info=True
            )
            return {
                'cost_price': None,
                'base_selling_price': None,
                'actual_price': None,
                'price_after_pricing_rule': None,
                'price_after_tax': None,
                'tax_amount': None,
                'final_price': None,
                'taxes_applied': [],
                'pricing_rule_applied': None,
                'tax_rule_applied': None,
                'tax_rules_applied': [],
                'error': f"Price calculation error: {str(e)}"
            }

