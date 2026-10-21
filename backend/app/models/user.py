import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, Enum):
    MARCA = "marca"
    CREADOR = "creador"
    ADMINISTRADOR = "administrador"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.CREADOR)
    is_active = Column(Boolean, default=True)
    privacy_status = Column(String(50), default="active")  # active, deletion_requested, deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    oauth_consents = relationship("OAuthConsent", back_populates="user", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="brand", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="creator", cascade="all, delete-orphan")
    privacy_requests = relationship("PrivacyRequest", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    location_declared = Column(String(255), nullable=True)  # e.g., "Cúcuta, Colombia"
    niche = Column(String(100), nullable=True)  # e.g., "Gastronomía", "Moda", "Fitness"
    languages = Column(String(255), default="Español")
    avatar_url = Column(String(500), nullable=True)
    portfolio_samples = Column(Text, nullable=True)  # JSON string of approved content URLs/thumbnails
    verified_reviews_count = Column(Integer, default=0)
    average_rating = Column(Float, default=5.0)
    current_media_kit_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class OAuthConsent(Base):
    __tablename__ = "oauth_consents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    platform = Column(String(50), nullable=False)  # INSTAGRAM, YOUTUBE, TIKTOK
    account_id = Column(String(255), nullable=False)
    account_username = Column(String(255), nullable=False)
    encrypted_token = Column(Text, nullable=False)
    scopes = Column(String(500), nullable=False)
    state = Column(String(255), nullable=True)
    code_verifier = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="oauth_consents")


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending, completed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="privacy_requests")
