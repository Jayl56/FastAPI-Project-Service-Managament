import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from backend.core.app_config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_s3() -> None:
    if not settings.s3_bucket_enabled:
        logger.warning("S3 bucket name or aws_region not provided.")
        return
    try:
        logger.info(
            "Checking access to S3 bucket '%s'...",
            settings.S3_BUCKET_NAME
        )
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE)
            s3=session.client("s3")

        else:
            s3=boto3.client("s3",region_name=settings.AWS_REGION)

        s3.head_bucket(
            Bucket=settings.S3_BUCKET_NAME
        )

        logger.info(
            "Successfully connected to S3 bucket '%s'",
            settings.S3_BUCKET_NAME
        )

    except NoCredentialsError:
        logger.exception(
            "AWS credentials not found."
        )
        raise

    except ClientError:
        logger.exception(
            "Unable to access S3 bucket '%s'",
            settings.S3_BUCKET_NAME
        )
        raise

if __name__ == "__main__":
    init_s3()