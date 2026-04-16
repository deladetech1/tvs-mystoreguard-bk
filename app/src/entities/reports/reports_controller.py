"""
Reports Controller
API endpoints for all reporting functionality
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import date
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.reports.reports_service import ReportsService
from src.entities.reports.reports_write_dto import *  # noqa: F403
from src.entities.reports.reports_read_dto import *  # noqa: F403
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

reports_router = APIRouter(prefix="/reports", tags=["Reports"])
logger = get_logger("reports_controller")


def check_report_permission(current_user: dict, action: str) -> bool:
    """Check if user has permission for report action"""
    # Check if user has any of the required permissions (OR logic)
    is_authorized = AuthService.has_any_permission(
        user_roles=current_user.data,
        required_permissions=[action]
    )
    if not is_authorized:
        logger.warning(
            f"Report access denied - unauthorized: {action}",
            extra={"extra_fields": {"action": action, "status": "unauthorized"}}
        )
    return is_authorized


# =====================================================
# 1. POPULAR / SALES REPORTS
# =====================================================

@reports_router.get("/popular/summary-items", response_model=Respons[SummaryItemsReportResponseReadBase])
def get_summary_items_report(
    from_date: Optional[date] = Query(None, description="Start date for the report (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date for the report (YYYY-MM-DD)"),
    loc_id: Optional[str] = Query(None, description="Location ID filter"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs"),
    format: str = Query("SUMMARY", description="Report format: SUMMARY, DETAILED, or GRAPHICAL"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    size: int = Query(100, ge=1, le=1000, description="Page size for pagination"),
    group_by: Optional[str] = Query("PRODUCT", description="Group by field: PRODUCT, MONTH, etc."),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get summary items report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = SummaryItemsReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        group_by=group_by,
    )
    
    return ReportsService.get_summary_items_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 2. APPOINTMENT REPORTS
# =====================================================

@reports_router.get("/appointments/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_appointments_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    group_by: Optional[str] = Query("MONTH"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get appointments summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = AppointmentsSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        status=status,
        group_by=group_by,
    )
    
    return ReportsService.get_appointments_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/appointments/detailed", response_model=Respons[AppointmentsDetailedReportResponseReadBase])
def get_appointments_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("DETAILED"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get appointments detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = AppointmentsDetailedReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        status=status,
        customer_id=customer_id,
    )
    
    return ReportsService.get_appointments_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 3. PRODUCT METADATA REPORTS
# =====================================================

@reports_router.get("/product-metadata/graphical", response_model=Respons[ProductMetadataGraphicalReportResponseReadBase])
def get_product_metadata_graphical_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("GRAPHICAL"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    metadata_type: Optional[str] = Query(None),
    group_by: Optional[str] = Query("PRODUCT"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get product metadata graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ProductMetadataGraphicalReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        metadata_type=metadata_type,
        group_by=group_by,
    )
    
    return ReportsService.get_product_metadata_graphical_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/product-metadata/summary", response_model=Respons[ProductMetadataSummaryReportResponseReadBase])
def get_product_metadata_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    metadata_type: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get product metadata summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ProductMetadataSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        metadata_type=metadata_type,
    )
    
    return ReportsService.get_product_metadata_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 4. CUSTOMER REPORTS
# =====================================================

@reports_router.get("/customers/summary", response_model=Respons[CustomersSummaryReportResponseReadBase])
def get_customers_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    group_by: Optional[str] = Query("CUSTOMER"),
    min_purchases: Optional[int] = Query(None),
    min_revenue: Optional[float] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get customers summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = CustomersSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        group_by=group_by,
        min_purchases=min_purchases,
        min_revenue=min_revenue,
    )
    
    return ReportsService.get_customers_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/customers/detailed", response_model=Respons[CustomersDetailedReportResponseReadBase])
def get_customers_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("DETAILED"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    customer_id: Optional[str] = Query(None),
    customer_ids: Optional[List[str]] = Query(None),
    include_inactive: bool = Query(False),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get customers detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = CustomersDetailedReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        customer_id=customer_id,
        customer_ids=customer_ids,
        include_inactive=include_inactive,
    )
    
    return ReportsService.get_customers_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/customers/new", response_model=Respons[NewCustomersReportResponseReadBase])
def get_new_customers_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("DETAILED"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    include_first_purchase: bool = Query(True),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get new customers report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = NewCustomersReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        include_first_purchase=include_first_purchase,
    )
    
    return ReportsService.get_new_customers_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 5. EXPENSE REPORTS
# =====================================================

@reports_router.get("/expenses/summary", response_model=Respons[ExpensesSummaryReportResponseReadBase])
def get_expenses_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    group_by: Optional[str] = Query("MONTH"),
    source: Optional[str] = Query(None),
    used_by: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expenses summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpensesSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        group_by=group_by,
        source=source,
        used_by=used_by,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    
    return ReportsService.get_expenses_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/expenses/detailed", response_model=Respons[ExpensesDetailedReportResponseReadBase])
def get_expenses_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("DETAILED"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    source: Optional[str] = Query(None),
    used_by: Optional[str] = Query(None),
    currency_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expenses detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpensesDetailedReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        source=source,
        used_by=used_by,
        currency_id=currency_id,
    )
    
    return ReportsService.get_expenses_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/expenses/by-source", response_model=Respons[ExpensesBySourceReportResponseReadBase])
def get_expenses_by_source_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    sources: Optional[List[str]] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expenses grouped by source report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpensesBySourceReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        sources=sources,
    )
    
    return ReportsService.get_expenses_by_source_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/expenses/by-user", response_model=Respons[ExpensesByUserReportResponseReadBase])
def get_expenses_by_user_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("DETAILED"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    source: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expenses grouped by user report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpensesByUserReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        source=source,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    
    return ReportsService.get_expenses_by_user_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/expenses/graphical", response_model=Respons[ExpensesGraphicalReportResponseReadBase])
def get_expenses_graphical_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("GRAPHICAL"),
    group_by: Optional[str] = Query("MONTH"),
    source: Optional[str] = Query(None),
    sources: Optional[List[str]] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expenses graphical/chart report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpensesGraphicalReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        group_by=group_by,
        source=source,
        sources=sources,
    )
    
    return ReportsService.get_expenses_graphical_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/expenses/by-location", response_model=Respons[ExpensesByLocationReportResponseReadBase])
def get_expenses_by_location_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    source: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expenses grouped by location report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpensesByLocationReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        source=source,
    )
    
    return ReportsService.get_expenses_by_location_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/expenses/by-period", response_model=Respons[ExpensesByPeriodReportResponseReadBase])
def get_expenses_by_period_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    group_by: Optional[str] = Query("MONTH"),
    source: Optional[str] = Query(None),
    sources: Optional[List[str]] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expenses by period/time series report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpensesByPeriodReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        group_by=group_by,
        source=source,
        sources=sources,
    )
    
    return ReportsService.get_expenses_by_period_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 6. INVENTORY REPORTS
# =====================================================

@reports_router.get("/inventory/low", response_model=Respons[LowInventoryReportResponseReadBase])
def get_low_inventory_report(
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    threshold_percentage: Optional[float] = Query(20, ge=0, le=100),
    include_zero_stock: bool = Query(True),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get low inventory report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = LowInventoryReportRequestWriteDto(
        loc_id=loc_id,
        location_ids=location_ids,
        threshold_percentage=threshold_percentage,
        include_zero_stock=include_zero_stock,
    )
    
    return ReportsService.get_low_inventory_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/inventory/summary", response_model=Respons[InventorySummaryReportResponseReadBase])
def get_inventory_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    include_values: bool = Query(True),
    group_by_location: bool = Query(False),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get inventory summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = InventorySummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        include_values=include_values,
        group_by_location=group_by_location,
    )
    
    return ReportsService.get_inventory_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/inventory/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_inventory_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("DETAILED"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    product_id: Optional[str] = Query(None),
    product_ids: Optional[List[str]] = Query(None),
    include_batches: bool = Query(True),
    min_quantity: Optional[float] = Query(None),
    max_quantity: Optional[float] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get inventory detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = InventoryDetailedReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        product_id=product_id,
        product_ids=product_ids,
        include_batches=include_batches,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )
    
    return ReportsService.get_inventory_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/inventory/count-summary", response_model=Respons[DetailedReportResponseReadBase])
def get_inventory_count_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    count_date: Optional[date] = Query(None),
    include_variance: bool = Query(True),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get inventory count summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = InventoryCountReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        count_date=count_date,
        include_variance=include_variance,
    )
    
    return ReportsService.get_inventory_count_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/inventory/count-detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_inventory_count_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("DETAILED"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    count_date: Optional[date] = Query(None),
    product_id: Optional[str] = Query(None),
    product_ids: Optional[List[str]] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get inventory count detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = InventoryCountDetailedReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        count_date=count_date,
        product_id=product_id,
        product_ids=product_ids,
    )
    
    return ReportsService.get_inventory_count_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/inventory/expiring", response_model=Respons[ExpiringItemsReportResponseReadBase])
def get_expiring_items_report(
    days_ahead: int = Query(30, ge=1),
    loc_id: Optional[str] = Query(None),
    include_expired: bool = Query(False),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expiring items report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ExpiringItemsReportRequestWriteDto(
        days_ahead=days_ahead,
        loc_id=loc_id,
        include_expired=include_expired,
    )
    
    return ReportsService.get_expiring_items_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 7. INVOICE REPORTS
# =====================================================

@reports_router.get("/invoices/summary", response_model=Respons[InvoicesSummaryReportResponseReadBase])
def get_invoices_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    status: Optional[str] = Query(None, description="Filter by invoice status: DRAFT, COMPLETED, PARTIALLY_PAID, OVERDUE, CANCELLED"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get invoices summary report. Returns report_type, report_format, generated_at, period_start, period_end, filters_applied, summary_items (List[InvoiceSummaryItemReadBase]), total_items, totals."""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = InvoicesSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        status=status,
    )
    
    return ReportsService.get_invoices_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/invoices/detailed", response_model=Respons[InvoicesDetailedReportResponseReadBase])
def get_invoices_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get invoices detailed report."""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = InvoicesDetailedReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id, location_ids=location_ids,
        page=page, size=size, customer_id=customer_id, status=status,
        min_amount=min_amount, max_amount=max_amount,
    )
    return ReportsService.get_invoices_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/invoices/aging", response_model=Respons[InvoiceAgingReportResponseReadBase])
def get_invoice_aging_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    include_paid: bool = Query(False),
    customer_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get invoice aging report."""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = InvoiceAgingReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id, location_ids=location_ids,
        page=page, size=size, include_paid=include_paid, customer_id=customer_id,
    )
    return ReportsService.get_invoice_aging_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 8. PAYMENT REPORTS
# =====================================================

@reports_router.get("/payments/summary", response_model=Respons[PaymentsSummaryReportResponseReadBase])
def get_payments_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    payment_method: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter by payment status: SUCCESS, FAILED, PENDING, REFUNDED"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get payments summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = PaymentsSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        payment_method=payment_method,
        status=status,
    )
    return ReportsService.get_payments_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/payments/detailed", response_model=Respons[PaymentsDetailedReportResponseReadBase])
def get_payments_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    payment_method: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sale_id: Optional[str] = Query(None),
    invoice_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get payments detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = PaymentsDetailedReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        page=page,
        size=size,
        payment_method=payment_method,
        status=status,
        sale_id=sale_id,
        invoice_id=invoice_id,
    )
    return ReportsService.get_payments_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/payments/graphical", response_model=Respons[PaymentsGraphicalReportResponseReadBase])
def get_payments_graphical_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    group_by: str = Query("MONTH", description="DAY, WEEK, MONTH, YEAR"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get payments graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = PaymentsGraphicalReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        group_by=group_by,
    )
    return ReportsService.get_payments_graphical_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 9. PRICING RULE REPORTS
# =====================================================

@reports_router.get("/pricing-rules/summary", response_model=Respons[PricingRulesSummaryReportResponseReadBase])
def get_pricing_rules_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get pricing rules summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = PricingRulesSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
    )
    return ReportsService.get_pricing_rules_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/pricing-rules/detailed", response_model=Respons[PricingRulesDetailedReportResponseReadBase])
def get_pricing_rules_detailed_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get pricing rules detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = PricingRulesDetailedReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        page=page,
        size=size,
    )
    return ReportsService.get_pricing_rules_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 10. RECEIVING / PURCHASE REPORTS
# =====================================================

@reports_router.get("/receivings/summary", response_model=Respons[ReceivingsSummaryReportResponseReadBase])
def get_receivings_summary_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None), status: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingSummaryReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id, status=status)
    return ReportsService.get_receivings_summary_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/detailed", response_model=Respons[ReceivingsDetailedReportResponseReadBase])
def get_receivings_detailed_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000),
    supplier_id: Optional[str] = Query(None), purchase_order_id: Optional[str] = Query(None), status: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingDetailedReportRequestWriteDto(from_date=from_date, to_date=to_date, page=page, size=size, supplier_id=supplier_id, purchase_order_id=purchase_order_id, status=status)
    return ReportsService.get_receivings_detailed_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/summary-categories", response_model=Respons[ReceivingsSummaryCategoriesReportResponseReadBase])
def get_receivings_summary_categories_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings summary by categories report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingSummaryCategoriesReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id)
    return ReportsService.get_receivings_summary_categories_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/suspended", response_model=Respons[ReceivingsSuspendedReportResponseReadBase])
def get_suspended_receivings_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suspended receivings report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuspendedReceivingsReportRequestWriteDto(from_date=from_date, to_date=to_date, page=page, size=size)
    return ReportsService.get_suspended_receivings_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/deleted", response_model=Respons[ReceivingsDeletedReportResponseReadBase])
def get_deleted_receivings_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get deleted receivings report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = DeletedReceivingsReportRequestWriteDto(from_date=from_date, to_date=to_date, page=page, size=size)
    return ReportsService.get_deleted_receivings_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/summary-taxes", response_model=Respons[ReceivingsSummaryTaxesReportResponseReadBase])
def get_receivings_summary_taxes_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None), tax_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings summary taxes report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingSummaryTaxesReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id, tax_id=tax_id)
    return ReportsService.get_receivings_summary_taxes_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/graphical-taxes", response_model=Respons[ReceivingsGraphicalTaxesReportResponseReadBase])
def get_receivings_graphical_taxes_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    group_by: str = Query("MONTH"), supplier_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings graphical taxes report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingGraphicalTaxesReportRequestWriteDto(from_date=from_date, to_date=to_date, group_by=group_by, supplier_id=supplier_id)
    return ReportsService.get_receivings_graphical_taxes_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/cheapest-supplier", response_model=Respons[CheapestSupplierReportResponseReadBase])
def get_cheapest_supplier_report(
    product_id: Optional[str] = Query(None), product_ids: Optional[List[str]] = Query(None),
    min_purchases: int = Query(1, ge=1),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get cheapest supplier report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = CheapestSupplierReportRequestWriteDto(product_id=product_id, product_ids=product_ids, min_purchases=min_purchases)
    return ReportsService.get_cheapest_supplier_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/items/graphical", response_model=Respons[ReceivingsItemsGraphicalReportResponseReadBase])
def get_receivings_items_graphical_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    group_by: str = Query("PRODUCT"), supplier_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings items graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingItemsGraphicalReportRequestWriteDto(from_date=from_date, to_date=to_date, group_by=group_by, supplier_id=supplier_id)
    return ReportsService.get_receivings_items_graphical_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/items/summary", response_model=Respons[ReceivingsItemsSummaryReportResponseReadBase])
def get_receivings_items_summary_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None), product_id: Optional[str] = Query(None), group_by: str = Query("PRODUCT"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings items summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingItemsSummaryReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id, product_id=product_id, group_by=group_by)
    return ReportsService.get_receivings_items_summary_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/payments/graphical", response_model=Respons[ReceivingsPaymentsGraphicalReportResponseReadBase])
def get_receivings_payments_graphical_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    group_by: str = Query("MONTH"), supplier_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings payments graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingPaymentsGraphicalReportRequestWriteDto(from_date=from_date, to_date=to_date, group_by=group_by, supplier_id=supplier_id)
    return ReportsService.get_receivings_payments_graphical_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/payments/summary", response_model=Respons[ReceivingsPaymentsSummaryReportResponseReadBase])
def get_receivings_payments_summary_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None), payment_method: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings payments summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingPaymentsSummaryReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id, payment_method=payment_method)
    return ReportsService.get_receivings_payments_summary_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/receivings/payments/detailed", response_model=Respons[ReceivingsPaymentsDetailedReportResponseReadBase])
def get_receivings_payments_detailed_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000),
    supplier_id: Optional[str] = Query(None), payment_method: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings payments detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = ReceivingPaymentsDetailedReportRequestWriteDto(from_date=from_date, to_date=to_date, page=page, size=size, supplier_id=supplier_id, payment_method=payment_method)
    return ReportsService.get_receivings_payments_detailed_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


# =====================================================
# 11. SUPPLIER REPORTS
# =====================================================

@reports_router.get("/suppliers/graphical", response_model=Respons[SuppliersGraphicalReportResponseReadBase])
def get_suppliers_graphical_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    group_by: str = Query("SUPPLIER"), metric: str = Query("revenue"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersGraphicalReportRequestWriteDto(from_date=from_date, to_date=to_date, group_by=group_by, metric=metric)
    return ReportsService.get_suppliers_graphical_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/suppliers/summary", response_model=Respons[SuppliersSummaryReportResponseReadBase])
def get_suppliers_summary_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None), min_purchases: Optional[int] = Query(None), min_amount: Optional[float] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersSummaryReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id, min_purchases=min_purchases, min_amount=min_amount)
    return ReportsService.get_suppliers_summary_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/suppliers/detailed", response_model=Respons[SuppliersDetailedReportResponseReadBase])
def get_suppliers_detailed_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000),
    supplier_id: Optional[str] = Query(None), include_inactive: bool = Query(False),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersDetailedReportRequestWriteDto(from_date=from_date, to_date=to_date, page=page, size=size, supplier_id=supplier_id, include_inactive=include_inactive)
    return ReportsService.get_suppliers_detailed_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/suppliers/summary-items", response_model=Respons[SuppliersSummaryItemsReportResponseReadBase])
def get_suppliers_summary_items_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None), product_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers summary items report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersSummaryItemsReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id, product_id=product_id)
    return ReportsService.get_suppliers_summary_items_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/suppliers/receivings/graphical", response_model=Respons[SuppliersReceivingsGraphicalReportResponseReadBase])
def get_suppliers_receivings_graphical_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None), group_by: str = Query("MONTH"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers receivings graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersGraphicalReceivingsReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id, group_by=group_by)
    return ReportsService.get_suppliers_receivings_graphical_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/suppliers/receivings/summary", response_model=Respons[SuppliersReceivingsSummaryReportResponseReadBase])
def get_suppliers_receivings_summary_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    supplier_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers receivings summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersSummaryReceivingsReportRequestWriteDto(from_date=from_date, to_date=to_date, supplier_id=supplier_id)
    return ReportsService.get_suppliers_receivings_summary_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/suppliers/receivings/detailed", response_model=Respons[SuppliersReceivingsDetailedReportResponseReadBase])
def get_suppliers_receivings_detailed_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000),
    supplier_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers receivings detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersDetailedReceivingsReportRequestWriteDto(from_date=from_date, to_date=to_date, page=page, size=size, supplier_id=supplier_id)
    return ReportsService.get_suppliers_receivings_detailed_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


@reports_router.get("/suppliers/tax-by-payments", response_model=Respons[SuppliersTaxByPaymentsReportResponseReadBase])
def get_suppliers_tax_by_payments_report(
    from_date: Optional[date] = Query(None), to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000),
    supplier_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers tax by payments received report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = SuppliersTaxByPaymentsReportRequestWriteDto(from_date=from_date, to_date=to_date, page=page, size=size, supplier_id=supplier_id)
    return ReportsService.get_suppliers_tax_by_payments_report(
        tenant_id=current_user.data[0].tenant_id, org_id=org_bus_loc["org_id"], bus_id=org_bus_loc["bus_id"], data=data,
    )


# =====================================================
# 12. AFFILIATE REPORTS
# =====================================================

@reports_router.get("/affiliates/summary", response_model=Respons[AffiliatesSummaryReportResponseReadBase])
def get_affiliates_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, INACTIVE, SUSPENDED"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get affiliates summary report."""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = AffiliatesSummaryReportRequestWriteDto(from_date=from_date, to_date=to_date, status=status)
    return ReportsService.get_affiliates_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# 13. OTHER REPORTS (Product Metadata, Product Prices, Pricing Rules, Tax, Tax Rule)
# =====================================================

@reports_router.get("/product-prices/summary", response_model=Respons[ProductPricesSummaryReportResponseReadBase])
def get_product_prices_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("SUMMARY"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    product_id: Optional[str] = Query(None),
    include_price_history: bool = Query(False),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get product prices summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ProductPricesSummaryReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        product_id=product_id,
        include_price_history=include_price_history,
    )
    
    return ReportsService.get_product_prices_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/product-prices/graphical", response_model=Respons[ProductPricesGraphicalReportResponseReadBase])
def get_product_prices_graphical_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    loc_id: Optional[str] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    format: str = Query("GRAPHICAL"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    product_id: Optional[str] = Query(None),
    price_type: str = Query('selling_price', description="Price type: cost_price or selling_price"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get product prices graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ProductPricesGraphicalReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=loc_id,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        product_id=product_id,
        price_type=price_type,
    )
    
    return ReportsService.get_product_prices_graphical_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/tax/summary", response_model=Respons[TaxSummaryReportResponseReadBase])
def get_tax_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    tax_id: Optional[str] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get tax summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = TaxSummaryReportRequestWriteDto(from_date=from_date, to_date=to_date, tax_id=tax_id)
    return ReportsService.get_tax_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/tax-rules/summary", response_model=Respons[TaxRulesSummaryReportResponseReadBase])
def get_tax_rules_summary_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    rule_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get tax rules summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    data = TaxRuleSummaryReportRequestWriteDto(from_date=from_date, to_date=to_date, rule_id=rule_id, is_active=is_active)
    return ReportsService.get_tax_rules_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


# =====================================================
# SALES REPORTS - NEW ENDPOINTS
# =====================================================

@reports_router.get("/sales/product-gross-profit", response_model=Respons[ProductGrossProfitReportResponseReadBase])
def get_product_gross_profit_report(
    from_date: Optional[date] = Query(None, description="Start date for the report (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date for the report (YYYY-MM-DD)"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs to filter by. Can provide multiple values like ?location_ids=loc1&location_ids=loc2&location_ids=loc3"),
    format: str = Query("SUMMARY", description="SUMMARY: one total (or per location); DETAILED: per product; GRAPHICAL: unchanged"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    size: int = Query(100, ge=1, le=1000, description="Page size for pagination"),
    product_ids: Optional[List[str]] = Query(None, description="Filter by list of product IDs. Can provide multiple values like ?product_ids=prod1&product_ids=prod2"),
    min_gross_profit: Optional[float] = Query(None, description="Minimum gross profit filter"),
    min_gross_profit_margin: Optional[float] = Query(None, description="Minimum gross profit margin percentage"),
    group_by_location: bool = Query(False, description="Group results by location"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """
    Get product gross profit report.

    Default SUMMARY returns one rolled-up row (total revenue, cost, gross profit, margins) for the filter.
    Use format=DETAILED for gross profit broken down by product.
    Gross profit = Revenue - Cost of Goods Sold (COGS). Filters: date range, locations, products.
    
    To filter by multiple locations, use: ?location_ids=loc1&location_ids=loc2&location_ids=loc3
    To filter by multiple products, use: ?product_ids=prod1&product_ids=prod2&product_ids=prod3
    """
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ProductGrossProfitReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=None,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        product_id=None,
        product_ids=product_ids,
        min_gross_profit=min_gross_profit,
        min_gross_profit_margin=min_gross_profit_margin,
        group_by_location=group_by_location,
    )
    
    loc_id = org_bus_loc["loc_id"]
    with LogContext("reports", "product_gross_profit", loc_id=loc_id):
        logger.info("Processing product gross profit report request")
        
        service_result = ReportsService.get_product_gross_profit_report(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            data=data,
        )
        return service_result


@reports_router.get("/sales/product-net-profit", response_model=Respons[ProductNetProfitReportResponseReadBase])
def get_product_net_profit_report(
    from_date: Optional[date] = Query(None, description="Start date for the report (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date for the report (YYYY-MM-DD)"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs to filter by. Can provide multiple values like ?location_ids=loc1&location_ids=loc2&location_ids=loc3"),
    format: str = Query("SUMMARY", description="SUMMARY: one total net/gross (or per location); DETAILED: per product"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    size: int = Query(100, ge=1, le=1000, description="Page size for pagination"),
    product_ids: Optional[List[str]] = Query(None, description="Filter by list of product IDs. Can provide multiple values like ?product_ids=prod1&product_ids=prod2"),
    expense_allocation_method: str = Query('revenue', description="Expense allocation method: 'revenue' (proportional to revenue) or 'equal' (equal split)"),
    min_net_profit: Optional[float] = Query(None, description="Minimum net profit filter"),
    min_net_profit_margin: Optional[float] = Query(None, description="Minimum net profit margin percentage"),
    group_by_location: bool = Query(False, description="Group results by location"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """
    Get product net profit report.

    Default SUMMARY returns one rolled-up row: totals after subtracting period expenses (net = gross - expenses).
    Use format=DETAILED for net profit per product with allocated expenses.
    Expenses: revenue-weighted or equal split when using group_by_location with SUMMARY.
    
    To filter by multiple locations, use: ?location_ids=loc1&location_ids=loc2&location_ids=loc3
    To filter by multiple products, use: ?product_ids=prod1&product_ids=prod2&product_ids=prod3
    """
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = ProductNetProfitReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=None,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        product_id=None,
        product_ids=product_ids,
        expense_allocation_method=expense_allocation_method,
        min_net_profit=min_net_profit,
        min_net_profit_margin=min_net_profit_margin,
        group_by_location=group_by_location,
    )
    
    loc_id = org_bus_loc["loc_id"]
    with LogContext("reports", "product_net_profit", loc_id=loc_id):
        logger.info("Processing product net profit report request")
        
        service_result = ReportsService.get_product_net_profit_report(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            data=data,
        )
        return service_result


@reports_router.get("/sales/location-performance", response_model=Respons[LocationPerformanceReportResponseReadBase])
def get_location_performance_report(
    from_date: Optional[date] = Query(None, description="Start date for the report (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date for the report (YYYY-MM-DD)"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs to filter by. Can provide multiple values like ?location_ids=loc1&location_ids=loc2&location_ids=loc3"),
    format: str = Query("GRAPHICAL", description="Report format: SUMMARY, DETAILED, or GRAPHICAL"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    size: int = Query(100, ge=1, le=1000, description="Page size for pagination"),
    metric: str = Query('revenue', description="Metric to compare: 'revenue', 'gross_profit', 'net_profit', 'sales_count'"),
    include_expenses: bool = Query(True, description="Include expenses in net profit calculation"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """
    Get location performance comparison report (graphical representation).
    
    Compares performance metrics across multiple locations:
    - Revenue, Gross Profit, Net Profit, Sales Count
    - Includes expenses in net profit calculation if requested
    - Returns data suitable for bar charts or other graphical representations
    - Filters by date range and list of locations (NOT from header)
    
    To filter by multiple locations, use: ?location_ids=loc1&location_ids=loc2&location_ids=loc3
    """
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    data = LocationPerformanceReportRequestWriteDto(
        from_date=from_date,
        to_date=to_date,
        loc_id=None,
        location_ids=location_ids,
        format=format,
        page=page,
        size=size,
        metric=metric,
        include_expenses=include_expenses,
    )
    
    loc_id = org_bus_loc["loc_id"]
    with LogContext("reports", "location_performance", loc_id=loc_id):
        logger.info("Processing location performance report request")
        
        service_result = ReportsService.get_location_performance_report(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            data=data,
        )
        return service_result


# =====================================================
# RETURNS REPORTS
# =====================================================

@reports_router.get("/returns/summary", response_model=Respons[ReturnsSummaryReportResponseReadBase])
def get_returns_summary_report(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    loc_id: Optional[str] = Query(None, description="Location ID filter"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs"),
    format: str = Query("SUMMARY", description="Report format"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get returns summary report - overall return statistics, return rate, refund totals, restock vs write-off"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")

    data = ReturnsSummaryReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id,
        location_ids=location_ids, format=format, page=page, size=size,
    )
    return ReportsService.get_returns_summary_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/returns/detailed", response_model=Respons[ReturnsDetailedReportResponseReadBase])
def get_returns_detailed_report(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    loc_id: Optional[str] = Query(None, description="Location ID filter"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED, COMPLETED)"),
    reason: Optional[str] = Query(None, description="Filter by reason"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    format: str = Query("DETAILED", description="Report format"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get returns detailed report - individual return records with filters"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")

    data = ReturnsDetailedReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id,
        location_ids=location_ids, status=status, reason=reason,
        customer_id=customer_id, format=format, page=page, size=size,
    )
    return ReportsService.get_returns_detailed_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/returns/by-reason", response_model=Respons[ReturnsByReasonReportResponseReadBase])
def get_returns_by_reason_report(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    loc_id: Optional[str] = Query(None, description="Location ID filter"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs"),
    format: str = Query("SUMMARY", description="Report format"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get returns by reason report - returns grouped by reason with percentages"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")

    data = ReturnsByReasonReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id,
        location_ids=location_ids, format=format, page=page, size=size,
    )
    return ReportsService.get_returns_by_reason_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/returns/by-product", response_model=Respons[ReturnsByProductReportResponseReadBase])
def get_returns_by_product_report(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    loc_id: Optional[str] = Query(None, description="Location ID filter"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs"),
    min_return_rate: Optional[float] = Query(None, description="Minimum return rate percentage to include"),
    format: str = Query("DETAILED", description="Report format"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get return rate by product - which products are returned most and why"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")

    data = ReturnsByProductReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id,
        location_ids=location_ids, min_return_rate=min_return_rate,
        format=format, page=page, size=size,
    )
    return ReportsService.get_returns_by_product_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/returns/write-off", response_model=Respons[ReturnsWriteOffReportResponseReadBase])
def get_returns_write_off_report(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    loc_id: Optional[str] = Query(None, description="Location ID filter"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs"),
    condition: Optional[str] = Query(None, description="Filter by condition (DAMAGED, EXPIRED, OPENED, WRITE_OFF)"),
    format: str = Query("DETAILED", description="Report format"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get returns write-off/inventory loss report - items lost due to returns (expired, damaged, etc.)"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")

    data = ReturnsWriteOffReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id,
        location_ids=location_ids, condition=condition,
        format=format, page=page, size=size,
    )
    return ReportsService.get_returns_write_off_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )


@reports_router.get("/returns/graphical", response_model=Respons[ReturnsGraphicalReportResponseReadBase])
def get_returns_graphical_report(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    loc_id: Optional[str] = Query(None, description="Location ID filter"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs"),
    group_by: Optional[str] = Query("MONTH", description="Group by: DAY, WEEK, MONTH, YEAR"),
    format: str = Query("GRAPHICAL", description="Report format"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get returns graphical report - returns over time for charts"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")

    data = ReturnsGraphicalReportRequestWriteDto(
        from_date=from_date, to_date=to_date, loc_id=loc_id,
        location_ids=location_ids, group_by=group_by,
        format=format, page=page, size=size,
    )
    return ReportsService.get_returns_graphical_report(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        data=data,
    )

