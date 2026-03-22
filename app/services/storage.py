from botocore.exceptions import ClientError
from botocore.client import Config
import boto3

from app.core.config import settings


class StorageService:
    def __init__(self):
        common_kwargs = {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": settings.s3_region,
            "use_ssl": settings.s3_use_ssl,
            "config": Config(signature_version="s3v4"),
        }
        self.internal_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            **common_kwargs,
        )
        self.presign_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_public_endpoint_url or settings.s3_endpoint_url,
            **common_kwargs,
        )

    def ensure_bucket(self) -> None:
        buckets = self.internal_client.list_buckets().get("Buckets", [])
        if not any(bucket["Name"] == settings.s3_bucket for bucket in buckets):
            self.internal_client.create_bucket(Bucket=settings.s3_bucket)

    def generate_presigned_upload_url(self, object_key: str, content_type: str) -> str:
        return self.presign_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.s3_presign_upload_expires_seconds,
        )

    def generate_presigned_download_url(self, object_key: str, filename: str) -> str:
        return self.presign_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": object_key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=settings.s3_presign_download_expires_seconds,
        )

    def head_object(self, object_key: str) -> dict | None:
        try:
            return self.internal_client.head_object(Bucket=settings.s3_bucket, Key=object_key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise


storage_service = StorageService()
