# File Sharing Application (FastAPI + PostgreSQL + MinIO)

This project is a take-home implementation for a file sharing web app.

## Features
- Upload a file and generate a share link
- Share links are hard to guess (high-entropy token)
- Share links expire
- MinIO storage via S3 API (easy migration path to AWS S3)

## Stack
- FastAPI
- PostgreSQL (metadata)
- MinIO (object storage)
- Docker / Docker Compose
- uv (local Python environment and dependency management)

## Local Development (uv)
1. Create env file:
```bash
cp .env.example .env
```

2. Create virtual environment and install dependencies:
```bash
uv venv
uv sync
```

3. Start the API locally:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. VS Code setup:
- This repo includes `.vscode/settings.json` and points to `${workspaceFolder}/.venv/bin/python`.
- If warnings still remain, run `Python: Select Interpreter` and choose `.venv/bin/python`.

## Quick Start
1. Create env file:
```bash
cp .env.example .env
```

2. Start services:
```bash
docker compose up --build
```

3. Verify app:
```bash
curl -s http://localhost:8000/health
```

## API
### 1) Upload file
```bash
curl -X POST "http://localhost:8000/api/v1/files/upload" \
  -F "file=@./README.md"
```

Example response:
```json
{
  "file_id": "6d9e8f3b-2f86-42d2-a2f1-9ff71cb43717",
  "original_name": "README.md",
  "mime_type": "text/markdown",
  "size_bytes": 1568
}
```

### 2) Create share link for uploaded file
```bash
curl -X POST "http://localhost:8000/api/v1/files/<file_id>/shares?expires_in_hours=24"
```

Example response:
```json
{
  "file_id": "6d9e8f3b-2f86-42d2-a2f1-9ff71cb43717",
  "expires_at": "2026-03-23T12:00:00.000000Z",
  "download_url": "http://localhost:8000/s/<token>"
}
```

### Download
```bash
curl -L "http://localhost:8000/s/<token>" -o downloaded.file
```

## Notes
- For simplicity, DB schema is auto-created on app startup using SQLAlchemy metadata.
- Production setup should use Alembic migrations and stronger operational hardening.
- `S3_ACCESS_KEY` and `S3_SECRET_KEY` are required environment variables and are not hard-coded in application code.

## Design Doc
See `docs/part1-design.md`.
