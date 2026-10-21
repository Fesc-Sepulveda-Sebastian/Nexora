import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    correlation_id = Column(String(64), index=True, nullable=False)
    actor_id = Column(String(36), index=True, nullable=True)
    rol = Column(String(50), nullable=True)
    timestamp_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    entidad = Column(String(100), nullable=False)  # campaign, application, agreement, etc.
    entidad_id = Column(String(36), nullable=False)
    operacion = Column(String(100), nullable=False)  # CREATE, UPDATE_STATE, SUBMIT_EVIDENCE, etc.
    
    estado_anterior = Column(String(100), nullable=True)
    estado_nuevo = Column(String(100), nullable=True)
    resultado = Column(String(50), nullable=False)  # SUCCESS, FAILED, CONFLICT
    
    # Non-sensitive contextual metadata
    metadata_json = Column(Text, nullable=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    idempotency_key = Column(String(128), primary_key=True)
    actor_id = Column(String(36), nullable=True)
    endpoint = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_code = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
