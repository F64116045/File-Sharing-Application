from botocore.client import Config
import boto3

from app.core.config import settings


class StorageService:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        buckets = self.client.list_buckets().get("Buckets", [])
        if not any(bucket["Name"] == settings.s3_bucket for bucket in buckets):
            self.client.create_bucket(Bucket=settings.s3_bucket)

    def upload_fileobj(self, fileobj, object_key: str, content_type: str) -> None:
        self.client.upload_fileobj(
            Fileobj=fileobj,
            Bucket=settings.s3_bucket,
            Key=object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def get_object_stream(self, object_key: str):
        response = self.client.get_object(Bucket=settings.s3_bucket, Key=object_key)
        return response["Body"]


storage_service = StorageService()
