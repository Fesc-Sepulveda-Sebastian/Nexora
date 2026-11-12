import json
from typing import List, Dict, Any, Optional, Set
from app.schemas.recommendation import CreatorRecommendation, MatchCriterion, RecommendationResult
from app.models.campaign import Campaign
from app.models.user import User, Profile

RULE_VERSION = "recommender-v1.3"


def _safe_json_loads(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _extract_campaign_formats(campaign: Campaign) -> Set[str]:
    formats: Set[str] = set()
    deliverables = _safe_json_loads(campaign.deliverables, [])
    if isinstance(deliverables, list):
        for item in deliverables:
            if isinstance(item, dict) and item.get("format"):
                formats.add(str(item["format"]).strip().lower())
    return formats


def _extract_creator_formats(profile: Profile) -> Set[str]:
    formats: Set[str] = set()
    samples = _safe_json_loads(profile.portfolio_samples, [])
    if isinstance(samples, list):
        for item in samples:
            if isinstance(item, dict) and item.get("format"):
                formats.add(str(item["format"]).strip().lower())
    return formats


def _extract_criteria_dict(campaign: Campaign) -> Dict[str, Any]:
    data = _safe_json_loads(campaign.selection_criteria, {})
    return data if isinstance(data, dict) else {}


class RecommenderService:
    """
    Decoupled explainable recommendation service (RF-26, RNF-15, H14).
    Calculates transparent, unbiased affinity scores with traceable criteria.
    """

    @staticmethod
    def recommend_creators_for_campaign(
        campaign: Campaign,
        creators: List[User],
        personalization_active: bool = True
    ) -> RecommendationResult:
        if not personalization_active:
            items = []
            for u in creators:
                p = u.profile
                if not p:
                    continue
                real_rating = round(float(p.average_rating), 2) if p.average_rating is not None else 0.0
                items.append(
                    CreatorRecommendation(
                        creator_id=u.id,
                        display_name=p.display_name,
                        niche=p.niche or "General",
                        location_declared=p.location_declared or "No especificada",
                        avatar_url=p.avatar_url,
                        average_rating=real_rating,
                        total_score=50.0,
                        matching_criteria=[
                            MatchCriterion(
                                criterion="orden_cronologico",
                                detail="Personalización desactivada por el usuario",
                                weight_score=50.0
                            )
                        ],
                        rule_version=RULE_VERSION
                    )
                )
            return RecommendationResult(personalization_active=False, rule_version=RULE_VERSION, items=items)

        criteria_dict = _extract_criteria_dict(campaign)
        target_location = str(criteria_dict.get("location") or "").strip().lower()
        target_platforms: Set[str] = {
            str(p).strip().lower()
            for p in (criteria_dict.get("platforms") or [])
            if str(p).strip()
        }
        target_formats = _extract_campaign_formats(campaign)

        recommendations: List[CreatorRecommendation] = []

        for creator in creators:
            profile: Optional[Profile] = creator.profile
            if not profile:
                continue

            score = 0.0
            criteria: List[MatchCriterion] = []

            # 1. Niche alignment (Weight: 35 pts)
            if (
                campaign.niche
                and profile.niche
                and (
                    campaign.niche.strip().lower() in profile.niche.strip().lower()
                    or profile.niche.strip().lower() in campaign.niche.strip().lower()
                )
            ):
                score += 35.0
                criteria.append(
                    MatchCriterion(
                        criterion="nicho",
                        detail=f"Coincide por: Nicho {profile.niche}",
                        weight_score=35.0
                    )
                )

            # 2. Objective Location alignment against campaign selection_criteria (Weight: 25 pts)
            if target_location and profile.location_declared:
                declared_loc = profile.location_declared.strip().lower()
                if target_location in declared_loc or declared_loc in target_location:
                    score += 25.0
                    criteria.append(
                        MatchCriterion(
                            criterion="ubicacion",
                            detail=f"Coincide con la ubicación solicitada: {profile.location_declared}",
                            weight_score=25.0
                        )
                    )

            # 3. Verified Bilateral Reputation (Weight: 20 pts; 0 pts if unreviewed)
            real_rating = round(float(profile.average_rating), 2) if profile.average_rating is not None else 0.0
            reviews_count = int(profile.verified_reviews_count or 0)
            if reviews_count > 0 and real_rating > 0.0:
                pts = round((min(real_rating, 5.0) / 5.0) * 20.0, 1)
                score += pts
                criteria.append(
                    MatchCriterion(
                        criterion="reputacion",
                        detail=f"Reputación bilateral verificada ({real_rating}★ con {reviews_count} reseñas)",
                        weight_score=pts
                    )
                )

            # 4. Content Format & Connected Platform fit (Weight: up to 20 pts: 12 format + 8 platform)
            creator_formats = _extract_creator_formats(profile)
            creator_platforms: Set[str] = {
                str(c.platform).strip().lower()
                for c in (creator.oauth_consents or [])
                if c.is_active and c.platform
            }

            format_pts = 0.0
            matched_details: List[str] = []

            if target_formats and creator_formats:
                matched_formats = target_formats.intersection(creator_formats)
                if matched_formats:
                    ratio = len(matched_formats) / len(target_formats)
                    format_pts += round(ratio * 12.0, 1)
                    matched_details.append(f"formatos {', '.join(sorted(matched_formats))}")

            if target_platforms and creator_platforms:
                matched_platforms = target_platforms.intersection(creator_platforms)
                if matched_platforms:
                    ratio = len(matched_platforms) / len(target_platforms)
                    format_pts += round(ratio * 8.0, 1)
                    matched_details.append(f"plataformas {', '.join(sorted(matched_platforms))}")

            if format_pts > 0.0:
                score += format_pts
                criteria.append(
                    MatchCriterion(
                        criterion="formato_audiencia",
                        detail=f"Afinidad verificada en {' y '.join(matched_details)}",
                        weight_score=format_pts
                    )
                )

            recommendations.append(
                CreatorRecommendation(
                    creator_id=creator.id,
                    display_name=profile.display_name,
                    niche=profile.niche or "General",
                    location_declared=profile.location_declared or "No especificada",
                    avatar_url=profile.avatar_url,
                    average_rating=real_rating,
                    total_score=round(min(score, 100.0), 1),
                    matching_criteria=criteria,
                    rule_version=RULE_VERSION
                )
            )

        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        return RecommendationResult(personalization_active=True, rule_version=RULE_VERSION, items=recommendations)


recommender_service = RecommenderService()
