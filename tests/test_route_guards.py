import uuid

import pytest
from fastapi import HTTPException

from app.api.routes import create_share, download_by_share_token
from app.models.file import File


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

    with pytest.raises(HTTPException) as exc:
        create_share(file_id=file_id, expires_in_hours=24, db=db)

    assert exc.value.status_code == 409
    assert exc.value.detail == "File upload not completed"


def test_download_rejects_invalid_share_token():
    db = FakeSession(share_obj=None)

    with pytest.raises(HTTPException) as exc:
        download_by_share_token(token="invalid-token", db=db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Invalid share link"
