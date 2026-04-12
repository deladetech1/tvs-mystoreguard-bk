import azure.functions as func
import datetime
import logging

from shared.database import get_db_connection
from shared.email_service import send_email, send_to_recipient_list, get_notification_email_credentials, fmt_currency
from stock_alerts.queries import (
    get_store_configs_with_out_of_stock_notifications,
    get_warehouse_configs_with_out_of_stock_notifications,
    get_low_stock_store_products_by_location,
    get_low_stock_warehouse_products_by_location,
    should_send_alert,
)
from stock_alerts.pdf_builder import build_stock_alert_pdf, build_stock_alert_email_summary
from daily_sales_report.queries import (
    get_store_configs_for_daily_reports,
    is_closing_time_slot,
    get_alert_recipients_for_store,
    get_sales_summary,
    get_payment_method_breakdown,
    get_top_selling_products,
    get_sales_by_hour,
    get_customer_summary,
    get_detailed_sales,
    get_sale_items,
)
from daily_sales_report.pdf_builder import build_daily_sales_report_pdf, build_daily_sales_report_email_summary

app = func.FunctionApp()

logger = logging.getLogger("mystoreguard_functions")


# ══════════════════════════════════════════════════
# Store Stock Alert (every 30 min)
# ══════════════════════════════════════════════════

@app.timer_trigger(schedule="0 */30 * * * *", arg_name="timer", run_on_startup=False)
def check_store_out_of_stock_alert(timer: func.TimerRequest) -> None:
    """Checks for out-of-stock and low-stock store products."""
    logger.info("Store stock alert triggered at %s", datetime.datetime.utcnow().isoformat())

    if timer.past_due:
        logger.warning("Store stock alert timer is past due — running catch-up execution.")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            configs = get_store_configs_with_out_of_stock_notifications(cursor)
            if not configs:
                logger.info("No store configs with out of stock notification enabled.")
                return

            total_emails_sent = 0
            for config in configs:
                if not should_send_alert(config["out_of_stock_notification_occurrence"]):
                    continue

                products = get_low_stock_store_products_by_location(
                    cursor, config["tenant_id"], config["org_id"], config["bus_id"], config["loc_id"],
                )
                if not products:
                    continue

                logger.info(f"Found {len(products)} low-stock store products at loc={config['loc_id']}")
                pdf_bytes = build_stock_alert_pdf(products, "STORE")
                email_body = build_stock_alert_email_summary(products, "STORE")
                out_count = sum(1 for p in products if p["current_qty"] == 0)
                low_count = len(products) - out_count
                subject = f"Store Stock Alert: {out_count} out of stock, {low_count} low stock items"
                today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
                pdf_filename = f"Store_Stock_Alert_{today_str}.pdf"
                total_emails_sent += send_to_recipient_list(
                    cursor, config["tenant_id"], config["out_of_stock_notification_email"],
                    subject, email_body, pdf_bytes, pdf_filename,
                )

            logger.info(f"Store stock alert complete. {total_emails_sent} email(s) sent.")

    except Exception as e:
        logger.error(f"Store stock alert function failed: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


# ══════════════════════════════════════════════════
# Warehouse Stock Alert (every 30 min)
# ══════════════════════════════════════════════════

@app.timer_trigger(schedule="0 */30 * * * *", arg_name="timer", run_on_startup=False)
def check_warehouse_out_of_stock_alert(timer: func.TimerRequest) -> None:
    """Checks for out-of-stock and low-stock warehouse products."""
    logger.info("Warehouse stock alert triggered at %s", datetime.datetime.utcnow().isoformat())

    if timer.past_due:
        logger.warning("Warehouse stock alert timer is past due — running catch-up execution.")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            configs = get_warehouse_configs_with_out_of_stock_notifications(cursor)
            if not configs:
                logger.info("No warehouse configs with out of stock notification enabled.")
                return

            total_emails_sent = 0
            for config in configs:
                if not should_send_alert(config["out_of_stock_notification_occurrence"]):
                    continue

                products = get_low_stock_warehouse_products_by_location(
                    cursor, config["tenant_id"], config["org_id"], config["bus_id"], config["loc_id"],
                )
                if not products:
                    continue

                logger.info(f"Found {len(products)} low-stock warehouse products at loc={config['loc_id']}")
                pdf_bytes = build_stock_alert_pdf(products, "WAREHOUSE")
                email_body = build_stock_alert_email_summary(products, "WAREHOUSE")
                out_count = sum(1 for p in products if p["current_qty"] == 0)
                low_count = len(products) - out_count
                subject = f"Warehouse Stock Alert: {out_count} out of stock, {low_count} low stock items"
                today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
                pdf_filename = f"Warehouse_Stock_Alert_{today_str}.pdf"
                total_emails_sent += send_to_recipient_list(
                    cursor, config["tenant_id"], config["out_of_stock_notification_email"],
                    subject, email_body, pdf_bytes, pdf_filename,
                )

            logger.info(f"Warehouse stock alert complete. {total_emails_sent} email(s) sent.")

    except Exception as e:
        logger.error(f"Warehouse stock alert function failed: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


# ══════════════════════════════════════════════════
# Daily Sales Report (every 30 min)
# ══════════════════════════════════════════════════

@app.timer_trigger(schedule="0 */30 * * * *", arg_name="timer", run_on_startup=False)
def send_daily_sales_report(timer: func.TimerRequest) -> None:
    """Sends a comprehensive daily sales report at each store's closing time."""
    logger.info("Daily sales report function triggered at %s", datetime.datetime.utcnow().isoformat())

    if timer.past_due:
        logger.warning("Daily sales report timer is past due — running catch-up execution.")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            configs = get_store_configs_for_daily_reports(cursor)
            if not configs:
                logger.info("No store configs with daily reports enabled.")
                return

            today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
            total_emails_sent = 0

            for config in configs:
                if not is_closing_time_slot(config["closing_time"]):
                    continue

                tenant_id = config["tenant_id"]
                org_id = config["org_id"]
                bus_id = config["bus_id"]
                loc_id = config["loc_id"]

                logger.info(f"Generating daily sales report for loc={loc_id}, store={config['store_name']}")

                summary = get_sales_summary(cursor, tenant_id, org_id, bus_id, loc_id, today)
                payment_breakdown = get_payment_method_breakdown(cursor, tenant_id, org_id, bus_id, loc_id, today)
                top_products = get_top_selling_products(cursor, tenant_id, org_id, bus_id, loc_id, today)
                hourly_sales = get_sales_by_hour(cursor, tenant_id, org_id, bus_id, loc_id, today)
                customer_summary_data = get_customer_summary(cursor, tenant_id, org_id, bus_id, loc_id, today)
                detailed_sales = get_detailed_sales(cursor, tenant_id, org_id, bus_id, loc_id, today)
                sale_items_by_number = get_sale_items(cursor, tenant_id, org_id, bus_id, loc_id, today)

                pdf_bytes = build_daily_sales_report_pdf(
                    store_name=config["store_name"],
                    location_name=config["location_name"],
                    sale_date=today,
                    summary=summary,
                    payment_breakdown=payment_breakdown,
                    top_products=top_products,
                    hourly_sales=hourly_sales,
                    customer_summary=customer_summary_data,
                    detailed_sales=detailed_sales,
                    sale_items_by_number=sale_items_by_number,
                )

                email_body = build_daily_sales_report_email_summary(
                    store_name=config["store_name"],
                    location_name=config["location_name"],
                    sale_date=today,
                    summary=summary,
                )

                total_transactions = summary["total_transactions"] or 0
                gross_revenue = fmt_currency(summary["gross_revenue"])
                display_name = config["store_name"] or config["location_name"]
                subject = f"Daily Sales Report — {display_name} — {total_transactions} sales, {gross_revenue} revenue"
                pdf_filename = f"Daily_Sales_Report_{display_name}_{today}.pdf"

                if config["sales_notification_emails"]:
                    total_emails_sent += send_to_recipient_list(
                        cursor, tenant_id, config["sales_notification_emails"],
                        subject, email_body, pdf_bytes, pdf_filename,
                    )
                else:
                    recipients = get_alert_recipients_for_store(cursor, tenant_id, org_id, bus_id)
                    sender_email, sender_password = get_notification_email_credentials(cursor, tenant_id)
                    if sender_email and sender_password:
                        for r in recipients:
                            if send_email(sender_email, sender_password, r["email"], subject, email_body, pdf_bytes, pdf_filename):
                                total_emails_sent += 1

            logger.info(f"Daily sales report complete. {total_emails_sent} email(s) sent.")

    except Exception as e:
        logger.error(f"Daily sales report function failed: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()
