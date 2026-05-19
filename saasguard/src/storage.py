import time
from io import BytesIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from src.config import get_settings


def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket_exists() -> None:
    settings = get_settings()
    last_error = None
    for _ in range(10):
        client = get_s3_client()
        try:
            client.head_bucket(Bucket=settings.minio_bucket)
            return
        except ClientError:
            try:
                client.create_bucket(Bucket=settings.minio_bucket)
                return
            except ClientError as exc:
                last_error = exc
                time.sleep(1)

    raise last_error or RuntimeError("minio bucket initialization failed")


def upload_csv(object_key: str, content: bytes) -> None:
    settings = get_settings()
    ensure_bucket_exists()
    client = get_s3_client()
    client.upload_fileobj(
        Fileobj=BytesIO(content),
        Bucket=settings.minio_bucket,
        Key=object_key,
        ExtraArgs={"ContentType": "text/csv"},
    )
def download_csv(object_key: str) -> bytes:
    settings = get_settings()
    ensure_bucket_exists()
    client = get_s3_client()
    response = client.get_object(Bucket=settings.minio_bucket, Key=object_key)
    return response["Body"].read()
