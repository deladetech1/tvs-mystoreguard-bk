from typing import Optional
from src.entities.filemanager.fmg_read_dto import (
    FileUploadServiceReadDto,
    FileUploadMultipleServiceReadDto,
    FileUpdateServiceReadDto,
    FileDeleteServiceReadDto,
    FileResponseServiceReadDto,
    GetDocumentServiceReadDto,
    ListDocumentsServiceReadDto,
)
from src.entities.filemanager.fmg_write_dto import (
    FileUploadServiceWriteDto,
    FileUpdateServiceWriteDto,
    FileDeleteServiceWriteDto,
    GetDocumentServiceWriteDto,
    ListDocumentsServiceWriteDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("file_upload_service")




class FileUploadService:
    """Unified service class for file operations"""

    @staticmethod
    def _extract_filename_from_path(blob_path: str) -> Optional[str]:
        """
        Extract filename from blob path
        
        Args:
            blob_path: Full blob path (e.g., "tenant_id/org_id/bus_id/images/file.png")
        
        Returns:
            Filename extracted from path or None
        """
        if not blob_path:
            return None
        # Extract the last part after the last '/'
        return blob_path.split('/')[-1] if '/' in blob_path else blob_path

    @staticmethod
    def _upload_file_to_storage(
        file_content: bytes,
        content_type: str,
        container_name: str,
        blob_path: str,
    ) -> Respons:
        """
        Upload file to Azure Storage using trovesuite StorageService
        
        Args:
            file_content: File content as bytes
            content_type: MIME type of the file
            container_name: Container name in Azure Storage
            blob_path: Blob path in storage
        
        Returns:
            Response with uploaded blob path
        """
        try:
            from trovesuite.storage import StorageService
            from trovesuite.storage.storage_write_dto import StorageFileUploadServiceWriteDto
            import os

            # Construct upload DTO
            upload_dto = StorageFileUploadServiceWriteDto(
                storage_account_url=f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net",
                container_name=container_name,
                blob_name=blob_path,
                file_content=file_content,
                content_type=content_type,
                managed_identity_client_id=db_settings.USER_ASSIGNED_MANAGED_IDENTITY,
            )

            # Upload file
            upload_result = StorageService.upload_file(upload_dto)

            return upload_result

        except Exception as e:
            logger.error(
                f"Error uploading file to storage: {str(e)}",
                extra={"extra_fields": {"container_name": container_name, "blob_path": blob_path, "error": str(e)}},
                exc_info=True
            )
            return Respons(
                detail=f"Failed to upload file: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )

    @staticmethod
    def _update_file_in_storage(
        file_content: bytes,
        content_type: str,
        container_name: str,
        blob_path: str,
    ) -> Respons:
        """
        Update file in Azure Storage using trovesuite StorageService
        
        Args:
            file_content: File content as bytes
            content_type: MIME type of the file
            container_name: Container name in Azure Storage
            blob_path: Blob path in storage
        
        Returns:
            Response with updated blob path
        """
        try:
            from trovesuite.storage import StorageService
            from trovesuite.storage.storage_write_dto import StorageFileUpdateServiceWriteDto
            import os

            # Construct update DTO
            update_dto = StorageFileUpdateServiceWriteDto(
                storage_account_url=f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net",
                container_name=container_name,
                blob_name=blob_path,
                file_content=file_content,
                content_type=content_type,
                managed_identity_client_id=db_settings.USER_ASSIGNED_MANAGED_IDENTITY,
            )

            # Update file
            update_result = StorageService.update_file(update_dto)

            return update_result

        except Exception as e:
            logger.error(
                f"Error updating file in storage: {str(e)}",
                extra={"extra_fields": {"container_name": container_name, "blob_path": blob_path, "error": str(e)}},
                exc_info=True
            )
            return Respons(
                detail=f"Failed to update file: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )

    @staticmethod
    def _get_file_presigned_url(
        container_name: str,
        blob_path: str,
        expiry_hours: int = 24
    ) -> Optional[str]:
        """
        Get pre-signed URL for a file
        
        Args:
            container_name: Container name in Azure Storage
            blob_path: Blob path in storage
            expiry_hours: URL expiry time in hours (default: 24)
        
        Returns:
            Pre-signed URL string or None if generation fails
        """
        try:
            from trovesuite.storage import StorageService
            from trovesuite.storage.storage_write_dto import StorageFileUrlServiceWriteDto
            import os

            url_dto = StorageFileUrlServiceWriteDto(
                storage_account_url=f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net",
                container_name=container_name,
                blob_name=blob_path,
                expiry_hours=expiry_hours,
                managed_identity_client_id=db_settings.USER_ASSIGNED_MANAGED_IDENTITY,
            )

            url_result = StorageService.get_file_url(url_dto)
            if url_result.success and url_result.data:
                return url_result.data[0].presigned_url
            else:
                logger.warning(
                    f"Failed to generate presigned URL for: {blob_path}",
                    extra={"extra_fields": {"container_name": container_name, "blob_path": blob_path, "error": url_result.error}}
                )
                return None
        except Exception as e:
            logger.error(
                f"Error generating presigned URL: {str(e)}",
                extra={"extra_fields": {"container_name": container_name, "blob_path": blob_path, "error": str(e)}},
                exc_info=True
            )
            return None

    @staticmethod
    def upload_file(
        data: FileUploadServiceWriteDto,
        document_name: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[FileUploadMultipleServiceReadDto]:
        """Upload a file to Azure Storage and store document information"""
        try:
            # Generate document_id first
            document_id = Helper.generate_unique_identifier(prefix="doc")
            
            # Insert document_id as a folder in the path: e.g., "folder/file.pdf" -> "folder/doc-123/file.pdf"
            import os
            blob_path_dir = os.path.dirname(data.blob_path) if os.path.dirname(data.blob_path) else ""
            blob_path_filename = os.path.basename(data.blob_path)
            # Insert document_id as a directory: e.g., "folder/file.pdf" -> "folder/doc-123/file.pdf"
            if blob_path_dir:
                modified_blob_path = f"{blob_path_dir}/{document_id}/{blob_path_filename}"
            else:
                modified_blob_path = f"{document_id}/{blob_path_filename}"
            
            # Extract filename from blob_path or use document_name if provided
            file_name = document_name if document_name and document_name.strip() else FileUploadService._extract_filename_from_path(data.blob_path)
            
            # Upload file to Azure Storage using the modified blob_path
            upload_result = FileUploadService._upload_file_to_storage(
                file_content=data.file_content,
                content_type=data.content_type,
                container_name=data.container_name,
                blob_path=modified_blob_path,
            )

            if not upload_result.success:
                return Respons[FileUploadMultipleServiceReadDto](
                    detail="Failed to upload file",
                    data=[],
                    success=False,
                    status_code=500,
                    error=upload_result.error or "Upload failed"
                )
            
            # Store document information in database
            cdate = Helper.current_date_time()["cdate"]
            ctime = Helper.current_date_time()["ctime"]
            cdatetime = Helper.current_date_time()["cdatetime"]
            
            try:
                with DatabaseManager.transaction() as cursor:
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, document_path, file_name, description, 
                         delete_status, is_active, cdate, ctime, cdatetime, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, document_path, description""",
                        (
                            document_id,
                            tenant_id,
                            org_id,
                            bus_id,
                            loc_id,
                            modified_blob_path,  # Store modified path with document_id
                            file_name,  # Store extracted filename
                            data.description,
                            'NOT_DELETED',
                            True,
                            cdate,
                            ctime,
                            cdatetime,
                            created_by,
                        ),
                    )
                    db_result = cursor.fetchone()
                    doc_dict = dict(db_result) if db_result else {}
                    stored_id = doc_dict.get('id', document_id)
                    stored_path = doc_dict.get('document_path', modified_blob_path)
                    stored_description = doc_dict.get('description', data.description)
                    
                    logger.info(
                        f"Document path stored successfully: {stored_id}",
                        extra={
                            "extra_fields": {
                                "document_id": stored_id,
                                "document_path": stored_path,
                                "description": stored_description,
                                "action": "created"
                            }
                        }
                    )
                    
                    return Respons[FileUploadMultipleServiceReadDto](
                        detail="File uploaded successfully",
                        data=[
                            FileUploadMultipleServiceReadDto(
                                id=stored_id
                            )
                        ],
                        success=True,
                        status_code=200,
                        error=None
                    )
            except Exception as db_error:
                logger.error(
                    f"Failed to store document path in database: {str(db_error)}",
                    extra={"extra_fields": {"document_path": modified_blob_path, "error": str(db_error)}},
                    exc_info=True
                )
                return Respons[FileUploadMultipleServiceReadDto](
                    detail=f"File uploaded but failed to store metadata: {str(db_error)}",
                    data=[],
                    success=False,
                    status_code=500,
                    error=str(db_error),
                )

        except Exception as e:
            logger.error(
                f"Error uploading file: {str(e)}",
                extra={"extra_fields": {"blob_path": data.blob_path, "error": str(e)}},
                exc_info=True
            )
            return Respons[FileUploadMultipleServiceReadDto](
                detail=f"An error occurred while uploading file: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )

    @staticmethod
    def upload_multiple_files(
        files_data: list[tuple[FileUploadServiceWriteDto, str]],  # (file_data, document_name)
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[FileUploadMultipleServiceReadDto]:
        """Upload multiple files to Azure Storage and store document information"""
        results = []
        errors = []
        
        for file_data, document_name in files_data:
            try:
                # Validate blob_path is not empty
                if not file_data.blob_path or not file_data.blob_path.strip():
                    errors.append(f"blob_path is required but was empty for file: {document_name or 'unknown'}")
                    continue

                # Generate document_id first
                document_id = Helper.generate_unique_identifier(prefix="doc")
                
                # Insert document_id as a folder in the path: e.g., "folder/file.pdf" -> "folder/doc-123/file.pdf"
                import os
                blob_path_dir = os.path.dirname(file_data.blob_path) if os.path.dirname(file_data.blob_path) else ""
                blob_path_filename = os.path.basename(file_data.blob_path)
                # Insert document_id as a directory: e.g., "folder/file.pdf" -> "folder/doc-123/file.pdf"
                if blob_path_dir:
                    modified_blob_path = f"{blob_path_dir}/{document_id}/{blob_path_filename}"
                else:
                    modified_blob_path = f"{document_id}/{blob_path_filename}"
                
                # Extract filename from original blob_path or use document_name if provided
                file_name = document_name if document_name and document_name.strip() else FileUploadService._extract_filename_from_path(file_data.blob_path)
                
                # Upload file to Azure Storage using the modified blob_path
                upload_result = FileUploadService._upload_file_to_storage(
                    file_content=file_data.file_content,
                    content_type=file_data.content_type,
                    container_name=file_data.container_name,
                    blob_path=modified_blob_path,
                )

                if not upload_result.success:
                    errors.append(f"Failed to upload {modified_blob_path}: {upload_result.error}")
                    continue
                
                # Store document information in database
                cdate = Helper.current_date_time()["cdate"]
                ctime = Helper.current_date_time()["ctime"]
                cdatetime = Helper.current_date_time()["cdatetime"]
                
                try:
                    with DatabaseManager.transaction() as cursor:
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, document_path, file_name, description, 
                             delete_status, is_active, cdate, ctime, cdatetime, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id, document_path, description""",
                            (
                                document_id,
                                tenant_id,
                                org_id,
                                bus_id,
                                loc_id,
                                modified_blob_path,  # Store modified path with document_id
                                file_name,  # Store extracted filename
                                file_data.description,
                                'NOT_DELETED',
                                True,
                                cdate,
                                ctime,
                                cdatetime,
                                created_by,
                            ),
                        )
                        db_result = cursor.fetchone()
                        doc_dict = dict(db_result) if db_result else {}
                        stored_id = doc_dict.get('id', document_id)

                        logger.info(
                            f"Document path stored successfully: {stored_id}",
                            extra={
                                "extra_fields": {
                                    "document_id": stored_id,
                                    "document_path": modified_blob_path,
                                    "action": "created"
                                }
                            }
                        )

                        # Return only id
                        results.append(
                            FileUploadMultipleServiceReadDto(
                                id=stored_id
                            )
                        )
                except Exception as db_error:
                    logger.error(
                        f"Failed to store document path in database: {str(db_error)}",
                        extra={"extra_fields": {"document_path": modified_blob_path, "error": str(db_error)}},
                        exc_info=True
                    )
                    errors.append(f"Failed to store document info for {modified_blob_path}: {str(db_error)}")
                    # Continue even if database insert fails - file is already uploaded
            except Exception as e:
                logger.error(
                    f"Error uploading file: {str(e)}",
                    extra={"extra_fields": {"document_path": document_path if 'document_path' in locals() else 'unknown', "error": str(e)}},
                    exc_info=True
                )
                errors.append(f"Error uploading file: {str(e)}")
        
        if not results:
            return Respons[FileUploadMultipleServiceReadDto](
                detail="Failed to upload any files",
                data=[],
                success=False,
                status_code=500,
                error="; ".join(errors) if errors else "Upload failed"
            )
        
        detail = f"Uploaded {len(results)} file(s) successfully"
        if errors:
            detail += f". {len(errors)} file(s) failed: {'; '.join(errors)}"
        
        # If there are errors, operation did not fully succeed
        return Respons[FileUploadMultipleServiceReadDto](
            detail=detail,
            data=results,
            success=False if errors else True,
            status_code=200 if not errors else 207,  # 207 Multi-Status for partial success
            error="; ".join(errors) if errors else None
            )

    @staticmethod
    def update_file(
        data: FileUpdateServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str,
        file_name: Optional[str] = None,
    ) -> Respons[FileResponseServiceReadDto]:
        """Update file in Azure Storage and update document_path and description in database"""
        try:
            if not data.document_id:
                return Respons[FileResponseServiceReadDto](
                    detail="document_id must be provided",
                    data=[],
                    success=False,
                    status_code=400,
                    error="document_id is required",
                )

            container_name = db_settings.MYSTOREGUARD_FILES_CONTAINER

            with DatabaseManager.transaction() as cursor:
                # Get document by document_id to get old path
                cursor.execute(
                    f"""SELECT id, document_path, description
                    FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                    WHERE tenant_id = %s
                    AND org_id = %s
                    AND bus_id = %s
                    AND loc_id = %s
                    AND id = %s
                    AND delete_status = 'NOT_DELETED'
                    AND is_active = true""",
                    (tenant_id, org_id, bus_id, loc_id, data.document_id),
                )
                document = cursor.fetchone()

                if not document:
                    return Respons[FileResponseServiceReadDto](
                        detail="Document not found",
                        data=[],
                        success=False,
                        status_code=404,
                        error="Document not found",
                    )

                doc_dict = dict(document)
                old_document_path = doc_dict.get('document_path')
                new_document_path = data.blob_path.strip() if data.blob_path and data.blob_path.strip() else old_document_path
                
                # Extract filename: from new path if path changed, from file_name parameter if provided, otherwise keep existing
                if new_document_path != old_document_path:
                    new_file_name = FileUploadService._extract_filename_from_path(new_document_path)
                elif file_name:
                    new_file_name = file_name
                else:
                    new_file_name = None  # Don't update filename if path unchanged and no filename provided

                # If path changed, delete old file and upload new one
                if new_document_path != old_document_path:
                    # Delete old file from storage
                    from trovesuite.storage import StorageService
                    from trovesuite.storage.storage_write_dto import StorageFileDeleteServiceWriteDto
                    import os
                    
                    delete_dto = StorageFileDeleteServiceWriteDto(
                        storage_account_url=f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net",
                        container_name=container_name,
                        blob_name=old_document_path,
                        managed_identity_client_id=db_settings.USER_ASSIGNED_MANAGED_IDENTITY,
                    )
                    StorageService.delete_file(delete_dto)
                    
                    # Upload new file to new path
                    upload_result = FileUploadService._upload_file_to_storage(
                        file_content=data.file_content,
                        content_type=data.content_type,
                        container_name=container_name,
                        blob_path=new_document_path,
                    )
                    
                    if not upload_result.success:
                        return Respons[FileResponseServiceReadDto](
                            detail="Failed to upload file to new path",
                            data=[],
                            success=False,
                            status_code=500,
                            error=upload_result.error or "Upload failed"
                        )
                else:
                    # Update file in Azure Storage using same path
                    update_result = FileUploadService._update_file_in_storage(
                        file_content=data.file_content,
                        content_type=data.content_type,
                        container_name=container_name,
                        blob_path=old_document_path,
                    )

                    if not update_result.success:
                        return Respons[FileResponseServiceReadDto](
                            detail="Failed to update file in Azure Storage",
                            data=[],
                            success=False,
                            status_code=500,
                            error=update_result.error or "Update failed"
                        )

                # Update document_path (if changed), file_name (if provided or path changed), and description in database
                if new_document_path != old_document_path:
                    # Path changed - update path and filename
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                        SET document_path = %s, file_name = %s, description = %s, updated_by = %s
                        WHERE tenant_id = %s
                        AND org_id = %s
                        AND bus_id = %s
                        AND loc_id = %s
                        AND id = %s
                        RETURNING id""",
                        (new_document_path, new_file_name, data.description, updated_by, tenant_id, org_id, bus_id, loc_id, data.document_id),
                    )
                elif new_file_name:
                    # Path unchanged but filename provided - update filename and description
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                        SET file_name = %s, description = %s, updated_by = %s
                        WHERE tenant_id = %s
                        AND org_id = %s
                        AND bus_id = %s
                        AND loc_id = %s
                        AND id = %s
                        RETURNING id""",
                        (new_file_name, data.description, updated_by, tenant_id, org_id, bus_id, loc_id, data.document_id),
                    )
                else:
                    # Only update description
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                        SET description = %s, updated_by = %s
                        WHERE tenant_id = %s
                        AND org_id = %s
                        AND bus_id = %s
                        AND loc_id = %s
                        AND id = %s
                        RETURNING id""",
                        (data.description, updated_by, tenant_id, org_id, bus_id, loc_id, data.document_id),
                    )
                updated_doc = cursor.fetchone()
                updated_id = dict(updated_doc).get('id', data.document_id) if updated_doc else data.document_id
            
                logger.info(
                    f"File updated successfully: {new_document_path}",
                    extra={
                        "extra_fields": {
                            "container_name": container_name,
                            "old_document_path": old_document_path,
                            "new_document_path": new_document_path,
                            "document_id": data.document_id,
                            "path_changed": new_document_path != old_document_path
                        }
                    }
                )

                return Respons[FileResponseServiceReadDto](
                    detail="File updated successfully",
                    data=[
                        FileResponseServiceReadDto(
                            id=updated_id,
                            presigned_url="",  # Not needed for update response
                            description=None  # Not needed for update response
                        )
                    ],
                    success=True,
                    status_code=200,
                    error=None
                )

        except Exception as e:
            logger.error(
                f"Failed to update file: {str(e)}",
                extra={"extra_fields": {"document_id": data.document_id, "error": str(e)}},
                exc_info=True
            )
            return Respons[FileResponseServiceReadDto](
                detail=f"An error occurred while updating file: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )

    @staticmethod
    def delete_file(
        data: FileDeleteServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        deleted_by: str,
    ) -> Respons[FileDeleteServiceReadDto]:
        """Delete file from Azure Storage and database by document_id and document_path"""
        try:
            from trovesuite.storage import StorageService
            from trovesuite.storage.storage_write_dto import StorageFileDeleteServiceWriteDto
            import os

            if not data.document_id:
                return Respons[FileDeleteServiceReadDto](
                    detail="document_id must be provided",
                    data=[],
                    success=False,
                    status_code=400,
                    error="document_id is required",
                )

            with DatabaseManager.transaction() as cursor:
                # Get document by document_id to retrieve the path
                cursor.execute(
                    f"""SELECT id, document_path
                    FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                    WHERE tenant_id = %s
                    AND org_id = %s
                    AND bus_id = %s
                    AND loc_id = %s
                    AND id = %s
                    AND delete_status = 'NOT_DELETED'
                    AND is_active = true""",
                    (tenant_id, org_id, bus_id, loc_id, data.document_id),
                )
                document = cursor.fetchone()

                if not document:
                    return Respons[FileDeleteServiceReadDto](
                        detail="Document not found",
                        data=[],
                        success=False,
                        status_code=404,
                        error="Document not found",
                    )

                container_name = db_settings.MYSTOREGUARD_FILES_CONTAINER
                doc_dict = dict(document)
                document_path = doc_dict.get('document_path')

                try:
                    # Delete from Azure Storage using path from database
                    delete_dto = StorageFileDeleteServiceWriteDto(
                        storage_account_url=f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net",
                        container_name=container_name,
                        blob_name=document_path,
                        managed_identity_client_id=db_settings.USER_ASSIGNED_MANAGED_IDENTITY,
                    )

                    delete_result = StorageService.delete_file(delete_dto)

                    if not delete_result.success:
                        logger.warning(
                            f"Failed to delete file from Azure: {document_path}",
                            extra={
                                "extra_fields": {
                                    "container_name": container_name,
                                    "blob_path": document_path,
                                    "error": delete_result.error
                                }
                            }
                        )
                        # Continue to delete from database even if storage deletion fails

                    # Delete from database
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                        WHERE tenant_id = %s
                        AND org_id = %s
                        AND bus_id = %s
                        AND loc_id = %s
                        AND id = %s""",
                        (tenant_id, org_id, bus_id, loc_id, data.document_id),
                    )

                    logger.info(
                        f"Document deleted successfully: {data.document_id}",
                        extra={"extra_fields": {"document_id": data.document_id, "document_path": document_path}}
                    )

                    return Respons[FileDeleteServiceReadDto](
                        detail="File deleted successfully",
                        data=[],
                        success=True,
                        status_code=200,
                        error=None
                    )

                except Exception as e:
                    logger.error(
                        f"Error deleting file: {str(e)}",
                        extra={"extra_fields": {"document_id": data.document_id, "document_path": document_path if 'document_path' in locals() else 'unknown', "error": str(e)}},
                        exc_info=True
                    )
                    return Respons[FileDeleteServiceReadDto](
                        detail=f"An error occurred while deleting file: {str(e)}",
                        data=[],
                        success=False,
                        status_code=500,
                        error=str(e),
                    )

        except Exception as e:
            logger.error(
                f"Failed to delete file: {str(e)}",
                extra={"extra_fields": {"document_id": data.document_id, "error": str(e)}},
                exc_info=True
            )
            return Respons[FileDeleteServiceReadDto](
                detail=f"An error occurred while deleting file: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )

    @staticmethod
    def delete_files_by_loan_id(
        loan_id: str,
        client_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> tuple[int, list[str]]:
        """
        Delete all files associated with a loan from Azure Storage.
        This is called before deleting a loan to ensure files are removed from storage.
        DEPRECATED: Use delete_files_by_source with resource_source_type='loan' and source_id=loan_id instead.

        Returns:
            tuple: (deleted_count, errors) - Number of files deleted and list of errors
        """
        try:
            from trovesuite.storage import StorageService
            from trovesuite.storage.storage_write_dto import StorageFileDeleteServiceWriteDto
            import os

            with DatabaseManager.transaction() as cursor:
                # Fetch all documents for this loan (using new schema)
                cursor.execute(
                    f"""SELECT id, document_path
                    FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                    WHERE tenant_id = %s
                    AND org_id = %s
                    AND bus_id = %s
                    AND loc_id = %s
                    AND source_type = 'loan'
                    AND source_id = %s
                    AND delete_status = 'NOT_DELETED'
                    AND is_active = true""",
                    (tenant_id, org_id, bus_id, loc_id, loan_id),
                )
                documents = cursor.fetchall()

                if not documents:
                    logger.info(
                        f"No documents found for loan {loan_id}",
                        extra={"extra_fields": {"loan_id": loan_id, "client_id": client_id}}
                    )
                    return 0, []

                container_name = db_settings.MYSTOREGUARD_FILES_CONTAINER
                deleted_count = 0
                errors = []

                # Delete each file from Azure Storage
                for doc in documents:
                    doc_dict = dict(doc)
                    document_path = doc_dict.get('document_path')

                    try:
                        # Delete from Azure Storage
                        delete_dto = StorageFileDeleteServiceWriteDto(
                            storage_account_url=f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net",
                            container_name=container_name,
                            blob_name=document_path,
                            managed_identity_client_id=db_settings.USER_ASSIGNED_MANAGED_IDENTITY,
                        )

                        delete_result = StorageService.delete_file(delete_dto)

                        if delete_result.success:
                            deleted_count += 1
                            logger.debug(
                                f"Deleted file from Azure Storage: {document_path}",
                                extra={"extra_fields": {"loan_id": loan_id, "document_path": document_path}}
                            )
                        else:
                            errors.append(f"Failed to delete {document_path}: {delete_result.error}")
                            logger.warning(
                                f"Failed to delete file from Azure: {document_path}",
                                extra={
                                    "extra_fields": {
                                        "container_name": container_name,
                                        "blob_path": document_path,
                                        "error": delete_result.error,
                                        "loan_id": loan_id
                                    }
                                }
                            )
                    except Exception as e:
                        errors.append(f"Error deleting {document_path}: {str(e)}")
                        logger.error(
                            f"Error deleting file: {str(e)}",
                            extra={"extra_fields": {"document_path": document_path, "loan_id": loan_id, "error": str(e)}},
                            exc_info=True
                        )

                logger.info(
                    f"Deleted {deleted_count} file(s) from Azure Storage for loan {loan_id}",
                    extra={"extra_fields": {"loan_id": loan_id, "client_id": client_id, "deleted_count": deleted_count, "errors": errors}}
                )

                return deleted_count, errors

        except Exception as e:
            logger.error(
                f"Failed to delete files for loan {loan_id}: {str(e)}",
                extra={"extra_fields": {"loan_id": loan_id, "client_id": client_id, "error": str(e)}},
                exc_info=True
            )
            return 0, [f"Error deleting files: {str(e)}"]

    @staticmethod
    def get_document(
        data: GetDocumentServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetDocumentServiceReadDto]:
        """Get a single document by path, look up details from database, and generate presigned URL"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Look up document in database by document_path
                cursor.execute(
                    f"""SELECT id, source_type, source_id, tenant_id, org_id, bus_id, loc_id, document_path,
                         file_name, description
                    FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                    WHERE document_path = %s
                    AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    AND delete_status = 'NOT_DELETED' AND is_active = true
                    LIMIT 1""",
                    (data.document_path, tenant_id, org_id, bus_id, loc_id),
                )
                document = cursor.fetchone()

                if not document:
                    return Respons[GetDocumentServiceReadDto](
                        detail="Document not found",
                        data=[],
                        success=False,
                        status_code=404,
                        error=None,
                    )

                doc_dict = dict(document)
                
                # Get container name from settings (or you could store it in the table)
                container_name = db_settings.MYSTOREGUARD_FILES_CONTAINER
                
                # Generate presigned URL
                presigned_url = FileUploadService._get_file_presigned_url(
                    container_name=container_name,
                    blob_path=data.document_path,
                    expiry_hours=24
                )

                if not presigned_url:
                    return Respons[GetDocumentServiceReadDto](
                        detail="Failed to generate presigned URL",
                        data=[],
                        success=False,
                        status_code=500,
                        error="URL generation failed",
                    )

                response_data = GetDocumentServiceReadDto(
                    id=doc_dict.get('id'),
                    resource_source_type=doc_dict.get('source_type'),
                    source_id=doc_dict.get('source_id'),
                    document_path=doc_dict.get('document_path'),
                    document_name=doc_dict.get('document_name'),
                    description=doc_dict.get('description'),
                    presigned_url=presigned_url,
                    container_name=container_name,
                )

                return Respons[GetDocumentServiceReadDto](
                    detail="Document retrieved successfully",
                    data=[response_data],
                success=True,
                status_code=200,
                    error=None,
            )

        except Exception as e:
            logger.error(
                f"Error getting document: {str(e)}",
                extra={"extra_fields": {"document_path": data.document_path, "error": str(e)}},
                exc_info=True
            )
            return Respons[GetDocumentServiceReadDto](
                detail=f"An error occurred while getting document: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )

    @staticmethod
    def list_documents(
        data: ListDocumentsServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[FileResponseServiceReadDto]:
        """Get documents by document IDs and generate presigned URLs"""
        try:
            document_ids = data.document_ids
            
            if not document_ids:
                return Respons[FileResponseServiceReadDto](
                    detail="No document IDs provided",
                    data=[],
                    success=False,
                    status_code=400,
                    error="document_ids list cannot be empty",
                )
            
            with DatabaseManager.transaction() as cursor:
                # Find documents by document IDs
                # Use ANY array for PostgreSQL
                cursor.execute(
                    f"""SELECT id, document_path, file_name, description
                    FROM {db_settings.MSG_DOCUMENT_PATHS_TABLE}
                    WHERE tenant_id = %s
                    AND org_id = %s
                    AND bus_id = %s
                    AND loc_id = %s
                    AND id = ANY(%s)
                    AND delete_status = 'NOT_DELETED'
                    AND is_active = true
                    ORDER BY cdatetime DESC""",
                    (tenant_id, org_id, bus_id, loc_id, document_ids),
                )
                documents = cursor.fetchall()

                if not documents:
                    return Respons[FileResponseServiceReadDto](
                        detail="No documents found",
                        data=[],
                        success=False,
                        status_code=404,
                        error=None,
                    )

                results = []
                container_name = db_settings.MYSTOREGUARD_FILES_CONTAINER
                expiry_hours = 24
                
                for doc in documents:
                    doc_dict = dict(doc)
                    doc_id = doc_dict.get('id')
                    stored_path = doc_dict.get('document_path')
                    file_name = doc_dict.get('file_name')
                    description = doc_dict.get('description')
                    
                    # Generate presigned URL using the document_path (24 hours expiry)
                    presigned_url = FileUploadService._get_file_presigned_url(
                        container_name=container_name,
                        blob_path=stored_path,
                        expiry_hours=expiry_hours
                    )

                    if presigned_url:
                        results.append(
                            FileResponseServiceReadDto(
                                id=doc_id,
                                presigned_url=presigned_url,
                                description=description,
                                file_name=file_name
                            )
                        )
                    else:
                        logger.warning(
                            f"Failed to generate presigned URL for document {doc_id}",
                            extra={
                                "extra_fields": {
                                    "doc_id": doc_id,
                                    "document_path": stored_path,
                                    "container_name": container_name
                                }
                            }
                        )

                if not results:
                    return Respons[FileResponseServiceReadDto](
                        detail="Failed to generate presigned URLs for any documents",
                        data=[],
                        success=False,
                        status_code=500,
                        error="URL generation failed for all documents",
                    )

                return Respons[FileResponseServiceReadDto](
                    detail=f"Retrieved {len(results)} document(s) successfully",
                    data=results,
                    success=True,
                    status_code=200,
                    error=None,
                )

        except Exception as e:
            logger.error(
                f"Error listing documents: {str(e)}",
                extra={"extra_fields": {"document_ids": data.document_ids, "error": str(e)}},
                exc_info=True
            )
            return Respons[FileResponseServiceReadDto](
                detail=f"An error occurred while listing documents: {str(e)}",
                data=[],
                success=False,
                status_code=500,
                error=str(e),
            )
