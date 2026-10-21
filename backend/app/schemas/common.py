from typing import Generic, TypeVar, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operación exitosa"
    data: Optional[T] = None
    correlation_id: Optional[str] = None

class AuditLogOut(BaseModel):
    id: str
    correlation_id: str
    actor_id: Optional[str]
    rol: Optional[str]
    timestamp_utc: datetime
    entidad: str
    entidad_id: str
    operacion: str
    estado_anterior: Optional[str]
    estado_nuevo: Optional[str]
    resultado: str
    metadata_json: Optional[str]

    class Config:
        from_attributes = True
