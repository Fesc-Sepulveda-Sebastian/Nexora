import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collaboration_id = Column(String(36), ForeignKey("collaboration_agreements.id"), nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    score = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=True)
    is_moderated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Ensure each user can only rate once per collaboration (RN-05)
    __table_args__ = (
        UniqueConstraint('collaboration_id', 'reviewer_id', name='uq_collaboration_reviewer'),
    )

    collaboration = relationship("CollaborationAgreement", back_populates="ratings")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewee = relationship("User", foreign_keys=[reviewee_id])
