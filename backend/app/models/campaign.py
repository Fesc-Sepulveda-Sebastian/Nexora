import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base

class CampaignStatus(str, Enum):
    BORRADOR = "Borrador"
    PUBLICADA = "Publicada"
    EN_EJECUCION = "En_Ejecucion"
    CERRADA = "Cerrada"
    CANCELADA = "Cancelada"

class CompensationType(str, Enum):
    PAGO_FIJO = "pago_fijo"
    CANJE = "canje"
    HIBRIDO = "hibrido"
    COMISION = "comision"

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Core Campaign Info
    title = Column(String(255), nullable=True)
    objective = Column(Text, nullable=True)
    niche = Column(String(100), nullable=True)  # Gastronomía, Moda, etc.
    status = Column(String(50), default=CampaignStatus.BORRADOR, nullable=False)
    version_id = Column(Integer, default=1, nullable=False)  # For optimistic concurrency & offline sync
    
    # Dates
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Compensation / Budget
    compensation_type = Column(String(50), default=CompensationType.PAGO_FIJO)
    budget = Column(Float, default=0.0)
    compensation_notes = Column(Text, nullable=True)
    
    # JSON-encoded structures for Deliverables & Selection Criteria
    deliverables = Column(Text, nullable=True)  # e.g., [{"format": "Reel", "qty": 1, "specs": "30s destacando receta"}]
    selection_criteria = Column(Text, nullable=True)  # e.g., {"min_followers": 2000, "location": "Cúcuta", "platforms": ["Instagram"]}
    
    # ROI Attribution metrics (RN-04)
    total_cost = Column(Float, default=0.0)
    attributable_benefit = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    brand = relationship("User", back_populates="campaigns")
    applications = relationship("Application", back_populates="campaign", cascade="all, delete-orphan")
    agreements = relationship("CollaborationAgreement", back_populates="campaign", cascade="all, delete-orphan")
