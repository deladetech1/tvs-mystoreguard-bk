from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date
from src.entities.reports.reports_base import (
    DateRangeFilter,
    LocationFilter,
    ProductFilter,
    CustomerFilter,
    SupplierFilter,
    ReportFormatType,
    ReportGroupByType,
)


# =====================================================
# BASE REPORT REQUEST DTOs
# =====================================================

class BaseReportRequestWriteDto(BaseModel):
    """Base report request DTO"""
    from_date: Optional[date] = Field(None, description="Start date for the report")
    to_date: Optional[date] = Field(None, description="End date for the report")
    loc_id: Optional[str] = Field(None, description="Location ID filter")
    location_ids: Optional[List[str]] = Field(None, description="List of location IDs")
    format: ReportFormatType = Field('SUMMARY', description="Report format: SUMMARY, DETAILED, or GRAPHICAL")
    page: int = Field(1, ge=1, description="Page number for pagination")
    size: int = Field(100, ge=1, le=1000, description="Page size for pagination")


# =====================================================
# SALES REPORTS REQUEST DTOs
# =====================================================

class SummaryItemsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for summary items report"""
    group_by: Optional[ReportGroupByType] = Field('PRODUCT', description="Group by field")


class DetailedSalesReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for detailed sales report"""
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")
    status: Optional[str] = Field(None, description="Filter by sale status")
    payment_method: Optional[str] = Field(None, description="Filter by payment method")
    min_amount: Optional[float] = Field(None, description="Minimum sale amount")
    max_amount: Optional[float] = Field(None, description="Maximum sale amount")


class CloseoutReportRequestWriteDto(BaseModel):
    """Request DTO for closeout report"""
    closeout_date: date = Field(..., description="Closeout date")
    loc_id: Optional[str] = Field(None, description="Location ID")


class ProfitLossReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for profit and loss report"""
    include_details: bool = Field(False, description="Include detailed line items")
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period")


class BalanceSheetReportRequestWriteDto(BaseModel):
    """Request DTO for balance sheet report"""
    as_of_date: date = Field(..., description="Balance sheet date")
    loc_id: Optional[str] = Field(None, description="Location ID")


class ProductGrossProfitReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for product gross profit report"""
    product_id: Optional[str] = Field(None, description="Filter by specific product ID")
    product_ids: Optional[List[str]] = Field(None, description="Filter by list of product IDs")
    min_gross_profit: Optional[float] = Field(None, description="Minimum gross profit filter")
    min_gross_profit_margin: Optional[float] = Field(None, description="Minimum gross profit margin percentage")
    group_by_location: bool = Field(False, description="Group results by location")


class ProductNetProfitReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for product net profit report (gross profit - expenses)"""
    product_id: Optional[str] = Field(None, description="Filter by specific product ID")
    product_ids: Optional[List[str]] = Field(None, description="Filter by list of product IDs")
    expense_allocation_method: str = Field('revenue', description="Expense allocation method: 'revenue' (proportional to revenue) or 'equal' (equal split)")
    min_net_profit: Optional[float] = Field(None, description="Minimum net profit filter")
    min_net_profit_margin: Optional[float] = Field(None, description="Minimum net profit margin percentage")
    group_by_location: bool = Field(False, description="Group results by location")


class LocationPerformanceReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for location performance comparison report (graphical)"""
    metric: str = Field('revenue', description="Metric to compare: 'revenue', 'gross_profit', 'net_profit', 'sales_count'")
    include_expenses: bool = Field(True, description="Include expenses in net profit calculation")


# =====================================================
# CUSTOMER REPORTS REQUEST DTOs
# =====================================================

class CustomersSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for customers summary report"""
    group_by: Optional[ReportGroupByType] = Field('CUSTOMER', description="Group by field")
    min_purchases: Optional[int] = Field(None, description="Minimum number of purchases")
    min_revenue: Optional[float] = Field(None, description="Minimum revenue")


class CustomersDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for customers detailed report"""
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")
    customer_ids: Optional[List[str]] = Field(None, description="List of customer IDs")
    include_inactive: bool = Field(False, description="Include inactive customers")


class CustomersSeriesReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for customers series report"""
    group_by: ReportGroupByType = Field('MONTH', description="Group by period")


class NewCustomersReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for new customers report"""
    include_first_purchase: bool = Field(True, description="Include first purchase details")


class DetailedNewCustomersReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for detailed new customers report"""
    pass


# =====================================================
# EXPENSE REPORTS REQUEST DTOs
# =====================================================

class ExpensesSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for expenses summary report"""
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period")
    source: Optional[str] = Field(None, description="Filter by expense source (ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE)")
    used_by: Optional[str] = Field(None, description="Filter by user ID")
    min_amount: Optional[float] = Field(None, description="Minimum expense amount")
    max_amount: Optional[float] = Field(None, description="Maximum expense amount")


class ExpensesDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for expenses detailed report"""
    source: Optional[str] = Field(None, description="Filter by expense source")
    used_by: Optional[str] = Field(None, description="Filter by user ID")
    currency_id: Optional[str] = Field(None, description="Filter by currency")


class ExpensesBySourceReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for expenses by source report"""
    sources: Optional[List[str]] = Field(None, description="Filter by specific sources (ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE)")


class ExpensesByUserReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for expenses by user report"""
    source: Optional[str] = Field(None, description="Filter by expense source")
    min_amount: Optional[float] = Field(None, description="Minimum expense amount per user")
    max_amount: Optional[float] = Field(None, description="Maximum expense amount per user")


class ExpensesGraphicalReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for expenses graphical report"""
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period (DAY, WEEK, MONTH, YEAR)")
    source: Optional[str] = Field(None, description="Filter by expense source")
    sources: Optional[List[str]] = Field(None, description="Filter by multiple sources")


class ExpensesByLocationReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for expenses by location report"""
    source: Optional[str] = Field(None, description="Filter by expense source")
    location_ids: Optional[List[str]] = Field(None, description="Filter by specific location IDs")


class ExpensesByPeriodReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for expenses by period/time series report"""
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period (DAY, WEEK, MONTH, YEAR)")
    source: Optional[str] = Field(None, description="Filter by expense source")
    sources: Optional[List[str]] = Field(None, description="Filter by multiple sources")


# =====================================================
# INVENTORY REPORTS REQUEST DTOs
# =====================================================

class LowInventoryReportRequestWriteDto(BaseModel):
    """Request DTO for low inventory report"""
    loc_id: Optional[str] = Field(None, description="Location ID")
    location_ids: Optional[List[str]] = Field(None, description="List of location IDs")
    threshold_percentage: Optional[float] = Field(20, ge=0, le=100, description="Low stock threshold percentage")
    include_zero_stock: bool = Field(True, description="Include out of stock items")


class InventorySummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for inventory summary report"""
    include_values: bool = Field(True, description="Include inventory values")
    group_by_location: bool = Field(False, description="Group results by location")


class InventorySummaryPastDateReportRequestWriteDto(BaseModel):
    """Request DTO for inventory summary at past date report"""
    as_of_date: date = Field(..., description="Historical date")
    loc_id: Optional[str] = Field(None, description="Location ID")


class InventoryDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for inventory detailed report"""
    product_id: Optional[str] = Field(None, description="Filter by product ID")
    product_ids: Optional[List[str]] = Field(None, description="List of product IDs")
    include_batches: bool = Field(True, description="Include batch details")
    min_quantity: Optional[float] = Field(None, description="Minimum quantity")
    max_quantity: Optional[float] = Field(None, description="Maximum quantity")


class InventoryCountReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for inventory count report"""
    count_date: Optional[date] = Field(None, description="Count date")
    include_variance: bool = Field(True, description="Include variance calculations")


class InventoryCountDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for detailed inventory count report"""
    count_date: Optional[date] = Field(None, description="Count date")
    product_id: Optional[str] = Field(None, description="Filter by product ID")
    product_ids: Optional[List[str]] = Field(None, description="List of product IDs")


class ExpiringItemsReportRequestWriteDto(BaseModel):
    """Request DTO for expiring items report"""
    days_ahead: int = Field(30, ge=1, description="Days ahead to check for expiration")
    loc_id: Optional[str] = Field(None, description="Location ID")
    include_expired: bool = Field(False, description="Include already expired items")


class InventoryAgingReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for inventory aging report"""
    aging_periods: Optional[List[str]] = Field(None, description="Custom aging periods (e.g., ['0-30', '31-60', '61-90'])")
    include_zero_quantity: bool = Field(False, description="Include items with zero quantity")


# =====================================================
# INVOICE REPORTS REQUEST DTOs
# =====================================================

class InvoicesSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for invoices summary report"""
    status: Optional[str] = Field(None, description="Filter by invoice status")
    include_overdue: bool = Field(True, description="Include overdue invoices separately")
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period")


class InvoicesDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for invoices detailed report"""
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")
    status: Optional[str] = Field(None, description="Filter by invoice status")
    include_overdue: bool = Field(True, description="Include overdue calculation")
    min_amount: Optional[float] = Field(None, description="Minimum invoice amount")
    max_amount: Optional[float] = Field(None, description="Maximum invoice amount")


class InvoiceAgingReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for invoice aging report"""
    aging_periods: Optional[List[str]] = Field(None, description="Custom aging periods")
    include_paid: bool = Field(False, description="Include paid invoices")
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")


# =====================================================
# PAYMENT REPORTS REQUEST DTOs
# =====================================================

class PaymentsSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for payments summary report"""
    payment_method: Optional[str] = Field(None, description="Filter by payment method")
    status: Optional[str] = Field(None, description="Filter by payment status")
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period")
    include_refunds: bool = Field(True, description="Include refunds in summary")


class PaymentsDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for payments detailed report"""
    payment_method: Optional[str] = Field(None, description="Filter by payment method")
    status: Optional[str] = Field(None, description="Filter by payment status")
    sale_id: Optional[str] = Field(None, description="Filter by sale ID")
    invoice_id: Optional[str] = Field(None, description="Filter by invoice ID")


class PaymentsGraphicalReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for payments graphical report"""
    group_by: ReportGroupByType = Field('MONTH', description="Group by period")
    group_by_method: bool = Field(True, description="Group by payment method")


# =====================================================
# PURCHASE/RECEIVING REPORTS REQUEST DTOs
# =====================================================

class ReceivingSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving summary report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    status: Optional[str] = Field(None, description="Filter by receiving status")
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period")


class ReceivingDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving detailed report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    purchase_order_id: Optional[str] = Field(None, description="Filter by PO ID")
    status: Optional[str] = Field(None, description="Filter by status")


class ReceivingSummaryCategoriesReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving summary by categories report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")


class SuspendedReceivingsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suspended receivings report"""
    pass


class DeletedReceivingsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for deleted receivings report"""
    pass


class ReceivingSummaryTaxesReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving summary taxes report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    tax_id: Optional[str] = Field(None, description="Filter by tax ID")


class ReceivingGraphicalTaxesReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving graphical taxes report"""
    group_by: ReportGroupByType = Field('MONTH', description="Group by period")
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")


class CheapestSupplierReportRequestWriteDto(BaseModel):
    """Request DTO for cheapest supplier report"""
    product_id: Optional[str] = Field(None, description="Filter by product ID")
    product_ids: Optional[List[str]] = Field(None, description="List of product IDs")
    min_purchases: Optional[int] = Field(1, ge=1, description="Minimum number of purchases")


class ReceivingItemsGraphicalReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving items graphical report"""
    group_by: ReportGroupByType = Field('PRODUCT', description="Group by field")
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")


class ReceivingItemsSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving items summary report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    product_id: Optional[str] = Field(None, description="Filter by product ID")
    group_by: Optional[ReportGroupByType] = Field('PRODUCT', description="Group by field")


class ReceivingPaymentsGraphicalReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving payments graphical report"""
    group_by: ReportGroupByType = Field('MONTH', description="Group by period")
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")


class ReceivingPaymentsSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving payments summary report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    payment_method: Optional[str] = Field(None, description="Filter by payment method")


class ReceivingPaymentsDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for receiving payments detailed report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    payment_method: Optional[str] = Field(None, description="Filter by payment method")


# =====================================================
# SUPPLIER REPORTS REQUEST DTOs
# =====================================================

class SuppliersGraphicalReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers graphical report"""
    group_by: ReportGroupByType = Field('SUPPLIER', description="Group by field")
    metric: str = Field('revenue', description="Metric to display: revenue, quantity, orders")


class SuppliersSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers summary report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    min_purchases: Optional[int] = Field(None, description="Minimum number of purchases")
    min_amount: Optional[float] = Field(None, description="Minimum purchase amount")


class SuppliersDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers detailed report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    include_inactive: bool = Field(False, description="Include inactive suppliers")


class SuppliersSummaryItemsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers summary items report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    product_id: Optional[str] = Field(None, description="Filter by product ID")


class SuppliersGraphicalReceivingsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers graphical receivings report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    group_by: ReportGroupByType = Field('MONTH', description="Group by period")


class SuppliersSummaryReceivingsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers summary receivings report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")


class SuppliersDetailedReceivingsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers detailed receivings report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")


class SuppliersTaxByPaymentsReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for suppliers tax by payments received report"""
    supplier_id: Optional[str] = Field(None, description="Filter by supplier ID")
    payment_method: Optional[str] = Field(None, description="Filter by payment method")


# =====================================================
# APPOINTMENT REPORTS REQUEST DTOs
# =====================================================

class AppointmentsSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for appointments summary report"""
    status: Optional[str] = Field(None, description="Filter by appointment status")
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period")


class AppointmentsDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for appointments detailed report"""
    status: Optional[str] = Field(None, description="Filter by appointment status")
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")


# =====================================================
# PRODUCT METADATA REPORTS REQUEST DTOs
# =====================================================

class ProductMetadataGraphicalReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for product metadata graphical report"""
    metadata_type: Optional[str] = Field(None, description="Filter by metadata type")
    group_by: ReportGroupByType = Field('PRODUCT', description="Group by field")


class ProductMetadataSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for product metadata summary report"""
    metadata_type: Optional[str] = Field(None, description="Filter by metadata type")


# =====================================================
# PRICING RULE REPORTS REQUEST DTOs
# =====================================================

class PricingRulesSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for pricing rules summary report"""
    rule_id: Optional[str] = Field(None, description="Filter by rule ID")
    is_active: Optional[bool] = Field(None, description="Filter by active status")


class PricingRulesDetailedReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for pricing rules detailed report"""
    rule_id: Optional[str] = Field(None, description="Filter by rule ID")
    include_inactive: bool = Field(False, description="Include inactive rules")


# =====================================================
# TAX REPORTS REQUEST DTOs
# =====================================================

class TaxSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for tax summary report"""
    tax_id: Optional[str] = Field(None, description="Filter by tax ID")
    group_by: Optional[ReportGroupByType] = Field('MONTH', description="Group by period")


class TaxRuleSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for tax rule summary report"""
    rule_id: Optional[str] = Field(None, description="Filter by rule ID")
    is_active: Optional[bool] = Field(None, description="Filter by active status")


# =====================================================
# PRODUCT PRICE REPORTS REQUEST DTOs
# =====================================================

class ProductPricesSummaryReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for product prices summary report"""
    product_id: Optional[str] = Field(None, description="Filter by product ID")
    include_price_history: bool = Field(False, description="Include price change history")


class ProductPricesGraphicalReportRequestWriteDto(BaseReportRequestWriteDto):
    """Request DTO for product prices graphical report"""
    product_id: Optional[str] = Field(None, description="Filter by product ID")
    price_type: str = Field('selling_price', description="Price type: cost_price or selling_price")

