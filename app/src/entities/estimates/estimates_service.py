import json
from typing import Optional, Any, List, Dict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from src.entities.estimates.estimates_read_dto import (
    CreateEstimateServiceReadDto,
    UpdateEstimateServiceReadDto,
    GetEstimateServiceReadDto,
    GetEstimateListServiceReadDto,
    UpdateEstimateStatusServiceReadDto,
    DeleteEstimateServiceReadDto,
    GetEstimateStatisticsServiceReadDto,
    EstimateItemReadBase,
)
from src.entities.estimates.estimates_write_dto import (
    CreateEstimateServiceWriteDto,
    UpdateEstimateServiceWriteDto,
    UpdateEstimateStatusServiceWriteDto,
    DeleteEstimateServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from src.utils.formula_evaluator import evaluate_formula, build_context, FormulaError
from trovesuite.utils import Helper

logger = get_logger("estimates_service")

# Statuses an estimate may move to from its current status.
_ALLOWED_TRANSITIONS = {
    "DRAFT": {"SENT", "ACCEPTED", "REJECTED", "EXPIRED"},
    "SENT": {"ACCEPTED", "REJECTED", "EXPIRED", "DRAFT"},
    "ACCEPTED": {"CONVERTED", "REJECTED"},
    "REJECTED": {"DRAFT"},
    "EXPIRED": {"DRAFT"},
    "CONVERTED": set(),
}


def _round_money(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _parse_json(value: Any, fallback: Any):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return fallback
    return fallback


class PricingError(ValueError):
    """Raised when an estimate cannot be priced against its template snapshot."""
    pass


class EstimatesService:
    """Service class for estimates (instances created from a template)."""

    # ------------------------------------------------------------------
    # Pricing engine
    # ------------------------------------------------------------------
    @staticmethod
    def _price(snapshot: dict, items: List[Any]) -> Dict[str, Any]:
        """Price a list of input items against a template snapshot.

        `snapshot` is {line_item_defs: [...], modifiers: {...}}.
        `items` are EstimateLineItemInput-like objects (have line_def_key,
        quantity, field_values, label). Returns priced lines + totals.
        Raises PricingError on unknown line keys or bad formulas.
        """
        defs_by_key = {d["key"]: d for d in snapshot.get("line_item_defs", [])}
        modifiers = snapshot.get("modifiers", {}) or {}

        priced_lines: List[dict] = []
        subtotal = 0.0

        for item in items:
            line_key = item.line_def_key
            line_def = defs_by_key.get(line_key)
            if not line_def:
                raise PricingError(f"Unknown line item key '{line_key}' for this template")

            # Validate required fields are present.
            for fdef in line_def.get("fields", []):
                if fdef.get("required") and item.field_values.get(fdef["key"]) in (None, ""):
                    raise PricingError(
                        f"Missing required field '{fdef.get('label', fdef['key'])}' for line '{line_def.get('name', line_key)}'"
                    )

            context = build_context(item.field_values, line_def.get("fields", []))
            try:
                unit_amount = evaluate_formula(line_def["formula"], context)
            except FormulaError as exc:
                raise PricingError(f"Could not price line '{line_def.get('name', line_key)}': {exc}")

            line_total = _round_money(unit_amount * float(item.quantity))
            subtotal += line_total

            priced_lines.append({
                "line_def_key": line_key,
                "name": line_def.get("name"),
                "label": item.label,
                "quantity": float(item.quantity),
                "field_values": item.field_values,
                "unit_amount": _round_money(unit_amount),
                "computed_amount": line_total,
            })

        subtotal = _round_money(subtotal)
        markup_amount = _round_money(subtotal * float(modifiers.get("markup_percent", 0)) / 100.0)
        after_markup = subtotal + markup_amount
        discount_amount = _round_money(after_markup * float(modifiers.get("discount_percent", 0)) / 100.0)
        taxable = after_markup - discount_amount
        tax_amount = _round_money(taxable * float(modifiers.get("tax_percent", 0)) / 100.0)
        grand_total = _round_money(taxable + tax_amount)

        min_charge = float(modifiers.get("min_charge", 0) or 0)
        if grand_total < min_charge:
            grand_total = _round_money(min_charge)

        return {
            "lines": priced_lines,
            "subtotal": subtotal,
            "markup_amount": markup_amount,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "grand_total": grand_total,
            "currency": modifiers.get("currency"),
            "valid_days": int(modifiers.get("valid_days", 30) or 0),
        }

    @staticmethod
    def _generate_estimate_number(cursor, tenant_id, org_id, bus_id, loc_id) -> str:
        """Systematic estimate number: EST-YYYYMMDD-NNN."""
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"EST-{today}"
        cursor.execute(
            f"""SELECT estimate_number FROM {db_settings.MSG_ESTIMATES_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
            AND estimate_number LIKE %s
            ORDER BY estimate_number DESC LIMIT 1""",
            (tenant_id, org_id, bus_id, loc_id, f"{prefix}-%"),
        )
        last = cursor.fetchone()
        next_seq = 1
        if last and last.get("estimate_number"):
            try:
                next_seq = int(last["estimate_number"].split("-")[-1]) + 1
            except (ValueError, IndexError):
                next_seq = 1
        return f"{prefix}-{next_seq:03d}"

    @staticmethod
    def _load_items(cursor, estimate_id, tenant_id) -> List[EstimateItemReadBase]:
        cursor.execute(
            f"""SELECT * FROM {db_settings.MSG_ESTIMATE_ITEMS_TABLE}
            WHERE estimate_id = %s AND tenant_id = %s
            ORDER BY cdatetime ASC, id ASC""",
            (estimate_id, tenant_id),
        )
        rows = cursor.fetchall() or []
        items = []
        for r in rows:
            d = dict(r)
            d["field_values"] = _parse_json(d.get("field_values"), {})
            items.append(EstimateItemReadBase(
                id=d["id"],
                estimate_id=d["estimate_id"],
                line_def_key=d.get("line_def_key"),
                name=d.get("name"),
                label=d.get("label"),
                quantity=float(d.get("quantity") or 1.0),
                field_values=d["field_values"],
                unit_amount=float(d.get("unit_amount") or 0.0),
                computed_amount=float(d.get("computed_amount") or 0.0),
            ))
        return items

    @staticmethod
    def _hydrate_estimate(cursor, row: dict, tenant_id: str) -> dict:
        d = dict(row)
        d["items"] = EstimatesService._load_items(cursor, d["id"], tenant_id)
        return d

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    @staticmethod
    def create_estimate(
        data: CreateEstimateServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str,
    ) -> Respons[CreateEstimateServiceReadDto]:
        """Create an estimate from a template, pricing each captured line."""
        logger.info(
            "Processing estimate creation",
            extra={"extra_fields": {"tenant_id": tenant_id, "template_id": data.template_id, "items": len(data.items)}},
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Load the active template.
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (data.template_id, tenant_id, org_id, bus_id),
                )
                template = cursor.fetchone()
                if not template:
                    return Respons(success=False, detail="Estimate template not found", error="NOT_FOUND")

                snapshot = {
                    "line_item_defs": _parse_json(template.get("line_item_defs"), []),
                    "modifiers": _parse_json(template.get("modifiers"), {}) or {},
                }
                template_version = int(template.get("version") or 1)

                # Optional customer validation + name.
                customer_name = None
                if data.customer_id:
                    cursor.execute(
                        f"""SELECT fullname FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (data.customer_id, tenant_id, org_id, bus_id),
                    )
                    crow = cursor.fetchone()
                    if not crow:
                        return Respons(success=False, detail="Customer not found", error="NOT_FOUND")
                    customer_name = crow.get("fullname")

                # Price.
                try:
                    priced = EstimatesService._price(snapshot, data.items)
                except PricingError as exc:
                    return Respons(success=False, detail=str(exc), error="VALIDATION_ERROR")

                valid_until = None
                if priced["valid_days"]:
                    valid_until = (cdatetime + timedelta(days=priced["valid_days"])).date()

                estimate_id = Helper.generate_unique_identifier(prefix="est")
                estimate_number = EstimatesService._generate_estimate_number(cursor, tenant_id, org_id, bus_id, loc_id)

                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_ESTIMATES_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, estimate_number,
                     template_id, template_version, template_snapshot,
                     customer_id, title, notes, status, currency,
                     subtotal, markup_amount, discount_amount, tax_amount, grand_total,
                     valid_until, delete_status, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        estimate_id, tenant_id, org_id, bus_id, loc_id, estimate_number,
                        data.template_id, template_version, json.dumps(snapshot),
                        data.customer_id, data.title, data.notes, "DRAFT", priced["currency"],
                        priced["subtotal"], priced["markup_amount"], priced["discount_amount"],
                        priced["tax_amount"], priced["grand_total"],
                        valid_until, "NOT_DELETED", cdate, ctime, cdatetime, created_by,
                    ),
                )
                estimate_row = cursor.fetchone()
                if not estimate_row:
                    raise ValueError("Failed to create estimate")

                EstimatesService._insert_items(cursor, priced["lines"], estimate_id, tenant_id, org_id, bus_id, loc_id, cdate, ctime, cdatetime, created_by)

                result = EstimatesService._hydrate_estimate(cursor, estimate_row, tenant_id)
                result["customer_name"] = customer_name

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-estimate",
                        resource_id=estimate_id,
                        action="create",
                        old_data=None,
                        new_data=dict(estimate_row),
                        description=f"Estimate {estimate_number} created",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Estimate created: {estimate_id} ({estimate_number})")
                return Respons(success=True, detail="Estimate created successfully", data=[CreateEstimateServiceReadDto(**result)])

        except ValueError as e:
            logger.error(f"Validation error creating estimate: {e}")
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error creating estimate: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to create estimate: {e}", error="INTERNAL_ERROR")

    @staticmethod
    def _insert_items(cursor, lines, estimate_id, tenant_id, org_id, bus_id, loc_id, cdate, ctime, cdatetime, created_by):
        for line in lines:
            item_id = Helper.generate_unique_identifier(prefix="esti")
            cursor.execute(
                f"""INSERT INTO {db_settings.MSG_ESTIMATE_ITEMS_TABLE}
                (id, tenant_id, org_id, bus_id, loc_id, estimate_id, line_def_key,
                 name, label, quantity, field_values, unit_amount, computed_amount,
                 cdate, ctime, cdatetime, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    item_id, tenant_id, org_id, bus_id, loc_id, estimate_id, line["line_def_key"],
                    line["name"], line["label"], line["quantity"], json.dumps(line["field_values"]),
                    line["unit_amount"], line["computed_amount"],
                    cdate, ctime, cdatetime, created_by,
                ),
            )

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------
    @staticmethod
    def get_estimate(estimate_id, tenant_id, org_id, bus_id) -> Respons[GetEstimateServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT e.*, c.fullname as customer_name
                    FROM {db_settings.MSG_ESTIMATES_TABLE} e
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON e.customer_id = c.id AND e.tenant_id = c.tenant_id
                    WHERE e.id = %s AND e.tenant_id = %s AND e.org_id = %s
                    AND e.bus_id = %s AND e.delete_status = 'NOT_DELETED'""",
                    (estimate_id, tenant_id, org_id, bus_id),
                )
                row = cursor.fetchone()
                if not row:
                    return Respons(success=False, detail="Estimate not found", error="NOT_FOUND")
                result = EstimatesService._hydrate_estimate(cursor, row, tenant_id)
                return Respons(success=True, detail="Estimate retrieved successfully", data=[GetEstimateServiceReadDto(**result)])
        except Exception as e:
            logger.error(f"Error getting estimate: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get estimate: {e}", error="INTERNAL_ERROR")

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------
    @staticmethod
    def list_estimates(
        tenant_id, org_id, bus_id,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        template_id: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetEstimateListServiceReadDto]]:
        try:
            with DatabaseManager.transaction() as cursor:
                where = ["e.tenant_id = %s", "e.org_id = %s", "e.bus_id = %s", "e.delete_status = 'NOT_DELETED'"]
                params = [tenant_id, org_id, bus_id]
                if status:
                    where.append("e.status = %s")
                    params.append(status)
                if customer_id:
                    where.append("e.customer_id = %s")
                    params.append(customer_id)
                if template_id:
                    where.append("e.template_id = %s")
                    params.append(template_id)
                where_clause = " AND ".join(where)

                cursor.execute(f"SELECT COUNT(*) as total FROM {db_settings.MSG_ESTIMATES_TABLE} e WHERE {where_clause}", tuple(params))
                total_row = cursor.fetchone()
                total = total_row["total"] if total_row else 0

                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT e.*, c.fullname as customer_name
                    FROM {db_settings.MSG_ESTIMATES_TABLE} e
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON e.customer_id = c.id AND e.tenant_id = c.tenant_id
                    WHERE {where_clause}
                    ORDER BY e.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                rows = cursor.fetchall()
                result = [GetEstimateListServiceReadDto(**EstimatesService._hydrate_estimate(cursor, r, tenant_id)) for r in rows]

                pagination = PaginationMeta(page=page, size=size, total=total, has_next=(page * size) < total)
                return Respons(success=True, detail="Estimates retrieved successfully", data=result, pagination=pagination)
        except Exception as e:
            logger.error(f"Error listing estimates: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to list estimates: {e}", error="INTERNAL_ERROR")

    # ------------------------------------------------------------------
    # Update (edit a draft and re-price against the stored snapshot)
    # ------------------------------------------------------------------
    @staticmethod
    def update_estimate(
        data: UpdateEstimateServiceWriteDto,
        estimate_id, tenant_id, org_id, bus_id, loc_id, updated_by,
    ) -> Respons[UpdateEstimateServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (estimate_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Estimate not found", error="NOT_FOUND")
                old_data = dict(existing)

                if old_data.get("status") not in ("DRAFT", "SENT"):
                    return Respons(success=False, detail=f"Only DRAFT or SENT estimates can be edited (current: {old_data.get('status')})", error="INVALID_STATE")

                cdate = Helper.current_date_time()["cdate"]
                ctime = Helper.current_date_time()["ctime"]
                cdatetime = Helper.current_date_time()["cdatetime"]

                set_fields = []
                params = []
                if data.customer_id is not None:
                    set_fields.append("customer_id = %s")
                    params.append(data.customer_id)
                if data.title is not None:
                    set_fields.append("title = %s")
                    params.append(data.title)
                if data.notes is not None:
                    set_fields.append("notes = %s")
                    params.append(data.notes)

                # Re-price if items provided, against the SNAPSHOT (not the live template).
                if data.items is not None:
                    snapshot = _parse_json(old_data.get("template_snapshot"), {}) or {}
                    try:
                        priced = EstimatesService._price(snapshot, data.items)
                    except PricingError as exc:
                        return Respons(success=False, detail=str(exc), error="VALIDATION_ERROR")

                    set_fields += [
                        "subtotal = %s", "markup_amount = %s", "discount_amount = %s",
                        "tax_amount = %s", "grand_total = %s", "currency = %s",
                    ]
                    params += [
                        priced["subtotal"], priced["markup_amount"], priced["discount_amount"],
                        priced["tax_amount"], priced["grand_total"], priced["currency"],
                    ]

                    cursor.execute(
                        f"DELETE FROM {db_settings.MSG_ESTIMATE_ITEMS_TABLE} WHERE estimate_id = %s AND tenant_id = %s",
                        (estimate_id, tenant_id),
                    )
                    EstimatesService._insert_items(cursor, priced["lines"], estimate_id, tenant_id, org_id, bus_id, loc_id, cdate, ctime, cdatetime, updated_by)

                if not set_fields:
                    return Respons(success=False, detail="No fields to update", error="VALIDATION_ERROR")

                set_fields.append("updated_by = %s")
                params.append(updated_by)
                params += [estimate_id, tenant_id, org_id, bus_id]

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_ESTIMATES_TABLE}
                    SET {', '.join(set_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_row = cursor.fetchone()
                result = EstimatesService._hydrate_estimate(cursor, updated_row, tenant_id)

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-estimate", resource_id=estimate_id,
                        action="update", old_data=old_data, new_data=dict(updated_row),
                        description=f"Estimate {estimate_id} updated", performed_by=updated_by,
                        org_id=org_id, bus_id=bus_id, loc_id=loc_id, cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Estimate updated successfully", data=[UpdateEstimateServiceReadDto(**result)])
        except Exception as e:
            logger.error(f"Error updating estimate: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update estimate: {e}", error="INTERNAL_ERROR")

    # ------------------------------------------------------------------
    # Update status
    # ------------------------------------------------------------------
    @staticmethod
    def update_status(
        data: UpdateEstimateStatusServiceWriteDto,
        estimate_id, tenant_id, org_id, bus_id, loc_id, updated_by,
    ) -> Respons[UpdateEstimateStatusServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (estimate_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Estimate not found", error="NOT_FOUND")

                current = existing.get("status")
                target = data.status
                if target != current and target not in _ALLOWED_TRANSITIONS.get(current, set()):
                    return Respons(success=False, detail=f"Cannot move estimate from {current} to {target}", error="INVALID_STATE")

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_ESTIMATES_TABLE}
                    SET status = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    (target, updated_by, estimate_id, tenant_id, org_id, bus_id),
                )
                updated_row = cursor.fetchone()
                result = EstimatesService._hydrate_estimate(cursor, updated_row, tenant_id)

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-estimate", resource_id=estimate_id,
                        action="update", old_data=dict(existing), new_data=dict(updated_row),
                        description=f"Estimate {estimate_id} status {current} -> {target}",
                        performed_by=updated_by, org_id=org_id, bus_id=bus_id, loc_id=loc_id, cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail=f"Estimate status updated to {target}", data=[UpdateEstimateStatusServiceReadDto(**result)])
        except Exception as e:
            logger.error(f"Error updating estimate status: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update estimate status: {e}", error="INTERNAL_ERROR")

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    @staticmethod
    def delete_estimate(
        data: DeleteEstimateServiceWriteDto,
        tenant_id, org_id, bus_id, loc_id, deleted_by,
    ) -> Respons[DeleteEstimateServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.estimate_id, tenant_id, org_id, bus_id),
                )
                row = cursor.fetchone()
                if not row:
                    return Respons(success=False, detail="Estimate not found", error="NOT_FOUND")

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-estimate", resource_id=data.estimate_id,
                        action="delete", old_data=dict(row), new_data=None,
                        description=f"Estimate {data.estimate_id} deleted", performed_by=deleted_by,
                        org_id=org_id, bus_id=bus_id, loc_id=loc_id, cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_ESTIMATES_TABLE}
                    SET delete_status = 'DELETED', deleted_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (deleted_by, data.estimate_id, tenant_id, org_id, bus_id),
                )
                return Respons(
                    success=True,
                    detail="Estimate deleted successfully",
                    data=[DeleteEstimateServiceReadDto(estimate_id=data.estimate_id, message="Estimate deleted")],
                )
        except Exception as e:
            logger.error(f"Error deleting estimate: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to delete estimate: {e}", error="INTERNAL_ERROR")

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    @staticmethod
    def get_statistics(
        tenant_id, org_id, bus_id,
    ) -> Respons[GetEstimateStatisticsServiceReadDto]:
        """Status counts and value totals for estimates in the org/business."""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT
                        COUNT(*) as total_estimates,
                        COUNT(CASE WHEN status = 'DRAFT' THEN 1 END) as draft,
                        COUNT(CASE WHEN status = 'SENT' THEN 1 END) as sent,
                        COUNT(CASE WHEN status = 'ACCEPTED' THEN 1 END) as accepted,
                        COUNT(CASE WHEN status = 'REJECTED' THEN 1 END) as rejected,
                        COUNT(CASE WHEN status = 'EXPIRED' THEN 1 END) as expired,
                        COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) as converted,
                        COALESCE(SUM(grand_total), 0) as total_value,
                        COALESCE(SUM(CASE WHEN status = 'ACCEPTED' THEN grand_total ELSE 0 END), 0) as accepted_value,
                        COALESCE(SUM(CASE WHEN status IN ('DRAFT', 'SENT') THEN grand_total ELSE 0 END), 0) as pipeline_value
                    FROM {db_settings.MSG_ESTIMATES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id),
                )
                row = cursor.fetchone() or {}
                stats = GetEstimateStatisticsServiceReadDto(
                    total_estimates=int(row.get("total_estimates") or 0),
                    draft=int(row.get("draft") or 0),
                    sent=int(row.get("sent") or 0),
                    accepted=int(row.get("accepted") or 0),
                    rejected=int(row.get("rejected") or 0),
                    expired=int(row.get("expired") or 0),
                    converted=int(row.get("converted") or 0),
                    total_value=_round_money(row.get("total_value") or 0),
                    accepted_value=_round_money(row.get("accepted_value") or 0),
                    pipeline_value=_round_money(row.get("pipeline_value") or 0),
                )
                return Respons(success=True, detail="Estimate statistics retrieved successfully", data=[stats])
        except Exception as e:
            logger.error(f"Error getting estimate statistics: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get estimate statistics: {e}", error="INTERNAL_ERROR")
