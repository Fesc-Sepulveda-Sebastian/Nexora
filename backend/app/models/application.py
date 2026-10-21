import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base

class ApplicationStatus(str, Enum):
    RECIBIDA = "Recibida"
    EN_REVISION = "En_Revision"
    ACEPTADA = "Aceptada"
    RECHAZADA = "Rechazada"

class DeliverableStatus(str, Enum):
    PENDIENTE = "Pendiente"
    EN_REVISION = "En_Revision"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"

class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    creator_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    creative_proposal = Column(Text, nullable=False)
    # Frozen Media Kit reference & snapshot at application time (RF-10)
    media_kit_snapshot_version = Column(Integer, default=1, nullable=False)
    media_kit_data = Column(Text, nullable=False)  # JSON snapshot: followers, engagement, niche, samples
    
    status = Column(String(50), default=ApplicationStatus.RECIBIDA, nullable=False)
    idempotency_key = Column(String(100), unique=True, nullable=True)  # RN-02, RNF-10
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="applications")
    creator = relationship("User", back_populates="applications")
    evidences = relationship("DeliverableEvidence", back_populates="application", cascade="all, delete-orphan")
    agreement = relationship("CollaborationAgreement", back_populates="application", uselist=False, cascade="all, delete-orphan")


class DeliverableEvidence(Base):
    __tablename__ = "deliverable_evidences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False)
    
    deliverable_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False)  # SHA-256 integrity verification
    file_size_mb = Column(Float, nullable=False)
    external_live_url = Column(String(500), nullable=True)  # link to published Instagram/TikTok/YT post
    
    status = Column(String(50), default=DeliverableStatus.EN_REVISION, nullable=False)
    review_notes = Column(Text, nullable=True)
    
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    application = relationship("Application", back_populates="evidences")
