# Reports entity module

# Export all read DTOs for frontend use
from src.entities.reports.reports_read_dto import (
    # Common base types
    SummaryItemReadBase,
    DetailedItemReadBase,
    GraphDataPointReadBase,
    
    # Sales Reports
    SalesSummaryItemReadBase,
    DetailedSalesItemReadBase,
    CloseoutReadBase,
    ProductGrossProfitItemReadBase,
    ProductNetProfitItemReadBase,
    LocationPerformanceItemReadBase,
    # Specific Report Responses - Summary
    SummaryItemsReportResponseReadBase,
    AppointmentsSummaryReportResponseReadBase,
    ProductMetadataSummaryReportResponseReadBase,
    ExpensesSummaryReportResponseReadBase,
    InventorySummaryReportResponseReadBase,
    InvoicesSummaryReportResponseReadBase,
    PaymentsSummaryReportResponseReadBase,
    PricingRulesSummaryReportResponseReadBase,
    ReceivingsSummaryReportResponseReadBase,
    ReceivingsItemsSummaryReportResponseReadBase,
    ReceivingsPaymentsSummaryReportResponseReadBase,
    SuppliersSummaryReportResponseReadBase,
    SuppliersSummaryItemsReportResponseReadBase,
    SuppliersReceivingsSummaryReportResponseReadBase,
    AffiliatesSummaryReportResponseReadBase,
    ProductPricesSummaryReportResponseReadBase,
    TaxSummaryReportResponseReadBase,
    TaxRulesSummaryReportResponseReadBase,
    # Specific Report Responses - Detailed
    DetailedSalesReportResponseReadBase,
    CustomersSummaryReportResponseReadBase,
    CustomersDetailedReportResponseReadBase,
    NewCustomersReportResponseReadBase,
    ExpensesDetailedReportResponseReadBase,
    ExpensesBySourceReportResponseReadBase,
    ExpensesByUserReportResponseReadBase,
    ExpensesGraphicalReportResponseReadBase,
    ExpensesByLocationReportResponseReadBase,
    ExpensesByPeriodReportResponseReadBase,
    LowInventoryReportResponseReadBase,
    InventoryDetailedReportResponseReadBase,
    InventoryCountSummaryReportResponseReadBase,
    InventoryCountDetailedReportResponseReadBase,
    ExpiringItemsReportResponseReadBase,
    InvoicesDetailedReportResponseReadBase,
    InvoiceAgingReportResponseReadBase,
    PaymentsDetailedReportResponseReadBase,
    PricingRulesDetailedReportResponseReadBase,
    ReceivingsDetailedReportResponseReadBase,
    ReceivingsSummaryCategoriesReportResponseReadBase,
    ReceivingsSuspendedReportResponseReadBase,
    ReceivingsDeletedReportResponseReadBase,
    ReceivingsSummaryTaxesReportResponseReadBase,
    CheapestSupplierReportResponseReadBase,
    ReceivingsPaymentsDetailedReportResponseReadBase,
    SuppliersDetailedReportResponseReadBase,
    SuppliersReceivingsDetailedReportResponseReadBase,
    SuppliersTaxByPaymentsReportResponseReadBase,
    AppointmentsDetailedReportResponseReadBase,
    ProductGrossProfitReportResponseReadBase,
    ProductNetProfitReportResponseReadBase,
    # Specific Report Responses - Graphical
    ProductMetadataGraphicalReportResponseReadBase,
    PaymentsGraphicalReportResponseReadBase,
    ReceivingsGraphicalTaxesReportResponseReadBase,
    ReceivingsItemsGraphicalReportResponseReadBase,
    ReceivingsPaymentsGraphicalReportResponseReadBase,
    SuppliersGraphicalReportResponseReadBase,
    SuppliersReceivingsGraphicalReportResponseReadBase,
    ProductPricesGraphicalReportResponseReadBase,
    LocationPerformanceReportResponseReadBase,
    
    # Profit and Loss Reports
    ProfitLossSummaryReadBase,
    ProfitLossDetailedItemReadBase,
    BalanceSheetReadBase,
    
    # Customer Reports
    CustomerSummaryItemReadBase,
    CustomerDetailedItemReadBase,
    CustomerSeriesItemReadBase,
    NewCustomerReadBase,
    
    # Expense Reports
    ExpenseSummaryItemReadBase,
    ExpenseDetailedItemReadBase,
    ExpenseBySourceItemReadBase,
    ExpenseByUserItemReadBase,
    ExpenseGraphItemReadBase,
    ExpenseByLocationItemReadBase,
    ExpenseByPeriodItemReadBase,
    
    # Inventory Reports
    LowInventoryItemReadBase,
    InventorySummaryItemReadBase,
    InventoryDetailedItemReadBase,
    InventoryCountItemReadBase,
    ExpiringItemReadBase,
    InventoryAgingItemReadBase,
    
    # Invoice Reports
    InvoiceSummaryItemReadBase,
    InvoiceDetailedItemReadBase,
    InvoiceAgingItemReadBase,
    
    # Payment Reports
    PaymentSummaryItemReadBase,
    PaymentDetailedItemReadBase,
    PaymentGraphItemReadBase,
    
    # Receiving/Purchase Reports
    ReceivingSummaryItemReadBase,
    ReceivingDetailedItemReadBase,
    ReceivingCategoryItemReadBase,
    ReceivingTaxItemReadBase,
    CheapestSupplierItemReadBase,
    
    # Supplier Reports
    SupplierSummaryItemReadBase,
    SupplierDetailedItemReadBase,
    
    # Affiliate Reports
    AffiliateSummaryItemReadBase,
    
    # Product Metadata Reports
    ProductMetadataSummaryItemReadBase,
    ProductMetadataGraphItemReadBase,
    
    # Pricing Rule Reports
    PricingRuleSummaryItemReadBase,
    PricingRuleDetailedItemReadBase,
    
    # Tax Reports
    TaxSummaryItemReadBase,
    TaxRuleSummaryItemReadBase,
    TaxByPaymentItemReadBase,
    
    # Appointment Reports
    AppointmentSummaryItemReadBase,
    AppointmentDetailedItemReadBase,
    
    # Product Price Reports
    ProductPriceSummaryItemReadBase,
    ProductPriceGraphItemReadBase,
    
    # Report Response DTOs
    ReportResponseReadBase,
    SummaryReportResponseReadBase,
    DetailedReportResponseReadBase,
    GraphicalReportResponseReadBase,
)

__all__ = [
    # Common base types
    "SummaryItemReadBase",
    "DetailedItemReadBase",
    "GraphDataPointReadBase",
    
    # Sales Reports
    "SalesSummaryItemReadBase",
    "DetailedSalesItemReadBase",
    "CloseoutReadBase",
    "ProductGrossProfitItemReadBase",
    "ProductNetProfitItemReadBase",
    "LocationPerformanceItemReadBase",
    # Specific Report Responses - Summary
    "SummaryItemsReportResponseReadBase",
    "AppointmentsSummaryReportResponseReadBase",
    "ProductMetadataSummaryReportResponseReadBase",
    "ExpensesSummaryReportResponseReadBase",
    "InventorySummaryReportResponseReadBase",
    "InvoicesSummaryReportResponseReadBase",
    "PaymentsSummaryReportResponseReadBase",
    "PricingRulesSummaryReportResponseReadBase",
    "ReceivingsSummaryReportResponseReadBase",
    "ReceivingsItemsSummaryReportResponseReadBase",
    "ReceivingsPaymentsSummaryReportResponseReadBase",
    "SuppliersSummaryReportResponseReadBase",
    "SuppliersSummaryItemsReportResponseReadBase",
    "SuppliersReceivingsSummaryReportResponseReadBase",
    "AffiliatesSummaryReportResponseReadBase",
    "ProductPricesSummaryReportResponseReadBase",
    "TaxSummaryReportResponseReadBase",
    "TaxRulesSummaryReportResponseReadBase",
    # Specific Report Responses - Detailed
    "DetailedSalesReportResponseReadBase",
    "CustomersSummaryReportResponseReadBase",
    "CustomersDetailedReportResponseReadBase",
    "NewCustomersReportResponseReadBase",
    "ExpensesDetailedReportResponseReadBase",
    "ExpensesBySourceReportResponseReadBase",
    "ExpensesByUserReportResponseReadBase",
    "ExpensesGraphicalReportResponseReadBase",
    "ExpensesByLocationReportResponseReadBase",
    "ExpensesByPeriodReportResponseReadBase",
    "LowInventoryReportResponseReadBase",
    "InventoryDetailedReportResponseReadBase",
    "InventoryCountSummaryReportResponseReadBase",
    "InventoryCountDetailedReportResponseReadBase",
    "ExpiringItemsReportResponseReadBase",
    "InvoicesDetailedReportResponseReadBase",
    "InvoiceAgingReportResponseReadBase",
    "PaymentsDetailedReportResponseReadBase",
    "PricingRulesDetailedReportResponseReadBase",
    "ReceivingsDetailedReportResponseReadBase",
    "ReceivingsSummaryCategoriesReportResponseReadBase",
    "ReceivingsSuspendedReportResponseReadBase",
    "ReceivingsDeletedReportResponseReadBase",
    "ReceivingsSummaryTaxesReportResponseReadBase",
    "CheapestSupplierReportResponseReadBase",
    "ReceivingsPaymentsDetailedReportResponseReadBase",
    "SuppliersDetailedReportResponseReadBase",
    "SuppliersReceivingsDetailedReportResponseReadBase",
    "SuppliersTaxByPaymentsReportResponseReadBase",
    "AppointmentsDetailedReportResponseReadBase",
    "ProductGrossProfitReportResponseReadBase",
    "ProductNetProfitReportResponseReadBase",
    # Specific Report Responses - Graphical
    "ProductMetadataGraphicalReportResponseReadBase",
    "PaymentsGraphicalReportResponseReadBase",
    "ReceivingsGraphicalTaxesReportResponseReadBase",
    "ReceivingsItemsGraphicalReportResponseReadBase",
    "ReceivingsPaymentsGraphicalReportResponseReadBase",
    "SuppliersGraphicalReportResponseReadBase",
    "SuppliersReceivingsGraphicalReportResponseReadBase",
    "ProductPricesGraphicalReportResponseReadBase",
    "LocationPerformanceReportResponseReadBase",
    
    # Profit and Loss Reports
    "ProfitLossSummaryReadBase",
    "ProfitLossDetailedItemReadBase",
    "BalanceSheetReadBase",
    
    # Customer Reports
    "CustomerSummaryItemReadBase",
    "CustomerDetailedItemReadBase",
    "CustomerSeriesItemReadBase",
    "NewCustomerReadBase",
    
    # Expense Reports
    "ExpenseSummaryItemReadBase",
    "ExpenseDetailedItemReadBase",
    "ExpenseBySourceItemReadBase",
    "ExpenseByUserItemReadBase",
    "ExpenseGraphItemReadBase",
    "ExpenseByLocationItemReadBase",
    "ExpenseByPeriodItemReadBase",
    
    # Inventory Reports
    "LowInventoryItemReadBase",
    "InventorySummaryItemReadBase",
    "InventoryDetailedItemReadBase",
    "InventoryCountItemReadBase",
    "ExpiringItemReadBase",
    "InventoryAgingItemReadBase",
    
    # Invoice Reports
    "InvoiceSummaryItemReadBase",
    "InvoiceDetailedItemReadBase",
    "InvoiceAgingItemReadBase",
    
    # Payment Reports
    "PaymentSummaryItemReadBase",
    "PaymentDetailedItemReadBase",
    "PaymentGraphItemReadBase",
    
    # Receiving/Purchase Reports
    "ReceivingSummaryItemReadBase",
    "ReceivingDetailedItemReadBase",
    "ReceivingCategoryItemReadBase",
    "ReceivingTaxItemReadBase",
    "CheapestSupplierItemReadBase",
    
    # Supplier Reports
    "SupplierSummaryItemReadBase",
    "SupplierDetailedItemReadBase",
    
    # Affiliate Reports
    "AffiliateSummaryItemReadBase",
    
    # Product Metadata Reports
    "ProductMetadataSummaryItemReadBase",
    "ProductMetadataGraphItemReadBase",
    
    # Pricing Rule Reports
    "PricingRuleSummaryItemReadBase",
    "PricingRuleDetailedItemReadBase",
    
    # Tax Reports
    "TaxSummaryItemReadBase",
    "TaxRuleSummaryItemReadBase",
    "TaxByPaymentItemReadBase",
    
    # Appointment Reports
    "AppointmentSummaryItemReadBase",
    "AppointmentDetailedItemReadBase",
    
    # Product Price Reports
    "ProductPriceSummaryItemReadBase",
    "ProductPriceGraphItemReadBase",
    
    # Report Response DTOs
    "ReportResponseReadBase",
    "SummaryReportResponseReadBase",
    "DetailedReportResponseReadBase",
    "GraphicalReportResponseReadBase",
]

