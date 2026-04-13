import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from shared.settings import (
    CP_NOTIFICATION_EMAIL_CREDENTIALS_TABLE,
    MAIL_SENDER_EMAIL,
    MAIL_SENDER_PWD,
)

logger = logging.getLogger("mystoreguard_functions")


def get_notification_email_credentials(cursor, tenant_id: str) -> tuple[str | None, str | None]:
    """
    Get email credentials for sending notifications.
    First checks tenant-specific credentials in cp_notification_email_credentials.
    Falls back to system default MAIL_SENDER_EMAIL / MAIL_SENDER_PWD env vars.
    """
    query = f"""
        SELECT notification_email, notification_password
        FROM {CP_NOTIFICATION_EMAIL_CREDENTIALS_TABLE}
        WHERE tenant_id = %s
            AND is_active = true
            AND delete_status = 'NOT_DELETED'
        LIMIT 1;
    """
    cursor.execute(query, (tenant_id,))
    row = cursor.fetchone()
    if row and row["notification_email"] and row["notification_password"]:
        return row["notification_email"], row["notification_password"]

    return MAIL_SENDER_EMAIL, MAIL_SENDER_PWD


def send_email(
    sender_email: str,
    sender_password: str,
    to_email: str,
    subject: str,
    body: str,
    pdf_bytes: bytes | None = None,
    pdf_filename: str | None = None,
) -> bool:
    """Send an HTML email via SMTP, optionally with a PDF attachment."""
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        if pdf_bytes and pdf_filename:
            pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
            msg.attach(pdf_part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_to_recipient_list(
    cursor,
    tenant_id: str,
    notification_email: str,
    subject: str,
    body: str,
    pdf_bytes: bytes | None = None,
    pdf_filename: str | None = None,
) -> int:
    """
    Send an email to a comma-separated list of recipients.
    Returns the number of emails successfully sent.
    """
    sender_email, sender_password = get_notification_email_credentials(cursor, tenant_id)
    if not sender_email or not sender_password:
        logger.warning(f"No email credentials available for tenant {tenant_id}. Skipping.")
        return 0

    recipient_emails = [e.strip() for e in notification_email.split(",") if e.strip()]
    if not recipient_emails:
        return 0

    emails_sent = 0
    for to_email in recipient_emails:
        if send_email(sender_email, sender_password, to_email, subject, body, pdf_bytes, pdf_filename):
            emails_sent += 1
    return emails_sent


def fmt_currency(amount) -> str:
    """Format a number as currency string."""
    if amount is None:
        return "0.00"
    return f"{float(amount):,.2f}"
