import json
from typing import Optional, Any
from src.entities.estimate_templates.estimate_templates_read_dto import (
    CreateEstimateTemplateServiceReadDto,
    UpdateEstimateTemplateServiceReadDto,
    GetEstimateTemplateServiceReadDto,
    GetEstimateTemplateListServiceReadDto,
    DeleteEstimateTemplateServiceReadDto,
)
from src.entities.estimate_templates.estimate_templates_write_dto import (
    CreateEstimateTemplateServiceWriteDto,
    UpdateEstimateTemplateServiceWriteDto,
    DeleteEstimateTemplateServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("estimate_templates_service")


def _parse_json(value: Any, fallback: Any):
    """JSONB columns may come back as a parsed object or a raw string depending on
    the driver config; normalise to a Python object."""
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


def _hydrate(row: dict) -> dict:
    """Turn a raw DB row into a dict ready for the read DTO."""
    data = dict(row)
    data["line_item_defs"] = _parse_json(data.get("line_item_defs"), [])
    data["modifiers"] = _parse_json(data.get("modifiers"), {}) or {}
    return data


class EstimateTemplatesService:
    """Service class for estimate template (per-domain blueprint) operations."""

    @staticmethod
    def create_template(
        data: CreateEstimateTemplateServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        created_by: str,
    ) -> Respons[CreateEstimateTemplateServiceReadDto]:
        """Create a new estimate template."""
        logger.info(
            "Processing estimate template creation",
            extra={"extra_fields": {"tenant_id": tenant_id, "org_id": org_id, "bus_id": bus_id, "name": data.name}},
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s
                    AND name = %s AND delete_status = 'NOT_DELETED'""",
                    (tenant_id, org_id, bus_id, data.name),
                )
                if cursor.fetchone():
                    return Respons(
                        success=False,
                        detail=f"An estimate template named '{data.name}' already exists",
                        error="DUPLICATE_ENTRY",
                    )

                template_id = Helper.generate_unique_identifier(prefix="estpl")
                line_defs_json = json.dumps([li.model_dump() for li in data.line_item_defs])
                modifiers_json = json.dumps(data.modifiers.model_dump())

                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    (id, tenant_id, org_id, bus_id, name, domain, description, version,
                     line_item_defs, modifiers, delete_status, is_active,
                     cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        template_id, tenant_id, org_id, bus_id,
                        data.name, data.domain, data.description, 1,
                        line_defs_json, modifiers_json, 'NOT_DELETED', True,
                        cdate, ctime, cdatetime, created_by,
                    ),
                )
                created_row = cursor.fetchone()
                if not created_row:
                    raise ValueError("Failed to create estimate template")

                template_read = CreateEstimateTemplateServiceReadDto(**_hydrate(created_row))

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-estimate-template",
                        resource_id=template_id,
                        action="create",
                        old_data=None,
                        new_data=dict(created_row),
                        description=f"Estimate template {template_id} created",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(f"Estimate template created: {template_id}")
                return Respons(success=True, detail="Estimate template created successfully", data=[template_read])

        except ValueError as e:
            logger.error(f"Validation error creating estimate template: {e}")
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error creating estimate template: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to create estimate template: {e}", error="INTERNAL_ERROR")

    @staticmethod
    def update_template(
        data: UpdateEstimateTemplateServiceWriteDto,
        template_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str,
    ) -> Respons[UpdateEstimateTemplateServiceReadDto]:
        """Update an estimate template. Changing the definition bumps `version`."""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (template_id, tenant_id, org_id, bus_id),
                )
                existing = cursor.fetchone()
                if not existing:
                    return Respons(success=False, detail="Estimate template not found", error="NOT_FOUND")
                old_data = dict(existing)

                update_fields = []
                params = []
                definition_changed = False

                if data.name is not None:
                    update_fields.append("name = %s")
                    params.append(data.name)
                if data.domain is not None:
                    update_fields.append("domain = %s")
                    params.append(data.domain)
                if data.description is not None:
                    update_fields.append("description = %s")
                    params.append(data.description)
                if data.is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(data.is_active)
                if data.line_item_defs is not None:
                    update_fields.append("line_item_defs = %s")
                    params.append(json.dumps([li.model_dump() for li in data.line_item_defs]))
                    definition_changed = True
                if data.modifiers is not None:
                    update_fields.append("modifiers = %s")
                    params.append(json.dumps(data.modifiers.model_dump()))
                    definition_changed = True

                if not update_fields:
                    return Respons(success=False, detail="No fields to update", error="VALIDATION_ERROR")

                if definition_changed:
                    update_fields.append("version = version + 1")

                update_fields.append("updated_by = %s")
                params.append(updated_by)
                params.extend([template_id, tenant_id, org_id, bus_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
                    RETURNING *""",
                    tuple(params),
                )
                updated_row = cursor.fetchone()
                if not updated_row:
                    raise ValueError("Failed to update estimate template")

                template_read = UpdateEstimateTemplateServiceReadDto(**_hydrate(updated_row))

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-estimate-template",
                        resource_id=template_id,
                        action="update",
                        old_data=old_data,
                        new_data=dict(updated_row),
                        description=f"Estimate template {template_id} updated",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Estimate template updated successfully", data=[template_read])

        except ValueError as e:
            logger.error(f"Validation error updating estimate template: {e}")
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error updating estimate template: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update estimate template: {e}", error="INTERNAL_ERROR")

    @staticmethod
    def get_template(
        template_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetEstimateTemplateServiceReadDto]:
        """Get a single estimate template by ID."""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (template_id, tenant_id, org_id, bus_id),
                )
                row = cursor.fetchone()
                if not row:
                    return Respons(success=False, detail="Estimate template not found", error="NOT_FOUND")
                return Respons(
                    success=True,
                    detail="Estimate template retrieved successfully",
                    data=[GetEstimateTemplateServiceReadDto(**_hydrate(row))],
                )
        except Exception as e:
            logger.error(f"Error getting estimate template: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get estimate template: {e}", error="INTERNAL_ERROR")

    @staticmethod
    def list_templates(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        domain: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetEstimateTemplateListServiceReadDto]]:
        """List estimate templates with filters and pagination."""
        try:
            with DatabaseManager.transaction() as cursor:
                where = ["tenant_id = %s", "org_id = %s", "bus_id = %s", "delete_status = 'NOT_DELETED'"]
                params = [tenant_id, org_id, bus_id]

                if domain:
                    where.append("domain = %s")
                    params.append(domain)
                if is_active is not None:
                    where.append("is_active = %s")
                    params.append(is_active)
                if search:
                    where.append("name ILIKE %s")
                    params.append(f"%{search}%")

                where_clause = " AND ".join(where)

                cursor.execute(
                    f"SELECT COUNT(*) as total FROM {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE} WHERE {where_clause}",
                    tuple(params),
                )
                total_row = cursor.fetchone()
                total = total_row["total"] if total_row else 0

                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    WHERE {where_clause}
                    ORDER BY cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                rows = cursor.fetchall()
                result = [GetEstimateTemplateListServiceReadDto(**_hydrate(r)) for r in rows]

                pagination = PaginationMeta(page=page, size=size, total=total, has_next=(page * size) < total)
                return Respons(success=True, detail="Estimate templates retrieved successfully", data=result, pagination=pagination)
        except Exception as e:
            logger.error(f"Error listing estimate templates: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to list estimate templates: {e}", error="INTERNAL_ERROR")

    @staticmethod
    def delete_template(
        data: DeleteEstimateTemplateServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str,
    ) -> Respons[DeleteEstimateTemplateServiceReadDto]:
        """Soft-delete an estimate template."""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s
                    AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
                    (data.template_id, tenant_id, org_id, bus_id),
                )
                row = cursor.fetchone()
                if not row:
                    return Respons(success=False, detail="Estimate template not found", error="NOT_FOUND")

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-estimate-template",
                        resource_id=data.template_id,
                        action="delete",
                        old_data=dict(row),
                        new_data=None,
                        description=f"Estimate template {data.template_id} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id="",
                        cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_ESTIMATE_TEMPLATES_TABLE}
                    SET delete_status = 'DELETED', is_active = FALSE, deleted_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (deleted_by, data.template_id, tenant_id, org_id, bus_id),
                )

                return Respons(
                    success=True,
                    detail="Estimate template deleted successfully",
                    data=[DeleteEstimateTemplateServiceReadDto(template_id=data.template_id, message="Estimate template deleted")],
                )
        except Exception as e:
            logger.error(f"Error deleting estimate template: {e}", exc_info=True)
            return Respons(success=False, detail=f"Failed to delete estimate template: {e}", error="INTERNAL_ERROR")
