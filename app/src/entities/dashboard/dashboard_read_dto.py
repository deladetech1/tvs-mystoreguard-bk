from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from src.entities.dashboard.dashboard_base import DashboardBase


# =====================================================
# DASHBOARD STATS OVERVIEW READ DTOs
# =====================================================

class DashboardStatsOverviewReadBase(BaseModel):
    """Base read DTO for dashboard stats overview"""
    total_sales: int = Field(default=0, description="Total number of sales")
    total_revenue: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Total revenue from sales and invoices")
    total_invoices: int = Field(default=0, description="Total number of invoices")
    total_expenses: int = Field(default=0, description="Total number of expenses")
    total_products: int = Field(default=0, description="Total number of products")
    total_customers: int = Field(default=0, description="Total number of customers")
    total_appointments: int = Field(default=0, description="Total number of appointments")
    gross_profit: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Gross profit (Revenue - Expenses)")


# =====================================================
# REVENUE VS EXPENSES CHART READ DTOs
# =====================================================

class RevenueExpenseDataPointReadBase(BaseModel):
    """Base read DTO for revenue vs expense data point"""
    period: str = Field(..., description="Time period (e.g., '2024-01', '2024-01-15')")
    revenue: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Revenue for this period")
    expenses: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Expenses for this period")


class RevenueExpensesChartReadBase(BaseModel):
    """Base read DTO for revenue vs expenses chart"""
    data: List[RevenueExpenseDataPointReadBase] = Field(default_factory=list, description="List of data points")


# =====================================================
# INVOICE STATUS DISTRIBUTION CHART READ DTOs
# =====================================================

class InvoiceStatusDataPointReadBase(BaseModel):
    """Base read DTO for invoice status data point"""
    status: str = Field(..., description="Invoice status (COMPLETED, DRAFT, PARTIALLY_PAID, OVERDUE, CANCELLED)")
    count: int = Field(default=0, description="Number of invoices with this status")
    percentage: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Percentage of total invoices")


class InvoiceStatusDistributionChartReadBase(BaseModel):
    """Base read DTO for invoice status distribution chart"""
    data: List[InvoiceStatusDataPointReadBase] = Field(default_factory=list, description="List of status data points")
    total: int = Field(default=0, description="Total number of invoices")


# =====================================================
# TOP PRODUCTS CHART READ DTOs
# =====================================================

class TopProductDataPointReadBase(BaseModel):
    """Base read DTO for top product data point"""
    product_id: str = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    sales_amount: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Total sales amount for this product")
    quantity_sold: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Total quantity sold")


class TopProductsChartReadBase(BaseModel):
    """Base read DTO for top products chart"""
    data: List[TopProductDataPointReadBase] = Field(default_factory=list, description="List of top 5 products")


# =====================================================
# SALES & REVENUE TREND CHART READ DTOs
# =====================================================

class SalesRevenueTrendDataPointReadBase(BaseModel):
    """Base read DTO for sales & revenue trend data point"""
    period: str = Field(..., description="Time period (e.g., '2024-01', '2024-01-15')")
    sales_count: int = Field(default=0, description="Number of sales in this period")
    revenue: Decimal = Field(default=Decimal('0'), decimal_places=2, description="Revenue in this period")


class SalesRevenueTrendChartReadBase(BaseModel):
    """Base read DTO for sales & revenue trend chart"""
    data: List[SalesRevenueTrendDataPointReadBase] = Field(default_factory=list, description="List of trend data points")


# =====================================================
# COMPLETE DASHBOARD DATA READ DTOs
# =====================================================

class DashboardDataReadBase(BaseModel):
    """Base read DTO for complete dashboard data"""
    stats_overview: DashboardStatsOverviewReadBase = Field(..., description="Dashboard statistics overview")
    revenue_expenses_chart: RevenueExpensesChartReadBase = Field(..., description="Revenue vs Expenses chart data")
    invoice_status_chart: InvoiceStatusDistributionChartReadBase = Field(..., description="Invoice status distribution chart data")
    top_products_chart: TopProductsChartReadBase = Field(..., description="Top products chart data")
    sales_revenue_trend_chart: SalesRevenueTrendChartReadBase = Field(..., description="Sales & Revenue trend chart data")
    from_date: Optional[date] = Field(None, description="Filter start date")
    to_date: Optional[date] = Field(None, description="Filter end date")


class GetDashboardDataControllerReadDto(DashboardDataReadBase):
    """Controller DTO for get dashboard data read operations"""
    pass


class GetDashboardDataServiceReadDto(DashboardDataReadBase):
    """Service DTO for get dashboard data read operations"""
    pass

