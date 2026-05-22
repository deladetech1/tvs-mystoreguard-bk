from typing import Optional, List
from src.entities.store_transfers.store_transfers_read_dto import (
    CreateStoreTransferServiceReadDto,
    GetStoreTransferServiceReadDto,
    GetStoreTransfersServiceReadDto,
    ApproveStoreTransferServiceReadDto,
    GetStoreTransferStatisticsServiceReadDto,
    UpdateStoreTransferServiceReadDto,
    DeleteStoreTransferServiceReadDto,
)
from src.entities.store_transfers.store_transfers_write_dto import (
    CreateStoreTransferServiceWriteDto,
    ApproveStoreTransferServiceWriteDto,
    UpdateStoreTransferServiceWriteDto,
    DeleteStoreTransferServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = get_logger("store_transfers_service")


def _do_send_email(to_email: str, subject: str, body: str, mail_sender_email: str, mail_sender_pwd: str):
    """Actually send the email via SMTP (runs in background thread)"""
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
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)


def _send_email_notification(
    to_email: str,
    subject: str,
    body: str,
    tenant_id: str
) -> bool:
    """Send email notification to approver in a background thread"""
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

        # If email credentials are available, send email in background thread
        if mail_sender_email and mail_sender_pwd:
            thread = threading.Thread(
                target=_do_send_email,
                args=(to_email, subject, body, mail_sender_email, mail_sender_pwd),
                daemon=True
            )
            thread.start()
            logger.info(f"Email notification queued for {to_email}")
            return True
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


def _generate_transfer_number(tenant_id: str, org_id: str, bus_id: str, cursor) -> str:
    """Generate unique transfer number"""
    prefix = "STF"
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

    # Generate transfer number: STF-YYYYMMDD-NN (e.g., STF-20251222-01)
    transfer_number = f"{prefix}-{date_str}-{str(count + 1).zfill(2)}"
    return transfer_number


def _extract_cdate_ctime_from_dict(transfer_dict: dict) -> dict:
    """Extract cdate and ctime from cdatetime if not present in dict"""
    if 'cdatetime' in transfer_dict and transfer_dict['cdatetime']:
        cdatetime_value = transfer_dict['cdatetime']
        if isinstance(cdatetime_value, str):
            from datetime import datetime
            try:
                cdatetime_value = datetime.fromisoformat(cdatetime_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Try parsing other formats
                try:
                    cdatetime_value = datetime.strptime(cdatetime_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        cdatetime_value = datetime.strptime(cdatetime_value, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        # If parsing fails, return dict as-is (will cause validation error but that's better than crashing)
                        return transfer_dict

        if 'cdate' not in transfer_dict or not transfer_dict.get('cdate'):
            transfer_dict['cdate'] = cdatetime_value.strftime("%Y-%m-%d")
        if 'ctime' not in transfer_dict or not transfer_dict.get('ctime'):
            transfer_dict['ctime'] = cdatetime_value.strftime("%H:%M:%S")

    return transfer_dict


def _fetch_items_map(tenant_id: str, org_id: str, bus_id: str, transfer_ids: List[str], cursor) -> dict:
    """Fetch transfer line items for the given transfer ids, grouped by transfer_id.

    Returns {transfer_id: [{id, product_id, qty, status, product_name}, ...]}.
    """
    if not transfer_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(transfer_ids))
    cursor.execute(
        f"""SELECT ti.id, ti.transfer_id, ti.product_id, ti.qty, ti.status,
                   p.name as product_name
        FROM {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE} ti
        LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
            ON ti.product_id = p.id
            AND ti.tenant_id = p.tenant_id
            AND ti.org_id = p.org_id
            AND ti.bus_id = p.bus_id
        WHERE ti.tenant_id = %s AND ti.org_id = %s AND ti.bus_id = %s
        AND ti.transfer_id IN ({placeholders})
        ORDER BY p.name ASC, ti.id ASC""",
        [tenant_id, org_id, bus_id] + list(transfer_ids),
    )
    rows = cursor.fetchall()

    items_map: dict = {}
    for row in rows:
        items_map.setdefault(row['transfer_id'], []).append({
            'id': row['id'],
            'product_id': row['product_id'],
            'qty': row['qty'],
            'status': row['status'],
            'product_name': row.get('product_name'),
        })
    return items_map


def _build_transfer_read_dict(header_row: dict, items_map: dict) -> dict:
    """Build a read-DTO-ready dict from a transfer header row plus its items."""
    transfer_dict = dict(header_row)
    transfer_dict = _extract_cdate_ctime_from_dict(transfer_dict)
    # Map source and destination to source_type and destination_type
    transfer_dict['source_type'] = transfer_dict.get('source')
    transfer_dict['destination_type'] = transfer_dict.get('destination')
    items = items_map.get(header_row['id'], [])
    transfer_dict['items'] = items
    transfer_dict['total_qty'] = sum(item['qty'] for item in items)
    return transfer_dict


class StoreTransfersService:
    """Service class for store transfers operations"""

    @staticmethod
    def _get_store_batches_for_product(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        product_id: str,
        cursor
    ) -> List[dict]:
        """Get batches allocated to a store location for a product in FIFO order"""
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
            AND bl.loc_id = %s AND pb.product_id = %s AND bl.location_type = 'STORE'
            AND bl.qty > 0
            ORDER BY bl.cdatetime ASC, pb.cdatetime ASC""",
            (tenant_id, org_id, bus_id, loc_id, product_id),
        )
        return cursor.fetchall()

    @staticmethod
    def create_store_transfer(
        data: CreateStoreTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        source_loc_id: str,
        created_by: str
    ) -> Respons[CreateStoreTransferServiceReadDto]:
        """Create a new store transfer request with one or more items"""
        logger.info(
            f"Processing store transfer creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "source_loc_id": source_loc_id,
                    "item_count": len(data.items),
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
                # Must have at least one item (also enforced by the DTO)
                if not data.items:
                    return Respons(
                        success=False,
                        detail="At least one item is required to create a transfer",
                        error="NO_ITEMS",
                    )

                # Reject duplicate products within the same transfer
                product_ids = [item.product_id for item in data.items]
                if len(set(product_ids)) != len(product_ids):
                    return Respons(
                        success=False,
                        detail="The same product cannot appear more than once in a transfer",
                        error="DUPLICATE_PRODUCT",
                    )

                # Validate quantities > 0
                for item in data.items:
                    if item.qty <= 0:
                        return Respons(
                            success=False,
                            detail="Quantity cannot be less than or equal to 0",
                            error="INVALID_QUANTITY",
                        )

                # Verify source location exists
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

                # Validate every item: product exists, present in source store, sufficient FIFO qty
                validated_items = []  # list of (product_id, qty, product_name)
                for item in data.items:
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

                    cursor.execute(
                        f"""SELECT id, current_qty FROM {db_settings.MSG_STORE_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, source_loc_id, item.product_id),
                    )
                    source_store_product = cursor.fetchone()
                    if not source_store_product:
                        return Respons(
                            success=False,
                            detail=f"Product {product.get('name', item.product_id)} not found in source store location",
                            error="PRODUCT_NOT_IN_SOURCE",
                        )

                    batches = StoreTransfersService._get_store_batches_for_product(
                        tenant_id=tenant_id,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=source_loc_id,
                        product_id=item.product_id,
                        cursor=cursor
                    )
                    total_available_qty = sum(batch['qty'] for batch in batches)
                    if item.qty > total_available_qty:
                        return Respons(
                            success=False,
                            detail=f"Insufficient quantity for {product.get('name', item.product_id)}. Available: {total_available_qty}, Requested: {item.qty}",
                            error="INSUFFICIENT_QUANTITY",
                        )

                    validated_items.append((item.product_id, item.qty, product.get('name')))

                # Generate transfer number
                transfer_number = _generate_transfer_number(tenant_id, org_id, bus_id, cursor)

                # Create transfer header record
                transfer_id = Helper.generate_unique_identifier(prefix="stf")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    (id, tenant_id, org_id, bus_id, source, source_id, destination, destination_id,
                     status, transfer_number, person_to_approve_id, description,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        transfer_id, tenant_id, org_id, bus_id,
                        'STORE', source_loc_id,
                        data.destination_type, data.destination_id,
                        'PENDING_APPROVAL', transfer_number,
                        data.person_to_approve_id, data.description,
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                transfer = cursor.fetchone()

                # Create line items
                for product_id, qty, _product_name in validated_items:
                    item_id = Helper.generate_unique_identifier(prefix="tfi")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                        (id, tenant_id, org_id, bus_id, transfer_id, product_id, qty, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (item_id, tenant_id, org_id, bus_id, transfer_id, product_id, qty, 'PENDING_APPROVAL'),
                    )

                # Get transfer header with related data
                cursor.execute(
                    f"""SELECT pt.*,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name,
                           approver.email as approver_email
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
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

                items_map = _fetch_items_map(tenant_id, org_id, bus_id, [transfer_id], cursor)
                transfer_dict = _build_transfer_read_dict(transfer_with_details, items_map)

                # Send email notification to approver
                approver_email = transfer_with_details.get('approver_email') if transfer_with_details else approver.get('email')
                if approver_email:
                    items_html = "".join(
                        f"<li>{product_name or product_id}: {qty}</li>"
                        for product_id, qty, product_name in validated_items
                    )
                    email_subject = f"Product Transfer Approval Required - {transfer_number}"
                    email_body = f"""
                    <html>
                    <body>
                        <h2>Product Transfer Approval Required</h2>
                        <p>Hello {approver.get('fullname', 'User')},</p>
                        <p>A product transfer request requires your approval:</p>
                        <ul>
                            <li><strong>Transfer Number:</strong> {transfer_number}</li>
                            <li><strong>From:</strong> {source_location.get('loc_name', 'N/A')}</li>
                            <li><strong>To:</strong> {destination_location.get('loc_name', 'N/A')}</li>
                        </ul>
                        <p><strong>Items:</strong></p>
                        <ul>{items_html}</ul>
                        <p>Please review and approve or reject this transfer request.</p>
                        <p>Thank you.</p>
                    </body>
                    </html>
                    """
                    _send_email_notification(
                        to_email=approver_email,
                        subject=email_subject,
                        body=email_body,
                        tenant_id=tenant_id
                    )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-transfers",
                        resource_id=transfer_id,
                        action="create",
                        old_data=None,
                        new_data=dict(transfer),
                        description=f"Store transfer {transfer_number} created successfully with {len(validated_items)} item(s)",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=source_loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                transfer_read = CreateStoreTransferServiceReadDto(**transfer_dict)

                logger.info(
                    f"Store transfer created successfully: {transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": transfer_id,
                            "transfer_number": transfer_number,
                            "item_count": len(validated_items),
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Store transfer created successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error creating store transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create store transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def _move_product_batches(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        transfer: dict,
        product_id: str,
        qty_to_transfer: int,
        source_location_name: str,
        cursor
    ) -> bool:
        """Move a single product's FIFO batches from source to destination for a transfer."""
        source_id = transfer['source_id']
        destination_id = transfer['destination_id']
        source_type = transfer['source']
        destination_type = transfer['destination']

        # Get source batches in FIFO order
        source_batches = StoreTransfersService._get_store_batches_for_product(
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

        # Format movement reasons based on source and destination types
        if source_type == 'WAREHOUSE' and destination_type == 'STORE':
            move_reason = f'Store product allocation from warehouse: {source_location_name}'
        elif source_type == 'STORE' and destination_type == 'WAREHOUSE':
            move_reason = f'Warehouse product allocation from store: {source_location_name}'
        elif source_type == 'STORE' and destination_type == 'STORE':
            move_reason = f'Store product transfer from: {source_location_name}'
        else:  # WAREHOUSE to WAREHOUSE
            move_reason = f'Warehouse product transfer from: {source_location_name}'

        # Deduct from source batches (FIFO - oldest first)
        remaining_qty = qty_to_transfer
        batches_to_move = []  # (batch_id, qty, batch_cdate, batch_ctime, batch_cdatetime)

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
            out_movement_id = Helper.generate_unique_identifier(prefix="mov")
            cursor.execute(
                f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                 movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    out_movement_id, tenant_id, org_id, bus_id, product_id,
                    batch_id, source_type, source_id,
                    'OUT', qty_to_deduct, move_reason, transfer['id'],
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
            in_movement_id = Helper.generate_unique_identifier(prefix="mov")
            cursor.execute(
                f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                 movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    in_movement_id, tenant_id, org_id, bus_id, product_id,
                    batch_id, destination_type, destination_id,
                    'IN', qty_to_add, move_reason, transfer['id'],
                    cdate, ctime, cdatetime, transfer['created_by']
                ),
            )

        # Update source store product quantity
        cursor.execute(
            f"""UPDATE {db_settings.MSG_STORE_PRODUCTS_TABLE}
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

        return True

    @staticmethod
    def _execute_transfer(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        transfer_id: str,
        cursor
    ) -> bool:
        """Execute the transfer by moving every item's batches from source to destination using FIFO"""
        try:
            # Get transfer header
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

            # Get location names for movement reasons
            cursor.execute(
                f"""SELECT id, loc_name FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                WHERE tenant_id = %s AND id IN (%s, %s)""",
                (tenant_id, source_id, destination_id),
            )
            locations = cursor.fetchall()
            location_map = {loc['id']: loc['loc_name'] for loc in locations}
            source_location_name = location_map.get(source_id, 'Unknown Location')

            # Get all line items for the transfer
            cursor.execute(
                f"""SELECT id, product_id, qty FROM {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND transfer_id = %s""",
                (tenant_id, org_id, bus_id, transfer_id),
            )
            items = cursor.fetchall()
            if not items:
                return False

            # Move each item
            for item in items:
                moved = StoreTransfersService._move_product_batches(
                    tenant_id=tenant_id,
                    org_id=org_id,
                    bus_id=bus_id,
                    transfer=transfer,
                    product_id=item['product_id'],
                    qty_to_transfer=item['qty'],
                    source_location_name=source_location_name,
                    cursor=cursor
                )
                if not moved:
                    return False

            # Mark items as COMPLETED
            cursor.execute(
                f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                SET status = 'COMPLETED'
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND transfer_id = %s""",
                (tenant_id, org_id, bus_id, transfer_id),
            )

            # Update transfer header status to COMPLETED
            cursor.execute(
                f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                SET status = 'COMPLETED'
                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                (transfer_id, tenant_id, org_id, bus_id),
            )

            return True

        except Exception as e:
            logger.error(f"Error executing transfer: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def approve_store_transfer(
        data: ApproveStoreTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        approved_by: str
    ) -> Respons[ApproveStoreTransferServiceReadDto]:
        """Approve or reject a store transfer"""
        logger.info(
            f"Processing store transfer approval/rejection",
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

                # If approving, validate available quantity for every item BEFORE updating status
                if new_status == 'APPROVED':
                    cursor.execute(
                        f"""SELECT ti.product_id, ti.qty, p.name as product_name
                        FROM {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE} ti
                        LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                            ON ti.product_id = p.id AND ti.tenant_id = p.tenant_id
                            AND ti.org_id = p.org_id AND ti.bus_id = p.bus_id
                        WHERE ti.tenant_id = %s AND ti.org_id = %s AND ti.bus_id = %s
                        AND ti.transfer_id = %s""",
                        (tenant_id, org_id, bus_id, data.transfer_id),
                    )
                    items = cursor.fetchall()
                    if not items:
                        return Respons(
                            success=False,
                            detail="Transfer has no items to approve",
                            error="NO_ITEMS",
                        )

                    for item in items:
                        batches = StoreTransfersService._get_store_batches_for_product(
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            loc_id=transfer['source_id'],
                            product_id=item['product_id'],
                            cursor=cursor
                        )
                        total_available_qty = sum(batch['qty'] for batch in batches)
                        if item['qty'] > total_available_qty:
                            return Respons(
                                success=False,
                                detail=f"Insufficient quantity available for {item.get('product_name') or item['product_id']}. Available: {total_available_qty}, Requested: {item['qty']}. The source location may have been depleted since the transfer was created.",
                                error="INSUFFICIENT_QUANTITY",
                            )

                # Update transfer header status
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    SET status = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (new_status, data.transfer_id, tenant_id, org_id, bus_id),
                )

                # Update item statuses to match
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                    SET status = %s
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND transfer_id = %s""",
                    (new_status, tenant_id, org_id, bus_id, data.transfer_id),
                )

                # If approved, execute the transfer
                if new_status == 'APPROVED':
                    success = StoreTransfersService._execute_transfer(
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
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                            SET status = %s
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND transfer_id = %s""",
                            (old_status, tenant_id, org_id, bus_id, data.transfer_id),
                        )
                        return Respons(
                            success=False,
                            detail="Failed to execute transfer. Please try again.",
                            error="TRANSFER_EXECUTION_FAILED",
                        )

                # Get updated transfer header with details
                cursor.execute(
                    f"""SELECT pt.*,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
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

                items_map = _fetch_items_map(tenant_id, org_id, bus_id, [data.transfer_id], cursor)

                # Log activity
                try:
                    old_data = dict(transfer)
                    new_data = dict(updated_transfer)
                    action = "approve" if new_status == 'APPROVED' else "reject"
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-transfers",
                        resource_id=data.transfer_id,
                        action=action,
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Store transfer {transfer['transfer_number']} {action}d" + (f" (reason: {data.reason})" if data.reason else ""),
                        performed_by=approved_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=transfer['source_id'],
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                transfer_dict = _build_transfer_read_dict(updated_transfer, items_map)
                transfer_read = ApproveStoreTransferServiceReadDto(**transfer_dict)

                action_msg = "approved" if new_status == 'APPROVED' else "rejected"
                logger.info(
                    f"Store transfer {action_msg} successfully: {data.transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": data.transfer_id,
                            "action": action_msg,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail=f"Store transfer {action_msg} successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error approving/rejecting store transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to process transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_store_transfer(
        transfer_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetStoreTransferServiceReadDto]:
        """Get a single store transfer by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT pt.*,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} sl
                        ON pt.source_id = sl.id AND pt.tenant_id = sl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} dl
                        ON pt.destination_id = dl.id AND pt.tenant_id = dl.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator
                        ON pt.created_by = creator.id AND pt.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} approver
                        ON pt.person_to_approve_id = approver.id AND pt.tenant_id = approver.tenant_id
                    WHERE pt.tenant_id = %s AND pt.org_id = %s AND pt.bus_id = %s
                    AND pt.id = %s AND pt.source = 'STORE'""",
                    (tenant_id, org_id, bus_id, transfer_id),
                )
                transfer = cursor.fetchone()

                if not transfer:
                    return Respons(
                        success=False,
                        detail="Store transfer not found",
                        error="TRANSFER_NOT_FOUND",
                    )

                items_map = _fetch_items_map(tenant_id, org_id, bus_id, [transfer_id], cursor)
                transfer_dict = _build_transfer_read_dict(transfer, items_map)
                transfer_read = GetStoreTransferServiceReadDto(**transfer_dict)

                return Respons(
                    success=True,
                    detail="Store transfer retrieved successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error getting store transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get store transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_store_transfers(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        source_loc_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetStoreTransfersServiceReadDto]]:
        """Get list of store transfers with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "pt.tenant_id = %s",
                    "pt.org_id = %s",
                    "pt.bus_id = %s",
                    "pt.source = 'STORE'"
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

                # Get transfer headers
                cursor.execute(
                    f"""SELECT pt.*,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
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

                transfer_ids = [transfer['id'] for transfer in transfers]
                items_map = _fetch_items_map(tenant_id, org_id, bus_id, transfer_ids, cursor)

                transfers_list = []
                for transfer in transfers:
                    transfer_dict = _build_transfer_read_dict(transfer, items_map)
                    transfers_list.append(GetStoreTransfersServiceReadDto(**transfer_dict))

                return Respons(
                    success=True,
                    detail="Store transfers retrieved successfully",
                    data=transfers_list,
                    pagination=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting store transfers: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get store transfers: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_store_transfer_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        source_loc_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Respons[GetStoreTransferStatisticsServiceReadDto]:
        """Get store transfer statistics with optional filtering"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause (on transfer header, aliased pt)
                where_conditions = [
                    "pt.tenant_id = %s",
                    "pt.org_id = %s",
                    "pt.bus_id = %s",
                    "pt.source = 'STORE'",
                ]
                params = [tenant_id, org_id, bus_id]

                if source_loc_id:
                    where_conditions.append("pt.source_id = %s")
                    params.append(source_loc_id)

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

                # Header-level counts
                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_transfers,
                        COALESCE(SUM(CASE WHEN pt.status = 'PENDING_APPROVAL' THEN 1 ELSE 0 END), 0) as total_pending_approval,
                        COALESCE(SUM(CASE WHEN pt.status = 'APPROVED' THEN 1 ELSE 0 END), 0) as total_approved,
                        COALESCE(SUM(CASE WHEN pt.status = 'REJECTED' THEN 1 ELSE 0 END), 0) as total_rejected,
                        COALESCE(SUM(CASE WHEN pt.status = 'COMPLETED' THEN 1 ELSE 0 END), 0) as total_completed
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    WHERE {where_clause}""",
                    tuple(params),
                )
                stats_row = cursor.fetchone() or {}

                # Item-level quantity sums (joined to matching headers)
                cursor.execute(
                    f"""SELECT
                        COALESCE(SUM(ti.qty), 0) as total_quantity,
                        COALESCE(SUM(CASE WHEN pt.status = 'PENDING_APPROVAL' THEN ti.qty ELSE 0 END), 0) as total_quantity_pending
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
                    INNER JOIN {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE} ti
                        ON ti.transfer_id = pt.id AND ti.tenant_id = pt.tenant_id
                        AND ti.org_id = pt.org_id AND ti.bus_id = pt.bus_id
                    WHERE {where_clause}""",
                    tuple(params),
                )
                qty_row = cursor.fetchone() or {}

                from decimal import Decimal, ROUND_HALF_UP

                total_transfers = int(stats_row.get('total_transfers', 0)) if stats_row else 0
                total_pending_approval = int(stats_row.get('total_pending_approval', 0)) if stats_row else 0
                total_approved = int(stats_row.get('total_approved', 0)) if stats_row else 0
                total_rejected = int(stats_row.get('total_rejected', 0)) if stats_row else 0
                total_completed = int(stats_row.get('total_completed', 0)) if stats_row else 0

                # Round quantities to 2 decimal places
                two_places = Decimal('0.01')
                total_quantity = Decimal(str(qty_row.get('total_quantity', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if qty_row else Decimal('0')
                total_quantity_pending = Decimal(str(qty_row.get('total_quantity_pending', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if qty_row else Decimal('0')
                # Average quantity per transfer
                if total_transfers > 0:
                    average_quantity = (total_quantity / Decimal(total_transfers)).quantize(two_places, rounding=ROUND_HALF_UP)
                else:
                    average_quantity = Decimal('0')

                logger.info(
                    f"Store transfer statistics calculated: total_transfers={total_transfers}, "
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

                statistics = GetStoreTransferStatisticsServiceReadDto(
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
                    detail="Store transfer statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting store transfer statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get store transfer statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_store_transfer(
        data: UpdateStoreTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdateStoreTransferServiceReadDto]:
        """Update a store transfer (only allowed when status is PENDING_APPROVAL)"""
        logger.info(
            f"Processing store transfer update",
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
                    AND id = %s AND source = 'STORE'""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                transfer = cursor.fetchone()
                if not transfer:
                    return Respons(
                        success=False,
                        detail="Store transfer not found",
                        error="TRANSFER_NOT_FOUND",
                    )

                # Only allow updates when status is PENDING_APPROVAL
                if transfer['status'] != 'PENDING_APPROVAL':
                    return Respons(
                        success=False,
                        detail=f"Cannot update transfer with status {transfer['status']}. Only transfers with PENDING_APPROVAL status can be updated.",
                        error="INVALID_STATUS",
                    )

                # Build header update fields
                update_fields = []
                update_values = []

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

                # Validate items replacement if provided
                validated_items = None
                if data.items is not None:
                    if not data.items:
                        return Respons(
                            success=False,
                            detail="Items list cannot be empty",
                            error="NO_ITEMS",
                        )

                    product_ids = [item.product_id for item in data.items]
                    if len(set(product_ids)) != len(product_ids):
                        return Respons(
                            success=False,
                            detail="The same product cannot appear more than once in a transfer",
                            error="DUPLICATE_PRODUCT",
                        )

                    validated_items = []
                    for item in data.items:
                        if item.qty <= 0:
                            return Respons(
                                success=False,
                                detail="Quantity must be greater than 0",
                                error="INVALID_QUANTITY",
                            )
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
                        batches = StoreTransfersService._get_store_batches_for_product(
                            tenant_id=tenant_id,
                            org_id=org_id,
                            bus_id=bus_id,
                            loc_id=transfer['source_id'],
                            product_id=item.product_id,
                            cursor=cursor
                        )
                        total_available_qty = sum(batch['qty'] for batch in batches)
                        if item.qty > total_available_qty:
                            return Respons(
                                success=False,
                                detail=f"Insufficient quantity for {product.get('name', item.product_id)}. Available: {total_available_qty}, Requested: {item.qty}",
                                error="INSUFFICIENT_QUANTITY",
                            )
                        validated_items.append((item.product_id, item.qty))

                # If nothing to update, return error
                if not update_fields and validated_items is None:
                    return Respons(
                        success=False,
                        detail="No fields provided to update",
                        error="NO_FIELDS_TO_UPDATE",
                    )

                # Execute header update
                if update_fields:
                    header_values = list(update_values) + [data.transfer_id, tenant_id, org_id, bus_id]
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        tuple(header_values),
                    )

                # Replace items if provided
                if validated_items is not None:
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND transfer_id = %s""",
                        (tenant_id, org_id, bus_id, data.transfer_id),
                    )
                    for product_id, qty in validated_items:
                        item_id = Helper.generate_unique_identifier(prefix="tfi")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                            (id, tenant_id, org_id, bus_id, transfer_id, product_id, qty, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (item_id, tenant_id, org_id, bus_id, data.transfer_id, product_id, qty, 'PENDING_APPROVAL'),
                        )

                # Get updated transfer header with details
                cursor.execute(
                    f"""SELECT pt.*,
                           sl.loc_name as source_location_name,
                           dl.loc_name as destination_location_name,
                           creator.fullname as created_by_name,
                           approver.fullname as approver_name,
                           approver.email as approver_email
                    FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE} pt
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

                items_map = _fetch_items_map(tenant_id, org_id, bus_id, [data.transfer_id], cursor)
                transfer_dict = _build_transfer_read_dict(updated_transfer, items_map)

                # Send email notification to approver if transfer was updated
                if updated_transfer and updated_transfer.get('approver_email'):
                    items_html = "".join(
                        f"<li>{item.get('product_name') or item['product_id']}: {item['qty']}</li>"
                        for item in transfer_dict.get('items', [])
                    )
                    email_subject = f"Product Transfer Updated - {updated_transfer['transfer_number']}"
                    email_body = f"""
                    <html>
                    <body>
                        <h2>Product Transfer Updated</h2>
                        <p>Hello {updated_transfer.get('approver_name', 'User')},</p>
                        <p>A product transfer request has been updated and requires your approval:</p>
                        <ul>
                            <li><strong>Transfer Number:</strong> {updated_transfer['transfer_number']}</li>
                            <li><strong>From:</strong> {updated_transfer.get('source_location_name', 'N/A')}</li>
                            <li><strong>To:</strong> {updated_transfer.get('destination_location_name', 'N/A')}</li>
                        </ul>
                        <p><strong>Items:</strong></p>
                        <ul>{items_html}</ul>
                        <p>Please review and approve or reject this transfer request.</p>
                        <p>Thank you.</p>
                    </body>
                    </html>
                    """
                    _send_email_notification(
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
                        resource_type="rt-store-transfers",
                        resource_id=data.transfer_id,
                        action="update",
                        old_data=old_data,
                        new_data=new_data,
                        description=f"Store transfer {transfer['transfer_number']} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=transfer['source_id'],
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                transfer_read = UpdateStoreTransferServiceReadDto(**transfer_dict)

                logger.info(
                    f"Store transfer updated successfully: {data.transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": data.transfer_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Store transfer updated successfully",
                    data=[transfer_read],
                )

        except Exception as e:
            logger.error(f"Error updating store transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update store transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_store_transfer(
        data: DeleteStoreTransferServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[DeleteStoreTransferServiceReadDto]:
        """Delete a store transfer (only allowed when status is PENDING_APPROVAL)"""
        logger.info(
            f"Processing store transfer deletion",
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
                    AND id = %s AND source = 'STORE'""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                transfer = cursor.fetchone()
                if not transfer:
                    return Respons(
                        success=False,
                        detail="Store transfer not found",
                        error="TRANSFER_NOT_FOUND",
                    )

                # Only allow deletion when status is PENDING_APPROVAL
                if transfer['status'] != 'PENDING_APPROVAL':
                    return Respons(
                        success=False,
                        detail=f"Cannot delete transfer with status {transfer['status']}. Only transfers with PENDING_APPROVAL status can be deleted.",
                        error="INVALID_STATUS",
                    )

                # Delete line items first, then the header
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_TRANSFER_ITEMS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND transfer_id = %s""",
                    (tenant_id, org_id, bus_id, data.transfer_id),
                )
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PRODUCT_TRANSFERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.transfer_id, tenant_id, org_id, bus_id),
                )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-store-transfers",
                        resource_id=data.transfer_id,
                        action="delete",
                        old_data=dict(transfer),
                        new_data=None,
                        description=f"Store transfer {transfer['transfer_number']} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=transfer['source_id'],
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                delete_read = DeleteStoreTransferServiceReadDto(
                    success=True,
                    message="Store transfer deleted successfully"
                )

                logger.info(
                    f"Store transfer deleted successfully: {data.transfer_id}",
                    extra={
                        "extra_fields": {
                            "transfer_id": data.transfer_id,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Store transfer deleted successfully",
                    data=[delete_read],
                )

        except Exception as e:
            logger.error(f"Error deleting store transfer: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete store transfer: {str(e)}",
                error="INTERNAL_ERROR",
            )
