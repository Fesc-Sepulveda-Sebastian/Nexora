from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class EngagementFormula(BaseModel):
    interactions: int = Field(description="Interacciones totales (likes, comments, shares, saves)")
    reach_or_impressions: int = Field(description="Alcance o impresiones totales")
    formula_string: str = Field(default="((likes + comments + shares + saves) / reach) * 100", description="Fórmula explícita de cálculo según RN-03")
    calculated_percentage: float = Field(description="Porcentaje resultante de engagement")

class MetricSnapshot(BaseModel):
    # 5 Mandatory metadata fields required by RF-04 / RN-03
    plataforma: str = Field(..., description="INSTAGRAM, YOUTUBE, TIKTOK")
    cuenta_id: str = Field(..., description="Identificador único de la cuenta en la plataforma social")
    periodo: str = Field(..., description="Ventana temporal analizada, ej. 'LAST_30_DAYS', '2026-M09'")
    fecha_captura_utc: datetime = Field(default_factory=datetime.utcnow, description="Timestamp UTC inmutable de captura")
    estado: str = Field(..., description="'CONECTADO_API', 'DECLARADO', 'NO_DISPONIBLE'")
    
    # Traceability & Schema Versioning (RN-03)
    esquema_version: str = Field(default="1.0.0", description="Versión del esquema de métricas")
    fuente_origen: str = Field(..., description="API_OFICIAL_INSTAGRAM, API_OFICIAL_YOUTUBE, API_OFICIAL_TIKTOK, DECLARADO_MANUAL")
    
    # Semi-structured metrics data
    followers_count: int = Field(default=0)
    engagement: EngagementFormula
    avg_impressions: int = Field(default=0)
    avg_video_views: Optional[int] = Field(default=0)
    top_locations: List[Dict[str, Any]] = Field(default_factory=list)  # e.g., [{"city": "Cúcuta", "pct": 45.2}]
    
    # Authenticity Notice Rule RN-03: Prohibido prometer 100% auténtica
    authenticity_notice: str = Field(
        default="Dato conectado verificado por API oficial. Nexora no certifica audiencia 100% auténtica (RN-03).",
        description="Aviso legal y técnico obligatorio de veracidad"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plataforma": "INSTAGRAM",
                "cuenta_id": "creator_cucuta_food",
                "periodo": "LAST_30_DAYS",
                "fecha_captura_utc": "2026-10-20T12:00:00Z",
                "estado": "CONECTADO_API",
                "esquema_version": "1.0.0",
                "fuente_origen": "API_OFICIAL_INSTAGRAM",
                "followers_count": 8500,
                "engagement": {
                    "interactions": 1250,
                    "reach_or_impressions": 18200,
                    "formula_string": "((interactions) / reach_or_impressions) * 100",
                    "calculated_percentage": 6.87
                },
                "avg_impressions": 6200,
                "avg_video_views": 11500,
                "top_locations": [{"city": "Cúcuta", "pct": 65.0}, {"city": "Bucaramanga", "pct": 18.0}],
                "authenticity_notice": "Dato conectado verificado por API oficial. Nexora no certifica audiencia 100% auténtica (RN-03)."
            }
        }
