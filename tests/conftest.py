import os

# Minimal required settings for test imports.
os.environ.setdefault("S3_ACCESS_KEY", "test-access-key")
os.environ.setdefault("S3_SECRET_KEY", "test-secret-key")

# Keep local test defaults explicit to avoid accidental dependency on host env.
os.environ.setdefault("POSTGRES_USER", "app")
os.environ.setdefault("POSTGRES_PASSWORD", "app")
os.environ.setdefault("POSTGRES_DB", "filesharing")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
