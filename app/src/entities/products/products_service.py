from typing import Optional, List
from src.entities.products.products_read_dto import (
    CreateProductServiceReadDto,
    UpdateProductServiceReadDto,
    GetProductServiceReadDto,
    GetProductsServiceReadDto,
    PurchaseBatchReadDto,
    ProductMovementReadDto,
    DocumentReadDto,
    MetadataReadDto,
    GetBatchLocationsServiceReadDto,
    PermanentDeleteProductServiceReadDto,
    GetProductStatisticsServiceReadDto,
    DeleteBatchServiceReadDto,
    DeleteMovementServiceReadDto,
    PricingRuleAppliedReadDto,
    TaxRuleAppliedReadDto,
)
from src.entities.products.products_write_dto import (
    CreateProductServiceWriteDto,
    UpdateProductServiceWriteDto,
    AddBatchToProductServiceWriteDto,
    ReverseBatchServiceWriteDto,
    PermanentDeleteProductServiceWriteDto,
    DeleteBatchServiceWriteDto,
    DeleteMovementServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from src.entities.filemanager.fmg_service import FileUploadService
from trovesuite.utils import Helper

logger = get_logger("products_service")


class ProductsService:
    """Service class for products operations"""

    @staticmethod
    def _generate_batch_number(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> str:
        """Generate a systematic batch number in format BA-YYYYMMDD-NNN
        Handles multiple batches per day by incrementing the sequence number
        """
        from datetime import datetime
        
        # Get current date in YYYYMMDD format
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"BA-{today}"
        
        # Find the highest sequence number for today
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
            # Extract sequence number from last batch (e.g., BA-20251218-001 -> 001)
            last_number = last_batch['batch_number']
            try:
                # Get the part after the last dash
                sequence_str = last_number.split('-')[-1]
                sequence_num = int(sequence_str)
                next_sequence = sequence_num + 1
            except (ValueError, IndexError):
                # If parsing fails, start from 1
                next_sequence = 1
        else:
            # No batches for today, start from 1
            next_sequence = 1
        
        # Format with zero padding (e.g., 001, 002, 010, 100)
        # This allows multiple batches per day: BA-20251218-001, BA-20251218-002, etc.
        batch_number = f"{prefix}-{next_sequence:03d}"
        
        # Double-check it doesn't exist (race condition protection)
        # If multiple batches are created simultaneously, increment until we find a free number
        max_attempts = 1000  # Safety limit
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
                # Number is available, return it
                return batch_number
            
            # Number exists, increment and try again
            next_sequence += 1
            batch_number = f"{prefix}-{next_sequence:03d}"
            attempts += 1
        
        # Fallback: if we hit max attempts, use timestamp-based unique number
        import time
        timestamp_suffix = int(time.time() * 1000) % 10000  # Last 4 digits of timestamp
        batch_number = f"{prefix}-{timestamp_suffix:04d}"
        
        return batch_number

    @staticmethod
    def _get_product_metadata(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        product_id: str
    ) -> List[dict]:
        """Get metadata objects (id, name, type) for a product"""
        cursor.execute(
            f"""SELECT pm.id, pm.name, pm.of_type as type
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
        results = cursor.fetchall()
        return [dict(row) for row in results if row.get('id')]

    @staticmethod
    def _get_product_documents(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        product_id: str
    ) -> List[DocumentReadDto]:
        """Get documents for a product with presigned URLs"""
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
    def _get_product_batches(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        product_id: str
    ) -> List[dict]:
        """Get batches for a product with related names"""
        cursor.execute(
            f"""SELECT pb.*,
                   creator.fullname as created_by,
                   updater.fullname as updated_by,
                   deleter.fullname as deleted_by,
                   c.symbol as currency_name,
                   uom.name as unit_of_measure_name,
                   s.fullname as supplier_name
            FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pb.created_by = creator.id AND pb.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON pb.updated_by = updater.id AND pb.tenant_id = updater.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON pb.deleted_by = deleter.id AND pb.tenant_id = deleter.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON pb.currency_id = c.id AND pb.tenant_id = c.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE} uom ON pb.unit_of_measure_id = uom.id AND pb.tenant_id = uom.tenant_id
            LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON pb.supplier_id = s.id AND pb.tenant_id = s.tenant_id AND pb.org_id = s.org_id AND pb.bus_id = s.bus_id
            WHERE pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s 
            AND pb.product_id = %s AND pb.delete_status = 'NOT_DELETED'
            ORDER BY pb.cdatetime DESC""",
            (tenant_id, org_id, bus_id, product_id),
        )
        batches = cursor.fetchall()
        # Convert date objects to strings for product_expiry_date
        from datetime import date
        batch_list = []
        for batch in batches:
            batch_dict = dict(batch)
            if batch_dict.get('product_expiry_date') and isinstance(batch_dict['product_expiry_date'], date):
                batch_dict['product_expiry_date'] = batch_dict['product_expiry_date'].isoformat()
            batch_list.append(batch_dict)
        return batch_list

    @staticmethod
    def _get_batch_movements(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        batch_id: str
    ) -> List[dict]:
        """Get movements for a specific batch (SYSTEM location_type and NULL/PURCHASE movements)"""
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
            AND pm.batch_id = %s AND (pm.location_type = 'SYSTEM' OR pm.location_type IS NULL)
            ORDER BY pm.cdatetime DESC""",
            (tenant_id, org_id, bus_id, batch_id),
        )
        return cursor.fetchall()

    @staticmethod
    def create_product(
        data: CreateProductServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[CreateProductServiceReadDto]:
        """Create a new product with optional batches"""
        logger.info(
            f"Processing product creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "name": data.name if data.name else None,
                    "created_by": created_by,
                }
            },
        )

        # If name is None, skip product creation entirely
        if not data.name:
            return Respons(
                success=False,
                detail="Product name is required. Cannot create product without a name.",
                error="MISSING_NAME",
            )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Check if product with same name already exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND name = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.name),
                )
                existing_product = cursor.fetchone()

                if existing_product:
                    # Return early for duplicate - no changes made, transaction will exit normally
                    return Respons(
                        success=False,
                        detail=f"Product with name '{data.name}' already exists",
                        error="DUPLICATE_NAME",
                    )
                
                # Generate product ID
                product_id = Helper.generate_unique_identifier(prefix="prd")

                # Insert into msg_products table
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRODUCTS_TABLE}
                    (id, tenant_id, org_id, bus_id, name, description, sku, bar_code,
                     delete_status, is_active, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        product_id, tenant_id, org_id, bus_id,
                        data.name, data.description,
                        data.sku, data.bar_code,
                        'NOT_DELETED', data.is_active if data.is_active is not None else True,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                product_result = cursor.fetchone()

                if not product_result:
                    raise ValueError("Failed to create product")

                # Insert metadata associations
                if data.metadata_ids:
                    for metadata_id in data.metadata_ids:
                        # Verify metadata exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s AND delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, metadata_id),
                        )
                        if not cursor.fetchone():
                            logger.warning(f"Metadata {metadata_id} not found, skipping")
                            continue

                        metadata_assignment_id = Helper.generate_unique_identifier(prefix="map")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_metadata_id, product_id,
                             cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                metadata_assignment_id, tenant_id, org_id, bus_id,
                                metadata_id, product_id,
                                cdate, ctime, cdatetime, created_by
                            ),
                        )

                # Insert document associations
                if data.document_ids:
                    for document_id in data.document_ids:
                        # Verify document exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s""",
                            (tenant_id, org_id, bus_id, document_id),
                        )
                        if not cursor.fetchone():
                            logger.warning(f"Document {document_id} not found, skipping")
                            continue

                        doc_assignment_id = Helper.generate_unique_identifier(prefix="pdoc")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_DOCUMENT_IDS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, document_id,
                             delete_status, is_active, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                doc_assignment_id, tenant_id, org_id, bus_id,
                                product_id, document_id,
                                'NOT_DELETED', True,
                                cdate, ctime, cdatetime, created_by
                            ),
                        )

                # Insert batch only if qty is provided and greater than 0
                # Database constraint requires qty_received > 0, so skip batch creation if qty <= 0
                if data.qty is not None and data.qty > 0:
                    # Validate required batch fields when qty > 0
                    if not data.currency_id:
                        raise ValueError("currency_id is required when qty > 0")
                    if data.cost_price is None:
                        raise ValueError("cost_price is required when qty > 0")
                    if data.base_selling_price is None:
                        raise ValueError("base_selling_price is required when qty > 0")
                    
                    # Verify currency exists (required for batch)
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.currency_id),
                    )
                    if not cursor.fetchone():
                        raise ValueError(f"Currency {data.currency_id} not found")

                    # Verify unit of measure if provided
                    if data.unit_of_measure_id:
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE}
                            WHERE tenant_id = %s AND id = %s""",
                            (tenant_id, data.unit_of_measure_id),
                        )
                        if not cursor.fetchone():
                            raise ValueError(f"Unit of measure {data.unit_of_measure_id} not found")

                    # Verify supplier if provided
                    if data.supplier_id:
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_SUPPLIERS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s AND delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, data.supplier_id),
                        )
                        if not cursor.fetchone():
                            raise ValueError(f"Supplier {data.supplier_id} not found")

                    # Handle batch_number: use provided one or generate automatically
                    if data.batch_number:
                        # Check if the provided batch_number already exists
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND batch_number = %s AND delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, data.batch_number),
                        )
                        existing_batch = cursor.fetchone()
                        
                        if existing_batch:
                            return Respons(
                                success=False,
                                detail=f"Batch number '{data.batch_number}' already exists. Please provide a different batch number.",
                                error="DUPLICATE_BATCH_NUMBER",
                            )
                        
                        # Use the provided batch_number
                        batch_number = data.batch_number
                    else:
                        # Generate batch number automatically if not provided
                        batch_number = ProductsService._generate_batch_number(
                            cursor, tenant_id, org_id, bus_id
                        )

                    # Handle expire_date: convert string to date or pass None
                    # expire_date is a string in format YYYY-MM-DD, PostgreSQL will handle the conversion
                    expiry_date_value = data.expire_date if data.expire_date else None

                    batch_id = Helper.generate_unique_identifier(prefix="bat")
                    # Set status to RECEIVED when qty is provided and greater than 0
                    # Since we're in the block where data.qty is not None and DTO validation requires qty > 0,
                    # status will always be RECEIVED here
                    batch_status = 'RECEIVED'
                    
                    # Wrap batch INSERT in try-except to prevent transaction rollback if batch creation fails
                    try:
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, supplier_id, batch_number,
                             currency_id, cost_price, base_selling_price, product_size, unit_of_measure_id,
                             product_expiry_date, batch_type, qty_ordered, qty_received, qty_remaining, qty_remaining_for_purchase_order,
                             status, delete_status, is_active, cdate, ctime, cdatetime, created_by, updated_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *""",
                            (
                                batch_id, tenant_id, org_id, bus_id, product_id,
                                data.supplier_id, batch_number,
                                data.currency_id, data.cost_price, data.base_selling_price,
                                data.size, data.unit_of_measure_id,
                                expiry_date_value,
                                'OPENING_STOCK',  # Batch type for initial stock when creating product
                                None,  # qty_ordered is NULL for OPENING_STOCK
                                data.qty, data.qty,  # qty_received = qty, qty_remaining = qty_received for OPENING_STOCK
                                0,  # qty_remaining_for_purchase_order = 0 for OPENING_STOCK (not from purchase order)
                                'RECEIVED',  # Set status to RECEIVED when qty > 0
                                'NOT_DELETED', data.is_active if data.is_active is not None else True,
                                cdate, ctime, cdatetime, created_by, created_by
                            ),
                        )
                    except Exception as batch_err:
                        # Log the error but don't rollback the transaction - product should still be created
                        logger.error(
                            f"Failed to create batch during product creation: {str(batch_err)}",
                            extra={
                                "extra_fields": {
                                    "product_id": product_id,
                                    "batch_id": batch_id,
                                    "error": str(batch_err),
                                }
                            },
                            exc_info=True
                        )
                        # Re-raise to see the actual error - this will help debug the issue
                        raise ValueError(f"Failed to create batch: {str(batch_err)}")

                # Get product with user fullnames
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s""",
                    (product_id, tenant_id, org_id, bus_id),
                )
                product_with_users = cursor.fetchone()

                if product_with_users:
                    product_dict = dict(product_with_users)
                    product_dict['created_by'] = product_dict.get('created_by') or None
                    product_dict['updated_by'] = product_dict.get('updated_by') or None
                    product_dict['deleted_by'] = product_dict.get('deleted_by') or None
                else:
                    product_dict = dict(product_result)
                    product_dict['created_by'] = None
                    product_dict['updated_by'] = None
                    product_dict['deleted_by'] = None

                # Get metadata, documents, and batches
                # Wrap in try-except to prevent transaction rollback if these fail
                try:
                    metadata_data = ProductsService._get_product_metadata(
                        cursor, tenant_id, org_id, bus_id, product_id
                    )
                    product_dict['metadata'] = [MetadataReadDto(**meta) for meta in metadata_data] if metadata_data else []
                    product_dict['documents'] = ProductsService._get_product_documents(
                        cursor, tenant_id, org_id, bus_id, product_id
                    )
                    batches_data = ProductsService._get_product_batches(
                        cursor, tenant_id, org_id, bus_id, product_id
                    )
                    # Format batches with movements nested inside each batch
                    batches_list = []
                    for batch_dict in batches_data:
                        batch_id = batch_dict.get('id')
                        
                        # Get movements for this specific batch
                        movements_data = []
                        if batch_id:
                            movements_data = ProductsService._get_batch_movements(
                                cursor, tenant_id, org_id, bus_id, batch_id
                            )
                        
                        # Format movements for this batch
                        movements_list = []
                        for movement in movements_data:
                            mov_dict = dict(movement)
                            mov_dict['batch_id'] = mov_dict.get('batch_id') or None
                            mov_dict['batch_number'] = mov_dict.get('batch_number') or None
                            mov_dict['location_type'] = mov_dict.get('location_type') or None
                            mov_dict['location_id'] = mov_dict.get('location_id') or None
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
                        
                        # Add movements to batch dict
                        batch_dict['movements'] = movements_list if movements_list else None
                        # Set new field names for batch quantities
                        batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                        batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                        batches_list.append(PurchaseBatchReadDto(**batch_dict))
                    
                    product_dict['batches'] = batches_list if batches_list else []
                    # Calculate total remaining_qty by summing qty_remaining from all active batches (exclude VOID and CANCELLED)
                    # For products: qty_remaining = sum(qty_remaining) from batches (actual stock remaining)
                    product_dict['remaining_qty'] = sum(
                        float(batch.get('qty_remaining', 0) or 0) for batch in batches_data 
                        if batch.get('status') not in ('VOID', 'CANCELLED') 
                        and batch.get('is_active', True) is True
                        and batch.get('delete_status') == 'NOT_DELETED'
                    ) if batches_data else 0
                    # Calculate specific_product_all_batch_remaining_qty (same as remaining_qty)
                    product_dict['specific_product_all_batch_remaining_qty'] = int(product_dict['remaining_qty'])
                    product_dict['remaining_qty'] = int(product_dict['remaining_qty'])
                except Exception as read_err:
                    # If reading related data fails, use empty values but don't fail transaction
                    logger.warning(f"Error reading product related data (non-critical): {read_err}", exc_info=True)
                    product_dict['metadata'] = []
                    product_dict['documents'] = []
                    product_dict['batches'] = []
                    product_dict['remaining_qty'] = 0
                    product_dict['specific_product_all_batch_remaining_qty'] = 0

                # Add default price fields (not calculated on creation)
                product_dict['cost_price'] = None
                product_dict['base_selling_price'] = None
                product_dict['actual_price'] = None
                product_dict['price_after_pricing_rule'] = None
                product_dict['price_after_tax'] = None
                product_dict['tax_amount'] = None
                product_dict['final_price'] = None
                product_dict['currency_id'] = None
                product_dict['currency_name'] = None
                product_dict['currency_symbol'] = None
                product_dict['taxes_applied'] = []
                product_dict['pricing_rule_applied'] = None
                product_dict['tax_rule_applied'] = None

                # Create DTO - if this fails, let it raise to rollback transaction (data integrity issue)
                product_read = CreateProductServiceReadDto(**product_dict)

                # Log activity - get ALL data from table after insert
                try:
                    # Get complete record with ALL columns from database (raw data with user IDs)
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (product_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    if not complete_new_data_record:
                        raise ValueError("Failed to fetch complete data for activity log")
                    
                    # Use raw database data (with user IDs, not fullnames)
                    complete_new_data = dict(complete_new_data_record)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product",
                        resource_id=product_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,  # All data from table after insert
                        description=f"Product {product_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Product created successfully: {product_id}",
                    extra={
                        "extra_fields": {
                            "product_id": product_id,
                            "name": data.name,
                        }
                    },
                )

                # Create response BEFORE returning to ensure it's ready
                response = Respons(
                    success=True,
                    detail="Product created successfully",
                    data=[product_read],
                )
                
                # Log that we're about to exit transaction - commit should happen next
                logger.info(
                    f"About to exit transaction for product {product_id} - commit should occur now",
                    extra={
                        "extra_fields": {
                            "product_id": product_id,
                            "transaction_status": "exiting",
                        }
                    },
                )

                # Return response - transaction will commit when context exits normally
                # The commit happens in database.py line 511: conn.commit()
                return response

        except ValueError as e:
            logger.error(f"Validation error creating product: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_product(
        data: UpdateProductServiceWriteDto,
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateProductServiceReadDto]:
        """Update a product with optional batches"""
        logger.info(
            f"Processing product update: {product_id}",
            extra={
                "extra_fields": {
                    "product_id": product_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing product
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (product_id, tenant_id, org_id, bus_id),
                )
                existing_product = cursor.fetchone()

                if not existing_product:
                    return Respons(
                        success=False,
                        detail="Product not found",
                        error="NOT_FOUND",
                    )
                
                old_data = dict(existing_product)

                # If name is being updated, check for duplicates
                if data.name is not None and data.name != old_data.get('name'):
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND name = %s AND id != %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.name, product_id),
                    )
                    duplicate = cursor.fetchone()
                    if duplicate:
                        return Respons(
                            success=False,
                            detail=f"Product with name '{data.name}' already exists",
                            error="DUPLICATE_NAME",
                        )

                # Build update query dynamically
                update_fields = []
                params = []

                if data.name is not None:
                    update_fields.append("name = %s")
                    params.append(data.name)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.sku is not None:
                    update_fields.append("sku = %s")
                    params.append(data.sku)
                if data.bar_code is not None:
                    update_fields.append("bar_code = %s")
                    params.append(data.bar_code)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)

                if update_fields:
                    update_fields.append("updated_by = %s")
                    params.extend([updated_by, product_id, tenant_id, org_id, bus_id])

                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PRODUCTS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        params,
                    )

                # Update metadata associations if provided
                if data.metadata_ids is not None:
                    # Delete existing associations
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s""",
                        (tenant_id, org_id, bus_id, product_id),
                    )

                    # Insert new associations
                    for metadata_id in data.metadata_ids:
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_PRODUCT_METADATA_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s AND delete_status = 'NOT_DELETED'""",
                            (tenant_id, org_id, bus_id, metadata_id),
                        )
                        if not cursor.fetchone():
                            logger.warning(f"Metadata {metadata_id} not found, skipping")
                            continue

                        metadata_assignment_id = Helper.generate_unique_identifier(prefix="map")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_metadata_id, product_id,
                             cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                metadata_assignment_id, tenant_id, org_id, bus_id,
                                metadata_id, product_id,
                                cdate, ctime, cdatetime, updated_by
                            ),
                        )

                # Update document associations if provided
                if data.document_ids is not None:
                    # Soft delete existing associations
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PRODUCT_DOCUMENT_IDS_TABLE}
                        SET delete_status = 'DELETED', deleted_by = %s, updated_by = %s
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                        (updated_by, updated_by, tenant_id, org_id, bus_id, product_id),
                    )

                    # Insert new associations
                    for document_id in data.document_ids:
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                            AND id = %s""",
                            (tenant_id, org_id, bus_id, document_id),
                        )
                        if not cursor.fetchone():
                            logger.warning(f"Document {document_id} not found, skipping")
                            continue

                        doc_assignment_id = Helper.generate_unique_identifier(prefix="pdoc")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_DOCUMENT_IDS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, document_id,
                             delete_status, is_active, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                doc_assignment_id, tenant_id, org_id, bus_id,
                                product_id, document_id,
                                'NOT_DELETED', True,
                                cdate, ctime, cdatetime, updated_by
                            ),
                        )

                # Get updated product with user fullnames
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s""",
                    (product_id, tenant_id, org_id, bus_id),
                )
                product_with_users = cursor.fetchone()

                if product_with_users:
                    product_dict = dict(product_with_users)
                    product_dict['created_by'] = product_dict.get('created_by') or None
                    product_dict['updated_by'] = product_dict.get('updated_by') or None
                    product_dict['deleted_by'] = product_dict.get('deleted_by') or None
                else:
                    product_dict = dict(existing_product)
                    product_dict['created_by'] = None
                    product_dict['updated_by'] = None
                    product_dict['deleted_by'] = None

                # Get metadata, documents, and batches
                metadata_data = ProductsService._get_product_metadata(
                    cursor, tenant_id, org_id, bus_id, product_id
                )
                product_dict['metadata'] = [MetadataReadDto(**meta) for meta in metadata_data] if metadata_data else []
                product_dict['documents'] = ProductsService._get_product_documents(
                    cursor, tenant_id, org_id, bus_id, product_id
                )
                batches_data = ProductsService._get_product_batches(
                    cursor, tenant_id, org_id, bus_id, product_id
                )
                # Format batches with movements nested inside each batch
                batches_list = []
                for batch_dict in batches_data:
                    batch_id = batch_dict.get('id')
                    
                    # Get movements for this specific batch
                    movements_data = []
                    if batch_id:
                        movements_data = ProductsService._get_batch_movements(
                            cursor, tenant_id, org_id, bus_id, batch_id
                        )
                    
                    # Format movements for this batch
                    movements_list = []
                    for movement in movements_data:
                        mov_dict = dict(movement)
                        mov_dict['batch_id'] = mov_dict.get('batch_id') or None
                        mov_dict['batch_number'] = mov_dict.get('batch_number') or None
                        mov_dict['location_type'] = mov_dict.get('location_type') or None
                        mov_dict['location_id'] = mov_dict.get('location_id') or None
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
                    
                    # Add movements to batch dict
                    batch_dict['movements'] = movements_list if movements_list else None
                    # Set new field names for batch quantities
                    batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                    batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                    batches_list.append(PurchaseBatchReadDto(**batch_dict))
                
                product_dict['batches'] = batches_list if batches_list else []
                # Calculate total remaining_qty by summing qty_remaining from all active non-VOID batches
                # Sum qty_remaining directly from database batches_data
                product_dict['remaining_qty'] = sum(
                    float(batch.get('qty_remaining', 0) or 0) for batch in batches_data 
                    if batch.get('status') not in ('VOID', 'CANCELLED')
                    and batch.get('is_active', True) is True
                    and batch.get('delete_status') == 'NOT_DELETED'
                ) if batches_data else 0
                product_dict['remaining_qty'] = int(product_dict['remaining_qty'])

                # Add default price fields (not recalculated here)
                product_dict['cost_price'] = None
                product_dict['base_selling_price'] = None
                product_dict['actual_price'] = None
                product_dict['price_after_pricing_rule'] = None
                product_dict['price_after_tax'] = None
                product_dict['tax_amount'] = None
                product_dict['final_price'] = None
                product_dict['currency_id'] = None
                product_dict['currency_name'] = None
                product_dict['currency_symbol'] = None
                product_dict['taxes_applied'] = []
                product_dict['pricing_rule_applied'] = None
                product_dict['tax_rule_applied'] = None

                product_read = UpdateProductServiceReadDto(**product_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (product_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else product_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product",
                        resource_id=product_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Product {product_id} updated successfully",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Product updated successfully: {product_id}",
                    extra={
                        "extra_fields": {
                            "product_id": product_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Product updated successfully",
                    data=[product_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating product: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product(
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetProductServiceReadDto]:
        """Get a single product by ID"""
        logger.info(
            f"Processing get product request: {product_id}",
            extra={
                "extra_fields": {
                    "product_id": product_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s AND p.org_id = %s 
                    AND p.bus_id = %s AND p.delete_status = 'NOT_DELETED'""",
                    (product_id, tenant_id, org_id, bus_id),
                )
                product = cursor.fetchone()

                if not product:
                    return Respons(
                        success=False,
                        detail="Product not found",
                        error="NOT_FOUND",
                    )

                product_dict = dict(product)
                product_dict['created_by'] = product_dict.get('created_by') or None
                product_dict['updated_by'] = product_dict.get('updated_by') or None
                product_dict['deleted_by'] = product_dict.get('deleted_by') or None

                # Get metadata, documents, and batches
                metadata_data = ProductsService._get_product_metadata(
                    cursor, tenant_id, org_id, bus_id, product_id
                )
                product_dict['metadata'] = [MetadataReadDto(**meta) for meta in metadata_data] if metadata_data else []
                product_dict['documents'] = ProductsService._get_product_documents(
                    cursor, tenant_id, org_id, bus_id, product_id
                )
                batches_data = ProductsService._get_product_batches(
                    cursor, tenant_id, org_id, bus_id, product_id
                )
                # Format batches with movements nested inside each batch
                batches_list = []
                for batch_dict in batches_data:
                    batch_id = batch_dict.get('id')
                    
                    # Get movements for this specific batch
                    movements_data = []
                    if batch_id:
                        movements_data = ProductsService._get_batch_movements(
                            cursor, tenant_id, org_id, bus_id, batch_id
                        )
                    
                    # Format movements for this batch
                    movements_list = []
                    for movement in movements_data:
                        mov_dict = dict(movement)
                        mov_dict['batch_id'] = mov_dict.get('batch_id') or None
                        mov_dict['batch_number'] = mov_dict.get('batch_number') or None
                        mov_dict['location_type'] = mov_dict.get('location_type') or None
                        mov_dict['location_id'] = mov_dict.get('location_id') or None
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
                    
                    # Add movements to batch dict
                    batch_dict['movements'] = movements_list if movements_list else None
                    # Set new field names for batch quantities
                    batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                    batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                    batches_list.append(PurchaseBatchReadDto(**batch_dict))
                
                product_dict['batches'] = batches_list if batches_list else []
                # Calculate total remaining_qty by summing qty_remaining from all active non-VOID batches
                # Sum qty_remaining directly from database batches_data
                product_dict['remaining_qty'] = sum(
                    float(batch.get('qty_remaining', 0) or 0) for batch in batches_data 
                    if batch.get('status') not in ('VOID', 'CANCELLED')
                    and batch.get('is_active', True) is True
                    and batch.get('delete_status') == 'NOT_DELETED'
                ) if batches_data else 0
                # Calculate specific_product_all_batch_remaining_qty (same as remaining_qty)
                product_dict['specific_product_all_batch_remaining_qty'] = int(product_dict['remaining_qty'])
                product_dict['remaining_qty'] = int(product_dict['remaining_qty'])

                # Get latest batch for cost_price and base_selling_price
                latest_batch = None
                if batches_data:
                    # Get the latest batch (already sorted by cdatetime DESC)
                    latest_batch = batches_data[0] if batches_data else None
                
                if latest_batch:
                    product_dict['cost_price'] = float(latest_batch.get('cost_price')) if latest_batch.get('cost_price') is not None else None
                    product_dict['base_selling_price'] = float(latest_batch.get('base_selling_price')) if latest_batch.get('base_selling_price') is not None else None
                else:
                    product_dict['cost_price'] = None
                    product_dict['base_selling_price'] = None

                # Calculate prices using pricing calculator
                from src.utils.pricing_calculator import PricingCalculator
                from datetime import datetime
                
                # Get product metadata for price calculation
                product_metadata = None
                if metadata_data:
                    product_metadata = {}
                    for meta in metadata_data:
                        meta_type = (meta.get('type') or '').upper()
                        meta_id = meta.get('id')
                        if meta_type == 'CATEGORY':
                            product_metadata['category_id'] = meta_id
                        elif meta_type == 'TAG':
                            product_metadata['tag_id'] = meta_id
                        elif meta_type == 'BRAND':
                            product_metadata['brand_id'] = meta_id
                        elif meta_type == 'LABEL':
                            product_metadata['label_id'] = meta_id
                
                # Get SKU
                sku = product_dict.get('sku')
                
                # Get latest batch ID if available
                batch_id = latest_batch.get('id') if latest_batch else None
                
                # Calculate all prices
                try:
                    prices = PricingCalculator.calculate_all_prices(
                        cursor=cursor,
                        product_id=product_id,
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        quantity=1,
                        location_id=None,
                        batch_id=batch_id,
                        sku=sku,
                        product_metadata=product_metadata,
                        current_datetime=datetime.now()
                    )
                    
                    actual_price = prices.get('actual_price')
                    base_selling_price = prices.get('base_selling_price')
                    # If actual_price is 0 or None, use base_selling_price
                    if actual_price is None or actual_price == 0:
                        actual_price = base_selling_price
                    product_dict['actual_price'] = actual_price
                    product_dict['price_after_pricing_rule'] = prices.get('price_after_pricing_rule')
                    product_dict['price_after_tax'] = prices.get('price_after_tax')
                    product_dict['tax_amount'] = prices.get('tax_amount')
                    product_dict['final_price'] = prices.get('final_price')
                    product_dict['currency_id'] = prices.get('currency_id')
                    product_dict['currency_name'] = prices.get('currency_name')
                    product_dict['currency_symbol'] = prices.get('currency_symbol')
                    product_dict['taxes_applied'] = prices.get('taxes_applied', [])
                    product_dict['pricing_rule_applied'] = prices.get('pricing_rule_applied')
                    product_dict['tax_rule_applied'] = prices.get('tax_rule_applied')
                except Exception as price_err:
                    logger.warning(f"Error calculating prices for product {product_id}: {str(price_err)}", exc_info=True)
                    product_dict['actual_price'] = None
                    product_dict['price_after_pricing_rule'] = None
                    product_dict['price_after_tax'] = None
                    product_dict['tax_amount'] = None
                    product_dict['final_price'] = None
                    product_dict['taxes_applied'] = []
                    product_dict['pricing_rule_applied'] = None
                    product_dict['tax_rule_applied'] = None

                product_read = GetProductServiceReadDto(**product_dict)

                return Respons(
                    success=True,
                    detail="Product retrieved successfully",
                    data=[product_read],
                )

        except Exception as e:
            logger.error(f"Error getting product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_products(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetProductsServiceReadDto]]:
        """Get list of products with pagination"""
        logger.info(
            f"Processing get products request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "is_active": is_active,
                    "search": search,
                    "page": page,
                    "size": size,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "p.tenant_id = %s",
                    "p.org_id = %s",
                    "p.bus_id = %s",
                    "p.delete_status = 'NOT_DELETED'"
                ]
                params = [tenant_id, org_id, bus_id]

                if is_active is not None:
                    where_conditions.append("p.is_active = %s")
                    params.append(is_active)

                if search:
                    where_conditions.append(
                        "(p.name ILIKE %s OR p.description ILIKE %s OR p.sku ILIKE %s OR p.bar_code ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"""SELECT COUNT(*) as total FROM {db_settings.MSG_PRODUCTS_TABLE} p
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

                # Get products with user fullnames
                cursor.execute(
                    f"""SELECT p.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON p.created_by = creator.id AND p.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON p.updated_by = updater.id AND p.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON p.deleted_by = deleter.id AND p.tenant_id = deleter.tenant_id
                    WHERE {where_clause}
                    ORDER BY p.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    params + [size, offset],
                )
                products = cursor.fetchall()

                product_list = []
                for prod in products:
                    prod_dict = dict(prod)
                    prod_dict['created_by'] = prod_dict.get('created_by') or None
                    prod_dict['updated_by'] = prod_dict.get('updated_by') or None
                    prod_dict['deleted_by'] = prod_dict.get('deleted_by') or None

                    # Get metadata, documents, and batches
                    metadata_data = ProductsService._get_product_metadata(
                        cursor, tenant_id, org_id, bus_id, prod_dict['id']
                    )
                    prod_dict['metadata'] = [MetadataReadDto(**meta) for meta in metadata_data] if metadata_data else []
                    prod_dict['documents'] = ProductsService._get_product_documents(
                        cursor, tenant_id, org_id, bus_id, prod_dict['id']
                    )
                    batches_data = ProductsService._get_product_batches(
                        cursor, tenant_id, org_id, bus_id, prod_dict['id']
                    )
                    # Format batches with movements nested inside each batch
                    batches_list = []
                    for batch_dict in batches_data:
                        batch_id = batch_dict.get('id')
                        
                        # Get movements for this specific batch
                        movements_data = []
                        if batch_id:
                            movements_data = ProductsService._get_batch_movements(
                                cursor, tenant_id, org_id, bus_id, batch_id
                            )
                        
                        # Format movements for this batch
                        movements_list = []
                        for movement in movements_data:
                            mov_dict = dict(movement)
                            mov_dict['batch_id'] = mov_dict.get('batch_id') or None
                            mov_dict['batch_number'] = mov_dict.get('batch_number') or None
                            mov_dict['location_type'] = mov_dict.get('location_type') or None
                            mov_dict['location_id'] = mov_dict.get('location_id') or None
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
                        
                        # Add movements to batch dict
                        batch_dict['movements'] = movements_list if movements_list else None
                        # Set new field names for batch quantities
                        batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                        batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                        batches_list.append(PurchaseBatchReadDto(**batch_dict))
                    
                    prod_dict['batches'] = batches_list if batches_list else []
                    # Calculate total remaining_qty by summing qty_remaining from all active non-VOID batches
                    # Sum qty_remaining directly from database batches_data
                    prod_dict['remaining_qty'] = sum(
                        float(batch.get('qty_remaining', 0) or 0) for batch in batches_data 
                        if batch.get('status') not in ('VOID', 'CANCELLED')
                        and batch.get('is_active', True) is True
                        and batch.get('delete_status') == 'NOT_DELETED'
                    ) if batches_data else 0
                    # Calculate specific_product_all_batch_remaining_qty (same as remaining_qty)
                    prod_dict['specific_product_all_batch_remaining_qty'] = int(prod_dict['remaining_qty'])
                    prod_dict['remaining_qty'] = int(prod_dict['remaining_qty'])

                    # Get latest batch for cost_price and base_selling_price
                    latest_batch = None
                    if batches_data:
                        # Get the latest batch (already sorted by cdatetime DESC)
                        latest_batch = batches_data[0] if batches_data else None
                    
                    if latest_batch:
                        prod_dict['cost_price'] = float(latest_batch.get('cost_price')) if latest_batch.get('cost_price') is not None else None
                        prod_dict['base_selling_price'] = float(latest_batch.get('base_selling_price')) if latest_batch.get('base_selling_price') is not None else None
                    else:
                        prod_dict['cost_price'] = None
                        prod_dict['base_selling_price'] = None

                    # Calculate prices using pricing calculator
                    from src.utils.pricing_calculator import PricingCalculator
                    from datetime import datetime
                    
                    # Get product metadata for price calculation
                    product_metadata = None
                    if metadata_data:
                        product_metadata = {}
                        for meta in metadata_data:
                            meta_type = (meta.get('type') or '').upper()
                            meta_id = meta.get('id')
                            if meta_type == 'CATEGORY':
                                product_metadata['category_id'] = meta_id
                            elif meta_type == 'TAG':
                                product_metadata['tag_id'] = meta_id
                            elif meta_type == 'BRAND':
                                product_metadata['brand_id'] = meta_id
                            elif meta_type == 'LABEL':
                                product_metadata['label_id'] = meta_id
                    
                    # Get SKU
                    sku = prod_dict.get('sku')
                    
                    # Get latest batch ID if available
                    batch_id = latest_batch.get('id') if latest_batch else None
                    
                    # Calculate all prices
                    try:
                        prices = PricingCalculator.calculate_all_prices(
                            cursor=cursor,
                            product_id=prod_dict['id'],
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            quantity=1,
                            location_id=None,
                            batch_id=batch_id,
                            sku=sku,
                            product_metadata=product_metadata,
                            current_datetime=datetime.now()
                        )
                        
                        actual_price = prices.get('actual_price')
                        base_selling_price = prices.get('base_selling_price')
                        # If actual_price is 0 or None, use base_selling_price
                        if actual_price is None or actual_price == 0:
                            actual_price = base_selling_price
                        prod_dict['actual_price'] = actual_price
                        prod_dict['price_after_pricing_rule'] = prices.get('price_after_pricing_rule')
                        prod_dict['price_after_tax'] = prices.get('price_after_tax')
                        prod_dict['tax_amount'] = prices.get('tax_amount')
                        prod_dict['final_price'] = prices.get('final_price')
                        prod_dict['currency_id'] = prices.get('currency_id')
                        prod_dict['currency_name'] = prices.get('currency_name')
                        prod_dict['currency_symbol'] = prices.get('currency_symbol')
                        prod_dict['taxes_applied'] = prices.get('taxes_applied', [])
                        prod_dict['pricing_rule_applied'] = prices.get('pricing_rule_applied')
                        prod_dict['tax_rule_applied'] = prices.get('tax_rule_applied')
                    except Exception as price_err:
                        logger.warning(f"Error calculating prices for product {prod_dict['id']}: {str(price_err)}", exc_info=True)
                        prod_dict['actual_price'] = None
                        prod_dict['price_after_pricing_rule'] = None
                        prod_dict['price_after_tax'] = None
                        prod_dict['tax_amount'] = None
                        prod_dict['final_price'] = None
                        prod_dict['taxes_applied'] = []
                        prod_dict['pricing_rule_applied'] = None
                        prod_dict['tax_rule_applied'] = None

                    product_list.append(GetProductsServiceReadDto(**prod_dict))

                return Respons(
                    success=True,
                    detail="Products retrieved successfully",
                    data=product_list,
                    meta=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting products: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get products: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_batch_locations(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        product_id: Optional[str] = None,
        location_type: Optional[str] = None,
    ) -> Respons[list[GetBatchLocationsServiceReadDto]]:
        """Get batch locations with optional filters"""
        logger.info(
            f"Processing get batch locations request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "product_id": product_id,
                    "location_type": location_type,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "bl.tenant_id = %s",
                    "bl.org_id = %s",
                    "bl.bus_id = %s",
                    "bl.loc_id = %s",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if product_id:
                    where_conditions.append("pb.product_id = %s")
                    params.append(product_id)

                if location_type:
                    where_conditions.append("bl.location_type = %s")
                    params.append(location_type)

                where_clause = " AND ".join(where_conditions)

                # Query batch locations with related data
                cursor.execute(
                    f"""SELECT bl.id, bl.tenant_id, bl.org_id, bl.bus_id, bl.loc_id, 
                           bl.purchase_batche_id, bl.location_type, bl.qty,
                           bl.cdate, bl.ctime, bl.cdatetime,
                           pb.batch_number, pb.product_expiry_date as expiry_date,
                           pb.cost_price, pb.currency_id, pb.unit_of_measure_id, pb.supplier_id,
                           c.name as currency_name,
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
                    WHERE {where_clause}
                    ORDER BY pb.cdatetime ASC""",
                    tuple(params),
                )
                results = cursor.fetchall()

                batch_locations = []
                for row in results:
                    batch_location_dict = dict(row)
                    batch_locations.append(GetBatchLocationsServiceReadDto(**batch_location_dict))

                return Respons(
                    success=True,
                    detail="Batch locations retrieved successfully",
                    data=batch_locations,
                )

        except Exception as e:
            logger.error(f"Error getting batch locations: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get batch locations: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def add_batch_to_product(
        data: AddBatchToProductServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str
    ) -> Respons[PurchaseBatchReadDto]:
        """Add a batch to an existing product"""
        logger.info(
            f"Processing add batch to product",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "product_id": data.product_id,
                    "qty_received": data.qty_received,
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
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )
                product = cursor.fetchone()

                if not product:
                    return Respons(
                        success=False,
                        detail=f"Product with id '{data.product_id}' not found",
                        error="NOT_FOUND",
                    )

                # Verify currency exists (required for batch)
                cursor.execute(
                    f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                    WHERE tenant_id = %s AND id = %s""",
                    (tenant_id, data.currency_id),
                )
                if not cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"Currency {data.currency_id} not found",
                        error="NOT_FOUND",
                    )

                # Verify unit of measure if provided
                if data.unit_of_measure_id:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.unit_of_measure_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Unit of measure {data.unit_of_measure_id} not found",
                            error="NOT_FOUND",
                        )

                # Verify supplier if provided
                if data.supplier_id:
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
                            error="NOT_FOUND",
                        )

                # Generate batch number automatically
                batch_number = ProductsService._generate_batch_number(
                    cursor, tenant_id, org_id, bus_id
                )

                # Handle expire_date: convert string to date or pass None
                expiry_date_value = data.expire_date if data.expire_date else None

                batch_id = Helper.generate_unique_identifier(prefix="bat")
                # Set status to RECEIVED when qty_received > 0
                batch_status = 'RECEIVED'
                
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    (id, tenant_id, org_id, bus_id, product_id, supplier_id, batch_number,
                     currency_id, cost_price, base_selling_price, product_size, unit_of_measure_id,
                     product_expiry_date, batch_type, qty_ordered, qty_received, qty_remaining, qty_remaining_for_purchase_order,
                     status, delete_status, is_active, cdate, ctime, cdatetime, created_by, updated_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        batch_id, tenant_id, org_id, bus_id, data.product_id,
                        data.supplier_id, batch_number,
                        data.currency_id, data.cost_price, data.base_selling_price,
                        data.size, data.unit_of_measure_id,
                        expiry_date_value,
                        'OPENING_STOCK',  # Batch type for manual stock addition
                        None,  # qty_ordered is NULL for OPENING_STOCK
                        data.qty_received, data.qty_received,  # qty_received = qty_received, qty_remaining = qty_received for OPENING_STOCK
                        0,  # qty_remaining_for_purchase_order = 0 for OPENING_STOCK (not from purchase order)
                        'RECEIVED',  # Set status to RECEIVED when qty_received > 0
                        'NOT_DELETED', data.is_active if data.is_active is not None else True,
                        cdate, ctime, cdatetime, created_by, created_by
                    ),
                )
                batch_result = cursor.fetchone()

                if not batch_result:
                    raise ValueError("Failed to create batch")

                # Create IN movement record for manual batch entry
                try:
                    movement_id = Helper.generate_unique_identifier(prefix="mov")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                         movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id""",
                        (
                            movement_id, tenant_id, org_id, bus_id, data.product_id,
                            batch_id, 'SYSTEM', None,
                            'IN', data.qty_received, f'Manual batch entry - batch {batch_number} added to product', None,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )
                    logger.info(
                        f"IN movement created for batch entry: movement_id={movement_id}, batch_number={batch_number}, qty={data.qty_received}",
                        extra={
                            "extra_fields": {
                                "movement_id": movement_id,
                                "batch_id": batch_id,
                                "batch_number": batch_number,
                                "qty": data.qty_received,
                            }
                        },
                    )
                except Exception as movement_err:
                    logger.warning(f"Failed to create movement for batch entry: {movement_err}", exc_info=True)
                    # Don't fail the transaction if movement creation fails, but log it

                # Get batch with user fullnames and related names
                cursor.execute(
                    f"""SELECT pb.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.symbol as currency_name,
                           uom.name as unit_of_measure_name,
                           s.fullname as supplier_name
                    FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pb.created_by = creator.id AND pb.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON pb.updated_by = updater.id AND pb.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON pb.deleted_by = deleter.id AND pb.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON pb.currency_id = c.id AND pb.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE} uom ON pb.unit_of_measure_id = uom.id AND pb.tenant_id = uom.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON pb.supplier_id = s.id AND pb.tenant_id = s.tenant_id AND pb.org_id = s.org_id AND pb.bus_id = s.bus_id
                    WHERE pb.id = %s AND pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s""",
                    (batch_id, tenant_id, org_id, bus_id),
                )
                batch_with_users = cursor.fetchone()

                if not batch_with_users:
                    raise ValueError("Failed to fetch created batch")

                batch_dict = dict(batch_with_users)
                batch_dict['created_by'] = batch_dict.get('created_by') or None
                batch_dict['updated_by'] = batch_dict.get('updated_by') or None
                batch_dict['deleted_by'] = batch_dict.get('deleted_by') or None
                # Convert date objects to strings for product_expiry_date
                from datetime import date
                if batch_dict.get('product_expiry_date') and isinstance(batch_dict['product_expiry_date'], date):
                    batch_dict['product_expiry_date'] = batch_dict['product_expiry_date'].isoformat()

                # Get movements for this batch (includes the IN movement created for manual batch entry)
                movements_data = ProductsService._get_batch_movements(
                    cursor, tenant_id, org_id, bus_id, batch_id
                )
                movements_list = []
                for movement in movements_data:
                    mov_dict = dict(movement)
                    mov_dict['batch_id'] = mov_dict.get('batch_id') or None
                    mov_dict['batch_number'] = mov_dict.get('batch_number') or None
                    mov_dict['location_type'] = mov_dict.get('location_type') or None
                    mov_dict['location_id'] = mov_dict.get('location_id') or None
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
                
                batch_dict['movements'] = movements_list if movements_list else None
                # Set new field names for batch quantities
                batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                batch_read = PurchaseBatchReadDto(**batch_dict)

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-batch",
                        resource_id=batch_id,
                        action="create",
                        old_data=None,
                        new_data=dict(batch_result),
                        description=f"Batch {batch_number} added to product {data.product_id}",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Batch added successfully to product: batch_number={batch_number}, product_id={data.product_id}",
                    extra={
                        "extra_fields": {
                            "batch_id": batch_id,
                            "batch_number": batch_number,
                            "product_id": data.product_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Batch added to product successfully",
                    data=[batch_read],
                )

        except ValueError as e:
            logger.error(f"Validation error adding batch to product: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error adding batch to product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to add batch to product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def reverse_batch(
        data: ReverseBatchServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[PurchaseBatchReadDto]:
        """Reverse a batch by setting remaining_qty to 0 and status to VOID"""
        logger.info(
            f"Processing batch reversal",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "batch_number": data.batch_number,
                    "updated_by": updated_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Find the batch by batch_number
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND batch_number = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.batch_number),
                )
                existing_batch = cursor.fetchone()

                if not existing_batch:
                    return Respons(
                        success=False,
                        detail=f"Batch with batch_number '{data.batch_number}' not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_batch)
                
                # Log the values before update
                old_qty_remaining = existing_batch.get('qty_remaining', 'N/A')
                old_status = existing_batch.get('status', 'N/A')
                logger.info(
                    f"Before update - Batch {data.batch_number}: qty_remaining={old_qty_remaining}, status={old_status}",
                    extra={
                        "extra_fields": {
                            "batch_id": existing_batch['id'],
                            "batch_number": data.batch_number,
                            "old_qty_remaining": old_qty_remaining,
                            "old_status": old_status,
                        }
                    },
                )

                # Update batch: set remaining_qty to 0 and status to VOID
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    SET qty_remaining = %s, status = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (0, 'VOID', updated_by, existing_batch['id'], tenant_id, org_id, bus_id),
                )
                
                # Check if the update actually affected a row
                if cursor.rowcount == 0:
                    logger.error(
                        f"UPDATE failed - No rows affected for batch {data.batch_number}",
                        extra={
                            "extra_fields": {
                                "batch_id": existing_batch['id'],
                                "batch_number": data.batch_number,
                                "batch_org_id": existing_batch.get('org_id'),
                                "batch_bus_id": existing_batch.get('bus_id'),
                                "request_org_id": org_id,
                                "request_bus_id": bus_id,
                            }
                        },
                    )
                    return Respons(
                        success=False,
                        detail=f"Failed to update batch with batch_number '{data.batch_number}'. No rows were updated.",
                        error="UPDATE_FAILED",
                    )
                
                logger.info(
                    f"Batch update successful: {cursor.rowcount} row(s) updated. qty_remaining: {old_qty_remaining} -> 0, status: {old_status} -> VOID",
                    extra={
                        "extra_fields": {
                            "batch_id": existing_batch['id'],
                            "batch_number": data.batch_number,
                            "rows_updated": cursor.rowcount,
                            "old_qty_remaining": old_qty_remaining,
                            "new_qty_remaining": 0,
                            "old_status": old_status,
                            "new_status": "VOID",
                        }
                    },
                )

                # Create product movement records for batch reversal
                # Query all batch_locations to find where products are located (STORE or WAREHOUSE)
                try:
                    product_id = existing_batch.get('product_id')
                    batch_id = existing_batch['id']
                    
                    # Get all batch locations for this batch
                    cursor.execute(
                        f"""SELECT loc_id, location_type, qty
                        FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND purchase_batche_id = %s""",
                        (tenant_id, org_id, bus_id, batch_id),
                    )
                    batch_locations = cursor.fetchall()
                    
                    movements_created = []
                    
                    if batch_locations:
                        # Create movements for each location
                        for location in batch_locations:
                            loc_id = location.get('loc_id')
                            location_type = location.get('location_type')  # 'STORE' or 'WAREHOUSE'
                            qty_at_location = location.get('qty', 0)
                            
                            if qty_at_location <= 0:
                                continue
                            
                            # Create OUT movement: product leaving the store/warehouse
                            out_movement_id = Helper.generate_unique_identifier(prefix="mov")
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                                (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                                 movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id""",
                                (
                                    out_movement_id, tenant_id, org_id, bus_id, product_id,
                                    batch_id, location_type, loc_id,
                                    'OUT', qty_at_location, f'Batch {data.batch_number} reversed - product leaving {location_type}', None,
                                    cdate, ctime, cdatetime, updated_by
                                ),
                            )
                            movements_created.append({'id': out_movement_id, 'type': 'OUT', 'location_type': location_type, 'loc_id': loc_id, 'qty': qty_at_location})
                            
                            # Create IN movement: product going back to purchase batch
                            in_movement_id = Helper.generate_unique_identifier(prefix="mov")
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                                (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                                 movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id""",
                                (
                                    in_movement_id, tenant_id, org_id, bus_id, product_id,
                                    batch_id, 'SYSTEM', None,
                                    'IN', qty_at_location, f'Batch {data.batch_number} reversed - product returning to batch', None,
                                    cdate, ctime, cdatetime, updated_by
                                ),
                            )
                            movements_created.append({'id': in_movement_id, 'type': 'IN', 'location_type': 'SYSTEM', 'loc_id': None, 'qty': qty_at_location})
                    else:
                        # If no batch_locations found, create movements for the remaining quantity in the batch
                        qty_reversed = old_qty_remaining if isinstance(old_qty_remaining, (int, float)) else 0
                        if qty_reversed > 0:
                            # Create OUT movement from SYSTEM (batch itself)
                            out_movement_id = Helper.generate_unique_identifier(prefix="mov")
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                                (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                                 movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id""",
                                (
                                    out_movement_id, tenant_id, org_id, bus_id, product_id,
                                    batch_id, 'SYSTEM', None,
                                    'OUT', qty_reversed, f'Batch {data.batch_number} reversed - batch voided', None,
                                    cdate, ctime, cdatetime, updated_by
                                ),
                            )
                            movements_created.append({'id': out_movement_id, 'type': 'OUT', 'location_type': 'SYSTEM', 'loc_id': None, 'qty': qty_reversed})
                            
                            # Create IN movement back to batch
                            in_movement_id = Helper.generate_unique_identifier(prefix="mov")
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                                (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                                 movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id""",
                                (
                                    in_movement_id, tenant_id, org_id, bus_id, product_id,
                                    batch_id, 'SYSTEM', None,
                                    'IN', qty_reversed, f'Batch {data.batch_number} reversed - product returning to batch', None,
                                    cdate, ctime, cdatetime, updated_by
                                ),
                            )
                            movements_created.append({'id': in_movement_id, 'type': 'IN', 'location_type': 'SYSTEM', 'loc_id': None, 'qty': qty_reversed})
                    
                    logger.info(
                        f"Movements created for batch reversal: batch_number={data.batch_number}, movements_count={len(movements_created)}",
                        extra={
                            "extra_fields": {
                                "batch_id": batch_id,
                                "batch_number": data.batch_number,
                                "product_id": product_id,
                                "movements_created": movements_created,
                            }
                        },
                    )
                except Exception as movement_err:
                    logger.warning(f"Failed to create movements for batch reversal: {movement_err}", exc_info=True)
                    # Don't fail the whole operation if movement creation fails

                # Get updated batch with user fullnames and related names
                cursor.execute(
                    f"""SELECT pb.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.symbol as currency_name,
                           uom.name as unit_of_measure_name,
                           s.fullname as supplier_name
                    FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON pb.created_by = creator.id AND pb.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON pb.updated_by = updater.id AND pb.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON pb.deleted_by = deleter.id AND pb.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON pb.currency_id = c.id AND pb.tenant_id = c.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_UNIT_OF_MEASURE_TABLE} uom ON pb.unit_of_measure_id = uom.id AND pb.tenant_id = uom.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON pb.supplier_id = s.id AND pb.tenant_id = s.tenant_id AND pb.org_id = s.org_id AND pb.bus_id = s.bus_id
                    WHERE pb.id = %s AND pb.tenant_id = %s AND pb.org_id = %s AND pb.bus_id = %s""",
                    (existing_batch['id'], tenant_id, org_id, bus_id),
                )
                batch_with_users = cursor.fetchone()

                if not batch_with_users:
                    raise ValueError("Failed to fetch updated batch")

                batch_dict = dict(batch_with_users)
                batch_dict['created_by'] = batch_dict.get('created_by') or None
                batch_dict['updated_by'] = batch_dict.get('updated_by') or None
                batch_dict['deleted_by'] = batch_dict.get('deleted_by') or None
                # Convert date objects to strings for product_expiry_date
                from datetime import date
                if batch_dict.get('product_expiry_date') and isinstance(batch_dict['product_expiry_date'], date):
                    batch_dict['product_expiry_date'] = batch_dict['product_expiry_date'].isoformat()

                # Set new field names for batch quantities
                batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                batch_read = PurchaseBatchReadDto(**batch_dict)

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (existing_batch['id'], tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else batch_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-batch",
                        resource_id=existing_batch['id'],
                        action="reverse",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Batch {data.batch_number} reversed (remaining_qty set to 0, status set to VOID)",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Batch reversed successfully: {data.batch_number}",
                    extra={
                        "extra_fields": {
                            "batch_id": existing_batch['id'],
                            "batch_number": data.batch_number,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Batch reversed successfully",
                    data=[batch_read],
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
    def delete_batch(
        data: DeleteBatchServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteBatchServiceReadDto]:
        """Permanently delete a batch"""
        logger.info(
            f"Processing batch permanent deletion",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "batch_id": data.batch_id,
                    "deleted_by": deleted_by,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Verify product exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )
                product = cursor.fetchone()

                if not product:
                    return Respons(
                        success=False,
                        detail=f"Product with id '{data.product_id}' not found",
                        error="NOT_FOUND",
                    )

                # Find the batch and verify it belongs to the product
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    WHERE id = %s AND product_id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.batch_id, data.product_id, tenant_id, org_id, bus_id),
                )
                existing_batch = cursor.fetchone()

                if not existing_batch:
                    return Respons(
                        success=False,
                        detail=f"Batch with id '{data.batch_id}' not found or does not belong to product '{data.product_id}'",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_batch)
                batch_number = old_data.get('batch_number', data.batch_id)

                # Log activity before permanent deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-batch",
                        resource_id=data.batch_id,
                        action="delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Batch {batch_number} permanently deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)
                    # ActivityLogService.log_activity handles savepoint rollback internally
                    # If it still raises an exception, the transaction is already aborted

                # Permanently delete the batch
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    WHERE id = %s AND product_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.batch_id, data.product_id, tenant_id, org_id, bus_id),
                )

                if cursor.rowcount == 0:
                    return Respons(
                        success=False,
                        detail=f"Failed to delete batch with id '{data.batch_id}'. No rows were deleted.",
                        error="DELETE_FAILED",
                    )

                logger.info(
                    f"Batch permanently deleted successfully: batch_id={data.batch_id}",
                    extra={
                        "extra_fields": {
                            "batch_id": data.batch_id,
                            "batch_number": batch_number,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Batch permanently deleted successfully",
                    data=[DeleteBatchServiceReadDto(
                        batch_id=data.batch_id,
                        message=f"Batch {batch_number} permanently deleted successfully"
                    )],
                )

        except ValueError as e:
            logger.error(f"Validation error deleting batch: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error deleting batch: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete batch: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_movement(
        data: DeleteMovementServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteMovementServiceReadDto]:
        """Permanently delete a movement"""
        logger.info(
            f"Processing movement deletion",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "movement_id": data.movement_id,
                    "deleted_by": deleted_by,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Verify product exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )
                product = cursor.fetchone()

                if not product:
                    return Respons(
                        success=False,
                        detail=f"Product with id '{data.product_id}' not found",
                        error="NOT_FOUND",
                    )

                # Find the movement and verify it belongs to the product
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    WHERE id = %s AND product_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.movement_id, data.product_id, tenant_id, org_id, bus_id),
                )
                existing_movement = cursor.fetchone()

                if not existing_movement:
                    return Respons(
                        success=False,
                        detail=f"Movement with id '{data.movement_id}' not found or does not belong to product '{data.product_id}'",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_movement)

                # Log activity before permanent deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product-movement",
                        resource_id=data.movement_id,
                        action="delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Movement {data.movement_id} permanently deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Permanently delete the movement
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    WHERE id = %s AND product_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.movement_id, data.product_id, tenant_id, org_id, bus_id),
                )

                if cursor.rowcount == 0:
                    return Respons(
                        success=False,
                        detail=f"Failed to delete movement with id '{data.movement_id}'. No rows were deleted.",
                        error="DELETE_FAILED",
                    )

                logger.info(
                    f"Movement deleted successfully: movement_id={data.movement_id}",
                    extra={
                        "extra_fields": {
                            "movement_id": data.movement_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Movement deleted successfully",
                    data=[DeleteMovementServiceReadDto(
                        movement_id=data.movement_id,
                        message=f"Movement {data.movement_id} deleted successfully"
                    )],
                )

        except ValueError as e:
            logger.error(f"Validation error deleting movement: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error deleting movement: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete movement: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def permanent_delete_product(
        data: PermanentDeleteProductServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[PermanentDeleteProductServiceReadDto]:
        """Permanently delete a product and its related associations"""
        logger.info(
            f"Processing permanent product deletion",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "product_id": data.product_id,
                    "deleted_by": deleted_by,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get product details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )
                product = cursor.fetchone()

                if not product:
                    return Respons(
                        success=False,
                        detail="Product not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion
                product_dict = dict(product)

                # Check for related records that might prevent deletion
                # Check for active batches
                cursor.execute(
                    f"""SELECT COUNT(*) as count FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                    WHERE product_id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )
                batches_result = cursor.fetchone()
                active_batches_count = batches_result['count'] if batches_result else 0

                if active_batches_count > 0:
                    return Respons(
                        success=False,
                        detail=f"Cannot permanently delete product. It has {active_batches_count} active batch(es). Please delete or void all batches first.",
                        error="RELATED_RECORDS_EXIST",
                    )

                # Check for store products
                cursor.execute(
                    f"""SELECT COUNT(*) as count FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE product_id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )
                store_products_result = cursor.fetchone()
                store_products_count = store_products_result['count'] if store_products_result else 0

                if store_products_count > 0:
                    return Respons(
                        success=False,
                        detail=f"Cannot permanently delete product. It has {store_products_count} active store product(s). Please delete all store products first.",
                        error="RELATED_RECORDS_EXIST",
                    )

                # Check for warehouse products
                cursor.execute(
                    f"""SELECT COUNT(*) as count FROM {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE}
                    WHERE product_id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )
                warehouse_products_result = cursor.fetchone()
                warehouse_products_count = warehouse_products_result['count'] if warehouse_products_result else 0

                if warehouse_products_count > 0:
                    return Respons(
                        success=False,
                        detail=f"Cannot permanently delete product. It has {warehouse_products_count} active warehouse product(s). Please delete all warehouse products first.",
                        error="RELATED_RECORDS_EXIST",
                    )

                # Log activity before permanent deletion
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-product",
                        resource_id=data.product_id,
                        action="delete",
                        old_data=product_dict,
                        new_data=None,
                        description=f"Product {data.product_id} permanently deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)
                    # ActivityLogService.log_activity handles savepoint rollback internally
                    # If it still raises an exception, the transaction is already aborted

                # Delete metadata associations
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE}
                    WHERE product_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )

                # Delete document associations
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_DOCUMENT_IDS_TABLE}
                    WHERE product_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )

                # Get all batch_locations for this product (across all locations)
                cursor.execute(
                    f"""SELECT purchase_batche_id, qty FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND purchase_batche_id IN (
                        SELECT id FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND product_id = %s
                    )""",
                    (tenant_id, org_id, bus_id, tenant_id, org_id, bus_id, data.product_id),
                )
                batch_locations = cursor.fetchall()

                # Delete all batch_locations for this product
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
                        AND purchase_batche_id IN ({placeholders})""",
                        (tenant_id, org_id, bus_id, *batch_ids),
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

                # Delete all movements (both IN and OUT) for this product
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND product_id = %s""",
                    (tenant_id, org_id, bus_id, data.product_id),
                )
                deleted_movements_count = cursor.rowcount

                # Permanently delete the product
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.product_id, tenant_id, org_id, bus_id),
                )

                logger.info(
                    f"Product permanently deleted successfully: {data.product_id}. "
                    f"Deleted {deleted_batch_locations_count} batch location(s) and {deleted_movements_count} movement(s) (IN and OUT).",
                    extra={
                        "extra_fields": {
                            "product_id": data.product_id,
                            "deleted_batch_locations_count": deleted_batch_locations_count,
                            "deleted_movements_count": deleted_movements_count,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Product permanently deleted successfully",
                    data=[PermanentDeleteProductServiceReadDto(
                        product_id=data.product_id,
                        message="Product permanently deleted",
                    )],
                )

        except Exception as e:
            logger.error(f"Error permanently deleting product: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to permanently delete product: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetProductStatisticsServiceReadDto]:
        """Get product statistics"""
        logger.info(
            f"Processing get product statistics request",
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
                # Build WHERE clause for products
                where_conditions = [
                    "p.tenant_id = %s",
                    "p.org_id = %s",
                    "p.bus_id = %s",
                    "p.delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id, org_id, bus_id]
                where_clause = " AND ".join(where_conditions)

                # Get basic product statistics
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_products,
                        SUM(CASE WHEN p.is_active = true THEN 1 ELSE 0 END) as active_products,
                        SUM(CASE WHEN p.is_active = false THEN 1 ELSE 0 END) as inactive_products
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    WHERE {where_clause}""",
                    tuple(params),
                )
                basic_stats = cursor.fetchone()

                # Get products with batches count
                cursor.execute(
                    f"""SELECT COUNT(DISTINCT p.id) as products_with_batches
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb 
                        ON p.id = pb.product_id 
                        AND p.tenant_id = pb.tenant_id 
                        AND p.org_id = pb.org_id 
                        AND p.bus_id = pb.bus_id
                    WHERE {where_clause}
                    AND pb.delete_status = 'NOT_DELETED'""",
                    tuple(params),
                )
                products_with_batches_result = cursor.fetchone()

                # Get products with remaining quantity > 0 and = 0
                # Calculate remaining_qty per product by summing qty_remaining from active batches
                cursor.execute(
                    f"""SELECT 
                        p.id,
                        COALESCE(SUM(CASE WHEN pb.status NOT IN ('VOID', 'CANCELLED') AND pb.is_active = true AND pb.delete_status = 'NOT_DELETED' THEN pb.qty_remaining ELSE 0 END), 0) as remaining_qty
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    LEFT JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb 
                        ON p.id = pb.product_id 
                        AND p.tenant_id = pb.tenant_id 
                        AND p.org_id = pb.org_id 
                        AND p.bus_id = pb.bus_id
                        AND pb.delete_status = 'NOT_DELETED'
                    WHERE {where_clause}
                    GROUP BY p.id""",
                    tuple(params),
                )
                products_with_qty = cursor.fetchall()

                # Calculate statistics from the results
                # Handle None values from database (SUM can return NULL)
                total_products = int(basic_stats.get('total_products') or 0) if basic_stats else 0
                active_products = int(basic_stats.get('active_products') or 0) if basic_stats else 0
                inactive_products = int(basic_stats.get('inactive_products') or 0) if basic_stats else 0
                products_with_batches = int(products_with_batches_result.get('products_with_batches') or 0) if products_with_batches_result else 0
                products_without_batches = total_products - products_with_batches

                # Calculate products in stock, out of stock, and total remaining quantity
                products_in_stock = 0
                products_out_of_stock = 0
                total_remaining_quantity = 0

                for product_qty in products_with_qty:
                    product_dict = dict(product_qty)
                    remaining_qty_value = product_dict.get('remaining_qty')
                    remaining_qty = int(remaining_qty_value) if remaining_qty_value is not None else 0
                    total_remaining_quantity += remaining_qty
                    if remaining_qty > 0:
                        products_in_stock += 1
                    else:
                        products_out_of_stock += 1

                logger.info(
                    f"Product statistics calculated: total_products={total_products}, "
                    f"active_products={active_products}, inactive_products={inactive_products}, "
                    f"products_with_batches={products_with_batches}, products_without_batches={products_without_batches}, "
                    f"products_in_stock={products_in_stock}, products_out_of_stock={products_out_of_stock}, "
                    f"total_remaining_quantity={total_remaining_quantity}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                        }
                    }
                )

                statistics = GetProductStatisticsServiceReadDto(
                    total_products=total_products,
                    active_products=active_products,
                    inactive_products=inactive_products,
                    products_with_batches=products_with_batches,
                    products_without_batches=products_without_batches,
                    products_in_stock=products_in_stock,
                    products_out_of_stock=products_out_of_stock,
                    total_remaining_quantity=total_remaining_quantity,
                )

                return Respons(
                    success=True,
                    detail="Product statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting product statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get product statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_prices(
        product_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        quantity: int = 1,
        location_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> Respons[dict]:
        """
        Get all calculated prices for a product.
        
        Returns:
            - cost_price: Cost price from product or batch
            - base_selling_price: Base selling price from product
            - actual_price: Actual price from msg_product_prices (with priority logic)
            - price_after_pricing_rule: Price after applying pricing rules
            - price_after_tax: Final price after applying tax rules
            - tax_amount: Total tax amount
            - taxes_applied: List of taxes applied
        """
        from src.utils.pricing_calculator import PricingCalculator
        from datetime import datetime
        
        logger.info(
            f"Calculating prices for product: {product_id}",
            extra={
                "extra_fields": {
                    "product_id": product_id,
                    "tenant_id": tenant_id,
                    "quantity": quantity,
                    "location_id": location_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get product metadata if needed
                product_metadata = None
                if product_id:
                    metadata_data = ProductsService._get_product_metadata(
                        cursor, tenant_id, org_id, bus_id, product_id
                    )
                    if metadata_data:
                        product_metadata = {}
                        for meta in metadata_data:
                            meta_type = (meta.get('type') or '').upper()
                            meta_id = meta.get('id')
                            if meta_type == 'CATEGORY':
                                product_metadata['category_id'] = meta_id
                            elif meta_type == 'TAG':
                                product_metadata['tag_id'] = meta_id
                            elif meta_type == 'BRAND':
                                product_metadata['brand_id'] = meta_id
                            elif meta_type == 'LABEL':
                                product_metadata['label_id'] = meta_id
                
                # Get SKU if not provided
                if not sku and product_id:
                    cursor.execute(
                        f"""SELECT sku FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (product_id, tenant_id, org_id, bus_id)
                    )
                    product = cursor.fetchone()
                    if product:
                        sku = product.get('sku')
                
                # Calculate all prices
                prices = PricingCalculator.calculate_all_prices(
                    cursor=cursor,
                    product_id=product_id,
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    quantity=quantity,
                    location_id=location_id,
                    batch_id=batch_id,
                    sku=sku,
                    product_metadata=product_metadata,
                    current_datetime=datetime.now()
                )

                return Respons(
                    success=True,
                    detail="Product prices calculated successfully",
                    data=[prices],
                )

        except Exception as e:
            logger.error(f"Error calculating product prices: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to calculate product prices: {str(e)}",
                error="INTERNAL_ERROR",
            )

