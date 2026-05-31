"""
Sales Price Calculator Utility

This module provides a full-featured price calculator for sales/checkout operations.
It includes ALL pricing logic including tax conditions and is used during:
- Checkout/verification
- Sale creation
- Price verification

This calculator includes:
1. Cost Price - from product or purchase batch
2. Base Selling Price - from product
3. Actual Price - from msg_product_prices table (with priority logic)
4. Price After Pricing Rule - after applying pricing rules
5. Price After Tax - after applying tax rules WITH CONDITIONS
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.configs.settings import db_settings
from src.configs.logging import get_logger
from src.utils.product_price_calculator import ProductPriceCalculator, round_money

logger = get_logger("sales_price_calculator")


class SalesPriceCalculator:
    """Full-featured price calculator for sales/checkout (WITH TAX CONDITIONS)"""

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
        Apply pricing rules to base price INCLUDING QUANTITY-BASED RULES.
        
        This method is used for sales/checkout where quantity matters.
        It includes all pricing rules including QUANTITY_BASED and QUANTITY_BREAK.
        
        Rules are evaluated in priority order (highest first).
        If a rule has stops_other_rules = TRUE, no further rules are applied.
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            base_price: Base price to apply rules to
            quantity: Quantity being purchased (used for quantity-based rules)
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
                "(end_datetime IS NULL OR end_datetime >= %s)"
                # NOTE: We DO NOT exclude QUANTITY_BASED rules here - they are included for sales
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
                    cdatetime DESC""",
                tuple(params)
            )
            rules = cursor.fetchall()

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

            if not rules:
                return {
                    'price': round_money(base_price),
                    'pricing_rule_applied': no_rule_result
                }

            # Find the first applicable rule (most specific, highest priority)
            # For QUANTITY_BASED rules, also check quantity constraints
            selected_rule = None
            for rule in rules:
                if rule['rule_category'] == 'QUANTITY_BASED':
                    qty_min = rule.get('quantity_min')
                    qty_max = rule.get('quantity_max')
                    if qty_min is not None and quantity < qty_min:
                        continue
                    if qty_max is not None and quantity > qty_max:
                        continue
                selected_rule = rule
                break

            if not selected_rule:
                return {
                    'price': round_money(base_price),
                    'pricing_rule_applied': no_rule_result
                }

            # Apply the single selected rule
            result_price = base_price
            rule_type = selected_rule['rule_type']

            if rule_type == 'FIXED_PRICE':
                result_price = max(Decimal('0'), Decimal(str(selected_rule['discount_value'])))

            elif rule_type == 'FIXED_AMOUNT':
                # Set price to a fixed amount (not subtract)
                result_price = max(Decimal('0'), Decimal(str(selected_rule['discount_value'])))

            elif rule_type == 'PRICE_DISCOUNT':
                discount = Decimal(str(selected_rule['discount_value']))
                result_price = max(Decimal('0'), result_price - discount)

            elif rule_type == 'PERCENTAGE_DISCOUNT':
                discount_percent = Decimal(str(selected_rule['discount_percent']))
                discount_amount = (result_price * discount_percent) / Decimal('100')
                result_price = max(Decimal('0'), result_price - discount_amount)

            elif rule_type == 'PRICE_MARKUP':
                markup = Decimal(str(selected_rule['discount_value']))
                result_price = result_price + markup

            elif rule_type == 'PERCENTAGE_MARKUP':
                markup_percent = Decimal(str(selected_rule['discount_percent']))
                markup_amount = (result_price * markup_percent) / Decimal('100')
                result_price = result_price + markup_amount

            elif rule_type == 'QUANTITY_BREAK':
                if selected_rule.get('discount_value') is not None:
                    discount = Decimal(str(selected_rule['discount_value']))
                    result_price = max(Decimal('0'), result_price - discount)
                elif selected_rule.get('discount_percent') is not None:
                    discount_percent = Decimal(str(selected_rule['discount_percent']))
                    discount_amount = (result_price * discount_percent) / Decimal('100')
                    result_price = max(Decimal('0'), result_price - discount_amount)

            primary_rule_applied = {
                'rule_id': selected_rule.get('id'),
                'rule_name': selected_rule.get('name'),
                'rule_type': rule_type,
                'rule_category': selected_rule.get('rule_category'),
                'rule_target_type': selected_rule.get('rule_target_type'),
                'rule_target_id': selected_rule.get('rule_target_id'),
                'price_before': float(round_money(base_price)),
                'price_after': float(round_money(result_price)),
                'adjustment': float(round_money(result_price - base_price)),
                'priority': selected_rule.get('priority', 0)
            }
            
            # Round only at the end after all calculations
            return {
                'price': round_money(result_price),
                'pricing_rule_applied': primary_rule_applied
            }
            
        except Exception as e:
            logger.error(
                f"Error applying pricing rules for product {product_id} (qty: {quantity}): {str(e)}. "
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
        Apply tax rules to price WITH CONDITIONS.
        
        This is the full tax calculation used during sales/checkout.
        It evaluates tax conditions based on item price, total price, and quantity.
        
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
            tax_rules_applied = []
            # Keep full precision during calculations - round only at the end
            current_price = base_price

            # First pass: evaluate conditions and collect applicable taxes
            applicable_taxes = []
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
                tax_reduction_pct = Decimal('0')

                if conditions:
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

                    # Evaluate logical operators to decide whether the rule's
                    # conditions FIRE. Conditions only ever RELIEVE tax (exempt
                    # or reduce it); they never gate whether tax is charged in
                    # the first place. So the default is full tax, and we only
                    # touch it when the chained conditions are satisfied — a
                    # condition that is NOT met must leave the normal tax in place.
                    if condition_results:
                        final_result = condition_results[0]['met']
                        for i in range(1, len(condition_results)):
                            prev_result = condition_results[i-1]
                            curr_result = condition_results[i]

                            if prev_result['logical_operator'] == 'AND':
                                final_result = final_result and curr_result['met']
                            else:  # OR
                                final_result = final_result or curr_result['met']

                        # Conditions fire -> grant the relief they describe.
                        # Conditions do not fire -> full tax stays applied.
                        if final_result:
                            for cond in condition_results:
                                # In an OR chain the overall result can be true
                                # while individual conditions are unmet; only act
                                # on the conditions that actually matched.
                                if not cond['met']:
                                    continue
                                if cond['type'] == 'TAX_EXEMPTION':
                                    should_apply_tax = False
                                    break
                                elif cond['type'] == 'TAX_REDUCTION':
                                    if cond.get('adjustment_value'):
                                        tax_reduction += Decimal(str(cond['adjustment_value']))
                                    elif cond.get('adjustment_percentage'):
                                        # Reduce the tax amount by a percentage (e.g., 50% reduction = half the tax)
                                        reduction_percent = Decimal(str(cond['adjustment_percentage']))
                                        tax_reduction_pct += reduction_percent

                if not should_apply_tax:
                    continue

                applicable_taxes.append({
                    'tax_rule_id': tax_rule_id,
                    'tax_rule_name': tax_rule_name,
                    'tax_rule_type': tax_rule_type,
                    'tax_rule_target_id': tax_rule_target_id,
                    'tax_id': tax_id,
                    'tax_rate': tax_rate,
                    'is_inclusive': is_inclusive,
                    'tax_name': tax_name,
                    'tax_reduction': tax_reduction,
                    'tax_reduction_pct': tax_reduction_pct,
                    'priority': rule.get('priority', 0)
                })

            # Compute combined inclusive rate for correct extraction
            combined_inclusive_rate = Decimal('0')
            for tax_info in applicable_taxes:
                if tax_info['is_inclusive']:
                    combined_inclusive_rate += tax_info['tax_rate']

            # Pre-tax base for inclusive taxes (extract all inclusive taxes together)
            if combined_inclusive_rate > Decimal('0'):
                pre_tax_base = base_price / (Decimal('1') + (combined_inclusive_rate / Decimal('100')))
            else:
                pre_tax_base = base_price

            # Second pass: calculate individual tax amounts
            for tax_info in applicable_taxes:
                tax_rate = tax_info['tax_rate']
                is_inclusive = tax_info['is_inclusive']
                tax_reduction = tax_info['tax_reduction']
                tax_reduction_pct = tax_info['tax_reduction_pct']

                # Inclusive taxes: calculate on pre_tax_base (extract from shelf price)
                # Exclusive taxes: calculate on base_price (the shelf price customers see)
                if is_inclusive:
                    tax_amount = (pre_tax_base * tax_rate) / Decimal('100')
                else:
                    tax_amount = (base_price * tax_rate) / Decimal('100')

                # Apply percentage reduction to the tax amount
                if tax_reduction_pct > Decimal('0'):
                    tax_amount = tax_amount * (Decimal('100') - tax_reduction_pct) / Decimal('100')
                # Apply fixed amount reduction
                tax_amount = max(Decimal('0'), tax_amount - tax_reduction)

                # Accumulate tax with full precision
                total_tax_amount += tax_amount

                # Track ALL applied tax rules (not just the first)
                if tax_amount > 0:
                    tax_rules_applied.append({
                        'tax_rule_id': tax_info['tax_rule_id'],
                        'tax_rule_name': tax_info['tax_rule_name'],
                        'tax_rule_type': tax_info['tax_rule_type'],
                        'tax_rule_target_id': tax_info['tax_rule_target_id'],
                        'tax_id': tax_info['tax_id'],
                        'tax_name': tax_info['tax_name'],
                        'rate': float(tax_rate),
                        'is_inclusive': is_inclusive,
                        'tax_amount': float(round_money(tax_amount)),
                        'priority': tax_info['priority']
                    })

                taxes_applied.append({
                    'tax_id': tax_info['tax_id'],
                    'tax_name': tax_info['tax_name'],
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
    def apply_promo_discount_to_item(
        price_after_pricing_rule: Decimal,
        quantity: int,
        discount_type: str,
        discount_value: Decimal,
        max_discount_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Apply promo code discount to an individual item (before tax).
        
        Rules:
        - PERCENTAGE: Applied per unit (each unit gets the percentage discount)
        - FIXED_AMOUNT: Applied once to the line total (not per unit)
        - Unit price after discount = price_after_pricing_rule - discount_per_unit (for PERCENTAGE)
        - Unit price after discount = (line_total - discount) ÷ quantity (for FIXED_AMOUNT)
        - Tax is calculated after discount per unit
        - Discount never exceeds line total (capped if needed)
        - min_purchase_amount is checked in validation before this is called
        
        Example (PERCENTAGE = 5%):
        - Unit Price: 100, Qty: 2
        - Discount per unit: (100 × 5) / 100 = 5
        - Total discount: 5 × 2 = 10
        - Unit Price After Discount: 100 - 5 = 95
        - Final Line Total: 95 × 2 = 190
        
        Example (FIXED_AMOUNT = 50):
        - Unit Price: 76, Qty: 2
        - Line Total: 76 × 2 = 152
        - Discount: 50 (applied once to line total)
        - Final Line Total: 152 - 50 = 102
        - Unit Price After Discount: 102 ÷ 2 = 51
        
        Args:
            price_after_pricing_rule: Price after pricing rules (per unit)
            quantity: Quantity being purchased
            discount_type: Discount type ('PERCENTAGE', 'FIXED_AMOUNT', 'FREE_SHIPPING')
            discount_value: Discount value (percentage or fixed amount)
            max_discount_amount: Maximum discount amount per unit (optional, for percentage discounts)
            
        Returns:
            Dict with:
            - price_after_promo: Price per unit after promo discount
            - promo_discount_amount: Discount amount applied to the line total
        """
        try:
            # Calculate line total (price per unit × quantity)
            line_total = price_after_pricing_rule * Decimal(str(quantity))
            discount_amount = Decimal('0')
            discount_per_unit = Decimal('0')
            
            if discount_type == 'PERCENTAGE':
                # Percentage discount: calculate per unit (apply to each individual unit)
                # Example: 5% on unit price 100 → discount_per_unit = 5, then multiply by quantity
                discount_per_unit = (price_after_pricing_rule * discount_value) / Decimal('100')
                # Apply max discount per unit if set (for percentage discounts)
                if max_discount_amount:
                    discount_per_unit = min(discount_per_unit, max_discount_amount)
                # Total discount = discount per unit × quantity
                discount_amount = discount_per_unit * Decimal(str(quantity))
                logger.info(
                    f"PERCENTAGE discount: discount_value={discount_value}%, unit_price={price_after_pricing_rule}, quantity={quantity}, discount_per_unit={discount_per_unit}, total_discount={discount_amount}",
                    extra={
                        "extra_fields": {
                            "discount_type": discount_type,
                            "discount_value": float(discount_value),
                            "unit_price": float(price_after_pricing_rule),
                            "quantity": quantity,
                            "discount_per_unit": float(discount_per_unit),
                            "total_discount": float(discount_amount),
                        }
                    }
                )
            elif discount_type == 'FIXED_AMOUNT':
                # FIXED_AMOUNT: Apply discount ONCE to the line total (not multiplied by quantity)
                # Example: discount_value = 50, line_total = 152 → discount = 50 (not 50 × 2 = 100)
                discount_amount = discount_value
                logger.info(
                    f"FIXED_AMOUNT discount: discount_value={discount_value}, line_total={line_total}, discount_applied={discount_amount}",
                    extra={
                        "extra_fields": {
                            "discount_type": discount_type,
                            "discount_value": float(discount_value),
                            "quantity": quantity,
                            "line_total": float(line_total),
                            "discount_applied": float(discount_amount),
                        }
                    }
                )
            elif discount_type == 'FREE_SHIPPING':
                # Free shipping doesn't affect item price
                discount_amount = Decimal('0')
            
            # CRITICAL: Never allow discount to exceed line total (cap it if needed)
            discount_amount_before_cap = discount_amount
            discount_amount = min(discount_amount, line_total)
            if discount_amount != discount_amount_before_cap:
                logger.warning(
                    f"Discount capped at line_total: original={discount_amount_before_cap}, capped={discount_amount}, line_total={line_total}",
                    extra={
                        "extra_fields": {
                            "original_discount": float(discount_amount_before_cap),
                            "capped_discount": float(discount_amount),
                            "line_total": float(line_total),
                        }
                    }
                )
            # Keep full precision - round only at the end
            discount_amount = max(Decimal('0'), discount_amount)
            
            # Calculate price per unit after discount (with full precision)
            if discount_type == 'PERCENTAGE':
                # For PERCENTAGE: If discount was capped, recalculate discount_per_unit
                if discount_amount != discount_amount_before_cap:
                    # Discount was capped, recalculate per-unit discount
                    discount_per_unit = discount_amount / Decimal(str(quantity)) if quantity > 0 else Decimal('0')
                # Unit price after discount = original unit price - discount per unit (keep full precision)
                price_after_promo = max(Decimal('0'), price_after_pricing_rule - discount_per_unit)
            else:
                # For FIXED_AMOUNT: Calculate unit price from line total after discount (keep full precision)
                line_total_after_discount = line_total - discount_amount
                price_after_promo = (line_total_after_discount / Decimal(str(quantity))) if quantity > 0 else Decimal('0')
                price_after_promo = max(Decimal('0'), price_after_promo)
            
            # Round only at the end for return values
            return {
                'price_after_promo': round_money(price_after_promo),
                'promo_discount_amount': round_money(discount_amount)
            }
        except Exception as e:
            logger.error(f"Error applying promo discount to item: {str(e)}", exc_info=True)
            return {
                'price_after_promo': round_money(price_after_pricing_rule),
                'promo_discount_amount': Decimal('0')
            }

    @staticmethod
    def calculate_sale_prices(
        cursor,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        quantity: int,
        base_selling_price: Decimal,
        location_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        sku: Optional[str] = None,
        product_metadata: Optional[Dict[str, str]] = None,
        current_datetime: Optional[datetime] = None,
        promo_discount_type: Optional[str] = None,
        promo_discount_value: Optional[Decimal] = None,
        promo_max_discount_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calculate prices for sales/checkout WITH TAX CONDITIONS.
        
        This is the full calculator used during checkout verification.
        It takes the base_selling_price provided by the client and recalculates
        all prices including taxes with conditions.
        
        Args:
            cursor: Database cursor
            product_id: Product ID
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            quantity: Quantity being purchased
            base_selling_price: Base selling price provided by client
            location_id: Optional location ID
            batch_id: Optional batch ID
            sku: Optional SKU
            product_metadata: Optional dict with metadata IDs
            current_datetime: Current datetime for time-based rule validation
            
        Returns:
            Dict with all calculated prices including taxes
        """
        try:
            # 1. Get Cost Price
            cost_price = ProductPriceCalculator.get_cost_price(
                cursor, product_id, tenant_id, org_id, bus_id, batch_id
            )
            
            # 2. Use provided base_selling_price or get from batch
            if base_selling_price is None or base_selling_price == 0:
                base_selling_price = ProductPriceCalculator.get_base_selling_price(
                    cursor, product_id, tenant_id, org_id, bus_id, batch_id
                ) or Decimal('0')
            else:
                base_selling_price = Decimal(str(base_selling_price))
            
            # 3. Get Actual Price (may override base_selling_price)
            actual_price = ProductPriceCalculator.get_actual_price(
                cursor, product_id, tenant_id, org_id, bus_id,
                location_id, sku, product_metadata, batch_id
            )
            
            if actual_price is None:
                actual_price = base_selling_price
            
            # 4. Apply Pricing Rules (INCLUDING QUANTITY-BASED RULES)
            pricing_result = SalesPriceCalculator.apply_pricing_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                actual_price, quantity, location_id, sku, product_metadata, current_datetime
            )
            
            price_after_pricing_rule = pricing_result['price'] if isinstance(pricing_result, dict) else pricing_result
            pricing_rule_applied = pricing_result.get('pricing_rule_applied') if isinstance(pricing_result, dict) else None
            
            if price_after_pricing_rule is not None:
                price_after_pricing_rule = round_money(max(Decimal('0'), price_after_pricing_rule))
            
            # 4.5. Apply INDIVIDUAL_ITEM Promo Discount (if provided, BEFORE tax)
            price_after_promo = price_after_pricing_rule
            item_promo_discount_amount = Decimal('0')
            if promo_discount_type and promo_discount_value is not None:
                promo_result = SalesPriceCalculator.apply_promo_discount_to_item(
                    price_after_pricing_rule,
                    quantity,
                    promo_discount_type,
                    Decimal(str(promo_discount_value)),
                    Decimal(str(promo_max_discount_amount)) if promo_max_discount_amount else None
                )
                price_after_promo = promo_result['price_after_promo']
                item_promo_discount_amount = promo_result['promo_discount_amount']
            
            # 5. Apply Tax Rules WITH CONDITIONS (on price after promo discount)
            tax_result = SalesPriceCalculator.apply_tax_rules(
                cursor, product_id, tenant_id, org_id, bus_id,
                price_after_promo, quantity, price_after_promo,
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
                'price_after_promo': decimal_to_float(price_after_promo),
                'item_promo_discount_amount': decimal_to_float(item_promo_discount_amount),
                'price_after_tax': decimal_to_float(price_after_tax),
                'tax_amount': decimal_to_float(tax_result['tax_amount']),
                'final_price': decimal_to_float(final_price),
                'taxes_applied': tax_result['taxes_applied'],
                'pricing_rule_applied': pricing_rule_applied,
                'tax_rule_applied': tax_result.get('tax_rule_applied')
            }
            
        except Exception as e:
            logger.error(f"Error calculating sale prices: {str(e)}", exc_info=True)
            return {
                'cost_price': None,
                'base_selling_price': None,
                'actual_price': None,
                'price_after_pricing_rule': None,
                'price_after_promo': None,
                'item_promo_discount_amount': None,
                'price_after_tax': None,
                'tax_amount': None,
                'final_price': None,
                'taxes_applied': [],
                'pricing_rule_applied': None,
                'tax_rule_applied': None
            }

