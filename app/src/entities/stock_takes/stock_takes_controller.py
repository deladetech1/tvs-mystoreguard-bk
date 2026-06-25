from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.stock_takes.stock_takes_service import StockTakesService
from src.entities.stock_takes.stock_takes_write_dto import (
    CreateStockTakeControllerWriteDto,
    ResolveStockTakeItemControllerWriteDto,
)
from src.entities.stock_takes.stock_takes_read_dto import (
    CreateStockTakeControllerReadDto,
    GetStockTakeControllerReadDto,
    CompleteStockTakeControllerReadDto,
    ResolveStockTakeItemControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from trovesuite import AuthService

stock_takes_router = APIRouter(prefix="/stock-takes", tags=["Stock Takes"])
logger = get_logger("stock_takes")


def _authorize(current_user, permissions: list[str]):
    if not AuthService.has_any_permission(user_roles=current_user.data, required_permissions=permissions):
        raise HTTPException(status_code=403, detail="Unauthorized access")


# 1. Create a stock take (count a list of products at the current location)
@stock_takes_router.post("/add", response_model=Respons[CreateStockTakeControllerReadDto])
def create_stock_take(
    data: CreateStockTakeControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Record a physical count for the current location.

    Snapshots the system's on-hand quantity for each product, computes the
    variance, and flags each line MATCH / OVER / SHORT. Counting alone never
    changes stock — variances are then investigated and resolved.
    """
    _authorize(current_user, ["permission-msg-stock-takes-create"])
    return StockTakesService.create_stock_take(
        data=data,
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        loc_id=org_bus_loc["loc_id"],
        created_by=current_user.data[0].user_id,
    )


# 2. List stock takes for the current location
@stock_takes_router.get("", response_model=Respons[GetStockTakeControllerReadDto])
def list_stock_takes(
    status: Optional[str] = Query(None, description="Filter by status (DRAFT|COMPLETED|CANCELLED)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """List stock takes recorded at the current location."""
    _authorize(current_user, ["permission-msg-stock-takes-get"])
    return StockTakesService.get_stock_takes(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        loc_id=org_bus_loc["loc_id"],
        status=status,
        page=page,
        size=size,
    )


# 3. Get one stock take with its variance report
@stock_takes_router.get("/{stock_take_id}", response_model=Respons[GetStockTakeControllerReadDto])
def get_stock_take(
    stock_take_id: str,
    only_variances: bool = Query(False, description="Return only mismatched (OVER/SHORT) lines"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a stock take with its counted lines and variance summary."""
    _authorize(current_user, ["permission-msg-stock-takes-get"])
    return StockTakesService.get_stock_take(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        stock_take_id=stock_take_id,
        only_variances=only_variances,
    )


# 4. Complete (lock) a stock take — does not change stock
@stock_takes_router.post("/{stock_take_id}/complete", response_model=Respons[CompleteStockTakeControllerReadDto])
def complete_stock_take(
    stock_take_id: str,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Mark counting finished. Variances remain for investigation; stock is untouched."""
    _authorize(current_user, ["permission-msg-stock-takes-create"])
    return StockTakesService.complete_stock_take(
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        stock_take_id=stock_take_id,
        user_id=current_user.data[0].user_id,
    )


# 5. Resolve a counted line (optionally apply a stock correction)
@stock_takes_router.put(
    "/{stock_take_id}/items/{item_id}/resolve",
    response_model=Respons[ResolveStockTakeItemControllerReadDto],
)
def resolve_stock_take_item(
    stock_take_id: str,
    item_id: str,
    data: ResolveStockTakeItemControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Advance a line's investigation and, optionally, correct a confirmed loss.

    Set resolution_status to INVESTIGATING/RESOLVED. On RESOLVED a negative
    adjustment_qty reduces stock (FIFO from the location's delivery breakdown, logged
    as a loss, purchase pool untouched); 0 leaves stock unchanged. A positive value is
    rejected — record surplus deliveries through Add Stock so cost/expiry are captured.
    """
    _authorize(current_user, ["permission-msg-stock-takes-resolve"])
    return StockTakesService.resolve_stock_take_item(
        data=data,
        tenant_id=current_user.data[0].tenant_id,
        org_id=org_bus_loc["org_id"],
        bus_id=org_bus_loc["bus_id"],
        stock_take_id=stock_take_id,
        item_id=item_id,
        user_id=current_user.data[0].user_id,
    )
