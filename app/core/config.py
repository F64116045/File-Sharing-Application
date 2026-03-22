from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "file-sharing-app"
    api_v1_prefix: str = "/api/v1"
    base_url: str = "http://localhost:8000"

    postgres_user: str = "app"
    postgres_password: str = "app"
    postgres_db: str = "filesharing"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "shared-files"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    s3_presign_upload_expires_seconds: int = 900
    s3_presign_download_expires_seconds: int = 300

    default_expires_hours: int = 24
    max_upload_size_mb: int = 50

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
