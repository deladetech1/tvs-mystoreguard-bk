import datetime
from shared.email_service import fmt_currency


def build_daily_sales_report_email(
    store_name: str,
    location_name: str,
    sale_date: str,
    summary: dict,
    payment_breakdown: list[dict],
    top_products: list[dict],
    hourly_sales: list[dict],
    customer_summary: list[dict],
    detailed_sales: list[dict],
    sale_items_by_number: dict[str, list[dict]],
) -> str:
    """Build a comprehensive daily sales report HTML email."""

    total_transactions = summary["total_transactions"] or 0
    gross_revenue = float(summary["gross_revenue"] or 0)
    total_collected = float(summary["total_collected"] or 0)
    total_outstanding = float(summary["total_outstanding"] or 0)
    total_discounts = float(summary["total_discounts"] or 0)
    total_gift_card = float(summary["total_gift_card_used"] or 0)
    avg_order = gross_revenue / total_transactions if total_transactions > 0 else 0
    unique_customers = summary["unique_customers"] or 0

    display_name = store_name or location_name
    formatted_date = datetime.datetime.strptime(sale_date, "%Y-%m-%d").strftime("%B %d, %Y")

    # ── Styles ──
    th_style = "padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6; font-size: 13px;"
    th_right = "padding: 10px 12px; text-align: right; border-bottom: 2px solid #dee2e6; font-size: 13px;"
    td_style = "padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 13px;"
    td_right = "padding: 8px 12px; border-bottom: 1px solid #eee; text-align: right; font-size: 13px;"
    section_title = "margin: 30px 0 12px 0; font-size: 16px; color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 6px;"
    kpi_box = "display: inline-block; width: 150px; padding: 15px; margin: 6px; background: #f8f9fa; border-radius: 8px; text-align: center; vertical-align: top;"
    kpi_value = "font-size: 22px; font-weight: bold; color: #1a73e8; margin: 0;"
    kpi_label = "font-size: 11px; color: #666; margin: 4px 0 0 0; text-transform: uppercase;"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 900px; margin: 0 auto;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1a73e8, #0d47a1); color: white; padding: 24px 30px; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; font-size: 22px;">Daily Sales Report</h1>
            <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">{display_name} &mdash; {formatted_date}</p>
        </div>

        <div style="padding: 20px 30px; background: white;">

        <!-- KPI CARDS -->
        <div style="text-align: center; margin: 20px 0;">
            <div style="{kpi_box}">
                <p style="{kpi_value}">{total_transactions}</p>
                <p style="{kpi_label}">Transactions</p>
            </div>
            <div style="{kpi_box}">
                <p style="{kpi_value}">{fmt_currency(gross_revenue)}</p>
                <p style="{kpi_label}">Gross Revenue</p>
            </div>
            <div style="{kpi_box}">
                <p style="{kpi_value}">{fmt_currency(total_collected)}</p>
                <p style="{kpi_label}">Collected</p>
            </div>
            <div style="{kpi_box}">
                <p style="{kpi_value} color: {'#dc3545' if total_outstanding > 0 else '#28a745'};">{fmt_currency(total_outstanding)}</p>
                <p style="{kpi_label}">Outstanding</p>
            </div>
            <div style="{kpi_box}">
                <p style="{kpi_value}">{fmt_currency(avg_order)}</p>
                <p style="{kpi_label}">Avg Order Value</p>
            </div>
        </div>"""

    if total_transactions == 0:
        body += """
            <div style="text-align: center; padding: 40px; color: #666;">
                <h3>No Sales Recorded Today</h3>
                <p>There were no sales transactions at this location today.</p>
            </div>
        </div></body></html>"""
        return body

    # ── SALES BY STATUS ──
    body += f"""
        <h3 style="{section_title}">Sales by Status</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
            <thead><tr style="background-color: #f8f9fa;">
                <th style="{th_style}">Status</th>
                <th style="{th_right}">Count</th>
            </tr></thead>
            <tbody>"""

    status_map = [
        ("PAID", summary["paid_count"], "#28a745"),
        ("PARTIALLY PAID", summary["partially_paid_count"], "#fd7e14"),
        ("ON HOLD", summary["on_hold_count"], "#6c757d"),
        ("OVERDUE", summary["overdue_count"], "#dc3545"),
        ("QUEUED", summary["queued_count"], "#17a2b8"),
        ("CANCELLED", summary["cancelled_count"], "#6c757d"),
    ]
    for label, count, color in status_map:
        if count and count > 0:
            body += f"""
                <tr>
                    <td style="{td_style}"><span style="color: {color}; font-weight: bold;">{label}</span></td>
                    <td style="{td_right}">{count}</td>
                </tr>"""
    body += "</tbody></table>"

    # ── PAYMENT METHOD BREAKDOWN ──
    if payment_breakdown:
        body += f"""
        <h3 style="{section_title}">Payment Methods</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
            <thead><tr style="background-color: #f8f9fa;">
                <th style="{th_style}">Method</th>
                <th style="{th_right}">Transactions</th>
                <th style="{th_right}">Amount</th>
            </tr></thead>
            <tbody>"""
        for pm in payment_breakdown:
            method_label = pm["payment_method"].replace("_", " ").title()
            body += f"""
                <tr>
                    <td style="{td_style}">{method_label}</td>
                    <td style="{td_right}">{pm['transaction_count']}</td>
                    <td style="{td_right}">{fmt_currency(pm['total_amount'])}</td>
                </tr>"""
        body += "</tbody></table>"

    if total_discounts > 0 or total_gift_card > 0:
        body += f"""
        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px 16px; margin: 16px 0; border-radius: 4px; font-size: 13px;">"""
        if total_discounts > 0:
            body += f"<strong>Promo Discounts Applied:</strong> {fmt_currency(total_discounts)}<br>"
        if total_gift_card > 0:
            body += f"<strong>Gift Card Payments:</strong> {fmt_currency(total_gift_card)}"
        body += "</div>"

    # ── HOURLY SALES BREAKDOWN ──
    if hourly_sales:
        body += f"""
        <h3 style="{section_title}">Sales by Hour</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
            <thead><tr style="background-color: #f8f9fa;">
                <th style="{th_style}">Hour</th>
                <th style="{th_right}">Transactions</th>
                <th style="{th_right}">Revenue</th>
            </tr></thead>
            <tbody>"""
        peak_hour = max(hourly_sales, key=lambda h: float(h["total_revenue"]))
        for h in hourly_sales:
            hour_int = int(h["sale_hour"])
            hour_label = f"{hour_int:02d}:00 - {hour_int:02d}:59"
            is_peak = h == peak_hour
            row_style = "background-color: #e8f5e9;" if is_peak else ""
            peak_badge = ' <span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">PEAK</span>' if is_peak else ""
            body += f"""
                <tr style="{row_style}">
                    <td style="{td_style}">{hour_label}{peak_badge}</td>
                    <td style="{td_right}">{h['transaction_count']}</td>
                    <td style="{td_right}">{fmt_currency(h['total_revenue'])}</td>
                </tr>"""
        body += "</tbody></table>"

    # ── TOP SELLING PRODUCTS ──
    if top_products:
        body += f"""
        <h3 style="{section_title}">Top Selling Products</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
            <thead><tr style="background-color: #f8f9fa;">
                <th style="{th_style}">#</th>
                <th style="{th_style}">Product</th>
                <th style="{th_right}">Qty Sold</th>
                <th style="{th_right}">Revenue</th>
                <th style="{th_right}">Tax</th>
            </tr></thead>
            <tbody>"""
        for i, tp in enumerate(top_products, 1):
            body += f"""
                <tr>
                    <td style="{td_style}">{i}</td>
                    <td style="{td_style}">{tp['product_name']}</td>
                    <td style="{td_right}">{tp['total_qty_sold']}</td>
                    <td style="{td_right}">{fmt_currency(tp['total_revenue'])}</td>
                    <td style="{td_right}">{fmt_currency(tp['total_tax'])}</td>
                </tr>"""
        body += "</tbody></table>"

    # ── CUSTOMER SUMMARY ──
    if customer_summary:
        body += f"""
        <h3 style="{section_title}">Customer Summary ({unique_customers} unique customer{'s' if unique_customers != 1 else ''})</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
            <thead><tr style="background-color: #f8f9fa;">
                <th style="{th_style}">Customer</th>
                <th style="{th_style}">Contact</th>
                <th style="{th_right}">Orders</th>
                <th style="{th_right}">Total Spent</th>
                <th style="{th_right}">Paid</th>
                <th style="{th_right}">Outstanding</th>
            </tr></thead>
            <tbody>"""
        for cs in customer_summary:
            outstanding_color = "#dc3545" if float(cs["outstanding"] or 0) > 0 else "#333"
            contact_display = cs["customer_email"] if cs["customer_email"] != "-" else cs["customer_contact"]
            body += f"""
                <tr>
                    <td style="{td_style}">{cs['customer_name']}</td>
                    <td style="{td_style} font-size: 12px; color: #666;">{contact_display}</td>
                    <td style="{td_right}">{cs['transaction_count']}</td>
                    <td style="{td_right}">{fmt_currency(cs['total_spent'])}</td>
                    <td style="{td_right}">{fmt_currency(cs['total_paid'])}</td>
                    <td style="{td_right} color: {outstanding_color}; font-weight: bold;">{fmt_currency(cs['outstanding'])}</td>
                </tr>"""
        body += "</tbody></table>"

    # ── DETAILED TRANSACTIONS ──
    if detailed_sales:
        body += f"""
        <h3 style="{section_title}">Detailed Transactions</h3>"""

        for sale in detailed_sales:
            sale_number = sale["sale_number"]
            status = sale["status"]
            status_colors = {
                "PAID": "#28a745", "PARTIALLY_PAID": "#fd7e14",
                "ON_HOLD": "#6c757d", "OVERDUE": "#dc3545",
                "CANCELLED": "#6c757d", "QUEUED": "#17a2b8",
            }
            s_color = status_colors.get(status, "#333")
            mode_label = sale["sale_mode"].replace("_", " ").title()
            discount_info = ""
            if sale["promo_discount_amount"] and float(sale["promo_discount_amount"]) > 0:
                discount_info = f' &nbsp;<span style="background: #ffc107; color: #333; padding: 1px 5px; border-radius: 3px; font-size: 10px;">-{fmt_currency(sale["promo_discount_amount"])} discount</span>'

            body += f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 12px; overflow: hidden;">
            <div style="background: #f8f9fa; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{sale_number}</strong>
                    <span style="color: {s_color}; font-weight: bold; margin-left: 10px; font-size: 12px;">{status.replace('_', ' ')}</span>
                    <span style="color: #666; font-size: 12px; margin-left: 10px;">{mode_label}</span>
                    {discount_info}
                </div>
                <div style="text-align: right; font-size: 12px; color: #666;">
                    {sale['ctime'] or ''} &bull; {sale['customer_name']} &bull; by {sale['sold_by'] or 'N/A'}
                </div>
            </div>"""

            items = sale_items_by_number.get(sale_number, [])
            if items:
                body += f"""
            <table style="width: 100%; border-collapse: collapse;">
                <thead><tr>
                    <th style="padding: 6px 14px; text-align: left; font-size: 11px; color: #999; border-bottom: 1px solid #eee;">PRODUCT</th>
                    <th style="padding: 6px 14px; text-align: right; font-size: 11px; color: #999; border-bottom: 1px solid #eee;">QTY</th>
                    <th style="padding: 6px 14px; text-align: right; font-size: 11px; color: #999; border-bottom: 1px solid #eee;">UNIT PRICE</th>
                    <th style="padding: 6px 14px; text-align: right; font-size: 11px; color: #999; border-bottom: 1px solid #eee;">TAX</th>
                    <th style="padding: 6px 14px; text-align: right; font-size: 11px; color: #999; border-bottom: 1px solid #eee;">LINE TOTAL</th>
                </tr></thead>
                <tbody>"""
                for item in items:
                    body += f"""
                <tr>
                    <td style="padding: 5px 14px; font-size: 12px; border-bottom: 1px solid #f5f5f5;">{item['product_name']}</td>
                    <td style="padding: 5px 14px; text-align: right; font-size: 12px; border-bottom: 1px solid #f5f5f5;">{item['quantity']}</td>
                    <td style="padding: 5px 14px; text-align: right; font-size: 12px; border-bottom: 1px solid #f5f5f5;">{fmt_currency(item['final_price'])}</td>
                    <td style="padding: 5px 14px; text-align: right; font-size: 12px; border-bottom: 1px solid #f5f5f5;">{fmt_currency(item['tax_amount'])}</td>
                    <td style="padding: 5px 14px; text-align: right; font-size: 12px; border-bottom: 1px solid #f5f5f5;">{fmt_currency(item['line_total'])}</td>
                </tr>"""
                body += "</tbody></table>"

            body += f"""
            <div style="padding: 8px 14px; background: #f8f9fa; text-align: right; font-size: 13px;">
                <strong>Total:</strong> {fmt_currency(sale['total_amount'])}
                &nbsp;&nbsp; <strong>Paid:</strong> {fmt_currency(sale['paid_amount'])}
                &nbsp;&nbsp; <strong>Balance:</strong> <span style="color: {'#dc3545' if float(sale['balance_amount'] or 0) > 0 else '#28a745'};">{fmt_currency(sale['balance_amount'])}</span>
            </div>
        </div>"""

    # ── Footer ──
    body += f"""
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
        <p style="font-size: 12px; color: #999; text-align: center;">
            This is an automated daily sales report from MyStoreGuard.<br>
            Generated on {datetime.datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC.
        </p>
        </div>
    </body>
    </html>"""

    return body
