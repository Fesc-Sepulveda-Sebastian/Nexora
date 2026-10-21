from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class RatingCreate(BaseModel):
    collaboration_id: str
    score: int = Field(..., ge=1, le=5, description="Calificación en escala de 1 a 5 estrellas")
    comment: Optional[str] = Field(None, max_length=1000, description="Comentario público sujeto a moderación")

class RatingOut(BaseModel):
    id: str
    collaboration_id: str
    reviewer_id: str
    reviewee_id: str
    score: int
    comment: Optional[str] = None
    is_moderated: bool
    created_at: datetime

    class Config:
        from_attributes = True
