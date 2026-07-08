import boto3
from mypy_boto3_s3 import S3Client

from backend.core.app_config import settings


def create_s3_client() -> S3Client:
    session_kwargs = {
        "region_name": settings.AWS_REGION
    }

    if settings.AWS_PROFILE:
        session_kwargs["profile_name"] = settings.AWS_PROFILE

    session = boto3.Session(**session_kwargs)

    return session.client("s3")

s3_client = create_s3_client()



