import sqlite3
import pandas as pd
from typing import List, Dict
import json

class FootballAnalyzer:
    """Classe para análise dos dados de futebol"""
    
    def __init__(self, db_name: str = "football_stats.db"):
        self.db_name = db_name
    
    def get_connection(self):
        """Retorna conexão com o banco de dados"""
        return sqlite3.connect(self.db_name)
    
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
            COUNT(CASE WHEN f.home_goals > 0 AND f.away_goals > 0 THEN 1 END) as btts_matches,
            COUNT(*) as total_matches,
            ROUND(CAST(COUNT(CASE WHEN f.home_goals > 0 AND f.away_goals > 0 THEN 1 END) AS FLOAT) / COUNT(*) * 100, 2) as btts_percentage
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
            AVG(fs.corner_kicks) as avg_corners_per_game,
            SUM(fs.corner_kicks) as total_corners,
            COUNT(fs.fixture_id) as matches_with_stats
        FROM teams t
        LEFT JOIN fixture_statistics fs ON t.id = fs.team_id
        LEFT JOIN fixtures f ON fs.fixture_id = f.id AND f.league_id = ?
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
            f.home_goals,
            f.away_goals,
            (f.home_goals + f.away_goals) as total_goals,
            f.date,
            f.status
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.league_id = ?
        ORDER BY (f.home_goals + f.away_goals) DESC
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
            COUNT(fs.fixture_id) as matches_with_stats,
            AVG(fs.shots_on_goal) as avg_shots_on_goal,
            AVG(fs.total_shots) as avg_total_shots,
            AVG(fs.ball_possession) as avg_possession,
            AVG(fs.fouls) as avg_fouls,
            AVG(fs.yellow_cards) as avg_yellow_cards,
            AVG(fs.red_cards) as avg_red_cards,
            AVG(fs.passes_percentage) as avg_pass_accuracy
        FROM fixture_statistics fs
        JOIN teams t ON fs.team_id = t.id
        JOIN fixtures f ON fs.fixture_id = f.id
        WHERE f.league_id = ?
        GROUP BY t.id, t.name
        ORDER BY avg_shots_on_goal DESC
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(league_id,))
        
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
            cursor.execute("SELECT SUM(home_goals + away_goals) FROM fixtures WHERE league_id = ?", (league_id,))
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

def main():
    """Função principal para demonstração das consultas"""
    analyzer = FootballAnalyzer()
    
    # Lista de ligas disponíveis
    leagues = [71, 72, 78]  # Serie A, Serie B, Bundesliga
    
    print("📊 ANÁLISE DE DADOS DE FUTEBOL")
    print("=" * 50)
    
    for league_id in leagues:
        print(f"\n🏆 LIGA ID: {league_id}")
        print("-" * 30)
        
        # Resumo da liga
        summary = analyzer.get_league_summary(league_id)
        print(f"Liga: {summary['league_name']} ({summary['country']})")
        print(f"Times: {summary['num_teams']}")
        print(f"Partidas: {summary['num_fixtures']}")
        print(f"Total de gols: {summary['total_goals']}")
        print(f"Média de gols por partida: {summary['avg_goals_per_match']}")
        print(f"Líder: {summary['top_team']['name']} ({summary['top_team']['points']} pts)")
        print(f"Maior artilheiro: {summary['top_scorer']['name']} ({summary['top_scorer']['goals']} gols)")
        
        # Top 5 da tabela
        standings = analyzer.get_league_standings(league_id)
        print(f"\n🏅 TOP 5 DA TABELA:")
        for i, row in standings.head().iterrows():
            print(f"{row['rank']}. {row['team_name']} - {row['points']} pts (Média: {row['avg_goals_for']} gols/jogo)")
        
        # Estatísticas BTTS
        btts_stats = analyzer.get_team_btts_stats(league_id)
        print(f"\n⚽ TIMES COM MAIS PARTIDAS BTTS (Both Teams To Score):")
        for i, row in btts_stats.head().iterrows():
            print(f"{i+1}. {row['team_name']} - {row['btts_matches']} partidas ({row['btts_percentage']}%)")
        
        # Estatísticas de escanteios
        corner_stats = analyzer.get_team_corner_stats(league_id)
        print(f"\n🔄 TIMES COM MAIS ESCANTEIOS POR JOGO:")
        for i, row in corner_stats.head().iterrows():
            print(f"{i+1}. {row['team_name']} - {row['avg_corners_per_game']} escanteios/jogo")
        
        # Exportar dados
        output_file = f"league_{league_id}_data.json"
        analyzer.export_league_data(league_id, output_file)

if __name__ == "__main__":
    main()
