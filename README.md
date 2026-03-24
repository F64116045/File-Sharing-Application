# File Sharing Application

This repository is my submission for the PicCollage Backend Developer Intern Take-Home Quiz.

A FastAPI file sharing application with expiring links, presigned MinIO (S3-compatible API) uploads/downloads, PostgreSQL metadata, and Dockerized setup.

## TL;DR
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec app alembic upgrade head
```

Open:
- Demo UI: `http://localhost:8000/demo`
- Swagger: `http://localhost:8000/docs`

## Quick Demo
![Quick Demo](assets/Demo.gif)

## Scope
This project currently supports:
- Initiating file uploads and uploading file bytes directly to object storage using presigned URLs
- Completing upload with backend verification (`HEAD` object check)
- Creating share links for uploaded files
- Setting custom share expiration (`expires_in_hours`)
- Downloading files through share links with expiration validation
- Hard-to-guess share tokens (stored as hash in database)

## Architecture
### Stack
- API: FastAPI
- DB: PostgreSQL
- Object Storage: MinIO (S3-compatible)
- Background worker: Scheduled DB cleanup script
- Migration: Alembic
- Local dev: uv
- Container: Docker Compose

### System Diagram
```mermaid
flowchart TB
    U[User]
    FE[Browser Frontend]

    subgraph AppLayer[Application Layer]
      API[FastAPI API]
      DB[(PostgreSQL Metadata)]
    end

    subgraph StorageLayer[Storage Layer]
      S3[(MinIO S3 Object Storage)]
    end

    subgraph OpsLayer[Operations]
      CW[Cleanup Worker Scheduler]
    end

    U --> FE

    FE -->|Initiate upload, complete upload, create share, access share link| API
    API -->|Issue presigned upload and download URLs| FE

    FE -->|Direct file upload and download| S3
    API -->|Object verify via HEAD| S3

    API -->|Validate token and expiry| DB
    CW -->|Delete expired shares and stale unfinished uploads| DB
```

### Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    participant FE as Frontend
    participant API as FastAPI
    participant DB as PostgreSQL
    participant S3 as MinIO/S3

    FE->>API: POST /api/v1/uploads/initiate
    API->>DB: Insert file (is_uploaded=false)
    API-->>FE: file_id + presigned PUT URL

    FE->>S3: PUT file bytes
    S3-->>FE: 200 OK

    FE->>API: POST /api/v1/uploads/{file_id}/complete
    API->>S3: HEAD object
    S3-->>API: object metadata
    API->>DB: Update file (is_uploaded=true)
    API-->>FE: upload complete

    FE->>API: POST /api/v1/files/{file_id}/shares?expires_in_hours=24
    API->>DB: Insert share (token_hash, expires_at)
    API-->>FE: download_url (/s/:token)

    FE->>API: GET /s/:token
    API->>DB: Validate token + expiry + file status
    API-->>FE: 307 redirect (presigned GET URL)
    FE->>S3: GET object
    S3-->>FE: file bytes
```

## API Flow
### 1) Initiate Upload
`POST /api/v1/uploads/initiate`

Request example:
```json
{
  "original_name": "demo.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 12345
}
```

### 2) Direct Upload
Use returned `upload_url` to upload file directly to MinIO/S3.

### 3) Complete Upload
`POST /api/v1/uploads/{file_id}/complete`

### 4) Create Share Link
`POST /api/v1/files/{file_id}/shares?expires_in_hours=24`

### 5) Download by Share Link
`GET /s/{token}`

## Setup
### Option A: Docker (recommended)
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec app alembic upgrade head
```

### Option B: Local (uv)
```bash
cp .env.example .env
uv venv
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Demo
1. Open `http://localhost:8000/demo`
2. Select a file
3. Click `Run Full Flow`
4. Open generated share URL and verify download

## Testing
Install test dependencies:
```bash
uv sync --extra dev
```

Run tests:
```bash
uv run pytest
```

## DB Cleanup Worker
Dry-run (Docker app container):
```bash
docker compose exec app python scripts/cleanup_db.py --batch-size 500
```

Execute deletion:
```bash
docker compose exec app python scripts/cleanup_db.py --execute --batch-size 500
```

Local uv mode example:
```bash
uv run python scripts/cleanup_db.py \
  --database-url "postgresql+psycopg://app:app@localhost:5432/filesharing" \
  --batch-size 500
```
