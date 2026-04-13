import io
import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)


BLUE = colors.HexColor("#1a73e8")
RED = colors.HexColor("#dc3545")
ORANGE = colors.HexColor("#fd7e14")
LIGHT_GREY = colors.HexColor("#f8f9fa")
BORDER_GREY = colors.HexColor("#dee2e6")


def build_stock_alert_pdf(products: list[dict], location_type: str) -> bytes:
    """Build a PDF report for stock alerts and return it as bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontSize=18, textColor=BLUE, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=colors.grey, spaceAfter=16,
    )
    section_style = ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"],
        fontSize=13, spaceAfter=6,
    )
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey, alignment=1,
    )

    type_label = "Store" if location_type == "STORE" else "Warehouse"
    out_of_stock = [p for p in products if p["current_qty"] == 0]
    low_stock = [p for p in products if p["current_qty"] > 0]

    elements = []

    # Title
    elements.append(Paragraph(f"{type_label} Stock Alert Report", title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC",
        subtitle_style,
    ))

    # Summary
    summary_data = [
        ["Total Items", "Out of Stock", "Low Stock"],
        [str(len(products)), str(len(out_of_stock)), str(len(low_stock))],
    ]
    summary_table = Table(summary_data, colWidths=[60 * mm, 60 * mm, 60 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GREY),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10 * mm))

    def _build_product_table(items: list[dict]) -> Table:
        header = ["Product", "SKU", "Location", "Qty", "Reorder Level", "Status"]
        data = [header]
        for p in items:
            status = "Out of Stock" if p["current_qty"] == 0 else "Low Stock"
            data.append([
                Paragraph(p["product_name"], styles["Normal"]),
                p["sku"] or "-",
                p["location_name"],
                str(p["current_qty"]),
                str(p["reorder_level"]),
                status,
            ])

        col_widths = [55 * mm, 30 * mm, 35 * mm, 15 * mm, 25 * mm, 22 * mm]
        table = Table(data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (3, 0), (4, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        # Color status cells
        for i, item in enumerate(items, 1):
            color = RED if item["current_qty"] == 0 else ORANGE
            style_cmds.append(("TEXTCOLOR", (5, i), (5, i), color))
            style_cmds.append(("FONTNAME", (5, i), (5, i), "Helvetica-Bold"))

        table.setStyle(TableStyle(style_cmds))
        return table

    if out_of_stock:
        elements.append(Paragraph(
            f"<font color='#dc3545'>Out of Stock ({len(out_of_stock)} items)</font>",
            section_style,
        ))
        elements.append(_build_product_table(out_of_stock))
        elements.append(Spacer(1, 8 * mm))

    if low_stock:
        elements.append(Paragraph(
            f"<font color='#fd7e14'>Low Stock ({len(low_stock)} items)</font>",
            section_style,
        ))
        elements.append(_build_product_table(low_stock))
        elements.append(Spacer(1, 8 * mm))

    # Footer
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(
        "This is an automated stock alert report from MyStoreGuard. Please review and restock these products as soon as possible.",
        footer_style,
    ))

    doc.build(elements)
    return buf.getvalue()


def build_stock_alert_email_summary(products: list[dict], location_type: str) -> str:
    """Build a brief HTML email body to accompany the PDF attachment."""
    type_label = "Store" if location_type == "STORE" else "Warehouse"
    out_count = sum(1 for p in products if p["current_qty"] == 0)
    low_count = len(products) - out_count

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #1a73e8;">{type_label} Stock Alert</h2>
        <p>Please find attached the detailed stock alert report.</p>
        <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 4px 0;"><strong>Total items requiring attention:</strong> {len(products)}</p>
            <p style="margin: 4px 0; color: #dc3545;"><strong>Out of stock:</strong> {out_count}</p>
            <p style="margin: 4px 0; color: #fd7e14;"><strong>Low stock:</strong> {low_count}</p>
        </div>
        <p>Please review the attached PDF and restock these products as soon as possible.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #999;">This is an automated alert from MyStoreGuard.</p>
    </body>
    </html>"""
