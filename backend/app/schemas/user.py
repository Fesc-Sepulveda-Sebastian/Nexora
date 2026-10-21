from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole
from app.schemas.metric_snapshot import MetricSnapshot

class UserBase(BaseModel):
    email: EmailStr
    role: UserRole

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=2)
    location_declared: Optional[str] = "Cúcuta, Colombia"
    niche: Optional[str] = "Gastronomía"
    terms_accepted: bool = Field(..., description="Aceptación de términos y condiciones obligatoria")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    display_name: str

class ProfileBase(BaseModel):
    display_name: str
    bio: Optional[str] = None
    location_declared: Optional[str] = None
    niche: Optional[str] = None
    languages: Optional[str] = "Español"
    avatar_url: Optional[str] = None
    portfolio_samples: Optional[str] = None

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    location_declared: Optional[str] = None
    niche: Optional[str] = None
    languages: Optional[str] = None
    avatar_url: Optional[str] = None
    portfolio_samples: Optional[str] = None

class ProfileOut(ProfileBase):
    id: str
    user_id: str
    verified_reviews_count: int
    average_rating: float
    current_media_kit_version: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool
    privacy_status: str
    profile: Optional[ProfileOut] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Dynamic Media Kit schema (RF-05, RF-21)
class MediaKitOut(BaseModel):
    creator_id: str
    display_name: str
    bio: Optional[str] = None
    location_declared: Optional[str] = None
    niche: Optional[str] = None
    languages: str
    avatar_url: Optional[str] = None
    version: int
    verified_reviews_count: int
    average_rating: float
    portfolio_samples: List[Dict[str, Any]] = []
    # Metrics snapshots differentiating connected API vs declared (RN-03)
    connected_metrics: List[MetricSnapshot] = []
    declared_metrics: List[Dict[str, Any]] = []
    generated_at_utc: datetime = Field(default_factory=datetime.utcnow)

class OAuthConsentOut(BaseModel):
    id: str
    platform: str
    account_username: str
    is_active: bool
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PrivacyRequestCreate(BaseModel):
    notes: Optional[str] = None

class PrivacyRequestOut(BaseModel):
    id: str
    status: str
    requested_at: datetime
    processed_at: Optional[datetime] = None
