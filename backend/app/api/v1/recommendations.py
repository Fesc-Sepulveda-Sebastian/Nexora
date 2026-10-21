from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.campaign import Campaign
from app.models.user import User, UserRole
from app.schemas.recommendation import RecommendationResult
from app.schemas.common import APIResponse
from app.services.recommender import recommender_service
from app.api.deps import get_current_user

router = APIRouter(prefix="/recommendations", tags=["Motor de Recomendaciones"])

@router.get("/campaigns/{campaign_id}/creators", response_model=APIResponse[RecommendationResult])
def recommend_creators(
    campaign_id: str,
    personalization: bool = Query(True, description="Interruptor para activar o desactivar la personalización algorítmica"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    RF-26, RNF-15: Transparent recommendation engine with explainable matching criteria and rule versioning.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    creators = db.query(User).filter(User.role == UserRole.CREADOR.value, User.is_active == True).all()

    result = recommender_service.recommend_creators_for_campaign(
        campaign=campaign,
        creators=creators,
        personalization_active=personalization
    )

    return APIResponse(
        success=True,
        message="Recomendaciones explicables generadas con éxito",
        data=result
    )
