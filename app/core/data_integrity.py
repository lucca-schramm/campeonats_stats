"""Sistema de validação e integridade de dados"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from app.models.league import League
from app.models.team_statistics import TeamStatistics
from app.models.player import Player
from app.models.fixture import Fixture

logger = logging.getLogger(__name__)


class DataIntegrityChecker:
    """Classe para verificar e garantir integridade dos dados"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_league(self, league: League) -> tuple[bool, Optional[str]]:
        """Valida integridade de uma liga"""
        if not league.name or len(league.name.strip()) == 0:
            return False, "Nome da liga é obrigatório"
        
        if not league.country or len(league.country.strip()) == 0:
            return False, "País da liga é obrigatório"
        
        if league.season_id and league.season_id < 2000:
            return False, "Season ID inválido"
        
        return True, None
    
    def validate_team_statistics(self, stats: TeamStatistics) -> tuple[bool, Optional[str]]:
        """Valida integridade de estatísticas de time"""
        if stats.rank is not None and stats.rank < 1:
            return False, "Rank deve ser maior que zero"
        
        if stats.points is not None and stats.points < 0:
            return False, "Pontos não podem ser negativos"
        
        if stats.matches_played is not None and stats.matches_played < 0:
            return False, "Partidas jogadas não podem ser negativas"
        
        if stats.goals_for is not None and stats.goals_for < 0:
            return False, "Gols a favor não podem ser negativos"
        
        if stats.goals_against is not None and stats.goals_against < 0:
            return False, "Gols contra não podem ser negativos"
        
        if stats.wins is not None and stats.wins < 0:
            return False, "Vitórias não podem ser negativas"
        
        if stats.draws is not None and stats.draws < 0:
            return False, "Empates não podem ser negativos"
        
        if stats.losses is not None and stats.losses < 0:
            return False, "Derrotas não podem ser negativas"
        
        matches_total = (stats.wins or 0) + (stats.draws or 0) + (stats.losses or 0)
        if stats.matches_played is not None and matches_total > stats.matches_played:
            return False, "Soma de vitórias/empates/derrotas excede partidas jogadas"
        
        return True, None
    
    def validate_player(self, player: Player) -> tuple[bool, Optional[str]]:
        """Valida integridade de um jogador"""
        if not player.name or len(player.name.strip()) == 0:
            return False, "Nome do jogador é obrigatório"
        
        if player.goals is not None and player.goals < 0:
            return False, "Gols não podem ser negativos"
        
        if player.assists is not None and player.assists < 0:
            return False, "Assistências não podem ser negativas"
        
        if player.matches_played is not None and player.matches_played < 0:
            return False, "Partidas jogadas não podem ser negativas"
        
        return True, None
    
    def validate_fixture(self, fixture: Fixture) -> tuple[bool, Optional[str]]:
        """Valida integridade de uma partida"""
        if fixture.home_team_id == fixture.away_team_id:
            return False, "Time mandante e visitante não podem ser o mesmo"
        
        if fixture.home_goals is not None and fixture.home_goals < 0:
            return False, "Gols do mandante não podem ser negativos"
        
        if fixture.away_goals is not None and fixture.away_goals < 0:
            return False, "Gols do visitante não podem ser negativos"
        
        if fixture.status == "complete":
            if fixture.home_goals is None or fixture.away_goals is None:
                return False, "Partida completa deve ter placar definido"
        
        return True, None
    
    def check_data_consistency(self) -> Dict[str, Any]:
        """Verifica consistência geral dos dados no banco"""
        issues = []
        
        leagues = self.db.query(League).all()
        for league in leagues:
            valid, error = self.validate_league(league)
            if not valid:
                issues.append(f"Liga {league.id}: {error}")
        
        stats = self.db.query(TeamStatistics).all()
        for stat in stats:
            valid, error = self.validate_team_statistics(stat)
            if not valid:
                issues.append(f"Estatísticas time {stat.team_id}: {error}")
        
        players = self.db.query(Player).limit(100).all()
        for player in players:
            valid, error = self.validate_player(player)
            if not valid:
                issues.append(f"Jogador {player.id}: {error}")
        
        fixtures = self.db.query(Fixture).limit(100).all()
        for fixture in fixtures:
            valid, error = self.validate_fixture(fixture)
            if not valid:
                issues.append(f"Partida {fixture.id}: {error}")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "issues_found": len(issues),
            "issues": issues,
            "status": "ok" if len(issues) == 0 else "issues_found"
        }
