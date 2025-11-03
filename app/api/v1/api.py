"""Router principal da API v1"""
from fastapi import APIRouter
from app.api.v1.endpoints import leagues, chatbot, webhooks, data_integrity, collection

api_router = APIRouter()

api_router.include_router(leagues.router, prefix="/leagues", tags=["leagues"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(data_integrity.router, prefix="/data-integrity", tags=["data-integrity"])
api_router.include_router(collection.router, prefix="/collect", tags=["collection"])

