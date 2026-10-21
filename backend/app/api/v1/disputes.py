import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.collaboration import CollaborationAgreement, CollaborationStatus, Dispute, DisputeStatus
from app.models.user import User, UserRole
from app.schemas.collaboration import DisputeCreate, DisputeResolve, DisputeOut
from app.schemas.common import APIResponse
from app.core.audit_middleware import record_audit_log
from app.api.deps import get_current_user, require_role, get_correlation_id

router = APIRouter(prefix="/disputes", tags=["Panel de Disputas y Moderación"])

@router.post("/collaborations/{collaboration_id}", response_model=APIResponse[DisputeOut], status_code=status.HTTP_201_CREATED)
def open_dispute(
    collaboration_id: str,
    dispute_in: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    collab = db.query(CollaborationAgreement).filter(CollaborationAgreement.id == collaboration_id).first()
    if not collab:
        raise HTTPException(status_code=404, detail="Colaboración no encontrada")

    if current_user.id != collab.brand_id and current_user.id != collab.creator_id:
        raise HTTPException(status_code=403, detail="No autorizado para abrir disputa en esta colaboración")

    previous_collab_state = collab.status
    collab.status = CollaborationStatus.DISPUTA

    dispute = Dispute(
        collaboration_id=collaboration_id,
        opened_by_id=current_user.id,
        reason=dispute_in.reason,
        evidence_urls=json.dumps(dispute_in.evidence_urls or []),
        status=DisputeStatus.ABIERTA,
        previous_state=previous_collab_state,
        created_at=datetime.utcnow()
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="dispute",
        entidad_id=dispute.id,
        operacion="OPEN_DISPUTE",
        estado_anterior=previous_collab_state,
        estado_nuevo=CollaborationStatus.DISPUTA.value,
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Disputa abierta. El equipo de administración revisará las evidencias.",
        data=DisputeOut.model_validate(dispute),
        correlation_id=correlation_id
    )

@router.get("", response_model=APIResponse[List[DisputeOut]])
def list_disputes(
    current_user: User = Depends(require_role(UserRole.ADMINISTRADOR)),
    db: Session = Depends(get_db)
):
    """
    RF-18: Admin Dispute Panel to inspect reports and state histories.
    """
    disputes = db.query(Dispute).order_by(Dispute.created_at.desc()).all()
    return APIResponse(
        success=True,
        data=[DisputeOut.model_validate(d) for d in disputes]
    )

@router.post("/{dispute_id}/resolve", response_model=APIResponse[DisputeOut])
def resolve_dispute(
    dispute_id: str,
    resolve_in: DisputeResolve,
    current_user: User = Depends(require_role(UserRole.ADMINISTRADOR)),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RF-18: Administrative closure of disputes, recording previous_state, new_state,
    actor, and justification without modifying original connected metrics.
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Disputa no encontrada")

    collab = dispute.collaboration
    previous_state = dispute.status
    
    dispute.status = resolve_in.resolution_status
    dispute.admin_id = current_user.id
    dispute.resolution_notes = resolve_in.resolution_notes
    dispute.new_state = resolve_in.new_collaboration_status.value
    dispute.resolved_at = datetime.utcnow()

    # Update collaboration status accordingly
    collab.status = resolve_in.new_collaboration_status
    collab.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(dispute)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="dispute",
        entidad_id=dispute.id,
        operacion="RESOLVE_DISPUTE",
        estado_anterior=previous_state,
        estado_nuevo=resolve_in.resolution_status.value,
        resultado="SUCCESS",
        metadata={"resolution_notes": resolve_in.resolution_notes, "final_collab_status": resolve_in.new_collaboration_status.value}
    )

    return APIResponse(
        success=True,
        message=f"Disputa resuelta como '{resolve_in.resolution_status.value}'. Transición de estado registrada en auditoría.",
        data=DisputeOut.model_validate(dispute),
        correlation_id=correlation_id
    )
