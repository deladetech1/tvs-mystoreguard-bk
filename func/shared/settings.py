import os


# Database
DB_URL = os.getenv("DB_URL")

# Email fallback credentials
MAIL_SENDER_EMAIL = os.getenv("MAIL_SENDER_EMAIL")
MAIL_SENDER_PWD = os.getenv("MAIL_SENDER_PWD")

# Mystoreguard tables
MSG_STORE_CONFIGS_TABLE = os.getenv("MSG_STORE_CONFIGS_TABLE", "mystoreguard.msg_store_configs")
MSG_WAREHOUSE_CONFIGS_TABLE = os.getenv("MSG_WAREHOUSE_CONFIGS_TABLE", "mystoreguard.msg_warehouse_configs")
MSG_STORE_PRODUCTS_TABLE = os.getenv("MSG_STORE_PRODUCTS_TABLE", "mystoreguard.msg_store_products")
MSG_WAREHOUSE_PRODUCTS_TABLE = os.getenv("MSG_WAREHOUSE_PRODUCTS_TABLE", "mystoreguard.msg_warehouse_products")
MSG_PRODUCTS_TABLE = os.getenv("MSG_PRODUCTS_TABLE", "mystoreguard.msg_products")
MSG_SALES_TABLE = os.getenv("MSG_SALES_TABLE", "mystoreguard.msg_sales")
MSG_SALES_ITEMS_TABLE = os.getenv("MSG_SALES_ITEMS_TABLE", "mystoreguard.msg_sales_items")
MSG_SALES_PAYMENTS_TABLE = os.getenv("MSG_SALES_PAYMENTS_TABLE", "mystoreguard.msg_sales_payments")
MSG_CUSTOMERS_TABLE = os.getenv("MSG_CUSTOMERS_TABLE", "mystoreguard.msg_customers")

# Messaging & Meetings tables
MSG_MESSAGES_TABLE = os.getenv("MSG_MESSAGES_TABLE", "mystoreguard.msg_messages")
MSG_MESSAGE_RECIPIENTS_TABLE = os.getenv("MSG_MESSAGE_RECIPIENTS_TABLE", "mystoreguard.msg_message_recipients")
MSG_MEETINGS_TABLE = os.getenv("MSG_MEETINGS_TABLE", "mystoreguard.msg_meetings")
MSG_MEETING_PARTICIPANTS_TABLE = os.getenv("MSG_MEETING_PARTICIPANTS_TABLE", "mystoreguard.msg_meeting_participants")
MSG_SUPPLIERS_TABLE = os.getenv("MSG_SUPPLIERS_TABLE", "mystoreguard.msg_suppliers")

# Core platform tables
CP_NOTIFICATION_EMAIL_CREDENTIALS_TABLE = os.getenv("CP_NOTIFICATION_EMAIL_CREDENTIALS_TABLE", "core_platform.cp_notification_email_credentials")
CP_LOCATIONS_TABLE = os.getenv("CP_LOCATIONS_TABLE", "core_platform.cp_locations")
CP_USERS_TABLE = os.getenv("CP_USERS_TABLE", "core_platform.cp_users")
CP_ASSIGN_ROLES_TABLE = os.getenv("CP_ASSIGN_ROLES_TABLE", "core_platform.cp_assign_roles")
