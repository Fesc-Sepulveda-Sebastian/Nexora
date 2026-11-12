import json
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Profile, PrivacyRequest, OAuthConsent, UserRole
from app.schemas.user import UserOut, ProfileUpdate, ProfileOut, MediaKitOut, PrivacyRequestCreate, PrivacyRequestOut
from app.schemas.common import APIResponse
from app.schemas.metric_snapshot import MetricSnapshot
from app.services.metrics_service import metrics_service
from app.domain.nexora_rules import (
    clasificar_creador_y_tarifa,
    es_elegible_premium_sin_costo,
    puede_ver_metricas,
)
from app.core.security import get_password_hash
from app.core.audit_middleware import record_audit_log
from app.api.deps import get_current_user, get_optional_current_user, get_correlation_id

router = APIRouter(prefix="/users", tags=["Usuarios y Media Kit"])

@router.get("/me", response_model=APIResponse[UserOut])
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return APIResponse(
        success=True,
        data=UserOut.model_validate(current_user)
    )

@router.put("/me/profile", response_model=APIResponse[ProfileOut])
def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = current_user.profile
    if not profile:
        profile = Profile(user_id=current_user.id, display_name=current_user.email)
        db.add(profile)
    
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    # Increment media kit version when profile/content is updated
    profile.current_media_kit_version += 1
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    return APIResponse(
        success=True,
        message="Perfil actualizado con éxito",
        data=ProfileOut.model_validate(profile)
    )

@router.get("/{creator_id}/media-kit", response_model=APIResponse[MediaKitOut])
def get_creator_media_kit(
    creator_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Generates dynamic Media Kit for creator (RF-05, RF-21).
    Distinguishes official connected API metrics from manually declared data (RN-03).
    Applies Guía 03 access rule (`puede_ver_metricas`: creator OR admin) for internal metrics snapshots.
    """
    creator = db.query(User).filter(User.id == creator_id).first()
    if not creator or not creator.profile or not creator.is_active or creator.privacy_status == "deleted":
        raise HTTPException(status_code=404, detail="Creador o perfil no encontrado")

    profile = creator.profile

    # Parse portfolio samples
    samples = []
    if profile.portfolio_samples:
        try:
            samples = json.loads(profile.portfolio_samples)
        except Exception:
            samples = []

    # Fetch connected snapshots from MongoDB / service
    raw_snapshots: List[MetricSnapshot] = []
    consents = db.query(OAuthConsent).filter(OAuthConsent.user_id == creator.id, OAuthConsent.is_active == True).all()

    for consent in consents:
        snapshots_data = metrics_service.get_snapshots_for_account(consent.account_id, consent.platform)
        for s in snapshots_data[:2]:  # Take most recent snapshots
            try:
                snapshot_obj = MetricSnapshot.model_validate(s)
                raw_snapshots.append(snapshot_obj)
            except Exception:
                pass

    # Determine follower tier & NEXORA Premium eligibility via pure rules
    followers_effective = profile.followers_declared or 0
    if raw_snapshots:
        followers_effective = max(
            followers_effective,
            max((s.followers_count for s in raw_snapshots), default=0),
        )
    tier_info = clasificar_creador_y_tarifa(max(followers_effective, 0))
    is_top_influencer = bool(
        tier_info["elegible_nexora_premium"]
        or (profile.verified_reviews_count >= 5 and profile.average_rating >= 4.5)
    )
    is_verified_brand = bool(
        current_user
        and current_user.role == UserRole.MARCA.value
        and current_user.profile
        and current_user.profile.is_verified
    )
    premium_eligible = es_elegible_premium_sin_costo(is_verified_brand, is_top_influencer)

    # Guía 03 OR rule for detailed metrics visibility
    es_creador = bool(current_user and current_user.id == creator.id)
    es_administrador = bool(current_user and current_user.role == UserRole.ADMINISTRADOR.value)
    can_view_metrics = puede_ver_metricas(es_creador, es_administrador)

    connected_snapshots: List[MetricSnapshot] = raw_snapshots if can_view_metrics else []
    declared_metrics: List[Dict[str, Any]] = []
    if can_view_metrics and not connected_snapshots and (profile.followers_declared or 0) > 0:
        declared_metrics.append({
            "plataforma": "INSTAGRAM",
            "tipo": "DECLARADO",
            "seguidores_estimados": profile.followers_declared,
            "badge": "Dato Declarado por Creador (RN-03)",
            "origen": "DECLARADO_MANUAL"
        })

    media_kit = MediaKitOut(
        creator_id=creator.id,
        display_name=profile.display_name,
        bio=profile.bio or "Creador de contenido enfocado en audiencias de alto valor.",
        location_declared=profile.location_declared or "No especificada",
        niche=profile.niche or "General",
        languages=profile.languages or "Español",
        avatar_url=profile.avatar_url or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
        version=profile.current_media_kit_version,
        verified_reviews_count=profile.verified_reviews_count,
        average_rating=profile.average_rating,
        portfolio_samples=samples,
        creator_tier=tier_info["nivel"],
        nexora_premium_eligible=premium_eligible,
        metrics_restricted=not can_view_metrics,
        connected_metrics=connected_snapshots,
        declared_metrics=declared_metrics,
        generated_at_utc=datetime.utcnow()
    )

    return APIResponse(
        success=True,
        message="Media Kit dinámico generado exitosamente",
        data=media_kit
    )

@router.post("/me/privacy/delete-request", response_model=APIResponse[PrivacyRequestOut])
def request_account_deletion(
    req_in: PrivacyRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Privacy and account deletion/anonymization request (RNF-12, RNF-17).
    Executes immediate PII anonymization, revokes OAuth consents, deactivates account,
    and records a completed PrivacyRequest atomically.
    """
    now = datetime.utcnow()
    try:
        req = PrivacyRequest(
            user_id=current_user.id,
            notes=req_in.notes,
            status="completed",
            created_at=now,
            processed_at=now
        )
        db.add(req)
        db.flush()

        # Anonymize user PII and deactivate account
        current_user.email = f"deleted_{current_user.id}@anonymized.nexora.local"
        current_user.hashed_password = get_password_hash(secrets.token_urlsafe(32))
        current_user.is_active = False
        current_user.privacy_status = "deleted"
        current_user.updated_at = now

        if current_user.profile:
            current_user.profile.display_name = f"Usuario Anonimizado {current_user.id[:8]}"
            current_user.profile.bio = None
            current_user.profile.location_declared = None
            current_user.profile.avatar_url = None
            current_user.profile.portfolio_samples = None
            current_user.profile.updated_at = now

        # Revoke all OAuth consents
        consents = db.query(OAuthConsent).filter(OAuthConsent.user_id == current_user.id).all()
        for c in consents:
            c.is_active = False
            c.encrypted_token = "REVOKED"

        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=current_user.id,
            rol=current_user.role,
            entidad="privacy_request",
            entidad_id=req.id or current_user.id,
            operacion="PRIVACY_DELETE_ANONYMIZE",
            estado_anterior="active",
            estado_nuevo="deleted",
            resultado="SUCCESS",
            commit=False
        )

        db.commit()
        db.refresh(req)
    except Exception:
        db.rollback()
        raise

    return APIResponse(
        success=True,
        message="Solicitud de privacidad procesada. Sus datos personales han sido anonimizados y la cuenta desactivada según RNF-12.",
        data=PrivacyRequestOut.model_validate(req),
        correlation_id=correlation_id
    )
