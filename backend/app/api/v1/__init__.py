from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.applications import router as applications_router
from app.api.v1.collaborations import router as collaborations_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.messages import router as messages_router
from app.api.v1.ratings import router as ratings_router
from app.api.v1.disputes import router as disputes_router
from app.api.v1.storage import router as storage_router
from app.api.v1.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(campaigns_router)
api_router.include_router(applications_router)
api_router.include_router(collaborations_router)
api_router.include_router(recommendations_router)
api_router.include_router(messages_router)
api_router.include_router(ratings_router)
api_router.include_router(disputes_router)
api_router.include_router(storage_router)
api_router.include_router(webhooks_router)
