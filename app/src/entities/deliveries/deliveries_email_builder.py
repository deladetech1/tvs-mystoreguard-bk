import datetime


def _status_color(status: str) -> str:
    """Return a color for the delivery status badge"""
    colors = {
        "PENDING": "#ffc107",
        "SCHEDULED": "#17a2b8",
        "OUT_FOR_DELIVERY": "#007bff",
        "DELIVERED": "#28a745",
        "FAILED": "#dc3545",
        "CANCELLED": "#6c757d",
    }
    return colors.get(status, "#6c757d")


def _status_label(status: str) -> str:
    """Return a human-readable label for the delivery status"""
    labels = {
        "PENDING": "Pending",
        "SCHEDULED": "Scheduled",
        "OUT_FOR_DELIVERY": "Out for Delivery",
        "DELIVERED": "Delivered",
        "FAILED": "Failed",
        "CANCELLED": "Cancelled",
    }
    return labels.get(status, status)


def _base_email_template(title: str, content: str) -> str:
    """Wrap content in a consistent email template"""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 0; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background-color: #1a73e8; padding: 20px 30px;">
                <h2 style="color: #ffffff; margin: 0;">{title}</h2>
            </div>
            <div style="padding: 30px;">
                {content}
            </div>
            <div style="background-color: #f8f9fa; padding: 15px 30px; border-top: 1px solid #eee;">
                <p style="font-size: 12px; color: #999; margin: 0;">
                    This is an automated notification from MyStoreGuard. Generated on {datetime.datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')} UTC.
                </p>
            </div>
        </div>
    </body></html>"""


def _items_table(items: list) -> str:
    """Build an HTML table for delivery items"""
    if not items:
        return ""
    rows = ""
    for item in items:
        product_name = item.get("product_name") or "Unknown Product"
        ordered_qty = item.get("ordered_qty", 0)
        delivered_qty = item.get("delivered_qty", 0)
        rows += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{product_name}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center;">{ordered_qty}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center;">{delivered_qty}</td>
            </tr>"""

    return f"""
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <thead><tr style="background-color: #f8f9fa;">
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Product</th>
                <th style="padding: 10px 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Ordered Qty</th>
                <th style="padding: 10px 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Delivered Qty</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>"""


def _delivery_details_section(
    delivery_number: str,
    status: str,
    recipient_name: str,
    delivery_address: str,
    recipient_phone: str = None,
    delivery_type: str = None,
    scheduled_date=None,
    tracking_number: str = None,
    driver_name: str = None,
    third_party_name: str = None,
    delivery_notes: str = None,
    delivery_fee: float = None,
    currency_symbol: str = None,
    sale_number: str = None,
) -> str:
    """Build delivery details section"""
    status_badge = f'<span style="display: inline-block; padding: 4px 12px; border-radius: 4px; background-color: {_status_color(status)}; color: #fff; font-weight: bold; font-size: 13px;">{_status_label(status)}</span>'

    details = f"""
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr><td style="padding: 6px 0; color: #666; width: 40%;">Delivery Number:</td><td style="padding: 6px 0; font-weight: bold;">{delivery_number}</td></tr>
            <tr><td style="padding: 6px 0; color: #666;">Status:</td><td style="padding: 6px 0;">{status_badge}</td></tr>"""

    if sale_number:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Sale Number:</td><td style="padding: 6px 0;">{sale_number}</td></tr>'

    details += f'<tr><td style="padding: 6px 0; color: #666;">Recipient:</td><td style="padding: 6px 0;">{recipient_name}</td></tr>'

    if recipient_phone:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Phone:</td><td style="padding: 6px 0;">{recipient_phone}</td></tr>'

    details += f'<tr><td style="padding: 6px 0; color: #666;">Delivery Address:</td><td style="padding: 6px 0;">{delivery_address}</td></tr>'

    if delivery_type:
        type_label = delivery_type.replace("_", " ").title()
        details += f'<tr><td style="padding: 6px 0; color: #666;">Delivery Type:</td><td style="padding: 6px 0;">{type_label}</td></tr>'

    if scheduled_date:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Scheduled Date:</td><td style="padding: 6px 0;">{scheduled_date}</td></tr>'

    if driver_name:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Driver:</td><td style="padding: 6px 0;">{driver_name}</td></tr>'

    if third_party_name:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Courier:</td><td style="padding: 6px 0;">{third_party_name}</td></tr>'

    if tracking_number:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Tracking Number:</td><td style="padding: 6px 0;">{tracking_number}</td></tr>'

    if delivery_fee is not None and delivery_fee > 0:
        symbol = currency_symbol or ""
        details += f'<tr><td style="padding: 6px 0; color: #666;">Delivery Fee:</td><td style="padding: 6px 0;">{symbol}{delivery_fee:,.2f}</td></tr>'

    if delivery_notes:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Notes:</td><td style="padding: 6px 0;">{delivery_notes}</td></tr>'

    details += "</table>"
    return details


def build_delivery_created_email(delivery: dict, items: list) -> tuple[str, str]:
    """Build email subject and body for delivery creation"""
    delivery_number = delivery.get("delivery_number", "N/A")
    subject = f"New Delivery Created - {delivery_number}"

    content = f"""
        <p>A new delivery has been created for your order.</p>
        {_delivery_details_section(
            delivery_number=delivery_number,
            status=delivery.get("delivery_status", "PENDING"),
            recipient_name=delivery.get("recipient_name", ""),
            delivery_address=delivery.get("delivery_address", ""),
            recipient_phone=delivery.get("recipient_phone"),
            delivery_type=delivery.get("delivery_type"),
            scheduled_date=delivery.get("scheduled_date"),
            tracking_number=delivery.get("tracking_number"),
            driver_name=delivery.get("driver_name"),
            third_party_name=delivery.get("third_party_name"),
            delivery_notes=delivery.get("delivery_notes"),
            delivery_fee=delivery.get("delivery_fee"),
            currency_symbol=delivery.get("currency_symbol"),
            sale_number=delivery.get("sale_number"),
        )}
        <h3 style="color: #333; margin-top: 20px;">Items</h3>
        {_items_table(items)}
        <p style="margin-top: 20px;">We will keep you updated on the status of your delivery.</p>"""

    return subject, _base_email_template("Delivery Created", content)


def build_delivery_status_changed_email(
    delivery: dict, old_status: str, new_status: str, notes: str = None
) -> tuple[str, str]:
    """Build email subject and body for delivery status change"""
    delivery_number = delivery.get("delivery_number", "N/A")
    subject = f"Delivery {delivery_number} - Status Updated to {_status_label(new_status)}"

    old_badge = f'<span style="display: inline-block; padding: 3px 10px; border-radius: 4px; background-color: {_status_color(old_status)}; color: #fff; font-size: 12px;">{_status_label(old_status)}</span>'
    new_badge = f'<span style="display: inline-block; padding: 3px 10px; border-radius: 4px; background-color: {_status_color(new_status)}; color: #fff; font-size: 12px;">{_status_label(new_status)}</span>'

    content = f"""
        <p>The status of your delivery <strong>{delivery_number}</strong> has been updated.</p>
        <div style="background-color: #f8f9fa; padding: 15px 20px; border-radius: 6px; margin: 15px 0; text-align: center;">
            {old_badge}
            <span style="margin: 0 10px; color: #666; font-size: 18px;">&rarr;</span>
            {new_badge}
        </div>"""

    if notes:
        content += f'<p style="margin-top: 10px;"><strong>Notes:</strong> {notes}</p>'

    content += f"""
        {_delivery_details_section(
            delivery_number=delivery_number,
            status=new_status,
            recipient_name=delivery.get("recipient_name", ""),
            delivery_address=delivery.get("delivery_address", ""),
            recipient_phone=delivery.get("recipient_phone"),
            delivery_type=delivery.get("delivery_type"),
            tracking_number=delivery.get("tracking_number"),
            driver_name=delivery.get("driver_name"),
            third_party_name=delivery.get("third_party_name"),
            delivery_fee=delivery.get("delivery_fee"),
            currency_symbol=delivery.get("currency_symbol"),
            sale_number=delivery.get("sale_number"),
        )}"""

    return subject, _base_email_template("Delivery Status Update", content)


def build_delivery_dispatched_email(delivery: dict, notes: str = None) -> tuple[str, str]:
    """Build email subject and body for delivery dispatch"""
    delivery_number = delivery.get("delivery_number", "N/A")
    subject = f"Delivery {delivery_number} - Out for Delivery"

    content = f"""
        <p>Great news! Your delivery <strong>{delivery_number}</strong> is now <strong>out for delivery</strong>.</p>
        {_delivery_details_section(
            delivery_number=delivery_number,
            status="OUT_FOR_DELIVERY",
            recipient_name=delivery.get("recipient_name", ""),
            delivery_address=delivery.get("delivery_address", ""),
            recipient_phone=delivery.get("recipient_phone"),
            delivery_type=delivery.get("delivery_type"),
            tracking_number=delivery.get("tracking_number"),
            driver_name=delivery.get("driver_name"),
            third_party_name=delivery.get("third_party_name"),
            delivery_fee=delivery.get("delivery_fee"),
            currency_symbol=delivery.get("currency_symbol"),
            sale_number=delivery.get("sale_number"),
        )}"""

    if notes:
        content += f'<p><strong>Dispatch Notes:</strong> {notes}</p>'

    content += '<p style="margin-top: 20px;">Please ensure someone is available at the delivery address to receive the package.</p>'

    return subject, _base_email_template("Delivery Dispatched", content)


def build_delivery_completed_email(delivery: dict, notes: str = None) -> tuple[str, str]:
    """Build email subject and body for delivery completion"""
    delivery_number = delivery.get("delivery_number", "N/A")
    subject = f"Delivery {delivery_number} - Successfully Delivered"

    content = f"""
        <p>Your delivery <strong>{delivery_number}</strong> has been <strong style="color: #28a745;">successfully delivered</strong>.</p>
        {_delivery_details_section(
            delivery_number=delivery_number,
            status="DELIVERED",
            recipient_name=delivery.get("recipient_name", ""),
            delivery_address=delivery.get("delivery_address", ""),
            recipient_phone=delivery.get("recipient_phone"),
            delivery_type=delivery.get("delivery_type"),
            tracking_number=delivery.get("tracking_number"),
            driver_name=delivery.get("driver_name"),
            third_party_name=delivery.get("third_party_name"),
            delivery_fee=delivery.get("delivery_fee"),
            currency_symbol=delivery.get("currency_symbol"),
            sale_number=delivery.get("sale_number"),
        )}"""

    if notes:
        content += f'<p><strong>Delivery Notes:</strong> {notes}</p>'

    content += '<p style="margin-top: 20px;">Thank you for your order!</p>'

    return subject, _base_email_template("Delivery Completed", content)


def build_delivery_cancelled_email(delivery: dict, reason: str = None) -> tuple[str, str]:
    """Build email subject and body for delivery cancellation"""
    delivery_number = delivery.get("delivery_number", "N/A")
    subject = f"Delivery {delivery_number} - Cancelled"

    content = f"""
        <p>Your delivery <strong>{delivery_number}</strong> has been <strong style="color: #dc3545;">cancelled</strong>.</p>"""

    if reason:
        content += f"""
        <div style="background-color: #fff3cd; padding: 12px 20px; border-radius: 6px; margin: 15px 0; border-left: 4px solid #ffc107;">
            <strong>Reason:</strong> {reason}
        </div>"""

    content += f"""
        {_delivery_details_section(
            delivery_number=delivery_number,
            status="CANCELLED",
            recipient_name=delivery.get("recipient_name", ""),
            delivery_address=delivery.get("delivery_address", ""),
            recipient_phone=delivery.get("recipient_phone"),
            sale_number=delivery.get("sale_number"),
        )}
        <p style="margin-top: 20px;">If you have any questions, please contact us.</p>"""

    return subject, _base_email_template("Delivery Cancelled", content)
