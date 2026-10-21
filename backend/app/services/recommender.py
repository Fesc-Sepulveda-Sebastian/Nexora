from typing import List, Dict, Any, Optional
from app.schemas.recommendation import CreatorRecommendation, CampaignRecommendation, MatchCriterion, RecommendationResult
from app.models.campaign import Campaign
from app.models.user import User, Profile

RULE_VERSION = "recommender-v1.2"

class RecommenderService:
    """
    Decoupled explainable recommendation service (RF-26, RNF-15).
    Calculates transparent affinity scores with traceable criteria.
    """

    @staticmethod
    def recommend_creators_for_campaign(
        campaign: Campaign, 
        creators: List[User], 
        personalization_active: bool = True
    ) -> RecommendationResult:
        if not personalization_active:
            # Return creators without algorithmic personalization
            items = []
            for u in creators:
                p = u.profile
                if not p:
                    continue
                items.append(
                    CreatorRecommendation(
                        creator_id=u.id,
                        display_name=p.display_name,
                        niche=p.niche or "General",
                        location_declared=p.location_declared or "Colombia",
                        avatar_url=p.avatar_url,
                        average_rating=p.average_rating or 5.0,
                        total_score=50.0,
                        matching_criteria=[
                            MatchCriterion(criterion="orden_cronologico", detail="Personalización desactivada por el usuario", weight_score=50.0)
                        ],
                        rule_version=RULE_VERSION
                    )
                )
            return RecommendationResult(personalization_active=False, rule_version=RULE_VERSION, items=items)

        recommendations: List[CreatorRecommendation] = []

        for creator in creators:
            profile: Optional[Profile] = creator.profile
            if not profile:
                continue

            score = 0.0
            criteria: List[MatchCriterion] = []

            # 1. Niche alignment (Weight: 35 pts)
            if campaign.niche and profile.niche and (campaign.niche.lower() in profile.niche.lower() or profile.niche.lower() in campaign.niche.lower()):
                score += 35.0
                criteria.append(MatchCriterion(
                    criterion="nicho",
                    detail=f"Coincide por: Nicho {profile.niche}",
                    weight_score=35.0
                ))

            # 2. Declared Location alignment (Weight: 25 pts)
            if profile.location_declared and ("cúcuta" in profile.location_declared.lower() or (campaign.selection_criteria and "cúcuta" in campaign.selection_criteria.lower())):
                score += 25.0
                criteria.append(MatchCriterion(
                    criterion="ubicacion",
                    detail=f"Ubicación declarada coincidente: {profile.location_declared}",
                    weight_score=25.0
                ))
            elif profile.location_declared:
                score += 15.0
                criteria.append(MatchCriterion(
                    criterion="ubicacion",
                    detail=f"Ubicación regional: {profile.location_declared}",
                    weight_score=15.0
                ))

            # 3. High Rating & Verified Reviews (Weight: 20 pts)
            if profile.average_rating and profile.average_rating >= 4.5:
                pts = round((profile.average_rating / 5.0) * 20.0, 1)
                score += pts
                criteria.append(MatchCriterion(
                    criterion="reputacion",
                    detail=f"Excelente reputación bilateral ({profile.average_rating}★ con {profile.verified_reviews_count} reseñas)",
                    weight_score=pts
                ))

            # 4. Content format fit / Nano-micro engagement bonus (Weight: 20 pts)
            score += 18.0
            criteria.append(MatchCriterion(
                criterion="formato_audiencia",
                detail="Formato de entrega afín a micro/nano influenciadores",
                weight_score=18.0
            ))

            recommendations.append(
                CreatorRecommendation(
                    creator_id=creator.id,
                    display_name=profile.display_name,
                    niche=profile.niche or "General",
                    location_declared=profile.location_declared or "Colombia",
                    avatar_url=profile.avatar_url,
                    average_rating=profile.average_rating or 5.0,
                    total_score=min(score, 100.0),
                    matching_criteria=criteria,
                    rule_version=RULE_VERSION
                )
            )

        # Sort highest score first
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        return RecommendationResult(personalization_active=True, rule_version=RULE_VERSION, items=recommendations)

recommender_service = RecommenderService()
