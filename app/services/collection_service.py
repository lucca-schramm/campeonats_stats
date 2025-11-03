"""Serviço inteligente de coleta de dados"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.fixture import Fixture
from app.models.league import League
import logging

logger = logging.getLogger(__name__)


class CollectionService:
    """Serviço para determinar quando coletar dados"""
    
    # Status de partidas que indicam necessidade de atualização
    ACTIVE_STATUSES = ['live', '1h', '2h', 'ht', 'et', 'p']
    COMPLETED_STATUSES = ['complete', 'finished', 'ft']
    
    def __init__(self, db: Session):
        self.db = db
    
    def should_collect_league(self, league_id: int) -> bool:
        """Verifica se uma liga precisa de coleta baseado em jogos"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=30)
        window_end = now + timedelta(hours=2)
        
        # Busca jogos próximos ou ao vivo desta liga
        fixtures = self.db.query(Fixture).filter(
            and_(
                Fixture.league_id == league_id,
                or_(
                    # Jogos ao vivo ou em andamento
                    Fixture.status.in_(self.ACTIVE_STATUSES),
                    # Jogos agendados nas próximas 2 horas
                    and_(
                        Fixture.status == 'scheduled',
                        Fixture.date_unix.isnot(None),
                        Fixture.date_unix <= int(window_end.timestamp()),
                        Fixture.date_unix >= int(window_start.timestamp())
                    ),
                    # Jogos finalizados nas últimas 30 min (atualizar resultado final)
                    and_(
                        Fixture.status.in_(self.COMPLETED_STATUSES),
                        Fixture.date_unix.isnot(None),
                        Fixture.date_unix >= int(window_start.timestamp())
                    )
                )
            )
        ).limit(1).first()
        
        return fixtures is not None
    
    def get_leagues_to_collect(self) -> List[int]:
        """Retorna IDs de ligas que precisam de coleta"""
        leagues = self.db.query(League.id).all()
        return [league_id for league_id, in leagues 
                if self.should_collect_league(league_id)]
    
    def get_fixtures_to_update(self, league_id: Optional[int] = None) -> List[int]:
        """Retorna IDs de partidas que precisam atualização"""
        now = datetime.utcnow()
        window_start = now - timedelta(hours=1)
        window_end = now + timedelta(hours=2)
        
        query = self.db.query(Fixture.id).filter(
            or_(
                Fixture.status.in_(self.ACTIVE_STATUSES),
                and_(
                    Fixture.status == 'scheduled',
                    Fixture.date_unix.isnot(None),
                    Fixture.date_unix <= int(window_end.timestamp()),
                    Fixture.date_unix >= int(window_start.timestamp())
                )
            )
        )
        
        if league_id:
            query = query.filter(Fixture.league_id == league_id)
        
        return [fixture_id for fixture_id, in query.all()]
    
    def get_collection_priority(self) -> dict:
        """Retorna prioridades de coleta otimizada"""
        now = datetime.utcnow()
        
        # Jogos ao vivo: alta prioridade
        live = self.db.query(Fixture.league_id).filter(
            Fixture.status.in_(self.ACTIVE_STATUSES)
        ).distinct().all()
        
        # Jogos próximos (próximas 30min): média prioridade
        window_end = now + timedelta(minutes=30)
        upcoming = self.db.query(Fixture.league_id).filter(
            and_(
                Fixture.status == 'scheduled',
                Fixture.date_unix.isnot(None),
                Fixture.date_unix <= int(window_end.timestamp()),
                Fixture.date_unix >= int(now.timestamp())
            )
        ).distinct().all()
        
        return {
            'high': [lid for lid, in live],
            'medium': [lid for lid, in upcoming if lid not in [lid for lid, in live]],
            'low': []  # Outras ligas (coleta periódica)
        }

