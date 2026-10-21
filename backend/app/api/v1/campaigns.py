import json
import uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus, CompensationType
from app.models.user import User, UserRole
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignOut, validate_campaign_for_publishing
from app.schemas.common import APIResponse, PaginatedResponse
from app.core.audit_middleware import record_audit_log
from app.api.deps import get_current_user, require_role, get_correlation_id

router = APIRouter(prefix="/campaigns", tags=["Campañas"])

@router.post("", response_model=APIResponse[CampaignOut], status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign_in: CampaignCreate,
    current_user: User = Depends(require_role(UserRole.MARCA)),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    deliverables_json = json.dumps([d.model_dump() for d in campaign_in.deliverables]) if campaign_in.deliverables else None
    criteria_json = json.dumps(campaign_in.selection_criteria.model_dump()) if campaign_in.selection_criteria else None

    campaign = Campaign(
        brand_id=current_user.id,
        title=campaign_in.title,
        objective=campaign_in.objective,
        niche=campaign_in.niche,
        status=CampaignStatus.BORRADOR,
        version_id=1,
        start_date=campaign_in.start_date,
        end_date=campaign_in.end_date,
        compensation_type=campaign_in.compensation_type,
        budget=campaign_in.budget,
        compensation_notes=campaign_in.compensation_notes,
        deliverables=deliverables_json,
        selection_criteria=criteria_json,
        total_cost=campaign_in.total_cost or 0.0,
        attributable_benefit=campaign_in.attributable_benefit or 0.0
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="campaign",
        entidad_id=campaign.id,
        operacion="CREATE_DRAFT",
        estado_anterior=None,
        estado_nuevo=CampaignStatus.BORRADOR.value,
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Borrador de campaña creado exitosamente",
        data=_format_campaign_out(campaign),
        correlation_id=correlation_id
    )

@router.get("", response_model=APIResponse[PaginatedResponse[CampaignOut]])
def list_campaigns(
    status_filter: Optional[str] = Query(None, description="Borrador, Publicada, etc."),
    niche: Optional[str] = Query(None, description="Filtro por nicho"),
    min_budget: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    query = db.query(Campaign)
    if status_filter:
        query = query.filter(Campaign.status == status_filter)
    if niche:
        query = query.filter(Campaign.niche.ilike(f"%{niche}%"))
    if min_budget:
        query = query.filter(Campaign.budget >= min_budget)

    total = query.count()
    campaigns = query.order_by(Campaign.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    total_pages = (total + limit - 1) // limit if limit > 0 else 1

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[_format_campaign_out(c) for c in campaigns],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        ),
        correlation_id=correlation_id
    )

@router.get("/{campaign_id}", response_model=APIResponse[CampaignOut])
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return APIResponse(success=True, data=_format_campaign_out(campaign))

@router.put("/{campaign_id}", response_model=APIResponse[CampaignOut])
def update_campaign(
    campaign_id: str,
    update_in: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    if campaign.brand_id != current_user.id and current_user.role != UserRole.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta campaña")

    # Conflict Resolution (RNF-14 / RF-31 / HTTP 409):
    # Verify optimistic lock version_id
    if campaign.version_id != update_in.version_id:
        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=current_user.id,
            rol=current_user.role,
            entidad="campaign",
            entidad_id=campaign.id,
            operacion="UPDATE_CONFLICT",
            estado_anterior=f"v{campaign.version_id}",
            estado_nuevo=f"v{update_in.version_id}",
            resultado="CONFLICT"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "VERSION_CONFLICT",
                "message": "La campaña fue modificada en el servidor mientras editaba sin conexión.",
                "server_version": campaign.version_id,
                "server_data": _format_campaign_out(campaign).model_dump()
            }
        )

    # Apply updates
    if update_in.title is not None:
        campaign.title = update_in.title
    if update_in.objective is not None:
        campaign.objective = update_in.objective
    if update_in.niche is not None:
        campaign.niche = update_in.niche
    if update_in.start_date is not None:
        campaign.start_date = update_in.start_date
    if update_in.end_date is not None:
        campaign.end_date = update_in.end_date
    if update_in.compensation_type is not None:
        campaign.compensation_type = update_in.compensation_type
    if update_in.budget is not None:
        campaign.budget = update_in.budget
    if update_in.compensation_notes is not None:
        campaign.compensation_notes = update_in.compensation_notes
    if update_in.deliverables is not None:
        campaign.deliverables = json.dumps([d.model_dump() for d in update_in.deliverables])
    if update_in.selection_criteria is not None:
        campaign.selection_criteria = json.dumps(update_in.selection_criteria.model_dump())
    if update_in.total_cost is not None:
        campaign.total_cost = update_in.total_cost
    if update_in.attributable_benefit is not None:
        campaign.attributable_benefit = update_in.attributable_benefit

    # Increment version
    campaign.version_id += 1
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="campaign",
        entidad_id=campaign.id,
        operacion="UPDATE",
        estado_anterior=f"v{update_in.version_id}",
        estado_nuevo=f"v{campaign.version_id}",
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Campaña actualizada exitosamente",
        data=_format_campaign_out(campaign),
        correlation_id=correlation_id
    )

@router.post("/{campaign_id}/publish", response_model=APIResponse[CampaignOut])
def publish_campaign(
    campaign_id: str,
    current_user: User = Depends(require_role(UserRole.MARCA)),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RN-01: Validates mandatory fields before changing status from Borrador to Publicada.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    if campaign.brand_id != current_user.id and current_user.role != UserRole.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="No autorizado para publicar esta campaña")

    # Validate RN-01
    errors = validate_campaign_for_publishing(campaign)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "RN-01_VALIDATION_FAILED",
                "message": "La campaña no cumple los requisitos obligatorios para publicación (RN-01)",
                "validation_errors": errors
            }
        )

    previous_status = campaign.status
    campaign.status = CampaignStatus.PUBLICADA
    campaign.version_id += 1
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="campaign",
        entidad_id=campaign.id,
        operacion="PUBLISH",
        estado_anterior=previous_status,
        estado_nuevo=CampaignStatus.PUBLICADA.value,
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="¡Campaña publicada exitosamente en el Marketplace de Nexora!",
        data=_format_campaign_out(campaign),
        correlation_id=correlation_id
    )

def _format_campaign_out(c: Campaign) -> CampaignOut:
    delivs = []
    if c.deliverables:
        try:
            delivs = json.loads(c.deliverables)
        except Exception:
            delivs = []
            
    crit = None
    if c.selection_criteria:
        try:
            crit = json.loads(c.selection_criteria)
        except Exception:
            crit = None

    return CampaignOut(
        id=c.id,
        brand_id=c.brand_id,
        title=c.title,
        objective=c.objective,
        niche=c.niche,
        status=c.status,
        version_id=c.version_id,
        start_date=c.start_date,
        end_date=c.end_date,
        compensation_type=c.compensation_type,
        budget=c.budget,
        compensation_notes=c.compensation_notes,
        deliverables=delivs,
        selection_criteria=crit,
        total_cost=c.total_cost,
        attributable_benefit=c.attributable_benefit,
        created_at=c.created_at,
        updated_at=c.updated_at
    )
