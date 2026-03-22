# File Sharing Application

A backend-focused file sharing web application built with FastAPI, PostgreSQL, and MinIO (S3-compatible API).

## TL;DR
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec app alembic upgrade head
```

Open:
- Demo UI: `http://localhost:8000/demo`
- Swagger: `http://localhost:8000/docs`

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
- Migration: Alembic
- Local dev: uv
- Container: Docker Compose

### System Diagram
```mermaid
flowchart LR
    subgraph Client[Client]
      FE[Browser / Frontend]
    end

    subgraph App[Backend]
      API[FastAPI API]
      DB[(PostgreSQL)]
      API --> DB
    end

    subgraph Storage[Object Storage]
      S3[(MinIO / S3)]
    end

    FE -->|Initiate upload| API
    API -->|Presigned PUT URL| FE
    FE -->|Direct file upload| S3
    FE -->|Complete upload| API
    API -->|HEAD object verify| S3

    FE -->|Create share link| API
    API -->|Store token hash + expiry| DB

    FE -->|GET /s/{token}| API
    API -->|Validate token + expiry| DB
    API -->|307 redirect with presigned GET URL| FE
    FE -->|Direct download| S3
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
    API-->>FE: download_url (/s/{token})

    FE->>API: GET /s/{token}
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
