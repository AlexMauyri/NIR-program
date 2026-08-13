from prefect import task, get_run_logger
from datetime import date
from configs import MinioConfig
from clients import MinioUploader


@task(name="upload_minio")
def upload_to_minio(
    local_path: str,
    minio_config: MinioConfig,
    start_date: date,
    end_date: date,
) -> None:
    logger = get_run_logger()
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    logger.info(">>> UPLOAD to MinIO: %s", local_path)
    uploader = MinioUploader(minio_config)

    versioned = f"historical/features_{start_str}_{end_str}.parquet"
    uploader.upload(local_path, versioned)
    logger.info("Uploaded: s3://%s/%s", minio_config.bucket, versioned)

    uploader.upload(local_path, "latest/features.parquet")
    logger.info("Uploaded: s3://%s/latest/features.parquet", minio_config.bucket)
    logger.info("<<< UPLOAD to MinIO: done")
