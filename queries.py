import sqlite3
import pandas as pd
from typing import List, Dict
import json
import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações da API FootyStats
API_BASE_URL = "https://api.football-data-api.com"
API_KEY = os.getenv("FOOTYSTATS_API_KEY")

class FootballAnalyzer:
    """Classe para análise dos dados de futebol com FootyStats API"""
    
    def __init__(self, db_name: str = "football_stats.db"):
        self.db_name = db_name
        self.api_key = API_KEY
    
    def get_connection(self):
        """Retorna conexão com o banco de dados"""
        return sqlite3.connect(self.db_name)
    
    def make_api_request(self, endpoint: str, params: dict = None) -> dict:
        """Faz requisição para a FootyStats API"""
        if params is None:
            params = {}
        
        params['key'] = self.api_key
        url = f"{API_BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para {url}: {e}")
            return {}
    
    def get_league_standings(self, league_id: int) -> pd.DataFrame:
        """Obtém a tabela de classificação de uma liga com estatísticas complementares"""
        query = """
        SELECT 
            t.name as team_name,
            ts.matches_played,
            ts.wins,
            ts.draws,
            ts.losses,
            ts.goals_for,
            ts.goals_against,
            ts.points,
            ts.rank,
            ROUND(CAST(ts.goals_for AS FLOAT) / ts.matches_played, 2) as avg_goals_for,
            ROUND(CAST(ts.goals_against AS FLOAT) / ts.matches_played, 2) as avg_goals_against,
            ROUND(CAST(ts.wins AS FLOAT) / ts.matches_played * 100, 2) as win_percentage
        FROM team_statistics ts
        JOIN teams t ON ts.team_id = t.id
        WHERE ts.league_id = ?
        ORDER BY ts.points DESC, (ts.goals_for - ts.goals_against) DESC
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id,))
        
        return df
    
    def get_team_btts_stats(self, league_id: int) -> pd.DataFrame:
        """Obtém estatísticas de BTTS (Both Teams To Score) para cada time"""
        query = """
        SELECT 
            t.name as team_name,
            COUNT(CASE WHEN f.home_goal_count > 0 AND f.away_goal_count > 0 
                      AND f.status = 'complete'
                      AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL 
                   THEN 1 END) as btts_matches,
            COUNT(CASE WHEN f.status = 'complete' AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL THEN 1 END) as total_matches,
            ROUND(CAST(COUNT(CASE WHEN f.home_goal_count > 0 AND f.away_goal_count > 0 
                                  AND f.status = 'complete'
                                  AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL 
                               THEN 1 END) AS FLOAT) / 
                  NULLIF(COUNT(CASE WHEN f.status = 'complete' AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL THEN 1 END), 0) * 100, 2) as btts_percentage
        FROM teams t
        LEFT JOIN fixtures f ON (t.id = f.home_team_id OR t.id = f.away_team_id) AND f.league_id = ?
        WHERE t.league_id = ?
        GROUP BY t.id, t.name
        ORDER BY btts_percentage DESC
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id, league_id))
        
        return df
    
    def get_team_corner_stats(self, league_id: int) -> pd.DataFrame:
        """Obtém estatísticas de escanteios para cada time"""
        query = """
        SELECT 
            t.name as team_name,
            AVG(CASE WHEN f.home_team_id = t.id THEN f.home_corners ELSE f.away_corners END) as avg_corners_per_game,
            SUM(CASE WHEN f.home_team_id = t.id THEN f.home_corners ELSE f.away_corners END) as total_corners,
            COUNT(f.id) as matches_with_stats
        FROM teams t
        LEFT JOIN fixtures f ON (f.home_team_id = t.id OR f.away_team_id = t.id) AND f.league_id = ? AND f.status = 'complete'
        WHERE t.league_id = ?
        GROUP BY t.id, t.name
        ORDER BY avg_corners_per_game DESC
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id, league_id))
        
        return df
    
    def get_top_scorers(self, league_id: int, limit: int = 10) -> pd.DataFrame:
        """Obtém os times com mais gols marcados"""
        query = """
        SELECT 
            t.name as team_name,
            ts.goals_for,
            ts.goals_against,
            (ts.goals_for - ts.goals_against) as goal_difference
        FROM team_statistics ts
        JOIN teams t ON ts.team_id = t.id
        WHERE ts.league_id = ?
        ORDER BY ts.goals_for DESC
        LIMIT ?
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id, limit))
        
        return df
    
    def get_high_scoring_matches(self, league_id: int, limit: int = 10) -> pd.DataFrame:
        """Obtém as partidas com mais gols"""
        query = """
        SELECT 
            ht.name as home_team,
            at.name as away_team,
            f.home_goal_count,
            f.away_goal_count,
            (f.home_goal_count + f.away_goal_count) as total_goals,
            f.date_unix,
            f.status
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.league_id = ?
        ORDER BY (f.home_goal_count + f.away_goal_count) DESC
        LIMIT ?
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id, limit))
        
        return df
    
    def get_team_performance_stats(self, league_id: int) -> pd.DataFrame:
        """Obtém estatísticas de performance dos times"""
        query = """
        SELECT 
            t.name as team_name,
            ts.matches_played,
            ROUND(CAST(ts.wins AS FLOAT) / ts.matches_played * 100, 2) as win_percentage,
            ROUND(CAST(ts.draws AS FLOAT) / ts.matches_played * 100, 2) as draw_percentage,
            ROUND(CAST(ts.losses AS FLOAT) / ts.matches_played * 100, 2) as loss_percentage,
            ROUND(CAST(ts.goals_for AS FLOAT) / ts.matches_played, 2) as goals_per_game,
            ROUND(CAST(ts.goals_against AS FLOAT) / ts.matches_played, 2) as goals_against_per_game
        FROM team_statistics ts
        JOIN teams t ON ts.team_id = t.id
        WHERE ts.league_id = ?
        ORDER BY ts.points DESC
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id,))
        
        return df
    
    def get_fixture_statistics_summary(self, league_id: int) -> pd.DataFrame:
        """Obtém resumo das estatísticas de partidas"""
        query = """
        SELECT 
            t.name as team_name,
            COUNT(f.id) as matches_with_stats,
            AVG(CASE WHEN f.home_team_id = t.id THEN f.home_shots_on_target ELSE f.away_shots_on_target END) as avg_shots_on_goal,
            AVG(CASE WHEN f.home_team_id = t.id THEN f.home_shots ELSE f.away_shots END) as avg_total_shots,
            AVG(CASE WHEN f.home_team_id = t.id THEN f.home_possession ELSE f.away_possession END) as avg_possession,
            AVG(CASE WHEN f.home_team_id = t.id THEN f.home_fouls ELSE f.away_fouls END) as avg_fouls,
            AVG(CASE WHEN f.home_team_id = t.id THEN f.home_yellow_cards ELSE f.away_yellow_cards END) as avg_yellow_cards,
            AVG(CASE WHEN f.home_team_id = t.id THEN f.home_red_cards ELSE f.away_red_cards END) as avg_red_cards,
            0 as avg_pass_accuracy
        FROM teams t
        LEFT JOIN fixtures f ON (f.home_team_id = t.id OR f.away_team_id = t.id) AND f.league_id = ? AND f.status = 'complete'
        WHERE t.league_id = ?
        GROUP BY t.id, t.name
        ORDER BY avg_shots_on_goal DESC
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id, league_id))
        
        return df
    
    def get_league_summary(self, league_id: int) -> Dict:
        """Obtém resumo geral de uma liga"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Informações básicas da liga
            cursor.execute("SELECT name, country FROM leagues WHERE id = ?", (league_id,))
            league_info = cursor.fetchone()
            
            # Número de times
            cursor.execute("SELECT COUNT(DISTINCT team_id) FROM team_statistics WHERE league_id = ?", (league_id,))
            num_teams = cursor.fetchone()[0]
            
            # Número de partidas
            cursor.execute("SELECT COUNT(*) FROM fixtures WHERE league_id = ?", (league_id,))
            num_fixtures = cursor.fetchone()[0]
            
            # Total de gols
            cursor.execute("SELECT SUM(home_goal_count + away_goal_count) FROM fixtures WHERE league_id = ?", (league_id,))
            total_goals = cursor.fetchone()[0] or 0
            
            # Média de gols por partida
            avg_goals = round(total_goals / num_fixtures, 2) if num_fixtures > 0 else 0
            
            # Time com mais pontos
            cursor.execute("""
                SELECT t.name, ts.points 
                FROM team_statistics ts 
                JOIN teams t ON ts.team_id = t.id 
                WHERE ts.league_id = ? 
                ORDER BY ts.points DESC 
                LIMIT 1
            """, (league_id,))
            top_team = cursor.fetchone()
            
            # Time com mais gols
            cursor.execute("""
                SELECT t.name, ts.goals_for 
                FROM team_statistics ts 
                JOIN teams t ON ts.team_id = t.id 
                WHERE ts.league_id = ? 
                ORDER BY ts.goals_for DESC 
                LIMIT 1
            """, (league_id,))
            top_scorer = cursor.fetchone()
        
        return {
            "league_name": league_info[0] if league_info else "N/A",
            "country": league_info[1] if league_info else "N/A",
            "num_teams": num_teams,
            "num_fixtures": num_fixtures,
            "total_goals": total_goals,
            "avg_goals_per_match": avg_goals,
            "top_team": {
                "name": top_team[0] if top_team else "N/A",
                "points": top_team[1] if top_team else 0
            },
            "top_scorer": {
                "name": top_scorer[0] if top_scorer else "N/A",
                "goals": top_scorer[1] if top_scorer else 0
            }
        }
    
    def get_available_leagues_from_api(self) -> List[Dict]:
        """Obtém ligas disponíveis diretamente da FootyStats API"""
        logger.info("🔍 Obtendo ligas disponíveis da FootyStats API...")
        
        params = {"chosen_leagues_only": "true"}
        data = self.make_api_request("league-list", params)
        
        leagues = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        logger.info(f"📋 Encontradas {len(leagues)} ligas disponíveis")
        
        return leagues
    
    def get_league_table_from_api(self, league_id: int, season: int = 2025) -> List[Dict]:
        """Obtém tabela de classificação diretamente da FootyStats API"""
        params = {"league_id": league_id, "season": season}
        data = self.make_api_request("league-table", params)
        
        return data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    
    def export_league_data(self, league_id: int, output_file: str):
        """Exporta dados de uma liga para JSON"""
        data = {
            "summary": self.get_league_summary(league_id),
            "standings": self.get_league_standings(league_id).to_dict('records'),
            "top_scorers": self.get_top_scorers(league_id).to_dict('records'),
            "high_scoring_matches": self.get_high_scoring_matches(league_id).to_dict('records'),
            "team_performance": self.get_team_performance_stats(league_id).to_dict('records'),
            "fixture_statistics": self.get_fixture_statistics_summary(league_id).to_dict('records')
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Dados exportados para {output_file}")

def calcular_estatisticas_complementares(league_id: int) -> List[Dict]:
    """Calcula estatísticas complementares para uma liga usando dados do banco local"""
    try:
        analyzer = FootballAnalyzer()
        
        # Obtém dados do banco de dados local
        standings_df = analyzer.get_league_standings(league_id)
        
        if standings_df.empty:
            logger.warning(f"Nenhuma tabela de classificação encontrada para liga {league_id}")
            return []
        
        result = []
        
        for _, row in standings_df.iterrows():
            team_name = row['team_name']
            matches_played = row['matches_played']
            wins = row['wins']
            draws = row['draws']
            losses = row['losses']
            goals_for = row['goals_for']
            goals_against = row['goals_against']
            points = row['points']
            rank = row['rank']
            goals_diff = goals_for - goals_against
            
            # Calcula aproveitamento
            aproveitamento = 0
            if matches_played > 0:
                max_points = matches_played * 3
                aproveitamento = round((points / max_points) * 100, 1)
            
            # Obtém estatísticas adicionais do banco
            with sqlite3.connect("football_stats.db") as conn:
                cursor = conn.cursor()
                
                # Busca o team_id pelo nome
                cursor.execute("SELECT id FROM teams WHERE name = ? AND league_id = ?", (team_name, league_id))
                team_result = cursor.fetchone()
                team_id = team_result[0] if team_result else None
                
                if team_id:
                    # BTTS Geral
                    btts_query = """
                    SELECT COUNT(*) as btts_matches
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND (f.home_team_id = ? OR f.away_team_id = ?)
                    AND f.status = 'complete'
                    AND f.home_goal_count > 0 AND f.away_goal_count > 0
                    AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL
                    """
                    cursor.execute(btts_query, (league_id, team_id, team_id))
                    btts_result = cursor.fetchone()
                    btts_matches = btts_result[0] if btts_result else 0
                    
                    # +2.5 gols (Jogos com 3 ou mais gols)
                    over_2_5_query = """
                    SELECT COUNT(*) as over_2_5_goals
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND (f.home_team_id = ? OR f.away_team_id = ?)
                    AND f.status = 'complete'
                    AND (COALESCE(f.home_goal_count, 0) + COALESCE(f.away_goal_count, 0)) >= 3
                    AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL
                    """
                    cursor.execute(over_2_5_query, (league_id, team_id, team_id))
                    over_2_5_result = cursor.fetchone()
                    over_2_5_goals = over_2_5_result[0] if over_2_5_result else 0
                    
                    # Clean sheets
                    clean_sheets_query = """
                    SELECT COUNT(*) as clean_sheets
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.status = 'complete'
                    AND (
                        (f.home_team_id = ? AND COALESCE(f.away_goal_count, 0) = 0) OR 
                        (f.away_team_id = ? AND COALESCE(f.home_goal_count, 0) = 0)
                    )
                    AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL
                    """
                    cursor.execute(clean_sheets_query, (league_id, team_id, team_id))
                    clean_sheets_result = cursor.fetchone()
                    clean_sheets = clean_sheets_result[0] if clean_sheets_result else 0
                else:
                    btts_matches = 0
                    over_2_5_goals = 0
                    clean_sheets = 0
            
            # Estrutura completa seguindo o padrão esperado
            team_dict = {
                "rank": rank,
                "team": {
                    "id": team_id,
                    "name": team_name,
                    "logo": ""
                },
                "points": points,
                "goalsDiff": goals_diff,
                "group": f"Liga {league_id} 2025",
                "form": "",
                "form_home": "",
                "form_visitor": "",
                "status": "same",
                "description": "",
                "all": {
                    "played": matches_played,
                    "win": wins,
                    "draw": draws,
                    "lose": losses,
                    "goals": {
                        "for": goals_for,
                        "against": goals_against
                    }
                },
                "home": {
                    "played": 0,
                    "win": 0,
                    "draw": 0,
                    "lose": 0,
                    "goals": {
                        "for": 0,
                        "against": 0
                    }
                },
                "away": {
                    "played": 0,
                    "win": 0,
                    "draw": 0,
                    "lose": 0,
                    "goals": {
                        "for": 0,
                        "against": 0
                    }
                },
                "update": "",
                # Estatísticas complementares
                "btts_matches": btts_matches,
                "over_2_5_goals": over_2_5_goals,
                "clean_sheets": clean_sheets,
                "aproveitamento": aproveitamento
            }
            result.append(team_dict)
        
        logger.info(f"✅ Estatísticas complementares calculadas para {len(result)} times")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas complementares para liga {league_id}: {e}")
        return []

def obter_artilharia(league_id: int) -> List[Dict]:
    """Obtém dados de artilharia da liga usando FootyStats API"""
    try:
        analyzer = FootballAnalyzer()
        
        # Tenta obter artilharia da API
        params = {"league_id": league_id, "season": 2025}
        data = analyzer.make_api_request("league-topscorers", params)
        
        artilharia = []
        scorers = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        
        for item in scorers:
            try:
                # Adapta os dados da FootyStats para o formato esperado
                artilharia.append({
                    "jogador-foto": item.get("player_image"),
                    "jogador-escudo": item.get("team_logo"),
                    "jogador-nome": item.get("player_name"),
                    "jogador-posicao": item.get("position", "N/A"),
                    "jogador-gols": item.get("goals", 0)
                })
            except Exception as e:
                logger.warning(f"Erro ao processar jogador na artilharia: {e}")
                continue
        
        # Ordena por número de gols (decrescente)
        artilharia.sort(key=lambda x: x["jogador-gols"], reverse=True)
        
        logger.info(f"Artilharia obtida para liga {league_id}: {len(artilharia)} jogadores")
        return artilharia
    except Exception as e:
        logger.error(f"Erro ao obter artilharia para liga {league_id}: {e}")
        return []

def main():
    """Função principal para demonstração das consultas com FootyStats"""
    analyzer = FootballAnalyzer()
    
    print("📊 ANÁLISE DE DADOS DE FUTEBOL - FootyStats API")
    print("=" * 50)
    
    # Obtém ligas disponíveis da API
    available_leagues = analyzer.get_available_leagues_from_api()
    
    if available_leagues:
        print(f"\n🏆 LIGAS DISPONÍVEIS NA API ({len(available_leagues)}):")
        for i, league in enumerate(available_leagues[:10], 1):  # Mostra apenas as primeiras 10
            league_id = league.get("id")
            league_name = league.get("name", "N/A")
            country = league.get("country", "N/A")
            print(f"{i}. ID: {league_id} - {league_name} ({country})")
        
        # Analisa a primeira liga como exemplo
        if available_leagues:
            first_league = available_leagues[0]
            league_id = first_league.get("id")
            
            print(f"\n📊 ANÁLISE DETALHADA - LIGA ID: {league_id}")
            print("-" * 30)
            
            # Resumo da liga
            summary = analyzer.get_league_summary(league_id)
            print(f"Liga: {summary['league_name']} ({summary['country']})")
            print(f"Times: {summary['num_teams']}")
            print(f"Partidas: {summary['num_fixtures']}")
            print(f"Total de gols: {summary['total_goals']}")
            print(f"Média de gols por partida: {summary['avg_goals_per_match']}")
            
            # Exportar dados
            output_file = f"footystats_league_{league_id}_data.json"
            analyzer.export_league_data(league_id, output_file)
    else:
        print("❌ Nenhuma liga encontrada na API. Verifique sua chave de API.")

if __name__ == "__main__":
    main()
