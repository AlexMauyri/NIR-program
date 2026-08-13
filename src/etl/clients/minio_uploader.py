import boto3
from botocore.client import Config
from configs import MinioConfig
from utils import _get_logger

class MinioUploader:
    def __init__(self, config: MinioConfig):
        self.config = config
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            config=Config(signature_version="s3v4"),
        )

    def upload(self, local_path: str, object_name: str) -> None:
        logger = _get_logger()
        logger.info(f"[MinIO] Upload {local_path} -> s3://{self.config.bucket}/{object_name}")
        self._client.upload_file(local_path, self.config.bucket, object_name)
        logger.info("[MinIO] Upload completed")
