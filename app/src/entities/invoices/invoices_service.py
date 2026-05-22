from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import json
import psycopg2
from psycopg2 import DatabaseError, IntegrityError
from src.entities.invoices.invoices_read_dto import (
    CreateInvoiceServiceReadDto,
    UpdateInvoiceServiceReadDto,
    GetInvoiceServiceReadDto,
    GetInvoicesServiceReadDto,
    DeleteInvoiceServiceReadDto,
    GetInvoiceStatisticsServiceReadDto,
    InvoiceItemReadBase,
    InvoicePaymentReadBase,
    InvoiceReadBase,
    CreateInvoicePaymentServiceReadDto,
    TaxAppliedReadDto,
)
from src.entities.invoices.invoices_write_dto import (
    CreateInvoiceServiceWriteDto,
    UpdateInvoiceServiceWriteDto,
    DeleteInvoiceServiceWriteDto,
    CreateInvoicePaymentServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from src.utils.pricing_calculator import PricingCalculator
from src.utils.sales_price_calculator import SalesPriceCalculator
from src.entities.store_sales.store_sales_service import StoreSalesService
from src.entities.store_sales.store_sales_write_dto import CreateSaleServiceWriteDto
from src.entities.store_sales.store_sales_base import SaleItemBase, SalePaymentInputBase, TaxAppliedItem as SaleTaxAppliedItem
from trovesuite.utils import Helper

logger = get_logger("invoices_service")


class InvoicesService:
    """Service class for invoices operations"""

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
    def _generate_invoice_number(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> str:
        """Generate a systematic invoice number in format INV-YYYYMMDD-NNN"""
        from datetime import datetime
        
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"INV-{today}"
        
        cursor.execute(
            f"""SELECT invoice_number 
            FROM {db_settings.MSG_INVOICES_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
            AND invoice_number LIKE %s
            ORDER BY invoice_number DESC
            LIMIT 1""",
            (tenant_id, org_id, bus_id, loc_id, f"{prefix}-%"),
        )
        last_invoice = cursor.fetchone()
        
        if last_invoice and last_invoice.get('invoice_number'):
            last_number = last_invoice['invoice_number']
            try:
                sequence_str = last_number.split('-')[-1]
                sequence_num = int(sequence_str)
                next_sequence = sequence_num + 1
            except (ValueError, IndexError):
                next_sequence = 1
        else:
            next_sequence = 1
        
        invoice_number = f"{prefix}-{next_sequence:03d}"
        
        max_attempts = 1000
        attempts = 0
        while attempts < max_attempts:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_INVOICES_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                AND invoice_number = %s""",
                (tenant_id, org_id, bus_id, loc_id, invoice_number),
            )
            if not cursor.fetchone():
                return invoice_number
            
            next_sequence += 1
            invoice_number = f"{prefix}-{next_sequence:03d}"
            attempts += 1
        
        import time
        timestamp_suffix = int(time.time() * 1000) % 10000
        invoice_number = f"{prefix}-{timestamp_suffix:04d}"
        
        return invoice_number

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
            ORDER BY bl.cdatetime ASC, pb.cdatetime ASC""",
            (tenant_id, org_id, bus_id, loc_id, product_id),
        )
        return cursor.fetchall()

    @staticmethod
    def _parse_invoice_items_from_db(items_results) -> List[InvoiceItemReadBase]:
        """Helper function to parse invoice items from database results, handling taxes_applied from JSON"""
        items_list = []
        for item in items_results:
            item_dict = dict(item)
            
            # Parse taxes_applied from JSON
            taxes_applied_list = []
            if item_dict.get('taxes_applied'):
                try:
                    if isinstance(item_dict['taxes_applied'], str):
                        taxes_applied_list = json.loads(item_dict['taxes_applied'])
                    elif isinstance(item_dict['taxes_applied'], list):
                        taxes_applied_list = item_dict['taxes_applied']
                    # Convert to TaxAppliedReadDto objects
                    item_dict['taxes_applied'] = [TaxAppliedReadDto(**tax) for tax in taxes_applied_list]
                    
                    # tax_rate and tax_amount are already stored in the database, no need to calculate from taxes_applied
                    # Just ensure they exist (defaults already set from database query)
                except Exception as e:
                    logger.warning(f"Error parsing taxes_applied for item: {str(e)}")
                    item_dict['taxes_applied'] = []
            else:
                item_dict['taxes_applied'] = []
            
            items_list.append(InvoiceItemReadBase(**item_dict))
        
        return items_list

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
        batches = InvoicesService._get_store_product_batches_fifo(
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
    def create_invoice(
        data: CreateInvoiceServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateInvoiceServiceReadDto]:
        """Create a new invoice with items"""
        logger.info(
            f"Processing invoice creation",
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

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Validate customer
                cursor.execute(
                    f"""SELECT id, fullname FROM {db_settings.MSG_CUSTOMERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.customer_id),
                )
                customer = cursor.fetchone()
                if not customer:
                    return Respons(
                        success=False,
                        detail=f"Customer {data.customer_id} not found",
                        error="CUSTOMER_NOT_FOUND",
                    )
                customer_name = customer.get('fullname', 'Unknown')

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

                # Parse sale_date
                try:
                    sale_date = datetime.strptime(data.sale_date, "%Y-%m-%d").date()
                except ValueError:
                    return Respons(
                        success=False,
                        detail="Invalid sale_date format. Expected YYYY-MM-DD",
                        error="INVALID_DATE_FORMAT",
                    )
                
                # Parse due_date if provided
                due_date = None
                if data.due_date is not None:
                    try:
                        due_date = datetime.strptime(data.due_date, "%Y-%m-%d").date()
                    except ValueError:
                        return Respons(
                            success=False,
                            detail="Invalid due_date format. Expected YYYY-MM-DD",
                            error="INVALID_DATE_FORMAT",
                        )

                # Validate status if provided
                valid_statuses = ['DRAFT', 'COMPLETED', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED']
                status = data.status.upper() if data.status else None
                if status and status not in valid_statuses:
                    return Respons(
                        success=False,
                        detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                        error="INVALID_STATUS",
                    )

                # Generate invoice number
                invoice_number = InvoicesService._generate_invoice_number(
                    cursor, tenant_id, org_id, bus_id, loc_id
                )

                # =====================================================
                # USE VERIFIED TOTALS FROM verify_price (if provided)
                # =====================================================
                # Use verified totals from verify_price endpoint to avoid recalculation discrepancies
                promo_code_id = None
                promo_discount_amount = Decimal('0')
                gift_card_id = None
                affiliate_id = None
                verified_total_amount = None
                
                if data.verified_total_amount is not None:
                    verified_total_amount = Decimal(str(data.verified_total_amount))
                    promo_discount_amount = Decimal(str(data.verified_promo_discount_amount)) if data.verified_promo_discount_amount is not None else Decimal('0')
                    promo_code_id = data.verified_promo_code_id
                    gift_card_id = data.verified_gift_card_id
                    affiliate_id = data.verified_affiliate_id
                    
                    logger.info(
                        f"Using verified totals from verify_price: total_amount={verified_total_amount}, "
                        f"promo_discount={promo_discount_amount}, promo_code_id={promo_code_id}"
                )

                # Check if we need to validate inventory availability
                should_check_availability = status in ['COMPLETED', 'PARTIALLY_PAID']
                
                # If status requires inventory check, validate all items first
                if should_check_availability:
                    availability_errors = []
                    for item in data.items:
                        required_qty = float(item.quantity)
                        is_available, available_qty, batches = InvoicesService._check_inventory_availability(
                            tenant_id, org_id, bus_id, loc_id, item.product_id, required_qty, cursor
                        )
                        
                        if not is_available:
                            # Get product name for error message
                            cursor.execute(
                                f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (item.product_id, tenant_id, org_id, bus_id),
                            )
                            product_result = cursor.fetchone()
                            product_name = product_result.get('name', 'Unknown') if product_result else 'Unknown'
                            
                            availability_errors.append({
                                'product_name': product_name,
                                'product_id': item.product_id,
                                'required_qty': required_qty,
                                'available_qty': available_qty
                            })
                    
                    if availability_errors:
                        error_details = []
                        for error in availability_errors:
                            error_details.append(
                                f"product: {error['product_name']}, current_qty: {error['available_qty']}"
                            )
                        
                        return Respons(
                            success=False,
                            detail=f"We don't have enough items available. {', '.join(error_details)}",
                            error="INSUFFICIENT_INVENTORY",
                        )

                # Process invoice items and calculate total
                invoice_items = []
                if verified_total_amount is not None:
                    # Use verified total from verify_price endpoint
                    total_amount = verified_total_amount
                    logger.info(f"Using verified total_amount: {total_amount}")
                else:
                    # Calculate from items (fallback)
                    total_amount = Decimal('0')
                
                for item in data.items:
                    # Validate product
                    product_id = item.product_id
                    cursor.execute(
                        f"""SELECT id, name FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, item.product_id),
                    )
                    product = cursor.fetchone()
                    if not product:
                        return Respons(
                            success=False,
                            detail=f"Product {item.product_id} not found",
                            error="PRODUCT_NOT_FOUND",
                        )

                    product_name = product.get('name', 'Unknown') if product else 'Unknown'

                    # Get taxes_applied from item (for storing, not for calculation)
                    taxes_applied = item.taxes_applied if item.taxes_applied else []
                    
                    # Use provided prices directly
                    base_selling_price = Decimal(str(item.base_selling_price)) if item.base_selling_price else Decimal('0')
                    actual_price = Decimal(str(item.actual_price)) if item.actual_price else Decimal('0')
                    price_after_pricing_rule = Decimal(str(item.price_after_pricing_rule)) if item.price_after_pricing_rule else Decimal('0')
                    price_after_tax = Decimal(str(item.price_after_tax)) if item.price_after_tax else Decimal('0')
                    final_price = Decimal(str(item.final_price)) if item.final_price else Decimal('0')
                    
                    # Use tax_rate and tax_amount directly from input (no calculation)
                    tax_rate = Decimal(str(item.tax_rate)) if item.tax_rate is not None else Decimal('0')
                    tax_amount = Decimal(str(item.tax_amount)) if item.tax_amount is not None else Decimal('0')
                    is_inclusive = item.is_inclusive if item.is_inclusive is not None else (any(tax.is_inclusive for tax in taxes_applied) if taxes_applied else False)

                    # If prices are not provided, calculate them
                    if final_price == 0:
                        # Get product metadata for pricing calculation
                        product_metadata = {}
                        try:
                            cursor.execute(
                                f"""SELECT pm.id, pm.of_type
                                FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                                INNER JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} pm 
                                    ON amp.product_metadata_id = pm.id 
                                    AND amp.tenant_id = pm.tenant_id 
                                    AND amp.org_id = pm.org_id 
                                    AND amp.bus_id = pm.bus_id
                                WHERE amp.tenant_id = %s AND amp.org_id = %s AND amp.bus_id = %s 
                                AND amp.product_id = %s
                                AND pm.delete_status = 'NOT_DELETED'""",
                                (tenant_id, org_id, bus_id, product_id),
                            )
                            metadata_results = cursor.fetchall()
                            
                            for meta in metadata_results:
                                meta_type = meta.get('of_type')
                                meta_id = meta.get('id')
                                
                                if meta_type == 'CATEGORY':
                                    product_metadata['category_id'] = meta_id
                                elif meta_type == 'TAG':
                                    product_metadata['tag_id'] = meta_id
                                elif meta_type == 'BRAND':
                                    product_metadata['brand_id'] = meta_id
                                elif meta_type == 'LABEL':
                                    product_metadata['label_id'] = meta_id
                        except Exception:
                            product_metadata = {}

                        # Get SKU
                        cursor.execute(
                            f"""SELECT sku FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (product_id, tenant_id, org_id, bus_id),
                        )
                        product_sku = cursor.fetchone()
                        sku = product_sku.get('sku') if product_sku else None

                        # Calculate prices using SalesPriceCalculator (same as sales)
                        prices = SalesPriceCalculator.calculate_sale_prices(
                            cursor, product_id, tenant_id, org_id, bus_id,
                            quantity=int(item.quantity),
                            base_selling_price=base_selling_price if base_selling_price > 0 else None,
                            location_id=loc_id,
                            sku=sku,
                            product_metadata=product_metadata if product_metadata else None
                        )
                        
                        # Extract calculated prices
                        base_selling_price = Decimal(str(prices.get('base_selling_price', 0) or 0))
                        actual_price = Decimal(str(prices.get('actual_price', 0) or 0))
                        price_after_pricing_rule = Decimal(str(prices.get('price_after_pricing_rule', 0) or 0))
                        price_after_tax = Decimal(str(prices.get('price_after_tax', 0) or 0))
                        final_price = Decimal(str(prices.get('final_price', 0) or 0))
                        
                        # Extract taxes_applied from calculator result
                        calculated_taxes_applied = prices.get('taxes_applied', [])
                        if calculated_taxes_applied:
                            # Convert to TaxAppliedItem format
                            from src.entities.invoices.invoices_base import TaxAppliedItem
                            taxes_applied = [
                                TaxAppliedItem(
                                    tax_id=tax.get('tax_id', ''),
                                    tax_name=tax.get('tax_name', ''),
                                    rate=float(tax.get('rate', 0) or 0),
                                    is_inclusive=bool(tax.get('is_inclusive', False)),
                                    amount=float(tax.get('amount', 0) or 0)
                                )
                                for tax in calculated_taxes_applied
                            ]
                            # tax_rate and tax_amount already set from input above - no calculation, use as-is
                            # Only update is_inclusive if not set from input
                            if not is_inclusive and taxes_applied:
                                is_inclusive = any(tax.is_inclusive for tax in taxes_applied)
                        else:
                            # Fallback to tax_rule_applied if no taxes_applied
                            tax_rule_applied = prices.get('tax_rule_applied')
                            if tax_rule_applied:
                                from src.entities.invoices.invoices_base import TaxAppliedItem
                                taxes_applied = [
                                    TaxAppliedItem(
                                        tax_id=tax_rule_applied.get('tax_id', ''),
                                        tax_name=tax_rule_applied.get('tax_name', ''),
                                        rate=float(tax_rule_applied.get('rate', 0) or 0),
                                        is_inclusive=bool(tax_rule_applied.get('is_inclusive', False)),
                                        amount=float(prices.get('tax_amount', 0) or 0)
                                    )
                                ]
                                # tax_rate and tax_amount already set from input above - no calculation, use as-is
                                # Only update is_inclusive if not set from input
                                if not is_inclusive:
                                    is_inclusive = tax_rule_applied.get('is_inclusive', False)
                            else:
                                taxes_applied = []
                                tax_rate = Decimal('0')
                                tax_amount = Decimal('0')
                                is_inclusive = False

                    # Calculate line total
                    line_total = final_price * Decimal(str(item.quantity))
                    # Only add to total if not using verified totals
                    if verified_total_amount is None:
                        total_amount += line_total

                    # Get batches for this item if status requires inventory allocation
                    batches_for_item = []
                    if should_check_availability:
                        _, _, batches_for_item = InvoicesService._check_inventory_availability(
                            tenant_id, org_id, bus_id, loc_id, product_id, float(item.quantity), cursor
                        )

                    invoice_items.append({
                        'item': item,
                        'product_id': product_id,
                        'product_name': product_name,
                        'batches': batches_for_item,
                        'base_selling_price': base_selling_price,
                        'actual_price': actual_price,
                        'price_after_pricing_rule': price_after_pricing_rule,
                        'price_after_tax': price_after_tax,
                        'final_price': final_price,
                        'line_total': line_total,
                        'tax_rate': tax_rate,
                        'is_inclusive': is_inclusive,
                        'tax_amount': tax_amount,
                        'taxes_applied': taxes_applied,
                    })

                # =====================================================
                # HANDLE GIFT CARDS, PROMO CODES, AFFILIATES
                # =====================================================
                # Initialize amounts (payments are handled via separate endpoint)
                paid_amount = Decimal('0')
                gift_card_amount_used = Decimal('0')
                balance_amount = total_amount
                
                # Determine status if not explicitly provided
                if not status:
                    # For invoices, default to DRAFT if no status provided
                    # Status will be updated when payments are added
                    status = 'DRAFT'

                # Create invoice
                invoice_id = Helper.generate_unique_identifier(prefix="inv")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_INVOICES_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, invoice_number, customer_id,
                     sale_date, due_date, status, sale_mode, description,
                     total_amount, paid_amount, balance_amount,
                     gift_card_amount_used, promo_code_id, promo_discount_amount, affiliate_id,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        invoice_id, tenant_id, org_id, bus_id, loc_id, invoice_number,
                        data.customer_id, sale_date, due_date, status, sale_mode, data.description,
                        InvoicesService._round_money(total_amount), 
                        InvoicesService._round_money(paid_amount), 
                        InvoicesService._round_money(balance_amount),
                        InvoicesService._round_money(gift_card_amount_used), 
                        promo_code_id, 
                        InvoicesService._round_money(promo_discount_amount), 
                        affiliate_id,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                invoice_result = cursor.fetchone()

                if not invoice_result:
                    raise ValueError("Failed to create invoice")

                # Create invoice items
                processed_items = []
                for item_data in invoice_items:
                    item = item_data['item']
                    product_id = item_data['product_id']
                    product_name = item_data['product_name']
                    batches = item_data.get('batches', [])
                    required_qty = float(item.quantity)
                    
                    # Determine batch_id based on status
                    batch_id_to_store = None
                    batch_allocations = []
                    
                    if should_check_availability and batches:
                        # Allocate batches using FIFO and deduct inventory
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
                        
                        # Use first batch_id for the invoice item
                        batch_id_to_store = batch_allocations[0]['batch_id'] if batch_allocations else None
                        
                        # Update store product current_qty
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                            SET current_qty = current_qty - %s, updated_by = %s
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND loc_id = %s AND product_id = %s""",
                            (float(required_qty), created_by, tenant_id, org_id, bus_id, loc_id, product_id),
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
                                    'INVOICE', invoice_id,
                                    cdate, ctime, cdatetime, created_by
                                ),
                            )
                    
                    # Create invoice item
                    invoice_item_id = Helper.generate_unique_identifier(prefix="invi")
                    taxes_applied_from_data = item_data.get('taxes_applied', [])
                    
                    # Prepare taxes_applied as JSON
                    taxes_applied_json = None
                    if taxes_applied_from_data:
                        taxes_applied_json = json.dumps([
                            {
                                'tax_id': tax.tax_id,
                                'tax_name': tax.tax_name,
                                'rate': float(tax.rate),
                                'is_inclusive': tax.is_inclusive,
                                'amount': float(tax.amount)
                            }
                            for tax in taxes_applied_from_data
                        ])
                    
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_INVOICE_ITEMS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, invoice_id, batch_id,
                         product_name, product_id, description,
                         base_selling_price, actual_price, price_after_pricing_rule,
                         price_after_tax, final_price, quantity, line_total,
                         tax_rate, is_inclusive, tax_amount, taxes_applied,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            invoice_item_id, tenant_id, org_id, bus_id, loc_id, invoice_id,
                            batch_id_to_store, product_name, product_id,
                            item.description,
                            InvoicesService._round_money(item_data['base_selling_price']), 
                            InvoicesService._round_money(item_data['actual_price']),
                            InvoicesService._round_money(item_data['price_after_pricing_rule']), 
                            InvoicesService._round_money(item_data['price_after_tax']),
                            InvoicesService._round_money(item_data['final_price']), 
                            float(item.quantity), 
                            InvoicesService._round_money(item_data['line_total']),
                            InvoicesService._round_money(item_data['tax_rate']), 
                            item_data['is_inclusive'], 
                            InvoicesService._round_money(item_data['tax_amount']),
                            taxes_applied_json,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    item_result = cursor.fetchone()
                    if item_result:
                        processed_items.append(dict(item_result))

                # Get invoice with customer name and items
                cursor.execute(
                    f"""SELECT i.*, c.fullname as customer_name
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON i.customer_id = c.id 
                        AND i.tenant_id = c.tenant_id 
                        AND i.org_id = c.org_id 
                        AND i.bus_id = c.bus_id
                    WHERE i.id = %s AND i.tenant_id = %s""",
                    (invoice_id, tenant_id),
                )
                invoice_with_customer = cursor.fetchone()

                if invoice_with_customer:
                    invoice_dict = dict(invoice_with_customer)
                    invoice_dict['customer_name'] = invoice_dict.get('customer_name') or customer_name
                else:
                    invoice_dict = dict(invoice_result)
                    invoice_dict['customer_name'] = customer_name

                # Get items for the invoice
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND invoice_id = %s
                    ORDER BY cdatetime ASC""",
                    (tenant_id, org_id, bus_id, loc_id, invoice_id),
                )
                items_results = cursor.fetchall()
                
                # Parse items and handle taxes_applied from JSON
                items_list = []
                for item in items_results:
                    item_dict = dict(item)
                    
                    # Parse taxes_applied from JSON
                    taxes_applied_list = []
                    if item_dict.get('taxes_applied'):
                        try:
                            if isinstance(item_dict['taxes_applied'], str):
                                taxes_applied_list = json.loads(item_dict['taxes_applied'])
                            elif isinstance(item_dict['taxes_applied'], list):
                                taxes_applied_list = item_dict['taxes_applied']
                            # Convert to TaxAppliedReadDto objects
                            item_dict['taxes_applied'] = [TaxAppliedReadDto(**tax) for tax in taxes_applied_list]
                            
                            # tax_rate is already stored in the database, no need to calculate from taxes_applied
                        except Exception as e:
                            logger.warning(f"Error parsing taxes_applied for item: {str(e)}")
                            item_dict['taxes_applied'] = []
                    else:
                        item_dict['taxes_applied'] = []
                    
                    items_list.append(InvoiceItemReadBase(**item_dict))
                
                invoice_dict['items'] = items_list
                
                # Get payments from sales_payments via invoice_sales
                cursor.execute(
                    f"""SELECT sp.*, ins.invoice_id
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                        ON sp.sale_id = ins.sale_id 
                        AND sp.tenant_id = ins.tenant_id 
                        AND sp.org_id = ins.org_id 
                        AND sp.bus_id = ins.bus_id 
                        AND sp.loc_id = ins.loc_id
                    WHERE ins.invoice_id = %s 
                        AND ins.tenant_id = %s 
                        AND ins.org_id = %s 
                        AND ins.bus_id = %s 
                        AND ins.loc_id = %s
                        AND ins.deleted_at IS NULL
                        AND sp.deleted_at IS NULL
                    ORDER BY sp.cdatetime ASC""",
                    (invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                payments_results = cursor.fetchall()
                # Convert sales payments to invoice payment format
                payments_list = []
                for payment in payments_results:
                    payment_dict = dict(payment)
                    invoice_payment = InvoicePaymentReadBase(
                        id=payment_dict['id'],
                        tenant_id=payment_dict['tenant_id'],
                        org_id=payment_dict['org_id'],
                        bus_id=payment_dict['bus_id'],
                        loc_id=payment_dict['loc_id'],
                        invoice_id=invoice_id,
                        payment_method=payment_dict['payment_method'],
                        payment_status=payment_dict['payment_status'],
                        paid_amount=float(payment_dict['paid_amount']),
                        gift_card_id=payment_dict.get('gift_card_id'),
                        description=payment_dict.get('description'),
                        cdate=payment_dict.get('cdate'),
                        ctime=payment_dict.get('ctime'),
                        cdatetime=payment_dict.get('cdatetime'),
                        created_by=payment_dict.get('created_by'),
                        updated_by=payment_dict.get('updated_by'),
                        deleted_by=payment_dict.get('deleted_by'),
                        deleted_at=payment_dict.get('deleted_at')
                    )
                    payments_list.append(invoice_payment)
                invoice_dict['payments'] = payments_list
                
                # Ensure amounts are included
                invoice_dict['total_amount'] = float(total_amount)
                invoice_dict['paid_amount'] = float(paid_amount)
                invoice_dict['balance_amount'] = float(balance_amount)

                invoice_read = CreateInvoiceServiceReadDto(**invoice_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_INVOICES_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (invoice_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(invoice_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-invoice",
                        resource_id=invoice_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Invoice {invoice_number} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as db_err:
                    # Database errors abort the transaction - re-raise immediately
                    # so transaction context manager can handle rollback
                    logger.error(f"Database error logging activity for invoice {invoice_id}: {str(db_err)}", exc_info=True)
                    raise ValueError(f"Failed to log activity for invoice: {str(db_err)}") from db_err
                except Exception as log_err:
                    # Non-database errors in activity logging - log warning but continue
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Invoice created successfully: {invoice_id}")

                return Respons(
                    success=True,
                    detail="Invoice created successfully",
                    data=[invoice_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating invoice: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create invoice: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_invoice(
        data: UpdateInvoiceServiceWriteDto,
        invoice_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[UpdateInvoiceServiceReadDto]:
        """Update an invoice"""
        logger.info(
            f"Processing invoice update: {invoice_id}",
            extra={
                "extra_fields": {
                    "invoice_id": invoice_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing invoice
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_INVOICES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s""",
                    (invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_invoice = cursor.fetchone()

                if not existing_invoice:
                    return Respons(
                        success=False,
                        detail="Invoice not found",
                        error="NOT_FOUND",
                    )
                
                old_data = dict(existing_invoice)
                
                # Check if invoice can be updated (cannot update invoices with status COMPLETED or CANCELLED)
                existing_status = existing_invoice.get('status', 'DRAFT').upper()
                if existing_status in ['COMPLETED', 'CANCELLED']:
                    return Respons(
                        success=False,
                        detail=f"Cannot update invoice with status {existing_status}",
                        error="INVALID_INVOICE_STATUS",
                    )

                # Build update query dynamically
                update_fields = []
                params = []

                if data.customer_id is not None:
                    # Validate customer
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

                if data.due_date is not None:
                    try:
                        due_date = datetime.strptime(data.due_date, "%Y-%m-%d").date()
                        update_fields.append("due_date = %s")
                        params.append(due_date)
                    except ValueError:
                        return Respons(
                            success=False,
                            detail="Invalid due_date format. Expected YYYY-MM-DD",
                            error="INVALID_DATE_FORMAT",
                        )

                if data.status is not None:
                    valid_statuses = ['DRAFT', 'COMPLETED', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED']
                    status = data.status.upper()
                    if status not in valid_statuses:
                        return Respons(
                            success=False,
                            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                            error="INVALID_STATUS",
                        )
                    update_fields.append("status = %s")
                    params.append(status)
                else:
                    # Use existing status if not updating
                    status = existing_invoice.get('status', 'DRAFT').upper()

                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)

                if not update_fields and not data.items:
                    return Respons(
                        success=False,
                        detail="No fields to update",
                        error="NO_UPDATE_FIELDS",
                    )

                # Update invoice if there are fields to update
                if update_fields:
                    update_fields.append("updated_by = %s")
                    params.append(updated_by)
                    params.extend([invoice_id, tenant_id, org_id, bus_id, loc_id])

                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_INVOICES_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        RETURNING *""",
                        tuple(params),
                    )
                    updated_invoice = cursor.fetchone()
                else:
                    updated_invoice = existing_invoice

                # Determine status for inventory check
                current_status = status if data.status is not None else existing_invoice.get('status', 'DRAFT').upper()
                should_check_availability = current_status in ['COMPLETED', 'PARTIALLY_PAID']

                # Update items if provided
                if data.items is not None:
                    # Check if we need to restore inventory (if invoice had inventory deducted)
                    old_status = existing_invoice.get('status', 'DRAFT').upper()
                    should_restore_old_inventory = old_status in ['COMPLETED', 'PARTIALLY_PAID']
                    
                    # Restore inventory for existing items if invoice had inventory deducted
                    if should_restore_old_inventory:
                        # Get existing items (same approach as sales - restore based on items, not movements)
                        cursor.execute(
                            f"""SELECT * FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                            WHERE invoice_id = %s AND tenant_id = %s AND org_id = %s 
                            AND bus_id = %s AND loc_id = %s""",
                            (invoice_id, tenant_id, org_id, bus_id, loc_id),
                        )
                        existing_items = cursor.fetchall()
                        
                        # Restore inventory for each existing item (same approach as sales)
                        restore_cdate = Helper.current_date_time()["cdate"]
                        restore_ctime = Helper.current_date_time()["ctime"]
                        restore_cdatetime = Helper.current_date_time()["cdatetime"]
                        
                        for existing_item in existing_items:
                            item_dict = dict(existing_item)
                            product_id = item_dict['product_id']
                            quantity = Decimal(str(item_dict['quantity']))
                            batch_id = item_dict.get('batch_id')
                            
                            # Restore to batch location if batch_id exists
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
                            
                            # Create reverse movement for this item (same approach as sales)
                            if batch_id:  # Only create reverse movement if batch_id exists
                                reverse_movement_id = Helper.generate_unique_identifier(prefix="mov")
                                cursor.execute(
                                    f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                                    (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                                     movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    RETURNING *""",
                                    (
                                        reverse_movement_id, tenant_id, org_id, bus_id, product_id,
                                        batch_id, 'STORE', loc_id,
                                        'IN', float(quantity),
                                        'INVOICE_UPDATE', invoice_id,
                                        restore_cdate, restore_ctime, restore_cdatetime, updated_by
                                    ),
                                )
                    
                    # If status requires inventory check, validate all new items first
                    if should_check_availability:
                        availability_errors = []
                        for item in data.items:
                            required_qty = float(item.quantity)
                            is_available, available_qty, batches = InvoicesService._check_inventory_availability(
                                tenant_id, org_id, bus_id, loc_id, item.product_id, required_qty, cursor
                            )
                            
                            if not is_available:
                                # Get product name for error message
                                cursor.execute(
                                    f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                    (item.product_id, tenant_id, org_id, bus_id),
                                )
                                product_result = cursor.fetchone()
                                product_name = product_result.get('name', 'Unknown') if product_result else 'Unknown'

                                availability_errors.append({
                                    'product_name': product_name,
                                    'product_id': item.product_id,
                                    'required_qty': required_qty,
                                    'available_qty': available_qty
                                })

                        if availability_errors:
                            error_details = []
                            for error in availability_errors:
                                error_details.append(
                                    f"product: {error['product_name']}, current_qty: {error['available_qty']}"
                                )

                            return Respons(
                                success=False,
                                detail=f"We don't have enough items available. {', '.join(error_details)}",
                                error="INSUFFICIENT_INVENTORY",
                            )

                    # Delete existing items (after restoring inventory)
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND invoice_id = %s""",
                        (tenant_id, org_id, bus_id, loc_id, invoice_id),
                    )

                    # Recalculate total
                    total_amount = Decimal('0')
                    cdate = Helper.current_date_time()["cdate"]
                    ctime = Helper.current_date_time()["ctime"]
                    cdatetime = Helper.current_date_time()["cdatetime"]

                    # Create new items (similar to create logic)
                    for item in data.items:
                        # Validate product
                        product_id = item.product_id

                        cursor.execute(
                            f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s AND delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, item.product_id),
                        )
                        product = cursor.fetchone()
                        product_name = product.get('name', 'Unknown') if product else 'Unknown'

                        # Get taxes_applied from item (for storing, not for calculation)
                        taxes_applied_from_input = item.taxes_applied if item.taxes_applied else []

                        # Use provided prices or calculate using SalesPriceCalculator (same as create)
                        base_selling_price = Decimal(str(item.base_selling_price)) if item.base_selling_price else Decimal('0')
                        actual_price = Decimal(str(item.actual_price)) if item.actual_price else Decimal('0')
                        price_after_pricing_rule = Decimal(str(item.price_after_pricing_rule)) if item.price_after_pricing_rule else Decimal('0')
                        price_after_tax = Decimal(str(item.price_after_tax)) if item.price_after_tax else Decimal('0')
                        final_price = Decimal(str(item.final_price)) if item.final_price else Decimal('0')
                        
                        # Use tax_rate and tax_amount directly from input (no calculation)
                        tax_rate = Decimal(str(item.tax_rate)) if item.tax_rate is not None else Decimal('0')
                        tax_amount = Decimal(str(item.tax_amount)) if item.tax_amount is not None else Decimal('0')
                        is_inclusive = item.is_inclusive if item.is_inclusive is not None else (any(tax.is_inclusive for tax in taxes_applied_from_input) if taxes_applied_from_input else False)
                        
                        if final_price == 0:
                            # Get product metadata for pricing calculation
                            product_metadata = {}
                            try:
                                cursor.execute(
                                    f"""SELECT pm.id, pm.of_type
                                    FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                                    INNER JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} pm 
                                        ON amp.product_metadata_id = pm.id 
                                        AND amp.tenant_id = pm.tenant_id 
                                        AND amp.org_id = pm.org_id 
                                        AND amp.bus_id = pm.bus_id
                                    WHERE amp.tenant_id = %s AND amp.org_id = %s AND bus_id = %s 
                                    AND amp.product_id = %s
                                    AND pm.delete_status = 'NOT_DELETED'""",
                                    (tenant_id, org_id, bus_id, product_id),
                                )
                                metadata_results = cursor.fetchall()
                                
                                for meta in metadata_results:
                                    meta_type = meta.get('of_type')
                                    meta_id = meta.get('id')
                                    
                                    if meta_type == 'CATEGORY':
                                        product_metadata['category_id'] = meta_id
                                    elif meta_type == 'TAG':
                                        product_metadata['tag_id'] = meta_id
                                    elif meta_type == 'BRAND':
                                        product_metadata['brand_id'] = meta_id
                                    elif meta_type == 'LABEL':
                                        product_metadata['label_id'] = meta_id
                            except Exception:
                                product_metadata = {}

                            # Get SKU
                            cursor.execute(
                                f"""SELECT sku FROM {db_settings.MSG_PRODUCTS_TABLE}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (product_id, tenant_id, org_id, bus_id),
                            )
                            product_sku = cursor.fetchone()
                            sku = product_sku.get('sku') if product_sku else None

                            # Calculate prices using SalesPriceCalculator (same as create)
                            prices = SalesPriceCalculator.calculate_sale_prices(
                                cursor, product_id, tenant_id, org_id, bus_id,
                                quantity=int(item.quantity),
                                base_selling_price=base_selling_price if base_selling_price > 0 else None,
                                location_id=loc_id,
                                sku=sku,
                                product_metadata=product_metadata if product_metadata else None
                            )
                            
                            # Extract calculated prices
                            base_selling_price = Decimal(str(prices.get('base_selling_price', 0) or 0))
                            actual_price = Decimal(str(prices.get('actual_price', 0) or 0))
                            price_after_pricing_rule = Decimal(str(prices.get('price_after_pricing_rule', 0) or 0))
                            price_after_tax = Decimal(str(prices.get('price_after_tax', 0) or 0))
                            final_price = Decimal(str(prices.get('final_price', 0) or 0))
                            
                            # Extract taxes_applied from calculator result and calculate totals
                            calculated_taxes_applied = prices.get('taxes_applied', [])
                            if calculated_taxes_applied:
                                # Convert to TaxAppliedItem format
                                from src.entities.invoices.invoices_base import TaxAppliedItem
                                taxes_applied_calculated = [
                                    TaxAppliedItem(
                                        tax_id=tax.get('tax_id', ''),
                                        tax_name=tax.get('tax_name', ''),
                                        rate=float(tax.get('rate', 0) or 0),
                                        is_inclusive=bool(tax.get('is_inclusive', False)),
                                        amount=float(tax.get('amount', 0) or 0)
                                    )
                                    for tax in calculated_taxes_applied
                                ]
                                # Only use calculator values if not provided in input
                                # tax_rate and tax_amount already set from input above - no calculation, use as-is
                                # Only update is_inclusive if not set from input
                                if not is_inclusive:
                                    is_inclusive = any(tax.is_inclusive for tax in taxes_applied_calculated)
                                taxes_applied_from_input = taxes_applied_calculated  # Use calculated taxes
                            else:
                                # Fallback to tax_rule_applied if no taxes_applied
                                tax_rule_applied = prices.get('tax_rule_applied')
                                if tax_rule_applied:
                                    from src.entities.invoices.invoices_base import TaxAppliedItem
                                    taxes_applied_from_input = [
                                        TaxAppliedItem(
                                            tax_id=tax_rule_applied.get('tax_id', ''),
                                            tax_name=tax_rule_applied.get('tax_name', ''),
                                            rate=float(tax_rule_applied.get('rate', 0) or 0),
                                            is_inclusive=bool(tax_rule_applied.get('is_inclusive', False)),
                                            amount=float(prices.get('tax_amount', 0) or 0)
                                        )
                                    ]
                                    # tax_rate and tax_amount already set from input above - no calculation, use as-is
                                    # Only update is_inclusive if not set from input
                                    if not is_inclusive:
                                        is_inclusive = tax_rule_applied.get('is_inclusive', False)
                                else:
                                    # tax_rate and tax_amount already set from input above - no calculation, use as-is
                                    # Only set defaults for taxes_applied and is_inclusive if needed
                                    if not taxes_applied_from_input:
                                        taxes_applied_from_input = []
                                    if not is_inclusive:
                                        is_inclusive = False
                        else:
                            # Use provided prices - taxes_applied already extracted from input above
                            # taxes_applied_from_input is already set from input item at the beginning
                            # tax_rate and tax_amount are already calculated from input taxes_applied
                            actual_price = Decimal(str(item.actual_price)) if item.actual_price else Decimal('0')
                            price_after_pricing_rule = Decimal(str(item.price_after_pricing_rule)) if item.price_after_pricing_rule else Decimal('0')
                            price_after_tax = Decimal(str(item.price_after_tax)) if item.price_after_tax else Decimal('0')

                        # Calculate line total (after price determination)
                        line_total = final_price * Decimal(str(item.quantity))
                        total_amount += line_total

                        # Get batches for this item if status requires inventory allocation
                        batches_for_item = []
                        if should_check_availability:
                            _, _, batches_for_item = InvoicesService._check_inventory_availability(
                                tenant_id, org_id, bus_id, loc_id, product_id, float(item.quantity), cursor
                            )
                        
                        # Determine batch_id based on status
                        batch_id_to_store = None
                        batch_allocations = []
                        
                        if should_check_availability and batches_for_item:
                            # Allocate batches using FIFO and deduct inventory
                            required_qty = float(item.quantity)
                            remaining_qty = required_qty
                            
                            for batch in batches_for_item:
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
                            
                            # Use first batch_id for the invoice item
                            batch_id_to_store = batch_allocations[0]['batch_id'] if batch_allocations else None
                            
                            # Update store product current_qty
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                                SET current_qty = current_qty - %s, updated_by = %s
                                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                AND loc_id = %s AND product_id = %s""",
                                (float(required_qty), updated_by, tenant_id, org_id, bus_id, loc_id, product_id),
                            )
                            
                            # Create product movements for each batch deduction
                            logger.info(f"Creating {len(batch_allocations)} product movement(s) for invoice update {invoice_id}")
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
                                        'INVOICE_UPDATE', invoice_id,
                                        cdate, ctime, cdatetime, updated_by
                                    ),
                                )
                                logger.info(
                                    f"Created product movement: movement_id={movement_id}, "
                                    f"batch_id={batch_allocation['batch_id']}, qty={batch_allocation['qty_deducted']}"
                                )
                            logger.info(f"All product movements created successfully for invoice update {invoice_id}")

                        invoice_item_id = Helper.generate_unique_identifier(prefix="invi")
                        
                        # Prepare taxes_applied as JSON
                        taxes_applied_json = None
                        if taxes_applied_from_input:
                            taxes_applied_json = json.dumps([
                                {
                                    'tax_id': tax.tax_id,
                                    'tax_name': tax.tax_name,
                                    'rate': float(tax.rate),
                                    'is_inclusive': tax.is_inclusive,
                                    'amount': float(tax.amount)
                                }
                                for tax in taxes_applied_from_input
                            ])
                        
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_INVOICE_ITEMS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, invoice_id, batch_id,
                             product_name, product_id, description,
                             base_selling_price, actual_price, price_after_pricing_rule,
                             price_after_tax, final_price, quantity, line_total,
                             tax_rate, is_inclusive, tax_amount, taxes_applied,
                             cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                invoice_item_id, tenant_id, org_id, bus_id, loc_id, invoice_id,
                                batch_id_to_store, product_name, item.product_id, item.description,
                                InvoicesService._round_money(base_selling_price), 
                                InvoicesService._round_money(actual_price),
                                InvoicesService._round_money(price_after_pricing_rule), 
                                InvoicesService._round_money(price_after_tax),
                                InvoicesService._round_money(final_price), 
                                float(item.quantity), 
                                InvoicesService._round_money(line_total),
                                InvoicesService._round_money(tax_rate), 
                                is_inclusive, 
                                InvoicesService._round_money(tax_amount),
                                taxes_applied_json,
                                cdate, ctime, cdatetime, updated_by
                            ),
                        )

                # Calculate total from items
                cursor.execute(
                    f"""SELECT COALESCE(SUM(line_total), 0) as total
                        FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND invoice_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id, invoice_id),
                )
                total_result = cursor.fetchone()
                calculated_total = Decimal(str(total_result.get('total', 0))) if total_result else Decimal('0')
                
                # Get current paid_amount from sales payments via invoice_sales
                cursor.execute(
                    f"""SELECT COALESCE(SUM(sp.paid_amount), 0) as total_paid
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                        ON sp.sale_id = ins.sale_id 
                        AND sp.tenant_id = ins.tenant_id 
                        AND sp.org_id = ins.org_id 
                        AND sp.bus_id = ins.bus_id 
                        AND sp.loc_id = ins.loc_id
                    WHERE ins.invoice_id = %s 
                        AND ins.tenant_id = %s 
                        AND ins.org_id = %s 
                        AND ins.bus_id = %s 
                        AND ins.loc_id = %s
                        AND sp.payment_status = 'SUCCESS'
                        AND ins.deleted_at IS NULL
                        AND sp.deleted_at IS NULL""",
                    (invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                paid_result = cursor.fetchone()
                calculated_paid = Decimal(str(paid_result.get('total_paid', 0))) if paid_result else Decimal('0')
                calculated_balance = calculated_total - calculated_paid
                
                # Update invoice with calculated amounts
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_INVOICES_TABLE}
                    SET total_amount = %s, paid_amount = %s, balance_amount = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (
                        float(calculated_total), float(calculated_paid), float(calculated_balance),
                        updated_by, invoice_id, tenant_id, org_id, bus_id, loc_id
                    ),
                )
                updated_invoice_with_amounts = cursor.fetchone()

                # Get updated invoice with customer name and items
                cursor.execute(
                    f"""SELECT i.*, c.fullname as customer_name
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON i.customer_id = c.id 
                        AND i.tenant_id = c.tenant_id 
                        AND i.org_id = c.org_id 
                        AND i.bus_id = c.bus_id
                    WHERE i.id = %s AND i.tenant_id = %s""",
                    (invoice_id, tenant_id),
                )
                invoice_with_customer = cursor.fetchone()

                if invoice_with_customer:
                    invoice_dict = dict(invoice_with_customer)
                    invoice_dict['customer_name'] = invoice_dict.get('customer_name')
                else:
                    invoice_dict = dict(updated_invoice_with_amounts) if updated_invoice_with_amounts else dict(updated_invoice) if updated_invoice else dict(existing_invoice)
                
                # Ensure amounts are included
                invoice_dict['total_amount'] = float(calculated_total)
                invoice_dict['paid_amount'] = float(calculated_paid)
                invoice_dict['balance_amount'] = float(calculated_balance)

                # Get items
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND invoice_id = %s
                    ORDER BY cdatetime ASC""",
                    (tenant_id, org_id, bus_id, loc_id, invoice_id),
                )
                items_results = cursor.fetchall()
                items_list = InvoicesService._parse_invoice_items_from_db(items_results)
                invoice_dict['items'] = items_list
                
                # Get payments from sales_payments via invoice_sales
                cursor.execute(
                    f"""SELECT sp.*, ins.invoice_id
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                        ON sp.sale_id = ins.sale_id 
                        AND sp.tenant_id = ins.tenant_id 
                        AND sp.org_id = ins.org_id 
                        AND sp.bus_id = ins.bus_id 
                        AND sp.loc_id = ins.loc_id
                    WHERE ins.invoice_id = %s 
                        AND ins.tenant_id = %s 
                        AND ins.org_id = %s 
                        AND ins.bus_id = %s 
                        AND ins.loc_id = %s
                        AND ins.deleted_at IS NULL
                        AND sp.deleted_at IS NULL
                    ORDER BY sp.cdatetime ASC""",
                    (invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                payments_results = cursor.fetchall()
                # Convert sales payments to invoice payment format
                payments_list = []
                for payment in payments_results:
                    payment_dict = dict(payment)
                    invoice_payment = InvoicePaymentReadBase(
                        id=payment_dict['id'],
                        tenant_id=payment_dict['tenant_id'],
                        org_id=payment_dict['org_id'],
                        bus_id=payment_dict['bus_id'],
                        loc_id=payment_dict['loc_id'],
                        invoice_id=invoice_id,
                        payment_method=payment_dict['payment_method'],
                        payment_status=payment_dict['payment_status'],
                        paid_amount=float(payment_dict['paid_amount']),
                        gift_card_id=payment_dict.get('gift_card_id'),
                        description=payment_dict.get('description'),
                        cdate=payment_dict.get('cdate'),
                        ctime=payment_dict.get('ctime'),
                        cdatetime=payment_dict.get('cdatetime'),
                        created_by=payment_dict.get('created_by'),
                        updated_by=payment_dict.get('updated_by'),
                        deleted_by=payment_dict.get('deleted_by'),
                        deleted_at=payment_dict.get('deleted_at')
                    )
                    payments_list.append(invoice_payment)
                invoice_dict['payments'] = payments_list

                invoice_read = UpdateInvoiceServiceReadDto(**invoice_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_INVOICES_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (invoice_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(invoice_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-invoice",
                        resource_id=invoice_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Invoice {invoice_dict.get('invoice_number', invoice_id)} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as db_err:
                    # Database errors abort the transaction - re-raise immediately
                    # so transaction context manager can handle rollback
                    logger.error(f"Database error logging activity for invoice {invoice_id}: {str(db_err)}", exc_info=True)
                    raise ValueError(f"Failed to log activity for invoice: {str(db_err)}") from db_err
                except Exception as log_err:
                    # Non-database errors in activity logging - log warning but continue
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Invoice updated successfully: {invoice_id}")

                return Respons(
                    success=True,
                    detail="Invoice updated successfully",
                    data=[invoice_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating invoice: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating invoice: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update invoice: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_invoice(
        invoice_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetInvoiceServiceReadDto]:
        """Get a single invoice by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT i.*, 
                           c.fullname as customer_name,
                           b.bus_name as business_name,
                           curr.id as currency_id,
                           curr.name as currency_name,
                           curr.symbol as currency_symbol
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON i.customer_id = c.id 
                        AND i.tenant_id = c.tenant_id 
                        AND i.org_id = c.org_id 
                        AND i.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_BUSINESSES_TABLE} b
                        ON i.bus_id = b.id
                        AND i.tenant_id = b.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} curr
                        ON curr.tenant_id = i.tenant_id
                        AND curr.is_default = true
                        AND curr.delete_status = 'NOT_DELETED'
                        AND curr.is_active = true
                    WHERE i.id = %s AND i.tenant_id = %s AND i.org_id = %s 
                    AND i.bus_id = %s AND i.loc_id = %s""",
                    (invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                invoice = cursor.fetchone()

                if not invoice:
                    return Respons(
                        success=False,
                        detail="Invoice not found",
                        error="NOT_FOUND",
                    )

                invoice_dict = dict(invoice)
                # Use stored amounts from invoice table, or calculate if not available
                total_amount = Decimal(str(invoice_dict.get('total_amount', 0) or 0))
                
                # Calculate paid_amount from sales payments via invoice_sales
                cursor.execute(
                    f"""SELECT COALESCE(SUM(sp.paid_amount), 0) as total_paid
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                        ON sp.sale_id = ins.sale_id 
                        AND sp.tenant_id = ins.tenant_id 
                        AND sp.org_id = ins.org_id 
                        AND sp.bus_id = ins.bus_id 
                        AND sp.loc_id = ins.loc_id
                    WHERE ins.invoice_id = %s 
                        AND ins.tenant_id = %s 
                        AND ins.org_id = %s 
                        AND ins.bus_id = %s 
                        AND ins.loc_id = %s
                        AND sp.payment_status = 'SUCCESS'
                        AND ins.deleted_at IS NULL
                        AND sp.deleted_at IS NULL""",
                    (invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                paid_result = cursor.fetchone()
                paid_amount = Decimal(str(paid_result['total_paid'])) if paid_result else Decimal('0')
                balance_amount = total_amount - paid_amount
                
                # If amounts are not stored, calculate from items
                if total_amount == 0:
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(line_total), 0) as total
                        FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND invoice_id = %s""",
                        (tenant_id, org_id, bus_id, loc_id, invoice_id),
                    )
                    total_result = cursor.fetchone()
                    total_amount = Decimal(str(total_result.get('total', 0))) if total_result else Decimal('0')
                    
                    # Calculate paid_amount from sales payments via invoice_sales
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(sp.paid_amount), 0) as total_paid
                        FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                        INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                            ON sp.sale_id = ins.sale_id 
                            AND sp.tenant_id = ins.tenant_id 
                            AND sp.org_id = ins.org_id 
                            AND sp.bus_id = ins.bus_id 
                            AND sp.loc_id = ins.loc_id
                        WHERE ins.invoice_id = %s 
                            AND ins.tenant_id = %s 
                            AND ins.org_id = %s 
                            AND ins.bus_id = %s 
                            AND ins.loc_id = %s
                            AND sp.payment_status = 'SUCCESS'
                            AND ins.deleted_at IS NULL
                            AND sp.deleted_at IS NULL""",
                        (invoice_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    paid_result = cursor.fetchone()
                    paid_amount = Decimal(str(paid_result.get('total_paid', 0))) if paid_result else Decimal('0')
                balance_amount = total_amount - paid_amount

                invoice_dict['total_amount'] = float(total_amount)
                invoice_dict['paid_amount'] = float(paid_amount)
                invoice_dict['balance_amount'] = float(balance_amount)

                # Get items
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND invoice_id = %s
                    ORDER BY cdatetime ASC""",
                    (tenant_id, org_id, bus_id, loc_id, invoice_id),
                )
                items_results = cursor.fetchall()
                items_list = InvoicesService._parse_invoice_items_from_db(items_results)
                invoice_dict['items'] = items_list
                
                # Get payments from sales_payments via invoice_sales
                cursor.execute(
                    f"""SELECT sp.*, ins.invoice_id
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                        ON sp.sale_id = ins.sale_id 
                        AND sp.tenant_id = ins.tenant_id 
                        AND sp.org_id = ins.org_id 
                        AND sp.bus_id = ins.bus_id 
                        AND sp.loc_id = ins.loc_id
                    WHERE ins.invoice_id = %s 
                        AND ins.tenant_id = %s 
                        AND ins.org_id = %s 
                        AND ins.bus_id = %s 
                        AND ins.loc_id = %s
                        AND ins.deleted_at IS NULL
                        AND sp.deleted_at IS NULL
                    ORDER BY sp.cdatetime ASC""",
                    (invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                payments_results = cursor.fetchall()
                # Convert sales payments to invoice payment format
                payments_list = []
                for payment in payments_results:
                    payment_dict = dict(payment)
                    invoice_payment = InvoicePaymentReadBase(
                        id=payment_dict['id'],
                        tenant_id=payment_dict['tenant_id'],
                        org_id=payment_dict['org_id'],
                        bus_id=payment_dict['bus_id'],
                        loc_id=payment_dict['loc_id'],
                        invoice_id=invoice_id,
                        payment_method=payment_dict['payment_method'],
                        payment_status=payment_dict['payment_status'],
                        paid_amount=float(payment_dict['paid_amount']),
                        gift_card_id=payment_dict.get('gift_card_id'),
                        description=payment_dict.get('description'),
                        cdate=payment_dict.get('cdate'),
                        ctime=payment_dict.get('ctime'),
                        cdatetime=payment_dict.get('cdatetime'),
                        created_by=payment_dict.get('created_by'),
                        updated_by=payment_dict.get('updated_by'),
                        deleted_by=payment_dict.get('deleted_by'),
                        deleted_at=payment_dict.get('deleted_at')
                    )
                    payments_list.append(invoice_payment)
                invoice_dict['payments'] = payments_list

                invoice_read = GetInvoiceServiceReadDto(**invoice_dict)

                return Respons(
                    success=True,
                    detail="Invoice retrieved successfully",
                    data=[invoice_read],
                )

        except Exception as e:
            logger.error(f"Error getting invoice: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get invoice: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_invoices(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[GetInvoicesServiceReadDto]:
        """Get list of invoices with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "i.tenant_id = %s",
                    "i.org_id = %s",
                    "i.bus_id = %s",
                    "i.loc_id = %s",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if customer_id:
                    where_conditions.append("i.customer_id = %s")
                    params.append(customer_id)
                if status:
                    # Validate status
                    valid_statuses = ['DRAFT', 'COMPLETED', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED']
                    status_upper = status.upper()
                    if status_upper not in valid_statuses:
                        return Respons(
                            success=False,
                            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                            error="INVALID_STATUS",
                        )
                    where_conditions.append("i.status = %s")
                    params.append(status_upper)
                if from_date:
                    where_conditions.append("DATE(i.sale_date) >= DATE(%s)")
                    params.append(from_date)
                if to_date:
                    where_conditions.append("DATE(i.sale_date) <= DATE(%s)")
                    params.append(to_date)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_INVOICES_TABLE} i WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = int(total_result.get('total', 0)) if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size

                # Get invoices
                cursor.execute(
                    f"""SELECT i.*, 
                           c.fullname as customer_name,
                           b.bus_name as business_name,
                           curr.id as currency_id,
                           curr.name as currency_name,
                           curr.symbol as currency_symbol
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON i.customer_id = c.id 
                        AND i.tenant_id = c.tenant_id 
                        AND i.org_id = c.org_id 
                        AND i.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_BUSINESSES_TABLE} b
                        ON i.bus_id = b.id
                        AND i.tenant_id = b.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} curr
                        ON curr.tenant_id = i.tenant_id
                        AND curr.is_default = true
                        AND curr.delete_status = 'NOT_DELETED'
                        AND curr.is_active = true
                    WHERE {where_clause}
                    ORDER BY i.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                invoices_results = cursor.fetchall()

                invoices_list = []
                for invoice_row in invoices_results:
                    invoice_dict = dict(invoice_row)
                    invoice_id = invoice_dict['id']

                    # Use stored amounts from invoice table, or calculate if not available
                    total_amount = Decimal(str(invoice_dict.get('total_amount', 0) or 0))
                    paid_amount = Decimal(str(invoice_dict.get('paid_amount', 0) or 0))
                    balance_amount = Decimal(str(invoice_dict.get('balance_amount', 0) or 0))
                    
                    # If amounts are not stored, calculate from items
                    if total_amount == 0:
                        cursor.execute(
                            f"""SELECT COALESCE(SUM(line_total), 0) as total
                            FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND loc_id = %s AND invoice_id = %s""",
                            (tenant_id, org_id, bus_id, loc_id, invoice_id),
                        )
                        total_result = cursor.fetchone()
                        total_amount = Decimal(str(total_result.get('total', 0))) if total_result else Decimal('0')
                        
                    # Calculate paid_amount from sales payments via invoice_sales
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(sp.paid_amount), 0) as total_paid
                        FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                        INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                            ON sp.sale_id = ins.sale_id 
                            AND sp.tenant_id = ins.tenant_id 
                            AND sp.org_id = ins.org_id 
                            AND sp.bus_id = ins.bus_id 
                            AND sp.loc_id = ins.loc_id
                        WHERE ins.invoice_id = %s 
                            AND ins.tenant_id = %s 
                            AND ins.org_id = %s 
                            AND ins.bus_id = %s 
                            AND ins.loc_id = %s
                            AND sp.payment_status = 'SUCCESS'
                            AND ins.deleted_at IS NULL
                            AND sp.deleted_at IS NULL""",
                        (invoice_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    paid_result = cursor.fetchone()
                    paid_amount = Decimal(str(paid_result.get('total_paid', 0))) if paid_result else Decimal('0')
                    balance_amount = total_amount - paid_amount

                    invoice_dict['total_amount'] = float(total_amount)
                    invoice_dict['paid_amount'] = float(paid_amount)
                    invoice_dict['balance_amount'] = float(balance_amount)

                    # Get items
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND invoice_id = %s
                        ORDER BY cdatetime ASC""",
                        (tenant_id, org_id, bus_id, loc_id, invoice_id),
                    )
                    items_results = cursor.fetchall()
                    items_list = InvoicesService._parse_invoice_items_from_db(items_results)
                    invoice_dict['items'] = items_list
                    
                    # For list view, don't include payments to avoid N+1 queries
                    # Payments can be retrieved via get_invoice if needed
                    invoice_dict['payments'] = []

                    invoices_list.append(InvoiceReadBase(**invoice_dict))

                result = GetInvoicesServiceReadDto(
                    invoices=invoices_list,
                    total=total,
                    page=page,
                    size=size,
                )

                return Respons(
                    success=True,
                    detail="Invoices retrieved successfully",
                    data=[result],
                )

        except Exception as e:
            logger.error(f"Error getting invoices: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get invoices: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_invoice(
        data: DeleteInvoiceServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        deleted_by: str
    ) -> Respons[DeleteInvoiceServiceReadDto]:
        """Delete an invoice (cascade deletes items)"""
        logger.info(
            f"Processing invoice deletion: {data.invoice_id}",
            extra={
                "extra_fields": {
                    "invoice_id": data.invoice_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing invoice
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_INVOICES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s""",
                    (data.invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_invoice = cursor.fetchone()

                if not existing_invoice:
                    return Respons(
                        success=False,
                        detail="Invoice not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_invoice)
                invoice_status = existing_invoice.get('status', 'DRAFT').upper()

                # If invoice had inventory deducted (COMPLETED or PARTIALLY_PAID), restore it
                should_restore_inventory = invoice_status in ['COMPLETED', 'PARTIALLY_PAID']
                
                if should_restore_inventory:
                    # Get invoice items to restore inventory
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                        WHERE invoice_id = %s AND tenant_id = %s AND org_id = %s 
                        AND bus_id = %s AND loc_id = %s""",
                        (data.invoice_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    invoice_items = cursor.fetchall()

                    # Restore inventory for each existing item (same approach as sales)
                    cdate = Helper.current_date_time()["cdate"]
                    ctime = Helper.current_date_time()["ctime"]
                    cdatetime = Helper.current_date_time()["cdatetime"]
                    
                    for existing_item in invoice_items:
                        item_dict = dict(existing_item)
                        product_id = item_dict['product_id']
                        quantity = Decimal(str(item_dict['quantity']))
                        batch_id = item_dict.get('batch_id')
                        
                        # Restore to batch location if batch_id exists
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
                            (float(quantity), deleted_by, tenant_id, org_id, bus_id, loc_id, product_id),
                        )
                        
                        # Create reverse movement for this item (same approach as sales)
                        if batch_id:  # Only create reverse movement if batch_id exists
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
                                    'IN', float(quantity),
                                    'INVOICE_DELETED', data.invoice_id,
                                    cdate, ctime, cdatetime, deleted_by
                                ),
                            )

                # Delete invoice items first (if not cascading)
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                    WHERE invoice_id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s""",
                    (data.invoice_id, tenant_id, org_id, bus_id, loc_id),
                )

                # Delete invoice permanently
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_INVOICES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (data.invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                deleted_invoice = cursor.fetchone()

                if not deleted_invoice:
                    return Respons(
                        success=False,
                        detail="Failed to delete invoice",
                        error="DELETE_FAILED",
                    )

                invoice_dict = dict(deleted_invoice)
                invoice_dict['total_amount'] = Decimal('0')
                invoice_dict['items'] = []
                invoice_read = DeleteInvoiceServiceReadDto(**invoice_dict)

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-invoice",
                        resource_id=data.invoice_id,
                        action="delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Invoice {invoice_dict.get('invoice_number', data.invoice_id)} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except (DatabaseError, IntegrityError) as db_err:
                    # Database errors abort the transaction - re-raise immediately
                    # so transaction context manager can handle rollback
                    logger.error(f"Database error logging activity for invoice {data.invoice_id}: {str(db_err)}", exc_info=True)
                    raise ValueError(f"Failed to log activity for invoice: {str(db_err)}") from db_err
                except Exception as log_err:
                    # Non-database errors in activity logging - log warning but continue
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Invoice deleted successfully: {data.invoice_id}")

                return Respons(
                    success=True,
                    detail="Invoice deleted successfully",
                    data=[invoice_read],
                )

        except Exception as e:
            logger.error(f"Error deleting invoice: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete invoice: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def create_payment(
        data: CreateInvoicePaymentServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateInvoicePaymentServiceReadDto]:
        """Create payments for an invoice by creating a sale with INSTANT or DEPOSIT mode"""
        total_payment_amount = sum(payment.paid_amount for payment in data.payments)
        logger.info(
            f"Processing invoice payment creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "invoice_id": data.invoice_id,
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
                # Validate invoice exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_INVOICES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                invoice = cursor.fetchone()

                if not invoice:
                    return Respons(
                        success=False,
                        detail="Invoice not found",
                        error="INVOICE_NOT_FOUND",
                    )

                invoice_dict = dict(invoice)
                if invoice_dict['status'] == 'CANCELLED':
                    return Respons(
                        success=False,
                        detail="Cannot add payment to a cancelled invoice",
                        error="INVOICE_CANCELLED",
                    )

                # Validate all payment methods
                valid_payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHEQUE', 'BITCOIN', 'GIFT_CARD', 'OTHERS']
                for idx, payment in enumerate(data.payments):
                    if payment.payment_method not in valid_payment_methods:
                        return Respons(
                            success=False,
                            detail=f"Invalid payment method at index {idx}: '{payment.payment_method}'. Must be one of: {', '.join(valid_payment_methods)}",
                            error="INVALID_PAYMENT_METHOD",
                        )

                total_amount = Decimal(str(invoice_dict.get('total_amount', 0)))
                
                # Get current total paid amount from existing sales payments via invoice_sales
                cursor.execute(
                    f"""SELECT COALESCE(SUM(sp.paid_amount), 0) as current_paid
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                        ON sp.sale_id = ins.sale_id 
                        AND sp.tenant_id = ins.tenant_id 
                        AND sp.org_id = ins.org_id 
                        AND sp.bus_id = ins.bus_id 
                        AND sp.loc_id = ins.loc_id
                    WHERE ins.invoice_id = %s 
                        AND ins.tenant_id = %s 
                        AND ins.org_id = %s 
                        AND ins.bus_id = %s 
                        AND ins.loc_id = %s
                        AND sp.payment_status = 'SUCCESS'
                        AND ins.deleted_at IS NULL
                        AND sp.deleted_at IS NULL""",
                    (data.invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                current_paid_result = cursor.fetchone()
                current_paid = Decimal(str(current_paid_result['current_paid'])) if current_paid_result else Decimal('0')
                
                # Calculate total payment amount from all payments
                total_payment_amount_decimal = Decimal('0')
                for payment in data.payments:
                    total_payment_amount_decimal += Decimal(str(payment.paid_amount))
                
                # Validation: Cannot accept payment that exceeds total amount
                remaining_balance = total_amount - current_paid
                
                if total_payment_amount_decimal > remaining_balance:
                    return Respons(
                        success=False,
                        detail=f"Total payment amount ({float(total_payment_amount_decimal):.2f}) exceeds remaining balance ({float(remaining_balance):.2f}). Total invoice amount: {float(total_amount):.2f}, Already paid: {float(current_paid):.2f}. Please pay the exact remaining amount.",
                        error="PAYMENT_EXCEEDS_BALANCE",
                    )

                # Get invoice items to convert to sale items
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_INVOICE_ITEMS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND invoice_id = %s
                    ORDER BY cdatetime ASC""",
                    (tenant_id, org_id, bus_id, loc_id, data.invoice_id),
                )
                invoice_items_results = cursor.fetchall()
                
                if not invoice_items_results:
                    return Respons(
                        success=False,
                        detail="Invoice has no items",
                        error="INVOICE_NO_ITEMS",
                    )

                # Convert invoice items to sale items
                sale_items = []
                for invoice_item in invoice_items_results:
                    item_dict = dict(invoice_item)
                    
                    # Parse taxes_applied from JSON
                    taxes_applied_list = []
                    if item_dict.get('taxes_applied'):
                        try:
                            if isinstance(item_dict['taxes_applied'], str):
                                taxes_applied_list = json.loads(item_dict['taxes_applied'])
                            elif isinstance(item_dict['taxes_applied'], list):
                                taxes_applied_list = item_dict['taxes_applied']
                        except Exception as e:
                            logger.warning(f"Error parsing taxes_applied for item: {str(e)}")
                            taxes_applied_list = []
                    
                    # Convert to SaleTaxAppliedItem
                    sale_taxes_applied = [
                        SaleTaxAppliedItem(
                            tax_id=tax.get('tax_id', ''),
                            tax_name=tax.get('tax_name', ''),
                            rate=float(tax.get('rate', 0) or 0),
                            is_inclusive=bool(tax.get('is_inclusive', False)),
                            amount=float(tax.get('amount', 0) or 0)
                        )
                        for tax in taxes_applied_list
                    ]
                    
                    sale_item = SaleItemBase(
                        product_id=item_dict['product_id'],
                        quantity=float(item_dict['quantity']),
                        base_selling_price=float(item_dict.get('base_selling_price', 0)),
                        actual_price=float(item_dict.get('actual_price', 0)),
                        price_after_pricing_rule=float(item_dict.get('price_after_pricing_rule', 0)),
                        price_after_tax=float(item_dict.get('price_after_tax', 0)),
                        final_price=float(item_dict.get('final_price', 0)),
                        taxes_applied=sale_taxes_applied,
                        tax_rate=float(item_dict.get('tax_rate', 0)),
                        tax_amount=float(item_dict.get('tax_amount', 0)),
                        is_inclusive=bool(item_dict.get('is_inclusive', False)) if item_dict.get('is_inclusive') is not None else False,
                        description=item_dict.get('description')
                    )
                    sale_items.append(sale_item)

                # Determine sale_mode: INSTANT if fully paid, DEPOSIT if partially paid
                new_total_paid = current_paid + total_payment_amount_decimal
                is_fully_paid = new_total_paid >= total_amount
                sale_mode = 'INSTANT' if is_fully_paid else 'DEPOSIT'
                
                # Check inventory availability BEFORE creating sale
                # Only check if inventory will be deducted (when fully paid or in INSTANT mode with full payment)
                # The sales service will also check, but we want to fail early with clear error messages
                inventory_errors = []
                if is_fully_paid:
                    # When invoice becomes fully paid, inventory will be deducted
                    # Check availability for all items
                    for sale_item in sale_items:
                        is_available, available_qty, batches = StoreSalesService._check_inventory_availability(
                            tenant_id, org_id, bus_id, loc_id, sale_item.product_id, sale_item.quantity, cursor
                        )
                        
                        if not is_available:
                            # Get product name for error message
                            cursor.execute(
                                f"""SELECT name FROM {db_settings.MSG_PRODUCTS_TABLE}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                                (sale_item.product_id, tenant_id, org_id, bus_id),
                            )
                            product = cursor.fetchone()
                            product_name = product.get('name', sale_item.product_id) if product else sale_item.product_id
                            
                            inventory_errors.append({
                                'product_id': sale_item.product_id,
                                'product_name': product_name,
                                'required_qty': float(sale_item.quantity),
                                'available_qty': available_qty
                            })
                    
                    if inventory_errors:
                        # Build detailed error message
                        error_details = []
                        for error in inventory_errors:
                            error_details.append(
                                f"Product '{error['product_name']}' (ID: {error['product_id']}): "
                                f"Required {error['required_qty']} units, but only {error['available_qty']} units available"
                            )
                        
                        error_message = (
                            f"Cannot process payment - insufficient inventory for {len(inventory_errors)} product(s). "
                            f"{'; '.join(error_details)}. "
                            f"Please add stock or adjust quantities before processing payment."
                        )
                        
                        return Respons(
                            success=False,
                            detail=error_message,
                            error="INSUFFICIENT_INVENTORY",
                        )
                
                # Convert invoice payments to sale payments
                sale_payments = [
                    SalePaymentInputBase(
                        payment_method=payment.payment_method,
                        paid_amount=payment.paid_amount,
                        description=payment.description
                    )
                    for payment in data.payments
                ]

                # Get invoice sale_date
                sale_date = invoice_dict.get('sale_date')
                if isinstance(sale_date, str):
                    sale_date_str = sale_date
                elif hasattr(sale_date, 'strftime'):
                    sale_date_str = sale_date.strftime("%Y-%m-%d")
                else:
                    sale_date_str = datetime.now().strftime("%Y-%m-%d")

                # Create sale using StoreSalesService
                # Note: When invoice is fully paid, sale_mode will be INSTANT, but paid_amount
                # might be less than total_amount if there were previous payments.
                # The sales service will check: paid_amount == total_amount for INSTANT mode.
                # So inventory might not be deducted automatically. We'll need to handle this
                # by ensuring the sale reflects the full payment when the invoice is fully paid.
                sale_data = CreateSaleServiceWriteDto(
                    customer_id=invoice_dict.get('customer_id'),
                    sale_date=sale_date_str,
                    sale_mode=sale_mode,
                    description=f"Payment for invoice {invoice_dict.get('invoice_number', data.invoice_id)}",
                    items=sale_items,
                    payments=sale_payments,
                    verified_total_amount=float(total_amount),
                    verified_promo_discount_amount=float(invoice_dict.get('promo_discount_amount', 0)),
                    verified_final_total_amount=float(total_amount),
                    verified_promo_code_id=invoice_dict.get('promo_code_id'),
                    verified_gift_card_id=invoice_dict.get('gift_card_id'),
                    verified_affiliate_id=invoice_dict.get('affiliate_id')
                )

                # Create sale (this will handle inventory, payments, etc.)
                sale_result = StoreSalesService.create_sale(
                    data=sale_data,
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            loc_id=loc_id,
                    created_by=created_by
                )

                if not sale_result.success:
                    return Respons(
                        success=False,
                        detail=f"Failed to create sale: {sale_result.detail}",
                        error=sale_result.error or "SALE_CREATION_FAILED",
                    )

                # Get the created sale ID from the result
                sale_data_result = sale_result.data
                sale_id = None
                
                if sale_data_result:
                    if hasattr(sale_data_result, 'id'):
                        sale_id = sale_data_result.id
                    elif isinstance(sale_data_result, dict):
                        sale_id = sale_data_result.get('id')
                    elif isinstance(sale_data_result, list) and len(sale_data_result) > 0:
                        first_item = sale_data_result[0]
                        if hasattr(first_item, 'id'):
                            sale_id = first_item.id
                        elif isinstance(first_item, dict):
                            sale_id = first_item.get('id')

                if not sale_id:
                    # Fallback: query the most recent sale for this location created by this user
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_SALES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND created_by = %s
                        ORDER BY cdatetime DESC LIMIT 1""",
                        (tenant_id, org_id, bus_id, loc_id, created_by),
                    )
                    latest_sale = cursor.fetchone()
                    sale_id = latest_sale['id'] if latest_sale else None

                if not sale_id:
                    raise ValueError("Failed to retrieve created sale ID")

                # Create invoice_sales linking record
                invoice_sales_id = Helper.generate_unique_identifier(prefix="invsal")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_INVOICE_SALES_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, invoice_id, sale_id,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        invoice_sales_id, tenant_id, org_id, bus_id, loc_id,
                        data.invoice_id, sale_id,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                invoice_sales_result = cursor.fetchone()

                if not invoice_sales_result:
                    raise ValueError("Failed to create invoice_sales record")

                # Recalculate paid_amount and balance_amount from sales payments via invoice_sales
                cursor.execute(
                    f"""SELECT COALESCE(SUM(sp.paid_amount), 0) as total_paid
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_INVOICE_SALES_TABLE} ins 
                        ON sp.sale_id = ins.sale_id 
                        AND sp.tenant_id = ins.tenant_id 
                        AND sp.org_id = ins.org_id 
                        AND sp.bus_id = ins.bus_id 
                        AND sp.loc_id = ins.loc_id
                    WHERE ins.invoice_id = %s 
                        AND ins.tenant_id = %s 
                        AND ins.org_id = %s 
                        AND ins.bus_id = %s 
                        AND ins.loc_id = %s
                        AND sp.payment_status = 'SUCCESS'
                        AND ins.deleted_at IS NULL
                        AND sp.deleted_at IS NULL""",
                    (data.invoice_id, tenant_id, org_id, bus_id, loc_id),
                )
                total_paid_result = cursor.fetchone()
                total_paid = Decimal(str(total_paid_result['total_paid'])) if total_paid_result else Decimal('0')
                balance_amount = total_amount - total_paid
                
                # Update invoice status based on payments
                if total_paid >= total_amount:
                    new_status = 'COMPLETED'
                elif total_paid > 0:
                    new_status = 'PARTIALLY_PAID'
                else:
                    new_status = 'DRAFT'
                
                # Update invoice with new amounts and status
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_INVOICES_TABLE}
                    SET paid_amount = %s, balance_amount = %s, status = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (
                        float(total_paid), float(balance_amount), new_status, created_by,
                        data.invoice_id, tenant_id, org_id, bus_id, loc_id
                    ),
                )

                # Get sale payments to return
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND sale_id = %s
                    AND deleted_at IS NULL
                    ORDER BY cdatetime ASC""",
                    (tenant_id, org_id, bus_id, loc_id, sale_id),
                )
                sale_payments_results = cursor.fetchall()
                
                # Convert sale payments to invoice payment format for response
                created_payments = []
                for sale_payment in sale_payments_results:
                    payment_dict = dict(sale_payment)
                    # Create a response DTO that matches CreateInvoicePaymentServiceReadDto structure
                    # We'll use the sale payment data but format it as invoice payment
                    payment_read = CreateInvoicePaymentServiceReadDto(
                        id=payment_dict['id'],
                        tenant_id=payment_dict['tenant_id'],
                        org_id=payment_dict['org_id'],
                        bus_id=payment_dict['bus_id'],
                        loc_id=payment_dict['loc_id'],
                        invoice_id=data.invoice_id,  # Use invoice_id instead of sale_id
                        payment_method=payment_dict['payment_method'],
                        payment_status=payment_dict['payment_status'],
                        paid_amount=float(payment_dict['paid_amount']),
                        gift_card_id=None,
                        description=payment_dict.get('description'),
                        cdate=payment_dict.get('cdate'),
                        ctime=payment_dict.get('ctime'),
                        cdatetime=payment_dict.get('cdatetime'),
                        created_by=payment_dict.get('created_by'),
                        updated_by=payment_dict.get('updated_by'),
                        deleted_by=payment_dict.get('deleted_by'),
                        deleted_at=payment_dict.get('deleted_at')
                    )
                    created_payments.append(payment_read)

                logger.info(
                    f"Sale created successfully for invoice payment: sale_id={sale_id}",
                    extra={
                        "extra_fields": {
                            "sale_id": sale_id,
                            "invoice_id": data.invoice_id,
                            "sale_mode": sale_mode,
                            "new_invoice_status": new_status,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail=f"Successfully created sale for invoice payment",
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
    def get_invoice_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Respons[GetInvoiceStatisticsServiceReadDto]:
        """Get invoice statistics with optional date filtering on sale_date field"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause for invoices
                where_conditions = [
                    "i.tenant_id = %s",
                    "i.org_id = %s",
                    "i.bus_id = %s",
                    "i.loc_id = %s",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                # Date filtering on sale_date
                if from_date is not None or to_date is not None:
                    if from_date is not None and to_date is not None:
                        # Both dates provided - range filter
                        where_conditions.append("DATE(i.sale_date) >= %s AND DATE(i.sale_date) <= %s")
                        params.extend([from_date, to_date])
                    elif from_date is not None:
                        # Only from_date provided
                        where_conditions.append("DATE(i.sale_date) >= %s")
                        params.append(from_date)
                    elif to_date is not None:
                        # Only to_date provided
                        where_conditions.append("DATE(i.sale_date) <= %s")
                        params.append(to_date)

                where_clause = " AND ".join(where_conditions)

                # Get invoice statistics by joining invoices with invoice_items to calculate totals
                cursor.execute(
                    f"""SELECT 
                        COUNT(DISTINCT i.id) as total_invoices,
                        COALESCE(SUM(ii.line_total), 0) as total_amount,
                        COALESCE(SUM(CASE WHEN i.status = 'DRAFT' THEN ii.line_total ELSE 0 END), 0) as total_draft,
                        COALESCE(SUM(CASE WHEN i.status = 'COMPLETED' THEN ii.line_total ELSE 0 END), 0) as total_completed,
                        COALESCE(SUM(CASE WHEN i.status = 'PARTIALLY_PAID' THEN ii.line_total ELSE 0 END), 0) as total_partially_paid,
                        COALESCE(SUM(CASE WHEN i.status = 'OVERDUE' THEN ii.line_total ELSE 0 END), 0) as total_overdue,
                        COALESCE(SUM(CASE WHEN i.status = 'CANCELLED' THEN ii.line_total ELSE 0 END), 0) as total_cancelled,
                        COUNT(DISTINCT CASE WHEN i.status = 'DRAFT' THEN i.id END) as count_draft,
                        COUNT(DISTINCT CASE WHEN i.status = 'COMPLETED' THEN i.id END) as count_completed,
                        COUNT(DISTINCT CASE WHEN i.status = 'PARTIALLY_PAID' THEN i.id END) as count_partially_paid,
                        COUNT(DISTINCT CASE WHEN i.status = 'OVERDUE' THEN i.id END) as count_overdue,
                        COUNT(DISTINCT CASE WHEN i.status = 'CANCELLED' THEN i.id END) as count_cancelled
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    LEFT JOIN {db_settings.MSG_INVOICE_ITEMS_TABLE} ii 
                        ON i.id = ii.invoice_id 
                        AND i.tenant_id = ii.tenant_id 
                        AND i.org_id = ii.org_id 
                        AND i.bus_id = ii.bus_id 
                        AND i.loc_id = ii.loc_id
                    WHERE {where_clause}""",
                    tuple(params),
                )
                stats_row = cursor.fetchone()

                # Handle None case
                if stats_row is None:
                    logger.warning("Statistics query returned no rows - using default values")
                    stats_row = {}

                # Round all Decimal values to 2 decimal places
                from decimal import ROUND_HALF_UP
                two_places = Decimal('0.01')
                
                total_invoices = int(stats_row.get('total_invoices', 0)) if stats_row else 0
                total_amount = Decimal(str(stats_row.get('total_amount', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_draft = Decimal(str(stats_row.get('total_draft', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_completed = Decimal(str(stats_row.get('total_completed', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_partially_paid = Decimal(str(stats_row.get('total_partially_paid', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_overdue = Decimal(str(stats_row.get('total_overdue', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_cancelled = Decimal(str(stats_row.get('total_cancelled', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                count_draft = int(stats_row.get('count_draft', 0)) if stats_row else 0
                count_completed = int(stats_row.get('count_completed', 0)) if stats_row else 0
                count_partially_paid = int(stats_row.get('count_partially_paid', 0)) if stats_row else 0
                count_overdue = int(stats_row.get('count_overdue', 0)) if stats_row else 0
                count_cancelled = int(stats_row.get('count_cancelled', 0)) if stats_row else 0
                
                logger.info(
                    f"Invoice statistics calculated: total_invoices={total_invoices}, total_amount={total_amount}, "
                    f"total_draft={total_draft}, total_completed={total_completed}, "
                    f"total_partially_paid={total_partially_paid}, total_overdue={total_overdue}, "
                    f"total_cancelled={total_cancelled}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "loc_id": loc_id,
                            "from_date": str(from_date) if from_date else None,
                            "to_date": str(to_date) if to_date else None,
                        }
                    },
                )
                
                statistics = GetInvoiceStatisticsServiceReadDto(
                    total_invoices=total_invoices,
                    total_amount=total_amount,
                    total_draft=total_draft,
                    total_completed=total_completed,
                    total_partially_paid=total_partially_paid,
                    total_overdue=total_overdue,
                    total_cancelled=total_cancelled,
                    count_draft=count_draft,
                    count_completed=count_completed,
                    count_partially_paid=count_partially_paid,
                    count_overdue=count_overdue,
                    count_cancelled=count_cancelled,
                )

                return Respons(
                    success=True,
                    detail="Invoice statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting invoice statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get invoice statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

