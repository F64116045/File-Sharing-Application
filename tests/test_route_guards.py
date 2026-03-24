import uuid
import datetime as dt
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.api.routes as routes_module
from app.api.routes import complete_upload, create_share, download_by_share_token
from app.models.file import File
from app.models.share import Share


class FakeSession:
    def __init__(self, file_obj=None, share_obj=None):
        self.file_obj = file_obj
        self.share_obj = share_obj

    def get(self, model, key):
        return self.file_obj

    def scalar(self, *_args, **_kwargs):
        return self.share_obj

    def add(self, _obj):
        return None

    def commit(self):
        return None


class FakeRequest:
    def __init__(self):
        self.state = SimpleNamespace(request_id="test-request-id")


def test_create_share_rejects_when_upload_not_completed():
    file_id = uuid.uuid4()
    db = FakeSession(
        file_obj=File(
            id=file_id,
            original_name="a.txt",
            object_key=f"uploads/{file_id}",
            mime_type="text/plain",
            size_bytes=10,
            is_uploaded=False,
        )
    )
    request = FakeRequest()

    with pytest.raises(HTTPException) as exc:
        create_share(file_id=file_id, request=request, expires_in_hours=24, db=db)

    assert exc.value.status_code == 409
    assert exc.value.detail == "File upload not completed"


def test_create_share_rejects_when_file_not_found():
    file_id = uuid.uuid4()
    db = FakeSession(file_obj=None)
    request = FakeRequest()

    with pytest.raises(HTTPException) as exc:
        create_share(file_id=file_id, request=request, expires_in_hours=24, db=db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "File not found"


def test_download_rejects_invalid_share_token():
    db = FakeSession(share_obj=None)
    request = FakeRequest()

    with pytest.raises(HTTPException) as exc:
        download_by_share_token(token="invalid-token", request=request, db=db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Invalid share link"


def test_download_rejects_expired_share_link():
    file_id = uuid.uuid4()
    share = Share(
        id=uuid.uuid4(),
        file_id=file_id,
        token_hash="dummy",
        expires_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
    )
    file_obj = File(
        id=file_id,
        original_name="expired.txt",
        object_key=f"uploads/{file_id}",
        mime_type="text/plain",
        size_bytes=10,
        is_uploaded=True,
    )
    db = FakeSession(file_obj=file_obj, share_obj=share)
    request = FakeRequest()

    with pytest.raises(HTTPException) as exc:
        download_by_share_token(token="any-token", request=request, db=db)

    assert exc.value.status_code == 410
    assert exc.value.detail == "Share link expired"


def test_download_rejects_when_file_not_found():
    file_id = uuid.uuid4()
    share = Share(
        id=uuid.uuid4(),
        file_id=file_id,
        token_hash="dummy",
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
    )
    db = FakeSession(file_obj=None, share_obj=share)
    request = FakeRequest()

    with pytest.raises(HTTPException) as exc:
        download_by_share_token(token="any-token", request=request, db=db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "File not found"


def test_complete_upload_rejects_when_size_mismatch(monkeypatch):
    file_id = uuid.uuid4()
    file_obj = File(
        id=file_id,
        original_name="mismatch.txt",
        object_key=f"uploads/{file_id}",
        mime_type="text/plain",
        size_bytes=10,
        is_uploaded=False,
    )
    db = FakeSession(file_obj=file_obj)
    request = FakeRequest()

    monkeypatch.setattr(
        routes_module.storage_service,
        "head_object",
        lambda _object_key: {"ContentLength": 12},
    )

    with pytest.raises(HTTPException) as exc:
        complete_upload(file_id=file_id, request=request, db=db)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Uploaded object size mismatch"
