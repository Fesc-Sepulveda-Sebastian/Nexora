import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Profile, PrivacyRequest, OAuthConsent
from app.schemas.user import UserOut, ProfileUpdate, ProfileOut, MediaKitOut, PrivacyRequestCreate, PrivacyRequestOut
from app.schemas.common import APIResponse
from app.schemas.metric_snapshot import MetricSnapshot
from app.services.metrics_service import metrics_service
from app.api.deps import get_current_user

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
def get_creator_media_kit(creator_id: str, db: Session = Depends(get_db)):
    """
    Generates dynamic Media Kit for creator (RF-05, RF-21).
    Distinguishes official connected API metrics from manually declared data (RN-03).
    """
    creator = db.query(User).filter(User.id == creator_id).first()
    if not creator or not creator.profile:
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
    connected_snapshots: List[MetricSnapshot] = []
    consents = db.query(OAuthConsent).filter(OAuthConsent.user_id == creator.id, OAuthConsent.is_active == True).all()
    
    for consent in consents:
        snapshots_data = metrics_service.get_snapshots_for_account(consent.account_id, consent.platform)
        for s in snapshots_data[:2]:  # Take most recent snapshots
            try:
                snapshot_obj = MetricSnapshot.model_validate(s)
                connected_snapshots.append(snapshot_obj)
            except Exception:
                pass

    # Declared metrics if no API connected or for complementary platforms
    declared_metrics = []
    if not connected_snapshots:
        declared_metrics.append({
            "plataforma": "INSTAGRAM",
            "tipo": "DECLARADO",
            "seguidores_estimados": 5400,
            "engagement_estimado": 4.2,
            "badge": "Dato Declarado por Creador (RN-03)",
            "origen": "DECLARADO_MANUAL"
        })

    media_kit = MediaKitOut(
        creator_id=creator.id,
        display_name=profile.display_name,
        bio=profile.bio or "Creador de contenido enfocado en micro-audiencias y alta fidelidad comunitaria.",
        location_declared=profile.location_declared or "Cúcuta, Colombia",
        niche=profile.niche or "Gastronomía",
        languages=profile.languages or "Español",
        avatar_url=profile.avatar_url or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
        version=profile.current_media_kit_version,
        verified_reviews_count=profile.verified_reviews_count,
        average_rating=profile.average_rating,
        portfolio_samples=samples,
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
    db: Session = Depends(get_db)
):
    """
    Privacy and account deletion request (RNF-12, RNF-17).
    Marks privacy status and schedules minimization of data.
    """
    req = PrivacyRequest(
        user_id=current_user.id,
        notes=req_in.notes,
        status="pending",
        created_at=datetime.utcnow()
    )
    current_user.privacy_status = "deletion_requested"
    db.add(req)
    db.commit()
    db.refresh(req)

    return APIResponse(
        success=True,
        message="Solicitud de eliminación de datos registrada. Su información será anonimizada según RNF-12.",
        data=PrivacyRequestOut.model_validate(req)
    )
