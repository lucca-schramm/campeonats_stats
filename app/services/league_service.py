"""Service de Liga (Async)"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.league import League
from app.models.team_statistics import TeamStatistics
from app.models.player import Player
from app.repositories.league_repository import LeagueRepository


class LeagueService:
    """Service async para operações com ligas"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = LeagueRepository(db)
    
    async def get_all_leagues(self, skip: int = 0, limit: int = 100) -> List[League]:
        """Obtém todas as ligas"""
        return await self.repository.get_all(skip=skip, limit=limit)
    
    async def get_league_by_id(self, league_id: int) -> Optional[League]:
        """Obtém liga por ID"""
        return await self.repository.get_by_id(league_id)
    
    async def get_league_by_name(self, name: str) -> Optional[League]:
        """Obtém liga por nome"""
        return await self.repository.get_by_name(name)
    
    async def search_leagues(self, query: str, limit: int = 10) -> List[League]:
        """Busca ligas por nome"""
        return await self.repository.search_by_name(query, limit)
    
    async def get_standings(self, league_id: int, season_id: Optional[int] = None) -> List[dict]:
        """Obtém tabela de classificação com informações completas dos times e estatísticas avançadas"""
        from app.models.team import Team
        from app.models.fixture import Fixture
        from sqlalchemy import func, case, and_, or_
        
        query = (
            select(TeamStatistics, Team)
            .join(Team, TeamStatistics.team_id == Team.id)
            .filter(TeamStatistics.league_id == league_id)
        )
        
        if season_id:
            query = query.filter(TeamStatistics.season_id == season_id)
        
        query = query.order_by(TeamStatistics.rank.asc(), TeamStatistics.points.desc())
        result = await self.db.execute(query)
        rows = result.all()
        
        standings = []
        for stats, team in rows:
            team_id = stats.team_id
            stats_season_id = stats.season_id
            
            # Calcula estatísticas avançadas a partir dos fixtures
            # Over 2.5 goals (jogos com 3+ gols)
            over25_query = select(func.count(Fixture.id)).filter(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == stats_season_id,
                    Fixture.status == 'complete',
                    or_(
                        and_(Fixture.home_team_id == team_id, Fixture.total_goal_count > 2),
                        and_(Fixture.away_team_id == team_id, Fixture.total_goal_count > 2)
                    )
                )
            )
            over25_result = await self.db.execute(over25_query)
            over25_goals = over25_result.scalar() or 0
            
            # BTTS (Both Teams To Score)
            btts_query = select(func.count(Fixture.id)).filter(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == stats_season_id,
                    Fixture.status == 'complete',
                    Fixture.btts == True,
                    or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id
                    )
                )
            )
            btts_result = await self.db.execute(btts_query)
            btts = btts_result.scalar() or 0
            
            # Clean Sheets (sem sofrer gol)
            clean_sheets_query = select(func.count(Fixture.id)).filter(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == stats_season_id,
                    Fixture.status == 'complete',
                    or_(
                        and_(Fixture.home_team_id == team_id, Fixture.away_goal_count == 0),
                        and_(Fixture.away_team_id == team_id, Fixture.home_goal_count == 0)
                    )
                )
            )
            clean_sheets_result = await self.db.execute(clean_sheets_query)
            clean_sheets = clean_sheets_result.scalar() or 0
            
            # Over 0.5 goals 1ºT (gols no primeiro tempo)
            # Nota: Como não temos dados de gols por tempo, vamos usar uma aproximação
            # Assumindo que se houve gol na partida, pode ter sido no 1ºT
            over05_ht_query = select(func.count(Fixture.id)).filter(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == stats_season_id,
                    Fixture.status == 'complete',
                    Fixture.over05 == True,
                    or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id
                    )
                )
            )
            over05_ht_result = await self.db.execute(over05_ht_query)
            over05_ht = over05_ht_result.scalar() or 0
            
            # Over 0.5 goals 2ºT (mesma lógica)
            over05_ft = over05_ht  # Aproximação: se teve gol, pode ter sido em qualquer tempo
            
            # Média de escanteios por jogo
            corners_query = select(
                func.sum(
                    case(
                        (Fixture.home_team_id == team_id, Fixture.home_corners),
                        else_=Fixture.away_corners
                    )
                )
            ).filter(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == stats_season_id,
                    Fixture.status == 'complete',
                    or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id
                    )
                )
            )
            corners_result = await self.db.execute(corners_query)
            total_corners = corners_result.scalar() or 0
            avg_corners = round(total_corners / (stats.matches_played or 1), 1) if stats.matches_played > 0 else 0
            
            # Forma (últimos 5 jogos: V=Vitória, E=Empate, D=Derrota)
            form_query = select(Fixture).filter(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == stats_season_id,
                    Fixture.status == 'complete',
                    or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id
                    )
                )
            ).order_by(Fixture.date_unix.desc()).limit(5)
            form_result = await self.db.execute(form_query)
            form_fixtures = form_result.scalars().all()
            
            form = []
            for fixture in form_fixtures:
                if fixture.home_team_id == team_id:
                    if fixture.home_goal_count > fixture.away_goal_count:
                        form.append('V')
                    elif fixture.home_goal_count == fixture.away_goal_count:
                        form.append('E')
                    else:
                        form.append('D')
                else:
                    if fixture.away_goal_count > fixture.home_goal_count:
                        form.append('V')
                    elif fixture.away_goal_count == fixture.home_goal_count:
                        form.append('E')
                    else:
                        form.append('D')
            
            # Completa com '-' se não houver 5 jogos
            while len(form) < 5:
                form.append('-')
            
            standings.append({
                "rank": stats.rank or 0,
                "team_id": stats.team_id,
                "name": team.name if team else f"Time {stats.team_id}",
                "logo": team.image if team and team.image else "",
                "points": stats.points or 0,
                "matches_played": stats.matches_played or 0,
                "wins": stats.wins or 0,
                "draws": stats.draws or 0,
                "losses": stats.losses or 0,
                "goals_for": stats.goals_for or 0,
                "goals_against": stats.goals_against or 0,
                "goals_diff": (stats.goals_for or 0) - (stats.goals_against or 0),
                # Estatísticas avançadas
                "over25Goals": over25_goals,
                "btts": btts,
                "cleanSheets": clean_sheets,
                "over05HT": over05_ht,
                "over05FT": over05_ft,
                "avgCorners": avg_corners,
                "form": form
            })
        
        return standings
    
    async def get_top_scorers(self, league_id: int, limit: int = 20) -> List[dict]:
        """Obtém artilheiros da liga com informações completas"""
        from app.models.team import Team
        
        result = await self.db.execute(
            select(Player, Team)
            .join(Team, Player.team_id == Team.id, isouter=True)
            .filter(Player.league_id == league_id, Player.goals > 0)
            .order_by(Player.goals.desc(), Player.assists.desc())
            .limit(limit)
        )
        rows = result.all()
        
        scorers = []
        for player, team in rows:
            # Gera URL da foto do jogador
            player_photo = ""
            if player.url:
                try:
                    url_parts = player.url.split('/')
                    if len(url_parts) >= 6 and url_parts[3] == 'players':
                        nationality = url_parts[4]
                        url_player_name = url_parts[5]
                        player_photo = f"https://cdn.footystats.org/img/players/{nationality}-{url_player_name}.png"
                except:
                    pass
            
            if not player_photo:
                player_photo = f"https://cdn.footystats.org/img/players/-{player.name.lower().replace(' ', '-')}.png"
            
            scorers.append({
                "jogador-nome": player.name,
                "jogador-posicao": player.position or "N/A",
                "jogador-gols": player.goals or 0,
                "jogador-assists": player.assists or 0,
                "jogador-partidas": player.matches_played or 0,
                "jogador-escudo": team.image if team and team.image else "",
                "jogador-foto": player_photo
            })
        
        return scorers

