import pytest
from fastapi import HTTPException

from app.api.routes import _validate_upload_size
from app.core.config import settings


def test_validate_upload_size_accepts_exact_limit():
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    _validate_upload_size(max_bytes)


def test_validate_upload_size_rejects_over_limit():
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    with pytest.raises(HTTPException) as exc:
        _validate_upload_size(max_bytes + 1)

    assert exc.value.status_code == 413
