"""Collaboration layer for task STEPS: comments, @mentions and file attachments.

Each step is the clickable "ticket": you open a step to see its discussion and files.

- Comments are editable by their author and HARD-deleted (no soft-delete column).
- Attachments reuse the file manager (Azure Blob + msg_document_paths): files of any
  format are uploaded first via the file manager, then linked here by `document_id`.
  An attachment is step-level (comment_id NULL) or comment-level (comment_id set).
- @Mentions tag any active user in the tenant; each mention enqueues a MENTIONED task
  notification (carrying the step), which the notifications worker delivers by email.

task_id is stored alongside step_id for scoping and so notifications can reference the
parent task; it is always derived from the step, never supplied by the caller.
"""
from typing import List, Optional, Tuple

from src.entities.tasks.tasks_service import TasksService
from src.entities.tasks.tasks_read_dto import (
    CommentMentionRead,
    AttachmentRead,
    CommentServiceReadDto,
    CommentsListServiceReadDto,
    StepAttachmentsServiceReadDto,
    DeletedServiceReadDto,
)
from src.entities.tasks.tasks_write_dto import (
    CreateCommentServiceWriteDto,
    UpdateCommentServiceWriteDto,
    AddStepAttachmentsWriteDto,
)
from src.entities.filemanager.fmg_service import FileUploadService
from src.entities.filemanager.fmg_write_dto import FileDeleteServiceWriteDto
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("tasks_comments_service")

T = db_settings


class TaskCommentsService:
    """Comments, mentions and attachments for task steps."""

    # =================================================================
    # INTERNAL HELPERS
    # =================================================================

    @staticmethod
    def _step_task_id(cursor, tenant_id, org_id, bus_id, step_id) -> Optional[str]:
        """Return the step's parent task_id if the step exists in this business, else None."""
        cursor.execute(
            f"""SELECT task_id FROM {T.MSG_TASK_STEPS_TABLE}
            WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s LIMIT 1""",
            (step_id, tenant_id, org_id, bus_id),
        )
        row = cursor.fetchone()
        return row["task_id"] if row else None

    @staticmethod
    def _valid_user_ids(cursor, tenant_id, user_ids: List[str]) -> List[str]:
        """Filter to ids that are active users in this tenant (any business)."""
        ids = [u for u in dict.fromkeys(user_ids) if u]
        if not ids:
            return []
        placeholders = ", ".join(["%s"] * len(ids))
        cursor.execute(
            f"""SELECT id FROM {T.CORE_PLATFORM_USERS_TABLE}
            WHERE tenant_id = %s AND id IN ({placeholders})
            AND is_active = true AND delete_status = 'NOT_DELETED'""",
            (tenant_id, *ids),
        )
        return [r["id"] for r in cursor.fetchall()]

    @staticmethod
    def _valid_document_ids(cursor, tenant_id, org_id, bus_id, document_ids: List[str]) -> List[str]:
        """Filter to document ids that exist and are live for this business."""
        ids = [d for d in dict.fromkeys(document_ids) if d]
        if not ids:
            return []
        placeholders = ", ".join(["%s"] * len(ids))
        cursor.execute(
            f"""SELECT id FROM {T.MSG_DOCUMENT_PATHS_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND id IN ({placeholders})
            AND delete_status = 'NOT_DELETED' AND is_active = true""",
            (tenant_id, org_id, bus_id, *ids),
        )
        return [r["id"] for r in cursor.fetchall()]

    @staticmethod
    def _link_attachments(cursor, tenant_id, org_id, bus_id, step_id, task_id, comment_id,
                          document_ids: List[str], created_by) -> None:
        """Insert junction rows linking valid documents to a step (and optionally a comment)."""
        valid = TaskCommentsService._valid_document_ids(cursor, tenant_id, org_id, bus_id, document_ids)
        if not valid:
            return
        ts = Helper.current_date_time()
        for doc_id in valid:
            cursor.execute(
                f"""INSERT INTO {T.MSG_TASK_ATTACHMENTS_TABLE}
                (id, tenant_id, org_id, bus_id, step_id, task_id, comment_id, document_id,
                 is_active, delete_status, cdate, ctime, cdatetime, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, 'NOT_DELETED', %s, %s, %s, %s)""",
                (Helper.generate_unique_identifier(prefix="tat"), tenant_id, org_id, bus_id,
                 step_id, task_id, comment_id, doc_id, ts["cdate"], ts["ctime"], ts["cdatetime"], created_by),
            )

    @staticmethod
    def _add_mentions(cursor, tenant_id, org_id, bus_id, step_id, task_id, comment_id,
                      user_ids: List[str], created_by) -> List[str]:
        """Insert mention rows for valid users (deduped). Returns the user ids inserted."""
        valid = TaskCommentsService._valid_user_ids(cursor, tenant_id, user_ids)
        added = []
        for uid in valid:
            cursor.execute(
                f"""INSERT INTO {T.MSG_TASK_COMMENT_MENTIONS_TABLE}
                (id, tenant_id, org_id, bus_id, comment_id, step_id, task_id, mentioned_user_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, org_id, bus_id, comment_id, mentioned_user_id) DO NOTHING""",
                (Helper.generate_unique_identifier(prefix="tmn"), tenant_id, org_id, bus_id,
                 comment_id, step_id, task_id, uid, created_by),
            )
            added.append(uid)
        return added

    @staticmethod
    def _notify_mentions(cursor, tenant_id, org_id, bus_id, step_id, task_id,
                         user_ids: List[str], actor_id) -> None:
        """Enqueue MENTIONED notifications (on the step) for everyone tagged except the author."""
        recipients = [u for u in dict.fromkeys(user_ids) if u and u != actor_id]
        if recipients:
            TasksService._enqueue(
                cursor, tenant_id, org_id, bus_id, task_id, step_id, recipients, "MENTIONED", actor_id)

    @staticmethod
    def _mentions_for(cursor, tenant_id, comment_ids: List[str]) -> dict:
        """Map comment_id -> [CommentMentionRead]. Single query for a page of comments."""
        if not comment_ids:
            return {}
        placeholders = ", ".join(["%s"] * len(comment_ids))
        cursor.execute(
            f"""SELECT m.comment_id, m.mentioned_user_id, u.fullname, u.email
            FROM {T.MSG_TASK_COMMENT_MENTIONS_TABLE} m
            LEFT JOIN {T.CORE_PLATFORM_USERS_TABLE} u
                ON m.mentioned_user_id = u.id AND m.tenant_id = u.tenant_id
            WHERE m.tenant_id = %s AND m.comment_id IN ({placeholders})""",
            (tenant_id, *comment_ids),
        )
        out: dict = {cid: [] for cid in comment_ids}
        for r in cursor.fetchall():
            out.setdefault(r["comment_id"], []).append(
                CommentMentionRead(user_id=r["mentioned_user_id"], fullname=r.get("fullname"), email=r.get("email")))
        return out

    @staticmethod
    def _attachments_for(cursor, tenant_id, org_id, bus_id, *, step_id=None, comment_ids=None) -> dict:
        """Map key -> [AttachmentRead] with presigned URLs.

        When comment_ids is given, keys are comment ids (comment-level attachments).
        When step_id is given (comment_ids None), returns step-level attachments keyed by step_id.
        """
        where = ["a.tenant_id = %s", "a.org_id = %s", "a.bus_id = %s",
                 "a.delete_status = 'NOT_DELETED'", "a.is_active = true"]
        params: list = [tenant_id, org_id, bus_id]
        if comment_ids is not None:
            if not comment_ids:
                return {}
            placeholders = ", ".join(["%s"] * len(comment_ids))
            where.append(f"a.comment_id IN ({placeholders})")
            params.extend(comment_ids)
        else:
            where.append("a.step_id = %s")
            where.append("a.comment_id IS NULL")
            params.append(step_id)
        cursor.execute(
            f"""SELECT a.id, a.comment_id, a.step_id, a.document_id, a.created_by, a.cdatetime,
                       d.document_path, d.file_name, d.description
            FROM {T.MSG_TASK_ATTACHMENTS_TABLE} a
            INNER JOIN {T.MSG_DOCUMENT_PATHS_TABLE} d
                ON a.document_id = d.id AND a.tenant_id = d.tenant_id
                AND a.org_id = d.org_id AND a.bus_id = d.bus_id
            WHERE {' AND '.join(where)}
            ORDER BY a.cdatetime ASC""",
            tuple(params),
        )
        out: dict = {}
        for r in cursor.fetchall():
            url = FileUploadService._get_file_presigned_url(
                db_settings.MYSTOREGUARD_FILES_CONTAINER, r["document_path"])
            item = AttachmentRead(
                id=r["id"], document_id=r["document_id"], file_name=r.get("file_name"),
                description=r.get("description"), presigned_url=url,
                created_by=r.get("created_by"), cdatetime=r.get("cdatetime"))
            key = r["comment_id"] if comment_ids is not None else r["step_id"]
            out.setdefault(key, []).append(item)
        return out

    @staticmethod
    def _build_comment(cursor, tenant_id, org_id, bus_id, comment_row) -> CommentServiceReadDto:
        cid = comment_row["id"]
        mentions = TaskCommentsService._mentions_for(cursor, tenant_id, [cid]).get(cid, [])
        attachments = TaskCommentsService._attachments_for(
            cursor, tenant_id, org_id, bus_id, comment_ids=[cid]).get(cid, [])
        return CommentServiceReadDto(
            id=cid, step_id=comment_row["step_id"], task_id=comment_row.get("task_id"),
            body=comment_row["body"], created_by=comment_row.get("created_by"),
            author_name=comment_row.get("author_name"), edited_at=comment_row.get("edited_at"),
            cdatetime=comment_row.get("cdatetime"), mentions=mentions, attachments=attachments)

    @staticmethod
    def _load_comment(cursor, tenant_id, org_id, bus_id, comment_id) -> Optional[dict]:
        cursor.execute(
            f"""SELECT c.id, c.step_id, c.task_id, c.body, c.edited_at, c.cdatetime, c.created_by,
                       u.fullname AS author_name
            FROM {T.MSG_TASK_COMMENTS_TABLE} c
            LEFT JOIN {T.CORE_PLATFORM_USERS_TABLE} u
                ON c.created_by = u.id AND c.tenant_id = u.tenant_id
            WHERE c.id = %s AND c.tenant_id = %s AND c.org_id = %s AND c.bus_id = %s""",
            (comment_id, tenant_id, org_id, bus_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def _purge_documents(documents: List[Tuple[str, str]], tenant_id, org_id, bus_id, deleted_by) -> None:
        """Best-effort removal of underlying blobs + document rows (post-commit).

        `documents` is a list of (document_id, loc_id). Failures are logged, not raised.
        """
        for document_id, loc_id in documents:
            try:
                FileUploadService.delete_file(
                    FileDeleteServiceWriteDto(document_id=document_id),
                    tenant_id, org_id, bus_id, loc_id or "", deleted_by)
            except Exception as e:  # noqa: BLE001 - cleanup must not break the request
                logger.warning(f"Failed to purge document {document_id}: {e}")

    @staticmethod
    def _orphan_documents(cursor, tenant_id, org_id, bus_id, comment_id) -> List[Tuple[str, str]]:
        """Document (id, loc_id) attached to this comment and to no other live attachment."""
        cursor.execute(
            f"""SELECT a.document_id, d.loc_id
            FROM {T.MSG_TASK_ATTACHMENTS_TABLE} a
            INNER JOIN {T.MSG_DOCUMENT_PATHS_TABLE} d
                ON a.document_id = d.id AND a.tenant_id = d.tenant_id
                AND a.org_id = d.org_id AND a.bus_id = d.bus_id
            WHERE a.tenant_id = %s AND a.org_id = %s AND a.bus_id = %s
                AND a.comment_id = %s AND a.delete_status = 'NOT_DELETED'
                AND NOT EXISTS (
                    SELECT 1 FROM {T.MSG_TASK_ATTACHMENTS_TABLE} o
                    WHERE o.tenant_id = a.tenant_id AND o.org_id = a.org_id AND o.bus_id = a.bus_id
                        AND o.document_id = a.document_id AND o.id <> a.id
                        AND o.delete_status = 'NOT_DELETED'
                )""",
            (tenant_id, org_id, bus_id, comment_id),
        )
        return [(r["document_id"], r.get("loc_id")) for r in cursor.fetchall()]

    # =================================================================
    # PUBLIC: comments (anchored on a step)
    # =================================================================

    @staticmethod
    def create_comment(data: CreateCommentServiceWriteDto, step_id, tenant_id, org_id, bus_id, created_by
                       ) -> Respons[CommentServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                task_id = TaskCommentsService._step_task_id(cursor, tenant_id, org_id, bus_id, step_id)
                if not task_id:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")

                comment_id = Helper.generate_unique_identifier(prefix="tcm")
                ts = Helper.current_date_time()
                cursor.execute(
                    f"""INSERT INTO {T.MSG_TASK_COMMENTS_TABLE}
                    (id, tenant_id, org_id, bus_id, step_id, task_id, body, cdate, ctime, cdatetime, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (comment_id, tenant_id, org_id, bus_id, step_id, task_id, data.body,
                     ts["cdate"], ts["ctime"], ts["cdatetime"], created_by),
                )

                TaskCommentsService._link_attachments(
                    cursor, tenant_id, org_id, bus_id, step_id, task_id, comment_id, data.document_ids, created_by)

                added = TaskCommentsService._add_mentions(
                    cursor, tenant_id, org_id, bus_id, step_id, task_id, comment_id,
                    data.mentioned_user_ids, created_by)
                TaskCommentsService._notify_mentions(
                    cursor, tenant_id, org_id, bus_id, step_id, task_id, added, created_by)

                row = TaskCommentsService._load_comment(cursor, tenant_id, org_id, bus_id, comment_id)
                dto = TaskCommentsService._build_comment(cursor, tenant_id, org_id, bus_id, row)
                return Respons(success=True, detail="Comment added", data=[dto])
        except Exception as e:
            logger.error(f"Error creating comment: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to add comment: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def list_comments(step_id, tenant_id, org_id, bus_id) -> Respons[CommentsListServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                task_id = TaskCommentsService._step_task_id(cursor, tenant_id, org_id, bus_id, step_id)
                if not task_id:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")

                cursor.execute(
                    f"""SELECT c.id, c.step_id, c.task_id, c.body, c.edited_at, c.cdatetime, c.created_by,
                               u.fullname AS author_name
                    FROM {T.MSG_TASK_COMMENTS_TABLE} c
                    LEFT JOIN {T.CORE_PLATFORM_USERS_TABLE} u
                        ON c.created_by = u.id AND c.tenant_id = u.tenant_id
                    WHERE c.tenant_id = %s AND c.org_id = %s AND c.bus_id = %s AND c.step_id = %s
                    ORDER BY c.cdatetime DESC""",
                    (tenant_id, org_id, bus_id, step_id),
                )
                rows = [dict(r) for r in cursor.fetchall()]
                ids = [r["id"] for r in rows]
                mentions = TaskCommentsService._mentions_for(cursor, tenant_id, ids)
                attachments = TaskCommentsService._attachments_for(
                    cursor, tenant_id, org_id, bus_id, comment_ids=ids)
                comments = [
                    CommentServiceReadDto(
                        id=r["id"], step_id=r["step_id"], task_id=r.get("task_id"), body=r["body"],
                        created_by=r.get("created_by"), author_name=r.get("author_name"),
                        edited_at=r.get("edited_at"), cdatetime=r.get("cdatetime"),
                        mentions=mentions.get(r["id"], []), attachments=attachments.get(r["id"], []))
                    for r in rows
                ]
                dto = CommentsListServiceReadDto(step_id=step_id, task_id=task_id, comments=comments)
                return Respons(success=True, detail="Comments retrieved", data=[dto])
        except Exception as e:
            logger.error(f"Error listing comments: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to list comments: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def update_comment(data: UpdateCommentServiceWriteDto, comment_id, tenant_id, org_id, bus_id, user_id
                      ) -> Respons[CommentServiceReadDto]:
        purge: List[Tuple[str, str]] = []
        try:
            with DatabaseManager.transaction() as cursor:
                comment = TaskCommentsService._load_comment(cursor, tenant_id, org_id, bus_id, comment_id)
                if not comment:
                    return Respons(success=False, detail="Comment not found", error="NOT_FOUND")
                if comment.get("created_by") != user_id:
                    return Respons(success=False, detail="Only the author can edit this comment", error="FORBIDDEN")

                step_id = comment["step_id"]
                task_id = comment.get("task_id")

                if data.body is not None:
                    cursor.execute(
                        f"""UPDATE {T.MSG_TASK_COMMENTS_TABLE}
                        SET body = %s, edited_at = NOW(), updated_by = %s
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (data.body, user_id, comment_id, tenant_id, org_id, bus_id),
                    )

                if data.mentioned_user_ids is not None:
                    cursor.execute(
                        f"""SELECT mentioned_user_id FROM {T.MSG_TASK_COMMENT_MENTIONS_TABLE}
                        WHERE tenant_id = %s AND comment_id = %s""",
                        (tenant_id, comment_id),
                    )
                    existing = {r["mentioned_user_id"] for r in cursor.fetchall()}
                    cursor.execute(
                        f"""DELETE FROM {T.MSG_TASK_COMMENT_MENTIONS_TABLE}
                        WHERE tenant_id = %s AND comment_id = %s""",
                        (tenant_id, comment_id),
                    )
                    added = TaskCommentsService._add_mentions(
                        cursor, tenant_id, org_id, bus_id, step_id, task_id, comment_id,
                        data.mentioned_user_ids, user_id)
                    newly = [u for u in added if u not in existing]
                    TaskCommentsService._notify_mentions(
                        cursor, tenant_id, org_id, bus_id, step_id, task_id, newly, user_id)

                if data.document_ids is not None:
                    # documents being unlinked and referenced nowhere else become orphans to purge
                    purge = TaskCommentsService._orphan_documents(cursor, tenant_id, org_id, bus_id, comment_id)
                    cursor.execute(
                        f"""DELETE FROM {T.MSG_TASK_ATTACHMENTS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND comment_id = %s""",
                        (tenant_id, org_id, bus_id, comment_id),
                    )
                    TaskCommentsService._link_attachments(
                        cursor, tenant_id, org_id, bus_id, step_id, task_id, comment_id, data.document_ids, user_id)
                    keep = set(TaskCommentsService._valid_document_ids(
                        cursor, tenant_id, org_id, bus_id, data.document_ids))
                    purge = [d for d in purge if d[0] not in keep]

                row = TaskCommentsService._load_comment(cursor, tenant_id, org_id, bus_id, comment_id)
                dto = TaskCommentsService._build_comment(cursor, tenant_id, org_id, bus_id, row)
        except Exception as e:
            logger.error(f"Error updating comment: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to update comment: {str(e)}", error="INTERNAL_ERROR")

        TaskCommentsService._purge_documents(purge, tenant_id, org_id, bus_id, user_id)
        return Respons(success=True, detail="Comment updated", data=[dto])

    @staticmethod
    def delete_comment(comment_id, tenant_id, org_id, bus_id, user_id, can_delete_any: bool = False
                      ) -> Respons[DeletedServiceReadDto]:
        purge: List[Tuple[str, str]] = []
        try:
            with DatabaseManager.transaction() as cursor:
                comment = TaskCommentsService._load_comment(cursor, tenant_id, org_id, bus_id, comment_id)
                if not comment:
                    return Respons(success=False, detail="Comment not found", error="NOT_FOUND")
                if comment.get("created_by") != user_id and not can_delete_any:
                    return Respons(success=False, detail="Not allowed to delete this comment", error="FORBIDDEN")

                purge = TaskCommentsService._orphan_documents(cursor, tenant_id, org_id, bus_id, comment_id)
                # hard delete: FK cascade removes mentions + attachment junction rows
                cursor.execute(
                    f"""DELETE FROM {T.MSG_TASK_COMMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (comment_id, tenant_id, org_id, bus_id),
                )
        except Exception as e:
            logger.error(f"Error deleting comment: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to delete comment: {str(e)}", error="INTERNAL_ERROR")

        TaskCommentsService._purge_documents(purge, tenant_id, org_id, bus_id, user_id)
        return Respons(success=True, detail="Comment deleted",
                       data=[DeletedServiceReadDto(id=comment_id, message="Comment deleted")])

    # =================================================================
    # PUBLIC: step-level attachments
    # =================================================================

    @staticmethod
    def add_step_attachments(data: AddStepAttachmentsWriteDto, step_id, tenant_id, org_id, bus_id, created_by
                            ) -> Respons[StepAttachmentsServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                task_id = TaskCommentsService._step_task_id(cursor, tenant_id, org_id, bus_id, step_id)
                if not task_id:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                TaskCommentsService._link_attachments(
                    cursor, tenant_id, org_id, bus_id, step_id, task_id, None, data.document_ids, created_by)
                attachments = TaskCommentsService._attachments_for(
                    cursor, tenant_id, org_id, bus_id, step_id=step_id).get(step_id, [])
                dto = StepAttachmentsServiceReadDto(step_id=step_id, task_id=task_id, attachments=attachments)
                return Respons(success=True, detail="Attachments added", data=[dto])
        except Exception as e:
            logger.error(f"Error adding step attachments: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to add attachments: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def list_step_attachments(step_id, tenant_id, org_id, bus_id) -> Respons[StepAttachmentsServiceReadDto]:
        try:
            with DatabaseManager.transaction() as cursor:
                task_id = TaskCommentsService._step_task_id(cursor, tenant_id, org_id, bus_id, step_id)
                if not task_id:
                    return Respons(success=False, detail="Step not found", error="NOT_FOUND")
                attachments = TaskCommentsService._attachments_for(
                    cursor, tenant_id, org_id, bus_id, step_id=step_id).get(step_id, [])
                dto = StepAttachmentsServiceReadDto(step_id=step_id, task_id=task_id, attachments=attachments)
                return Respons(success=True, detail="Attachments retrieved", data=[dto])
        except Exception as e:
            logger.error(f"Error listing step attachments: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to list attachments: {str(e)}", error="INTERNAL_ERROR")

    @staticmethod
    def delete_attachment(attachment_id, tenant_id, org_id, bus_id, user_id
                         ) -> Respons[DeletedServiceReadDto]:
        purge: List[Tuple[str, str]] = []
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT a.id, a.document_id, d.loc_id
                    FROM {T.MSG_TASK_ATTACHMENTS_TABLE} a
                    LEFT JOIN {T.MSG_DOCUMENT_PATHS_TABLE} d
                        ON a.document_id = d.id AND a.tenant_id = d.tenant_id
                        AND a.org_id = d.org_id AND a.bus_id = d.bus_id
                    WHERE a.id = %s AND a.tenant_id = %s AND a.org_id = %s AND a.bus_id = %s
                        AND a.delete_status = 'NOT_DELETED'""",
                    (attachment_id, tenant_id, org_id, bus_id),
                )
                att = cursor.fetchone()
                if not att:
                    return Respons(success=False, detail="Attachment not found", error="NOT_FOUND")

                cursor.execute(
                    f"""DELETE FROM {T.MSG_TASK_ATTACHMENTS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (attachment_id, tenant_id, org_id, bus_id),
                )
                # purge the blob only if no other live attachment references the document
                cursor.execute(
                    f"""SELECT 1 FROM {T.MSG_TASK_ATTACHMENTS_TABLE}
                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND document_id = %s
                        AND delete_status = 'NOT_DELETED' LIMIT 1""",
                    (tenant_id, org_id, bus_id, att["document_id"]),
                )
                if not cursor.fetchone():
                    purge = [(att["document_id"], att.get("loc_id"))]
        except Exception as e:
            logger.error(f"Error deleting attachment: {str(e)}", exc_info=True)
            return Respons(success=False, detail=f"Failed to delete attachment: {str(e)}", error="INTERNAL_ERROR")

        TaskCommentsService._purge_documents(purge, tenant_id, org_id, bus_id, user_id)
        return Respons(success=True, detail="Attachment removed",
                       data=[DeletedServiceReadDto(id=attachment_id, message="Attachment removed")])
