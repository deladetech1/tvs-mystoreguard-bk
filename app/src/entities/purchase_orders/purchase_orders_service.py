from typing import Optional, List
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from collections import defaultdict
from src.entities.purchase_orders.purchase_orders_read_dto import (
    CreatePurchaseOrderServiceReadDto,
    UpdatePurchaseOrderServiceReadDto,
    GetPurchaseOrderServiceReadDto,
    GetPurchaseOrdersServiceReadDto,
    PurchaseOrderItemReadDto,
    PurchaseOrderReadBase,
    PurchaseBatchReadDto,
    PurchaseReceiptForBatchReadDto,
    ProductMovementReadDto,
    CancelPurchaseOrderServiceReadDto,
    PermanentDeletePurchaseOrderServiceReadDto,
    ReceivePurchaseOrderServiceReadDto,
    PurchaseReceiptReadBase,
    CurrencyReadDto,
    GetPurchaseOrderStatisticsServiceReadDto,
    GetPurchaseReceiptServiceReadDto,
    GetPurchaseReceiptsServiceReadDto,
    UpdatePurchaseReceiptServiceReadDto,
    DeletePurchaseReceiptServiceReadDto,
)
from src.entities.purchase_orders.purchase_orders_write_dto import (
    CreatePurchaseOrderServiceWriteDto,
    UpdatePurchaseOrderServiceWriteDto,
    CancelPurchaseOrderServiceWriteDto,
    PermanentDeletePurchaseOrderServiceWriteDto,
    ReceivePurchaseOrderServiceWriteDto,
    UpdatePurchaseReceiptServiceWriteDto,
    DeletePurchaseReceiptServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("purchase_orders_service")


class PurchaseOrdersService:
    """Service class for purchase orders operations"""

    @staticmethod
    def _generate_po_number(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> str:
        """Generate a systematic purchase order number in format PO-YYYYMMDD-NNN"""
        from datetime import datetime
        
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"PO-{today}"
        
        cursor.execute(
            f"""SELECT po_number 
            FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
            AND po_number LIKE %s
            ORDER BY po_number DESC
            LIMIT 1""",
            (tenant_id, org_id, bus_id, f"{prefix}-%"),
        )
        last_po = cursor.fetchone()
        
        if last_po and last_po.get('po_number'):
            last_number = last_po['po_number']
            try:
                sequence_str = last_number.split('-')[-1]
                sequence_num = int(sequence_str)
                next_sequence = sequence_num + 1
            except (ValueError, IndexError):
                next_sequence = 1
        else:
            next_sequence = 1
        
        po_number = f"{prefix}-{next_sequence:03d}"
        
        max_attempts = 1000
        attempts = 0
        while attempts < max_attempts:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND po_number = %s""",
                (tenant_id, org_id, bus_id, po_number),
            )
            if not cursor.fetchone():
                return po_number
            
            next_sequence += 1
            po_number = f"{prefix}-{next_sequence:03d}"
            attempts += 1
        
        import time
        timestamp_suffix = int(time.time() * 1000) % 10000
        po_number = f"{prefix}-{timestamp_suffix:04d}"
        
        return po_number

    @staticmethod
    def _generate_receipt_number(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> str:
        """Generate a systematic receipt number in format GRN-YYYYMMDD-NNN"""
        from datetime import datetime
        
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"GRN-{today}"
        
        cursor.execute(
            f"""SELECT receipt_number 
            FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
            AND receipt_number LIKE %s
            ORDER BY receipt_number DESC
            LIMIT 1""",
            (tenant_id, org_id, bus_id, f"{prefix}-%"),
        )
        last_receipt = cursor.fetchone()
        
        if last_receipt and last_receipt.get('receipt_number'):
            last_number = last_receipt['receipt_number']
            try:
                sequence_str = last_number.split('-')[-1]
                sequence_num = int(sequence_str)
                next_sequence = sequence_num + 1
            except (ValueError, IndexError):
                next_sequence = 1
        else:
            next_sequence = 1
        
        receipt_number = f"{prefix}-{next_sequence:03d}"
        
        max_attempts = 1000
        attempts = 0
        while attempts < max_attempts:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND receipt_number = %s""",
                (tenant_id, org_id, bus_id, receipt_number),
            )
            if not cursor.fetchone():
                return receipt_number
            
            next_sequence += 1
            receipt_number = f"{prefix}-{next_sequence:03d}"
            attempts += 1
        
        import time
        timestamp_suffix = int(time.time() * 1000) % 10000
        receipt_number = f"{prefix}-{timestamp_suffix:04d}"
        
        return receipt_number

    @staticmethod
    def _generate_batch_number(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> str:
        """Generate a systematic batch number in format BA-YYYYMMDD-NNN"""
        from datetime import datetime
        
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"BA-{today}"
        
        cursor.execute(
            f"""SELECT batch_number 
            FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
            AND batch_number LIKE %s
            AND delete_status = 'NOT_DELETED'
            ORDER BY batch_number DESC
            LIMIT 1""",
            (tenant_id, org_id, bus_id, f"{prefix}-%"),
        )
        last_batch = cursor.fetchone()
        
        if last_batch and last_batch.get('batch_number'):
            last_number = last_batch['batch_number']
            try:
                sequence_str = last_number.split('-')[-1]
                sequence_num = int(sequence_str)
                next_sequence = sequence_num + 1
            except (ValueError, IndexError):
                next_sequence = 1
        else:
            next_sequence = 1
        
        batch_number = f"{prefix}-{next_sequence:03d}"
        
        max_attempts = 1000
        attempts = 0
        while attempts < max_attempts:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND batch_number = %s 
                AND delete_status = 'NOT_DELETED'""",
                (tenant_id, org_id, bus_id, batch_number),
            )
            if not cursor.fetchone():
                return batch_number
            
            next_sequence += 1
            batch_number = f"{prefix}-{next_sequence:03d}"
            attempts += 1
        
        import time
        timestamp_suffix = int(time.time() * 1000) % 10000
        batch_number = f"{prefix}-{timestamp_suffix:04d}"
        
        return batch_number

    @staticmethod
    def _get_purchase_order_items(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        purchase_order_id: str
    ) -> List[dict]:
        """Get items for a purchase order with related names"""
        cursor.execute(
            f"""SELECT poi.*,
                   p.name as product_name,
                   c.name as currency_name,
                   c.code as currency_code,
                   c.symbol as currency_symbol,
                   c.decimal_places as currency_decimal_places,
                   c.currency_position as currency_position
            FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi
            LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON poi.product_id = p.id 
                AND poi.tenant_id = p.tenant_id 
                AND poi.org_id = p.org_id 
                AND poi.bus_id = p.bus_id
            LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON poi.currency_id = c.id 
                AND poi.tenant_id = c.tenant_id
            WHERE poi.tenant_id = %s AND poi.org_id = %s AND poi.bus_id = %s 
            AND poi.purchase_order_id = %s
            ORDER BY poi.id""",
            (tenant_id, org_id, bus_id, purchase_order_id),
        )
        items = cursor.fetchall()
        result = []
        for item in items:
            item_dict = dict(item)
            if item_dict.get('product_expiry_date') and isinstance(item_dict['product_expiry_date'], date):
                item_dict['product_expiry_date'] = item_dict['product_expiry_date'].isoformat()
            result.append(item_dict)
        return result

    @staticmethod
    def _get_purchase_order_batches(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        purchase_order_id: str
    ) -> List[dict]:
        """Get batches for a purchase order - only batches created when receiving this purchase order"""
        cursor.execute(
            f"""SELECT DISTINCT pb.*,
                   creator.fullname as created_by,
                   updater.fullname as updated_by,
                   deleter.fullname as deleted_by,
                   c.name as currency_name,
                   c.code as currency_code,
                   c.symbol as currency_symbol,
                   c.decimal_places as currency_decimal_places,
                   c.currency_position as currency_position,
                   uom.name as unit_of_measure_name,
                   s.fullname as supplier_name,
                   pr.id as receipt_id,
                   pr.receipt_number as receipt_number,
                   pr.received_date as receipt_received_date,
                   pr.description as receipt_description,
                   pr.status as receipt_status,
                   pr.cdatetime as receipt_cdatetime
            FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
            INNER JOIN {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm ON pb.id = pm.batch_id 
                AND pb.tenant_id = pm.tenant_id 
                AND pb.org_id = pm.org_id 
                AND pb.bus_id = pm.bus_id
            INNER JOIN {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr ON pm.reference_id = pr.id 
                AND pm.reason = 'PURCHASE'
                AND pr.tenant_id = pm.tenant_id 
                AND pr.org_id = pm.org_id 
                AND pr.bus_id = pm.bus_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pb.created_by = creator.id AND pb.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON pb.updated_by = updater.id AND pb.tenant_id = updater.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON pb.deleted_by = deleter.id AND pb.tenant_id = deleter.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON pb.currency_id = c.id AND pb.tenant_id = c.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE} uom ON pb.unit_of_measure_id = uom.id AND pb.tenant_id = uom.tenant_id
            LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON pb.supplier_id = s.id AND pb.tenant_id = s.tenant_id AND pb.org_id = s.org_id AND pb.bus_id = s.bus_id
            WHERE pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s 
            AND pb.delete_status = 'NOT_DELETED'
            AND pb.batch_type = 'PURCHASE'
            AND pr.purchase_order_id = %s
            ORDER BY pb.cdatetime DESC""",
            (tenant_id, org_id, bus_id, purchase_order_id),
        )
        batches = cursor.fetchall()
        # Convert date objects to strings for product_expiry_date and receipt dates
        from datetime import date
        batch_list = []
        for batch in batches:
            batch_dict = dict(batch)
            if batch_dict.get('product_expiry_date') and isinstance(batch_dict['product_expiry_date'], date):
                batch_dict['product_expiry_date'] = batch_dict['product_expiry_date'].isoformat()
            
            # Extract receipt information and create receipt object
            if batch_dict.get('receipt_id'):
                receipt_dict = {
                    'id': batch_dict.pop('receipt_id'),
                    'receipt_number': batch_dict.pop('receipt_number'),
                    'received_date': batch_dict.pop('receipt_received_date'),
                    'description': batch_dict.pop('receipt_description', None),
                    'status': batch_dict.pop('receipt_status'),
                    'cdatetime': batch_dict.pop('receipt_cdatetime'),
                }
                # Convert receipt received_date to string if it's a date object
                if isinstance(receipt_dict['received_date'], date):
                    receipt_dict['received_date'] = receipt_dict['received_date'].isoformat()
                batch_dict['receipt'] = receipt_dict
            else:
                batch_dict['receipt'] = None
            
            batch_list.append(batch_dict)
        return batch_list

    @staticmethod
    def _get_batch_movements(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        batch_ids: List[str]
    ) -> dict:
        """Get movements for a list of batch IDs, returns dict mapping batch_id to list of movements"""
        if not batch_ids:
            return {}
        
        # Create placeholders for batch_ids
        placeholders = ','.join(['%s'] * len(batch_ids))
        
        cursor.execute(
            f"""SELECT pm.*,
                   creator.fullname as created_by
            FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pm.created_by = creator.id AND pm.tenant_id = creator.tenant_id
            WHERE pm.tenant_id = %s AND pm.org_id = %s AND pm.bus_id = %s
            AND pm.batch_id IN ({placeholders})
            ORDER BY pm.cdatetime DESC""",
            (tenant_id, org_id, bus_id, *batch_ids),
        )
        movements = cursor.fetchall()
        
        # Group movements by batch_id
        movements_by_batch = {}
        from datetime import date
        for movement in movements:
            movement_dict = dict(movement)
            batch_id = movement_dict.get('batch_id')
            if batch_id:
                if batch_id not in movements_by_batch:
                    movements_by_batch[batch_id] = []
                movements_by_batch[batch_id].append(movement_dict)
        
        return movements_by_batch

    @staticmethod
    def _convert_batches_to_dtos(batches_data: List[dict], movements_by_batch: Optional[dict] = None) -> List[PurchaseBatchReadDto]:
        """Convert batch dictionaries to PurchaseBatchReadDto objects, handling receipt and movement conversion"""
        batches_list = []
        movements_by_batch = movements_by_batch or {}
        
        for batch_dict in batches_data if batches_data else []:
            # Convert receipt dict to DTO if present
            if batch_dict.get('receipt'):
                batch_dict['receipt'] = PurchaseReceiptForBatchReadDto(**batch_dict['receipt'])
            
            # Attach movements for this batch
            batch_id = batch_dict.get('id')
            if batch_id and batch_id in movements_by_batch:
                movements_list = []
                for movement_dict in movements_by_batch[batch_id]:
                    movements_list.append(ProductMovementReadDto(**movement_dict))
                batch_dict['movements'] = movements_list if movements_list else None
            else:
                batch_dict['movements'] = None
            
            # Set new field names for batch quantities
            batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
            # For purchase orders: specific_product_per_batch_remaining_qty = qty_remaining_for_purchase_order (remaining to receive for PO)
            qty_remaining_for_po = batch_dict.get('qty_remaining_for_purchase_order')
            if qty_remaining_for_po is not None:
                batch_dict['specific_product_per_batch_remaining_qty'] = qty_remaining_for_po
            else:
                # Fallback for batches without qty_remaining_for_purchase_order (old data)
                qty_ordered = batch_dict.get('qty_ordered', 0)
                batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', qty_ordered)
            batches_list.append(PurchaseBatchReadDto(**batch_dict))
        return batches_list

    @staticmethod
    def create_purchase_order(
        data: CreatePurchaseOrderServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreatePurchaseOrderServiceReadDto]:
        """FLOW 1: Create Purchase Order - No batches, no movements"""
        try:
            with DatabaseManager.transaction() as cursor:
                po_number = PurchaseOrdersService._generate_po_number(
                    cursor, tenant_id, org_id, bus_id
                )
                
                logger.info(
                    f"Processing purchase order creation",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "po_number": po_number,
                            "created_by": created_by,
                        }
                    },
                )

                # Verify supplier exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_SUPPLIERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.supplier_id),
                )
                if not cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"Supplier {data.supplier_id} not found",
                        error="SUPPLIER_NOT_FOUND",
                    )

                # Verify assign_to user exists if provided
                if data.assign_to:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.assign_to),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"User {data.assign_to} not found",
                            error="USER_NOT_FOUND",
                        )

                # Generate purchase order ID
                po_id = Helper.generate_unique_identifier(prefix="po")

                # Set default status to DRAFT if not provided
                po_status = data.status if data.status else 'DRAFT'

                # Insert into msg_purchase_orders table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    (id, tenant_id, org_id, bus_id, supplier_id, po_number, assign_to, status,
                     order_date, expected_delivery_date, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        po_id, tenant_id, org_id, bus_id,
                        data.supplier_id,
                        po_number,
                        data.assign_to,
                        po_status,
                        data.order_date,
                        data.expected_delivery_date,
                        data.notes,
                        created_by
                    ),
                )
                po_result = cursor.fetchone()

                if not po_result:
                    raise ValueError("Failed to create purchase order")

                # Insert purchase order items if provided
                if data.items is not None and len(data.items) > 0:
                    product_ids_seen = set()
                    for item in data.items:
                        if item.product_id in product_ids_seen:
                            raise ValueError(f"Product {item.product_id} appears multiple times in the items array.")
                        product_ids_seen.add(item.product_id)
                    
                    for item in data.items:
                        # Verify product exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s AND delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, item.product_id),
                        )
                        if not cursor.fetchone():
                            raise ValueError(f"Product {item.product_id} not found")

                        # Verify currency exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                            WHERE tenant_id = %s AND id = %s""",
                            (tenant_id, item.currency_id),
                        )
                        if not cursor.fetchone():
                            raise ValueError(f"Currency {item.currency_id} not found")

                        # Verify unit of measure if provided
                        if getattr(item, 'unit_of_measure_id', None):
                            cursor.execute(
                                f"""SELECT id FROM {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE}
                                WHERE tenant_id = %s AND id = %s""",
                                (tenant_id, item.unit_of_measure_id),
                            )
                            if not cursor.fetchone():
                                raise ValueError(f"Unit of measure {item.unit_of_measure_id} not found")

                        item_id = Helper.generate_unique_identifier(prefix="poi")
                        qty_received = 0  # Always 0 for new PO
                        qty_remaining = item.qty_ordered  # Set explicitly
                        
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                            (id, tenant_id, org_id, bus_id, purchase_order_id, product_id,
                             qty_ordered, qty_received, qty_remaining, currency_id, cost_price, base_selling_price,
                             product_size, unit_of_measure_id, product_expiry_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                item_id, tenant_id, org_id, bus_id, po_id,
                                item.product_id, item.qty_ordered,
                                qty_received, qty_remaining,
                                item.currency_id, item.cost_price, item.base_selling_price,
                                getattr(item, 'product_size', None) or None,
                                getattr(item, 'unit_of_measure_id', None) or None,
                                getattr(item, 'product_expiry_date', None) or None,
                            ),
                        )

                # Get purchase order with user fullnames
                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE po.id = %s AND po.tenant_id = %s AND po.org_id = %s AND po.bus_id = %s""",
                    (po_id, tenant_id, org_id, bus_id),
                )
                po_with_users = cursor.fetchone()

                if po_with_users:
                    po_dict = dict(po_with_users)
                    po_dict['created_by'] = po_dict.get('created_by') or None
                    po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                    po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None
                else:
                    po_dict = dict(po_result)
                    po_dict['created_by'] = None
                    po_dict['supplier_name'] = None
                    po_dict['assign_to_name'] = None

                # Get items
                items_data = PurchaseOrdersService._get_purchase_order_items(
                    cursor, tenant_id, org_id, bus_id, po_id
                )

                # Get batches (should be empty for new PO)
                batches_data = PurchaseOrdersService._get_purchase_order_batches(
                    cursor, tenant_id, org_id, bus_id, po_id
                )
                # Get movements for batches
                batch_ids = [batch.get('id') for batch in batches_data if batch.get('id')]
                movements_by_batch = PurchaseOrdersService._get_batch_movements(
                    cursor, tenant_id, org_id, bus_id, batch_ids
                ) if batch_ids else {}
                batches_list = PurchaseOrdersService._convert_batches_to_dtos(batches_data, movements_by_batch)

                # Group batches by product_id
                batches_by_product = {}
                for batch in batches_list:
                    product_id = batch.product_id
                    if product_id not in batches_by_product:
                        batches_by_product[product_id] = []
                    batches_by_product[product_id].append(batch)

                # Attach batches to items and construct currency object
                items_list = []
                for item in items_data:
                    item_dict = dict(item)
                    product_id = item_dict.get('product_id')
                    item_dict['batches'] = batches_by_product.get(product_id, None)
                    currency_id = item_dict.get('currency_id')
                    if currency_id:
                        currency_dict = {
                            'id': currency_id,
                            'name': item_dict.pop('currency_name', None),
                            'code': item_dict.pop('currency_code', None),
                            'symbol': item_dict.pop('currency_symbol', None),
                            'decimal_places': item_dict.pop('currency_decimal_places', None),
                            'currency_position': item_dict.pop('currency_position', None),
                        }
                        item_dict['currency'] = CurrencyReadDto(**currency_dict)
                    else:
                        item_dict['currency'] = None
                    items_list.append(PurchaseOrderItemReadDto(**item_dict))

                po_read = CreatePurchaseOrderServiceReadDto(
                    purchase_order=PurchaseOrderReadBase(**po_dict),
                    items=items_list
                )

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (po_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else po_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-orders",
                        resource_id=po_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Purchase order {po_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Purchase order created successfully: {po_id}",
                    extra={
                        "extra_fields": {
                            "po_id": po_id,
                            "po_number": po_number,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Purchase order created successfully",
                    data=[po_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating purchase order: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def receive_purchase_order(
        data: ReceivePurchaseOrderServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[ReceivePurchaseOrderServiceReadDto]:
        """FLOW 2: Receive Purchase Order - Create receipt, batches, update PO items, insert movements, update PO status"""
        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                logger.info(
                    f"Processing purchase order receipt",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "purchase_order_id": data.purchase_order_id,
                            "created_by": created_by,
                        }
                    },
                )

                # Step 1: Verify purchase order exists and get supplier_id
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                po = cursor.fetchone()
                if not po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )

                po_dict = dict(po)
                supplier_id = po_dict.get('supplier_id')

                # Pre-validate: aggregate received_qty by purchase_order_item_id (before creating receipt)
                qty_per_po_item = defaultdict(int)
                for receipt_item in data.items:
                    qty_per_po_item[receipt_item.purchase_order_item_id] += receipt_item.received_qty

                already_fully_received_all = True  # idempotent: all lines already at 0 remaining
                for po_item_id, total_in_receipt in qty_per_po_item.items():
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND purchase_order_id = %s""",
                        (po_item_id, tenant_id, org_id, bus_id, data.purchase_order_id),
                    )
                    poi = cursor.fetchone()
                    if not poi:
                        raise ValueError(f"Purchase order item {po_item_id} not found")
                    poi_dict = dict(poi)
                    qty_ordered = poi_dict.get('qty_ordered', 0)
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(pb.qty_received), 0) as total_received
                        FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        INNER JOIN {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm 
                            ON pb.id = pm.batch_id AND pb.tenant_id = pm.tenant_id 
                            AND pb.org_id = pm.org_id AND pb.bus_id = pm.bus_id
                        INNER JOIN {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr 
                            ON pm.reference_id = pr.id AND pm.tenant_id = pr.tenant_id 
                            AND pm.org_id = pr.org_id AND pm.bus_id = pr.bus_id
                        WHERE pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s 
                        AND pb.product_id = %s AND pb.delete_status = 'NOT_DELETED'
                        AND pb.batch_type = 'PURCHASE' AND pr.purchase_order_id = %s
                        AND pm.movement_type = 'IN' AND pm.reason = 'PURCHASE'""",
                        (tenant_id, org_id, bus_id, poi_dict.get('product_id'), data.purchase_order_id),
                    )
                    total_received_result = cursor.fetchone()
                    total_received_so_far = float(total_received_result.get('total_received', 0) or 0) if total_received_result else 0
                    current_qty_remaining = qty_ordered - total_received_so_far
                    if total_in_receipt > current_qty_remaining:
                        if current_qty_remaining > 0:
                            raise ValueError(
                                f"Received quantity ({total_in_receipt}) exceeds remaining quantity ({current_qty_remaining}) for purchase order item {po_item_id}. "
                                f"Ordered: {qty_ordered}, Already received: {total_received_so_far}, Remaining: {current_qty_remaining}."
                            )
                        # remaining is 0: this line is already fully received (duplicate receive)
                        already_fully_received_all = already_fully_received_all and True
                    else:
                        already_fully_received_all = False

                # Idempotent: all lines already fully received — return success without creating a new receipt
                if already_fully_received_all and qty_per_po_item:
                    po_dict.setdefault('created_by', None)
                    po_dict.setdefault('supplier_name', None)
                    po_dict.setdefault('assign_to_name', None)
                    cursor.execute(
                        f"""SELECT po.*, creator.fullname as created_by,
                                   supplier.fullname as supplier_name, assignee.fullname as assign_to_name
                            FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                            LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id
                                AND po.tenant_id = supplier.tenant_id AND po.org_id = supplier.org_id AND po.bus_id = supplier.bus_id
                            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                            WHERE po.id = %s AND po.tenant_id = %s AND po.org_id = %s AND po.bus_id = %s""",
                        (data.purchase_order_id, tenant_id, org_id, bus_id),
                    )
                    po_with_users = cursor.fetchone()
                    if po_with_users:
                        po_dict = dict(po_with_users)
                        po_dict['created_by'] = po_dict.get('created_by') or None
                        po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                        po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None
                    items_data = PurchaseOrdersService._get_purchase_order_items(
                        cursor, tenant_id, org_id, bus_id, data.purchase_order_id
                    )
                    batches_data = PurchaseOrdersService._get_purchase_order_batches(
                        cursor, tenant_id, org_id, bus_id, data.purchase_order_id
                    )
                    batch_ids = [b.get('id') for b in batches_data if b.get('id')]
                    movements_by_batch = PurchaseOrdersService._get_batch_movements(
                        cursor, tenant_id, org_id, bus_id, batch_ids
                    ) if batch_ids else {}
                    batches_list = PurchaseOrdersService._convert_batches_to_dtos(batches_data, movements_by_batch)
                    batches_by_product = {}
                    for batch in batches_list:
                        pid = batch.product_id
                        if pid not in batches_by_product:
                            batches_by_product[pid] = []
                        batches_by_product[pid].append(batch)
                    items_list = []
                    for item in items_data:
                        item_dict = dict(item)
                        item_dict['batches'] = batches_by_product.get(item_dict.get('product_id'), None)
                        cid = item_dict.get('currency_id')
                        if cid:
                            item_dict['currency'] = CurrencyReadDto(
                                id=cid,
                                name=item_dict.pop('currency_name', None),
                                code=item_dict.pop('currency_code', None),
                                symbol=item_dict.pop('currency_symbol', None),
                                decimal_places=item_dict.pop('currency_decimal_places', None),
                                currency_position=item_dict.pop('currency_position', None),
                            )
                        else:
                            item_dict['currency'] = None
                        items_list.append(PurchaseOrderItemReadDto(**item_dict))
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND purchase_order_id = %s
                        ORDER BY cdatetime DESC NULLS LAST LIMIT 1""",
                        (tenant_id, org_id, bus_id, data.purchase_order_id),
                    )
                    latest_receipt = cursor.fetchone()
                    if latest_receipt:
                        r = dict(latest_receipt)
                        receipt_read = PurchaseReceiptReadBase(
                            id=r.get('id'), tenant_id=r.get('tenant_id'), org_id=r.get('org_id'), bus_id=r.get('bus_id'),
                            purchase_order_id=r.get('purchase_order_id'), receipt_number=r.get('receipt_number'),
                            received_date=r.get('received_date'), description=r.get('description'), status=r.get('status'),
                            cdatetime=r.get('cdatetime'), created_by=r.get('created_by'),
                        )
                    else:
                        receipt_read = None
                    po_read = ReceivePurchaseOrderServiceReadDto(
                        purchase_order=PurchaseOrderReadBase(**po_dict),
                        items=items_list,
                        receipt=receipt_read,
                    )
                    return Respons(
                        success=True,
                        detail="Already fully received; no new receipt created.",
                        data=[po_read],
                    )

                # Step 2: Create Receipt
                receipt_id = Helper.generate_unique_identifier(prefix="rec")
                receipt_number = PurchaseOrdersService._generate_receipt_number(
                    cursor, tenant_id, org_id, bus_id
                )
                receipt_status = getattr(data, 'status', 'DRAFT')
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                    (id, tenant_id, org_id, bus_id, purchase_order_id, receipt_number,
                     received_date, description, status, created_by, cdate, ctime, cdatetime)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        receipt_id, tenant_id, org_id, bus_id, data.purchase_order_id,
                        receipt_number, data.received_date, data.description, receipt_status,
                        created_by, cdate, ctime, cdatetime
                    ),
                )
                receipt_result = cursor.fetchone()

                # Step 3: Process each received item
                for receipt_item in data.items:
                    # Get the purchase order item
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND purchase_order_id = %s""",
                        (receipt_item.purchase_order_item_id, tenant_id, org_id, bus_id, data.purchase_order_id),
                    )
                    poi = cursor.fetchone()
                    if not poi:
                        raise ValueError(f"Purchase order item {receipt_item.purchase_order_item_id} not found")
                    
                    poi_dict = dict(poi)
                    qty_ordered = poi_dict.get('qty_ordered', 0)
                    received_qty = receipt_item.received_qty
                    
                    # Get sum of all qty_received from all batches for this PO item
                    # Sum from batches that are linked to receipts for this purchase order
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(pb.qty_received), 0) as total_received
                        FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        INNER JOIN {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm 
                            ON pb.id = pm.batch_id 
                            AND pb.tenant_id = pm.tenant_id 
                            AND pb.org_id = pm.org_id 
                            AND pb.bus_id = pm.bus_id
                        INNER JOIN {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr 
                            ON pm.reference_id = pr.id 
                            AND pm.tenant_id = pr.tenant_id 
                            AND pm.org_id = pr.org_id 
                            AND pm.bus_id = pr.bus_id
                        WHERE pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s 
                        AND pb.product_id = %s 
                        AND pb.delete_status = 'NOT_DELETED'
                        AND pb.batch_type = 'PURCHASE'
                        AND pr.purchase_order_id = %s
                        AND pm.movement_type = 'IN'
                        AND pm.reason = 'PURCHASE'""",
                        (tenant_id, org_id, bus_id, poi_dict.get('product_id'), data.purchase_order_id),
                    )
                    total_received_result = cursor.fetchone()
                    total_received_so_far = float(total_received_result.get('total_received', 0) or 0) if total_received_result else 0
                    
                    # Calculate remaining quantity: qty_ordered - sum of all qty_received (including this receipt)
                    total_received_after_this = total_received_so_far + received_qty
                    current_qty_remaining = qty_ordered - total_received_so_far
                    
                    # Skip already-fully-received lines (idempotent: no batch, no update)
                    if received_qty > current_qty_remaining and current_qty_remaining == 0:
                        continue
                    # Reject over-receive when there is remaining (invalid)
                    if received_qty > current_qty_remaining:
                        raise ValueError(
                            f"Received quantity ({received_qty}) exceeds remaining quantity ({current_qty_remaining}). "
                            f"Ordered: {qty_ordered}, Already received: {total_received_so_far}, Remaining: {current_qty_remaining}."
                        )

                    # Step 4: Create Batch
                    # Batch number is always auto-generated by the system
                    batch_number = PurchaseOrdersService._generate_batch_number(
                        cursor, tenant_id, org_id, bus_id
                    )
                    
                    # Verify batch number doesn't exist
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND batch_number = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, batch_number),
                    )
                    if cursor.fetchone():
                        raise ValueError(f"Batch with number '{batch_number}' already exists")

                    # Default batch product_size, unit_of_measure_id, product_expiry_date from PO item when not provided in receipt
                    batch_product_size = receipt_item.product_size if receipt_item.product_size is not None else poi_dict.get('product_size')
                    batch_unit_of_measure_id = receipt_item.unit_of_measure_id if receipt_item.unit_of_measure_id is not None else poi_dict.get('unit_of_measure_id')
                    batch_product_expiry_date = receipt_item.product_expiry_date if receipt_item.product_expiry_date is not None else poi_dict.get('product_expiry_date')

                    # Verify unit of measure if provided (from receipt or PO item)
                    if batch_unit_of_measure_id:
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE}
                            WHERE tenant_id = %s AND id = %s""",
                            (tenant_id, batch_unit_of_measure_id),
                        )
                        if not cursor.fetchone():
                            raise ValueError(f"Unit of measure {batch_unit_of_measure_id} not found")

                    batch_id = Helper.generate_unique_identifier(prefix="bat")
                    batch_status = 'RECEIVED'  # Status for received batches
                    # qty_remaining_for_purchase_order: remaining quantity for the purchase order after this receipt
                    qty_remaining_for_purchase_order = qty_ordered - total_received_after_this
                    # qty_remaining: actual stock remaining in this batch (starts with received_qty, decreases with sales)
                    batch_qty_remaining = received_qty
                    
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, supplier_id, batch_number,
                         currency_id, cost_price, base_selling_price, product_size, unit_of_measure_id,
                         product_expiry_date, batch_type, qty_ordered, qty_received, qty_remaining, qty_remaining_for_purchase_order,
                         status, delete_status, is_active, cdate, ctime, cdatetime, created_by, updated_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            batch_id, tenant_id, org_id, bus_id, poi_dict.get('product_id'),
                            supplier_id, batch_number,
                            poi_dict.get('currency_id'), poi_dict.get('cost_price'), poi_dict.get('base_selling_price'),
                            batch_product_size, batch_unit_of_measure_id,
                            batch_product_expiry_date,
                            'PURCHASE',  # Batch type for stock from supplier
                            qty_ordered,  # qty_ordered is required for PURCHASE batches
                            received_qty, batch_qty_remaining, qty_remaining_for_purchase_order,  # qty_remaining = actual stock, qty_remaining_for_purchase_order = PO remaining
                            batch_status,
                            'NOT_DELETED', True,
                            cdate, ctime, cdatetime, created_by, created_by
                        ),
                    )

                    # Step 5: Update PO Item qty_received and qty_remaining
                    # Calculate: qty_remaining = qty_remaining_for_purchase_order (remaining to receive for PO)
                    new_qty_received = total_received_after_this
                    new_qty_remaining = qty_remaining_for_purchase_order
                    
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                        SET qty_received = %s, qty_remaining = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (new_qty_received, new_qty_remaining, receipt_item.purchase_order_item_id,
                         tenant_id, org_id, bus_id),
                    )

                    # Step 6: Insert Product Movement
                    movement_id = Helper.generate_unique_identifier(prefix="mov")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                         movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            movement_id, tenant_id, org_id, bus_id, poi_dict.get('product_id'),
                            batch_id, None, None,  # location_type and location_id are NULL for purchase
                            'IN', received_qty, 'PURCHASE', receipt_id,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    movement_result = cursor.fetchone()
                    if not movement_result:
                        raise ValueError(f"Failed to create movement for batch {batch_id}")
                    
                    logger.info(
                        f"Movement created successfully for batch: batch_id={batch_id}, movement_id={movement_id}, qty={received_qty}",
                        extra={
                            "extra_fields": {
                                "batch_id": batch_id,
                                "batch_number": batch_number,
                                "movement_id": movement_id,
                                "product_id": poi_dict.get('product_id'),
                                "qty": received_qty,
                                "receipt_id": receipt_id,
                                "purchase_order_id": data.purchase_order_id,
                            }
                        },
                    )

                # Step 7: Update PO Status automatically based on received quantities
                # Don't update status if PO is CANCELLED
                current_status = po_dict.get('status', 'DRAFT')
                if current_status == 'CANCELLED':
                    new_status = 'CANCELLED'  # Preserve CANCELLED status
                else:
                    # Check if all items are fully received
                    cursor.execute(
                        f"""SELECT COUNT(*) as total,
                               SUM(CASE WHEN qty_received >= qty_ordered THEN 1 ELSE 0 END) as fully_received
                        FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                        WHERE purchase_order_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (data.purchase_order_id, tenant_id, org_id, bus_id),
                    )
                    status_check = cursor.fetchone()
                    total_items = status_check.get('total', 0) if status_check else 0
                    fully_received = status_check.get('fully_received', 0) if status_check else 0

                    if total_items > 0 and fully_received == total_items:
                        # All items fully received -> COMPLETED
                        new_status = 'COMPLETED'
                    else:
                        # Check if any items have been received (partially or fully)
                        cursor.execute(
                            f"""SELECT COUNT(*) as received_count
                            FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                            WHERE purchase_order_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                            AND qty_received > 0""",
                            (data.purchase_order_id, tenant_id, org_id, bus_id),
                        )
                        received_check = cursor.fetchone()
                        received_count = received_check.get('received_count', 0) if received_check else 0
                        
                        if received_count > 0:
                            # Some items received but not all -> PARTIALLY_RECEIVED
                            new_status = 'PARTIALLY_RECEIVED'
                        else:
                            # No items received yet -> keep current status (DRAFT or APPROVED)
                            new_status = current_status

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    SET status = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (new_status, data.purchase_order_id, tenant_id, org_id, bus_id),
                )

                # Get updated purchase order with items
                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE po.id = %s AND po.tenant_id = %s AND po.org_id = %s AND po.bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                po_with_users = cursor.fetchone()

                if po_with_users:
                    po_dict = dict(po_with_users)
                    po_dict['created_by'] = po_dict.get('created_by') or None
                    po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                    po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None

                # Get items
                items_data = PurchaseOrdersService._get_purchase_order_items(
                    cursor, tenant_id, org_id, bus_id, data.purchase_order_id
                )

                # Get batches
                batches_data = PurchaseOrdersService._get_purchase_order_batches(
                    cursor, tenant_id, org_id, bus_id, data.purchase_order_id
                )
                # Get movements for batches
                batch_ids = [batch.get('id') for batch in batches_data if batch.get('id')]
                movements_by_batch = PurchaseOrdersService._get_batch_movements(
                    cursor, tenant_id, org_id, bus_id, batch_ids
                ) if batch_ids else {}
                batches_list = PurchaseOrdersService._convert_batches_to_dtos(batches_data, movements_by_batch)

                # Group batches by product_id
                batches_by_product = {}
                for batch in batches_list:
                    product_id = batch.product_id
                    if product_id not in batches_by_product:
                        batches_by_product[product_id] = []
                    batches_by_product[product_id].append(batch)

                # Attach batches to items and construct currency object
                items_list = []
                for item in items_data:
                    item_dict = dict(item)
                    product_id = item_dict.get('product_id')
                    item_dict['batches'] = batches_by_product.get(product_id, None)
                    currency_id = item_dict.get('currency_id')
                    if currency_id:
                        currency_dict = {
                            'id': currency_id,
                            'name': item_dict.pop('currency_name', None),
                            'code': item_dict.pop('currency_code', None),
                            'symbol': item_dict.pop('currency_symbol', None),
                            'decimal_places': item_dict.pop('currency_decimal_places', None),
                            'currency_position': item_dict.pop('currency_position', None),
                        }
                        item_dict['currency'] = CurrencyReadDto(**currency_dict)
                    else:
                        item_dict['currency'] = None
                    items_list.append(PurchaseOrderItemReadDto(**item_dict))

                # Create receipt read DTO
                receipt_dict = dict(receipt_result) if receipt_result else {}
                receipt_read = PurchaseReceiptReadBase(
                    id=receipt_dict.get('id', receipt_id),
                    tenant_id=receipt_dict.get('tenant_id', tenant_id),
                    org_id=receipt_dict.get('org_id', org_id),
                    bus_id=receipt_dict.get('bus_id', bus_id),
                    purchase_order_id=receipt_dict.get('purchase_order_id', data.purchase_order_id),
                    receipt_number=receipt_dict.get('receipt_number', receipt_number),
                    received_date=receipt_dict.get('received_date', data.received_date),
                    description=receipt_dict.get('description', data.description),
                    status=receipt_dict.get('status', receipt_status),
                    cdatetime=receipt_dict.get('cdatetime', cdatetime),
                    created_by=receipt_dict.get('created_by', created_by),
                )

                po_read = ReceivePurchaseOrderServiceReadDto(
                    purchase_order=PurchaseOrderReadBase(**po_dict),
                    items=items_list,
                    receipt=receipt_read
                )

                logger.info(
                    f"Purchase order received successfully: {data.purchase_order_id}",
                    extra={
                        "extra_fields": {
                            "purchase_order_id": data.purchase_order_id,
                            "receipt_id": receipt_id,
                            "receipt_number": receipt_number,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Purchase order received successfully",
                    data=[po_read],
                )

        except ValueError as e:
            logger.error(f"Validation error receiving purchase order: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error receiving purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to receive purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def receive_purchase_orders(
        orders: List[ReceivePurchaseOrderServiceWriteDto],
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[List[ReceivePurchaseOrderServiceReadDto]]:
        """Receive multiple purchase orders. Processes in order; returns first error if any fail."""
        if not orders:
            return Respons(
                success=False,
                detail="At least one purchase order is required",
                error="VALIDATION_ERROR",
            )
        results: List[ReceivePurchaseOrderServiceReadDto] = []
        for data in orders:
            result = PurchaseOrdersService.receive_purchase_order(
                data=data,
                tenant_id=tenant_id,
                org_id=org_id,
                bus_id=bus_id,
                created_by=created_by,
            )
            if not result.success:
                return result
            if result.data and len(result.data) > 0:
                results.append(result.data[0])
        return Respons(
            success=True,
            detail=f"Received {len(results)} purchase order(s) successfully",
            data=results,
        )

    @staticmethod
    def update_purchase_order(
        data: UpdatePurchaseOrderServiceWriteDto,
        purchase_order_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdatePurchaseOrderServiceReadDto]:
        """Update a purchase order with optional items (qty_received cannot be updated directly)"""
        logger.info(
            f"Processing purchase order update: {purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (purchase_order_id, tenant_id, org_id, bus_id),
                )
                existing_po = cursor.fetchone()

                if not existing_po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )
                
                old_data = dict(existing_po)

                # Verify supplier if being updated
                if data.supplier_id is not None:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.supplier_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Supplier {data.supplier_id} not found",
                            error="SUPPLIER_NOT_FOUND",
                        )

                # Verify assign_to user if being updated
                if data.assign_to is not None:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.assign_to),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"User {data.assign_to} not found",
                            error="USER_NOT_FOUND",
                        )

                # Build update query dynamically
                update_fields = []
                params = []

                if data.supplier_id is not None:
                    update_fields.append("supplier_id = %s")
                    params.append(data.supplier_id)
                if data.assign_to is not None:
                    update_fields.append("assign_to = %s")
                    params.append(data.assign_to)
                if data.status is not None:
                    update_fields.append("status = %s")
                    params.append(data.status)
                if data.order_date is not None:
                    update_fields.append("order_date = %s")
                    params.append(data.order_date)
                if data.expected_delivery_date is not None:
                    update_fields.append("expected_delivery_date = %s")
                    params.append(data.expected_delivery_date)
                if data.notes is not None:
                    update_fields.append("notes = %s")
                    params.append(data.notes)

                if update_fields:
                    params.extend([purchase_order_id, tenant_id, org_id, bus_id])
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        params,
                    )

                # Handle items if provided (qty_received cannot be updated here)
                if data.items is not None and len(data.items) > 0:
                    # Split items into two lists:
                    # 1. Items with item_id (existing items to update)
                    # 2. Items without item_id (new items to insert)
                    items_to_update = []
                    items_to_insert = []
                    
                    for item in data.items:
                        item_id = getattr(item, 'item_id', None)
                        if item_id and item_id.strip():
                            items_to_update.append(item)
                        else:
                            items_to_insert.append(item)
                    
                    # Step 1: Process items with item_id (update existing items)
                    for item in items_to_update:
                        item_id = getattr(item, 'item_id', None)
                        
                        # Get existing item
                        cursor.execute(
                            f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s 
                            AND bus_id = %s AND purchase_order_id = %s""",
                            (item_id, tenant_id, org_id, bus_id, purchase_order_id),
                        )
                        existing_item = cursor.fetchone()
                        
                        if not existing_item:
                            logger.warning(f"Item {item_id} not found, skipping")
                            continue
                        
                        existing_item_dict = dict(existing_item)
                        item_update_fields = []
                        item_params = []
                        
                        # Validate and update product_id if provided and different
                        if item.product_id is not None:
                            existing_product_id = existing_item_dict.get('product_id')
                            
                            if item.product_id != existing_product_id:
                                # Validate the new product exists
                                cursor.execute(
                                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                    AND id = %s AND delete_status = 'NOT_DELETED'""",
                                    (tenant_id, org_id, bus_id, item.product_id),
                                )
                                if not cursor.fetchone():
                                    raise ValueError(f"Product {item.product_id} not found")
                                
                                # Check if the new product_id already exists in another item
                                cursor.execute(
                                    f"""SELECT id FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                    AND purchase_order_id = %s AND product_id = %s 
                                    AND id != %s""",
                                    (tenant_id, org_id, bus_id, purchase_order_id, item.product_id, item_id),
                                )
                                if cursor.fetchone():
                                    raise ValueError(f"Product {item.product_id} already exists in this purchase order")
                                
                                item_update_fields.append("product_id = %s")
                                item_params.append(item.product_id)
                        
                        # Update qty_ordered if provided
                        if item.qty_ordered is not None:
                            existing_qty_received = existing_item_dict.get('qty_received', 0)
                            # Get the latest qty_remaining_for_purchase_order from batches for this PO item
                            cursor.execute(
                                f"""SELECT pb.qty_remaining_for_purchase_order
                                FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                                INNER JOIN {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm 
                                    ON pb.id = pm.batch_id 
                                    AND pb.tenant_id = pm.tenant_id 
                                    AND pb.org_id = pm.org_id 
                                    AND pb.bus_id = pm.bus_id
                                INNER JOIN {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr 
                                    ON pm.reference_id = pr.id 
                                    AND pm.tenant_id = pr.tenant_id 
                                    AND pm.org_id = pr.org_id 
                                    AND pm.bus_id = pr.bus_id
                                WHERE pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s 
                                AND pb.product_id = %s 
                                AND pb.delete_status = 'NOT_DELETED'
                                AND pb.batch_type = 'PURCHASE'
                                AND pr.purchase_order_id = %s
                                AND pm.movement_type = 'IN'
                                AND pm.reason = 'PURCHASE'
                                ORDER BY pb.cdatetime DESC
                                LIMIT 1""",
                                (tenant_id, org_id, bus_id, existing_item_dict.get('product_id'), purchase_order_id),
                            )
                            latest_remaining_result = cursor.fetchone()
                            latest_remaining_for_po = float(latest_remaining_result.get('qty_remaining_for_purchase_order', 0) or 0) if latest_remaining_result and latest_remaining_result.get('qty_remaining_for_purchase_order') is not None else None
                            
                            # Calculate: qty_remaining = qty_remaining_for_purchase_order (from latest batch, remaining to receive)
                            # If no batches yet, use qty_ordered - existing_qty_received
                            if latest_remaining_for_po is not None:
                                new_qty_remaining = latest_remaining_for_po
                            else:
                                new_qty_remaining = item.qty_ordered - existing_qty_received
                            
                            if new_qty_remaining < 0:
                                raise ValueError(f"qty_ordered ({item.qty_ordered}) cannot be less than qty_received ({existing_qty_received})")
                            item_update_fields.append("qty_ordered = %s")
                            item_params.append(item.qty_ordered)
                            item_update_fields.append("qty_remaining = %s")
                            item_params.append(new_qty_remaining)
                        
                        # Update currency_id if provided
                        if item.currency_id is not None:
                            cursor.execute(
                                f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                                WHERE tenant_id = %s AND id = %s""",
                                (tenant_id, item.currency_id),
                            )
                            if not cursor.fetchone():
                                raise ValueError(f"Currency {item.currency_id} not found")
                            item_update_fields.append("currency_id = %s")
                            item_params.append(item.currency_id)
                        
                        # Update cost_price if provided
                        if item.cost_price is not None:
                            item_update_fields.append("cost_price = %s")
                            item_params.append(item.cost_price)
                        
                        # Update base_selling_price if provided
                        if item.base_selling_price is not None:
                            item_update_fields.append("base_selling_price = %s")
                            item_params.append(item.base_selling_price)
                        
                        # Update product_size if provided
                        if item.product_size is not None:
                            item_update_fields.append("product_size = %s")
                            item_params.append(item.product_size)
                        
                        # Update unit_of_measure_id if provided (validate first)
                        if item.unit_of_measure_id is not None:
                            cursor.execute(
                                f"""SELECT id FROM {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE}
                                WHERE tenant_id = %s AND id = %s""",
                                (tenant_id, item.unit_of_measure_id),
                            )
                            if not cursor.fetchone():
                                raise ValueError(f"Unit of measure {item.unit_of_measure_id} not found")
                            item_update_fields.append("unit_of_measure_id = %s")
                            item_params.append(item.unit_of_measure_id)
                        
                        # Update product_expiry_date if provided
                        if item.product_expiry_date is not None:
                            item_update_fields.append("product_expiry_date = %s")
                            item_params.append(item.product_expiry_date)
                        
                        # Execute update if there are fields to update
                        if item_update_fields:
                            item_params.extend([item_id, tenant_id, org_id, bus_id, purchase_order_id])
                            cursor.execute(
                                f"""UPDATE {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                                SET {', '.join(item_update_fields)}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s 
                                AND bus_id = %s AND purchase_order_id = %s""",
                                item_params,
                            )
                    
                    # Step 2: Process items without item_id (insert new items)
                    for item in items_to_insert:
                        if not item.product_id:
                            raise ValueError("New items must have a product_id")
                        
                        # Validate product exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s AND delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, item.product_id),
                        )
                        if not cursor.fetchone():
                            raise ValueError(f"Product {item.product_id} not found")
                        
                        # Validate currency if provided
                        if item.currency_id:
                            cursor.execute(
                                f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                                WHERE tenant_id = %s AND id = %s""",
                                (tenant_id, item.currency_id),
                            )
                            if not cursor.fetchone():
                                raise ValueError(f"Currency {item.currency_id} not found")
                        
                        # Check if product already exists in purchase order
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND purchase_order_id = %s AND product_id = %s""",
                            (tenant_id, org_id, bus_id, purchase_order_id, item.product_id),
                        )
                        if cursor.fetchone():
                            raise ValueError(f"Product {item.product_id} already exists in this purchase order")
                        
                        # Validate unit of measure if provided (for new item)
                        if getattr(item, 'unit_of_measure_id', None):
                            cursor.execute(
                                f"""SELECT id FROM {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE}
                                WHERE tenant_id = %s AND id = %s""",
                                (tenant_id, item.unit_of_measure_id),
                            )
                            if not cursor.fetchone():
                                raise ValueError(f"Unit of measure {item.unit_of_measure_id} not found")
                        
                        # Insert new item
                        item_id = Helper.generate_unique_identifier(prefix="poi")
                        qty_received = 0
                        qty_remaining = item.qty_ordered
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                            (id, tenant_id, org_id, bus_id, purchase_order_id, product_id,
                             qty_ordered, qty_received, qty_remaining, currency_id, cost_price, base_selling_price,
                             product_size, unit_of_measure_id, product_expiry_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                item_id, tenant_id, org_id, bus_id, purchase_order_id,
                                item.product_id, item.qty_ordered,
                                qty_received, qty_remaining,
                                item.currency_id, item.cost_price, item.base_selling_price,
                                getattr(item, 'product_size', None) or None,
                                getattr(item, 'unit_of_measure_id', None) or None,
                                getattr(item, 'product_expiry_date', None) or None,
                            ),
                        )

                # Get updated purchase order
                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE po.id = %s AND po.tenant_id = %s AND po.org_id = %s AND po.bus_id = %s""",
                    (purchase_order_id, tenant_id, org_id, bus_id),
                )
                po_with_users = cursor.fetchone()

                if po_with_users:
                    po_dict = dict(po_with_users)
                    po_dict['created_by'] = po_dict.get('created_by') or None
                    po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                    po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None
                else:
                    po_dict = dict(existing_po)
                    po_dict['created_by'] = None
                    po_dict['supplier_name'] = None
                    po_dict['assign_to_name'] = None

                # Get items and batches
                items_data = PurchaseOrdersService._get_purchase_order_items(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                batches_data = PurchaseOrdersService._get_purchase_order_batches(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                batches_list = PurchaseOrdersService._convert_batches_to_dtos(batches_data)

                batches_by_product = {}
                for batch in batches_list:
                    product_id = batch.product_id
                    if product_id not in batches_by_product:
                        batches_by_product[product_id] = []
                    batches_by_product[product_id].append(batch)

                items_list = []
                for item in items_data:
                    item_dict = dict(item)
                    product_id = item_dict.get('product_id')
                    item_dict['batches'] = batches_by_product.get(product_id, None)
                    currency_id = item_dict.get('currency_id')
                    if currency_id:
                        currency_dict = {
                            'id': currency_id,
                            'name': item_dict.pop('currency_name', None),
                            'code': item_dict.pop('currency_code', None),
                            'symbol': item_dict.pop('currency_symbol', None),
                            'decimal_places': item_dict.pop('currency_decimal_places', None),
                            'currency_position': item_dict.pop('currency_position', None),
                        }
                        item_dict['currency'] = CurrencyReadDto(**currency_dict)
                    else:
                        item_dict['currency'] = None
                    items_list.append(PurchaseOrderItemReadDto(**item_dict))

                po_read = UpdatePurchaseOrderServiceReadDto(
                    purchase_order=PurchaseOrderReadBase(**po_dict),
                    items=items_list
                )

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (purchase_order_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else po_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-orders",
                        resource_id=purchase_order_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Purchase order {purchase_order_id} updated successfully",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(
                    success=True,
                    detail="Purchase order updated successfully",
                    data=[po_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating purchase order: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_purchase_order(
        purchase_order_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPurchaseOrderServiceReadDto]:
        """Get a single purchase order by ID"""
        logger.info(
            f"Processing get purchase order request: {purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE po.id = %s AND po.tenant_id = %s AND po.org_id = %s AND po.bus_id = %s""",
                    (purchase_order_id, tenant_id, org_id, bus_id),
                )
                po = cursor.fetchone()

                if not po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )

                po_dict = dict(po)
                po_dict['created_by'] = po_dict.get('created_by') or None
                po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None

                items_data = PurchaseOrdersService._get_purchase_order_items(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                batches_data = PurchaseOrdersService._get_purchase_order_batches(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                # Get movements for batches
                batch_ids = [batch.get('id') for batch in batches_data if batch.get('id')]
                movements_by_batch = PurchaseOrdersService._get_batch_movements(
                    cursor, tenant_id, org_id, bus_id, batch_ids
                ) if batch_ids else {}
                batches_list = PurchaseOrdersService._convert_batches_to_dtos(batches_data, movements_by_batch)

                batches_by_product = {}
                for batch in batches_list:
                    product_id = batch.product_id
                    if product_id not in batches_by_product:
                        batches_by_product[product_id] = []
                    batches_by_product[product_id].append(batch)

                items_list = []
                for item in items_data:
                    item_dict = dict(item)
                    product_id = item_dict.get('product_id')
                    item_dict['batches'] = batches_by_product.get(product_id, None)
                    currency_id = item_dict.get('currency_id')
                    if currency_id:
                        currency_dict = {
                            'id': currency_id,
                            'name': item_dict.pop('currency_name', None),
                            'code': item_dict.pop('currency_code', None),
                            'symbol': item_dict.pop('currency_symbol', None),
                            'decimal_places': item_dict.pop('currency_decimal_places', None),
                            'currency_position': item_dict.pop('currency_position', None),
                        }
                        item_dict['currency'] = CurrencyReadDto(**currency_dict)
                    else:
                        item_dict['currency'] = None
                    items_list.append(PurchaseOrderItemReadDto(**item_dict))

                po_read = GetPurchaseOrderServiceReadDto(
                    purchase_order=PurchaseOrderReadBase(**po_dict),
                    items=items_list
                )

                return Respons(
                    success=True,
                    detail="Purchase order retrieved successfully",
                    data=[po_read],
                )

        except Exception as e:
            logger.error(f"Error getting purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_purchase_orders(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        status: Optional[str] = None,
        supplier_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetPurchaseOrdersServiceReadDto]]:
        """Get list of purchase orders with pagination"""
        logger.info(
            f"Processing get purchase orders request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "status": status,
                    "supplier_id": supplier_id,
                    "search": search,
                    "page": page,
                    "size": size,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                where_conditions = [
                    "po.tenant_id = %s",
                    "po.org_id = %s",
                    "po.bus_id = %s"
                ]
                params = [tenant_id, org_id, bus_id]

                if status:
                    where_conditions.append("po.status = %s")
                    params.append(status)

                if supplier_id:
                    where_conditions.append("po.supplier_id = %s")
                    params.append(supplier_id)

                if search:
                    where_conditions.append(
                        "(po.po_number ILIKE %s OR po.notes ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                cursor.execute(
                    f"""SELECT COUNT(*) as total FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    WHERE {where_clause}""",
                    params,
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                offset = (page - 1) * size
                pagination_meta = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total
                )

                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE {where_clause}
                    ORDER BY po.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    params + [size, offset],
                )
                purchase_orders = cursor.fetchall()

                po_list = []
                for po in purchase_orders:
                    po_dict = dict(po)
                    po_dict['created_by'] = po_dict.get('created_by') or None
                    po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                    po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None

                    items_data = PurchaseOrdersService._get_purchase_order_items(
                        cursor, tenant_id, org_id, bus_id, po_dict['id']
                    )
                    batches_data = PurchaseOrdersService._get_purchase_order_batches(
                        cursor, tenant_id, org_id, bus_id, po_dict['id']
                    )
                    # Get movements for batches
                    batch_ids = [batch.get('id') for batch in batches_data if batch.get('id')]
                    movements_by_batch = PurchaseOrdersService._get_batch_movements(
                        cursor, tenant_id, org_id, bus_id, batch_ids
                    ) if batch_ids else {}
                    batches_list = PurchaseOrdersService._convert_batches_to_dtos(batches_data, movements_by_batch)

                    batches_by_product = {}
                    for batch in batches_list:
                        product_id = batch.product_id
                        if product_id not in batches_by_product:
                            batches_by_product[product_id] = []
                        batches_by_product[product_id].append(batch)

                    items_list = []
                    for item in items_data:
                        item_dict = dict(item)
                        product_id = item_dict.get('product_id')
                        item_dict['batches'] = batches_by_product.get(product_id, None)
                        items_list.append(PurchaseOrderItemReadDto(**item_dict))

                    po_list.append(GetPurchaseOrdersServiceReadDto(
                        purchase_order=PurchaseOrderReadBase(**po_dict),
                        items=items_list
                    ))

                return Respons(
                    success=True,
                    detail="Purchase orders retrieved successfully",
                    data=po_list,
                    meta=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting purchase orders: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get purchase orders: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def cancel_purchase_order(
        data: CancelPurchaseOrderServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        cancelled_by: str
    ) -> Respons[CancelPurchaseOrderServiceReadDto]:
        """Cancel a purchase order by setting status to CANCELLED"""
        logger.info(
            f"Processing purchase order cancellation: {data.purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": data.purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                existing_po = cursor.fetchone()

                if not existing_po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_po)

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    SET status = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    ('CANCELLED', data.purchase_order_id, tenant_id, org_id, bus_id),
                )

                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (data.purchase_order_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else old_data
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-orders",
                        resource_id=data.purchase_order_id,
                        action="cancel",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Purchase order {data.purchase_order_id} cancelled",
                        performed_by=cancelled_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                cancel_result = CancelPurchaseOrderServiceReadDto(
                    purchase_order_id=data.purchase_order_id,
                    message="Purchase order cancelled successfully"
                )

                return Respons(
                    success=True,
                    detail="Purchase order cancelled successfully",
                    data=[cancel_result],
                )

        except Exception as e:
            logger.error(f"Error cancelling purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to cancel purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def permanent_delete_purchase_order(
        data: PermanentDeletePurchaseOrderServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[PermanentDeletePurchaseOrderServiceReadDto]:
        """Permanently delete a purchase order and its related items"""
        logger.info(
            f"Processing permanent delete purchase order: {data.purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": data.purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                existing_po = cursor.fetchone()

                if not existing_po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_po)

                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                    WHERE purchase_order_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                items_deleted = cursor.rowcount

                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Failed to delete purchase order")

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-orders",
                        resource_id=data.purchase_order_id,
                        action="permanent_delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Purchase order {data.purchase_order_id} permanently deleted along with {items_deleted} items",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                delete_result = PermanentDeletePurchaseOrderServiceReadDto(
                    purchase_order_id=data.purchase_order_id,
                    message=f"Purchase order permanently deleted successfully. {items_deleted} items were also deleted."
                )

                return Respons(
                    success=True,
                    detail=f"Purchase order permanently deleted successfully. {items_deleted} items were also deleted.",
                    data=[delete_result],
                )

        except Exception as e:
            logger.error(f"Error permanently deleting purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to permanently delete purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_purchase_order_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPurchaseOrderStatisticsServiceReadDto]:
        """Get comprehensive statistics for purchase orders"""
        logger.info(
            f"Processing get purchase order statistics request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get purchase order statistics by status
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_purchase_orders,
                        COUNT(CASE WHEN status = 'DRAFT' THEN 1 END) as total_draft,
                        COUNT(CASE WHEN status = 'APPROVED' THEN 1 END) as total_approved,
                        COUNT(CASE WHEN status = 'PARTIALLY_RECEIVED' THEN 1 END) as total_partially_received,
                        COUNT(CASE WHEN status = 'RECEIVED' THEN 1 END) as total_received,
                        COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as total_cancelled,
                        COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as total_completed,
                        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as total_pending,
                        COUNT(CASE WHEN status = 'ON_HOLD' THEN 1 END) as total_on_hold,
                        COUNT(CASE WHEN status = 'IN_PROGRESS' THEN 1 END) as total_in_progress
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (tenant_id, org_id, bus_id),
                )
                po_stats = cursor.fetchone()

                # Get item statistics (total items, quantities, and values)
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_items,
                        COALESCE(SUM(qty_ordered), 0) as total_qty_ordered,
                        COALESCE(SUM(qty_received), 0) as total_qty_received,
                        COALESCE(SUM(COALESCE(cost_price, 0) * COALESCE(qty_ordered, 0)), 0) as total_value,
                        COALESCE(SUM(COALESCE(cost_price, 0) * COALESCE(qty_received, 0)), 0) as total_received_value
                    FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi
                    INNER JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po 
                        ON poi.purchase_order_id = po.id 
                        AND poi.tenant_id = po.tenant_id 
                        AND poi.org_id = po.org_id 
                        AND poi.bus_id = po.bus_id
                    WHERE poi.tenant_id = %s AND poi.org_id = %s AND poi.bus_id = %s""",
                    (tenant_id, org_id, bus_id),
                )
                item_stats = cursor.fetchone()

                # Handle None cases
                if po_stats is None:
                    logger.warning("Purchase order statistics query returned no rows - using default values")
                    po_stats = {}
                
                if item_stats is None:
                    logger.warning("Item statistics query returned no rows - using default values")
                    item_stats = {}

                # Extract values with defaults
                total_purchase_orders = int(po_stats.get('total_purchase_orders', 0)) if po_stats else 0
                total_draft = int(po_stats.get('total_draft', 0)) if po_stats else 0
                total_approved = int(po_stats.get('total_approved', 0)) if po_stats else 0
                total_partially_received = int(po_stats.get('total_partially_received', 0)) if po_stats else 0
                total_received = int(po_stats.get('total_received', 0)) if po_stats else 0
                total_cancelled = int(po_stats.get('total_cancelled', 0)) if po_stats else 0
                total_completed = int(po_stats.get('total_completed', 0)) if po_stats else 0
                total_pending = int(po_stats.get('total_pending', 0)) if po_stats else 0
                total_on_hold = int(po_stats.get('total_on_hold', 0)) if po_stats else 0
                total_in_progress = int(po_stats.get('total_in_progress', 0)) if po_stats else 0

                total_items = int(item_stats.get('total_items', 0)) if item_stats else 0
                total_qty_ordered = int(item_stats.get('total_qty_ordered', 0)) if item_stats else 0
                total_qty_received = int(item_stats.get('total_qty_received', 0)) if item_stats else 0
                
                # Round decimal/numeric values to 2 decimal places
                two_places = Decimal('0.01')
                total_value = float(Decimal(str(item_stats.get('total_value', 0))).quantize(two_places, rounding=ROUND_HALF_UP)) if item_stats else 0.0
                total_received_value = float(Decimal(str(item_stats.get('total_received_value', 0))).quantize(two_places, rounding=ROUND_HALF_UP)) if item_stats else 0.0

                # Calculate average order value (avoid division by zero) and round to 2 decimal places
                if total_purchase_orders > 0:
                    average_order_value = float(Decimal(str(total_value / total_purchase_orders)).quantize(two_places, rounding=ROUND_HALF_UP))
                else:
                    average_order_value = None

                logger.info(
                    f"Statistics calculated: total_purchase_orders={total_purchase_orders}, "
                    f"total_items={total_items}, total_value={total_value}, "
                    f"total_received_value={total_received_value}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                        }
                    }
                )

                statistics = GetPurchaseOrderStatisticsServiceReadDto(
                    total_purchase_orders=total_purchase_orders,
                    total_items=total_items,
                    total_value=total_value,
                    total_received_value=total_received_value,
                    total_draft=total_draft,
                    total_approved=total_approved,
                    total_partially_received=total_partially_received,
                    total_received=total_received,
                    total_cancelled=total_cancelled,
                    total_completed=total_completed,
                    total_pending=total_pending,
                    total_on_hold=total_on_hold,
                    total_in_progress=total_in_progress,
                    average_order_value=average_order_value,
                    total_qty_ordered=total_qty_ordered,
                    total_qty_received=total_qty_received,
                )

                return Respons(
                    success=True,
                    detail="Purchase order statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting purchase order statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get purchase order statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_purchase_receipt(
        receipt_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPurchaseReceiptServiceReadDto]:
        """Get a single purchase receipt by ID"""
        logger.info(
            f"Processing get purchase receipt request: {receipt_id}",
            extra={
                "extra_fields": {
                    "receipt_id": receipt_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT pr.*,
                           creator.fullname as created_by_name,
                           po.po_number as purchase_order_number
                    FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pr.created_by = creator.id AND pr.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po ON pr.purchase_order_id = po.id 
                        AND pr.tenant_id = po.tenant_id 
                        AND pr.org_id = po.org_id 
                        AND pr.bus_id = po.bus_id
                    WHERE pr.id = %s AND pr.tenant_id = %s AND pr.org_id = %s AND pr.bus_id = %s""",
                    (receipt_id, tenant_id, org_id, bus_id),
                )
                receipt = cursor.fetchone()

                if not receipt:
                    return Respons(
                        success=False,
                        detail="Purchase receipt not found",
                        error="NOT_FOUND",
                    )

                receipt_dict = dict(receipt)
                receipt_dict['created_by_name'] = receipt_dict.get('created_by_name') or None
                receipt_dict['purchase_order_number'] = receipt_dict.get('purchase_order_number') or None

                receipt_read = GetPurchaseReceiptServiceReadDto(**receipt_dict)

                return Respons(
                    success=True,
                    detail="Purchase receipt retrieved successfully",
                    data=[receipt_read],
                )

        except Exception as e:
            logger.error(f"Error getting purchase receipt: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get purchase receipt: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_purchase_receipts(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        purchase_order_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetPurchaseReceiptsServiceReadDto]]:
        """Get list of purchase receipts with pagination"""
        logger.info(
            f"Processing get purchase receipts request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "purchase_order_id": purchase_order_id,
                    "search": search,
                    "page": page,
                    "size": size,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                where_conditions = [
                    "pr.tenant_id = %s",
                    "pr.org_id = %s",
                    "pr.bus_id = %s"
                ]
                params = [tenant_id, org_id, bus_id]

                if purchase_order_id:
                    where_conditions.append("pr.purchase_order_id = %s")
                    params.append(purchase_order_id)

                if search:
                    where_conditions.append(
                        "(pr.receipt_number ILIKE %s OR pr.description ILIKE %s OR po.po_number ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                cursor.execute(
                    f"""SELECT COUNT(*) as total 
                    FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po ON pr.purchase_order_id = po.id 
                        AND pr.tenant_id = po.tenant_id 
                        AND pr.org_id = po.org_id 
                        AND pr.bus_id = po.bus_id
                    WHERE {where_clause}""",
                    params,
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                offset = (page - 1) * size
                pagination_meta = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total
                )

                cursor.execute(
                    f"""SELECT pr.*,
                           creator.fullname as created_by_name,
                           po.po_number as purchase_order_number
                    FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pr.created_by = creator.id AND pr.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po ON pr.purchase_order_id = po.id 
                        AND pr.tenant_id = po.tenant_id 
                        AND pr.org_id = po.org_id 
                        AND pr.bus_id = po.bus_id
                    WHERE {where_clause}
                    ORDER BY pr.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    params + [size, offset],
                )
                receipts = cursor.fetchall()

                receipts_list = []
                for receipt in receipts:
                    receipt_dict = dict(receipt)
                    receipt_dict['created_by_name'] = receipt_dict.get('created_by_name') or None
                    receipt_dict['purchase_order_number'] = receipt_dict.get('purchase_order_number') or None
                    receipts_list.append(GetPurchaseReceiptsServiceReadDto(**receipt_dict))

                return Respons(
                    success=True,
                    detail="Purchase receipts retrieved successfully",
                    data=receipts_list,
                    meta=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting purchase receipts: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get purchase receipts: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_purchase_receipt(
        data: UpdatePurchaseReceiptServiceWriteDto,
        receipt_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdatePurchaseReceiptServiceReadDto]:
        """Update a purchase receipt"""
        logger.info(
            f"Processing purchase receipt update: {receipt_id}",
            extra={
                "extra_fields": {
                    "receipt_id": receipt_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (receipt_id, tenant_id, org_id, bus_id),
                )
                existing_receipt = cursor.fetchone()

                if not existing_receipt:
                    return Respons(
                        success=False,
                        detail="Purchase receipt not found",
                        error="NOT_FOUND",
                    )
                
                old_data = dict(existing_receipt)

                # Build update query dynamically
                update_fields = []
                params = []

                if data.received_date is not None:
                    update_fields.append("received_date = %s")
                    params.append(data.received_date)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.status is not None:
                    update_fields.append("status = %s")
                    params.append(data.status)

                if update_fields:
                    params.extend([receipt_id, tenant_id, org_id, bus_id])
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        params,
                    )

                # Get updated receipt
                cursor.execute(
                    f"""SELECT pr.*,
                           creator.fullname as created_by_name,
                           po.po_number as purchase_order_number
                    FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pr.created_by = creator.id AND pr.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po ON pr.purchase_order_id = po.id 
                        AND pr.tenant_id = po.tenant_id 
                        AND pr.org_id = po.org_id 
                        AND pr.bus_id = po.bus_id
                    WHERE pr.id = %s AND pr.tenant_id = %s AND pr.org_id = %s AND pr.bus_id = %s""",
                    (receipt_id, tenant_id, org_id, bus_id),
                )
                receipt_with_users = cursor.fetchone()

                if receipt_with_users:
                    receipt_dict = dict(receipt_with_users)
                    receipt_dict['created_by_name'] = receipt_dict.get('created_by_name') or None
                    receipt_dict['purchase_order_number'] = receipt_dict.get('purchase_order_number') or None
                else:
                    receipt_dict = dict(existing_receipt)
                    receipt_dict['created_by_name'] = None
                    receipt_dict['purchase_order_number'] = None

                receipt_read = UpdatePurchaseReceiptServiceReadDto(**receipt_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (receipt_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else receipt_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-receipts",
                        resource_id=receipt_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Purchase receipt {receipt_id} updated successfully",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(
                    success=True,
                    detail="Purchase receipt updated successfully",
                    data=[receipt_read],
                )

        except Exception as e:
            logger.error(f"Error updating purchase receipt: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update purchase receipt: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_purchase_receipt(
        data: DeletePurchaseReceiptServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeletePurchaseReceiptServiceReadDto]:
        """Delete a purchase receipt"""
        logger.info(
            f"Processing purchase receipt deletion: {data.receipt_id}",
            extra={
                "extra_fields": {
                    "receipt_id": data.receipt_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.receipt_id, tenant_id, org_id, bus_id),
                )
                existing_receipt = cursor.fetchone()

                if not existing_receipt:
                    return Respons(
                        success=False,
                        detail="Purchase receipt not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_receipt)

                # Delete the receipt
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.receipt_id, tenant_id, org_id, bus_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Failed to delete purchase receipt")

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-receipts",
                        resource_id=data.receipt_id,
                        action="delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Purchase receipt {data.receipt_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                delete_result = DeletePurchaseReceiptServiceReadDto(
                    receipt_id=data.receipt_id,
                    message="Purchase receipt deleted successfully"
                )

                return Respons(
                    success=True,
                    detail="Purchase receipt deleted successfully",
                    data=[delete_result],
                )

        except Exception as e:
            logger.error(f"Error deleting purchase receipt: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete purchase receipt: {str(e)}",
                error="INTERNAL_ERROR",
            )

