import json
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, SessionLocal
from app.core.audit_middleware import CorrelationIdMiddleware
from app.core.security import decode_access_token
from app.core.websocket_manager import ws_manager
from app.models.user import User, UserRole
from app.models.collaboration import CollaborationAgreement
from app.api.v1 import api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    init_db()
    logger.info("Nexora Backend MVP (Fase 1) initialized.")
    yield
    logger.info("Nexora Backend shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API RESTful de Nexora: Marketplace B2B/B2C para Marcas y Creadores de Contenido (Mobile-First / PWA).",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"]
)

# Traceability & Correlation ID Middleware (RNF-11)
app.add_middleware(CorrelationIdMiddleware)

# Mount API v1 Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health check
@app.get("/health", tags=["Salud del Sistema"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

def _authenticate_ws_token(websocket: WebSocket, token: Optional[str]) -> Optional[User]:
    jwt_token = token
    if not jwt_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            jwt_token = auth_header.split(" ", 1)[1].strip()
    if not jwt_token:
        return None

    payload = decode_access_token(jwt_token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active or user.privacy_status == "deleted":
            return None
        # Detach scalar attributes needed after session close
        db.expunge(user)
        return user
    finally:
        db.close()


# WebSocket for active real-time messaging and live state updates
@app.websocket("/ws/{user_id}")
async def websocket_user_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None)
):
    user = _authenticate_ws_token(websocket, token)
    if not user or user.id != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect_user(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or process incoming ping
            await websocket.send_text(json.dumps({"event": "ack", "received": data}))
    except WebSocketDisconnect:
        ws_manager.disconnect_user(websocket, user_id)

@app.websocket("/ws/collaboration/{collab_id}")
async def websocket_collaboration_room(
    websocket: WebSocket,
    collab_id: str,
    token: Optional[str] = Query(None)
):
    user = _authenticate_ws_token(websocket, token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()
    try:
        collab = db.query(CollaborationAgreement).filter(CollaborationAgreement.id == collab_id).first()
        is_member = bool(
            collab and (
                user.id == collab.brand_id
                or user.id == collab.creator_id
                or user.role == UserRole.ADMINISTRADOR.value
            )
        )
    finally:
        db.close()

    if not is_member:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    room_id = f"collaboration_{collab_id}"
    await ws_manager.join_room(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast_to_room({"event": "room_message", "payload": data}, room_id)
    except WebSocketDisconnect:
        ws_manager.leave_room(websocket, room_id)
