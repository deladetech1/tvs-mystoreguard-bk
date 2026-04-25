from decimal import Decimal
import json
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.entities.store_returns.store_returns_read_dto import (
    CreateReturnServiceReadDto,
    ApproveReturnServiceReadDto,
    RejectReturnServiceReadDto,
    ProcessReturnServiceReadDto,
    GetReturnServiceReadDto,
    GetReturnsServiceReadDto,
    GetReturnStatisticsServiceReadDto,
    ReturnItemReadBase,
)
from src.entities.store_returns.store_returns_write_dto import (
    CreateReturnServiceWriteDto,
    ApproveReturnServiceWriteDto,
    RejectReturnServiceWriteDto,
    ProcessReturnServiceWriteDto,
)
from src.entities.store_returns.store_returns_email_builder import (
    build_return_pending_approval_email,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("store_returns_service")


def _do_send_email(to_email: str, subject: str, body: str, mail_sender_email: str, mail_sender_pwd: str):
    """Send a single email via SMTP (runs in a background thread)."""
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
        logger.info(f"Return approval email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send return approval email to {to_email}: {str(e)}", exc_info=True)


def _send_return_approval_notifications(approver_emails: list, subject: str, body: str, tenant_id: str) -> int:
    """Fire off background SMTP sends for each approver. Returns the number queued."""
    if not approver_emails:
        return 0

    try:
        mail_sender_email, mail_sender_pwd = Helper.get_email_credentials(tenant_id)
    except Exception as e:
        logger.error(f"Failed to load email credentials for tenant {tenant_id}: {str(e)}", exc_info=True)
        return 0

    if not (mail_sender_email and mail_sender_pwd):
        logger.warning(
            "Email credentials not configured. Return approval notifications not sent.",
            extra={"extra_fields": {"tenant_id": tenant_id, "approver_count": len(approver_emails)}},
        )
        return 0

    queued = 0
    for to_email in approver_emails:
        if not to_email:
            continue
        thread = threading.Thread(
            target=_do_send_email,
            args=(to_email, subject, body, mail_sender_email, mail_sender_pwd),
            daemon=True,
        )
        thread.start()
        queued += 1

    logger.info(f"Queued {queued} return approval notification email(s) for tenant {tenant_id}")
    return queued


def _extract_approver_emails(policy: dict) -> list:
    """Normalise the policy.approvers JSONB field into a clean list of email strings."""
    if not policy:
        return []
    raw = policy.get('approvers')
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return []
    if not isinstance(raw, list):
        return []
    return [e.strip() for e in raw if isinstance(e, str) and e.strip()]


class StoreReturnsService:
    """Service class for store returns operations"""

    @staticmethod
    def _round_money(value) -> float:
        """Round to 2 decimal places for money"""
        if value is None:
            return 0.0
        return float(Decimal(str(value)).quantize(Decimal('0.01')))

    @staticmethod
    def _find_applicable_return_policy(cursor, product_id: str, tenant_id: str, org_id: str, bus_id: str, loc_id: str) -> dict | None:
        """
        Find the most applicable return policy for a product.
        Uses the same specificity resolution as pricing rules:
        SKU > PRODUCT > TAG/LABEL/CATEGORY/BRAND > LOCATION > ALL_PRODUCTS
        """
        # Get product details and metadata
        cursor.execute(
            f"""SELECT p.id, p.sku,
                   (SELECT string_agg(m.id, ',') FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                    JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} m ON amp.product_metadata_id = m.id
                        AND amp.tenant_id = m.tenant_id AND amp.org_id = m.org_id AND amp.bus_id = m.bus_id
                    WHERE amp.product_id = p.id AND amp.tenant_id = p.tenant_id
                        AND amp.org_id = p.org_id AND amp.bus_id = p.bus_id
                        AND m.of_type ='category') as category_ids,
                   (SELECT string_agg(m.id, ',') FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                    JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} m ON amp.product_metadata_id = m.id
                        AND amp.tenant_id = m.tenant_id AND amp.org_id = m.org_id AND amp.bus_id = m.bus_id
                    WHERE amp.product_id = p.id AND amp.tenant_id = p.tenant_id
                        AND amp.org_id = p.org_id AND amp.bus_id = p.bus_id
                        AND m.of_type ='tag') as tag_ids,
                   (SELECT string_agg(m.id, ',') FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                    JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} m ON amp.product_metadata_id = m.id
                        AND amp.tenant_id = m.tenant_id AND amp.org_id = m.org_id AND amp.bus_id = m.bus_id
                    WHERE amp.product_id = p.id AND amp.tenant_id = p.tenant_id
                        AND amp.org_id = p.org_id AND amp.bus_id = p.bus_id
                        AND m.of_type ='brand') as brand_ids,
                   (SELECT string_agg(m.id, ',') FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                    JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} m ON amp.product_metadata_id = m.id
                        AND amp.tenant_id = m.tenant_id AND amp.org_id = m.org_id AND amp.bus_id = m.bus_id
                    WHERE amp.product_id = p.id AND amp.tenant_id = p.tenant_id
                        AND amp.org_id = p.org_id AND amp.bus_id = p.bus_id
                        AND m.of_type ='label') as label_ids
            FROM {db_settings.MSG_PRODUCTS_TABLE} p
            WHERE p.id = %s AND p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s""",
            (product_id, tenant_id, org_id, bus_id),
        )
        product = cursor.fetchone()

        if not product:
            return None

        product_dict = dict(product)

        # Build target conditions
        target_conditions = ["policy_target_type = 'ALL_PRODUCTS'"]
        params = []

        # Product
        target_conditions.append("(policy_target_type = 'PRODUCT' AND policy_target_id = %s)")
        params.append(product_id)

        # SKU
        if product_dict.get('sku'):
            target_conditions.append("(policy_target_type = 'SKU' AND policy_target_id = %s)")
            params.append(product_dict['sku'])

        # Location
        target_conditions.append("(policy_target_type = 'LOCATION' AND policy_target_id = %s)")
        params.append(loc_id)

        # Metadata: categories, tags, brands, labels
        for field, target_type in [('category_ids', 'CATEGORY'), ('tag_ids', 'TAG'), ('brand_ids', 'BRAND'), ('label_ids', 'LABEL')]:
            ids_str = product_dict.get(field)
            if ids_str:
                id_list = [i.strip() for i in ids_str.split(',') if i.strip()]
                for meta_id in id_list:
                    target_conditions.append(f"(policy_target_type = '{target_type}' AND policy_target_id = %s)")
                    params.append(meta_id)

        cursor.execute(
            f"""SELECT * FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
              AND is_active = true
              AND (start_datetime IS NULL OR start_datetime <= NOW())
              AND (end_datetime IS NULL OR end_datetime >= NOW())
              AND ({' OR '.join(target_conditions)})
            ORDER BY
                priority DESC,
                CASE policy_target_type
                    WHEN 'SKU' THEN 1
                    WHEN 'PRODUCT' THEN 2
                    WHEN 'TAG' THEN 3
                    WHEN 'LABEL' THEN 3
                    WHEN 'CATEGORY' THEN 3
                    WHEN 'BRAND' THEN 3
                    WHEN 'LOCATION' THEN 4
                    WHEN 'ALL_PRODUCTS' THEN 5
                END,
                cdatetime DESC
            LIMIT 1""",
            (tenant_id, org_id, bus_id, *params),
        )
        policy = cursor.fetchone()
        return dict(policy) if policy else None

    @staticmethod
    def _build_return_read_dto(cursor, return_id: str, tenant_id: str, org_id: str, bus_id: str, loc_id: str) -> dict:
        """Build a complete return read DTO with items, customer name, etc."""
        # Get return with creator/approver names
        cursor.execute(
            f"""SELECT r.*,
                   s.sale_number,
                   c.fullname as customer_name,
                   creator.fullname as created_by_name,
                   approver.fullname as approved_by_name,
                   rejecter.fullname as rejected_by_name,
                   processor.fullname as processed_by_name,
                   rp.name as return_policy_name
            FROM {db_settings.MSG_RETURNS_TABLE} r
            LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                ON r.sale_id = s.id AND r.tenant_id = s.tenant_id AND r.org_id = s.org_id
                AND r.bus_id = s.bus_id AND r.loc_id = s.loc_id
            LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                ON r.customer_id = c.id AND r.tenant_id = c.tenant_id
                AND r.org_id = c.org_id AND r.bus_id = c.bus_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} approver ON r.approved_by = approver.id AND r.tenant_id = approver.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} rejecter ON r.rejected_by = rejecter.id AND r.tenant_id = rejecter.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} processor ON r.processed_by = processor.id AND r.tenant_id = processor.tenant_id
            LEFT JOIN {db_settings.MSG_RETURN_POLICIES_TABLE} rp
                ON r.return_policy_id = rp.id AND r.tenant_id = rp.tenant_id
                AND r.org_id = rp.org_id AND r.bus_id = rp.bus_id
            WHERE r.id = %s AND r.tenant_id = %s AND r.org_id = %s AND r.bus_id = %s AND r.loc_id = %s""",
            (return_id, tenant_id, org_id, bus_id, loc_id),
        )
        return_record = cursor.fetchone()
        if not return_record:
            return None

        return_dict = dict(return_record)
        return_dict['created_by'] = return_dict.pop('created_by_name', None) or return_dict.get('created_by')
        return_dict['approved_by'] = return_dict.pop('approved_by_name', None) or return_dict.get('approved_by')
        return_dict['rejected_by'] = return_dict.pop('rejected_by_name', None) or return_dict.get('rejected_by')
        return_dict['processed_by'] = return_dict.pop('processed_by_name', None) or return_dict.get('processed_by')

        # Get return items
        cursor.execute(
            f"""SELECT ri.*, p.name as product_name
            FROM {db_settings.MSG_RETURN_ITEMS_TABLE} ri
            LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                ON ri.product_id = p.id AND ri.tenant_id = p.tenant_id
                AND ri.org_id = p.org_id AND ri.bus_id = p.bus_id
            WHERE ri.return_id = %s AND ri.tenant_id = %s AND ri.org_id = %s
            AND ri.bus_id = %s AND ri.loc_id = %s
            ORDER BY ri.cdatetime ASC""",
            (return_id, tenant_id, org_id, bus_id, loc_id),
        )
        items = cursor.fetchall()
        return_dict['items'] = [ReturnItemReadBase(**dict(item)) for item in items]

        return return_dict

    @staticmethod
    def create_return(
        data: CreateReturnServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateReturnServiceReadDto]:
        """Create a new return request"""
        logger.info(
            f"Processing return creation for sale: {data.sale_id}",
            extra={"extra_fields": {"sale_id": data.sale_id, "tenant_id": tenant_id}},
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # 1. Validate sale exists and is not cancelled
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_SALES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale = cursor.fetchone()
                if not sale:
                    return Respons(success=False, detail="Sale not found", error="NOT_FOUND")

                sale_dict = dict(sale)
                if sale_dict['status'] == 'CANCELLED':
                    return Respons(success=False, detail="Cannot return items from a cancelled sale", error="INVALID_STATUS")

                # 2. Validate each return item
                total_subtotal = Decimal('0')
                validated_items = []

                for item in data.items:
                    # Fetch original sale item
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_SALES_ITEMS_TABLE}
                        WHERE id = %s AND sale_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (item.sale_item_id, data.sale_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    sale_item = cursor.fetchone()
                    if not sale_item:
                        return Respons(success=False, detail=f"Sale item '{item.sale_item_id}' not found in sale", error="NOT_FOUND")

                    sale_item_dict = dict(sale_item)

                    # Check quantity doesn't exceed what was sold (minus already returned)
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(ri.quantity_returned), 0) as already_returned
                        FROM {db_settings.MSG_RETURN_ITEMS_TABLE} ri
                        JOIN {db_settings.MSG_RETURNS_TABLE} ret ON ri.return_id = ret.id
                            AND ri.tenant_id = ret.tenant_id AND ri.org_id = ret.org_id
                            AND ri.bus_id = ret.bus_id AND ri.loc_id = ret.loc_id
                        WHERE ri.sale_item_id = %s AND ri.tenant_id = %s AND ri.org_id = %s
                        AND ri.bus_id = %s AND ri.loc_id = %s
                        AND ret.status NOT IN ('REJECTED')""",
                        (item.sale_item_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    already_returned_result = cursor.fetchone()
                    already_returned = float(already_returned_result['already_returned']) if already_returned_result else 0

                    available_to_return = float(sale_item_dict['quantity']) - already_returned
                    if item.quantity_returned > available_to_return:
                        return Respons(
                            success=False,
                            detail=f"Cannot return {item.quantity_returned} of '{sale_item_dict['product_name']}'. "
                                   f"Only {available_to_return} available (sold: {sale_item_dict['quantity']}, already returned: {already_returned})",
                            error="QUANTITY_EXCEEDED",
                        )

                    # Calculate unit refund amount (using final_price / quantity = unit price)
                    original_qty = Decimal(str(sale_item_dict['quantity']))
                    original_line_total = Decimal(str(sale_item_dict.get('line_total', 0) or 0))
                    unit_price = (original_line_total / original_qty) if original_qty > 0 else Decimal('0')
                    qty_returned = Decimal(str(item.quantity_returned))
                    line_refund = (unit_price * qty_returned).quantize(Decimal('0.01'))
                    total_subtotal += line_refund

                    # Determine restock based on condition
                    restock = item.condition == 'RESALABLE'

                    validated_items.append({
                        'sale_item': sale_item_dict,
                        'input': item,
                        'unit_refund_amount': float(unit_price.quantize(Decimal('0.01'))),
                        'line_refund_amount': float(line_refund),
                        'restock': restock,
                    })

                # 3. Find applicable return policy (using first item's product for policy lookup)
                first_product_id = validated_items[0]['sale_item']['product_id']
                policy = StoreReturnsService._find_applicable_return_policy(
                    cursor, first_product_id, tenant_id, org_id, bus_id, loc_id
                )

                return_policy_id = None
                restocking_fee_percent = Decimal('0')
                approval_required = False

                if policy:
                    return_policy_id = policy['id']

                    # Check return window
                    sale_date = sale_dict.get('sale_date')
                    if sale_date and policy['return_window_days'] == 0:
                        return Respons(
                            success=False,
                            detail=f"This item is non-returnable per policy '{policy['name']}'",
                            error="NON_RETURNABLE",
                        )

                    if sale_date and policy['return_window_days'] > 0:
                        from datetime import datetime, timedelta
                        if isinstance(sale_date, str):
                            sale_date = datetime.strptime(sale_date, '%Y-%m-%d').date()
                        deadline = sale_date + timedelta(days=policy['return_window_days'])
                        today = datetime.now().date()
                        if today > deadline:
                            return Respons(
                                success=False,
                                detail=f"Return window has expired. Policy '{policy['name']}' allows returns within {policy['return_window_days']} days. "
                                       f"Sale date: {sale_date}, deadline: {deadline}",
                                error="RETURN_WINDOW_EXPIRED",
                            )

                    # Check expired items
                    has_expired = any(vi['input'].condition == 'EXPIRED' for vi in validated_items)
                    if has_expired and not policy.get('allow_expired_returns', False):
                        return Respons(
                            success=False,
                            detail=f"Expired items cannot be returned per policy '{policy['name']}'",
                            error="EXPIRED_NOT_ALLOWED",
                        )

                    restocking_fee_percent = Decimal(str(policy.get('restocking_fee_percent', 0) or 0))

                    # Check approval requirement
                    approval_required = policy.get('approval_required', False)
                    if approval_required and policy.get('approval_threshold_amount') is not None:
                        threshold = Decimal(str(policy['approval_threshold_amount']))
                        if total_subtotal <= threshold:
                            approval_required = False

                # 4. Calculate restocking fee and total refund
                restocking_fee_amount = (total_subtotal * restocking_fee_percent / Decimal('100')).quantize(Decimal('0.01'))
                total_refund_amount = total_subtotal - restocking_fee_amount

                # 5. Determine initial status
                initial_status = 'PENDING' if approval_required else 'APPROVED'

                # 6. Generate return number
                cursor.execute(
                    f"""SELECT COUNT(*) as count FROM {db_settings.MSG_RETURNS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                count_result = cursor.fetchone()
                return_count = (count_result['count'] if count_result else 0) + 1
                return_number = f"RET-{return_count:04d}"

                # 7. Insert return
                return_id = Helper.generate_unique_identifier(prefix="ret")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_RETURNS_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, sale_id, return_number, return_date,
                     return_type, status, reason, reason_notes, refund_method,
                     subtotal_refund_amount, restocking_fee_percent, restocking_fee_amount, total_refund_amount,
                     return_policy_id, approval_required,
                     customer_id,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        return_id, tenant_id, org_id, bus_id, loc_id,
                        data.sale_id, return_number, cdate,
                        data.return_type, initial_status, data.reason, data.reason_notes, data.refund_method,
                        float(total_subtotal), float(restocking_fee_percent), float(restocking_fee_amount), float(total_refund_amount),
                        return_policy_id, approval_required,
                        sale_dict.get('customer_id'),
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                cursor.fetchone()

                # 8. Insert return items
                for vi in validated_items:
                    item_id = Helper.generate_unique_identifier(prefix="rti")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_RETURN_ITEMS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, return_id, sale_item_id,
                         product_id, batch_id, quantity_returned, condition, restock,
                         unit_refund_amount, line_refund_amount, reason,
                         cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            item_id, tenant_id, org_id, bus_id, loc_id, return_id,
                            vi['input'].sale_item_id,
                            vi['sale_item']['product_id'],
                            vi['sale_item'].get('batch_id'),
                            vi['input'].quantity_returned,
                            vi['input'].condition,
                            vi['restock'],
                            vi['unit_refund_amount'],
                            vi['line_refund_amount'],
                            vi['input'].reason,
                            cdate, ctime, cdatetime, created_by
                        ),
                    )

                # 9. Build response
                return_dict = StoreReturnsService._build_return_read_dto(
                    cursor, return_id, tenant_id, org_id, bus_id, loc_id
                )
                return_read = CreateReturnServiceReadDto(**return_dict)

                # 10. Log activity
                try:
                    cursor.execute("SAVEPOINT before_activity_log")
                    try:
                        ActivityLogService.log_activity(
                            tenant_id=tenant_id,
                            resource_type="rt-store-returns",
                            resource_id=return_id,
                            action="create",
                            old_data=None,
                            new_data=return_dict,
                            description=f"Return {return_number} created for sale {sale_dict.get('sale_number', data.sale_id)}",
                            performed_by=created_by,
                            org_id=org_id,
                            bus_id=bus_id,
                            loc_id=loc_id,
                            cursor=cursor
                        )
                        cursor.execute("RELEASE SAVEPOINT before_activity_log")
                    except Exception as log_err:
                        try:
                            cursor.execute("ROLLBACK TO SAVEPOINT before_activity_log")
                            logger.warning(f"Activity log failed (rolled back): {log_err}")
                        except Exception as rb_err:
                            logger.error(f"Savepoint rollback failed: {rb_err}", exc_info=True)
                            raise
                except Exception:
                    pass

                detail = "Return created successfully"
                if initial_status == 'PENDING':
                    detail += " - awaiting approval"
                elif initial_status == 'APPROVED':
                    detail += " - auto-approved (no approval required). Process to complete."

                # 11. Notify approvers (fire-and-forget) when approval is required
                if initial_status == 'PENDING':
                    try:
                        approver_emails = _extract_approver_emails(policy)
                        if approver_emails:
                            subject, body = build_return_pending_approval_email(
                                return_dict, policy, sale_dict
                            )
                            _send_return_approval_notifications(
                                approver_emails, subject, body, tenant_id
                            )
                        else:
                            logger.info(
                                "Return requires approval but policy has no approvers configured",
                                extra={"extra_fields": {"return_id": return_id, "policy_id": policy.get('id') if policy else None}},
                            )
                    except Exception as notify_err:
                        logger.error(
                            f"Failed to dispatch return approval notifications: {str(notify_err)}",
                            exc_info=True,
                        )

                return Respons(success=True, detail=detail, data=[return_read])

        except Exception as e:
            logger.error(f"Error creating return: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to create return: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def approve_return(
        data: ApproveReturnServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        approved_by: str
    ) -> Respons[ApproveReturnServiceReadDto]:
        """Approve a pending return"""
        logger.info(f"Processing return approval: {data.return_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_RETURNS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.return_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Return not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] not in ('PENDING', 'REJECTED'):
                    return Respons(
                        success=False,
                        detail=f"Return is '{old_data['status']}', only PENDING or REJECTED returns can be approved",
                        error="INVALID_STATUS",
                    )

                # Check if this user is an authorized approver for this return's policy
                return_policy_id = old_data.get('return_policy_id')
                if return_policy_id:
                    cursor.execute(
                        f"""SELECT approvers FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (return_policy_id, tenant_id, org_id, bus_id),
                    )
                    policy_record = cursor.fetchone()
                    if policy_record:
                        approvers_list = policy_record.get('approvers')
                        # Parse JSONB if it comes back as string
                        if isinstance(approvers_list, str):
                            import json as _json
                            approvers_list = _json.loads(approvers_list)
                        if approvers_list and len(approvers_list) > 0:
                            # Get the approving user's email
                            cursor.execute(
                                f"""SELECT email FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                                WHERE id = %s AND tenant_id = %s""",
                                (approved_by, tenant_id),
                            )
                            user_record = cursor.fetchone()
                            user_email = user_record.get('email', '') if user_record else ''
                            if user_email not in approvers_list:
                                return Respons(
                                    success=False,
                                    detail=f"You are not an authorized approver for this return policy. Authorized approvers: {', '.join(approvers_list)}",
                                    error="NOT_AUTHORIZED_APPROVER",
                                )

                cdatetime = Helper.current_date_time()["cdatetime"]
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_RETURNS_TABLE}
                    SET status = 'APPROVED', approved_by = %s, approved_at = %s,
                        updated_by = %s, processing_notes = COALESCE(processing_notes || ' | ', '') || %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (
                        approved_by, cdatetime, approved_by,
                        data.notes or 'Approved',
                        data.return_id, tenant_id, org_id, bus_id, loc_id
                    ),
                )
                cursor.fetchone()

                return_dict = StoreReturnsService._build_return_read_dto(
                    cursor, data.return_id, tenant_id, org_id, bus_id, loc_id
                )
                return_read = ApproveReturnServiceReadDto(**return_dict)

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-store-returns",
                        resource_id=data.return_id, action="approve",
                        old_data=old_data, new_data=return_dict,
                        description=f"Return {old_data.get('return_number')} approved",
                        performed_by=approved_by, org_id=org_id, bus_id=bus_id, loc_id=loc_id, cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Return approved successfully. Process to complete.", data=[return_read])

        except Exception as e:
            logger.error(f"Error approving return: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to approve return: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def reject_return(
        data: RejectReturnServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        rejected_by: str
    ) -> Respons[RejectReturnServiceReadDto]:
        """Reject a pending return"""
        logger.info(f"Processing return rejection: {data.return_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_RETURNS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.return_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Return not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] not in ('PENDING', 'APPROVED'):
                    return Respons(
                        success=False,
                        detail=f"Return is '{old_data['status']}', only PENDING or APPROVED returns can be rejected",
                        error="INVALID_STATUS",
                    )

                # Check if this user is an authorized approver for this return's policy
                return_policy_id = old_data.get('return_policy_id')
                if return_policy_id:
                    cursor.execute(
                        f"""SELECT approvers FROM {db_settings.MSG_RETURN_POLICIES_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (return_policy_id, tenant_id, org_id, bus_id),
                    )
                    policy_record = cursor.fetchone()
                    if policy_record:
                        approvers_list = policy_record.get('approvers')
                        if isinstance(approvers_list, str):
                            import json as _json
                            approvers_list = _json.loads(approvers_list)
                        if approvers_list and len(approvers_list) > 0:
                            cursor.execute(
                                f"""SELECT email FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                                WHERE id = %s AND tenant_id = %s""",
                                (rejected_by, tenant_id),
                            )
                            user_record = cursor.fetchone()
                            user_email = user_record.get('email', '') if user_record else ''
                            if user_email not in approvers_list:
                                return Respons(
                                    success=False,
                                    detail=f"You are not an authorized approver for this return policy. Authorized approvers: {', '.join(approvers_list)}",
                                    error="NOT_AUTHORIZED_APPROVER",
                                )

                cdatetime = Helper.current_date_time()["cdatetime"]
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_RETURNS_TABLE}
                    SET status = 'REJECTED', rejected_by = %s, rejected_at = %s,
                        rejection_reason = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (
                        rejected_by, cdatetime, data.rejection_reason, rejected_by,
                        data.return_id, tenant_id, org_id, bus_id, loc_id
                    ),
                )
                cursor.fetchone()

                return_dict = StoreReturnsService._build_return_read_dto(
                    cursor, data.return_id, tenant_id, org_id, bus_id, loc_id
                )
                return_read = RejectReturnServiceReadDto(**return_dict)

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-store-returns",
                        resource_id=data.return_id, action="reject",
                        old_data=old_data, new_data=return_dict,
                        description=f"Return {old_data.get('return_number')} rejected: {data.rejection_reason}",
                        performed_by=rejected_by, org_id=org_id, bus_id=bus_id, loc_id=loc_id, cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Return rejected", data=[return_read])

        except Exception as e:
            logger.error(f"Error rejecting return: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to reject return: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def process_return(
        data: ProcessReturnServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        processed_by: str
    ) -> Respons[ProcessReturnServiceReadDto]:
        """
        Process an approved return: restock items + issue refund.
        This is the final step that actually:
        - Restores inventory for resalable items
        - Creates product movements
        - Creates a refund payment on the original sale
        - Updates sale payment status
        """
        logger.info(f"Processing return: {data.return_id}")

        try:
            with DatabaseManager.transaction() as cursor:
                # 1. Get return and validate status
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_RETURNS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.return_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Return not found", error="NOT_FOUND")

                old_data = dict(existing)
                if old_data['status'] != 'APPROVED':
                    return Respons(
                        success=False,
                        detail=f"Return is '{old_data['status']}', only APPROVED returns can be processed",
                        error="INVALID_STATUS",
                    )

                sale_id = old_data['sale_id']
                cdatetime_dict = Helper.current_date_time()
                cdate = cdatetime_dict["cdate"]
                ctime = cdatetime_dict["ctime"]
                cdatetime = cdatetime_dict["cdatetime"]

                # 2. Get return items
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_RETURN_ITEMS_TABLE}
                    WHERE return_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.return_id, tenant_id, org_id, bus_id, loc_id),
                )
                return_items = cursor.fetchall()

                # 3. Process each item: restock + movements
                for item in return_items:
                    item_dict = dict(item)
                    product_id = item_dict['product_id']
                    quantity = Decimal(str(item_dict['quantity_returned']))
                    batch_id = item_dict.get('batch_id')
                    restock = item_dict.get('restock', False)
                    condition = item_dict.get('condition', 'RESALABLE')

                    if restock and condition == 'RESALABLE':
                        # Restore batch location quantity
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
                            (float(quantity), processed_by, tenant_id, org_id, bus_id, loc_id, product_id),
                        )

                        # Create IN movement for restock
                        movement_id = Helper.generate_unique_identifier(prefix="mov")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                             movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                movement_id, tenant_id, org_id, bus_id, product_id,
                                batch_id, 'STORE', loc_id,
                                'IN', float(quantity),
                                'RETURN', data.return_id,
                                cdate, ctime, cdatetime, processed_by
                            ),
                        )
                    else:
                        # Item is not resalable - create IN then immediately OUT as write-off
                        # IN movement (item received back)
                        movement_in_id = Helper.generate_unique_identifier(prefix="mov")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                             movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                movement_in_id, tenant_id, org_id, bus_id, product_id,
                                batch_id, 'STORE', loc_id,
                                'IN', float(quantity),
                                'RETURN', data.return_id,
                                cdate, ctime, cdatetime, processed_by
                            ),
                        )

                        # OUT movement (write-off)
                        movement_out_id = Helper.generate_unique_identifier(prefix="mov")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                            (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                             movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                movement_out_id, tenant_id, org_id, bus_id, product_id,
                                batch_id, 'STORE', loc_id,
                                'OUT', float(quantity),
                                f'WRITE_OFF_{condition.upper()}', data.return_id,
                                cdate, ctime, cdatetime, processed_by
                            ),
                        )

                # 4. Refund is tracked on the return itself (msg_returns.total_refund_amount).
                # The original sale stays as PAID — the sale was completed.
                # The return is a separate transaction, not a reversal of the sale payment.
                total_refund = Decimal(str(old_data['total_refund_amount']))

                # 5. Update return status to COMPLETED
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_RETURNS_TABLE}
                    SET status = 'COMPLETED', processed_by = %s, processed_at = %s,
                        updated_by = %s, processing_notes = COALESCE(processing_notes || ' | ', '') || %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (
                        processed_by, cdatetime, processed_by,
                        data.notes or 'Processed',
                        data.return_id, tenant_id, org_id, bus_id, loc_id
                    ),
                )
                cursor.fetchone()

                # 6. Build response
                return_dict = StoreReturnsService._build_return_read_dto(
                    cursor, data.return_id, tenant_id, org_id, bus_id, loc_id
                )
                return_read = ProcessReturnServiceReadDto(**return_dict)

                # 7. Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-store-returns",
                        resource_id=data.return_id, action="process",
                        old_data=old_data, new_data=return_dict,
                        description=f"Return {old_data.get('return_number')} processed - refund: {float(total_refund)}",
                        performed_by=processed_by, org_id=org_id, bus_id=bus_id, loc_id=loc_id, cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Return processed successfully - inventory updated and refund issued", data=[return_read])

        except Exception as e:
            logger.error(f"Error processing return: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to process return: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_return(
        return_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetReturnServiceReadDto]:
        """Get a single return by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                return_dict = StoreReturnsService._build_return_read_dto(
                    cursor, return_id, tenant_id, org_id, bus_id, loc_id
                )
                if not return_dict:
                    return Respons(success=False, detail="Return not found", error="NOT_FOUND")

                return_read = GetReturnServiceReadDto(**return_dict)
                return Respons(success=True, detail="Return retrieved successfully", data=[return_read])

        except Exception as e:
            logger.error(f"Error getting return: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get return: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_returns(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        page: int = 1,
        size: int = 10,
        status: str = None,
        sale_id: str = None,
    ) -> Respons[list[GetReturnsServiceReadDto]]:
        """Get list of returns with pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                where_conditions = [
                    "r.tenant_id = %s", "r.org_id = %s", "r.bus_id = %s", "r.loc_id = %s",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if status:
                    where_conditions.append("r.status = %s")
                    params.append(status)
                if sale_id:
                    where_conditions.append("r.sale_id = %s")
                    params.append(sale_id)

                where_clause = " AND ".join(where_conditions)

                # Count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_RETURNS_TABLE} r WHERE {where_clause}",
                    tuple(params),
                )
                total = cursor.fetchone()['total'] if cursor.fetchone is not None else 0
                total_result = cursor.fetchone()
                # Re-run count (cursor was consumed)
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_RETURNS_TABLE} r WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                offset = (page - 1) * size

                # Get returns
                cursor.execute(
                    f"""SELECT r.*,
                           s.sale_number,
                           c.fullname as customer_name,
                           creator.fullname as created_by_name,
                           rp.name as return_policy_name
                    FROM {db_settings.MSG_RETURNS_TABLE} r
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON r.sale_id = s.id AND r.tenant_id = s.tenant_id AND r.org_id = s.org_id
                        AND r.bus_id = s.bus_id AND r.loc_id = s.loc_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON r.customer_id = c.id AND r.tenant_id = c.tenant_id
                        AND r.org_id = c.org_id AND r.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON r.created_by = creator.id AND r.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_RETURN_POLICIES_TABLE} rp
                        ON r.return_policy_id = rp.id AND r.tenant_id = rp.tenant_id
                        AND r.org_id = rp.org_id AND r.bus_id = rp.bus_id
                    WHERE {where_clause}
                    ORDER BY r.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                returns = cursor.fetchall()

                return_list = []
                for ret in returns:
                    ret_dict = dict(ret)
                    ret_dict['created_by'] = ret_dict.pop('created_by_name', None) or ret_dict.get('created_by')

                    # Get items for each return
                    cursor.execute(
                        f"""SELECT ri.*, p.name as product_name
                        FROM {db_settings.MSG_RETURN_ITEMS_TABLE} ri
                        LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                            ON ri.product_id = p.id AND ri.tenant_id = p.tenant_id
                            AND ri.org_id = p.org_id AND ri.bus_id = p.bus_id
                        WHERE ri.return_id = %s AND ri.tenant_id = %s
                        ORDER BY ri.cdatetime ASC""",
                        (ret_dict['id'], tenant_id),
                    )
                    items = cursor.fetchall()
                    ret_dict['items'] = [ReturnItemReadBase(**dict(item)) for item in items]
                    return_list.append(GetReturnsServiceReadDto(**ret_dict))

                pagination = PaginationMeta(page=page, size=size, total=total, has_next=(page * size) < total)

                return Respons(success=True, detail="Returns retrieved successfully", data=return_list, pagination=pagination)

        except Exception as e:
            logger.error(f"Error getting returns: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get returns: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_returns_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetReturnStatisticsServiceReadDto]:
        """Get return statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_returns,
                        COUNT(CASE WHEN r.status = 'PENDING' THEN 1 END) as total_pending,
                        COUNT(CASE WHEN r.status = 'APPROVED' THEN 1 END) as total_approved,
                        COUNT(CASE WHEN r.status = 'REJECTED' THEN 1 END) as total_rejected,
                        COUNT(CASE WHEN r.status = 'COMPLETED' THEN 1 END) as total_completed,
                        COALESCE(SUM(CASE WHEN r.status = 'COMPLETED' THEN r.total_refund_amount ELSE 0 END), 0) as total_refund_amount,
                        COALESCE(SUM(CASE WHEN r.status = 'COMPLETED' THEN r.restocking_fee_amount ELSE 0 END), 0) as total_restocking_fees
                    FROM {db_settings.MSG_RETURNS_TABLE} r
                    WHERE r.tenant_id = %s AND r.org_id = %s AND r.bus_id = %s AND r.loc_id = %s""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                result = cursor.fetchone()

                # Get item-level stats
                cursor.execute(
                    f"""SELECT
                        COALESCE(SUM(ri.quantity_returned), 0) as total_items_returned,
                        COALESCE(SUM(CASE WHEN ri.restock = true THEN ri.quantity_returned ELSE 0 END), 0) as total_items_restocked,
                        COALESCE(SUM(CASE WHEN ri.restock = false THEN ri.quantity_returned ELSE 0 END), 0) as total_items_written_off
                    FROM {db_settings.MSG_RETURN_ITEMS_TABLE} ri
                    JOIN {db_settings.MSG_RETURNS_TABLE} ret ON ri.return_id = ret.id
                        AND ri.tenant_id = ret.tenant_id AND ri.org_id = ret.org_id
                        AND ri.bus_id = ret.bus_id AND ri.loc_id = ret.loc_id
                    WHERE ri.tenant_id = %s AND ri.org_id = %s AND ri.bus_id = %s AND ri.loc_id = %s
                    AND ret.status = 'COMPLETED'""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                item_result = cursor.fetchone()

                stats = GetReturnStatisticsServiceReadDto(
                    total_returns=result.get('total_returns', 0) or 0 if result else 0,
                    total_pending=result.get('total_pending', 0) or 0 if result else 0,
                    total_approved=result.get('total_approved', 0) or 0 if result else 0,
                    total_rejected=result.get('total_rejected', 0) or 0 if result else 0,
                    total_completed=result.get('total_completed', 0) or 0 if result else 0,
                    total_refund_amount=float(result.get('total_refund_amount', 0) or 0) if result else 0,
                    total_restocking_fees=float(result.get('total_restocking_fees', 0) or 0) if result else 0,
                    total_items_returned=float(item_result.get('total_items_returned', 0) or 0) if item_result else 0,
                    total_items_restocked=float(item_result.get('total_items_restocked', 0) or 0) if item_result else 0,
                    total_items_written_off=float(item_result.get('total_items_written_off', 0) or 0) if item_result else 0,
                )

                return Respons(success=True, detail="Return statistics retrieved successfully", data=[stats])

        except Exception as e:
            logger.error(f"Error getting return statistics: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get return statistics: {str(e)}", error="INTERNAL_ERROR")
