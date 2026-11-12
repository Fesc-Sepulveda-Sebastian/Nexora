import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.collaboration import (
    CollaborationAgreement,
    CollaborationAgreementVersion,
    CollaborationStatus,
)
from app.models.user import User, UserRole
from app.schemas.collaboration import (
    CollaborationAgreementUpdate,
    CollaborationAgreementAccept,
    CollaborationAgreementOut,
    CollaborationAgreementVersionOut,
    ROICalculatorInput,
    ROICalculatorOutput,
)
from app.schemas.common import APIResponse
from app.core.audit_middleware import record_audit_log
from app.api.deps import get_current_user, get_correlation_id

router = APIRouter(prefix="/collaborations", tags=["Colaboraciones y Acuerdos"])


def _enum_val(val) -> str:
    return val.value if hasattr(val, "value") else str(val)


def _assert_collaboration_access(agreement: CollaborationAgreement, current_user: User) -> None:
    if (
        current_user.id != agreement.brand_id
        and current_user.id != agreement.creator_id
        and current_user.role != UserRole.ADMINISTRADOR.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para acceder a este acuerdo de colaboración",
        )


def _ensure_version_snapshot(
    db: Session,
    agreement: CollaborationAgreement,
    version_number: int,
    edited_by_id: Optional[str] = None,
) -> None:
    exists = (
        db.query(CollaborationAgreementVersion)
        .filter(
            CollaborationAgreementVersion.collaboration_id == agreement.id,
            CollaborationAgreementVersion.version_id == version_number,
        )
        .first()
    )
    if not exists:
        snapshot = CollaborationAgreementVersion(
            collaboration_id=agreement.id,
            version_id=version_number,
            scope_description=agreement.scope_description,
            deliverables_terms=agreement.deliverables_terms,
            compensation_amount=agreement.compensation_amount,
            deadline=agreement.deadline,
            edited_by_id=edited_by_id,
        )
        db.add(snapshot)


@router.get("", response_model=APIResponse[List[CollaborationAgreementOut]])
def list_collaborations(
    campaign_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(CollaborationAgreement)
    if current_user.role != UserRole.ADMINISTRADOR.value:
        query = query.filter(
            or_(
                CollaborationAgreement.brand_id == current_user.id,
                CollaborationAgreement.creator_id == current_user.id,
            )
        )
    if campaign_id:
        query = query.filter(CollaborationAgreement.campaign_id == campaign_id)

    agreements = query.order_by(CollaborationAgreement.updated_at.desc()).all()
    return APIResponse(
        success=True,
        data=[CollaborationAgreementOut.model_validate(a) for a in agreements],
    )


@router.get("/{collaboration_id}", response_model=APIResponse[CollaborationAgreementOut])
def get_collaboration_agreement(
    collaboration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agreement = (
        db.query(CollaborationAgreement)
        .filter(CollaborationAgreement.id == collaboration_id)
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Acuerdo de colaboración no encontrado")
    _assert_collaboration_access(agreement, current_user)
    return APIResponse(success=True, data=CollaborationAgreementOut.model_validate(agreement))


@router.get(
    "/{collaboration_id}/versions",
    response_model=APIResponse[List[CollaborationAgreementVersionOut]],
)
def get_collaboration_versions(
    collaboration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agreement = (
        db.query(CollaborationAgreement)
        .filter(CollaborationAgreement.id == collaboration_id)
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Acuerdo de colaboración no encontrado")
    _assert_collaboration_access(agreement, current_user)

    versions = (
        db.query(CollaborationAgreementVersion)
        .filter(CollaborationAgreementVersion.collaboration_id == collaboration_id)
        .order_by(CollaborationAgreementVersion.version_id.asc())
        .all()
    )
    return APIResponse(
        success=True,
        data=[CollaborationAgreementVersionOut.model_validate(v) for v in versions],
    )


@router.put("/{collaboration_id}/terms", response_model=APIResponse[CollaborationAgreementOut])
def update_collaboration_terms(
    collaboration_id: str,
    update_in: CollaborationAgreementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    RF-13: Terms negotiation with optimistic concurrency (expected_version).
    Any modification to conditions preserves version history, generates a new version_id,
    and invalidates prior acceptances.
    """
    agreement = (
        db.query(CollaborationAgreement)
        .filter(CollaborationAgreement.id == collaboration_id)
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Acuerdo no encontrado")

    _assert_collaboration_access(agreement, current_user)

    current_status = _enum_val(agreement.status)
    if current_status in (
        CollaborationStatus.EN_EJECUCION.value,
        CollaborationStatus.EN_REVISION.value,
        CollaborationStatus.CERRADA.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden editar términos de un acuerdo que ya está en ejecución, revisión o cerrado.",
        )

    if agreement.version_id != update_in.expected_version:
        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=current_user.id,
            rol=current_user.role,
            entidad="collaboration_agreement",
            entidad_id=agreement.id,
            operacion="UPDATE_TERMS_CONFLICT",
            estado_anterior=f"v{agreement.version_id}",
            estado_nuevo=f"v{update_in.expected_version}",
            resultado="CONFLICT",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "VERSION_CONFLICT",
                "message": "El acuerdo fue actualizado por la otra parte antes de guardar sus cambios.",
                "server_version": agreement.version_id,
                "server_data": CollaborationAgreementOut.model_validate(agreement).model_dump(mode="json"),
            },
        )

    try:
        # Preserve current version snapshot before mutating
        _ensure_version_snapshot(db, agreement, agreement.version_id, edited_by_id=None)

        if update_in.scope_description is not None:
            agreement.scope_description = update_in.scope_description
        if update_in.deliverables_terms is not None:
            agreement.deliverables_terms = json.dumps(update_in.deliverables_terms)
        if update_in.compensation_amount is not None:
            agreement.compensation_amount = update_in.compensation_amount
        if update_in.deadline is not None:
            agreement.deadline = update_in.deadline

        previous_version = agreement.version_id
        agreement.version_id += 1
        agreement.brand_accepted = False
        agreement.brand_accepted_at = None
        agreement.creator_accepted = False
        agreement.creator_accepted_at = None
        agreement.status = CollaborationStatus.ACUERDO_PENDIENTE.value
        agreement.updated_at = datetime.utcnow()

        # Record new version snapshot in history
        _ensure_version_snapshot(db, agreement, agreement.version_id, edited_by_id=current_user.id)

        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=current_user.id,
            rol=current_user.role,
            entidad="collaboration_agreement",
            entidad_id=agreement.id,
            operacion="UPDATE_TERMS",
            estado_anterior=f"v{previous_version}",
            estado_nuevo=f"v{agreement.version_id}",
            resultado="SUCCESS",
            commit=False,
        )

        db.commit()
        db.refresh(agreement)
    except Exception:
        db.rollback()
        raise

    return APIResponse(
        success=True,
        message=f"Términos actualizados a versión {agreement.version_id}. Se requiere re-aceptación de ambas partes.",
        data=CollaborationAgreementOut.model_validate(agreement),
        correlation_id=correlation_id,
    )


@router.post("/{collaboration_id}/accept", response_model=APIResponse[CollaborationAgreementOut])
def accept_collaboration_agreement(
    collaboration_id: str,
    accept_in: CollaborationAgreementAccept,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    RF-13: Both parties must accept online the same version for status to reach En_Ejecucion.
    Executes agreement update and audit log inside the same atomic transaction.
    """
    agreement = (
        db.query(CollaborationAgreement)
        .filter(CollaborationAgreement.id == collaboration_id)
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Acuerdo no encontrado")

    is_brand = current_user.id == agreement.brand_id
    is_creator = current_user.id == agreement.creator_id
    if not is_brand and not is_creator:
        raise HTTPException(status_code=403, detail="No eres parte de esta colaboración")

    previous_status = _enum_val(agreement.status)
    if previous_status in (CollaborationStatus.CERRADA.value, CollaborationStatus.DISPUTA.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede aceptar un acuerdo en estado '{previous_status}'.",
        )

    if accept_in.accepted_version_id != agreement.version_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflicto de versión: La versión que intenta aceptar ({accept_in.accepted_version_id}) no coincide con la versión activa ({agreement.version_id}).",
        )

    now = datetime.utcnow()
    try:
        if is_brand:
            agreement.brand_accepted = True
            agreement.brand_accepted_at = now
        if is_creator:
            agreement.creator_accepted = True
            agreement.creator_accepted_at = now

        transitioned = False
        if agreement.brand_accepted and agreement.creator_accepted:
            agreement.status = CollaborationStatus.EN_EJECUCION.value
            transitioned = True

        agreement.updated_at = now
        new_status = _enum_val(agreement.status)

        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=current_user.id,
            rol=current_user.role,
            entidad="collaboration_agreement",
            entidad_id=agreement.id,
            operacion="ACCEPT_AGREEMENT",
            estado_anterior=previous_status,
            estado_nuevo=new_status,
            resultado="SUCCESS",
            commit=False,
        )

        db.commit()
        db.refresh(agreement)
    except Exception:
        db.rollback()
        raise

    msg = (
        "¡Colaboración en ejecución! Ambas partes han aceptado los términos formalmente."
        if transitioned
        else "Aceptación registrada. Esperando confirmación de la contraparte."
    )

    return APIResponse(
        success=True,
        message=msg,
        data=CollaborationAgreementOut.model_validate(agreement),
        correlation_id=correlation_id,
    )


@router.post("/{collaboration_id}/close", response_model=APIResponse[CollaborationAgreementOut])
def close_collaboration(
    collaboration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    RF-17 / RN-05: Ordinary closure of a collaboration agreement.
    Persists status='Cerrada' in database, enabling bilateral ratings (RN-05).
    """
    agreement = (
        db.query(CollaborationAgreement)
        .filter(CollaborationAgreement.id == collaboration_id)
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Colaboración no encontrada")

    _assert_collaboration_access(agreement, current_user)

    previous_status = _enum_val(agreement.status)
    if previous_status not in (
        CollaborationStatus.EN_EJECUCION.value,
        CollaborationStatus.EN_REVISION.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden cerrar colaboraciones en estado 'En_Ejecucion' o 'En_Revision'. Estado actual: {previous_status}",
        )

    try:
        agreement.status = CollaborationStatus.CERRADA.value
        agreement.updated_at = datetime.utcnow()

        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=current_user.id,
            rol=current_user.role,
            entidad="collaboration_agreement",
            entidad_id=agreement.id,
            operacion="CLOSE_COLLABORATION",
            estado_anterior=previous_status,
            estado_nuevo=CollaborationStatus.CERRADA.value,
            resultado="SUCCESS",
            commit=False,
        )

        db.commit()
        db.refresh(agreement)
    except Exception:
        db.rollback()
        raise

    return APIResponse(
        success=True,
        message="Colaboración cerrada exitosamente. Calificaciones bilaterales habilitadas (RN-05).",
        data=CollaborationAgreementOut.model_validate(agreement),
        correlation_id=correlation_id,
    )


@router.post("/roi-calculator", response_model=APIResponse[ROICalculatorOutput])
def calculate_estimated_roi(roi_in: ROICalculatorInput):
    """
    RN-04: Calculates estimated ROI strictly if brand declares total_cost > 0.
    Formula: ((beneficio_atribuible - costo) / costo) * 100.
    Always labeled as 'Estimación' with input sources and timestamp.
    """
    if roi_in.total_cost <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RN-04: El costo total declarado debe ser estrictamente mayor a 0 para calcular el ROI.",
        )

    net_profit = roi_in.attributable_benefit - roi_in.total_cost
    roi_pct = round((net_profit / roi_in.total_cost) * 100.0, 2)

    result = ROICalculatorOutput(
        roi_percentage=roi_pct,
        total_cost=roi_in.total_cost,
        attributable_benefit=roi_in.attributable_benefit,
        net_profit=round(net_profit, 2),
        currency=roi_in.currency,
        cost_source=roi_in.cost_source,
        benefit_source=roi_in.benefit_source,
        calculated_at_utc=datetime.utcnow(),
    )

    return APIResponse(
        success=True,
        message="Cálculo de ROI Estimado procesado según RN-04",
        data=result,
    )
