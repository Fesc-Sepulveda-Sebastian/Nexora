import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class CollaborationStatus(str, Enum):
    ACUERDO_PENDIENTE = "Acuerdo_Pendiente"
    EN_EJECUCION = "En_Ejecucion"
    EN_REVISION = "En_Revision"
    CERRADA = "Cerrada"
    DISPUTA = "Disputa"

class DisputeStatus(str, Enum):
    ABIERTA = "Abierta"
    EN_REVISION = "En_Revision"
    CERRADA_RESUELTA = "Cerrada_Resuelta"
    CERRADA_DESESTIMADA = "Cerrada_Desestimada"

class CollaborationAgreement(Base):
    __tablename__ = "collaboration_agreements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id"), unique=True, nullable=False)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    brand_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    creator_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Optimistic Concurrency & Agreement Versioning (RF-13)
    version_id = Column(Integer, default=1, nullable=False)
    scope_description = Column(Text, nullable=False)
    deliverables_terms = Column(Text, nullable=False)  # JSON specifications
    compensation_amount = Column(Float, nullable=False)
    deadline = Column(DateTime, nullable=False)

    brand_accepted = Column(Boolean, default=False)
    brand_accepted_at = Column(DateTime, nullable=True)
    creator_accepted = Column(Boolean, default=False)
    creator_accepted_at = Column(DateTime, nullable=True)

    status = Column(String(50), default=CollaborationStatus.ACUERDO_PENDIENTE, nullable=False)
    
    # Placeholder for future Stripe Connect transfer contract (RN-06 / RF-22)
    stripe_transfer_intent_id = Column(String(255), nullable=True)
    stripe_account_destination = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="agreement")
    campaign = relationship("Campaign", back_populates="agreements")
    disputes = relationship("Dispute", back_populates="collaboration", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="collaboration", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="collaboration", cascade="all, delete-orphan")


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collaboration_id = Column(String(36), ForeignKey("collaboration_agreements.id"), nullable=False)
    opened_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    reason = Column(Text, nullable=False)
    evidence_urls = Column(Text, nullable=True)  # JSON list of links/files
    
    status = Column(String(50), default=DisputeStatus.ABIERTA, nullable=False)
    admin_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Audit trail for dispute resolution (RF-18)
    previous_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    collaboration = relationship("CollaborationAgreement", back_populates="disputes")
