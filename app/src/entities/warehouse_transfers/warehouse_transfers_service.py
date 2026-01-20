from typing import Optional, List
from src.entities.warehouse_transfers.warehouse_transfers_read_dto import (
    CreateWarehouseTransferServiceReadDto,
    GetWarehouseTransferServiceReadDto,
    GetWarehouseTransfersServiceReadDto,
    ApproveWarehouseTransferServiceReadDto,
    GetWarehouseTransferStatisticsServiceReadDto,
    UpdateWarehouseTransferServiceReadDto,
    DeleteWarehouseTransferServiceReadDto,
)
from src.entities.warehouse_transfers.warehouse_transfers_write_dto import (
    CreateWarehouseTransferServiceWriteDto,
    ApproveWarehouseTransferServiceWriteDto,
    UpdateWarehouseTransferServiceWriteDto,
    DeleteWarehouseTransferServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = get_logger("warehouse_transfers_service")


def _send_email_notification_warehouse(
    to_email: str,
    subject: str,
    body: str,
    tenant_id: str
) -> bool:
    """Send email notification to approver"""
    try:
        if not to_email:
            logger.warning("No email address provided for notification")
            return False
            
        logger.info(
            f"Sending email notification",
            extra={
                "extra_fields": {
                    "to": to_email,
                    "subject": subject,
                    "tenant_id": tenant_id,
                }
            }
        )
        
        # Get email credentials (tenant-specific or system default)
        mail_sender_email, mail_sender_pwd = Helper.get_email_credentials(tenant_id)
        
        # If email credentials are available, send email
        if mail_sender_email and mail_sender_pwd:
            try:
                msg = MIMEMultipart()
                msg['From'] = mail_sender_email
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'html'))
                
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(mail_sender_email, mail_sender_pwd)
                server.send_message(msg)
                server.quit()
                logger.info(f"Email sent successfully to {to_email}")
                return True
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}", exc_info=True)
                return False
        else:
            logger.warning(
                "Email credentials not configured. Email notification not sent.",
                extra={
                    "extra_fields": {
                        "to": to_email,
                        "subject": subject,
                        "tenant_id": tenant_id,
                    }
                }
            )
            return False
    except Exception as e:
        logger.error(f"Error in email notification: {str(e)}", exc_info=True)
        return False


def _generate_warehouse_transfer_number(tenant_id: str, org_id: str, bus_id: str, cursor) -> str:
    """Generate unique warehouse transfer number"""
    prefix = "WTF"
    cdate = Helper.current_date_time()["cdate"]
    # Format: YYYYMMDD (e.g., 20251222)
    date_str = cdate.replace("-", "")
    
    # Get count of transfers for this specific day
    cursor.execute(
        f"""SELECT COUNT(*) as count FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
        AND transfer_number LIKE %s""",
        (tenant_id, org_id, bus_id, f"{prefix}-{date_str}-%"),
    )
    result = cursor.fetchone()
    count = result['count'] if result else 0
    
    # Generate transfer number: WTF-YYYYMMDD-NN (e.g., WTF-20251222-01)
    transfer_number = f"{prefix}-{date_str}-{str(count + 1).zfill(2)}"
    return transfer_number


class WarehouseTransfersService:
    """Service class for warehouse transfers operations"""

    @staticmethod
    def _get_warehouse_batches_for_product(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        product_id: str,
        cursor
    ) -> List[dict]:
        """Get batches allocated to a warehouse location for a product in FIFO order"""
        cursor.execute(
            f"""SELECT bl.*, pb.batch_number, pb.cdate as batch_cdate, 
                   pb.ctime as batch_ctime, pb.cdatetime as batch_cdatetime
            FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
            INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb 
                ON bl.purchase_batche_id = pb.id 
                AND bl.tenant_id = pb.tenant_id 
                AND bl.org_id = pb.org_id 
                AND bl.bus_id = pb.bus_id
            WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s 
            AND bl.loc_id = %s AND pb.product_id = %s AND bl.location_type = 'WAREHOUSE'
            AND bl.qty > 0
            ORDER BY bl.cdatetime ASC, pb.cdatetime ASC""",
            (tenant_id, org_id, bus_id, loc_id, product_id),
        )
        return cursor.fetchall()

    @staticmethod
    def create_warehouse_transfer(
        data: CreateWarehouseTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        source_loc_id: str,
        created_by: str
    ) -> Respons[CreateWarehouseTransferServiceReadDto]:
        """Create a new warehouse transfer request"""
        logger.info(
            f"Processing warehouse transfer creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "source_loc_id": source_loc_id,
                    "product_id": data.product_id,
                    "qty": data.qty,
                    "destination_type": data.destination_type,
                    "destination_id": data.destination_id,
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
                    f"""SELECT id, name FROM {db_settings.MSG_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.product_id),
                )
                product = cursor.fetchone()
                if not product:
                    return Respons(
                        success=False,
                        detail=f"Product {data.product_id} not found",
                        error="PRODUCT_NOT_FOUND",
                    )

                # Verify source location exists and is a WAREHOUSE
                cursor.execute(
                    f"""SELECT id, loc_name FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND id = %s""",
                    (tenant_id, source_loc_id),
                )
                source_location = cursor.fetchone()
                if not source_location:
                    return Respons(
                        success=False,
                        detail=f"Source location {source_loc_id} not found",
                        error="SOURCE_LOCATION_NOT_FOUND",
                    )

                # Verify destination location exists
                cursor.execute(
                    f"""SELECT id, loc_name FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND id = %s""",
                    (tenant_id, data.destination_id),
                )
                destination_location = cursor.fetchone()
                if not destination_location:
                    return Respons(
                        success=False,
                        detail=f"Destination location {data.destination_id} not found",
                        error="DESTINATION_LOCATION_NOT_FOUND",
                    )

                # Verify source warehouse product exists
                cursor.execute(
                    f"""SELECT id, current_qty FROM {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, source_loc_id, data.product_id),
                )
                source_warehouse_product = cursor.fetchone()
                if not source_warehouse_product:
                    return Respons(
                        success=False,
                        detail=f"Product not found in source warehouse location",
                        error="PRODUCT_NOT_IN_SOURCE",
                    )

                # Check available quantity using FIFO batches
                batches = WarehouseTransfersService._get_warehouse_batches_for_product(
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    loc_id=source_loc_id,
                    product_id=data.product_id,
                    cursor=cursor
                )

                total_available_qty = sum(batch['qty'] for batch in batches)

                if data.qty > total_available_qty:
                    return Respons(
                        success=False,
                        detail=f"Insufficient quantity. Available: {total_available_qty}, Requested: {data.qty}",
                        error="INSUFFICIENT_QUANTITY",
                    )

                # Verify approver exists
                cursor.execute(
                    f"""SELECT id, email, fullname FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                    WHERE tenant_id = %s AND id = %s""",
                    (tenant_id, data.person_to_approve_id),
                )
                approver = cursor.fetchone()
                if not approver:
                    return Respons(
                        success=False,
                        detail=f"Approver {data.person_to_approve_id} not found",
                        error="APPROVER_NOT_FOUND",
                    )

                # Generate transfer number
                transfer_number = _generate_warehouse_transfer_number(tenant_id, org_id, bus_id, cursor)

                # Create transfer record
                transfer_id = Helper.generate_unique_identifier(prefix="whf")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    (id, tenant_id, org_id, bus_id, source, source_id, destination, destination_id,
                     product_id, qty, status, transfer_number, person_to_approve_id, description,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        transfer_id, tenant_id, org_id, bus_id,
                        'WAREHOUSE', source_loc_id,
                        data.destination_type, data.destination_id,
                        data.product_id, data.qty, 'PENDING_APPROVAL', transfer_number,
                        data.person_to_approve_id, data.description,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                transfer = cursor.fetchone()

                # Get transfer with related data
                cursor.execute(
                    f"""SELECT pt.*,
                           p.name as product_name,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name,
                           approver.email as approver_email
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p 
                        ON pt.product_id = p.id 
                        AND pt.tenant_id = p.tenant_id 
                        AND pt.org_id = p.org_id 
                        AND pt.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} sl 
                        ON pt.source_id = sl.id AND pt.tenant_id = sl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} dl 
                        ON pt.destination_id = dl.id AND pt.tenant_id = dl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                        ON pt.created_by = creator.id AND pt.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} approver 
                        ON pt.person_to_approve_id = approver.id AND pt.tenant_id = approver.tenant_id
                    WHERE pt.tenant_id = %s AND pt.org_id = %s AND pt.bus_id = %s 
                    AND pt.id = %s""",
                    (tenant_id, org_id, bus_id, transfer_id),
                )
                transfer_with_details = cursor.fetchone()

                # Send email notification to approver
                approver_email = transfer_with_details.get('approver_email') if transfer_with_details else approver.get('email')
                if approver_email:
                    email_subject = f"Product Transfer Approval Required - {transfer_number}"
                    email_body = f"""
                    <html>
                    <body>
                        <h2>Product Transfer Approval Required</h2>
                        <p>Hello {approver.get('fullname', 'User')},</p>
                        <p>A product transfer request requires your approval:</p>
                        <ul>
                            <li><strong>Transfer Number:</strong> {transfer_number}</li>
                            <li><strong>Product:</strong> {product.get('name', 'N/A')}</li>
                            <li><strong>Quantity:</strong> {data.qty}</li>
                            <li><strong>From:</strong> {source_location.get('loc_name', 'N/A')}</li>
                            <li><strong>To:</strong> {destination_location.get('loc_name', 'N/A')}</li>
                        </ul>
                        <p>Please review and approve or reject this transfer request.</p>
                        <p>Thank you.</p>
                    </body>
                    </html>
                    """
                    _send_email_notification_warehouse(
                        to_email=approver_email,
                        subject=email_subject,
                        body=email_body,
                        tenant_id=tenant_id
                    )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-warehouse-transfers",
                        resource_id=transfer_id,
                        action="create",
                        old_data=None,
                        new_data=dict(transfer),
                        description=f"Warehouse transfer {transfer_number} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=source_loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                transfer_dict = dict(transfer_with_details)
                # Map source and destination to source_type and destination_type
                transfer_dict['source_type'] = transfer_dict.get('source')
                transfer_dict['destination_type'] = transfer_dict.get('destination')
                transfer_read = CreateWarehouseTransferServiceReadDto(**transfer_dict)

                logger.info(
                    f"Warehouse transfer created successfully: {transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": transfer_id,
                            "transfer_number": transfer_number,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Warehouse transfer created successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error creating warehouse transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create warehouse transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def _execute_warehouse_transfer(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        transfer_id: str,
        cursor
    ) -> bool:
        """Execute the transfer by moving batches from source to destination using FIFO"""
        try:
            # Get transfer details
            cursor.execute(
                f"""SELECT * FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND id = %s AND status = 'APPROVED'""",
                (tenant_id, org_id, bus_id, transfer_id),
            )
            transfer = cursor.fetchone()
            if not transfer:
                return False

            source_id = transfer['source_id']
            destination_id = transfer['destination_id']
            product_id = transfer['product_id']
            qty_to_transfer = transfer['qty']
            source_type = transfer['source']  # 'WAREHOUSE' for warehouse transfers
            destination_type = transfer['destination']

            # Get location names for movement reasons
            cursor.execute(
                f"""SELECT id, loc_name FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                WHERE tenant_id = %s AND id IN (%s, %s)""",
                (tenant_id, source_id, destination_id),
            )
            locations = cursor.fetchall()
            location_map = {loc['id']: loc['loc_name'] for loc in locations}
            source_location_name = location_map.get(source_id, 'Unknown Location')
            destination_location_name = location_map.get(destination_id, 'Unknown Location')

            # Get source batches in FIFO order
            source_batches = WarehouseTransfersService._get_warehouse_batches_for_product(
                tenant_id=tenant_id,
                org_id=org_id,
                bus_id=bus_id,
                loc_id=source_id,
                product_id=product_id,
                cursor=cursor
            )

            if not source_batches:
                return False

            # Calculate total available
            total_available = sum(batch['qty'] for batch in source_batches)
            if qty_to_transfer > total_available:
                return False

            # Prepare datetime for movements
            cdate = Helper.current_date_time()["cdate"]
            ctime = Helper.current_date_time()["ctime"]
            cdatetime = Helper.current_date_time()["cdatetime"]

            # Deduct from source batches (FIFO - oldest first)
            remaining_qty = qty_to_transfer
            batches_to_move = []  # Store (batch_id, qty, batch_created_at) for destination insertion

            for batch in source_batches:
                if remaining_qty <= 0:
                    break

                batch_location_id = batch['id']
                batch_id = batch['purchase_batche_id']
                current_qty = batch['qty']
                batch_cdate = batch.get('batch_cdate') or batch.get('cdate')
                batch_ctime = batch.get('batch_ctime') or batch.get('ctime')
                batch_cdatetime = batch.get('batch_cdatetime') or batch.get('cdatetime')

                qty_to_deduct = min(remaining_qty, current_qty)

                if current_qty == qty_to_deduct:
                    # Delete batch location entry
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (batch_location_id, tenant_id, org_id, bus_id),
                    )
                else:
                    # Update batch location quantity
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        SET qty = qty - %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (qty_to_deduct, batch_location_id, tenant_id, org_id, bus_id),
                    )

                # Create OUT movement (product leaving source location)
                # Format reason based on source and destination types
                if source_type == 'WAREHOUSE' and destination_type == 'STORE':
                    out_reason = f'Store product allocation from warehouse: {source_location_name}'
                elif source_type == 'STORE' and destination_type == 'WAREHOUSE':
                    out_reason = f'Warehouse product allocation from store: {source_location_name}'
                elif source_type == 'STORE' and destination_type == 'STORE':
                    out_reason = f'Store product transfer from: {source_location_name}'
                else:  # WAREHOUSE to WAREHOUSE
                    out_reason = f'Warehouse product transfer from: {source_location_name}'
                
                out_movement_id = Helper.generate_unique_identifier(prefix="mov")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                     movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        out_movement_id, tenant_id, org_id, bus_id, product_id,
                        batch_id, source_type, source_id,
                        'OUT', qty_to_deduct, out_reason, transfer_id,
                        cdate, ctime, cdatetime, transfer['created_by']
                    ),
                )

                # Store for destination insertion (maintain FIFO order)
                batches_to_move.append((batch_id, qty_to_deduct, batch_cdate, batch_ctime, batch_cdatetime))
                remaining_qty -= qty_to_deduct

            # Add to destination location (maintain FIFO order - what was picked first goes in first)
            for batch_id, qty_to_add, batch_cdate, batch_ctime, batch_cdatetime in batches_to_move:
                # Check if batch_location already exists at destination
                cursor.execute(
                    f"""SELECT id, qty FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND purchase_batche_id = %s AND location_type = %s""",
                    (tenant_id, org_id, bus_id, destination_id, batch_id, destination_type),
                )
                existing_batch_location = cursor.fetchone()

                if existing_batch_location:
                    # Update existing batch location
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        SET qty = qty + %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (qty_to_add, existing_batch_location['id'], tenant_id, org_id, bus_id),
                    )
                else:
                    # Insert new batch location (preserve original batch datetime for FIFO)
                    batch_location_id = Helper.generate_unique_identifier(prefix="bloc")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, purchase_batche_id, location_type, qty,
                         cdate, ctime, cdatetime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            batch_location_id, tenant_id, org_id, bus_id, destination_id,
                            batch_id, destination_type, qty_to_add,
                            batch_cdate, batch_ctime, batch_cdatetime
                        ),
                    )

                # Create IN movement (product entering destination location)
                # Format reason based on source and destination types
                if source_type == 'WAREHOUSE' and destination_type == 'STORE':
                    in_reason = f'Store product allocation from warehouse: {source_location_name}'
                elif source_type == 'STORE' and destination_type == 'WAREHOUSE':
                    in_reason = f'Warehouse product allocation from store: {source_location_name}'
                elif source_type == 'STORE' and destination_type == 'STORE':
                    in_reason = f'Store product transfer from: {source_location_name}'
                else:  # WAREHOUSE to WAREHOUSE
                    in_reason = f'Warehouse product transfer from: {source_location_name}'
                
                in_movement_id = Helper.generate_unique_identifier(prefix="mov")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                    (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                     movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        in_movement_id, tenant_id, org_id, bus_id, product_id,
                        batch_id, destination_type, destination_id,
                        'IN', qty_to_add, in_reason, transfer_id,
                        cdate, ctime, cdatetime, transfer['created_by']
                    ),
                )

            # Update source warehouse product quantity
            cursor.execute(
                f"""UPDATE {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE}
                SET current_qty = current_qty - %s, updated_by = %s
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                AND loc_id = %s AND product_id = %s""",
                (qty_to_transfer, transfer['created_by'], tenant_id, org_id, bus_id, source_id, product_id),
            )

            # Update or create destination product record
            if destination_type == 'STORE':
                cursor.execute(
                    f"""SELECT id, current_qty FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, destination_id, product_id),
                )
                dest_product = cursor.fetchone()
                if dest_product:
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        SET current_qty = current_qty + %s, updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (qty_to_transfer, transfer['created_by'], dest_product['id'], tenant_id, org_id, bus_id),
                    )
                else:
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        (tenant_id, org_id, bus_id, loc_id, product_id, current_qty,
                         reorder_level, reorder_quantity, is_active, delete_status,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            tenant_id, org_id, bus_id, destination_id, product_id,
                            qty_to_transfer, 0, 0, True, 'NOT_DELETED',
                            cdate, ctime, cdatetime, transfer['created_by']
                        ),
                    )
            else:  # WAREHOUSE
                cursor.execute(
                    f"""SELECT id, current_qty FROM {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, destination_id, product_id),
                )
                dest_product = cursor.fetchone()
                if dest_product:
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE}
                        SET current_qty = current_qty + %s, updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (qty_to_transfer, transfer['created_by'], dest_product['id'], tenant_id, org_id, bus_id),
                    )
                else:
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE}
                        (tenant_id, org_id, bus_id, loc_id, product_id, current_qty,
                         reorder_level, reorder_quantity, is_active, delete_status,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            tenant_id, org_id, bus_id, destination_id, product_id,
                            qty_to_transfer, 0, 0, True, 'NOT_DELETED',
                            cdate, ctime, cdatetime, transfer['created_by']
                        ),
                    )

            # Update transfer status to COMPLETED
            cursor.execute(
                f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                SET status = 'COMPLETED'
                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                (transfer_id, tenant_id, org_id, bus_id),
            )

            return True

        except Exception as e:
            logger.error(f"Error executing warehouse transfer: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def approve_warehouse_transfer(
        data: ApproveWarehouseTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        approved_by: str
    ) -> Respons[ApproveWarehouseTransferServiceReadDto]:
        """Approve or reject a warehouse transfer"""
        logger.info(
            f"Processing warehouse transfer approval/rejection",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "transfer_id": data.transfer_id,
                    "action": data.action,
                    "approved_by": approved_by,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get transfer
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND status = 'PENDING_APPROVAL'""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                transfer = cursor.fetchone()
                if not transfer:
                    return Respons(
                        success=False,
                        detail="Transfer not found or already processed",
                        error="TRANSFER_NOT_FOUND",
                    )

                # Verify approver matches
                if transfer['person_to_approve_id'] != approved_by:
                    return Respons(
                        success=False,
                        detail="You are not authorized to approve this transfer",
                        error="UNAUTHORIZED_APPROVER",
                    )

                old_status = transfer['status']
                # Accept both 'APPROVE' and 'APPROVED' for approval, 'REJECT' and 'REJECTED' for rejection
                action_upper = data.action.upper()
                if action_upper in ['APPROVE', 'APPROVED']:
                    new_status = 'APPROVED'
                elif action_upper in ['REJECT', 'REJECTED']:
                    new_status = 'REJECTED'
                else:
                    return Respons(
                        success=False,
                        detail=f"Invalid action: {data.action}. Must be 'APPROVE'/'APPROVED' or 'REJECT'/'REJECTED'",
                        error="INVALID_ACTION",
                    )

                # If approving, validate available quantity BEFORE updating status
                if new_status == 'APPROVED':
                    # Check available quantity using FIFO batches
                    batches = WarehouseTransfersService._get_warehouse_batches_for_product(
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=transfer['source_id'],
                        product_id=transfer['product_id'],
                        cursor=cursor
                    )
                    
                    total_available_qty = sum(batch['qty'] for batch in batches)
                    
                    if transfer['qty'] > total_available_qty:
                        return Respons(
                            success=False,
                            detail=f"Insufficient quantity available for transfer. Available: {total_available_qty}, Requested: {transfer['qty']}. The source location may have been depleted since the transfer was created.",
                            error="INSUFFICIENT_QUANTITY",
                        )

                # Update transfer status
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    SET status = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (new_status, data.transfer_id, tenant_id, org_id, bus_id),
                )

                # If approved, execute the transfer
                if new_status == 'APPROVED':
                    success = WarehouseTransfersService._execute_warehouse_transfer(
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        transfer_id=data.transfer_id,
                        cursor=cursor
                    )
                    if not success:
                        # Rollback status change (shouldn't happen since we validated above, but safety check)
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                            SET status = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                            (old_status, data.transfer_id, tenant_id, org_id, bus_id),
                        )
                        return Respons(
                            success=False,
                            detail="Failed to execute transfer. Please try again.",
                            error="TRANSFER_EXECUTION_FAILED",
                        )

                # Get updated transfer with details
                cursor.execute(
                    f"""SELECT pt.*,
                           p.name as product_name,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p 
                        ON pt.product_id = p.id 
                        AND pt.tenant_id = p.tenant_id 
                        AND pt.org_id = p.org_id 
                        AND pt.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} sl 
                        ON pt.source_id = sl.id AND pt.tenant_id = sl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} dl 
                        ON pt.destination_id = dl.id AND pt.tenant_id = dl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                        ON pt.created_by = creator.id AND pt.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} approver 
                        ON pt.person_to_approve_id = approver.id AND pt.tenant_id = approver.tenant_id
                    WHERE pt.tenant_id = %s AND pt.org_id = %s AND pt.bus_id = %s 
                    AND pt.id = %s""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                updated_transfer = cursor.fetchone()

                # Log activity
                try:
                    old_data = dict(transfer)
                    new_data = dict(updated_transfer)
                    action = "approve" if new_status == 'APPROVED' else "reject"
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-warehouse-transfers",
                        resource_id=data.transfer_id,
                        action=action,
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Warehouse transfer {transfer['transfer_number']} {action}d" + (f" (reason: {data.reason})" if data.reason else ""),
                        performed_by=approved_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=transfer['source_id'],
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                transfer_dict = dict(updated_transfer)
                # Map source and destination to source_type and destination_type
                transfer_dict['source_type'] = transfer_dict.get('source')
                transfer_dict['destination_type'] = transfer_dict.get('destination')
                transfer_read = ApproveWarehouseTransferServiceReadDto(**transfer_dict)

                action_msg = "approved" if new_status == 'APPROVED' else "rejected"
                logger.info(
                    f"Warehouse transfer {action_msg} successfully: {data.transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": data.transfer_id,
                            "action": action_msg,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail=f"Warehouse transfer {action_msg} successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error approving/rejecting warehouse transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to process transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_warehouse_transfer(
        transfer_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetWarehouseTransferServiceReadDto]:
        """Get a single warehouse transfer by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT pt.*,
                           p.name as product_name,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p 
                        ON pt.product_id = p.id 
                        AND pt.tenant_id = p.tenant_id 
                        AND pt.org_id = p.org_id 
                        AND pt.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} sl 
                        ON pt.source_id = sl.id AND pt.tenant_id = sl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} dl 
                        ON pt.destination_id = dl.id AND pt.tenant_id = dl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                        ON pt.created_by = creator.id AND pt.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} approver 
                        ON pt.person_to_approve_id = approver.id AND pt.tenant_id = approver.tenant_id
                    WHERE pt.tenant_id = %s AND pt.org_id = %s AND pt.bus_id = %s 
                    AND pt.id = %s AND pt.source = 'WAREHOUSE'""",
                    (tenant_id, org_id, bus_id, transfer_id),
                )
                transfer = cursor.fetchone()

                if not transfer:
                    return Respons(
                        success=False,
                        detail="Warehouse transfer not found",
                        error="TRANSFER_NOT_FOUND",
                    )

                transfer_dict = dict(transfer)
                # Map source and destination to source_type and destination_type
                transfer_dict['source_type'] = transfer_dict.get('source')
                transfer_dict['destination_type'] = transfer_dict.get('destination')
                transfer_read = GetWarehouseTransferServiceReadDto(**transfer_dict)

                return Respons(
                    success=True,
                    detail="Warehouse transfer retrieved successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error getting warehouse transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get warehouse transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_warehouse_transfers(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        source_loc_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetWarehouseTransfersServiceReadDto]]:
        """Get list of warehouse transfers with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "pt.tenant_id = %s",
                    "pt.org_id = %s",
                    "pt.bus_id = %s",
                    "pt.source = 'WAREHOUSE'"
                ]
                params = [tenant_id, org_id, bus_id]

                if source_loc_id:
                    where_conditions.append("pt.source_id = %s")
                    params.append(source_loc_id)

                if status:
                    where_conditions.append("pt.status = %s")
                    params.append(status)

                # Date filtering on cdatetime
                if from_date is not None or to_date is not None:
                    if from_date is not None and to_date is not None:
                        where_conditions.append("DATE(pt.cdatetime) >= %s AND DATE(pt.cdatetime) <= %s")
                        params.extend([from_date, to_date])
                    elif from_date is not None:
                        where_conditions.append("DATE(pt.cdatetime) >= %s")
                        params.append(from_date)
                    elif to_date is not None:
                        where_conditions.append("DATE(pt.cdatetime) <= %s")
                        params.append(to_date)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                cursor.execute(
                    f"""SELECT COUNT(*) as total FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
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

                # Get transfers
                cursor.execute(
                    f"""SELECT pt.*,
                           p.name as product_name,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p 
                        ON pt.product_id = p.id 
                        AND pt.tenant_id = p.tenant_id 
                        AND pt.org_id = p.org_id 
                        AND pt.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} sl 
                        ON pt.source_id = sl.id AND pt.tenant_id = sl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} dl 
                        ON pt.destination_id = dl.id AND pt.tenant_id = dl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                        ON pt.created_by = creator.id AND pt.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} approver 
                        ON pt.person_to_approve_id = approver.id AND pt.tenant_id = approver.tenant_id
                    WHERE {where_clause}
                    ORDER BY pt.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    params + [size, offset],
                )
                transfers = cursor.fetchall()

                transfers_list = []
                for transfer in transfers:
                    transfer_dict = dict(transfer)
                    # Map source and destination to source_type and destination_type
                    transfer_dict['source_type'] = transfer_dict.get('source')
                    transfer_dict['destination_type'] = transfer_dict.get('destination')
                    transfers_list.append(GetWarehouseTransfersServiceReadDto(**transfer_dict))

                return Respons(
                    success=True,
                    detail="Warehouse transfers retrieved successfully",
                    data=transfers_list,
                    pagination=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting warehouse transfers: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get warehouse transfers: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_warehouse_transfer_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        source_loc_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Respons[GetWarehouseTransferStatisticsServiceReadDto]:
        """Get warehouse transfer statistics with optional filtering"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "tenant_id = %s",
                    "org_id = %s",
                    "bus_id = %s",
                    "source = 'WAREHOUSE'",
                ]
                params = [tenant_id, org_id, bus_id]

                if source_loc_id:
                    where_conditions.append("source_id = %s")
                    params.append(source_loc_id)

                # Date filtering on cdatetime
                if from_date is not None or to_date is not None:
                    if from_date is not None and to_date is not None:
                        where_conditions.append("DATE(cdatetime) >= %s AND DATE(cdatetime) <= %s")
                        params.extend([from_date, to_date])
                    elif from_date is not None:
                        where_conditions.append("DATE(cdatetime) >= %s")
                        params.append(from_date)
                    elif to_date is not None:
                        where_conditions.append("DATE(cdatetime) <= %s")
                        params.append(to_date)

                where_clause = " AND ".join(where_conditions)

                # Get statistics
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_transfers,
                        COALESCE(SUM(CASE WHEN status = 'PENDING_APPROVAL' THEN 1 ELSE 0 END), 0) as total_pending_approval,
                        COALESCE(SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END), 0) as total_approved,
                        COALESCE(SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END), 0) as total_rejected,
                        COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END), 0) as total_completed,
                        COALESCE(SUM(COALESCE(qty, 0)), 0) as total_quantity,
                        COALESCE(SUM(CASE WHEN status = 'PENDING_APPROVAL' THEN COALESCE(qty, 0) ELSE 0 END), 0) as total_quantity_pending,
                        CASE 
                            WHEN COUNT(*) > 0 THEN COALESCE(AVG(COALESCE(qty, 0)), 0)
                            ELSE 0
                        END as average_quantity
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    WHERE {where_clause}""",
                    tuple(params),
                )
                stats_row = cursor.fetchone()

                if stats_row is None:
                    logger.warning("Statistics query returned no rows - using default values")
                    stats_row = {}

                from decimal import Decimal, ROUND_HALF_UP
                
                total_transfers = int(stats_row.get('total_transfers', 0)) if stats_row else 0
                total_pending_approval = int(stats_row.get('total_pending_approval', 0)) if stats_row else 0
                total_approved = int(stats_row.get('total_approved', 0)) if stats_row else 0
                total_rejected = int(stats_row.get('total_rejected', 0)) if stats_row else 0
                total_completed = int(stats_row.get('total_completed', 0)) if stats_row else 0
                
                # Round quantities to 2 decimal places
                two_places = Decimal('0.01')
                total_quantity = Decimal(str(stats_row.get('total_quantity', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_quantity_pending = Decimal(str(stats_row.get('total_quantity_pending', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                average_quantity = Decimal(str(stats_row.get('average_quantity', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')

                logger.info(
                    f"Warehouse transfer statistics calculated: total_transfers={total_transfers}, "
                    f"total_pending_approval={total_pending_approval}, total_approved={total_approved}, "
                    f"total_rejected={total_rejected}, total_completed={total_completed}, "
                    f"total_quantity={total_quantity}, total_quantity_pending={total_quantity_pending}, "
                    f"average_quantity={average_quantity}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "source_loc_id": source_loc_id,
                            "from_date": from_date,
                            "to_date": to_date,
                        }
                    }
                )

                statistics = GetWarehouseTransferStatisticsServiceReadDto(
                    total_transfers=total_transfers,
                    total_pending_approval=total_pending_approval,
                    total_approved=total_approved,
                    total_rejected=total_rejected,
                    total_completed=total_completed,
                    total_quantity=total_quantity,
                    total_quantity_pending=total_quantity_pending,
                    average_quantity=average_quantity,
                )

                return Respons(
                    success=True,
                    detail="Warehouse transfer statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting warehouse transfer statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get warehouse transfer statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_warehouse_transfer(
        data: UpdateWarehouseTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateWarehouseTransferServiceReadDto]:
        """Update a warehouse transfer (only allowed when status is PENDING_APPROVAL)"""
        logger.info(
            f"Processing warehouse transfer update",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "transfer_id": data.transfer_id,
                    "updated_by": updated_by,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get existing transfer
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND source = 'WAREHOUSE'""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                transfer = cursor.fetchone()
                if not transfer:
                    return Respons(
                        success=False,
                        detail="Warehouse transfer not found",
                        error="TRANSFER_NOT_FOUND",
                    )

                # Only allow updates when status is PENDING_APPROVAL
                if transfer['status'] != 'PENDING_APPROVAL':
                    return Respons(
                        success=False,
                        detail=f"Cannot update transfer with status {transfer['status']}. Only transfers with PENDING_APPROVAL status can be updated.",
                        error="INVALID_STATUS",
                    )

                # Build update fields
                update_fields = []
                update_values = []

                # Validate and update quantity if provided
                if data.qty is not None:
                    if data.qty <= 0:
                        return Respons(
                            success=False,
                            detail="Quantity must be greater than 0",
                            error="INVALID_QUANTITY",
                        )
                    # Check available quantity if qty is being increased
                    if data.qty > transfer['qty']:
                        batches = WarehouseTransfersService._get_warehouse_batches_for_product(
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            loc_id=transfer['source_id'],
                            product_id=transfer['product_id'],
                            cursor=cursor
                        )
                        total_available_qty = sum(batch['qty'] for batch in batches)
                        if data.qty > total_available_qty:
                            return Respons(
                                success=False,
                                detail=f"Insufficient quantity. Available: {total_available_qty}, Requested: {data.qty}",
                                error="INSUFFICIENT_QUANTITY",
                            )
                    update_fields.append("qty = %s")
                    update_values.append(data.qty)

                # Validate and update destination if provided
                if data.destination_id is not None:
                    cursor.execute(
                        f"""SELECT id, loc_name FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.destination_id),
                    )
                    destination_location = cursor.fetchone()
                    if not destination_location:
                        return Respons(
                            success=False,
                            detail=f"Destination location {data.destination_id} not found",
                            error="DESTINATION_LOCATION_NOT_FOUND",
                        )
                    update_fields.append("destination_id = %s")
                    update_values.append(data.destination_id)

                if data.destination_type is not None:
                    update_fields.append("destination = %s")
                    update_values.append(data.destination_type)

                # Validate and update approver if provided
                if data.person_to_approve_id is not None:
                    cursor.execute(
                        f"""SELECT id, email, fullname FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.person_to_approve_id),
                    )
                    approver = cursor.fetchone()
                    if not approver:
                        return Respons(
                            success=False,
                            detail=f"Approver {data.person_to_approve_id} not found",
                            error="APPROVER_NOT_FOUND",
                        )
                    update_fields.append("person_to_approve_id = %s")
                    update_values.append(data.person_to_approve_id)

                # Update description if provided
                if data.description is not None:
                    update_fields.append("description = %s")
                    update_values.append(data.description)

                # If no fields to update, return error
                if not update_fields:
                    return Respons(
                        success=False,
                        detail="No fields provided to update",
                        error="NO_FIELDS_TO_UPDATE",
                    )

                # Execute update
                update_values.extend([data.transfer_id, tenant_id, org_id, bus_id])
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    tuple(update_values),
                )

                # Get updated transfer with details
                cursor.execute(
                    f"""SELECT pt.*,
                           p.name as product_name,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name,
                           approver.email as approver_email
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p 
                        ON pt.product_id = p.id 
                        AND pt.tenant_id = p.tenant_id 
                        AND pt.org_id = p.org_id 
                        AND pt.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} sl 
                        ON pt.source_id = sl.id AND pt.tenant_id = sl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} dl 
                        ON pt.destination_id = dl.id AND pt.tenant_id = dl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                        ON pt.created_by = creator.id AND pt.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} approver 
                        ON pt.person_to_approve_id = approver.id AND pt.tenant_id = approver.tenant_id
                    WHERE pt.tenant_id = %s AND pt.org_id = %s AND pt.bus_id = %s 
                    AND pt.id = %s""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                updated_transfer = cursor.fetchone()

                # Send email notification to approver if transfer was updated
                if updated_transfer and updated_transfer.get('approver_email'):
                    email_subject = f"Product Transfer Updated - {updated_transfer['transfer_number']}"
                    email_body = f"""
                    <html>
                    <body>
                        <h2>Product Transfer Updated</h2>
                        <p>Hello {updated_transfer.get('approver_name', 'User')},</p>
                        <p>A product transfer request has been updated and requires your approval:</p>
                        <ul>
                            <li><strong>Transfer Number:</strong> {updated_transfer['transfer_number']}</li>
                            <li><strong>Product:</strong> {updated_transfer.get('product_name', 'N/A')}</li>
                            <li><strong>Quantity:</strong> {updated_transfer['qty']}</li>
                            <li><strong>From:</strong> {updated_transfer.get('source_location_name', 'N/A')}</li>
                            <li><strong>To:</strong> {updated_transfer.get('destination_location_name', 'N/A')}</li>
                        </ul>
                        <p>Please review and approve or reject this transfer request.</p>
                        <p>Thank you.</p>
                    </body>
                    </html>
                    """
                    _send_email_notification_warehouse(
                        to_email=updated_transfer['approver_email'],
                        subject=email_subject,
                        body=email_body,
                        tenant_id=tenant_id
                    )

                # Log activity
                try:
                    old_data = dict(transfer)
                    new_data = dict(updated_transfer)
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-warehouse-transfers",
                        resource_id=data.transfer_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Warehouse transfer {transfer['transfer_number']} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=transfer['source_id'],
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                transfer_dict = dict(updated_transfer)
                # Map source and destination to source_type and destination_type
                transfer_dict['source_type'] = transfer_dict.get('source')
                transfer_dict['destination_type'] = transfer_dict.get('destination')
                transfer_read = UpdateWarehouseTransferServiceReadDto(**transfer_dict)

                logger.info(
                    f"Warehouse transfer updated successfully: {data.transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": data.transfer_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Warehouse transfer updated successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error updating warehouse transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update warehouse transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_warehouse_transfer(
        data: DeleteWarehouseTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteWarehouseTransferServiceReadDto]:
        """Delete a warehouse transfer (only allowed when status is PENDING_APPROVAL)"""
        logger.info(
            f"Processing warehouse transfer deletion",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "transfer_id": data.transfer_id,
                    "deleted_by": deleted_by,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Get existing transfer
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                    AND id = %s AND source = 'WAREHOUSE'""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                transfer = cursor.fetchone()
                if not transfer:
                    return Respons(
                        success=False,
                        detail="Warehouse transfer not found",
                        error="TRANSFER_NOT_FOUND",
                    )

                # Only allow deletion when status is PENDING_APPROVAL
                if transfer['status'] != 'PENDING_APPROVAL':
                    return Respons(
                        success=False,
                        detail=f"Cannot delete transfer with status {transfer['status']}. Only transfers with PENDING_APPROVAL status can be deleted.",
                        error="INVALID_STATUS",
                    )

                # Delete the transfer
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.transfer_id, tenant_id, org_id, bus_id),
                )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-warehouse-transfers",
                        resource_id=data.transfer_id,
                        action="delete",
                        old_data=dict(transfer),
                        new_data=None,
                        description=f"Warehouse transfer {transfer['transfer_number']} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=transfer['source_id'],
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                delete_read = DeleteWarehouseTransferServiceReadDto(
                    success=True,
                    message="Warehouse transfer deleted successfully"
                )

                logger.info(
                    f"Warehouse transfer deleted successfully: {data.transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": data.transfer_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Warehouse transfer deleted successfully",
                    data=[delete_read],
                )

        except Exception as e:
            logger.error(f"Error deleting warehouse transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete warehouse transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )


