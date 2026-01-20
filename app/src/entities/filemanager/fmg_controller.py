from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import Optional
from urllib.parse import unquote
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.filemanager.fmg_service import FileUploadService
from src.entities.filemanager.fmg_read_dto import (
    FileUploadMultipleServiceReadDto,
    FileResponseControllerReadDto,
    FileDeleteServiceReadDto,
)
from src.entities.filemanager.fmg_write_dto import (
    FileUploadServiceWriteDto,
    FileUpdateServiceWriteDto,
    FileDeleteServiceWriteDto,
    ListDocumentsServiceWriteDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

file_management_router = APIRouter(prefix="/file", tags=["File Management"])
logger = get_logger("file_management")


# =====================================================
# FILE MANAGEMENT ENDPOINTS
# =====================================================

# Upload Multiple Files
@file_management_router.post("/post/multiple", response_model=Respons[FileUploadMultipleServiceReadDto])
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    blob_paths: str = Query(..., description="Full document paths (e.g., 'tenant_id/org_id/bus_id/images/file.png') - comma-separated, must match number of files, or single path for all files"),
    descriptions: Optional[str] = Query(None, description="Optional comma-separated descriptions (can be fewer than files)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Upload multiple files to Azure Storage and store document information"""
    with LogContext(
        "file_management",
        "upload_multiple_files",
    ):
        # Parse comma-separated values and URL decode
        blob_path_list = [unquote(path.strip()) for path in blob_paths.split(",") if path.strip()]
        description_list = [unquote(d.strip()) if d else None for d in descriptions.split(",")] if descriptions else [None] * len(files)
        
        # If only one blob_path is provided, use it for all files
        if len(blob_path_list) == 1 and len(files) > 1:
            blob_path_list = blob_path_list * len(files)
        elif len(files) != len(blob_path_list):
            raise HTTPException(
                status_code=400,
                detail=f"Number of files ({len(files)}) must match number of blob paths ({len(blob_path_list)}), or provide a single blob path for all files"
            )
        
        # Pad descriptions if needed
        while len(description_list) < len(files):
            description_list.append(None)
        
        # Get container name from settings
        from src.configs.settings import db_settings
        container_name = db_settings.MYSTOREGUARD_FILES_CONTAINER
        
        logger.info(
            "Processing upload multiple files request",
            extra={
                "extra_fields": {
                    "endpoint": "/file/post/multiple",
                    "container_name": container_name,
                    "files_count": len(files),
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-file-upload-multiple"]
        )

        if not is_authorized:
            logger.warning(
                "Upload multiple files failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/post/multiple",
                        "container_name": container_name,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        # Read all file contents and prepare data
        # blob_paths contains the full path: tenant_id/org_id/bus_id/images/file.png or tenant_id/org_id/bus_id/documents/file.doc
        files_data = []
        
        for file, blob_path, desc in zip(files, blob_path_list, description_list):
            file_content = await file.read()
            
            # Extract filename from UploadFile object, or from blob_path as fallback
            file_name = file.filename if file.filename else None
            
            # blob_path is already the full path (e.g., "tenant_id/org_id/bus_id/images/file.png")
            # Use it directly
            files_data.append((
                FileUploadServiceWriteDto(
                    file_content=file_content,
                    content_type=file.content_type or "application/octet-stream",
                    container_name=container_name,
                    blob_path=blob_path,  # Full path: tenant_id/org_id/bus_id/images/file.png
                    description=desc,
                ),
                file_name  # Pass filename from UploadFile
            ))

        service_result = FileUploadService.upload_multiple_files(
            files_data=files_data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                f"Uploaded {len(service_result.data)} file(s) successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/post/multiple",
                        "container_name": container_name,
                        "uploaded_count": len(service_result.data),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Multiple files upload failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/post/multiple",
                        "container_name": container_name,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# Update File
@file_management_router.put("/put", response_model=Respons[FileResponseControllerReadDto])
async def update_file(
    file: UploadFile = File(...),
    document_id: str = Query(..., description="Document ID to update"),
    blob_path: Optional[str] = Query(None, description="Optional: New document path (if provided, will change the path)"),
    description: Optional[str] = Query(None, description="New description"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update file in Azure Storage and update description/path in database"""
    with LogContext(
        "file_management",
        "update_file",
    ):
        if not document_id or not document_id.strip():
            raise HTTPException(
                status_code=400,
                detail="document_id must be provided"
            )

        # URL decode blob_path if provided
        decoded_blob_path = unquote(blob_path.strip()) if blob_path and blob_path.strip() else None

        logger.info(
            "Processing update file request",
            extra={
                "extra_fields": {
                    "endpoint": "/file/put",
                    "document_id": document_id,
                    "blob_path": decoded_blob_path,
                    "filename": file.filename,
                    "content_type": file.content_type,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-file-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update file failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/put",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        # Read file content
        file_content = await file.read()
        
        # Extract filename from UploadFile object if available
        file_name = file.filename if file.filename else None

        service_result = FileUploadService.update_file(
            data=FileUpdateServiceWriteDto(
                file_content=file_content,
                content_type=file.content_type or "application/octet-stream",
                document_id=document_id.strip(),
                blob_path=decoded_blob_path,
                description=description.strip() if description else None,
            ),
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            updated_by=current_user.data[0].user_id,
            file_name=file_name,  # Pass filename from UploadFile
        )

        if service_result.success:
            logger.info(
                "File updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/put",
                        "document_id": document_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"File update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/put",
                        "document_id": document_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# Delete File
@file_management_router.delete("/delete", response_model=Respons[FileDeleteServiceReadDto])
def delete_file(
    document_id: str = Query(..., description="Document ID to delete"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete file from Azure Storage and database"""
    with LogContext(
        "file_management",
        "delete_file",
    ):
        if not document_id or not document_id.strip():
            raise HTTPException(
                status_code=400,
                detail="document_id must be provided"
            )

        logger.info(
            "Processing delete file request",
            extra={
                "extra_fields": {
                    "endpoint": "/file/delete",
                    "document_id": document_id,
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-file-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete file failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = FileUploadService.delete_file(
            data=FileDeleteServiceWriteDto(
                document_id=document_id.strip(),
            ),
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
            deleted_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "File deleted successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/delete",
                        "document_id": document_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"File deletion failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/delete",
                        "document_id": document_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# List Documents
@file_management_router.get("/list", response_model=Respons[FileResponseControllerReadDto])
def list_documents(
    document_ids: str = Query(..., description="Comma-separated list of document IDs"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get documents by IDs, generate presigned URLs (24 hours expiry) and return id, description, presigned_url"""
    with LogContext(
        "file_management",
        "list_documents",
    ):
        if not document_ids or not document_ids.strip():
            raise HTTPException(
                status_code=400,
                detail="document_ids must be provided"
            )

        # Parse comma-separated document IDs
        document_id_list = [doc_id.strip() for doc_id in document_ids.split(",") if doc_id.strip()]
        
        if not document_id_list:
            raise HTTPException(
                status_code=400,
                detail="At least one document_id must be provided"
            )

        logger.info(
            "Processing list documents request",
            extra={
                "extra_fields": {
                    "endpoint": "/file/list",
                    "document_ids_count": len(document_id_list),
                }
            },
        )

                # Check if user has any of the required permissions (OR logic)
        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-file-list-documents"]
        )

        if not is_authorized:
            logger.warning(
                "List documents failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = FileUploadService.list_documents(
            data=ListDocumentsServiceWriteDto(
                document_ids=document_id_list
            ),
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            loc_id=org_bus_loc["loc_id"],
        )

        if service_result.success:
            logger.info(
                f"Retrieved {len(service_result.data)} document(s) successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/list",
                        "documents_count": len(service_result.data),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"List documents failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/file/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result
