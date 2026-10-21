import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.collaboration import CollaborationAgreement, CollaborationStatus
from app.models.user import User, UserRole
from app.schemas.collaboration import (
    CollaborationAgreementUpdate, CollaborationAgreementAccept,
    CollaborationAgreementOut, ROICalculatorInput, ROICalculatorOutput
)
from app.schemas.common import APIResponse
from app.core.audit_middleware import record_audit_log
from app.api.deps import get_current_user, get_correlation_id

router = APIRouter(prefix="/collaborations", tags=["Colaboraciones y Acuerdos"])

@router.get("/{collaboration_id}", response_model=APIResponse[CollaborationAgreementOut])
def get_collaboration_agreement(collaboration_id: str, db: Session = Depends(get_db)):
    agreement = db.query(CollaborationAgreement).filter(CollaborationAgreement.id == collaboration_id).first()
    if not agreement:
        raise HTTPException(status_code=404, detail="Acuerdo de colaboración no encontrado")
    return APIResponse(success=True, data=CollaborationAgreementOut.model_validate(agreement))

@router.put("/{collaboration_id}/terms", response_model=APIResponse[CollaborationAgreementOut])
def update_collaboration_terms(
    collaboration_id: str,
    update_in: CollaborationAgreementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RF-13: Terms negotiation with optimistic concurrency.
    Any modification to conditions generates a new version_id and invalidates prior acceptances.
    """
    agreement = db.query(CollaborationAgreement).filter(CollaborationAgreement.id == collaboration_id).first()
    if not agreement:
        raise HTTPException(status_code=404, detail="Acuerdo no encontrado")

    if current_user.id != agreement.brand_id and current_user.id != agreement.creator_id and current_user.role != UserRole.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="No autorizado para editar los términos de este acuerdo")

    # If agreement is already executed or closed, modifications are prohibited
    if agreement.status in (CollaborationStatus.EN_EJECUCION.value, CollaborationStatus.CERRADA.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden editar términos de un acuerdo que ya está en ejecución o cerrado."
        )

    # Apply changes
    if update_in.scope_description is not None:
        agreement.scope_description = update_in.scope_description
    if update_in.deliverables_terms is not None:
        agreement.deliverables_terms = json.dumps(update_in.deliverables_terms)
    if update_in.compensation_amount is not None:
        agreement.compensation_amount = update_in.compensation_amount
    if update_in.deadline is not None:
        agreement.deadline = update_in.deadline

    # Invalidate previous acceptances and increment version (RF-13)
    previous_version = agreement.version_id
    agreement.version_id += 1
    agreement.brand_accepted = False
    agreement.brand_accepted_at = None
    agreement.creator_accepted = False
    agreement.creator_accepted_at = None
    agreement.status = CollaborationStatus.ACUERDO_PENDIENTE
    agreement.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(agreement)

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
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message=f"Términos actualizados a versión {agreement.version_id}. Se requiere re-aceptación de ambas partes.",
        data=CollaborationAgreementOut.model_validate(agreement),
        correlation_id=correlation_id
    )

@router.post("/{collaboration_id}/accept", response_model=APIResponse[CollaborationAgreementOut])
def accept_collaboration_agreement(
    collaboration_id: str,
    accept_in: CollaborationAgreementAccept,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RF-13: Both parties must accept online the same version for status to reach En_Ejecucion.
    """
    agreement = db.query(CollaborationAgreement).filter(CollaborationAgreement.id == collaboration_id).first()
    if not agreement:
        raise HTTPException(status_code=404, detail="Acuerdo no encontrado")

    if accept_in.accepted_version_id != agreement.version_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflicto de versión: La versión que intenta aceptar ({accept_in.accepted_version_id}) no coincide con la versión activa ({agreement.version_id})."
        )

    now = datetime.utcnow()
    is_brand = (current_user.id == agreement.brand_id)
    is_creator = (current_user.id == agreement.creator_id)

    if not is_brand and not is_creator:
        raise HTTPException(status_code=403, detail="No eres parte de esta colaboración")

    if is_brand:
        agreement.brand_accepted = True
        agreement.brand_accepted_at = now
    if is_creator:
        agreement.creator_accepted = True
        agreement.creator_accepted_at = now

    # Transition to En_Ejecucion when both accept the current version
    transitioned = False
    if agreement.brand_accepted and agreement.creator_accepted:
        agreement.status = CollaborationStatus.EN_EJECUCION
        transitioned = True

    agreement.updated_at = now
    db.commit()
    db.refresh(agreement)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="collaboration_agreement",
        entidad_id=agreement.id,
        operacion="ACCEPT_AGREEMENT",
        estado_anterior=CollaborationStatus.ACUERDO_PENDIENTE.value,
        estado_nuevo=agreement.status.value,
        resultado="SUCCESS"
    )

    msg = "¡Colaboración en ejecución! Ambas partes han aceptado los términos formalmente." if transitioned else "Aceptación registrada. Esperando confirmación de la contraparte."

    return APIResponse(
        success=True,
        message=msg,
        data=CollaborationAgreementOut.model_validate(agreement),
        correlation_id=correlation_id
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
            detail="RN-04: El costo total declarado debe ser estrictamente mayor a 0 para calcular el ROI."
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
        calculated_at_utc=datetime.utcnow()
    )

    return APIResponse(
        success=True,
        message="Cálculo de ROI Estimado procesado según RN-04",
        data=result
    )
