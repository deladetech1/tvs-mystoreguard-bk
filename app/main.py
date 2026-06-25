from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from src.configs.logging import setup_logging
from src.configs.settings import db_settings
from trovesuite.configs.database import initialize_database
from src.middleware.logging_middleware import (
    LoggingMiddleware,
    SecurityLoggingMiddleware,
)
from src.middleware.exception_handler import (
    response_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)
from fastapi import HTTPException
from src.entities.shared.sh_response import ResponseException

# Patch Helper class to add current_date_time method
from src.utils.helper_patch import Helper

# Import Routes
from src.entities.expenses.expenses_controller import expenses_router
from src.entities.filemanager.fmg_controller import file_management_router
from src.entities.shared.unified_logs_controller import unified_logs_router
from src.entities.prod_metadata.prod_metadata_controller import prod_metadata_router
from src.entities.products.products_controller import products_router
from src.entities.product_prices.product_prices_controller import product_prices_router
from src.entities.store_products.store_products_controller import store_products_router
from src.entities.warehouse_products.warehouse_products_controller import warehouse_products_router
from src.entities.stock_takes.stock_takes_controller import stock_takes_router
from src.entities.pricing_rules.pricing_rules_controller import pricing_rules_router
from src.entities.suppliers.suppliers_controller import suppliers_router
from src.entities.customers.customers_controller import customers_router
from src.entities.currencies.currencies_controller import currencies_router
from src.entities.locations.locations_controller import locations_router
from src.entities.unit_of_measures.unit_of_measures_controller import unit_of_measures_router
from src.entities.taxes.taxes_controller import taxes_router
from src.entities.tax_rules.tax_rules_controller import tax_rules_router
from src.entities.store_configs.store_configs_controller import store_configs_router
from src.entities.warehouse_configs.warehouse_configs_controller import warehouse_configs_router
from src.entities.store_transfers.store_transfers_controller import store_transfers_router
from src.entities.warehouse_transfers.warehouse_transfers_controller import warehouse_transfers_router
from src.entities.users.users_controller import users_router
from src.entities.appointments.appointments_controller import appointments_router
from src.entities.workflow_templates.workflow_templates_controller import workflow_templates_router
from src.entities.tasks.tasks_controller import tasks_router
from src.entities.purchase_orders.purchase_orders_controller import purchase_orders_router
from src.entities.store_sales.store_sales_controller import store_sales_router
from src.entities.invoices.invoices_controller import invoices_router
from src.entities.deliveries.deliveries_controller import deliveries_router
from src.entities.dashboard.dashboard_controller import dashboard_router
from src.entities.reports.reports_controller import reports_router
from src.entities.gift_cards.gift_cards_controller import gift_cards_router
from src.entities.promo_codes.promo_codes_controller import promo_codes_router
from src.entities.affiliates.affiliates_controller import affiliates_router
from src.entities.return_policies.return_policies_controller import return_policies_router
from src.entities.store_returns.store_returns_controller import store_returns_router
from src.entities.messaging.messaging_controller import messaging_router
from src.entities.meetings.meetings_controller import meetings_router

# Initialize logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    FIXED: Replaced time.sleep() with asyncio.sleep() to avoid blocking the event loop.
    FIXED: Application will NOT start if database initialization fails - prevents 503 errors.
    """
    import asyncio
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Initializing database connection pool "
                f"(attempt {attempt}/{max_retries})..."
            )
            initialize_database()
            logger.info("✅ Database initialization completed successfully")
            break  # Success, exit retry loop
        except Exception as e:
            logger.error(
                f"Database initialization attempt {attempt} failed: {str(e)}"
            )
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                # Use asyncio.sleep() instead of time.sleep() to avoid blocking event loop
                await asyncio.sleep(retry_delay)
            else:
                logger.critical(
                    "❌ CRITICAL: All database initialization attempts failed!"
                )
                logger.critical(
                    "❌ Application will NOT start without a database connection."
                )
                logger.critical(
                    "❌ Please check your DATABASE_URL and database configuration."
                )
                # Raise exception to prevent app from starting without DB
                # This prevents 503 errors from auth endpoints trying to use None pool
                raise RuntimeError(
                    "Database initialization failed after all retries. "
                    "Application cannot start without a database connection."
                )
    
    yield
    
    # Shutdown: Cleanup (if needed)
    logger.info("Application shutting down...")

app = FastAPI(
    title="Mystoreguard",
    description="API for Mystoreguard application",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add exception handlers (order matters - more specific handlers first)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ResponseException, response_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Add logging middleware (order matters - add before CORS)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityLoggingMiddleware)


# Catch unhandled exceptions HERE, inside CORSMiddleware, and convert them to a
# JSONResponse. This middleware is registered before CORSMiddleware below, so it
# ends up *inside* the CORS layer: the error response it returns flows back out
# through CORSMiddleware and receives the Access-Control-Allow-Origin header.
#
# Without this, an unhandled exception propagates up to Starlette's
# ServerErrorMiddleware (which sits OUTSIDE CORSMiddleware). The resulting 500
# response has no CORS headers, so the browser reports it as a CORS failure
# ("No 'Access-Control-Allow-Origin' header is present") and the real server
# error is hidden from the frontend.
@app.middleware("http")
async def cors_safe_exception_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        # HTTPException / ResponseException are already handled by their own
        # handlers in the inner ExceptionMiddleware, so only genuinely unhandled
        # exceptions reach here. generic_exception_handler logs and returns a 500.
        return await generic_exception_handler(request, exc)


app.add_middleware(
    CORSMiddleware,
    allow_origins=db_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    logger.info("Root endpoint accessed - auto-reload test")
    return RedirectResponse("/docs")


# Log application startup
logger.info("Application starting up")
logger.info(
    "Including routers: health_check_router, clients_router, registration_router, capturing_router, reference_data_router"
)

app.include_router(prefix="/api/v1", router=expenses_router)
app.include_router(prefix="/api/v1", router=file_management_router)
app.include_router(prefix="/api/v1", router=unified_logs_router)
app.include_router(prefix="/api/v1", router=prod_metadata_router)
app.include_router(prefix="/api/v1", router=products_router)
app.include_router(prefix="/api/v1", router=product_prices_router)
app.include_router(prefix="/api/v1", router=store_products_router)
app.include_router(prefix="/api/v1", router=warehouse_products_router)
app.include_router(prefix="/api/v1", router=stock_takes_router)
app.include_router(prefix="/api/v1", router=pricing_rules_router)
app.include_router(prefix="/api/v1", router=taxes_router)
app.include_router(prefix="/api/v1", router=tax_rules_router)
app.include_router(prefix="/api/v1", router=suppliers_router)
app.include_router(prefix="/api/v1", router=customers_router)
app.include_router(prefix="/api/v1", router=currencies_router)
app.include_router(prefix="/api/v1", router=locations_router)
app.include_router(prefix="/api/v1", router=unit_of_measures_router)
app.include_router(prefix="/api/v1", router=store_configs_router)
app.include_router(prefix="/api/v1", router=warehouse_configs_router)
app.include_router(prefix="/api/v1", router=store_transfers_router)
app.include_router(prefix="/api/v1", router=warehouse_transfers_router)
app.include_router(prefix="/api/v1", router=users_router)
app.include_router(prefix="/api/v1", router=appointments_router)
app.include_router(prefix="/api/v1", router=workflow_templates_router)
app.include_router(prefix="/api/v1", router=tasks_router)
app.include_router(prefix="/api/v1", router=purchase_orders_router)
app.include_router(prefix="/api/v1", router=store_sales_router)
app.include_router(prefix="/api/v1", router=invoices_router)
app.include_router(prefix="/api/v1", router=deliveries_router)
app.include_router(prefix="/api/v1", router=dashboard_router)
app.include_router(prefix="/api/v1", router=reports_router)
app.include_router(prefix="/api/v1", router=gift_cards_router)
app.include_router(prefix="/api/v1", router=promo_codes_router)
app.include_router(prefix="/api/v1", router=affiliates_router)
app.include_router(prefix="/api/v1", router=return_policies_router)
app.include_router(prefix="/api/v1", router=store_returns_router)
app.include_router(prefix="/api/v1", router=messaging_router)
app.include_router(prefix="/api/v1", router=meetings_router)
logger.info("Application startup completed")