"""
Reports Controller
API endpoints for all reporting functionality
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import date
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.reports.reports_service import ReportsService
from src.entities.reports.reports_write_dto import *
from src.entities.reports.reports_read_dto import *
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

@reports_router.get("/invoices/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_invoices_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get invoices summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Invoices summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/invoices/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_invoices_detailed_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get invoices detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Invoices detailed report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/invoices/aging", response_model=Respons[DetailedReportResponseReadBase])
def get_invoice_aging_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get invoice aging report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Invoice aging report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


# =====================================================
# 8. PAYMENT REPORTS
# =====================================================

@reports_router.get("/payments/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_payments_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get payments summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Payments summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/payments/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_payments_detailed_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get payments detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Payments detailed report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/payments/graphical", response_model=Respons[GraphicalReportResponseReadBase])
def get_payments_graphical_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get payments graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Payments graphical report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


# =====================================================
# 9. PRICING RULE REPORTS
# =====================================================

@reports_router.get("/pricing-rules/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_pricing_rules_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get pricing rules summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Pricing rules summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/pricing-rules/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_pricing_rules_detailed_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get pricing rules detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Pricing rules detailed report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


# =====================================================
# 10. RECEIVING / PURCHASE REPORTS
# =====================================================

@reports_router.get("/receivings/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_receivings_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_receivings_detailed_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings detailed report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/summary-categories", response_model=Respons[DetailedReportResponseReadBase])
def get_receivings_summary_categories_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings summary by categories report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings summary categories report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/suspended", response_model=Respons[DetailedReportResponseReadBase])
def get_suspended_receivings_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suspended receivings report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suspended receivings report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/deleted", response_model=Respons[DetailedReportResponseReadBase])
def get_deleted_receivings_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get deleted receivings report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Deleted receivings report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/summary-taxes", response_model=Respons[DetailedReportResponseReadBase])
def get_receivings_summary_taxes_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings summary taxes report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings summary taxes report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/graphical-taxes", response_model=Respons[GraphicalReportResponseReadBase])
def get_receivings_graphical_taxes_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings graphical taxes report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings graphical taxes report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/cheapest-supplier", response_model=Respons[DetailedReportResponseReadBase])
def get_cheapest_supplier_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get cheapest supplier report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Cheapest supplier report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/items/graphical", response_model=Respons[GraphicalReportResponseReadBase])
def get_receivings_items_graphical_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings items graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings items graphical report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/items/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_receivings_items_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings items summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings items summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/payments/graphical", response_model=Respons[GraphicalReportResponseReadBase])
def get_receivings_payments_graphical_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings payments graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings payments graphical report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/payments/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_receivings_payments_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings payments summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings payments summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/receivings/payments/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_receivings_payments_detailed_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get receivings payments detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Receivings payments detailed report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


# =====================================================
# 11. SUPPLIER REPORTS
# =====================================================

@reports_router.get("/suppliers/graphical", response_model=Respons[GraphicalReportResponseReadBase])
def get_suppliers_graphical_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers graphical report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/suppliers/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_suppliers_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/suppliers/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_suppliers_detailed_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers detailed report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/suppliers/summary-items", response_model=Respons[SummaryReportResponseReadBase])
def get_suppliers_summary_items_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers summary items report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers summary items report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/suppliers/receivings/graphical", response_model=Respons[GraphicalReportResponseReadBase])
def get_suppliers_receivings_graphical_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers receivings graphical report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers receivings graphical report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/suppliers/receivings/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_suppliers_receivings_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers receivings summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers receivings summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/suppliers/receivings/detailed", response_model=Respons[DetailedReportResponseReadBase])
def get_suppliers_receivings_detailed_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers receivings detailed report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers receivings detailed report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/suppliers/tax-by-payments", response_model=Respons[DetailedReportResponseReadBase])
def get_suppliers_tax_by_payments_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get suppliers tax by payments received report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Suppliers tax by payments report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


# =====================================================
# 12. OTHER REPORTS (Product Metadata, Product Prices, Pricing Rules, Tax, Tax Rule)
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


@reports_router.get("/tax/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_tax_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get tax summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Tax summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


@reports_router.get("/tax-rules/summary", response_model=Respons[SummaryReportResponseReadBase])
def get_tax_rules_summary_report(
    # data parameter removed - using Query params instead
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get tax rules summary report"""
    if not check_report_permission(current_user, "permission-msg-reports-get"):
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return Respons(
        success=False,
        detail="Tax rules summary report - implementation in progress",
        error="NOT_IMPLEMENTED",
    )


# =====================================================
# SALES REPORTS - NEW ENDPOINTS
# =====================================================

@reports_router.get("/sales/product-gross-profit", response_model=Respons[ProductGrossProfitReportResponseReadBase])
def get_product_gross_profit_report(
    from_date: Optional[date] = Query(None, description="Start date for the report (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date for the report (YYYY-MM-DD)"),
    location_ids: Optional[List[str]] = Query(None, description="List of location IDs to filter by. Can provide multiple values like ?location_ids=loc1&location_ids=loc2&location_ids=loc3"),
    format: str = Query("DETAILED", description="Report format: SUMMARY, DETAILED, or GRAPHICAL"),
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
    
    Shows gross profit per product calculated as: Revenue - Cost of Goods Sold (COGS)
    Can filter by date range, locations (one or more), and specific products.
    Supports grouping by location.
    
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
    format: str = Query("DETAILED", description="Report format: SUMMARY, DETAILED, or GRAPHICAL"),
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
    
    Shows net profit per product calculated as: Gross Profit - Allocated Expenses
    Expenses can be allocated proportionally by revenue or equally across products.
    Can filter by date range, locations (one or more), and specific products.
    Supports grouping by location.
    
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

