from typing import Optional, List
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from src.entities.expenses.expenses_read_dto import (
    CreateExpenseServiceReadDto,
    UpdateExpenseServiceReadDto,
    GetExpenseServiceReadDto,
    GetExpensesServiceReadDto,
    PermanentDeleteExpenseServiceReadDto,
    GetExpenseStatisticsServiceReadDto,
)
from src.entities.expenses.expenses_write_dto import (
    CreateExpenseServiceWriteDto,
    UpdateExpenseServiceWriteDto,
    PermanentDeleteExpenseServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("expenses_service")


class ExpensesService:
    """Service class for expenses operations"""

    @staticmethod
    def create_expense(
        data: CreateExpenseServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateExpenseServiceReadDto]:
        """Create an expense and deduct from cp_expense if source is ALLOCATED"""
        logger.info(
            f"Processing expense creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "amount": str(data.amount),
                    "source": data.source,
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # If source is ALLOCATED, check and deduct from cp_expense
                expense_allocation_id = None
                if data.source == 'ALLOCATED':
                    # Check available amount in cp_expense table
                    # Exact match: tenant_id, org_id, bus_id, loc_id (no NULL values)
                    cursor.execute(
                        f"""SELECT id, amount FROM {db_settings.CORE_PLATFORM_EXPENSE_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND delete_status = 'NOT_DELETED' AND is_active = true
                        LIMIT 1""",
                        (tenant_id, org_id, bus_id, loc_id),
                    )
                    expense_record = cursor.fetchone()

                    if not expense_record:
                        return Respons(
                            success=False,
                            detail="No available expense allocation found. Please allocate funds for expenses first.",
                            error="NO_ALLOCATION_FOUND",
                        )

                    available_amount = Decimal(str(expense_record['amount']))
                    expense_allocation_id = expense_record['id']

                    # Check if available amount is greater than or equal to requested amount
                    # This prevents negative values and informs client if insufficient funds
                    if data.amount > available_amount:
                        return Respons(
                            success=False,
                            detail=f"There is not enough funds for expenses. Available: {available_amount}, "
                                   f"Requested: {data.amount}. Please allocate more funds before making this expense.",
                            error="INSUFFICIENT_FUNDS",
                        )

                    # Deduct the amount from cp_expense
                    new_amount = available_amount - data.amount
                    cursor.execute(
                        f"""UPDATE {db_settings.CORE_PLATFORM_EXPENSE_TABLE}
                        SET amount = %s, updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND is_active = true""",
                        (new_amount, created_by, expense_allocation_id, tenant_id, org_id, bus_id, loc_id),
                    )

                    # Calculate balance: remaining allocated amount after this expense
                    balance = new_amount

                    logger.info(
                        f"Deducted {data.amount} from cp_expense. New amount: {new_amount}, Balance: {balance}",
                        extra={
                            "extra_fields": {
                                "expense_allocation_id": expense_allocation_id,
                                "deducted_amount": str(data.amount),
                                "new_amount": str(new_amount),
                                "balance": str(balance),
                            }
                        },
                    )
                else:
                    # For CONTIGENCY, FIXED, and REIMBURSABLE expenses, balance is 0 (not applicable, but column requires NOT NULL)
                    balance = Decimal('0')

                # Generate expense ID
                expense_id = Helper.generate_unique_identifier(prefix="exp")

                # Insert into cp_expenses_history table
                cursor.execute(
                    f"""INSERT INTO {db_settings.CP_EXPENSES_HISTORY_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, amount, currency_id, used_by, used_for, source, balance,
                     delete_status, is_active, description, app, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        expense_id, tenant_id, org_id, bus_id, loc_id,
                        data.amount, data.currency_id, data.used_by, data.used_for, data.source, balance,
                        'NOT_DELETED', True, data.description, 'MYSTOREGUARD',
                        cdate, ctime, cdatetime, created_by
                    ),
                )
                expense_result = cursor.fetchone()

                if not expense_result:
                    raise ValueError("Failed to create expense")

                # Get expense with user fullnames
                cursor.execute(
                    f"""SELECT e.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON e.created_by = creator.id AND e.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON e.updated_by = updater.id AND e.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON e.deleted_by = deleter.id AND e.tenant_id = deleter.tenant_id
                    WHERE e.id = %s AND e.tenant_id = %s""",
                    (expense_id, tenant_id),
                )
                expense_with_users = cursor.fetchone()

                if expense_with_users:
                    if isinstance(expense_with_users, dict):
                        expense_dict = expense_with_users.copy()
                    else:
                        expense_dict = dict(expense_with_users)
                    # Replace user IDs with fullnames (or None if not found)
                    expense_dict['created_by'] = expense_dict.get('created_by') or None
                    expense_dict['updated_by'] = expense_dict.get('updated_by') or None
                    expense_dict['deleted_by'] = expense_dict.get('deleted_by') or None
                else:
                    if isinstance(expense_result, dict):
                        expense_dict = expense_result.copy()
                    else:
                        expense_dict = dict(expense_result)
                    expense_dict['created_by'] = None
                    expense_dict['updated_by'] = None
                    expense_dict['deleted_by'] = None

                expense_read = CreateExpenseServiceReadDto(**expense_dict)

                # Log activity - get ALL data after insertion for new_data
                # Pass cursor to use the same transaction
                try:
                    # Get complete record with all columns after insertion
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (expense_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else dict(expense_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-expenses",
                        resource_id=expense_id,
                        action="create",
                        old_data=None,
                        new_data=complete_new_data,
                        description=f"Expense {expense_id} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor  # Use same transaction
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Expense created successfully: {expense_id}",
                    extra={
                        "extra_fields": {
                            "expense_id": expense_id,
                            "amount": str(data.amount),
                            "source": data.source,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Expense created successfully",
                    data=[expense_read],  # Wrap in list - Respons expects data to be a list
                )

        except ValueError as e:
            logger.error(f"Validation error creating expense: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating expense: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create expense: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_expense(
        data: UpdateExpenseServiceWriteDto,
        expense_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[UpdateExpenseServiceReadDto]:
        """Update an expense"""
        logger.info(
            f"Processing expense update: {expense_id}",
            extra={
                "extra_fields": {
                    "expense_id": expense_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                # Fetch existing data (for audit/activity log)
                cursor.execute(
                    f"""SELECT * FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s AND delete_status = 'NOT_DELETED'""",
                    (expense_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_expense = cursor.fetchone()

                if not existing_expense:
                    raise ValueError("Expense not found")
                
                # Store complete old data (variable A) - all columns before update
                old_data = dict(existing_expense)

                # Build update query dynamically - only allow updating used_by, used_for, and description
                update_fields = []
                params = []

                if data.used_by is not None:
                    update_fields.append("used_by = %s")
                    params.append(data.used_by)
                if data.used_for is not None:
                    update_fields.append("used_for = %s")
                    params.append(data.used_for)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([expense_id, tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.CP_EXPENSES_HISTORY_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_expense = cursor.fetchone()

                if not updated_expense:
                    raise ValueError("Failed to update expense")

                # Get expense with user fullnames
                cursor.execute(
                    f"""SELECT e.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON e.created_by = creator.id AND e.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON e.updated_by = updater.id AND e.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON e.deleted_by = deleter.id AND e.tenant_id = deleter.tenant_id
                    WHERE e.id = %s AND e.tenant_id = %s""",
                    (expense_id, tenant_id),
                )
                expense_with_users = cursor.fetchone()

                if expense_with_users:
                    expense_dict = dict(expense_with_users)
                    # Replace user IDs with fullnames (or None if not found)
                    expense_dict['created_by'] = expense_dict.get('created_by') or None
                    expense_dict['updated_by'] = expense_dict.get('updated_by') or None
                    expense_dict['deleted_by'] = expense_dict.get('deleted_by') or None
                else:
                    expense_dict = dict(updated_expense)
                    expense_dict['created_by'] = None
                    expense_dict['updated_by'] = None
                    expense_dict['deleted_by'] = None

                expense_read = UpdateExpenseServiceReadDto(**expense_dict)

                # Log activity - get complete new data (variable B) after update
                # Pass cursor to use same transaction
                try:
                    # Get complete record with all columns after update (variable B)
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                        WHERE id = %s AND tenant_id = %s""",
                        (expense_id, tenant_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    new_data = dict(complete_new_data_record) if complete_new_data_record else dict(expense_dict)
                    
                    # old_data (variable A) was captured before update
                    # new_data (variable B) captured after update
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-expenses",
                        resource_id=expense_id,
                        action="update",
                        old_data=old_data,  # Variable A - complete data before update
                        new_data=new_data,  # Variable B - complete data after update
                        description=f"Expense {expense_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor  # Use same transaction
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Expense updated successfully: {expense_id}")

                return Respons(
                    success=True,
                    detail="Expense updated successfully",
                    data=[expense_read],  # Wrap in list - Respons expects data to be a list
                )

        except ValueError as e:
            logger.error(f"Validation error updating expense: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating expense: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update expense: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expense(
        expense_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetExpenseServiceReadDto]:
        """Get a single expense by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT e.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON e.created_by = creator.id AND e.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON e.updated_by = updater.id AND e.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON e.deleted_by = deleter.id AND e.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON e.currency_id = c.id AND e.tenant_id = c.tenant_id
                    WHERE e.id = %s AND e.tenant_id = %s AND e.org_id = %s 
                    AND e.bus_id = %s AND e.loc_id = %s AND e.delete_status = 'NOT_DELETED'""",
                    (expense_id, tenant_id, org_id, bus_id, loc_id),
                )
                expense = cursor.fetchone()

                if not expense:
                    return Respons(
                        success=False,
                        detail="Expense not found",
                        error="NOT_FOUND",
                    )

                expense_dict = dict(expense)
                # Replace user IDs with fullnames (or None if not found)
                expense_dict['created_by'] = expense_dict.get('created_by') or None
                expense_dict['updated_by'] = expense_dict.get('updated_by') or None
                expense_dict['deleted_by'] = expense_dict.get('deleted_by') or None
                expense_read = GetExpenseServiceReadDto(**expense_dict)

                return Respons(
                    success=True,
                    detail="Expense retrieved successfully",
                    data=[expense_read],  # Wrap in list - Respons expects data to be a list
                )

        except Exception as e:
            logger.error(f"Error getting expense: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get expense: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expenses(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        sources: Optional[List[str]] = None,
        used_by: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetExpensesServiceReadDto]]:
        """Get list of expenses with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build base WHERE clause with table alias
                base_where_conditions = [
                    "e.tenant_id = %s",
                    "e.org_id = %s",
                    "e.bus_id = %s",
                    "e.loc_id = %s",
                    "e.delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                # Check if sources contains ALLOCATED or CONTIGENCY - if so, always include FIXED
                # But if sources is ONLY FIXED, don't add anything - just return FIXED expenses
                if sources and len(sources) > 0:
                    # Only auto-add FIXED if ALLOCATED or CONTIGENCY is present
                    # If sources is ONLY ['FIXED'], we don't modify it
                    if ('ALLOCATED' in sources or 'CONTIGENCY' in sources) and 'FIXED' not in sources:
                        sources = sources + ['FIXED']

                # Build source and date filter conditions
                # If FIXED is in sources and dates are provided, FIXED should not be filtered by date
                if sources and len(sources) > 0:
                    non_fixed_sources = [s for s in sources if s != 'FIXED']
                    has_fixed = 'FIXED' in sources
                    has_date_filter = from_date is not None or to_date is not None
                    
                    # Check if sources is ONLY FIXED (no other sources)
                    is_only_fixed = has_fixed and len(non_fixed_sources) == 0
                    
                    if is_only_fixed:
                        # Only FIXED source - return only FIXED expenses, no date filtering
                        base_where_conditions.append("e.source = 'FIXED'")
                    elif has_fixed and non_fixed_sources and has_date_filter:
                        # We have FIXED + other sources + date filter
                        # Non-FIXED sources: apply date filter
                        # FIXED sources: no date filter (always include)
                        non_fixed_placeholders = ','.join(['%s'] * len(non_fixed_sources))
                        params.extend(non_fixed_sources)
                        
                        date_conditions = []
                        if from_date:
                            date_conditions.append("DATE(e.cdatetime) >= DATE(%s)")
                            params.append(from_date)
                        if to_date:
                            date_conditions.append("DATE(e.cdatetime) <= DATE(%s)")
                            params.append(to_date)
                        
                        date_clause = " AND ".join(date_conditions)
                        base_where_conditions.append(f"((e.source IN ({non_fixed_placeholders}) AND {date_clause}) OR e.source = 'FIXED')")
                    elif has_fixed and non_fixed_sources and not has_date_filter:
                        # We have FIXED + other sources, no date filter
                        all_sources_placeholders = ','.join(['%s'] * len(sources))
                        base_where_conditions.append(f"e.source IN ({all_sources_placeholders})")
                        params.extend(sources)
                    else:
                        # Only non-FIXED sources (no FIXED in the list)
                        placeholders = ','.join(['%s'] * len(non_fixed_sources))
                        base_where_conditions.append(f"e.source IN ({placeholders})")
                        params.extend(non_fixed_sources)
                else:
                    # No sources filter provided - apply date filters if provided
                    if from_date:
                        base_where_conditions.append("DATE(e.cdatetime) >= DATE(%s)")
                        params.append(from_date)
                    if to_date:
                        base_where_conditions.append("DATE(e.cdatetime) <= DATE(%s)")
                        params.append(to_date)
                
                if used_by:
                    base_where_conditions.append("e.used_by = %s")
                    params.append(used_by)
                
                # Apply date filters only for non-FIXED sources when sources filter is provided
                # This handles the case where sources is provided but doesn't include FIXED
                if sources and len(sources) > 0 and 'FIXED' not in sources:
                    if from_date:
                        base_where_conditions.append("DATE(e.cdatetime) >= DATE(%s)")
                        params.append(from_date)
                    if to_date:
                        base_where_conditions.append("DATE(e.cdatetime) <= DATE(%s)")
                        params.append(to_date)

                where_clause = " AND ".join(base_where_conditions)

                # Get total count
                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e WHERE {where_clause}",
                    tuple(params),
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Calculate pagination
                offset = (page - 1) * size
                params_with_pagination = params + [size, offset]

                # Get expenses with user fullnames and currency info
                cursor.execute(
                    f"""SELECT e.*,
                           creator.fullname as created_by,
                           updater.fullname as updated_by,
                           deleter.fullname as deleted_by,
                           c.name as currency_name,
                           c.symbol as currency_symbol
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE} e
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON e.created_by = creator.id AND e.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON e.updated_by = updater.id AND e.tenant_id = updater.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} deleter ON e.deleted_by = deleter.id AND e.tenant_id = deleter.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} c ON e.currency_id = c.id AND e.tenant_id = c.tenant_id
                    WHERE {where_clause}
                    ORDER BY e.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params_with_pagination),
                )
                expenses = cursor.fetchall()

                expense_list = []
                for exp in expenses:
                    exp_dict = dict(exp)
                    # Replace user IDs with fullnames (or None if not found)
                    exp_dict['created_by'] = exp_dict.get('created_by') or None
                    exp_dict['updated_by'] = exp_dict.get('updated_by') or None
                    exp_dict['deleted_by'] = exp_dict.get('deleted_by') or None
                    expense_list.append(GetExpensesServiceReadDto(**exp_dict))

                pagination = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    has_next=(page * size) < total,
                )

                return Respons(
                    success=True,
                    detail="Expenses retrieved successfully",
                    data=expense_list,
                    pagination=pagination,
                )

        except Exception as e:
            logger.error(f"Error getting expenses: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get expenses: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def permanent_delete_expense(
        data: PermanentDeleteExpenseServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        deleted_by: str
    ) -> Respons[PermanentDeleteExpenseServiceReadDto]:
        """Permanently delete an expense and refund if source is ALLOCATED"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Get expense details before deletion
                cursor.execute(
                    f"""SELECT * FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s 
                    AND bus_id = %s AND loc_id = %s""",
                    (data.expense_id, tenant_id, org_id, bus_id, loc_id),
                )
                expense = cursor.fetchone()

                if not expense:
                    return Respons(
                        success=False,
                        detail="Expense not found",
                        error="NOT_FOUND",
                    )

                # Store complete old data before deletion - get ALL columns
                expense_dict = dict(expense)
                expense_amount = Decimal(str(expense_dict['amount']))
                expense_source = expense_dict.get('source')
                
                # If source is ALLOCATED, refund the amount to cp_expense before permanent deletion
                if expense_source == 'ALLOCATED':
                    # Find using exact match
                    cursor.execute(
                        f"""SELECT id, amount FROM {db_settings.CORE_PLATFORM_EXPENSE_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                        AND delete_status = 'NOT_DELETED' AND is_active = true
                        LIMIT 1""",
                        (tenant_id, org_id, bus_id, loc_id),
                    )
                    expense_record = cursor.fetchone()
                    if expense_record:
                        current_amount = Decimal(str(expense_record['amount']))
                        new_amount = current_amount + expense_amount
                        cursor.execute(
                            f"""UPDATE {db_settings.CORE_PLATFORM_EXPENSE_TABLE}
                            SET amount = %s, updated_by = %s
                            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                            AND is_active = true""",
                            (new_amount, deleted_by, expense_record['id'], tenant_id, org_id, bus_id, loc_id),
                        )
                        logger.info(
                            f"Refunded {expense_amount} to cp_expense before permanent delete. New amount: {new_amount}",
                            extra={
                                "extra_fields": {
                                    "expense_allocation_id": expense_record['id'],
                                    "refunded_amount": str(expense_amount),
                                    "new_amount": str(new_amount),
                                }
                            },
                        )
                    else:
                        logger.error(
                            f"Failed to refund {expense_amount} to cp_expense before permanent delete - expense record not found",
                            extra={
                                "extra_fields": {
                                    "expense_id": data.expense_id,
                                    "tenant_id": tenant_id,
                                    "org_id": org_id,
                                    "bus_id": bus_id,
                                    "loc_id": loc_id,
                                    "refunded_amount": str(expense_amount),
                                }
                            },
                        )
                        return Respons(
                            success=False,
                            detail=f"Failed to refund expense amount before permanent delete: Expense allocation record not found",
                            error="REFUND_FAILED",
                        )

                # Log activity before permanent deletion - get complete old data first
                # Pass cursor to use same transaction
                try:
                    # Get complete record with ALL columns before deletion
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s 
                        AND bus_id = %s AND loc_id = %s""",
                        (data.expense_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    complete_old_data_record = cursor.fetchone()
                    complete_old_data = dict(complete_old_data_record) if complete_old_data_record else dict(expense_dict)
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-expenses",
                        resource_id=data.expense_id,
                        action="delete",
                        old_data=complete_old_data,  # Complete data before deletion
                        new_data=None,
                        description=f"Expense {data.expense_id} permanently deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor  # Use same transaction
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Permanently delete
                cursor.execute(
                    f"""DELETE FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.expense_id, tenant_id, org_id, bus_id, loc_id),
                )

                return Respons(
                    success=True,
                    detail="Expense permanently deleted successfully",
                    data=[PermanentDeleteExpenseServiceReadDto(
                        expense_id=data.expense_id,
                        message="Expense permanently deleted",
                    )],  # Wrap in list - Respons expects data to be a list
                )

        except Exception as e:
            logger.error(f"Error permanently deleting expense: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to permanently delete expense: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_expense_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        sources: Optional[List[str]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Respons[GetExpenseStatisticsServiceReadDto]:
        """Get expense statistics with optional date filtering. FIXED expenses are always included regardless of date filters."""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build base WHERE clause
                base_where_conditions = [
                    "tenant_id = %s",
                    "org_id = %s",
                    "bus_id = %s",
                    "loc_id = %s",
                    "delete_status = 'NOT_DELETED'",
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                # Check if sources contains ALLOCATED or CONTIGENCY - if so, always include FIXED
                # But if sources is ONLY FIXED, don't add anything - just return FIXED expenses
                if sources and len(sources) > 0:
                    # Only auto-add FIXED if ALLOCATED or CONTIGENCY is present
                    # If sources is ONLY ['FIXED'], we don't modify it
                    if ('ALLOCATED' in sources or 'CONTIGENCY' in sources) and 'FIXED' not in sources:
                        sources = sources + ['FIXED']

                # Build source and date filter conditions
                # If FIXED is in sources and dates are provided, FIXED should not be filtered by date
                has_date_filter = from_date is not None or to_date is not None
                
                if sources and len(sources) > 0:
                    non_fixed_sources = [s for s in sources if s != 'FIXED']
                    has_fixed = 'FIXED' in sources
                    
                    # Check if sources is ONLY FIXED (no other sources)
                    is_only_fixed = has_fixed and len(non_fixed_sources) == 0
                    
                    if is_only_fixed:
                        # Only FIXED source - return only FIXED expenses, no date filtering
                        base_where_conditions.append("source = 'FIXED'")
                    elif has_fixed and non_fixed_sources and has_date_filter:
                        # We have FIXED + other sources + date filter
                        # Non-FIXED sources: apply date filter
                        # FIXED sources: no date filter (always include)
                        non_fixed_placeholders = ','.join(['%s'] * len(non_fixed_sources))
                        params.extend(non_fixed_sources)
                        
                        date_conditions = []
                        if from_date is not None and to_date is not None:
                            date_conditions.append("DATE(cdatetime) >= %s AND DATE(cdatetime) <= %s")
                            params.extend([from_date, to_date])
                        elif from_date is not None:
                            date_conditions.append("DATE(cdatetime) >= %s")
                            params.append(from_date)
                        elif to_date is not None:
                            date_conditions.append("DATE(cdatetime) <= %s")
                            params.append(to_date)
                        
                        date_clause = " AND ".join(date_conditions)
                        base_where_conditions.append(f"((source IN ({non_fixed_placeholders}) AND {date_clause}) OR source = 'FIXED')")
                    elif has_fixed and non_fixed_sources and not has_date_filter:
                        # We have FIXED + other sources, no date filter
                        all_sources_placeholders = ','.join(['%s'] * len(sources))
                        base_where_conditions.append(f"source IN ({all_sources_placeholders})")
                        params.extend(sources)
                    else:
                        # Only non-FIXED sources (no FIXED in the list)
                        placeholders = ','.join(['%s'] * len(non_fixed_sources))
                        base_where_conditions.append(f"source IN ({placeholders})")
                        params.extend(non_fixed_sources)
                        
                        # Apply date filters for non-FIXED sources
                        if has_date_filter:
                            if from_date is not None and to_date is not None:
                                base_where_conditions.append("DATE(cdatetime) >= %s AND DATE(cdatetime) <= %s")
                                params.extend([from_date, to_date])
                            elif from_date is not None:
                                base_where_conditions.append("DATE(cdatetime) >= %s")
                                params.append(from_date)
                            elif to_date is not None:
                                base_where_conditions.append("DATE(cdatetime) <= %s")
                                params.append(to_date)
                else:
                    # No sources filter provided - apply date filters if provided
                    # Date filtering: FIXED expenses should not be filtered by date
                    # When dates are provided, use: (date conditions) OR (source = 'FIXED')
                    if has_date_filter:
                        # Build date conditions for non-FIXED expenses
                        date_conditions = []
                        if from_date is not None and to_date is not None:
                            date_conditions.append("DATE(cdatetime) >= %s AND DATE(cdatetime) <= %s")
                            params.extend([from_date, to_date])
                        elif from_date is not None:
                            date_conditions.append("DATE(cdatetime) >= %s")
                            params.append(from_date)
                        elif to_date is not None:
                            date_conditions.append("DATE(cdatetime) <= %s")
                            params.append(to_date)
                        
                        # Include all expenses: those matching date filter OR FIXED expenses
                        date_clause = " AND ".join(date_conditions)
                        base_where_conditions.append(f"({date_clause} OR source = 'FIXED')")
                    # If no date filter, all expenses are included (no additional condition needed)

                where_clause = " AND ".join(base_where_conditions)

                # Get total expenses and amounts
                # Note: COUNT(*) always returns a row (even if 0), so fetchone() should never return None
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_expenses,
                        COALESCE(SUM(COALESCE(amount, 0)), 0) as total_amount,
                        COALESCE(SUM(CASE WHEN source = 'ALLOCATED' THEN COALESCE(amount, 0) ELSE 0 END), 0) as total_allocated,
                        COALESCE(SUM(CASE WHEN source = 'CONTIGENCY' THEN COALESCE(amount, 0) ELSE 0 END), 0) as total_contigency,
                        COALESCE(SUM(CASE WHEN source = 'FIXED' THEN COALESCE(amount, 0) ELSE 0 END), 0) as total_fixed,
                        COALESCE(SUM(CASE WHEN source = 'REIMBURSABLE' THEN COALESCE(amount, 0) ELSE 0 END), 0) as total_reimbursable
                    FROM {db_settings.CP_EXPENSES_HISTORY_TABLE}
                    WHERE {where_clause}""",
                    tuple(params),
                )
                stats_row = cursor.fetchone()

                # Get available allocated amount from cp_expense - exact match
                cursor.execute(
                    f"""SELECT COALESCE(SUM(amount), 0) as available_allocated
                    FROM {db_settings.CORE_PLATFORM_EXPENSE_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND delete_status = 'NOT_DELETED' AND is_active = true""",
                    (tenant_id, org_id, bus_id, loc_id),
                )
                available_row = cursor.fetchone()

                # RealDictCursor returns RealDictRow which supports dictionary access
                # Handle None case (when no rows match) - COUNT/SUM queries should still return a row with zeros
                # But if fetchone() returns None, we'll use defaults
                if stats_row is None:
                    logger.warning("Statistics query returned no rows - using default values")
                    stats_row = {}
                
                if available_row is None:
                    logger.warning("Available allocation query returned no rows - using default values")
                    available_row = {}
                
                # Access values directly using dictionary syntax
                # RealDictRow supports both dict access and attribute access
                # Round all Decimal values to 2 decimal places
                two_places = Decimal('0.01')
                
                total_expenses = int(stats_row.get('total_expenses', 0)) if stats_row else 0
                total_amount = Decimal(str(stats_row.get('total_amount', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_allocated = Decimal(str(stats_row.get('total_allocated', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_contigency = Decimal(str(stats_row.get('total_contigency', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_fixed = Decimal(str(stats_row.get('total_fixed', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                total_reimbursable = Decimal(str(stats_row.get('total_reimbursable', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if stats_row else Decimal('0')
                available_allocated = Decimal(str(available_row.get('available_allocated', 0))).quantize(two_places, rounding=ROUND_HALF_UP) if available_row else Decimal('0')
                
                # Calculate total amount without fixed expenses
                total_amount_without_fixed = (total_amount - total_fixed).quantize(two_places, rounding=ROUND_HALF_UP)
                
                logger.info(
                    f"Statistics calculated: total_expenses={total_expenses}, total_amount={total_amount}, "
                    f"total_allocated={total_allocated}, total_contigency={total_contigency}, "
                    f"total_fixed={total_fixed}, total_reimbursable={total_reimbursable}, available_allocated={available_allocated}, "
                    f"total_amount_without_fixed={total_amount_without_fixed}",
                    extra={
                        "extra_fields": {
                            "tenant_id": tenant_id,
                            "org_id": org_id,
                            "bus_id": bus_id,
                            "loc_id": loc_id,
                            "from_date": str(from_date) if from_date else None,
                            "to_date": str(to_date) if to_date else None,
                        }
                    }
                )
                
                statistics = GetExpenseStatisticsServiceReadDto(
                    total_expenses=total_expenses,
                    total_amount=total_amount,
                    total_allocated=total_allocated,
                    total_contigency=total_contigency,
                    total_fixed=total_fixed,
                    total_reimbursable=total_reimbursable,
                    available_allocated=available_allocated,
                    total_amount_without_fixed=total_amount_without_fixed,
                )

                return Respons(
                    success=True,
                    detail="Expense statistics retrieved successfully",
                    data=[statistics],  # Wrap in list - Respons expects data to be a list
                )

        except Exception as e:
            logger.error(f"Error getting expense statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get expense statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

