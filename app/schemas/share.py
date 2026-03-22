from datetime import datetime

from pydantic import BaseModel, Field


class InitiateUploadRequest(BaseModel):
    original_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(default="application/octet-stream", min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)


class InitiateUploadResponse(BaseModel):
    file_id: str
    object_key: str
    upload_url: str
    upload_expires_at: datetime


class CompleteUploadResponse(BaseModel):
    file_id: str
    is_uploaded: bool
    original_name: str
    mime_type: str
    size_bytes: int


class CreateShareResponse(BaseModel):
    file_id: str
    expires_at: datetime
    download_url: str
