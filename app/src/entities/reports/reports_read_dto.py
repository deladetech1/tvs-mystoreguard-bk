"""
Reports Read DTOs

This module contains all Read Data Transfer Objects (DTOs) used for Reports API responses.
These DTOs define the structure of data returned by all report endpoints.

Frontend developers can use these DTOs to:
- Understand the exact structure of API responses
- Type-check their frontend code
- Generate TypeScript/JavaScript types automatically

Available Report DTOs by Category:

=== COMMON BASE TYPES ===
- SummaryItemReadBase: Generic summary item with label, value, count
- DetailedItemReadBase: Generic detailed item with id, name, date, amount
- GraphDataPointReadBase: Generic graph data point with label, value, category, date

=== SALES REPORTS ===
- SalesSummaryItemReadBase: Sales summary statistics
- DetailedSalesItemReadBase: Individual sale details
- CloseoutReadBase: Daily closeout report data

=== PROFIT AND LOSS REPORTS ===
- ProfitLossSummaryReadBase: P&L summary with revenue, COGS, expenses, profit
- ProfitLossDetailedItemReadBase: Detailed P&L line items
- BalanceSheetReadBase: Balance sheet with assets, liabilities, equity

=== CUSTOMER REPORTS ===
- CustomerSummaryItemReadBase: Customer summary with purchases, revenue, lifetime value
- CustomerDetailedItemReadBase: Detailed customer information and statistics
- CustomerSeriesItemReadBase: Customer growth over time series
- NewCustomerReadBase: New customer registration and purchase data

=== EXPENSE REPORTS ===
- ExpenseSummaryItemReadBase: Expense summary by source and category
- ExpenseDetailedItemReadBase: Individual expense line items
- ExpenseBySourceItemReadBase: Expenses grouped by source (ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE)
- ExpenseByUserItemReadBase: Expenses grouped by user with source breakdown
- ExpenseGraphItemReadBase: Expense graph/chart data points for visualization
- ExpenseByLocationItemReadBase: Expenses grouped by location with source breakdown
- ExpenseByPeriodItemReadBase: Expenses grouped by time period (day/week/month/year)

=== INVENTORY REPORTS ===
- LowInventoryItemReadBase: Products with low stock levels
- InventorySummaryItemReadBase: Inventory summary statistics
- InventoryDetailedItemReadBase: Detailed inventory by product
- InventoryCountItemReadBase: Inventory count/variance data
- ExpiringItemReadBase: Products expiring soon
- InventoryAgingItemReadBase: Inventory aging analysis

=== INVOICE REPORTS ===
- InvoiceSummaryItemReadBase: Invoice summary statistics
- InvoiceDetailedItemReadBase: Individual invoice details
- InvoiceAgingItemReadBase: Invoice aging analysis

=== PAYMENT REPORTS ===
- PaymentSummaryItemReadBase: Payment summary by method and status
- PaymentDetailedItemReadBase: Individual payment details
- PaymentGraphItemReadBase: Payment graph/chart data points

=== RECEIVING/PURCHASE REPORTS ===
- ReceivingSummaryItemReadBase: Receiving/purchase summary statistics
- ReceivingDetailedItemReadBase: Individual receiving/purchase order details
- ReceivingCategoryItemReadBase: Receiving summary by category
- ReceivingTaxItemReadBase: Receiving tax summary
- CheapestSupplierItemReadBase: Cheapest supplier analysis per product

=== SUPPLIER REPORTS ===
- SupplierSummaryItemReadBase: Supplier summary statistics
- SupplierDetailedItemReadBase: Detailed supplier information and statistics

=== PRODUCT METADATA REPORTS ===
- ProductMetadataSummaryItemReadBase: Product metadata summary
- ProductMetadataGraphItemReadBase: Product metadata graph data

=== PRICING RULE REPORTS ===
- PricingRuleSummaryItemReadBase: Pricing rule usage summary
- PricingRuleDetailedItemReadBase: Detailed pricing rule information

=== TAX REPORTS ===
- TaxSummaryItemReadBase: Tax summary by tax type
- TaxRuleSummaryItemReadBase: Tax rule usage summary
- TaxByPaymentItemReadBase: Tax summary by payment method

=== APPOINTMENT REPORTS ===
- AppointmentSummaryItemReadBase: Appointment summary statistics
- AppointmentDetailedItemReadBase: Individual appointment details

=== PRODUCT PRICE REPORTS ===
- ProductPriceSummaryItemReadBase: Product price summary with margins
- ProductPriceGraphItemReadBase: Product price history graph data

=== REPORT RESPONSE DTOs ===
- ReportResponseReadBase: Base response wrapper for all reports
- SummaryReportResponseReadBase: Response wrapper for summary reports
- DetailedReportResponseReadBase: Response wrapper for detailed reports
- GraphicalReportResponseReadBase: Response wrapper for graphical reports

Each report endpoint returns a Respons[T] where T is one of the Response DTOs above.
The Response DTOs contain lists of the corresponding Item DTOs.
"""
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal


# =====================================================
# COMMON REPORT DATA POINTS
# =====================================================

class SummaryItemReadBase(BaseModel):
    """Base model for summary report items"""
    label: str
    value: Decimal
    count: Optional[int] = None
    percentage: Optional[Decimal] = None


class DetailedItemReadBase(BaseModel):
    """Base model for detailed report items"""
    id: str
    name: str
    date: date
    amount: Decimal
    quantity: Optional[Decimal] = None
    additional_fields: Optional[dict] = Field(default_factory=dict)


class GraphDataPointReadBase(BaseModel):
    """Base model for graph data points"""
    label: str
    value: Decimal
    category: Optional[str] = None
    date: Optional[date] = None


# =====================================================
# SALES REPORTS
# =====================================================

class SalesSummaryItemReadBase(BaseModel):
    """Sales summary item"""
    total_sales: int
    total_revenue: Decimal
    total_items_sold: Decimal
    average_transaction_value: Decimal
    total_discounts: Decimal
    total_tax: Decimal


class DetailedSalesItemReadBase(BaseModel):
    """Detailed sales report item"""
    sale_id: str
    sale_number: str
    sale_date: date
    customer_name: Optional[str]
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    payment_methods: List[str]
    items_count: int
    status: str
    created_by: Optional[str]


class CloseoutReadBase(BaseModel):
    """Closeout report data"""
    date: date
    opening_balance: Decimal
    total_sales: Decimal
    total_receipts: Decimal
    total_expenses: Decimal
    total_refunds: Decimal
    closing_balance: Decimal
    cash_sales: Decimal
    card_sales: Decimal
    other_payments: Decimal
    transaction_count: int


# =====================================================
# PROFIT AND LOSS REPORTS
# =====================================================

class ProfitLossSummaryReadBase(BaseModel):
    """Profit and Loss summary"""
    period_start: date
    period_end: date
    total_revenue: Decimal
    cost_of_goods_sold: Decimal
    gross_profit: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    gross_profit_margin: Decimal
    net_profit_margin: Decimal


class BalanceSheetReadBase(BaseModel):
    """Balance Sheet report"""
    as_of_date: date
    assets: Decimal
    liabilities: Decimal
    equity: Decimal
    current_assets: Decimal
    inventory_value: Decimal
    accounts_receivable: Decimal
    accounts_payable: Decimal


class ProfitLossDetailedItemReadBase(BaseModel):
    """Detailed P&L item"""
    date: date
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    expenses: Decimal
    net_profit: Decimal
    location_name: Optional[str] = None


class ProductGrossProfitItemReadBase(BaseModel):
    """Product gross profit report item"""
    product_id: str
    product_name: str
    total_quantity_sold: Decimal
    total_revenue: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    gross_profit_margin: Decimal  # Percentage
    location_id: Optional[str] = None
    location_name: Optional[str] = None


class ProductNetProfitItemReadBase(BaseModel):
    """Product net profit report item (after expenses)"""
    product_id: str
    product_name: str
    total_quantity_sold: Decimal
    total_revenue: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    allocated_expenses: Decimal  # Expenses allocated to this product
    net_profit: Decimal
    gross_profit_margin: Decimal
    net_profit_margin: Decimal
    location_id: Optional[str] = None
    location_name: Optional[str] = None


class LocationPerformanceItemReadBase(BaseModel):
    """Location performance comparison item (for graphical representation)"""
    location_id: str
    location_name: str
    total_sales: int
    total_revenue: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    gross_profit_margin: Decimal
    net_profit_margin: Decimal
    average_transaction_value: Decimal
    total_items_sold: Decimal


# =====================================================
# CUSTOMER REPORTS
# =====================================================

class CustomerSummaryItemReadBase(BaseModel):
    """Customer summary item"""
    customer_id: str
    customer_name: str
    total_purchases: int
    total_revenue: Decimal
    average_order_value: Decimal
    last_purchase_date: Optional[date]
    lifetime_value: Decimal


class CustomerDetailedItemReadBase(BaseModel):
    """Detailed customer report item"""
    customer_id: str
    customer_name: str
    email: Optional[str]
    contact: Optional[str]
    address: Optional[str]
    total_orders: int
    total_spent: Decimal
    first_purchase_date: Optional[date]
    last_purchase_date: Optional[date]
    average_order_value: Decimal


class CustomerSeriesItemReadBase(BaseModel):
    """Customer series report item"""
    period: str
    new_customers: int
    returning_customers: int
    total_customers: int
    customer_growth_rate: Decimal


class NewCustomerReadBase(BaseModel):
    """New customer report item"""
    customer_id: str
    customer_name: str
    email: Optional[str]
    contact: Optional[str]
    registration_date: date
    first_purchase_date: Optional[date]
    first_purchase_amount: Optional[Decimal]
    total_spent: Decimal


# =====================================================
# EXPENSE REPORTS
# =====================================================

class ExpenseSummaryItemReadBase(BaseModel):
    """Expense summary item"""
    total_expenses: Decimal
    expense_count: int
    average_expense: Decimal
    expenses_by_source: dict  # ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE
    expenses_by_category: dict


class ExpenseDetailedItemReadBase(BaseModel):
    """Detailed expense report item"""
    expense_id: str
    amount: Decimal
    currency_id: str
    source: str
    used_for: Optional[str]
    used_by: Optional[str]
    description: Optional[str]
    expense_date: date
    created_by: Optional[str]


class ExpenseBySourceItemReadBase(BaseModel):
    """Expense by source report item"""
    source: str  # ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE
    total_amount: Decimal
    expense_count: int
    average_amount: Decimal
    percentage: Decimal  # Percentage of total expenses


class ExpenseByUserItemReadBase(BaseModel):
    """Expense by user report item"""
    user_id: str
    user_name: Optional[str]
    total_amount: Decimal
    expense_count: int
    average_amount: Decimal
    expenses_by_source: dict  # Breakdown by source


class ExpenseGraphItemReadBase(BaseModel):
    """Expense graph/chart data point"""
    label: str  # Date or period label
    value: Decimal  # Total amount for this period
    category: Optional[str]  # Source type if grouped
    date: Optional[date]  # Date for sorting


class ExpenseByLocationItemReadBase(BaseModel):
    """Expense by location report item"""
    location_id: str
    location_name: str
    total_amount: Decimal
    expense_count: int
    average_amount: Decimal
    expenses_by_source: dict  # Breakdown by source


class ExpenseByPeriodItemReadBase(BaseModel):
    """Expense by period/time series report item"""
    period: str  # Period label (e.g., "2024-01", "Week 1", "2024-01-15")
    period_start: date
    period_end: date
    total_amount: Decimal
    expense_count: int
    expenses_by_source: dict  # Breakdown by source


# =====================================================
# INVENTORY REPORTS
# =====================================================

class LowInventoryItemReadBase(BaseModel):
    """Low inventory item"""
    product_id: str
    product_name: str
    sku: Optional[str]
    current_qty: Decimal
    minimum_threshold: Optional[Decimal]
    location_name: str
    reorder_suggestion: Decimal


class InventorySummaryItemReadBase(BaseModel):
    """Inventory summary item"""
    total_products: int
    total_quantity: Decimal
    total_value: Decimal
    products_low_stock: int
    products_out_of_stock: int
    average_product_value: Decimal


class InventoryDetailedItemReadBase(BaseModel):
    """Detailed inventory item"""
    product_id: str
    product_name: str
    sku: Optional[str]
    location_name: str
    current_qty: Decimal
    unit_cost: Decimal
    total_value: Decimal
    batches_count: int
    last_movement_date: Optional[date]


class InventoryCountItemReadBase(BaseModel):
    """Inventory count report item"""
    product_id: str
    product_name: str
    sku: Optional[str]
    expected_qty: Decimal
    counted_qty: Decimal
    variance: Decimal
    variance_value: Decimal
    location_name: str


class ExpiringItemReadBase(BaseModel):
    """Expiring item report"""
    product_id: str
    product_name: str
    batch_id: str
    expiry_date: date
    days_until_expiry: int
    quantity: Decimal
    location_name: str


class InventoryAgingItemReadBase(BaseModel):
    """Inventory aging report item"""
    product_id: str
    product_name: str
    batch_id: str
    purchase_date: date
    days_in_stock: int
    quantity: Decimal
    unit_cost: Decimal
    total_value: Decimal
    location_name: str


# =====================================================
# INVOICE REPORTS
# =====================================================

class InvoiceSummaryItemReadBase(BaseModel):
    """Invoice summary item"""
    total_invoices: int
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    overdue_amount: Decimal
    average_invoice_value: Decimal
    invoices_by_status: dict


class InvoiceDetailedItemReadBase(BaseModel):
    """Detailed invoice item"""
    invoice_id: str
    invoice_number: str
    invoice_date: date
    due_date: date
    customer_name: str
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    status: str
    days_overdue: Optional[int]
    items_count: int


class InvoiceAgingItemReadBase(BaseModel):
    """Invoice aging item"""
    customer_id: str
    customer_name: str
    invoice_id: str
    invoice_number: str
    invoice_date: date
    due_date: date
    days_overdue: int
    amount: Decimal
    status: str


# =====================================================
# PAYMENT REPORTS
# =====================================================

class PaymentSummaryItemReadBase(BaseModel):
    """Payment summary item"""
    total_payments: int
    total_amount: Decimal
    payments_by_method: dict
    payments_by_status: dict
    average_payment_amount: Decimal
    refunds_count: int
    refunds_amount: Decimal


class PaymentDetailedItemReadBase(BaseModel):
    """Detailed payment item"""
    payment_id: str
    sale_id: Optional[str]
    invoice_id: Optional[str]
    payment_date: date
    payment_method: str
    amount: Decimal
    status: str
    reference_number: Optional[str]
    customer_name: Optional[str]


class PaymentGraphItemReadBase(BaseModel):
    """Payment graph data item"""
    period: str
    payment_method: str
    amount: Decimal
    count: int


# =====================================================
# PURCHASE/RECEIVING REPORTS
# =====================================================

class ReceivingSummaryItemReadBase(BaseModel):
    """Receiving summary item"""
    total_receivings: int
    total_amount: Decimal
    total_items_received: Decimal
    average_receiving_value: Decimal
    receivings_by_status: dict
    receivings_by_supplier: dict


class ReceivingDetailedItemReadBase(BaseModel):
    """Detailed receiving item"""
    purchase_order_id: str
    po_number: Optional[str]
    receiving_date: date
    supplier_name: Optional[str]
    total_amount: Decimal
    items_count: int
    status: str
    batches_created: int


class ReceivingCategoryItemReadBase(BaseModel):
    """Receiving by category item"""
    category_name: str
    total_receivings: int
    total_amount: Decimal
    total_quantity: Decimal


class ReceivingTaxItemReadBase(BaseModel):
    """Receiving tax summary item"""
    tax_name: str
    tax_rate: Decimal
    total_taxable_amount: Decimal
    total_tax_amount: Decimal
    transaction_count: int


class CheapestSupplierItemReadBase(BaseModel):
    """Cheapest supplier for product"""
    product_id: str
    product_name: str
    supplier_id: str
    supplier_name: str
    average_cost: Decimal
    purchase_count: int
    total_quantity: Decimal


# =====================================================
# SUPPLIER REPORTS
# =====================================================

class SupplierSummaryItemReadBase(BaseModel):
    """Supplier summary item"""
    supplier_id: str
    supplier_name: str
    total_purchases: int
    total_amount: Decimal
    total_items_purchased: Decimal
    average_order_value: Decimal
    last_purchase_date: Optional[date]
    on_time_delivery_rate: Optional[Decimal]


class SupplierDetailedItemReadBase(BaseModel):
    """Detailed supplier item"""
    supplier_id: str
    supplier_name: str
    contact: Optional[str]
    email: Optional[str]
    address: Optional[str]
    total_orders: int
    total_spent: Decimal
    total_items: Decimal
    first_order_date: Optional[date]
    last_order_date: Optional[date]
    average_order_value: Decimal


# =====================================================
# PRODUCT METADATA REPORTS
# =====================================================

class ProductMetadataSummaryItemReadBase(BaseModel):
    """Product metadata summary item"""
    metadata_name: str
    metadata_type: str
    products_count: int
    total_value: Decimal


class ProductMetadataGraphItemReadBase(BaseModel):
    """Product metadata graph item"""
    metadata_value: str
    product_count: int
    total_revenue: Decimal


# =====================================================
# PRICING RULE REPORTS
# =====================================================

class PricingRuleSummaryItemReadBase(BaseModel):
    """Pricing rule summary item"""
    rule_id: str
    rule_name: str
    times_applied: int
    total_discount_amount: Decimal
    total_items_affected: Decimal
    average_discount_percentage: Decimal


class PricingRuleDetailedItemReadBase(BaseModel):
    """Detailed pricing rule item"""
    rule_id: str
    rule_name: str
    rule_type: str
    is_active: bool
    times_applied: int
    total_discount: Decimal
    affected_products_count: int
    date_created: date
    last_applied_date: Optional[date]


# =====================================================
# TAX REPORTS
# =====================================================

class TaxSummaryItemReadBase(BaseModel):
    """Tax summary item"""
    tax_id: str
    tax_name: str
    tax_rate: Decimal
    total_taxable_amount: Decimal
    total_tax_collected: Decimal
    transaction_count: int


class TaxRuleSummaryItemReadBase(BaseModel):
    """Tax rule summary item"""
    rule_id: str
    rule_name: str
    times_applied: int
    total_tax_collected: Decimal
    affected_transactions: int


class TaxByPaymentItemReadBase(BaseModel):
    """Tax by payment received item"""
    payment_method: str
    total_taxable_amount: Decimal
    total_tax_collected: Decimal
    transaction_count: int


# =====================================================
# APPOINTMENT REPORTS
# =====================================================

class AppointmentSummaryItemReadBase(BaseModel):
    """Appointment summary item
    
    Contains aggregated statistics about appointments within the specified period.
    All rates are percentages (0-100).
    """
    total_appointments: int = Field(..., description="Total number of appointments in the period")
    completed_appointments: int = Field(..., description="Number of appointments with status 'COMPLETED'")
    cancelled_appointments: int = Field(..., description="Number of appointments with status 'CANCELLED'")
    pending_appointments: int = Field(..., description="Number of appointments with status 'PENDING', 'CONFIRMED', 'IN_PROGRESS', or 'RESCHEDULED'")
    completion_rate: Decimal = Field(..., description="Percentage of appointments that were completed (completed_appointments / total_appointments * 100). Range: 0.00 to 100.00")
    no_show_rate: Decimal = Field(..., description="Percentage of appointments that were no-shows (no_show_appointments / total_appointments * 100). Range: 0.00 to 100.00")


class AppointmentDetailedItemReadBase(BaseModel):
    """Detailed appointment item
    
    Contains individual appointment details for detailed reports.
    """
    appointment_id: str = Field(..., description="Unique identifier for the appointment (format: 'apt-...')")
    customer_name: Optional[str] = Field(None, description="Full name of the customer associated with the appointment. Null for walk-in appointments")
    start_datetime: datetime = Field(..., description="Start date and time of the appointment (ISO 8601 format)")
    end_datetime: datetime = Field(..., description="End date and time of the appointment (ISO 8601 format)")
    status: str = Field(..., description="Current status of the appointment. Possible values: 'PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'NO_SHOW', 'CANCELLED', 'RESCHEDULED'")
    service_type: Optional[str] = Field(None, description="Type of service for the appointment. Possible values: 'SALES', 'SERVICE', 'DELIVERY', 'INSTALLATION', 'CONSULTATION', 'OTHERS'")
    notes: Optional[str] = Field(None, description="Additional description or notes about the appointment")
    created_by: Optional[str] = Field(None, description="Full name of the user who created the appointment")


# =====================================================
# PRODUCT PRICE REPORTS
# =====================================================

class ProductPriceSummaryItemReadBase(BaseModel):
    """Product price summary item"""
    product_id: str
    product_name: str
    current_price: Decimal
    cost_price: Decimal
    margin_percentage: Decimal
    price_change_count: int
    last_price_change_date: Optional[date]


class ProductPriceGraphItemReadBase(BaseModel):
    """Product price graph item"""
    date: date
    product_id: str
    product_name: str
    price: Decimal
    price_type: str  # cost_price, selling_price


# =====================================================
# TYPE ALIASES FOR ALLOWED ITEM TYPES
# =====================================================

# Union type for all possible detailed report items
# Note: This is for documentation purposes. At runtime, Pydantic will validate
# against the actual item types used (e.g., DetailedSalesItemReadBase, CustomerDetailedItemReadBase, etc.)
DetailedReportItemType = Union[
    DetailedSalesItemReadBase,
    CustomerSummaryItemReadBase,
    CustomerDetailedItemReadBase,
    NewCustomerReadBase,
    ExpenseDetailedItemReadBase,
    LowInventoryItemReadBase,
    ExpiringItemReadBase,
    InventoryDetailedItemReadBase,
    InventoryCountItemReadBase,
    InvoiceDetailedItemReadBase,
    InvoiceAgingItemReadBase,
    PaymentDetailedItemReadBase,
    ReceivingDetailedItemReadBase,
    SupplierDetailedItemReadBase,
    AppointmentDetailedItemReadBase,
    ProfitLossDetailedItemReadBase,
    DetailedItemReadBase,  # Generic fallback
]

# Union type for all possible summary report items
SummaryReportItemType = Union[
    SummaryItemReadBase,  # Generic summary item
    ExpenseSummaryItemReadBase,
    InventorySummaryItemReadBase,
    InvoiceSummaryItemReadBase,
    PaymentSummaryItemReadBase,
    ReceivingSummaryItemReadBase,
    SupplierSummaryItemReadBase,
    ProductMetadataSummaryItemReadBase,
    PricingRuleSummaryItemReadBase,
    TaxSummaryItemReadBase,
    TaxRuleSummaryItemReadBase,
    AppointmentSummaryItemReadBase,
    ProductPriceSummaryItemReadBase,
    SalesSummaryItemReadBase,
]

# Union type for all possible graph data points
GraphDataPointType = Union[
    GraphDataPointReadBase,  # Generic graph data point
    PaymentGraphItemReadBase,
    ProductMetadataGraphItemReadBase,
    ProductPriceGraphItemReadBase,
    CustomerSeriesItemReadBase,
    ReceivingTaxItemReadBase,
    ReceivingCategoryItemReadBase,
]


# =====================================================
# REPORT RESPONSE DTOs
# =====================================================

class ReportResponseReadBase(BaseModel):
    """Base report response
    
    All report endpoints return a Respons[ReportResponseReadBase] wrapper.
    This base class contains common fields for all report responses.
    """
    report_type: str = Field(..., description="Type of report (e.g., 'summary_items', 'customers_summary', 'expenses_detailed')")
    report_format: str = Field(..., description="Report format: SUMMARY, DETAILED, or GRAPHICAL")
    generated_at: datetime = Field(..., description="Timestamp when the report was generated")
    period_start: Optional[date] = Field(None, description="Start date of the report period")
    period_end: Optional[date] = Field(None, description="End date of the report period")
    filters_applied: Optional[dict] = Field(default_factory=dict, description="Filters applied to generate this report")


class SummaryReportResponseReadBase(ReportResponseReadBase):
    """Summary report response
    
    Used for summary-type reports that aggregate data.
    
    The summary_items list contains objects whose structure depends on the report_type.
    Check the report_type field to determine which specific item type is used.
    
    Item structures by report_type:
    - "summary_items" → SummaryItemReadBase: label, value, count, percentage
    - "expenses_summary" → ExpenseSummaryItemReadBase: category, total_amount, count, percentage
    - "inventory_summary" → InventorySummaryItemReadBase: location_name, total_items, total_value, low_stock_count
    - "invoices_summary" → InvoiceSummaryItemReadBase: status, total_amount, count, percentage
    - "payments_summary" → PaymentSummaryItemReadBase: payment_method, total_amount, count, percentage
    - "receivings_summary" → ReceivingSummaryItemReadBase: supplier_name, total_amount, items_count, batches_created
    - "suppliers_summary" → SupplierSummaryItemReadBase: supplier_name, total_orders, total_spent, average_order_value
    - "product_metadata_summary" → ProductMetadataSummaryItemReadBase: metadata_type, product_count, usage_count
    - "pricing_rules_summary" → PricingRuleSummaryItemReadBase: rule_name, usage_count, total_discount_applied
    - "tax_summary" → TaxSummaryItemReadBase: tax_name, total_amount, count
    - "tax_rules_summary" → TaxRuleSummaryItemReadBase: rule_name, usage_count, total_exemption_applied
    - "appointments_summary" → AppointmentSummaryItemReadBase: total_appointments, completed_appointments, cancelled_appointments, pending_appointments, completion_rate, no_show_rate
    - "product_prices_summary" → ProductPriceSummaryItemReadBase: product_id, product_name, cost_price, selling_price, margin, margin_percentage
    - "sales_summary" → SalesSummaryItemReadBase: total_sales, total_revenue, total_items_sold, average_transaction_value, total_discounts, total_tax
    """
    summary_items: List[SummaryReportItemType] = Field(
        default_factory=list, 
        description="List of summary items. The structure depends on report_type - see class docstring for field mappings."
    )
    total_items: int = Field(
        0, 
        description="Total number of summary items in the list. For appointments_summary, this is typically 1"
    )
    totals: Optional[dict] = Field(
        default_factory=dict, 
        description="Aggregated totals and statistics. May contain additional computed values"
    )


class DetailedReportResponseReadBase(ReportResponseReadBase):
    """Detailed report response
    
    Used for detailed reports that list individual records.
    
    The items list contains objects whose structure depends on the report_type.
    Check the report_type field to determine which specific item type is used.
    
    Item structures by report_type:
    - "detailed_sales" → DetailedSalesItemReadBase: sale_id, sale_number, sale_date, customer_name, total_amount, paid_amount, balance_amount, payment_methods, items_count, status, created_by
    - "customers_summary" → CustomerSummaryItemReadBase: customer_id, customer_name, total_purchases, total_revenue, average_order_value, last_purchase_date, lifetime_value
    - "customers_detailed" → CustomerDetailedItemReadBase: customer_id, customer_name, email, contact, address, total_orders, total_spent, first_purchase_date, last_purchase_date, average_order_value
    - "customers_new" → NewCustomerReadBase: customer_id, customer_name, email, contact, registration_date, first_purchase_date, first_purchase_amount, total_spent
    - "expenses_detailed" → ExpenseDetailedItemReadBase: expense_id, amount, currency_id, source, used_for, used_by, description, expense_date, created_by
    - "inventory_low" → LowInventoryItemReadBase: product_id, product_name, sku, current_qty, minimum_threshold, location_name, reorder_suggestion
    - "inventory_expiring" → ExpiringItemReadBase: product_id, product_name, batch_id, expiry_date, days_until_expiry, quantity, location_name
    - "inventory_detailed" → InventoryDetailedItemReadBase: product_id, product_name, sku, location_name, current_qty, unit_cost, total_value, batches_count, last_movement_date
    - "inventory_count_summary" → InventoryCountItemReadBase: product_id, product_name, sku, expected_qty, counted_qty, variance, variance_value, location_name
    - "inventory_count_detailed" → InventoryCountItemReadBase: product_id, product_name, sku, expected_qty, counted_qty, variance, variance_value, location_name
    - "invoices_detailed" → InvoiceDetailedItemReadBase: invoice_id, invoice_number, invoice_date, due_date, customer_name, total_amount, paid_amount, balance_amount, status, days_overdue, items_count
    - "invoices_aging" → InvoiceAgingItemReadBase: customer_id, customer_name, invoice_id, invoice_number, invoice_date, due_date, days_overdue, amount, status
    - "payments_detailed" → PaymentDetailedItemReadBase: payment_id, sale_id, invoice_id, payment_date, payment_method, amount, status, reference_number, customer_name
    - "receivings_detailed" → ReceivingDetailedItemReadBase: purchase_order_id, po_number, receiving_date, supplier_name, total_amount, items_count, status, batches_created
    - "suppliers_detailed" → SupplierDetailedItemReadBase: supplier_id, supplier_name, contact, email, address, total_orders, total_spent, total_items, first_order_date, last_order_date, average_order_value
    - "appointments_detailed" → AppointmentDetailedItemReadBase: appointment_id, customer_name, start_datetime, end_datetime, status, service_type, notes, created_by
    - "profit_loss_detailed" → ProfitLossDetailedItemReadBase: date, revenue, cogs, gross_profit, expenses, net_profit, location_name
    - "product_gross_profit" → ProductGrossProfitItemReadBase: product_id, product_name, total_quantity_sold, total_revenue, total_cost, gross_profit, gross_profit_margin, location_id, location_name
    - "product_net_profit" → ProductNetProfitItemReadBase: product_id, product_name, total_quantity_sold, total_revenue, total_cost, gross_profit, allocated_expenses, net_profit, gross_profit_margin, net_profit_margin, location_id, location_name
    """
    items: List[DetailedReportItemType] = Field(
        default_factory=list, 
        description="List of detailed items. The structure depends on report_type - see class docstring for field mappings."
    )
    total_items: int = Field(
        0, 
        description="Total number of items matching the filters (before pagination). For appointments_detailed, this is the total count of appointments"
    )
    total_amount: Optional[Decimal] = Field(
        None, 
        description="Total amount across all items (if applicable). Not used for appointments_detailed reports"
    )
    pagination: Optional[dict] = Field(
        default_factory=dict, 
        description="Pagination metadata: {page, size, total, total_pages, has_next, has_previous}. For appointments_detailed, includes all pagination info"
    )


class GraphicalReportResponseReadBase(ReportResponseReadBase):
    """Graphical report response
    
    Used for reports that return data for charts/graphs.
    
    The graph_data list contains objects whose structure depends on the report_type.
    Check the report_type field to determine which specific item type is used.
    
    Item structures by report_type:
    - "product_metadata_graphical" → ProductMetadataGraphItemReadBase: label, value, category, date, metadata_type
    - "product_prices_graphical" → ProductPriceGraphItemReadBase: date, product_id, product_name, price, price_type
    - "payments_graphical" → PaymentGraphItemReadBase: date, payment_method, amount, count
    - "customers_series" → CustomerSeriesItemReadBase: date, new_customers, total_customers, customers_with_purchases
    - "receivings_graphical_taxes" → ReceivingTaxItemReadBase: tax_name, total_amount, percentage
    - "receivings_summary_categories" → ReceivingCategoryItemReadBase: category_name, total_amount, items_count
    - "location_performance" → GraphDataPointReadBase: label (location_name), value (metric value), category (location_id), date (null)
    - Generic graphs → GraphDataPointReadBase: label, value, category, date
    """
    graph_data: List[GraphDataPointType] = Field(
        default_factory=list, 
        description="List of graph data points. The structure depends on report_type - see class docstring for field mappings."
    )
    chart_type: str = Field("bar", description="Recommended chart type: bar, line, pie, area, etc.")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


# =====================================================
# SPECIFIC REPORT RESPONSE DTOs
# =====================================================

class ProductGrossProfitReportResponseReadBase(ReportResponseReadBase):
    """Product gross profit report response"""
    items: List[ProductGrossProfitItemReadBase] = Field(
        default_factory=list,
        description="List of products with their gross profit calculations"
    )
    total_items: int = Field(0, description="Total number of products in the report")
    pagination: Optional[dict] = Field(
        default_factory=dict,
        description="Pagination metadata: {page, size, total_pages, has_next, has_previous}"
    )


class ProductNetProfitReportResponseReadBase(ReportResponseReadBase):
    """Product net profit report response (gross profit - allocated expenses)"""
    items: List[ProductNetProfitItemReadBase] = Field(
        default_factory=list,
        description="List of products with their net profit calculations"
    )
    total_items: int = Field(0, description="Total number of products in the report")
    pagination: Optional[dict] = Field(
        default_factory=dict,
        description="Pagination metadata: {page, size, total_pages, has_next, has_previous}"
    )


class LocationPerformanceReportResponseReadBase(ReportResponseReadBase):
    """Location performance comparison report response (graphical)"""
    graph_data: List[GraphDataPointReadBase] = Field(
        default_factory=list,
        description="Graph data points for location comparison. Each point has: label (location_name), value (metric value), category (location_id)"
    )
    chart_type: str = Field("bar", description="Recommended chart type: bar")
    metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Additional metadata including full performance_data array with LocationPerformanceItemReadBase items"
    )


# =====================================================
# SUMMARY REPORT RESPONSE DTOs
# =====================================================

class SummaryItemsReportResponseReadBase(ReportResponseReadBase):
    """Summary items report response"""
    summary_items: List[SummaryItemReadBase] = Field(
        default_factory=list,
        description="List of summary items with label, value, count, and percentage"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class AppointmentsSummaryReportResponseReadBase(ReportResponseReadBase):
    """Appointments summary report response"""
    summary_items: List[AppointmentSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of appointment summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ProductMetadataSummaryReportResponseReadBase(ReportResponseReadBase):
    """Product metadata summary report response"""
    summary_items: List[ProductMetadataSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of product metadata summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ExpensesSummaryReportResponseReadBase(ReportResponseReadBase):
    """Expenses summary report response"""
    summary_items: List[ExpenseSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of expense summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class InventorySummaryReportResponseReadBase(ReportResponseReadBase):
    """Inventory summary report response"""
    summary_items: List[InventorySummaryItemReadBase] = Field(
        default_factory=list,
        description="List of inventory summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class InvoicesSummaryReportResponseReadBase(ReportResponseReadBase):
    """Invoices summary report response"""
    summary_items: List[InvoiceSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of invoice summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class PaymentsSummaryReportResponseReadBase(ReportResponseReadBase):
    """Payments summary report response"""
    summary_items: List[PaymentSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of payment summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class PricingRulesSummaryReportResponseReadBase(ReportResponseReadBase):
    """Pricing rules summary report response"""
    summary_items: List[PricingRuleSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of pricing rule summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ReceivingsSummaryReportResponseReadBase(ReportResponseReadBase):
    """Receivings summary report response"""
    summary_items: List[ReceivingSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of receiving summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ReceivingsItemsSummaryReportResponseReadBase(ReportResponseReadBase):
    """Receivings items summary report response"""
    summary_items: List[SummaryItemReadBase] = Field(
        default_factory=list,
        description="List of receiving items summary"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ReceivingsPaymentsSummaryReportResponseReadBase(ReportResponseReadBase):
    """Receivings payments summary report response"""
    summary_items: List[PaymentSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of receiving payment summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class SuppliersSummaryReportResponseReadBase(ReportResponseReadBase):
    """Suppliers summary report response"""
    summary_items: List[SupplierSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of supplier summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class SuppliersSummaryItemsReportResponseReadBase(ReportResponseReadBase):
    """Suppliers summary items report response"""
    summary_items: List[SummaryItemReadBase] = Field(
        default_factory=list,
        description="List of supplier items summary"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class SuppliersReceivingsSummaryReportResponseReadBase(ReportResponseReadBase):
    """Suppliers receivings summary report response"""
    summary_items: List[ReceivingSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of supplier receiving summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ProductPricesSummaryReportResponseReadBase(ReportResponseReadBase):
    """Product prices summary report response"""
    summary_items: List[ProductPriceSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of product price summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class TaxSummaryReportResponseReadBase(ReportResponseReadBase):
    """Tax summary report response"""
    summary_items: List[TaxSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of tax summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class TaxRulesSummaryReportResponseReadBase(ReportResponseReadBase):
    """Tax rules summary report response"""
    summary_items: List[TaxRuleSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of tax rule summary items"
    )
    total_items: int = Field(0, description="Total number of summary items")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


# =====================================================
# DETAILED REPORT RESPONSE DTOs
# =====================================================

class DetailedSalesReportResponseReadBase(ReportResponseReadBase):
    """Detailed sales report response"""
    items: List[DetailedSalesItemReadBase] = Field(
        default_factory=list,
        description="List of detailed sales items"
    )
    total_items: int = Field(0, description="Total number of sales")
    total_amount: Optional[Decimal] = Field(None, description="Total amount across all sales")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class CustomersSummaryReportResponseReadBase(ReportResponseReadBase):
    """Customers summary report response"""
    items: List[CustomerSummaryItemReadBase] = Field(
        default_factory=list,
        description="List of customer summary items"
    )
    total_items: int = Field(0, description="Total number of customers")
    total_amount: Optional[Decimal] = Field(None, description="Total revenue across all customers")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class CustomersDetailedReportResponseReadBase(ReportResponseReadBase):
    """Customers detailed report response"""
    items: List[CustomerDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed customer items"
    )
    total_items: int = Field(0, description="Total number of customers")
    total_amount: Optional[Decimal] = Field(None, description="Total amount spent by all customers")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class NewCustomersReportResponseReadBase(ReportResponseReadBase):
    """New customers report response"""
    items: List[NewCustomerReadBase] = Field(
        default_factory=list,
        description="List of new customer items"
    )
    total_items: int = Field(0, description="Total number of new customers")
    total_amount: Optional[Decimal] = Field(None, description="Total amount spent by new customers")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ExpensesDetailedReportResponseReadBase(ReportResponseReadBase):
    """Expenses detailed report response"""
    items: List[ExpenseDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed expense items"
    )
    total_items: int = Field(0, description="Total number of expenses")
    total_amount: Optional[Decimal] = Field(None, description="Total amount of expenses")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ExpensesBySourceReportResponseReadBase(ReportResponseReadBase):
    """Expenses by source report response"""
    items: List[ExpenseBySourceItemReadBase] = Field(
        default_factory=list,
        description="List of expenses grouped by source"
    )
    total_items: int = Field(0, description="Total number of source groups")
    total_amount: Optional[Decimal] = Field(None, description="Total amount across all sources")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ExpensesByUserReportResponseReadBase(ReportResponseReadBase):
    """Expenses by user report response"""
    items: List[ExpenseByUserItemReadBase] = Field(
        default_factory=list,
        description="List of expenses grouped by user"
    )
    total_items: int = Field(0, description="Total number of users")
    total_amount: Optional[Decimal] = Field(None, description="Total amount across all users")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ExpensesGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Expenses graphical report response"""
    items: List[ExpenseGraphItemReadBase] = Field(
        default_factory=list,
        description="List of expense graph data points"
    )
    total_items: int = Field(0, description="Total number of data points")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class ExpensesByLocationReportResponseReadBase(ReportResponseReadBase):
    """Expenses by location report response"""
    items: List[ExpenseByLocationItemReadBase] = Field(
        default_factory=list,
        description="List of expenses grouped by location"
    )
    total_items: int = Field(0, description="Total number of locations")
    total_amount: Optional[Decimal] = Field(None, description="Total amount across all locations")
    totals: Optional[dict] = Field(default_factory=dict, description="Aggregated totals and statistics")


class ExpensesByPeriodReportResponseReadBase(ReportResponseReadBase):
    """Expenses by period/time series report response"""
    items: List[ExpenseByPeriodItemReadBase] = Field(
        default_factory=list,
        description="List of expenses grouped by time period"
    )
    total_items: int = Field(0, description="Total number of periods")
    total_amount: Optional[Decimal] = Field(None, description="Total amount across all periods")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata including period type")


class LowInventoryReportResponseReadBase(ReportResponseReadBase):
    """Low inventory report response"""
    items: List[LowInventoryItemReadBase] = Field(
        default_factory=list,
        description="List of low inventory items"
    )
    total_items: int = Field(0, description="Total number of low inventory items")
    total_amount: Optional[Decimal] = Field(None, description="Total value of low inventory items")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class InventoryDetailedReportResponseReadBase(ReportResponseReadBase):
    """Inventory detailed report response"""
    items: List[InventoryDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed inventory items"
    )
    total_items: int = Field(0, description="Total number of inventory items")
    total_amount: Optional[Decimal] = Field(None, description="Total inventory value")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class InventoryCountSummaryReportResponseReadBase(ReportResponseReadBase):
    """Inventory count summary report response"""
    items: List[InventoryCountItemReadBase] = Field(
        default_factory=list,
        description="List of inventory count items"
    )
    total_items: int = Field(0, description="Total number of counted items")
    total_amount: Optional[Decimal] = Field(None, description="Total variance value")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class InventoryCountDetailedReportResponseReadBase(ReportResponseReadBase):
    """Inventory count detailed report response"""
    items: List[InventoryCountItemReadBase] = Field(
        default_factory=list,
        description="List of detailed inventory count items"
    )
    total_items: int = Field(0, description="Total number of counted items")
    total_amount: Optional[Decimal] = Field(None, description="Total variance value")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ExpiringItemsReportResponseReadBase(ReportResponseReadBase):
    """Expiring items report response"""
    items: List[ExpiringItemReadBase] = Field(
        default_factory=list,
        description="List of expiring items"
    )
    total_items: int = Field(0, description="Total number of expiring items")
    total_amount: Optional[Decimal] = Field(None, description="Total value of expiring items")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class InvoicesDetailedReportResponseReadBase(ReportResponseReadBase):
    """Invoices detailed report response"""
    items: List[InvoiceDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed invoice items"
    )
    total_items: int = Field(0, description="Total number of invoices")
    total_amount: Optional[Decimal] = Field(None, description="Total invoice amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class InvoiceAgingReportResponseReadBase(ReportResponseReadBase):
    """Invoice aging report response"""
    items: List[InvoiceAgingItemReadBase] = Field(
        default_factory=list,
        description="List of invoice aging items"
    )
    total_items: int = Field(0, description="Total number of invoices")
    total_amount: Optional[Decimal] = Field(None, description="Total aging amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class PaymentsDetailedReportResponseReadBase(ReportResponseReadBase):
    """Payments detailed report response"""
    items: List[PaymentDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed payment items"
    )
    total_items: int = Field(0, description="Total number of payments")
    total_amount: Optional[Decimal] = Field(None, description="Total payment amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class PricingRulesDetailedReportResponseReadBase(ReportResponseReadBase):
    """Pricing rules detailed report response"""
    items: List[PricingRuleDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed pricing rule items"
    )
    total_items: int = Field(0, description="Total number of pricing rules")
    total_amount: Optional[Decimal] = Field(None, description="Total discount applied")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ReceivingsDetailedReportResponseReadBase(ReportResponseReadBase):
    """Receivings detailed report response"""
    items: List[ReceivingDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed receiving items"
    )
    total_items: int = Field(0, description="Total number of receivings")
    total_amount: Optional[Decimal] = Field(None, description="Total receiving amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ReceivingsSummaryCategoriesReportResponseReadBase(ReportResponseReadBase):
    """Receivings summary by categories report response"""
    items: List[ReceivingCategoryItemReadBase] = Field(
        default_factory=list,
        description="List of receiving category items"
    )
    total_items: int = Field(0, description="Total number of categories")
    total_amount: Optional[Decimal] = Field(None, description="Total amount by categories")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ReceivingsSuspendedReportResponseReadBase(ReportResponseReadBase):
    """Suspended receivings report response"""
    items: List[ReceivingDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of suspended receiving items"
    )
    total_items: int = Field(0, description="Total number of suspended receivings")
    total_amount: Optional[Decimal] = Field(None, description="Total suspended amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ReceivingsDeletedReportResponseReadBase(ReportResponseReadBase):
    """Deleted receivings report response"""
    items: List[ReceivingDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of deleted receiving items"
    )
    total_items: int = Field(0, description="Total number of deleted receivings")
    total_amount: Optional[Decimal] = Field(None, description="Total deleted amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ReceivingsSummaryTaxesReportResponseReadBase(ReportResponseReadBase):
    """Receivings summary taxes report response"""
    items: List[ReceivingTaxItemReadBase] = Field(
        default_factory=list,
        description="List of receiving tax items"
    )
    total_items: int = Field(0, description="Total number of tax items")
    total_amount: Optional[Decimal] = Field(None, description="Total tax amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class CheapestSupplierReportResponseReadBase(ReportResponseReadBase):
    """Cheapest supplier report response"""
    items: List[CheapestSupplierItemReadBase] = Field(
        default_factory=list,
        description="List of cheapest supplier items"
    )
    total_items: int = Field(0, description="Total number of suppliers")
    total_amount: Optional[Decimal] = Field(None, description="Total purchase amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class ReceivingsPaymentsDetailedReportResponseReadBase(ReportResponseReadBase):
    """Receivings payments detailed report response"""
    items: List[PaymentDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of receiving payment items"
    )
    total_items: int = Field(0, description="Total number of payments")
    total_amount: Optional[Decimal] = Field(None, description="Total payment amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class SuppliersDetailedReportResponseReadBase(ReportResponseReadBase):
    """Suppliers detailed report response"""
    items: List[SupplierDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed supplier items"
    )
    total_items: int = Field(0, description="Total number of suppliers")
    total_amount: Optional[Decimal] = Field(None, description="Total purchase amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class SuppliersReceivingsDetailedReportResponseReadBase(ReportResponseReadBase):
    """Suppliers receivings detailed report response"""
    items: List[ReceivingDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of supplier receiving items"
    )
    total_items: int = Field(0, description="Total number of receivings")
    total_amount: Optional[Decimal] = Field(None, description="Total receiving amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class SuppliersTaxByPaymentsReportResponseReadBase(ReportResponseReadBase):
    """Suppliers tax by payments report response"""
    items: List[TaxByPaymentItemReadBase] = Field(
        default_factory=list,
        description="List of tax by payment items"
    )
    total_items: int = Field(0, description="Total number of tax items")
    total_amount: Optional[Decimal] = Field(None, description="Total tax amount")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


class AppointmentsDetailedReportResponseReadBase(ReportResponseReadBase):
    """Appointments detailed report response"""
    items: List[AppointmentDetailedItemReadBase] = Field(
        default_factory=list,
        description="List of detailed appointment items"
    )
    total_items: int = Field(0, description="Total number of appointments")
    total_amount: Optional[Decimal] = Field(None, description="Not applicable for appointments")
    pagination: Optional[dict] = Field(default_factory=dict, description="Pagination metadata")


# =====================================================
# GRAPHICAL REPORT RESPONSE DTOs
# =====================================================

class ProductMetadataGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Product metadata graphical report response"""
    graph_data: List[ProductMetadataGraphItemReadBase] = Field(
        default_factory=list,
        description="List of product metadata graph data points"
    )
    chart_type: str = Field("bar", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class PaymentsGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Payments graphical report response"""
    graph_data: List[PaymentGraphItemReadBase] = Field(
        default_factory=list,
        description="List of payment graph data points"
    )
    chart_type: str = Field("line", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class ReceivingsGraphicalTaxesReportResponseReadBase(ReportResponseReadBase):
    """Receivings graphical taxes report response"""
    graph_data: List[ReceivingTaxItemReadBase] = Field(
        default_factory=list,
        description="List of receiving tax graph data points"
    )
    chart_type: str = Field("bar", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class ReceivingsItemsGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Receivings items graphical report response"""
    graph_data: List[GraphDataPointReadBase] = Field(
        default_factory=list,
        description="List of receiving items graph data points"
    )
    chart_type: str = Field("bar", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class ReceivingsPaymentsGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Receivings payments graphical report response"""
    graph_data: List[PaymentGraphItemReadBase] = Field(
        default_factory=list,
        description="List of receiving payment graph data points"
    )
    chart_type: str = Field("line", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class SuppliersGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Suppliers graphical report response"""
    graph_data: List[GraphDataPointReadBase] = Field(
        default_factory=list,
        description="List of supplier graph data points"
    )
    chart_type: str = Field("bar", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class SuppliersReceivingsGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Suppliers receivings graphical report response"""
    graph_data: List[GraphDataPointReadBase] = Field(
        default_factory=list,
        description="List of supplier receiving graph data points"
    )
    chart_type: str = Field("line", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


class ProductPricesGraphicalReportResponseReadBase(ReportResponseReadBase):
    """Product prices graphical report response"""
    graph_data: List[ProductPriceGraphItemReadBase] = Field(
        default_factory=list,
        description="List of product price graph data points"
    )
    chart_type: str = Field("line", description="Recommended chart type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for chart rendering")


# =====================================================
# QUICK REFERENCE: ALL READ DTOs BY ENDPOINT
# =====================================================
"""
QUICK REFERENCE GUIDE - All Report Read DTOs

Use this guide to find which DTOs are used by which endpoints:

1. POPULAR/SALES REPORTS
   GET /reports/popular/summary-items
   → SummaryReportResponseReadBase
   → Contains: List[SummaryItemReadBase]

   GET /reports/sales/detailed (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[DetailedSalesItemReadBase]

   GET /reports/sales/closeout (when implemented)
   → CloseoutReadBase

   GET /reports/sales/profit-loss (when implemented)
   → ProfitLossSummaryReadBase (summary) or DetailedReportResponseReadBase (detailed)

   GET /reports/sales/balance-sheet (when implemented)
   → BalanceSheetReadBase

2. APPOINTMENT REPORTS
   GET /reports/appointments/summary
   → SummaryReportResponseReadBase
   → Contains: List[AppointmentSummaryItemReadBase] (when implemented)

   GET /reports/appointments/detailed
   → DetailedReportResponseReadBase
   → Contains: List[AppointmentDetailedItemReadBase] (when implemented)

3. PRODUCT METADATA REPORTS
   GET /reports/product-metadata/summary
   → SummaryReportResponseReadBase
   → Contains: List[ProductMetadataSummaryItemReadBase] (when implemented)

   GET /reports/product-metadata/graphical
   → GraphicalReportResponseReadBase
   → Contains: List[ProductMetadataGraphItemReadBase] (when implemented)

4. CUSTOMER REPORTS
   GET /reports/customers/summary
   → DetailedReportResponseReadBase
   → Contains: List[CustomerSummaryItemReadBase]

   GET /reports/customers/detailed
   → DetailedReportResponseReadBase
   → Contains: List[CustomerDetailedItemReadBase]

   GET /reports/customers/new
   → DetailedReportResponseReadBase
   → Contains: List[NewCustomerReadBase]

5. EXPENSE REPORTS
   GET /reports/expenses/summary
   → SummaryReportResponseReadBase
   → Contains: List[ExpenseSummaryItemReadBase]

   GET /reports/expenses/detailed
   → DetailedReportResponseReadBase
   → Contains: List[ExpenseDetailedItemReadBase]

   GET /reports/expenses/by-source
   → ExpensesBySourceReportResponseReadBase
   → Contains: List[ExpenseBySourceItemReadBase]

   GET /reports/expenses/by-user
   → ExpensesByUserReportResponseReadBase
   → Contains: List[ExpenseByUserItemReadBase]

   GET /reports/expenses/graphical
   → ExpensesGraphicalReportResponseReadBase
   → Contains: List[ExpenseGraphItemReadBase]

   GET /reports/expenses/by-location
   → ExpensesByLocationReportResponseReadBase
   → Contains: List[ExpenseByLocationItemReadBase]

   GET /reports/expenses/by-period
   → ExpensesByPeriodReportResponseReadBase
   → Contains: List[ExpenseByPeriodItemReadBase]

6. INVENTORY REPORTS
   GET /reports/inventory/low
   → DetailedReportResponseReadBase
   → Contains: List[LowInventoryItemReadBase]

   GET /reports/inventory/summary
   → SummaryReportResponseReadBase
   → Contains: List[InventorySummaryItemReadBase]

   GET /reports/inventory/detailed (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[InventoryDetailedItemReadBase]

   GET /reports/inventory/count-summary (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[InventoryCountItemReadBase]

   GET /reports/inventory/count-detailed (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[InventoryCountItemReadBase]

   GET /reports/inventory/expiring
   → DetailedReportResponseReadBase
   → Contains: List[ExpiringItemReadBase]

7. INVOICE REPORTS
   GET /reports/invoices/summary (when implemented)
   → SummaryReportResponseReadBase
   → Contains: List[InvoiceSummaryItemReadBase]

   GET /reports/invoices/detailed (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[InvoiceDetailedItemReadBase]

   GET /reports/invoices/aging (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[InvoiceAgingItemReadBase]

8. PAYMENT REPORTS
   GET /reports/payments/summary (when implemented)
   → SummaryReportResponseReadBase
   → Contains: List[PaymentSummaryItemReadBase]

   GET /reports/payments/detailed (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[PaymentDetailedItemReadBase]

   GET /reports/payments/graphical (when implemented)
   → GraphicalReportResponseReadBase
   → Contains: List[PaymentGraphItemReadBase]

9. PRICING RULE REPORTS
   GET /reports/pricing-rules/summary (when implemented)
   → SummaryReportResponseReadBase
   → Contains: List[PricingRuleSummaryItemReadBase]

   GET /reports/pricing-rules/detailed (when implemented)
   → DetailedReportResponseReadBase
   → Contains: List[PricingRuleDetailedItemReadBase]

10. RECEIVING/PURCHASE REPORTS
    GET /reports/receivings/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[ReceivingSummaryItemReadBase]

    GET /reports/receivings/detailed (when implemented)
    → DetailedReportResponseReadBase
    → Contains: List[ReceivingDetailedItemReadBase]

    GET /reports/receivings/summary-categories (when implemented)
    → DetailedReportResponseReadBase
    → Contains: List[ReceivingCategoryItemReadBase]

    GET /reports/receivings/summary-taxes (when implemented)
    → GraphicalReportResponseReadBase or DetailedReportResponseReadBase
    → Contains: List[ReceivingTaxItemReadBase]

    GET /reports/receivings/graphical-taxes (when implemented)
    → GraphicalReportResponseReadBase
    → Contains: List[ReceivingTaxItemReadBase]

    GET /reports/receivings/cheapest-supplier (when implemented)
    → DetailedReportResponseReadBase
    → Contains: List[CheapestSupplierItemReadBase]

    GET /reports/receivings/items/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[SummaryItemReadBase]

    GET /reports/receivings/items/graphical (when implemented)
    → GraphicalReportResponseReadBase
    → Contains: List[GraphDataPointReadBase]

    GET /reports/receivings/payments/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[PaymentSummaryItemReadBase]

    GET /reports/receivings/payments/graphical (when implemented)
    → GraphicalReportResponseReadBase
    → Contains: List[PaymentGraphItemReadBase]

    GET /reports/receivings/payments/detailed (when implemented)
    → DetailedReportResponseReadBase
    → Contains: List[PaymentDetailedItemReadBase]

11. SUPPLIER REPORTS
    GET /reports/suppliers/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[SupplierSummaryItemReadBase]

    GET /reports/suppliers/detailed (when implemented)
    → DetailedReportResponseReadBase
    → Contains: List[SupplierDetailedItemReadBase]

    GET /reports/suppliers/summary-items (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[SummaryItemReadBase]

    GET /reports/suppliers/receivings/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[ReceivingSummaryItemReadBase]

    GET /reports/suppliers/receivings/graphical (when implemented)
    → GraphicalReportResponseReadBase
    → Contains: List[GraphDataPointReadBase]

    GET /reports/suppliers/receivings/detailed (when implemented)
    → DetailedReportResponseReadBase
    → Contains: List[ReceivingDetailedItemReadBase]

    GET /reports/suppliers/tax-by-payments (when implemented)
    → DetailedReportResponseReadBase
    → Contains: List[TaxByPaymentItemReadBase]

    GET /reports/suppliers/graphical (when implemented)
    → GraphicalReportResponseReadBase
    → Contains: List[GraphDataPointReadBase]

12. OTHER REPORTS
    GET /reports/product-prices/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[ProductPriceSummaryItemReadBase]

    GET /reports/product-prices/graphical (when implemented)
    → GraphicalReportResponseReadBase
    → Contains: List[ProductPriceGraphItemReadBase]

    GET /reports/tax/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[TaxSummaryItemReadBase]

    GET /reports/tax-rules/summary (when implemented)
    → SummaryReportResponseReadBase
    → Contains: List[TaxRuleSummaryItemReadBase]

NOTE: All endpoints return Respons[T] where T is one of the Response DTOs above.
The Respons wrapper has: success (bool), detail (str), data (List[T]), error (Optional[str])

To use these DTOs in your frontend:
1. Import from this module: from reports_read_dto import *
2. Generate TypeScript types using pydantic-to-typescript or similar tools
3. Use the OpenAPI/Swagger schema to see exact field definitions
4. Check the report_type field in responses to determine which item type is used
"""

