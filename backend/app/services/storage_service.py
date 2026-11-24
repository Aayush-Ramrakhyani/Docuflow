"""
S3/MinIO storage service with private-only access.
All document access goes through short-lived signed URLs.
Uploaded filenames are always UUID-based — never the original filename.

The boto3 client is created once per process (module-level singleton via lru_cache)
to avoid credential resolution overhead on every request.
"""

import uuid
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()


def _make_client():
    kwargs = {
        "region_name": settings.AWS_REGION,
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "config": Config(
            signature_version="s3v4",
            # Reuse connections across requests
            max_pool_connections=20,
        ),
    }
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
    return boto3.client("s3", **kwargs)


@lru_cache(maxsize=1)
def _get_client():
    """Module-level boto3 client singleton. Created once per process."""
    return _make_client()


class StorageService:
    """
    Thin wrapper around the shared boto3 client.
    All instances share the same underlying client — no per-request overhead.
    """

    @property
    def _client(self):
        return _get_client()

    def generate_storage_key(self, organization_id: uuid.UUID, extension: str) -> str:
        """Generate a UUID-based storage key. Never uses original filename."""
        safe_ext = extension.lstrip(".").lower()[:10]
        return f"organizations/{organization_id}/documents/{uuid.uuid4()}.{safe_ext}"

    def upload_file(
        self,
        file_obj: BinaryIO,
        bucket: str,
        key: str,
        content_type: str,
    ) -> None:
        self._client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs={
                "ContentType": content_type,
                # Private ACL — no public access
                "ServerSideEncryption": "AES256",
            },
        )

    def download_file(self, bucket: str, key: str) -> bytes:
        """Download a file from storage and return its contents as bytes."""
        obj = self._client.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()

    def generate_signed_download_url(
        self,
        bucket: str,
        key: str,
        expiration: int | None = None,
    ) -> str:
        """
        Generate a signed URL valid for `expiration` seconds.
        Authorization must be verified before calling this method.
        """
        exp = expiration or settings.SIGNED_URL_EXPIRATION_SECONDS
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=exp,
        )

    def delete_file(self, bucket: str, key: str) -> None:
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except ClientError:
            pass  # Already deleted or doesn't exist — not an error

    def file_exists(self, bucket: str, key: str) -> bool:
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
