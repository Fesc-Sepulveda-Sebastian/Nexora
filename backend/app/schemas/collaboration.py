from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from app.models.collaboration import CollaborationStatus, DisputeStatus

class CollaborationAgreementCreate(BaseModel):
    application_id: str
    scope_description: str = Field(..., min_length=10)
    deliverables_terms: List[Dict[str, Any]] = Field(..., description="Lista de condiciones de entregables")
    compensation_amount: float = Field(..., ge=0)
    deadline: datetime

class CollaborationAgreementUpdate(BaseModel):
    # Any update to terms increments version_id and resets acceptances (RF-13)
    scope_description: Optional[str] = None
    deliverables_terms: Optional[List[Dict[str, Any]]] = None
    compensation_amount: Optional[float] = None
    deadline: Optional[datetime] = None

class CollaborationAgreementAccept(BaseModel):
    accepted_version_id: int = Field(..., description="Versión exacta del acuerdo que el usuario está aceptando en línea")

class CollaborationAgreementOut(BaseModel):
    id: str
    application_id: str
    campaign_id: str
    brand_id: str
    creator_id: str
    version_id: int
    scope_description: str
    deliverables_terms: str
    compensation_amount: float
    deadline: datetime
    brand_accepted: bool
    brand_accepted_at: Optional[datetime] = None
    creator_accepted: bool
    creator_accepted_at: Optional[datetime] = None
    status: CollaborationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DisputeCreate(BaseModel):
    reason: str = Field(..., min_length=15, description="Motivo detallado del reclamo o controversia")
    evidence_urls: Optional[List[str]] = Field(default_factory=list)

class DisputeResolve(BaseModel):
    resolution_status: DisputeStatus = Field(..., description="Cerrada_Resuelta o Cerrada_Desestimada")
    resolution_notes: str = Field(..., min_length=10, description="Justificación administrativa formal")
    new_collaboration_status: CollaborationStatus = Field(default=CollaborationStatus.CERRADA)

class DisputeOut(BaseModel):
    id: str
    collaboration_id: str
    opened_by_id: str
    reason: str
    evidence_urls: Optional[str] = None
    status: DisputeStatus
    admin_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# RN-04: Estimated ROI Calculation Schema
class ROICalculatorInput(BaseModel):
    total_cost: float = Field(..., description="Costo total declarado por la marca (debe ser > 0)")
    attributable_benefit: float = Field(..., description="Ingreso o beneficio económico atribuible a la campaña")
    currency: str = Field(default="COP", description="Moneda declarada (ej. COP, USD)")
    cost_source: str = Field(default="Presupuesto acordado en Nexora", description="Fuente del costo")
    benefit_source: str = Field(default="Ventas atribuidas con código promocional", description="Fuente del beneficio")

class ROICalculatorOutput(BaseModel):
    roi_percentage: float = Field(..., description="((beneficio_atribuible - costo) / costo) * 100")
    total_cost: float
    attributable_benefit: float
    net_profit: float
    currency: str
    cost_source: str
    benefit_source: str
    calculated_at_utc: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default="Estimación basada exclusivamente en datos declarados por la marca (RN-04). No constituye una garantía financiera auditada.",
        description="Rótulo legal obligatorio de Estimación"
    )
