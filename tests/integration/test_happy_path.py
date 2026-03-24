import json
import hashlib
import os
from urllib.parse import urlparse
import urllib.error
import urllib.request

import psycopg
import pytest


BASE_URL = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8000")
TIMEOUT_SECONDS = float(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "20"))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _json_request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def _put_binary(url: str, content: bytes, content_type: str) -> int:
    req = urllib.request.Request(
        url,
        data=content,
        headers={"Content-Type": content_type},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return resp.status


def _assert_integration_env_available() -> None:
    health_req = urllib.request.Request(f"{BASE_URL}/health", method="GET")
    try:
        with urllib.request.urlopen(health_req, timeout=TIMEOUT_SECONDS) as health_resp:
            assert health_resp.status == 200
    except Exception as exc:  # pragma: no cover - environment precondition
        pytest.skip(f"integration environment unavailable at {BASE_URL}: {exc}")


def _upload_and_complete(content: bytes, mime_type: str, original_name: str) -> str:
    initiate_status, initiate_data = _json_request(
        "POST",
        f"{BASE_URL}/api/v1/uploads/initiate",
        payload={
            "original_name": original_name,
            "mime_type": mime_type,
            "size_bytes": len(content),
        },
    )
    assert initiate_status == 200
    assert initiate_data["file_id"]
    assert initiate_data["upload_url"]
    assert initiate_data["object_key"].startswith("uploads/")

    put_status = _put_binary(initiate_data["upload_url"], content, mime_type)
    assert put_status in {200, 204}

    complete_status, complete_data = _json_request(
        "POST",
        f"{BASE_URL}/api/v1/uploads/{initiate_data['file_id']}/complete",
    )
    assert complete_status == 200
    assert complete_data["is_uploaded"] is True
    assert complete_data["size_bytes"] == len(content)
    return initiate_data["file_id"]


def _extract_share_token(download_url: str) -> str:
    parsed = urlparse(download_url)
    return parsed.path.rsplit("/", 1)[-1]


def _expire_share_by_token(token: str) -> int:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = int(os.getenv("POSTGRES_PORT", "5432"))
    db_name = os.getenv("POSTGRES_DB", "filesharing")
    db_user = os.getenv("POSTGRES_USER", "app")
    db_password = os.getenv("POSTGRES_PASSWORD", "app")

    with psycopg.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE shares
                SET expires_at = NOW() - INTERVAL '1 minute'
                WHERE token_hash = %s
                """,
                (token_hash,),
            )
            rowcount = cur.rowcount
        conn.commit()
    return rowcount


@pytest.mark.integration
def test_e2e_happy_path_upload_share_and_download_redirect():
    _assert_integration_env_available()

    content = b"hello-e2e\n"
    mime_type = "text/plain"
    file_id = _upload_and_complete(content=content, mime_type=mime_type, original_name="e2e.txt")

    share_status, share_data = _json_request(
        "POST",
        f"{BASE_URL}/api/v1/files/{file_id}/shares?expires_in_hours=1",
    )
    assert share_status == 200
    assert share_data["download_url"].startswith(f"{BASE_URL}/s/")

    token_url = share_data["download_url"]
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        opener.open(urllib.request.Request(token_url, method="GET"), timeout=TIMEOUT_SECONDS)
        pytest.fail("expected redirect response")
    except urllib.error.HTTPError as exc:
        assert exc.code == 307
        location = exc.headers.get("Location", "")
        assert location
        assert "X-Amz-" in location


@pytest.mark.integration
def test_e2e_expired_share_returns_410():
    _assert_integration_env_available()

    content = b"hello-expired\n"
    file_id = _upload_and_complete(content=content, mime_type="text/plain", original_name="expired.txt")
    share_status, share_data = _json_request(
        "POST",
        f"{BASE_URL}/api/v1/files/{file_id}/shares?expires_in_hours=1",
    )
    assert share_status == 200
    token_url = share_data["download_url"]
    token = _extract_share_token(token_url)

    try:
        updated_rows = _expire_share_by_token(token)
    except Exception as exc:  # pragma: no cover - environment precondition
        pytest.skip(f"integration DB unavailable for expiration update: {exc}")
    assert updated_rows == 1

    opener = urllib.request.build_opener(_NoRedirect())
    try:
        opener.open(urllib.request.Request(token_url, method="GET"), timeout=TIMEOUT_SECONDS)
        pytest.fail("expected expired share error")
    except urllib.error.HTTPError as exc:
        assert exc.code == 410
