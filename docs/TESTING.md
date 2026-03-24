# Testing Guide

This document explains the current test strategy, how to run tests locally, and how to troubleshoot common failures.

## 1. Test Strategy

The project uses two layers of tests:

- Unit tests
  - Fast feedback
  - Validate route guards, token/security logic, cleanup logic, and storage-service behavior with mocks
- Integration tests
  - Validate end-to-end behavior across API + PostgreSQL + MinIO (S3-compatible)
  - No S3/DB mocking for core file flow

## 2. Current Coverage

Unit tests currently cover:

- Token generation and hashing behavior
- Route guard behavior:
  - missing file
  - file not uploaded
  - expired share
  - invalid share
  - upload size mismatch handling
- Storage service `head_object` behavior with mock client
- DB cleanup script behavior (expired shares and stale uploads)

Integration tests currently cover:

- Happy path:
  - initiate upload
  - direct PUT to presigned upload URL
  - complete upload
  - create share
  - token download redirect
- Expired share path (`410`)
- Complete upload size mismatch path (`409`)

## 3. Prerequisites

Install dependencies:

```bash
uv sync --extra dev
```

For integration tests, start services first:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec app alembic upgrade head
```

Important endpoint note:

- Server internal S3 endpoint can be Docker DNS (`http://minio:9000`)
- Browser-facing/presigned endpoint should be host-reachable (for local demo: `http://localhost:9000`)

## 4. Run Tests

Run all tests:

```bash
uv run pytest
```

Run only unit tests:

```bash
uv run pytest -m "not integration"
```

Run only integration tests:

```bash
uv run pytest -m integration -rs
```

## 5. Coverage Report

Terminal summary:

```bash
uv run pytest --cov=app --cov-report=term-missing
```

HTML report:

```bash
uv run pytest --cov=app --cov-report=html
```

Then open `htmlcov/index.html`.

## 6. CI Behavior

GitHub Actions workflow:

- File: `.github/workflows/ci.yml`
- Installs dependencies with `uv sync --extra dev`
- Runs `uv run pytest`

If integration infrastructure is not available in CI, integration tests are expected to skip by design.

## 7. Troubleshooting

`ValidationError: s3_access_key / s3_secret_key missing`:

- Ensure tests load required env values.
- This repository includes test defaults in `tests/conftest.py`.

`ERR_NAME_NOT_RESOLVED` for upload URL in browser:

- Presigned URL host is not browser-resolvable.
- Set browser-facing endpoint to `S3_PUBLIC_ENDPOINT_URL=http://localhost:9000`.

Integration tests are skipped:

- Usually means app/minio/postgres is not reachable from the test runtime.
- Confirm `http://localhost:8000/health` responds.

