from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from app.models.campaign import CampaignStatus, CompensationType

class DeliverableItem(BaseModel):
    format: str = Field(..., description="Reel, TikTok, Story, Post, YouTube Video")
    qty: int = Field(..., ge=1, description="Cantidad requerida")
    specs: str = Field(..., description="Especificaciones detalladas del contenido")

class SelectionCriteria(BaseModel):
    min_followers: int = Field(default=1000, ge=0)
    location: Optional[str] = None
    platforms: List[str] = Field(default_factory=lambda: ["Instagram"])

class CampaignBase(BaseModel):
    title: Optional[str] = None
    objective: Optional[str] = None
    niche: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    compensation_type: CompensationType = CompensationType.PAGO_FIJO
    budget: float = 0.0
    compensation_notes: Optional[str] = None
    deliverables: Optional[List[DeliverableItem]] = None
    selection_criteria: Optional[SelectionCriteria] = None
    total_cost: Optional[float] = 0.0
    attributable_benefit: Optional[float] = 0.0

class CampaignCreate(CampaignBase):
    title: str = Field(..., min_length=3)

class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    objective: Optional[str] = None
    niche: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    compensation_type: Optional[CompensationType] = None
    budget: Optional[float] = None
    compensation_notes: Optional[str] = None
    deliverables: Optional[List[DeliverableItem]] = None
    selection_criteria: Optional[SelectionCriteria] = None
    total_cost: Optional[float] = None
    attributable_benefit: Optional[float] = None
    # Required for optimistic locking (RNF-14 / RF-31)
    version_id: int = Field(..., description="Versión esperada del registro para evitar sobrescrituras offline")

class CampaignOut(CampaignBase):
    id: str
    brand_id: str
    status: CampaignStatus
    version_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

def validate_campaign_for_publishing(campaign) -> List[str]:
    """
    RN-01: Validates mandatory fields before publishing a campaign.
    Returns list of error messages if invalid.
    """
    errors = []
    if not campaign.title or len(campaign.title.strip()) < 3:
        errors.append("Título de campaña obligatorio (mínimo 3 caracteres).")
    if not campaign.objective or len(campaign.objective.strip()) < 10:
        errors.append("Objetivo de campaña obligatorio (mínimo 10 caracteres).")
    if not campaign.niche or len(campaign.niche.strip()) == 0:
        errors.append("Nicho/categoría obligatorio.")
    if not campaign.start_date or not campaign.end_date:
        errors.append("Fechas de vigencia de inicio y fin obligatorias.")
    elif campaign.end_date <= campaign.start_date:
        errors.append("La fecha de fin debe ser posterior a la fecha de inicio.")
    
    # Deliverables validation
    if not campaign.deliverables:
        errors.append("Debe definir al menos un entregable con formato y especificaciones.")
    
    # Compensation validation
    if campaign.compensation_type != CompensationType.CANJE and (not campaign.budget or campaign.budget <= 0):
        errors.append("Debe especificar un presupuesto mayor a 0 para campañas pagadas.")
    elif campaign.compensation_type == CompensationType.CANJE and (not campaign.compensation_notes or len(campaign.compensation_notes.strip()) < 5):
        errors.append("Debe detallar el producto/servicio ofrecido en canje.")
    
    # Selection criteria
    if not campaign.selection_criteria:
        errors.append("Criterios de selección obligatorios.")

    return errors
