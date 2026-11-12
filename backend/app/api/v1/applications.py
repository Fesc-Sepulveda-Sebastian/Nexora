import hashlib
import json
import uuid
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.application import Application, ApplicationStatus, DeliverableEvidence, DeliverableStatus
from app.models.collaboration import CollaborationAgreement, CollaborationAgreementVersion, CollaborationStatus
from app.models.audit import IdempotencyRecord
from app.models.user import User, UserRole
from app.schemas.application import (
    ApplicationCreate, ApplicationStatusUpdate, ApplicationOut,
    DeliverableEvidenceCreate, DeliverableEvidenceOut, DeliverableEvidenceReview
)
from app.schemas.common import APIResponse
from app.core.audit_middleware import record_audit_log
from app.services.storage_service import storage_service
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
    endpoint = f"/campaigns/{campaign_id}/apply"
    payload_hash = hashlib.sha256(
        json.dumps(app_in.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()

    # 1. Idempotency Check (isolated per actor + endpoint + payload_hash)
    if idempotency_key:
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.actor_id == current_user.id,
            IdempotencyRecord.endpoint == endpoint,
        ).first()
        if record:
            if record.request_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key ya utilizada previamente con un payload diferente."
                )
            try:
                cached_data = json.loads(record.response_body)
                return APIResponse(
                    success=True,
                    message="Respuesta recuperada por Idempotency-Key",
                    data=ApplicationOut.model_validate(cached_data),
                    correlation_id=correlation_id
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se pudo reconstruir la respuesta idempotente previa."
                ) from exc

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
    try:
        db.flush()
        db.refresh(application)

        app_out = ApplicationOut.model_validate(application)
        if idempotency_key:
            idem = IdempotencyRecord(
                idempotency_key=idempotency_key,
                actor_id=current_user.id,
                endpoint=endpoint,
                request_hash=payload_hash,
                response_code=201,
                response_body=json.dumps(app_out.model_dump(mode="json"))
            )
            db.add(idem)

        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            record = db.query(IdempotencyRecord).filter(
                IdempotencyRecord.idempotency_key == idempotency_key,
                IdempotencyRecord.actor_id == current_user.id,
                IdempotencyRecord.endpoint == endpoint,
            ).first()
            if record:
                if record.request_hash != payload_hash:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency-Key ya utilizada previamente con un payload diferente."
                    )
                cached_data = json.loads(record.response_body)
                return APIResponse(
                    success=True,
                    message="Respuesta recuperada por Idempotency-Key",
                    data=ApplicationOut.model_validate(cached_data),
                    correlation_id=correlation_id
                )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto al registrar la postulación o clave de idempotencia duplicada."
        )

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

    # If accepted, automatically initiate Collaboration Agreement and initial v1 history snapshot
    if new_state == ApplicationStatus.ACEPTADA and not app.agreement:
        deadline_dt = campaign.end_date or (datetime.utcnow() + timedelta(days=14))
        scope_desc = f"Colaboración para campaña: {campaign.title}"
        deliv_terms = campaign.deliverables or "[]"
        comp_amount = campaign.budget or 0.0

        agreement = CollaborationAgreement(
            application_id=app.id,
            campaign_id=campaign.id,
            brand_id=campaign.brand_id,
            creator_id=app.creator_id,
            version_id=1,
            scope_description=scope_desc,
            deliverables_terms=deliv_terms,
            compensation_amount=comp_amount,
            deadline=deadline_dt,
            brand_accepted=False,
            creator_accepted=False,
            status=CollaborationStatus.ACUERDO_PENDIENTE
        )
        db.add(agreement)
        db.flush()

        initial_version = CollaborationAgreementVersion(
            collaboration_id=agreement.id,
            version_id=1,
            scope_description=scope_desc,
            deliverables_terms=deliv_terms,
            compensation_amount=comp_amount,
            deadline=deadline_dt,
            edited_by_id=current_user.id,
        )
        db.add(initial_version)

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
    RF-14: Confirms uploaded evidence for deliverable after verifying the object exists in storage,
    matches MIME/size policies, and passes server-side SHA-256 integrity verification.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")

    if app.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para subir evidencias en esta postulación")

    app_status = app.status.value if hasattr(app.status, "value") else app.status
    if app_status != ApplicationStatus.ACEPTADA.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden subir evidencias para postulaciones aceptadas."
        )

    if app.agreement:
        agreement_status = app.agreement.status.value if hasattr(app.agreement.status, "value") else app.agreement.status
        if agreement_status not in (
            CollaborationStatus.EN_EJECUCION.value,
            CollaborationStatus.EN_REVISION.value,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El acuerdo debe estar en ejecución para cargar evidencias. Estado actual: {agreement_status}"
            )

    try:
        verified_sha256, actual_size_bytes, _ = storage_service.verify_uploaded_object(
            file_key=evidence_in.file_key,
            file_url=evidence_in.file_url,
            expected_sha256=evidence_in.file_hash_sha256,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    verified_size_mb = max(round(actual_size_bytes / (1024 * 1024), 4), 0.0001)
    now = datetime.utcnow()

    try:
        evidence = DeliverableEvidence(
            application_id=application_id,
            deliverable_name=evidence_in.deliverable_name,
            file_url=evidence_in.file_url,
            file_hash_sha256=verified_sha256,
            file_size_mb=verified_size_mb,
            external_live_url=evidence_in.external_live_url,
            status=DeliverableStatus.EN_REVISION.value,
            submitted_at=now
        )
        db.add(evidence)
        db.flush()

        if app.agreement:
            agreement_status = app.agreement.status.value if hasattr(app.agreement.status, "value") else app.agreement.status
            if agreement_status == CollaborationStatus.EN_EJECUCION.value:
                app.agreement.status = CollaborationStatus.EN_REVISION.value
                app.agreement.updated_at = now

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
            resultado="SUCCESS",
            commit=False
        )

        db.commit()
        db.refresh(evidence)
    except Exception:
        db.rollback()
        raise

    return APIResponse(
        success=True,
        message="Evidencia de entregable cargada y verificada por SHA-256 en almacenamiento. Estado: En Revisión.",
        data=DeliverableEvidenceOut.model_validate(evidence),
        correlation_id=correlation_id
    )


@router.patch("/evidences/{evidence_id}/review", response_model=APIResponse[DeliverableEvidenceOut])
def review_deliverable_evidence(
    evidence_id: str,
    review_in: DeliverableEvidenceReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    evidence = db.query(DeliverableEvidence).filter(DeliverableEvidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")

    app = evidence.application
    campaign = app.campaign
    if campaign.brand_id != current_user.id and current_user.role != UserRole.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="No autorizado para revisar esta evidencia")

    if review_in.status not in (DeliverableStatus.APROBADO, DeliverableStatus.RECHAZADO):
        raise HTTPException(status_code=400, detail="La revisión solo admite estado Aprobado o Rechazado")

    previous_status = evidence.status.value if hasattr(evidence.status, "value") else evidence.status
    now = datetime.utcnow()

    try:
        evidence.status = review_in.status.value
        evidence.review_notes = review_in.review_notes
        evidence.reviewed_at = now

        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=current_user.id,
            rol=current_user.role,
            entidad="deliverable_evidence",
            entidad_id=evidence.id,
            operacion="REVIEW_EVIDENCE",
            estado_anterior=previous_status,
            estado_nuevo=review_in.status.value,
            resultado="SUCCESS",
            commit=False
        )
        db.commit()
        db.refresh(evidence)
    except Exception:
        db.rollback()
        raise

    return APIResponse(
        success=True,
        message=f"Evidencia marcada como '{review_in.status.value}'.",
        data=DeliverableEvidenceOut.model_validate(evidence),
        correlation_id=correlation_id
    )
