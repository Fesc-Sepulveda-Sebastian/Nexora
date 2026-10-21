from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.application import ApplicationStatus, DeliverableStatus

class ApplicationCreate(BaseModel):
    creative_proposal: str = Field(..., min_length=15, description="Propuesta creativa y enfoque del creador")
    # The client can pass current media kit version to freeze snapshot
    media_kit_snapshot_version: Optional[int] = 1

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    review_notes: Optional[str] = None

class DeliverableEvidenceCreate(BaseModel):
    deliverable_name: str = Field(..., min_length=2)
    file_url: str = Field(..., description="URL firmada de S3/MinIO del archivo subido")
    file_hash_sha256: str = Field(..., min_length=64, max_length=64, description="Hash SHA-256 para verificación de integridad")
    file_size_mb: float = Field(..., ge=0.01, le=10.0, description="Tamaño de archivo permitido entre 0.01 MB y 10 MB")
    external_live_url: Optional[str] = Field(None, description="Enlace a la publicación pública en red social")

class DeliverableEvidenceOut(BaseModel):
    id: str
    application_id: str
    deliverable_name: str
    file_url: str
    file_hash_sha256: str
    file_size_mb: float
    external_live_url: Optional[str] = None
    status: DeliverableStatus
    review_notes: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ApplicationOut(BaseModel):
    id: str
    campaign_id: str
    creator_id: str
    creative_proposal: str
    media_kit_snapshot_version: int
    media_kit_data: Optional[str] = None
    status: ApplicationStatus
    idempotency_key: Optional[str] = None
    evidences: List[DeliverableEvidenceOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
