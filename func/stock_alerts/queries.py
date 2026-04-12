import datetime

from shared.settings import (
    MSG_STORE_CONFIGS_TABLE,
    MSG_WAREHOUSE_CONFIGS_TABLE,
    MSG_STORE_PRODUCTS_TABLE,
    MSG_WAREHOUSE_PRODUCTS_TABLE,
    MSG_PRODUCTS_TABLE,
    CP_LOCATIONS_TABLE,
)


def get_store_configs_with_out_of_stock_notifications(cursor) -> list[dict]:
    """Get all store configs that have out of stock notification enabled and configured."""
    query = f"""
        SELECT sc.tenant_id, sc.org_id, sc.bus_id, sc.loc_id,
               sc.out_of_stock_notification_email, sc.out_of_stock_notification_occurrence
        FROM {MSG_STORE_CONFIGS_TABLE} sc
        WHERE sc.enable_out_of_stock_notification = true
            AND sc.out_of_stock_notification_email IS NOT NULL
            AND sc.out_of_stock_notification_email != ''
            AND sc.out_of_stock_notification_occurrence IS NOT NULL
            AND sc.out_of_stock_notification_occurrence > 0
            AND sc.is_active = true;
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_warehouse_configs_with_out_of_stock_notifications(cursor) -> list[dict]:
    """Get all warehouse configs that have out of stock notification enabled and configured."""
    query = f"""
        SELECT wc.tenant_id, wc.org_id, wc.bus_id, wc.loc_id,
               wc.out_of_stock_notification_email, wc.out_of_stock_notification_occurrence
        FROM {MSG_WAREHOUSE_CONFIGS_TABLE} wc
        WHERE wc.enable_out_of_stock_notification = true
            AND wc.out_of_stock_notification_email IS NOT NULL
            AND wc.out_of_stock_notification_email != ''
            AND wc.out_of_stock_notification_occurrence IS NOT NULL
            AND wc.out_of_stock_notification_occurrence > 0
            AND wc.is_active = true;
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_low_stock_store_products_by_location(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str) -> list[dict]:
    """Fetch store products that are out of stock or below reorder level for a specific location."""
    query = f"""
        SELECT
            p.name AS product_name, p.sku, p.bar_code,
            sp.current_qty, sp.reorder_level, sp.reorder_quantity,
            loc.loc_name AS location_name
        FROM {MSG_STORE_PRODUCTS_TABLE} sp
        JOIN {MSG_PRODUCTS_TABLE} p ON p.id = sp.product_id AND p.tenant_id = sp.tenant_id
        JOIN {CP_LOCATIONS_TABLE} loc ON loc.id = sp.loc_id AND loc.tenant_id = sp.tenant_id
        WHERE sp.tenant_id = %s AND sp.org_id = %s AND sp.bus_id = %s AND sp.loc_id = %s
            AND sp.is_active = true AND sp.delete_status = 'NOT_DELETED'
            AND p.is_active = true AND p.delete_status = 'NOT_DELETED'
            AND sp.current_qty <= sp.reorder_level
        ORDER BY sp.current_qty ASC, p.name ASC;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id))
    return cursor.fetchall()


def get_low_stock_warehouse_products_by_location(cursor, tenant_id: str, org_id: str, bus_id: str, loc_id: str) -> list[dict]:
    """Fetch warehouse products that are out of stock or below reorder level for a specific location."""
    query = f"""
        SELECT
            p.name AS product_name, p.sku, p.bar_code,
            wp.current_qty, wp.reorder_level, wp.reorder_quantity,
            loc.loc_name AS location_name
        FROM {MSG_WAREHOUSE_PRODUCTS_TABLE} wp
        JOIN {MSG_PRODUCTS_TABLE} p ON p.id = wp.product_id AND p.tenant_id = wp.tenant_id
        JOIN {CP_LOCATIONS_TABLE} loc ON loc.id = wp.loc_id AND loc.tenant_id = wp.tenant_id
        WHERE wp.tenant_id = %s AND wp.org_id = %s AND wp.bus_id = %s AND wp.loc_id = %s
            AND wp.is_active = true AND wp.delete_status = 'NOT_DELETED'
            AND p.is_active = true AND p.delete_status = 'NOT_DELETED'
            AND wp.current_qty <= wp.reorder_level
        ORDER BY wp.current_qty ASC, p.name ASC;
    """
    cursor.execute(query, (tenant_id, org_id, bus_id, loc_id))
    return cursor.fetchall()


def should_send_alert(occurrence: int) -> bool:
    """
    Determine if an alert should be sent based on the out_of_stock_notification_occurrence.
    The function runs every 30 minutes. We check if the current 30-min slot
    aligns with the configured occurrence using modular arithmetic.
    """
    now = datetime.datetime.utcnow()
    minutes_since_midnight = now.hour * 60 + now.minute
    current_slot = (minutes_since_midnight // 30) * 30
    return current_slot % occurrence == 0
