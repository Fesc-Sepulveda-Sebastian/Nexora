import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database import get_mongo_db
from app.schemas.metric_snapshot import MetricSnapshot, EngagementFormula

logger = logging.getLogger(__name__)

# In-memory storage for metric snapshots when MongoDB instance is not configured locally
_fallback_snapshots_store: List[Dict[str, Any]] = []

class MetricsService:
    @staticmethod
    def save_snapshot(snapshot: MetricSnapshot) -> Dict[str, Any]:
        """
        Stores immutable metric snapshot with the 5 mandatory metadata fields (RF-04, RN-03).
        """
        data = snapshot.model_dump()
        data["fecha_captura_utc"] = snapshot.fecha_captura_utc.isoformat()
        
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            try:
                result = mongo_db.metric_snapshots.insert_one(data)
                data["_id"] = str(result.inserted_id)
                logger.info(f"Saved metric snapshot to MongoDB for {snapshot.cuenta_id}")
                return data
            except Exception as e:
                logger.error(f"Error saving to MongoDB: {e}. Storing in fallback store.")
        
        # Fallback in-memory
        _fallback_snapshots_store.append(data)
        return data

    @staticmethod
    def get_snapshots_for_account(cuenta_id: str, plataforma: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all historical immutable snapshots for a creator's social account.
        """
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            try:
                query = {"cuenta_id": cuenta_id}
                if plataforma:
                    query["plataforma"] = plataforma.upper()
                cursor = mongo_db.metric_snapshots.find(query).sort("fecha_captura_utc", -1)
                results = []
                for doc in cursor:
                    doc["_id"] = str(doc["_id"])
                    results.append(doc)
                return results
            except Exception as e:
                logger.error(f"Error querying MongoDB: {e}")
        
        # Fallback store search
        results = [
            s for s in _fallback_snapshots_store
            if s["cuenta_id"] == cuenta_id and (not plataforma or s["plataforma"] == plataforma.upper())
        ]
        results.sort(key=lambda x: x["fecha_captura_utc"], reverse=True)
        return results

    @staticmethod
    def create_mock_connected_snapshot(cuenta_id: str, plataforma: str, followers: int, engagement_pct: float, city: str = "Cúcuta") -> MetricSnapshot:
        """
        Helper to simulate an official API metric sync (RF-04, RN-03).
        Calculates exact engagement formula and stores transparent metadata.
        """
        reach = int(followers * 2.2)
        interactions = int(reach * (engagement_pct / 100.0))
        
        formula = EngagementFormula(
            interactions=interactions,
            reach_or_impressions=reach,
            formula_string="((likes + comments + shares + saves) / reach) * 100",
            calculated_percentage=engagement_pct
        )
        
        snapshot = MetricSnapshot(
            plataforma=plataforma.upper(),
            cuenta_id=cuenta_id,
            periodo="LAST_30_DAYS",
            fecha_captura_utc=datetime.utcnow(),
            estado="CONECTADO_API",
            esquema_version="1.0.0",
            fuente_origen=f"API_OFICIAL_{plataforma.upper()}",
            followers_count=followers,
            engagement=formula,
            avg_impressions=int(reach * 0.75),
            avg_video_views=int(reach * 0.9),
            top_locations=[
                {"city": city, "pct": 62.5},
                {"city": "Bucaramanga", "pct": 18.0},
                {"city": "Bogotá", "pct": 12.0}
            ],
            authenticity_notice="Dato conectado verificado por API oficial. Nexora no certifica audiencia 100% auténtica (RN-03)."
        )
        return snapshot

metrics_service = MetricsService()
