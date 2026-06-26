from typing import Optional, List
from src.entities.workflow_templates.workflow_templates_read_dto import (
    CreateWorkflowTemplateServiceReadDto,
    UpdateWorkflowTemplateServiceReadDto,
    GetWorkflowTemplateServiceReadDto,
    GetWorkflowTemplatesServiceReadDto,
    DeleteWorkflowTemplateServiceReadDto,
    WorkflowTemplateStatisticsServiceReadDto,
    TopUsedTemplateDto,
)
from src.entities.workflow_templates.workflow_templates_write_dto import (
    CreateWorkflowTemplateServiceWriteDto,
    UpdateWorkflowTemplateServiceWriteDto,
    DeleteWorkflowTemplateServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.entities.shared.wf_helpers import resolve_target_name
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("workflow_templates_service")


class WorkflowTemplatesService:
    """Service class for workflow template operations"""

    # ---------- internal helpers ----------

    @staticmethod
    def _insert_steps(cursor, tenant_id, org_id, bus_id, template_id, steps, created_by):
        """Insert step rows + their deps and targets. Maps client `ref` -> generated id."""
        ref_to_id = {}
        # First pass: create steps so all ids exist before wiring deps.
        for step in steps:
            step_id = Helper.generate_unique_identifier(prefix="wts")
            ref_to_id[step.ref] = step_id
            cursor.execute(
                f"""INSERT INTO {db_settings.MSG_WORKFLOW_TEMPLATE_STEPS_TABLE}
                (id, tenant_id, org_id, bus_id, template_id, name, description,
                 display_order, default_location_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    step_id, tenant_id, org_id, bus_id, template_id, step.name,
                    step.description, step.display_order, step.location_id, created_by,
                ),
            )
            for target in step.targets:
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_WORKFLOW_TEMPLATE_STEP_TARGETS_TABLE}
                    (id, tenant_id, org_id, bus_id, step_id, target_kind, target_type, target_id, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        Helper.generate_unique_identifier(prefix="wtt"),
                        tenant_id, org_id, bus_id, step_id,
                        target.target_kind, target.target_type, target.target_id, created_by,
                    ),
                )
        # Second pass: wire dependencies now that every ref has an id.
        for step in steps:
            step_id = ref_to_id[step.ref]
            for dep_ref in step.depends_on:
                dep_id = ref_to_id.get(dep_ref)
                if not dep_id:
                    raise ValueError(f"Step '{step.ref}' depends on unknown ref '{dep_ref}'")
                if dep_id == step_id:
                    raise ValueError(f"Step '{step.ref}' cannot depend on itself")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_WORKFLOW_TEMPLATE_STEP_DEPS_TABLE}
                    (id, tenant_id, org_id, bus_id, step_id, depends_on_step_id, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        Helper.generate_unique_identifier(prefix="wtd"),
                        tenant_id, org_id, bus_id, step_id, dep_id, created_by,
                    ),
                )

    @staticmethod
    def _load_template(cursor, tenant_id, org_id, bus_id, template_id) -> Optional[dict]:
        """Assemble a template dict with nested steps/deps/targets, or None."""
        cursor.execute(
            f"""SELECT t.*, creator.fullname AS created_by_name,
                       updater.fullname AS updated_by_name
            FROM {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE} t
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON t.created_by = creator.id AND t.tenant_id = creator.tenant_id
            LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} updater ON t.updated_by = updater.id AND t.tenant_id = updater.tenant_id
            WHERE t.id = %s AND t.tenant_id = %s AND t.org_id = %s AND t.bus_id = %s
            AND t.delete_status = 'NOT_DELETED'""",
            (template_id, tenant_id, org_id, bus_id),
        )
        template = cursor.fetchone()
        if not template:
            return None
        tpl = dict(template)
        tpl["created_by"] = tpl.get("created_by_name")
        tpl["updated_by"] = tpl.get("updated_by_name")
        tpl["deleted_by"] = None

        cursor.execute(
            f"""SELECT * FROM {db_settings.MSG_WORKFLOW_TEMPLATE_STEPS_TABLE}
            WHERE template_id = %s AND tenant_id = %s
            ORDER BY display_order ASC""",
            (template_id, tenant_id),
        )
        steps = [dict(r) for r in cursor.fetchall()]
        step_ids = [s["id"] for s in steps]

        deps_by_step = {sid: [] for sid in step_ids}
        targets_by_step = {sid: [] for sid in step_ids}
        if step_ids:
            cursor.execute(
                f"""SELECT step_id, depends_on_step_id FROM {db_settings.MSG_WORKFLOW_TEMPLATE_STEP_DEPS_TABLE}
                WHERE tenant_id = %s AND step_id = ANY(%s)""",
                (tenant_id, step_ids),
            )
            for r in cursor.fetchall():
                deps_by_step.setdefault(r["step_id"], []).append(r["depends_on_step_id"])

            cursor.execute(
                f"""SELECT * FROM {db_settings.MSG_WORKFLOW_TEMPLATE_STEP_TARGETS_TABLE}
                WHERE tenant_id = %s AND step_id = ANY(%s)""",
                (tenant_id, step_ids),
            )
            for r in cursor.fetchall():
                tr = dict(r)
                tr["target_name"] = resolve_target_name(cursor, tenant_id, tr["target_type"], tr["target_id"])
                targets_by_step.setdefault(r["step_id"], []).append({
                    "id": tr["id"],
                    "target_kind": tr["target_kind"],
                    "target_type": tr["target_type"],
                    "target_id": tr["target_id"],
                    "target_name": tr["target_name"],
                })

        for s in steps:
            s["depends_on"] = deps_by_step.get(s["id"], [])
            s["targets"] = targets_by_step.get(s["id"], [])
        tpl["steps"] = steps
        return tpl

    # ---------- public API ----------

    @staticmethod
    def create_template(
        data: CreateWorkflowTemplateServiceWriteDto,
        tenant_id: str, org_id: str, bus_id: str, created_by: str,
    ) -> Respons[CreateWorkflowTemplateServiceReadDto]:
        try:
            refs = [s.ref for s in data.steps]
            if len(refs) != len(set(refs)):
                return Respons(success=False, detail="Duplicate step refs in payload", error="VALIDATION_ERROR")

            with DatabaseManager.transaction() as cursor:
                template_id = Helper.generate_unique_identifier(prefix="wtpl")
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE}
                    (id, tenant_id, org_id, bus_id, name, template_type, description, is_active, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (template_id, tenant_id, org_id, bus_id, data.name, data.template_type,
                     data.description, data.is_active, created_by),
                )
                WorkflowTemplatesService._insert_steps(
                    cursor, tenant_id, org_id, bus_id, template_id, data.steps, created_by)

                tpl = WorkflowTemplatesService._load_template(cursor, tenant_id, org_id, bus_id, template_id)
                result = CreateWorkflowTemplateServiceReadDto(**tpl)

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-tasks", resource_id=template_id,
                        action="create", old_data=None, new_data=tpl,
                        description=f"Workflow template {template_id} created",
                        performed_by=created_by, org_id=org_id, bus_id=bus_id, loc_id=None, cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Workflow template created successfully", data=[result])
        except ValueError as e:
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error creating workflow template: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to create workflow template: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def update_template(
        data: UpdateWorkflowTemplateServiceWriteDto, template_id: str,
        tenant_id: str, org_id: str, bus_id: str, updated_by: str,
    ) -> Respons[UpdateWorkflowTemplateServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                existing = WorkflowTemplatesService._load_template(cursor, tenant_id, org_id, bus_id, template_id)
                if not existing:
                    raise ValueError("Workflow template not found")

                fields, params = [], []
                if data.name is not None:
                    fields.append("name = %s"); params.append(data.name)
                if data.template_type is not None:
                    fields.append("template_type = %s"); params.append(data.template_type)
                if data.description is not None:
                    fields.append("description = %s"); params.append(data.description)
                if data.is_active is not None:
                    fields.append("is_active = %s"); params.append(data.is_active)

                if fields:
                    fields.append("updated_by = %s"); params.append(updated_by)
                    params.extend([template_id, tenant_id, org_id, bus_id])
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE}
                        SET {', '.join(fields)}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        tuple(params),
                    )

                # Full replace of steps when provided.
                if data.steps is not None:
                    refs = [s.ref for s in data.steps]
                    if len(refs) != len(set(refs)):
                        raise ValueError("Duplicate step refs in payload")
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_WORKFLOW_TEMPLATE_STEPS_TABLE}
                        WHERE template_id = %s AND tenant_id = %s""",
                        (template_id, tenant_id),
                    )  # deps & targets cascade via FK
                    WorkflowTemplatesService._insert_steps(
                        cursor, tenant_id, org_id, bus_id, template_id, data.steps, updated_by)

                tpl = WorkflowTemplatesService._load_template(cursor, tenant_id, org_id, bus_id, template_id)
                result = UpdateWorkflowTemplateServiceReadDto(**tpl)

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-tasks", resource_id=template_id,
                        action="update", old_data=existing, new_data=tpl,
                        description=f"Workflow template {template_id} updated",
                        performed_by=updated_by, org_id=org_id, bus_id=bus_id, loc_id=None, cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Workflow template updated successfully", data=[result])
        except ValueError as e:
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error updating workflow template: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update workflow template: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_template(
        template_id: str, tenant_id: str, org_id: str, bus_id: str,
    ) -> Respons[GetWorkflowTemplateServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                tpl = WorkflowTemplatesService._load_template(cursor, tenant_id, org_id, bus_id, template_id)
                if not tpl:
                    return Respons(success=False, detail="Workflow template not found", error="NOT_FOUND")
                return Respons(success=True, detail="Workflow template retrieved successfully",
                               data=[GetWorkflowTemplateServiceReadDto(**tpl)])
        except Exception as e:
            logger.error(f"Error getting workflow template: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get workflow template: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_templates(
        tenant_id: str, org_id: str, bus_id: str,
        template_type: Optional[str] = None, is_active: Optional[bool] = None,
        search: Optional[str] = None, page: int = 1, size: int = 10,
    ) -> Respons[list[GetWorkflowTemplatesServiceReadDto]]:
        try:
            with DatabaseManager.transaction() as cursor:
                where = ["tenant_id = %s", "org_id = %s", "bus_id = %s", "delete_status = 'NOT_DELETED'"]
                params = [tenant_id, org_id, bus_id]
                if template_type:
                    where.append("template_type = %s"); params.append(template_type)
                if is_active is not None:
                    where.append("is_active = %s"); params.append(is_active)
                if search:
                    where.append("name ILIKE %s"); params.append(f"%{search}%")
                where_clause = " AND ".join(where)

                cursor.execute(
                    f"SELECT COUNT(*) AS total FROM {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE} WHERE {where_clause}",
                    tuple(params),
                )
                total = (cursor.fetchone() or {}).get("total", 0)

                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT id FROM {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE}
                    WHERE {where_clause} ORDER BY cdatetime DESC LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                ids = [r["id"] for r in cursor.fetchall()]
                items = []
                for tid in ids:
                    tpl = WorkflowTemplatesService._load_template(cursor, tenant_id, org_id, bus_id, tid)
                    if tpl:
                        items.append(GetWorkflowTemplatesServiceReadDto(**tpl))

                pagination = PaginationMeta(
                    page=page, size=size, total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total,
                )
                return Respons(success=True, detail="Workflow templates retrieved successfully",
                               data=items, pagination=pagination)
        except Exception as e:
            logger.error(f"Error listing workflow templates: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to list workflow templates: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def delete_template(
        data: DeleteWorkflowTemplateServiceWriteDto,
        tenant_id: str, org_id: str, bus_id: str, deleted_by: str,
    ) -> Respons[DeleteWorkflowTemplateServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                existing = WorkflowTemplatesService._load_template(cursor, tenant_id, org_id, bus_id, data.template_id)
                if not existing:
                    raise ValueError("Workflow template not found")
                # Soft delete the template; steps/deps/targets remain but the
                # template is filtered out by delete_status.
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE}
                    SET delete_status = 'DELETED', is_active = false, deleted_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (deleted_by, data.template_id, tenant_id, org_id, bus_id),
                )
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-tasks", resource_id=data.template_id,
                        action="delete", old_data=existing, new_data=None,
                        description=f"Workflow template {data.template_id} deleted",
                        performed_by=deleted_by, org_id=org_id, bus_id=bus_id, loc_id=None, cursor=cursor,
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Workflow template deleted successfully",
                               data=[DeleteWorkflowTemplateServiceReadDto(
                                   template_id=data.template_id, message="Workflow template deleted successfully")])
        except ValueError as e:
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error deleting workflow template: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to delete workflow template: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_statistics(
        tenant_id: str, org_id: str, bus_id: str,
    ) -> Respons[WorkflowTemplateStatisticsServiceReadDto]:
        """Aggregate workflow-template statistics for the business."""
        try:
            with DatabaseManager.transaction() as cursor:
                scope = "tenant_id = %s AND org_id = %s AND bus_id = %s AND delete_status = 'NOT_DELETED'"
                params = (tenant_id, org_id, bus_id)

                cursor.execute(
                    f"""SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE is_active) AS active,
                        COUNT(*) FILTER (WHERE NOT is_active) AS inactive
                    FROM {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE} WHERE {scope}""",
                    params,
                )
                row = cursor.fetchone() or {}
                total = row.get("total", 0) or 0

                cursor.execute(
                    f"""SELECT template_type, COUNT(*) AS c
                    FROM {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE} WHERE {scope}
                    GROUP BY template_type""",
                    params,
                )
                by_type = {r["template_type"]: r["c"] for r in cursor.fetchall()}

                cursor.execute(
                    f"""SELECT COUNT(*) AS total_steps
                    FROM {db_settings.MSG_WORKFLOW_TEMPLATE_STEPS_TABLE} s
                    JOIN {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE} t
                        ON t.id = s.template_id AND t.tenant_id = s.tenant_id
                    WHERE t.{scope}""",
                    params,
                )
                total_steps = (cursor.fetchone() or {}).get("total_steps", 0) or 0

                cursor.execute(
                    f"""SELECT t.id AS template_id, t.name, COUNT(tk.id) AS jobs_created
                    FROM {db_settings.MSG_WORKFLOW_TEMPLATES_TABLE} t
                    LEFT JOIN {db_settings.MSG_TASKS_TABLE} tk
                        ON tk.template_id = t.id AND tk.tenant_id = t.tenant_id AND tk.delete_status = 'NOT_DELETED'
                    WHERE t.{scope}
                    GROUP BY t.id, t.name
                    ORDER BY jobs_created DESC, t.name ASC
                    LIMIT 5""",
                    params,
                )
                top = [TopUsedTemplateDto(template_id=r["template_id"], name=r["name"],
                                          jobs_created=r["jobs_created"] or 0) for r in cursor.fetchall()]

                dto = WorkflowTemplateStatisticsServiceReadDto(
                    total_templates=total,
                    active=row.get("active", 0) or 0,
                    inactive=row.get("inactive", 0) or 0,
                    by_type=by_type,
                    total_steps=total_steps,
                    avg_steps_per_template=round(total_steps / total, 2) if total else 0,
                    top_used_templates=top,
                )
                return Respons(success=True, detail="Workflow template statistics retrieved", data=[dto])
        except Exception as e:
            logger.error(f"Error getting workflow template statistics: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get statistics: {str(e)}", error="INTERNAL_ERROR")
