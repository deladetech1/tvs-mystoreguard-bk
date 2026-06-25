from typing import Optional, List
from src.entities.stock_takes.stock_takes_write_dto import (
    CreateStockTakeServiceWriteDto,
    ResolveStockTakeItemServiceWriteDto,
)
from src.entities.stock_takes.stock_takes_read_dto import (
    StockTakeReadDto,
    StockTakeItemReadDto,
    StockTakeVarianceSummary,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("stock_takes_service")


def _qty_table(location_type: str) -> str:
    """Map a location type to the on-hand quantity table."""
    return (
        db_settings.MSG_WAREHOUSE_PRODUCTS_TABLE
        if location_type == "WAREHOUSE"
        else db_settings.MSG_STORE_PRODUCTS_TABLE
    )


def _match_status(variance: int) -> str:
    if variance == 0:
        return "MATCH"
    return "OVER" if variance > 0 else "SHORT"


def _generate_stock_take_number(tenant_id: str, org_id: str, bus_id: str, loc_id: str, cursor) -> str:
    """Generate a per-location stock take number: STK-YYYYMMDD-NN."""
    prefix = "STK"
    date_str = Helper.current_date_time()["cdate"].replace("-", "")
    cursor.execute(
        f"""SELECT COUNT(*) AS count FROM {db_settings.MSG_STOCK_TAKES_TABLE}
        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
        AND stock_take_number LIKE %s""",
        (tenant_id, org_id, bus_id, loc_id, f"{prefix}-{date_str}-%"),
    )
    result = cursor.fetchone()
    count = result["count"] if result else 0
    return f"{prefix}-{date_str}-{str(count + 1).zfill(2)}"


class StockTakesService:
    # =====================================================
    # CREATE
    # =====================================================
    @staticmethod
    def create_stock_take(
        data: CreateStockTakeServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str,
    ) -> Respons:
        if data.location_type not in ("STORE", "WAREHOUSE"):
            return Respons(success=False, detail="Invalid location type", error="INVALID_LOCATION_TYPE")

        # Reject duplicate products in the same count (one line per product per take).
        product_ids = [i.product_id for i in data.items]
        if len(product_ids) != len(set(product_ids)):
            return Respons(
                success=False,
                detail="Duplicate products in count. Each product may appear once per stock take.",
                error="DUPLICATE_PRODUCT",
            )

        qty_table = _qty_table(data.location_type)
        dt = Helper.current_date_time()
        cdate, ctime, cdatetime = dt["cdate"], dt["ctime"], dt["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Verify location exists
                cursor.execute(
                    f"""SELECT id FROM {db_settings.CORE_PLATFORM_LOCATIONS_TABLE}
                    WHERE tenant_id = %s AND id = %s""",
                    (tenant_id, loc_id),
                )
                if not cursor.fetchone():
                    return Respons(success=False, detail=f"Location {loc_id} not found", error="LOCATION_NOT_FOUND")

                stock_take_id = Helper.generate_unique_identifier(prefix="stk")
                stock_take_number = _generate_stock_take_number(tenant_id, org_id, bus_id, loc_id, cursor)

                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_STOCK_TAKES_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, location_type, stock_take_number,
                     status, description, delete_status, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        stock_take_id, tenant_id, org_id, bus_id, loc_id, data.location_type,
                        stock_take_number, "DRAFT", data.description, "NOT_DELETED",
                        cdate, ctime, cdatetime, created_by,
                    ),
                )

                items_out: List[StockTakeItemReadDto] = []
                summary = StockTakeVarianceSummary()

                for line in data.items:
                    # Confirm the product belongs to this business
                    cursor.execute(
                        f"""SELECT id, name FROM {db_settings.MSG_PRODUCTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, line.product_id),
                    )
                    product = cursor.fetchone()
                    if not product:
                        return Respons(
                            success=False,
                            detail=f"Product {line.product_id} not found",
                            error="PRODUCT_NOT_FOUND",
                        )

                    # Snapshot what the system currently believes is on hand here
                    cursor.execute(
                        f"""SELECT current_qty FROM {qty_table}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, loc_id, line.product_id),
                    )
                    row = cursor.fetchone()
                    system_qty = row["current_qty"] if row else 0
                    variance = line.counted_qty - system_qty
                    match_status = _match_status(variance)

                    item_id = Helper.generate_unique_identifier(prefix="sti")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE}
                        (id, tenant_id, org_id, bus_id, stock_take_id, product_id,
                         counted_qty, system_qty, variance_qty, match_status, resolution_status,
                         note, adjustment_qty, cdate, ctime, cdatetime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            item_id, tenant_id, org_id, bus_id, stock_take_id, line.product_id,
                            line.counted_qty, system_qty, variance, match_status, "PENDING",
                            line.note, 0, cdate, ctime, cdatetime,
                        ),
                    )

                    items_out.append(StockTakeItemReadDto(
                        id=item_id, stock_take_id=stock_take_id, product_id=line.product_id,
                        product_name=product["name"], counted_qty=line.counted_qty,
                        system_qty=system_qty, variance_qty=variance, match_status=match_status,
                        resolution_status="PENDING", note=line.note, adjustment_qty=0,
                        cdatetime=cdatetime,
                    ))

                    summary.total_lines += 1
                    if match_status == "MATCH":
                        summary.matched += 1
                    elif match_status == "OVER":
                        summary.over += 1
                        summary.unresolved_variances += 1
                    else:
                        summary.short += 1
                        summary.unresolved_variances += 1

                result = StockTakeReadDto(
                    id=stock_take_id, loc_id=loc_id, location_type=data.location_type,
                    stock_take_number=stock_take_number, status="DRAFT",
                    description=data.description, cdatetime=cdatetime, created_by=created_by,
                    summary=summary, items=items_out,
                )
                return Respons(
                    success=True,
                    detail=f"Stock take {stock_take_number} created with {summary.total_lines} line(s), "
                           f"{summary.unresolved_variances} variance(s) to review",
                    data=result,
                )
        except Exception as e:
            logger.error(f"Failed to create stock take: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to create stock take", error=str(e))

    # =====================================================
    # LIST
    # =====================================================
    @staticmethod
    def get_stock_takes(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons:
        try:
            with DatabaseManager.transaction() as cursor:
                filters = ["tenant_id = %s", "org_id = %s", "bus_id = %s", "loc_id = %s",
                           "delete_status = 'NOT_DELETED'"]
                params: list = [tenant_id, org_id, bus_id, loc_id]
                if status:
                    filters.append("status = %s")
                    params.append(status)
                where = " AND ".join(filters)

                cursor.execute(
                    f"SELECT COUNT(*) AS count FROM {db_settings.MSG_STOCK_TAKES_TABLE} WHERE {where}",
                    tuple(params),
                )
                total = cursor.fetchone()["count"]

                cursor.execute(
                    f"""SELECT id, loc_id, location_type, stock_take_number, status, description,
                    completed_datetime, completed_by, cdatetime, created_by
                    FROM {db_settings.MSG_STOCK_TAKES_TABLE} WHERE {where}
                    ORDER BY cdatetime DESC LIMIT %s OFFSET %s""",
                    tuple(params + [size, (page - 1) * size]),
                )
                rows = cursor.fetchall()
                stock_takes = [StockTakeReadDto(**dict(r)) for r in rows]

                meta = PaginationMeta(
                    page=page, size=size, total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total,
                )
                return Respons(success=True, detail="Stock takes retrieved",
                               data={"stock_takes": stock_takes}, meta=meta)
        except Exception as e:
            logger.error(f"Failed to list stock takes: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to list stock takes", error=str(e))

    # =====================================================
    # DETAIL (variance report)
    # =====================================================
    @staticmethod
    def get_stock_take(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        stock_take_id: str,
        only_variances: bool = False,
    ) -> Respons:
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT id, loc_id, location_type, stock_take_number, status, description,
                    completed_datetime, completed_by, cdatetime, created_by
                    FROM {db_settings.MSG_STOCK_TAKES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, stock_take_id),
                )
                header = cursor.fetchone()
                if not header:
                    return Respons(success=False, detail="Stock take not found", error="STOCK_TAKE_NOT_FOUND")

                item_filter = ""
                if only_variances:
                    item_filter = " AND sti.match_status <> 'MATCH'"
                cursor.execute(
                    f"""SELECT sti.id, sti.stock_take_id, sti.product_id, p.name AS product_name,
                    sti.counted_qty, sti.system_qty, sti.variance_qty, sti.match_status,
                    sti.resolution_status, sti.note, sti.resolution_note, sti.adjustment_qty,
                    sti.adjustment_movement_id, sti.resolved_by, sti.resolved_datetime, sti.cdatetime
                    FROM {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE} sti
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON sti.product_id = p.id AND sti.tenant_id = p.tenant_id
                        AND sti.org_id = p.org_id AND sti.bus_id = p.bus_id
                    WHERE sti.tenant_id = %s AND sti.org_id = %s AND sti.bus_id = %s
                    AND sti.stock_take_id = %s{item_filter}
                    ORDER BY sti.match_status, p.name""",
                    (tenant_id, org_id, bus_id, stock_take_id),
                )
                items = [StockTakeItemReadDto(**dict(r)) for r in cursor.fetchall()]

                summary = StockTakeVarianceSummary(total_lines=len(items))
                for it in items:
                    if it.match_status == "MATCH":
                        summary.matched += 1
                    elif it.match_status == "OVER":
                        summary.over += 1
                    else:
                        summary.short += 1
                    if it.match_status != "MATCH" and it.resolution_status != "RESOLVED":
                        summary.unresolved_variances += 1

                result = StockTakeReadDto(**dict(header), summary=summary, items=items)
                return Respons(success=True, detail="Stock take retrieved", data=result)
        except Exception as e:
            logger.error(f"Failed to get stock take: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to get stock take", error=str(e))

    # =====================================================
    # COMPLETE (lock counting; does NOT change stock)
    # =====================================================
    @staticmethod
    def complete_stock_take(
        tenant_id: str, org_id: str, bus_id: str, stock_take_id: str, user_id: str
    ) -> Respons:
        dt = Helper.current_date_time()
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT status FROM {db_settings.MSG_STOCK_TAKES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, stock_take_id),
                )
                header = cursor.fetchone()
                if not header:
                    return Respons(success=False, detail="Stock take not found", error="STOCK_TAKE_NOT_FOUND")
                if header["status"] != "DRAFT":
                    return Respons(
                        success=False,
                        detail=f"Only DRAFT stock takes can be completed (current: {header['status']})",
                        error="INVALID_STATUS",
                    )

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_STOCK_TAKES_TABLE}
                    SET status = 'COMPLETED', completed_datetime = %s, completed_by = %s, updated_by = %s
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s""",
                    (dt["cdatetime"], user_id, user_id, tenant_id, org_id, bus_id, stock_take_id),
                )
            return StockTakesService.get_stock_take(tenant_id, org_id, bus_id, stock_take_id)
        except Exception as e:
            logger.error(f"Failed to complete stock take: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to complete stock take", error=str(e))

    # =====================================================
    # RESOLVE A LINE (optional explicit stock correction)
    # =====================================================
    @staticmethod
    def resolve_stock_take_item(
        data: ResolveStockTakeItemServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        stock_take_id: str,
        item_id: str,
        user_id: str,
    ) -> Respons:
        dt = Helper.current_date_time()
        cdate, ctime, cdatetime = dt["cdate"], dt["ctime"], dt["cdatetime"]
        try:
            with DatabaseManager.transaction() as cursor:
                # Load the line together with its parent's location context, plus any
                # adjustment already applied to it (the double-apply guard below).
                cursor.execute(
                    f"""SELECT sti.id, sti.product_id, sti.adjustment_qty, sti.adjustment_movement_id,
                        st.loc_id, st.location_type
                    FROM {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE} sti
                    JOIN {db_settings.MSG_STOCK_TAKES_TABLE} st
                        ON sti.stock_take_id = st.id AND sti.tenant_id = st.tenant_id
                        AND sti.org_id = st.org_id AND sti.bus_id = st.bus_id
                    WHERE sti.tenant_id = %s AND sti.org_id = %s AND sti.bus_id = %s
                    AND sti.stock_take_id = %s AND sti.id = %s""",
                    (tenant_id, org_id, bus_id, stock_take_id, item_id),
                )
                line = cursor.fetchone()
                if not line:
                    return Respons(success=False, detail="Stock take item not found", error="ITEM_NOT_FOUND")

                # Double-apply guard: if a stock change was already applied to this line,
                # never apply another one. The note/status can still be edited (send
                # adjustment_qty 0), but a second non-zero adjustment is refused so a loss
                # can't be deducted twice.
                already_adjusted = (line["adjustment_qty"] or 0) != 0
                if already_adjusted and data.adjustment_qty != 0:
                    return Respons(
                        success=False,
                        detail=f"This line was already corrected by {line['adjustment_qty']:+d}. "
                               "It can't be adjusted again — record any further change via Add Stock "
                               "or do a fresh stock take.",
                        error="ALREADY_ADJUSTED",
                    )

                # A stock take only corrects CONFIRMED LOSSES (shortages), and only in
                # place: it deducts from the location's per-delivery breakdown (FIFO,
                # oldest delivery first) and the location total, then logs the loss. It
                # must NEVER return stock to the purchase pool (purchase_batches.qty_remaining)
                # and must NEVER invent stock. A surplus is a real delivery that was not
                # recorded, so it is corrected through the normal Add Stock flow (which
                # captures cost/expiry on a proper batch).
                adjustment = data.adjustment_qty if data.resolution_status == "RESOLVED" else 0
                movement_id = None

                if adjustment > 0:
                    return Respons(
                        success=False,
                        detail="A surplus can't be added from a stock take. Record the missing "
                               "delivery via Add Stock so its cost and expiry are captured.",
                        error="USE_ADD_STOCK_FOR_SURPLUS",
                    )

                if adjustment < 0:
                    amount = abs(adjustment)
                    qty_table = _qty_table(line["location_type"])
                    location_type = line["location_type"]
                    loc_id = line["loc_id"]
                    product_id = line["product_id"]

                    # Location total must exist and be able to cover the loss
                    cursor.execute(
                        f"""SELECT current_qty FROM {qty_table}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND loc_id = %s AND product_id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, loc_id, product_id),
                    )
                    qty_row = cursor.fetchone()
                    if not qty_row:
                        return Respons(
                            success=False,
                            detail="Product has no stock record at this location to reduce.",
                            error="NO_STOCK_RECORD",
                        )
                    if qty_row["current_qty"] - amount < 0:
                        return Respons(
                            success=False,
                            detail=f"Reduction exceeds stock on hand (current {qty_row['current_qty']}, "
                                   f"reducing {amount}).",
                            error="NEGATIVE_STOCK",
                        )

                    # Pull the per-delivery breakdown at this location, oldest first (FIFO).
                    # batch_locations links to a product via its purchase batch.
                    cursor.execute(
                        f"""SELECT bl.id, bl.qty
                        FROM {db_settings.MSG_BATCH_LOCATIONS_TABLE} bl
                        JOIN {db_settings.MSG_PURCHASE_BATCHES_TABLE} pb
                            ON bl.purchase_batche_id = pb.id AND bl.tenant_id = pb.tenant_id
                            AND bl.org_id = pb.org_id AND bl.bus_id = pb.bus_id
                        WHERE bl.tenant_id = %s AND bl.org_id = %s AND bl.bus_id = %s
                        AND bl.loc_id = %s AND bl.location_type = %s AND pb.product_id = %s
                        AND bl.qty > 0
                        ORDER BY bl.cdatetime ASC""",
                        (tenant_id, org_id, bus_id, loc_id, location_type, product_id),
                    )
                    breakdown = cursor.fetchall()
                    if sum(b["qty"] for b in breakdown) < amount:
                        return Respons(
                            success=False,
                            detail="Stock breakdown by delivery is less than the amount to reduce; "
                                   "the data looks inconsistent. Please review before adjusting.",
                            error="BREAKDOWN_INSUFFICIENT",
                        )

                    # Deduct FIFO. We touch ONLY msg_batch_locations here — NOT
                    # purchase_batches.qty_remaining — so lost stock does not reappear
                    # in the available-to-distribute pool.
                    remaining = amount
                    for b in breakdown:
                        if remaining <= 0:
                            break
                        take = min(remaining, b["qty"])
                        cursor.execute(
                            f"""UPDATE {db_settings.MSG_BATCH_LOCATIONS_TABLE}
                            SET qty = qty - %s
                            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id = %s""",
                            (take, tenant_id, org_id, bus_id, b["id"]),
                        )
                        remaining -= take

                    # Reduce the location total
                    cursor.execute(
                        f"""UPDATE {qty_table} SET current_qty = current_qty - %s, updated_by = %s
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                        AND loc_id = %s AND product_id = %s""",
                        (amount, user_id, tenant_id, org_id, bus_id, loc_id, product_id),
                    )

                    # Log the loss (OUT). batch_id is NULL: the loss can span several FIFO
                    # deliveries; all rows for this correction share reference_id = stock_take_id.
                    movement_id = Helper.generate_unique_identifier(prefix="mov")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_PRODUCT_MOVEMENTS_TABLE}
                        (id, tenant_id, org_id, bus_id, product_id, batch_id, location_type, location_id,
                         movement_type, qty, reason, reference_id, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            movement_id, tenant_id, org_id, bus_id, product_id, None,
                            location_type, loc_id, "OUT", amount,
                            "STOCK_TAKE_ADJUSTMENT", stock_take_id, cdate, ctime, cdatetime, user_id,
                        ),
                    )

                # Persist the new correction only when one was applied this call; otherwise
                # keep whatever was recorded before so a note-only edit never erases it.
                if adjustment < 0:
                    final_adjustment, final_movement_id = adjustment, movement_id
                else:
                    final_adjustment = line["adjustment_qty"] or 0
                    final_movement_id = line["adjustment_movement_id"]

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE}
                    SET resolution_status = %s, resolution_note = %s, adjustment_qty = %s,
                        adjustment_movement_id = %s, resolved_by = %s, resolved_datetime = %s
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND stock_take_id = %s AND id = %s""",
                    (
                        data.resolution_status, data.resolution_note, final_adjustment, final_movement_id,
                        user_id if data.resolution_status == "RESOLVED" else None,
                        cdatetime if data.resolution_status == "RESOLVED" else None,
                        tenant_id, org_id, bus_id, stock_take_id, item_id,
                    ),
                )

            # Return the refreshed line
            detail = StockTakesService.get_stock_take(tenant_id, org_id, bus_id, stock_take_id)
            updated = None
            if detail.success and detail.data and detail.data.items:
                updated = next((i for i in detail.data.items if i.id == item_id), None)
            msg = "Item resolved" if data.resolution_status == "RESOLVED" else "Item updated"
            if adjustment != 0:
                msg += f" with stock adjustment of {adjustment:+d}"
            return Respons(success=True, detail=msg, data=updated)
        except Exception as e:
            logger.error(f"Failed to resolve stock take item: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to resolve stock take item", error=str(e))
