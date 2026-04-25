import datetime


def _base_email_template(title: str, content: str) -> str:
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 0; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background-color: #d97706; padding: 20px 30px;">
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
    if not items:
        return ""
    rows = ""
    for item in items:
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        elif hasattr(item, "dict"):
            item = item.dict()
        product_name = item.get("product_name") or "Unknown Product"
        qty = item.get("quantity_returned", 0)
        condition = item.get("condition", "")
        line_refund = item.get("line_refund_amount", 0) or 0
        rows += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{product_name}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center;">{qty}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center;">{condition}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: right;">{float(line_refund):,.2f}</td>
            </tr>"""

    return f"""
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <thead><tr style="background-color: #f8f9fa;">
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Product</th>
                <th style="padding: 10px 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Qty</th>
                <th style="padding: 10px 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Condition</th>
                <th style="padding: 10px 12px; text-align: right; border-bottom: 2px solid #dee2e6;">Refund</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>"""


def build_return_pending_approval_email(
    return_dict: dict,
    policy: dict,
    sale_dict: dict,
) -> tuple[str, str]:
    """Build email for an approver when a return is awaiting approval."""
    return_number = return_dict.get("return_number", "N/A")
    sale_number = sale_dict.get("sale_number") or return_dict.get("sale_id", "")
    policy_name = policy.get("name", "N/A") if policy else "N/A"
    reason = return_dict.get("reason") or ""
    reason_notes = return_dict.get("reason_notes") or ""
    total_refund = return_dict.get("total_refund_amount") or 0
    restocking_fee = return_dict.get("restocking_fee_amount") or 0
    created_by = return_dict.get("created_by") or ""
    customer_name = return_dict.get("customer_name") or ""
    items = return_dict.get("items") or []

    subject = f"Approval Required - Return {return_number}"

    details = f"""
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr><td style="padding: 6px 0; color: #666; width: 40%;">Return Number:</td><td style="padding: 6px 0; font-weight: bold;">{return_number}</td></tr>
            <tr><td style="padding: 6px 0; color: #666;">Sale Number:</td><td style="padding: 6px 0;">{sale_number}</td></tr>
            <tr><td style="padding: 6px 0; color: #666;">Return Policy:</td><td style="padding: 6px 0;">{policy_name}</td></tr>"""

    if customer_name:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Customer:</td><td style="padding: 6px 0;">{customer_name}</td></tr>'
    if created_by:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Created By:</td><td style="padding: 6px 0;">{created_by}</td></tr>'
    if reason:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Reason:</td><td style="padding: 6px 0;">{reason}</td></tr>'
    if reason_notes:
        details += f'<tr><td style="padding: 6px 0; color: #666;">Notes:</td><td style="padding: 6px 0;">{reason_notes}</td></tr>'

    details += f"""
            <tr><td style="padding: 6px 0; color: #666;">Restocking Fee:</td><td style="padding: 6px 0;">{float(restocking_fee):,.2f}</td></tr>
            <tr><td style="padding: 6px 0; color: #666;">Total Refund:</td><td style="padding: 6px 0; font-weight: bold; color: #d97706;">{float(total_refund):,.2f}</td></tr>
        </table>"""

    content = f"""
        <p>A new return has been submitted and is <strong>awaiting your approval</strong> under the <strong>{policy_name}</strong> return policy.</p>
        {details}
        <h3 style="color: #333; margin-top: 20px;">Items</h3>
        {_items_table(items)}
        <p style="margin-top: 20px;">Please review and approve or reject this return in the MyStoreGuard app.</p>"""

    return subject, _base_email_template("Return Awaiting Approval", content)
