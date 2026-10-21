from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MatchCriterion(BaseModel):
    criterion: str = Field(..., description="Nombre del criterio (nicho, ubicacion, engagement, formato)")
    detail: str = Field(..., description="Explicación legible, ej: 'Coincide por: Nicho Gastronomía'")
    weight_score: float = Field(..., description="Puntos aportados a la coincidencia")

class CreatorRecommendation(BaseModel):
    creator_id: str
    display_name: str
    niche: str
    location_declared: str
    avatar_url: Optional[str] = None
    average_rating: float
    total_score: float = Field(..., description="Puntaje de afinidad calculado transparentemente (0-100)")
    matching_criteria: List[MatchCriterion] = Field(..., description="Criterios explícitos de coincidencia (RF-26)")
    rule_version: str = Field(default="recommender-v1.2", description="Versión de regla utilizada para trazabilidad RNF-15")

class CampaignRecommendation(BaseModel):
    campaign_id: str
    title: str
    brand_name: str
    niche: str
    budget: float
    compensation_type: str
    total_score: float
    matching_criteria: List[MatchCriterion]
    rule_version: str = Field(default="recommender-v1.2")

class RecommendationResult(BaseModel):
    personalization_active: bool = True
    rule_version: str = "recommender-v1.2"
    items: List[Any] = []
