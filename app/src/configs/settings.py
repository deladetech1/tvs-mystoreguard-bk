import os
class Settings:

    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    DB_USER: str = os.getenv("DB_USER")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_NAME: str = os.getenv("DB_NAME")
    DB_PORT: str = os.getenv("DB_PORT")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true",1)
    APP_NAME: str = os.getenv("APP_NAME", "Python Template API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "detailed")  # detailed, json, simple
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "False").lower() in ("true", 1)
    LOG_MAX_SIZE: int = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
        
   # Security settings
    ALGORITHM: str = os.getenv("ALGORITHM")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "300"))
    
    # =============================================================================
    # SHARED TABLES (core_platform schema)
    # =============================================================================
    CORE_PLATFORM_USERS_TABLE = os.getenv("CORE_PLATFORM_USERS_TABLE", "core_platform.cp_users")
    CORE_PLATFORM_MEMBERS_TABLE = os.getenv("CORE_PLATFORM_MEMBERS_TABLE", "core_platform.cp_members")
    CORE_PLATFORM_RESOURCE_ID_TABLE = os.getenv("CORE_PLATFORM_RESOURCE_ID_TABLE", "core_platform.cp_shared_resource_ids")
    CORE_PLATFORM_TENANTS_TABLE = os.getenv("CORE_PLATFORM_TENANTS_TABLE", "core_platform.cp_tenants")
    CORE_PLATFORM_APP_SUBSCRIPTIONS_TABLE = os.getenv("CORE_PLATFORM_APP_SUBSCRIPTIONS_TABLE", "core_platform.cp_app_subscriptions")
    CORE_PLATFORM_APP_SUBSCRIPTION_HISTORY_TABLE = os.getenv("CORE_PLATFORM_APP_SUBSCRIPTION_HISTORY_TABLE", "core_platform.cp_app_subscription_histories")
    # Grace window (days) past period/trial end before access is cut. Must match core-platform.
    SUBSCRIPTION_GRACE_DAYS = int(os.getenv("SUBSCRIPTION_GRACE_DAYS", "4"))
    CORE_PLATFORM_APPS_TABLE = os.getenv("CORE_PLATFORM_APPS_TABLE", "core_platform.cp_apps")

    # =============================================================================
    # CORE PLATFORM TABLES (prefixed with cp_, now in core_platform schema with tenant_id)
    # =============================================================================
    # NOTE: These tables have been renamed from tenant_ prefix to cp_ (core platform).
    # All tables include tenant_id column for multi-tenant isolation.
    # Tables with is_system column can contain both user and system data.
    # System-level data is identified by is_system=true flag in the same tables.
    # =============================================================================
    CORE_PLATFORM_USER_GROUPS_TABLE = os.getenv("CORE_PLATFORM_USER_GROUPS_TABLE", "core_platform.cp_user_groups")
    CORE_PLATFORM_LOCATIONS_TABLE = os.getenv("CORE_PLATFORM_LOCATIONS_TABLE", "core_platform.cp_locations")
    CORE_PLATFORM_UNIT_OF_MEASURE_TABLE = os.getenv("CORE_PLATFORM_UNIT_OF_MEASURE_TABLE", "core_platform.cp_unit_of_measures")
    CORE_PLATFORM_CURRENCY = os.getenv("CORE_PLATFORM_CURRENCY", "core_platform.cp_currencies")
    CORE_PLATFORM_EXPENSE_TABLE = os.getenv("CORE_PLATFORM_EXPENSE_TABLE", "core_platform.cp_expense")
    CORE_PLATFORM_USER_LOCATIONS_TABLE = os.getenv("CORE_PLATFORM_USER_LOCATIONS_TABLE", "core_platform.cp_user_locations")
    CORE_PLATFORM_GROUP_LOCATIONS_TABLE = os.getenv("CORE_PLATFORM_GROUP_LOCATIONS_TABLE", "core_platform.cp_group_locations")
    CORE_PLATFORM_BUSINESS_APP_LOCATIONS_TABLE = os.getenv("CORE_PLATFORM_BUSINESS_APP_LOCATIONS_TABLE", "core_platform.cp_business_app_locations")
    CORE_PLATFORM_BUSINESSES_TABLE = os.getenv("CORE_PLATFORM_BUSINESSES_TABLE", "core_platform.cp_businesses")

    # =============================================================================
    # MYSTORE GUARD TABLES (mystoreguard schema)
    # =============================================================================
    CP_EXPENSES_HISTORY_TABLE = os.getenv("CP_EXPENSES_HISTORY_TABLE", "core_platform.cp_expenses_history")

    # For activity logs specifically for mystoreguard
    MSG_ACTIVITY_LOGS_TABLE = os.getenv("MSG_ACTIVITY_LOGS_TABLE", "mystoreguard.msg_activity_logs")

    # Mail Configurations
    MAIL_SENDER_EMAIL=os.getenv("MAIL_SENDER_EMAIL")
    MAIL_SENDER_PWD=os.getenv("MAIL_SENDER_PWD")

    # Application Configurations
    APP_URL=os.getenv("APP_URL", "https://trovesuite.com")
    USER_ASSIGNED_MANAGED_IDENTITY=os.getenv("USER_ASSIGNED_MANAGED_IDENTITY")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")
    
    # Azure Storage Container Names
    MYSTOREGUARD_FILES_CONTAINER = os.getenv("MYSTOREGUARD_FILES_CONTAINER", "mystoreguard")
    
    # Document paths table
    MSG_DOCUMENT_PATHS_TABLE = os.getenv("MSG_DOCUMENT_PATHS_TABLE", "mystoreguard.msg_document_paths")
    
    # Product metadata table
    MSG_PRODUCT_METADATA_TABLE = os.getenv("MSG_PRODUCT_METADATA_TABLE", "mystoreguard.msg_product_metadata")
    
    # Products table
    MSG_PRODUCTS_TABLE = os.getenv("MSG_PRODUCTS_TABLE", "mystoreguard.msg_products")
    MSG_PRODUCT_DOCUMENT_IDS_TABLE = os.getenv("MSG_PRODUCT_DOCUMENT_IDS_TABLE", "mystoreguard.msg_product_document_ids")
    MSG_PURCHASE_BATCHES_TABLE = os.getenv("MSG_PURCHASE_BATCHES_TABLE", "mystoreguard.msg_purchase_batches")
    # Product splits (break-bulk) table
    MSG_PRODUCT_SPLITS_TABLE = os.getenv("MSG_PRODUCT_SPLITS_TABLE", "mystoreguard.msg_product_splits")

    # Product metadata assignments table
    MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE = os.getenv("MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE", "mystoreguard.msg_assign_metadata_to_products")
    
    # Product prices table
    MSG_PRODUCT_PRICES_TABLE = os.getenv("MSG_PRODUCT_PRICES_TABLE", "mystoreguard.msg_product_prices")
    
    # Pricing rules table
    MSG_PRICING_RULES_TABLE = os.getenv("MSG_PRICING_RULES_TABLE", "mystoreguard.msg_pricing_rule")
    
    # Suppliers table
    MSG_SUPPLIERS_TABLE = os.getenv("MSG_SUPPLIERS_TABLE", "mystoreguard.msg_suppliers")
    
    # Purchase orders table
    MSG_PURCHASE_ORDERS_TABLE = os.getenv("MSG_PURCHASE_ORDERS_TABLE", "mystoreguard.msg_purchase_orders")
    MSG_PURCHASE_ORDER_ITEMS_TABLE = os.getenv("MSG_PURCHASE_ORDER_ITEMS_TABLE", "mystoreguard.msg_purchase_order_items")
    MSG_PURCHASE_RECEIPTS_TABLE = os.getenv("MSG_PURCHASE_RECEIPTS_TABLE", "mystoreguard.msg_purchase_receipts")
    
    # Store products table
    MSG_STORE_PRODUCTS_TABLE = os.getenv("MSG_STORE_PRODUCTS_TABLE", "mystoreguard.msg_store_products")
    # Warehouse products table
    MSG_WAREHOUSE_PRODUCTS_TABLE = os.getenv("MSG_WAREHOUSE_PRODUCTS_TABLE", "mystoreguard.msg_warehouse_products")
    MSG_BATCH_LOCATIONS_TABLE = os.getenv("MSG_BATCH_LOCATIONS_TABLE", "mystoreguard.msg_batch_locations")
    MSG_PRODUCT_MOVEMENTS_TABLE = os.getenv("MSG_PRODUCT_MOVEMENTS_TABLE", "mystoreguard.msg_product_movements")
    
    # Customers table
    MSG_CUSTOMERS_TABLE = os.getenv("MSG_CUSTOMERS_TABLE", "mystoreguard.msg_customers")
    
    # Taxes table
    MSG_TAXES_TABLE = os.getenv("MSG_TAXES_TABLE", "mystoreguard.msg_taxes")
    
    # Tax rules table
    MSG_TAX_RULES_TABLE = os.getenv("MSG_TAX_RULES_TABLE", "mystoreguard.msg_tax_rule")
    
    # Tax rule conditions table
    MSG_TAX_RULE_CONDITIONS_TABLE = os.getenv("MSG_TAX_RULE_CONDITIONS_TABLE", "mystoreguard.tax_rule_conditions")
    
    # Store configs table
    MSG_STORE_CONFIGS_TABLE = os.getenv("MSG_STORE_CONFIGS_TABLE", "mystoreguard.msg_store_configs")
    
    # Warehouse configs table
    MSG_WAREHOUSE_CONFIGS_TABLE = os.getenv("MSG_WAREHOUSE_CONFIGS_TABLE", "mystoreguard.msg_warehouse_configs")
    
    # Stock taking audit table
    MSG_STOCK_TAKING_AUDIT_TABLE = os.getenv("MSG_STOCK_TAKING_AUDIT_TABLE", "mystoreguard.msg_stock_taking_audit")

    # Manual stock take tables (count + investigate/resolve)
    MSG_STOCK_TAKES_TABLE = os.getenv("MSG_STOCK_TAKES_TABLE", "mystoreguard.msg_stock_takes")
    MSG_STOCK_TAKE_ITEMS_TABLE = os.getenv("MSG_STOCK_TAKE_ITEMS_TABLE", "mystoreguard.msg_stock_take_items")

    # Product transfers table
    MSG_PRODUCT_TRANSFERS_TABLE = os.getenv("MSG_PRODUCT_TRANSFERS_TABLE", "mystoreguard.msg_product_transfers")
    MSG_PRODUCT_TRANSFER_ITEMS_TABLE = os.getenv("MSG_PRODUCT_TRANSFER_ITEMS_TABLE", "mystoreguard.msg_product_transfer_items")
    MSG_PRODUCT_TRANSFER_APPROVALS_TABLE = os.getenv("MSG_PRODUCT_TRANSFER_APPROVALS_TABLE", "mystoreguard.msg_product_transfer_approvals")
    
    # Appointments table
    MSG_APPOINTMENTS_TABLE = os.getenv("MSG_APPOINTMENTS_TABLE", "mystoreguard.msg_appointments")

    # Tasks & workflows tables
    MSG_WORKFLOW_TEMPLATES_TABLE = os.getenv("MSG_WORKFLOW_TEMPLATES_TABLE", "mystoreguard.msg_workflow_templates")
    MSG_WORKFLOW_TEMPLATE_STEPS_TABLE = os.getenv("MSG_WORKFLOW_TEMPLATE_STEPS_TABLE", "mystoreguard.msg_workflow_template_steps")
    MSG_WORKFLOW_TEMPLATE_STEP_DEPS_TABLE = os.getenv("MSG_WORKFLOW_TEMPLATE_STEP_DEPS_TABLE", "mystoreguard.msg_workflow_template_step_deps")
    MSG_WORKFLOW_TEMPLATE_STEP_TARGETS_TABLE = os.getenv("MSG_WORKFLOW_TEMPLATE_STEP_TARGETS_TABLE", "mystoreguard.msg_workflow_template_step_targets")
    MSG_TASKS_TABLE = os.getenv("MSG_TASKS_TABLE", "mystoreguard.msg_tasks")
    MSG_TASK_STEPS_TABLE = os.getenv("MSG_TASK_STEPS_TABLE", "mystoreguard.msg_task_steps")
    MSG_TASK_STEP_DEPS_TABLE = os.getenv("MSG_TASK_STEP_DEPS_TABLE", "mystoreguard.msg_task_step_deps")
    MSG_TASK_STEP_TARGETS_TABLE = os.getenv("MSG_TASK_STEP_TARGETS_TABLE", "mystoreguard.msg_task_step_targets")
    MSG_TASK_NOTIFICATION_SETTINGS_TABLE = os.getenv("MSG_TASK_NOTIFICATION_SETTINGS_TABLE", "mystoreguard.msg_task_notification_settings")
    MSG_TASK_NOTIFICATIONS_TABLE = os.getenv("MSG_TASK_NOTIFICATIONS_TABLE", "mystoreguard.msg_task_notifications")
    CORE_PLATFORM_GROUPS_TABLE = os.getenv("CORE_PLATFORM_GROUPS_TABLE", "core_platform.cp_groups")

    # Sales tables
    MSG_SALES_TABLE = os.getenv("MSG_SALES_TABLE", "mystoreguard.msg_sales")
    MSG_SALES_ITEMS_TABLE = os.getenv("MSG_SALES_ITEMS_TABLE", "mystoreguard.msg_sales_items")
    MSG_SALES_PAYMENTS_TABLE = os.getenv("MSG_SALES_PAYMENTS_TABLE", "mystoreguard.msg_sales_payments")
    
    # Invoices tables
    MSG_INVOICES_TABLE = os.getenv("MSG_INVOICES_TABLE", "mystoreguard.msg_invoices")
    MSG_INVOICE_ITEMS_TABLE = os.getenv("MSG_INVOICE_ITEMS_TABLE", "mystoreguard.msg_invoice_items")
    MSG_INVOICE_PAYMENTS_TABLE = os.getenv("MSG_INVOICE_PAYMENTS_TABLE", "mystoreguard.msg_invoice_payments")
    MSG_INVOICE_SALES_TABLE = os.getenv("MSG_INVOICE_SALES_TABLE", "mystoreguard.msg_invoice_sales")
    
    # Deliveries tables
    MSG_DELIVERIES_TABLE = os.getenv("MSG_DELIVERIES_TABLE", "mystoreguard.msg_deliveries")
    MSG_DELIVERY_ITEMS_TABLE = os.getenv("MSG_DELIVERY_ITEMS_TABLE", "mystoreguard.msg_delivery_items")
    
    # Gift Cards tables
    MSG_GIFT_CARDS_TABLE = os.getenv("MSG_GIFT_CARDS_TABLE", "mystoreguard.msg_gift_cards")
    MSG_GIFT_CARD_TRANSACTIONS_TABLE = os.getenv("MSG_GIFT_CARD_TRANSACTIONS_TABLE", "mystoreguard.msg_gift_card_transactions")
    
    # Promo Codes tables
    MSG_PROMO_CODES_TABLE = os.getenv("MSG_PROMO_CODES_TABLE", "mystoreguard.msg_promo_codes")
    MSG_PROMO_CODE_USAGE_TABLE = os.getenv("MSG_PROMO_CODE_USAGE_TABLE", "mystoreguard.msg_promo_code_usage")
    
    # Return Policies table
    MSG_RETURN_POLICIES_TABLE = os.getenv("MSG_RETURN_POLICIES_TABLE", "mystoreguard.msg_return_policies")

    # Returns tables
    MSG_RETURNS_TABLE = os.getenv("MSG_RETURNS_TABLE", "mystoreguard.msg_returns")
    MSG_RETURN_ITEMS_TABLE = os.getenv("MSG_RETURN_ITEMS_TABLE", "mystoreguard.msg_return_items")

    # Messaging tables
    MSG_MESSAGES_TABLE = os.getenv("MSG_MESSAGES_TABLE", "mystoreguard.msg_messages")
    MSG_MESSAGE_RECIPIENTS_TABLE = os.getenv("MSG_MESSAGE_RECIPIENTS_TABLE", "mystoreguard.msg_message_recipients")

    # Meetings tables
    MSG_MEETINGS_TABLE = os.getenv("MSG_MEETINGS_TABLE", "mystoreguard.msg_meetings")
    MSG_MEETING_PARTICIPANTS_TABLE = os.getenv("MSG_MEETING_PARTICIPANTS_TABLE", "mystoreguard.msg_meeting_participants")

    # Affiliates tables
    MSG_AFFILIATES_TABLE = os.getenv("MSG_AFFILIATES_TABLE", "mystoreguard.msg_affiliates")
    MSG_AFFILIATE_REFERRALS_TABLE = os.getenv("MSG_AFFILIATE_REFERRALS_TABLE", "mystoreguard.msg_affiliate_referrals")
    MSG_AFFILIATE_COMMISSIONS_TABLE = os.getenv("MSG_AFFILIATE_COMMISSIONS_TABLE", "mystoreguard.msg_affiliate_commissions")

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        port = int(self.DB_PORT) if self.DB_PORT else 5432
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{port}/{self.DB_NAME}"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS from comma-separated string to list.
        When empty, defaults to common dev origins so local frontends work without env."""
        if not self.CORS_ORIGINS:
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8080",
            ]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

# Global settings instance
db_settings = Settings()