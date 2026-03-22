import datetime as dt
import uuid

from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.file import File
from app.models.share import Share
from app.schemas.share import CreateShareResponse, UploadFileResponse
from app.services.security import generate_share_token, hash_token
from app.services.storage import storage_service

api_router = APIRouter()
public_router = APIRouter()


@public_router.get("/health")
def health_check():
    return {"status": "ok"}


def _validate_upload_size(file: UploadFile) -> int:
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_upload_size_mb} MB")
    return size_bytes


def _upload_file(file: UploadFile) -> File:
    file_id = uuid.uuid4()
    object_key = f"uploads/{file_id}/{file.filename}"
    mime_type = file.content_type or "application/octet-stream"
    size_bytes = _validate_upload_size(file)

    storage_service.upload_fileobj(file.file, object_key=object_key, content_type=mime_type)

    return File(
        id=file_id,
        original_name=file.filename,
        object_key=object_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )


def _create_share(file_id: uuid.UUID, expires_in_hours: int) -> tuple[Share, str]:
    token = generate_share_token()
    token_digest = hash_token(token)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=expires_in_hours)

    return Share(file_id=file_id, token_hash=token_digest, expires_at=expires_at), token


@api_router.post("/files/upload", response_model=UploadFileResponse)
def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
):
    db_file = _upload_file(file)
    db.add(db_file)
    db.commit()
    return UploadFileResponse(
        file_id=str(db_file.id),
        original_name=db_file.original_name,
        mime_type=db_file.mime_type,
        size_bytes=db_file.size_bytes,
    )


@api_router.post("/files/{file_id}/shares", response_model=CreateShareResponse)
def create_share(
    file_id: uuid.UUID,
    expires_in_hours: int = Query(default=settings.default_expires_hours, ge=1, le=168),
    db: Session = Depends(get_db),
):
    file = db.get(File, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")

    db_share, token = _create_share(file_id=file.id, expires_in_hours=expires_in_hours)
    db.add(db_share)
    db.commit()

    return CreateShareResponse(
        file_id=str(file.id),
        expires_at=db_share.expires_at,
        download_url=f"{settings.base_url}/s/{token}",
    )


@public_router.get("/s/{token}")
def download_by_share_token(token: str, db: Session = Depends(get_db)):
    token_digest = hash_token(token)
    share = db.scalar(select(Share).where(Share.token_hash == token_digest))

    if share is None:
        raise HTTPException(status_code=404, detail="Invalid share link")

    if dt.datetime.now(dt.timezone.utc) > share.expires_at:
        raise HTTPException(status_code=410, detail="Share link expired")

    file = db.get(File, share.file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")

    stream = storage_service.get_object_stream(file.object_key)
    headers = {"Content-Disposition": f'attachment; filename="{file.original_name}"'}
    return StreamingResponse(stream, media_type=file.mime_type, headers=headers)
