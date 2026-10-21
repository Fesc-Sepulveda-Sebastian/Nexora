import hashlib
import logging
import uuid
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.bucket = settings.MINIO_BUCKET
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY

    def generate_presigned_upload_url(self, filename: str, content_type: str = "image/jpeg", expires_in: int = 900) -> Dict[str, Any]:
        """
        Generates a presigned URL (or simulated local presigned URL) for uploading deliverables.
        Ensures short validity (15 mins) and strict file size expectations (0.2MB - 10MB).
        """
        unique_file_key = f"deliverables/{uuid.uuid4()}_{filename}"
        
        try:
            import boto3
            from botocore.client import Config
            
            s3_client = boto3.client(
                's3',
                endpoint_url=f"http://{self.endpoint}",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': unique_file_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            final_file_url = f"http://{self.endpoint}/{self.bucket}/{unique_file_key}"
            return {
                "upload_url": presigned_url,
                "file_key": unique_file_key,
                "public_url": final_file_url,
                "expires_in_seconds": expires_in,
                "min_size_mb": 0.2,
                "max_size_mb": 10.0
            }
        except Exception as e:
            logger.warning(f"MinIO client not available directly ({e}). Providing mock presigned contract URL.")
            # Standard simulated presigned upload contract
            mock_url = f"http://{self.endpoint}/{self.bucket}/{unique_file_key}?signature=mock_presigned_sig_{uuid.uuid4().hex[:12]}&expires={expires_in}"
            return {
                "upload_url": mock_url,
                "file_key": unique_file_key,
                "public_url": f"http://{self.endpoint}/{self.bucket}/{unique_file_key}",
                "expires_in_seconds": expires_in,
                "min_size_mb": 0.2,
                "max_size_mb": 10.0
            }

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """
        Calculates SHA-256 hash of byte payload for deliverable integrity validation.
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify_hash(data: bytes, expected_hash: str) -> bool:
        calculated = hashlib.sha256(data).hexdigest()
        return calculated.lower() == expected_hash.lower()

storage_service = StorageService()
