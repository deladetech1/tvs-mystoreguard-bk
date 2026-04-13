import io
import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from shared.email_service import fmt_currency


BLUE = colors.HexColor("#1a73e8")
DARK_BLUE = colors.HexColor("#0d47a1")
GREEN = colors.HexColor("#28a745")
RED = colors.HexColor("#dc3545")
ORANGE = colors.HexColor("#fd7e14")
LIGHT_GREY = colors.HexColor("#f8f9fa")
BORDER_GREY = colors.HexColor("#dee2e6")
YELLOW_BG = colors.HexColor("#fff3cd")


def build_daily_sales_report_pdf(
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
) -> bytes:
    """Build a comprehensive daily sales report PDF and return it as bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontSize=20, textColor=BLUE, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=colors.grey, spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"],
        fontSize=13, textColor=BLUE, spaceBefore=12, spaceAfter=6,
        borderWidth=0, borderColor=BLUE, borderPadding=0,
    )
    note_style = ParagraphStyle(
        "Note", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#666666"),
    )
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey, alignment=1,
    )
    cell_style = ParagraphStyle(
        "CellText", parent=styles["Normal"], fontSize=8,
    )

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

    elements = []

    # ── Title ──
    elements.append(Paragraph("Daily Sales Report", title_style))
    elements.append(Paragraph(f"{display_name} &mdash; {formatted_date}", subtitle_style))

    # ── KPI Cards ──
    kpi_headers = ["Transactions", "Gross Revenue", "Collected", "Outstanding", "Avg Order"]
    outstanding_color = RED if total_outstanding > 0 else GREEN
    kpi_values = [
        str(total_transactions),
        fmt_currency(gross_revenue),
        fmt_currency(total_collected),
        fmt_currency(total_outstanding),
        fmt_currency(avg_order),
    ]
    kpi_table = Table(
        [kpi_headers, kpi_values],
        colWidths=[36 * mm] * 5,
    )
    kpi_style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GREY),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("TEXTCOLOR", (3, 1), (3, 1), outstanding_color),
    ]
    kpi_table.setStyle(TableStyle(kpi_style_cmds))
    elements.append(kpi_table)

    if total_transactions == 0:
        elements.append(Spacer(1, 20 * mm))
        elements.append(Paragraph(
            "<b>No Sales Recorded Today</b><br/>There were no sales transactions at this location today.",
            ParagraphStyle("NoSales", parent=styles["Normal"], fontSize=12, alignment=1, textColor=colors.grey),
        ))
        doc.build(elements)
        return buf.getvalue()

    # ── Sales by Status ──
    elements.append(Paragraph("Sales by Status", section_style))
    status_map = [
        ("PAID", summary["paid_count"], GREEN),
        ("PARTIALLY PAID", summary["partially_paid_count"], ORANGE),
        ("ON HOLD", summary["on_hold_count"], colors.grey),
        ("OVERDUE", summary["overdue_count"], RED),
        ("QUEUED", summary["queued_count"], colors.HexColor("#17a2b8")),
        ("CANCELLED", summary["cancelled_count"], colors.grey),
    ]
    status_data = [["Status", "Count"]]
    status_colors_list = []
    for label, count, color in status_map:
        if count and count > 0:
            status_data.append([label, str(count)])
            status_colors_list.append(color)

    if len(status_data) > 1:
        status_table = Table(status_data, colWidths=[80 * mm, 40 * mm])
        status_style = [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ]
        for i, sc in enumerate(status_colors_list):
            status_style.append(("TEXTCOLOR", (0, i + 1), (0, i + 1), sc))
            status_style.append(("FONTNAME", (0, i + 1), (0, i + 1), "Helvetica-Bold"))
        status_table.setStyle(TableStyle(status_style))
        elements.append(status_table)

    # ── Payment Methods ──
    if payment_breakdown:
        elements.append(Paragraph("Payment Methods", section_style))
        pm_data = [["Method", "Transactions", "Amount"]]
        for pm in payment_breakdown:
            pm_data.append([
                pm["payment_method"].replace("_", " ").title(),
                str(pm["transaction_count"]),
                fmt_currency(pm["total_amount"]),
            ])
        pm_table = Table(pm_data, colWidths=[60 * mm, 40 * mm, 40 * mm])
        pm_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ]))
        elements.append(pm_table)

    # Discount / Gift Card note
    if total_discounts > 0 or total_gift_card > 0:
        note_parts = []
        if total_discounts > 0:
            note_parts.append(f"<b>Promo Discounts Applied:</b> {fmt_currency(total_discounts)}")
        if total_gift_card > 0:
            note_parts.append(f"<b>Gift Card Payments:</b> {fmt_currency(total_gift_card)}")
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(" &nbsp;|&nbsp; ".join(note_parts), note_style))

    # ── Hourly Sales ──
    if hourly_sales:
        elements.append(Paragraph("Sales by Hour", section_style))
        hourly_data = [["Hour", "Transactions", "Revenue"]]
        peak_hour = max(hourly_sales, key=lambda h: float(h["total_revenue"]))
        peak_idx = None
        for i, h in enumerate(hourly_sales):
            hour_int = int(h["sale_hour"])
            hour_label = f"{hour_int:02d}:00 - {hour_int:02d}:59"
            if h == peak_hour:
                hour_label += "  (PEAK)"
                peak_idx = i + 1
            hourly_data.append([
                hour_label,
                str(h["transaction_count"]),
                fmt_currency(h["total_revenue"]),
            ])
        hourly_table = Table(hourly_data, colWidths=[60 * mm, 40 * mm, 40 * mm])
        hourly_style = [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ]
        if peak_idx is not None:
            hourly_style.append(("BACKGROUND", (0, peak_idx), (-1, peak_idx), colors.HexColor("#e8f5e9")))
            hourly_style.append(("FONTNAME", (0, peak_idx), (-1, peak_idx), "Helvetica-Bold"))
        hourly_table.setStyle(TableStyle(hourly_style))
        elements.append(hourly_table)

    # ── Top Selling Products ──
    if top_products:
        elements.append(Paragraph("Top Selling Products", section_style))
        tp_data = [["#", "Product", "Qty Sold", "Revenue", "Tax"]]
        for i, tp in enumerate(top_products, 1):
            tp_data.append([
                str(i),
                Paragraph(tp["product_name"], cell_style),
                str(tp["total_qty_sold"]),
                fmt_currency(tp["total_revenue"]),
                fmt_currency(tp["total_tax"]),
            ])
        tp_table = Table(tp_data, colWidths=[10 * mm, 70 * mm, 20 * mm, 40 * mm, 40 * mm])
        tp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(tp_table)

    # ── Customer Summary ──
    if customer_summary:
        elements.append(Paragraph(
            f"Customer Summary ({unique_customers} unique customer{'s' if unique_customers != 1 else ''})",
            section_style,
        ))
        cs_data = [["Customer", "Contact", "Orders", "Total Spent", "Paid", "Outstanding"]]
        outstanding_rows = []
        for i, cs in enumerate(customer_summary):
            contact = cs["customer_email"] if cs["customer_email"] != "-" else cs["customer_contact"]
            cs_data.append([
                Paragraph(cs["customer_name"], cell_style),
                Paragraph(contact, cell_style),
                str(cs["transaction_count"]),
                fmt_currency(cs["total_spent"]),
                fmt_currency(cs["total_paid"]),
                fmt_currency(cs["outstanding"]),
            ])
            if float(cs["outstanding"] or 0) > 0:
                outstanding_rows.append(i + 1)

        cs_table = Table(cs_data, colWidths=[35 * mm, 35 * mm, 18 * mm, 28 * mm, 28 * mm, 28 * mm])
        cs_style = [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for row_idx in outstanding_rows:
            cs_style.append(("TEXTCOLOR", (5, row_idx), (5, row_idx), RED))
            cs_style.append(("FONTNAME", (5, row_idx), (5, row_idx), "Helvetica-Bold"))
        cs_table.setStyle(TableStyle(cs_style))
        elements.append(cs_table)

    # ── Detailed Transactions ──
    if detailed_sales:
        elements.append(Paragraph("Detailed Transactions", section_style))

        for sale in detailed_sales:
            sale_number = sale["sale_number"]
            status = sale["status"]
            mode_label = sale["sale_mode"].replace("_", " ").title()

            discount_text = ""
            if sale["promo_discount_amount"] and float(sale["promo_discount_amount"]) > 0:
                discount_text = f"  |  Discount: -{fmt_currency(sale['promo_discount_amount'])}"

            # Sale header
            elements.append(Paragraph(
                f"<b>{sale_number}</b> &nbsp; "
                f"<font color='#666'>{status.replace('_', ' ')}</font> &nbsp; "
                f"<font color='#999'>{mode_label}</font>"
                f"<font color='#999'>{discount_text}</font>",
                ParagraphStyle("SaleHeader", parent=styles["Normal"], fontSize=9, spaceBefore=6, spaceAfter=2),
            ))
            elements.append(Paragraph(
                f"<font color='#999'>{sale['ctime'] or ''} &bull; {sale['customer_name']} &bull; by {sale['sold_by'] or 'N/A'}</font>",
                ParagraphStyle("SaleMeta", parent=styles["Normal"], fontSize=8, spaceAfter=2),
            ))

            items = sale_items_by_number.get(sale_number, [])
            if items:
                item_data = [["Product", "Qty", "Unit Price", "Tax", "Line Total"]]
                for item in items:
                    item_data.append([
                        Paragraph(item["product_name"], cell_style),
                        str(item["quantity"]),
                        fmt_currency(item["final_price"]),
                        fmt_currency(item["tax_amount"]),
                        fmt_currency(item["line_total"]),
                    ])
                item_table = Table(item_data, colWidths=[60 * mm, 18 * mm, 30 * mm, 30 * mm, 30 * mm])
                item_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                elements.append(item_table)

            # Sale totals row
            balance = float(sale["balance_amount"] or 0)
            balance_color = "#dc3545" if balance > 0 else "#28a745"
            elements.append(Paragraph(
                f"<b>Total:</b> {fmt_currency(sale['total_amount'])} &nbsp;&nbsp; "
                f"<b>Paid:</b> {fmt_currency(sale['paid_amount'])} &nbsp;&nbsp; "
                f"<b>Balance:</b> <font color='{balance_color}'>{fmt_currency(sale['balance_amount'])}</font>",
                ParagraphStyle("SaleTotals", parent=styles["Normal"], fontSize=9, spaceAfter=6,
                               backColor=LIGHT_GREY, leftIndent=4, rightIndent=4,
                               spaceBefore=0, borderPadding=4),
            ))

    # ── Footer ──
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        f"This is an automated daily sales report from MyStoreGuard. "
        f"Generated on {datetime.datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC.",
        footer_style,
    ))

    doc.build(elements)
    return buf.getvalue()


def build_daily_sales_report_email_summary(
    store_name: str,
    location_name: str,
    sale_date: str,
    summary: dict,
) -> str:
    """Build a brief HTML email body to accompany the PDF attachment."""
    total_transactions = summary["total_transactions"] or 0
    gross_revenue = fmt_currency(summary["gross_revenue"] or 0)
    total_collected = fmt_currency(summary["total_collected"] or 0)
    total_outstanding = fmt_currency(summary["total_outstanding"] or 0)

    display_name = store_name or location_name
    formatted_date = datetime.datetime.strptime(sale_date, "%Y-%m-%d").strftime("%B %d, %Y")
    outstanding_color = "#dc3545" if float(summary["total_outstanding"] or 0) > 0 else "#28a745"

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #1a73e8;">Daily Sales Report</h2>
        <p><strong>{display_name}</strong> &mdash; {formatted_date}</p>
        <p>Please find attached the detailed daily sales report.</p>
        <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 4px 0;"><strong>Total Transactions:</strong> {total_transactions}</p>
            <p style="margin: 4px 0;"><strong>Gross Revenue:</strong> {gross_revenue}</p>
            <p style="margin: 4px 0;"><strong>Total Collected:</strong> {total_collected}</p>
            <p style="margin: 4px 0;"><strong>Outstanding:</strong> <span style="color: {outstanding_color};">{total_outstanding}</span></p>
        </div>
        <p>Open the attached PDF for the full breakdown including payment methods, top products, hourly sales, and detailed transactions.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #999;">This is an automated report from MyStoreGuard.</p>
    </body>
    </html>"""
