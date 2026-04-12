import datetime

from shared.settings import (
    MSG_STORE_CONFIGS_TABLE,
    MSG_SALES_TABLE,
    MSG_SALES_ITEMS_TABLE,
    MSG_SALES_PAYMENTS_TABLE,
    MSG_CUSTOMERS_TABLE,
    CP_LOCATIONS_TABLE,
    CP_USERS_TABLE,
    CP_ASSIGN_ROLES_TABLE,
)


def get_store_configs_for_daily_reports(cursor) -> list[dict]:
    """Get store configs with daily reports enabled and a closing time set."""
    query = f"""
        SELECT sc.tenant_id, sc.org_id, sc.bus_id, sc.loc_id,
               sc.store_name, sc.closing_time, sc.sales_notification_emails,
               loc.loc_name AS location_name
        FROM {MSG_STORE_CONFIGS_TABLE} sc
        JOIN {CP_LOCATIONS_TABLE} loc
            ON loc.id = sc.loc_id AND loc.tenant_id = sc.tenant_id
        WHERE sc.enable_daily_sales_reports = true
            AND sc.closing_time IS NOT NULL
            AND sc.is_active = true;
    """
    cursor.execute(query)
    return cursor.fetchall()


def is_closing_time_slot(closing_time) -> bool:
    """
    Check if the current 30-minute window covers the store's closing time.
    e.g. if closing_time is 17:45 and function runs at the 17:30 slot,
    the window 17:30-18:00 covers 17:45 -> return True.
    """
    now = datetime.datetime.utcnow()
    current_slot = (now.hour * 60 + now.minute) // 30 * 30

    if hasattr(closing_time, "hour"):
        closing_minutes = closing_time.hour * 60 + closing_time.minute
    else:
        closing_minutes = closing_time.total_seconds() // 60

    return current_slot <= closing_minutes < current_slot + 30


def get_alert_recipients_for_store(cursor, tenant_id: str, org_id: str, bus_id: str) -> list[dict]:
    """Get owners and admins who should receive reports (fallback when no sales_notification_emails)."""
    query = f"""
        SELECT DISTINCT u.id, u.fullname, u.email
        FROM {CP_USERS_TABLE} u
        WHERE u.tenant_id = %s
            AND u.is_active = true
            AND u.delete_status = 'NOT_DELETED'
            AND u.email IS NOT NULL AND u.email != ''
            AND (
                u.is_owner = true
                OR u.id IN (
                    SELECT ar.user_id
                    FROM {CP_ASSIGN_ROLES_TABLE} ar
                    WHERE ar.tenant_id = %s
                        AND ar.role_id IN ('role-msg-admin', 'role-msg-store-admin')
                        AND ar.delete_status = 'NOT_DELETED'
                )
            );
    """
    cursor.execute(query, (tenant_id, tenant_id))
    return cursor.fetchall()


def get_sales_summary(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str, sale_date: str) -> dict:
    """Get aggregated sales summary for a location on a given date."""
    query = f"""
        SELECT
            COUNT(*) AS total_transactions,
            COALESCE(SUM(s.total_amount), 0) AS gross_revenue,
            COALESCE(SUM(s.paid_amount), 0) AS total_collected,
            COALESCE(SUM(s.balance_amount), 0) AS total_outstanding,
            COALESCE(SUM(s.promo_discount_amount), 0) AS total_discounts,
            COALESCE(SUM(s.gift_card_amount_used), 0) AS total_gift_card_used,
            COUNT(*) FILTER (WHERE s.status = 'PAID') AS paid_count,
            COUNT(*) FILTER (WHERE s.status = 'PARTIALLY_PAID') AS partially_paid_count,
            COUNT(*) FILTER (WHERE s.status = 'ON_HOLD') AS on_hold_count,
            COUNT(*) FILTER (WHERE s.status = 'CANCELLED') AS cancelled_count,
            COUNT(*) FILTER (WHERE s.status = 'OVERDUE') AS overdue_count,
            COUNT(*) FILTER (WHERE s.status = 'QUEUED') AS queued_count,
            COUNT(DISTINCT s.customer_id) FILTER (WHERE s.customer_id IS NOT NULL) AS unique_customers
        FROM {MSG_SALES_TABLE} s
        WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
            AND s.sale_date = %s
            AND s.deleted_by IS NULL;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id, sale_date))
    return cursor.fetchone()


def get_payment_method_breakdown(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str, sale_date: str) -> list[dict]:
    """Get payment breakdown by method for a location on a given date."""
    query = f"""
        SELECT
            p.payment_method,
            COUNT(*) AS transaction_count,
            COALESCE(SUM(p.paid_amount), 0) AS total_amount
        FROM {MSG_SALES_PAYMENTS_TABLE} p
        JOIN {MSG_SALES_TABLE} s
            ON s.id = p.sale_id
            AND s.tenant_id = p.tenant_id AND s.org_id = p.org_id
            AND s.bus_id = p.bus_id AND s.loc_id = p.loc_id
        WHERE p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s AND p.loc_id = %s
            AND s.sale_date = %s
            AND p.payment_status = 'SUCCESS'
            AND p.deleted_at IS NULL
            AND s.deleted_by IS NULL
        GROUP BY p.payment_method
        ORDER BY total_amount DESC;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id, sale_date))
    return cursor.fetchall()


def get_top_selling_products(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str, sale_date: str, limit: int = 10) -> list[dict]:
    """Get top-selling products by quantity and revenue for a location on a given date."""
    query = f"""
        SELECT
            si.product_name,
            SUM(si.quantity) AS total_qty_sold,
            SUM(si.line_total) AS total_revenue,
            COALESCE(SUM(si.tax_amount), 0) AS total_tax
        FROM {MSG_SALES_ITEMS_TABLE} si
        JOIN {MSG_SALES_TABLE} s
            ON s.id = si.sale_id
            AND s.tenant_id = si.tenant_id AND s.org_id = si.org_id
            AND s.bus_id = si.bus_id AND s.loc_id = si.loc_id
        WHERE si.tenant_id = %s AND si.org_id = %s AND si.bus_id = %s AND si.loc_id = %s
            AND s.sale_date = %s
            AND s.deleted_by IS NULL
            AND si.deleted_by IS NULL
        GROUP BY si.product_name
        ORDER BY total_revenue DESC
        LIMIT %s;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id, sale_date, limit))
    return cursor.fetchall()


def get_sales_by_hour(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str, sale_date: str) -> list[dict]:
    """Get sales count and revenue grouped by hour."""
    query = f"""
        SELECT
            EXTRACT(HOUR FROM s.cdatetime) AS sale_hour,
            COUNT(*) AS transaction_count,
            COALESCE(SUM(s.total_amount), 0) AS total_revenue
        FROM {MSG_SALES_TABLE} s
        WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
            AND s.sale_date = %s
            AND s.deleted_by IS NULL
        GROUP BY EXTRACT(HOUR FROM s.cdatetime)
        ORDER BY sale_hour;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id, sale_date))
    return cursor.fetchall()


def get_customer_summary(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str, sale_date: str) -> list[dict]:
    """Get customer-level spend summary for the day."""
    query = f"""
        SELECT
            COALESCE(c.fullname, 'Walk-in Customer') AS customer_name,
            COALESCE(c.email, '-') AS customer_email,
            COALESCE(c.contact, '-') AS customer_contact,
            COUNT(*) AS transaction_count,
            COALESCE(SUM(s.total_amount), 0) AS total_spent,
            COALESCE(SUM(s.paid_amount), 0) AS total_paid,
            COALESCE(SUM(s.balance_amount), 0) AS outstanding
        FROM {MSG_SALES_TABLE} s
        LEFT JOIN {MSG_CUSTOMERS_TABLE} c
            ON c.id = s.customer_id
            AND c.tenant_id = s.tenant_id AND c.org_id = s.org_id AND c.bus_id = s.bus_id
        WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
            AND s.sale_date = %s
            AND s.deleted_by IS NULL
        GROUP BY c.fullname, c.email, c.contact
        ORDER BY total_spent DESC;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id, sale_date))
    return cursor.fetchall()


def get_detailed_sales(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str, sale_date: str) -> list[dict]:
    """Get all individual sales with items for the day."""
    query = f"""
        SELECT
            s.sale_number, s.status, s.sale_mode,
            s.total_amount, s.paid_amount, s.balance_amount,
            s.promo_discount_amount,
            COALESCE(c.fullname, 'Walk-in') AS customer_name,
            s.ctime,
            creator.fullname AS sold_by
        FROM {MSG_SALES_TABLE} s
        LEFT JOIN {MSG_CUSTOMERS_TABLE} c
            ON c.id = s.customer_id
            AND c.tenant_id = s.tenant_id AND c.org_id = s.org_id AND c.bus_id = s.bus_id
        LEFT JOIN {CP_USERS_TABLE} creator
            ON creator.id = s.created_by AND creator.tenant_id = s.tenant_id
        WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
            AND s.sale_date = %s
            AND s.deleted_by IS NULL
        ORDER BY s.cdatetime ASC;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id, sale_date))
    return cursor.fetchall()


def get_sale_items(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str, sale_date: str) -> dict[str, list[dict]]:
    """Get all sale items grouped by sale_number for the day."""
    query = f"""
        SELECT
            s.sale_number,
            si.product_name, si.quantity,
            si.base_selling_price, si.final_price,
            si.line_total, si.tax_amount
        FROM {MSG_SALES_ITEMS_TABLE} si
        JOIN {MSG_SALES_TABLE} s
            ON s.id = si.sale_id
            AND s.tenant_id = si.tenant_id AND s.org_id = si.org_id
            AND s.bus_id = si.bus_id AND s.loc_id = si.loc_id
        WHERE si.tenant_id = %s AND si.org_id = %s AND si.bus_id = %s AND si.loc_id = %s
            AND s.sale_date = %s
            AND s.deleted_by IS NULL
            AND si.deleted_by IS NULL
        ORDER BY s.cdatetime ASC, si.product_name ASC;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id, sale_date))
    rows = cursor.fetchall()

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["sale_number"], []).append(row)
    return grouped
