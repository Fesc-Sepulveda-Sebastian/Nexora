import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Profile, OAuthConsent, UserRole
from app.schemas.user import UserCreate, PublicUserRole, UserLogin, TokenResponse, UserOut, OAuthConsentOut
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

    if user_in.role not in (PublicUserRole.MARCA, PublicUserRole.CREADOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El registro público solo permite roles de 'marca' o 'creador'."
        )

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

    # Create associated profile (start with 0.0 rating and 0 verified reviews per H14)
    profile = Profile(
        user_id=user.id,
        display_name=user_in.display_name,
        location_declared=user_in.location_declared,
        niche=user_in.niche,
        average_rating=0.0,
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

# OAuth 2.0 Flow (RF-03) - Simulated Demo Mode until real provider OAuth credentials are configured
@router.post("/oauth/authorize")
def oauth_authorize(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiates OAuth 2.0 with state and PKCE code challenge for social APIs.
    Persists pending state/PKCE verifier for callback validation.
    """
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    normalized_platform = platform.upper()

    pending_consent = OAuthConsent(
        user_id=current_user.id,
        platform=normalized_platform,
        account_id=f"pending_{state[:12]}",
        account_username="pending",
        encrypted_token="pending_demo_handshake",
        scopes="user_profile,user_media,user_insights",
        state=state,
        code_verifier=code_verifier,
        is_active=False,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.add(pending_consent)
    db.commit()

    auth_url = f"https://api.{platform.lower()}.com/oauth/authorize?client_id=nexora_client&state={state}&scope=user_profile,user_media,user_insights"
    
    return {
        "platform": normalized_platform,
        "mode": "DEMO_SIMULADO",
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
    Completes OAuth 2.0 handshake in DEMO/SIMULATED mode (validating state & PKCE),
    and generates an explicitly labeled DEMO/SIMULADO metric snapshot (RF-04, RN-03).
    """
    if not code or not code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de autorización OAuth requerido."
        )

    normalized_platform = platform.upper()
    consent = db.query(OAuthConsent).filter(
        OAuthConsent.user_id == current_user.id,
        OAuthConsent.platform == normalized_platform,
        OAuthConsent.state == state,
        OAuthConsent.is_active == False
    ).first()

    if not consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado OAuth (state) inválido o no encontrado para este usuario."
        )

    if consent.expires_at and consent.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sesión OAuth (state) ha expirado. Inicie el flujo nuevamente."
        )

    if consent.code_verifier and code_verifier != consent.code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verificador PKCE (code_verifier) inválido."
        )

    display_slug = (current_user.profile.display_name if current_user.profile else current_user.email.split("@")[0]).lower().replace(" ", "_")
    username = f"{display_slug}_{platform.lower()}"
    account_id = f"demo_{platform.lower()}_{uuid.uuid4().hex[:8]}"

    consent.account_id = account_id
    consent.account_username = username
    consent.encrypted_token = f"demo_sim_token_{secrets.token_hex(16)}"
    consent.is_active = True
    consent.expires_at = datetime.utcnow() + timedelta(days=60)
    db.commit()
    db.refresh(consent)

    # Generate explicitly labeled DEMO/SIMULADO snapshot (never labeled as API_OFICIAL)
    snapshot = metrics_service.create_demo_snapshot(
        cuenta_id=account_id,
        plataforma=normalized_platform,
        followers=8500,
        engagement_pct=5.8,
        city=(current_user.profile.location_declared if current_user.profile else None) or "Cúcuta"
    )
    metrics_service.save_snapshot(snapshot)

    return APIResponse(
        success=True,
        message=f"Cuenta de {normalized_platform} vinculada en modo DEMO. Métricas generadas como SIMULADO (no conectadas a API oficial).",
        data=OAuthConsentOut.model_validate(consent)
    )
