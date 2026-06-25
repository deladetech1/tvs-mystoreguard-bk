from typing import Optional, List
from src.entities.stock_takes.stock_takes_write_dto import (
    CreateStockTakeServiceWriteDto,
    ResolveStockTakeItemServiceWriteDto,
)
from src.entities.stock_takes.stock_takes_read_dto import (
    StockTakeReadDto,
    StockTakeItemReadDto,
    StockTakeVarianceSummary,
    StockTakeStatisticsReadDto,
    CurrencyMoneyDto,
    TopShortageProductDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.filemanager.fmg_service import FileUploadService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("stock_takes_service")

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg")


def _product_image_urls(cursor, tenant_id: str, org_id: str, bus_id: str, product_id: str) -> list:
    """Presigned URLs for a product's image documents (same source as the products API)."""
    cursor.execute(
        f"""SELECT dp.file_name, dp.document_path
        FROM {db_settings.MSG_PRODUCT_DOCUMENT_IDS_TABLE} pdi
        INNER JOIN {db_settings.MSG_DOCUMENT_PATHS_TABLE} dp
            ON pdi.document_id = dp.id AND pdi.tenant_id = dp.tenant_id
            AND pdi.org_id = dp.org_id AND pdi.bus_id = dp.bus_id
        WHERE pdi.tenant_id = %s AND pdi.org_id = %s AND pdi.bus_id = %s
        AND pdi.product_id = %s
        AND pdi.delete_status = 'NOT_DELETED' AND pdi.is_active = true
        AND dp.delete_status = 'NOT_DELETED' AND dp.is_active = true""",
        (tenant_id, org_id, bus_id, product_id),
    )
    urls = []
    for row in cursor.fetchall():
        path = row.get("document_path")
        name = (row.get("file_name") or "").lower()
        if not path or not name.endswith(_IMAGE_EXTS):
            continue
        url = FileUploadService._get_file_presigned_url(
            container_name=db_settings.MYSTOREGUARD_FILES_CONTAINER,
            blob_path=path,
            expiry_hours=24,
        )
        if url:
            urls.append(url)
    return urls


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

                    variance_value = (variance * line.unit_price) if line.unit_price is not None else None

                    item_id = Helper.generate_unique_identifier(prefix="sti")
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE}
                        (id, tenant_id, org_id, bus_id, stock_take_id, product_id,
                         counted_qty, system_qty, variance_qty, unit_price,
                         currency_id, currency_name, currency_symbol, match_status, resolution_status,
                         note, adjustment_qty, cdate, ctime, cdatetime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            item_id, tenant_id, org_id, bus_id, stock_take_id, line.product_id,
                            line.counted_qty, system_qty, variance, line.unit_price,
                            line.currency_id, line.currency_name, line.currency_symbol, match_status, "PENDING",
                            line.note, 0, cdate, ctime, cdatetime,
                        ),
                    )

                    items_out.append(StockTakeItemReadDto(
                        id=item_id, stock_take_id=stock_take_id, product_id=line.product_id,
                        product_name=product["name"],
                        image_urls=_product_image_urls(cursor, tenant_id, org_id, bus_id, line.product_id),
                        counted_qty=line.counted_qty,
                        system_qty=system_qty, variance_qty=variance,
                        unit_price=line.unit_price, variance_value=variance_value,
                        currency_id=line.currency_id, currency_name=line.currency_name,
                        currency_symbol=line.currency_symbol,
                        match_status=match_status,
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
                    description=data.description,
                    cdatetime=cdatetime, created_by=created_by,
                    summary=summary, items=items_out,
                )
                return Respons(
                    success=True,
                    detail=f"Stock take {stock_take_number} created with {summary.total_lines} line(s), "
                           f"{summary.unresolved_variances} variance(s) to review",
                    data=[result],
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
        location_type: Optional[str] = None,
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
                if location_type:
                    filters.append("location_type = %s")
                    params.append(location_type)
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

                pagination = PaginationMeta(
                    page=page, size=size, total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total,
                )
                return Respons(success=True, detail="Stock takes retrieved",
                               data=stock_takes, pagination=pagination)
        except Exception as e:
            logger.error(f"Failed to list stock takes: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to list stock takes", error=str(e))

    # =====================================================
    # STATISTICS (aggregate for a location)
    # =====================================================
    @staticmethod
    def get_statistics(
        tenant_id: str, org_id: str, bus_id: str, loc_id: str,
        location_type: Optional[str] = None,
    ) -> Respons:
        # Optional location_type filter, applied to the header table directly in the
        # counts query and via the `st` alias in the line/top queries.
        base = [tenant_id, org_id, bus_id, loc_id]
        lt_header = lt_st = ""
        if location_type:
            lt_header = " AND location_type = %s"
            lt_st = " AND st.location_type = %s"
            base.append(location_type)
        params_h = tuple(base)
        params_s = tuple(base)
        try:
            with DatabaseManager.transaction() as cursor:
                # Stock-take header counts by status
                cursor.execute(
                    f"""SELECT
                        COUNT(*) AS total_stock_takes,
                        COUNT(*) FILTER (WHERE status = 'DRAFT') AS draft,
                        COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed,
                        COUNT(*) FILTER (WHERE status = 'CANCELLED') AS cancelled
                    FROM {db_settings.MSG_STOCK_TAKES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND delete_status = 'NOT_DELETED'{lt_header}""",
                    params_h,
                )
                hc = cursor.fetchone() or {}

                # Line-level counts (currency-independent).
                cursor.execute(
                    f"""SELECT
                        COUNT(*) AS total_lines,
                        COUNT(*) FILTER (WHERE sti.match_status = 'MATCH') AS matched,
                        COUNT(*) FILTER (WHERE sti.match_status = 'OVER') AS over_count,
                        COUNT(*) FILTER (WHERE sti.match_status = 'SHORT') AS short_count,
                        COUNT(*) FILTER (WHERE sti.match_status <> 'MATCH'
                                         AND sti.resolution_status <> 'RESOLVED') AS unresolved
                    FROM {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE} sti
                    JOIN {db_settings.MSG_STOCK_TAKES_TABLE} st
                        ON sti.stock_take_id = st.id AND sti.tenant_id = st.tenant_id
                        AND sti.org_id = st.org_id AND sti.bus_id = st.bus_id
                    WHERE st.tenant_id = %s AND st.org_id = %s AND st.bus_id = %s AND st.loc_id = %s
                    AND st.delete_status = 'NOT_DELETED'{lt_st}""",
                    params_s,
                )
                lc = cursor.fetchone() or {}

                # Money roll-ups GROUPED PER CURRENCY — values are never summed across
                # currencies. Only priced lines (unit_price IS NOT NULL) contribute.
                cursor.execute(
                    f"""SELECT sti.currency_id, sti.currency_name, sti.currency_symbol,
                        -COALESCE(SUM(CASE WHEN sti.variance_qty < 0
                                           THEN sti.variance_qty * sti.unit_price END), 0) AS shortage_value,
                        COALESCE(SUM(CASE WHEN sti.variance_qty > 0
                                          THEN sti.variance_qty * sti.unit_price END), 0) AS overage_value,
                        COALESCE(SUM(sti.variance_qty * sti.unit_price), 0) AS net_value,
                        -COALESCE(SUM(sti.adjustment_qty * sti.unit_price), 0) AS corrected_value
                    FROM {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE} sti
                    JOIN {db_settings.MSG_STOCK_TAKES_TABLE} st
                        ON sti.stock_take_id = st.id AND sti.tenant_id = st.tenant_id
                        AND sti.org_id = st.org_id AND sti.bus_id = st.bus_id
                    WHERE st.tenant_id = %s AND st.org_id = %s AND st.bus_id = %s AND st.loc_id = %s
                    AND st.delete_status = 'NOT_DELETED' AND sti.unit_price IS NOT NULL{lt_st}
                    GROUP BY sti.currency_id, sti.currency_name, sti.currency_symbol
                    ORDER BY shortage_value DESC""",
                    params_s,
                )
                money_by_currency = [
                    CurrencyMoneyDto(
                        currency_id=r.get("currency_id"),
                        currency_name=r.get("currency_name"),
                        currency_symbol=r.get("currency_symbol"),
                        total_shortage_value=float(r["shortage_value"] or 0),
                        total_overage_value=float(r["overage_value"] or 0),
                        net_variance_value=float(r["net_value"] or 0),
                        total_corrected_value=float(r["corrected_value"] or 0),
                    )
                    for r in cursor.fetchall()
                ]

                # Worst offenders by shortage value, per product+currency.
                cursor.execute(
                    f"""SELECT sti.product_id, p.name AS product_name,
                        sti.currency_id, sti.currency_name, sti.currency_symbol,
                        COALESCE(SUM(sti.variance_qty), 0) AS short_qty_signed,
                        -COALESCE(SUM(sti.variance_qty * sti.unit_price), 0) AS shortage_value
                    FROM {db_settings.MSG_STOCK_TAKE_ITEMS_TABLE} sti
                    JOIN {db_settings.MSG_STOCK_TAKES_TABLE} st
                        ON sti.stock_take_id = st.id AND sti.tenant_id = st.tenant_id
                        AND sti.org_id = st.org_id AND sti.bus_id = st.bus_id
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON sti.product_id = p.id AND sti.tenant_id = p.tenant_id
                        AND sti.org_id = p.org_id AND sti.bus_id = p.bus_id
                    WHERE st.tenant_id = %s AND st.org_id = %s AND st.bus_id = %s AND st.loc_id = %s
                    AND st.delete_status = 'NOT_DELETED' AND sti.variance_qty < 0{lt_st}
                    GROUP BY sti.product_id, p.name, sti.currency_id, sti.currency_name, sti.currency_symbol
                    ORDER BY shortage_value DESC, short_qty_signed ASC
                    LIMIT 5""",
                    params_s,
                )
                top = [
                    TopShortageProductDto(
                        product_id=r["product_id"],
                        product_name=r.get("product_name"),
                        short_qty=abs(int(r["short_qty_signed"] or 0)),
                        shortage_value=float(r["shortage_value"] or 0),
                        currency_id=r.get("currency_id"),
                        currency_name=r.get("currency_name"),
                        currency_symbol=r.get("currency_symbol"),
                    )
                    for r in cursor.fetchall()
                ]

                total_lines = int(lc.get("total_lines") or 0)
                matched = int(lc.get("matched") or 0)
                accuracy = round((matched / total_lines) * 100, 2) if total_lines else 0.0

                stats = StockTakeStatisticsReadDto(
                    total_stock_takes=int(hc.get("total_stock_takes") or 0),
                    draft=int(hc.get("draft") or 0),
                    completed=int(hc.get("completed") or 0),
                    cancelled=int(hc.get("cancelled") or 0),
                    total_lines=total_lines,
                    matched=matched,
                    over=int(lc.get("over_count") or 0),
                    short=int(lc.get("short_count") or 0),
                    unresolved_variances=int(lc.get("unresolved") or 0),
                    accuracy_rate=accuracy,
                    money_by_currency=money_by_currency,
                    top_shortage_products=top,
                )
                return Respons(success=True, detail="Stock take statistics retrieved", data=[stats])
        except Exception as e:
            logger.error(f"Failed to get stock take statistics: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to get stock take statistics", error=str(e))

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
                    sti.counted_qty, sti.system_qty, sti.variance_qty, sti.unit_price,
                    sti.currency_id, sti.currency_name, sti.currency_symbol, sti.match_status,
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
                items = []
                for r in cursor.fetchall():
                    row = dict(r)
                    price = row.get("unit_price")
                    row["unit_price"] = float(price) if price is not None else None
                    row["variance_value"] = (
                        row["variance_qty"] * row["unit_price"] if price is not None else None
                    )
                    row["image_urls"] = _product_image_urls(
                        cursor, tenant_id, org_id, bus_id, row["product_id"]
                    )
                    items.append(StockTakeItemReadDto(**row))

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
                return Respons(success=True, detail="Stock take retrieved", data=[result])
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

            # Return the refreshed line. get_stock_take wraps its result in a list (data[0]).
            detail = StockTakesService.get_stock_take(tenant_id, org_id, bus_id, stock_take_id)
            updated = None
            if detail.success and detail.data and detail.data[0].items:
                updated = next((i for i in detail.data[0].items if i.id == item_id), None)
            msg = "Item resolved" if data.resolution_status == "RESOLVED" else "Item updated"
            if adjustment != 0:
                msg += f" with stock adjustment of {adjustment:+d}"
            return Respons(success=True, detail=msg, data=[updated] if updated else None)
        except Exception as e:
            logger.error(f"Failed to resolve stock take item: {e}", exc_info=True)
            return Respons(success=False, detail="Failed to resolve stock take item", error=str(e))
