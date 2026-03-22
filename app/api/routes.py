import datetime as dt
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.file import File
from app.models.share import Share
from app.schemas.share import (
    CompleteUploadResponse,
    CreateShareResponse,
    InitiateUploadRequest,
    InitiateUploadResponse,
)
from app.services.security import generate_share_token, hash_token
from app.services.storage import storage_service

api_router = APIRouter()
public_router = APIRouter()


@public_router.get("/health")
def health_check():
    return {"status": "ok"}


@public_router.get("/demo")
def demo_page():
    demo_path = Path(__file__).resolve().parent.parent / "web" / "demo.html"
    return FileResponse(demo_path)


def _validate_upload_size(size_bytes: int) -> None:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_upload_size_mb} MB")


def _build_upload_file(payload: InitiateUploadRequest) -> File:
    file_id = uuid.uuid4()
    object_key = f"uploads/{file_id}"
    _validate_upload_size(payload.size_bytes)

    return File(
        id=file_id,
        original_name=payload.original_name,
        object_key=object_key,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        is_uploaded=False,
    )


def _create_share(file_id: uuid.UUID, expires_in_hours: int) -> tuple[Share, str]:
    token = generate_share_token()
    token_digest = hash_token(token)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=expires_in_hours)

    return Share(file_id=file_id, token_hash=token_digest, expires_at=expires_at), token


@api_router.post("/uploads/initiate", response_model=InitiateUploadResponse)
def initiate_upload(
    payload: InitiateUploadRequest,
    db: Session = Depends(get_db),
):
    db_file = _build_upload_file(payload)
    db.add(db_file)
    db.commit()
    upload_url = storage_service.generate_presigned_upload_url(
        object_key=db_file.object_key,
        content_type=db_file.mime_type,
    )
    upload_expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        seconds=settings.s3_presign_upload_expires_seconds
    )
    return InitiateUploadResponse(
        file_id=str(db_file.id),
        object_key=db_file.object_key,
        upload_url=upload_url,
        upload_expires_at=upload_expires_at,
    )


@api_router.post("/uploads/{file_id}/complete", response_model=CompleteUploadResponse)
def complete_upload(file_id: uuid.UUID, db: Session = Depends(get_db)):
    file = db.get(File, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")

    if file.is_uploaded:
        return CompleteUploadResponse(
            file_id=str(file.id),
            is_uploaded=True,
            original_name=file.original_name,
            mime_type=file.mime_type,
            size_bytes=file.size_bytes,
        )

    object_metadata = storage_service.head_object(file.object_key)
    if object_metadata is None:
        raise HTTPException(status_code=409, detail="Object not uploaded yet")

    actual_size_bytes = int(object_metadata.get("ContentLength", 0))
    _validate_upload_size(actual_size_bytes)
    if actual_size_bytes != file.size_bytes:
        raise HTTPException(status_code=409, detail="Uploaded object size mismatch")

    file.is_uploaded = True
    db.add(file)
    db.commit()
    db.refresh(file)

    return CompleteUploadResponse(
        file_id=str(file.id),
        is_uploaded=file.is_uploaded,
        original_name=file.original_name,
        mime_type=file.mime_type,
        size_bytes=file.size_bytes,
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
    if not file.is_uploaded:
        raise HTTPException(status_code=409, detail="File upload not completed")

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
    if not file.is_uploaded:
        raise HTTPException(status_code=404, detail="File not available")

    download_url = storage_service.generate_presigned_download_url(
        object_key=file.object_key,
        filename=file.original_name,
    )
    return RedirectResponse(url=download_url, status_code=307)
