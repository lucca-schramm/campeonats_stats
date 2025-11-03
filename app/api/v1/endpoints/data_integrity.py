"""Endpoint de verificação de integridade de dados"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.data_integrity import DataIntegrityChecker

router = APIRouter()


@router.get("/check")
async def check_data_integrity(db: Session = Depends(get_db)):
    """Verifica integridade dos dados no banco"""
    checker = DataIntegrityChecker(db)
    result = checker.check_data_consistency()
    return result
