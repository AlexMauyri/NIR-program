import os
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from configs import MinioConfig
from utils import _get_logger

class MinioClient:
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

    def download(self, object_name: str, local_path: str) -> None:
        logger = _get_logger()
        logger.info("[MinIO] Download s3://%s/%s -> %s", self.config.bucket, object_name, local_path)
        self._client.download_file(self.config.bucket, object_name, local_path)
        logger.info("[MinIO] Download completed")

    def download_to_memory(self, object_name: str) -> bytes:
        logger = _get_logger()
        logger.info("[MinIO] Download s3://%s/%s to memory", self.config.bucket, object_name)
        response = self._client.get_object(Bucket=self.config.bucket, Key=object_name)
        data = response["Body"].read()
        logger.info("[MinIO] Downloaded %d bytes", len(data))
        return data

    def exists(self, object_name: str) -> bool:
        try:
            self._client.head_object(Bucket=self.config.bucket, Key=object_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def list_objects(self, prefix: str = "") -> list[str]:
        response = self._client.list_objects_v2(
            Bucket=self.config.bucket,
            Prefix=prefix,
        )
        return [obj["Key"] for obj in response.get("Contents", [])]
