import json

from minio import Minio

from app.core.config import settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
    return _client


def ensure_bucket() -> None:
    client = get_minio_client()
    bucket = settings.MINIO_BUCKET
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }
        ],
    }
    client.set_bucket_policy(bucket, json.dumps(policy))


def upload_file(data: bytes, filename: str, content_type: str) -> str:
    import io

    client = get_minio_client()
    client.put_object(
        settings.MINIO_BUCKET,
        filename,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    endpoint = settings.MINIO_ENDPOINT
    return f"http://{endpoint}/{settings.MINIO_BUCKET}/{filename}"
