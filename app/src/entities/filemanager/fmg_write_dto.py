from pydantic import BaseModel
from typing import Optional


# =====================================================
# UNIFIED FILE OPERATIONS WRITE DTOs
# =====================================================

class FileUploadWriteBase(BaseModel):
    """Base write DTO for uploading a file"""
    file_content: bytes
    content_type: str
    container_name: str
    blob_path: str
    description: Optional[str] = None


class FileUploadServiceWriteDto(FileUploadWriteBase):
    """Service DTO for uploading a file"""
    pass


class FileUpdateServiceWriteDto(BaseModel):
    """Service DTO for updating a file"""
    file_content: bytes
    content_type: str
    document_id: str  # Required: Specific document ID to update
    blob_path: Optional[str] = None  # Optional: New document path (if provided, will change the path)
    description: Optional[str] = None  # New description


class FileDeleteServiceWriteDto(BaseModel):
    """Service DTO for deleting a file"""
    document_id: str  # Required: Specific document ID to delete


class FileGetUrlServiceWriteDto(BaseModel):
    """Service DTO for getting file pre-signed URL"""
    container_name: str
    blob_path: str
    expiry_hours: Optional[int] = 24


class GetDocumentWriteBase(BaseModel):
    """Base write DTO for getting document by path"""
    document_path: str  # The document_path (blob_path) to look up


class GetDocumentControllerWriteDto(GetDocumentWriteBase):
    """Controller DTO for getting a single document"""
    pass


class GetDocumentServiceWriteDto(GetDocumentWriteBase):
    """Service DTO for getting a single document"""
    pass


class ListDocumentsWriteBase(BaseModel):
    """Base write DTO for listing multiple documents"""
    document_ids: list[str]  # List of document IDs to retrieve


class ListDocumentsControllerWriteDto(ListDocumentsWriteBase):
    """Controller DTO for listing multiple documents"""
    pass


class ListDocumentsServiceWriteDto(ListDocumentsWriteBase):
    """Service DTO for listing multiple documents"""
    pass
