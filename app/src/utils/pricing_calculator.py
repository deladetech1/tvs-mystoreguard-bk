"""
Pricing Calculator Utility

This module provides functions to calculate various price values for products:
1. Cost Price - from product or purchase batch
2. Base Selling Price - from product
3. Actual Price - from msg_product_prices table (with priority logic)
4. Price After Pricing Rule - after applying pricing rules
5. Price After Tax - after applying tax rules
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.configs.database import DatabaseManager
from src.configs.settings import db_settings
from src.configs.logging import get_logger

logger = get_logger("pricing_calculator")


def round_money(value: Optional[Decimal]) -> Optional[Decimal]:
    """Round money value to 2 decimal places"""
    if value is None:
        return None
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class PricingCalculator:
    """Utility class for calculating product prices"""

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
        2. Otherwise, get from product (if available)
        
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
                # Get cost price from specific batch
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
            
            # Get cost price from latest batch (sorted by cdatetime DESC)
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
                # Get base_selling_price from specific batch
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
            
            # Get base_selling_price from latest batch (sorted by cdatetime DESC)
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
            # Build query to get applicable prices
            # Priority: SKU > LOCATION > TAG/CATEGORY/BRAND/LABEL > GLOBAL
            # Also consider stops_other_prices flag
            
            logger.debug(f"Getting actual price for product_id={product_id}, location_id={location_id}, sku={sku}, metadata={product_metadata}")
            
            # First, try to find a price with stops_other_prices = TRUE
            price_conditions = [
                "product_id = %s",
                "tenant_id = %s",
                "org_id = %s",
                "bus_id = %s",
                "(deleted_by IS NULL OR deleted_by = '')"  # Only get non-deleted prices
            ]
            params = [product_id, tenant_id, org_id, bus_id]
            
            # Build conditions for all applicable price types
            # Priority order: Type priority (SKU=1, LOCATION=2, TAG/CATEGORY/BRAND/LABEL=3, GLOBAL=4) 
            #                 THEN numeric priority (DESC)
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
                        # Map metadata keys to of_type values
                        type_map = {
                            'category_id': 'CATEGORY',
                            'tag_id': 'TAG',
                            'brand_id': 'BRAND',
                            'label_id': 'LABEL'
                        }
                        if meta_type in type_map:
                            type_conditions.append(f"(of_type = '{type_map[meta_type]}' AND target_id = %s)")
                            params.append(meta_id)
            
            # Always include GLOBAL prices as fallback
            type_conditions.append("of_type = 'GLOBAL'")
            
            if type_conditions:
                price_conditions.append(f"({' OR '.join(type_conditions)})")
            
            where_clause = " AND ".join(price_conditions)
            logger.debug(f"Price query WHERE clause: {where_clause}")
            logger.debug(f"Price query params: {params}")
            
            # Debug: Check all matching prices
            cursor.execute(
                f"""SELECT price, of_type, target_id, priority, stops_other_prices
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
                    priority DESC""",
                tuple(params)
            )
            all_matching_prices = cursor.fetchall()
            logger.debug(f"Found {len(all_matching_prices)} matching prices: {[dict(p) for p in all_matching_prices]}")
            
            # First check for prices with stops_other_prices = TRUE
            # Order by type priority first, then by numeric priority
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
                logger.info(f"Selected stopping price from msg_product_prices: type={stopping_price.get('of_type')}, target_id={stopping_price.get('target_id')}, priority={stopping_price.get('priority')}, price={stopping_price.get('price')}, product_id={product_id}, location_id={location_id}")
                return round_money(Decimal(str(stopping_price['price'])))
            
            # If no stopping price, get highest priority price
            # Order by type priority first, then by numeric priority
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
                logger.info(f"Selected price from msg_product_prices: type={price.get('of_type')}, target_id={price.get('target_id')}, priority={price.get('priority')}, price={price.get('price')}, product_id={product_id}, location_id={location_id}")
                return round_money(Decimal(str(price['price'])))
            
            # If no price found in msg_product_prices, return base_selling_price from latest batch
            logger.debug(f"No price found in msg_product_prices for product_id={product_id}, location_id={location_id}. Falling back to base_selling_price.")
            return PricingCalculator.get_base_selling_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )
            
        except Exception as e:
            logger.error(f"Error getting actual price: {str(e)}", exc_info=True)
            # Fallback to base selling price from latest batch
            return PricingCalculator.get_base_selling_price(
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
        Apply pricing rules to base price.
        
        Rules are evaluated in priority order (highest first).
        If a rule has stops_other_rules = TRUE, no further rules are applied.
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            base_price: Base price to apply rules to
            quantity: Quantity (for quantity-based rules)
            location_id: Optional location ID
            sku: Optional SKU
            product_metadata: Optional dict with metadata IDs
            current_datetime: Current datetime for time-based rule validation
            
        Returns:
            Dict with:
            - price: Price after applying pricing rules
            - rules_applied: List of pricing rules that were applied
        """
        try:
            if current_datetime is None:
                current_datetime = datetime.now()
            
            # Build conditions to find applicable rules
            rule_conditions = [
                "tenant_id = %s",
                "org_id = %s",
                "bus_id = %s",
                "is_active = TRUE",
                "(start_datetime IS NULL OR start_datetime <= %s)",
                "(end_datetime IS NULL OR end_datetime >= %s)"
            ]
            params = [tenant_id, org_id, bus_id, current_datetime, current_datetime]
            
            # Build target matching conditions
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
            
            # Get applicable rules ordered by priority
            cursor.execute(
                f"""SELECT id, name, rule_type, rule_category, rule_target_type, rule_target_id,
                       discount_value, discount_percent,
                       quantity_min, quantity_max, free_qty, stops_other_rules, priority
                FROM {db_settings.MSG_PRICING_RULES_TABLE}
                WHERE {where_clause}
                ORDER BY priority DESC, cdatetime DESC""",
                tuple(params)
            )
            rules = cursor.fetchall()
            
            if not rules:
                return {
                    'price': round_money(base_price),
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
                    }
                }
            
            # Keep full precision during calculations - round only at the end
            result_price = base_price
            primary_rule_applied = None
            
            for rule in rules:
                # Check quantity constraints for QUANTITY_BASED rules
                if rule['rule_category'] == 'QUANTITY_BASED':
                    qty_min = rule.get('quantity_min')
                    qty_max = rule.get('quantity_max')
                    
                    if qty_min is not None and quantity < qty_min:
                        continue
                    if qty_max is not None and quantity > qty_max:
                        continue
                
                # Apply rule based on rule_type
                rule_type = rule['rule_type']
                rule_id = rule.get('id')
                rule_name = rule.get('name')
                rule_category = rule.get('rule_category')
                rule_target_type = rule.get('rule_target_type')
                rule_target_id = rule.get('rule_target_id')
                price_before_rule = result_price
                
                if rule_type == 'FIXED_PRICE':
                    # FIXED_PRICE sets the price to a fixed value
                    result_price = max(Decimal('0'), Decimal(str(rule['discount_value'])))
                
                elif rule_type == 'FIXED_AMOUNT':
                    # FIXED_AMOUNT subtracts a fixed amount from the price
                    discount = Decimal(str(rule['discount_value']))
                    result_price = max(Decimal('0'), result_price - discount)
                
                elif rule_type == 'PRICE_DISCOUNT':
                    # PRICE_DISCOUNT also subtracts a fixed amount (same as FIXED_AMOUNT)
                    discount = Decimal(str(rule['discount_value']))
                    result_price = max(Decimal('0'), result_price - discount)
                
                elif rule_type == 'PERCENTAGE_DISCOUNT':
                    # Use full precision for percentage calculations
                    discount_percent = Decimal(str(rule['discount_percent']))
                    discount_amount = (result_price * discount_percent) / Decimal('100')
                    result_price = max(Decimal('0'), result_price - discount_amount)
                
                elif rule_type == 'PRICE_MARKUP':
                    markup = Decimal(str(rule['discount_value']))
                    result_price = result_price + markup
                
                elif rule_type == 'PERCENTAGE_MARKUP':
                    # Use full precision for percentage calculations
                    markup_percent = Decimal(str(rule['discount_percent']))
                    markup_amount = (result_price * markup_percent) / Decimal('100')
                    result_price = result_price + markup_amount
                
                elif rule_type == 'QUANTITY_BREAK':
                    # QUANTITY_BREAK: Apply price adjustment when quantity falls within the range
                    # Can use either discount_value (fixed amount) or discount_percent (percentage)
                    if rule.get('discount_value') is not None:
                        # Fixed amount discount/markup
                        discount = Decimal(str(rule['discount_value']))
                        result_price = max(Decimal('0'), result_price - discount)
                    elif rule.get('discount_percent') is not None:
                        # Percentage discount/markup - use full precision
                        discount_percent = Decimal(str(rule['discount_percent']))
                        discount_amount = (result_price * discount_percent) / Decimal('100')
                        result_price = max(Decimal('0'), result_price - discount_amount)
                    # If neither discount_value nor discount_percent is provided, skip this rule
                    else:
                        continue
                
                elif rule_type in ['BUNDLE', 'BOGO']:
                    # These are more complex and might affect quantity rather than unit price
                    # For now, we'll skip them in price calculation
                    # You may need to handle these differently based on your business logic
                    continue
                
                # Track the first rule that actually changed the price (use rounded values for comparison)
                if round_money(price_before_rule) != round_money(result_price) and primary_rule_applied is None:
                    primary_rule_applied = {
                        'rule_id': rule_id,
                        'rule_name': rule_name,
                        'rule_type': rule_type,
                        'rule_category': rule_category,
                        'rule_target_type': rule_target_type,
                        'rule_target_id': rule_target_id,
                        'price_before': float(round_money(price_before_rule)),
                        'price_after': float(round_money(result_price)),
                        'adjustment': float(round_money(result_price - price_before_rule)),
                        'priority': rule.get('priority', 0)
                    }
                
                # If this rule stops other rules, break
                if rule.get('stops_other_rules'):
                    break
            
            # If no rule was applied, return default structure
            if primary_rule_applied is None:
                primary_rule_applied = {
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
            
            # Round only at the end after all calculations
            return {
                'price': round_money(result_price),
                'pricing_rule_applied': primary_rule_applied
            }
            
        except Exception as e:
            logger.error(f"Error applying pricing rules: {str(e)}", exc_info=True)
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
                }
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
        Apply tax rules to price.
        
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
            quantity: Quantity (for tax rule conditions)
            item_price: Item price (for tax rule conditions)
            location_id: Optional location ID
            sku: Optional SKU
            product_metadata: Optional dict with metadata IDs
            
        Returns:
            Dict with final_price, tax_amount, and taxes_applied
        """
        try:
            if item_price is None:
                item_price = base_price
            
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
            
            # Get applicable tax rules with tax details
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
            primary_tax_rule_applied = None
            # Keep full precision during calculations - round only at the end
            current_price = base_price
            
            for rule in tax_rules:
                tax_rule_id = rule.get('tax_rule_id')
                tax_rule_name = rule.get('tax_rule_name')
                tax_rule_type = rule.get('rule_type')
                tax_rule_target_id = rule.get('rule_target_id')
                tax_id = rule['tax_id']
                tax_rate = Decimal(str(rule['rate']))
                is_inclusive = rule.get('is_inclusive', False)
                tax_name = rule.get('tax_name', 'Unknown Tax')
                
                # Get tax rule conditions
                cursor.execute(
                    f"""SELECT condition_type, condition, comparison_operator, 
                           comparison_value, adjustment_value, adjustment_percentage,
                           logical_operator, priority
                    FROM {db_settings.MSG_TAX_RULE_CONDITIONS_TABLE}
                    WHERE tax_rule_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    ORDER BY priority ASC""",
                    (rule['tax_rule_id'], tenant_id, org_id, bus_id)
                )
                conditions = cursor.fetchall()
                
                # Evaluate conditions
                should_apply_tax = True
                tax_reduction = Decimal('0')
                
                if conditions:
                    # Evaluate all conditions
                    condition_results = []
                    
                    for condition in conditions:
                        condition_type = condition['condition_type']
                        condition_field = condition['condition']
                        operator = condition['comparison_operator']
                        comparison_value = Decimal(str(condition['comparison_value']))
                        
                        # Get value to compare
                        if condition_field == 'IF_ITEM_PRICE':
                            compare_value = item_price
                        elif condition_field == 'IF_TOTAL_PRICE':
                            compare_value = base_price * quantity
                        elif condition_field == 'IF_ITEM_QTY':
                            compare_value = Decimal(str(quantity))
                        else:
                            compare_value = None
                        
                        if compare_value is None:
                            continue
                        
                        # Evaluate comparison
                        condition_met = False
                        if operator == 'EQUALS':
                            condition_met = (compare_value == comparison_value)
                        elif operator == 'NOT_EQUALS':
                            condition_met = (compare_value != comparison_value)
                        elif operator == 'GREATER_THAN':
                            condition_met = (compare_value > comparison_value)
                        elif operator == 'LESS_THAN':
                            condition_met = (compare_value < comparison_value)
                        elif operator == 'GREATER_THAN_OR_EQUALS':
                            condition_met = (compare_value >= comparison_value)
                        elif operator == 'LESS_THAN_OR_EQUALS':
                            condition_met = (compare_value <= comparison_value)
                        
                        condition_results.append({
                            'met': condition_met,
                            'type': condition_type,
                            'logical_operator': condition.get('logical_operator', 'AND'),
                            'adjustment_value': condition.get('adjustment_value'),
                            'adjustment_percentage': condition.get('adjustment_percentage')
                        })
                    
                    # Evaluate logical operators
                    if condition_results:
                        final_result = condition_results[0]['met']
                        for i in range(1, len(condition_results)):
                            prev_result = condition_results[i-1]
                            curr_result = condition_results[i]
                            
                            if prev_result['logical_operator'] == 'AND':
                                final_result = final_result and curr_result['met']
                            else:  # OR
                                final_result = final_result or curr_result['met']
                        
                        if not final_result:
                            should_apply_tax = False
                        
                        # Calculate tax reduction if conditions met
                        if final_result:
                            for cond in condition_results:
                                if cond['type'] == 'TAX_REDUCTION':
                                    if cond.get('adjustment_value'):
                                        tax_reduction += Decimal(str(cond['adjustment_value']))
                                    elif cond.get('adjustment_percentage'):
                                        reduction_percent = Decimal(str(cond['adjustment_percentage']))
                                        tax_reduction += (tax_rate * reduction_percent) / Decimal('100')
                                elif cond['type'] == 'TAX_EXEMPTION':
                                    if cond['met']:
                                        should_apply_tax = False
                                        break
                
                if not should_apply_tax:
                    continue
                
                # Calculate tax amount with full precision (no rounding yet)
                if is_inclusive:
                    # Tax is already included in price
                    # Extract tax: tax_amount = price - (price / (1 + rate/100))
                    tax_amount = current_price - (current_price / (Decimal('1') + (tax_rate / Decimal('100'))))
                else:
                    # Tax is added to price - use current_price with full precision
                    tax_amount = (current_price * tax_rate) / Decimal('100')
                
                # Apply reduction (keep full precision)
                tax_amount = max(Decimal('0'), tax_amount - tax_reduction)
                
                # Accumulate tax with full precision
                total_tax_amount += tax_amount
                
                # Track the first tax rule that was actually applied (round only for display)
                if primary_tax_rule_applied is None and tax_amount > 0:
                    primary_tax_rule_applied = {
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
                    }
                
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
            
            # If no tax rule was applied, return default structure
            if primary_tax_rule_applied is None:
                primary_tax_rule_applied = {
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
                'tax_rule_applied': primary_tax_rule_applied
            }
            
        except Exception as e:
            logger.error(f"Error applying tax rules: {str(e)}", exc_info=True)
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
                # Get currency from specific batch
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
            
            # Get currency from latest batch (sorted by cdatetime DESC)
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
        """
        try:
            # 1. Get Cost Price
            cost_price = PricingCalculator.get_cost_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )
            
            # 2. Get Base Selling Price (from latest batch)
            base_selling_price = PricingCalculator.get_base_selling_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )
            
            # 3. Get Actual Price
            actual_price = PricingCalculator.get_actual_price(
                cursor, product_id, tenant_id, org_id, bus_id,
                location_id, sku, product_metadata, batch_id
            )
            
            if actual_price is None:
                actual_price = base_selling_price or Decimal('0')
            
            # 4. Apply Pricing Rules
            pricing_result = PricingCalculator.apply_pricing_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                actual_price, quantity, location_id, sku, product_metadata, current_datetime
            )
            
            price_after_pricing_rule = pricing_result['price'] if isinstance(pricing_result, dict) else pricing_result
            pricing_rule_applied = pricing_result.get('pricing_rule_applied') if isinstance(pricing_result, dict) else None
            
            # Ensure price_after_pricing_rule is not negative and rounded
            if price_after_pricing_rule is not None:
                price_after_pricing_rule = round_money(max(Decimal('0'), price_after_pricing_rule))
            
            # 5. Apply Tax Rules
            tax_result = PricingCalculator.apply_tax_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                price_after_pricing_rule, quantity, price_after_pricing_rule,
                location_id, sku, product_metadata
            )
            
            # Final price is the price after tax (the ultimate final price)
            # Ensure it's never negative and rounded
            final_price = tax_result['final_price'] if tax_result['final_price'] is not None else None
            if final_price is not None:
                final_price = round_money(max(Decimal('0'), final_price))
            
            # Ensure price_after_tax is also not negative and rounded
            price_after_tax = tax_result['final_price'] if tax_result['final_price'] is not None else None
            if price_after_tax is not None:
                price_after_tax = round_money(max(Decimal('0'), price_after_tax))
            
            # Get currency information from latest batch
            currency_info = PricingCalculator.get_currency_info(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )
            
            # Helper function to convert Decimal to float with 2 decimal places
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

