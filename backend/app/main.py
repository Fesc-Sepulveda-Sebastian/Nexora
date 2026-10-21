import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.core.audit_middleware import CorrelationIdMiddleware
from app.core.websocket_manager import ws_manager
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

# WebSocket for active real-time messaging and live state updates
@app.websocket("/ws/{user_id}")
async def websocket_user_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect_user(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or process incoming ping
            await websocket.send_text(f'{{"event":"ack","received":"{data}"}}')
    except WebSocketDisconnect:
        ws_manager.disconnect_user(websocket, user_id)

@app.websocket("/ws/collaboration/{collab_id}")
async def websocket_collaboration_room(websocket: WebSocket, collab_id: str):
    await websocket.accept()
    room_id = f"collaboration_{collab_id}"
    await ws_manager.join_room(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast_to_room({"event": "room_message", "payload": data}, room_id)
    except WebSocketDisconnect:
        ws_manager.leave_room(websocket, room_id)
