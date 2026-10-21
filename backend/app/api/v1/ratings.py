from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.rating import Rating
from app.models.collaboration import CollaborationAgreement, CollaborationStatus
from app.models.user import User, Profile
from app.schemas.rating import RatingCreate, RatingOut
from app.schemas.common import APIResponse
from app.core.audit_middleware import record_audit_log
from app.api.deps import get_current_user, get_correlation_id

router = APIRouter(prefix="/ratings", tags=["Reputación Bilateral"])

@router.post("", response_model=APIResponse[RatingOut], status_code=status.HTTP_201_CREATED)
def submit_rating(
    rating_in: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    RN-05: Bilateral ratings (1-5 stars) ONLY enabled when collaboration is 'Cerrada'.
    Allows exactly one rating per party.
    """
    collab = db.query(CollaborationAgreement).filter(CollaborationAgreement.id == rating_in.collaboration_id).first()
    if not collab:
        raise HTTPException(status_code=404, detail="Colaboración no encontrada")

    # RN-05 check: Collaboration must be Cerrada
    if collab.status != CollaborationStatus.CERRADA.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"RN-05: Las calificaciones solo se habilitan cuando la colaboración está 'Cerrada'. Estado actual: {collab.status}"
        )

    # Determine reviewer and reviewee
    if current_user.id == collab.brand_id:
        reviewee_id = collab.creator_id
    elif current_user.id == collab.creator_id:
        reviewee_id = collab.brand_id
    else:
        raise HTTPException(status_code=403, detail="No eres parte de esta colaboración")

    # Check if already rated (RN-05)
    existing_rating = db.query(Rating).filter(
        Rating.collaboration_id == collab.id,
        Rating.reviewer_id == current_user.id
    ).first()
    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RN-05: Ya has emitido una calificación para esta colaboración. No se permiten calificaciones duplicadas."
        )

    rating = Rating(
        collaboration_id=collab.id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        score=rating_in.score,
        comment=rating_in.comment,
        is_moderated=False,
        created_at=datetime.utcnow()
    )
    db.add(rating)

    # Update reviewee profile statistics
    reviewee = db.query(User).filter(User.id == reviewee_id).first()
    if reviewee and reviewee.profile:
        prof = reviewee.profile
        all_ratings = db.query(Rating).filter(Rating.reviewee_id == reviewee_id).all()
        scores = [r.score for r in all_ratings] + [rating_in.score]
        prof.verified_reviews_count = len(scores)
        prof.average_rating = round(sum(scores) / len(scores), 2)

    db.commit()
    db.refresh(rating)

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=current_user.id,
        rol=current_user.role,
        entidad="rating",
        entidad_id=rating.id,
        operacion="SUBMIT_RATING",
        estado_anterior=None,
        estado_nuevo="created",
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Calificación registrada exitosamente",
        data=RatingOut.model_validate(rating),
        correlation_id=correlation_id
    )
