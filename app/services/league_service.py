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
    
    async def get_standings(self, league_id: int, season_id: Optional[int] = None, filter_type: str = "geral") -> List[dict]:
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
            
            if filter_type == "geral":
                matches_played = stats.matches_played or 0
                wins = stats.wins or 0
                draws = stats.draws or 0
                losses = stats.losses or 0
                goals_for = stats.goals_for or 0
                goals_against = stats.goals_against or 0
                points = stats.points or 0
                
                fixture_filter = or_(
                    Fixture.home_team_id == team_id,
                    Fixture.away_team_id == team_id
                )
            elif filter_type == "casa":
                home_query = select(
                    func.count(Fixture.id).label('matches'),
                    func.sum(case((Fixture.home_goal_count > Fixture.away_goal_count, 1), else_=0)).label('wins'),
                    func.sum(case((Fixture.home_goal_count == Fixture.away_goal_count, 1), else_=0)).label('draws'),
                    func.sum(case((Fixture.home_goal_count < Fixture.away_goal_count, 1), else_=0)).label('losses'),
                    func.sum(Fixture.home_goal_count).label('goals_for'),
                    func.sum(Fixture.away_goal_count).label('goals_against')
                ).filter(
                    and_(
                        Fixture.league_id == league_id,
                        Fixture.season_id == stats_season_id,
                        Fixture.home_team_id == team_id,
                        Fixture.status == 'complete'
                    )
                )
                home_result = await self.db.execute(home_query)
                home_row = home_result.first()
                
                matches_played = home_row.matches or 0 if home_row else 0
                wins = home_row.wins or 0 if home_row else 0
                draws = home_row.draws or 0 if home_row else 0
                losses = home_row.losses or 0 if home_row else 0
                goals_for = home_row.goals_for or 0 if home_row else 0
                goals_against = home_row.goals_against or 0 if home_row else 0
                points = (wins * 3) + (draws * 1)
                
                fixture_filter = Fixture.home_team_id == team_id
            else:
                away_query = select(
                    func.count(Fixture.id).label('matches'),
                    func.sum(case((Fixture.away_goal_count > Fixture.home_goal_count, 1), else_=0)).label('wins'),
                    func.sum(case((Fixture.away_goal_count == Fixture.home_goal_count, 1), else_=0)).label('draws'),
                    func.sum(case((Fixture.away_goal_count < Fixture.home_goal_count, 1), else_=0)).label('losses'),
                    func.sum(Fixture.away_goal_count).label('goals_for'),
                    func.sum(Fixture.home_goal_count).label('goals_against')
                ).filter(
                    and_(
                        Fixture.league_id == league_id,
                        Fixture.season_id == stats_season_id,
                        Fixture.away_team_id == team_id,
                        Fixture.status == 'complete'
                    )
                )
                away_result = await self.db.execute(away_query)
                away_row = away_result.first()
                
                matches_played = away_row.matches or 0 if away_row else 0
                wins = away_row.wins or 0 if away_row else 0
                draws = away_row.draws or 0 if away_row else 0
                losses = away_row.losses or 0 if away_row else 0
                goals_for = away_row.goals_for or 0 if away_row else 0
                goals_against = away_row.goals_against or 0 if away_row else 0
                points = (wins * 3) + (draws * 1)
                
                fixture_filter = Fixture.away_team_id == team_id
            
            base_filter = and_(
                Fixture.league_id == league_id,
                Fixture.season_id == stats_season_id,
                Fixture.status == 'complete',
                fixture_filter
            )
            
            over25_query = select(func.count(Fixture.id)).filter(
                and_(base_filter, Fixture.total_goal_count > 2)
            )
            over25_result = await self.db.execute(over25_query)
            over25_goals = over25_result.scalar() or 0
            
            btts_query = select(func.count(Fixture.id)).filter(
                and_(base_filter, Fixture.btts == True)
            )
            btts_result = await self.db.execute(btts_query)
            btts = btts_result.scalar() or 0
            
            if filter_type == "casa":
                clean_sheets_filter = and_(base_filter, Fixture.away_goal_count == 0)
            elif filter_type == "fora":
                clean_sheets_filter = and_(base_filter, Fixture.home_goal_count == 0)
            else:
                clean_sheets_filter = and_(
                    base_filter,
                    or_(
                        and_(Fixture.home_team_id == team_id, Fixture.away_goal_count == 0),
                        and_(Fixture.away_team_id == team_id, Fixture.home_goal_count == 0)
                    )
                )
            
            clean_sheets_query = select(func.count(Fixture.id)).filter(clean_sheets_filter)
            clean_sheets_result = await self.db.execute(clean_sheets_query)
            clean_sheets = clean_sheets_result.scalar() or 0
            
            over05_ht_query = select(func.count(Fixture.id)).filter(
                and_(base_filter, Fixture.over05 == True)
            )
            over05_ht_result = await self.db.execute(over05_ht_query)
            over05_ht = over05_ht_result.scalar() or 0
            over05_ft = over05_ht
            
            corners_query = select(
                func.sum(
                    case(
                        (Fixture.home_team_id == team_id, Fixture.home_corners),
                        else_=Fixture.away_corners
                    )
                )
            ).filter(base_filter)
            corners_result = await self.db.execute(corners_query)
            total_corners = corners_result.scalar() or 0
            avg_corners = round(total_corners / matches_played, 1) if matches_played > 0 else 0
            
            form_query = select(Fixture).filter(base_filter).order_by(Fixture.date_unix.desc()).limit(5)
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
            
            while len(form) < 5:
                form.append('-')
            
            standings.append({
                "rank": stats.rank or 0,
                "team_id": stats.team_id,
                "name": team.name if team else f"Time {stats.team_id}",
                "logo": team.image if team and team.image else "",
                "points": points,
                "matches_played": matches_played,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goals_diff": goals_for - goals_against,
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

