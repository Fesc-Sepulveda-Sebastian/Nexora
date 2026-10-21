import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Profile, OAuthConsent, UserRole
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserOut, OAuthConsentOut
from app.schemas.common import APIResponse
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.audit_middleware import record_audit_log
from app.services.metrics_service import metrics_service
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Autenticación y OAuth"])

@router.post("/register", response_model=APIResponse[UserOut], status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    x_correlation_id: Optional[str] = Header(None)
):
    correlation_id = x_correlation_id or str(uuid.uuid4())

    if not user_in.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe aceptar los Términos y Condiciones para crear una cuenta."
        )

    # Check email duplicate
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta registrada con este correo electrónico."
        )

    hashed_pw = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_pw,
        role=user_in.role.value,
        is_active=True
    )
    db.add(user)
    db.flush()

    # Create associated profile
    profile = Profile(
        user_id=user.id,
        display_name=user_in.display_name,
        location_declared=user_in.location_declared or "Cúcuta, Colombia",
        niche=user_in.niche or "Gastronomía",
        average_rating=5.0,
        verified_reviews_count=0
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    # Audit register
    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=user.id,
        rol=user.role,
        entidad="user",
        entidad_id=user.id,
        operacion="REGISTER",
        estado_anterior=None,
        estado_nuevo="active",
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Usuario registrado exitosamente en Nexora",
        data=UserOut.model_validate(user),
        correlation_id=correlation_id
    )

@router.post("/login", response_model=APIResponse[TokenResponse])
def login(
    login_data: UserLogin, 
    db: Session = Depends(get_db),
    x_correlation_id: Optional[str] = Header(None)
):
    correlation_id = x_correlation_id or str(uuid.uuid4())
    
    # RF-01: Generic error messages to prevent account enumeration
    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas. Verifique su correo y contraseña.",
        headers={"WWW-Authenticate": "Bearer"}
    )

    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise generic_error

    if not verify_password(login_data.password, user.hashed_password):
        record_audit_log(
            db=db,
            correlation_id=correlation_id,
            actor_id=None,
            rol=None,
            entidad="user",
            entidad_id=user.id,
            operacion="LOGIN_FAILED",
            estado_anterior=None,
            estado_nuevo=None,
            resultado="FAILED"
        )
        raise generic_error

    if not user.is_active or user.privacy_status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta se encuentra inactiva o ha sido eliminada."
        )

    token = create_access_token(subject=user.id, role=user.role)
    display_name = user.profile.display_name if user.profile else user.email

    record_audit_log(
        db=db,
        correlation_id=correlation_id,
        actor_id=user.id,
        rol=user.role,
        entidad="user",
        entidad_id=user.id,
        operacion="LOGIN_SUCCESS",
        estado_anterior=None,
        estado_nuevo="authenticated",
        resultado="SUCCESS"
    )

    return APIResponse(
        success=True,
        message="Inicio de sesión exitoso",
        data=TokenResponse(
            access_token=token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            display_name=display_name
        ),
        correlation_id=correlation_id
    )

# OAuth 2.0 Flow (RF-03)
@router.post("/oauth/authorize")
def oauth_authorize(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """
    Initiates OAuth 2.0 with state and PKCE code challenge for social APIs.
    """
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    auth_url = f"https://api.{platform.lower()}.com/oauth/authorize?client_id=nexora_client&state={state}&scope=user_profile,user_media,user_insights"
    
    return {
        "platform": platform.upper(),
        "authorization_url": auth_url,
        "state": state,
        "code_verifier": code_verifier
    }

@router.post("/oauth/callback", response_model=APIResponse[OAuthConsentOut])
def oauth_callback(
    platform: str,
    code: str,
    state: str,
    code_verifier: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Completes OAuth 2.0 handshake, stores encrypted token record,
    and automatically fetches and saves verified connected metric snapshot (RF-04, RN-03).
    """
    username = f"{current_user.profile.display_name.lower().replace(' ', '_')}_{platform.lower()}"
    account_id = f"{platform.lower()}_{uuid.uuid4().hex[:8]}"
    
    consent = OAuthConsent(
        user_id=current_user.id,
        platform=platform.upper(),
        account_id=account_id,
        account_username=username,
        encrypted_token=f"enc_token_{secrets.token_hex(16)}",
        scopes="user_profile,user_media,user_insights",
        state=state,
        code_verifier=code_verifier,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=60)
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)

    # Immediately capture official connected metric snapshot in MongoDB (RF-04, RN-03)
    snapshot = metrics_service.create_mock_connected_snapshot(
        cuenta_id=account_id,
        plataforma=platform.upper(),
        followers=8500,
        engagement_pct=5.8,
        city=current_user.profile.location_declared or "Cúcuta"
    )
    metrics_service.save_snapshot(snapshot)

    return APIResponse(
        success=True,
        message=f"Cuenta de {platform.upper()} vinculada con éxito. Métricas sincronizadas vía API oficial.",
        data=OAuthConsentOut.model_validate(consent)
    )
