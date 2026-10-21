import uuid
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every request has an X-Correlation-ID header,
    attaching it to request state and response headers for complete end-to-end tracing.
    """
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

def record_audit_log(
    db: Session,
    correlation_id: str,
    actor_id: Optional[str],
    rol: Optional[str],
    entidad: str,
    entidad_id: str,
    operacion: str,
    estado_anterior: Optional[str],
    estado_nuevo: Optional[str],
    resultado: str = "SUCCESS",
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    RNF-11 & RNF-20: Persists commercial transactions and state changes to audit_logs,
    strictly sanitizing passwords, tokens, and sensitive keys.
    """
    clean_metadata = None
    if metadata:
        # Sanitize sensitive fields
        sanitized = {k: v for k, v in metadata.items() if k not in ("password", "token", "encrypted_token", "secret", "cvv")}
        clean_metadata = json.dumps(sanitized, default=str)

    log_entry = AuditLog(
        id=str(uuid.uuid4()),
        correlation_id=correlation_id or str(uuid.uuid4()),
        actor_id=actor_id,
        rol=rol,
        timestamp_utc=datetime.utcnow(),
        entidad=entidad,
        entidad_id=str(entidad_id),
        operacion=operacion,
        estado_anterior=str(estado_anterior) if estado_anterior is not None else None,
        estado_nuevo=str(estado_nuevo) if estado_nuevo is not None else None,
        resultado=resultado,
        metadata_json=clean_metadata
    )
    
    db.add(log_entry)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record audit log: {e}")
        
    return log_entry
