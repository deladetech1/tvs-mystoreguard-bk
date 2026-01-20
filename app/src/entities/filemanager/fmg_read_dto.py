from pydantic import BaseModel
from typing import Optional


# =====================================================
# UNIFIED FILE OPERATIONS READ DTOs
# =====================================================

class FileUploadReadBase(BaseModel):
    """Base read DTO for file upload result"""
    file_url: str
    blob_path: str
    container_name: str
    message: str


class FileUploadMultipleReadBase(BaseModel):
    """Base read DTO for multiple file upload result - returns only the document id"""
    id: str


class FileUploadServiceReadDto(FileUploadReadBase):
    """Service DTO for file upload read operations"""
    pass


class FileUploadMultipleServiceReadDto(FileUploadMultipleReadBase):
    """Service DTO for multiple file upload read operations"""
    pass


class FileResponseReadBase(BaseModel):
    """Unified base read DTO for file operations - returns id, presigned_url, description, and file_name"""
    id: str
    presigned_url: str
    description: Optional[str] = None
    file_name: Optional[str] = None


class FileResponseServiceReadDto(FileResponseReadBase):
    """Service DTO for unified file response read operations"""
    pass


class FileResponseControllerReadDto(FileResponseReadBase):
    """Controller DTO for unified file response read operations"""
    pass


class FileUpdateServiceReadDto(FileUploadReadBase):
    """Service DTO for file update read operations"""
    pass


class FileGetUrlReadBase(BaseModel):
    """Base read DTO for getting file URL"""
    presigned_url: str
    blob_path: str
    container_name: str
    document_name: Optional[str] = None
    description: Optional[str] = None


class FileGetUrlServiceReadDto(FileGetUrlReadBase):
    """Service DTO for get file URL read operations"""
    pass


class FileDeleteReadBase(BaseModel):
    """Base read DTO for deleting a file"""
    blob_path: str
    container_name: str
    message: str


class FileDeleteServiceReadDto(FileDeleteReadBase):
    """Service DTO for delete file read operations"""
    pass


class GetDocumentReadBase(BaseModel):
    """Base read DTO for getting a single document"""
    id: str
    document_path: str
    description: Optional[str] = None
    presigned_url: str


class GetDocumentServiceReadDto(GetDocumentReadBase):
    """Service DTO for getting a single document"""
    pass


class ListDocumentsServiceReadDto(FileResponseReadBase):
    """Service DTO for listing multiple documents"""
    pass
