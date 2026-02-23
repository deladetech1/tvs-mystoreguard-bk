"""
Reports Service
Comprehensive reporting functionality for MyStoreGuard
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from src.entities.reports.reports_read_dto import (
    # Sales Reports
    SalesSummaryItemReadBase,
    DetailedSalesItemReadBase,
    CloseoutReadBase,
    ProfitLossSummaryReadBase,
    ProfitLossDetailedItemReadBase,
    BalanceSheetReadBase,
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
    ProductPricesSummaryReportResponseReadBase,
    TaxSummaryReportResponseReadBase,
    TaxRulesSummaryReportResponseReadBase,
    AffiliatesSummaryReportResponseReadBase,
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
    # Receiving Reports
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
    # Response DTOs
    SummaryReportResponseReadBase,
    DetailedReportResponseReadBase,
    GraphicalReportResponseReadBase,
    SummaryItemReadBase,
    DetailedItemReadBase,
    GraphDataPointReadBase,
)
from src.entities.reports.reports_write_dto import *
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger

logger = get_logger("reports_service")


class ReportsService:
    """Service class for reports operations"""

    @staticmethod
    def _get_base_where_conditions(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: Optional[str] = None,
        location_ids: Optional[List[str]] = None,
        table_alias: Optional[str] = None,
    ) -> tuple:
        """Build base WHERE conditions and parameters
        
        Args:
            tenant_id: Tenant ID
            org_id: Organization ID
            bus_id: Business ID
            loc_id: Optional location ID
            location_ids: Optional list of location IDs
            table_alias: Optional table alias prefix (e.g., 's', 'si', 'c') for qualifying column names
        """
        prefix = f"{table_alias}." if table_alias else ""
        conditions = [
            f"{prefix}tenant_id = %s",
            f"{prefix}org_id = %s",
            f"{prefix}bus_id = %s"
        ]
        params = [tenant_id, org_id, bus_id]
        
        if loc_id:
            conditions.append(f"{prefix}loc_id = %s")
            params.append(loc_id)
        elif location_ids:
            placeholders = ','.join(['%s'] * len(location_ids))
            conditions.append(f"{prefix}loc_id IN ({placeholders})")
            params.extend(location_ids)
        
        return conditions, params

    @staticmethod
    def _add_date_filters(
        conditions: List[str],
        params: List[Any],
        from_date: Optional[date],
        to_date: Optional[date],
        date_field: str = "date"
    ) -> tuple:
        """Add date filters to WHERE conditions"""
        if from_date:
            conditions.append(f"{date_field} >= %s")
            params.append(from_date)
        if to_date:
            conditions.append(f"{date_field} <= %s")
            params.append(to_date)
        return conditions, params

    @staticmethod
    def _quantize_decimal(value: Any, places: int = 2) -> Decimal:
        """Quantize decimal to specified places"""
        if value is None:
            return Decimal('0')
        decimal_value = Decimal(str(value))
        quantizer = Decimal('0.1') ** places
        return decimal_value.quantize(quantizer, rounding=ROUND_HALF_UP)

    @staticmethod
    def _get_date_format_for_group_by(group_by: str) -> str:
        """Get SQL date format string for grouping"""
        formats = {
            'DAY': "TO_CHAR(e.cdatetime, 'YYYY-MM-DD')",
            'WEEK': "TO_CHAR(e.cdatetime, 'IYYY-IW')",
            'MONTH': "TO_CHAR(e.cdatetime, 'YYYY-MM')",
            'YEAR': "TO_CHAR(e.cdatetime, 'YYYY')",
        }
        return formats.get(group_by, formats['MONTH'])

    @staticmethod
    def _get_date_trunc_for_group_by(group_by: str) -> str:
        """Get SQL date truncation for grouping"""
        truncs = {
            'DAY': "DATE_TRUNC('day', e.cdatetime)",
            'WEEK': "DATE_TRUNC('week', e.cdatetime)",
            'MONTH': "DATE_TRUNC('month', e.cdatetime)",
            'YEAR': "DATE_TRUNC('year', e.cdatetime)",
        }
        return truncs.get(group_by, truncs['MONTH'])

    # =====================================================
    # 1. POPULAR / SALES REPORTS
    # =====================================================

    @staticmethod
    def get_summary_items_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SummaryItemsReportRequestWriteDto,
    ) -> Respons[SummaryItemsReportResponseReadBase]:
        """Get summary items report grouped by specified field"""
        logger.info("Generating summary items report", extra={
            "extra_fields": {"tenant_id": tenant_id, "group_by": data.group_by}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="si"
                )
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "s.sale_date"
                )

                where_clause = " AND ".join(conditions)
                
                if data.group_by == 'PRODUCT':
                    query = f"""
                        SELECT 
                            si.product_id,
                            p.name as product_name,
                            COUNT(DISTINCT s.id) as sale_count,
                            COALESCE(SUM(si.quantity), 0) as total_quantity,
                            COALESCE(SUM(si.line_total), 0) as total_revenue
                        FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                        INNER JOIN {db_settings.MSG_SALES_TABLE} s
                            ON si.sale_id = s.id
                            AND si.tenant_id = s.tenant_id
                            AND si.org_id = s.org_id
                            AND si.bus_id = s.bus_id
                            AND si.loc_id = s.loc_id
                        LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                            ON si.product_id = p.id
                            AND si.tenant_id = p.tenant_id
                            AND si.org_id = p.org_id
                            AND si.bus_id = p.bus_id
                        WHERE {where_clause}
                        AND s.deleted_by IS NULL
                        GROUP BY si.product_id, p.name
                        ORDER BY total_revenue DESC
                        LIMIT %s
                    """
                    params.append(data.size)
                    cursor.execute(query, tuple(params))
                    results = cursor.fetchall()
                    
                    summary_items = []
                    for row in results:
                        summary_items.append(SummaryItemReadBase(
                            label=row.get('product_name') or 'Unknown Product',
                            value=ReportsService._quantize_decimal(row.get('total_revenue')),
                            count=int(row.get('sale_count', 0)),
                        ))
                
                elif data.group_by == 'MONTH':
                    # Group by month
                    conditions, params = ReportsService._get_base_where_conditions(
                        tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="s"
                    )
                    conditions, params = ReportsService._add_date_filters(
                        conditions, params, data.from_date, data.to_date, "s.sale_date"
                    )
                    where_clause = " AND ".join(conditions)
                    
                    query = f"""
                        SELECT 
                            TO_CHAR(s.sale_date, 'YYYY-MM') as period,
                            COUNT(DISTINCT s.id) as sale_count,
                            COALESCE(SUM(si.line_total), 0) as total_revenue
                        FROM {db_settings.MSG_SALES_TABLE} s
                        INNER JOIN {db_settings.MSG_SALES_ITEMS_TABLE} si
                            ON s.id = si.sale_id
                            AND s.tenant_id = si.tenant_id
                            AND s.org_id = si.org_id
                            AND s.bus_id = si.bus_id
                            AND s.loc_id = si.loc_id
                        WHERE {where_clause}
                        AND s.deleted_by IS NULL
                        GROUP BY TO_CHAR(s.sale_date, 'YYYY-MM')
                        ORDER BY period DESC
                    """
                    cursor.execute(query, tuple(params))
                    results = cursor.fetchall()
                    
                    summary_items = []
                    for row in results:
                        summary_items.append(SummaryItemReadBase(
                            label=row.get('period', ''),
                            value=ReportsService._quantize_decimal(row.get('total_revenue')),
                            count=int(row.get('sale_count', 0)),
                        ))

                response = SummaryItemsReportResponseReadBase(
                    report_type="summary_items",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    summary_items=summary_items,
                    total_items=len(summary_items),
                )

                return Respons(
                    success=True,
                    detail="Summary items report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating summary items report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate summary items report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_detailed_sales_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: DetailedSalesReportRequestWriteDto,
    ) -> Respons[DetailedSalesReportResponseReadBase]:
        """Get detailed sales report"""
        logger.info("Generating detailed sales report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="s"
                )
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "s.sale_date"
                )

                # Additional filters
                if data.customer_id:
                    conditions.append("s.customer_id = %s")
                    params.append(data.customer_id)
                if data.status:
                    conditions.append("s.status = %s")
                    params.append(data.status)

                where_clause = " AND ".join(conditions)

                # Get payment methods for each sale
                query = f"""
                    SELECT DISTINCT
                        s.id as sale_id,
                        s.sale_number,
                        s.sale_date,
                        s.total_amount,
                        s.paid_amount,
                        s.balance_amount,
                        s.status,
                        s.created_by,
                        c.fullname as customer_name,
                        (SELECT COUNT(*) FROM {db_settings.MSG_SALES_ITEMS_TABLE} si 
                         WHERE si.sale_id = s.id AND si.tenant_id = s.tenant_id) as items_count
                    FROM {db_settings.MSG_SALES_TABLE} s
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON s.customer_id = c.id
                        AND s.tenant_id = c.tenant_id
                        AND s.org_id = c.org_id
                        AND s.bus_id = c.bus_id
                    WHERE {where_clause}
                    AND s.deleted_by IS NULL
                    ORDER BY s.sale_date DESC, s.sale_number DESC
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                params.extend([data.size, offset])
                cursor.execute(query, tuple(params))
                sales = cursor.fetchall()

                # Get payment methods for each sale
                detailed_items = []
                for sale in sales:
                    # Get payment methods
                    cursor.execute(
                        f"""
                        SELECT DISTINCT payment_method
                        FROM {db_settings.MSG_SALES_PAYMENTS_TABLE}
                        WHERE sale_id = %s
                        AND tenant_id = %s
                        AND payment_status = 'SUCCESS'
                        AND deleted_at IS NULL
                        """,
                        (sale['sale_id'], tenant_id)
                    )
                    payment_methods = [row['payment_method'] for row in cursor.fetchall()]

                    # Apply amount filters if specified
                    total_amount = Decimal(str(sale.get('total_amount', 0)))
                    if data.min_amount and total_amount < Decimal(str(data.min_amount)):
                        continue
                    if data.max_amount and total_amount > Decimal(str(data.max_amount)):
                        continue

                    detailed_items.append(DetailedSalesItemReadBase(
                        sale_id=sale['sale_id'],
                        sale_number=sale['sale_number'],
                        sale_date=sale['sale_date'],
                        customer_name=sale.get('customer_name'),
                        total_amount=ReportsService._quantize_decimal(sale.get('total_amount')),
                        paid_amount=ReportsService._quantize_decimal(sale.get('paid_amount')),
                        balance_amount=ReportsService._quantize_decimal(sale.get('balance_amount')),
                        payment_methods=payment_methods,
                        items_count=int(sale.get('items_count', 0)),
                        status=sale.get('status', ''),
                        created_by=sale.get('created_by'),
                    ))

                # Get total count
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM {db_settings.MSG_SALES_TABLE} s
                    WHERE {where_clause}
                    AND s.deleted_by IS NULL
                """
                cursor.execute(count_query, tuple(params[:-2]))  # Remove LIMIT and OFFSET params
                total_result = cursor.fetchone()
                total_count = int(total_result['total']) if total_result else 0

                # Calculate total amount
                total_amount = sum(item.total_amount for item in detailed_items)
                
                response = DetailedSalesReportResponseReadBase(
                    report_type="detailed_sales",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=detailed_items,
                    total_items=total_count,
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (total_count + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Detailed sales report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating detailed sales report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate detailed sales report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_closeout_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: CloseoutReportRequestWriteDto,
    ) -> Respons[CloseoutReadBase]:
        """Get closeout report for a specific date"""
        logger.info("Generating closeout report", extra={
            "extra_fields": {"tenant_id": tenant_id, "date": str(data.closeout_date)}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, table_alias="s"
                )
                conditions.append("DATE(s.sale_date) = DATE(%s)")
                params.append(data.closeout_date)

                where_clause = " AND ".join(conditions)

                # Get sales for the day
                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(DISTINCT s.id) as transaction_count,
                        COALESCE(SUM(s.total_amount), 0) as total_sales,
                        COALESCE(SUM(s.paid_amount), 0) as total_receipts
                    FROM {db_settings.MSG_SALES_TABLE} s
                    WHERE {where_clause}
                    AND s.deleted_by IS NULL
                    """,
                    tuple(params)
                )
                sales_result = cursor.fetchone()

                # Get payments by method
                cursor.execute(
                    f"""
                    SELECT 
                        p.payment_method,
                        COALESCE(SUM(p.paid_amount), 0) as amount
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} p
                    INNER JOIN {db_settings.MSG_SALES_TABLE} s
                        ON p.sale_id = s.id
                        AND p.tenant_id = s.tenant_id
                        AND p.org_id = s.org_id
                        AND p.bus_id = s.bus_id
                        AND p.loc_id = s.loc_id
                    WHERE {where_clause}
                    AND p.payment_status = 'SUCCESS'
                    AND p.deleted_at IS NULL
                    AND s.deleted_by IS NULL
                    GROUP BY p.payment_method
                    """,
                    tuple(params)
                )
                payments_by_method = cursor.fetchall()
                
                cash_sales = Decimal('0')
                card_sales = Decimal('0')
                other_payments = Decimal('0')
                
                for payment in payments_by_method:
                    method = payment.get('payment_method', '').upper()
                    amount = ReportsService._quantize_decimal(payment.get('amount'))
                    if 'CASH' in method:
                        cash_sales = amount
                    elif 'CARD' in method or 'DEBIT' in method or 'CREDIT' in method:
                        card_sales += amount
                    else:
                        other_payments += amount

                # Get expenses for the day
                expense_conditions = [
                    "tenant_id = %s",
                    "org_id = %s",
                    "bus_id = %s",
                    "delete_status = 'NOT_DELETED'",
                    "DATE(cdate) = DATE(%s)"
                ]
                expense_params = [tenant_id, org_id, bus_id, data.closeout_date]
                if data.loc_id:
                    expense_conditions.append("loc_id = %s")
                    expense_params.append(data.loc_id)

                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(amount), 0) as total_expenses
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                    WHERE {' AND '.join(expense_conditions)}
                    """,
                    tuple(expense_params)
                )
                expenses_result = cursor.fetchone()

                # Get refunds for the day
                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(*) as refund_count,
                        COALESCE(SUM(p.paid_amount), 0) as refund_amount
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} p
                    INNER JOIN {db_settings.MSG_SALES_TABLE} s
                        ON p.sale_id = s.id
                        AND p.tenant_id = s.tenant_id
                        AND p.org_id = s.org_id
                        AND p.bus_id = s.bus_id
                        AND p.loc_id = s.loc_id
                    WHERE {where_clause}
                    AND p.payment_status = 'REFUNDED'
                    AND p.deleted_at IS NULL
                    AND s.deleted_by IS NULL
                    """,
                    tuple(params)
                )
                refunds_result = cursor.fetchone()

                # For now, opening balance would need to be calculated from previous closeout
                # This is a simplified version - you may want to store previous closeout values
                opening_balance = Decimal('0')  # TODO: Get from previous closeout if stored
                
                total_sales = ReportsService._quantize_decimal(sales_result.get('total_sales'))
                total_receipts = ReportsService._quantize_decimal(sales_result.get('total_receipts'))
                total_expenses = ReportsService._quantize_decimal(expenses_result.get('total_expenses'))
                total_refunds = ReportsService._quantize_decimal(refunds_result.get('refund_amount', 0))
                
                closing_balance = opening_balance + total_receipts - total_expenses - total_refunds

                closeout = CloseoutReadBase(
                    date=data.closeout_date,
                    opening_balance=opening_balance,
                    total_sales=total_sales,
                    total_receipts=total_receipts,
                    total_expenses=total_expenses,
                    total_refunds=total_refunds,
                    closing_balance=closing_balance,
                    cash_sales=cash_sales,
                    card_sales=card_sales,
                    other_payments=other_payments,
                    transaction_count=int(sales_result.get('transaction_count', 0)),
                )

                return Respons(
                    success=True,
                    detail="Closeout report generated successfully",
                    data=[closeout],
                )

        except Exception as e:
            logger.error(f"Error generating closeout report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate closeout report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_profit_loss_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ProfitLossReportRequestWriteDto,
    ) -> Respons:
        """Get profit and loss report"""
        logger.info("Generating profit and loss report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="s"
                )

                # Get revenue from sales
                sales_conditions = list(conditions)
                sales_params = list(params)
                sales_conditions, sales_params = ReportsService._add_date_filters(
                    sales_conditions, sales_params, data.from_date, data.to_date, "s.sale_date"
                )
                sales_where = " AND ".join(sales_conditions)

                cursor.execute(
                    f"""
                    SELECT 
                        COALESCE(SUM(p.paid_amount), 0) as total_revenue
                    FROM {db_settings.MSG_SALES_TABLE} s
                    INNER JOIN {db_settings.MSG_SALES_PAYMENTS_TABLE} p
                        ON s.id = p.sale_id
                        AND s.tenant_id = p.tenant_id
                        AND s.org_id = p.org_id
                        AND s.bus_id = p.bus_id
                        AND s.loc_id = p.loc_id
                    WHERE {sales_where}
                    AND p.payment_status = 'SUCCESS'
                    AND p.deleted_at IS NULL
                    AND s.deleted_by IS NULL
                    """,
                    tuple(sales_params)
                )
                sales_revenue_result = cursor.fetchone()

                # Get revenue from invoices
                invoice_conditions, invoice_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="i"
                )
                invoice_conditions, invoice_params = ReportsService._add_date_filters(
                    invoice_conditions, invoice_params, data.from_date, data.to_date, "i.sale_date"
                )
                invoice_where = " AND ".join(invoice_conditions)

                cursor.execute(
                    f"""
                    SELECT 
                        COALESCE(SUM(ii.line_total), 0) as total_revenue
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    INNER JOIN {db_settings.MSG_INVOICE_ITEMS_TABLE} ii
                        ON i.id = ii.invoice_id
                        AND i.tenant_id = ii.tenant_id
                        AND i.org_id = ii.org_id
                        AND i.bus_id = ii.bus_id
                        AND i.loc_id = ii.loc_id
                    WHERE {invoice_where}
                    AND i.deleted_by IS NULL
                    """,
                    tuple(invoice_params)
                )
                invoice_revenue_result = cursor.fetchone()

                # Get COGS (Cost of Goods Sold) - from sale items
                cursor.execute(
                    f"""
                    SELECT 
                        COALESCE(SUM(si.quantity * pb.cost_price), 0) as total_cogs
                    FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                    INNER JOIN {db_settings.MSG_SALES_TABLE} s
                        ON si.sale_id = s.id
                        AND si.tenant_id = s.tenant_id
                        AND si.org_id = s.org_id
                        AND si.bus_id = s.bus_id
                        AND si.loc_id = s.loc_id
                    INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        ON si.batch_id = pb.id
                        AND si.tenant_id = pb.tenant_id
                    WHERE {sales_where}
                    AND s.deleted_by IS NULL
                    """,
                    tuple(sales_params)
                )
                cogs_result = cursor.fetchone()

                # Get expenses
                expense_conditions, expense_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                expense_conditions, expense_params = ReportsService._add_date_filters(
                    expense_conditions, expense_params, data.from_date, data.to_date, "DATE(e.cdate)"
                )
                expense_where = " AND ".join(expense_conditions)

                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(amount), 0) as total_expenses
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {expense_where}
                    AND e.delete_status = 'NOT_DELETED'
                    """,
                    tuple(expense_params)
                )
                expenses_result = cursor.fetchone()

                total_revenue = ReportsService._quantize_decimal(sales_revenue_result.get('total_revenue')) + \
                               ReportsService._quantize_decimal(invoice_revenue_result.get('total_revenue'))
                total_cogs = ReportsService._quantize_decimal(cogs_result.get('total_cogs'))
                total_expenses = ReportsService._quantize_decimal(expenses_result.get('total_expenses'))
                
                gross_profit = total_revenue - total_cogs
                net_profit = gross_profit - total_expenses

                gross_profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')
                net_profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')

                profit_loss = ProfitLossSummaryReadBase(
                    period_start=data.from_date or date.today() - timedelta(days=30),
                    period_end=data.to_date or date.today(),
                    total_revenue=total_revenue,
                    cost_of_goods_sold=total_cogs,
                    gross_profit=gross_profit,
                    total_expenses=total_expenses,
                    net_profit=net_profit,
                    gross_profit_margin=ReportsService._quantize_decimal(gross_profit_margin),
                    net_profit_margin=ReportsService._quantize_decimal(net_profit_margin),
                )

                return Respons(
                    success=True,
                    detail="Profit and loss report generated successfully",
                    data=[profit_loss],
                )

        except Exception as e:
            logger.error(f"Error generating profit and loss report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate profit and loss report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_balance_sheet_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: BalanceSheetReportRequestWriteDto,
    ) -> Respons[BalanceSheetReadBase]:
        """Get balance sheet report"""
        logger.info("Generating balance sheet report", extra={
            "extra_fields": {"tenant_id": tenant_id, "as_of_date": str(data.as_of_date)}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, table_alias="sp"
                )

                # Inventory value (current stock value at cost)
                inventory_conditions = list(conditions)
                inventory_params = list(params)
                inventory_where = " AND ".join(inventory_conditions)

                cursor.execute(
                    f"""
                    SELECT 
                        COALESCE(SUM(sp.current_qty * pb.cost_price), 0) as inventory_value
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                        ON sp.loc_id = bl.loc_id
                        AND sp.tenant_id = bl.tenant_id
                        AND sp.org_id = bl.org_id
                        AND sp.bus_id = bl.bus_id
                        AND bl.location_type = 'STORE'
                    INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        ON bl.purchase_batche_id = pb.id
                        AND bl.tenant_id = pb.tenant_id
                        AND bl.org_id = pb.org_id
                        AND bl.bus_id = pb.bus_id
                        AND pb.product_id = sp.product_id
                    WHERE {inventory_where}
                    AND sp.delete_status = 'NOT_DELETED'
                    """,
                    tuple(inventory_params)
                )
                inventory_result = cursor.fetchone()

                # Accounts Receivable (outstanding invoices + sale balances)
                # For invoices
                ar_invoice_conditions, ar_invoice_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, table_alias="i"
                )
                ar_invoice_where = " AND ".join(ar_invoice_conditions)
                
                # For sales
                ar_sales_conditions, ar_sales_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, table_alias="s"
                )
                ar_sales_where = " AND ".join(ar_sales_conditions)

                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(balance_amount), 0) as accounts_receivable
                    FROM (
                        SELECT balance_amount
                        FROM {db_settings.MSG_INVOICES_TABLE} i
                        WHERE {ar_invoice_where}
                        AND i.deleted_by IS NULL
                        AND i.status IN ('DRAFT', 'PARTIALLY_PAID', 'OVERDUE')
                        UNION ALL
                        SELECT balance_amount
                        FROM {db_settings.MSG_SALES_TABLE} s
                        WHERE {ar_sales_where}
                        AND s.deleted_by IS NULL
                        AND s.balance_amount > 0
                    ) combined_ar
                    """,
                    tuple(ar_invoice_params + ar_sales_params)
                )
                ar_result = cursor.fetchone()

                # Accounts Payable would typically come from purchase orders or bills
                # For now, we'll set it to 0 as this might require additional tables
                accounts_payable = Decimal('0')

                # Assets = Inventory + Accounts Receivable + Cash (if tracked)
                inventory_value = ReportsService._quantize_decimal(inventory_result.get('inventory_value'))
                accounts_receivable = ReportsService._quantize_decimal(ar_result.get('accounts_receivable'))
                current_assets = inventory_value + accounts_receivable
                assets = current_assets  # Simplified - would include other assets

                liabilities = accounts_payable
                equity = assets - liabilities

                balance_sheet = BalanceSheetReadBase(
                    as_of_date=data.as_of_date,
                    assets=assets,
                    liabilities=liabilities,
                    equity=equity,
                    current_assets=current_assets,
                    inventory_value=inventory_value,
                    accounts_receivable=accounts_receivable,
                    accounts_payable=accounts_payable,
                )

                return Respons(
                    success=True,
                    detail="Balance sheet report generated successfully",
                    data=[balance_sheet],
                )

        except Exception as e:
            logger.error(f"Error generating balance sheet report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate balance sheet report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_invoices_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: InvoicesSummaryReportRequestWriteDto,
    ) -> Respons[InvoicesSummaryReportResponseReadBase]:
        """Get invoices summary report"""
        logger.info("Generating invoices summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="i"
                )
                conditions.append("i.deleted_by IS NULL")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "i.sale_date"
                )
                if data.status:
                    conditions.append("i.status = %s")
                    params.append(data.status)

                where_clause = " AND ".join(conditions)

                # Main aggregates
                cursor.execute(
                    f"""
                    SELECT
                        COUNT(*) as total_invoices,
                        COALESCE(SUM(i.total_amount), 0) as total_amount,
                        COALESCE(SUM(i.paid_amount), 0) as paid_amount,
                        COALESCE(SUM(CASE WHEN i.status NOT IN ('CANCELLED') AND i.balance_amount > 0
                            THEN i.balance_amount ELSE 0 END), 0) as outstanding_amount,
                        COALESCE(SUM(CASE WHEN i.status = 'OVERDUE' OR (i.due_date IS NOT NULL AND i.due_date < CURRENT_DATE AND i.balance_amount > 0)
                            THEN i.balance_amount ELSE 0 END), 0) as overdue_amount,
                        COALESCE(AVG(CASE WHEN i.status != 'CANCELLED' THEN i.total_amount END), 0) as average_invoice_value
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    WHERE {where_clause}
                    """,
                    tuple(params),
                )
                agg_result = cursor.fetchone()

                # Count by status
                cursor.execute(
                    f"""
                    SELECT i.status, COUNT(*) as cnt, COALESCE(SUM(i.total_amount), 0) as amount
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    WHERE {where_clause}
                    GROUP BY i.status
                    """,
                    tuple(params),
                )
                status_rows = cursor.fetchall()
                invoices_by_status = {}
                for row in status_rows:
                    invoices_by_status[row['status']] = {
                        "count": int(row['cnt']),
                        "amount": str(ReportsService._quantize_decimal(row['amount'])),
                    }

                total_invoices = int(agg_result['total_invoices']) if agg_result else 0
                total_amount = ReportsService._quantize_decimal(agg_result['total_amount']) if agg_result else Decimal('0')
                paid_amount = ReportsService._quantize_decimal(agg_result['paid_amount']) if agg_result else Decimal('0')
                outstanding_amount = ReportsService._quantize_decimal(agg_result['outstanding_amount']) if agg_result else Decimal('0')
                overdue_amount = ReportsService._quantize_decimal(agg_result['overdue_amount']) if agg_result else Decimal('0')
                average_invoice_value = ReportsService._quantize_decimal(agg_result['average_invoice_value']) if agg_result else Decimal('0')

                summary_item = InvoiceSummaryItemReadBase(
                    total_invoices=total_invoices,
                    total_amount=total_amount,
                    paid_amount=paid_amount,
                    outstanding_amount=outstanding_amount,
                    overdue_amount=overdue_amount,
                    average_invoice_value=average_invoice_value,
                    invoices_by_status=invoices_by_status,
                )

                response = InvoicesSummaryReportResponseReadBase(
                    report_type="invoices_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={
                        "status": data.status,
                        "loc_id": data.loc_id,
                        "location_ids": data.location_ids,
                    },
                    summary_items=[summary_item],
                    total_items=1,
                    totals={
                        "total_invoices": total_invoices,
                        "total_amount": str(total_amount),
                        "paid_amount": str(paid_amount),
                        "outstanding_amount": str(outstanding_amount),
                        "overdue_amount": str(overdue_amount),
                        "average_invoice_value": str(average_invoice_value),
                    },
                )

                return Respons(
                    success=True,
                    detail="Invoices summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating invoices summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate invoices summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_invoices_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: InvoicesDetailedReportRequestWriteDto,
    ) -> Respons[InvoicesDetailedReportResponseReadBase]:
        """Get invoices detailed report"""
        logger.info("Generating invoices detailed report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="i"
                )
                conditions.append("i.deleted_by IS NULL")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "i.sale_date"
                )
                if data.customer_id:
                    conditions.append("i.customer_id = %s")
                    params.append(data.customer_id)
                if data.status:
                    conditions.append("i.status = %s")
                    params.append(data.status)
                if data.min_amount is not None:
                    conditions.append("i.total_amount >= %s")
                    params.append(data.min_amount)
                if data.max_amount is not None:
                    conditions.append("i.total_amount <= %s")
                    params.append(data.max_amount)
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT i.id as invoice_id, i.invoice_number, i.sale_date as invoice_date, i.due_date,
                        c.fullname as customer_name, i.total_amount, i.paid_amount, i.balance_amount,
                        i.status,
                        CASE WHEN i.due_date IS NOT NULL AND i.due_date < CURRENT_DATE AND i.balance_amount > 0
                            THEN (CURRENT_DATE - i.due_date)::int ELSE 0 END as days_overdue,
                        (SELECT COUNT(*) FROM {db_settings.MSG_INVOICE_ITEMS_TABLE} ii
                            WHERE ii.invoice_id = i.id AND ii.tenant_id = i.tenant_id AND ii.org_id = i.org_id
                            AND ii.bus_id = i.bus_id AND ii.loc_id = i.loc_id) as items_count
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON i.customer_id = c.id AND i.tenant_id = c.tenant_id AND i.org_id = c.org_id AND i.bus_id = c.bus_id
                    WHERE {where}
                    ORDER BY i.sale_date DESC, i.cdatetime DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {db_settings.MSG_INVOICES_TABLE} i WHERE {where}",
                    tuple(params),
                )
                total_items = cursor.fetchone()['cnt']
                total_amount_sum = sum(ReportsService._quantize_decimal(r['total_amount']) for r in rows)

                items = [
                    InvoiceDetailedItemReadBase(
                        invoice_id=r['invoice_id'],
                        invoice_number=r['invoice_number'],
                        invoice_date=r['invoice_date'],
                        due_date=r['due_date'],
                        customer_name=r['customer_name'] or "",
                        total_amount=ReportsService._quantize_decimal(r['total_amount']),
                        paid_amount=ReportsService._quantize_decimal(r['paid_amount']),
                        balance_amount=ReportsService._quantize_decimal(r['balance_amount']),
                        status=r['status'],
                        days_overdue=r['days_overdue'],
                        items_count=int(r['items_count']) if r['items_count'] else 0,
                    )
                    for r in rows
                ]

                response = InvoicesDetailedReportResponseReadBase(
                    report_type="invoices_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"customer_id": data.customer_id, "status": data.status},
                    items=items,
                    total_items=total_items,
                    total_amount=ReportsService._quantize_decimal(total_amount_sum) if items else None,
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Invoices detailed report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating invoices detailed report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_invoice_aging_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: InvoiceAgingReportRequestWriteDto,
    ) -> Respons[InvoiceAgingReportResponseReadBase]:
        """Get invoice aging report"""
        logger.info("Generating invoice aging report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="i"
                )
                conditions.append("i.deleted_by IS NULL")
                conditions.append("i.balance_amount > 0")
                if not data.include_paid:
                    conditions.append("i.status IN ('DRAFT', 'PARTIALLY_PAID', 'OVERDUE')")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "i.sale_date"
                )
                if data.customer_id:
                    conditions.append("i.customer_id = %s")
                    params.append(data.customer_id)
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT i.customer_id, c.fullname as customer_name, i.id as invoice_id, i.invoice_number,
                        i.sale_date as invoice_date, i.due_date,
                        CASE WHEN i.due_date IS NOT NULL AND i.due_date < CURRENT_DATE
                            THEN (CURRENT_DATE - i.due_date)::int ELSE 0 END as days_overdue,
                        i.balance_amount as amount, i.status
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON i.customer_id = c.id AND i.tenant_id = c.tenant_id AND i.org_id = c.org_id AND i.bus_id = c.bus_id
                    WHERE {where}
                    ORDER BY days_overdue DESC NULLS LAST, i.due_date ASC NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COUNT(*) as cnt, COALESCE(SUM(i.balance_amount), 0) as tot FROM {db_settings.MSG_INVOICES_TABLE} i WHERE {where}",
                    tuple(params),
                )
                agg = cursor.fetchone()
                total_items = agg['cnt']
                total_amount_val = ReportsService._quantize_decimal(agg['tot'])

                items = [
                    InvoiceAgingItemReadBase(
                        customer_id=r['customer_id'] or "",
                        customer_name=r['customer_name'] or "",
                        invoice_id=r['invoice_id'],
                        invoice_number=r['invoice_number'],
                        invoice_date=r['invoice_date'],
                        due_date=r['due_date'],
                        days_overdue=r['days_overdue'] or 0,
                        amount=ReportsService._quantize_decimal(r['amount']),
                        status=r['status'],
                    )
                    for r in rows
                ]

                response = InvoiceAgingReportResponseReadBase(
                    report_type="invoices_aging",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"include_paid": data.include_paid, "customer_id": data.customer_id},
                    items=items,
                    total_items=total_items,
                    total_amount=total_amount_val,
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Invoice aging report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating invoice aging report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_payments_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: PaymentsSummaryReportRequestWriteDto,
    ) -> Respons[PaymentsSummaryReportResponseReadBase]:
        """Get payments summary report from sales_payments and invoice_payments"""
        logger.info("Generating payments summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.deleted_by IS NULL")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(sp.cdatetime)"
                )
                if data.payment_method:
                    conditions.append("sp.payment_method = %s")
                    params.append(data.payment_method)
                if data.status:
                    conditions.append("sp.payment_status = %s")
                    params.append(data.status)
                where = " AND ".join(conditions)

                # Sales payments
                cursor.execute(
                    f"""
                    SELECT COUNT(*) as cnt, COALESCE(SUM(paid_amount), 0) as amt,
                        payment_method, payment_status
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    WHERE {where}
                    GROUP BY payment_method, payment_status
                    """,
                    tuple(params),
                )
                sales_rows = cursor.fetchall()

                # Invoice payments - same conditions but table alias ip
                ip_conditions, ip_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="ip"
                )
                ip_conditions.append("ip.deleted_by IS NULL")
                ip_conditions, ip_params = ReportsService._add_date_filters(
                    ip_conditions, ip_params, data.from_date, data.to_date, "DATE(ip.cdatetime)"
                )
                if data.payment_method:
                    ip_conditions.append("ip.payment_method = %s")
                    ip_params.append(data.payment_method)
                if data.status:
                    ip_conditions.append("ip.payment_status = %s")
                    ip_params.append(data.status)
                ip_where = " AND ".join(ip_conditions)

                cursor.execute(
                    f"""
                    SELECT COUNT(*) as cnt, COALESCE(SUM(paid_amount), 0) as amt,
                        payment_method, payment_status
                    FROM {db_settings.MSG_INVOICE_PAYMENTS_TABLE} ip
                    WHERE {ip_where}
                    GROUP BY payment_method, payment_status
                    """,
                    tuple(ip_params),
                )
                inv_rows = cursor.fetchall()

                payments_by_method = {}
                payments_by_status = {}
                total_payments = 0
                total_amount = Decimal('0')
                refunds_count = 0
                refunds_amount = Decimal('0')

                for row in sales_rows + inv_rows:
                    cnt, amt = int(row['cnt']), ReportsService._quantize_decimal(row['amt'])
                    meth, status = row['payment_method'], row['payment_status']
                    total_payments += cnt
                    total_amount += amt
                    payments_by_method[meth] = payments_by_method.get(meth, {'count': 0, 'amount': Decimal('0')})
                    payments_by_method[meth]['count'] += cnt
                    payments_by_method[meth]['amount'] += amt
                    payments_by_status[status] = payments_by_status.get(status, {'count': 0, 'amount': Decimal('0')})
                    payments_by_status[status]['count'] += cnt
                    payments_by_status[status]['amount'] += amt
                    if status == 'REFUNDED':
                        refunds_count += cnt
                        refunds_amount += amt

                for k in payments_by_method:
                    payments_by_method[k] = {"count": payments_by_method[k]['count'], "amount": str(payments_by_method[k]['amount'])}
                for k in payments_by_status:
                    payments_by_status[k] = {"count": payments_by_status[k]['count'], "amount": str(payments_by_status[k]['amount'])}

                avg = total_amount / total_payments if total_payments else Decimal('0')
                summary_item = PaymentSummaryItemReadBase(
                    total_payments=total_payments,
                    total_amount=total_amount,
                    payments_by_method=payments_by_method,
                    payments_by_status=payments_by_status,
                    average_payment_amount=ReportsService._quantize_decimal(avg),
                    refunds_count=refunds_count,
                    refunds_amount=refunds_amount,
                )
                response = PaymentsSummaryReportResponseReadBase(
                    report_type="payments_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"payment_method": data.payment_method, "status": data.status},
                    summary_items=[summary_item],
                    total_items=1,
                    totals={"total_payments": total_payments, "total_amount": str(total_amount), "refunds_count": refunds_count, "refunds_amount": str(refunds_amount)},
                )
                return Respons(success=True, detail="Payments summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating payments summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_payments_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: PaymentsDetailedReportRequestWriteDto,
    ) -> Respons[PaymentsDetailedReportResponseReadBase]:
        """Get payments detailed report"""
        logger.info("Generating payments detailed report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                offset = (data.page - 1) * data.size
                items = []
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.deleted_by IS NULL")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(sp.cdatetime)"
                )
                if data.payment_method:
                    conditions.append("sp.payment_method = %s")
                    params.append(data.payment_method)
                if data.status:
                    conditions.append("sp.payment_status = %s")
                    params.append(data.status)
                if data.sale_id:
                    conditions.append("sp.sale_id = %s")
                    params.append(data.sale_id)
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT sp.id as payment_id, sp.sale_id, NULL::text as invoice_id,
                        DATE(sp.cdatetime) as payment_date, sp.payment_method, sp.paid_amount as amount,
                        sp.payment_status as status, sp.description as reference_number,
                        c.fullname as customer_name
                    FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s ON sp.sale_id = s.id AND sp.tenant_id = s.tenant_id AND sp.org_id = s.org_id AND sp.bus_id = s.bus_id AND sp.loc_id = s.loc_id AND s.deleted_by IS NULL
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c ON s.customer_id = c.id AND s.tenant_id = c.tenant_id AND s.org_id = c.org_id AND s.bus_id = c.bus_id
                    WHERE {where}
                    ORDER BY sp.cdatetime DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                for row in cursor.fetchall():
                    items.append(PaymentDetailedItemReadBase(
                        payment_id=row['payment_id'],
                        sale_id=row['sale_id'],
                        invoice_id=row['invoice_id'],
                        payment_date=row['payment_date'],
                        payment_method=row['payment_method'],
                        amount=ReportsService._quantize_decimal(row['amount']),
                        status=row['status'],
                        reference_number=row['reference_number'],
                        customer_name=row['customer_name'],
                    ))

                inv_conditions, inv_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="ip"
                )
                inv_conditions.append("ip.deleted_by IS NULL")
                inv_conditions, inv_params = ReportsService._add_date_filters(
                    inv_conditions, inv_params, data.from_date, data.to_date, "DATE(ip.cdatetime)"
                )
                if data.payment_method:
                    inv_conditions.append("ip.payment_method = %s")
                    inv_params.append(data.payment_method)
                if data.status:
                    inv_conditions.append("ip.payment_status = %s")
                    inv_params.append(data.status)
                if data.invoice_id:
                    inv_conditions.append("ip.invoice_id = %s")
                    inv_params.append(data.invoice_id)
                inv_where = " AND ".join(inv_conditions)

                cursor.execute(
                    f"""
                    SELECT ip.id as payment_id, NULL::text as sale_id, ip.invoice_id,
                        DATE(ip.cdatetime) as payment_date, ip.payment_method, ip.paid_amount as amount,
                        ip.payment_status as status, ip.description as reference_number,
                        c.fullname as customer_name
                    FROM {db_settings.MSG_INVOICE_PAYMENTS_TABLE} ip
                    LEFT JOIN {db_settings.MSG_INVOICES_TABLE} i ON ip.invoice_id = i.id AND ip.tenant_id = i.tenant_id AND ip.org_id = i.org_id AND ip.bus_id = i.bus_id AND ip.loc_id = i.loc_id AND i.deleted_by IS NULL
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c ON i.customer_id = c.id AND i.tenant_id = c.tenant_id AND i.org_id = c.org_id AND i.bus_id = c.bus_id
                    WHERE {inv_where}
                    ORDER BY ip.cdatetime DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(inv_params) + (data.size, offset),
                )
                for row in cursor.fetchall():
                    items.append(PaymentDetailedItemReadBase(
                        payment_id=row['payment_id'],
                        sale_id=row['sale_id'],
                        invoice_id=row['invoice_id'],
                        payment_date=row['payment_date'],
                        payment_method=row['payment_method'],
                        amount=ReportsService._quantize_decimal(row['amount']),
                        status=row['status'],
                        reference_number=row['reference_number'],
                        customer_name=row['customer_name'],
                    ))

                items.sort(key=lambda x: x.payment_date, reverse=True)
                items = items[: data.size]
                total_amount = sum(i.amount for i in items)

                cursor.execute(
                    f"SELECT COUNT(*) FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp WHERE {where}",
                    tuple(params),
                )
                cnt_s = cursor.fetchone()['count']
                cursor.execute(
                    f"SELECT COUNT(*) FROM {db_settings.MSG_INVOICE_PAYMENTS_TABLE} ip WHERE {inv_where}",
                    tuple(inv_params),
                )
                cnt_i = cursor.fetchone()['count']
                total_items = cnt_s + cnt_i

                response = PaymentsDetailedReportResponseReadBase(
                    report_type="payments_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={},
                    items=items,
                    total_items=total_items,
                    total_amount=ReportsService._quantize_decimal(total_amount) if items else None,
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Payments detailed report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating payments detailed report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_payments_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: PaymentsGraphicalReportRequestWriteDto,
    ) -> Respons[PaymentsGraphicalReportResponseReadBase]:
        """Get payments graphical report"""
        logger.info("Generating payments graphical report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                fmt = {"DAY": "YYYY-MM-DD", "WEEK": "IYYY-IW", "MONTH": "YYYY-MM", "YEAR": "YYYY"}.get(
                    getattr(data, 'group_by', 'MONTH') or 'MONTH', "YYYY-MM"
                )
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.deleted_by IS NULL")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(sp.cdatetime)"
                )
                where = " AND ".join(conditions)
                ip_conditions, ip_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="ip"
                )
                ip_conditions.append("ip.deleted_by IS NULL")
                ip_conditions, ip_params = ReportsService._add_date_filters(
                    ip_conditions, ip_params, data.from_date, data.to_date, "DATE(ip.cdatetime)"
                )
                ip_where = " AND ".join(ip_conditions)

                cursor.execute(
                    f"""
                    SELECT period, payment_method, COALESCE(SUM(paid_amount), 0) as amount, COUNT(*) as cnt
                    FROM (
                        SELECT TO_CHAR(sp.cdatetime, %s) as period, sp.payment_method, sp.paid_amount
                        FROM {db_settings.MSG_SALES_PAYMENTS_TABLE} sp
                        WHERE {where}
                    ) sub
                    GROUP BY period, payment_method
                    """,
                    (fmt,) + tuple(params),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT period, payment_method, COALESCE(SUM(paid_amount), 0) as amount, COUNT(*) as cnt
                    FROM (
                        SELECT TO_CHAR(ip.cdatetime, %s) as period, ip.payment_method, ip.paid_amount
                        FROM {db_settings.MSG_INVOICE_PAYMENTS_TABLE} ip
                        WHERE {ip_where}
                    ) sub
                    GROUP BY period, payment_method
                    """,
                    (fmt,) + tuple(ip_params),
                )
                inv_rows = cursor.fetchall()

                period_data = {}
                for row in rows + inv_rows:
                    p, m = row['period'], row['payment_method']
                    key = (p, m)
                    if key not in period_data:
                        period_data[key] = {'amount': Decimal('0'), 'count': 0}
                    period_data[key]['amount'] += ReportsService._quantize_decimal(row['amount'])
                    period_data[key]['count'] += int(row['cnt'])

                graph_data = [
                    PaymentGraphItemReadBase(
                        period=k[0],
                        payment_method=k[1],
                        amount=v['amount'],
                        count=v['count'],
                    )
                    for k, v in sorted(period_data.items())
                ]
                response = PaymentsGraphicalReportResponseReadBase(
                    report_type="payments_graphical",
                    report_format="GRAPHICAL",
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={},
                    graph_data=graph_data,
                    chart_type="bar",
                    metadata={},
                )
                return Respons(success=True, detail="Payments graphical report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating payments graphical report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_pricing_rules_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: PricingRulesSummaryReportRequestWriteDto,
    ) -> Respons[PricingRulesSummaryReportResponseReadBase]:
        """Get pricing rules summary report"""
        logger.info("Generating pricing rules summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["r.tenant_id = %s", "r.org_id = %s", "r.bus_id = %s", "r.deleted_by IS NULL"]
                params = [tenant_id, org_id, bus_id]
                if data.rule_id:
                    conditions.append("r.id = %s")
                    params.append(data.rule_id)
                if data.is_active is not None:
                    conditions.append("r.is_active = %s")
                    params.append(data.is_active)
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT r.id as rule_id, r.name as rule_name, r.rule_type, r.is_active,
                        r.discount_value, r.discount_percent, r.cdatetime
                    FROM {db_settings.MSG_PRICING_RULES_TABLE} r
                    WHERE {where}
                    ORDER BY r.name
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                summary_items = []
                for row in rows:
                    summary_items.append(PricingRuleSummaryItemReadBase(
                        rule_id=row['rule_id'],
                        rule_name=row['rule_name'],
                        times_applied=0,
                        total_discount_amount=Decimal('0'),
                        total_items_affected=Decimal('0'),
                        average_discount_percentage=row['discount_percent'] or Decimal('0'),
                    ))
                response = PricingRulesSummaryReportResponseReadBase(
                    report_type="pricing_rules_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"rule_id": data.rule_id, "is_active": data.is_active},
                    summary_items=summary_items,
                    total_items=len(summary_items),
                    totals={"total_rules": len(summary_items)},
                )
                return Respons(success=True, detail="Pricing rules summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating pricing rules summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_pricing_rules_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: PricingRulesDetailedReportRequestWriteDto,
    ) -> Respons[PricingRulesDetailedReportResponseReadBase]:
        """Get pricing rules detailed report"""
        logger.info("Generating pricing rules detailed report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["r.tenant_id = %s", "r.org_id = %s", "r.bus_id = %s"]
                params = [tenant_id, org_id, bus_id]
                if not data.include_inactive:
                    conditions.append("r.is_active = true")
                if data.rule_id:
                    conditions.append("r.id = %s")
                    params.append(data.rule_id)
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT r.id as rule_id, r.name as rule_name, r.rule_type, r.is_active,
                        r.discount_value, r.discount_percent, r.cdatetime
                    FROM {db_settings.MSG_PRICING_RULES_TABLE} r
                    WHERE {where}
                    ORDER BY r.name
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {db_settings.MSG_PRICING_RULES_TABLE} r WHERE {where}", tuple(params))
                total_items = cursor.fetchone()['cnt']

                items = []
                for row in rows:
                    cdt = row['cdatetime']
                    items.append(PricingRuleDetailedItemReadBase(
                        rule_id=row['rule_id'],
                        rule_name=row['rule_name'],
                        rule_type=row['rule_type'],
                        is_active=row['is_active'],
                        times_applied=0,
                        total_discount=Decimal('0'),
                        affected_products_count=0,
                        date_created=cdt.date() if cdt else date.today(),
                        last_applied_date=None,
                    ))
                response = PricingRulesDetailedReportResponseReadBase(
                    report_type="pricing_rules_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={},
                    items=items,
                    total_items=total_items,
                    total_amount=None,
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Pricing rules detailed report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating pricing rules detailed report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_affiliates_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: AffiliatesSummaryReportRequestWriteDto,
    ) -> Respons[AffiliatesSummaryReportResponseReadBase]:
        """Get affiliates summary report"""
        logger.info("Generating affiliates summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["a.tenant_id = %s", "a.org_id = %s", "a.bus_id = %s", "a.delete_status = 'NOT_DELETED'"]
                params = [tenant_id, org_id, bus_id]
                if data.status:
                    conditions.append("a.status = %s")
                    params.append(data.status)
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT a.id as affiliate_id, a.affiliate_code, a.affiliate_name,
                        a.total_referrals, a.total_conversions, a.total_commission_earned, a.total_commission_paid,
                        a.status,
                        (a.total_commission_earned - a.total_commission_paid) as commission_outstanding,
                        CASE WHEN a.total_referrals > 0 THEN (a.total_conversions::numeric / a.total_referrals * 100) ELSE NULL END as conversion_rate,
                        CASE WHEN a.total_conversions > 0 THEN (a.total_commission_earned / a.total_conversions) ELSE NULL END as avg_commission,
                        (SELECT MAX(r.referral_date) FROM {db_settings.MSG_AFFILIATE_REFERRALS_TABLE} r
                            WHERE r.affiliate_id = a.id AND r.tenant_id = a.tenant_id AND r.org_id = a.org_id AND r.bus_id = a.bus_id) as last_referral_date
                    FROM {db_settings.MSG_AFFILIATES_TABLE} a
                    WHERE {where}
                    ORDER BY a.affiliate_name
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                summary_items = []
                for r in rows:
                    outstanding = ReportsService._quantize_decimal(r['commission_outstanding'] or 0)
                    conv_rate = ReportsService._quantize_decimal(r['conversion_rate']) if r['conversion_rate'] is not None else None
                    avg_comm = ReportsService._quantize_decimal(r['avg_commission']) if r['avg_commission'] is not None else None
                    lrd = r['last_referral_date'].date() if hasattr(r['last_referral_date'], 'date') else r['last_referral_date'] if isinstance(r['last_referral_date'], date) else r['last_referral_date']
                    summary_items.append(AffiliateSummaryItemReadBase(
                        affiliate_id=r['affiliate_id'],
                        affiliate_code=r['affiliate_code'],
                        affiliate_name=r['affiliate_name'],
                        total_referrals=int(r['total_referrals'] or 0),
                        total_conversions=int(r['total_conversions'] or 0),
                        total_commission_earned=ReportsService._quantize_decimal(r['total_commission_earned'] or 0),
                        total_commission_paid=ReportsService._quantize_decimal(r['total_commission_paid'] or 0),
                        commission_outstanding=outstanding,
                        conversion_rate=conv_rate,
                        average_commission_per_conversion=avg_comm,
                        status=r['status'],
                        last_referral_date=lrd,
                    ))
                response = AffiliatesSummaryReportResponseReadBase(
                    report_type="affiliates_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"status": data.status},
                    summary_items=summary_items,
                    total_items=len(summary_items),
                    totals={"total_affiliates": len(summary_items)},
                )
                return Respons(success=True, detail="Affiliates summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating affiliates summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_tax_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: TaxSummaryReportRequestWriteDto,
    ) -> Respons[TaxSummaryReportResponseReadBase]:
        """Get tax summary report - lists taxes with usage from sales/invoice items"""
        logger.info("Generating tax summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["t.tenant_id = %s", "t.org_id = %s", "t.bus_id = %s", "t.deleted_by IS NULL"]
                params = [tenant_id, org_id, bus_id]
                if data.tax_id:
                    conditions.append("t.id = %s")
                    params.append(data.tax_id)
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT t.id as tax_id, t.name as tax_name, t.rate as tax_rate
                    FROM {db_settings.MSG_TAXES_TABLE} t
                    WHERE {where}
                    ORDER BY t.name
                    """,
                    tuple(params),
                )
                tax_rows = cursor.fetchall()
                summary_items = []
                for tr in tax_rows:
                    tid = tr['tax_id']
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(si.line_total), 0) as taxable, COALESCE(SUM(si.tax_amount), 0) as tax_amt, COUNT(DISTINCT si.sale_id) as txn_cnt
                        FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                        INNER JOIN {db_settings.MSG_SALES_TABLE} s ON si.sale_id = s.id AND si.tenant_id = s.tenant_id AND si.org_id = s.org_id AND si.bus_id = s.bus_id AND si.loc_id = s.loc_id
                        WHERE si.tenant_id = %s AND si.org_id = %s AND si.bus_id = %s AND s.deleted_by IS NULL
                        AND si.tax_rate = %s
                        """,
                        (tenant_id, org_id, bus_id, float(tr['tax_rate'] or 0)),
                    )
                    sales_agg = cursor.fetchone()
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(ii.line_total), 0) as taxable, COALESCE(SUM(ii.tax_amount), 0) as tax_amt, COUNT(DISTINCT ii.invoice_id) as txn_cnt
                        FROM {db_settings.MSG_INVOICE_ITEMS_TABLE} ii
                        INNER JOIN {db_settings.MSG_INVOICES_TABLE} i ON ii.invoice_id = i.id AND ii.tenant_id = i.tenant_id AND ii.org_id = i.org_id AND ii.bus_id = i.bus_id AND ii.loc_id = i.loc_id
                        WHERE ii.tenant_id = %s AND ii.org_id = %s AND ii.bus_id = %s AND i.deleted_by IS NULL
                        AND ii.tax_rate = %s
                        """,
                        (tenant_id, org_id, bus_id, float(tr['tax_rate'] or 0)),
                    )
                    inv_agg = cursor.fetchone()
                    taxable = ReportsService._quantize_decimal((sales_agg['taxable'] or 0) + (inv_agg['taxable'] or 0))
                    tax_collected = ReportsService._quantize_decimal((sales_agg['tax_amt'] or 0) + (inv_agg['tax_amt'] or 0))
                    txn_cnt = int(sales_agg['txn_cnt'] or 0) + int(inv_agg['txn_cnt'] or 0)
                    summary_items.append(TaxSummaryItemReadBase(
                        tax_id=tid,
                        tax_name=tr['tax_name'],
                        tax_rate=ReportsService._quantize_decimal(tr['tax_rate'] or 0),
                        total_taxable_amount=taxable,
                        total_tax_collected=tax_collected,
                        transaction_count=txn_cnt,
                    ))
                response = TaxSummaryReportResponseReadBase(
                    report_type="tax_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"tax_id": data.tax_id},
                    summary_items=summary_items,
                    total_items=len(summary_items),
                    totals={},
                )
                return Respons(success=True, detail="Tax summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating tax summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_tax_rules_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: TaxRuleSummaryReportRequestWriteDto,
    ) -> Respons[TaxRulesSummaryReportResponseReadBase]:
        """Get tax rules summary report"""
        logger.info("Generating tax rules summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["r.tenant_id = %s", "r.org_id = %s", "r.bus_id = %s", "r.deleted_by IS NULL"]
                params = [tenant_id, org_id, bus_id]
                if data.rule_id:
                    conditions.append("r.id = %s")
                    params.append(data.rule_id)
                if data.is_active is not None:
                    conditions.append("r.is_active = %s")
                    params.append(data.is_active)
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT r.id as rule_id, r.name as rule_name, r.rule_type, r.tax_id
                    FROM {db_settings.MSG_TAX_RULES_TABLE} r
                    WHERE {where}
                    ORDER BY r.name
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                summary_items = [
                    TaxRuleSummaryItemReadBase(
                        rule_id=r['rule_id'],
                        rule_name=r['rule_name'],
                        times_applied=0,
                        total_tax_collected=Decimal('0'),
                        affected_transactions=0,
                    )
                    for r in rows
                ]
                response = TaxRulesSummaryReportResponseReadBase(
                    report_type="tax_rules_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"rule_id": data.rule_id, "is_active": data.is_active},
                    summary_items=summary_items,
                    total_items=len(summary_items),
                    totals={"total_rules": len(summary_items)},
                )
                return Respons(success=True, detail="Tax rules summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating tax rules summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    # =====================================================
    # 2. CUSTOMER REPORTS
    # =====================================================

    @staticmethod
    def get_customers_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: CustomersSummaryReportRequestWriteDto,
    ) -> Respons[CustomersSummaryReportResponseReadBase]:
        """Get customers summary report"""
        logger.info("Generating customers summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="c"
                )
                conditions.append("c.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                query = f"""
                    SELECT 
                        c.id as customer_id,
                        c.fullname as customer_name,
                        COUNT(DISTINCT s.id) as total_purchases,
                        COALESCE(SUM(s.total_amount), 0) as total_revenue,
                        COALESCE(SUM(s.total_amount) / NULLIF(COUNT(DISTINCT s.id), 0), 0) as avg_order_value,
                        MAX(s.sale_date) as last_purchase_date,
                        COALESCE(SUM(s.total_amount), 0) as lifetime_value
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON c.id = s.customer_id
                        AND c.tenant_id = s.tenant_id
                        AND c.org_id = s.org_id
                        AND c.bus_id = s.bus_id
                    WHERE {base_where}
                    GROUP BY c.id, c.fullname
                    HAVING COUNT(DISTINCT s.id) >= COALESCE(%s, 0)
                        AND COALESCE(SUM(s.total_amount), 0) >= COALESCE(%s, 0)
                    ORDER BY total_revenue DESC
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                params.extend([
                    data.min_purchases or 0,
                    Decimal(str(data.min_revenue)) if data.min_revenue else Decimal('0'),
                    data.size,
                    offset
                ])
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    items.append(CustomerSummaryItemReadBase(
                        customer_id=row['customer_id'],
                        customer_name=row['customer_name'],
                        total_purchases=int(row['total_purchases']),
                        total_revenue=ReportsService._quantize_decimal(row['total_revenue']),
                        average_order_value=ReportsService._quantize_decimal(row['avg_order_value']),
                        last_purchase_date=row['last_purchase_date'],
                        lifetime_value=ReportsService._quantize_decimal(row['lifetime_value']),
                    ))

                # Calculate total revenue
                total_revenue = sum(item.total_revenue for item in items)
                
                response = CustomersSummaryReportResponseReadBase(
                    report_type="customers_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_revenue),
                )

                return Respons(
                    success=True,
                    detail="Customers summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating customers summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate customers summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_customers_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: CustomersDetailedReportRequestWriteDto,
    ) -> Respons[CustomersDetailedReportResponseReadBase]:
        """Get customers detailed report"""
        logger.info("Generating customers detailed report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="c"
                )
                
                if not data.include_inactive:
                    conditions.append("c.is_active = true")
                
                if data.customer_id:
                    conditions.append("c.id = %s")
                    params.append(data.customer_id)
                elif data.customer_ids:
                    placeholders = ','.join(['%s'] * len(data.customer_ids))
                    conditions.append(f"c.id IN ({placeholders})")
                    params.extend(data.customer_ids)

                conditions.append("c.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                query = f"""
                    SELECT 
                        c.id as customer_id,
                        c.fullname as customer_name,
                        c.email,
                        c.contact,
                        c.address,
                        COUNT(DISTINCT s.id) as total_orders,
                        COALESCE(SUM(s.total_amount), 0) as total_spent,
                        MIN(s.sale_date) as first_purchase_date,
                        MAX(s.sale_date) as last_purchase_date,
                        COALESCE(SUM(s.total_amount) / NULLIF(COUNT(DISTINCT s.id), 0), 0) as avg_order_value
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON c.id = s.customer_id
                        AND c.tenant_id = s.tenant_id
                        AND c.org_id = s.org_id
                        AND c.bus_id = s.bus_id
                        AND s.deleted_by IS NULL
                    WHERE {base_where}
                    GROUP BY c.id, c.fullname, c.email, c.contact, c.address
                    ORDER BY total_spent DESC
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                params.extend([data.size, offset])
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    items.append(CustomerDetailedItemReadBase(
                        customer_id=row['customer_id'],
                        customer_name=row['customer_name'],
                        email=row.get('email'),
                        contact=row.get('contact'),
                        address=row.get('address'),
                        total_orders=int(row['total_orders']),
                        total_spent=ReportsService._quantize_decimal(row['total_spent']),
                        first_purchase_date=row.get('first_purchase_date'),
                        last_purchase_date=row.get('last_purchase_date'),
                        average_order_value=ReportsService._quantize_decimal(row['avg_order_value']),
                    ))

                # Calculate total spent
                total_spent = sum(item.total_spent for item in items)
                
                response = CustomersDetailedReportResponseReadBase(
                    report_type="customers_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_spent),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (len(items) + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Customers detailed report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating customers detailed report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate customers detailed report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_new_customers_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: NewCustomersReportRequestWriteDto,
    ) -> Respons:
        """Get new customers report"""
        logger.info("Generating new customers report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="c"
                )
                conditions.append("c.delete_status = 'NOT_DELETED'")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(c.cdatetime)"
                )
                base_where = " AND ".join(conditions)

                query = f"""
                    SELECT 
                        c.id as customer_id,
                        c.fullname as customer_name,
                        c.email,
                        c.contact,
                        DATE(c.cdatetime) as registration_date,
                        MIN(s.sale_date) as first_purchase_date,
                        MIN(s.total_amount) as first_purchase_amount,
                        COALESCE(SUM(s.total_amount), 0) as total_spent
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON c.id = s.customer_id
                        AND c.tenant_id = s.tenant_id
                        AND c.org_id = s.org_id
                        AND c.bus_id = s.bus_id
                        AND s.deleted_by IS NULL
                    WHERE {base_where}
                    GROUP BY c.id, c.fullname, c.email, c.contact, DATE(c.cdatetime)
                    ORDER BY registration_date DESC
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                params.extend([data.size, offset])
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    items.append(NewCustomerReadBase(
                        customer_id=row['customer_id'],
                        customer_name=row['customer_name'],
                        email=row.get('email'),
                        contact=row.get('contact'),
                        registration_date=row['registration_date'],
                        first_purchase_date=row.get('first_purchase_date') if data.include_first_purchase else None,
                        first_purchase_amount=ReportsService._quantize_decimal(row['first_purchase_amount']) if data.include_first_purchase and row.get('first_purchase_amount') else None,
                        total_spent=ReportsService._quantize_decimal(row['total_spent']),
                    ))

                # Calculate total spent
                total_spent = sum(item.total_spent for item in items)
                
                response = NewCustomersReportResponseReadBase(
                    report_type="new_customers",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_spent),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (len(items) + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="New customers report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating new customers report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate new customers report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    # =====================================================
    # 3. EXPENSE REPORTS
    # =====================================================

    @staticmethod
    def get_expenses_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpensesSummaryReportRequestWriteDto,
    ) -> Respons:
        """Get expenses summary report"""
        logger.info("Generating expenses summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                conditions.append("e.delete_status = 'NOT_DELETED'")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(e.cdate)"
                )

                if data.source:
                    conditions.append("e.source = %s")
                    params.append(data.source)
                if data.used_by:
                    conditions.append("e.used_by = %s")
                    params.append(data.used_by)

                base_where = " AND ".join(conditions)

                # Get summary stats
                query = f"""
                    SELECT 
                        COUNT(*) as expense_count,
                        COALESCE(SUM(amount), 0) as total_expenses,
                        COALESCE(AVG(amount), 0) as avg_expense,
                        source,
                        COUNT(*) FILTER (WHERE source = 'ALLOCATED') as allocated_count,
                        COALESCE(SUM(amount) FILTER (WHERE source = 'ALLOCATED'), 0) as allocated_amount,
                        COUNT(*) FILTER (WHERE source = 'CONTIGENCY') as contigency_count,
                        COALESCE(SUM(amount) FILTER (WHERE source = 'CONTIGENCY'), 0) as contigency_amount,
                        COUNT(*) FILTER (WHERE source = 'FIXED') as fixed_count,
                        COALESCE(SUM(amount) FILTER (WHERE source = 'FIXED'), 0) as fixed_amount
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {base_where}
                    GROUP BY source
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                expenses_by_source = {}
                total_expenses = Decimal('0')
                expense_count = 0
                total_amount = Decimal('0')

                for row in results:
                    source = row.get('source', 'UNKNOWN')
                    expenses_by_source[source] = {
                        'count': int(row.get('expense_count', 0)),
                        'amount': ReportsService._quantize_decimal(row.get('total_expenses')),
                    }
                    total_amount += ReportsService._quantize_decimal(row.get('total_expenses'))
                    expense_count += int(row.get('expense_count', 0))

                total_expenses = total_amount
                avg_expense = total_expenses / expense_count if expense_count > 0 else Decimal('0')

                summary = ExpenseSummaryItemReadBase(
                    total_expenses=total_expenses,
                    expense_count=expense_count,
                    average_expense=ReportsService._quantize_decimal(avg_expense),
                    expenses_by_source=expenses_by_source,
                    expenses_by_category={},  # Would need expense categories if tracked
                )

                response = ExpensesSummaryReportResponseReadBase(
                    report_type="expenses_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    summary_items=[summary],
                    total_items=1,
                )

                return Respons(
                    success=True,
                    detail="Expenses summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expenses summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expenses summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expenses_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpensesDetailedReportRequestWriteDto,
    ) -> Respons:
        """Get expenses detailed report"""
        logger.info("Generating expenses detailed report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                conditions.append("e.delete_status = 'NOT_DELETED'")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(e.cdate)"
                )

                if data.source:
                    conditions.append("e.source = %s")
                    params.append(data.source)
                if data.used_by:
                    conditions.append("e.used_by = %s")
                    params.append(data.used_by)
                if data.currency_id:
                    conditions.append("e.currency_id = %s")
                    params.append(data.currency_id)

                base_where = " AND ".join(conditions)

                query = f"""
                    SELECT 
                        e.id as expense_id,
                        e.amount,
                        e.currency_id,
                        e.source,
                        e.used_for,
                        e.used_by,
                        e.description,
                        DATE(e.cdate) as expense_date,
                        e.created_by
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {base_where}
                    ORDER BY e.cdate DESC
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                params.extend([data.size, offset])
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    items.append(ExpenseDetailedItemReadBase(
                        expense_id=row['expense_id'],
                        amount=ReportsService._quantize_decimal(row['amount']),
                        currency_id=row['currency_id'],
                        source=row.get('source', ''),
                        used_for=row.get('used_for'),
                        used_by=row.get('used_by'),
                        description=row.get('description'),
                        expense_date=row['expense_date'],
                        created_by=row.get('created_by'),
                    ))

                # Calculate total amount
                total_amount = sum(item.amount for item in items)
                
                response = ExpensesDetailedReportResponseReadBase(
                    report_type="expenses_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (len(items) + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Expenses detailed report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expenses detailed report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expenses detailed report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expenses_by_source_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpensesBySourceReportRequestWriteDto,
    ) -> Respons:
        """Get expenses grouped by source report"""
        logger.info("Generating expenses by source report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                conditions.append("e.delete_status = 'NOT_DELETED'")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(e.cdate)"
                )

                if data.sources:
                    placeholders = ','.join(['%s'] * len(data.sources))
                    conditions.append(f"e.source IN ({placeholders})")
                    params.extend(data.sources)

                base_where = " AND ".join(conditions)

                # Get total for percentage calculation
                cursor.execute(
                    f"SELECT COALESCE(SUM(amount), 0) as total FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e WHERE {base_where}",
                    tuple(params)
                )
                total_row = cursor.fetchone()
                total_all = Decimal(str(total_row.get('total', 0))) if total_row else Decimal('0')

                # Get expenses by source
                query = f"""
                    SELECT 
                        source,
                        COUNT(*) as expense_count,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COALESCE(AVG(amount), 0) as average_amount
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {base_where}
                    GROUP BY source
                    ORDER BY total_amount DESC
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    source = row.get('source', 'UNKNOWN')
                    total_amount = ReportsService._quantize_decimal(row.get('total_amount', 0))
                    percentage = (total_amount / total_all * 100) if total_all > 0 else Decimal('0')
                    
                    items.append(ExpenseBySourceItemReadBase(
                        source=source,
                        total_amount=total_amount,
                        expense_count=int(row.get('expense_count', 0)),
                        average_amount=ReportsService._quantize_decimal(row.get('average_amount', 0)),
                        percentage=ReportsService._quantize_decimal(percentage),
                    ))

                response = ExpensesBySourceReportResponseReadBase(
                    report_type="expenses_by_source",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=total_all,
                )

                return Respons(
                    success=True,
                    detail="Expenses by source report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expenses by source report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expenses by source report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expenses_by_user_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpensesByUserReportRequestWriteDto,
    ) -> Respons:
        """Get expenses grouped by user report"""
        logger.info("Generating expenses by user report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                conditions.append("e.delete_status = 'NOT_DELETED'")
                conditions.append("e.used_by IS NOT NULL")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(e.cdate)"
                )

                if data.source:
                    conditions.append("e.source = %s")
                    params.append(data.source)

                base_where = " AND ".join(conditions)

                # Get expenses by user with source breakdown
                query = f"""
                    SELECT 
                        e.used_by as user_id,
                        u.fullname as user_name,
                        COUNT(*) as expense_count,
                        COALESCE(SUM(e.amount), 0) as total_amount,
                        COALESCE(AVG(e.amount), 0) as average_amount,
                        COUNT(*) FILTER (WHERE e.source = 'ALLOCATED') as allocated_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'ALLOCATED'), 0) as allocated_amount,
                        COUNT(*) FILTER (WHERE e.source = 'CONTIGENCY') as contigency_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'CONTIGENCY'), 0) as contigency_amount,
                        COUNT(*) FILTER (WHERE e.source = 'FIXED') as fixed_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'FIXED'), 0) as fixed_amount,
                        COUNT(*) FILTER (WHERE e.source = 'REIMBURSABLE') as reimbursable_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'REIMBURSABLE'), 0) as reimbursable_amount
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} u ON e.used_by = u.id AND e.tenant_id = u.tenant_id
                    WHERE {base_where}
                    GROUP BY e.used_by, u.fullname
                    HAVING COALESCE(SUM(e.amount), 0) > 0
                """
                
                if data.min_amount:
                    query += " HAVING COALESCE(SUM(e.amount), 0) >= %s"
                    params.append(data.min_amount)
                if data.max_amount:
                    query += " AND COALESCE(SUM(e.amount), 0) <= %s"
                    params.append(data.max_amount)
                
                query += " ORDER BY total_amount DESC"
                
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                total_amount = Decimal('0')
                for row in results:
                    expenses_by_source = {
                        'ALLOCATED': {
                            'count': int(row.get('allocated_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('allocated_amount', 0))
                        },
                        'CONTIGENCY': {
                            'count': int(row.get('contigency_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('contigency_amount', 0))
                        },
                        'FIXED': {
                            'count': int(row.get('fixed_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('fixed_amount', 0))
                        },
                        'REIMBURSABLE': {
                            'count': int(row.get('reimbursable_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('reimbursable_amount', 0))
                        }
                    }
                    
                    user_total = ReportsService._quantize_decimal(row.get('total_amount', 0))
                    total_amount += user_total
                    
                    items.append(ExpenseByUserItemReadBase(
                        user_id=row.get('user_id', ''),
                        user_name=row.get('user_name'),
                        total_amount=user_total,
                        expense_count=int(row.get('expense_count', 0)),
                        average_amount=ReportsService._quantize_decimal(row.get('average_amount', 0)),
                        expenses_by_source=expenses_by_source,
                    ))

                response = ExpensesByUserReportResponseReadBase(
                    report_type="expenses_by_user",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=total_amount,
                )

                return Respons(
                    success=True,
                    detail="Expenses by user report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expenses by user report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expenses by user report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expenses_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpensesGraphicalReportRequestWriteDto,
    ) -> Respons:
        """Get expenses graphical/chart report"""
        logger.info("Generating expenses graphical report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                conditions.append("e.delete_status = 'NOT_DELETED'")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(e.cdate)"
                )

                if data.source:
                    conditions.append("e.source = %s")
                    params.append(data.source)
                elif data.sources:
                    placeholders = ','.join(['%s'] * len(data.sources))
                    conditions.append(f"e.source IN ({placeholders})")
                    params.extend(data.sources)

                base_where = " AND ".join(conditions)

                # Determine date grouping based on group_by
                date_format = ReportsService._get_date_format_for_group_by(data.group_by or 'MONTH')
                date_trunc = ReportsService._get_date_trunc_for_group_by(data.group_by or 'MONTH')

                query = f"""
                    SELECT 
                        {date_format} as label,
                        DATE({date_trunc}) as date,
                        COALESCE(SUM(e.amount), 0) as value,
                        e.source as category
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {base_where}
                    GROUP BY {date_trunc}, e.source
                    ORDER BY date ASC, category ASC
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    items.append(ExpenseGraphItemReadBase(
                        label=row.get('label', ''),
                        value=ReportsService._quantize_decimal(row.get('value', 0)),
                        category=row.get('category'),
                        date=row.get('date'),
                    ))

                response = ExpensesGraphicalReportResponseReadBase(
                    report_type="expenses_graphical",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    metadata={
                        "group_by": data.group_by or 'MONTH',
                        "chart_type": "line" if data.group_by in ['DAY', 'WEEK'] else "bar"
                    }
                )

                return Respons(
                    success=True,
                    detail="Expenses graphical report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expenses graphical report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expenses graphical report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expenses_by_location_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpensesByLocationReportRequestWriteDto,
    ) -> Respons:
        """Get expenses grouped by location report"""
        logger.info("Generating expenses by location report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                conditions.append("e.delete_status = 'NOT_DELETED'")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(e.cdate)"
                )

                if data.source:
                    conditions.append("e.source = %s")
                    params.append(data.source)

                base_where = " AND ".join(conditions)

                # Get expenses by location with source breakdown
                query = f"""
                    SELECT 
                        e.loc_id as location_id,
                        l.name as location_name,
                        COUNT(*) as expense_count,
                        COALESCE(SUM(e.amount), 0) as total_amount,
                        COALESCE(AVG(e.amount), 0) as average_amount,
                        COUNT(*) FILTER (WHERE e.source = 'ALLOCATED') as allocated_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'ALLOCATED'), 0) as allocated_amount,
                        COUNT(*) FILTER (WHERE e.source = 'CONTIGENCY') as contigency_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'CONTIGENCY'), 0) as contigency_amount,
                        COUNT(*) FILTER (WHERE e.source = 'FIXED') as fixed_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'FIXED'), 0) as fixed_amount,
                        COUNT(*) FILTER (WHERE e.source = 'REIMBURSABLE') as reimbursable_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'REIMBURSABLE'), 0) as reimbursable_amount
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l ON e.loc_id = l.id AND e.tenant_id = l.tenant_id
                    WHERE {base_where}
                    GROUP BY e.loc_id, l.name
                    ORDER BY total_amount DESC
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                total_amount = Decimal('0')
                for row in results:
                    expenses_by_source = {
                        'ALLOCATED': {
                            'count': int(row.get('allocated_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('allocated_amount', 0))
                        },
                        'CONTIGENCY': {
                            'count': int(row.get('contigency_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('contigency_amount', 0))
                        },
                        'FIXED': {
                            'count': int(row.get('fixed_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('fixed_amount', 0))
                        },
                        'REIMBURSABLE': {
                            'count': int(row.get('reimbursable_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('reimbursable_amount', 0))
                        }
                    }
                    
                    loc_total = ReportsService._quantize_decimal(row.get('total_amount', 0))
                    total_amount += loc_total
                    
                    items.append(ExpenseByLocationItemReadBase(
                        location_id=row.get('location_id', ''),
                        location_name=row.get('location_name', 'Unknown'),
                        total_amount=loc_total,
                        expense_count=int(row.get('expense_count', 0)),
                        average_amount=ReportsService._quantize_decimal(row.get('average_amount', 0)),
                        expenses_by_source=expenses_by_source,
                    ))

                response = ExpensesByLocationReportResponseReadBase(
                    report_type="expenses_by_location",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=total_amount,
                )

                return Respons(
                    success=True,
                    detail="Expenses by location report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expenses by location report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expenses by location report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expenses_by_period_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpensesByPeriodReportRequestWriteDto,
    ) -> Respons:
        """Get expenses by period/time series report"""
        logger.info("Generating expenses by period report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="e"
                )
                conditions.append("e.delete_status = 'NOT_DELETED'")
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(e.cdate)"
                )

                if data.source:
                    conditions.append("e.source = %s")
                    params.append(data.source)
                elif data.sources:
                    placeholders = ','.join(['%s'] * len(data.sources))
                    conditions.append(f"e.source IN ({placeholders})")
                    params.extend(data.sources)

                base_where = " AND ".join(conditions)

                # Determine date grouping based on group_by
                date_format = ReportsService._get_date_format_for_group_by(data.group_by or 'MONTH')
                date_trunc = ReportsService._get_date_trunc_for_group_by(data.group_by or 'MONTH')

                query = f"""
                    SELECT 
                        {date_format} as period,
                        DATE(MIN({date_trunc})) as period_start,
                        DATE(MAX({date_trunc})) as period_end,
                        COUNT(*) as expense_count,
                        COALESCE(SUM(e.amount), 0) as total_amount,
                        COUNT(*) FILTER (WHERE e.source = 'ALLOCATED') as allocated_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'ALLOCATED'), 0) as allocated_amount,
                        COUNT(*) FILTER (WHERE e.source = 'CONTIGENCY') as contigency_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'CONTIGENCY'), 0) as contigency_amount,
                        COUNT(*) FILTER (WHERE e.source = 'FIXED') as fixed_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'FIXED'), 0) as fixed_amount,
                        COUNT(*) FILTER (WHERE e.source = 'REIMBURSABLE') as reimbursable_count,
                        COALESCE(SUM(e.amount) FILTER (WHERE e.source = 'REIMBURSABLE'), 0) as reimbursable_amount
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {base_where}
                    GROUP BY {date_trunc}
                    ORDER BY period_start ASC
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                total_amount = Decimal('0')
                for row in results:
                    expenses_by_source = {
                        'ALLOCATED': {
                            'count': int(row.get('allocated_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('allocated_amount', 0))
                        },
                        'CONTIGENCY': {
                            'count': int(row.get('contigency_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('contigency_amount', 0))
                        },
                        'FIXED': {
                            'count': int(row.get('fixed_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('fixed_amount', 0))
                        },
                        'REIMBURSABLE': {
                            'count': int(row.get('reimbursable_count', 0)),
                            'amount': ReportsService._quantize_decimal(row.get('reimbursable_amount', 0))
                        }
                    }
                    
                    period_total = ReportsService._quantize_decimal(row.get('total_amount', 0))
                    total_amount += period_total
                    
                    items.append(ExpenseByPeriodItemReadBase(
                        period=row.get('period', ''),
                        period_start=row.get('period_start'),
                        period_end=row.get('period_end'),
                        total_amount=period_total,
                        expense_count=int(row.get('expense_count', 0)),
                        expenses_by_source=expenses_by_source,
                    ))

                response = ExpensesByPeriodReportResponseReadBase(
                    report_type="expenses_by_period",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=len(items),
                    total_amount=total_amount,
                    metadata={
                        "group_by": data.group_by or 'MONTH',
                        "period_type": data.group_by or 'MONTH'
                    }
                )

                return Respons(
                    success=True,
                    detail="Expenses by period report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expenses by period report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expenses by period report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    # =====================================================
    # 4. INVENTORY REPORTS
    # =====================================================

    @staticmethod
    def get_low_inventory_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: LowInventoryReportRequestWriteDto,
    ) -> Respons:
        """Get low inventory report"""
        logger.info("Generating low inventory report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                # Get products with low stock.
                # Low = out of stock, OR at/below reorder_level, OR at/below threshold% of average.
                # Use GREATEST(..., min_low_qty) so single-location products (where AVG = current_qty)
                # still show when qty is at or below min_low_qty (e.g. 10).
                min_low_qty = 10
                query = f"""
                    SELECT 
                        sp.product_id,
                        p.name as product_name,
                        p.sku,
                        sp.current_qty,
                        sp.loc_id,
                        sp.reorder_level,
                        l.loc_name as location_name
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON sp.product_id = p.id
                        AND sp.tenant_id = p.tenant_id
                        AND sp.org_id = p.org_id
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON sp.loc_id = l.id
                        AND sp.tenant_id = l.tenant_id
                    WHERE {base_where}
                    AND p.delete_status = 'NOT_DELETED'
                    AND (
                        sp.current_qty <= 0
                        OR sp.current_qty <= sp.reorder_level
                        OR sp.current_qty <= GREATEST(
                            COALESCE(
                                (SELECT AVG(current_qty) * %s / 100
                                 FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp2
                                 WHERE sp2.product_id = sp.product_id AND sp2.tenant_id = sp.tenant_id),
                                0
                            ),
                            %s
                        )
                    )
                    ORDER BY sp.current_qty ASC
                """
                
                params.append(data.threshold_percentage)
                params.append(min_low_qty)
                if not data.include_zero_stock:
                    query = query.replace(
                        "sp.current_qty <= 0\n                        OR sp.current_qty <= sp.reorder_level",
                        "sp.current_qty > 0\n                        AND (sp.current_qty <= sp.reorder_level",
                    ).replace(
                        "                        )\n                    )",
                        "                        ))\n                    )",
                    )
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    current_qty = Decimal(str(row.get('current_qty', 0)))
                    reorder_level = Decimal(str(row.get('reorder_level', 0)))
                    minimum_threshold = max(
                        reorder_level,
                        current_qty * Decimal(str(100 + data.threshold_percentage)) / Decimal('100'),
                    )
                    reorder_suggestion = max(Decimal('0'), minimum_threshold - current_qty)
                    
                    items.append(LowInventoryItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown'),
                        sku=row.get('sku'),
                        current_qty=current_qty,
                        minimum_threshold=minimum_threshold,
                        location_name=row.get('location_name', 'Unknown Location'),
                        reorder_suggestion=reorder_suggestion,
                    ))

                response = LowInventoryReportResponseReadBase(
                    report_type="low_inventory",
                    report_format="DETAILED",
                    generated_at=datetime.now(),
                    items=items,
                    total_items=len(items),
                    total_amount=None,  # Not applicable for low inventory
                )

                return Respons(
                    success=True,
                    detail="Low inventory report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating low inventory report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate low inventory report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_inventory_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: InventorySummaryReportRequestWriteDto,
    ) -> Respons:
        """Get inventory summary report"""
        logger.info("Generating inventory summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                if data.group_by_location:
                    query = f"""
                        SELECT 
                            sp.loc_id,
                            l.loc_name as location_name,
                            COUNT(DISTINCT sp.product_id) as total_products,
                            COALESCE(SUM(sp.current_qty), 0) as total_quantity,
                            COALESCE(SUM(sp.current_qty * pb.cost_price), 0) as total_value,
                            COUNT(DISTINCT CASE WHEN sp.current_qty <= 0 THEN sp.product_id END) as out_of_stock,
                            COUNT(DISTINCT CASE WHEN sp.current_qty > 0 AND sp.current_qty <= 10 THEN sp.product_id END) as low_stock
                        FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                        LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                            ON sp.loc_id = l.id
                            AND sp.tenant_id = l.tenant_id
                        LEFT JOIN {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                            ON sp.loc_id = bl.loc_id
                            AND sp.tenant_id = bl.tenant_id
                            AND sp.org_id = bl.org_id
                            AND sp.bus_id = bl.bus_id
                            AND bl.location_type = 'STORE'
                        LEFT JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                            ON bl.purchase_batche_id = pb.id
                            AND bl.tenant_id = pb.tenant_id
                            AND bl.org_id = pb.org_id
                            AND bl.bus_id = pb.bus_id
                            AND pb.product_id = sp.product_id
                        WHERE {base_where}
                        GROUP BY sp.loc_id, l.loc_name
                    """
                else:
                    query = f"""
                        SELECT 
                            COUNT(DISTINCT sp.product_id) as total_products,
                            COALESCE(SUM(sp.current_qty), 0) as total_quantity,
                            COALESCE(SUM(sp.current_qty * pb.cost_price), 0) as total_value,
                            COUNT(DISTINCT CASE WHEN sp.current_qty <= 0 THEN sp.product_id END) as out_of_stock,
                            COUNT(DISTINCT CASE WHEN sp.current_qty > 0 AND sp.current_qty <= 10 THEN sp.product_id END) as low_stock
                        FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                        LEFT JOIN {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                            ON sp.loc_id = bl.loc_id
                            AND sp.tenant_id = bl.tenant_id
                            AND sp.org_id = bl.org_id
                            AND sp.bus_id = bl.bus_id
                            AND bl.location_type = 'STORE'
                        LEFT JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                            ON bl.purchase_batche_id = pb.id
                            AND bl.tenant_id = pb.tenant_id
                            AND bl.org_id = pb.org_id
                            AND bl.bus_id = pb.bus_id
                            AND pb.product_id = sp.product_id
                        WHERE {base_where}
                    """
                
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                if data.group_by_location:
                    summary_items = []
                    for row in results:
                        total_value = ReportsService._quantize_decimal(row.get('total_value')) if data.include_values else Decimal('0')
                        total_products = int(row.get('total_products', 0))
                        avg_value = total_value / total_products if total_products > 0 else Decimal('0')
                        
                        summary_items.append(InventorySummaryItemReadBase(
                            total_products=total_products,
                            total_quantity=ReportsService._quantize_decimal(row.get('total_quantity')),
                            total_value=total_value,
                            products_low_stock=int(row.get('low_stock', 0)),
                            products_out_of_stock=int(row.get('out_of_stock', 0)),
                            average_product_value=avg_value,
                        ))
                else:
                    row = results[0] if results else {}
                    total_value = ReportsService._quantize_decimal(row.get('total_value')) if data.include_values else Decimal('0')
                    total_products = int(row.get('total_products', 0))
                    avg_value = total_value / total_products if total_products > 0 else Decimal('0')
                    
                    summary_items = [InventorySummaryItemReadBase(
                        total_products=total_products,
                        total_quantity=ReportsService._quantize_decimal(row.get('total_quantity')),
                        total_value=total_value,
                        products_low_stock=int(row.get('low_stock', 0)),
                        products_out_of_stock=int(row.get('out_of_stock', 0)),
                        average_product_value=avg_value,
                    )]

                response = InventorySummaryReportResponseReadBase(
                    report_type="inventory_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    summary_items=summary_items,
                    total_items=len(summary_items),
                )

                return Respons(
                    success=True,
                    detail="Inventory summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating inventory summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate inventory summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_inventory_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: InventoryDetailedReportRequestWriteDto,
    ) -> Respons[InventoryDetailedReportResponseReadBase]:
        """Get inventory detailed report - per product per location with current qty, unit cost, value, batches count, last movement date"""
        logger.info("Generating inventory detailed report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                product_filter = ""
                if data.product_id:
                    product_filter = " AND sp.product_id = %s"
                    params.append(data.product_id)
                if data.product_ids:
                    placeholders = ','.join(['%s'] * len(data.product_ids))
                    product_filter = f" AND sp.product_id IN ({placeholders})"
                    params.extend(data.product_ids)

                qty_filter = ""
                if data.min_quantity is not None:
                    qty_filter += " AND sp.current_qty >= %s"
                    params.append(data.min_quantity)
                if data.max_quantity is not None:
                    qty_filter += " AND sp.current_qty <= %s"
                    params.append(data.max_quantity)

                query = f"""
                    SELECT 
                        sp.product_id,
                        p.name as product_name,
                        p.sku,
                        l.loc_name as location_name,
                        sp.current_qty as current_qty,
                        COALESCE(batch_costs.avg_cost, 0) as unit_cost,
                        sp.current_qty * COALESCE(batch_costs.avg_cost, 0) as total_value,
                        COALESCE(batch_costs.batches_count, 0) as batches_count,
                        (SELECT MAX(DATE(pm.cdate)) FROM {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE} pm
                         WHERE pm.product_id = sp.product_id AND pm.location_id = sp.loc_id
                         AND pm.tenant_id = sp.tenant_id AND pm.org_id = sp.org_id AND pm.bus_id = sp.bus_id) as last_movement_date
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON sp.product_id = p.id
                        AND sp.tenant_id = p.tenant_id
                        AND sp.org_id = p.org_id
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON sp.loc_id = l.id
                        AND sp.tenant_id = l.tenant_id
                    LEFT JOIN (
                        SELECT bl.loc_id, pb.product_id, bl.tenant_id, bl.org_id, bl.bus_id,
                               AVG(pb.cost_price) as avg_cost,
                               COUNT(DISTINCT bl.purchase_batche_id) as batches_count
                        FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                        INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                            ON bl.purchase_batche_id = pb.id
                            AND bl.tenant_id = pb.tenant_id
                            AND bl.org_id = pb.org_id
                            AND bl.bus_id = pb.bus_id
                        WHERE bl.location_type = 'STORE'
                        GROUP BY bl.loc_id, pb.product_id, bl.tenant_id, bl.org_id, bl.bus_id
                    ) batch_costs
                        ON batch_costs.loc_id = sp.loc_id
                        AND batch_costs.product_id = sp.product_id
                        AND batch_costs.tenant_id = sp.tenant_id
                        AND batch_costs.org_id = sp.org_id
                        AND batch_costs.bus_id = sp.bus_id
                    WHERE {base_where}
                    AND p.delete_status = 'NOT_DELETED'
                    {product_filter}
                    {qty_filter}
                    ORDER BY l.loc_name, p.name
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    unit_cost = ReportsService._quantize_decimal(row.get('unit_cost', 0))
                    total_value = ReportsService._quantize_decimal(row.get('total_value', 0))
                    last_mov = row.get('last_movement_date')
                    if last_mov is None:
                        last_movement_date = None
                    elif isinstance(last_mov, datetime):
                        last_movement_date = last_mov.date()
                    else:
                        last_movement_date = last_mov

                    items.append(InventoryDetailedItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown'),
                        sku=row.get('sku'),
                        location_name=row.get('location_name', 'Unknown Location'),
                        current_qty=ReportsService._quantize_decimal(row.get('current_qty', 0)),
                        unit_cost=unit_cost,
                        total_value=total_value,
                        batches_count=int(row.get('batches_count', 0)),
                        last_movement_date=last_movement_date,
                    ))

                total_amount = sum(item.total_value for item in items)
                offset = (data.page - 1) * data.size
                paginated_items = items[offset:offset + data.size]

                response = InventoryDetailedReportResponseReadBase(
                    report_type="inventory_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=paginated_items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (len(items) + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Inventory detailed report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating inventory detailed report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate inventory detailed report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_inventory_count_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: InventoryCountReportRequestWriteDto,
    ) -> Respons[InventoryCountSummaryReportResponseReadBase]:
        """Get inventory count summary report. Uses current store product qty as expected; counted equals expected when no count data exists."""
        logger.info("Generating inventory count summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                query = f"""
                    SELECT 
                        sp.product_id,
                        p.name as product_name,
                        p.sku,
                        l.loc_name as location_name,
                        sp.current_qty as expected_qty,
                        sp.current_qty as counted_qty,
                        0 as variance,
                        0 as variance_value
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON sp.product_id = p.id
                        AND sp.tenant_id = p.tenant_id
                        AND sp.org_id = p.org_id
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON sp.loc_id = l.id
                        AND sp.tenant_id = l.tenant_id
                    WHERE {base_where}
                    AND p.delete_status = 'NOT_DELETED'
                    ORDER BY l.loc_name, p.name
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    expected_qty = ReportsService._quantize_decimal(row.get('expected_qty', 0))
                    counted_qty = ReportsService._quantize_decimal(row.get('counted_qty', 0))
                    variance = ReportsService._quantize_decimal(row.get('variance', 0))
                    variance_value = ReportsService._quantize_decimal(row.get('variance_value', 0))
                    items.append(InventoryCountItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown'),
                        sku=row.get('sku'),
                        expected_qty=expected_qty,
                        counted_qty=counted_qty,
                        variance=variance,
                        variance_value=variance_value,
                        location_name=row.get('location_name', 'Unknown Location'),
                    ))

                total_amount = sum(item.variance_value for item in items)
                offset = (data.page - 1) * data.size
                paginated_items = items[offset:offset + data.size]

                response = InventoryCountSummaryReportResponseReadBase(
                    report_type="inventory_count_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=paginated_items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (len(items) + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Inventory count summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating inventory count summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate inventory count summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_inventory_count_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: InventoryCountDetailedReportRequestWriteDto,
    ) -> Respons[InventoryCountDetailedReportResponseReadBase]:
        """Get inventory count detailed report. Uses current store product qty as expected; counted equals expected when no count data exists."""
        logger.info("Generating inventory count detailed report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="sp"
                )
                conditions.append("sp.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                product_filter = ""
                if data.product_id:
                    product_filter = " AND sp.product_id = %s"
                    params.append(data.product_id)
                if data.product_ids:
                    placeholders = ','.join(['%s'] * len(data.product_ids))
                    product_filter = f" AND sp.product_id IN ({placeholders})"
                    params.extend(data.product_ids)

                query = f"""
                    SELECT 
                        sp.product_id,
                        p.name as product_name,
                        p.sku,
                        l.loc_name as location_name,
                        sp.current_qty as expected_qty,
                        sp.current_qty as counted_qty,
                        0 as variance,
                        0 as variance_value
                    FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON sp.product_id = p.id
                        AND sp.tenant_id = p.tenant_id
                        AND sp.org_id = p.org_id
                        AND sp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON sp.loc_id = l.id
                        AND sp.tenant_id = l.tenant_id
                    WHERE {base_where}
                    AND p.delete_status = 'NOT_DELETED'
                    {product_filter}
                    ORDER BY l.loc_name, p.name
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    expected_qty = ReportsService._quantize_decimal(row.get('expected_qty', 0))
                    counted_qty = ReportsService._quantize_decimal(row.get('counted_qty', 0))
                    variance = ReportsService._quantize_decimal(row.get('variance', 0))
                    variance_value = ReportsService._quantize_decimal(row.get('variance_value', 0))
                    items.append(InventoryCountItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown'),
                        sku=row.get('sku'),
                        expected_qty=expected_qty,
                        counted_qty=counted_qty,
                        variance=variance,
                        variance_value=variance_value,
                        location_name=row.get('location_name', 'Unknown Location'),
                    ))

                total_amount = sum(item.variance_value for item in items)
                offset = (data.page - 1) * data.size
                paginated_items = items[offset:offset + data.size]

                response = InventoryCountDetailedReportResponseReadBase(
                    report_type="inventory_count_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=paginated_items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (len(items) + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Inventory count detailed report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating inventory count detailed report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate inventory count detailed report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expiring_items_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ExpiringItemsReportRequestWriteDto,
    ) -> Respons:
        """Get expiring items report"""
        logger.info("Generating expiring items report", extra={
            "extra_fields": {"tenant_id": tenant_id, "days_ahead": data.days_ahead}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, table_alias="pb"
                )
                conditions.append("pb.delete_status = 'NOT_DELETED'")
                
                # Also add tenant_id, org_id, bus_id to batch_locations join
                conditions.append("bl.tenant_id = %s")
                conditions.append("bl.org_id = %s")
                conditions.append("bl.bus_id = %s")
                params.extend([tenant_id, org_id, bus_id])
                
                expiry_date_filter = f"pb.product_expiry_date <= (CURRENT_DATE + INTERVAL '{data.days_ahead} days')"
                if not data.include_expired:
                    expiry_date_filter += " AND pb.product_expiry_date >= CURRENT_DATE"
                
                conditions.append(expiry_date_filter)
                base_where = " AND ".join(conditions)

                query = f"""
                    SELECT 
                        pb.product_id,
                        p.name as product_name,
                        pb.id as batch_id,
                        pb.product_expiry_date as expiry_date,
                        (pb.product_expiry_date - CURRENT_DATE) as days_until_expiry,
                        bl.qty as quantity,
                        bl.loc_id,
                        l.loc_name as location_name
                    FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                    INNER JOIN {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                        ON pb.id = bl.purchase_batche_id
                        AND pb.tenant_id = bl.tenant_id
                        AND pb.org_id = bl.org_id
                        AND pb.bus_id = bl.bus_id
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON pb.product_id = p.id
                        AND pb.tenant_id = p.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON bl.loc_id = l.id
                        AND bl.tenant_id = l.tenant_id
                    WHERE {base_where}
                    AND pb.product_expiry_date IS NOT NULL
                    ORDER BY pb.product_expiry_date ASC, bl.qty DESC
                """
                
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    days_until = int(row.get('days_until_expiry', 0)) if row.get('days_until_expiry') else 0
                    items.append(ExpiringItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown'),
                        batch_id=row['batch_id'],
                        expiry_date=row['expiry_date'],
                        days_until_expiry=days_until,
                        quantity=ReportsService._quantize_decimal(row.get('quantity')),
                        location_name=row.get('location_name', 'Unknown Location'),
                    ))

                response = ExpiringItemsReportResponseReadBase(
                    report_type="expiring_items",
                    report_format="DETAILED",
                    generated_at=datetime.now(),
                    items=items,
                    total_items=len(items),
                    total_amount=None,  # Could calculate if needed
                )

                return Respons(
                    success=True,
                    detail="Expiring items report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating expiring items report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate expiring items report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    # =====================================================
    # APPOINTMENT REPORTS
    # =====================================================

    @staticmethod
    def get_appointments_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: AppointmentsSummaryReportRequestWriteDto,
    ) -> Respons:
        """Get appointments summary report"""
        logger.info("Generating appointments summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="a"
                )
                
                # Add date filters based on start_datetime
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(a.start_datetime)"
                )

                # Add status filter if provided
                if data.status:
                    conditions.append("a.status = %s")
                    params.append(data.status)

                base_where = " AND ".join(conditions)

                # Get summary statistics
                query = f"""
                    SELECT 
                        COUNT(*) as total_appointments,
                        COUNT(*) FILTER (WHERE a.status = 'COMPLETED') as completed_appointments,
                        COUNT(*) FILTER (WHERE a.status = 'CANCELLED') as cancelled_appointments,
                        COUNT(*) FILTER (WHERE a.status IN ('PENDING', 'CONFIRMED', 'IN_PROGRESS', 'RESCHEDULED')) as pending_appointments,
                        COUNT(*) FILTER (WHERE a.status = 'NO_SHOW') as no_show_appointments
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    WHERE {base_where}
                """
                cursor.execute(query, tuple(params))
                result = cursor.fetchone()

                if not result:
                    # No appointments found
                    summary = AppointmentSummaryItemReadBase(
                        total_appointments=0,
                        completed_appointments=0,
                        cancelled_appointments=0,
                        pending_appointments=0,
                        completion_rate=Decimal('0'),
                        no_show_rate=Decimal('0'),
                    )
                else:
                    total = int(result.get('total_appointments', 0))
                    completed = int(result.get('completed_appointments', 0))
                    cancelled = int(result.get('cancelled_appointments', 0))
                    pending = int(result.get('pending_appointments', 0))
                    no_show = int(result.get('no_show_appointments', 0))

                    # Calculate rates
                    completion_rate = (Decimal(str(completed)) / Decimal(str(total)) * 100) if total > 0 else Decimal('0')
                    no_show_rate = (Decimal(str(no_show)) / Decimal(str(total)) * 100) if total > 0 else Decimal('0')

                    summary = AppointmentSummaryItemReadBase(
                        total_appointments=total,
                        completed_appointments=completed,
                        cancelled_appointments=cancelled,
                        pending_appointments=pending,
                        completion_rate=ReportsService._quantize_decimal(completion_rate),
                        no_show_rate=ReportsService._quantize_decimal(no_show_rate),
                    )

                # Build filters_applied dictionary
                filters_applied = {}
                if data.from_date:
                    filters_applied["from_date"] = str(data.from_date)
                if data.to_date:
                    filters_applied["to_date"] = str(data.to_date)
                if data.loc_id:
                    filters_applied["loc_id"] = data.loc_id
                if data.location_ids:
                    filters_applied["location_ids"] = data.location_ids
                if data.status:
                    filters_applied["status"] = data.status

                response = AppointmentsSummaryReportResponseReadBase(
                    report_type="appointments_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied=filters_applied,
                    summary_items=[summary],
                    total_items=1,
                )

                return Respons(
                    success=True,
                    detail="Appointments summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating appointments summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate appointments summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_appointments_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: AppointmentsDetailedReportRequestWriteDto,
    ) -> Respons:
        """Get appointments detailed report"""
        logger.info("Generating appointments detailed report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="a"
                )
                
                # Add date filters based on start_datetime
                conditions, params = ReportsService._add_date_filters(
                    conditions, params, data.from_date, data.to_date, "DATE(a.start_datetime)"
                )

                # Add status filter if provided
                if data.status:
                    conditions.append("a.status = %s")
                    params.append(data.status)

                # Add customer_id filter if provided
                if data.customer_id:
                    conditions.append("a.customer_id = %s")
                    params.append(data.customer_id)

                base_where = " AND ".join(conditions)

                # Get total count for pagination
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    WHERE {base_where}
                """
                cursor.execute(count_query, tuple(params))
                total_result = cursor.fetchone()
                total = int(total_result['total']) if total_result else 0

                # Get appointments with user fullnames, customer name
                query = f"""
                    SELECT 
                        a.id as appointment_id,
                        c.fullname as customer_name,
                        a.start_datetime,
                        a.end_datetime,
                        a.status,
                        a.appointment_type as service_type,
                        a.description as notes,
                        creator.fullname as created_by
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator 
                        ON a.created_by = creator.id AND a.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c 
                        ON a.customer_id = c.id 
                        AND a.tenant_id = c.tenant_id 
                        AND a.org_id = c.org_id 
                        AND a.bus_id = c.bus_id
                    WHERE {base_where}
                    ORDER BY a.start_datetime DESC
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                params_with_pagination = params + [data.size, offset]
                cursor.execute(query, tuple(params_with_pagination))
                results = cursor.fetchall()

                items = []
                for row in results:
                    items.append(AppointmentDetailedItemReadBase(
                        appointment_id=row['appointment_id'],
                        customer_name=row.get('customer_name'),
                        start_datetime=row['start_datetime'],
                        end_datetime=row['end_datetime'],
                        status=row['status'],
                        service_type=row.get('service_type'),
                        notes=row.get('notes'),
                        created_by=row.get('created_by'),
                    ))

                # Build filters_applied dictionary
                filters_applied = {}
                if data.from_date:
                    filters_applied["from_date"] = str(data.from_date)
                if data.to_date:
                    filters_applied["to_date"] = str(data.to_date)
                if data.loc_id:
                    filters_applied["loc_id"] = data.loc_id
                if data.location_ids:
                    filters_applied["location_ids"] = data.location_ids
                if data.status:
                    filters_applied["status"] = data.status
                if data.customer_id:
                    filters_applied["customer_id"] = data.customer_id

                # Calculate pagination metadata
                total_pages = (total + data.size - 1) // data.size if total > 0 else 0
                pagination_meta = {
                    "page": data.page,
                    "size": data.size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": (data.page * data.size) < total,
                    "has_previous": data.page > 1,
                }

                response = AppointmentsDetailedReportResponseReadBase(
                    report_type="appointments_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied=filters_applied,
                    items=items,
                    total_items=total,
                    total_amount=None,  # Not applicable for appointments
                    pagination=pagination_meta,
                )

                return Respons(
                    success=True,
                    detail="Appointments detailed report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating appointments detailed report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate appointments detailed report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    # =====================================================
    # PRODUCT METADATA REPORTS
    # =====================================================

    @staticmethod
    def get_product_metadata_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ProductMetadataGraphicalReportRequestWriteDto,
    ) -> Respons:
        """Get product metadata graphical report"""
        logger.info("Generating product metadata graphical report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="amp"
                )
                conditions.append("pm.delete_status = 'NOT_DELETED'")
                conditions.append("p.delete_status = 'NOT_DELETED'")
                
                if data.metadata_type:
                    conditions.append("pm.of_type = %s")
                    params.append(data.metadata_type)

                base_where = " AND ".join(conditions)

                # Get metadata values with product counts and revenue
                query = f"""
                    SELECT 
                        pm.name as metadata_value,
                        COUNT(DISTINCT amp.product_id) as product_count,
                        COALESCE(SUM(si.line_total), 0) as total_revenue
                    FROM {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                    INNER JOIN {db_settings.MSG_PRODUCT_METADATA_TABLE} pm 
                        ON amp.product_metadata_id = pm.id 
                        AND amp.tenant_id = pm.tenant_id
                        AND amp.org_id = pm.org_id
                        AND amp.bus_id = pm.bus_id
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON amp.product_id = p.id
                        AND amp.tenant_id = p.tenant_id
                        AND amp.org_id = p.org_id
                        AND amp.bus_id = p.bus_id
                    LEFT JOIN {db_settings.MSG_SALES_ITEMS_TABLE} si
                        ON p.id = si.product_id
                        AND p.tenant_id = si.tenant_id
                        AND p.org_id = si.org_id
                        AND p.bus_id = si.bus_id
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON si.sale_id = s.id
                        AND si.tenant_id = s.tenant_id
                        AND si.org_id = s.org_id
                        AND si.bus_id = s.bus_id
                        AND s.deleted_by IS NULL
                    WHERE {base_where}
                    GROUP BY pm.name
                    ORDER BY total_revenue DESC
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                graph_data = []
                for row in results:
                    graph_data.append(ProductMetadataGraphItemReadBase(
                        metadata_value=row['metadata_value'],
                        product_count=int(row['product_count']),
                        total_revenue=ReportsService._quantize_decimal(row['total_revenue']),
                    ))

                # Build filters_applied dictionary
                filters_applied = {}
                if data.loc_id:
                    filters_applied["loc_id"] = data.loc_id
                if data.location_ids:
                    filters_applied["location_ids"] = data.location_ids
                if data.metadata_type:
                    filters_applied["metadata_type"] = data.metadata_type
                filters_applied["group_by"] = data.group_by

                response = ProductMetadataGraphicalReportResponseReadBase(
                    report_type="product_metadata_graphical",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied=filters_applied,
                    graph_data=graph_data,
                    chart_type="bar",
                    metadata={"x_axis": "metadata_value", "y_axis": "total_revenue"},
                )

                return Respons(
                    success=True,
                    detail="Product metadata graphical report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating product metadata graphical report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate product metadata graphical report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_metadata_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ProductMetadataSummaryReportRequestWriteDto,
    ) -> Respons:
        """Get product metadata summary report"""
        logger.info("Generating product metadata summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="pm"
                )
                conditions.append("pm.delete_status = 'NOT_DELETED'")
                
                if data.metadata_type:
                    conditions.append("pm.of_type = %s")
                    params.append(data.metadata_type)

                base_where = " AND ".join(conditions)

                # Get metadata summary with product counts and values
                query = f"""
                    SELECT 
                        pm.name as metadata_name,
                        pm.of_type as metadata_type,
                        COUNT(DISTINCT amp.product_id) as products_count,
                        COALESCE(SUM(COALESCE(sp.current_qty, 0) * COALESCE(COALESCE(latest_price.price, latest_batch.base_selling_price), 0)), 0) as total_value
                    FROM {db_settings.MSG_PRODUCT_METADATA_TABLE} pm
                    LEFT JOIN {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp
                        ON pm.id = amp.product_metadata_id
                        AND pm.tenant_id = amp.tenant_id
                        AND pm.org_id = amp.org_id
                        AND pm.bus_id = amp.bus_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON amp.product_id = p.id
                        AND amp.tenant_id = p.tenant_id
                        AND amp.org_id = p.org_id
                        AND amp.bus_id = p.bus_id
                        AND p.delete_status = 'NOT_DELETED'
                    LEFT JOIN {db_settings.MSG_STORE_PRODUCTS_TABLE} sp
                        ON p.id = sp.product_id
                        AND p.tenant_id = sp.tenant_id
                        AND p.org_id = sp.org_id
                        AND p.bus_id = sp.bus_id
                    LEFT JOIN LATERAL (
                        SELECT pp.price
                        FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                        WHERE pp.product_id = p.id
                        AND pp.tenant_id = p.tenant_id
                        AND pp.org_id = p.org_id
                        AND pp.bus_id = p.bus_id
                        AND pp.deleted_by IS NULL
                        ORDER BY pp.cdatetime DESC
                        LIMIT 1
                    ) latest_price ON TRUE
                    LEFT JOIN LATERAL (
                        SELECT pb.base_selling_price
                        FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        WHERE pb.product_id = p.id
                        AND pb.tenant_id = p.tenant_id
                        AND pb.org_id = p.org_id
                        AND pb.bus_id = p.bus_id
                        AND pb.delete_status = 'NOT_DELETED'
                        ORDER BY pb.cdatetime DESC
                        LIMIT 1
                    ) latest_batch ON TRUE
                    WHERE {base_where}
                    GROUP BY pm.id, pm.name, pm.of_type
                    ORDER BY total_value DESC
                """
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                summary_items = []
                for row in results:
                    summary_items.append(ProductMetadataSummaryItemReadBase(
                        metadata_name=row['metadata_name'],
                        metadata_type=row['metadata_type'],
                        products_count=int(row['products_count']),
                        total_value=ReportsService._quantize_decimal(row['total_value']),
                    ))

                # Build filters_applied dictionary
                filters_applied = {}
                if data.loc_id:
                    filters_applied["loc_id"] = data.loc_id
                if data.location_ids:
                    filters_applied["location_ids"] = data.location_ids
                if data.metadata_type:
                    filters_applied["metadata_type"] = data.metadata_type

                response = ProductMetadataSummaryReportResponseReadBase(
                    report_type="product_metadata_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied=filters_applied,
                    summary_items=summary_items,
                    total_items=len(summary_items),
                )

                return Respons(
                    success=True,
                    detail="Product metadata summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating product metadata summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate product metadata summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    # =====================================================
    # PRODUCT PRICES REPORTS
    # =====================================================

    @staticmethod
    def get_product_prices_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ProductPricesSummaryReportRequestWriteDto,
    ) -> Respons:
        """Get product prices summary report"""
        logger.info("Generating product prices summary report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="p"
                )
                conditions.append("p.delete_status = 'NOT_DELETED'")
                
                if data.product_id:
                    conditions.append("p.id = %s")
                    params.append(data.product_id)

                base_where = " AND ".join(conditions)

                # Get product prices summary with cost, selling price, and margin
                # Use subqueries to get latest price and cost from respective tables
                query = f"""
                    SELECT 
                        p.id as product_id,
                        p.name as product_name,
                        (SELECT pp.price 
                         FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                         WHERE pp.product_id = p.id
                         AND pp.tenant_id = p.tenant_id
                         AND pp.org_id = p.org_id
                         AND pp.bus_id = p.bus_id
                         AND pp.deleted_by IS NULL
                         ORDER BY pp.cdatetime DESC
                         LIMIT 1) as current_price,
                        (SELECT pb.cost_price 
                         FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                         WHERE pb.product_id = p.id
                         AND pb.tenant_id = p.tenant_id
                         AND pb.org_id = p.org_id
                         AND pb.bus_id = p.bus_id
                         AND pb.delete_status = 'NOT_DELETED'
                         ORDER BY pb.cdatetime DESC
                         LIMIT 1) as cost_price,
                        CASE 
                            WHEN (SELECT pp.price 
                                   FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                                   WHERE pp.product_id = p.id
                                   AND pp.tenant_id = p.tenant_id
                                   AND pp.org_id = p.org_id
                                   AND pp.bus_id = p.bus_id
                                   AND pp.deleted_by IS NULL
                                   ORDER BY pp.cdatetime DESC
                                   LIMIT 1) > 0 
                            AND (SELECT pb.cost_price 
                                 FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                                 WHERE pb.product_id = p.id
                                 AND pb.tenant_id = p.tenant_id
                                 AND pb.org_id = p.org_id
                                 AND pb.bus_id = p.bus_id
                                 AND pb.delete_status = 'NOT_DELETED'
                                 ORDER BY pb.cdatetime DESC
                                 LIMIT 1) IS NOT NULL
                            THEN (((SELECT pp.price 
                                    FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                                    WHERE pp.product_id = p.id
                                    AND pp.tenant_id = p.tenant_id
                                    AND pp.org_id = p.org_id
                                    AND pp.bus_id = p.bus_id
                                    AND pp.deleted_by IS NULL
                                    ORDER BY pp.cdatetime DESC
                                    LIMIT 1) - COALESCE((SELECT pb.cost_price 
                                                         FROM {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                                                         WHERE pb.product_id = p.id
                                                         AND pb.tenant_id = p.tenant_id
                                                         AND pb.org_id = p.org_id
                                                         AND pb.bus_id = p.bus_id
                                                         AND pb.delete_status = 'NOT_DELETED'
                                                         ORDER BY pb.cdatetime DESC
                                                         LIMIT 1), 0)) / (SELECT pp.price 
                                                                           FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                                                                           WHERE pp.product_id = p.id
                                                                           AND pp.tenant_id = p.tenant_id
                                                                           AND pp.org_id = p.org_id
                                                                           AND pp.bus_id = p.bus_id
                                                                           AND pp.deleted_by IS NULL
                                                                           ORDER BY pp.cdatetime DESC
                                                                           LIMIT 1) * 100)
                            ELSE 0
                        END as margin_percentage,
                        (SELECT COUNT(*) 
                         FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                         WHERE pp.product_id = p.id
                         AND pp.tenant_id = p.tenant_id
                         AND pp.org_id = p.org_id
                         AND pp.bus_id = p.bus_id
                         AND pp.deleted_by IS NULL) as price_change_count,
                        (SELECT DATE(MAX(pp.cdatetime))
                         FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                         WHERE pp.product_id = p.id
                         AND pp.tenant_id = p.tenant_id
                         AND pp.org_id = p.org_id
                         AND pp.bus_id = p.bus_id
                         AND pp.deleted_by IS NULL) as last_price_change_date
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    WHERE {base_where}
                    ORDER BY p.name
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                params.extend([data.size, offset])
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                summary_items = []
                for row in results:
                    current_price = ReportsService._quantize_decimal(row.get('current_price', 0))
                    cost_price = ReportsService._quantize_decimal(row.get('cost_price', 0))
                    margin_percentage = ReportsService._quantize_decimal(row.get('margin_percentage', 0))
                    
                    # Convert datetime to date if needed
                    last_price_change_date = row.get('last_price_change_date')
                    if last_price_change_date and isinstance(last_price_change_date, datetime):
                        last_price_change_date = last_price_change_date.date()
                    
                    summary_items.append(ProductPriceSummaryItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown'),
                        current_price=current_price,
                        cost_price=cost_price,
                        margin_percentage=margin_percentage,
                        price_change_count=int(row.get('price_change_count', 0)),
                        last_price_change_date=last_price_change_date,
                    ))

                # Get total count
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    WHERE {base_where}
                """
                cursor.execute(count_query, tuple(params[:-2]))  # Remove LIMIT and OFFSET params
                total_result = cursor.fetchone()
                total_count = int(total_result['total']) if total_result else 0

                # Build filters_applied dictionary
                filters_applied = {}
                if data.loc_id:
                    filters_applied["loc_id"] = data.loc_id
                if data.location_ids:
                    filters_applied["location_ids"] = data.location_ids
                if data.product_id:
                    filters_applied["product_id"] = data.product_id

                response = ProductPricesSummaryReportResponseReadBase(
                    report_type="product_prices_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied=filters_applied,
                    summary_items=summary_items,
                    total_items=total_count,
                )

                return Respons(
                    success=True,
                    detail="Product prices summary report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating product prices summary report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate product prices summary report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_prices_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ProductPricesGraphicalReportRequestWriteDto,
    ) -> Respons:
        """Get product prices graphical report"""
        logger.info("Generating product prices graphical report", extra={
            "extra_fields": {"tenant_id": tenant_id}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="pp"
                )
                conditions.append("pp.deleted_by IS NULL")
                
                if data.product_id:
                    conditions.append("pp.product_id = %s")
                    params.append(data.product_id)

                # Add date filters if provided
                if data.from_date or data.to_date:
                    if data.from_date:
                        conditions.append("DATE(pp.cdatetime) >= %s")
                        params.append(data.from_date)
                    if data.to_date:
                        conditions.append("DATE(pp.cdatetime) <= %s")
                        params.append(data.to_date)

                base_where = " AND ".join(conditions)

                # Get price history from product_prices table
                if data.price_type == 'cost_price':
                    # For cost price, we need to get from products table
                    # Build conditions for products table
                    product_conditions, product_params = ReportsService._get_base_where_conditions(
                        tenant_id, org_id, bus_id, data.loc_id, data.location_ids, table_alias="p"
                    )
                    product_conditions.append("p.delete_status = 'NOT_DELETED'")
                    
                    if data.product_id:
                        product_conditions.append("p.id = %s")
                        product_params.append(data.product_id)
                    
                    # Add date filters if provided
                    if data.from_date or data.to_date:
                        if data.from_date:
                            product_conditions.append("DATE(p.cdatetime) >= %s")
                            product_params.append(data.from_date)
                        if data.to_date:
                            product_conditions.append("DATE(p.cdatetime) <= %s")
                            product_params.append(data.to_date)
                    
                    product_where = " AND ".join(product_conditions)
                    
                    query = f"""
                        SELECT 
                            DATE(p.cdatetime) as date,
                            p.id as product_id,
                            p.name as product_name,
                            COALESCE(p.cost_price, 0) as price
                        FROM {db_settings.MSG_PRODUCTS_TABLE} p
                        WHERE {product_where}
                        ORDER BY DATE(p.cdatetime) DESC, p.name
                        LIMIT %s
                    """
                    product_params.append(data.size if hasattr(data, 'size') else 100)
                    params = product_params
                else:
                    # For selling price, get from product_prices table
                    query = f"""
                        SELECT 
                            DATE(pp.cdatetime) as date,
                            pp.product_id,
                            p.name as product_name,
                            pp.price
                        FROM {db_settings.MSG_PRODUCT_PRICES_TABLE} pp
                        INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                            ON pp.product_id = p.id
                            AND pp.tenant_id = p.tenant_id
                            AND pp.org_id = p.org_id
                            AND pp.bus_id = p.bus_id
                        WHERE {base_where}
                        AND p.delete_status = 'NOT_DELETED'
                        ORDER BY DATE(pp.cdatetime) DESC, p.name
                        LIMIT %s
                    """
                    params.append(data.size if hasattr(data, 'size') else 100)

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                graph_data = []
                for row in results:
                    graph_data.append(ProductPriceGraphItemReadBase(
                        date=row['date'],
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown'),
                        price=ReportsService._quantize_decimal(row.get('price', 0)),
                        price_type=data.price_type,
                    ))

                # Build filters_applied dictionary
                filters_applied = {}
                if data.loc_id:
                    filters_applied["loc_id"] = data.loc_id
                if data.location_ids:
                    filters_applied["location_ids"] = data.location_ids
                if data.product_id:
                    filters_applied["product_id"] = data.product_id
                if data.from_date:
                    filters_applied["from_date"] = str(data.from_date)
                if data.to_date:
                    filters_applied["to_date"] = str(data.to_date)
                filters_applied["price_type"] = data.price_type

                response = ProductPricesGraphicalReportResponseReadBase(
                    report_type="product_prices_graphical",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied=filters_applied,
                    graph_data=graph_data,
                    chart_type="line",
                    metadata={"x_axis": "date", "y_axis": "price", "price_type": data.price_type},
                )

                return Respons(
                    success=True,
                    detail="Product prices graphical report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating product prices graphical report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate product prices graphical report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_gross_profit_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ProductGrossProfitReportRequestWriteDto,
    ) -> Respons[ProductGrossProfitReportResponseReadBase]:
        """Get product gross profit report - shows gross profit per product"""
        logger.info("Generating product gross profit report", extra={
            "extra_fields": {"tenant_id": tenant_id, "from_date": str(data.from_date), "to_date": str(data.to_date)}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                # Build base conditions for sales
                sales_conditions, sales_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, None, data.location_ids, table_alias="s"
                )
                sales_conditions, sales_params = ReportsService._add_date_filters(
                    sales_conditions, sales_params, data.from_date, data.to_date, "s.sale_date"
                )
                sales_conditions.append("s.deleted_by IS NULL")
                sales_where = " AND ".join(sales_conditions)

                # Build product filter
                product_filter = ""
                if data.product_ids:
                    placeholders = ','.join(['%s'] * len(data.product_ids))
                    product_filter = f"AND si.product_id IN ({placeholders})"
                    sales_params.extend(data.product_ids)

                # Group by clause
                group_by_clause = "si.product_id, p.name"
                location_select = ""
                # Always include location fields: exact columns when grouping by location, else MAX() so every row has a location
                if data.group_by_location:
                    group_by_clause += ", s.loc_id, l.loc_name"
                    location_select = ",\n                        s.loc_id,\n                        l.loc_name as location_name"
                else:
                    # When not grouping by location, use MAX() so location_id/location_name are never null
                    location_select = ",\n                        MAX(s.loc_id) as loc_id,\n                        MAX(l.loc_name) as location_name"

                # Query to get product gross profit
                query = f"""
                    SELECT 
                        si.product_id,
                        p.name as product_name,
                        COALESCE(SUM(si.quantity), 0) as total_quantity_sold,
                        COALESCE(SUM(si.line_total), 0) as total_revenue,
                        COALESCE(SUM(si.quantity * pb.cost_price), 0) as total_cost,
                        COALESCE(SUM(si.line_total), 0) - COALESCE(SUM(si.quantity * pb.cost_price), 0) as gross_profit,
                        CASE 
                            WHEN COALESCE(SUM(si.line_total), 0) > 0 
                            THEN ((COALESCE(SUM(si.line_total), 0) - COALESCE(SUM(si.quantity * pb.cost_price), 0)) / COALESCE(SUM(si.line_total), 0)) * 100
                            ELSE 0
                        END as gross_profit_margin{location_select}
                    FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                    INNER JOIN {db_settings.MSG_SALES_TABLE} s
                        ON si.sale_id = s.id
                        AND si.tenant_id = s.tenant_id
                        AND si.org_id = s.org_id
                        AND si.bus_id = s.bus_id
                        AND si.loc_id = s.loc_id
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON si.product_id = p.id
                        AND si.tenant_id = p.tenant_id
                        AND si.org_id = p.org_id
                        AND si.bus_id = p.bus_id
                    INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        ON si.batch_id = pb.id
                        AND si.tenant_id = pb.tenant_id
                        AND si.org_id = pb.org_id
                        AND si.bus_id = pb.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON s.loc_id = l.id
                        AND s.tenant_id = l.tenant_id
                    WHERE {sales_where}
                    {product_filter}
                    GROUP BY {group_by_clause}
                    HAVING COALESCE(SUM(si.line_total), 0) - COALESCE(SUM(si.quantity * pb.cost_price), 0) > 0
                    ORDER BY gross_profit DESC
                    LIMIT %s OFFSET %s
                """
                
                offset = (data.page - 1) * data.size
                sales_params.extend([data.size, offset])
                cursor.execute(query, tuple(sales_params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    gross_profit = ReportsService._quantize_decimal(row.get('gross_profit', 0))
                    gross_profit_margin = ReportsService._quantize_decimal(row.get('gross_profit_margin', 0))
                    
                    # Apply filters
                    if data.min_gross_profit and gross_profit < Decimal(str(data.min_gross_profit)):
                        continue
                    if data.min_gross_profit_margin and gross_profit_margin < Decimal(str(data.min_gross_profit_margin)):
                        continue

                    items.append(ProductGrossProfitItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown Product'),
                        total_quantity_sold=ReportsService._quantize_decimal(row.get('total_quantity_sold', 0)),
                        total_revenue=ReportsService._quantize_decimal(row.get('total_revenue', 0)),
                        total_cost=ReportsService._quantize_decimal(row.get('total_cost', 0)),
                        gross_profit=gross_profit,
                        gross_profit_margin=gross_profit_margin,
                        location_id=row.get('loc_id'),
                        location_name=row.get('location_name'),
                    ))

                # Get total count (using subquery to handle HAVING clause)
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM (
                        SELECT si.product_id
                        FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                        INNER JOIN {db_settings.MSG_SALES_TABLE} s
                            ON si.sale_id = s.id
                            AND si.tenant_id = s.tenant_id
                            AND si.org_id = s.org_id
                            AND si.bus_id = s.bus_id
                            AND si.loc_id = s.loc_id
                        INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                            ON si.batch_id = pb.id
                            AND si.tenant_id = pb.tenant_id
                            AND si.org_id = pb.org_id
                            AND si.bus_id = pb.bus_id
                        WHERE {sales_where}
                        {product_filter}
                        GROUP BY si.product_id
                        HAVING COALESCE(SUM(si.line_total), 0) - COALESCE(SUM(si.quantity * pb.cost_price), 0) > 0
                    ) as product_counts
                """
                cursor.execute(count_query, tuple(sales_params[:-2]))  # Remove LIMIT and OFFSET
                total_result = cursor.fetchone()
                total_count = int(total_result['total']) if total_result else len(items)

                response = ProductGrossProfitReportResponseReadBase(
                    report_type="product_gross_profit",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=items,
                    total_items=total_count,
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (total_count + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Product gross profit report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating product gross profit report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate product gross profit report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_product_net_profit_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ProductNetProfitReportRequestWriteDto,
    ) -> Respons[ProductNetProfitReportResponseReadBase]:
        """Get product net profit report - shows net profit per product (gross profit - allocated expenses)"""
        logger.info("Generating product net profit report", extra={
            "extra_fields": {"tenant_id": tenant_id, "from_date": str(data.from_date), "to_date": str(data.to_date)}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                # First get product gross profit (same as above)
                sales_conditions, sales_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, None, data.location_ids, table_alias="s"
                )
                sales_conditions, sales_params = ReportsService._add_date_filters(
                    sales_conditions, sales_params, data.from_date, data.to_date, "s.sale_date"
                )
                sales_conditions.append("s.deleted_by IS NULL")
                sales_where = " AND ".join(sales_conditions)

                product_filter = ""
                if data.product_ids:
                    placeholders = ','.join(['%s'] * len(data.product_ids))
                    product_filter = f"AND si.product_id IN ({placeholders})"
                    sales_params.extend(data.product_ids)

                group_by_clause = "si.product_id, p.name"
                location_select = ""
                # Always include location fields: exact columns when grouping by location, else MAX() so every row has a location
                if data.group_by_location:
                    group_by_clause += ", s.loc_id, l.loc_name"
                    location_select = ",\n                        s.loc_id,\n                        l.loc_name as location_name"
                else:
                    location_select = ",\n                        MAX(s.loc_id) as loc_id,\n                        MAX(l.loc_name) as location_name"

                # Get product gross profit
                gross_profit_query = f"""
                    SELECT 
                        si.product_id,
                        p.name as product_name,
                        COALESCE(SUM(si.quantity), 0) as total_quantity_sold,
                        COALESCE(SUM(si.line_total), 0) as total_revenue,
                        COALESCE(SUM(si.quantity * pb.cost_price), 0) as total_cost,
                        COALESCE(SUM(si.line_total), 0) - COALESCE(SUM(si.quantity * pb.cost_price), 0) as gross_profit{location_select}
                    FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                    INNER JOIN {db_settings.MSG_SALES_TABLE} s
                        ON si.sale_id = s.id
                        AND si.tenant_id = s.tenant_id
                        AND si.org_id = s.org_id
                        AND si.bus_id = s.bus_id
                        AND si.loc_id = s.loc_id
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON si.product_id = p.id
                        AND si.tenant_id = p.tenant_id
                        AND si.org_id = p.org_id
                        AND si.bus_id = p.bus_id
                    INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        ON si.batch_id = pb.id
                        AND si.tenant_id = pb.tenant_id
                        AND si.org_id = pb.org_id
                        AND si.bus_id = pb.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON s.loc_id = l.id
                        AND s.tenant_id = l.tenant_id
                    WHERE {sales_where}
                    {product_filter}
                    GROUP BY {group_by_clause}
                    HAVING COALESCE(SUM(si.line_total), 0) - COALESCE(SUM(si.quantity * pb.cost_price), 0) > 0
                """
                cursor.execute(gross_profit_query, tuple(sales_params))
                gross_profit_results = cursor.fetchall()

                # Get total expenses for the period
                expense_conditions, expense_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, None, data.location_ids, table_alias="e"
                )
                expense_conditions, expense_params = ReportsService._add_date_filters(
                    expense_conditions, expense_params, data.from_date, data.to_date, "DATE(e.cdate)"
                )
                expense_conditions.append("e.delete_status = 'NOT_DELETED'")
                expense_where = " AND ".join(expense_conditions)

                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(amount), 0) as total_expenses
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {expense_where}
                    """,
                    tuple(expense_params)
                )
                expenses_result = cursor.fetchone()
                total_expenses = ReportsService._quantize_decimal(expenses_result.get('total_expenses', 0))

                # Calculate total revenue for expense allocation
                total_revenue = sum(ReportsService._quantize_decimal(row.get('total_revenue', 0)) for row in gross_profit_results)
                
                items = []
                for row in gross_profit_results:
                    product_revenue = ReportsService._quantize_decimal(row.get('total_revenue', 0))
                    gross_profit = ReportsService._quantize_decimal(row.get('gross_profit', 0))
                    
                    # Allocate expenses based on method
                    if data.expense_allocation_method == 'revenue' and total_revenue > 0:
                        allocated_expenses = (product_revenue / total_revenue) * total_expenses
                    else:
                        # Equal allocation
                        num_products = len(gross_profit_results) if gross_profit_results else 1
                        allocated_expenses = total_expenses / Decimal(str(num_products)) if num_products > 0 else Decimal('0')
                    
                    allocated_expenses = ReportsService._quantize_decimal(allocated_expenses)
                    net_profit = gross_profit - allocated_expenses
                    
                    gross_profit_margin = (gross_profit / product_revenue * 100) if product_revenue > 0 else Decimal('0')
                    net_profit_margin = (net_profit / product_revenue * 100) if product_revenue > 0 else Decimal('0')

                    # Apply filters
                    if data.min_net_profit and net_profit < Decimal(str(data.min_net_profit)):
                        continue
                    if data.min_net_profit_margin and net_profit_margin < Decimal(str(data.min_net_profit_margin)):
                        continue

                    items.append(ProductNetProfitItemReadBase(
                        product_id=row['product_id'],
                        product_name=row.get('product_name', 'Unknown Product'),
                        total_quantity_sold=ReportsService._quantize_decimal(row.get('total_quantity_sold', 0)),
                        total_revenue=product_revenue,
                        total_cost=ReportsService._quantize_decimal(row.get('total_cost', 0)),
                        gross_profit=gross_profit,
                        allocated_expenses=allocated_expenses,
                        net_profit=net_profit,
                        gross_profit_margin=ReportsService._quantize_decimal(gross_profit_margin),
                        net_profit_margin=ReportsService._quantize_decimal(net_profit_margin),
                        location_id=row.get('loc_id'),
                        location_name=row.get('location_name'),
                    ))

                # Sort by net profit descending
                items.sort(key=lambda x: x.net_profit, reverse=True)
                
                # Apply pagination
                offset = (data.page - 1) * data.size
                paginated_items = items[offset:offset + data.size]

                response = ProductNetProfitReportResponseReadBase(
                    report_type="product_net_profit",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    items=paginated_items,
                    total_items=len(items),
                    pagination={
                        "page": data.page,
                        "size": data.size,
                        "total_pages": (len(items) + data.size - 1) // data.size if data.size > 0 else 0,
                    }
                )

                return Respons(
                    success=True,
                    detail="Product net profit report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating product net profit report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate product net profit report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_location_performance_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: LocationPerformanceReportRequestWriteDto,
    ) -> Respons[LocationPerformanceReportResponseReadBase]:
        """Get location performance comparison report (graphical representation)"""
        logger.info("Generating location performance report", extra={
            "extra_fields": {"tenant_id": tenant_id, "from_date": str(data.from_date), "to_date": str(data.to_date)}
        })

        try:
            with DatabaseManager.transaction() as cursor:
                # Build conditions for sales
                sales_conditions, sales_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, None, data.location_ids, table_alias="s"
                )
                sales_conditions, sales_params = ReportsService._add_date_filters(
                    sales_conditions, sales_params, data.from_date, data.to_date, "s.sale_date"
                )
                sales_conditions.append("s.deleted_by IS NULL")
                sales_where = " AND ".join(sales_conditions)

                # Get location performance metrics
                query = f"""
                    SELECT 
                        s.loc_id,
                        l.loc_name as location_name,
                        COUNT(DISTINCT s.id) as total_sales,
                        COALESCE(SUM(si.line_total), 0) as total_revenue,
                        COALESCE(SUM(si.quantity * pb.cost_price), 0) as total_cost,
                        COALESCE(SUM(si.line_total), 0) - COALESCE(SUM(si.quantity * pb.cost_price), 0) as gross_profit,
                        COALESCE(SUM(si.quantity), 0) as total_items_sold,
                        CASE 
                            WHEN COUNT(DISTINCT s.id) > 0 
                            THEN COALESCE(SUM(si.line_total), 0) / COUNT(DISTINCT s.id)
                            ELSE 0
                        END as average_transaction_value
                    FROM {db_settings.MSG_SALES_TABLE} s
                    INNER JOIN {db_settings.MSG_SALES_ITEMS_TABLE} si
                        ON s.id = si.sale_id
                        AND s.tenant_id = si.tenant_id
                        AND s.org_id = si.org_id
                        AND s.bus_id = si.bus_id
                        AND s.loc_id = si.loc_id
                    INNER JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                        ON si.batch_id = pb.id
                        AND si.tenant_id = pb.tenant_id
                        AND si.org_id = pb.org_id
                        AND si.bus_id = pb.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_LOCATIONS_TABLE} l
                        ON s.loc_id = l.id
                        AND s.tenant_id = l.tenant_id
                    WHERE {sales_where}
                    GROUP BY s.loc_id, l.loc_name
                    ORDER BY total_revenue DESC
                """
                cursor.execute(query, tuple(sales_params))
                location_results = cursor.fetchall()

                # Get expenses per location if needed
                expense_conditions, expense_params = ReportsService._get_base_where_conditions(
                    tenant_id, org_id, bus_id, None, data.location_ids, table_alias="e"
                )
                expense_conditions, expense_params = ReportsService._add_date_filters(
                    expense_conditions, expense_params, data.from_date, data.to_date, "DATE(e.cdate)"
                )
                expense_conditions.append("e.delete_status = 'NOT_DELETED'")
                expense_where = " AND ".join(expense_conditions)

                cursor.execute(
                    f"""
                    SELECT loc_id, COALESCE(SUM(amount), 0) as total_expenses
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {expense_where}
                    GROUP BY loc_id
                    """,
                    tuple(expense_params)
                )
                expenses_by_location = {row['loc_id']: ReportsService._quantize_decimal(row.get('total_expenses', 0)) 
                                       for row in cursor.fetchall()}

                performance_items = []
                for row in location_results:
                    loc_id = row['loc_id']
                    total_revenue = ReportsService._quantize_decimal(row.get('total_revenue', 0))
                    total_cost = ReportsService._quantize_decimal(row.get('total_cost', 0))
                    gross_profit = ReportsService._quantize_decimal(row.get('gross_profit', 0))
                    total_expenses = expenses_by_location.get(loc_id, Decimal('0')) if data.include_expenses else Decimal('0')
                    net_profit = gross_profit - total_expenses

                    gross_profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')
                    net_profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')

                    performance_items.append(LocationPerformanceItemReadBase(
                        location_id=loc_id,
                        location_name=row.get('location_name', 'Unknown Location'),
                        total_sales=int(row.get('total_sales', 0)),
                        total_revenue=total_revenue,
                        total_cost=total_cost,
                        gross_profit=gross_profit,
                        total_expenses=total_expenses,
                        net_profit=net_profit,
                        gross_profit_margin=ReportsService._quantize_decimal(gross_profit_margin),
                        net_profit_margin=ReportsService._quantize_decimal(net_profit_margin),
                        average_transaction_value=ReportsService._quantize_decimal(row.get('average_transaction_value', 0)),
                        total_items_sold=ReportsService._quantize_decimal(row.get('total_items_sold', 0)),
                    ))

                # Convert to graph data points based on metric
                graph_data = []
                for item in performance_items:
                    if data.metric == 'revenue':
                        value = item.total_revenue
                    elif data.metric == 'gross_profit':
                        value = item.gross_profit
                    elif data.metric == 'net_profit':
                        value = item.net_profit
                    elif data.metric == 'sales_count':
                        value = Decimal(str(item.total_sales))
                    else:
                        value = item.total_revenue

                    graph_data.append(GraphDataPointReadBase(
                        label=item.location_name,
                        value=value,
                        category=item.location_id,
                        date=None,
                    ))

                response = LocationPerformanceReportResponseReadBase(
                    report_type="location_performance",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={
                        "location_ids": data.location_ids,
                        "from_date": str(data.from_date),
                        "to_date": str(data.to_date),
                        "metric": data.metric,
                        "include_expenses": data.include_expenses,
                    },
                    graph_data=graph_data,
                    chart_type="bar",  # Bar chart for location comparison
                    metadata={
                        "x_axis": "location",
                        "y_axis": data.metric,
                        "chart_type": "bar",
                        "performance_data": [item.dict() for item in performance_items],
                    },
                )

                return Respons(
                    success=True,
                    detail="Location performance report generated successfully",
                    data=[response],
                )

        except Exception as e:
            logger.error(f"Error generating location performance report: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to generate location performance report: {str(e)}",
                error="INTERNAL_ERROR",
            )

    # =====================================================
    # 10. RECEIVINGS REPORTS
    # =====================================================

    @staticmethod
    def _get_po_base_conditions(tenant_id: str, org_id: str, bus_id: str, from_date=None, to_date=None, supplier_id=None, status=None, table_alias="po"):
        """Build base WHERE conditions for purchase orders (no loc_id)"""
        prefix = f"{table_alias}."
        conditions = [f"{prefix}tenant_id = %s", f"{prefix}org_id = %s", f"{prefix}bus_id = %s"]
        params = [tenant_id, org_id, bus_id]
        if from_date:
            conditions.append(f"{prefix}order_date >= %s")
            params.append(from_date)
        if to_date:
            conditions.append(f"{prefix}order_date <= %s")
            params.append(to_date)
        if supplier_id:
            conditions.append(f"{prefix}supplier_id = %s")
            params.append(supplier_id)
        if status:
            conditions.append(f"{prefix}status = %s")
            params.append(status)
        return conditions, params

    @staticmethod
    def get_receivings_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingSummaryReportRequestWriteDto,
    ) -> Respons[ReceivingsSummaryReportResponseReadBase]:
        """Get receivings summary report"""
        logger.info("Generating receivings summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, data.status
                )
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT COUNT(DISTINCT po.id) as total_receivings,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COALESCE(SUM(poi.qty_received), 0) as total_items_received
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    WHERE {where}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
                total_receivings = int(row['total_receivings'] or 0)
                total_amount = ReportsService._quantize_decimal(row['total_amount'] or 0)
                total_items_received = ReportsService._quantize_decimal(row['total_items_received'] or 0)
                avg_value = (total_amount / total_receivings) if total_receivings > 0 else Decimal('0')

                cursor.execute(
                    f"""
                    SELECT po.status, COUNT(*) as cnt
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    WHERE {where}
                    GROUP BY po.status
                    """,
                    tuple(params),
                )
                receivings_by_status = {r['status']: int(r['cnt']) for r in cursor.fetchall()}

                cursor.execute(
                    f"""
                    SELECT s.fullname as supplier_name, COUNT(DISTINCT po.id) as cnt
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON po.supplier_id = s.id AND po.tenant_id = s.tenant_id AND po.org_id = s.org_id AND po.bus_id = s.bus_id
                    WHERE {where}
                    GROUP BY s.fullname
                    ORDER BY cnt DESC
                    LIMIT 20
                    """,
                    tuple(params),
                )
                receivings_by_supplier = {r['supplier_name'] or 'Unknown': int(r['cnt']) for r in cursor.fetchall()}

                summary_item = ReceivingSummaryItemReadBase(
                    total_receivings=total_receivings,
                    total_amount=total_amount,
                    total_items_received=total_items_received,
                    average_receiving_value=ReportsService._quantize_decimal(avg_value),
                    receivings_by_status=receivings_by_status,
                    receivings_by_supplier=receivings_by_supplier,
                )
                response = ReceivingsSummaryReportResponseReadBase(
                    report_type="receivings_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "status": data.status},
                    summary_items=[summary_item],
                    total_items=1,
                    totals={"total_receivings": total_receivings, "total_amount": float(total_amount)},
                )
                return Respons(success=True, detail="Receivings summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingDetailedReportRequestWriteDto,
    ) -> Respons[ReceivingsDetailedReportResponseReadBase]:
        """Get receivings detailed report"""
        logger.info("Generating receivings detailed report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, data.status
                )
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT po.id as purchase_order_id, po.po_number, po.order_date as receiving_date,
                        s.fullname as supplier_name,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COUNT(DISTINCT poi.id) as items_count,
                        po.status,
                        (SELECT COUNT(*) FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr
                            WHERE pr.purchase_order_id = po.id AND pr.tenant_id = po.tenant_id AND pr.org_id = po.org_id AND pr.bus_id = po.bus_id) as batches_created
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON po.supplier_id = s.id AND po.tenant_id = s.tenant_id AND po.org_id = s.org_id AND po.bus_id = s.bus_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    WHERE {where}
                    GROUP BY po.id, po.po_number, po.order_date, s.fullname, po.status
                    ORDER BY po.order_date DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po WHERE {where}",
                    tuple(params),
                )
                total_items = cursor.fetchone()['cnt']
                items = []
                for row in rows:
                    rec_date = row['receiving_date']
                    if hasattr(rec_date, 'date'):
                        rec_date = rec_date.date()
                    items.append(ReceivingDetailedItemReadBase(
                        purchase_order_id=row['purchase_order_id'],
                        po_number=row['po_number'],
                        receiving_date=rec_date,
                        supplier_name=row['supplier_name'],
                        total_amount=ReportsService._quantize_decimal(row['total_amount']),
                        items_count=int(row['items_count'] or 0),
                        status=row['status'],
                        batches_created=int(row['batches_created'] or 0),
                    ))
                total_amount = sum(i.total_amount for i in items)
                response = ReceivingsDetailedReportResponseReadBase(
                    report_type="receivings_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "status": data.status},
                    items=items,
                    total_items=total_items,
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Receivings detailed report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings detailed report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_summary_categories_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingSummaryCategoriesReportRequestWriteDto,
    ) -> Respons[ReceivingsSummaryCategoriesReportResponseReadBase]:
        """Get receivings summary by categories report"""
        logger.info("Generating receivings summary categories report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT COALESCE(amp.metadata_value, 'Uncategorized') as category_name,
                        COUNT(DISTINCT po.id) as total_receivings,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COALESCE(SUM(poi.qty_received), 0) as total_quantity
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON poi.product_id = p.id AND poi.tenant_id = p.tenant_id AND poi.org_id = p.org_id AND poi.bus_id = p.bus_id
                    LEFT JOIN {db_settings.MSG_ASSIGN_METADATA_TO_PRODUCTS_TABLE} amp ON p.id = amp.product_id AND amp.tenant_id = p.tenant_id AND amp.org_id = p.org_id AND amp.bus_id = p.bus_id AND amp.of_type = 'CATEGORY'
                    WHERE {where}
                    GROUP BY COALESCE(amp.metadata_value, 'Uncategorized')
                    ORDER BY total_amount DESC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                items = []
                for row in rows:
                    items.append(ReceivingCategoryItemReadBase(
                        category_name=row['category_name'],
                        total_receivings=int(row['total_receivings'] or 0),
                        total_amount=ReportsService._quantize_decimal(row['total_amount'] or 0),
                        total_quantity=ReportsService._quantize_decimal(row['total_quantity'] or 0),
                    ))
                total_amount = sum(i.total_amount for i in items)
                response = ReceivingsSummaryCategoriesReportResponseReadBase(
                    report_type="receivings_summary_categories",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id},
                    items=items,
                    total_items=len(items),
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={},
                )
                return Respons(success=True, detail="Receivings summary categories report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings summary categories report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suspended_receivings_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuspendedReceivingsReportRequestWriteDto,
    ) -> Respons[ReceivingsSuspendedReportResponseReadBase]:
        """Get suspended receivings report - POs with status DRAFT or PARTIALLY_RECEIVED"""
        logger.info("Generating suspended receivings report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, None, None
                )
                conditions.append("po.status IN ('DRAFT', 'PARTIALLY_RECEIVED')")
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT po.id as purchase_order_id, po.po_number, po.order_date as receiving_date,
                        s.fullname as supplier_name,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COUNT(DISTINCT poi.id) as items_count,
                        po.status,
                        (SELECT COUNT(*) FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr WHERE pr.purchase_order_id = po.id AND pr.tenant_id = po.tenant_id AND pr.org_id = po.org_id AND pr.bus_id = po.bus_id) as batches_created
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON po.supplier_id = s.id AND po.tenant_id = s.tenant_id AND po.org_id = s.org_id AND po.bus_id = s.bus_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    WHERE {where}
                    GROUP BY po.id, po.po_number, po.order_date, s.fullname, po.status
                    ORDER BY po.order_date DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po WHERE {where}",
                    tuple(params),
                )
                total_items = cursor.fetchone()['cnt']
                items = []
                for row in rows:
                    rec_date = row['receiving_date']
                    if hasattr(rec_date, 'date'):
                        rec_date = rec_date.date()
                    items.append(ReceivingDetailedItemReadBase(
                        purchase_order_id=row['purchase_order_id'],
                        po_number=row['po_number'],
                        receiving_date=rec_date,
                        supplier_name=row['supplier_name'],
                        total_amount=ReportsService._quantize_decimal(row['total_amount']),
                        items_count=int(row['items_count'] or 0),
                        status=row['status'],
                        batches_created=int(row['batches_created'] or 0),
                    ))
                total_amount = sum(i.total_amount for i in items)
                response = ReceivingsSuspendedReportResponseReadBase(
                    report_type="receivings_suspended",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={},
                    items=items,
                    total_items=total_items,
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Suspended receivings report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suspended receivings report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_deleted_receivings_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: DeletedReceivingsReportRequestWriteDto,
    ) -> Respons[ReceivingsDeletedReportResponseReadBase]:
        """Get deleted receivings report - purchase orders with CANCELLED status"""
        logger.info("Generating deleted receivings report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, None, None
                )
                conditions.append("po.status = 'CANCELLED'")
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT po.id as purchase_order_id, po.po_number, po.order_date as receiving_date,
                        s.fullname as supplier_name,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COUNT(DISTINCT poi.id) as items_count,
                        po.status,
                        (SELECT COUNT(*) FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr WHERE pr.purchase_order_id = po.id AND pr.tenant_id = po.tenant_id AND pr.org_id = po.org_id AND pr.bus_id = po.bus_id) as batches_created
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON po.supplier_id = s.id AND po.tenant_id = s.tenant_id AND po.org_id = s.org_id AND po.bus_id = s.bus_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    WHERE {where}
                    GROUP BY po.id, po.po_number, po.order_date, s.fullname, po.status
                    ORDER BY po.order_date DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po WHERE {where}",
                    tuple(params),
                )
                total_items = cursor.fetchone()['cnt']
                items = []
                for row in rows:
                    rec_date = row['receiving_date']
                    if hasattr(rec_date, 'date'):
                        rec_date = rec_date.date()
                    items.append(ReceivingDetailedItemReadBase(
                        purchase_order_id=row['purchase_order_id'],
                        po_number=row['po_number'],
                        receiving_date=rec_date,
                        supplier_name=row['supplier_name'],
                        total_amount=ReportsService._quantize_decimal(row['total_amount']),
                        items_count=int(row['items_count'] or 0),
                        status=row['status'],
                        batches_created=int(row['batches_created'] or 0),
                    ))
                total_amount = sum(i.total_amount for i in items)
                response = ReceivingsDeletedReportResponseReadBase(
                    report_type="receivings_deleted",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={},
                    items=items,
                    total_items=total_items,
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Deleted receivings report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating deleted receivings report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_summary_taxes_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingSummaryTaxesReportRequestWriteDto,
    ) -> Respons[ReceivingsSummaryTaxesReportResponseReadBase]:
        """Get receivings summary taxes report - purchase order items don't typically have tax_id, return empty/placeholder"""
        logger.info("Generating receivings summary taxes report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                where = " AND ".join(conditions)
                cursor.execute(
                    f"""
                    SELECT t.id as tax_id, t.name as tax_name, t.rate as tax_rate,
                        0::numeric as total_taxable_amount, 0::numeric as total_tax_amount, 0::int as transaction_count
                    FROM {db_settings.MSG_TAXES_TABLE} t
                    WHERE t.tenant_id = %s AND t.org_id = %s AND t.bus_id = %s AND t.deleted_by IS NULL
                    """,
                    (tenant_id, org_id, bus_id),
                )
                rows = cursor.fetchall()
                items = []
                for row in rows:
                    items.append(ReceivingTaxItemReadBase(
                        tax_name=row['tax_name'],
                        tax_rate=ReportsService._quantize_decimal(row['tax_rate'] or 0),
                        total_taxable_amount=Decimal('0'),
                        total_tax_amount=Decimal('0'),
                        transaction_count=0,
                    ))
                response = ReceivingsSummaryTaxesReportResponseReadBase(
                    report_type="receivings_summary_taxes",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id},
                    items=items,
                    total_items=len(items),
                    total_amount=Decimal('0'),
                    pagination={},
                )
                return Respons(success=True, detail="Receivings summary taxes report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings summary taxes report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_graphical_taxes_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingGraphicalTaxesReportRequestWriteDto,
    ) -> Respons[ReceivingsGraphicalTaxesReportResponseReadBase]:
        """Get receivings graphical taxes report"""
        logger.info("Generating receivings graphical taxes report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                where = " AND ".join(conditions)
                cursor.execute(
                    f"""
                    SELECT t.id, t.name as tax_name, t.rate as tax_rate,
                        0::numeric as total_taxable_amount, 0::numeric as total_tax_amount, 0::int as transaction_count
                    FROM {db_settings.MSG_TAXES_TABLE} t
                    WHERE t.tenant_id = %s AND t.org_id = %s AND t.bus_id = %s AND t.deleted_by IS NULL
                    """,
                    (tenant_id, org_id, bus_id),
                )
                rows = cursor.fetchall()
                graph_data = []
                for row in rows:
                    graph_data.append(ReceivingTaxItemReadBase(
                        tax_name=row['tax_name'],
                        tax_rate=ReportsService._quantize_decimal(row['tax_rate'] or 0),
                        total_taxable_amount=Decimal('0'),
                        total_tax_amount=Decimal('0'),
                        transaction_count=0,
                    ))
                response = ReceivingsGraphicalTaxesReportResponseReadBase(
                    report_type="receivings_graphical_taxes",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id},
                    graph_data=graph_data,
                    chart_type="bar",
                    metadata={},
                )
                return Respons(success=True, detail="Receivings graphical taxes report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings graphical taxes report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_cheapest_supplier_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: CheapestSupplierReportRequestWriteDto,
    ) -> Respons[CheapestSupplierReportResponseReadBase]:
        """Get cheapest supplier per product report"""
        logger.info("Generating cheapest supplier report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["poi.tenant_id = %s", "poi.org_id = %s", "poi.bus_id = %s", "po.status NOT IN ('CANCELLED', 'DRAFT')"]
                params = [tenant_id, org_id, bus_id]
                product_ids = data.product_ids or []
                if data.product_id:
                    product_ids = [data.product_id] if not product_ids else product_ids
                if product_ids:
                    placeholders = ','.join(['%s'] * len(product_ids))
                    conditions.append(f"poi.product_id IN ({placeholders})")
                    params.extend(product_ids)
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    WITH supplier_agg AS (
                        SELECT poi.product_id, po.supplier_id,
                            AVG(poi.cost_price) as average_cost,
                            COUNT(*) as purchase_count,
                            SUM(poi.qty_received) as total_quantity
                        FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi
                        INNER JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po ON poi.purchase_order_id = po.id AND poi.tenant_id = po.tenant_id AND poi.org_id = po.org_id AND poi.bus_id = po.bus_id
                        WHERE {where}
                        GROUP BY poi.product_id, po.supplier_id
                        HAVING COUNT(*) >= %s
                    ),
                    ranked AS (
                        SELECT product_id, supplier_id, average_cost, purchase_count, total_quantity,
                            ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY average_cost ASC) as rn
                        FROM supplier_agg
                    )
                    SELECT r.product_id, p.name as product_name, s.id as supplier_id, s.fullname as supplier_name,
                        r.average_cost, r.purchase_count, r.total_quantity
                    FROM ranked r
                    INNER JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON r.product_id = p.id AND p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s
                    INNER JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON r.supplier_id = s.id AND s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s
                    WHERE r.rn = 1
                    ORDER BY p.name
                    """,
                    tuple(params) + (data.min_purchases, tenant_id, org_id, bus_id, tenant_id, org_id, bus_id),
                )
                rows = cursor.fetchall()
                items = []
                for row in rows:
                    items.append(CheapestSupplierItemReadBase(
                        product_id=row['product_id'],
                        product_name=row['product_name'],
                        supplier_id=row['supplier_id'],
                        supplier_name=row['supplier_name'],
                        average_cost=ReportsService._quantize_decimal(row['average_cost']),
                        purchase_count=int(row['purchase_count']),
                        total_quantity=ReportsService._quantize_decimal(row['total_quantity']),
                    ))
                response = CheapestSupplierReportResponseReadBase(
                    report_type="cheapest_supplier",
                    report_format="DETAILED",
                    generated_at=datetime.now(),
                    period_start=None,
                    period_end=None,
                    filters_applied={"product_id": data.product_id, "product_ids": data.product_ids, "min_purchases": data.min_purchases},
                    items=items,
                    total_items=len(items),
                    total_amount=None,
                    pagination={},
                )
                return Respons(success=True, detail="Cheapest supplier report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating cheapest supplier report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_items_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingItemsGraphicalReportRequestWriteDto,
    ) -> Respons[ReceivingsItemsGraphicalReportResponseReadBase]:
        """Get receivings items graphical report"""
        logger.info("Generating receivings items graphical report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                where = " AND ".join(conditions)
                date_expr = "TO_CHAR(po.order_date, 'YYYY-MM')" if data.group_by in ('MONTH', 'YEAR') else "poi.product_id"
                group_col = "TO_CHAR(po.order_date, 'YYYY-MM')" if data.group_by in ('MONTH', 'YEAR') else "p.name"
                order_col = "TO_CHAR(po.order_date, 'YYYY-MM')" if data.group_by in ('MONTH', 'YEAR') else "total_value DESC"

                cursor.execute(
                    f"""
                    SELECT {group_col} as label,
                        COALESCE(SUM(poi.qty_received * poi.cost_price), 0) as total_value,
                        COALESCE(SUM(poi.qty_received), 0) as total_qty
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON poi.product_id = p.id AND poi.tenant_id = p.tenant_id AND poi.org_id = p.org_id AND poi.bus_id = p.bus_id
                    WHERE {where}
                    GROUP BY {group_col}
                    ORDER BY {order_col}
                    LIMIT 50
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                graph_data = []
                for row in rows:
                    graph_data.append(GraphDataPointReadBase(
                        label=str(row['label'] or 'Unknown'),
                        value=ReportsService._quantize_decimal(row['total_value']),
                        category=str(row['label']),
                        date=None,
                    ))
                response = ReceivingsItemsGraphicalReportResponseReadBase(
                    report_type="receivings_items_graphical",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "group_by": data.group_by},
                    graph_data=graph_data,
                    chart_type="bar",
                    metadata={},
                )
                return Respons(success=True, detail="Receivings items graphical report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings items graphical report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_items_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingItemsSummaryReportRequestWriteDto,
    ) -> Respons[ReceivingsItemsSummaryReportResponseReadBase]:
        """Get receivings items summary report"""
        logger.info("Generating receivings items summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                if data.product_id:
                    conditions.append("poi.product_id = %s")
                    params.append(data.product_id)
                where = " AND ".join(conditions)
                if data.group_by == 'PRODUCT':
                    select_col = "poi.product_id, p.name as product_name"
                    group_col = "poi.product_id, p.name"
                else:
                    select_col = "TO_CHAR(po.order_date, 'YYYY-MM') as product_name, NULL::text as product_id"
                    group_col = "TO_CHAR(po.order_date, 'YYYY-MM')"

                cursor.execute(
                    f"""
                    SELECT {select_col},
                        COUNT(DISTINCT po.id) as sale_count,
                        COALESCE(SUM(poi.qty_received), 0) as total_quantity,
                        COALESCE(SUM(poi.qty_received * poi.cost_price), 0) as total_revenue
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON poi.product_id = p.id AND poi.tenant_id = p.tenant_id AND poi.org_id = p.org_id AND poi.bus_id = p.bus_id
                    WHERE {where}
                    GROUP BY {group_col}
                    ORDER BY total_revenue DESC
                    LIMIT 100
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                summary_items = []
                for row in rows:
                    sale_count = int(row['sale_count'] or 0)
                    total_qty = ReportsService._quantize_decimal(row['total_quantity'] or 0)
                    total_rev = ReportsService._quantize_decimal(row['total_revenue'] or 0)
                    product_id = row.get('product_id') or ''
                    product_name = row.get('product_name') or 'Unknown'
                    summary_items.append(SummaryItemReadBase(
                        product_id=product_id,
                        product_name=product_name,
                        sale_count=sale_count,
                        total_quantity=total_qty,
                        total_revenue=total_rev,
                    ))
                response = ReceivingsItemsSummaryReportResponseReadBase(
                    report_type="receivings_items_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "product_id": data.product_id, "group_by": data.group_by},
                    summary_items=summary_items,
                    total_items=len(summary_items),
                    totals={"total_quantity": sum(i.total_quantity for i in summary_items), "total_revenue": sum(i.total_revenue for i in summary_items)},
                )
                return Respons(success=True, detail="Receivings items summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings items summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_payments_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingPaymentsGraphicalReportRequestWriteDto,
    ) -> Respons[ReceivingsPaymentsGraphicalReportResponseReadBase]:
        """Get receivings payments graphical report - no purchase payment table, return empty"""
        logger.info("Generating receivings payments graphical report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            response = ReceivingsPaymentsGraphicalReportResponseReadBase(
                report_type="receivings_payments_graphical",
                report_format=data.format,
                generated_at=datetime.now(),
                period_start=data.from_date,
                period_end=data.to_date,
                filters_applied={"supplier_id": data.supplier_id, "group_by": data.group_by},
                graph_data=[],
                chart_type="line",
                metadata={"note": "Purchase order payments are not tracked in the current schema"},
            )
            return Respons(success=True, detail="Receivings payments graphical report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings payments graphical report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_payments_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingPaymentsSummaryReportRequestWriteDto,
    ) -> Respons[ReceivingsPaymentsSummaryReportResponseReadBase]:
        """Get receivings payments summary report - no purchase payment table, return empty"""
        logger.info("Generating receivings payments summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            response = ReceivingsPaymentsSummaryReportResponseReadBase(
                report_type="receivings_payments_summary",
                report_format=data.format,
                generated_at=datetime.now(),
                period_start=data.from_date,
                period_end=data.to_date,
                filters_applied={"supplier_id": data.supplier_id, "payment_method": data.payment_method},
                summary_items=[],
                total_items=0,
                totals={"total_amount": 0, "total_payments": 0},
            )
            return Respons(success=True, detail="Receivings payments summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings payments summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_receivings_payments_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: ReceivingPaymentsDetailedReportRequestWriteDto,
    ) -> Respons[ReceivingsPaymentsDetailedReportResponseReadBase]:
        """Get receivings payments detailed report - no purchase payment table, return empty"""
        logger.info("Generating receivings payments detailed report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            response = ReceivingsPaymentsDetailedReportResponseReadBase(
                report_type="receivings_payments_detailed",
                report_format=data.format,
                generated_at=datetime.now(),
                period_start=data.from_date,
                period_end=data.to_date,
                filters_applied={"supplier_id": data.supplier_id, "payment_method": data.payment_method},
                items=[],
                total_items=0,
                total_amount=Decimal('0'),
                pagination={"page": data.page, "size": data.size, "total": 0},
            )
            return Respons(success=True, detail="Receivings payments detailed report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating receivings payments detailed report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    # =====================================================
    # 11. SUPPLIER REPORTS
    # =====================================================

    @staticmethod
    def get_suppliers_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersGraphicalReportRequestWriteDto,
    ) -> Respons[SuppliersGraphicalReportResponseReadBase]:
        """Get suppliers graphical report"""
        logger.info("Generating suppliers graphical report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, None, None
                )
                where = " AND ".join(conditions)
                if data.metric == 'revenue':
                    val_expr = "COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0)"
                elif data.metric == 'quantity':
                    val_expr = "COALESCE(SUM(poi.qty_ordered), 0)"
                else:
                    val_expr = "COUNT(DISTINCT po.id)"

                cursor.execute(
                    f"""
                    SELECT s.fullname as label, s.id as category, {val_expr} as value
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    INNER JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON po.supplier_id = s.id AND po.tenant_id = s.tenant_id AND po.org_id = s.org_id AND po.bus_id = s.bus_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    WHERE {where}
                    GROUP BY s.id, s.fullname
                    ORDER BY value DESC
                    LIMIT 50
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                graph_data = []
                for row in rows:
                    graph_data.append(GraphDataPointReadBase(
                        label=row['label'] or 'Unknown',
                        value=ReportsService._quantize_decimal(row['value']),
                        category=row['category'],
                        date=None,
                    ))
                response = SuppliersGraphicalReportResponseReadBase(
                    report_type="suppliers_graphical",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"group_by": data.group_by, "metric": data.metric},
                    graph_data=graph_data,
                    chart_type="bar",
                    metadata={},
                )
                return Respons(success=True, detail="Suppliers graphical report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers graphical report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suppliers_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersSummaryReportRequestWriteDto,
    ) -> Respons[SuppliersSummaryReportResponseReadBase]:
        """Get suppliers summary report"""
        logger.info("Generating suppliers summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                join_extra = ["po.tenant_id = s.tenant_id", "po.org_id = s.org_id", "po.bus_id = s.bus_id"]
                join_params = []
                if data.from_date:
                    join_extra.append("po.order_date >= %s")
                    join_params.append(data.from_date)
                if data.to_date:
                    join_extra.append("po.order_date <= %s")
                    join_params.append(data.to_date)
                if data.supplier_id:
                    join_extra.append("po.supplier_id = %s")
                    join_params.append(data.supplier_id)
                join_clause = " AND ".join(join_extra)
                having_parts = []
                having_params = []
                if data.min_purchases is not None:
                    having_parts.append("COUNT(DISTINCT po.id) >= %s")
                    having_params.append(data.min_purchases)
                if data.min_amount is not None:
                    having_parts.append("COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) >= %s")
                    having_params.append(data.min_amount)
                having = " HAVING " + " AND ".join(having_parts) if having_parts else ""

                cursor.execute(
                    f"""
                    SELECT s.id as supplier_id, s.fullname as supplier_name,
                        COUNT(DISTINCT po.id) as total_purchases,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COALESCE(SUM(poi.qty_ordered), 0) as total_items_purchased,
                        MAX(po.order_date) as last_purchase_date
                    FROM {db_settings.MSG_SUPPLIERS_TABLE} s
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po ON s.id = po.supplier_id AND {join_clause}
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND poi.tenant_id = po.tenant_id AND poi.org_id = po.org_id AND poi.bus_id = po.bus_id
                    WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.delete_status = 'NOT_DELETED'
                    GROUP BY s.id, s.fullname
                    {having}
                    ORDER BY total_amount DESC
                    """,
                    tuple(join_params) + (tenant_id, org_id, bus_id) + tuple(having_params),
                )
                rows = cursor.fetchall()
                summary_items = []
                for row in rows:
                    lp = row['last_purchase_date']
                    lp_date = lp.date() if lp and hasattr(lp, 'date') else lp
                    total_purchases = int(row['total_purchases'] or 0)
                    avg_val = (ReportsService._quantize_decimal(row['total_amount']) / total_purchases) if total_purchases else Decimal('0')
                    summary_items.append(SupplierSummaryItemReadBase(
                        supplier_id=row['supplier_id'],
                        supplier_name=row['supplier_name'],
                        total_purchases=total_purchases,
                        total_amount=ReportsService._quantize_decimal(row['total_amount'] or 0),
                        total_items_purchased=ReportsService._quantize_decimal(row['total_items_purchased'] or 0),
                        average_order_value=ReportsService._quantize_decimal(avg_val),
                        last_purchase_date=lp_date,
                        on_time_delivery_rate=None,
                    ))
                response = SuppliersSummaryReportResponseReadBase(
                    report_type="suppliers_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "min_purchases": data.min_purchases, "min_amount": data.min_amount},
                    summary_items=summary_items,
                    total_items=len(summary_items),
                    totals={"total_suppliers": len(summary_items)},
                )
                return Respons(success=True, detail="Suppliers summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suppliers_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersDetailedReportRequestWriteDto,
    ) -> Respons[SuppliersDetailedReportResponseReadBase]:
        """Get suppliers detailed report"""
        logger.info("Generating suppliers detailed report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions = ["s.tenant_id = %s", "s.org_id = %s", "s.bus_id = %s", "s.delete_status = 'NOT_DELETED'"]
                params = [tenant_id, org_id, bus_id]
                if not data.include_inactive:
                    conditions.append("s.is_active = true")
                if data.supplier_id:
                    conditions.append("s.id = %s")
                    params.append(data.supplier_id)
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT s.id as supplier_id, s.fullname as supplier_name, s.contact, s.email, s.address,
                        COUNT(DISTINCT po.id) as total_orders,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_spent,
                        COALESCE(SUM(poi.qty_ordered), 0) as total_items,
                        MIN(po.order_date) as first_order_date,
                        MAX(po.order_date) as last_order_date
                    FROM {db_settings.MSG_SUPPLIERS_TABLE} s
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDERS_TABLE} po ON s.id = po.supplier_id AND s.tenant_id = po.tenant_id AND s.org_id = po.org_id AND s.bus_id = po.bus_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND poi.tenant_id = po.tenant_id AND poi.org_id = po.org_id AND poi.bus_id = po.bus_id
                    WHERE {where}
                    GROUP BY s.id, s.fullname, s.contact, s.email, s.address
                    ORDER BY total_spent DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {db_settings.MSG_SUPPLIERS_TABLE} s WHERE {where}",
                    tuple(params),
                )
                total_items = cursor.fetchone()['cnt']
                items = []
                for row in rows:
                    total_orders = int(row['total_orders'] or 0)
                    avg_val = (ReportsService._quantize_decimal(row['total_spent']) / total_orders) if total_orders else Decimal('0')
                    items.append(SupplierDetailedItemReadBase(
                        supplier_id=row['supplier_id'],
                        supplier_name=row['supplier_name'],
                        contact=row['contact'],
                        email=row['email'],
                        address=row['address'],
                        total_orders=total_orders,
                        total_spent=ReportsService._quantize_decimal(row['total_spent'] or 0),
                        total_items=ReportsService._quantize_decimal(row['total_items'] or 0),
                        first_order_date=row['first_order_date'].date() if row['first_order_date'] and hasattr(row['first_order_date'], 'date') else row['first_order_date'],
                        last_order_date=row['last_order_date'].date() if row['last_order_date'] and hasattr(row['last_order_date'], 'date') else row['last_order_date'],
                        average_order_value=ReportsService._quantize_decimal(avg_val),
                    ))
                total_amount = sum(i.total_spent for i in items)
                response = SuppliersDetailedReportResponseReadBase(
                    report_type="suppliers_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "include_inactive": data.include_inactive},
                    items=items,
                    total_items=total_items,
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Suppliers detailed report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers detailed report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suppliers_summary_items_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersSummaryItemsReportRequestWriteDto,
    ) -> Respons[SuppliersSummaryItemsReportResponseReadBase]:
        """Get suppliers summary items report"""
        logger.info("Generating suppliers summary items report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                if data.product_id:
                    conditions.append("poi.product_id = %s")
                    params.append(data.product_id)
                where = " AND ".join(conditions)

                cursor.execute(
                    f"""
                    SELECT p.id as product_id, p.name as product_name,
                        COUNT(DISTINCT po.id) as sale_count,
                        COALESCE(SUM(poi.qty_ordered), 0) as total_quantity,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_revenue
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p ON poi.product_id = p.id AND poi.tenant_id = p.tenant_id AND poi.org_id = p.org_id AND poi.bus_id = p.bus_id
                    WHERE {where}
                    GROUP BY p.id, p.name
                    ORDER BY total_revenue DESC
                    LIMIT 100
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                summary_items = []
                for row in rows:
                    summary_items.append(SummaryItemReadBase(
                        product_id=row['product_id'] or '',
                        product_name=row['product_name'] or 'Unknown',
                        sale_count=int(row['sale_count'] or 0),
                        total_quantity=ReportsService._quantize_decimal(row['total_quantity'] or 0),
                        total_revenue=ReportsService._quantize_decimal(row['total_revenue'] or 0),
                    ))
                response = SuppliersSummaryItemsReportResponseReadBase(
                    report_type="suppliers_summary_items",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "product_id": data.product_id},
                    summary_items=summary_items,
                    total_items=len(summary_items),
                    totals={"total_quantity": sum(i.total_quantity for i in summary_items), "total_revenue": sum(i.total_revenue for i in summary_items)},
                )
                return Respons(success=True, detail="Suppliers summary items report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers summary items report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suppliers_receivings_graphical_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersGraphicalReceivingsReportRequestWriteDto,
    ) -> Respons[SuppliersReceivingsGraphicalReportResponseReadBase]:
        """Get suppliers receivings graphical report"""
        logger.info("Generating suppliers receivings graphical report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                where = " AND ".join(conditions)
                group_expr = "TO_CHAR(po.order_date, 'YYYY-MM')" if data.group_by in ('MONTH', 'YEAR') else "s.fullname"
                cursor.execute(
                    f"""
                    SELECT {group_expr} as label, COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as value
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    INNER JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON po.supplier_id = s.id AND po.tenant_id = s.tenant_id AND po.org_id = s.org_id AND po.bus_id = s.bus_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND poi.tenant_id = po.tenant_id AND poi.org_id = po.org_id AND poi.bus_id = poi.bus_id
                    WHERE {where}
                    GROUP BY {group_expr}
                    ORDER BY value DESC
                    LIMIT 50
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                graph_data = [GraphDataPointReadBase(label=str(r['label'] or 'Unknown'), value=ReportsService._quantize_decimal(r['value']), category=str(r['label']), date=None) for r in rows]
                response = SuppliersReceivingsGraphicalReportResponseReadBase(
                    report_type="suppliers_receivings_graphical",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id, "group_by": data.group_by},
                    graph_data=graph_data,
                    chart_type="line",
                    metadata={},
                )
                return Respons(success=True, detail="Suppliers receivings graphical report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers receivings graphical report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suppliers_receivings_summary_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersSummaryReceivingsReportRequestWriteDto,
    ) -> Respons[SuppliersReceivingsSummaryReportResponseReadBase]:
        """Get suppliers receivings summary report"""
        logger.info("Generating suppliers receivings summary report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                where = " AND ".join(conditions)
                cursor.execute(
                    f"""
                    SELECT COUNT(DISTINCT po.id) as total_receivings,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COALESCE(SUM(poi.qty_ordered), 0) as total_items_received
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    WHERE {where}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
                total_receivings = int(row['total_receivings'] or 0)
                total_amount = ReportsService._quantize_decimal(row['total_amount'] or 0)
                total_items_received = ReportsService._quantize_decimal(row['total_items_received'] or 0)
                avg_value = (total_amount / total_receivings) if total_receivings > 0 else Decimal('0')
                summary_item = ReceivingSummaryItemReadBase(
                    total_receivings=total_receivings,
                    total_amount=total_amount,
                    total_items_received=total_items_received,
                    average_receiving_value=ReportsService._quantize_decimal(avg_value),
                    receivings_by_status={},
                    receivings_by_supplier={},
                )
                response = SuppliersReceivingsSummaryReportResponseReadBase(
                    report_type="suppliers_receivings_summary",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id},
                    summary_items=[summary_item],
                    total_items=1,
                    totals={"total_receivings": total_receivings, "total_amount": float(total_amount)},
                )
                return Respons(success=True, detail="Suppliers receivings summary report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers receivings summary report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suppliers_receivings_detailed_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersDetailedReceivingsReportRequestWriteDto,
    ) -> Respons[SuppliersReceivingsDetailedReportResponseReadBase]:
        """Get suppliers receivings detailed report"""
        logger.info("Generating suppliers receivings detailed report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            with DatabaseManager.transaction() as cursor:
                conditions, params = ReportsService._get_po_base_conditions(
                    tenant_id, org_id, bus_id, data.from_date, data.to_date, data.supplier_id, None
                )
                where = " AND ".join(conditions)
                offset = (data.page - 1) * data.size

                cursor.execute(
                    f"""
                    SELECT po.id as purchase_order_id, po.po_number, po.order_date as receiving_date,
                        s.fullname as supplier_name,
                        COALESCE(SUM(poi.qty_ordered * poi.cost_price), 0) as total_amount,
                        COUNT(DISTINCT poi.id) as items_count,
                        po.status,
                        (SELECT COUNT(*) FROM {db_settings.MSG_PURCHASE_RECEIPTS_TABLE} pr WHERE pr.purchase_order_id = po.id AND pr.tenant_id = po.tenant_id AND pr.org_id = po.org_id AND pr.bus_id = po.bus_id) as batches_created
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} s ON po.supplier_id = s.id AND po.tenant_id = s.tenant_id AND po.org_id = s.org_id AND po.bus_id = s.bus_id
                    LEFT JOIN {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE} poi ON po.id = poi.purchase_order_id AND po.tenant_id = poi.tenant_id AND po.org_id = poi.org_id AND po.bus_id = poi.bus_id
                    WHERE {where}
                    GROUP BY po.id, po.po_number, po.order_date, s.fullname, po.status
                    ORDER BY po.order_date DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params) + (data.size, offset),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po WHERE {where}",
                    tuple(params),
                )
                total_items = cursor.fetchone()['cnt']
                items = []
                for row in rows:
                    rec_date = row['receiving_date']
                    if hasattr(rec_date, 'date'):
                        rec_date = rec_date.date()
                    items.append(ReceivingDetailedItemReadBase(
                        purchase_order_id=row['purchase_order_id'],
                        po_number=row['po_number'],
                        receiving_date=rec_date,
                        supplier_name=row['supplier_name'],
                        total_amount=ReportsService._quantize_decimal(row['total_amount']),
                        items_count=int(row['items_count'] or 0),
                        status=row['status'],
                        batches_created=int(row['batches_created'] or 0),
                    ))
                total_amount = sum(i.total_amount for i in items)
                response = SuppliersReceivingsDetailedReportResponseReadBase(
                    report_type="suppliers_receivings_detailed",
                    report_format=data.format,
                    generated_at=datetime.now(),
                    period_start=data.from_date,
                    period_end=data.to_date,
                    filters_applied={"supplier_id": data.supplier_id},
                    items=items,
                    total_items=total_items,
                    total_amount=ReportsService._quantize_decimal(total_amount),
                    pagination={"page": data.page, "size": data.size, "total": total_items},
                )
                return Respons(success=True, detail="Suppliers receivings detailed report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers receivings detailed report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

    @staticmethod
    def get_suppliers_tax_by_payments_report(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        data: SuppliersTaxByPaymentsReportRequestWriteDto,
    ) -> Respons[SuppliersTaxByPaymentsReportResponseReadBase]:
        """Get suppliers tax by payments report - no purchase payment table, return empty"""
        logger.info("Generating suppliers tax by payments report", extra={"extra_fields": {"tenant_id": tenant_id}})
        try:
            response = SuppliersTaxByPaymentsReportResponseReadBase(
                report_type="suppliers_tax_by_payments",
                report_format=data.format,
                generated_at=datetime.now(),
                period_start=data.from_date,
                period_end=data.to_date,
                filters_applied={"supplier_id": data.supplier_id, "payment_method": data.payment_method},
                items=[],
                total_items=0,
                total_amount=Decimal('0'),
                pagination={"page": data.page, "size": data.size, "total": 0},
            )
            return Respons(success=True, detail="Suppliers tax by payments report generated successfully", data=[response])
        except Exception as e:
            logger.error(f"Error generating suppliers tax by payments report: {str(e)}", exc_info=True)
            return Respons(success=False, detail=str(e), error="INTERNAL_ERROR")

