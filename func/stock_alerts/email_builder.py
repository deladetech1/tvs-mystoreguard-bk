import datetime


def build_stock_alert_email_body(products: list[dict], location_type: str) -> str:
    """Build an HTML email body for the stock alert."""
    out_of_stock = [p for p in products if p["current_qty"] == 0]
    low_stock = [p for p in products if p["current_qty"] > 0]
    type_label = "Store" if location_type == "STORE" else "Warehouse"

    def _product_rows(items: list[dict]) -> str:
        rows = ""
        for p in items:
            status_color = "#dc3545" if p["current_qty"] == 0 else "#fd7e14"
            status_label = "Out of Stock" if p["current_qty"] == 0 else "Low Stock"
            rows += f"""
                <tr>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{p['product_name']}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{p['sku'] or '-'}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{p['location_name']}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center;">{p['current_qty']}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center;">{p['reorder_level']}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">
                        <span style="color: {status_color}; font-weight: bold;">{status_label}</span>
                    </td>
                </tr>"""
        return rows

    table_header = """
            <thead><tr style="background-color: #f8f9fa;">
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Product</th>
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">SKU</th>
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Location</th>
                <th style="padding: 10px 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Qty</th>
                <th style="padding: 10px 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Reorder Level</th>
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Status</th>
            </tr></thead>"""

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #1a73e8;">{type_label} Stock Alert - Attention Required</h2>
        <p>The following <strong>{type_label.lower()}</strong> products require your attention due to low or zero stock levels:</p>"""

    if out_of_stock:
        body += f"""
        <h3 style="color: #dc3545;">Out of Stock ({len(out_of_stock)} items)</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            {table_header}
            <tbody>{_product_rows(out_of_stock)}</tbody>
        </table>"""

    if low_stock:
        body += f"""
        <h3 style="color: #fd7e14;">Low Stock ({len(low_stock)} items)</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            {table_header}
            <tbody>{_product_rows(low_stock)}</tbody>
        </table>"""

    body += f"""
        <p style="margin-top: 20px; font-size: 14px; color: #666;">
            <strong>Total items requiring attention:</strong> {len(products)}<br>
            Please review and restock these products as soon as possible.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #999;">
            This is an automated alert from MyStoreGuard. Generated on {datetime.datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC.
        </p>
    </body></html>"""
    return body
