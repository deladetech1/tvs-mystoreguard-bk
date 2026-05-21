from typing import Optional, List
from decimal import Decimal
from src.entities.store_products.store_products_read_dto import (
    CreateStoreProductServiceReadDto,
    UpdateStoreProductServiceReadDto,
    DeleteStoreProductServiceReadDto,
    PermanentDeleteStoreProductServiceReadDto,
    ReverseBatchStoreProductServiceReadDto,
    GetStoreProductServiceReadDto,
    GetStoreProductsServiceReadDto,
    GetStoreProductStatisticsServiceReadDto,
    AddStockStoreProductServiceReadDto,
    BulkCreateStoreProductServiceReadDto,
)
from src.entities.products.products_read_dto import ProductMovementReadDto
from src.entities.products.products_read_dto import PurchaseBatchReadDto
from src.entities.products.products_read_dto import DocumentReadDto
from src.entities.products.products_read_dto import MetadataReadDto
from src.entities.products.products_service import ProductsService
from src.entities.store_products.store_products_write_dto import (
    CreateStoreProductServiceWriteDto,
    UpdateStoreProductServiceWriteDto,
    DeleteStoreProductServiceWriteDto,
    PermanentDeleteStoreProductServiceWriteDto,
    ReverseBatchStoreProductServiceWriteDto,
    AddStockStoreProductServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from src.entities.filemanager.fmg_service import FileUploadService
from src.utils.product_price_calculator import ProductPriceCalculator
from trovesuite.utils import Helper

logger = get_logger("store_products_service")


class StoreProductsService:
    """Service class for store products operations"""

    @staticmethod
    def _get_store_product_batches(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        product_id: str,
        cursor
    ) -> List[dict]:
        """Get batches allocated to a store location for a product"""
        cursor.execute(
            f"""SELECT bl.*, pb.batch_number, pb.supplier_id, pb.currency_id, pb.cost_price, 
                   pb.base_selling_price, pb.product_size, pb.unit_of_measure_id, 
                   pb.qty_received, pb.qty_remaining, pb.product_expiry_date,
                   pb.status as batch_status, pb.delete_status as batch_delete_status, 
                   pb.is_active as batch_is_active, pb.batch_type,
                   pb.cdate as batch_cdate, pb.ctime as batch_ctime, pb.cdatetime as batch_cdatetime,
                   pb.created_by as batch_created_by, pb.updated_by as batch_updated_by,
                   pb.deleted_by as batch_deleted_by,
                   c.name as currency_name, c.code as currency_code, c.symbol as currency_symbol,
                   c.decimal_places as currency_decimal_places,
                   uom.name as unit_of_measure_name,
                   s.fullname as supplier_name,
                   l.loc_name as location_name
            FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
            INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb 
                ON bl.purchase_batche_id = pb.id 
                AND bl.tenant_id = pb.tenant_id 
                AND bl.org_id = pb.org_id 
                AND bl.bus_id = pb.bus_id
            LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c 
                ON pb.currency_id = c.id AND pb.tenant_id = c.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE} uom 
                ON pb.unit_of_measure_id = uom.id AND pb.tenant_id = uom.tenant_id
            LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s 
                ON pb.supplier_id = s.id 
                AND pb.tenant_id = s.tenant_id 
                AND pb.org_id = s.org_id 
                AND pb.bus_id = s.bus_id
            LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l 
                ON bl.loc_id = l.id AND bl.tenant_id = l.tenant_id
            WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s 
            AND bl.loc_id = %s AND pb.product_id = %s AND bl.location_type = 'STORE'
            ORDER BY bl.cdatetime ASC, pb.cdatetime ASC""",
            (tenant_id, org_id, bus_id, loc_id, product_id),
        )
        return cursor.fetchall()

    @staticmethod
    def _get_store_product_documents(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        product_id: str
    ) -> List[DocumentReadDto]:
        """Get documents for a product (used by store products) with presigned URLs"""
        cursor.execute(
            f"""SELECT pdi.document_id, dp.file_name, dp.description, dp.document_path
            FROM {db_settings.MSG_PRODUCT_DOCUMENT_IDS_TABLE} pdi
            INNER JOIN {db_settings.MSG_DOCUMENT_PATHS_TABLE} dp 
                ON pdi.document_id = dp.id 
                AND pdi.tenant_id = dp.tenant_id 
                AND pdi.org_id = dp.org_id 
                AND pdi.bus_id = dp.bus_id
            WHERE pdi.tenant_id = %s AND pdi.org_id = %s AND pdi.bus_id = %s 
            AND pdi.product_id = %s 
            AND pdi.delete_status = 'NOT_DELETED' AND pdi.is_active = true
            AND dp.delete_status = 'NOT_DELETED' AND dp.is_active = true""",
            (tenant_id, org_id, bus_id, product_id),
        )
        results = cursor.fetchall()
        
        documents = []
        container_name = db_settings.MYSTOREGUARD_FILES_CONTAINER
        expiry_hours = 24
        
        for row in results:
            doc_id = row.get('document_id')
            if not doc_id:
                continue
                
            document_path = row.get('document_path')
            file_name = row.get('file_name')
            description = row.get('description')
            
            # Generate presigned URL
            presigned_url = ""
            if document_path:
                presigned_url = FileUploadService._get_file_presigned_url(
                    container_name=container_name,
                    blob_path=document_path,
                    expiry_hours=expiry_hours
                ) or ""
            
            documents.append(DocumentReadDto(
                doc_id=doc_id,
                description=description,
                name=file_name,
                presigned_url=presigned_url
            ))
        
        return documents

    @staticmethod
    def _get_store_product_movements(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        product_id: str,
        cursor
    ) -> List[dict]:
        """Get product movements for a store location (DEPRECATED - use _get_batch_movements instead)"""
        cursor.execute(
            f"""SELECT pm.*, pb.batch_number,
                   p.name as product_name,
                   l.loc_name as location_name,
                   creator.fullname as created_by_name,
                   updater.fullname as updated_by_name,
                   deleter.fullname as deleted_by_name
            FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm
            LEFT JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb 
                ON pm.batch_id = pb.id 
                AND pm.tenant_id = pb.tenant_id 
                AND pm.org_id = pb.org_id 
                AND pm.bus_id = pb.bus_id
            LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p 
                ON pm.product_id = p.id 
                AND pm.tenant_id = p.tenant_id 
                AND pm.org_id = p.org_id 
                AND pm.bus_id = p.bus_id
            LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l 
                ON pm.location_id = l.id AND pm.tenant_id = l.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                ON pm.created_by = creator.id AND pm.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater 
                ON pm.updated_by = updater.id AND pm.tenant_id = updater.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter 
                ON pm.deleted_by = deleter.id AND pm.tenant_id = deleter.tenant_id
            WHERE pm.tenant_id = %s AND pm.org_id = %s AND pm.bus_id = %s 
            AND pm.product_id = %s AND pm.location_id = %s AND pm.location_type = 'STORE'
            ORDER BY pm.cdatetime DESC""",
            (tenant_id, org_id, bus_id, product_id, loc_id),
        )
        return cursor.fetchall()

    @staticmethod
    def _get_batch_movements(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        batch_id: str,
        loc_id: str,
        cursor
    ) -> List[dict]:
        """Get movements for a specific batch at a store location (only STORE location_type)"""
        cursor.execute(
            f"""SELECT pm.*, pb.batch_number,
                   p.name as product_name,
                   l.loc_name as location_name,
                   creator.fullname as created_by_name,
                   updater.fullname as updated_by_name,
                   deleter.fullname as deleted_by_name
            FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm
            LEFT JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb 
                ON pm.batch_id = pb.id 
                AND pm.tenant_id = pb.tenant_id 
                AND pm.org_id = pb.org_id 
                AND pm.bus_id = pb.bus_id
            LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p 
                ON pm.product_id = p.id 
                AND pm.tenant_id = p.tenant_id 
                AND pm.org_id = p.org_id 
                AND pm.bus_id = p.bus_id
            LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l 
                ON pm.location_id = l.id AND pm.tenant_id = l.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                ON pm.created_by = creator.id AND pm.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater 
                ON pm.updated_by = updater.id AND pm.tenant_id = updater.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter 
                ON pm.deleted_by = deleter.id AND pm.tenant_id = deleter.tenant_id
            WHERE pm.tenant_id = %s AND pm.org_id = %s AND pm.bus_id = %s 
            AND pm.batch_id = %s AND pm.location_type = 'STORE' AND pm.location_id = %s
            ORDER BY pm.cdatetime DESC""",
            (tenant_id, org_id, bus_id, batch_id, loc_id),
        )
        return cursor.fetchall()

    @staticmethod
    def create_store_product(
        data: CreateStoreProductServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateStoreProductServiceReadDto]:
        """Create a new store product with FIFO batch allocation"""
        logger.info(
            f"Processing store product creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "product_id": data.product_id,
                    "current_qty": data.current_qty,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Verify product exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.product_id),
                )
                if not cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"Product {data.product_id} not found",
                        error="PRODUCT_NOT_FOUND",
                    )

                # Verify location exists
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

                # Validate quantity > 0
                if data.current_qty <= 0:
                    return Respons(
                        success=False,
                        detail="Quantity cannot be less than or equal to 0",
                        error="INVALID_QUANTITY",
                    )

                # Check if store product already exists
                cursor.execute(
                    f"""SELECT id, current_qty FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                existing = cursor.fetchone()
                is_update = existing is not None
                existing_qty = existing['current_qty'] if existing else 0
                
                # When product exists, treat the provided qty as new batch allocation (add to existing)
                # When product doesn't exist, use the provided qty as is
                qty_to_allocate = data.current_qty
                new_total_qty = existing_qty + qty_to_allocate if is_update else qty_to_allocate

                # Get batches based on batch_numbers
                batches_to_use = []
                if not data.batch_numbers or len(data.batch_numbers) == 0:
                    # Get batches in FIFO order (oldest first) - include datetime fields for FIFO insertion
                    cursor.execute(
                        f"""SELECT id, batch_number, qty_remaining, cdate, ctime, cdatetime
                        FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s AND delete_status = 'NOT_DELETED' AND is_active = true
                        AND qty_remaining > 0
                        ORDER BY cdatetime ASC""",
                        (tenant_id, org_id, bus_id, data.product_id),
                    )
                    batches_to_use = cursor.fetchall()
                else:
                    # Get specific batches by batch_number, ordered by cdatetime ASC for FIFO - include datetime fields
                    cursor.execute(
                        f"""SELECT id, batch_number, qty_remaining, cdate, ctime, cdatetime
                        FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s AND batch_number = ANY(%s)
                        AND delete_status = 'NOT_DELETED' AND is_active = true
                        AND qty_remaining > 0
                        ORDER BY cdatetime ASC""",
                        (tenant_id, org_id, bus_id, data.product_id, data.batch_numbers),
                    )
                    batches_to_use = cursor.fetchall()

                if not batches_to_use:
                    return Respons(
                        success=False,
                        detail="No available batches found for this product",
                        error="NO_BATCHES_AVAILABLE",
                    )

                # Calculate total available quantity
                total_available_qty = sum(batch['qty_remaining'] for batch in batches_to_use)

                # Validate quantity needed
                if qty_to_allocate > total_available_qty:
                    return Respons(
                        success=False,
                        detail=f"Insufficient quantity. Available: {total_available_qty}, Needed: {qty_to_allocate}",
                        error="INSUFFICIENT_QUANTITY",
                    )

                # Allocate batches to location using FIFO
                batch_allocations = []  # Store (batch_id, qty_allocated) for movements - maintains FIFO order
                remaining_qty_to_allocate = qty_to_allocate

                # Process batches in the order they were retrieved (already sorted by cdatetime ASC)
                for batch in batches_to_use:
                    if remaining_qty_to_allocate <= 0:
                        break

                    batch_id = batch['id']
                    # Get batch creation datetime from initial query for FIFO ordering
                    batch_cdate = batch['cdate']
                    batch_ctime = batch['ctime']
                    batch_cdatetime_for_insert = batch['cdatetime']
                    
                    # Read current qty_remaining from database to ensure accuracy (handles multiple batches correctly)
                    cursor.execute(
                        f"""SELECT qty_remaining FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND delete_status = 'NOT_DELETED' AND is_active = true""",
                        (batch_id, tenant_id, org_id, bus_id),
                    )
                    current_batch = cursor.fetchone()
                    
                    if not current_batch or current_batch['qty_remaining'] <= 0:
                        # Skip this batch if it no longer has available quantity
                        continue
                    
                    current_batch_qty_remaining = current_batch['qty_remaining']
                    qty_to_allocate_batch = min(remaining_qty_to_allocate, current_batch_qty_remaining)

                    # Check if batch_location already exists for this batch and location
                    cursor.execute(
                        f"""SELECT id, qty FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND purchase_batche_id = %s AND location_type = 'STORE'""",
                        (tenant_id, org_id, bus_id, loc_id, batch_id),
                    )
                    existing_batch_location = cursor.fetchone()

                    if existing_batch_location:
                        # Update existing batch location (preserve original cdatetime for FIFO)
                        # Don't update cdatetime - keep the original to maintain FIFO order
                        new_qty = existing_batch_location['qty'] + qty_to_allocate_batch
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            SET qty = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (new_qty, existing_batch_location['id'], tenant_id, org_id, bus_id),
                        )
                    else:
                        # Insert new batch location using batch's creation datetime for FIFO ordering
                        # This ensures first batch in = first batch out when deducting
                        batch_location_id = Helper.generate_unique_identifier(prefix="bloc")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, purchase_batche_id, location_type, qty,
                             cdate, ctime, cdatetime)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                batch_location_id, tenant_id, org_id, bus_id, loc_id,
                                batch_id, 'STORE', qty_to_allocate_batch,
                                batch_cdate, batch_ctime, batch_cdatetime_for_insert
                            ),
                        )

                    # Update qty_remaining in purchase batch (using current value from database)
                    new_batch_qty_remaining = current_batch_qty_remaining - qty_to_allocate_batch
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        SET qty_remaining = %s, updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND qty_remaining = %s""",
                        (new_batch_qty_remaining, created_by, batch_id, tenant_id, org_id, bus_id, current_batch_qty_remaining),
                    )
                    
                    # Verify the update was successful (optimistic locking)
                    if cursor.rowcount == 0:
                        # Batch was modified by another transaction, skip and continue to next batch
                        logger.warning(
                            f"Batch {batch_id} qty_remaining was modified, skipping allocation",
                            extra={
                                "extra_fields": {
                                    "batch_id": batch_id,
                                    "expected_qty": current_batch_qty_remaining,
                                }
                            }
                        )
                        continue

                    # Store allocation for movement creation (maintains FIFO order)
                    batch_allocations.append((batch_id, qty_to_allocate_batch))
                    remaining_qty_to_allocate -= qty_to_allocate_batch

                # Insert or update store product
                if is_update:
                    # Update existing store product - only update current_qty, don't update reorder_level, reorder_quantity, description, or is_active
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        SET current_qty = %s, updated_by = %s
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND product_id = %s""",
                        (new_total_qty, created_by, tenant_id, org_id, bus_id, loc_id, data.product_id),
                    )
                    
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND product_id = %s""",
                        (tenant_id, org_id, bus_id, loc_id, data.product_id),
                    )
                    store_product_result = cursor.fetchone()
                else:
                    # Insert new store product
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        (tenant_id, org_id, bus_id, loc_id, product_id, current_qty,
                         reorder_level, reorder_quantity, is_active, delete_status,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            tenant_id, org_id, bus_id, loc_id, data.product_id,
                            new_total_qty,
                            data.reorder_level, data.reorder_quantity,
                            data.is_active if data.is_active is not None else True,
                            'NOT_DELETED',
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    store_product_result = cursor.fetchone()

                if not store_product_result:
                    raise ValueError("Failed to create/update store product")

                # Create transfer movements (one OUT and one IN per batch allocation, in FIFO order)
                # This ensures if we have 10 batches, we create 20 movements (10 OUT + 10 IN)
                for batch_id, qty_allocated in batch_allocations:
                    # Create OUT movement (product leaving the system side)
                    out_movement_id = Helper.generate_unique_identifier(prefix="mov")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                         movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            out_movement_id, tenant_id, org_id, bus_id, data.product_id,
                            batch_id, 'SYSTEM', None,
                            'OUT', qty_allocated, 'Store product allocation', None,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    
                    # Create IN movement (product going into the store)
                    in_movement_id = Helper.generate_unique_identifier(prefix="mov")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                         movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            in_movement_id, tenant_id, org_id, bus_id, data.product_id,
                            batch_id, 'STORE', loc_id,
                            'IN', qty_allocated, 'Store product allocation', None,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )

                # Get store product with user fullnames
                cursor.execute(
                    f"""SELECT sp.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           p.name as product_name,
                           p.name,
                           p.description,
                           p.sku,
                           p.bar_code,
                           p.is_active,
                           l.loc_name as location_name
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sp.created_by = creator.id AND sp.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sp.updated_by = updater.id AND sp.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sp.deleted_by = deleter.id AND sp.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON sp.product_id = p.id 
                        AND sp.tenant_id = p.tenant_id 
                        AND sp.org_id = p.org_id 
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l ON sp.loc_id = l.id AND sp.tenant_id = l.tenant_id
                    WHERE sp.tenant_id = %s AND sp.org_id = %s AND sp.bus_id = %s 
                    AND sp.loc_id = %s AND sp.product_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                sp_with_users = cursor.fetchone()

                if sp_with_users:
                    sp_dict = dict(sp_with_users)
                    sp_dict['created_by'] = sp_dict.get('created_by') or None
                    sp_dict['updated_by'] = sp_dict.get('updated_by') or None
                    sp_dict['deleted_by'] = sp_dict.get('deleted_by') or None
                    sp_dict['product_name'] = sp_dict.get('product_name') or None
                    sp_dict['location_name'] = sp_dict.get('location_name') or None
                    # Product fields
                    sp_dict['name'] = sp_dict.get('name') or ''
                    sp_dict['description'] = sp_dict.get('description') or None
                    sp_dict['sku'] = sp_dict.get('sku') or None
                    sp_dict['bar_code'] = sp_dict.get('bar_code') or None
                    sp_dict['is_active'] = sp_dict.get('is_active', True)
                else:
                    sp_dict = dict(store_product_result)
                    sp_dict['created_by'] = None
                    sp_dict['updated_by'] = None
                    sp_dict['deleted_by'] = None
                    sp_dict['product_name'] = None
                    sp_dict['location_name'] = None
                    # Product fields - need to fetch from product table if store_product_result exists
                    if store_product_result and store_product_result.get('product_id'):
                        cursor.execute(
                            f"""SELECT name, description, sku, bar_code, is_active
                            FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (store_product_result['product_id'], tenant_id, org_id, bus_id),
                        )
                        product = cursor.fetchone()
                        if product:
                            sp_dict['name'] = product.get('name') or ''
                            sp_dict['description'] = product.get('description') or None
                            sp_dict['sku'] = product.get('sku') or None
                            sp_dict['bar_code'] = product.get('bar_code') or None
                            sp_dict['is_active'] = product.get('is_active', True)
                        else:
                            sp_dict['name'] = ''
                            sp_dict['description'] = None
                            sp_dict['sku'] = None
                            sp_dict['bar_code'] = None
                            sp_dict['is_active'] = True
                    else:
                        sp_dict['name'] = ''
                        sp_dict['description'] = None
                        sp_dict['sku'] = None
                        sp_dict['bar_code'] = None
                        sp_dict['is_active'] = True

                # Get metadata for price calculation
                metadata_data = ProductsService._get_product_metadata(
                    cursor=cursor,
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    product_id=data.product_id
                )
                
                # Calculate prices using PricingCalculator
                product_metadata_for_pricing = {}
                if metadata_data:
                    # Transform metadata to format expected by PricingCalculator
                    for meta in metadata_data:
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
                
                sku = sp_dict.get('sku')
                
                # Price fields from batch (if available)
                sp_dict['cost_price'] = None
                sp_dict['base_selling_price'] = None
                sp_dict['currency_id'] = None
                sp_dict['currency_name'] = None
                sp_dict['currency_symbol'] = None
                
                try:
                    # Calculate prices using ProductPriceCalculator (SIMPLE TAX - NO CONDITIONS)
                    prices = ProductPriceCalculator.calculate_product_prices(
                        cursor, data.product_id, tenant_id, org_id, bus_id,
                        quantity=1,  # quantity = 1 for unit price display
                        location_id=loc_id,
                        sku=sku,
                        product_metadata=product_metadata_for_pricing if product_metadata_for_pricing else None
                    )
                    
                    sp_dict['actual_price'] = prices.get('actual_price')
                    sp_dict['price_after_pricing_rule'] = prices.get('price_after_pricing_rule')
                    sp_dict['price_after_tax'] = None  # No tax for store products
                    sp_dict['tax_amount'] = None  # No tax for store products
                    sp_dict['final_price'] = prices.get('final_price')  # Same as price_after_pricing_rule
                    sp_dict['taxes_applied'] = []  # No tax for store products
                    sp_dict['pricing_rules_applied'] = prices.get('pricing_rules_applied', [])
                    sp_dict['tax_rules_applied'] = []  # No tax for store products
                except Exception as price_err:
                    # If price calculation fails, set to None and log
                    logger.debug(f"Price calculation failed for product {data.product_id}: {str(price_err)}")
                    sp_dict['actual_price'] = None
                    sp_dict['price_after_pricing_rule'] = None
                    sp_dict['price_after_tax'] = None
                    sp_dict['tax_amount'] = None
                    sp_dict['final_price'] = None
                    sp_dict['taxes_applied'] = []
                    sp_dict['pricing_rules_applied'] = []
                    sp_dict['tax_rules_applied'] = []

                sp_read = CreateStoreProductServiceReadDto(**sp_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND product_id = %s""",
                        (tenant_id, org_id, bus_id, loc_id, data.product_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else sp_dict
                    
                    action = "update" if is_update else "create"
                    old_data_for_log = dict(existing) if is_update else None
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-products",
                        resource_id=sp_dict['id'],
                        action=action,
                        old_data=old_data_for_log,
                        new_data=complete_new_data,
                        description=f"Store product {sp_dict['id']} {action}d successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                action_msg = "updated" if is_update else "created"
                logger.info(
                    f"Store product {action_msg} successfully: {sp_dict['id']}",
                    extra={
                        "extra_fields": {
                            "store_product_id": sp_dict['id'],
                            "product_id": data.product_id,
                            "loc_id": loc_id,
                            "action": action_msg,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail=f"Store product {action_msg} successfully",
                    data=[sp_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating store product: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating store product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create store product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def create_store_products(
        items: List[CreateStoreProductServiceWriteDto],
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[BulkCreateStoreProductServiceReadDto]:
        """Create one or more store products at a single location (best-effort).

        Each item is processed independently via ``create_store_product`` (its own
        transaction), so a failure on one item does not roll back the items that
        already succeeded. A per-item result is returned for every item in the
        request, in the same order.
        """
        if not items:
            return Respons(
                success=False,
                detail="At least one store product is required",
                error="VALIDATION_ERROR",
            )

        logger.info(
            "Processing bulk store product creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "item_count": len(items),
                    "product_ids": [item.product_id for item in items],
                }
            },
        )

        results: List[BulkCreateStoreProductServiceReadDto] = []
        succeeded = 0

        for index, data in enumerate(items):
            result = StoreProductsService.create_store_product(
                data=data,
                tenant_id=tenant_id,
                org_id=org_id,
                bus_id=bus_id,
                loc_id=loc_id,
                created_by=created_by,
            )

            store_product = result.data[0] if (result.success and result.data) else None
            if result.success:
                succeeded += 1

            results.append(
                BulkCreateStoreProductServiceReadDto(
                    index=index,
                    product_id=data.product_id,
                    success=result.success,
                    detail=result.detail,
                    error=result.error,
                    store_product=store_product,
                )
            )

        failed = len(items) - succeeded
        detail = f"Added {succeeded} of {len(items)} store product(s) successfully"
        if failed:
            detail += f", {failed} failed"

        return Respons(
            # Best-effort: success when at least one item was added
            success=succeeded > 0,
            detail=detail,
            data=results,
        )

    @staticmethod
    def add_stock_store_product(
        data: AddStockStoreProductServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[AddStockStoreProductServiceReadDto]:
        """Add stock to an existing store product with FIFO batch allocation"""
        logger.info(
            f"Processing add stock to store product",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "product_id": data.product_id,
                    "qty": data.qty,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Validate quantity > 0
                if data.qty <= 0:
                    return Respons(
                        success=False,
                        detail="Quantity cannot be less than or equal to 0",
                        error="INVALID_QUANTITY",
                    )

                # Verify product exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.product_id),
                )
                if not cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"Product {data.product_id} not found",
                        error="PRODUCT_NOT_FOUND",
                    )

                # Verify location exists
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

                # Check if store product exists - MUST exist for add stock
                cursor.execute(
                    f"""SELECT id, current_qty FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                existing = cursor.fetchone()
                
                if not existing:
                    return Respons(
                        success=False,
                        detail="Store product does not exist. Use create endpoint to add a new product.",
                        error="STORE_PRODUCT_NOT_FOUND",
                    )

                existing_qty = existing['current_qty']
                qty_to_allocate = data.qty
                new_total_qty = existing_qty + qty_to_allocate

                logger.info(
                    f"Add stock calculation: existing_qty={existing_qty}, qty_to_allocate={qty_to_allocate}, new_total_qty={new_total_qty}",
                    extra={
                        "extra_fields": {
                            "existing_qty": existing_qty,
                            "qty_to_allocate": qty_to_allocate,
                            "new_total_qty": new_total_qty,
                        }
                    },
                )

                # Get batches based on batch_numbers
                batches_to_use = []
                if not data.batch_numbers or len(data.batch_numbers) == 0:
                    # Get batches in FIFO order (oldest first) - include datetime fields for FIFO insertion
                    cursor.execute(
                        f"""SELECT id, batch_number, qty_remaining, cdate, ctime, cdatetime
                        FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s AND delete_status = 'NOT_DELETED' AND is_active = true
                        AND qty_remaining > 0
                        ORDER BY cdatetime ASC""",
                        (tenant_id, org_id, bus_id, data.product_id),
                    )
                    batches_to_use = cursor.fetchall()
                else:
                    # Get specific batches by batch_number, ordered by cdatetime ASC for FIFO - include datetime fields
                    cursor.execute(
                        f"""SELECT id, batch_number, qty_remaining, cdate, ctime, cdatetime
                        FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s AND batch_number = ANY(%s)
                        AND delete_status = 'NOT_DELETED' AND is_active = true
                        AND qty_remaining > 0
                        ORDER BY cdatetime ASC""",
                        (tenant_id, org_id, bus_id, data.product_id, data.batch_numbers),
                    )
                    batches_to_use = cursor.fetchall()

                if not batches_to_use:
                    return Respons(
                        success=False,
                        detail="No available batches found for this product",
                        error="NO_BATCHES_AVAILABLE",
                    )

                # Calculate total available quantity
                total_available_qty = sum(batch['qty_remaining'] for batch in batches_to_use)

                # Validate quantity needed
                if qty_to_allocate > total_available_qty:
                    return Respons(
                        success=False,
                        detail=f"Insufficient quantity. Available: {total_available_qty}, Needed: {qty_to_allocate}",
                        error="INSUFFICIENT_QUANTITY",
                    )

                # Allocate batches to location using FIFO
                batch_allocations = []  # Store (batch_id, qty_allocated) for movements - maintains FIFO order
                remaining_qty_to_allocate = qty_to_allocate

                # Process batches in the order they were retrieved (already sorted by cdatetime ASC)
                for batch in batches_to_use:
                    if remaining_qty_to_allocate <= 0:
                        break

                    batch_id = batch['id']
                    # Get batch creation datetime from initial query for FIFO ordering
                    batch_cdate = batch['cdate']
                    batch_ctime = batch['ctime']
                    batch_cdatetime_for_insert = batch['cdatetime']
                    
                    # Read current qty_remaining from database to ensure accuracy (handles multiple batches correctly)
                    cursor.execute(
                        f"""SELECT qty_remaining FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND delete_status = 'NOT_DELETED' AND is_active = true""",
                        (batch_id, tenant_id, org_id, bus_id),
                    )
                    current_batch = cursor.fetchone()
                    
                    if not current_batch or current_batch['qty_remaining'] <= 0:
                        # Skip this batch if it no longer has available quantity
                        continue
                    
                    current_batch_qty_remaining = current_batch['qty_remaining']
                    qty_to_allocate_batch = min(remaining_qty_to_allocate, current_batch_qty_remaining)

                    # Check if batch_location already exists for this batch and location
                    cursor.execute(
                        f"""SELECT id, qty FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND purchase_batche_id = %s AND location_type = 'STORE'""",
                        (tenant_id, org_id, bus_id, loc_id, batch_id),
                    )
                    existing_batch_location = cursor.fetchone()

                    if existing_batch_location:
                        # Update existing batch location (preserve original cdatetime for FIFO)
                        # Don't update cdatetime - keep the original to maintain FIFO order
                        new_qty = existing_batch_location['qty'] + qty_to_allocate_batch
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            SET qty = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (new_qty, existing_batch_location['id'], tenant_id, org_id, bus_id),
                        )
                    else:
                        # Insert new batch location using batch's creation datetime for FIFO ordering
                        # This ensures first batch in = first batch out when deducting
                        batch_location_id = Helper.generate_unique_identifier(prefix="bloc")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, purchase_batche_id, location_type, qty,
                             cdate, ctime, cdatetime)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                batch_location_id, tenant_id, org_id, bus_id, loc_id,
                                batch_id, 'STORE', qty_to_allocate_batch,
                                batch_cdate, batch_ctime, batch_cdatetime_for_insert
                            ),
                        )

                    # Update qty_remaining in purchase batch (using current value from database)
                    new_batch_qty_remaining = current_batch_qty_remaining - qty_to_allocate_batch
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        SET qty_remaining = %s, updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND qty_remaining = %s""",
                        (new_batch_qty_remaining, created_by, batch_id, tenant_id, org_id, bus_id, current_batch_qty_remaining),
                    )
                    
                    # Verify the update was successful (optimistic locking)
                    if cursor.rowcount == 0:
                        # Batch was modified by another transaction, skip and continue to next batch
                        logger.warning(
                            f"Batch {batch_id} qty_remaining was modified, skipping allocation",
                            extra={
                                "extra_fields": {
                                    "batch_id": batch_id,
                                    "expected_qty": current_batch_qty_remaining,
                                }
                            }
                        )
                        continue

                    # Store allocation for movement creation (maintains FIFO order)
                    batch_allocations.append((batch_id, qty_to_allocate_batch))
                    remaining_qty_to_allocate -= qty_to_allocate_batch

                # Validate that we actually allocated something
                if not batch_allocations:
                    return Respons(
                        success=False,
                        detail="Failed to allocate any batches. All batches may have been modified by another transaction.",
                        error="ALLOCATION_FAILED",
                    )

                # Calculate actual quantity allocated (may be less than requested if batches were modified)
                actual_qty_allocated = sum(qty for _, qty in batch_allocations)
                actual_new_total_qty = existing_qty + actual_qty_allocated

                logger.info(
                    f"Updating store product: existing_qty={existing_qty}, actual_qty_allocated={actual_qty_allocated}, actual_new_total_qty={actual_new_total_qty}",
                    extra={
                        "extra_fields": {
                            "existing_qty": existing_qty,
                            "requested_qty": qty_to_allocate,
                            "actual_qty_allocated": actual_qty_allocated,
                            "actual_new_total_qty": actual_new_total_qty,
                            "batch_allocations_count": len(batch_allocations),
                        }
                    },
                )

                # Validate that the new quantity is actually greater (defensive check)
                if actual_new_total_qty <= existing_qty:
                    logger.error(
                        f"BUG DETECTED: New quantity ({actual_new_total_qty}) is not greater than existing ({existing_qty}). This should never happen when adding stock!",
                        extra={
                            "extra_fields": {
                                "existing_qty": existing_qty,
                                "actual_qty_allocated": actual_qty_allocated,
                                "actual_new_total_qty": actual_new_total_qty,
                                "requested_qty": qty_to_allocate,
                            }
                        },
                    )
                    return Respons(
                        success=False,
                        detail=f"Internal error: New quantity ({actual_new_total_qty}) is not greater than existing ({existing_qty}). Please contact support.",
                        error="INTERNAL_ERROR",
                    )

                # Update store product - only update current_qty with actual allocated quantity
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    SET current_qty = %s, updated_by = %s
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s""",
                    (actual_new_total_qty, created_by, tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                
                # Verify the update was successful and check the result
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                store_product_result = cursor.fetchone()

                if not store_product_result:
                    raise ValueError("Failed to update store product")

                # Verify the update actually worked (defensive check)
                updated_qty = store_product_result.get('current_qty', 0)
                if updated_qty != actual_new_total_qty:
                    logger.error(
                        f"BUG DETECTED: Updated quantity ({updated_qty}) does not match expected ({actual_new_total_qty})!",
                        extra={
                            "extra_fields": {
                                "expected_qty": actual_new_total_qty,
                                "actual_updated_qty": updated_qty,
                                "existing_qty": existing_qty,
                                "actual_qty_allocated": actual_qty_allocated,
                            }
                        },
                    )
                    # Rollback would happen automatically, but log the error
                    raise ValueError(f"Update verification failed: Expected {actual_new_total_qty}, got {updated_qty}")

                # Create transfer movements (one OUT and one IN per batch allocation, in FIFO order)
                for batch_id, qty_allocated in batch_allocations:
                    # Create OUT movement (product leaving the system side)
                    out_movement_id = Helper.generate_unique_identifier(prefix="mov")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                         movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            out_movement_id, tenant_id, org_id, bus_id, data.product_id,
                            batch_id, 'SYSTEM', None,
                            'OUT', qty_allocated, 'Add stock to store product', None,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    
                    # Create IN movement (product going into the store)
                    in_movement_id = Helper.generate_unique_identifier(prefix="mov")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                         movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            in_movement_id, tenant_id, org_id, bus_id, data.product_id,
                            batch_id, 'STORE', loc_id,
                            'IN', qty_allocated, 'Add stock to store product', None,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )

                # Get store product with user fullnames
                cursor.execute(
                    f"""SELECT sp.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           p.name as product_name,
                           p.name,
                           p.description,
                           p.sku,
                           p.bar_code,
                           p.is_active,
                           l.loc_name as location_name
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sp.created_by = creator.id AND sp.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sp.updated_by = updater.id AND sp.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sp.deleted_by = deleter.id AND sp.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON sp.product_id = p.id 
                        AND sp.tenant_id = p.tenant_id 
                        AND sp.org_id = p.org_id 
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l ON sp.loc_id = l.id AND sp.tenant_id = l.tenant_id
                    WHERE sp.tenant_id = %s AND sp.org_id = %s AND sp.bus_id = %s 
                    AND sp.loc_id = %s AND sp.product_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                sp_with_users = cursor.fetchone()

                if sp_with_users:
                    sp_dict = dict(sp_with_users)
                    sp_dict['created_by'] = sp_dict.get('created_by') or None
                    sp_dict['updated_by'] = sp_dict.get('updated_by') or None
                    sp_dict['deleted_by'] = sp_dict.get('deleted_by') or None
                    sp_dict['product_name'] = sp_dict.get('product_name') or None
                    sp_dict['location_name'] = sp_dict.get('location_name') or None
                    # Product fields
                    sp_dict['name'] = sp_dict.get('name') or ''
                    sp_dict['description'] = sp_dict.get('description') or None
                    sp_dict['sku'] = sp_dict.get('sku') or None
                    sp_dict['bar_code'] = sp_dict.get('bar_code') or None
                    sp_dict['is_active'] = sp_dict.get('is_active', True)
                else:
                    sp_dict = dict(store_product_result)
                    sp_dict['created_by'] = None
                    sp_dict['updated_by'] = None
                    sp_dict['deleted_by'] = None
                    sp_dict['product_name'] = None
                    sp_dict['location_name'] = None
                    # Product fields - need to fetch from product table if store_product_result exists
                    if store_product_result and store_product_result.get('product_id'):
                        cursor.execute(
                            f"""SELECT name, description, sku, bar_code, is_active
                            FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (store_product_result['product_id'], tenant_id, org_id, bus_id),
                        )
                        product = cursor.fetchone()
                        if product:
                            sp_dict['name'] = product.get('name') or ''
                            sp_dict['description'] = product.get('description') or None
                            sp_dict['sku'] = product.get('sku') or None
                            sp_dict['bar_code'] = product.get('bar_code') or None
                            sp_dict['is_active'] = product.get('is_active', True)
                        else:
                            sp_dict['name'] = ''
                            sp_dict['description'] = None
                            sp_dict['sku'] = None
                            sp_dict['bar_code'] = None
                            sp_dict['is_active'] = True
                    else:
                        sp_dict['name'] = ''
                        sp_dict['description'] = None
                        sp_dict['sku'] = None
                        sp_dict['bar_code'] = None
                        sp_dict['is_active'] = True


                sp_read = AddStockStoreProductServiceReadDto(**sp_dict)

                # Log activity
                try:
                    old_data = dict(existing)
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-products",
                        resource_id=sp_dict['id'],
                        action="add_stock",
                        old_data=old_data,
                        new_data=sp_dict,
                        description=f"Added {qty_to_allocate} units to store product {sp_dict['id']}",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Stock added to store product successfully: {sp_dict['id']}",
                    extra={
                        "extra_fields": {
                            "store_product_id": sp_dict['id'],
                            "product_id": data.product_id,
                            "loc_id": loc_id,
                            "qty_added": qty_to_allocate,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail=f"Successfully added {qty_to_allocate} units to store product",
                    data=[sp_read],
                )

        except ValueError as e:
            logger.error(f"Validation error adding stock to store product: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error adding stock to store product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to add stock to store product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_store_product(
        data: UpdateStoreProductServiceWriteDto,
        loc_id: str,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateStoreProductServiceReadDto]:
        """Update a store product"""
        logger.info(
            f"Processing store product update: loc_id={loc_id}, product_id={product_id}",
            extra={
                "extra_fields": {
                    "loc_id": loc_id,
                    "product_id": product_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing store product
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, loc_id, product_id),
                )
                existing_sp = cursor.fetchone()

                if not existing_sp:
                    return Respons(
                        success=False,
                        detail="Store product not found",
                        error="NOT_FOUND",
                    )
                
                old_data = dict(existing_sp)

                # Build update query dynamically
                update_fields = []
                params = []
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.reorder_level is not None:
                    update_fields.append("reorder_level = %s")
                    params.append(data.reorder_level)
                if data.reorder_quantity is not None:
                    update_fields.append("reorder_quantity = %s")
                    params.append(data.reorder_quantity)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                if update_fields:
                    update_fields.append("updated_by = %s")
                    params.extend([updated_by, tenant_id, org_id, bus_id, loc_id, product_id])

                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND product_id = %s""",
                        params,
                    )

                # Get updated store product with user fullnames
                cursor.execute(
                    f"""SELECT sp.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           p.name as product_name,
                           p.name,
                           p.description,
                           p.sku,
                           p.bar_code,
                           p.is_active,
                           l.loc_name as location_name
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sp.created_by = creator.id AND sp.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sp.updated_by = updater.id AND sp.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sp.deleted_by = deleter.id AND sp.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON sp.product_id = p.id 
                        AND sp.tenant_id = p.tenant_id 
                        AND sp.org_id = p.org_id 
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l ON sp.loc_id = l.id AND sp.tenant_id = l.tenant_id
                    WHERE sp.tenant_id = %s AND sp.org_id = %s AND sp.bus_id = %s 
                    AND sp.loc_id = %s AND sp.product_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id, product_id),
                )
                sp_with_users = cursor.fetchone()

                if sp_with_users:
                    sp_dict = dict(sp_with_users)
                    sp_dict['created_by'] = sp_dict.get('created_by') or None
                    sp_dict['updated_by'] = sp_dict.get('updated_by') or None
                    sp_dict['deleted_by'] = sp_dict.get('deleted_by') or None
                    sp_dict['product_name'] = sp_dict.get('product_name') or None
                    sp_dict['location_name'] = sp_dict.get('location_name') or None
                    # Product fields
                    sp_dict['name'] = sp_dict.get('name') or ''
                    sp_dict['description'] = sp_dict.get('description') or None
                    sp_dict['sku'] = sp_dict.get('sku') or None
                    sp_dict['bar_code'] = sp_dict.get('bar_code') or None
                    sp_dict['is_active'] = sp_dict.get('is_active', True)
                else:
                    sp_dict = dict(existing_sp)
                    sp_dict['created_by'] = None
                    sp_dict['updated_by'] = None
                    sp_dict['deleted_by'] = None
                    sp_dict['product_name'] = None
                    sp_dict['location_name'] = None
                    # Product fields - need to fetch from product table if existing_sp exists
                    if existing_sp and existing_sp.get('product_id'):
                        cursor.execute(
                            f"""SELECT name, description, sku, bar_code, is_active
                            FROM {db_settings.MSG_PRODUCTS_TABLE}
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (existing_sp['product_id'], tenant_id, org_id, bus_id),
                        )
                        product = cursor.fetchone()
                        if product:
                            sp_dict['name'] = product.get('name') or ''
                            sp_dict['description'] = product.get('description') or None
                            sp_dict['sku'] = product.get('sku') or None
                            sp_dict['bar_code'] = product.get('bar_code') or None
                            sp_dict['is_active'] = product.get('is_active', True)
                        else:
                            sp_dict['name'] = ''
                            sp_dict['description'] = None
                            sp_dict['sku'] = None
                            sp_dict['bar_code'] = None
                            sp_dict['is_active'] = True
                    else:
                        sp_dict['name'] = ''
                        sp_dict['description'] = None
                        sp_dict['sku'] = None
                        sp_dict['bar_code'] = None
                        sp_dict['is_active'] = True

                # Get metadata for price calculation
                metadata_data = ProductsService._get_product_metadata(
                    cursor=cursor,
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    product_id=product_id
                )
                
                # Calculate prices using PricingCalculator
                product_metadata_for_pricing = {}
                if metadata_data:
                    # Transform metadata to format expected by PricingCalculator
                    for meta in metadata_data:
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
                
                sku = sp_dict.get('sku')
                
                # Price fields from batch (if available)
                sp_dict['cost_price'] = None
                sp_dict['base_selling_price'] = None
                sp_dict['currency_id'] = None
                sp_dict['currency_name'] = None
                sp_dict['currency_symbol'] = None
                
                try:
                    # Step 1: Get actual price (from product_prices or product)
                    actual_price = ProductPriceCalculator.get_actual_price(
                        cursor, product_id, tenant_id, org_id, bus_id,
                        loc_id, sku, product_metadata_for_pricing if product_metadata_for_pricing else None
                    )
                    
                    if actual_price is not None:
                        # Step 2: Apply pricing rules (using quantity 1 for unit price display)
                        pricing_result = ProductPriceCalculator.apply_pricing_rules(
                            cursor, product_id, tenant_id, org_id, bus_id,
                            actual_price, 1,  # quantity = 1 for unit price
                            loc_id, sku, product_metadata_for_pricing if product_metadata_for_pricing else None
                        )
                        price_after_pricing_rule = Decimal(str(pricing_result.get('price', actual_price)))
                        
                        # Step 3: Apply tax rules
                        tax_result = ProductPriceCalculator.apply_tax_rules(
                            cursor, product_id, tenant_id, org_id, bus_id,
                            price_after_pricing_rule, 1, price_after_pricing_rule,  # quantity = 1
                            loc_id, sku, product_metadata_for_pricing if product_metadata_for_pricing else None
                        )
                        
                        # Get final price after tax
                        final_price = Decimal(str(tax_result.get('final_price', price_after_pricing_rule)))
                        
                        # Extract tax information
                        tax_amount = Decimal('0')
                        taxes_applied = []
                        if tax_result.get('taxes_applied'):
                            taxes_applied = tax_result['taxes_applied']
                            for tax in taxes_applied:
                                if tax.get('amount'):
                                    tax_amount += Decimal(str(tax.get('amount', 0)))
                        
                        sp_dict['actual_price'] = float(actual_price)
                        sp_dict['price_after_pricing_rule'] = float(price_after_pricing_rule)
                        sp_dict['price_after_tax'] = float(final_price)
                        sp_dict['tax_amount'] = round(float(tax_amount), 2)
                        sp_dict['final_price'] = float(final_price)
                        sp_dict['taxes_applied'] = taxes_applied
                        sp_dict['pricing_rules_applied'] = pricing_result.get('pricing_rules_applied', [])
                        sp_dict['tax_rules_applied'] = tax_result.get('tax_rules_applied', [])
                    else:
                        # No price available
                        sp_dict['actual_price'] = None
                        sp_dict['price_after_pricing_rule'] = None
                        sp_dict['price_after_tax'] = None
                        sp_dict['tax_amount'] = None
                        sp_dict['final_price'] = None
                        sp_dict['taxes_applied'] = []
                        sp_dict['pricing_rules_applied'] = []
                        sp_dict['tax_rules_applied'] = []
                except Exception as price_err:
                    # If price calculation fails, set to None and log
                    logger.debug(f"Price calculation failed for product {product_id}: {str(price_err)}")
                    sp_dict['actual_price'] = None
                    sp_dict['price_after_pricing_rule'] = None
                    sp_dict['price_after_tax'] = None
                    sp_dict['tax_amount'] = None
                    sp_dict['final_price'] = None
                    sp_dict['taxes_applied'] = []
                    sp_dict['pricing_rules_applied'] = []
                    sp_dict['tax_rules_applied'] = []

                sp_read = UpdateStoreProductServiceReadDto(**sp_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND product_id = %s""",
                        (tenant_id, org_id, bus_id, loc_id, product_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else sp_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-products",
                        resource_id=sp_dict['id'],
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Store product {sp_dict['id']} updated successfully",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Store product updated successfully: {sp_dict['id']}",
                    extra={
                        "extra_fields": {
                            "store_product_id": sp_dict['id'],
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Store product updated successfully",
                    data=[sp_read],
                )

        except Exception as e:
            logger.error(f"Error updating store product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update store product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_store_product(
        loc_id: str,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetStoreProductServiceReadDto]:
        """Get a single store product by location and product ID"""
        logger.info(
            f"Processing get store product request: loc_id={loc_id}, product_id={product_id}",
            extra={
                "extra_fields": {
                    "loc_id": loc_id,
                    "product_id": product_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT sp.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           p.name as product_name,
                           p.name,
                           p.description,
                           p.sku,
                           p.bar_code,
                           p.is_active,
                           l.loc_name as location_name
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sp.created_by = creator.id AND sp.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sp.updated_by = updater.id AND sp.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sp.deleted_by = deleter.id AND sp.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON sp.product_id = p.id 
                        AND sp.tenant_id = p.tenant_id 
                        AND sp.org_id = p.org_id 
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l ON sp.loc_id = l.id AND sp.tenant_id = l.tenant_id
                    WHERE sp.tenant_id = %s AND sp.org_id = %s AND sp.bus_id = %s 
                    AND sp.loc_id = %s AND sp.product_id = %s AND sp.delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, loc_id, product_id),
                )
                sp = cursor.fetchone()

                if not sp:
                    return Respons(
                        success=False,
                        detail="Store product not found",
                        error="NOT_FOUND",
                    )

                sp_dict = dict(sp)
                sp_dict['created_by'] = sp_dict.get('created_by') or None
                sp_dict['updated_by'] = sp_dict.get('updated_by') or None
                sp_dict['deleted_by'] = sp_dict.get('deleted_by') or None
                sp_dict['product_name'] = sp_dict.get('product_name') or None
                sp_dict['location_name'] = sp_dict.get('location_name') or None
                # Product fields
                sp_dict['name'] = sp_dict.get('name') or ''
                sp_dict['description'] = sp_dict.get('description') or None
                sp_dict['sku'] = sp_dict.get('sku') or None
                sp_dict['bar_code'] = sp_dict.get('bar_code') or None
                sp_dict['is_active'] = sp_dict.get('is_active', True)

                # Get metadata for this product
                metadata_data = ProductsService._get_product_metadata(
                    cursor=cursor,
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    product_id=product_id
                )
                sp_dict['metadata'] = [MetadataReadDto(**meta) for meta in metadata_data] if metadata_data else []

                # Get documents for this product
                sp_dict['documents'] = StoreProductsService._get_store_product_documents(
                    cursor=cursor,
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    product_id=product_id
                )

                # Get batches for this store product
                batches_data = StoreProductsService._get_store_product_batches(
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    loc_id=loc_id,
                    product_id=product_id,
                    cursor=cursor
                )

                # Format batches with movements nested inside each batch
                batches_list = []
                # Note: remaining_qty_total will be set from sp_dict['current_qty'] which is the total quantity at this location
                for batch_loc in batches_data:
                    batch_dict = dict(batch_loc)
                    batch_dict['batch_number'] = batch_dict.get('batch_number') or None
                    
                    # Get the quantity allocated to THIS store location (from batch_locations table)
                    qty_at_location = batch_dict.get('qty', 0)  # This is bl.qty from batch_locations
                    
                    # Get movements for this specific batch
                    batch_id = batch_dict.get('purchase_batche_id')
                    movements_data = []
                    if batch_id:
                        movements_data = StoreProductsService._get_batch_movements(
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            batch_id=batch_id,
                            loc_id=loc_id,
                            cursor=cursor
                        )
                    
                    # Format movements for this batch
                    movements_list = []
                    for movement in movements_data:
                        mov_dict = dict(movement)
                        mov_dict['batch_id'] = mov_dict.get('batch_id') or None
                        mov_dict['batch_number'] = mov_dict.get('batch_number') or None
                        mov_dict['reason'] = mov_dict.get('reason') or None
                        mov_dict['reference_id'] = mov_dict.get('reference_id') or None
                        mov_dict['cdate'] = mov_dict.get('cdate') or None
                        mov_dict['ctime'] = mov_dict.get('ctime') or None
                        mov_dict['cdatetime'] = mov_dict.get('cdatetime')
                        mov_dict['created_by'] = mov_dict.get('created_by') or None
                        mov_dict['updated_by'] = mov_dict.get('updated_by') or None
                        mov_dict['deleted_by'] = mov_dict.get('deleted_by') or None
                        mov_dict['product_name'] = mov_dict.get('product_name') or None
                        mov_dict['location_name'] = mov_dict.get('location_name') or None
                        mov_dict['created_by_name'] = mov_dict.get('created_by_name') or None
                        mov_dict['updated_by_name'] = mov_dict.get('updated_by_name') or None
                        mov_dict['deleted_by_name'] = mov_dict.get('deleted_by_name') or None
                        movements_list.append(ProductMovementReadDto(**mov_dict))
                    
                    # Create PurchaseBatchReadDto with movements
                    if batch_dict.get('purchase_batche_id'):
                        batch_id = batch_dict['purchase_batche_id']
                        batch_status = batch_dict.get('batch_status') or 'RECEIVED'
                        
                        # Calculate total remaining quantity across all locations by summing qty from batch_locations
                        # This is more accurate than using qty_remaining from purchase_batches
                        cursor.execute(
                            f"""SELECT COALESCE(SUM(qty), 0) as total_qty
                            FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND purchase_batche_id = %s""",
                            (tenant_id, org_id, bus_id, batch_id),
                        )
                        total_remaining_result = cursor.fetchone()
                        total_remaining_across_locations = int(total_remaining_result['total_qty']) if total_remaining_result and total_remaining_result.get('total_qty') else batch_dict.get('qty_remaining', 0)
                        
                        # Convert date objects to strings for product_expiry_date
                        from datetime import date
                        product_expiry_date = batch_dict.get('product_expiry_date')
                        if product_expiry_date and isinstance(product_expiry_date, date):
                            product_expiry_date = product_expiry_date.isoformat()
                        
                        batch_details_dict = {
                            'id': batch_id,
                            'tenant_id': tenant_id,
                            'org_id': org_id,
                            'bus_id': bus_id,
                            'product_id': product_id,
                            'supplier_id': batch_dict.get('supplier_id'),
                            'batch_number': batch_dict.get('batch_number'),
                            'currency_id': batch_dict.get('currency_id'),
                            'cost_price': float(batch_dict.get('cost_price', 0)) if batch_dict.get('cost_price') else 0,
                            'base_selling_price': float(batch_dict.get('base_selling_price', 0)) if batch_dict.get('base_selling_price') else 0,
                            'unit_of_measure_id': batch_dict.get('unit_of_measure_id'),
                            'qty_received': batch_dict.get('qty_received', 0),
                            'qty_remaining': None,  # Not used for store products
                            'specific_product_per_batch_received_qty': int(qty_at_location) if qty_at_location else None,  # Use qty_at_location
                            'specific_product_per_batch_remaining_qty': int(qty_at_location) if qty_at_location else None,  # Use same value as received_qty
                            'qty_at_location': int(qty_at_location) if qty_at_location else None,  # Quantity at THIS store location
                            'product_expiry_date': product_expiry_date,
                            'status': batch_status,
                            'product_size': batch_dict.get('product_size'),
                            'delete_status': batch_dict.get('batch_delete_status', 'NOT_DELETED'),
                            'is_active': batch_dict.get('batch_is_active', True),
                            'cdate': batch_dict.get('batch_cdate', ''),
                            'ctime': batch_dict.get('batch_ctime', ''),
                            'cdatetime': batch_dict.get('batch_cdatetime'),
                            'created_by': batch_dict.get('batch_created_by'),
                            'updated_by': batch_dict.get('batch_updated_by'),
                            'deleted_by': batch_dict.get('batch_deleted_by'),
                            'batch_type': batch_dict.get('batch_type', 'OPENING_STOCK'),
                            'currency_name': batch_dict.get('currency_name'),
                            'unit_of_measure_name': batch_dict.get('unit_of_measure_name'),
                            'supplier_name': batch_dict.get('supplier_name'),
                            'movements': movements_list if movements_list else None,
                        }
                        try:
                            batch_details = PurchaseBatchReadDto(**batch_details_dict)
                            batches_list.append(batch_details)
                        except Exception as e:
                            logger.warning(f"Error creating batch details: {e}", exc_info=True)

                sp_dict['batches'] = batches_list if batches_list else None
                # Use current_qty from store_products table (total quantity at this location)
                # This should equal the sum of all qty_at_location values from batches
                sp_dict['remaining_qty'] = sp_dict.get('current_qty', 0)
                # Calculate specific_product_all_batch_remaining_qty (sum of qty_at_location from all active batches)
                sp_dict['specific_product_all_batch_remaining_qty'] = sum(
                    int(batch.qty_at_location) if batch.qty_at_location is not None else 0 
                    for batch in batches_list 
                    if batch.status not in ('VOID', 'CANCELLED')
                ) if batches_list else 0

                # Get latest batch for cost_price and base_selling_price
                from datetime import datetime
                latest_batch = None
                if batches_data:
                    # Sort by batch cdatetime DESC to get latest
                    sorted_batches = sorted(batches_data, key=lambda x: x.get('batch_cdatetime') or datetime.min, reverse=True)
                    latest_batch = sorted_batches[0] if sorted_batches else None
                
                if latest_batch:
                    sp_dict['cost_price'] = float(latest_batch.get('cost_price')) if latest_batch.get('cost_price') is not None else None
                    sp_dict['base_selling_price'] = float(latest_batch.get('base_selling_price')) if latest_batch.get('base_selling_price') is not None else None
                    sp_dict['currency_id'] = latest_batch.get('currency_id')
                    sp_dict['currency_name'] = latest_batch.get('currency_name')
                    sp_dict['currency_symbol'] = latest_batch.get('currency_symbol')
                else:
                    sp_dict['cost_price'] = None
                    sp_dict['base_selling_price'] = None
                    sp_dict['currency_id'] = None
                    sp_dict['currency_name'] = None
                    sp_dict['currency_symbol'] = None
                
                # Calculate prices using PricingCalculator
                product_metadata_for_pricing = {}
                if metadata_data:
                    # Transform metadata to format expected by PricingCalculator
                    for meta in metadata_data:
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
                
                sku = sp_dict.get('sku')
                
                try:
                    # Calculate prices using ProductPriceCalculator (SIMPLE TAX - NO CONDITIONS)
                    prices = ProductPriceCalculator.calculate_product_prices(
                        cursor, product_id, tenant_id, org_id, bus_id,
                        quantity=1,  # quantity = 1 for unit price display
                        location_id=loc_id,
                        sku=sku,
                        product_metadata=product_metadata_for_pricing if product_metadata_for_pricing else None
                    )
                    
                    sp_dict['actual_price'] = prices.get('actual_price')
                    sp_dict['price_after_pricing_rule'] = prices.get('price_after_pricing_rule')
                    sp_dict['price_after_tax'] = prices.get('price_after_tax')
                    sp_dict['tax_amount'] = prices.get('tax_amount')
                    sp_dict['final_price'] = prices.get('final_price')
                    sp_dict['taxes_applied'] = prices.get('taxes_applied', [])
                    sp_dict['pricing_rules_applied'] = prices.get('pricing_rules_applied', [])
                    sp_dict['tax_rules_applied'] = prices.get('tax_rules_applied', [])
                except Exception as price_err:
                    # If price calculation fails, set to None and log
                    logger.debug(f"Price calculation failed for product {product_id}: {str(price_err)}")
                    sp_dict['actual_price'] = None
                    sp_dict['price_after_pricing_rule'] = None
                    sp_dict['price_after_tax'] = None
                    sp_dict['tax_amount'] = None
                    sp_dict['final_price'] = None
                    sp_dict['taxes_applied'] = []
                    sp_dict['pricing_rules_applied'] = []
                    sp_dict['tax_rules_applied'] = []

                sp_read = GetStoreProductServiceReadDto(**sp_dict)

                return Respons(
                    success=True,
                    detail="Store product retrieved successfully",
                    data=[sp_read],
                )

        except Exception as e:
            logger.error(f"Error getting store product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get store product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_store_products(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: Optional[str] = None,
        product_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        metadata_ids: Optional[List[str]] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetStoreProductsServiceReadDto]]:
        """Get list of store products with pagination"""
        logger.info(
            f"Processing get store products request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "loc_id": loc_id,
                    "product_id": product_id,
                    "is_active": is_active,
                    "search": search,
                    "metadata_ids": metadata_ids,
                    "page": page,
                    "size": size,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "sp.tenant_id = %s",
                    "sp.org_id = %s",
                    "sp.bus_id = %s",
                    "sp.delete_status = 'NOT_DELETED'"
                ]
                params = [tenant_id, org_id, bus_id]

                if loc_id:
                    where_conditions.append("sp.loc_id = %s")
                    params.append(loc_id)

                if product_id:
                    where_conditions.append("sp.product_id = %s")
                    params.append(product_id)

                if is_active is not None:
                    where_conditions.append("sp.is_active = %s")
                    params.append(is_active)

                if search:
                    where_conditions.append(
                        "(p.name ILIKE %s OR l.loc_name ILIKE %s OR p.bar_code ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern, search_pattern])

                if metadata_ids:
                    placeholders = ", ".join(["%s"] * len(metadata_ids))
                    where_conditions.append(
                        f"""EXISTS (
                            SELECT 1 FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                            WHERE amp.product_id = sp.product_id AND amp.tenant_id = sp.tenant_id
                            AND amp.org_id = sp.org_id AND amp.bus_id = sp.bus_id
                            AND amp.product_metadata_id IN ({placeholders})
                        )"""
                    )
                    params.extend(metadata_ids)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"""SELECT COUNT(*) as total FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON sp.product_id = p.id 
                        AND sp.tenant_id = p.tenant_id 
                        AND sp.org_id = p.org_id 
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l ON sp.loc_id = l.id AND sp.tenant_id = l.tenant_id
                    WHERE {where_clause}""",
                    params,
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                pagination_meta = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total
                )

                # Get store products with user fullnames
                cursor.execute(
                    f"""SELECT sp.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           p.name as product_name,
                           p.name,
                           p.description,
                           p.sku,
                           p.bar_code,
                           p.is_active,
                           l.loc_name as location_name
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON sp.created_by = creator.id AND sp.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON sp.updated_by = updater.id AND sp.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON sp.deleted_by = deleter.id AND sp.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON sp.product_id = p.id 
                        AND sp.tenant_id = p.tenant_id 
                        AND sp.org_id = p.org_id 
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l ON sp.loc_id = l.id AND sp.tenant_id = l.tenant_id
                    WHERE {where_clause}
                    ORDER BY sp.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    params + [size, offset],
                )
                store_products = cursor.fetchall()

                sp_list = []
                for sp in store_products:
                    sp_dict = dict(sp)
                    sp_dict['created_by'] = sp_dict.get('created_by') or None
                    sp_dict['updated_by'] = sp_dict.get('updated_by') or None
                    sp_dict['deleted_by'] = sp_dict.get('deleted_by') or None
                    sp_dict['product_name'] = sp_dict.get('product_name') or None
                    sp_dict['location_name'] = sp_dict.get('location_name') or None
                    # Product fields
                    sp_dict['name'] = sp_dict.get('name') or ''
                    sp_dict['description'] = sp_dict.get('description') or None
                    sp_dict['sku'] = sp_dict.get('sku') or None
                    sp_dict['bar_code'] = sp_dict.get('bar_code') or None
                    sp_dict['is_active'] = sp_dict.get('is_active', True)

                    # Get metadata for this product
                    metadata_data = ProductsService._get_product_metadata(
                        cursor=cursor,
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        product_id=sp_dict['product_id']
                    )
                    sp_dict['metadata'] = [MetadataReadDto(**meta) for meta in metadata_data] if metadata_data else []

                    # Get documents for this product
                    sp_dict['documents'] = StoreProductsService._get_store_product_documents(
                        cursor=cursor,
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        product_id=sp_dict['product_id']
                    )

                    # Get batches for this store product
                    batches_data = StoreProductsService._get_store_product_batches(
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=sp_dict['loc_id'],
                        product_id=sp_dict['product_id'],
                        cursor=cursor
                    )

                    # Format batches with movements nested inside each batch
                    batches_list = []
                    remaining_qty_total = 0
                    for batch_loc in batches_data:
                        batch_dict = dict(batch_loc)
                        batch_dict['batch_number'] = batch_dict.get('batch_number') or None
                        
                        # Get movements for this specific batch
                        batch_id = batch_dict.get('purchase_batche_id')
                        movements_data = []
                        if batch_id:
                            movements_data = StoreProductsService._get_batch_movements(
                                tenant_id=tenant_id,
                                org_id=org_id,
                                bus_id=bus_id,
                                batch_id=batch_id,
                                loc_id=sp_dict['loc_id'],
                                cursor=cursor
                            )
                        
                        # Format movements for this batch
                        movements_list = []
                        for movement in movements_data:
                            mov_dict = dict(movement)
                            mov_dict['batch_id'] = mov_dict.get('batch_id') or None
                            mov_dict['batch_number'] = mov_dict.get('batch_number') or None
                            mov_dict['reason'] = mov_dict.get('reason') or None
                            mov_dict['reference_id'] = mov_dict.get('reference_id') or None
                            mov_dict['cdate'] = mov_dict.get('cdate') or None
                            mov_dict['ctime'] = mov_dict.get('ctime') or None
                            mov_dict['cdatetime'] = mov_dict.get('cdatetime')
                            mov_dict['created_by'] = mov_dict.get('created_by') or None
                            mov_dict['updated_by'] = mov_dict.get('updated_by') or None
                            mov_dict['deleted_by'] = mov_dict.get('deleted_by') or None
                            mov_dict['product_name'] = mov_dict.get('product_name') or None
                            mov_dict['location_name'] = mov_dict.get('location_name') or None
                            mov_dict['created_by_name'] = mov_dict.get('created_by_name') or None
                            mov_dict['updated_by_name'] = mov_dict.get('updated_by_name') or None
                            mov_dict['deleted_by_name'] = mov_dict.get('deleted_by_name') or None
                            movements_list.append(ProductMovementReadDto(**mov_dict))
                        
                        # Create PurchaseBatchReadDto with movements
                        if batch_dict.get('purchase_batche_id'):
                            batch_status = batch_dict.get('batch_status') or 'RECEIVED'
                            
                            # Get the quantity allocated to THIS store location (from batch_locations table)
                            qty_at_location = batch_dict.get('qty', 0)  # This is bl.qty from batch_locations
                            
                            # Only count non-VOID and non-CANCELLED batches for remaining_qty
                            if batch_status not in ('VOID', 'CANCELLED'):
                                remaining_qty_total += int(qty_at_location) if qty_at_location else 0
                            
                            # Convert date objects to strings for product_expiry_date
                            from datetime import date
                            product_expiry_date = batch_dict.get('product_expiry_date')
                            if product_expiry_date and isinstance(product_expiry_date, date):
                                product_expiry_date = product_expiry_date.isoformat()
                            
                            batch_details_dict = {
                                'id': batch_dict['purchase_batche_id'],
                                'tenant_id': tenant_id,
                                'org_id': org_id,
                                'bus_id': bus_id,
                                'product_id': sp_dict['product_id'],
                                'supplier_id': batch_dict.get('supplier_id'),
                                'batch_number': batch_dict.get('batch_number'),
                                'currency_id': batch_dict.get('currency_id'),
                                'cost_price': float(batch_dict.get('cost_price', 0)) if batch_dict.get('cost_price') else 0,
                                'base_selling_price': float(batch_dict.get('base_selling_price', 0)) if batch_dict.get('base_selling_price') else 0,
                                'unit_of_measure_id': batch_dict.get('unit_of_measure_id'),
                                'qty_received': batch_dict.get('qty_received', 0),
                                'qty_remaining': None,  # Not used for store products
                                'specific_product_per_batch_received_qty': int(qty_at_location) if qty_at_location else None,  # Use qty_at_location
                                'specific_product_per_batch_remaining_qty': int(qty_at_location) if qty_at_location else None,  # Use same value as received_qty
                                'qty_at_location': int(qty_at_location) if qty_at_location else None,  # Quantity at THIS store location
                                'product_expiry_date': product_expiry_date,
                                'status': batch_status,
                                'delete_status': batch_dict.get('batch_delete_status', 'NOT_DELETED'),
                                'is_active': batch_dict.get('batch_is_active', True),
                                'created_at': batch_dict.get('batch_created_at'),
                                'updated_at': batch_dict.get('batch_updated_at'),
                                'created_by': batch_dict.get('batch_created_by'),
                                'updated_by': batch_dict.get('batch_updated_by'),
                                'deleted_by': batch_dict.get('batch_deleted_by'),
                                'batch_type': batch_dict.get('batch_type', 'OPENING_STOCK'),
                                'currency_name': batch_dict.get('currency_name'),
                                'unit_of_measure_name': batch_dict.get('unit_of_measure_name'),
                                'supplier_name': batch_dict.get('supplier_name'),
                                'movements': movements_list if movements_list else None,
                                'cdate': batch_dict.get('batch_cdate', ''),
                                'ctime': batch_dict.get('batch_ctime', ''),
                                'cdatetime': batch_dict.get('batch_cdatetime'),
                            }
                            try:
                                batch_details = PurchaseBatchReadDto(**batch_details_dict)
                                batches_list.append(batch_details)
                            except Exception as e:
                                logger.warning(f"Error creating batch details: {e}", exc_info=True)

                    sp_dict['batches'] = batches_list if batches_list else None
                    sp_dict['remaining_qty'] = remaining_qty_total
                    # Calculate specific_product_all_batch_remaining_qty (sum of qty_at_location from all active batches)
                    sp_dict['specific_product_all_batch_remaining_qty'] = sum(
                        int(batch.qty_at_location) if batch.qty_at_location else 0 
                        for batch in batches_list 
                        if batch.status not in ('VOID', 'CANCELLED')
                    ) if batches_list else 0

                    # Get latest batch for cost_price and base_selling_price
                    from datetime import datetime
                    latest_batch = None
                    if batches_data:
                        # Sort by batch cdatetime DESC to get latest
                        sorted_batches = sorted(batches_data, key=lambda x: x.get('batch_cdatetime') or datetime.min, reverse=True)
                        latest_batch = sorted_batches[0] if sorted_batches else None
                    
                    if latest_batch:
                        sp_dict['cost_price'] = float(latest_batch.get('cost_price')) if latest_batch.get('cost_price') is not None else None
                        sp_dict['base_selling_price'] = float(latest_batch.get('base_selling_price')) if latest_batch.get('base_selling_price') is not None else None
                        sp_dict['currency_id'] = latest_batch.get('currency_id')
                        sp_dict['currency_name'] = latest_batch.get('currency_name')
                        sp_dict['currency_symbol'] = latest_batch.get('currency_symbol')
                    else:
                        sp_dict['cost_price'] = None
                        sp_dict['base_selling_price'] = None
                        sp_dict['currency_id'] = None
                        sp_dict['currency_name'] = None
                        sp_dict['currency_symbol'] = None
                    
                    # Calculate prices using PricingCalculator
                    product_metadata_for_pricing = {}
                    if metadata_data:
                        # Transform metadata to format expected by PricingCalculator
                        for meta in metadata_data:
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
                    
                    sku = sp_dict.get('sku')
                    
                    try:
                        # Calculate prices using ProductPriceCalculator (SIMPLE TAX - NO CONDITIONS)
                        prices = ProductPriceCalculator.calculate_product_prices(
                            cursor, sp_dict['product_id'], tenant_id, org_id, bus_id,
                            quantity=1,  # quantity = 1 for unit price display
                            location_id=sp_dict['loc_id'],
                            sku=sku,
                            product_metadata=product_metadata_for_pricing if product_metadata_for_pricing else None
                        )
                        
                        sp_dict['actual_price'] = prices.get('actual_price')
                        sp_dict['price_after_pricing_rule'] = prices.get('price_after_pricing_rule')
                        sp_dict['price_after_tax'] = None  # No tax for store products
                        sp_dict['tax_amount'] = None  # No tax for store products
                        sp_dict['final_price'] = prices.get('final_price')  # Same as price_after_pricing_rule
                        sp_dict['taxes_applied'] = []  # No tax for store products
                        sp_dict['pricing_rules_applied'] = prices.get('pricing_rules_applied', [])
                        sp_dict['tax_rules_applied'] = []  # No tax for store products
                    except Exception as price_err:
                        # If price calculation fails, set to None and log
                        logger.debug(f"Price calculation failed for product {sp_dict['product_id']}: {str(price_err)}")
                        sp_dict['actual_price'] = None
                        sp_dict['price_after_pricing_rule'] = None
                        sp_dict['price_after_tax'] = None
                        sp_dict['tax_amount'] = None
                        sp_dict['final_price'] = None
                        sp_dict['taxes_applied'] = []
                        sp_dict['pricing_rules_applied'] = []
                        sp_dict['tax_rules_applied'] = []

                    sp_list.append(GetStoreProductsServiceReadDto(**sp_dict))

                return Respons(
                    success=True,
                    detail="Store products retrieved successfully",
                    data=sp_list,
                    pagination=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting store products: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get store products: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_store_product(
        data: DeleteStoreProductServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteStoreProductServiceReadDto]:
        """Delete a store product"""
        logger.info(
            f"Processing store product deletion: loc_id={data.loc_id}, product_id={data.product_id}",
            extra={
                "extra_fields": {
                    "loc_id": data.loc_id,
                    "product_id": data.product_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if store product exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.loc_id, data.product_id),
                )
                existing_sp = cursor.fetchone()

                if not existing_sp:
                    return Respons(
                        success=False,
                        detail="Store product not found",
                        error="NOT_FOUND",
                    )

                # Get all batch_locations for this product at this location
                cursor.execute(
                    f"""SELECT purchase_batche_id, qty FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND location_type = 'STORE'
                    AND purchase_batche_id IN (
                        SELECT id FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s
                    )""",
                    (tenant_id, org_id, bus_id, data.loc_id, tenant_id, org_id, bus_id, data.product_id),
                )
                batch_locations = cursor.fetchall()

                # Delete all batch_locations for this product at this location
                deleted_batch_locations_count = 0
                if batch_locations:
                    # Get batch IDs to restore qty_remaining
                    batch_ids = [bl['purchase_batche_id'] for bl in batch_locations]
                    batch_qtys = {bl['purchase_batche_id']: bl['qty'] for bl in batch_locations}
                    
                    # Delete batch_locations
                    placeholders = ','.join(['%s'] * len(batch_ids))
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND location_type = 'STORE'
                        AND purchase_batche_id IN ({placeholders})""",
                        (tenant_id, org_id, bus_id, data.loc_id, *batch_ids),
                    )
                    deleted_batch_locations_count = cursor.rowcount
                    
                    # Restore qty_remaining in purchase batches
                    for batch_id, qty in batch_qtys.items():
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                            SET qty_remaining = qty_remaining + %s, updated_by = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (qty, deleted_by, batch_id, tenant_id, org_id, bus_id),
                        )

                # Delete all movements (both IN and OUT) for this product at this location
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND product_id = %s AND location_type = 'STORE' 
                    AND location_id = %s""",
                    (tenant_id, org_id, bus_id, data.product_id, data.loc_id),
                )
                deleted_movements_count = cursor.rowcount

                # Soft delete store product
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    SET delete_status = 'DELETED', deleted_by = %s, updated_by = %s
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s""",
                    (deleted_by, deleted_by, tenant_id, org_id, bus_id, data.loc_id, data.product_id),
                )

                # Log activity
                try:
                    old_data = dict(existing_sp)
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-products",
                        resource_id=old_data.get('id', ''),
                        action="delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Store product deleted successfully",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Store product deleted successfully: loc_id={data.loc_id}, product_id={data.product_id}. "
                    f"Deleted {deleted_batch_locations_count} batch location(s) and {deleted_movements_count} movement(s) (IN and OUT).",
                    extra={
                        "extra_fields": {
                            "loc_id": data.loc_id,
                            "product_id": data.product_id,
                            "deleted_batch_locations_count": deleted_batch_locations_count,
                            "deleted_movements_count": deleted_movements_count,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Store product deleted successfully",
                    data=[DeleteStoreProductServiceReadDto(
                        loc_id=data.loc_id,
                        product_id=data.product_id,
                        message="Store product deleted successfully"
                    )],
                )

        except Exception as e:
            logger.error(f"Error deleting store product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete store product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def permanent_delete_store_product(
        data: PermanentDeleteStoreProductServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        deleted_by: str
    ) -> Respons[PermanentDeleteStoreProductServiceReadDto]:
        """Permanently delete a store product from the database"""
        logger.info(
            f"Processing permanent delete store product: loc_id={loc_id}, product_id={data.product_id}",
            extra={
                "extra_fields": {
                    "loc_id": loc_id,
                    "product_id": data.product_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if store product exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                existing_sp = cursor.fetchone()

                if not existing_sp:
                    return Respons(
                        success=False,
                        detail="Store product not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_sp)

                # Get all batch_locations for this product at this location
                cursor.execute(
                    f"""SELECT purchase_batche_id, qty FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND location_type = 'STORE'
                    AND purchase_batche_id IN (
                        SELECT id FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s
                    )""",
                    (tenant_id, org_id, bus_id, loc_id, tenant_id, org_id, bus_id, data.product_id),
                )
                batch_locations = cursor.fetchall()

                # Delete all batch_locations for this product at this location
                deleted_batch_locations_count = 0
                if batch_locations:
                    # Get batch IDs to restore qty_remaining
                    batch_ids = [bl['purchase_batche_id'] for bl in batch_locations]
                    batch_qtys = {bl['purchase_batche_id']: bl['qty'] for bl in batch_locations}
                    
                    # Delete batch_locations
                    placeholders = ','.join(['%s'] * len(batch_ids))
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND loc_id = %s AND location_type = 'STORE'
                        AND purchase_batche_id IN ({placeholders})""",
                        (tenant_id, org_id, bus_id, loc_id, *batch_ids),
                    )
                    deleted_batch_locations_count = cursor.rowcount
                    
                    # Restore qty_remaining in purchase batches
                    for batch_id, qty in batch_qtys.items():
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                            SET qty_remaining = qty_remaining + %s, updated_by = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (qty, deleted_by, batch_id, tenant_id, org_id, bus_id),
                        )

                # Delete all movements (both IN and OUT) for this product at this location
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND product_id = %s AND location_type = 'STORE' 
                    AND location_id = %s""",
                    (tenant_id, org_id, bus_id, data.product_id, loc_id),
                )
                deleted_movements_count = cursor.rowcount

                # Permanently delete the store product
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Failed to permanently delete store product")

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-products",
                        resource_id=old_data.get('id', ''),
                        action="permanent_delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Store product permanently deleted from location {loc_id}",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Store product permanently deleted successfully: loc_id={loc_id}, product_id={data.product_id}. "
                    f"Deleted {deleted_batch_locations_count} batch location(s) and {deleted_movements_count} movement(s) (IN and OUT).",
                    extra={
                        "extra_fields": {
                            "loc_id": loc_id,
                            "product_id": data.product_id,
                            "deleted_batch_locations_count": deleted_batch_locations_count,
                            "deleted_movements_count": deleted_movements_count,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Store product permanently deleted successfully",
                    data=[PermanentDeleteStoreProductServiceReadDto(
                        loc_id=loc_id,
                        product_id=data.product_id,
                        message="Store product permanently deleted successfully"
                    )],
                )

        except Exception as e:
            logger.error(f"Error permanently deleting store product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to permanently delete store product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def reverse_batch_store_product(
        data: ReverseBatchStoreProductServiceWriteDto,
        loc_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[ReverseBatchStoreProductServiceReadDto]:
        """Reverse a batch allocation from a store product by removing batch_location and restoring batch qty_remaining"""
        logger.info(
            f"Processing reverse batch for store product: loc_id={loc_id}, product_id={data.product_id}, batch_number={data.batch_number}",
            extra={
                "extra_fields": {
                    "loc_id": loc_id,
                    "product_id": data.product_id,
                    "batch_number": data.batch_number,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Find the batch by batch_number
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND batch_number = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.batch_number),
                )
                batch = cursor.fetchone()

                if not batch:
                    return Respons(
                        success=False,
                        detail=f"Batch with batch_number '{data.batch_number}' not found",
                        error="NOT_FOUND",
                    )

                batch_id = batch['id']
                batch_dict = dict(batch)

                # Find the batch_location record
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND purchase_batche_id = %s AND location_type = 'STORE'""",
                    (tenant_id, org_id, bus_id, loc_id, batch_id),
                )
                batch_location = cursor.fetchone()

                if not batch_location:
                    return Respons(
                        success=False,
                        detail=f"Batch '{data.batch_number}' is not allocated to this store location",
                        error="NOT_FOUND",
                    )

                batch_location_dict = dict(batch_location)
                qty_to_reverse = batch_location_dict.get('qty', 0)

                if qty_to_reverse <= 0:
                    return Respons(
                        success=False,
                        detail=f"Batch '{data.batch_number}' has no quantity allocated to reverse",
                        error="INVALID_QUANTITY",
                    )

                # Get current store product
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, loc_id, data.product_id),
                )
                store_product = cursor.fetchone()

                if not store_product:
                    return Respons(
                        success=False,
                        detail="Store product not found",
                        error="NOT_FOUND",
                    )

                store_product_dict = dict(store_product)
                current_qty = store_product_dict.get('current_qty', 0)

                # Validate that we're not reversing more than available
                if qty_to_reverse > current_qty:
                    return Respons(
                        success=False,
                        detail=f"Cannot reverse {qty_to_reverse} units. Store product only has {current_qty} units",
                        error="INSUFFICIENT_QUANTITY",
                    )

                # Get all affected store/warehouse products BEFORE deleting batch_locations
                # This allows us to update their quantities after reversal
                cursor.execute(
                    f"""SELECT bl.loc_id, bl.location_type, bl.qty, sp.product_id, sp.current_qty, sp.id as product_record_id, 'STORE' as table_type
                    FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                    INNER JOIN {db_settings.MSG_STORE_PRODUCTS_TABLE} sp 
                        ON bl.loc_id = sp.loc_id 
                        AND bl.tenant_id = sp.tenant_id 
                        AND bl.org_id = sp.org_id 
                        AND bl.bus_id = sp.bus_id
                    WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s 
                    AND bl.purchase_batche_id = %s AND bl.location_type = 'STORE'
                    AND sp.delete_status = 'NOT_DELETED'
                    UNION ALL
                    SELECT bl.loc_id, bl.location_type, bl.qty, wp.product_id, wp.current_qty, wp.id as product_record_id, 'WAREHOUSE' as table_type
                    FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                    INNER JOIN {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE} wp 
                        ON bl.loc_id = wp.loc_id 
                        AND bl.tenant_id = wp.tenant_id 
                        AND bl.org_id = wp.org_id 
                        AND bl.bus_id = wp.bus_id
                    WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s 
                    AND bl.purchase_batche_id = %s AND bl.location_type = 'WAREHOUSE'
                    AND wp.delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, batch_id, tenant_id, org_id, bus_id, batch_id),
                )
                affected_products = cursor.fetchall()

                # Delete ALL batch_location records for this batch (across all locations)
                # This ensures the batch is completely reversed from all store and warehouse locations
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND purchase_batche_id = %s""",
                    (tenant_id, org_id, bus_id, batch_id),
                )
                deleted_locations_count = cursor.rowcount

                # Update batch: set remaining_qty to 0 and status to VOID (same as products reverse_batch)
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    SET qty_remaining = %s, status = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (0, 'VOID', updated_by, batch_id, tenant_id, org_id, bus_id),
                )

                # Update all affected store/warehouse products - reduce their current_qty by the allocated quantity
                for affected in affected_products:
                    affected_dict = dict(affected)
                    allocated_qty = affected_dict.get('qty', 0)
                    current_product_qty = affected_dict.get('current_qty', 0)
                    product_record_id = affected_dict.get('product_record_id')
                    table_type = affected_dict.get('table_type')
                    
                    new_product_qty = current_product_qty - allocated_qty
                    if new_product_qty < 0:
                        new_product_qty = 0
                    
                    if table_type == 'STORE':
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                            SET current_qty = %s, updated_by = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (new_product_qty, updated_by, product_record_id, tenant_id, org_id, bus_id),
                        )
                    else:  # WAREHOUSE
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE}
                            SET current_qty = %s, updated_by = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (new_product_qty, updated_by, product_record_id, tenant_id, org_id, bus_id),
                        )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-products",
                        resource_id=store_product_dict['id'],
                        action="reverse_batch",
                        old_data={
                            **store_product_dict,
                            "batch_location_qty": qty_to_reverse,
                            "batch_qty_remaining": batch_dict.get('qty_remaining', 0),
                            "batch_status": batch_dict.get('status'),
                            "deleted_locations_count": deleted_locations_count,
                        },
                        new_data={
                            **store_product_dict,
                            "current_qty": store_product_dict.get('current_qty', 0) - qty_to_reverse if store_product_dict.get('current_qty', 0) - qty_to_reverse >= 0 else 0,
                            "batch_qty_remaining": 0,
                            "batch_status": "VOID",
                        },
                        description=f"Batch {data.batch_number} reversed (qty_remaining set to 0, status set to VOID). {deleted_locations_count} location(s) affected.",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Batch reversed successfully for store product: batch_number={data.batch_number}, qty_reversed={qty_to_reverse}",
                    extra={
                        "extra_fields": {
                            "loc_id": loc_id,
                            "product_id": data.product_id,
                            "batch_number": data.batch_number,
                            "qty_reversed": qty_to_reverse,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail=f"Batch {data.batch_number} reversed successfully (qty_remaining set to 0, status set to VOID). {deleted_locations_count} location(s) affected.",
                    data=[ReverseBatchStoreProductServiceReadDto(
                        loc_id=loc_id,
                        product_id=data.product_id,
                        batch_number=data.batch_number,
                        qty_reversed=qty_to_reverse,
                        message=f"Batch {data.batch_number} reversed successfully (qty_remaining set to 0, status set to VOID). {deleted_locations_count} location(s) affected."
                    )],
                )

        except ValueError as e:
            logger.error(f"Validation error reversing batch: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error reversing batch: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to reverse batch: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_store_product_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetStoreProductStatisticsServiceReadDto]:
        """Get store product statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "tenant_id = %s",
                    "org_id = %s",
                    "bus_id = %s",
                    "loc_id = %s",
                    "delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]
                where_clause = " AND ".join(where_conditions)

                # Get statistics
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_products,
                        COALESCE(SUM(current_qty), 0) as total_quantity,
                        SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active_products,
                        SUM(CASE WHEN current_qty <= reorder_level AND reorder_level > 0 THEN 1 ELSE 0 END) as low_stock_products,
                        SUM(CASE WHEN current_qty = 0 THEN 1 ELSE 0 END) as out_of_stock_products,
                        CASE 
                            WHEN COUNT(*) > 0 THEN COALESCE(AVG(current_qty), 0)
                            ELSE 0
                        END as average_quantity,
                        SUM(CASE WHEN current_qty <= reorder_level AND reorder_level > 0 THEN 1 ELSE 0 END) as products_needing_reorder,
                        SUM(CASE WHEN current_qty > reorder_level OR reorder_level = 0 THEN 1 ELSE 0 END) as well_stocked_products
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE {where_clause}""",
                    tuple(params),
                )
                stats_row = cursor.fetchone()

                # Handle None case
                if stats_row is None:
                    logger.warning("Statistics query returned no rows - using default values")
                    stats_row = {}

                # Extract values - handle None values from database
                # Round decimal values to 2 decimal places
                from decimal import ROUND_HALF_UP
                two_places = Decimal('0.01')
                
                total_products = int(stats_row.get('total_products') or 0) if stats_row else 0
                total_quantity = int(stats_row.get('total_quantity') or 0) if stats_row else 0
                active_products = int(stats_row.get('active_products') or 0) if stats_row else 0
                low_stock_products = int(stats_row.get('low_stock_products') or 0) if stats_row else 0
                out_of_stock_products = int(stats_row.get('out_of_stock_products') or 0) if stats_row else 0
                average_quantity = float(Decimal(str(stats_row.get('average_quantity') or 0)).quantize(two_places, rounding=ROUND_HALF_UP)) if stats_row else 0.0
                products_needing_reorder = int(stats_row.get('products_needing_reorder') or 0) if stats_row else 0
                well_stocked_products = int(stats_row.get('well_stocked_products') or 0) if stats_row else 0

                logger.info(
                    f"Store product statistics calculated: total_products={total_products}, "
                    f"total_quantity={total_quantity}, active_products={active_products}, "
                    f"low_stock_products={low_stock_products}, out_of_stock_products={out_of_stock_products}, "
                    f"average_quantity={average_quantity}, products_needing_reorder={products_needing_reorder}, "
                    f"well_stocked_products={well_stocked_products}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "loc_id": loc_id,
                        }
                    }
                )

                statistics = GetStoreProductStatisticsServiceReadDto(
                    total_products=total_products,
                    total_quantity=total_quantity,
                    active_products=active_products,
                    low_stock_products=low_stock_products,
                    out_of_stock_products=out_of_stock_products,
                    average_quantity=average_quantity,
                    products_needing_reorder=products_needing_reorder,
                    well_stocked_products=well_stocked_products,
                )

                return Respons(
                    success=True,
                    detail="Store product statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting store product statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get store product statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

