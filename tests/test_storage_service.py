from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from app.services.storage import StorageService


def _client_error(code: str) -> ClientError:
    return ClientError(error_response={"Error": {"Code": code, "Message": "mock"}}, operation_name="HeadObject")


def test_head_object_returns_none_for_not_found_codes():
    service = StorageService()
    service.internal_client = Mock()

    for code in ("404", "NoSuchKey", "NotFound"):
        service.internal_client.head_object.side_effect = _client_error(code)
        assert service.head_object("uploads/abc") is None


def test_head_object_raises_for_non_404_client_error():
    service = StorageService()
    service.internal_client = Mock()
    service.internal_client.head_object.side_effect = _client_error("AccessDenied")

    with pytest.raises(ClientError):
        service.head_object("uploads/abc")
