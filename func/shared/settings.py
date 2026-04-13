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

# Core platform tables
CP_NOTIFICATION_EMAIL_CREDENTIALS_TABLE = os.getenv("CP_NOTIFICATION_EMAIL_CREDENTIALS_TABLE", "core_platform.cp_notification_email_credentials")
CP_LOCATIONS_TABLE = os.getenv("CP_LOCATIONS_TABLE", "core_platform.cp_locations")
CP_USERS_TABLE = os.getenv("CP_USERS_TABLE", "core_platform.cp_users")
CP_ASSIGN_ROLES_TABLE = os.getenv("CP_ASSIGN_ROLES_TABLE", "core_platform.cp_assign_roles")
