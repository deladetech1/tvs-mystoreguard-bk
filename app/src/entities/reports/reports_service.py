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
                    tenant_id, org_id, bus_id, data.loc_id, data.location_ids
                )
                conditions.append("sp.delete_status = 'NOT_DELETED'")
                base_where = " AND ".join(conditions)

                # Get products with low stock
                # Note: This assumes a minimum threshold field exists or needs to be calculated
                query = f"""
                    SELECT 
                        sp.product_id,
                        p.name as product_name,
                        p.sku,
                        sp.current_qty,
                        sp.loc_id,
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
                    AND (sp.current_qty <= 0 OR sp.current_qty <= COALESCE((SELECT AVG(current_qty) * %s / 100 FROM {db_settings.MSG_STORE_PRODUCTS_TABLE} WHERE product_id = sp.product_id AND tenant_id = sp.tenant_id), 0))
                    ORDER BY sp.current_qty ASC
                """
                
                params.append(data.threshold_percentage)
                if not data.include_zero_stock:
                    query = query.replace("AND (sp.current_qty <= 0 OR", "AND (")
                
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                items = []
                for row in results:
                    current_qty = Decimal(str(row.get('current_qty', 0)))
                    minimum_threshold = Decimal(str(current_qty)) * Decimal(str(100 + data.threshold_percentage)) / Decimal('100')
                    reorder_suggestion = minimum_threshold - current_qty if current_qty < minimum_threshold else Decimal('0')
                    
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
                # Include location fields if grouping by location OR if filtering by a single location
                single_location = (data.location_ids and len(data.location_ids) == 1)
                if data.group_by_location:
                    group_by_clause += ", s.loc_id, l.loc_name"
                    location_select = ",\n                        s.loc_id,\n                        l.loc_name as location_name"
                elif single_location:
                    # When filtering by single location but not grouping, include location in SELECT but not GROUP BY
                    # Use MAX() or MIN() to satisfy SQL requirements since we know all rows have the same location
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
                # Include location fields if grouping by location OR if filtering by a single location
                single_location = (data.location_ids and len(data.location_ids) == 1)
                if data.group_by_location:
                    group_by_clause += ", s.loc_id, l.loc_name"
                    location_select = ",\n                        s.loc_id,\n                        l.loc_name as location_name"
                elif single_location:
                    # When filtering by single location but not grouping, include location in SELECT but not GROUP BY
                    # Use MAX() or MIN() to satisfy SQL requirements since we know all rows have the same location
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

