from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
import json
import psycopg2
from psycopg2 import DatabaseError, IntegrityError
from src.entities.store_sales.store_sales_read_dto import (
    CreateSaleServiceReadDto,
    UpdateSaleServiceReadDto,
    GetSaleServiceReadDto,
    GetSalesServiceReadDto,
    CancelSaleServiceReadDto,
    DeleteSaleServiceReadDto,
    SaleItemReadBase,
    SaleReadBase,
    PaymentReadBase,
    CreatePaymentServiceReadDto,
    UpdatePaymentServiceReadDto,
    GetPaymentServiceReadDto,
    GetPaymentsServiceReadDto,
    RefundPaymentServiceReadDto,
    GetSalesStatisticsServiceReadDto,
    SalesStatusStats,
    PaymentMethodStats,
    VerifyPriceServiceReadDto,
    VerifiedPriceItemReadDto,
    TaxAppliedReadDto,
    PricingRuleAppliedReadDto,
    TaxRuleAppliedReadDto,
)
from src.entities.store_sales.store_sales_write_dto import (
    CreateSaleServiceWriteDto,
    UpdateSaleServiceWriteDto,
    CancelSaleServiceWriteDto,
    DeleteSaleServiceWriteDto,
    CreatePaymentServiceWriteDto,
    UpdatePaymentServiceWriteDto,
    RefundPaymentServiceWriteDto,
    VerifyPriceServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from src.utils.sales_price_calculator import SalesPriceCalculator
from trovesuite.utils import Helper

logger = get_logger("store_sales_service")


class StoreSalesService:
    """Service class for store sales operations"""
    
    @staticmethod
    def _convert_item_to_dto(item_dict):
        """Helper method to convert item dict from database to SaleItemReadBase DTO"""
        # Map final_price from database to price for DTO (required field)
        if 'price' not in item_dict:
            item_dict['price'] = StoreSalesService._round_money(item_dict.get('final_price', 0.0) or 0.0)
        
        # Parse taxes_applied from JSON
        taxes_applied_list = []
        if item_dict.get('taxes_applied'):
            try:
                if isinstance(item_dict['taxes_applied'], str):
                    taxes_applied_list = json.loads(item_dict['taxes_applied'])
                elif isinstance(item_dict['taxes_applied'], list):
                    taxes_applied_list = item_dict['taxes_applied']
                # Convert to TaxAppliedItem objects
                from src.entities.store_sales.store_sales_base import TaxAppliedItem
                item_dict['taxes_applied'] = [TaxAppliedItem(**tax) for tax in taxes_applied_list]
                # tax_rate and tax_amount are already stored in the database, no need to calculate from taxes_applied
                # Just ensure they exist (defaults already set from database query)
            except Exception as e:
                logger.warning(f"Error parsing taxes_applied for item: {str(e)}")
                item_dict['taxes_applied'] = []
        else:
            item_dict['taxes_applied'] = []
        
        # Ensure is_inclusive is a boolean
        if 'is_inclusive' not in item_dict or item_dict.get('is_inclusive') is None:
            item_dict['is_inclusive'] = False
        
        return SaleItemReadBase(**item_dict)

    @staticmethod
    def _round_money(value) -> float:
        """Round money value to 2 decimal places"""
        from decimal import ROUND_HALF_UP
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        return round(float(value), 2)

    @staticmethod
    def _generate_sale_number(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        date_override: Optional[str] = None,
    ) -> str:
        """Generate a systematic sale number in format SAL-YYYYMMDD-NNN"""
        from datetime import datetime

        today = date_override if date_override else datetime.now().strftime("%Y%m%d")
        prefix = f"SAL-{today}"
        
        cursor.execute(
            f"""SELECT sale_number 
            FROM {db_settings.MSG_SALES_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
            AND sale_number LIKE %s
            ORDER BY sale_number DESC
            LIMIT 1""",
            (tenant_id, org_id, bus_id, loc_id, f"{prefix}-%"),
        )
        last_sale = cursor.fetchone()
        
        if last_sale and last_sale.get('sale_number'):
            last_number = last_sale['sale_number']
            try:
                sequence_str = last_number.split('-')[-1]
                sequence_num = int(sequence_str)
                next_sequence = sequence_num + 1
            except (ValueError, IndexError):
                next_sequence = 1
        else:
            next_sequence = 1
        
        sale_number = f"{prefix}-{next_sequence:03d}"
        
        max_attempts = 1000
        attempts = 0
        while attempts < max_attempts:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_SALES_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                AND sale_number = %s""",
                (tenant_id, org_id, bus_id, loc_id, sale_number),
            )
            if not cursor.fetchone():
                return sale_number
            
            next_sequence += 1
            sale_number = f"{prefix}-{next_sequence:03d}"
            attempts += 1
        
        import time
        timestamp_suffix = int(time.time() * 1000) % 10000
        sale_number = f"{prefix}-{timestamp_suffix:04d}"
        
        return sale_number

    @staticmethod
    def _get_store_product_batches_fifo(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        product_id: str,
        cursor
    ) -> List[dict]:
        """Get batches allocated to a store location for a product in FIFO order"""
        cursor.execute(
            f"""SELECT bl.*, pb.batch_number, pb.supplier_id, pb.currency_id, pb.cost_price, 
                   pb.base_selling_price, pb.product_size, pb.unit_of_measure_id, 
                   pb.qty_received, pb.qty_remaining, pb.product_expiry_date,
                   pb.status as batch_status, pb.delete_status as batch_delete_status, 
                   pb.is_active as batch_is_active, pb.batch_type,
                   pb.cdate as batch_cdate, pb.ctime as batch_ctime, pb.cdatetime as batch_cdatetime
            FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
            INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb 
                ON bl.purchase_batche_id = pb.id 
                AND bl.tenant_id = pb.tenant_id 
                AND bl.org_id = pb.org_id 
                AND bl.bus_id = pb.bus_id
            WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s 
            AND bl.loc_id = %s AND pb.product_id = %s 
            AND bl.location_type = 'STORE'
            AND pb.delete_status = 'NOT_DELETED' 
            AND pb.is_active = true
            AND pb.status NOT IN ('VOID', 'CANCELLED')
            AND bl.qty > 0
            ORDER BY bl.cdatetime ASC, pb.cdatetime ASC
            FOR UPDATE OF bl""",
            (tenant_id, org_id, bus_id, loc_id, product_id),
        )
        return cursor.fetchall()

    @staticmethod
    def _check_inventory_availability(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        product_id: str,
        required_qty: float,
        cursor
    ) -> tuple[bool, float, List[dict]]:
        """
        Check if required quantity is available in store using FIFO batches.
        
        Returns:
            (is_available, available_qty, batches_to_use)
        """
        batches = StoreSalesService._get_store_product_batches_fifo(
            tenant_id, org_id, bus_id, loc_id, product_id, cursor
        )
        
        total_available = Decimal('0')
        batches_to_use = []
        
        for batch in batches:
            batch_qty = Decimal(str(batch['qty']))
            total_available += batch_qty
            batches_to_use.append(batch)
            
            if total_available >= Decimal(str(required_qty)):
                break
        
        available_qty = float(total_available)
        is_available = total_available >= Decimal(str(required_qty))
        
        return is_available, available_qty, batches_to_use

    @staticmethod
    def create_sale(
        data: CreateSaleServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str,
        occurred_at: Optional[dict] = None,
    ) -> Respons[CreateSaleServiceReadDto]:
        """Create a new sale with FIFO inventory deduction"""
        logger.info(
            f"Processing sale creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "items_count": len(data.items),
                    "created_by": created_by,
                }
            },
        )

        dt = occurred_at if occurred_at is not None else Helper.current_date_time()
        cdate = dt["cdate"]
        ctime = dt["ctime"]
        cdatetime = dt["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Validate customer if provided
                if data.customer_id:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.customer_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Customer {data.customer_id} not found",
                            error="CUSTOMER_NOT_FOUND",
                        )

                # Validate location
                cursor.execute(
                    f"""SELECT id FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND id = %s""",
                    (tenant_id, loc_id),
                )
                if not cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"Location {loc_id} not found",
                        error="LOCATION_NOT_FOUND",
                    )

                # Validate sale_mode
                valid_sale_modes = ['INSTANT', 'DEPOSIT', 'CREDIT']
                sale_mode = data.sale_mode.upper() if data.sale_mode else 'INSTANT'
                if sale_mode not in valid_sale_modes:
                    return Respons(
                        success=False,
                        detail=f"Invalid sale_mode. Must be one of: {', '.join(valid_sale_modes)}",
                        error="INVALID_SALE_MODE",
                    )

                # Validate status if provided
                if data.status:
                    valid_statuses = ['ON_HOLD', 'PAID', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED', 'QUEUED']
                    status_upper = data.status.upper()
                    if status_upper not in valid_statuses:
                        return Respons(
                            success=False,
                            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                            error="INVALID_STATUS",
                        )

                # Check inventory availability for all items before processing
                # For DEPOSIT mode, we still check availability but won't move inventory until fully paid
                # First, aggregate quantities per product_id (same product can appear multiple times in cart)
                product_qty_totals = {}
                for item in data.items:
                    pid = item.product_id
                    product_qty_totals[pid] = product_qty_totals.get(pid, Decimal('0')) + Decimal(str(item.quantity))

                inventory_checks = {}
                for product_id_check, total_qty_needed in product_qty_totals.items():
                    is_available, available_qty, batches = StoreSalesService._check_inventory_availability(
                        tenant_id, org_id, bus_id, loc_id, product_id_check, float(total_qty_needed), cursor
                    )
                    
                    if not is_available:
                        # Get product name for error message
                        cursor.execute(
                            f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (product_id_check, tenant_id, org_id, bus_id),
                        )
                        product = cursor.fetchone()
                        product_name = product.get('name', product_id_check) if product else product_id_check

                        # Check if product exists in any location (for better error message)
                        cursor.execute(
                            f"""SELECT COUNT(*) as batch_count, COALESCE(SUM(bl.qty), 0) as total_qty
                            FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                            INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                                ON bl.purchase_batche_id = pb.id
                                AND bl.tenant_id = pb.tenant_id
                                AND bl.org_id = pb.org_id
                                AND bl.bus_id = pb.bus_id
                            WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s
                            AND pb.product_id = %s
                            AND bl.location_type = 'STORE'
                            AND pb.delete_status = 'NOT_DELETED'
                            AND pb.is_active = true
                            AND pb.status NOT IN ('VOID', 'CANCELLED')
                            AND bl.qty > 0""",
                            (tenant_id, org_id, bus_id, product_id_check),
                        )
                        inventory_check = cursor.fetchone()
                        total_inventory = float(inventory_check['total_qty']) if inventory_check else 0.0

                        # Check if product exists in warehouse
                        cursor.execute(
                            f"""SELECT COUNT(*) as warehouse_batch_count, COALESCE(SUM(bl.qty), 0) as warehouse_qty
                            FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                            INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                                ON bl.purchase_batche_id = pb.id
                                AND bl.tenant_id = pb.tenant_id
                                AND bl.org_id = pb.org_id
                                AND bl.bus_id = pb.bus_id
                            WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s
                            AND pb.product_id = %s
                            AND bl.location_type = 'WAREHOUSE'
                            AND pb.delete_status = 'NOT_DELETED'
                            AND pb.is_active = true
                            AND pb.status NOT IN ('VOID', 'CANCELLED')
                            AND bl.qty > 0""",
                            (tenant_id, org_id, bus_id, product_id_check),
                        )
                        warehouse_check = cursor.fetchone()
                        warehouse_qty = float(warehouse_check['warehouse_qty']) if warehouse_check else 0.0

                        # Build detailed error message
                        error_detail = f"Insufficient inventory for product '{product_name}' at this location. Required: {float(total_qty_needed)}, Available: {available_qty}"

                        if total_inventory > 0:
                            error_detail += f". Note: {total_inventory} units exist in other store locations."

                        if warehouse_qty > 0:
                            error_detail += f" {warehouse_qty} units available in warehouse - consider transferring to store first."

                        if total_inventory == 0 and warehouse_qty == 0:
                            error_detail += " No inventory found in any location. Please add stock first."

                        return Respons(
                            success=False,
                            detail=error_detail,
                            error="INSUFFICIENT_INVENTORY",
                        )

                    inventory_checks[product_id_check] = {
                        'batches': batches,
                        'required_qty': total_qty_needed
                    }

                # Generate sale number (use backdated date when available)
                sale_number_date = cdate.replace("-", "") if occurred_at else None
                sale_number = StoreSalesService._generate_sale_number(
                    cursor, tenant_id, org_id, bus_id, loc_id, date_override=sale_number_date
                )

                # Parse sale_date — when backdating is active, always use the backdated date
                effective_sale_date_str = cdate if occurred_at else (data.sale_date if data.sale_date else cdate)
                try:
                    sale_date = datetime.strptime(effective_sale_date_str, "%Y-%m-%d").date()
                except ValueError:
                    return Respons(
                        success=False,
                        detail="Invalid sale_date format. Expected YYYY-MM-DD",
                        error="INVALID_DATE_FORMAT",
                    )

                # =====================================================
                # USE VERIFIED TOTALS FROM verify_price (if provided)
                # =====================================================
                # Use verified totals from verify_price endpoint to avoid recalculation discrepancies
                promo_code_id = None
                promo_discount_amount = Decimal('0')
                gift_card_id = None
                affiliate_id = None
                
                if data.verified_total_amount is not None:
                    total_amount = Decimal(str(data.verified_total_amount))
                    promo_discount_amount = Decimal(str(data.verified_promo_discount_amount)) if data.verified_promo_discount_amount is not None else Decimal('0')
                    promo_code_id = data.verified_promo_code_id
                    gift_card_id = data.verified_gift_card_id
                    affiliate_id = data.verified_affiliate_id
                    
                    logger.info(
                        f"Using verified totals from verify_price: total_amount={total_amount}, "
                        f"promo_discount={promo_discount_amount}, promo_code_id={promo_code_id}"
                    )
                else:
                    # Fallback: Calculate from items if verified totals not provided (backward compatibility)
                    logger.warning("Verified totals not provided, calculating from items (backward compatibility mode)")
                    total_amount = Decimal('0')
                    promo_discount_amount = Decimal('0')
                    promo_code_id = None
                    
                    # Collect item line totals (price_after_pricing_rule × quantity) for min_purchase validation
                    item_line_totals_for_validation = []
                    
                    for item in data.items:
                        # Use final_price from item (already calculated by verify_price)
                        final_price = Decimal(str(item.final_price)) if item.final_price else Decimal('0')
                        if final_price == 0 and item.price_after_tax:
                            final_price = Decimal(str(item.price_after_tax))
                        if final_price == 0 and item.price_after_pricing_rule:
                            final_price = Decimal(str(item.price_after_pricing_rule))
                        if final_price == 0 and item.actual_price:
                            final_price = Decimal(str(item.actual_price))
                        if final_price == 0 and item.base_selling_price:
                            final_price = Decimal(str(item.base_selling_price))
                        
                        line_total = final_price * Decimal(str(item.quantity))
                        total_amount += line_total
                        
                        # For min_purchase validation, use price_after_pricing_rule if available, otherwise use final_price
                        price_for_min_check = Decimal(str(item.price_after_pricing_rule)) if item.price_after_pricing_rule else final_price
                        line_total_for_validation = price_for_min_check * Decimal(str(item.quantity))
                        item_line_totals_for_validation.append(line_total_for_validation)
                    
                    # Validate promo code if provided (but don't recalculate discount)
                    if data.promo_code:
                        from src.entities.promo_codes.promo_codes_service import PromoCodesService
                        
                        # Collect product IDs for validation
                        cart_product_ids = [item.product_id for item in data.items]
                        
                        is_valid, error_msg, discount_amt, promo_id, promo_details = PromoCodesService.validate_and_calculate_discount(
                            promo_code=data.promo_code,
                            item_line_totals=item_line_totals_for_validation,  # Line totals for min_purchase check
                            customer_id=data.customer_id,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            cursor=cursor,
                            product_ids=cart_product_ids if cart_product_ids else None,
                            product_metadata=None,  # Not available in fallback mode
                            location_id=loc_id
                        )
                        
                        if not is_valid:
                            return Respons(
                                success=False,
                                detail=error_msg or "Invalid promo code",
                                error="INVALID_PROMO_CODE",
                            )
                        
                        promo_code_id = promo_id
                        # Note: discount_amount is None for per-item discounts, so we don't subtract it here
                        # Discounts are already applied per-item in the final_price

                # Process each sale item (use verified prices directly, no recalculation)
                sale_items = []
                
                for item in data.items:
                    product_id = item.product_id
                    required_qty = Decimal(str(item.quantity))  # Use this item's quantity, not the aggregated total
                    batches = inventory_checks[product_id]['batches']
                    
                    # Get product name
                    cursor.execute(
                        f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (product_id, tenant_id, org_id, bus_id),
                    )
                    product = cursor.fetchone()
                    product_name = product.get('name', 'Unknown Product') if product else 'Unknown Product'

                    # Use verified prices directly from item (no recalculation)
                    base_selling_price = Decimal(str(item.base_selling_price)) if item.base_selling_price is not None else Decimal('0')
                    actual_price = Decimal(str(item.actual_price)) if item.actual_price is not None else Decimal('0')
                    price_after_pricing_rules = Decimal(str(item.price_after_pricing_rule)) if item.price_after_pricing_rule is not None else Decimal('0')
                    
                    # Get price_after_tax and final_price from item
                    if item.final_price is not None:
                        final_price = Decimal(str(item.final_price))
                        price_after_tax = Decimal(str(item.price_after_tax)) if item.price_after_tax is not None else final_price
                    elif item.price_after_tax is not None:
                        price_after_tax = Decimal(str(item.price_after_tax))
                        final_price = price_after_tax
                    else:
                        final_price = Decimal('0')
                        price_after_tax = Decimal('0')
                    
                    # Get taxes_applied from item (for storing, not for calculation)
                    taxes_applied = item.taxes_applied if item.taxes_applied else []
                    
                    # Use tax_rate and tax_amount directly from input (no calculation)
                    tax_rate = Decimal(str(item.tax_rate)) if item.tax_rate is not None else Decimal('0')
                    item_tax_amount = Decimal(str(item.tax_amount)) if item.tax_amount is not None else Decimal('0')
                    # is_inclusive - use from input or from taxes_applied
                    is_inclusive = item.is_inclusive if item.is_inclusive is not None else (any(tax.is_inclusive for tax in taxes_applied) if taxes_applied else False)
                    
                    # Calculate line_total from final_price (or use from item if available)
                    line_total = final_price * Decimal(str(item.quantity)) if final_price > 0 else Decimal('0')

                    # Store item data for later processing
                    sale_items.append({
                        'product_id': product_id,
                        'product_name': product_name,
                        'required_qty': required_qty,
                        'batches': batches,
                        'item': item,
                        'base_selling_price': base_selling_price,
                        'actual_price': actual_price,
                        'price_after_pricing_rule': price_after_pricing_rules,
                        'price_after_tax': price_after_tax,
                        'final_price': final_price,
                        'tax_rate': tax_rate,
                        'is_inclusive': is_inclusive,
                        'tax_amount': item_tax_amount,
                        'taxes_applied': taxes_applied,
                        'line_total': line_total
                    })

                # Check if status is explicitly provided as ON_HOLD
                explicit_status = data.status.upper() if data.status else None
                is_explicitly_on_hold = explicit_status == 'ON_HOLD'

                # =====================================================
                # VALIDATE AND PROCESS GIFT CARD (if provided)
                # =====================================================
                gift_card_id = data.verified_gift_card_id if data.verified_gift_card_id else None
                gift_card_amount_used = Decimal('0')
                gift_card_obj = None
                
                if data.gift_card_code:
                    from src.entities.gift_cards.gift_cards_service import GiftCardsService
                    
                    # If verified_gift_card_id is provided, use it and validate the code matches
                    if data.verified_gift_card_id:
                        gift_card_id = data.verified_gift_card_id
                        # Quick validation that the code matches the ID
                        gift_card_result = GiftCardsService.get_gift_card_by_code(
                            gift_card_code=data.gift_card_code,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                        )
                        if not gift_card_result.success or not gift_card_result.data:
                            return Respons(
                                success=False,
                                detail="Gift card code does not match verified gift card",
                                error="INVALID_GIFT_CARD",
                            )
                        gift_card_obj = gift_card_result.data[0] if isinstance(gift_card_result.data, list) else gift_card_result.data
                    else:
                        # Fallback: Get gift card by code (backward compatibility)
                        gift_card_result = GiftCardsService.get_gift_card_by_code(
                            gift_card_code=data.gift_card_code,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                        )
                        
                        if not gift_card_result.success or not gift_card_result.data:
                            return Respons(
                                success=False,
                                detail="Gift card not found or invalid",
                                error="INVALID_GIFT_CARD",
                            )
                        
                        gift_card_obj = gift_card_result.data[0] if isinstance(gift_card_result.data, list) else gift_card_result.data
                        
                        # Validate gift card
                        if gift_card_obj.status != 'ACTIVE':
                            return Respons(
                                success=False,
                                detail=f"Gift card is {gift_card_obj.status.lower()}",
                                error="INVALID_GIFT_CARD_STATUS",
                            )
                        
                        if gift_card_obj.current_balance <= 0:
                            return Respons(
                                success=False,
                                detail="Gift card has no balance",
                                error="INSUFFICIENT_GIFT_CARD_BALANCE",
                            )
                        
                        # Check expiry
                        if gift_card_obj.expiry_date:
                            from datetime import date
                            if date.today() > gift_card_obj.expiry_date:
                                return Respons(
                                    success=False,
                                    detail="Gift card has expired",
                                    error="EXPIRED_GIFT_CARD",
                                )
                        
                        # Check location restrictions - STRICT: if applicable_to_locations is empty/null, don't apply to any
                        applicable_locations = gift_card_obj.applicable_to_locations
                        location_match = False
                        if applicable_locations:
                            # Convert to list of location IDs if it's a list of objects
                            if isinstance(applicable_locations, list) and len(applicable_locations) > 0:
                                if isinstance(applicable_locations[0], dict):
                                    applicable_location_ids = [loc.get('location_id') for loc in applicable_locations if loc.get('location_id')]
                                else:
                                    applicable_location_ids = [str(loc) for loc in applicable_locations]
                                
                                if applicable_location_ids:
                                    location_match = str(loc_id).strip() in [str(lid).strip() for lid in applicable_location_ids]
                        
                        if not location_match:
                            return Respons(
                                success=False,
                                detail="Gift card is not valid for this location. At least one location must be selected for the gift card to be usable.",
                                error="INVALID_GIFT_CARD_LOCATION",
                            )
                        
                        gift_card_id = gift_card_obj.id

                # Process payments if provided (ignore payments if explicitly ON_HOLD)
                paid_amount = Decimal('0')
                payments_list = []
                # Use verified_final_total_amount if provided, otherwise use total_amount
                final_total_for_payments = Decimal(str(data.verified_final_total_amount)) if data.verified_final_total_amount is not None else total_amount
                remaining_balance = final_total_for_payments  # Track remaining balance for gift card usage
                
                if data.payments and not is_explicitly_on_hold:
                    for payment_data in data.payments:
                        # Validate payment method
                        valid_payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'GIFT_CARD', 'OTHERS']
                        if payment_data.payment_method not in valid_payment_methods:
                            raise ValueError(f"Invalid payment method. Must be one of: {', '.join(valid_payment_methods)}")

                        # Handle gift card payment
                        if payment_data.payment_method == 'GIFT_CARD':
                            if not data.gift_card_code or not gift_card_obj:
                                raise ValueError("gift_card_code is required when payment_method is GIFT_CARD")
                            
                            # Calculate how much can be used from gift card
                            gift_card_balance = Decimal(str(gift_card_obj.current_balance))
                            amount_to_use = min(gift_card_balance, remaining_balance)
                            
                            if amount_to_use <= 0:
                                raise ValueError("Gift card has insufficient balance or sale is already fully paid")
                            
                            gift_card_amount_used = amount_to_use
                            paid_amount += amount_to_use
                            remaining_balance -= amount_to_use
                        else:
                            # Regular payment method - cap at remaining balance to prevent overpayment
                            payment_amount = Decimal(str(payment_data.paid_amount))
                            if remaining_balance <= 0:
                                raise ValueError("Sale is already fully paid. Cannot accept additional payment.")
                            payment_amount = min(payment_amount, remaining_balance)
                            paid_amount += payment_amount
                            remaining_balance -= payment_amount

                # Calculate balance (use final_total_amount after promo discount)
                balance_amount = final_total_for_payments - paid_amount

                # Determine status and fulfillment_status
                # If status is explicitly ON_HOLD, override automatic determination
                if is_explicitly_on_hold:
                    status = 'ON_HOLD'
                    fulfillment_status = 'PENDING'  # Items are on hold, not fulfilled
                    paid_amount = Decimal('0')  # No payments when on hold
                    balance_amount = final_total_for_payments
                elif explicit_status:
                    # Status is explicitly provided but not ON_HOLD
                    status = explicit_status
                    # Still determine fulfillment_status based on sale_mode and payment
                    if sale_mode == 'INSTANT':
                        if paid_amount >= final_total_for_payments:
                            fulfillment_status = 'FULFILLED'
                        else:
                            fulfillment_status = 'PENDING'
                    elif sale_mode == 'DEPOSIT':
                        if paid_amount >= final_total_for_payments:
                            fulfillment_status = 'FULFILLED'
                        else:
                            fulfillment_status = 'PENDING'
                    elif sale_mode == 'CREDIT':
                        fulfillment_status = 'FULFILLED'  # Goods are taken immediately
                    else:
                        fulfillment_status = 'PENDING'
                else:
                    # No explicit status provided, determine automatically based on sale_mode
                    if sale_mode == 'INSTANT':
                        if paid_amount >= final_total_for_payments:
                            status = 'PAID'
                            fulfillment_status = 'FULFILLED'
                        else:
                            status = 'PARTIALLY_PAID'
                            fulfillment_status = 'PENDING'
                    elif sale_mode == 'DEPOSIT':
                        if paid_amount >= final_total_for_payments:
                            status = 'PAID'
                            fulfillment_status = 'FULFILLED'
                        elif paid_amount > 0:
                            status = 'PARTIALLY_PAID'
                            fulfillment_status = 'PENDING'
                        else:
                            status = 'ON_HOLD'
                            fulfillment_status = 'PENDING'
                    elif sale_mode == 'CREDIT':
                        status = 'ON_HOLD'
                        fulfillment_status = 'FULFILLED'  # Goods are taken immediately

                # =====================================================
                # VALIDATE AND TRACK AFFILIATE (if provided)
                # =====================================================
                # Use verified_affiliate_id if provided, otherwise validate from code
                affiliate_id = data.verified_affiliate_id if data.verified_affiliate_id else None
                
                if data.affiliate_code:
                    if data.verified_affiliate_id:
                        # Quick validation that the code matches the ID
                        from src.entities.affiliates.affiliates_service import AffiliatesService
                        affiliate_result = AffiliatesService.get_affiliate_by_code(
                            affiliate_code=data.affiliate_code,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                        )
                        if not affiliate_result.success or not affiliate_result.data:
                            return Respons(
                                success=False,
                                detail="Affiliate code does not match verified affiliate",
                                error="INVALID_AFFILIATE_CODE",
                            )
                        affiliate = affiliate_result.data[0] if isinstance(affiliate_result.data, list) else affiliate_result.data
                        if affiliate.id != data.verified_affiliate_id:
                            return Respons(
                                success=False,
                                detail="Affiliate code does not match verified affiliate ID",
                                error="INVALID_AFFILIATE_CODE",
                            )
                    else:
                        # Fallback: Get affiliate by code (backward compatibility)
                        from src.entities.affiliates.affiliates_service import AffiliatesService
                        
                        affiliate_result = AffiliatesService.get_affiliate_by_code(
                            affiliate_code=data.affiliate_code,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                        )
                        
                        if not affiliate_result.success or not affiliate_result.data:
                            return Respons(
                                success=False,
                                detail="Affiliate code not found or invalid",
                                error="INVALID_AFFILIATE_CODE",
                            )
                        
                        affiliate = affiliate_result.data[0] if isinstance(affiliate_result.data, list) else affiliate_result.data
                        
                        # Validate affiliate
                        if affiliate.status != 'ACTIVE' or not affiliate.is_active:
                            return Respons(
                                success=False,
                                detail="Affiliate is not active",
                                error="INACTIVE_AFFILIATE",
                            )
                        
                        # Collect product IDs and product-to-metadata mapping for affiliate validation
                        cart_product_ids_for_affiliate = [item.product_id for item in data.items]
                        cart_metadata_ids = []
                        product_metadata_map = {}  # Map product_id -> list of metadata_ids
                        for item in data.items:
                            product_metadata_map[item.product_id] = []
                            try:
                                cursor.execute(
                                    f"""SELECT pm.id
                                    FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                                    INNER JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} pm 
                                        ON amp.product_metadata_id = pm.id 
                                        AND amp.tenant_id = pm.tenant_id 
                                        AND amp.org_id = pm.org_id 
                                        AND amp.bus_id = pm.bus_id
                                    WHERE amp.tenant_id = %s AND amp.org_id = %s AND amp.bus_id = %s 
                                    AND amp.product_id = %s
                                    AND pm.delete_status = 'NOT_DELETED'""",
                                    (tenant_id, org_id, bus_id, item.product_id),
                                )
                                metadata_records = cursor.fetchall()
                                for meta in metadata_records:
                                    meta_id = meta.get('id')
                                    if meta_id:
                                        if meta_id not in cart_metadata_ids:
                                            cart_metadata_ids.append(meta_id)
                                        product_metadata_map[item.product_id].append(str(meta_id))
                            except Exception as meta_error:
                                logger.warning(f"Error fetching metadata for product {item.product_id}: {str(meta_error)}")
                                # Continue even if metadata fetch fails
                        
                        # Check location restrictions (if applicable_to_locations is set)
                        applicable_locations = affiliate.applicable_to_locations
                        if applicable_locations:
                            if isinstance(applicable_locations, list) and len(applicable_locations) > 0:
                                applicable_location_ids = []
                                for loc in applicable_locations:
                                    if isinstance(loc, dict):
                                        loc_id_val = loc.get('location_id')
                                        if loc_id_val:
                                            applicable_location_ids.append(str(loc_id_val))
                                    elif hasattr(loc, 'location_id'):
                                        # Pydantic model or object with location_id attribute
                                        applicable_location_ids.append(str(loc.location_id))
                                    elif hasattr(loc, 'dict'):
                                        # Pydantic v1 model - convert to dict
                                        loc_dict = loc.dict()
                                        loc_id_val = loc_dict.get('location_id')
                                        if loc_id_val:
                                            applicable_location_ids.append(str(loc_id_val))
                                    elif hasattr(loc, 'model_dump'):
                                        # Pydantic v2 model - convert to dict
                                        loc_dict = loc.model_dump()
                                        loc_id_val = loc_dict.get('location_id')
                                        if loc_id_val:
                                            applicable_location_ids.append(str(loc_id_val))
                                    else:
                                        # Fallback: try to convert to string (for backwards compatibility)
                                        applicable_location_ids.append(str(loc))
                                
                                if applicable_location_ids:
                                    location_match = str(loc_id).strip() in [str(lid).strip() for lid in applicable_location_ids]
                                    if not location_match:
                                        return Respons(
                                            success=False,
                                            detail="Affiliate is not valid for this location",
                                            error="INVALID_AFFILIATE_LOCATION",
                                        )
                        
                        # Check product restrictions (if applicable_to_products is set)
                        applicable_products = affiliate.applicable_to_products
                        applicable_product_ids = []
                        if applicable_products:
                            if isinstance(applicable_products, list) and len(applicable_products) > 0:
                                for prod in applicable_products:
                                    if isinstance(prod, dict):
                                        prod_id_val = prod.get('product_id')
                                        if prod_id_val:
                                            applicable_product_ids.append(str(prod_id_val))
                                    elif hasattr(prod, 'product_id'):
                                        # Pydantic model or object with product_id attribute
                                        applicable_product_ids.append(str(prod.product_id))
                                    elif hasattr(prod, 'dict'):
                                        # Pydantic v1 model - convert to dict
                                        prod_dict = prod.dict()
                                        prod_id_val = prod_dict.get('product_id')
                                        if prod_id_val:
                                            applicable_product_ids.append(str(prod_id_val))
                                    elif hasattr(prod, 'model_dump'):
                                        # Pydantic v2 model - convert to dict
                                        prod_dict = prod.model_dump()
                                        prod_id_val = prod_dict.get('product_id')
                                        if prod_id_val:
                                            applicable_product_ids.append(str(prod_id_val))
                                    else:
                                        # Fallback: try to convert to string (for backwards compatibility)
                                        applicable_product_ids.append(str(prod))
                                
                                if applicable_product_ids and cart_product_ids_for_affiliate:
                                    product_match = any(pid in applicable_product_ids for pid in cart_product_ids_for_affiliate)
                                    if not product_match:
                                        return Respons(
                                            success=False,
                                            detail="Affiliate is not valid for the products in this sale",
                                            error="INVALID_AFFILIATE_PRODUCTS",
                                        )
                                elif applicable_product_ids:
                                    return Respons(
                                        success=False,
                                        detail="Affiliate is restricted to specific products, but no matching products found in sale",
                                        error="INVALID_AFFILIATE_PRODUCTS",
                                    )
                        
                        # Check product metadata restrictions (if applicable_to_product_metadata is set)
                        applicable_metadata = affiliate.applicable_to_product_metadata
                        applicable_metadata_ids = []
                        if applicable_metadata:
                            if isinstance(applicable_metadata, list) and len(applicable_metadata) > 0:
                                for meta in applicable_metadata:
                                    if isinstance(meta, dict):
                                        meta_id_val = meta.get('metadata_id')
                                        if meta_id_val:
                                            applicable_metadata_ids.append(str(meta_id_val))
                                    elif hasattr(meta, 'metadata_id'):
                                        # Pydantic model or object with metadata_id attribute
                                        applicable_metadata_ids.append(str(meta.metadata_id))
                                    elif hasattr(meta, 'dict'):
                                        # Pydantic v1 model - convert to dict
                                        meta_dict = meta.dict()
                                        meta_id_val = meta_dict.get('metadata_id')
                                        if meta_id_val:
                                            applicable_metadata_ids.append(str(meta_id_val))
                                    elif hasattr(meta, 'model_dump'):
                                        # Pydantic v2 model - convert to dict
                                        meta_dict = meta.model_dump()
                                        meta_id_val = meta_dict.get('metadata_id')
                                        if meta_id_val:
                                            applicable_metadata_ids.append(str(meta_id_val))
                                    else:
                                        # Fallback: try to convert to string (for backwards compatibility)
                                        applicable_metadata_ids.append(str(meta))
                                
                                # If BOTH product and metadata restrictions are set, check that products matching 
                                # the product restriction ALSO have the metadata restriction
                                if applicable_product_ids and applicable_metadata_ids:
                                    # Find products in cart that match product restriction
                                    matching_products = [pid for pid in cart_product_ids_for_affiliate if pid in applicable_product_ids]
                                    if not matching_products:
                                        return Respons(
                                            success=False,
                                            detail="Affiliate is not valid for the products in this sale",
                                            error="INVALID_AFFILIATE_PRODUCTS",
                                        )
                                    
                                    # Check if any of the matching products also have the required metadata
                                    metadata_match = False
                                    for product_id in matching_products:
                                        product_metas = product_metadata_map.get(product_id, [])
                                        if any(mid in applicable_metadata_ids for mid in product_metas):
                                            metadata_match = True
                                            break
                                    
                                    if not metadata_match:
                                        return Respons(
                                            success=False,
                                            detail="Affiliate is not valid: the products in this sale do not have the required metadata (categories, brands, tags, labels)",
                                            error="INVALID_AFFILIATE_METADATA",
                                        )
                                elif applicable_metadata_ids:
                                    # Only metadata restriction (no product restriction)
                                    if cart_metadata_ids:
                                        metadata_match = any(mid in applicable_metadata_ids for mid in cart_metadata_ids)
                                        if not metadata_match:
                                            return Respons(
                                                success=False,
                                                detail="Affiliate is not valid for the product metadata (categories, brands, tags, labels) in this sale",
                                                error="INVALID_AFFILIATE_METADATA",
                                            )
                                    else:
                                        return Respons(
                                            success=False,
                                            detail="Affiliate is restricted to specific product metadata, but no matching metadata found in sale",
                                            error="INVALID_AFFILIATE_METADATA",
                                        )
                        
                        affiliate_id = affiliate.id

                # Set fulfillment_date_time if fulfillment_status is FULFILLED
                fulfillment_date_time = None
                if fulfillment_status == 'FULFILLED':
                    fulfillment_date_time = cdatetime

                # Create sale
                sale_id = Helper.generate_unique_identifier(prefix="sal")
                if fulfillment_date_time:
                    cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_SALES_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, sale_number, customer_id,
                         sale_date, status, sale_mode, fulfillment_status, description,
                         total_amount, paid_amount, balance_amount, fulfillment_date_time,
                         gift_card_amount_used, promo_code_id, promo_discount_amount, affiliate_id,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        sale_id, tenant_id, org_id, bus_id, loc_id, sale_number,
                            data.customer_id, sale_date, status, sale_mode, fulfillment_status, data.description,
                            StoreSalesService._round_money(final_total_for_payments), StoreSalesService._round_money(paid_amount), StoreSalesService._round_money(balance_amount), fulfillment_date_time,
                            StoreSalesService._round_money(gift_card_amount_used), promo_code_id, StoreSalesService._round_money(promo_discount_amount), affiliate_id,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                else:
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_SALES_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, sale_number, customer_id,
                         sale_date, status, sale_mode, fulfillment_status, description,
                         total_amount, paid_amount, balance_amount,
                         gift_card_amount_used, promo_code_id, promo_discount_amount, affiliate_id,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            sale_id, tenant_id, org_id, bus_id, loc_id, sale_number,
                            data.customer_id, sale_date, status, sale_mode, fulfillment_status, data.description,
                            StoreSalesService._round_money(final_total_for_payments), StoreSalesService._round_money(paid_amount), StoreSalesService._round_money(balance_amount),
                            StoreSalesService._round_money(gift_card_amount_used), promo_code_id, StoreSalesService._round_money(promo_discount_amount), affiliate_id,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                sale_result = cursor.fetchone()

                if not sale_result:
                    raise ValueError("Failed to create sale")

                # Process each sale item and handle inventory based on sale_mode
                # Determine if inventory should be moved now
                # If explicitly ON_HOLD, never move inventory
                should_move_inventory = False
                if not is_explicitly_on_hold:
                    # Compare Decimal values by quantizing to 2 decimal places to avoid precision issues
                    from decimal import ROUND_HALF_UP
                    paid_amount_rounded = paid_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    total_amount_rounded = final_total_for_payments.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    logger.info(
                        f"Checking inventory movement: sale_mode={sale_mode}, "
                        f"paid_amount={paid_amount} (rounded={paid_amount_rounded}), "
                        f"total_amount={total_amount} (rounded={total_amount_rounded}), "
                        f"is_explicitly_on_hold={is_explicitly_on_hold}"
                    )
                    
                    if sale_mode == 'INSTANT' and paid_amount_rounded == total_amount_rounded:
                        should_move_inventory = True  # INSTANT: deduct inventory only when fully paid
                        logger.info(f"Inventory movement ENABLED for INSTANT sale (fully paid)")
                    elif sale_mode == 'CREDIT':
                        should_move_inventory = True  # Credit: goods taken immediately
                        logger.info(f"Inventory movement ENABLED for CREDIT sale")
                    elif sale_mode == 'DEPOSIT' and paid_amount_rounded >= total_amount_rounded:
                        should_move_inventory = True  # Deposit: only move when fully paid
                        logger.info(f"Inventory movement ENABLED for DEPOSIT sale (fully paid)")
                    else:
                        logger.info(f"Inventory movement DISABLED: sale_mode={sale_mode}, condition not met")
                    # For DEPOSIT with partial payment, don't move inventory yet

                processed_sale_items = []
                logger.info(f"Processing {len(sale_items)} sale items for inventory deduction. should_move_inventory={should_move_inventory}")
                for item_data in sale_items:
                    product_id = item_data['product_id']
                    product_name = item_data['product_name']
                    required_qty = item_data['required_qty']
                    batches = item_data['batches']
                    item = item_data['item']
                    base_selling_price = item_data['base_selling_price']
                    actual_price = item_data['actual_price']
                    price_after_pricing_rule = item_data['price_after_pricing_rule']
                    price_after_tax = item_data['price_after_tax']
                    final_price = item_data['final_price']
                    tax_rate = item_data['tax_rate']
                    is_inclusive = item_data['is_inclusive']
                    tax_amount = item_data['tax_amount']
                    taxes_applied = item_data.get('taxes_applied', [])
                    line_total = item_data['line_total']

                    # Handle inventory movement based on sale_mode
                    batch_allocations = []
                    # Ensure first_batch_id is always set from batches (required for NOT NULL constraint)
                    # Since inventory check passed, batches should exist
                    first_batch_id = batches[0]['purchase_batche_id'] if batches and len(batches) > 0 else None
                    
                    if not first_batch_id:
                        # This should not happen if inventory check passed, but handle gracefully
                        logger.error(
                            f"No batches available for product {product_id} at location {loc_id}. "
                            f"This should have been caught by inventory check."
                        )
                        return Respons(
                            success=False,
                            detail=f"No batches available for product. This should have been caught during inventory check.",
                            error="INVENTORY_CHECK_FAILED",
                        )
                    
                    if should_move_inventory:
                        logger.info(
                            f"Processing inventory deduction for sale {sale_id}, product {product_id}, "
                            f"required_qty={required_qty}, batches_count={len(batches)}"
                        )
                        
                        if not batches or len(batches) == 0:
                            logger.warning(
                                f"No batches found for product {product_id} at location {loc_id}. "
                                f"Cannot deduct inventory."
                            )
                        else:
                            logger.info(
                                f"Starting batch deduction: product={product_id}, required_qty={required_qty}, "
                                f"batches_available={len(batches)}"
                            )
                            # Deduct from batches in FIFO order
                            remaining_qty = required_qty

                            for batch in batches:
                                if remaining_qty <= 0:
                                    break

                                batch_id = batch['purchase_batche_id']
                                batch_location_id = batch['id']
                                batch_qty = Decimal(str(batch['qty']))
                            
                                qty_to_deduct = min(remaining_qty, batch_qty)

                                # Update batch location (deduct quantity)
                                new_batch_qty = batch_qty - qty_to_deduct
                                cursor.execute(
                                    f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                                    SET qty = %s
                                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                    (float(new_batch_qty), batch_location_id, tenant_id, org_id, bus_id),
                                )

                                batch_allocations.append({
                                    'batch_id': batch_id,
                                    'qty_deducted': float(qty_to_deduct)
                                })
                                remaining_qty -= qty_to_deduct

                            # Validate that all required quantity was deducted
                            if remaining_qty > 0:
                                total_deducted = required_qty - remaining_qty
                                error_message = (
                                    f"Insufficient inventory during deduction for product '{product_name}' (ID: {product_id}). "
                                    f"Required: {float(required_qty)} units, "
                                    f"Successfully deducted: {float(total_deducted)} units, "
                                    f"Remaining needed: {float(remaining_qty)} units. "
                                    f"This may occur if inventory was consumed by another transaction. "
                                    f"Please check inventory levels and try again."
                                )
                                logger.error(error_message)
                                raise ValueError(error_message)

                            # Update first_batch_id from batch_allocations if available (use the batch we actually deducted from)
                            if batch_allocations:
                                first_batch_id = batch_allocations[0]['batch_id']
                            
                            logger.info(
                                f"Batch deduction completed: product={product_id}, "
                                f"total_deducted={sum(a['qty_deducted'] for a in batch_allocations)}, "
                                f"allocations_count={len(batch_allocations)}"
                            )
                        
                            # Update store product current_qty
                            logger.info(f"Updating store product current_qty for product {product_id}, deducting {required_qty}")
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                                SET current_qty = current_qty - %s, updated_by = %s
                                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                AND loc_id = %s AND product_id = %s""",
                                (float(required_qty), created_by, tenant_id, org_id, bus_id, loc_id, product_id),
                            )
                            logger.info(f"Store product current_qty updated successfully")

                            # Create product movements for each batch deduction
                            logger.info(f"Creating {len(batch_allocations)} product movement(s) for sale {sale_id}")
                            for batch_allocation in batch_allocations:
                                movement_id = Helper.generate_unique_identifier(prefix="mov")
                                cursor.execute(
                                    f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                                    (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                                     movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    RETURNING *""",
                                    (
                                        movement_id, tenant_id, org_id, bus_id, product_id,
                                        batch_allocation['batch_id'], 'STORE', loc_id,
                                        'OUT', float(batch_allocation['qty_deducted']),
                                        'SALE', sale_id,
                                        cdate, ctime, cdatetime, created_by
                                    ),
                                )
                                logger.info(
                                    f"Created product movement: movement_id={movement_id}, "
                                    f"batch_id={batch_allocation['batch_id']}, qty={batch_allocation['qty_deducted']}"
                                )
                            logger.info(f"All product movements created successfully for sale {sale_id}")
                    # else: For DEPOSIT mode with partial payment or ON_HOLD, first_batch_id is already set above

                    # Create sale item
                    sale_item_id = Helper.generate_unique_identifier(prefix="sali")
                    
                    # Prepare taxes_applied as JSON
                    taxes_applied_json = None
                    if taxes_applied:
                        taxes_applied_json = json.dumps([
                            {
                                'tax_id': tax.tax_id,
                                'tax_name': tax.tax_name,
                                'rate': float(tax.rate),
                                'is_inclusive': tax.is_inclusive,
                                'amount': float(tax.amount)
                            }
                            for tax in taxes_applied
                        ])
                    
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_SALES_ITEMS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, sale_id, batch_id,
                         product_name, product_id, description, quantity,
                         base_selling_price, actual_price, price_after_pricing_rule, price_after_tax, final_price,
                         tax_rate, is_inclusive, tax_amount, taxes_applied, line_total,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            sale_item_id, tenant_id, org_id, bus_id, loc_id, sale_id, first_batch_id,
                            product_name, product_id, item.description, float(item.quantity),
                            StoreSalesService._round_money(base_selling_price), StoreSalesService._round_money(actual_price), StoreSalesService._round_money(price_after_pricing_rule), 
                            StoreSalesService._round_money(price_after_tax), StoreSalesService._round_money(final_price),
                            StoreSalesService._round_money(tax_rate), is_inclusive, StoreSalesService._round_money(tax_amount), taxes_applied_json, StoreSalesService._round_money(line_total),
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    sale_item_result = cursor.fetchone()
                    
                    if sale_item_result:
                        processed_sale_items.append(dict(sale_item_result))

                # Process payments if provided (skip if explicitly ON_HOLD)
                payments_list = []
                if data.payments and not is_explicitly_on_hold:
                    logger.info(f"Processing {len(data.payments)} payment(s) for sale {sale_id}")
                    for payment_data in data.payments:
                        # Validate payment method
                        valid_payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'GIFT_CARD', 'OTHERS']
                        if payment_data.payment_method not in valid_payment_methods:
                            error_msg = f"Invalid payment method. Must be one of: {', '.join(valid_payment_methods)}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)

                        # Handle gift card payment
                        payment_gift_card_id = None
                        if payment_data.payment_method == 'GIFT_CARD':
                            if not gift_card_id:
                                raise ValueError("gift_card_code is required when payment_method is GIFT_CARD")
                            payment_gift_card_id = gift_card_id
                            
                            # Update gift card balance
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_GIFT_CARDS_TABLE}
                                SET current_balance = current_balance - %s,
                                    updated_by = %s
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                                RETURNING current_balance""",
                                (float(gift_card_amount_used), created_by, gift_card_id, tenant_id, org_id, bus_id),
                            )
                            updated_gift_card = cursor.fetchone()
                            if not updated_gift_card:
                                raise ValueError("Failed to update gift card balance")
                            
                            new_balance = Decimal(str(updated_gift_card['current_balance']))
                            
                            # Update gift card status if balance is 0
                            if new_balance <= 0:
                                cursor.execute(
                                    f"""UPDATE {db_settings.MSG_GIFT_CARDS_TABLE}
                                    SET status = 'USED', updated_by = %s
                                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                    (created_by, gift_card_id, tenant_id, org_id, bus_id),
                                )
                            
                            # Create gift card transaction record
                            transaction_id = Helper.generate_unique_identifier(prefix="gft")
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_GIFT_CARD_TRANSACTIONS_TABLE}
                                (id, tenant_id, org_id, bus_id, loc_id, gift_card_id, transaction_type,
                                 amount, balance_before, balance_after, sale_id, description, cdate, ctime, cdatetime, created_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                (
                                    transaction_id, tenant_id, org_id, bus_id, loc_id, gift_card_id, 'REDEMPTION',
                                    float(gift_card_amount_used), float(gift_card_obj.current_balance), float(new_balance),
                                    sale_id, f"Gift card used for sale {sale_number}",
                                    cdate, ctime, cdatetime, created_by
                                ),
                            )

                        # Create payment - payment_status is automatically set to 'SUCCESS'
                        payment_id = Helper.generate_unique_identifier(prefix="pay")
                        paid_amount_value = StoreSalesService._round_money(payment_data.paid_amount)
                        if payment_data.payment_method == 'GIFT_CARD':
                            paid_amount_value = StoreSalesService._round_money(gift_card_amount_used)
                        
                        payment_status = 'SUCCESS'  # Automatically set by the app
                        logger.info(
                            f"Inserting payment: id={payment_id}, sale_id={sale_id}, method={payment_data.payment_method}, "
                            f"status={payment_status}, amount={paid_amount_value}, gift_card_id={payment_gift_card_id}"
                        )
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_SALES_PAYMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, sale_id, payment_method,
                             payment_status, paid_amount, gift_card_id, description, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                payment_id, tenant_id, org_id, bus_id, loc_id, sale_id,
                                payment_data.payment_method, payment_status,
                                paid_amount_value, payment_gift_card_id, payment_data.description,
                                cdate, ctime, cdatetime, created_by
                            ),
                        )
                        payment_result = cursor.fetchone()
                        if payment_result:
                            payments_list.append(dict(payment_result))
                            logger.info(f"Successfully inserted payment {payment_id} for sale {sale_id}")
                        else:
                            logger.error(f"Failed to insert payment {payment_id} for sale {sale_id} - no result returned")
                
                # Create promo code usage record if promo code was used
                if promo_code_id and promo_discount_amount > 0:
                    usage_id = Helper.generate_unique_identifier(prefix="pcu")
                    # Use verified subtotal_before_discount if available (accurate: includes tax on undiscounted prices)
                    # Otherwise fall back to approximate calculation
                    if data.verified_subtotal_before_discount is not None:
                        sale_total_before = Decimal(str(data.verified_subtotal_before_discount))
                    else:
                        sale_total_before = final_total_for_payments + promo_discount_amount  # Approximate
                    sale_total_after = final_total_for_payments  # Total after discount
                    
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PROMO_CODE_USAGE_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, promo_code_id, sale_id, customer_id,
                         discount_amount, sale_total_before_discount, sale_total_after_discount,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            usage_id, tenant_id, org_id, bus_id, loc_id, promo_code_id, sale_id, data.customer_id,
                            float(promo_discount_amount), float(sale_total_before), float(sale_total_after),
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    
                    # Update promo code usage count
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PROMO_CODES_TABLE}
                        SET current_usage_count = current_usage_count + 1,
                            updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (created_by, promo_code_id, tenant_id, org_id, bus_id),
                    )
                
                # Create affiliate referral record if affiliate code was provided
                if affiliate_id:
                    referral_id = Helper.generate_unique_identifier(prefix="afr")
                    conversion_status = 'PENDING'
                    conversion_date = None
                    
                    # If sale is fully paid, mark as converted
                    if status == 'PAID':
                        conversion_status = 'CONVERTED'
                        conversion_date = cdatetime
                    
                    # Calculate commission (only if converted)
                    commission_amount = Decimal('0')
                    if conversion_status == 'CONVERTED':
                        # Get affiliate details for commission calculation
                        cursor.execute(
                            f"""SELECT commission_rate, commission_type, fixed_commission_amount
                            FROM {db_settings.MSG_AFFILIATES_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (affiliate_id, tenant_id, org_id, bus_id),
                        )
                        affiliate_data = cursor.fetchone()
                        if affiliate_data:
                            if affiliate_data['commission_type'] == 'PERCENTAGE':
                                commission_rate = Decimal(str(affiliate_data['commission_rate']))
                                commission_amount = (final_total_for_payments * commission_rate) / Decimal('100')
                            else:
                                commission_amount = Decimal(str(affiliate_data['fixed_commission_amount'] or 0))
                    
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_AFFILIATE_REFERRALS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, affiliate_id, customer_id, sale_id,
                         referral_date, conversion_date, conversion_status, sale_amount, commission_amount,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            referral_id, tenant_id, org_id, bus_id, loc_id, affiliate_id, data.customer_id, sale_id,
                            cdatetime, conversion_date, conversion_status, float(final_total_for_payments), float(commission_amount),
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    
                    # Update affiliate statistics
                    if conversion_status == 'CONVERTED':
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_AFFILIATES_TABLE}
                            SET total_referrals = total_referrals + 1,
                                total_conversions = total_conversions + 1,
                                total_commission_earned = total_commission_earned + %s,
                                updated_by = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (float(commission_amount), created_by, affiliate_id, tenant_id, org_id, bus_id),
                        )
                        
                        # Create commission record
                        commission_id = Helper.generate_unique_identifier(prefix="afc")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_AFFILIATE_COMMISSIONS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, affiliate_id, referral_id, sale_id,
                             commission_amount, payment_status, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                commission_id, tenant_id, org_id, bus_id, loc_id, affiliate_id, referral_id, sale_id,
                                float(commission_amount), 'PENDING',
                                cdate, ctime, cdatetime, created_by
                            ),
                        )
                    else:
                        # Just increment referrals count (conversion will happen when sale is paid)
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_AFFILIATES_TABLE}
                            SET total_referrals = total_referrals + 1,
                                updated_by = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (created_by, affiliate_id, tenant_id, org_id, bus_id),
                        )
                elif is_explicitly_on_hold:
                    logger.info(f"Sale {sale_id} is ON_HOLD - payments skipped (will be null)")
                else:
                    logger.info(f"No payments provided for sale {sale_id}")

                # For DEPOSIT mode: Check if fully paid and move inventory if needed
                # Skip this if explicitly ON_HOLD or if inventory was already moved above
                if not is_explicitly_on_hold and not should_move_inventory and sale_mode == 'DEPOSIT' and paid_amount >= final_total_for_payments and fulfillment_status == 'PENDING':
                    # Now move inventory since fully paid
                    for item_data in sale_items:
                        product_id = item_data['product_id']
                        required_qty = item_data['required_qty']
                        batches = item_data['batches']
                        
                        remaining_qty = required_qty
                        for batch in batches:
                            if remaining_qty <= 0:
                                break

                            batch_id = batch['purchase_batche_id']
                            batch_location_id = batch['id']
                            batch_qty = Decimal(str(batch['qty']))
                            
                            qty_to_deduct = min(remaining_qty, batch_qty)

                            # Update batch location (deduct quantity)
                            new_batch_qty = batch_qty - qty_to_deduct
                            cursor.execute(
                            f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            SET qty = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (float(new_batch_qty), batch_location_id, tenant_id, org_id, bus_id),
                        )

                            # Create product movement
                            movement_id = Helper.generate_unique_identifier(prefix="mov")
                            cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                             movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                movement_id, tenant_id, org_id, bus_id, product_id,
                                    batch_id, 'STORE', loc_id,
                                    'OUT', float(qty_to_deduct),
                                'SALE', sale_id,
                                cdate, ctime, cdatetime, created_by
                            ),
                            )

                            remaining_qty -= qty_to_deduct
                        
                        # Validate that all required quantity was deducted
                        if remaining_qty > 0:
                            total_deducted = required_qty - remaining_qty
                            # Get product name for error message
                            cursor.execute(
                                f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (product_id, tenant_id, org_id, bus_id),
                            )
                            product = cursor.fetchone()
                            product_name = product.get('name', product_id) if product else product_id
                            
                            error_message = (
                                f"Insufficient inventory during DEPOSIT sale fulfillment for product '{product_name}' (ID: {product_id}). "
                                f"Required: {float(required_qty)} units, "
                                f"Successfully deducted: {float(total_deducted)} units, "
                                f"Remaining needed: {float(remaining_qty)} units. "
                                f"This may occur if inventory was consumed by another transaction. "
                                f"Please check inventory levels and try again."
                            )
                            logger.error(error_message)
                            raise ValueError(error_message)

                        # Update store product current_qty (after all batches for this item)
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                            SET current_qty = current_qty - %s, updated_by = %s
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND loc_id = %s AND product_id = %s""",
                            (float(required_qty), created_by, tenant_id, org_id, bus_id, loc_id, product_id),
                        )

                    # Update fulfillment status to FULFILLED and set fulfillment_date_time
                    fulfillment_status = 'FULFILLED'
                    fulfillment_date_time = cdatetime
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_SALES_TABLE}
                        SET fulfillment_status = %s, status = %s, fulfillment_date_time = %s, updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (fulfillment_status, status, fulfillment_date_time, created_by, sale_id, tenant_id, org_id, bus_id, loc_id),
                        )

                # Get sale with customer name
                cursor.execute(
                    f"""SELECT s.*, c.fullname as customer_name
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    WHERE s.id = %s AND s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale_with_customer = cursor.fetchone()

                sale_dict = dict(sale_with_customer) if sale_with_customer else dict(sale_result)
                sale_dict['customer_name'] = sale_dict.get('customer_name') or None
                # Convert items to DTOs, ensuring is_inclusive is bool and mapping final_price to price
                items_list = []
                for item in processed_sale_items:
                    item_dict = dict(item) if not isinstance(item, dict) else item
                    items_list.append(StoreSalesService._convert_item_to_dto(item_dict))
                sale_dict['items'] = items_list
                sale_dict['payments'] = [PaymentReadBase(**payment) for payment in payments_list]
                sale_dict['total_paid'] = StoreSalesService._round_money(paid_amount)
                sale_dict['sale_total'] = StoreSalesService._round_money(final_total_for_payments)

                sale_read = CreateSaleServiceReadDto(**sale_dict)

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-sales",
                        resource_id=sale_id,
                        action="create",
                        old_data=None,
                        new_data=sale_dict,
                        description=f"Sale {sale_number} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as log_db_err:
                    logger.error(f"Database error during activity logging: {log_db_err}", exc_info=True)
                    raise
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Sale created successfully: {sale_id}",
                    extra={
                        "extra_fields": {
                            "sale_id": sale_id,
                            "sale_number": sale_number,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Sale created successfully",
                    data=[sale_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating sale: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating sale: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create sale: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_sale(
        sale_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetSaleServiceReadDto]:
        """Get a single sale by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT s.*, c.fullname as customer_name
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    WHERE s.id = %s AND s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
                    AND s.deleted_by IS NULL""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale = cursor.fetchone()

                if not sale:
                    return Respons(
                        success=False,
                        detail="Sale not found",
                        error="NOT_FOUND",
                    )

                # Get sale items
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    ORDER BY cdatetime ASC""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                items = cursor.fetchall()

                # Get payments (excluding refunded)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND deleted_at IS NULL
                    ORDER BY cdatetime ASC""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                payments = cursor.fetchall()

                # Use fields from sale table (total_amount, paid_amount, balance_amount)
                sale_dict = dict(sale)
                sale_dict['customer_name'] = sale_dict.get('customer_name') or None
                # Convert items to DTOs, ensuring is_inclusive is bool and mapping final_price to price
                items_list = []
                for item in items:
                    item_dict = dict(item)
                    items_list.append(StoreSalesService._convert_item_to_dto(item_dict))
                sale_dict['items'] = items_list
                sale_dict['payments'] = [PaymentReadBase(**dict(payment)) for payment in payments]
                # Use total_amount, paid_amount, balance_amount from table
                sale_dict['total_paid'] = StoreSalesService._round_money(sale_dict.get('paid_amount', 0))
                sale_dict['sale_total'] = StoreSalesService._round_money(sale_dict.get('total_amount', 0))

                sale_read = GetSaleServiceReadDto(**sale_dict)

                return Respons(
                    success=True,
                    detail="Sale retrieved successfully",
                    data=[sale_read],
                )

        except Exception as e:
            logger.error(f"Error getting sale: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get sale: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_sales(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        sale_mode: Optional[str] = None,
        fulfillment_status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[GetSalesServiceReadDto]:
        """Get list of sales with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "s.tenant_id = %s",
                    "s.org_id = %s",
                    "s.bus_id = %s",
                    "s.loc_id = %s",
                    "s.deleted_by IS NULL"
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if customer_id:
                    where_conditions.append("s.customer_id = %s")
                    params.append(customer_id)

                if status:
                    where_conditions.append("s.status = %s")
                    params.append(status)

                if sale_mode:
                    where_conditions.append("s.sale_mode = %s")
                    params.append(sale_mode)

                if fulfillment_status:
                    where_conditions.append("s.fulfillment_status = %s")
                    params.append(fulfillment_status)

                if from_date:
                    where_conditions.append("s.sale_date >= %s")
                    params.append(from_date)

                if to_date:
                    where_conditions.append("s.sale_date <= %s")
                    params.append(to_date)

                if search:
                    where_conditions.append(
                        "(s.sale_number ILIKE %s OR c.fullname ILIKE %s)"
                    )
                    search_param = f"%{search}%"
                    params.extend([search_param, search_param])

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"""SELECT COUNT(*) as total
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    WHERE {where_clause}""",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Get paginated sales
                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT s.*, c.fullname as customer_name
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    WHERE {where_clause}
                    ORDER BY s.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                sales = cursor.fetchall()

                # Get items for each sale
                sale_ids = [sale['id'] for sale in sales]
                items_by_sale = {}
                if sale_ids:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                        WHERE sale_id = ANY(%s) AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        ORDER BY cdatetime ASC""",
                        (sale_ids, tenant_id, org_id, bus_id, loc_id),
                    )
                    all_items = cursor.fetchall()
                    
                    for item in all_items:
                        sale_id = item['sale_id']
                        if sale_id not in items_by_sale:
                            items_by_sale[sale_id] = []
                        item_dict = dict(item)
                        # Use helper method to properly convert item (handles taxes_applied parsing)
                        items_by_sale[sale_id].append(StoreSalesService._convert_item_to_dto(item_dict))

                # Get payments for each sale
                payments_by_sale = {}
                total_paid_by_sale = {}
                if sale_ids:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                        WHERE sale_id = ANY(%s) AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND deleted_at IS NULL
                        ORDER BY cdatetime ASC""",
                        (sale_ids, tenant_id, org_id, bus_id, loc_id),
                    )
                    all_payments = cursor.fetchall()
                    
                    for payment in all_payments:
                        sale_id = payment['sale_id']
                        if sale_id not in payments_by_sale:
                            payments_by_sale[sale_id] = []
                        payments_by_sale[sale_id].append(PaymentReadBase(**dict(payment)))

                sales_list = []
                for sale in sales:
                    sale_id = sale['id']
                    sale_dict = dict(sale)
                    sale_dict['customer_name'] = sale_dict.get('customer_name') or None
                    sale_dict['items'] = items_by_sale.get(sale_id, [])
                    sale_dict['payments'] = payments_by_sale.get(sale_id, [])
                    
                    # Use fields from sale table (total_amount, paid_amount, balance_amount)
                    sale_dict['sale_total'] = StoreSalesService._round_money(sale_dict.get('total_amount', 0))
                    sale_dict['total_paid'] = StoreSalesService._round_money(sale_dict.get('paid_amount', 0))
                    
                    sales_list.append(sale_dict)

                sales_read = GetSalesServiceReadDto(
                    sales=[SaleReadBase(**sale) for sale in sales_list],
                    total=total,
                    page=page,
                    size=size
                )

                return Respons(
                    success=True,
                    detail="Sales retrieved successfully",
                    data=[sales_read],
                )

        except Exception as e:
            logger.error(f"Error getting sales: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get sales: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_sale(
        data: UpdateSaleServiceWriteDto,
        sale_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[UpdateSaleServiceReadDto]:
        """Update a sale"""
        logger.info(
            f"Processing sale update: {sale_id}",
            extra={
                "extra_fields": {
                    "sale_id": sale_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing sale
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_sale = cursor.fetchone()

                if not existing_sale:
                    return Respons(
                        success=False,
                        detail="Sale not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_sale)
                sale_dict = dict(existing_sale)

                # Check if sale can be updated (can't update items if paid or cancelled)
                if data.items is not None:
                    if sale_dict['status'] in ['PAID', 'CANCELLED']:
                        return Respons(
                            success=False,
                            detail=f"Cannot update items for a sale with status {sale_dict['status']}",
                            error="INVALID_SALE_STATUS",
                        )

                # Validate customer if provided
                if data.customer_id is not None:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.customer_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Customer {data.customer_id} not found",
                            error="CUSTOMER_NOT_FOUND",
                        )

                # Build update query
                update_fields = []
                params = []

                if data.customer_id is not None:
                    update_fields.append("customer_id = %s")
                    params.append(data.customer_id)

                if data.sale_date is not None:
                    try:
                        sale_date = datetime.strptime(data.sale_date, "%Y-%m-%d").date()
                        update_fields.append("sale_date = %s")
                        params.append(sale_date)
                    except ValueError:
                        return Respons(
                            success=False,
                            detail="Invalid sale_date format. Expected YYYY-MM-DD",
                            error="INVALID_DATE_FORMAT",
                        )

                if data.status is not None:
                    update_fields.append("status = %s")
                    params.append(data.status)

                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)

                # Handle items update if provided (before updating sale table)
                if data.items is not None:
                    # Check if sale can be updated (can't update items if paid or cancelled)
                    if sale_dict['status'] in ['PAID', 'CANCELLED']:
                        return Respons(
                            success=False,
                            detail=f"Cannot update items for a sale with status {sale_dict['status']}",
                            error="INVALID_SALE_STATUS",
                        )

                    # Get existing items
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                        WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (sale_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    existing_items = cursor.fetchall()

                    # Restore inventory for existing items
                    for existing_item in existing_items:
                        item_dict = dict(existing_item)
                        product_id = item_dict['product_id']
                        quantity = Decimal(str(item_dict['quantity']))
                        batch_id = item_dict.get('batch_id')

                        # Restore to batch location
                        if batch_id:
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                                SET qty = qty + %s
                                WHERE purchase_batche_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s 
                                AND loc_id = %s AND location_type = 'STORE'""",
                                (float(quantity), batch_id, tenant_id, org_id, bus_id, loc_id),
                            )

                        # Restore store product current_qty
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                            SET current_qty = current_qty + %s, updated_by = %s
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND loc_id = %s AND product_id = %s""",
                            (float(quantity), updated_by, tenant_id, org_id, bus_id, loc_id, product_id),
                        )

                    # Delete existing items
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                        WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (sale_id, tenant_id, org_id, bus_id, loc_id),
                    )

                    # Validate and process new items (similar to create_sale)
                    if not data.items:
                        return Respons(
                            success=False,
                            detail="Items list cannot be empty. Provide at least one item.",
                            error="VALIDATION_ERROR",
                        )

                    # Check inventory availability for all new items
                    inventory_checks = {}
                    for item in data.items:
                        is_available, available_qty, batches = StoreSalesService._check_inventory_availability(
                            tenant_id, org_id, bus_id, loc_id, item.product_id, item.quantity, cursor
                        )
                        
                        if not is_available:
                            # Get product name for error message
                            cursor.execute(
                                f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (item.product_id, tenant_id, org_id, bus_id),
                            )
                            product = cursor.fetchone()
                            product_name = product.get('name', item.product_id) if product else item.product_id
                            
                            return Respons(
                                success=False,
                                detail=f"Insufficient inventory for product '{product_name}'. Required: {item.quantity}, Available: {available_qty}",
                                error="INSUFFICIENT_INVENTORY",
                            )
                        
                        inventory_checks[item.product_id] = {
                            'batches': batches,
                            'required_qty': Decimal(str(item.quantity))
                        }

                    # Process each new sale item
                    cdate = Helper.current_date_time()["cdate"]
                    ctime = Helper.current_date_time()["ctime"]
                    cdatetime = Helper.current_date_time()["cdatetime"]
                    
                    for item in data.items:
                        product_id = item.product_id
                        required_qty = inventory_checks[product_id]['required_qty']
                        batches = inventory_checks[product_id]['batches']
                        
                        # Get product name
                        cursor.execute(
                            f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (product_id, tenant_id, org_id, bus_id),
                        )
                        product = cursor.fetchone()
                        product_name = product.get('name', 'Unknown Product') if product else 'Unknown Product'

                        # Deduct from batches in FIFO order
                        remaining_qty = required_qty
                        batch_allocations = []

                        for batch in batches:
                            if remaining_qty <= 0:
                                break

                            batch_id = batch['purchase_batche_id']
                            batch_location_id = batch['id']
                            batch_qty = Decimal(str(batch['qty']))
                            
                            qty_to_deduct = min(remaining_qty, batch_qty)

                            # Update batch location (deduct quantity)
                            new_batch_qty = batch_qty - qty_to_deduct
                            cursor.execute(
                            f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            SET qty = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (float(new_batch_qty), batch_location_id, tenant_id, org_id, bus_id),
                        )

                            batch_allocations.append({
                                'batch_id': batch_id,
                                'qty_deducted': float(qty_to_deduct)
                            })
                            remaining_qty -= qty_to_deduct

                        # Validate that all required quantity was deducted
                        if remaining_qty > 0:
                            total_deducted = required_qty - remaining_qty
                            error_message = (
                                f"Insufficient inventory during sale update for product '{product_name}' (ID: {product_id}). "
                                f"Required: {float(required_qty)} units, "
                                f"Successfully deducted: {float(total_deducted)} units, "
                                f"Remaining needed: {float(remaining_qty)} units. "
                                f"This may occur if inventory was consumed by another transaction. "
                                f"Please check inventory levels and try again."
                            )
                            logger.error(error_message)
                            raise ValueError(error_message)

                        # Calculate prices and taxes for the item
                        first_batch_id = batch_allocations[0]['batch_id'] if batch_allocations else None
                        
                        # Get base_selling_price from the first batch if available, otherwise use item value
                        if item.base_selling_price is not None:
                            base_selling_price = Decimal(str(item.base_selling_price))
                        elif batches and len(batches) > 0:
                            base_selling_price = Decimal(str(batches[0].get('base_selling_price', 0))) if batches[0].get('base_selling_price') else Decimal('0')
                        else:
                            base_selling_price = Decimal('0')
                        
                        # Use only values from item if provided, do not calculate anything
                        actual_price = Decimal(str(item.actual_price)) if item.actual_price is not None else Decimal('0')
                        price_after_pricing_rules = Decimal(str(item.price_after_pricing_rule)) if item.price_after_pricing_rule is not None else Decimal('0')
                        
                        # Get price_after_tax and final_price from item
                        if item.final_price is not None:
                            final_price = Decimal(str(item.final_price))
                            price_after_tax = final_price if item.price_after_tax is None else Decimal(str(item.price_after_tax))
                        elif item.price_after_tax is not None:
                            price_after_tax = Decimal(str(item.price_after_tax))
                            final_price = price_after_tax
                        else:
                            final_price = Decimal('0')
                            price_after_tax = Decimal('0')
                        
                        # Get taxes_applied from item (for storing, not for calculation)
                        taxes_applied = item.taxes_applied if item.taxes_applied else []
                        
                        # Use tax_rate and tax_amount directly from input (no calculation)
                        tax_rate = Decimal(str(item.tax_rate)) if item.tax_rate is not None else Decimal('0')
                        item_tax_amount = Decimal(str(item.tax_amount)) if item.tax_amount is not None else Decimal('0')
                        # is_inclusive - use from input or from taxes_applied
                        is_inclusive = item.is_inclusive if item.is_inclusive is not None else (any(tax.is_inclusive for tax in taxes_applied) if taxes_applied else False)
                        
                        # Calculate line_total from final_price
                        line_total = final_price * Decimal(str(item.quantity)) if final_price > 0 else Decimal('0')

                        # Prepare taxes_applied as JSON
                        taxes_applied_json = None
                        if taxes_applied:
                            taxes_applied_json = json.dumps([
                                {
                                    'tax_id': tax.tax_id,
                                    'tax_name': tax.tax_name,
                                    'rate': float(tax.rate),
                                    'is_inclusive': tax.is_inclusive,
                                    'amount': float(tax.amount)
                                }
                                for tax in taxes_applied
                            ])

                        # Create new sale item
                        sale_item_id = Helper.generate_unique_identifier(prefix="sali")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_SALES_ITEMS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, sale_id, batch_id,
                             product_name, product_id, description, quantity,
                             base_selling_price, actual_price, price_after_pricing_rule, price_after_tax, final_price,
                             tax_rate, is_inclusive, tax_amount, taxes_applied, line_total,
                             cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                sale_item_id, tenant_id, org_id, bus_id, loc_id, sale_id, first_batch_id,
                                product_name, product_id, item.description, float(item.quantity),
                                StoreSalesService._round_money(base_selling_price), StoreSalesService._round_money(actual_price), StoreSalesService._round_money(price_after_pricing_rules), 
                                StoreSalesService._round_money(price_after_tax), StoreSalesService._round_money(final_price),
                                StoreSalesService._round_money(tax_rate), is_inclusive, StoreSalesService._round_money(item_tax_amount), taxes_applied_json, StoreSalesService._round_money(line_total),
                                cdate, ctime, cdatetime, updated_by
                            ),
                        )

                        # Update store product current_qty
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                            SET current_qty = current_qty - %s, updated_by = %s
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND loc_id = %s AND product_id = %s""",
                            (float(required_qty), updated_by, tenant_id, org_id, bus_id, loc_id, product_id),
                        )

                        # Create product movements for each batch deduction
                        for batch_allocation in batch_allocations:
                            movement_id = Helper.generate_unique_identifier(prefix="mov")
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                                (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                                 movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING *""",
                                (
                                    movement_id, tenant_id, org_id, bus_id, product_id,
                                    batch_allocation['batch_id'], 'STORE', loc_id,
                                    'OUT', float(batch_allocation['qty_deducted']),
                                    'SALE_UPDATE', sale_id,
                                    cdate, ctime, cdatetime, updated_by
                                ),
                            )

                if not update_fields and data.items is None and data.payments is None:
                    return Respons(
                        success=False,
                        detail="No fields to update",
                        error="VALIDATION_ERROR",
                    )

                if update_fields:
                    update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([sale_id, tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_SALES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_sale = cursor.fetchone()

                if not updated_sale:
                    return Respons(
                        success=False,
                        detail="Failed to update sale",
                        error="INTERNAL_ERROR",
                        )
                else:
                    # If only items/payments updated, fetch current sale
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SALES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (sale_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    updated_sale = cursor.fetchone()

                # Process payments if provided
                if data.payments:
                    cdate = Helper.current_date_time()["cdate"]
                    ctime = Helper.current_date_time()["ctime"]
                    cdatetime = Helper.current_date_time()["cdatetime"]
                    
                    for payment_data in data.payments:
                        # Validate payment method
                        valid_payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'OTHERS']
                        if payment_data.payment_method not in valid_payment_methods:
                            return Respons(
                                success=False,
                                detail=f"Invalid payment method. Must be one of: {', '.join(valid_payment_methods)}",
                                error="INVALID_PAYMENT_METHOD",
                            )

                        # Create payment - payment_status is automatically set to 'SUCCESS'
                        payment_id = Helper.generate_unique_identifier(prefix="pay")
                        payment_status = 'SUCCESS'  # Automatically set by the app
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_SALES_PAYMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, sale_id, payment_method,
                             payment_status, paid_amount, description, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                payment_id, tenant_id, org_id, bus_id, loc_id, sale_id,
                                payment_data.payment_method, payment_status,
                                StoreSalesService._round_money(payment_data.paid_amount), payment_data.description,
                                cdate, ctime, cdatetime, updated_by
                            ),
                            )

                # If items were updated, recalculate total_amount from items
                if data.items is not None:
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(line_total), 0) as total_amount
                        FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                        WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (sale_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    total_amount_result = cursor.fetchone()
                    new_total_amount = Decimal(str(total_amount_result['total_amount'])) if total_amount_result else Decimal('0')
                    
                    # Update total_amount in sale table
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_SALES_TABLE}
                        SET total_amount = %s, updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (StoreSalesService._round_money(new_total_amount), updated_by, sale_id, tenant_id, org_id, bus_id, loc_id),
                    )

                # Update sale status based on total payments (this also updates paid_amount and balance_amount)
                total_paid, new_status, new_fulfillment_status = StoreSalesService._calculate_and_update_sale_status(
                    cursor, sale_id, tenant_id, org_id, bus_id, loc_id, updated_by
                    )

                # Get sale with customer name and items
                cursor.execute(
                    f"""SELECT s.*, c.fullname as customer_name
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    WHERE s.id = %s AND s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale_with_customer = cursor.fetchone()

                # Get sale items
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    ORDER BY cdatetime ASC""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                items = cursor.fetchall()

                # Convert items to DTOs, ensuring is_inclusive is bool and mapping final_price to price
                items_list = []
                for item in items:
                    try:
                        item_dict = dict(item)
                        # Map final_price from database to price for DTO (required field)
                        if 'price' not in item_dict:
                            item_dict['price'] = StoreSalesService._round_money(item_dict.get('final_price', 0.0) or 0.0)
                        
                        # Parse taxes_applied from JSON
                        taxes_applied_list = []
                        if item_dict.get('taxes_applied'):
                            try:
                                if isinstance(item_dict['taxes_applied'], str):
                                    taxes_applied_list = json.loads(item_dict['taxes_applied'])
                                elif isinstance(item_dict['taxes_applied'], list):
                                    taxes_applied_list = item_dict['taxes_applied']
                                # Convert to TaxAppliedItem objects
                                from src.entities.store_sales.store_sales_base import TaxAppliedItem
                                item_dict['taxes_applied'] = [TaxAppliedItem(**tax) for tax in taxes_applied_list]
                                # tax_rate and tax_amount are already stored in the database, no need to calculate from taxes_applied
                                # Just ensure they exist (defaults already set from database query)
                            except Exception as e:
                                logger.warning(f"Error parsing taxes_applied for item: {str(e)}")
                                item_dict['taxes_applied'] = []
                        else:
                            item_dict['taxes_applied'] = []
                        
                        items_list.append(SaleItemReadBase(**item_dict))
                    except Exception as e:
                        logger.warning(f"Error converting sale item to DTO: {str(e)}", exc_info=True)
                        # Continue with other items even if one fails

                # Get payments (excluding refunded)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND deleted_at IS NULL
                    ORDER BY cdatetime ASC""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                payments = cursor.fetchall()

                # Convert payments to DTOs
                payments_list = []
                for payment in payments:
                    try:
                        payments_list.append(PaymentReadBase(**dict(payment)))
                    except Exception as e:
                        logger.warning(f"Error converting payment to DTO: {str(e)}", exc_info=True)
                        # Continue with other payments even if one fails

                sale_dict = dict(sale_with_customer) if sale_with_customer else dict(updated_sale)
                sale_dict['customer_name'] = sale_dict.get('customer_name') or None
                sale_dict['items'] = items_list
                sale_dict['payments'] = payments_list
                # Use fields from sale table
                sale_dict['total_paid'] = StoreSalesService._round_money(sale_dict.get('paid_amount', 0))
                sale_dict['sale_total'] = StoreSalesService._round_money(sale_dict.get('total_amount', 0))

                sale_read = UpdateSaleServiceReadDto(**sale_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SALES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (sale_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else sale_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-sales",
                        resource_id=sale_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Sale {sale_dict.get('sale_number', sale_id)} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as log_db_err:
                    logger.error(f"Database error during activity logging: {log_db_err}", exc_info=True)
                    raise
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Sale updated successfully: {sale_id}")

                return Respons(
                    success=True,
                    detail="Sale updated successfully",
                    data=[sale_read],
                )

        except Exception as e:
            logger.error(f"Error updating sale: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update sale: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def cancel_sale(
        data: CancelSaleServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        cancelled_by: str
    ) -> Respons[CancelSaleServiceReadDto]:
        """Cancel a sale and restore inventory"""
        logger.info(
            f"Processing sale cancellation: {data.sale_id}",
            extra={
                "extra_fields": {
                    "sale_id": data.sale_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get sale
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale = cursor.fetchone()

                if not sale:
                    return Respons(
                        success=False,
                        detail="Sale not found",
                        error="NOT_FOUND",
                    )

                sale_dict = dict(sale)

                if sale_dict['status'] == 'CANCELLED':
                    return Respons(
                        success=False,
                        detail="Sale is already cancelled",
                        error="ALREADY_CANCELLED",
                    )

                # Get sale items
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                items = cursor.fetchall()

                # Restore inventory using the original OUT movements (preserves correct batch split)
                # First get all OUT movements for this sale
                cursor.execute(
                    f"""SELECT product_id, batch_id, qty
                    FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    WHERE reference_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND movement_type = 'OUT' AND reason LIKE 'SALE%'""",
                    (data.sale_id, tenant_id, org_id, bus_id),
                )
                original_movements = cursor.fetchall()

                dt_cancel = Helper.current_date_time()
                cdate = dt_cancel["cdate"]
                ctime = dt_cancel["ctime"]
                cdatetime = dt_cancel["cdatetime"]

                if original_movements:
                    # Restore using exact batch allocations from original movements
                    restored_products = set()
                    for mov in original_movements:
                        mov_product_id = mov['product_id']
                        mov_batch_id = mov['batch_id']
                        mov_qty = Decimal(str(mov['qty']))

                        # Restore to the exact batch location
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            SET qty = qty + %s
                            WHERE purchase_batche_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                            AND loc_id = %s AND location_type = 'STORE'""",
                            (float(mov_qty), mov_batch_id, tenant_id, org_id, bus_id, loc_id),
                        )

                        # Create reverse movement
                        movement_id = Helper.generate_unique_identifier(prefix="mov")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                             movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                movement_id, tenant_id, org_id, bus_id, mov_product_id,
                                mov_batch_id, 'STORE', loc_id,
                                'IN', float(mov_qty),
                                'SALE_CANCELLED', data.sale_id,
                                cdate, ctime, cdatetime, cancelled_by
                            ),
                        )

                        restored_products.add(mov_product_id)

                    # Restore store product current_qty once per product
                    for item in items:
                        item_dict = dict(item)
                        product_id = item_dict['product_id']
                        quantity = Decimal(str(item_dict['quantity']))
                        if product_id in restored_products:
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                                SET current_qty = current_qty + %s, updated_by = %s
                                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                                AND loc_id = %s AND product_id = %s""",
                                (float(quantity), cancelled_by, tenant_id, org_id, bus_id, loc_id, product_id),
                            )
                else:
                    # No movements found (sale was ON_HOLD, inventory was never deducted)
                    # Just log it — no inventory to restore
                    logger.info(f"No inventory movements found for sale {data.sale_id}. Inventory was not deducted (likely ON_HOLD).")

                # Restore gift card balance if gift card was used
                gift_card_amount_used = Decimal(str(sale_dict.get('gift_card_amount_used') or 0))
                if gift_card_amount_used > 0:
                    # Find the gift card payment to get the gift card ID
                    cursor.execute(
                        f"""SELECT gift_card_id FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                        WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND payment_method = 'GIFT_CARD' AND deleted_at IS NULL
                        LIMIT 1""",
                        (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    gc_payment = cursor.fetchone()
                    if gc_payment and gc_payment.get('gift_card_id'):
                        # Restore balance and reactivate if it was marked USED
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_GIFT_CARDS_TABLE}
                            SET current_balance = current_balance + %s,
                                status = CASE WHEN status = 'USED' THEN 'ACTIVE' ELSE status END
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (float(gift_card_amount_used), gc_payment['gift_card_id'], tenant_id, org_id, bus_id),
                        )
                        logger.info(f"Restored gift card balance: {float(gift_card_amount_used)} for sale {data.sale_id}")

                # Reverse promo code usage if promo code was used
                promo_code_id = sale_dict.get('promo_code_id')
                if promo_code_id:
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PROMO_CODES_TABLE}
                        SET current_usage_count = GREATEST(current_usage_count - 1, 0),
                            updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (cancelled_by, promo_code_id, tenant_id, org_id, bus_id),
                    )
                    logger.info(f"Reversed promo code usage count for promo {promo_code_id} on sale {data.sale_id}")

                # Reverse affiliate referral and commission if affiliate was used
                affiliate_id = sale_dict.get('affiliate_id')
                if affiliate_id:
                    # Check if the referral was converted (commission was paid)
                    cursor.execute(
                        f"""SELECT id, conversion_status, commission_amount
                        FROM {db_settings.MSG_AFFILIATE_REFERRALS_TABLE}
                        WHERE sale_id = %s AND affiliate_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        LIMIT 1""",
                        (data.sale_id, affiliate_id, tenant_id, org_id, bus_id),
                    )
                    referral = cursor.fetchone()
                    if referral:
                        was_converted = referral['conversion_status'] == 'CONVERTED'
                        commission_amount = Decimal(str(referral.get('commission_amount') or 0))

                        # Update affiliate stats
                        if was_converted:
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_AFFILIATES_TABLE}
                                SET total_referrals = GREATEST(total_referrals - 1, 0),
                                    total_conversions = GREATEST(total_conversions - 1, 0),
                                    total_commission_earned = GREATEST(total_commission_earned - %s, 0),
                                    updated_by = %s
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (float(commission_amount), cancelled_by, affiliate_id, tenant_id, org_id, bus_id),
                            )
                        else:
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_AFFILIATES_TABLE}
                                SET total_referrals = GREATEST(total_referrals - 1, 0),
                                    updated_by = %s
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (cancelled_by, affiliate_id, tenant_id, org_id, bus_id),
                            )

                        # Mark referral as cancelled
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_AFFILIATE_REFERRALS_TABLE}
                            SET conversion_status = 'CANCELLED'
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (referral['id'], tenant_id, org_id, bus_id),
                        )

                        # Mark commission as cancelled
                        if was_converted:
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_AFFILIATE_COMMISSIONS_TABLE}
                                SET payment_status = 'CANCELLED'
                                WHERE sale_id = %s AND affiliate_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (data.sale_id, affiliate_id, tenant_id, org_id, bus_id),
                            )

                        logger.info(f"Reversed affiliate referral for affiliate {affiliate_id} on sale {data.sale_id}")

                # Update sale status and reset financial amounts
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_SALES_TABLE}
                    SET status = 'CANCELLED', paid_amount = 0, balance_amount = 0, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (cancelled_by, data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                updated_sale = cursor.fetchone()

                # Get sale with customer name and items
                cursor.execute(
                    f"""SELECT s.*, c.fullname as customer_name
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    WHERE s.id = %s AND s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale_with_customer = cursor.fetchone()

                # Get payments (excluding refunded)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND deleted_at IS NULL
                    ORDER BY cdatetime ASC""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                payments = cursor.fetchall()

                sale_dict = dict(sale_with_customer) if sale_with_customer else dict(updated_sale)
                sale_dict['customer_name'] = sale_dict.get('customer_name') or None
                # Convert items to DTOs, ensuring is_inclusive is bool and mapping final_price to price
                items_list = []
                for item in items:
                    item_dict = dict(item)
                    items_list.append(StoreSalesService._convert_item_to_dto(item_dict))
                sale_dict['items'] = items_list
                sale_dict['payments'] = [PaymentReadBase(**dict(payment)) for payment in payments]
                # Use fields from sale table
                sale_dict['total_paid'] = StoreSalesService._round_money(sale_dict.get('paid_amount', 0))
                sale_dict['sale_total'] = StoreSalesService._round_money(sale_dict.get('total_amount', 0))

                sale_read = CancelSaleServiceReadDto(**sale_dict)

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-sales",
                        resource_id=data.sale_id,
                        action="cancel",
                        old_data=dict(sale),
                        new_data=sale_dict,
                        description=f"Sale {sale_dict.get('sale_number', data.sale_id)} cancelled",
                        performed_by=cancelled_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as log_db_err:
                    logger.error(f"Database error during activity logging: {log_db_err}", exc_info=True)
                    raise
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Sale cancelled successfully: {data.sale_id}")

                return Respons(
                    success=True,
                    detail="Sale cancelled successfully",
                    data=[sale_read],
                )

        except Exception as e:
            logger.error(f"Error cancelling sale: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to cancel sale: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def _calculate_and_update_sale_status(
        cursor,
        sale_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> tuple[Decimal, str, str]:
        """
        Calculate total paid amount and update sale status based on payments.
        Handles fulfillment_status for DEPOSIT mode.
        Returns: (total_paid, new_status, new_fulfillment_status)
        """
        # Get sale info including sale_mode and current fulfillment_status
        cursor.execute(
            f"""SELECT total_amount, sale_mode, fulfillment_status
            FROM {db_settings.MSG_SALES_TABLE}
            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
            (sale_id, tenant_id, org_id, bus_id, loc_id),
        )
        sale_info = cursor.fetchone()
        if not sale_info:
            return Decimal('0'), 'ON_HOLD', 'PENDING'
        
        total_amount = Decimal(str(sale_info['total_amount'])) if sale_info.get('total_amount') else Decimal('0')
        sale_mode = sale_info.get('sale_mode', 'INSTANT')
        current_fulfillment = sale_info.get('fulfillment_status', 'PENDING')

        # Get total paid (only SUCCESS payments that are not refunded)
        cursor.execute(
            f"""SELECT COALESCE(SUM(paid_amount), 0) as total_paid
            FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
            WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
            AND payment_status = 'SUCCESS' AND deleted_at IS NULL""",
            (sale_id, tenant_id, org_id, bus_id, loc_id),
        )
        total_paid_result = cursor.fetchone()
        total_paid = Decimal(str(total_paid_result['total_paid'])) if total_paid_result else Decimal('0')

        # Calculate balance
        balance_amount = total_amount - total_paid

        # Determine new status and fulfillment_status based on sale_mode
        if sale_mode == 'INSTANT':
            # INSTANT mode: Full payment is REQUIRED to release inventory from ON_HOLD
            # Partial payments are allowed but inventory remains on hold until fully paid
            if total_paid >= total_amount:
                new_status = 'PAID'
                new_fulfillment_status = 'FULFILLED'  # Only fulfilled when fully paid
            elif total_paid > 0:
                new_status = 'PARTIALLY_PAID'
                new_fulfillment_status = 'PENDING'  # Inventory stays on hold with partial payment
            else:
                new_status = 'ON_HOLD'
                new_fulfillment_status = 'PENDING'
        elif sale_mode == 'DEPOSIT':
            if total_paid >= total_amount:
                new_status = 'PAID'
                new_fulfillment_status = 'FULFILLED'  # Now can fulfill
            elif total_paid > 0:
                new_status = 'PARTIALLY_PAID'
                new_fulfillment_status = 'PENDING'  # Still waiting for full payment
            else:
                new_status = 'ON_HOLD'
                new_fulfillment_status = 'PENDING'
        elif sale_mode == 'CREDIT':
            # For credit mode:
            # - If current_fulfillment is FULFILLED: goods already taken, just update status based on payment
            # - If current_fulfillment is PENDING: sale was ON_HOLD, goods not taken yet
            #   When payment is made, change to FULFILLED and move inventory
            if current_fulfillment == 'FULFILLED':
                # Goods already taken, just update payment status
                if total_paid >= total_amount:
                    new_status = 'PAID'
                elif total_paid > 0:
                    new_status = 'PARTIALLY_PAID'
                else:
                    new_status = 'ON_HOLD'
                new_fulfillment_status = 'FULFILLED'
            else:
                # Goods not taken yet (was ON_HOLD), move inventory when payment received
                if total_paid >= total_amount:
                    new_status = 'PAID'
                    new_fulfillment_status = 'FULFILLED'
                elif total_paid > 0:
                    new_status = 'PARTIALLY_PAID'
                    new_fulfillment_status = 'FULFILLED'  # For credit, goods taken when any payment is made
                else:
                    new_status = 'ON_HOLD'
                    new_fulfillment_status = 'PENDING'

        # Update sale with new amounts and status
        # Set fulfillment_date_time when fulfillment_status changes to FULFILLED
        fulfillment_date_time = None
        if new_fulfillment_status == 'FULFILLED' and current_fulfillment != 'FULFILLED':
            fulfillment_date_time = Helper.current_date_time()["cdatetime"]
        
        if fulfillment_date_time:
            cursor.execute(
                f"""UPDATE {db_settings.MSG_SALES_TABLE}
                SET status = %s, fulfillment_status = %s, paid_amount = %s, balance_amount = %s, 
                    fulfillment_date_time = %s, updated_by = %s
                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                (new_status, new_fulfillment_status, StoreSalesService._round_money(total_paid), StoreSalesService._round_money(balance_amount),
                 fulfillment_date_time, updated_by, sale_id, tenant_id, org_id, bus_id, loc_id),
            )
        else:
            cursor.execute(
                f"""UPDATE {db_settings.MSG_SALES_TABLE}
                SET status = %s, fulfillment_status = %s, paid_amount = %s, balance_amount = %s, updated_by = %s
                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                (new_status, new_fulfillment_status, StoreSalesService._round_money(total_paid), StoreSalesService._round_money(balance_amount), updated_by,
                 sale_id, tenant_id, org_id, bus_id, loc_id),
            )

        # Move inventory when fulfillment_status changes from PENDING to FULFILLED
        # This handles ON_HOLD sales that are being released via payment
        should_move_inventory = False
        if new_fulfillment_status == 'FULFILLED' and current_fulfillment == 'PENDING':
            if sale_mode == 'INSTANT':
                # INSTANT: Move inventory ONLY when FULLY paid (requires total_paid >= total_amount)
                # Partial payments do NOT release inventory for INSTANT mode
                should_move_inventory = (total_paid >= total_amount)
            elif sale_mode == 'DEPOSIT':
                # DEPOSIT: Move inventory when fully paid
                should_move_inventory = (total_paid >= total_amount)
            elif sale_mode == 'CREDIT':
                # CREDIT: Move inventory when any payment is made (goods taken immediately)
                should_move_inventory = (total_paid > 0)
        
        if should_move_inventory:
            # Safety check: Verify no inventory movements already exist for this sale
            # This prevents double movement in case of edge cases or manual fulfillment_status changes
            cursor.execute(
                f"""SELECT COUNT(*) as movement_count
                FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                WHERE reference_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                AND reason LIKE %s
                AND movement_type = 'OUT'""",
                (sale_id, tenant_id, org_id, bus_id, 'SALE%'),
            )
            movement_check = cursor.fetchone()
            existing_movements = movement_check['movement_count'] if movement_check else 0
            
            if existing_movements > 0:
                # Inventory already moved, skip movement but log warning
                logger.warning(
                    f"Inventory already moved for sale {sale_id}. "
                    f"Found {existing_movements} existing movements. Skipping duplicate movement."
                )
            else:
                # Get sale items to move inventory
                cursor.execute(
                    f"""SELECT si.*, pb.id as batch_id
                    FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                    INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb ON si.batch_id = pb.id
                    WHERE si.sale_id = %s AND si.tenant_id = %s AND si.org_id = %s AND si.bus_id = %s AND si.loc_id = %s""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale_items = cursor.fetchall()

                cdate = Helper.current_date_time()["cdate"]
                ctime = Helper.current_date_time()["ctime"]
                cdatetime = Helper.current_date_time()["cdatetime"]

                for item in sale_items:
                    product_id = item['product_id']
                    quantity = Decimal(str(item['quantity']))
                    batch_id = item['batch_id']

                    # Re-check inventory availability before moving (in case inventory was taken by another sale)
                    is_available, available_qty, batches_to_use = StoreSalesService._check_inventory_availability(
                        tenant_id, org_id, bus_id, loc_id, product_id, float(quantity), cursor
                    )
                    
                    if not is_available:
                        # Get product name for error message
                        cursor.execute(
                            f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (product_id, tenant_id, org_id, bus_id),
                        )
                        product = cursor.fetchone()
                        product_name = product.get('name', product_id) if product else product_id
                        
                        # Log error and raise exception (this will rollback the transaction)
                        logger.error(
                            f"Insufficient inventory for {sale_mode} sale fulfillment. Product: {product_name}, "
                            f"Required: {quantity}, Available: {available_qty}, Sale ID: {sale_id}"
                        )
                        raise ValueError(
                            f"Insufficient inventory to fulfill {sale_mode} sale. Product '{product_name}'. "
                            f"Required: {quantity}, Available: {available_qty}. "
                            f"Another sale may have taken the inventory."
                        )

                    # Get available batches in FIFO order (use the batches from availability check)
                    batches = batches_to_use

                    remaining_qty = quantity
                    for batch in batches:
                        if remaining_qty <= 0:
                            break

                        batch_location_id = batch['id']
                        batch_qty = Decimal(str(batch['qty']))
                        qty_to_deduct = min(remaining_qty, batch_qty)

                        # Update batch location
                        new_batch_qty = batch_qty - qty_to_deduct
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            SET qty = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (float(new_batch_qty), batch_location_id, tenant_id, org_id, bus_id),
                        )

                        batch_id = batch['purchase_batche_id']

                        # Create product movement
                        movement_id = Helper.generate_unique_identifier(prefix="mov")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                             movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                movement_id, tenant_id, org_id, bus_id, product_id,
                                batch['purchase_batche_id'], 'STORE', loc_id,
                                'OUT', float(qty_to_deduct),
                                f'SALE_{sale_mode}_FULFILLED', sale_id,
                                cdate, ctime, cdatetime, updated_by
                            ),
                        )

                        remaining_qty -= qty_to_deduct
                    
                    # Validate that all required quantity was deducted
                    if remaining_qty > 0:
                        total_deducted = float(quantity) - float(remaining_qty)
                        error_message = (
                            f"Insufficient inventory during sale fulfillment for product '{product_name}' (ID: {product_id}). "
                            f"Required: {float(quantity)} units, "
                            f"Successfully deducted: {float(total_deducted)} units, "
                            f"Remaining needed: {float(remaining_qty)} units. "
                            f"This may occur if inventory was consumed by another transaction. "
                            f"Please check inventory levels and try again."
                        )
                        logger.error(error_message)
                        raise ValueError(error_message)

                    # Update store product current_qty once per product (outside batch loop)
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        SET current_qty = current_qty - %s, updated_by = %s
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND product_id = %s""",
                        (float(quantity), updated_by, tenant_id, org_id, bus_id, loc_id, product_id),
                    )

        # Convert affiliate referral when sale becomes PAID (for DEPOSIT/CREDIT sales paid later)
        if new_status == 'PAID':
            cursor.execute(
                f"""SELECT s.affiliate_id, s.total_amount
                FROM {db_settings.MSG_SALES_TABLE} s
                WHERE s.id = %s AND s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
                AND s.affiliate_id IS NOT NULL""",
                (sale_id, tenant_id, org_id, bus_id, loc_id),
            )
            sale_affiliate = cursor.fetchone()
            if sale_affiliate and sale_affiliate.get('affiliate_id'):
                aff_id = sale_affiliate['affiliate_id']
                sale_total = Decimal(str(sale_affiliate['total_amount'] or 0))

                # Check if referral exists and is still PENDING
                cursor.execute(
                    f"""SELECT id, conversion_status
                    FROM {db_settings.MSG_AFFILIATE_REFERRALS_TABLE}
                    WHERE sale_id = %s AND affiliate_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND conversion_status = 'PENDING'
                    LIMIT 1""",
                    (sale_id, aff_id, tenant_id, org_id, bus_id),
                )
                pending_referral = cursor.fetchone()
                if pending_referral:
                    referral_id = pending_referral['id']
                    cdate_now = Helper.current_date_time()["cdate"]
                    ctime_now = Helper.current_date_time()["ctime"]
                    cdatetime_now = Helper.current_date_time()["cdatetime"]

                    # Calculate commission
                    cursor.execute(
                        f"""SELECT commission_rate, commission_type, fixed_commission_amount
                        FROM {db_settings.MSG_AFFILIATES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (aff_id, tenant_id, org_id, bus_id),
                    )
                    affiliate_data = cursor.fetchone()
                    commission_amount = Decimal('0')
                    if affiliate_data:
                        if affiliate_data['commission_type'] == 'PERCENTAGE':
                            commission_rate = Decimal(str(affiliate_data['commission_rate']))
                            commission_amount = (sale_total * commission_rate) / Decimal('100')
                        else:
                            commission_amount = Decimal(str(affiliate_data['fixed_commission_amount'] or 0))

                    # Update referral to CONVERTED
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_AFFILIATE_REFERRALS_TABLE}
                        SET conversion_status = 'CONVERTED', conversion_date = %s, commission_amount = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (cdatetime_now, float(commission_amount), referral_id, tenant_id, org_id, bus_id),
                    )

                    # Update affiliate stats
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_AFFILIATES_TABLE}
                        SET total_conversions = total_conversions + 1,
                            total_commission_earned = total_commission_earned + %s,
                            updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (float(commission_amount), updated_by, aff_id, tenant_id, org_id, bus_id),
                    )

                    # Create commission record
                    commission_id = Helper.generate_unique_identifier(prefix="afc")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_AFFILIATE_COMMISSIONS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, affiliate_id, referral_id, sale_id,
                         commission_amount, payment_status, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            commission_id, tenant_id, org_id, bus_id, loc_id, aff_id, referral_id, sale_id,
                            float(commission_amount), 'PENDING',
                            cdate_now, ctime_now, cdatetime_now, updated_by
                        ),
                    )

                    logger.info(f"Affiliate referral {referral_id} converted to CONVERTED for sale {sale_id}, commission={float(commission_amount)}")

        # Return the calculated values
        return total_paid, new_status, new_fulfillment_status

    @staticmethod
    def create_payment(
        data: CreatePaymentServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreatePaymentServiceReadDto]:
        """Create payments for a sale"""
        total_payment_amount = sum(payment.paid_amount for payment in data.payments)
        logger.info(
            f"Processing payment creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "sale_id": data.sale_id,
                    "payments_count": len(data.payments),
                    "total_paid_amount": total_payment_amount,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Validate sale exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale = cursor.fetchone()

                if not sale:
                    return Respons(
                        success=False,
                        detail="Sale not found",
                        error="SALE_NOT_FOUND",
                    )

                sale_dict = dict(sale)
                if sale_dict['status'] == 'CANCELLED':
                    return Respons(
                        success=False,
                        detail="Cannot add payment to a cancelled sale",
                        error="SALE_CANCELLED",
                    )

                # Validate all payment methods
                # GIFT_CARD is not allowed in create_payment — gift cards are only handled during sale creation
                # because they require balance deduction, transaction records, and status updates
                valid_payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'OTHERS']
                for idx, payment in enumerate(data.payments):
                    if payment.payment_method == 'GIFT_CARD':
                        return Respons(
                            success=False,
                            detail="Gift card payments can only be applied during sale creation (via the create sale endpoint). To use a gift card, please cancel this sale and create a new one with the gift card code.",
                            error="GIFT_CARD_NOT_SUPPORTED_IN_ADD_PAYMENT",
                        )
                    if payment.payment_method not in valid_payment_methods:
                        return Respons(
                            success=False,
                            detail=f"Invalid payment method at index {idx}: '{payment.payment_method}'. Must be one of: {', '.join(valid_payment_methods)}",
                            error="INVALID_PAYMENT_METHOD",
                        )

                # For INSTANT mode: No partial payments allowed - must pay full amount
                sale_mode = sale_dict.get('sale_mode', 'INSTANT')
                current_status = sale_dict.get('status', 'ON_HOLD')
                total_amount = Decimal(str(sale_dict.get('total_amount', 0)))
                
                # Get current total paid amount
                cursor.execute(
                    f"""SELECT COALESCE(SUM(paid_amount), 0) as current_paid
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND payment_status = 'SUCCESS' AND deleted_at IS NULL""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                current_paid_result = cursor.fetchone()
                current_paid = Decimal(str(current_paid_result['current_paid'])) if current_paid_result else Decimal('0')
                
                # Calculate total payment amount from all payments
                total_payment_amount_decimal = Decimal('0')
                for payment in data.payments:
                    total_payment_amount_decimal += Decimal(str(payment.paid_amount))
                
                # General validation: Cannot accept payment that exceeds total amount
                remaining_balance = total_amount - current_paid
                
                if total_payment_amount_decimal > remaining_balance:
                    return Respons(
                        success=False,
                        detail=f"Total payment amount ({float(total_payment_amount_decimal):.2f}) exceeds remaining balance ({float(remaining_balance):.2f}). Total sale amount: {float(total_amount):.2f}, Already paid: {float(current_paid):.2f}. Please pay the exact remaining amount.",
                        error="PAYMENT_EXCEEDS_BALANCE",
                    )
                
                if sale_mode == 'INSTANT' and current_status in ['ON_HOLD', 'PARTIALLY_PAID']:
                    # INSTANT mode requires full payment - reject if payment doesn't cover remaining balance
                    if total_payment_amount_decimal < remaining_balance:
                        return Respons(
                            success=False,
                            detail=f"INSTANT mode requires full payment. Remaining balance: {float(remaining_balance):.2f}, Total payment amount: {float(total_payment_amount_decimal):.2f}. Please pay the full remaining amount.",
                            error="INSTANT_FULL_PAYMENT_REQUIRED",
                        )

                # Create all payments - payment_status is automatically set to 'SUCCESS'
                payment_status = 'SUCCESS'  # Automatically set by the app
                created_payments = []
                
                for payment in data.payments:
                    payment_id = Helper.generate_unique_identifier(prefix="pay")
                    try:
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_SALES_PAYMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, sale_id, payment_method,
                             payment_status, paid_amount, description, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                payment_id, tenant_id, org_id, bus_id, loc_id, data.sale_id,
                                payment.payment_method, payment_status, StoreSalesService._round_money(payment.paid_amount),
                                payment.description, cdate, ctime, cdatetime, created_by
                            ),
                        )
                        payment_result = cursor.fetchone()
                    except (DatabaseError, IntegrityError) as db_err:
                        # Database errors abort the transaction - re-raise immediately
                        # so transaction context manager can handle rollback
                        logger.error(f"Database error creating payment: {str(db_err)}", exc_info=True)
                        raise ValueError(f"Failed to create payment with method {payment.payment_method}: {str(db_err)}") from db_err

                    if not payment_result:
                        raise ValueError(f"Failed to create payment with method {payment.payment_method}")

                    payment_dict = dict(payment_result)
                    payment_read = CreatePaymentServiceReadDto(**payment_dict)
                    created_payments.append(payment_read)

                    # Log activity for each payment
                    try:
                        ActivityLogService.log_activity(
                            tenant_id=tenant_id,
                            resource_type="rt-store-sales",
                            resource_id=payment_id,
                            action="create",
                            old_data=None,
                            new_data=payment_dict,
                            description=f"Payment of {payment.paid_amount} ({payment.payment_method}) created for sale {sale_dict.get('sale_number', data.sale_id)}",
                            performed_by=created_by,
                            org_id=org_id,
                            bus_id=bus_id,
                            cursor=cursor
                        )
                    except (DatabaseError, IntegrityError) as log_db_err:
                        # Do not swallow DB errors from shared transaction cursor.
                        # The transaction is already marked aborted, so re-raise and rollback.
                        logger.error(
                            f"Database error while logging activity for payment {payment_id}: {log_db_err}",
                            exc_info=True
                        )
                        raise
                    except Exception as log_err:
                        # Non-database logging failures should not block payment creation.
                        logger.warning(f"Activity log failed for payment {payment_id}: {log_err}", exc_info=True)

                # Update sale status based on total payments (only once after all payments are created)
                total_paid, new_status, new_fulfillment_status = StoreSalesService._calculate_and_update_sale_status(
                    cursor, data.sale_id, tenant_id, org_id, bus_id, loc_id, created_by
                )

                logger.info(
                    f"Payments created successfully: {len(created_payments)} payment(s)",
                    extra={
                        "extra_fields": {
                            "payment_count": len(created_payments),
                            "sale_id": data.sale_id,
                            "new_sale_status": new_status,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail=f"Successfully created {len(created_payments)} payment(s)",
                    data=created_payments,
                )

        except ValueError as e:
            logger.error(f"Validation error creating payment: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create payment: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_payment(
        payment_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetPaymentServiceReadDto]:
        """Get a single payment by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (payment_id, tenant_id, org_id, bus_id, loc_id),
                )
                payment = cursor.fetchone()

                if not payment:
                    return Respons(
                        success=False,
                        detail="Payment not found",
                        error="NOT_FOUND",
                    )

                payment_read = GetPaymentServiceReadDto(**dict(payment))

                return Respons(
                    success=True,
                    detail="Payment retrieved successfully",
                    data=[payment_read],
                )

        except Exception as e:
            logger.error(f"Error getting payment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get payment: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_payments(
        sale_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        payment_status: Optional[str] = None,
        payment_method: Optional[str] = None,
        include_refunded: bool = False,
        page: int = 1,
        size: int = 10,
    ) -> Respons[GetPaymentsServiceReadDto]:
        """Get list of payments for a sale with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Validate sale exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale = cursor.fetchone()

                if not sale:
                    return Respons(
                        success=False,
                        detail="Sale not found",
                        error="SALE_NOT_FOUND",
                    )

                # Get sale total
                cursor.execute(
                    f"""SELECT COALESCE(SUM(line_total), 0) as sale_total
                    FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale_total_result = cursor.fetchone()
                sale_total = StoreSalesService._round_money(sale_total_result['sale_total']) if sale_total_result else 0.0

                # Build WHERE clause
                where_conditions = [
                    "p.sale_id = %s",
                    "p.tenant_id = %s",
                    "p.org_id = %s",
                    "p.bus_id = %s",
                    "p.loc_id = %s"
                ]
                params = [sale_id, tenant_id, org_id, bus_id, loc_id]

                if not include_refunded:
                    where_conditions.append("p.deleted_at IS NULL")

                if payment_status:
                    where_conditions.append("p.payment_status = %s")
                    params.append(payment_status)

                if payment_method:
                    where_conditions.append("p.payment_method = %s")
                    params.append(payment_method)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"""SELECT COUNT(*) as total
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} p
                    WHERE {where_clause}""",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Get paginated payments
                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} p
                    WHERE {where_clause}
                    ORDER BY p.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                payments = cursor.fetchall()

                # Calculate total paid (excluding refunded)
                cursor.execute(
                    f"""SELECT COALESCE(SUM(paid_amount), 0) as total_paid
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND payment_status = 'SUCCESS' AND deleted_at IS NULL""",
                    (sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                total_paid_result = cursor.fetchone()
                total_paid = StoreSalesService._round_money(total_paid_result['total_paid']) if total_paid_result else 0.0

                payments_list = [GetPaymentServiceReadDto(**dict(payment)) for payment in payments]

                payments_read = GetPaymentsServiceReadDto(
                    payments=payments_list,
                    total=total,
                    page=page,
                    size=size,
                    total_paid=total_paid,
                    sale_total=sale_total
                )

                return Respons(
                    success=True,
                    detail="Payments retrieved successfully",
                    data=[payments_read],
                )

        except Exception as e:
            logger.error(f"Error getting payments: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get payments: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_payment(
        data: UpdatePaymentServiceWriteDto,
        payment_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[UpdatePaymentServiceReadDto]:
        """Update a payment"""
        logger.info(
            f"Processing payment update: {payment_id}",
            extra={
                "extra_fields": {
                    "payment_id": payment_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing payment
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (payment_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_payment = cursor.fetchone()

                if not existing_payment:
                    return Respons(
                        success=False,
                        detail="Payment not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_payment)
                sale_id = old_data['sale_id']

                # Check if payment is refunded
                if old_data.get('deleted_at'):
                    return Respons(
                        success=False,
                        detail="Cannot update a refunded payment",
                        error="PAYMENT_REFUNDED",
                    )

                # Validate payment status if provided
                if data.payment_status is not None:
                    valid_payment_statuses = ['SUCCESS', 'FAILED', 'PENDING', 'REFUNDED']
                    if data.payment_status not in valid_payment_statuses:
                        return Respons(
                            success=False,
                            detail=f"Invalid payment status. Must be one of: {', '.join(valid_payment_statuses)}",
                            error="INVALID_PAYMENT_STATUS",
                        )

                # Build update query
                update_fields = []
                params = []

                if data.payment_status is not None:
                    update_fields.append("payment_status = %s")
                    params.append(data.payment_status)

                if data.paid_amount is not None:
                    update_fields.append("paid_amount = %s")
                    params.append(StoreSalesService._round_money(data.paid_amount))

                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)

                if not update_fields:
                    return Respons(
                        success=False,
                        detail="No fields to update",
                        error="VALIDATION_ERROR",
                    )

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([payment_id, tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_payment = cursor.fetchone()

                if not updated_payment:
                    return Respons(
                        success=False,
                        detail="Failed to update payment",
                        error="INTERNAL_ERROR",
                    )

                # Update sale status based on total payments
                total_paid, new_status, new_fulfillment_status = StoreSalesService._calculate_and_update_sale_status(
                    cursor, sale_id, tenant_id, org_id, bus_id, loc_id, updated_by
                )

                payment_read = UpdatePaymentServiceReadDto(**dict(updated_payment))

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-sales",
                        resource_id=payment_id,
                        action="update",
                        old_data=old_data,
                        new_data=dict(updated_payment),
                        description=f"Payment {payment_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as log_db_err:
                    logger.error(f"Database error during activity logging: {log_db_err}", exc_info=True)
                    raise
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Payment updated successfully: {payment_id}")

                return Respons(
                    success=True,
                    detail="Payment updated successfully",
                    data=[payment_read],
                )

        except Exception as e:
            logger.error(f"Error updating payment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update payment: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def refund_payment(
        data: RefundPaymentServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        refunded_by: str
    ) -> Respons[RefundPaymentServiceReadDto]:
        """Refund a payment (soft delete)"""
        logger.info(
            f"Processing payment refund: {data.payment_id}",
            extra={
                "extra_fields": {
                    "payment_id": data.payment_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing payment
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.payment_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_payment = cursor.fetchone()

                if not existing_payment:
                    return Respons(
                        success=False,
                        detail="Payment not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_payment)
                sale_id = old_data['sale_id']

                # Check if already refunded
                if old_data.get('deleted_at'):
                    return Respons(
                        success=False,
                        detail="Payment is already refunded",
                        error="ALREADY_REFUNDED",
                    )

                # Check if payment status is SUCCESS (only SUCCESS payments should be refunded)
                if old_data.get('payment_status') != 'SUCCESS':
                    return Respons(
                        success=False,
                        detail=f"Cannot refund payment with status {old_data.get('payment_status')}. Only SUCCESS payments can be refunded.",
                        error="INVALID_PAYMENT_STATUS",
                    )

                # Soft delete the payment (set deleted_at and update payment_status to REFUNDED)
                cdatetime = Helper.current_date_time()["cdatetime"]
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    SET payment_status = 'REFUNDED', deleted_at = %s, deleted_by = %s, updated_by = %s,
                        description = CASE 
                            WHEN description IS NULL THEN %s
                            ELSE description || ' | Refunded: ' || %s
                        END
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (
                        cdatetime, refunded_by, refunded_by,
                        data.description or 'Payment refunded',
                        data.description or 'Payment refunded',
                        data.payment_id, tenant_id, org_id, bus_id, loc_id
                    ),
                )
                refunded_payment = cursor.fetchone()

                if not refunded_payment:
                    return Respons(
                        success=False,
                        detail="Failed to refund payment",
                        error="INTERNAL_ERROR",
                    )

                # Update sale status based on total payments
                total_paid, new_status, new_fulfillment_status = StoreSalesService._calculate_and_update_sale_status(
                    cursor, sale_id, tenant_id, org_id, bus_id, loc_id, refunded_by
                )

                payment_read = RefundPaymentServiceReadDto(**dict(refunded_payment))

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-sales",
                        resource_id=data.payment_id,
                        action="refund",
                        old_data=old_data,
                        new_data=dict(refunded_payment),
                        description=f"Payment {data.payment_id} refunded",
                        performed_by=refunded_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as log_db_err:
                    logger.error(f"Database error during activity logging: {log_db_err}", exc_info=True)
                    raise
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Payment refunded successfully: {data.payment_id}")

                return Respons(
                    success=True,
                    detail="Payment refunded successfully",
                    data=[payment_read],
                )

        except Exception as e:
            logger.error(f"Error refunding payment: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to refund payment: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_sales_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Respons[GetSalesStatisticsServiceReadDto]:
        """Get sales statistics"""
        logger.info(
            f"Processing sales statistics request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "from_date": from_date,
                    "to_date": to_date,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "s.tenant_id = %s",
                    "s.org_id = %s",
                    "s.bus_id = %s",
                    "s.loc_id = %s"
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if from_date:
                    where_conditions.append("s.sale_date >= %s")
                    params.append(from_date)

                if to_date:
                    where_conditions.append("s.sale_date <= %s")
                    params.append(to_date)

                where_clause = " AND ".join(where_conditions)

                # Get total sales count
                cursor.execute(
                    f"""SELECT COUNT(*) as total_sales
                    FROM {db_settings.MSG_SALES_TABLE} s
                    WHERE {where_clause}""",
                    tuple(params),
                )
                total_sales_result = cursor.fetchone()
                total_sales = total_sales_result['total_sales'] if total_sales_result else 0

                # Get total paid (sum of all successful payments, excluding refunded)
                cursor.execute(
                    f"""SELECT COALESCE(SUM(p.paid_amount), 0) as total_paid
                    FROM {db_settings.MSG_SALES_TABLE} s
                    INNER JOIN {db_settings.MSG_SALES_PAYMENTS_TABLE} p 
                        ON s.id = p.sale_id 
                        AND s.tenant_id = p.tenant_id 
                        AND s.org_id = p.org_id 
                        AND s.bus_id = p.bus_id 
                        AND s.loc_id = p.loc_id
                    WHERE {where_clause}
                    AND p.payment_status = 'SUCCESS' 
                    AND p.deleted_at IS NULL""",
                    tuple(params),
                )
                total_paid_result = cursor.fetchone()
                total_paid = StoreSalesService._round_money(total_paid_result['total_paid']) if total_paid_result else 0.0

                # Get total amount and outstanding from sales table
                cursor.execute(
                    f"""SELECT 
                        COALESCE(SUM(total_amount), 0) as total_amount,
                        COALESCE(SUM(balance_amount), 0) as total_outstanding
                    FROM {db_settings.MSG_SALES_TABLE} s
                    WHERE {where_clause}""",
                    tuple(params),
                )
                totals_result = cursor.fetchone()
                total_amount = StoreSalesService._round_money(totals_result['total_amount']) if totals_result else 0.0
                total_outstanding = StoreSalesService._round_money(totals_result['total_outstanding']) if totals_result else 0.0

                # Calculate average sale amount
                average_sale_amount = StoreSalesService._round_money(total_amount / total_sales) if total_sales > 0 else 0.0

                # Get statistics by status
                cursor.execute(
                    f"""SELECT 
                        s.status,
                        COUNT(DISTINCT s.id) as count,
                        COALESCE(SUM(s.total_amount), 0) as total_amount,
                        COALESCE(SUM(s.paid_amount), 0) as total_paid
                    FROM {db_settings.MSG_SALES_TABLE} s
                    WHERE {where_clause}
                    GROUP BY s.status
                    ORDER BY s.status""",
                    tuple(params),
                )
                status_stats_results = cursor.fetchall()

                all_sale_statuses = ['PAID', 'PARTIALLY_PAID', 'ON_HOLD', 'CANCELLED', 'QUEUED']
                status_stats_map = {stat['status']: stat for stat in status_stats_results}

                status_breakdown = []
                for status in all_sale_statuses:
                    if status in status_stats_map:
                        stat = status_stats_map[status]
                        status_breakdown.append(SalesStatusStats(
                            status=stat['status'],
                            count=int(stat['count']),
                            total_amount=StoreSalesService._round_money(stat['total_amount']),
                            total_paid=StoreSalesService._round_money(stat['total_paid'])
                        ))
                    else:
                        status_breakdown.append(SalesStatusStats(
                            status=status,
                            count=0,
                            total_amount=0.0,
                            total_paid=0.0
                        ))

                # Get statistics by payment method - include all methods even with 0
                all_payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'OTHERS']
                
                cursor.execute(
                    f"""SELECT 
                        p.payment_method,
                        COUNT(DISTINCT p.id) as count,
                        COALESCE(SUM(p.paid_amount), 0) as total_amount
                    FROM {db_settings.MSG_SALES_TABLE} s
                    INNER JOIN {db_settings.MSG_SALES_PAYMENTS_TABLE} p 
                        ON s.id = p.sale_id 
                        AND s.tenant_id = p.tenant_id 
                        AND s.org_id = p.org_id 
                        AND s.bus_id = p.bus_id 
                        AND s.loc_id = p.loc_id
                    WHERE {where_clause}
                    AND p.payment_status = 'SUCCESS' 
                    AND p.deleted_at IS NULL
                    GROUP BY p.payment_method
                    ORDER BY p.payment_method""",
                    tuple(params),
                )
                payment_method_stats_results = cursor.fetchall()

                # Create a dictionary from results for easy lookup
                payment_method_dict = {}
                for stat in payment_method_stats_results:
                    payment_method_dict[stat['payment_method']] = {
                        'count': int(stat['count']),
                        'total_amount': StoreSalesService._round_money(stat['total_amount'])
                    }

                # Include all payment methods, even if they have 0 count
                payment_method_breakdown = []
                for method in all_payment_methods:
                    if method in payment_method_dict:
                        payment_method_breakdown.append(PaymentMethodStats(
                            payment_method=method,
                            count=payment_method_dict[method]['count'],
                            total_amount=payment_method_dict[method]['total_amount']
                        ))
                    else:
                        payment_method_breakdown.append(PaymentMethodStats(
                            payment_method=method,
                            count=0,
                            total_amount=0.0
                        ))

                statistics = GetSalesStatisticsServiceReadDto(
                    total_sales=total_sales,
                    total_paid=total_paid,
                    total_outstanding=total_outstanding,
                    average_sale_amount=average_sale_amount,
                    status_breakdown=status_breakdown,
                    payment_method_breakdown=payment_method_breakdown,
                    from_date=from_date,
                    to_date=to_date
                )

                return Respons(
                    success=True,
                    detail="Sales statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting sales statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get sales statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_sale(
        data: DeleteSaleServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        deleted_by: str
    ) -> Respons[DeleteSaleServiceReadDto]:
        """Permanently delete a sale and all related records"""
        logger.info(
            f"Processing permanent sale deletion: {data.sale_id}",
            extra={
                "extra_fields": {
                    "sale_id": data.sale_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get sale before deletion (with all related data for response)
                cursor.execute(
                    f"""SELECT s.*, c.fullname as customer_name
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    WHERE s.id = %s AND s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale = cursor.fetchone()

                if not sale:
                    return Respons(
                        success=False,
                        detail="Sale not found",
                        error="NOT_FOUND",
                    )

                sale_dict = dict(sale)

                # Get sale items before deletion (for response)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    ORDER BY cdatetime ASC""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                items = cursor.fetchall()

                # Get payments before deletion (for response)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND deleted_at IS NULL
                    ORDER BY cdatetime ASC""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                payments = cursor.fetchall()

                # Log activity before permanent deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-sales",
                        resource_id=data.sale_id,
                        action="delete",
                        old_data=sale_dict,
                        new_data=None,
                        description=f"Sale {data.sale_id} permanently deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as log_db_err:
                    logger.error(f"Database error during activity logging: {log_db_err}", exc_info=True)
                    raise
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Permanently delete sale items
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )

                # Permanently delete sale payments
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )

                # Permanently delete the sale
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_SALES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )

                # Prepare response data from the sale data we fetched before deletion
                sale_dict['customer_name'] = sale_dict.get('customer_name') or None
                
                # Convert items to DTOs
                items_list = []
                for item in items:
                    item_dict = dict(item)
                    items_list.append(StoreSalesService._convert_item_to_dto(item_dict))
                sale_dict['items'] = items_list
                sale_dict['payments'] = [PaymentReadBase(**dict(payment)) for payment in payments]
                sale_dict['total_paid'] = StoreSalesService._round_money(sale_dict.get('paid_amount', 0))
                sale_dict['sale_total'] = StoreSalesService._round_money(sale_dict.get('total_amount', 0))

                sale_read = DeleteSaleServiceReadDto(**sale_dict)

                logger.info(f"Sale permanently deleted successfully: {data.sale_id}")
                return Respons(
                    success=True,
                    detail="Sale permanently deleted successfully",
                    data=[sale_read],
                )

        except Exception as e:
            logger.error(f"Error deleting sale: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete sale: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def verify_price(
        data: VerifyPriceServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[VerifyPriceServiceReadDto]:
        """
        Verify prices for items during checkout.
        
        This recalculates all prices including taxes with conditions based on
        the items being purchased with their quantities and base selling prices.
        """
        logger.info(
            f"Processing verify price request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "loc_id": loc_id,
                    "items_count": len(data.items),
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # =====================================================
                # STEP 1: VALIDATE PROMO CODE FIRST (if provided)
                # =====================================================
                promo_code_id = None
                promo_details = None
                promo_code_error = None
                
                # Collect product IDs (used for both promo and affiliate validation)
                cart_product_ids = [item.product_id for item in data.items]
                
                # Initialize cart_product_metadata_by_product (used for per-item promo eligibility checking)
                cart_product_metadata_by_product = {}
                
                # =====================================================
                # STEP 1A: COLLECT METADATA AND CALCULATE PRICES (for min_purchase validation)
                # =====================================================
                # First, we need to calculate prices (without promo) to get price_after_pricing_rule
                # for min_purchase_amount validation
                cart_product_metadata_flat = {
                    'category_ids': [],
                    'tag_ids': [],
                    'brand_ids': [],
                    'label_ids': []
                }
                item_line_totals_for_validation = []  # List of (price_after_pricing_rule × quantity) for each item
                item_line_totals_before_promo = []  # List of (final_price_without_promo × quantity) for subtotal_before_discount
                
                for item in data.items:
                    # Collect metadata for this item
                    try:
                        cursor.execute(
                            f"""SELECT pm.of_type, pm.id
                            FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                            INNER JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} pm 
                                ON amp.product_metadata_id = pm.id 
                                AND amp.tenant_id = pm.tenant_id 
                                AND amp.org_id = pm.org_id 
                                AND amp.bus_id = pm.bus_id
                            WHERE amp.tenant_id = %s AND amp.org_id = %s AND amp.bus_id = %s 
                            AND amp.product_id = %s
                            AND pm.delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, item.product_id),
                        )
                        metadata_records = cursor.fetchall()
                        
                        item_metadata = {
                            'category_ids': [],
                            'tag_ids': [],
                            'brand_ids': [],
                            'label_ids': []
                        }
                        for meta in metadata_records:
                            meta_type = meta.get('of_type')
                            meta_id = meta.get('id')
                            if meta_type == 'CATEGORY':
                                item_metadata['category_ids'].append(meta_id)
                                if meta_id not in cart_product_metadata_flat['category_ids']:
                                    cart_product_metadata_flat['category_ids'].append(meta_id)
                            elif meta_type == 'TAG':
                                item_metadata['tag_ids'].append(meta_id)
                                if meta_id not in cart_product_metadata_flat['tag_ids']:
                                    cart_product_metadata_flat['tag_ids'].append(meta_id)
                            elif meta_type == 'BRAND':
                                item_metadata['brand_ids'].append(meta_id)
                                if meta_id not in cart_product_metadata_flat['brand_ids']:
                                    cart_product_metadata_flat['brand_ids'].append(meta_id)
                            elif meta_type == 'LABEL':
                                item_metadata['label_ids'].append(meta_id)
                                if meta_id not in cart_product_metadata_flat['label_ids']:
                                    cart_product_metadata_flat['label_ids'].append(meta_id)
                        
                        cart_product_metadata_by_product[item.product_id] = item_metadata
                    except Exception as meta_error:
                        logger.warning(f"Error fetching metadata for product {item.product_id}: {str(meta_error)}")
                        cart_product_metadata_by_product[item.product_id] = {
                            'category_ids': [],
                            'tag_ids': [],
                            'brand_ids': [],
                            'label_ids': []
                        }
                    
                    # Calculate price WITHOUT promo discount to get price_after_pricing_rule for validation
                    # Build product_metadata_for_pricing from the item_metadata we just collected
                    product_metadata_for_pricing = {}
                    item_metadata = cart_product_metadata_by_product.get(item.product_id, {})
                    if item_metadata.get('category_ids'):
                        product_metadata_for_pricing['category_id'] = item_metadata['category_ids'][0]
                    if item_metadata.get('tag_ids'):
                        product_metadata_for_pricing['tag_id'] = item_metadata['tag_ids'][0]
                    if item_metadata.get('brand_ids'):
                        product_metadata_for_pricing['brand_id'] = item_metadata['brand_ids'][0]
                    if item_metadata.get('label_ids'):
                        product_metadata_for_pricing['label_id'] = item_metadata['label_ids'][0]
                    
                    # Get SKU
                    try:
                        cursor.execute(
                            f"""SELECT sku FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (item.product_id, tenant_id, org_id, bus_id),
                        )
                        product_sku = cursor.fetchone()
                        sku = product_sku.get('sku') if product_sku else None
                    except Exception as sku_error:
                        logger.error(f"Error fetching SKU for product {item.product_id}: {str(sku_error)}")
                        raise
                    
                    # Calculate price WITHOUT promo discount (to get price_after_pricing_rule for min_purchase validation)
                    prices_for_validation = SalesPriceCalculator.calculate_sale_prices(
                        cursor, item.product_id, tenant_id, org_id, bus_id,
                        quantity=int(item.quantity),
                        base_selling_price=Decimal(str(item.base_selling_price)),
                        location_id=loc_id,
                        sku=sku,
                        product_metadata=product_metadata_for_pricing if product_metadata_for_pricing else None,
                        promo_discount_type=None,  # No promo discount for validation
                        promo_discount_value=None,
                        promo_max_discount_amount=None
                    )
                    
                    # Get price_after_pricing_rule and calculate line total
                    price_after_pricing_rule = Decimal(str(prices_for_validation.get('price_after_pricing_rule', 0) or 0))
                    line_total_for_validation = price_after_pricing_rule * Decimal(str(item.quantity))
                    item_line_totals_for_validation.append(line_total_for_validation)

                    # Store the full final_price (with tax, without promo) for subtotal_before_discount
                    final_price_no_promo = Decimal(str(prices_for_validation.get('final_price', 0) or 0))
                    item_line_totals_before_promo.append(final_price_no_promo * Decimal(str(item.quantity)))
                
                # =====================================================
                # STEP 1B: VALIDATE PROMO CODE (if provided)
                # =====================================================
                if data.promo_code:
                    from src.entities.promo_codes.promo_codes_service import PromoCodesService
                    
                    # Validate promo code (checks location, min purchase per item, and if ANY product matches)
                    is_valid, error_msg, discount_amt, promo_id, promo_details_result = PromoCodesService.validate_and_calculate_discount(
                        promo_code=data.promo_code,
                        item_line_totals=item_line_totals_for_validation,  # Line totals (price_after_pricing_rule × quantity) for min_purchase check
                        customer_id=data.customer_id,
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor,
                        product_ids=cart_product_ids if cart_product_ids else None,
                        product_metadata=cart_product_metadata_flat,
                        location_id=loc_id
                    )
                    
                    if is_valid:
                        promo_code_id = promo_id
                        promo_details = promo_details_result
                        logger.info(
                            f"Promo code '{data.promo_code}' validated successfully. Will apply per-item discounts.",
                            extra={
                                "extra_fields": {
                                    "promo_code": data.promo_code,
                                    "promo_code_id": promo_id,
                                    "promo_details": promo_details,
                                }
                            }
                        )
                    else:
                        promo_code_error = error_msg
                        logger.warning(
                            f"Promo code '{data.promo_code}' validation failed: {error_msg}",
                            extra={
                                "extra_fields": {
                                    "promo_code": data.promo_code,
                                    "error": error_msg,
                                }
                            }
                        )
                
                # =====================================================
                # STEP 2: CALCULATE PRICES FOR EACH ITEM (with per-item promo discounts)
                # =====================================================
                verified_items = []
                total_amount = Decimal('0')
                total_tax_amount = Decimal('0')
                total_promo_discount_amount = Decimal('0')
                
                for item in data.items:
                    # Get product metadata for pricing
                    product_metadata_for_pricing = {}
                    try:
                        cursor.execute(
                            f"""SELECT pm.of_type, pm.id
                            FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                            INNER JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} pm 
                                ON amp.product_metadata_id = pm.id 
                                AND amp.tenant_id = pm.tenant_id 
                                AND amp.org_id = pm.org_id 
                                AND amp.bus_id = pm.bus_id
                            WHERE amp.tenant_id = %s AND amp.org_id = %s AND amp.bus_id = %s 
                            AND amp.product_id = %s
                            AND pm.delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, item.product_id),
                        )
                        metadata_records = cursor.fetchall()
                        for meta in metadata_records:
                            meta_type = meta.get('of_type')
                            meta_id = meta.get('id')
                            if meta_type == 'CATEGORY':
                                product_metadata_for_pricing['category_id'] = meta_id
                            elif meta_type == 'TAG':
                                product_metadata_for_pricing['tag_id'] = meta_id
                            elif meta_type == 'BRAND':
                                product_metadata_for_pricing['brand_id'] = meta_id
                            elif meta_type == 'LABEL':
                                product_metadata_for_pricing['label_id'] = meta_id
                    except Exception as meta_error:
                        # If query fails, transaction is aborted - re-raise to fail the entire operation
                        logger.error(f"Error fetching product metadata for product {item.product_id}: {str(meta_error)}")
                        raise
                    
                    # Get SKU and product name
                    try:
                        cursor.execute(
                            f"""SELECT sku, name FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (item.product_id, tenant_id, org_id, bus_id),
                        )
                        product_data = cursor.fetchone()
                        sku = product_data.get('sku') if product_data else None
                        product_name = product_data.get('name', 'Unknown Product') if product_data else 'Unknown Product'
                    except Exception as sku_error:
                        # If query fails, transaction is aborted - re-raise to fail the entire operation
                        logger.error(f"Error fetching SKU and name for product {item.product_id}: {str(sku_error)}")
                        raise
                    
                    # Check if this item is eligible for promo code discount
                    item_is_eligible_for_promo = False
                    promo_discount_type = None
                    promo_discount_value = None
                    promo_max_discount_amount = None
                    
                    if promo_details:
                        applicable_products = promo_details.get('applicable_to_products')
                        applicable_product_metadata = promo_details.get('applicable_to_product_metadata')
                        
                        if applicable_products:
                            # Normalize product IDs for comparison (handle PostgreSQL array format, strings, etc.)
                            if isinstance(applicable_products, str):
                                import ast
                                try:
                                    applicable_products = ast.literal_eval(applicable_products)
                                except:
                                    # Try PostgreSQL array format {id1,id2}
                                    if applicable_products.startswith('{') and applicable_products.endswith('}'):
                                        applicable_products = [p.strip() for p in applicable_products[1:-1].split(',') if p.strip()]
                                    else:
                                        applicable_products = [applicable_products]
                            elif isinstance(applicable_products, (tuple, set)):
                                applicable_products = list(applicable_products)
                            elif not isinstance(applicable_products, list):
                                applicable_products = [applicable_products] if applicable_products else []
                            
                            # Filter out None/empty values and normalize
                            applicable_products_normalized = [str(p).strip() for p in applicable_products if p]
                            item_product_id_normalized = str(item.product_id).strip()
                            
                            # Debug logging for product matching
                            logger.info(
                                f"Checking item eligibility for promo: item_product_id={item_product_id_normalized}, applicable_products={applicable_products_normalized}",
                                extra={
                                    "extra_fields": {
                                        "item_product_id": item_product_id_normalized,
                                        "applicable_products": applicable_products_normalized,
                                        "match": item_product_id_normalized in applicable_products_normalized,
                                    }
                                }
                            )
                            
                            # Check if this product is in the applicable products list
                            if item_product_id_normalized in applicable_products_normalized:
                                item_is_eligible_for_promo = True
                                logger.info(f"Item {item.product_id} is eligible for promo discount")
                            else:
                                logger.warning(f"Item {item.product_id} is NOT eligible - product ID not in applicable products list")
                        elif applicable_product_metadata:
                            # Check if this product's metadata matches any applicable metadata
                            # Get this product's metadata from the cart metadata we collected earlier
                            item_metadata = cart_product_metadata_by_product.get(item.product_id, {
                                'category_ids': [],
                                'tag_ids': [],
                                'brand_ids': [],
                                'label_ids': []
                            })
                            
                            # Get all metadata IDs for this product
                            all_item_metadata_ids = (
                                item_metadata.get('category_ids', []) +
                                item_metadata.get('tag_ids', []) +
                                item_metadata.get('brand_ids', []) +
                                item_metadata.get('label_ids', [])
                            )
                            
                            # Normalize for comparison
                            applicable_metadata_normalized = [str(m).strip() for m in applicable_product_metadata if m]
                            item_metadata_normalized = [str(m).strip() for m in all_item_metadata_ids if m]
                            
                            # Check if any metadata matches (only apply once even if multiple match)
                            if any(mid in applicable_metadata_normalized for mid in item_metadata_normalized):
                                item_is_eligible_for_promo = True
                        
                        if item_is_eligible_for_promo:
                            promo_discount_type = promo_details.get('discount_type')
                            promo_discount_value = promo_details.get('discount_value')
                            promo_max_discount_amount = promo_details.get('max_discount_amount')
                            
                            # Log promo discount details for eligible items
                            logger.info(
                                f"Applying promo discount to item {item.product_id}: type={promo_discount_type}, value={promo_discount_value}, max={promo_max_discount_amount}",
                                extra={
                                    "extra_fields": {
                                        "product_id": item.product_id,
                                        "promo_discount_type": promo_discount_type,
                                        "promo_discount_value": float(promo_discount_value) if promo_discount_value else None,
                                        "promo_max_discount_amount": float(promo_max_discount_amount) if promo_max_discount_amount else None,
                                    }
                                }
                            )
                    
                    # Calculate prices using SalesPriceCalculator (WITH TAX CONDITIONS and per-item promo discount)
                    prices = SalesPriceCalculator.calculate_sale_prices(
                        cursor, item.product_id, tenant_id, org_id, bus_id,
                        quantity=int(item.quantity),
                        base_selling_price=Decimal(str(item.base_selling_price)),
                        location_id=loc_id,
                        sku=sku,
                        product_metadata=product_metadata_for_pricing if product_metadata_for_pricing else None,
                        promo_discount_type=promo_discount_type if item_is_eligible_for_promo else None,
                        promo_discount_value=promo_discount_value if item_is_eligible_for_promo else None,
                        promo_max_discount_amount=promo_max_discount_amount if item_is_eligible_for_promo else None
                    )
                    
                    # Calculate line total (convert from float to Decimal since price calculator returns floats)
                    final_price = Decimal(str(prices.get('final_price', 0) or 0))
                    line_total = final_price * Decimal(str(item.quantity))
                    
                    # Log the calculated prices to verify discount application
                    if item_is_eligible_for_promo:
                        # Convert from float to Decimal (price calculator returns floats)
                        item_promo_discount_float = prices.get('item_promo_discount_amount', 0) or 0
                        item_promo_discount = Decimal(str(item_promo_discount_float))
                        logger.info(
                            f"Price calculation result for item {item.product_id}: final_price={prices.get('final_price')}, promo_discount={item_promo_discount}",
                            extra={
                                "extra_fields": {
                                    "product_id": item.product_id,
                                    "final_price": float(final_price),
                                    "item_promo_discount_amount": float(item_promo_discount),
                                }
                            }
                        )
                    
                    # Convert taxes_applied list to DTOs
                    taxes_applied_dto = []
                    taxes_applied_data = prices.get('taxes_applied', [])
                    total_tax_rate = Decimal('0')
                    if taxes_applied_data:
                        for tax in taxes_applied_data:
                            taxes_applied_dto.append(TaxAppliedReadDto(**tax))
                            # Sum up all tax rates (for display, not for calculation)
                            if tax.get('rate') is not None:
                                total_tax_rate += Decimal(str(tax.get('rate')))
                    
                    # Convert pricing_rule_applied to DTO (return None if all fields are None)
                    pricing_rule_dto = None
                    pricing_rule_data = prices.get('pricing_rule_applied')
                    if pricing_rule_data and any(v is not None for v in pricing_rule_data.values()):
                        pricing_rule_dto = PricingRuleAppliedReadDto(**pricing_rule_data)
                    
                    # Convert tax_rule_applied to DTO (return None if all fields are None)
                    tax_rule_dto = None
                    tax_rule_data = prices.get('tax_rule_applied')
                    if tax_rule_data and any(v is not None for v in tax_rule_data.values()):
                        tax_rule_dto = TaxRuleAppliedReadDto(**tax_rule_data)
                    
                    # Use tax_amount from calculator prices (verify_price calculates prices, doesn't receive them)
                    item_tax_amount = float(prices.get('tax_amount', 0) or 0)
                    
                    verified_item = VerifiedPriceItemReadDto(
                        product_id=item.product_id,
                        product_name=product_name,
                        quantity=item.quantity,
                        base_selling_price=item.base_selling_price,
                        actual_price=prices.get('actual_price'),
                        price_after_pricing_rule=prices.get('price_after_pricing_rule'),
                        price_after_tax=prices.get('price_after_tax'),
                        tax_amount=item_tax_amount,  # Tax amount from calculator
                        final_price=float(final_price),
                        line_total=float(line_total),
                        taxes_applied=taxes_applied_dto,
                        tax_rate=float(total_tax_rate),  # Sum of all tax rates from taxes_applied
                        pricing_rule_applied=pricing_rule_dto,
                        tax_rule_applied=tax_rule_dto
                    )
                    
                    verified_items.append(verified_item)
                    total_amount += line_total
                    total_tax_amount += Decimal(str(item_tax_amount))
                    
                    # Accumulate promo discount amount (for reporting only - discounts already applied in final_price)
                    # Convert from float to Decimal (price calculator returns floats via decimal_to_float)
                    item_promo_discount_float = prices.get('item_promo_discount_amount', 0) or 0
                    item_promo_discount = Decimal(str(item_promo_discount_float))
                    total_promo_discount_amount += item_promo_discount
                
                # Final total is already calculated (total_amount includes discounted prices)
                # total_promo_discount_amount is kept for reporting/display purposes only
                final_total_amount = total_amount

                # Calculate subtotal_before_discount from the first-pass prices (without promo, with tax)
                subtotal_before_discount = None
                if total_promo_discount_amount > 0 and item_line_totals_before_promo:
                    subtotal_before_discount = float(sum(item_line_totals_before_promo))
                
                # =====================================================
                # VALIDATE AND PROCESS GIFT CARD (if provided)
                # =====================================================
                gift_card_id = None
                gift_card_balance_available = None
                gift_card_amount_usable = None
                
                if data.gift_card_code:
                    from src.entities.gift_cards.gift_cards_service import GiftCardsService
                    
                    # Get gift card by code
                    gift_card_result = GiftCardsService.get_gift_card_by_code(
                        gift_card_code=data.gift_card_code,
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                    )
                    
                    if gift_card_result.success and gift_card_result.data:
                        gift_card = gift_card_result.data[0] if isinstance(gift_card_result.data, list) else gift_card_result.data
                        
                        # Only include if gift card is valid (don't fail verification if invalid)
                        if gift_card.status == 'ACTIVE' and gift_card.current_balance > 0:
                            # Check expiry
                            from datetime import date
                            is_expired = gift_card.expiry_date and date.today() > gift_card.expiry_date
                            
                            if not is_expired:
                                # Check location restrictions - STRICT: if applicable_to_locations is empty/null, don't apply to any
                                location_match = False
                                applicable_locations = gift_card.applicable_to_locations
                                if applicable_locations:
                                    # Convert to list of location IDs if it's a list of objects
                                    if isinstance(applicable_locations, list) and len(applicable_locations) > 0:
                                        applicable_location_ids = []
                                        for loc in applicable_locations:
                                            if isinstance(loc, dict):
                                                loc_id_val = loc.get('location_id')
                                                if loc_id_val:
                                                    applicable_location_ids.append(str(loc_id_val))
                                            elif hasattr(loc, 'location_id'):
                                                # Pydantic model or object with location_id attribute
                                                applicable_location_ids.append(str(loc.location_id))
                                            elif hasattr(loc, 'dict'):
                                                # Pydantic v1 model - convert to dict
                                                loc_dict = loc.dict()
                                                loc_id_val = loc_dict.get('location_id')
                                                if loc_id_val:
                                                    applicable_location_ids.append(str(loc_id_val))
                                            elif hasattr(loc, 'model_dump'):
                                                # Pydantic v2 model - convert to dict
                                                loc_dict = loc.model_dump()
                                                loc_id_val = loc_dict.get('location_id')
                                                if loc_id_val:
                                                    applicable_location_ids.append(str(loc_id_val))
                                            else:
                                                # Fallback: try to convert to string (for backwards compatibility)
                                                applicable_location_ids.append(str(loc))
                                        
                                        if applicable_location_ids:
                                            location_match = str(loc_id).strip() in [str(lid).strip() for lid in applicable_location_ids]
                                
                                # Only apply if location matches (or if no restrictions set, but we're being strict - so must match)
                                if location_match:
                                    gift_card_id = gift_card.id
                                    gift_card_balance_available = float(gift_card.current_balance)
                                    # Amount usable is the minimum of balance and final total
                                    gift_card_amount_usable = float(min(Decimal(str(gift_card.current_balance)), final_total_amount))
                
                # =====================================================
                # VALIDATE AFFILIATE (if provided)
                # =====================================================
                affiliate_id = None
                
                if data.affiliate_code:
                    from src.entities.affiliates.affiliates_service import AffiliatesService
                    
                    # Collect all product metadata IDs (categories, brands, tags, labels) from cart items
                    cart_metadata_ids = []
                    for item in data.items:
                        try:
                            cursor.execute(
                                f"""SELECT pm.id
                                FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                                INNER JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} pm 
                                    ON amp.product_metadata_id = pm.id 
                                    AND amp.tenant_id = pm.tenant_id 
                                    AND amp.org_id = pm.org_id 
                                    AND amp.bus_id = pm.bus_id
                                WHERE amp.tenant_id = %s AND amp.org_id = %s AND amp.bus_id = %s 
                                AND amp.product_id = %s
                                AND pm.delete_status = 'NOT_DELETED'""",
                                (tenant_id, org_id, bus_id, item.product_id),
                            )
                            metadata_records = cursor.fetchall()
                            for meta in metadata_records:
                                meta_id = meta.get('id')
                                if meta_id and meta_id not in cart_metadata_ids:
                                    cart_metadata_ids.append(meta_id)
                        except Exception as meta_error:
                            logger.warning(f"Error fetching metadata for product {item.product_id}: {str(meta_error)}")
                            # Continue even if metadata fetch fails
                    
                    # Get affiliate by code
                    affiliate_result = AffiliatesService.get_affiliate_by_code(
                        affiliate_code=data.affiliate_code,
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                    )
                    
                    # Only include if affiliate is valid (don't fail verification if invalid)
                    if affiliate_result.success and affiliate_result.data:
                        affiliate = affiliate_result.data[0] if isinstance(affiliate_result.data, list) else affiliate_result.data
                        if affiliate.status == 'ACTIVE' and affiliate.is_active:
                            # Check location restrictions (if applicable_to_locations is set)
                            location_match = True
                            applicable_locations = affiliate.applicable_to_locations
                            if applicable_locations:
                                if isinstance(applicable_locations, list) and len(applicable_locations) > 0:
                                    if isinstance(applicable_locations[0], dict):
                                        applicable_location_ids = [loc.get('location_id') for loc in applicable_locations if loc.get('location_id')]
                                    else:
                                        applicable_location_ids = [str(loc) for loc in applicable_locations]
                                    
                                    if applicable_location_ids:
                                        location_match = str(loc_id).strip() in [str(lid).strip() for lid in applicable_location_ids]
                            
                            # Check product restrictions (if applicable_to_products is set)
                            product_match = True
                            applicable_products = affiliate.applicable_to_products
                            if applicable_products:
                                if isinstance(applicable_products, list) and len(applicable_products) > 0:
                                    if isinstance(applicable_products[0], dict):
                                        applicable_product_ids = [prod.get('product_id') for prod in applicable_products if prod.get('product_id')]
                                    else:
                                        applicable_product_ids = [str(prod) for prod in applicable_products]
                                    
                                    if applicable_product_ids and cart_product_ids:
                                        product_match = any(pid in applicable_product_ids for pid in cart_product_ids)
                                    elif applicable_product_ids:
                                        product_match = False
                            
                            # Check product metadata restrictions (if applicable_to_product_metadata is set)
                            metadata_match = True
                            applicable_metadata = affiliate.applicable_to_product_metadata
                            if applicable_metadata:
                                if isinstance(applicable_metadata, list) and len(applicable_metadata) > 0:
                                    if isinstance(applicable_metadata[0], dict):
                                        applicable_metadata_ids = [meta.get('metadata_id') for meta in applicable_metadata if meta.get('metadata_id')]
                                    else:
                                        applicable_metadata_ids = [str(meta) for meta in applicable_metadata]
                                    
                                    if applicable_metadata_ids and cart_metadata_ids:
                                        # Check if any cart metadata matches (categories, brands, tags, labels, etc.)
                                        metadata_match = any(mid in applicable_metadata_ids for mid in cart_metadata_ids)
                                    elif applicable_metadata_ids:
                                        metadata_match = False
                            
                            # Only apply affiliate if all restrictions match
                            if location_match and product_match and metadata_match:
                                affiliate_id = affiliate.id
                
                # Fetch business name
                business_name = "Unknown Business"
                try:
                    cursor.execute(
                        f"""SELECT bus_name FROM {db_settings.CORE_PLATFORM_BUSINESSES_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (bus_id, tenant_id),
                    )
                    business_data = cursor.fetchone()
                    business_name = business_data.get('bus_name', 'Unknown Business') if business_data else 'Unknown Business'
                except Exception as business_error:
                    logger.warning(f"Error fetching business name: {str(business_error)}")
                    # Don't fail the entire operation if business name fetch fails
                
                verify_price_read = VerifyPriceServiceReadDto(
                    items=verified_items,
                    business_name=business_name,
                    subtotal_before_discount=subtotal_before_discount,
                    total_amount=float(total_amount),
                    total_tax_amount=float(total_tax_amount),
                    promo_code_id=promo_code_id,
                    promo_discount_amount=float(total_promo_discount_amount) if total_promo_discount_amount > 0 else None,
                    promo_code_error=promo_code_error,
                    final_total_amount=float(final_total_amount),
                    gift_card_id=gift_card_id,
                    gift_card_balance_available=gift_card_balance_available,
                    gift_card_amount_usable=gift_card_amount_usable,
                    affiliate_id=affiliate_id
                )
                
                logger.info(f"Price verification completed successfully for {len(data.items)} items")
                return Respons(
                    success=True,
                    detail="Prices verified successfully",
                    data=[verify_price_read],
                )

        except Exception as e:
            logger.error(f"Error verifying prices: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to verify prices: {str(e)}",
                error="INTERNAL_ERROR",
            )

