import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, unquote, urlparse

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EVIDENCE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/quicktime",
    "application/pdf",
}

MAX_EVIDENCE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class StorageService:
    def __init__(self):
        self.internal_endpoint = settings.MINIO_INTERNAL_ENDPOINT or settings.MINIO_ENDPOINT
        self.public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
        self.bucket = settings.MINIO_BUCKET
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.scheme = "https" if settings.MINIO_SECURE else "http"

    @property
    def local_root(self) -> Path:
        root = Path(settings.LOCAL_STORAGE_DIR).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        base = os.path.basename(filename or "evidence.bin")
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)
        return cleaned or "evidence.bin"

    def _safe_local_path(self, file_key: str) -> Path:
        normalized = file_key.lstrip("/").replace("\\", "/")
        if not normalized.startswith("deliverables/") or ".." in normalized.split("/"):
            raise ValueError("Clave de archivo inválida.")
        target = (self.local_root / normalized).resolve()
        if self.local_root not in target.parents:
            raise ValueError("Ruta de archivo fuera del directorio permitido.")
        return target

    @staticmethod
    def validate_content_type(content_type: str) -> str:
        normalized = (content_type or "").split(";")[0].strip().lower()
        if normalized not in ALLOWED_EVIDENCE_MIME_TYPES:
            raise ValueError(
                f"Tipo MIME '{content_type}' no permitido. Permitidos: {', '.join(sorted(ALLOWED_EVIDENCE_MIME_TYPES))}"
            )
        return normalized

    def _sign_local_upload(self, file_key: str, content_type: str, expires: int) -> str:
        msg = f"{file_key}:{content_type}:{expires}".encode("utf-8")
        return hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def verify_local_upload_signature(
        self, file_key: str, content_type: str, expires: int, signature: str
    ) -> bool:
        if expires < int(time.time()):
            return False
        expected = self._sign_local_upload(file_key, content_type, expires)
        return hmac.compare_digest(expected, signature or "")

    def _s3_client(self, endpoint: str):
        import boto3
        from botocore.client import Config

        return boto3.client(
            "s3",
            endpoint_url=f"{self.scheme}://{endpoint}",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(
                signature_version="s3v4",
                connect_timeout=1,
                read_timeout=2,
                retries={"max_attempts": 1},
            ),
            region_name="us-east-1",
        )

    def _is_minio_reachable(self) -> bool:
        try:
            client = self._s3_client(self.internal_endpoint)
            client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False

    def generate_presigned_upload_url(
        self, filename: str, content_type: str = "image/jpeg", expires_in: int = 900
    ) -> Dict[str, Any]:
        """
        Issues a short-lived signed upload URL (MinIO S3 when reachable, or signed local storage PUT endpoint).
        """
        valid_mime = self.validate_content_type(content_type)
        safe_name = self._sanitize_filename(filename)
        unique_file_key = f"deliverables/{uuid.uuid4()}_{safe_name}"

        if self._is_minio_reachable():
            try:
                s3_public = self._s3_client(self.public_endpoint)
                presigned_url = s3_public.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": self.bucket,
                        "Key": unique_file_key,
                        "ContentType": valid_mime,
                    },
                    ExpiresIn=expires_in,
                )
                public_url = f"{self.scheme}://{self.public_endpoint}/{self.bucket}/{unique_file_key}"
                return {
                    "upload_url": presigned_url,
                    "file_key": unique_file_key,
                    "public_url": public_url,
                    "content_type": valid_mime,
                    "storage_backend": "minio",
                    "expires_in_seconds": expires_in,
                    "min_size_mb": 0.001,
                    "max_size_mb": 10.0,
                }
            except Exception as e:
                logger.warning(f"MinIO presign failed ({e}); falling back to signed local storage upload.")

        expires = int(time.time()) + expires_in
        sig = self._sign_local_upload(unique_file_key, valid_mime, expires)
        upload_url = (
            f"{settings.API_V1_STR}/storage/upload"
            f"?file_key={quote(unique_file_key)}&content_type={quote(valid_mime)}&expires={expires}&sig={sig}"
        )
        public_url = f"{settings.API_V1_STR}/storage/objects/{unique_file_key}"
        return {
            "upload_url": upload_url,
            "file_key": unique_file_key,
            "public_url": public_url,
            "content_type": valid_mime,
            "storage_backend": "local",
            "expires_in_seconds": expires_in,
            "min_size_mb": 0.001,
            "max_size_mb": 10.0,
        }

    def save_local_object(self, file_key: str, content_type: str, data: bytes) -> Dict[str, Any]:
        valid_mime = self.validate_content_type(content_type)
        if len(data) == 0:
            raise ValueError("El archivo está vacío (0 bytes).")
        if len(data) > MAX_EVIDENCE_SIZE_BYTES:
            raise ValueError("El archivo excede el tamaño máximo permitido de 10 MB.")

        target = self._safe_local_path(file_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

        sha256 = self.calculate_sha256(data)
        meta = {
            "file_key": file_key,
            "content_type": valid_mime,
            "size_bytes": len(data),
            "sha256": sha256,
        }
        meta_path = target.with_suffix(target.suffix + ".meta.json")
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        return meta

    def get_local_object(self, file_key: str) -> Tuple[bytes, str]:
        target = self._safe_local_path(file_key)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError("Archivo no encontrado en almacenamiento local.")
        meta_path = target.with_suffix(target.suffix + ".meta.json")
        content_type = "application/octet-stream"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                content_type = meta.get("content_type", content_type)
            except Exception:
                pass
        return target.read_bytes(), content_type

    def extract_file_key(self, file_key: Optional[str], file_url: str) -> str:
        if file_key:
            return file_key.lstrip("/")
        parsed = urlparse(file_url or "")
        path = unquote(parsed.path or "")
        if "/storage/objects/" in path:
            return path.split("/storage/objects/", 1)[1].lstrip("/")
        if f"/{self.bucket}/" in path:
            return path.split(f"/{self.bucket}/", 1)[1].lstrip("/")
        if "deliverables/" in path:
            return "deliverables/" + path.split("deliverables/", 1)[1].lstrip("/")
        raise ValueError("No se pudo determinar la clave del archivo de evidencia.")

    def verify_uploaded_object(
        self, file_key: Optional[str], file_url: str, expected_sha256: str
    ) -> Tuple[str, int, str]:
        """
        Verifies that the object exists in storage, conforms to size & MIME constraints,
        and matches the expected SHA-256 hash computed over the stored bytes.
        """
        resolved_key = self.extract_file_key(file_key, file_url)
        # Validate key structure before touching local or S3 storage
        local_target = self._safe_local_path(resolved_key)

        data: Optional[bytes] = None
        content_type: Optional[str] = None

        if local_target.exists() and local_target.is_file():
            data, content_type = self.get_local_object(resolved_key)
        elif self._is_minio_reachable():
            try:
                s3_internal = self._s3_client(self.internal_endpoint)
                obj = s3_internal.get_object(Bucket=self.bucket, Key=resolved_key)
                data = obj["Body"].read()
                content_type = obj.get("ContentType", "application/octet-stream")
            except Exception as exc:
                raise FileNotFoundError(
                    f"El archivo '{resolved_key}' no existe en el almacenamiento MinIO/S3."
                ) from exc
        else:
            raise FileNotFoundError(
                f"El archivo '{resolved_key}' no existe en el almacenamiento. Debe realizar la subida PUT antes de confirmar."
            )

        if not data or len(data) == 0:
            raise ValueError("El archivo almacenado está vacío.")
        if len(data) > MAX_EVIDENCE_SIZE_BYTES:
            raise ValueError("El archivo almacenado excede el límite máximo de 10 MB.")

        self.validate_content_type(content_type or "")

        actual_sha256 = self.calculate_sha256(data)
        if not hmac.compare_digest(actual_sha256.lower(), (expected_sha256 or "").lower()):
            raise ValueError(
                "Verificación de integridad fallida: el hash SHA-256 declarado no coincide con los bytes almacenados."
            )

        return actual_sha256, len(data), content_type or "application/octet-stream"

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify_hash(data: bytes, expected_hash: str) -> bool:
        calculated = hashlib.sha256(data).hexdigest()
        return hmac.compare_digest(calculated.lower(), expected_hash.lower())


storage_service = StorageService()
