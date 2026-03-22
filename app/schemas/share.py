from datetime import datetime

from pydantic import BaseModel


class UploadFileResponse(BaseModel):
    file_id: str
    original_name: str
    mime_type: str
    size_bytes: int


class CreateShareResponse(BaseModel):
    file_id: str
    expires_at: datetime
    download_url: str
