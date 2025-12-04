"""Service de Chatbot"""
import re
from typing import Optional, Dict, List, Union
from app.core.database import SessionLocal
from app.services.league_service import LeagueService
from app.models.team import Team
from app.models.team_statistics import TeamStatistics
from app.models.fixture import Fixture
from app.models.player import Player
from sqlalchemy import or_, and_, func


class ChatbotService:
    """
    Service para processar mensagens do chatbot - Restrito a futebol e estatísticas
    
    NOTA: Este chatbot é baseado em regras (rule-based), não utiliza LLM (Large Language Model).
    Todas as respostas são geradas através de padrões e lógica pré-definida.
    Para implementar um chatbot com LLM, seria necessário integrar com serviços como OpenAI, 
    Anthropic ou modelos locais via LangChain.
    """
    
    def __init__(self):
        self.greetings = ['oi', 'olá', 'hello', 'hi', 'hey']
        self.help_patterns = [
            r'help', r'ajuda', r'comandos', r'o que você pode fazer'
        ]
        
        # Palavras-chave relacionadas a futebol
        self.football_keywords = [
            'futebol', 'football', 'soccer', 'liga', 'league', 'time', 'team', 'clube',
            'jogador', 'player', 'partida', 'match', 'jogo', 'game', 'gol', 'goal',
            'tabela', 'standings', 'classificação', 'artilheiro', 'scorer', 'goleador',
            'estatística', 'stat', 'estatísticas', 'stats', 'dados', 'brasileirão',
            'brasileiro', 'campeonato', 'championship', 'temporada', 'season',
            'vitória', 'win', 'derrota', 'loss', 'empate', 'draw', 'pontos', 'points',
            'confronto', 'fixture', 'comparar', 'compare', 'comparação', 'comparison'
        ]
        
        # Assuntos proibidos (respostas curtas)
        self.off_topic_keywords = [
            'filme', 'movie', 'música', 'music', 'política', 'politics', 'notícia',
            'news', 'tempo', 'weather', 'clima', 'receita', 'recipe', 'cozinha',
            'cooking', 'viagem', 'travel', 'programação', 'programming', 'código',
            'code', 'python', 'javascript', 'outros esportes', 'other sports',
            'basquete', 'basketball', 'vôlei', 'volleyball', 'tênis', 'tennis'
        ]
    
    def process_message(self, message: str, chatbot_type: str = "simple") -> str:
        """Processa mensagem e retorna resposta"""
        if chatbot_type == "llm":
            return self._process_with_llm(message)
        else:
            return self._process_simple(message)
    
    def _is_football_related(self, message: str) -> bool:
        """Verifica se a mensagem é relacionada a futebol"""
        message_lower = message.lower()
        
        # Verifica se contém palavras-chave de futebol
        has_football_keywords = any(keyword in message_lower for keyword in self.football_keywords)
        
        # Verifica se contém palavras proibidas (assuntos off-topic)
        has_off_topic = any(keyword in message_lower for keyword in self.off_topic_keywords)
        
        # Se tem palavras off-topic e não tem futebol, rejeita
        if has_off_topic and not has_football_keywords:
            return False
        
        # Aceita se tem palavras de futebol OU é cumprimento/ajuda (casos especiais)
        if has_football_keywords:
            return True
        
        # Permite cumprimentos e ajuda
        if any(greeting in message_lower for greeting in self.greetings):
            return True
        if any(re.search(pattern, message_lower) for pattern in self.help_patterns):
            return True
        
        return False
    
    def _process_simple(self, message: str) -> str:
        """Processa mensagem com bot simples baseado em regras - Restrito a futebol"""
        message_lower = message.lower().strip()
        
        # VALIDAÇÃO: Bloqueia assuntos fora de futebol
        if not self._is_football_related(message):
            return (
                "Desculpe, sou especializado apenas em estatísticas de futebol e informações sobre ligas.\n"
                "Por favor, faça perguntas sobre:\n"
                "- Tabelas de classificação\n"
                "- Artilheiros\n"
                "- Estatísticas de times\n"
                "- Partidas e confrontos\n"
                "- Comparações entre times\n\n"
                "Digite 'ajuda' para ver todos os comandos disponíveis."
            )
        
        # Cumprimentos
        if any(greeting in message_lower for greeting in self.greetings):
            return self._get_greeting_response()
        
        # Ajuda
        if any(re.search(pattern, message_lower) for pattern in self.help_patterns):
            return self._get_help_response()
        
        # Buscar classificação
        if re.search(r'(classifica|tabela|standings)', message_lower):
            league_name = self._extract_league_name(message)
            league_id = self._extract_league_id(message)  # Também aceita ID para compatibilidade
            resolved_id = self._resolve_league(league_name) if league_name else league_id
            if resolved_id:
                return self._get_standings_response(resolved_id, league_name)
            return "Por favor, especifique o nome da liga. Ex: 'Tabela do Brasileirão' ou 'Classificação da Premier League'"
        
        # Buscar artilheiros
        if re.search(r'(artilh|goleador|top scorer)', message_lower):
            league_name = self._extract_league_name(message)
            league_id = self._extract_league_id(message)  # Também aceita ID para compatibilidade
            resolved_id = self._resolve_league(league_name) if league_name else league_id
            if resolved_id:
                return self._get_top_scorers_response(resolved_id, league_name)
            return "Por favor, especifique o nome da liga. Ex: 'Artilheiros do Brasileirão'"
        
        # Buscar liga
        if re.search(r'(liga|league)', message_lower):
            league_name = self._extract_league_name(message)
            if league_name:
                return self._search_league_response(league_name)
        
        # Buscar time
        if re.search(r'(time|team|clube)', message_lower):
            team_name = self._extract_team_name(message)
            league_name = self._extract_league_name(message)
            league_id = self._extract_league_id(message)
            resolved_id = self._resolve_league(league_name) if league_name else league_id
            if team_name or resolved_id:
                return self._get_team_info_response(team_name, resolved_id)
        
        # Buscar partidas
        if re.search(r'(partida|jogo|match|fixture|confronto)', message_lower):
            league_name = self._extract_league_name(message)
            league_id = self._extract_league_id(message)
            resolved_id = self._resolve_league(league_name) if league_name else league_id
            return self._get_recent_matches_response(resolved_id)
        
        # Comparar times
        if re.search(r'(comparar|comparison|diferença)', message_lower):
            return self._compare_teams_response(message)
        
        # Estatísticas gerais
        if re.search(r'(estatística|stat|dados|informação)', message_lower):
            league_name = self._extract_league_name(message)
            league_id = self._extract_league_id(message)
            resolved_id = self._resolve_league(league_name) if league_name else league_id
            return self._get_league_stats_response(resolved_id, league_name)
        
        return "Desculpe, não entendi. Digite 'ajuda' para ver os comandos disponíveis."
    
    def _process_with_llm(self, message: str) -> str:
        """Processa mensagem com RAG (Retrieval-Augmented Generation)"""
        # RAG será processado de forma async no endpoint
        # Este método é apenas placeholder - o endpoint chama diretamente o RAG service
        return "Processando com RAG..."
    
    def _extract_league_id(self, message: str) -> Optional[int]:
        """Extrai ID de liga da mensagem"""
        numbers = re.findall(r'\d+', message)
        if numbers:
            return int(numbers[0])
        return None
    
    def _extract_league_name(self, message: str) -> Optional[str]:
        """Extrai nome de liga da mensagem"""
        message_lower = message.lower()
        
        # Padrões comuns de ligas
        league_patterns = {
            'brasileirão': ['brasileirão', 'brasileiro', 'serie a', 'série a'],
            'premier league': ['premier league', 'premier', 'inglês', 'inglês'],
            'la liga': ['la liga', 'espanhol', 'espanhola'],
            'serie a': ['serie a', 'italiano', 'italiana'],
            'bundesliga': ['bundesliga', 'alemão', 'alemã'],
            'ligue 1': ['ligue 1', 'francês', 'francesa'],
            'championship': ['championship', 'segunda divisão inglesa'],
        }
        
        # Tenta encontrar padrões conhecidos
        for league_name, patterns in league_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    return league_name
        
        # Tenta extrair texto após palavras-chave de liga
        import re
        patterns = [
            r'(?:liga|league|campeonato|championship)\s+([a-záéíóúâêôãõç\s]+?)(?:\s|$|,|\.)',
            r'([a-záéíóúâêôãõç\s]+?)\s+(?:liga|league|campeonato)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                league_name = match.group(1).strip()
                # Remove palavras comuns que não fazem parte do nome
                stop_words = ['da', 'do', 'de', 'o', 'a', 'os', 'as', 'tabela', 'classificação', 'estatísticas']
                words = [w for w in league_name.split() if w not in stop_words]
                if words:
                    return ' '.join(words)
        
        return None
    
    def _resolve_league(self, league_name_or_id: Optional[Union[str, int]]) -> Optional[int]:
        """Resolve nome ou ID de liga para ID"""
        if league_name_or_id is None:
            return None
        
        # Se já é um número (ID), retorna direto
        if isinstance(league_name_or_id, int):
            return league_name_or_id
        
        # Se é string, tenta buscar por nome
        try:
            db = SessionLocal()
            try:
                service = LeagueService(db)
                league = service.get_league_by_name(league_name_or_id)
                if league:
                    return league.id
                return None
            finally:
                db.close()
        except Exception:
            return None
    
    def _get_greeting_response(self) -> str:
        return (
            "Olá! 👋 Sou assistente especializado em estatísticas de futebol.\n"
            "Posso ajudar com:\n"
            "• Tabelas de classificação\n"
            "• Artilheiros\n"
            "• Estatísticas de times\n"
            "• Partidas recentes\n"
            "• Comparações entre times\n\n"
            "Digite 'ajuda' para ver comandos."
        )
    
    def _get_help_response(self) -> str:
        return (
            "📋 Comandos disponíveis:\n\n"
            "🏆 Classificação:\n"
            "• Tabela do Brasileirão\n"
            "• Classificação da Premier League\n"
            "• Tabela de classificação\n\n"
            "⚽ Artilheiros:\n"
            "• Artilheiros do Brasileirão\n"
            "• Top scorers da Premier League\n"
            "• Goleadores da La Liga\n\n"
            "🔍 Buscar Liga:\n"
            "• Buscar liga Brasileirão\n"
            "• Liga Premier League\n"
            "• Mostrar ligas disponíveis\n\n"
            "⚽ Informações de Time:\n"
            "• Time Flamengo\n"
            "• Estatísticas do Palmeiras\n"
            "• Time Corinthians do Brasileirão\n\n"
            "🎮 Partidas:\n"
            "• Partidas recentes do Brasileirão\n"
            "• Últimos jogos da Premier League\n\n"
            "📊 Estatísticas:\n"
            "• Estatísticas do Brasileirão\n"
            "• Dados da Premier League\n\n"
            "💬 Faça uma pergunta sobre futebol usando o nome da liga!"
        )
    
    def _get_standings_response(self, league_id: int, league_name: Optional[str] = None) -> str:
        """Resposta otimizada - apenas top 5 para economizar tokens"""
        try:
            db = SessionLocal()
            try:
                service = LeagueService(db)
                
                # Obtém nome da liga se não foi fornecido
                if not league_name:
                    league = service.get_league_by_id(league_id)
                    league_name = league.name if league else f"Liga {league_id}"
                
                standings = service.get_standings(league_id)
                
                if not standings:
                    return f"Nenhuma classificação encontrada para {league_name}"
                
                response = f"🏆 Top 5 - {league_name}:\n"
                for standing in standings[:5]:
                    response += f"{standing['rank']}º - {standing['points']}pts\n"
                
                if len(standings) > 5:
                    response += f"\n(Total: {len(standings)} times)"
                
                return response
            finally:
                db.close()
        except Exception as e:
            return f"Erro: {str(e)}"
    
    def _get_top_scorers_response(self, league_id: int, league_name: Optional[str] = None) -> str:
        """Resposta otimizada - apenas top 5 para economizar tokens"""
        try:
            db = SessionLocal()
            try:
                service = LeagueService(db)
                
                # Obtém nome da liga se não foi fornecido
                if not league_name:
                    league = service.get_league_by_id(league_id)
                    league_name = league.name if league else f"Liga {league_id}"
                
                scorers = service.get_top_scorers(league_id)
                
                if not scorers:
                    return f"Nenhum artilheiro encontrado para {league_name}"
                
                response = f"⚽ Top 5 - {league_name}:\n"
                for i, scorer in enumerate(scorers[:5], 1):
                    response += (
                        f"{i}º {scorer['jogador-nome']} - "
                        f"{scorer['jogador-gols']} gols\n"
                    )
                
                if len(scorers) > 5:
                    response += f"\n(Total: {len(scorers)} artilheiros)"
                
                return response
            finally:
                db.close()
        except Exception as e:
            return f"Erro: {str(e)}"
    
    def _search_league_response(self, league_name: str) -> str:
        try:
            db = SessionLocal()
            try:
                service = LeagueService(db)
                leagues = service.search_leagues(league_name, limit=5)
                
                if not leagues:
                    return f"Nenhuma liga encontrada com o nome '{league_name}'"
                
                response = f"Ligas encontradas ({len(leagues)}):\n"
                for league in leagues[:5]:  # Limita a 5
                    response += f"• {league.name} (ID: {league.id})\n"
                
                if len(leagues) > 5:
                    response += f"\n(Mostrando 5 de {len(leagues)})"
                
                return response
            finally:
                db.close()
        except Exception as e:
            return f"Erro ao buscar ligas: {str(e)}"
    
    def _extract_team_name(self, message: str) -> Optional[str]:
        """Extrai nome de time da mensagem"""
        # Padrões comuns de nomes de times brasileiros
        teams_map = {
            'flamengo': 'Flamengo',
            'palmeiras': 'Palmeiras',
            'corinthians': 'Corinthians',
            'são paulo': 'São Paulo',
            'santos': 'Santos',
            'gremio': 'Grêmio',
            'internacional': 'Internacional',
            'fluminense': 'Fluminense',
            'botafogo': 'Botafogo',
            'vasco': 'Vasco',
            'atletico': 'Atlético',
            'cruzeiro': 'Cruzeiro'
        }
        
        message_lower = message.lower()
        for key, value in teams_map.items():
            if key in message_lower:
                return value
        return None
    
    def _get_team_info_response(self, team_name: Optional[str], league_id: Optional[int]) -> str:
        """Obtém informações sobre um time"""
        try:
            db = SessionLocal()
            try:
                query = db.query(TeamStatistics).join(Team)
                
                if league_id:
                    query = query.filter(TeamStatistics.league_id == league_id)
                
                if team_name:
                    query = query.filter(or_(
                        Team.name.ilike(f'%{team_name}%'),
                        Team.clean_name.ilike(f'%{team_name}%')
                    ))
                
                stats = query.order_by(TeamStatistics.rank.asc()).limit(1).first()
                
                if not stats:
                    return "Time não encontrado. Verifique o nome ou ID da liga."
                
                team = stats.team
                aproveitamento = round((stats.points / (stats.matches_played * 3)) * 100) if stats.matches_played > 0 else 0
                
                # Resposta compacta para economizar tokens
                response = f"⚽ {team.name} (Liga {stats.league_id})\n"
                response += f"{stats.rank}º lugar - {stats.points}pts\n"
                response += f"J: {stats.matches_played} | "
                response += f"V: {stats.wins} | E: {stats.draws} | D: {stats.losses}\n"
                response += f"GP: {stats.goals_for} | GC: {stats.goals_against} | "
                response += f"SG: {stats.goals_for - stats.goals_against}\n"
                response += f"Aproveitamento: {aproveitamento}%"
                
                return response
            finally:
                db.close()
        except Exception as e:
            return f"Erro ao buscar informações do time: {str(e)}"
    
    def _get_recent_matches_response(self, league_id: Optional[int]) -> str:
        """Obtém partidas recentes"""
        try:
            db = SessionLocal()
            try:
                query = db.query(Fixture).filter(Fixture.status == 'FT')
                
                if league_id:
                    query = query.filter(Fixture.league_id == league_id)
                
                matches = query.order_by(Fixture.date_unix.desc()).limit(5).all()
                
                if not matches:
                    return "Nenhuma partida recente encontrada."
                
                # Resposta compacta - apenas 3 últimas partidas
                response = f"🎮 Últimas 3 partidas:\n"
                for match in matches[:3]:
                    response += (
                        f"{match.home_team_name} {match.home_goal_count}x"
                        f"{match.away_goal_count} {match.away_team_name}\n"
                    )
                
                return response
            finally:
                db.close()
        except Exception as e:
            return f"Erro ao buscar partidas: {str(e)}"
    
    def _compare_teams_response(self, message: str) -> str:
        """Compara dois times"""
        # Extrai nomes de times da mensagem
        teams = []
        teams_map = {
            'flamengo': 'Flamengo',
            'palmeiras': 'Palmeiras',
            'corinthians': 'Corinthians',
            'são paulo': 'São Paulo',
            'santos': 'Santos',
            'gremio': 'Grêmio'
        }
        
        message_lower = message.lower()
        for key, value in teams_map.items():
            if key in message_lower and value not in teams:
                teams.append(value)
        
        if len(teams) < 2:
            return "Por favor, mencione dois times para comparar. Ex: 'Comparar Flamengo e Palmeiras liga 123'"
        
        try:
            db = SessionLocal()
            try:
                team1_stats = db.query(TeamStatistics).join(Team).filter(
                    Team.name.ilike(f'%{teams[0]}%')
                ).first()
                
                team2_stats = db.query(TeamStatistics).join(Team).filter(
                    Team.name.ilike(f'%{teams[1]}%')
                ).first()
                
                if not team1_stats or not team2_stats:
                    return "Um ou ambos os times não foram encontrados."
                
                # Resposta compacta
                response = f"📊 {team1_stats.team.name} vs {team2_stats.team.name}\n"
                response += f"Pos: {team1_stats.rank}º vs {team2_stats.rank}º\n"
                response += f"Pts: {team1_stats.points} vs {team2_stats.points}\n"
                response += f"GP: {team1_stats.goals_for} vs {team2_stats.goals_for}\n"
                response += f"GC: {team1_stats.goals_against} vs {team2_stats.goals_against}"
                
                return response
            finally:
                db.close()
        except Exception as e:
            return f"Erro ao comparar times: {str(e)}"
    
    def _get_league_stats_response(self, league_id: Optional[int], league_name: Optional[str] = None) -> str:
        """Obtém estatísticas gerais da liga"""
        try:
            db = SessionLocal()
            try:
                if not league_id:
                    return "Por favor, especifique o nome da liga. Ex: 'Estatísticas do Brasileirão'"
                
                service = LeagueService(db)
                
                # Obtém nome da liga se não foi fornecido
                if not league_name:
                    league = service.get_league_by_id(league_id)
                    league_name = league.name if league else f"Liga {league_id}"
                
                # Total de times
                total_teams = db.query(TeamStatistics).filter(
                    TeamStatistics.league_id == league_id
                ).count()
                
                # Total de partidas
                total_matches = db.query(Fixture).filter(
                    Fixture.league_id == league_id,
                    Fixture.status == 'FT'
                ).count()
                
                # Total de gols
                total_goals = db.query(func.sum(Fixture.total_goal_count)).filter(
                    Fixture.league_id == league_id,
                    Fixture.status == 'FT'
                ).scalar() or 0
                
                # Média de gols por partida
                avg_goals = round(total_goals / total_matches, 2) if total_matches > 0 else 0
                
                # Resposta compacta
                response = f"📊 {league_name}:\n"
                response += f"Times: {total_teams} | Partidas: {total_matches}\n"
                response += f"Total gols: {total_goals} | Média: {avg_goals} gols/jogo"
                
                return response
            finally:
                db.close()
        except Exception as e:
            return f"Erro ao buscar estatísticas: {str(e)}"

