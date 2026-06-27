from typing import Optional, List
from src.entities.tasks.tasks_read_dto import (
    CreateTaskServiceReadDto,
    UpdateTaskServiceReadDto,
    GetTaskServiceReadDto,
    GetTasksServiceReadDto,
    StepActionServiceReadDto,
    TaskNotificationSettingsServiceReadDto,
    TaskStatisticsServiceReadDto,
)
from src.entities.tasks.tasks_write_dto import (
    CreateTaskServiceWriteDto,
    UpdateTaskServiceWriteDto,
    TaskNotificationSettingsWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.entities.shared.wf_helpers import (
    resolve_target_name, expand_targets_to_user_ids, user_in_group, resolve_group_members,
)
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("tasks_service")

T = db_settings  # alias for brevity in SQL strings


class TasksService:
    """Service for tasks (multi-step jobs) and their step-level workflow engine."""

    # =================================================================
    # INTERNAL: step source assembly (from template or ad-hoc payload)
    # =================================================================

    @staticmethod
    def _step_source_from_template(cursor, tenant_id, org_id, bus_id, template_id) -> Optional[List[dict]]:
        """Return a normalized step list copied from a template, or None if not found."""
        cursor.execute(
            f"""SELECT 1 FROM {T.MSG_WORKFLOW_TEMPLATES_TABLE}
            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s
            AND delete_status = 'NOT_DELETED'""",
            (template_id, tenant_id, org_id, bus_id),
        )
        if not cursor.fetchone():
            return None

        cursor.execute(
            f"""SELECT * FROM {T.MSG_WORKFLOW_TEMPLATE_STEPS_TABLE}
            WHERE template_id = %s AND tenant_id = %s ORDER BY display_order ASC""",
            (template_id, tenant_id),
        )
        steps = [dict(r) for r in cursor.fetchall()]
        step_ids = [s["id"] for s in steps]
        deps = {sid: [] for sid in step_ids}
        targets = {sid: [] for sid in step_ids}
        if step_ids:
            cursor.execute(
                f"""SELECT step_id, depends_on_step_id FROM {T.MSG_WORKFLOW_TEMPLATE_STEP_DEPS_TABLE}
                WHERE tenant_id = %s AND step_id = ANY(%s)""",
                (tenant_id, step_ids),
            )
            for r in cursor.fetchall():
                deps.setdefault(r["step_id"], []).append(r["depends_on_step_id"])
            cursor.execute(
                f"""SELECT step_id, target_kind, target_type, target_id
                FROM {T.MSG_WORKFLOW_TEMPLATE_STEP_TARGETS_TABLE}
                WHERE tenant_id = %s AND step_id = ANY(%s)""",
                (tenant_id, step_ids),
            )
            for r in cursor.fetchall():
                targets.setdefault(r["step_id"], []).append({
                    "target_kind": r["target_kind"], "target_type": r["target_type"], "target_id": r["target_id"],
                })
        return [{
            "ref": s["id"],
            "name": s["name"],
            "description": s.get("description"),
            "display_order": s.get("display_order", 0),
            "location_id": s.get("default_location_id"),
            "depends_on": deps.get(s["id"], []),
            "targets": targets.get(s["id"], []),
        } for s in steps]

    @staticmethod
    def _step_source_from_payload(steps) -> List[dict]:
        return [{
            "ref": s.ref,
            "name": s.name,
            "description": s.description,
            "display_order": s.display_order,
            "location_id": s.location_id,
            "depends_on": list(s.depends_on),
            "targets": [{"target_kind": t.target_kind, "target_type": t.target_type, "target_id": t.target_id}
                        for t in s.targets],
        } for s in steps]

    @staticmethod
    def _insert_task_steps(cursor, tenant_id, org_id, bus_id, task_id, step_source, created_by) -> dict:
        """Insert step rows + deps + targets; returns ref->id map."""
        refs = [s["ref"] for s in step_source]
        if len(refs) != len(set(refs)):
            raise ValueError("Duplicate step refs")
        ref_to_id = {}
        for s in step_source:
            step_id = Helper.generate_unique_identifier(prefix="tsk_step")
            ref_to_id[s["ref"]] = step_id
            cursor.execute(
                f"""INSERT INTO {T.MSG_TASK_STEPS_TABLE}
                (id, tenant_id, org_id, bus_id, task_id, name, description, display_order, location_id, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', %s)""",
                (step_id, tenant_id, org_id, bus_id, task_id, s["name"], s["description"],
                 s["display_order"], s["location_id"], created_by),
            )
            for t in s["targets"]:
                cursor.execute(
                    f"""INSERT INTO {T.MSG_TASK_STEP_TARGETS_TABLE}
                    (id, tenant_id, org_id, bus_id, step_id, target_kind, target_type, target_id, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (Helper.generate_unique_identifier(prefix="tst"), tenant_id, org_id, bus_id, step_id,
                     t["target_kind"], t["target_type"], t["target_id"], created_by),
                )
        for s in step_source:
            step_id = ref_to_id[s["ref"]]
            for dep_ref in s["depends_on"]:
                dep_id = ref_to_id.get(dep_ref)
                if not dep_id:
                    raise ValueError(f"Step '{s['ref']}' depends on unknown ref '{dep_ref}'")
                if dep_id == step_id:
                    raise ValueError(f"Step '{s['ref']}' cannot depend on itself")
                cursor.execute(
                    f"""INSERT INTO {T.MSG_TASK_STEP_DEPS_TABLE}
                    (id, tenant_id, org_id, bus_id, step_id, depends_on_step_id, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (Helper.generate_unique_identifier(prefix="tsd"), tenant_id, org_id, bus_id,
                     step_id, dep_id, created_by),
                )
        return ref_to_id

    # =================================================================
    # INTERNAL: engine helpers
    # =================================================================

    @staticmethod
    def _step_prereqs_complete(cursor, tenant_id, step_id) -> bool:
        cursor.execute(
            f"""SELECT COUNT(*) AS pending
            FROM {T.MSG_TASK_STEP_DEPS_TABLE} d
            JOIN {T.MSG_TASK_STEPS_TABLE} s ON s.id = d.depends_on_step_id AND s.tenant_id = d.tenant_id
            WHERE d.tenant_id = %s AND d.step_id = %s AND s.status <> 'COMPLETED'""",
            (tenant_id, step_id),
        )
        row = cursor.fetchone()
        return (row["pending"] if row else 0) == 0

    @staticmethod
    def _step_targets(cursor, tenant_id, step_id, kind: Optional[str] = None) -> List[dict]:
        sql = (f"SELECT target_kind, target_type, target_id FROM {T.MSG_TASK_STEP_TARGETS_TABLE} "
               f"WHERE tenant_id = %s AND step_id = %s")
        params = [tenant_id, step_id]
        if kind:
            sql += " AND target_kind = %s"
            params.append(kind)
        cursor.execute(sql, tuple(params))
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def _user_matches_targets(cursor, tenant_id, step_id, user_id, kind) -> bool:
        for t in TasksService._step_targets(cursor, tenant_id, step_id, kind):
            if t["target_type"] == "USER" and t["target_id"] == user_id:
                return True
            if t["target_type"] == "GROUP" and user_in_group(cursor, tenant_id, t["target_id"], user_id):
                return True
        return False

    @staticmethod
    def _enqueue(cursor, tenant_id, org_id, bus_id, task_id, step_id, user_ids, kind, created_by):
        for uid in set(user_ids):
            if not uid:
                continue
            cursor.execute(
                f"""INSERT INTO {T.MSG_TASK_NOTIFICATIONS_TABLE}
                (id, tenant_id, org_id, bus_id, task_id, step_id, recipient_user_id, kind, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', %s)""",
                (Helper.generate_unique_identifier(prefix="tnf"), tenant_id, org_id, bus_id,
                 task_id, step_id, uid, kind, created_by),
            )

    @staticmethod
    def _has_ready_notification(cursor, tenant_id, step_id) -> bool:
        cursor.execute(
            f"""SELECT 1 FROM {T.MSG_TASK_NOTIFICATIONS_TABLE}
            WHERE tenant_id = %s AND step_id = %s AND kind IN ('ASSIGNED', 'READY') LIMIT 1""",
            (tenant_id, step_id),
        )
        return cursor.fetchone() is not None

    @staticmethod
    def _notify_step_assignees(cursor, tenant_id, org_id, bus_id, task_id, step_id, created_by, kind="READY"):
        targets = TasksService._step_targets(cursor, tenant_id, step_id, "ASSIGNEE")
        user_ids = expand_targets_to_user_ids(cursor, tenant_id, targets)
        TasksService._enqueue(cursor, tenant_id, org_id, bus_id, task_id, step_id, user_ids, kind, created_by)

    @staticmethod
    def _maybe_complete_task(cursor, tenant_id, org_id, bus_id, task_id):
        cursor.execute(
            f"""SELECT COUNT(*) AS open_steps FROM {T.MSG_TASK_STEPS_TABLE}
            WHERE tenant_id = %s AND task_id = %s AND status NOT IN ('COMPLETED', 'CANCELLED')""",
            (tenant_id, task_id),
        )
        if (cursor.fetchone() or {}).get("open_steps", 0) == 0:
            cursor.execute(
                f"""UPDATE {T.MSG_TASKS_TABLE} SET status = 'COMPLETED'
                WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND status = 'ACTIVE'""",
                (task_id, tenant_id, org_id, bus_id),
            )

    @staticmethod
    def _load_task(cursor, tenant_id, org_id, bus_id, task_id) -> Optional[dict]:
        cursor.execute(
            f"""SELECT t.*, creator.fullname AS created_by_name, updater.fullname AS updated_by_name,
                       c.fullname AS customer_name
            FROM {T.MSG_TASKS_TABLE} t
            LEFT JOIN {T.CORE_PLATFORM_USERS_TABLE} creator ON t.created_by = creator.id AND t.tenant_id = creator.tenant_id
            LEFT JOIN {T.CORE_PLATFORM_USERS_TABLE} updater ON t.updated_by = updater.id AND t.tenant_id = updater.tenant_id
            LEFT JOIN {T.MSG_CUSTOMERS_TABLE} c ON t.customer_id = c.id AND t.tenant_id = c.tenant_id AND t.org_id = c.org_id AND t.bus_id = c.bus_id
            WHERE t.id = %s AND t.tenant_id = %s AND t.org_id = %s AND t.bus_id = %s
            AND t.delete_status = 'NOT_DELETED'""",
            (task_id, tenant_id, org_id, bus_id),
        )
        task = cursor.fetchone()
        if not task:
            return None
        td = dict(task)
        td["created_by"] = td.get("created_by_name")
        td["updated_by"] = td.get("updated_by_name")
        td["deleted_by"] = None

        cursor.execute(
            f"""SELECT s.*, claimer.fullname AS claimed_by_name
            FROM {T.MSG_TASK_STEPS_TABLE} s
            LEFT JOIN {T.CORE_PLATFORM_USERS_TABLE} claimer ON s.claimed_by = claimer.id AND s.tenant_id = claimer.tenant_id
            WHERE s.task_id = %s AND s.tenant_id = %s ORDER BY s.display_order ASC""",
            (task_id, tenant_id),
        )
        steps = [dict(r) for r in cursor.fetchall()]
        step_ids = [s["id"] for s in steps]
        deps = {sid: [] for sid in step_ids}
        targets = {sid: [] for sid in step_ids}
        if step_ids:
            cursor.execute(
                f"""SELECT step_id, depends_on_step_id FROM {T.MSG_TASK_STEP_DEPS_TABLE}
                WHERE tenant_id = %s AND step_id = ANY(%s)""",
                (tenant_id, step_ids),
            )
            for r in cursor.fetchall():
                deps.setdefault(r["step_id"], []).append(r["depends_on_step_id"])
            cursor.execute(
                f"""SELECT * FROM {T.MSG_TASK_STEP_TARGETS_TABLE}
                WHERE tenant_id = %s AND step_id = ANY(%s)""",
                (tenant_id, step_ids),
            )
            for r in cursor.fetchall():
                tr = dict(r)
                members = (resolve_group_members(cursor, tenant_id, tr["target_id"])
                           if tr["target_type"] == "GROUP" else [])
                targets.setdefault(r["step_id"], []).append({
                    "id": tr["id"], "target_kind": tr["target_kind"], "target_type": tr["target_type"],
                    "target_id": tr["target_id"],
                    "target_name": resolve_target_name(cursor, tenant_id, tr["target_type"], tr["target_id"]),
                    "members": members,
                })
        for s in steps:
            s["depends_on"] = deps.get(s["id"], [])
            s["targets"] = targets.get(s["id"], [])
            s["claimed_by_name"] = s.get("claimed_by_name")
            s["claimed_by"] = s.get("claimed_by")
            s["is_available"] = (
                s["status"] in ("TODO", "IN_PROGRESS")
                and TasksService._step_prereqs_complete(cursor, tenant_id, s["id"])
            )
        td["steps"] = steps
        return td

    # =================================================================
    # PUBLIC: create / update / get / list / cancel
    # =================================================================

    @staticmethod
    def create_task(
        data: CreateTaskServiceWriteDto, tenant_id: str, org_id: str, bus_id: str, created_by: str,
    ) -> Respons[CreateTaskServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                if data.steps:
                    step_source = TasksService._step_source_from_payload(data.steps)
                else:
                    step_source = TasksService._step_source_from_template(
                        cursor, tenant_id, org_id, bus_id, data.template_id)
                    if step_source is None:
                        return Respons(success=False, detail="Template not found", error="NOT_FOUND")
                if not step_source:
                    return Respons(success=False, detail="A job must have at least one step", error="VALIDATION_ERROR")

                task_id = Helper.generate_unique_identifier(prefix="tsk")
                cursor.execute(
                    f"""INSERT INTO {T.MSG_TASKS_TABLE}
                    (id, tenant_id, org_id, bus_id, title, description, task_type, customer_id,
                     template_id, origin_location_id, status, due_date, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s)""",
                    (task_id, tenant_id, org_id, bus_id, data.title, data.description, data.task_type,
                     data.customer_id, data.template_id, data.origin_location_id, data.due_date, created_by),
                )
                ref_to_id = TasksService._insert_task_steps(
                    cursor, tenant_id, org_id, bus_id, task_id, step_source, created_by)

                # Activate steps that have no prerequisites -> notify their assignees.
                for s in step_source:
                    if not s["depends_on"]:
                        TasksService._notify_step_assignees(
                            cursor, tenant_id, org_id, bus_id, task_id, ref_to_id[s["ref"]], created_by, kind="ASSIGNED")

                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-tasks", resource_id=task_id, action="create",
                        old_data=None, new_data=task, description=f"Task {task_id} created",
                        performed_by=created_by, org_id=org_id, bus_id=bus_id, loc_id=None, cursor=cursor)
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(success=True, detail="Task created successfully",
                               data=[CreateTaskServiceReadDto(**task)])
        except ValueError as e:
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to create task: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def update_task(
        data: UpdateTaskServiceWriteDto, task_id: str, tenant_id: str, org_id: str, bus_id: str, updated_by: str,
    ) -> Respons[UpdateTaskServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                existing = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                if not existing:
                    raise ValueError("Task not found")

                fields, params = [], []
                for col, val in [
                    ("title", data.title), ("task_type", data.task_type), ("description", data.description),
                    ("customer_id", data.customer_id), ("origin_location_id", data.origin_location_id),
                    ("due_date", data.due_date),
                ]:
                    if val is not None:
                        fields.append(f"{col} = %s"); params.append(val)
                if not fields:
                    raise ValueError("No fields to update")
                fields.append("updated_by = %s"); params.append(updated_by)
                params.extend([task_id, tenant_id, org_id, bus_id])
                cursor.execute(
                    f"""UPDATE {T.MSG_TASKS_TABLE} SET {', '.join(fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    tuple(params),
                )
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Task updated successfully",
                               data=[UpdateTaskServiceReadDto(**task)])
        except ValueError as e:
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update task: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_task(task_id, tenant_id, org_id, bus_id) -> Respons[GetTaskServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                if not task:
                    return Respons(success=False, detail="Task not found", error="NOT_FOUND")
                return Respons(success=True, detail="Task retrieved successfully",
                               data=[GetTaskServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error getting task: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get task: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def get_tasks(
        tenant_id, org_id, bus_id, status: Optional[str] = None, task_type: Optional[str] = None,
        template_id: Optional[str] = None, customer_id: Optional[str] = None, search: Optional[str] = None,
        page: int = 1, size: int = 10,
    ) -> Respons[list[GetTasksServiceReadDto]]:
        try:
            with DatabaseManager.transaction() as cursor:
                where = ["tenant_id = %s", "org_id = %s", "bus_id = %s", "delete_status = 'NOT_DELETED'"]
                params = [tenant_id, org_id, bus_id]
                if status:
                    where.append("status = %s"); params.append(status)
                if task_type:
                    where.append("task_type = %s"); params.append(task_type)
                if template_id:
                    where.append("template_id = %s"); params.append(template_id)
                if customer_id:
                    where.append("customer_id = %s"); params.append(customer_id)
                if search:
                    where.append("title ILIKE %s"); params.append(f"%{search}%")
                where_clause = " AND ".join(where)

                cursor.execute(f"SELECT COUNT(*) AS total FROM {T.MSG_TASKS_TABLE} WHERE {where_clause}", tuple(params))
                total = (cursor.fetchone() or {}).get("total", 0)

                offset = (page - 1) * size
                cursor.execute(
                    f"""SELECT id FROM {T.MSG_TASKS_TABLE} WHERE {where_clause}
                    ORDER BY cdatetime DESC LIMIT %s OFFSET %s""",
                    tuple(params + [size, offset]),
                )
                ids = [r["id"] for r in cursor.fetchall()]
                items = [GetTasksServiceReadDto(**TasksService._load_task(cursor, tenant_id, org_id, bus_id, tid))
                         for tid in ids]

                pagination = PaginationMeta(
                    page=page, size=size, total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total,
                )
                return Respons(success=True, detail="Tasks retrieved successfully", data=items, pagination=pagination)
        except Exception as e:
            logger.error(f"Error listing tasks: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to list tasks: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def cancel_task(task_id, tenant_id, org_id, bus_id, performed_by) -> Respons[StepActionServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                existing = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                if not existing:
                    raise ValueError("Task not found")
                cursor.execute(
                    f"""UPDATE {T.MSG_TASK_STEPS_TABLE} SET status = 'CANCELLED'
                    WHERE task_id = %s AND tenant_id = %s AND status NOT IN ('COMPLETED', 'CANCELLED')""",
                    (task_id, tenant_id),
                )
                cursor.execute(
                    f"""UPDATE {T.MSG_TASKS_TABLE} SET status = 'CANCELLED', updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (performed_by, task_id, tenant_id, org_id, bus_id),
                )
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Task cancelled", data=[StepActionServiceReadDto(**task)])
        except ValueError as e:
            return Respons(success=False, detail=str(e), error="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Error cancelling task: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to cancel task: {str(e)}", error="INTERNAL_ERROR")

    # =================================================================
    # PUBLIC: step actions (the state machine)
    # =================================================================

    @staticmethod
    def _get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id) -> Optional[dict]:
        cursor.execute(
            f"""SELECT * FROM {T.MSG_TASK_STEPS_TABLE}
            WHERE id = %s AND task_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
            (step_id, task_id, tenant_id, org_id, bus_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def claim_step(task_id, step_id, tenant_id, org_id, bus_id, user_id) -> Respons[StepActionServiceReadDto]:
        return TasksService._claim_or_start(task_id, step_id, tenant_id, org_id, bus_id, user_id, start=False)

    @staticmethod
    def start_step(task_id, step_id, tenant_id, org_id, bus_id, user_id) -> Respons[StepActionServiceReadDto]:
        return TasksService._claim_or_start(task_id, step_id, tenant_id, org_id, bus_id, user_id, start=True)

    @staticmethod
    def _claim_or_start(task_id, step_id, tenant_id, org_id, bus_id, user_id, start: bool):
        action = "start" if start else "claim"
        try:
            with DatabaseManager.transaction() as cursor:
                step = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id)
                if not step:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                if step["status"] not in ("TODO", "IN_PROGRESS"):
                    return Respons(success=False, detail=f"Cannot {action} a step in status {step['status']}",
                                   error="INVALID_STATE")
                if not TasksService._step_prereqs_complete(cursor, tenant_id, step_id):
                    return Respons(success=False, detail="Step is not yet available (prerequisites incomplete)",
                                   error="STEP_BLOCKED")
                if step["claimed_by"] and step["claimed_by"] != user_id:
                    return Respons(success=False, detail="Step already claimed by another user", error="ALREADY_CLAIMED")
                if not TasksService._user_matches_targets(cursor, tenant_id, step_id, user_id, "ASSIGNEE"):
                    return Respons(success=False, detail="You are not an assignee of this step", error="NOT_ASSIGNEE")

                if start:
                    cursor.execute(
                        f"""UPDATE {T.MSG_TASK_STEPS_TABLE}
                        SET status = 'IN_PROGRESS', claimed_by = %s,
                            claimed_at = COALESCE(claimed_at, NOW())
                        WHERE id = %s AND tenant_id = %s""",
                        (user_id, step_id, tenant_id),
                    )
                else:
                    cursor.execute(
                        f"""UPDATE {T.MSG_TASK_STEPS_TABLE}
                        SET claimed_by = %s, claimed_at = NOW()
                        WHERE id = %s AND tenant_id = %s""",
                        (user_id, step_id, tenant_id),
                    )
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail=f"Step {action}ed successfully",
                               data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error during step {action}: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to {action} step: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def done_step(task_id, step_id, tenant_id, org_id, bus_id, user_id) -> Respons[StepActionServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                step = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id)
                if not step:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                if step["status"] != "IN_PROGRESS":
                    return Respons(success=False, detail="Only an IN_PROGRESS step can be marked DONE",
                                   error="INVALID_STATE")
                if step["claimed_by"] and step["claimed_by"] != user_id:
                    return Respons(success=False, detail="Only the user who claimed this step can mark it DONE",
                                   error="NOT_CLAIMER")
                cursor.execute(
                    f"""UPDATE {T.MSG_TASK_STEPS_TABLE}
                    SET status = 'DONE', done_by = %s, done_at = NOW()
                    WHERE id = %s AND tenant_id = %s""",
                    (user_id, step_id, tenant_id),
                )
                # Notify the step's approvers.
                approver_targets = TasksService._step_targets(cursor, tenant_id, step_id, "APPROVER")
                approver_ids = expand_targets_to_user_ids(cursor, tenant_id, approver_targets)
                TasksService._enqueue(cursor, tenant_id, org_id, bus_id, task_id, step_id,
                                      approver_ids, "DONE_NEEDS_APPROVAL", user_id)
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Step marked DONE; approvers notified",
                               data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error marking step done: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to mark step done: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def approve_step(task_id, step_id, tenant_id, org_id, bus_id, user_id) -> Respons[StepActionServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                step = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id)
                if not step:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                if step["status"] != "DONE":
                    return Respons(success=False, detail="Only a DONE step can be approved", error="INVALID_STATE")
                if not TasksService._user_matches_targets(cursor, tenant_id, step_id, user_id, "APPROVER"):
                    return Respons(success=False, detail="You are not an approver of this step", error="NOT_APPROVER")

                cursor.execute(
                    f"""UPDATE {T.MSG_TASK_STEPS_TABLE}
                    SET status = 'COMPLETED', completed_by = %s, completed_at = NOW()
                    WHERE id = %s AND tenant_id = %s""",
                    (user_id, step_id, tenant_id),
                )
                # Activate any downstream steps whose prerequisites are now all complete.
                cursor.execute(
                    f"""SELECT step_id FROM {T.MSG_TASK_STEP_DEPS_TABLE}
                    WHERE tenant_id = %s AND depends_on_step_id = %s""",
                    (tenant_id, step_id),
                )
                dependents = [r["step_id"] for r in cursor.fetchall()]
                for dep_step_id in dependents:
                    ds = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, dep_step_id)
                    if (ds and ds["status"] == "TODO"
                            and TasksService._step_prereqs_complete(cursor, tenant_id, dep_step_id)
                            and not TasksService._has_ready_notification(cursor, tenant_id, dep_step_id)):
                        TasksService._notify_step_assignees(
                            cursor, tenant_id, org_id, bus_id, task_id, dep_step_id, user_id, kind="READY")

                TasksService._maybe_complete_task(cursor, tenant_id, org_id, bus_id, task_id)
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id, resource_type="rt-tasks", resource_id=task_id, action="update",
                        old_data=None, new_data={"step_id": step_id, "status": "COMPLETED"},
                        description=f"Step {step_id} approved/completed",
                        performed_by=user_id, org_id=org_id, bus_id=bus_id, loc_id=None, cursor=cursor)
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)
                return Respons(success=True, detail="Step approved and completed",
                               data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error approving step: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to approve step: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def reject_step(task_id, step_id, tenant_id, org_id, bus_id, user_id, reason=None) -> Respons[StepActionServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                step = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id)
                if not step:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                if step["status"] != "DONE":
                    return Respons(success=False, detail="Only a DONE step can be rejected", error="INVALID_STATE")
                if not TasksService._user_matches_targets(cursor, tenant_id, step_id, user_id, "APPROVER"):
                    return Respons(success=False, detail="You are not an approver of this step", error="NOT_APPROVER")
                cursor.execute(
                    f"""UPDATE {T.MSG_TASK_STEPS_TABLE}
                    SET status = 'IN_PROGRESS', done_by = NULL, done_at = NULL
                    WHERE id = %s AND tenant_id = %s""",
                    (step_id, tenant_id),
                )
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Step sent back to IN_PROGRESS",
                               data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error rejecting step: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to reject step: {str(e)}", error="INTERNAL_ERROR")

    # =================================================================
    # PUBLIC: step editing (per-job tweaks)
    # =================================================================

    @staticmethod
    def _editable_guard(cursor, tenant_id, org_id, bus_id, task_id, step=None):
        """Returns an error Respons if the job isn't ACTIVE or the step is finished, else None."""
        cursor.execute(
            f"""SELECT status FROM {T.MSG_TASKS_TABLE}
            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND delete_status = 'NOT_DELETED'""",
            (task_id, tenant_id, org_id, bus_id),
        )
        row = cursor.fetchone()
        if not row:
            return Respons(success=False, detail="Task not found", error="NOT_FOUND")
        if row["status"] != "ACTIVE":
            return Respons(success=False, detail="Job is not active; steps can no longer be edited", error="INVALID_STATE")
        if step is not None and step["status"] not in ("TODO", "IN_PROGRESS"):
            return Respons(success=False, detail=f"A {step['status']} step can no longer be edited", error="INVALID_STATE")
        return None

    @staticmethod
    def _assignee_user_ids(cursor, tenant_id, step_id) -> set:
        return set(expand_targets_to_user_ids(
            cursor, tenant_id, TasksService._step_targets(cursor, tenant_id, step_id, "ASSIGNEE")))

    @staticmethod
    def _insert_targets(cursor, tenant_id, org_id, bus_id, step_id, targets, created_by):
        for t in targets:
            cursor.execute(
                f"""INSERT INTO {T.MSG_TASK_STEP_TARGETS_TABLE}
                (id, tenant_id, org_id, bus_id, step_id, target_kind, target_type, target_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (Helper.generate_unique_identifier(prefix="tst"), tenant_id, org_id, bus_id, step_id,
                 t.target_kind, t.target_type, t.target_id, created_by),
            )

    @staticmethod
    def _would_cycle(cursor, tenant_id, task_id, step_id, new_dep_ids) -> bool:
        """True if making step_id depend on new_dep_ids introduces a cycle."""
        cursor.execute(
            f"""SELECT d.step_id, d.depends_on_step_id
            FROM {T.MSG_TASK_STEP_DEPS_TABLE} d
            JOIN {T.MSG_TASK_STEPS_TABLE} s ON s.id = d.step_id AND s.tenant_id = d.tenant_id
            WHERE d.tenant_id = %s AND s.task_id = %s""",
            (tenant_id, task_id),
        )
        graph = {}
        for r in cursor.fetchall():
            if r["step_id"] == step_id:
                continue  # this step's deps are being replaced
            graph.setdefault(r["step_id"], set()).add(r["depends_on_step_id"])
        graph[step_id] = set(new_dep_ids)

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {}

        def dfs(n):
            color[n] = GRAY
            for m in graph.get(n, ()):  # n depends on m
                c = color.get(m, WHITE)
                if c == GRAY:
                    return True
                if c == WHITE and dfs(m):
                    return True
            color[n] = BLACK
            return False

        return any(color.get(n, WHITE) == WHITE and dfs(n) for n in list(graph.keys()))

    @staticmethod
    def update_step(task_id, step_id, tenant_id, org_id, bus_id, user_id,
                    name=None, description=None, location_id=None, targets=None) -> Respons[StepActionServiceReadDto]:
        """Edit a step's details and/or replace its assignees/approvers."""
        try:
            with DatabaseManager.transaction() as cursor:
                step = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id)
                if not step:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                guard = TasksService._editable_guard(cursor, tenant_id, org_id, bus_id, task_id, step)
                if guard:
                    return guard

                fields, params = [], []
                for col, val in [("name", name), ("description", description), ("location_id", location_id)]:
                    if val is not None:
                        fields.append(f"{col} = %s"); params.append(val)
                if fields:
                    fields.append("updated_by = %s"); params.append(user_id)
                    params.extend([step_id, tenant_id])
                    cursor.execute(
                        f"UPDATE {T.MSG_TASK_STEPS_TABLE} SET {', '.join(fields)} WHERE id = %s AND tenant_id = %s",
                        tuple(params),
                    )

                if targets is not None:
                    old_assignees = TasksService._assignee_user_ids(cursor, tenant_id, step_id)
                    cursor.execute(
                        f"DELETE FROM {T.MSG_TASK_STEP_TARGETS_TABLE} WHERE tenant_id = %s AND step_id = %s",
                        (tenant_id, step_id),
                    )
                    TasksService._insert_targets(cursor, tenant_id, org_id, bus_id, step_id, targets, user_id)
                    # Notify newly added assignees if the step is currently available.
                    if TasksService._step_prereqs_complete(cursor, tenant_id, step_id):
                        new_assignees = TasksService._assignee_user_ids(cursor, tenant_id, step_id)
                        added = new_assignees - old_assignees
                        TasksService._enqueue(cursor, tenant_id, org_id, bus_id, task_id, step_id,
                                              added, "ASSIGNED", user_id)

                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Step updated", data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error updating step: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update step: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def add_step(task_id, tenant_id, org_id, bus_id, user_id,
                 name, description=None, location_id=None, display_order=0,
                 depends_on=None, targets=None) -> Respons[StepActionServiceReadDto]:
        """Add a new step to an active job."""
        depends_on = depends_on or []
        targets = targets or []
        try:
            with DatabaseManager.transaction() as cursor:
                guard = TasksService._editable_guard(cursor, tenant_id, org_id, bus_id, task_id)
                if guard:
                    return guard
                # Validate referenced prerequisite steps belong to this task.
                for dep_id in depends_on:
                    if not TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, dep_id):
                        return Respons(success=False, detail=f"Unknown dependency step {dep_id}", error="VALIDATION_ERROR")

                step_id = Helper.generate_unique_identifier(prefix="tsk_step")
                cursor.execute(
                    f"""INSERT INTO {T.MSG_TASK_STEPS_TABLE}
                    (id, tenant_id, org_id, bus_id, task_id, name, description, display_order, location_id, status, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'TODO', %s)""",
                    (step_id, tenant_id, org_id, bus_id, task_id, name, description, display_order, location_id, user_id),
                )
                TasksService._insert_targets(cursor, tenant_id, org_id, bus_id, step_id, targets, user_id)
                for dep_id in depends_on:
                    cursor.execute(
                        f"""INSERT INTO {T.MSG_TASK_STEP_DEPS_TABLE}
                        (id, tenant_id, org_id, bus_id, step_id, depends_on_step_id, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (Helper.generate_unique_identifier(prefix="tsd"), tenant_id, org_id, bus_id, step_id, dep_id, user_id),
                    )
                # If immediately available, notify assignees.
                if TasksService._step_prereqs_complete(cursor, tenant_id, step_id):
                    TasksService._notify_step_assignees(cursor, tenant_id, org_id, bus_id, task_id, step_id, user_id, kind="ASSIGNED")
                # Adding an unfinished step may re-open a job that had auto-completed; not applicable while ACTIVE.
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Step added", data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error adding step: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to add step: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def remove_step(task_id, step_id, tenant_id, org_id, bus_id, user_id) -> Respons[StepActionServiceReadDto]:
        """Remove an unfinished step from an active job."""
        try:
            with DatabaseManager.transaction() as cursor:
                step = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id)
                if not step:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                guard = TasksService._editable_guard(cursor, tenant_id, org_id, bus_id, task_id, step)
                if guard:
                    return guard
                # Capture dependents before we delete the dep rows.
                cursor.execute(
                    f"""SELECT step_id FROM {T.MSG_TASK_STEP_DEPS_TABLE}
                    WHERE tenant_id = %s AND depends_on_step_id = %s""",
                    (tenant_id, step_id),
                )
                dependents = [r["step_id"] for r in cursor.fetchall()]
                # Delete deps in BOTH directions (the depends_on FK is RESTRICT), then the step
                # (targets & outbox rows cascade).
                cursor.execute(
                    f"""DELETE FROM {T.MSG_TASK_STEP_DEPS_TABLE}
                    WHERE tenant_id = %s AND (step_id = %s OR depends_on_step_id = %s)""",
                    (tenant_id, step_id, step_id),
                )
                cursor.execute(
                    f"DELETE FROM {T.MSG_TASK_STEPS_TABLE} WHERE id = %s AND tenant_id = %s",
                    (step_id, tenant_id),
                )
                # Dependents may now be unblocked -> notify their assignees.
                for dep_step_id in dependents:
                    ds = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, dep_step_id)
                    if (ds and ds["status"] == "TODO"
                            and TasksService._step_prereqs_complete(cursor, tenant_id, dep_step_id)
                            and not TasksService._has_ready_notification(cursor, tenant_id, dep_step_id)):
                        TasksService._notify_step_assignees(
                            cursor, tenant_id, org_id, bus_id, task_id, dep_step_id, user_id, kind="READY")
                # Removing the last open step could complete the job.
                TasksService._maybe_complete_task(cursor, tenant_id, org_id, bus_id, task_id)
                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Step removed", data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error removing step: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to remove step: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def set_step_dependencies(task_id, step_id, tenant_id, org_id, bus_id, user_id, depends_on) -> Respons[StepActionServiceReadDto]:
        """Replace a step's prerequisite list (gating/order)."""
        depends_on = depends_on or []
        try:
            with DatabaseManager.transaction() as cursor:
                step = TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, step_id)
                if not step:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                guard = TasksService._editable_guard(cursor, tenant_id, org_id, bus_id, task_id, step)
                if guard:
                    return guard
                dedup = list(dict.fromkeys(depends_on))
                for dep_id in dedup:
                    if dep_id == step_id:
                        return Respons(success=False, detail="A step cannot depend on itself", error="VALIDATION_ERROR")
                    if not TasksService._get_step(cursor, tenant_id, org_id, bus_id, task_id, dep_id):
                        return Respons(success=False, detail=f"Unknown dependency step {dep_id}", error="VALIDATION_ERROR")
                if TasksService._would_cycle(cursor, tenant_id, task_id, step_id, dedup):
                    return Respons(success=False, detail="These dependencies would create a cycle", error="VALIDATION_ERROR")

                cursor.execute(
                    f"DELETE FROM {T.MSG_TASK_STEP_DEPS_TABLE} WHERE tenant_id = %s AND step_id = %s",
                    (tenant_id, step_id),
                )
                for dep_id in dedup:
                    cursor.execute(
                        f"""INSERT INTO {T.MSG_TASK_STEP_DEPS_TABLE}
                        (id, tenant_id, org_id, bus_id, step_id, depends_on_step_id, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (Helper.generate_unique_identifier(prefix="tsd"), tenant_id, org_id, bus_id, step_id, dep_id, user_id),
                    )
                # If now available and not yet notified, alert assignees.
                if (step["status"] == "TODO"
                        and TasksService._step_prereqs_complete(cursor, tenant_id, step_id)
                        and not TasksService._has_ready_notification(cursor, tenant_id, step_id)):
                    TasksService._notify_step_assignees(cursor, tenant_id, org_id, bus_id, task_id, step_id, user_id, kind="READY")

                task = TasksService._load_task(cursor, tenant_id, org_id, bus_id, task_id)
                return Respons(success=True, detail="Step dependencies updated", data=[StepActionServiceReadDto(**task)])
        except Exception as e:
            logger.error(f"Error setting step dependencies: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to set dependencies: {str(e)}", error="INTERNAL_ERROR")

    # =================================================================
    # PUBLIC: per-user notification settings
    # =================================================================

    @staticmethod
    def get_notification_settings(tenant_id, org_id, bus_id, user_id) -> Respons[TaskNotificationSettingsServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT user_id, opt_in, reminder_interval_minutes
                    FROM {T.MSG_TASK_NOTIFICATION_SETTINGS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND user_id = %s""",
                    (tenant_id, org_id, bus_id, user_id),
                )
                row = cursor.fetchone()
                if row:
                    dto = TaskNotificationSettingsServiceReadDto(**dict(row))
                else:
                    dto = TaskNotificationSettingsServiceReadDto(user_id=user_id)
                return Respons(success=True, detail="Notification settings retrieved", data=[dto])
        except Exception as e:
            logger.error(f"Error getting notification settings: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get settings: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def upsert_notification_settings(
        data: TaskNotificationSettingsWriteDto, tenant_id, org_id, bus_id, user_id,
    ) -> Respons[TaskNotificationSettingsServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT id FROM {T.MSG_TASK_NOTIFICATION_SETTINGS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND user_id = %s""",
                    (tenant_id, org_id, bus_id, user_id),
                )
                existing = cursor.fetchone()
                opt_in = data.opt_in if data.opt_in is not None else True
                interval = data.reminder_interval_minutes if data.reminder_interval_minutes is not None else 120
                if existing:
                    fields, params = [], []
                    if data.opt_in is not None:
                        fields.append("opt_in = %s"); params.append(data.opt_in)
                    if data.reminder_interval_minutes is not None:
                        fields.append("reminder_interval_minutes = %s"); params.append(data.reminder_interval_minutes)
                    if fields:
                        fields.append("updated_by = %s"); params.append(user_id)
                        params.extend([existing["id"], tenant_id])
                        cursor.execute(
                            f"""UPDATE {T.MSG_TASK_NOTIFICATION_SETTINGS_TABLE} SET {', '.join(fields)}
                            WHERE id = %s AND tenant_id = %s""",
                            tuple(params),
                        )
                else:
                    cursor.execute(
                        f"""INSERT INTO {T.MSG_TASK_NOTIFICATION_SETTINGS_TABLE}
                        (id, tenant_id, org_id, bus_id, user_id, opt_in, reminder_interval_minutes, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (Helper.generate_unique_identifier(prefix="tns"), tenant_id, org_id, bus_id,
                         user_id, opt_in, interval, user_id),
                    )
                return TasksService.get_notification_settings(tenant_id, org_id, bus_id, user_id)
        except Exception as e:
            logger.error(f"Error saving notification settings: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to save settings: {str(e)}", error="INTERNAL_ERROR")

    # =================================================================
    # PUBLIC: statistics
    # =================================================================

    @staticmethod
    def get_statistics(tenant_id, org_id, bus_id) -> Respons[TaskStatisticsServiceReadDto]:
        """Aggregate task/job statistics for the business."""
        try:
            with DatabaseManager.transaction() as cursor:
                scope = "tenant_id = %s AND org_id = %s AND bus_id = %s AND delete_status = 'NOT_DELETED'"
                # Alias-qualified variant for the JOINed step-count query (avoids ambiguous columns).
                tkscope = "tk.tenant_id = %s AND tk.org_id = %s AND tk.bus_id = %s AND tk.delete_status = 'NOT_DELETED'"
                params = (tenant_id, org_id, bus_id)

                cursor.execute(
                    f"""SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE status = 'ACTIVE') AS active,
                        COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed,
                        COUNT(*) FILTER (WHERE status = 'CANCELLED') AS cancelled,
                        COUNT(*) FILTER (WHERE status = 'ACTIVE' AND due_date IS NOT NULL AND due_date < NOW()) AS overdue
                    FROM {T.MSG_TASKS_TABLE} WHERE {scope}""",
                    params,
                )
                t = cursor.fetchone() or {}

                cursor.execute(
                    f"""SELECT task_type, COUNT(*) AS c
                    FROM {T.MSG_TASKS_TABLE} WHERE {scope} GROUP BY task_type""",
                    params,
                )
                by_type = {r["task_type"]: r["c"] for r in cursor.fetchall()}

                # Step counts across non-deleted jobs.
                cursor.execute(
                    f"""SELECT
                        COUNT(*) AS total_steps,
                        COUNT(*) FILTER (WHERE s.status = 'TODO') AS todo,
                        COUNT(*) FILTER (WHERE s.status = 'IN_PROGRESS') AS in_progress,
                        COUNT(*) FILTER (WHERE s.status = 'DONE') AS done,
                        COUNT(*) FILTER (WHERE s.status = 'COMPLETED') AS completed,
                        COUNT(*) FILTER (WHERE s.status = 'CANCELLED') AS cancelled,
                        COUNT(*) FILTER (WHERE s.status = 'DONE' AND tk.status = 'ACTIVE') AS pending_approvals
                    FROM {T.MSG_TASK_STEPS_TABLE} s
                    JOIN {T.MSG_TASKS_TABLE} tk ON tk.id = s.task_id AND tk.tenant_id = s.tenant_id
                    WHERE {tkscope}""",
                    params,
                )
                s = cursor.fetchone() or {}

                dto = TaskStatisticsServiceReadDto(
                    total_tasks=t.get("total", 0) or 0,
                    active=t.get("active", 0) or 0,
                    completed=t.get("completed", 0) or 0,
                    cancelled=t.get("cancelled", 0) or 0,
                    overdue=t.get("overdue", 0) or 0,
                    by_type=by_type,
                    total_steps=s.get("total_steps", 0) or 0,
                    steps_todo=s.get("todo", 0) or 0,
                    steps_in_progress=s.get("in_progress", 0) or 0,
                    steps_done=s.get("done", 0) or 0,
                    steps_completed=s.get("completed", 0) or 0,
                    steps_cancelled=s.get("cancelled", 0) or 0,
                    pending_approvals=s.get("pending_approvals", 0) or 0,
                )
                return Respons(success=True, detail="Task statistics retrieved", data=[dto])
        except Exception as e:
            logger.error(f"Error getting task statistics: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to get statistics: {str(e)}", error="INTERNAL_ERROR")
