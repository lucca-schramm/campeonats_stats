"""Serviço para monitoramento e atualização de partidas ao vivo"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.fixture import Fixture
from app.models.league import League
import logging

logger = logging.getLogger(__name__)


class LiveMatchService:
    """Serviço para gerenciar partidas ao vivo e em tempo real"""
    
    # Status que indicam partida ao vivo
    LIVE_STATUSES = ['live', '1h', '2h', 'ht', 'et', 'p', 'inprogress']
    # Status que indicam partida agendada (próxima a começar)
    UPCOMING_STATUSES = ['scheduled', 'notstarted']
    # Status que indicam partida finalizada recentemente
    RECENTLY_FINISHED_STATUSES = ['complete', 'finished', 'ft', 'aet', 'pen']
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_live_matches(self, league_id: Optional[int] = None) -> List[Fixture]:
        """Retorna todas as partidas ao vivo"""
        query = self.db.query(Fixture).filter(
            Fixture.status.in_(self.LIVE_STATUSES)
        )
        
        if league_id:
            query = query.filter(Fixture.league_id == league_id)
        
        return query.all()
    
    def get_upcoming_matches(self, minutes_ahead: int = 30, league_id: Optional[int] = None) -> List[Fixture]:
        """Retorna partidas que começam nas próximas X minutos"""
        now = datetime.utcnow()
        window_end = now + timedelta(minutes=minutes_ahead)
        
        query = self.db.query(Fixture).filter(
            and_(
                Fixture.status.in_(self.UPCOMING_STATUSES),
                Fixture.date_unix.isnot(None),
                Fixture.date_unix >= int(now.timestamp()),
                Fixture.date_unix <= int(window_end.timestamp())
            )
        )
        
        if league_id:
            query = query.filter(Fixture.league_id == league_id)
        
        return query.all()
    
    def get_recently_finished_matches(self, minutes_ago: int = 30, league_id: Optional[int] = None) -> List[Fixture]:
        """Retorna partidas finalizadas recentemente (para atualizar resultado final)"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=minutes_ago)
        
        query = self.db.query(Fixture).filter(
            and_(
                Fixture.status.in_(self.RECENTLY_FINISHED_STATUSES),
                Fixture.date_unix.isnot(None),
                Fixture.date_unix >= int(window_start.timestamp())
            )
        )
        
        if league_id:
            query = query.filter(Fixture.league_id == league_id)
        
        return query.all()
    
    def get_matches_to_update(self, league_id: Optional[int] = None) -> List[Fixture]:
        """Retorna todas as partidas que precisam atualização (ao vivo, próximas, ou recém finalizadas)"""
        live = self.get_live_matches(league_id)
        upcoming = self.get_upcoming_matches(league_id=league_id)
        finished = self.get_recently_finished_matches(league_id=league_id)
        
        # Combina todas e remove duplicatas
        all_matches = {match.id: match for match in live + upcoming + finished}
        return list(all_matches.values())
    
    def get_leagues_with_live_matches(self) -> List[int]:
        """Retorna IDs de ligas que têm partidas ao vivo"""
        live_matches = self.get_live_matches()
        league_ids = list(set([match.league_id for match in live_matches]))
        return league_ids
    
    def get_match_update_summary(self) -> Dict:
        """Retorna resumo de partidas que precisam atualização"""
        live = self.get_live_matches()
        upcoming = self.get_upcoming_matches()
        finished = self.get_recently_finished_matches()
        
        leagues_with_live = self.get_leagues_with_live_matches()
        
        return {
            "live_matches": len(live),
            "upcoming_matches": len(upcoming),
            "recently_finished": len(finished),
            "total_to_update": len(live) + len(upcoming) + len(finished),
            "leagues_with_live": len(leagues_with_live),
            "league_ids": leagues_with_live,
            "matches": [
                {
                    "id": m.id,
                    "league_id": m.league_id,
                    "home": m.home_team_name,
                    "away": m.away_team_name,
                    "status": m.status,
                    "score": f"{m.home_goal_count}-{m.away_goal_count}"
                }
                for m in live[:10]  # Limita a 10 para não sobrecarregar
            ]
        }

