from typing import Optional
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from src.entities.dashboard.dashboard_read_dto import (
    GetDashboardDataServiceReadDto,
    DashboardStatsOverviewReadBase,
    RevenueExpensesChartReadBase,
    RevenueExpenseDataPointReadBase,
    InvoiceStatusDistributionChartReadBase,
    InvoiceStatusDataPointReadBase,
    TopProductsChartReadBase,
    TopProductDataPointReadBase,
    SalesRevenueTrendChartReadBase,
    SalesRevenueTrendDataPointReadBase,
)
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger

logger = get_logger("dashboard_service")


class DashboardService:
    """Service class for dashboard operations"""

    @staticmethod
    def get_dashboard_data(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Respons[GetDashboardDataServiceReadDto]:
        """Get complete dashboard data with all charts and statistics"""
        logger.info(
            f"Processing dashboard data request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "from_date": str(from_date) if from_date else None,
                    "to_date": str(to_date) if to_date else None,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                base_params = [tenant_id, org_id, bus_id, loc_id]

                # =====================================================
                # 1. DASHBOARD STATS OVERVIEW
                # =====================================================

                # Total Sales (from store_sales)
                sales_where_conditions = [
                    "s.tenant_id = %s",
                    "s.org_id = %s",
                    "s.bus_id = %s",
                    "s.loc_id = %s"
                ]
                sales_params = list(base_params)
                if from_date:
                    sales_where_conditions.append("s.sale_date >= %s")
                    sales_params.append(from_date)
                if to_date:
                    sales_where_conditions.append("s.sale_date <= %s")
                    sales_params.append(to_date)
                
                sales_where = " AND ".join(sales_where_conditions)

                cursor.execute(
                    f"""SELECT COUNT(*) as total_sales
                    FROM {db_settings.MSG_SALES_TABLE} s
                    WHERE {sales_where}""",
                    tuple(sales_params),
                )
                total_sales_result = cursor.fetchone()
                total_sales = int(total_sales_result['total_sales']) if total_sales_result else 0

                # Total Revenue (from sales payments + invoice items)
                # Revenue from sales (successful payments)
                cursor.execute(
                    f"""SELECT COALESCE(SUM(p.paid_amount), 0) as total_revenue
                    FROM {db_settings.MSG_SALES_TABLE} s
                    INNER JOIN {db_settings.MSG_SALES_PAYMENTS_TABLE} p 
                        ON s.id = p.sale_id 
                        AND s.tenant_id = p.tenant_id 
                        AND s.org_id = p.org_id 
                        AND s.bus_id = p.bus_id 
                        AND s.loc_id = p.loc_id
                    WHERE {sales_where}
                    AND p.payment_status = 'SUCCESS' 
                    AND p.deleted_at IS NULL""",
                    tuple(sales_params),
                )
                sales_revenue_result = cursor.fetchone()
                sales_revenue = Decimal(str(sales_revenue_result['total_revenue'])) if sales_revenue_result else Decimal('0')

                # Revenue from invoices (sum of line_total from invoice_items)
                invoice_where_conditions = [
                    "i.tenant_id = %s",
                    "i.org_id = %s",
                    "i.bus_id = %s",
                    "i.loc_id = %s"
                ]
                invoice_params = list(base_params)
                if from_date:
                    invoice_where_conditions.append("DATE(i.sale_date) >= DATE(%s)")
                    invoice_params.append(from_date)
                if to_date:
                    invoice_where_conditions.append("DATE(i.sale_date) <= DATE(%s)")
                    invoice_params.append(to_date)
                
                invoice_where = " AND ".join(invoice_where_conditions)

                cursor.execute(
                    f"""SELECT COALESCE(SUM(ii.line_total), 0) as total_revenue
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    INNER JOIN {db_settings.MSG_INVOICE_ITEMS_TABLE} ii
                        ON i.id = ii.invoice_id
                        AND i.tenant_id = ii.tenant_id
                        AND i.org_id = ii.org_id
                        AND i.bus_id = ii.bus_id
                        AND i.loc_id = ii.loc_id
                    WHERE {invoice_where}""",
                    tuple(invoice_params),
                )
                invoice_revenue_result = cursor.fetchone()
                invoice_revenue = Decimal(str(invoice_revenue_result['total_revenue'])) if invoice_revenue_result else Decimal('0')

                total_revenue = sales_revenue + invoice_revenue

                # Total Invoices
                cursor.execute(
                    f"""SELECT COUNT(*) as total_invoices
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    WHERE {invoice_where}""",
                    tuple(invoice_params),
                )
                total_invoices_result = cursor.fetchone()
                total_invoices = int(total_invoices_result['total_invoices']) if total_invoices_result else 0

                # Total Expenses
                expense_where_conditions = [
                    "e.tenant_id = %s",
                    "e.org_id = %s",
                    "e.bus_id = %s",
                    "e.loc_id = %s"
                ]
                expense_params = list(base_params)
                if from_date:
                    expense_where_conditions.append("DATE(e.cdate) >= DATE(%s)")
                    expense_params.append(from_date)
                if to_date:
                    expense_where_conditions.append("DATE(e.cdate) <= DATE(%s)")
                    expense_params.append(to_date)
                
                expense_where = " AND ".join(expense_where_conditions)

                cursor.execute(
                    f"""SELECT COUNT(*) as total_expenses
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {expense_where}
                    AND e.delete_status = 'NOT_DELETED'""",
                    tuple(expense_params),
                )
                total_expenses_result = cursor.fetchone()
                total_expenses = int(total_expenses_result['total_expenses']) if total_expenses_result else 0

                # Total Products
                cursor.execute(
                    f"""SELECT COUNT(*) as total_products
                    FROM {db_settings.MSG_PRODUCTS_TABLE} p
                    WHERE p.tenant_id = %s AND p.org_id = %s AND p.bus_id = %s
                    AND p.delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id),
                )
                total_products_result = cursor.fetchone()
                total_products = int(total_products_result['total_products']) if total_products_result else 0

                # Total Customers
                cursor.execute(
                    f"""SELECT COUNT(*) as total_customers
                    FROM {db_settings.MSG_CUSTOMERS_TABLE} c
                    WHERE c.tenant_id = %s AND c.org_id = %s AND c.bus_id = %s
                    AND c.delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id),
                )
                total_customers_result = cursor.fetchone()
                total_customers = int(total_customers_result['total_customers']) if total_customers_result else 0

                # Total Appointments
                appointment_where_conditions = [
                    "a.tenant_id = %s",
                    "a.org_id = %s",
                    "a.bus_id = %s",
                    "a.loc_id = %s"
                ]
                appointment_params = list(base_params)
                if from_date:
                    appointment_where_conditions.append("DATE(a.start_datetime) >= DATE(%s)")
                    appointment_params.append(from_date)
                if to_date:
                    appointment_where_conditions.append("DATE(a.start_datetime) <= DATE(%s)")
                    appointment_params.append(to_date)
                
                appointment_where = " AND ".join(appointment_where_conditions)

                cursor.execute(
                    f"""SELECT COUNT(*) as total_appointments
                    FROM {db_settings.MSG_APPOINTMENTS_TABLE} a
                    WHERE {appointment_where}""",
                    tuple(appointment_params),
                )
                total_appointments_result = cursor.fetchone()
                total_appointments = int(total_appointments_result['total_appointments']) if total_appointments_result else 0

                # Total Expenses Amount
                cursor.execute(
                    f"""SELECT COALESCE(SUM(amount), 0) as total_expenses_amount
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    WHERE {expense_where}
                    AND e.delete_status = 'NOT_DELETED'""",
                    tuple(expense_params),
                )
                total_expenses_amount_result = cursor.fetchone()
                total_expenses_amount = Decimal(str(total_expenses_amount_result['total_expenses_amount'])) if total_expenses_amount_result else Decimal('0')

                # Gross Profit (Revenue - Expenses)
                gross_profit = total_revenue - total_expenses_amount
                two_places = Decimal('0.01')
                gross_profit = gross_profit.quantize(two_places, rounding=ROUND_HALF_UP)
                total_revenue = total_revenue.quantize(two_places, rounding=ROUND_HALF_UP)
                total_expenses_amount = total_expenses_amount.quantize(two_places, rounding=ROUND_HALF_UP)

                stats_overview = DashboardStatsOverviewReadBase(
                    total_sales=total_sales,
                    total_revenue=total_revenue,
                    total_invoices=total_invoices,
                    total_expenses=total_expenses,
                    total_products=total_products,
                    total_customers=total_customers,
                    total_appointments=total_appointments,
                    gross_profit=gross_profit,
                )

                # =====================================================
                # 2. REVENUE VS EXPENSES CHART (Monthly breakdown)
                # =====================================================

                # Determine date range for grouping
                if from_date and to_date:
                    start_date = from_date
                    end_date = to_date
                elif from_date:
                    start_date = from_date
                    end_date = date.today()
                elif to_date:
                    # If only to_date, go back 12 months
                    start_date = to_date - timedelta(days=365)
                    end_date = to_date
                else:
                    # Default: last 12 months
                    end_date = date.today()
                    start_date = end_date - timedelta(days=365)

                # Generate monthly periods
                revenue_expenses_data = []
                current = start_date.replace(day=1)  # Start of month
                while current <= end_date:
                    period_end = (current + timedelta(days=32)).replace(day=1) - timedelta(days=1)  # End of month
                    if period_end > end_date:
                        period_end = end_date
                    
                    period_str = current.strftime("%Y-%m")

                    # Revenue for this month
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(p.paid_amount), 0) as revenue
                        FROM {db_settings.MSG_SALES_TABLE} s
                        INNER JOIN {db_settings.MSG_SALES_PAYMENTS_TABLE} p 
                            ON s.id = p.sale_id 
                            AND s.tenant_id = p.tenant_id 
                            AND s.org_id = p.org_id 
                            AND s.bus_id = p.bus_id 
                            AND s.loc_id = p.loc_id
                        WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
                        AND s.sale_date >= %s AND s.sale_date <= %s
                        AND p.payment_status = 'SUCCESS' 
                        AND p.deleted_at IS NULL""",
                        (tenant_id, org_id, bus_id, loc_id, current, period_end),
                    )
                    sales_rev_result = cursor.fetchone()
                    sales_rev = Decimal(str(sales_rev_result['revenue'])) if sales_rev_result else Decimal('0')

                    cursor.execute(
                        f"""SELECT COALESCE(SUM(ii.line_total), 0) as revenue
                        FROM {db_settings.MSG_INVOICES_TABLE} i
                        INNER JOIN {db_settings.MSG_INVOICE_ITEMS_TABLE} ii
                            ON i.id = ii.invoice_id
                            AND i.tenant_id = ii.tenant_id
                            AND i.org_id = ii.org_id
                            AND i.bus_id = ii.bus_id
                            AND i.loc_id = ii.loc_id
                        WHERE i.tenant_id = %s AND i.org_id = %s AND i.bus_id = %s AND i.loc_id = %s
                        AND i.sale_date >= %s AND i.sale_date <= %s""",
                        (tenant_id, org_id, bus_id, loc_id, current, period_end),
                    )
                    inv_rev_result = cursor.fetchone()
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(ii.line_total), 0) as revenue
                        FROM {db_settings.MSG_INVOICES_TABLE} i
                        INNER JOIN {db_settings.MSG_INVOICE_ITEMS_TABLE} ii
                            ON i.id = ii.invoice_id
                            AND i.tenant_id = ii.tenant_id
                            AND i.org_id = ii.org_id
                            AND i.bus_id = ii.bus_id
                            AND i.loc_id = ii.loc_id
                        WHERE i.tenant_id = %s AND i.org_id = %s AND i.bus_id = %s AND i.loc_id = %s
                        AND i.sale_date >= %s AND i.sale_date <= %s""",
                        (tenant_id, org_id, bus_id, loc_id, current, period_end),
                    )
                    inv_rev_result = cursor.fetchone()
                    inv_rev = Decimal(str(inv_rev_result['revenue'])) if inv_rev_result else Decimal('0')
                    revenue = (sales_rev + inv_rev).quantize(two_places, rounding=ROUND_HALF_UP)

                    # Expenses for this month
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(e.amount), 0) as expenses
                        FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                        WHERE e.tenant_id = %s AND e.org_id = %s AND e.bus_id = %s AND e.loc_id = %s
                        AND DATE(e.cdate) >= DATE(%s) AND DATE(e.cdate) <= DATE(%s)
                        AND e.delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, loc_id, current, period_end),
                    )
                    exp_result = cursor.fetchone()
                    expenses = Decimal(str(exp_result['expenses'])).quantize(two_places, rounding=ROUND_HALF_UP) if exp_result else Decimal('0')

                    revenue_expenses_data.append(RevenueExpenseDataPointReadBase(
                        period=period_str,
                        revenue=revenue,
                        expenses=expenses,
                    ))

                    # Move to next month
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)

                revenue_expenses_chart = RevenueExpensesChartReadBase(data=revenue_expenses_data)

                # =====================================================
                # 3. INVOICE STATUS DISTRIBUTION CHART (Pie Chart)
                # =====================================================

                cursor.execute(
                    f"""SELECT 
                        status,
                        COUNT(*) as count
                    FROM {db_settings.MSG_INVOICES_TABLE} i
                    WHERE {invoice_where}
                    GROUP BY status""",
                    tuple(invoice_params),
                )
                invoice_status_results = cursor.fetchall()

                # Ensure all statuses are included
                all_statuses = ['COMPLETED', 'DRAFT', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED']
                status_counts = {row['status']: int(row['count']) for row in invoice_status_results}
                total_invoices_for_pie = sum(status_counts.values())

                invoice_status_data = []
                for status in all_statuses:
                    count = status_counts.get(status, 0)
                    percentage = (Decimal(str(count)) / Decimal(str(total_invoices_for_pie)) * Decimal('100')).quantize(two_places, rounding=ROUND_HALF_UP) if total_invoices_for_pie > 0 else Decimal('0')
                    invoice_status_data.append(InvoiceStatusDataPointReadBase(
                        status=status,
                        count=count,
                        percentage=percentage,
                    ))

                invoice_status_chart = InvoiceStatusDistributionChartReadBase(
                    data=invoice_status_data,
                    total=total_invoices_for_pie,
                )

                # =====================================================
                # 4. TOP PRODUCTS CHART (Top 5)
                # =====================================================

                # Get top 5 products by sales amount
                cursor.execute(
                    f"""SELECT 
                        si.product_id,
                        p.name as product_name,
                        COALESCE(SUM(si.line_total), 0) as sales_amount,
                        COALESCE(SUM(si.quantity), 0) as quantity_sold
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
                    WHERE si.tenant_id = %s AND si.org_id = %s AND si.bus_id = %s AND si.loc_id = %s
                    {('AND s.sale_date >= %s' if from_date else '')}
                    {('AND s.sale_date <= %s' if to_date else '')}
                    GROUP BY si.product_id, p.name
                    ORDER BY sales_amount DESC
                    LIMIT 5""",
                    tuple([tenant_id, org_id, bus_id, loc_id] + ([from_date] if from_date else []) + ([to_date] if to_date else [])),
                )
                top_products_results = cursor.fetchall()

                top_products_data = []
                for row in top_products_results:
                    top_products_data.append(TopProductDataPointReadBase(
                        product_id=row['product_id'],
                        product_name=row['product_name'] or 'Unknown Product',
                        sales_amount=Decimal(str(row['sales_amount'])).quantize(two_places, rounding=ROUND_HALF_UP),
                        quantity_sold=Decimal(str(row['quantity_sold'])).quantize(two_places, rounding=ROUND_HALF_UP),
                    ))

                top_products_chart = TopProductsChartReadBase(data=top_products_data)

                # =====================================================
                # 5. SALES & REVENUE TREND CHART (Monthly breakdown)
                # =====================================================

                # Use same date range and monthly grouping as revenue/expenses chart
                sales_revenue_trend_data = []
                current = start_date.replace(day=1)  # Start of month
                while current <= end_date:
                    period_end = (current + timedelta(days=32)).replace(day=1) - timedelta(days=1)  # End of month
                    if period_end > end_date:
                        period_end = end_date
                    
                    period_str = current.strftime("%Y-%m")

                    # Sales count for this month
                    cursor.execute(
                        f"""SELECT COUNT(*) as sales_count
                        FROM {db_settings.MSG_SALES_TABLE} s
                        WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
                        AND s.sale_date >= %s AND s.sale_date <= %s""",
                        (tenant_id, org_id, bus_id, loc_id, current, period_end),
                    )
                    sales_count_result = cursor.fetchone()
                    sales_count = int(sales_count_result['sales_count']) if sales_count_result else 0

                    # Revenue for this month
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(p.paid_amount), 0) as revenue
                        FROM {db_settings.MSG_SALES_TABLE} s
                        INNER JOIN {db_settings.MSG_SALES_PAYMENTS_TABLE} p 
                            ON s.id = p.sale_id 
                            AND s.tenant_id = p.tenant_id 
                            AND s.org_id = p.org_id 
                            AND s.bus_id = p.bus_id 
                            AND s.loc_id = p.loc_id
                        WHERE s.tenant_id = %s AND s.org_id = %s AND s.bus_id = %s AND s.loc_id = %s
                        AND s.sale_date >= %s AND s.sale_date <= %s
                        AND p.payment_status = 'SUCCESS' 
                        AND p.deleted_at IS NULL""",
                        (tenant_id, org_id, bus_id, loc_id, current, period_end),
                    )
                    sales_rev_result = cursor.fetchone()
                    sales_rev = Decimal(str(sales_rev_result['revenue'])) if sales_rev_result else Decimal('0')

                    cursor.execute(
                        f"""SELECT COALESCE(SUM(ii.line_total), 0) as revenue
                        FROM {db_settings.MSG_INVOICES_TABLE} i
                        INNER JOIN {db_settings.MSG_INVOICE_ITEMS_TABLE} ii
                            ON i.id = ii.invoice_id
                            AND i.tenant_id = ii.tenant_id
                            AND i.org_id = ii.org_id
                            AND i.bus_id = ii.bus_id
                            AND i.loc_id = ii.loc_id
                        WHERE i.tenant_id = %s AND i.org_id = %s AND i.bus_id = %s AND i.loc_id = %s
                        AND i.sale_date >= %s AND i.sale_date <= %s""",
                        (tenant_id, org_id, bus_id, loc_id, current, period_end),
                    )
                    inv_rev_result = cursor.fetchone()
                    inv_rev = Decimal(str(inv_rev_result['revenue'])) if inv_rev_result else Decimal('0')
                    revenue = (sales_rev + inv_rev).quantize(two_places, rounding=ROUND_HALF_UP)

                    sales_revenue_trend_data.append(SalesRevenueTrendDataPointReadBase(
                        period=period_str,
                        sales_count=sales_count,
                        revenue=revenue,
                    ))

                    # Move to next month
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)

                sales_revenue_trend_chart = SalesRevenueTrendChartReadBase(data=sales_revenue_trend_data)

                # =====================================================
                # COMPILE COMPLETE DASHBOARD DATA
                # =====================================================

                dashboard_data = GetDashboardDataServiceReadDto(
                    stats_overview=stats_overview,
                    revenue_expenses_chart=revenue_expenses_chart,
                    invoice_status_chart=invoice_status_chart,
                    top_products_chart=top_products_chart,
                    sales_revenue_trend_chart=sales_revenue_trend_chart,
                    from_date=from_date,
                    to_date=to_date,
                )

                logger.info(
                    "Dashboard data retrieved successfully",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "total_sales": total_sales,
                            "total_revenue": str(total_revenue),
                            "total_invoices": total_invoices,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Dashboard data retrieved successfully",
                    data=[dashboard_data],
                )

        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get dashboard data: {str(e)}",
                error="INTERNAL_ERROR",
            )

