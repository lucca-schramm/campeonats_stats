"""Router principal da API v1"""
from fastapi import APIRouter
from app.api.v1.endpoints import leagues, chatbot, webhooks, collection, live_matches, monitoring, data_integrity

api_router = APIRouter()

api_router.include_router(leagues.router, prefix="/leagues", tags=["leagues"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(collection.router, prefix="/collect", tags=["collection"])
api_router.include_router(live_matches.router, prefix="/live-matches", tags=["live-matches"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(data_integrity.router, prefix="/data-integrity", tags=["data-integrity"])

