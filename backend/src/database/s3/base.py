import aiobotocore
from aiobotocore.session import get_session
import aiofiles
from pathlib import Path
from typing import Optional, BinaryIO, Dict, Any, List
from uuid import uuid4
import mimetypes
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

s3_config = {
    'endpoint_url': os.getenv('S3_URL'),
    'aws_access_key_id': os.getenv('AWS_ACCESS_KEY'),
    'aws_secret_access_key': os.getenv('AWS_SECRET_KEY'),
    'region_name': 'us-east-1',
}


class S3Service:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.session = get_session()
        self.endpoint_url = s3_config['endpoint_url']

    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client('s3', **s3_config) as client:
            yield client

    async def create_bucket_if_not_exists(self) -> bool:
        """Создание bucket если он не существует"""
        try:
            async with self.get_client() as client:
                try:
                    await client.head_bucket(Bucket=self.bucket_name)
                    logger.info(f"Bucket already exists: {self.bucket_name}")
                    return True
                except client.exceptions.ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == '404' or error_code == 'NoSuchBucket':
                        await client.create_bucket(Bucket=self.bucket_name)
                        logger.info(f"Bucket created: {self.bucket_name}")
                        return True
                    else:
                        logger.error(f"Error checking bucket {self.bucket_name}: {str(e)}")
                        return False
        except Exception as e:
            logger.error(f"Error creating bucket {self.bucket_name}: {str(e)}")
            return False

    async def upload_fileobj(
            self,
            file_obj: BinaryIO,
            s3_key: str,
            content_type: Optional[str] = None,
            metadata: Optional[Dict[str, str]] = None,
            public: bool = False
    ) -> str:
        """Загрузка файлового объекта в S3"""
        if not content_type:
            content_type = 'application/octet-stream'

        content = file_obj.read()

        async with self.get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
                Metadata=metadata or {},
                ACL='public-read' if public else 'private'
            )

        logger.info(f"File object uploaded to S3: {s3_key}")
        return s3_key

    async def delete_file(self, s3_key: str) -> bool:
        """Удаление файла из S3"""
        try:
            async with self.get_client() as client:
                await client.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
            logger.info(f"File deleted from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file from S3: {s3_key}, error: {str(e)}")
            return False

    async def generate_presigned_url(
            self,
            s3_key: str,
            expires_in: int = 3600,
            response_content_disposition: Optional[str] = None,
            response_content_type: Optional[str] = None
    ) -> str:
        """Генерация предварительно подписанного URL для доступа к файлу"""
        params = {
            'Bucket': self.bucket_name,
            'Key': s3_key
        }

        if response_content_disposition:
            params['ResponseContentDisposition'] = response_content_disposition

        if response_content_type:
            params['ResponseContentType'] = response_content_type

        async with self.get_client() as client:
            url = await client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )

        return url

    async def get_file_url(self, s3_key: str, use_presigned: bool = False) -> str:
        """Получение URL файла"""
        if use_presigned:
            return await self.generate_presigned_url(s3_key)
        return f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"


async def create_s3_buckets():
    """Создание необходимых bucket'ов при запуске приложения"""
    buckets_to_create = [
        os.getenv('S3_AVATARS_BUCKET', 'avatars'),
        os.getenv('S3_PROJECT_FILES_BUCKET', 'project-files'),
        os.getenv('S3_MEDIA_BUCKET', "media-bucket"),
        os.getenv('S3_ANNOUNCEMENT_BUCKET', 'announcement-bucket')
    ]

    logger.info("Creating S3 buckets...")

    created_buckets = []
    for bucket_name in buckets_to_create:
        if bucket_name:
            s3_service = S3Service(bucket_name)
            success = await s3_service.create_bucket_if_not_exists()
            if success:
                created_buckets.append(bucket_name)
                logger.info(f"Successfully ensured bucket exists: {bucket_name}")
            else:
                logger.error(f"Failed to create bucket: {bucket_name}")

    logger.info(f"Bucket creation completed. Created/verified: {created_buckets}")
    return created_buckets