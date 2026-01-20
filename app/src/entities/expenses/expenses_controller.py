from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import date
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.expenses.expenses_service import ExpensesService
from src.entities.expenses.expenses_write_dto import (
    CreateExpenseControllerWriteDto,
    UpdateExpenseControllerWriteDto,
    PermanentDeleteExpenseControllerWriteDto,
)
from src.entities.expenses.expenses_read_dto import (
    CreateExpenseControllerReadDto,
    UpdateExpenseControllerReadDto,
    GetExpenseControllerReadDto,
    GetExpensesControllerReadDto,
    PermanentDeleteExpenseControllerReadDto,
    GetExpenseStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

expenses_router = APIRouter(prefix="/expenses", tags=["Expenses"])
logger = get_logger("expenses")


# 1. Create Expense
@expenses_router.post("/add", response_model=Respons[CreateExpenseControllerReadDto])
def create_expense(
    data: CreateExpenseControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new expense. If source is ALLOCATED, deducts from cp_expense table. CONTIGENCY, FIXED, and REIMBURSABLE expenses don't deduct from allocations."""
    with LogContext(
        "expenses",
        "create_expense",
        amount=str(data.amount) if hasattr(data, "amount") else "unknown",
    ):
        logger.info(
            "Processing create expense request",
            extra={
                "extra_fields": {
                    "endpoint": "/expenses/add",
                    "amount": str(data.amount),
                    "source": data.source,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-expense-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create expense failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ExpensesService.create_expense(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Expense created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/add",
                        "expense_id": (
                            service_result.data.id 
                            if service_result.data and hasattr(service_result.data, 'id')
                            else (service_result.data[0].id if isinstance(service_result.data, list) and service_result.data else None)
                        ),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Expense creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Expense
@expenses_router.put("/update", response_model=Respons[UpdateExpenseControllerReadDto])
def update_expense(
    data: UpdateExpenseControllerWriteDto,
    expense_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update an expense"""
    with LogContext(
        "expenses",
        "update_expense",
        expense_id=expense_id,
    ):
        logger.info(
            "Processing update expense request",
            extra={
                "extra_fields": {
                    "endpoint": "/expenses/update",
                    "expense_id": expense_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-expense-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update expense failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/update",
                        "expense_id": expense_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ExpensesService.update_expense(
            data=data,
            expense_id=expense_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Expense updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/update",
                        "expense_id": expense_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Expense update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/update",
                        "expense_id": expense_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Expense
@expenses_router.get("/get", response_model=Respons[GetExpenseControllerReadDto])
def get_expense(
    expense_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single expense by ID"""
    with LogContext(
        "expenses",
        "get_expense",
        expense_id=expense_id,
    ):
        logger.info(
            "Processing get expense request",
            extra={
                "extra_fields": {
                    "endpoint": "/expenses/get",
                    "expense_id": expense_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-expense-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get expense failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/get",
                        "expense_id": expense_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ExpensesService.get_expense(
            expense_id=expense_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
        )

        if service_result.success:
            logger.info(
                "Expense retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/get",
                        "expense_id": expense_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Expense retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/get",
                        "expense_id": expense_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Expenses (List)
@expenses_router.get("/list", response_model=Respons[GetExpensesControllerReadDto])
def get_expenses(
    source: Optional[str] = Query(None, description="Filter by a single source (ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE). Use 'sources' parameter for multiple values."),
    sources: Optional[List[str]] = Query(None, description="Filter by one or more sources (ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE). Can provide multiple values like ?sources=ALLOCATED&sources=CONTIGENCY"),
    used_by: Optional[str] = Query(None, description="Filter by user ID"),
    from_date: Optional[str] = Query(None, description="Filter expenses from this date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"),
    to_date: Optional[str] = Query(None, description="Filter expenses to this date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of expenses with filters and pagination"""
    # Normalize source/sources parameters: if source is provided, convert it to sources list
    # If both are provided, sources takes precedence
    if source and not sources:
        sources = [source]
    
    with LogContext(
        "expenses",
        "get_expenses",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get expenses request",
            extra={
                "extra_fields": {
                    "endpoint": "/expenses/list",
                    "filters": {
                        "source": source,
                        "sources": sources,
                        "used_by": used_by,
                        "from_date": from_date,
                        "to_date": to_date,
                        "page": page,
                        "size": size,
                    },
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-expense-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get expenses failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ExpensesService.get_expenses(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            sources=sources,
            used_by=used_by,
            from_date=from_date,
            to_date=to_date,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Expenses retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Expenses retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 5. Permanent Delete Expense
@expenses_router.delete("/permanent-delete", response_model=Respons[PermanentDeleteExpenseControllerReadDto])
def permanent_delete_expense(
    data: PermanentDeleteExpenseControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Permanently delete an expense. If source is ALLOCATED, refunds the amount to cp_expense. CONTIGENCY, FIXED, and REIMBURSABLE expenses don't refund to allocations."""
    with LogContext(
        "expenses",
        "permanent_delete_expense",
        expense_id=data.expense_id if hasattr(data, "expense_id") else "unknown",
    ):
        logger.info(
            "Processing permanent delete expense request",
            extra={
                "extra_fields": {
                    "endpoint": "/expenses/permanent-delete",
                    "expense_id": data.expense_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-expense-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Permanent delete expense failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/permanent-delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ExpensesService.permanent_delete_expense(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 6. Get Expense Statistics
@expenses_router.get("/statistics", response_model=Respons[GetExpenseStatisticsControllerReadDto])
def get_expense_statistics(
    source: Optional[str] = Query(None, description="Filter by a single source (ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE). Use 'sources' parameter for multiple values."),
    sources: Optional[List[str]] = Query(None, description="Filter by one or more sources (ALLOCATED, CONTIGENCY, FIXED, REIMBURSABLE). Can provide multiple values like ?sources=ALLOCATED&sources=CONTIGENCY"),
    from_date: Optional[date] = Query(None, description="Filter expenses from this date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter expenses to this date (YYYY-MM-DD)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get expense statistics with optional date filtering on cdatetime field"""
    # Normalize source/sources parameters: if source is provided, convert it to sources list
    # If both are provided, sources takes precedence
    if source and not sources:
        sources = [source]
    
    with LogContext(
        "expenses",
        "get_expense_statistics",
    ):
        logger.info(
            "Processing get expense statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/expenses/statistics",
                    "source": source,
                    "sources": sources,
                    "from_date": str(from_date) if from_date else None,
                    "to_date": str(to_date) if to_date else None,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-expense-get-statistics"]
        )

        if not is_authorized:
            logger.warning(
                "Get expense statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/expenses/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = ExpensesService.get_expense_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            sources=sources,
            from_date=from_date,
            to_date=to_date,
        )

        return service_result

