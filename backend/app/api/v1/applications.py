import json
import uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.application import Application, ApplicationStatus, DeliverableEvidence, DeliverableStatus
from app.models.collaboration import CollaborationAgreement, CollaborationStatus
from app.models.audit import IdempotencyRecord
from app.models.user import User, UserRole
from app.schemas.application import (
    ApplicationCreate, ApplicationStatusUpdate, ApplicationOut,
    DeliverableEvidenceCreate, DeliverableEvidenceOut
)
from app.schemas.common import APIResponse
from app.core.audit_middleware import record_audit_log
from app.api.deps import get_current_user, require_role, get_correlation_id

router = APIRouter(tags=["Postulaciones y Entregables"])

@router.post("/campaigns/{campaign_id}/apply", response_model=APIResponse[ApplicationOut], status_code=status.HTTP_201_CREATED)
def apply_to_campaign(
    campaign_id: str,
    app_in: ApplicationCreate,
    current_user: User = Depends(require_role(UserRole.CREADOR)),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RN-02 & RNF-10: Application confirmed exclusively against server.
    Uses Idempotency-Key to prevent double submissions upon reconnection.
    Freezes Media Kit version snapshot at application time (RF-10).
    """
    # 1. Idempotency Check
    if idempotency_key:
        record = db.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key == idempotency_key).first()
        if record:
            try:
                cached_data = json.loads(record.response_body)
                return APIResponse(
                    success=True,
                    message="Respuesta recuperada por Idempotency-Key",
                    data=ApplicationOut.model_validate(cached_data),
                    correlation_id=correlation_id
                )
            except Exception:
                pass

    # 2. Check campaign existence and published state
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if campaign.status != CampaignStatus.PUBLICADA.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo es posible postularse a campañas en estado 'Publicada'."
        )

    # 3. Check for existing application by this creator
    existing = db.query(Application).filter(
        Application.campaign_id == campaign_id,
        Application.creator_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has enviado una postulación previa a esta campaña."
        )

    # 4. Freeze Media Kit snapshot (RF-10)
    profile = current_user.profile
    frozen_mediakit = {
        "creator_id": current_user.id,
        "display_name": profile.display_name if profile else current_user.email,
        "location": profile.location_declared if profile else "Colombia",
        "niche": profile.niche if profile else "General",
        "rating": profile.average_rating if profile else 5.0,
        "media_kit_version": profile.current_media_kit_version if profile else 1,
        "frozen_at_utc": datetime.utcnow().isoformat()
    }

    application = Application(
        campaign_id=campaign_id,
        creator_id=current_user.id,
        creative_proposal=app_in.creative_proposal,
        media_kit_snapshot_version=profile.current_media_kit_version if profile else 1,
        media_kit_data=json.dumps(frozen_mediakit),
        status=ApplicationStatus.RECIBIDA,
        idempotency_key=idempotency_key
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # 5. Record Idempotency cache
    app_out = ApplicationOut.model_validate(application)
    if idempotency_key:
        idem = IdempotencyRecord(
            idempotency_key=idempotency_key,
            actor_id=current_user.id,
            endpoint=f"/campaigns/{campaign_id}/apply",
            request_hash=str(hash(app_in.creative_proposal)),
            response_code=201,
            response_body=json.dumps(app_out.model_dump(), default=str)
        )
        db.add(idem)
        db.commit()

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="application",
        entidad_id=application.id,
        operacion="SUBMIT_APPLICATION",
        estado_anterior=None,
        estado_nuevo=ApplicationStatus.RECIBIDA.value,
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Postulación enviada exitosamente a la marca",
        data=app_out,
        correlation_id=correlation_id
    )

@router.get("/campaigns/{campaign_id}/applications", response_model=APIResponse[List[ApplicationOut]])
def get_campaign_applications(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    if campaign.brand_id != current_user.id and current_user.role != UserRole.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="No autorizado para ver postulantes de esta campaña")

    apps = db.query(Application).filter(Application.campaign_id == campaign_id).all()
    return APIResponse(
        success=True,
        data=[ApplicationOut.model_validate(a) for a in apps]
    )

@router.patch("/applications/{application_id}/status", response_model=APIResponse[ApplicationOut])
def update_application_status(
    application_id: str,
    status_update: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RF-11: State machine for applications: Recibida -> En_Revision -> Aceptada | Rechazada.
    When Aceptada, initiates CollaborationAgreement.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")

    campaign = app.campaign
    if campaign.brand_id != current_user.id and current_user.role != UserRole.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="No autorizado para modificar esta postulación")

    previous_state = app.status
    new_state = status_update.status

    # State machine transition rules
    allowed = {
        ApplicationStatus.RECIBIDA: [ApplicationStatus.EN_REVISION, ApplicationStatus.ACEPTADA, ApplicationStatus.RECHAZADA],
        ApplicationStatus.EN_REVISION: [ApplicationStatus.ACEPTADA, ApplicationStatus.RECHAZADA],
        ApplicationStatus.ACEPTADA: [],
        ApplicationStatus.RECHAZADA: []
    }

    if new_state not in allowed.get(previous_state, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transición de estado no permitida de '{previous_state}' a '{new_state}'"
        )

    app.status = new_state
    app.updated_at = datetime.utcnow()

    # If accepted, automatically initiate Collaboration Agreement
    if new_state == ApplicationStatus.ACEPTADA and not app.agreement:
        agreement = CollaborationAgreement(
            application_id=app.id,
            campaign_id=campaign.id,
            brand_id=campaign.brand_id,
            creator_id=app.creator_id,
            version_id=1,
            scope_description=f"Colaboración para campaña: {campaign.title}",
            deliverables_terms=campaign.deliverables or "[]",
            compensation_amount=campaign.budget or 0.0,
            deadline=campaign.end_date or (datetime.utcnow() + datetime.timedelta(days=14)),
            brand_accepted=False,
            creator_accepted=False,
            status=CollaborationStatus.ACUERDO_PENDIENTE
        )
        db.add(agreement)

    db.commit()
    db.refresh(app)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="application",
        entidad_id=app.id,
        operacion="UPDATE_APPLICATION_STATUS",
        estado_anterior=previous_state,
        estado_nuevo=new_state.value,
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message=f"Estado de postulación actualizado a '{new_state.value}'",
        data=ApplicationOut.model_validate(app),
        correlation_id=correlation_id
    )

@router.post("/applications/{application_id}/evidences", response_model=APIResponse[DeliverableEvidenceOut])
def submit_deliverable_evidence(
    application_id: str,
    evidence_in: DeliverableEvidenceCreate,
    current_user: User = Depends(require_role(UserRole.CREADOR)),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RF-14: Uploads evidence for deliverable, recording SHA-256 hash and setting status to En_Revision.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")

    if app.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para subir evidencias en esta postulación")

    evidence = DeliverableEvidence(
        application_id=application_id,
        deliverable_name=evidence_in.deliverable_name,
        file_url=evidence_in.file_url,
        file_hash_sha256=evidence_in.file_hash_sha256,
        file_size_mb=evidence_in.file_size_mb,
        external_live_url=evidence_in.external_live_url,
        status=DeliverableStatus.EN_REVISION,
        submitted_at=datetime.utcnow()
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="deliverable_evidence",
        entidad_id=evidence.id,
        operacion="SUBMIT_EVIDENCE",
        estado_anterior=None,
        estado_nuevo=DeliverableStatus.EN_REVISION.value,
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Evidencia de entregable cargada exitosamente. Notificada a la marca para revisión.",
        data=DeliverableEvidenceOut.model_validate(evidence),
        correlation_id=correlation_id
    )
