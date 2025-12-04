"""Serviço RAG (Retrieval-Augmented Generation) para Chatbot com DeepSeek"""
import os
import json
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from app.core.database import SessionLocal
from app.models.league import League
from app.models.team import Team
from app.models.team_statistics import TeamStatistics
from app.models.fixture import Fixture
from app.models.player import Player
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RAGService:
    """Serviço RAG para interagir com banco de dados via linguagem natural usando DeepSeek"""
    
    def __init__(self):
        """Inicializa o serviço RAG"""
        self.llm = None
        self.conversation_history: Dict[str, List[BaseMessage]] = {}  # Histórico por sessão
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Inicializa LLM com DeepSeek"""
        try:
            # Prioriza DeepSeek, fallback para OpenAI
            api_key = settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY
            
            if not api_key:
                logger.warning("Nenhuma API key configurada (DEEPSEEK_API_KEY ou OPENAI_API_KEY). RAG funcionará em modo limitado.")
                return
            
            # Configura DeepSeek se disponível
            if settings.DEEPSEEK_API_KEY:
                base_url = settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com/v1"
                # Garante que a URL termina com /v1
                if not base_url.endswith("/v1"):
                    base_url = base_url.rstrip("/") + "/v1"
                
                self.llm = ChatOpenAI(
                    model=settings.CHATBOT_MODEL or "deepseek-chat",
                    temperature=settings.CHATBOT_TEMPERATURE or 0.7,
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=base_url
                )
                logger.info(f"RAG Service inicializado com DeepSeek (modelo: {settings.CHATBOT_MODEL}, base_url: {base_url})")
            else:
                # Fallback para OpenAI
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    api_key=settings.OPENAI_API_KEY
                )
                logger.info("RAG Service inicializado com OpenAI (fallback)")
                
        except Exception as e:
            logger.error(f"Erro ao inicializar RAG Service: {e}")
            self.llm = None
    
    async def process_query(self, query: str, db: AsyncSession, session_id: Optional[str] = None) -> str:
        """
        Processa query do usuário usando RAG com contexto conversacional:
        1. Analisa a intenção da pergunta
        2. Busca dados relevantes no banco
        3. Gera resposta usando LLM com contexto e histórico
        """
        if not self.llm:
            return await self._fallback_response(query, db)
        
        try:
            # 1. Analisa intenção e extrai entidades
            intent = await self._analyze_intent(query)
            logger.info(f"Intenção detectada: {intent}")
            
            # Adiciona query_text às entidades para uso em comparação e outras análises
            if "entities" not in intent:
                intent["entities"] = {}
            intent["entities"]["query_text"] = query.lower()
            
            # 2. Busca dados relevantes no banco
            context_data = await self._retrieve_data(intent, query, db)
            logger.info(f"Dados recuperados: {len(context_data)} registros")
            
            # 3. Gera resposta usando LLM com histórico conversacional
            response = await self._generate_response(query, intent, context_data, session_id)
            
            # 4. Atualiza histórico da conversa
            if session_id:
                self._update_conversation_history(session_id, query, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao processar query RAG: {e}", exc_info=True)
            return await self._fallback_response(query, db)
    
    def _update_conversation_history(self, session_id: str, user_query: str, ai_response: str):
        """Atualiza histórico de conversa para contexto - OTIMIZADO para economia de tokens"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        # Adiciona mensagens ao histórico
        self.conversation_history[session_id].append(HumanMessage(content=user_query))
        
        # Trunca resposta do AI se muito longa (economia de tokens no histórico)
        max_response_length = 500
        truncated_response = ai_response[:max_response_length] + "..." if len(ai_response) > max_response_length else ai_response
        self.conversation_history[session_id].append(AIMessage(content=truncated_response))
        
        # Limita histórico baseado na configuração (padrão: 2 interações = 4 mensagens)
        max_messages = settings.CHATBOT_MAX_HISTORY_MESSAGES or 4
        if len(self.conversation_history[session_id]) > max_messages:
            self.conversation_history[session_id] = self.conversation_history[session_id][-max_messages:]
    
    def clear_conversation_history(self, session_id: str):
        """Limpa histórico de uma sessão"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
    
    async def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """Analisa a intenção da pergunta usando LLM - OTIMIZADO com cache e validação prévia"""
        try:
            # Primeiro valida se é sobre futebol (fallback rápido - economia de tokens)
            if not self._is_football_related(query):
                return {"intent": "off_topic", "entities": {}, "filters": {}}
            
            # Para greetings e help simples, pula análise LLM (economia de tokens)
            # MAS só se NÃO tiver palavras-chave importantes de futebol
            if settings.CHATBOT_SKIP_INTENT_ANALYSIS_IF_SIMPLE:
                query_lower = query.lower().strip()
                has_important_keywords = any(word in query_lower for word in [
                    'estatística', 'estatísticas', 'tabela', 'artilh', 'liga', 'brasileirão', 
                    'time', 'partida', 'jogo', 'gols', 'pontos', 'classificação', 'jogador', 'jogadores'
                ])
                
                # Só trata como greeting se NÃO tiver palavras-chave importantes E for muito curto
                if not has_important_keywords and len(query_lower.split()) <= 3:
                    if any(word in query_lower for word in ['oi', 'olá', 'hello', 'hi', 'hey', 'eae', 'e aí', 'tudo bem']):
                        return {"intent": "greeting", "entities": {}, "filters": {}}
                
                if any(word in query_lower for word in ['ajuda', 'help', 'comandos', 'o que você pode', 'o que pode']):
                    return {"intent": "help", "entities": {}, "filters": {}}
            
            # Prompt otimizado e mais curto (economia de tokens)
            prompt = f"""Analise a pergunta sobre futebol e retorne JSON:

"{query}"

Retorne JSON: {{"intent": "standings|scorers|team_info|match_info|league_stats|comparison|general|off_topic", "entities": {{"league_name": "...", "team_name": "..."}}, "filters": {{"limit": 10}}}}

Se não for futebol: intent="off_topic". Apenas JSON, sem markdown."""

            # Prompt do sistema mais curto (economia de tokens)
            messages = [
                SystemMessage(content="Analise intenções sobre futebol. Retorne apenas JSON válido."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            response_text = response.content.strip()
            
            # Remove markdown code blocks se presente
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            intent_data = json.loads(response_text.strip())
            return intent_data
            
        except Exception as e:
            logger.error(f"Erro ao analisar intenção: {e}")
            # Fallback: análise simples por palavras-chave
            return self._simple_intent_analysis(query)
    
    def _is_football_related(self, query: str) -> bool:
        """Verifica se a pergunta é sobre futebol"""
        query_lower = query.lower().strip()
        
        # Greetings e help são sempre permitidos
        if any(word in query_lower for word in ['oi', 'olá', 'hello', 'hi', 'hey', 'eae', 'e aí', 'tudo bem', 'ajuda', 'help']):
            return True
        
        # Palavras-chave de futebol
        football_keywords = ['futebol', 'football', 'soccer', 'liga', 'league', 'time', 'team', 'clube', 
                            'jogador', 'player', 'partida', 'match', 'jogo', 'game', 'gol', 'goal',
                            'tabela', 'standings', 'classificação', 'artilheiro', 'scorer', 'goleador',
                            'estatística', 'stat', 'brasileirão', 'brasileiro', 'campeonato', 'championship',
                            'vitória', 'win', 'derrota', 'loss', 'empate', 'draw', 'pontos', 'points',
                            'confronto', 'fixture', 'comparar', 'compare', 'flamengo', 'palmeiras', 'corinthians',
                            'são paulo', 'santos', 'fluminense', 'botafogo', 'atlético', 'cruzeiro', 'grêmio',
                            'internacional', 'premier', 'bundesliga', 'champions', 'serie a', 'serie b']
        
        return any(keyword in query_lower for keyword in football_keywords)
    
    def _simple_intent_analysis(self, query: str) -> Dict[str, Any]:
        """Análise simples de intenção por palavras-chave (fallback) - MELHORADA"""
        query_lower = query.lower().strip()
        
        # Greetings (mas não se tiver outras palavras importantes - verifica ANTES de outras intenções)
        # Se tiver palavras de futebol/estatísticas, não é só greeting
        has_football_keywords = any(word in query_lower for word in [
            'estatística', 'estatísticas', 'tabela', 'artilh', 'liga', 'brasileirão', 
            'time', 'partida', 'jogo', 'gols', 'pontos', 'classificação', 'jogador', 'jogadores'
        ])
        
        # Só trata como greeting se NÃO tiver palavras-chave importantes E for muito curto
        if not has_football_keywords and len(query_lower.split()) <= 3:
            if any(word in query_lower for word in ['oi', 'olá', 'hello', 'hi', 'hey', 'eae', 'e aí']):
                return {"intent": "greeting", "entities": {}, "filters": {}}
        
        # Help
        if any(word in query_lower for word in ['ajuda', 'help', 'comandos', 'o que você pode', 'o que pode']):
            return {"intent": "help", "entities": {}, "filters": {}}
        
        intent = "general"
        entities = {}
        
        # PRIORIDADE: Detecta "estatísticas" primeiro (pode ser league_stats ou team_info)
        if any(word in query_lower for word in ['estatística', 'estatísticas', 'stats', 'dados']):
            # Se menciona liga/campeonato, é league_stats
            if any(word in query_lower for word in ['liga', 'league', 'campeonato', 'brasileirão', 'brasileiro', 'serie a', 'serie b']):
                intent = "league_stats"
            # Se menciona time, é team_info
            elif any(word in query_lower for word in ['time', 'team', 'clube', 'flamengo', 'palmeiras', 'corinthians']):
                intent = "team_info"
            else:
                # Por padrão, se tem "estatísticas" e menciona liga, assume league_stats
                intent = "league_stats"
        
        # Detecta intenção específica
        elif any(word in query_lower for word in ['tabela', 'classificação', 'standings', 'posição', 'ranking']):
            intent = "standings"
        elif any(word in query_lower for word in ['artilh', 'goleador', 'scorer', 'gols', 'quem fez mais gols', 'jogador', 'jogadores', 'players']):
            intent = "scorers"
        elif any(word in query_lower for word in ['time', 'team', 'clube']):
            intent = "team_info"
        elif any(word in query_lower for word in ['partida', 'jogo', 'match', 'confronto', 'resultado']):
            intent = "match_info"
        elif any(word in query_lower for word in ['comparar', 'comparison', 'vs', 'versus', 'x']):
            intent = "comparison"
        elif any(word in query_lower for word in ['liga', 'league', 'campeonato']):
            intent = "league_stats"
        
        # Extrai entidades com mapeamento melhorado de sinônimos
        # Brasileirão / Serie A
        if any(term in query_lower for term in ['brasileirão', 'brasileiro', 'serie a', 'série a', 'serie-a', 'brasil série a']):
            entities['league_name'] = 'Serie A'  # Nome exato no banco
            entities['league_synonyms'] = ['Brasileirão', 'Brasileiro', 'Serie A', 'Série A']
        
        # Serie B
        if 'serie b' in query_lower or 'série b' in query_lower:
            entities['league_name'] = 'Serie B'
        
        # Premier League
        if 'premier' in query_lower:
            entities['league_name'] = 'Premier League'
        
        # Bundesliga
        if 'bundesliga' in query_lower:
            entities['league_name'] = 'Bundesliga'
        
        # Champions League
        if 'champions' in query_lower:
            entities['league_name'] = 'Champions League'
        
            # Extrai nomes de times comuns (múltiplos times para comparação)
            common_teams = {
                'flamengo': 'Flamengo', 'palmeiras': 'Palmeiras', 'corinthians': 'Corinthians',
                'são paulo': 'São Paulo', 'santos': 'Santos', 'fluminense': 'Fluminense',
                'botafogo': 'Botafogo', 'atlético': 'Atlético', 'cruzeiro': 'Cruzeiro',
                'grêmio': 'Grêmio', 'internacional': 'Internacional', 'athletico': 'Athletico',
                'atletico': 'Atlético', 'atletico mineiro': 'Atlético Mineiro', 'atletico mg': 'Atlético Mineiro'
            }
            found_teams = []
            for key, value in common_teams.items():
                if key in query_lower:
                    if value not in found_teams:
                        found_teams.append(value)
            
            if len(found_teams) >= 2:
                entities['team1_name'] = found_teams[0]
                entities['team2_name'] = found_teams[1]
            elif len(found_teams) == 1:
                entities['team_name'] = found_teams[0]
        
        return {"intent": intent, "entities": entities, "filters": {}}
    
    async def _retrieve_data(self, intent: Dict[str, Any], query: str, db: AsyncSession) -> List[Dict]:
        """Busca dados relevantes no banco de dados baseado na intenção - MELHORADO com fallback"""
        intent_type = intent.get("intent", "general")
        entities = intent.get("entities", {})
        filters = intent.get("filters", {})
        
        context_data = []
        
        try:
            if intent_type == "standings":
                context_data = await self._retrieve_standings(entities, filters, db)
                # Se não encontrou dados, tenta buscar ligas disponíveis
                if not context_data and not entities.get("league_name"):
                    logger.info("Standings sem league_name, buscando ligas disponíveis...")
                    context_data = await self._retrieve_general_data(query, db)
            elif intent_type == "scorers":
                context_data = await self._retrieve_scorers(entities, filters, db)
                # Se não encontrou dados, tenta buscar ligas disponíveis
                if not context_data:
                    logger.info("Scorers sem dados, buscando ligas disponíveis...")
                    context_data = await self._retrieve_general_data(query, db)
            elif intent_type == "team_info":
                context_data = await self._retrieve_team_info(entities, filters, db)
            elif intent_type == "match_info":
                context_data = await self._retrieve_matches(entities, filters, db)
            elif intent_type == "league_stats":
                context_data = await self._retrieve_league_stats(entities, filters, db)
                # Se não encontrou dados específicos, tenta buscar standings como fallback
                if not context_data or (len(context_data) == 1 and "available_leagues" in context_data[0]):
                    # Tenta buscar standings da liga se disponível
                    league_id = await self._resolve_league_id(entities.get("league_name"), entities.get("league_id"), db)
                    if league_id:
                        logger.info(f"Buscando standings como fallback para league_stats (liga {league_id})...")
                        standings_data = await self._retrieve_standings(entities, filters, db)
                        if standings_data:
                            context_data = standings_data
            elif intent_type == "comparison":
                context_data = await self._retrieve_comparison_data(entities, filters, db)
            else:
                # Busca geral: tenta encontrar ligas
                context_data = await self._retrieve_general_data(query, db)
                
        except Exception as e:
            logger.error(f"Erro ao recuperar dados: {e}", exc_info=True)
        
        return context_data
    
    async def _retrieve_standings(self, entities: Dict, filters: Dict, db: AsyncSession) -> List[Dict]:
        """Recupera dados de classificação"""
        league_id = await self._resolve_league_id(entities.get("league_name"), entities.get("league_id"), db)
        
        if not league_id:
            return []
        
        try:
            from app.services.league_service import LeagueService
            service = LeagueService(db)
            standings = await service.get_standings(league_id)
            
            # Converte para formato esperado
            return [
                {
                    "rank": s.get("rank", 0),
                    "team_id": s.get("team_id", 0),
                    "team_name": s.get("name", f"Time {s.get('team_id', 0)}"),
                    "points": s.get("points", 0),
                    "matches_played": s.get("matches_played", 0),
                    "wins": s.get("wins", 0),
                    "draws": s.get("draws", 0),
                    "losses": s.get("losses", 0),
                    "goals_for": s.get("goals_for", 0),
                    "goals_against": s.get("goals_against", 0),
                    "goals_diff": s.get("goals_diff", 0)
                }
                for s in standings
            ]
        except Exception as e:
            logger.error(f"Erro ao recuperar standings: {e}", exc_info=True)
            return []
    
    async def _retrieve_scorers(self, entities: Dict, filters: Dict, db: AsyncSession) -> List[Dict]:
        """Recupera dados de artilheiros - MELHORADO com fallback quando não tem league_id"""
        league_id = await self._resolve_league_id(entities.get("league_name"), entities.get("league_id"), db)
        
        try:
            from app.services.league_service import LeagueService
            service = LeagueService(db)
            
            # Se não tem league_id, busca artilheiros de todas as ligas disponíveis
            if not league_id:
                logger.info("Scorers sem league_id, buscando de todas as ligas...")
                # Busca ligas disponíveis
                result = await db.execute(select(League).limit(5))
                leagues = result.scalars().all()
                
                all_scorers = []
                for league in leagues:
                    try:
                        scorers = await service.get_top_scorers(league.id, 5)  # Top 5 de cada liga
                        for s in scorers:
                            all_scorers.append({
                                "player_name": s.get("jogador-nome", "N/A"),
                                "team_name": s.get("jogador-escudo", ""),
                                "goals": s.get("jogador-gols", 0),
                                "assists": s.get("jogador-assists", 0),
                                "matches_played": s.get("jogador-partidas", 0),
                                "position": s.get("jogador-posicao", "N/A"),
                                "league_name": league.name
                            })
                    except:
                        continue
                
                # Ordena por gols e limita
                all_scorers.sort(key=lambda x: x.get("goals", 0), reverse=True)
                limit = filters.get("limit", settings.CHATBOT_MAX_CONTEXT_ITEMS or 10)
                return all_scorers[:limit]
            
            # Limita para economia de tokens (top 10 por padrão)
            limit = filters.get("limit", settings.CHATBOT_MAX_CONTEXT_ITEMS or 10)
            scorers = await service.get_top_scorers(league_id, limit)
            
            # Converte para formato esperado
            return [
                {
                    "player_name": s.get("jogador-nome", "N/A"),
                    "team_name": s.get("jogador-escudo", ""),  # Nome do time se disponível
                    "goals": s.get("jogador-gols", 0),
                    "assists": s.get("jogador-assists", 0),
                    "matches_played": s.get("jogador-partidas", 0),
                    "position": s.get("jogador-posicao", "N/A")
                }
                for s in scorers
            ]
        except Exception as e:
            logger.error(f"Erro ao recuperar scorers: {e}", exc_info=True)
            return []
    
    async def _retrieve_team_info(self, entities: Dict, filters: Dict, db: AsyncSession) -> List[Dict]:
        """Recupera informações de time"""
        team_name = entities.get("team_name")
        league_id = await self._resolve_league_id(entities.get("league_name"), entities.get("league_id"), db)
        
        query = select(TeamStatistics, Team).join(Team, TeamStatistics.team_id == Team.id)
        
        if league_id:
            query = query.filter(TeamStatistics.league_id == league_id)
        
        if team_name:
            query = query.filter(or_(
                Team.name.ilike(f'%{team_name}%'),
                Team.clean_name.ilike(f'%{team_name}%')
            ))
        
        query = query.order_by(TeamStatistics.rank.asc()).limit(5)
        
        result = await db.execute(query)
        rows = result.all()
        
        teams = []
        for stats, team in rows:
            aproveitamento = round((stats.points / (stats.matches_played * 3)) * 100) if stats.matches_played > 0 else 0
            teams.append({
                "team_name": team.name if team else f"Time {stats.team_id}",
                "league_id": stats.league_id,
                "rank": stats.rank or 0,
                "points": stats.points or 0,
                "matches_played": stats.matches_played or 0,
                "wins": stats.wins or 0,
                "draws": stats.draws or 0,
                "losses": stats.losses or 0,
                "goals_for": stats.goals_for or 0,
                "goals_against": stats.goals_against or 0,
                "goals_diff": (stats.goals_for or 0) - (stats.goals_against or 0),
                "aproveitamento": aproveitamento
            })
        
        return teams
    
    async def _retrieve_matches(self, entities: Dict, filters: Dict, db: AsyncSession) -> List[Dict]:
        """Recupera informações de partidas - CORRIGIDO para incluir partidas futuras"""
        from datetime import datetime
        
        league_id = await self._resolve_league_id(entities.get("league_name"), entities.get("league_id"), db)
        
        # Determina se busca partidas futuras ou passadas baseado na query
        query_text = entities.get("query_text", "").lower() if hasattr(entities, 'get') else ""
        search_upcoming = any(word in query_text for word in ['próxima', 'próximas', 'futura', 'futuras', 'vem', 'vindas', 'agendada', 'agendadas'])
        
        # Status de partidas futuras/agendadas
        upcoming_statuses = ['incomplete', 'scheduled', 'notstarted', 'ns', 'tbd', 'postponed']
        completed_statuses = ['complete', 'finished', 'ft', 'aet', 'pen']
        
        query = select(Fixture)
        
        if search_upcoming:
            # Busca partidas futuras/agendadas
            now_timestamp = int(datetime.utcnow().timestamp())
            query = query.filter(
                or_(
                    Fixture.status.in_(upcoming_statuses),
                    and_(
                        Fixture.status.in_(completed_statuses),
                        Fixture.date_unix.isnot(None),
                        Fixture.date_unix > now_timestamp  # Partidas com data futura mesmo com status complete (adiadas)
                    )
                )
            ).order_by(Fixture.date_unix.asc())  # Ordena por data crescente (próximas primeiro)
        else:
            # Busca partidas passadas/completas
            query = query.filter(Fixture.status.in_(completed_statuses))
            query = query.order_by(Fixture.date_unix.desc())  # Ordena por data decrescente (mais recentes primeiro)
        
        if league_id:
            query = query.filter(Fixture.league_id == league_id)
        
        query = query.limit(20)  # Aumenta limite para ter mais opções
        
        result = await db.execute(query)
        matches = result.scalars().all()
        
        matches_data = []
        for match in matches:
            # Determina se é partida futura
            now_timestamp = int(datetime.utcnow().timestamp())
            is_future = match.date_unix and match.date_unix > now_timestamp
            
            matches_data.append({
                "home_team": match.home_team_name,
                "away_team": match.away_team_name,
                "home_goals": match.home_goal_count or 0,
                "away_goals": match.away_goal_count or 0,
                "status": match.status,
                "date_unix": match.date_unix,
                "is_future": is_future or match.status in upcoming_statuses
            })
        
        return matches_data
    
    async def _retrieve_league_stats(self, entities: Dict, filters: Dict, db: AsyncSession) -> List[Dict]:
        """Recupera estatísticas gerais da liga - MELHORADO com fallback"""
        league_id = await self._resolve_league_id(entities.get("league_name"), entities.get("league_id"), db)
        
        if not league_id:
            # Se não encontrou a liga, tenta buscar todas as ligas disponíveis
            logger.warning(f"Liga não encontrada: {entities.get('league_name')}. Buscando ligas disponíveis...")
            result = await db.execute(select(League).limit(10))
            leagues = result.scalars().all()
            
            if leagues:
                # Retorna informações sobre ligas disponíveis
                return [{
                    "available_leagues": [{"id": l.id, "name": l.name, "country": l.country} for l in leagues],
                    "message": f"Liga '{entities.get('league_name', 'desconhecida')}' não encontrada. Ligas disponíveis listadas acima."
                }]
            return []
        
        # Busca informações da liga
        league_result = await db.execute(select(League).filter(League.id == league_id))
        league = league_result.scalar_one_or_none()
        
        # Conta times
        teams_query = select(func.count(TeamStatistics.id)).filter(TeamStatistics.league_id == league_id)
        teams_result = await db.execute(teams_query)
        total_teams = teams_result.scalar() or 0
        
        # Conta partidas
        matches_query = select(func.count(Fixture.id)).filter(
            Fixture.league_id == league_id,
            Fixture.status == 'complete'
        )
        matches_result = await db.execute(matches_query)
        total_matches = matches_result.scalar() or 0
        
        # Total de gols
        goals_query = select(func.sum(Fixture.total_goal_count)).filter(
            Fixture.league_id == league_id,
            Fixture.status == 'complete'
        )
        goals_result = await db.execute(goals_query)
        total_goals = goals_result.scalar() or 0
        
        avg_goals = round(total_goals / total_matches, 2) if total_matches > 0 else 0
        
        # Busca também a tabela de classificação para estatísticas mais completas
        from app.services.league_service import LeagueService
        service = LeagueService(db)
        standings = await service.get_standings(league_id)
        
        stats = {
            "league_id": league_id,
            "league_name": league.name if league else f"Liga {league_id}",
            "country": league.country if league else "N/A",
            "total_teams": total_teams,
            "total_matches": total_matches,
            "total_goals": total_goals,
            "avg_goals_per_match": avg_goals,
            "standings_count": len(standings) if standings else 0
        }
        
        # Adiciona top 5 da tabela se disponível
        if standings:
            stats["top_5_teams"] = [
                {
                    "rank": s.get("rank", 0),
                    "name": s.get("name", "N/A"),
                    "points": s.get("points", 0)
                }
                for s in standings[:5]
            ]
        
        return [stats]
    
    async def _retrieve_comparison_data(self, entities: Dict, filters: Dict, db: AsyncSession) -> List[Dict]:
        """Recupera dados completos para comparação de times - MELHORADO"""
        team1_name = entities.get("team1_name") or entities.get("team_name")
        team2_name = entities.get("team2_name")
        
        if not team1_name or not team2_name:
            # Se não tem dois times, tenta extrair da query original
            query_text = entities.get("query_text", "").lower() if hasattr(entities, 'get') else ""
            if not query_text:
                return []
            
            # Tenta encontrar dois times na query
            common_teams = {
                'flamengo', 'palmeiras', 'corinthians', 'são paulo', 'santos', 'fluminense',
                'botafogo', 'atlético', 'cruzeiro', 'grêmio', 'internacional', 'athletico',
                'atletico mineiro', 'atletico mg', 'vasco', 'coritiba', 'fortaleza', 'bahia'
            }
            found_teams = []
            for team in common_teams:
                if team in query_text:
                    found_teams.append(team)
                    if len(found_teams) >= 2:
                        break
            
            if len(found_teams) >= 2:
                team1_name = found_teams[0]
                team2_name = found_teams[1]
            else:
                return []
        
        # Busca estatísticas do time 1
        query1 = select(TeamStatistics, Team).join(Team, TeamStatistics.team_id == Team.id).filter(
            or_(
                Team.name.ilike(f'%{team1_name}%'),
                Team.clean_name.ilike(f'%{team1_name}%')
            )
        ).limit(1)
        
        result1 = await db.execute(query1)
        row1 = result1.first()
        
        # Busca estatísticas do time 2
        query2 = select(TeamStatistics, Team).join(Team, TeamStatistics.team_id == Team.id).filter(
            or_(
                Team.name.ilike(f'%{team2_name}%'),
                Team.clean_name.ilike(f'%{team2_name}%')
            )
        ).limit(1)
        
        result2 = await db.execute(query2)
        row2 = result2.first()
        
        if not row1 or not row2:
            return []
        
        stats1, team1 = row1
        stats2, team2 = row2
        
        # Calcula aproveitamento
        aproveitamento1 = round((stats1.points / (stats1.matches_played * 3)) * 100) if stats1.matches_played > 0 else 0
        aproveitamento2 = round((stats2.points / (stats2.matches_played * 3)) * 100) if stats2.matches_played > 0 else 0
        
        # Busca jogadores dos times (top scorers)
        players1_query = select(Player).filter(
            Player.team_id == team1.id
        ).order_by(Player.goals.desc(), Player.assists.desc()).limit(5)
        
        players2_query = select(Player).filter(
            Player.team_id == team2.id
        ).order_by(Player.goals.desc(), Player.assists.desc()).limit(5)
        
        players1_result = await db.execute(players1_query)
        players2_result = await db.execute(players2_query)
        
        players1 = players1_result.scalars().all()
        players2 = players2_result.scalars().all()
        
        # Busca confrontos diretos
        h2h_query = select(Fixture).filter(
            or_(
                and_(
                    Fixture.home_team_id == team1.id,
                    Fixture.away_team_id == team2.id
                ),
                and_(
                    Fixture.home_team_id == team2.id,
                    Fixture.away_team_id == team1.id
                )
            ),
            Fixture.status == 'complete'
        ).order_by(Fixture.date_unix.desc()).limit(5)
        
        h2h_result = await db.execute(h2h_query)
        h2h_matches = h2h_result.scalars().all()
        
        # Monta dados completos
        comparison_data = {
            "team1": {
                "team_name": team1.name if team1 else f"Time {stats1.team_id}",
                "league_id": stats1.league_id,
                "rank": stats1.rank or 0,
                "points": stats1.points or 0,
                "matches_played": stats1.matches_played or 0,
                "wins": stats1.wins or 0,
                "draws": stats1.draws or 0,
                "losses": stats1.losses or 0,
                "goals_for": stats1.goals_for or 0,
                "goals_against": stats1.goals_against or 0,
                "goals_diff": (stats1.goals_for or 0) - (stats1.goals_against or 0),
                "aproveitamento": aproveitamento1,
                "top_players": [
                    {
                        "name": p.name,
                        "goals": p.goals or 0,
                        "assists": p.assists or 0,
                        "matches_played": p.matches_played or 0
                    }
                    for p in players1
                ]
            },
            "team2": {
                "team_name": team2.name if team2 else f"Time {stats2.team_id}",
                "league_id": stats2.league_id,
                "rank": stats2.rank or 0,
                "points": stats2.points or 0,
                "matches_played": stats2.matches_played or 0,
                "wins": stats2.wins or 0,
                "draws": stats2.draws or 0,
                "losses": stats2.losses or 0,
                "goals_for": stats2.goals_for or 0,
                "goals_against": stats2.goals_against or 0,
                "goals_diff": (stats2.goals_for or 0) - (stats2.goals_against or 0),
                "aproveitamento": aproveitamento2,
                "top_players": [
                    {
                        "name": p.name,
                        "goals": p.goals or 0,
                        "assists": p.assists or 0,
                        "matches_played": p.matches_played or 0
                    }
                    for p in players2
                ]
            },
            "head_to_head": [
                {
                    "home_team": m.home_team_name,
                    "away_team": m.away_team_name,
                    "home_goals": m.home_goal_count or 0,
                    "away_goals": m.away_goal_count or 0,
                    "date": m.date_unix
                }
                for m in h2h_matches
            ]
        }
        
        return [comparison_data]
    
    async def _retrieve_general_data(self, query: str, db: AsyncSession) -> List[Dict]:
        """Recupera dados gerais (ligas disponíveis)"""
        result = await db.execute(select(League).limit(10))
        leagues = result.scalars().all()
        
        return [{"id": l.id, "name": l.name, "country": l.country} for l in leagues]
    
    async def _resolve_league_id(self, league_name: Optional[str], league_id: Optional[int], db: AsyncSession) -> Optional[int]:
        """Resolve nome ou ID de liga para ID - MELHORADO com mapeamento de sinônimos"""
        if league_id:
            return league_id
        
        if not league_name:
            return None
        
        # Mapeamento de sinônimos comuns para nomes exatos no banco
        league_synonyms = {
            'brasileirão': 'Serie A',
            'brasileiro': 'Serie A',
            'serie a': 'Serie A',
            'série a': 'Serie A',
            'brasil série a': 'Serie A',
            'brasileirão série a': 'Serie A',
            'serie b': 'Serie B',
            'série b': 'Serie B',
            'premier league': 'Premier League',
            'premier': 'Premier League',
            'bundesliga': 'Bundesliga',
            'champions league': 'Champions League',
            'champions': 'Champions League',
            'uefa champions': 'Champions League'
        }
        
        # Normaliza o nome
        league_name_lower = league_name.lower().strip()
        
        # Verifica se é um sinônimo conhecido
        if league_name_lower in league_synonyms:
            league_name = league_synonyms[league_name_lower]
        
        # Busca por nome exato primeiro
        result = await db.execute(
            select(League).filter(
                League.name.ilike(f'%{league_name}%')
            ).limit(5)
        )
        leagues = result.scalars().all()
        
        if leagues:
            # Prioriza correspondência exata ou mais próxima
            for league in leagues:
                if league.name.lower() == league_name.lower():
                    return league.id
            # Retorna a primeira se não houver correspondência exata
            return leagues[0].id
        
        # Se não encontrou, tenta buscar por país (Brasil -> Serie A)
        if 'brasil' in league_name_lower or 'brasileirão' in league_name_lower or 'brasileiro' in league_name_lower:
            result = await db.execute(
                select(League).filter(
                    and_(
                        League.country.ilike('%Brazil%'),
                        League.name.ilike('%Serie A%')
                    )
                ).limit(1)
            )
            league = result.scalar_one_or_none()
            if league:
                return league.id
        
        return None
    
    async def _generate_response(self, query: str, intent: Dict, context_data: List[Dict], session_id: Optional[str] = None) -> str:
        """Gera resposta usando LLM com contexto dos dados recuperados e histórico conversacional"""
        try:
            intent_type = intent.get("intent", "general")
            
            # Rejeita perguntas fora do escopo
            if intent_type == "off_topic":
                return "Desculpe, mas eu sou um assistente especializado exclusivamente em estatísticas de futebol. Posso te ajudar com informações sobre ligas, times, jogadores e partidas do nosso banco de dados. O que você gostaria de saber sobre futebol? ⚽"
            
            # Trata greetings e help sem precisar de dados
            if intent_type == "greeting":
                return self._handle_greeting()
            elif intent_type == "help":
                return self._handle_help()
            
            # Prepara contexto
            context_str = self._format_context(context_data, intent_type)
            
            # System prompt restritivo - APENAS futebol e dados do banco
            system_prompt = """Você é um assistente especializado EXCLUSIVAMENTE em estatísticas de futebol.
Você tem acesso APENAS a dados reais de ligas, times, jogadores e partidas do banco de dados.

REGRAS ESTRITAS:
1. **SOMENTE FUTEBOL**: Responda APENAS perguntas sobre futebol. Se o usuário perguntar sobre outros assuntos (política, filmes, tecnologia, etc.), responda educadamente que você só pode ajudar com futebol.

2. **APENAS DADOS DO BANCO**: Use EXCLUSIVAMENTE os dados fornecidos no contexto. NÃO invente informações, NÃO use conhecimento geral sobre futebol que não esteja nos dados.

3. **SE NÃO HOUVER DADOS**: Se não houver dados suficientes no contexto, seja honesto: "Não encontrei essas informações no banco de dados. Posso ajudar com outras estatísticas disponíveis."

4. **ESTILO**: Seja natural, conversacional e amigável, mas sempre baseado nos dados reais.

5. **EMOJIS**: Use emojis ocasionalmente (🏆 ⚽ 🎯 📊) para tornar a resposta mais interessante.

6. **IDIOMA**: Responda sempre em português brasileiro.

7. **CONTEXTO**: Mantenha o contexto da conversa anterior quando relevante para futebol.

8. **NÃO ESPECULE**: Se não tiver certeza dos dados, diga que não encontrou a informação no banco.

Lembre-se: Você é um assistente de dados de futebol, não um especialista geral em futebol. Suas respostas devem ser baseadas nos dados do banco."""

            # Prepara histórico da conversa se disponível - OTIMIZADO
            messages = [SystemMessage(content=system_prompt)]
            
            # Adiciona histórico da conversa (limitado para economia de tokens)
            if session_id and session_id in self.conversation_history:
                max_history = settings.CHATBOT_MAX_HISTORY_MESSAGES or 4
                history = self.conversation_history[session_id][-max_history:]
                messages.extend(history)
            
            # Prepara prompt do usuário com contexto
            if context_data:
                # Prompt especial para comparação/previsão
                if intent_type == "comparison":
                    user_prompt = f"""Pergunta do usuário: "{query}"

Dados disponíveis no banco de dados para comparação:
{context_str}

IMPORTANTE PARA COMPARAÇÃO/PREVISÃO:
- Analise as estatísticas de AMBOS os times (pontos, classificação, gols, aproveitamento)
- Compare os jogadores principais (artilheiros, assistências)
- Considere o histórico de confrontos diretos (head_to_head) se disponível
- Faça uma análise comparativa detalhada e dê uma opinião fundamentada sobre qual time tem mais chances de vencer
- Seja específico: mencione números, estatísticas e razões para sua análise
- Se não houver dados suficientes, seja honesto sobre as limitações
- Use os dados reais do banco, não invente informações"""
                else:
                    user_prompt = f"""Pergunta do usuário: "{query}"

Dados disponíveis no banco de dados:
{context_str}

IMPORTANTE: 
- Responda APENAS com base nos dados acima
- Se a pergunta não for sobre futebol, diga que só pode ajudar com futebol
- Se os dados não forem suficientes, seja honesto: "Não encontrei essas informações no banco de dados"
- Seja natural e conversacional, mas sempre baseado nos dados reais"""
            else:
                user_prompt = f"""Pergunta do usuário: "{query}"

Não encontrei dados específicos no banco de dados para esta pergunta.

IMPORTANTE:
- Se a pergunta NÃO for sobre futebol, responda educadamente que você só pode ajudar com futebol
- Se for sobre futebol mas não temos os dados, seja honesto: "Não encontrei essas informações no banco de dados. Posso ajudar com outras estatísticas disponíveis."
- NÃO invente informações ou use conhecimento geral sobre futebol"""

            messages.append(HumanMessage(content=user_prompt))
            
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}", exc_info=True)
            return self._format_fallback_response(context_data, intent.get("intent"))
    
    def _handle_greeting(self) -> str:
        """Responde a cumprimentos"""
        greetings = [
            "Olá! 👋 Sou seu assistente de estatísticas de futebol! Posso te ajudar com informações sobre ligas, times, jogadores e muito mais. O que você gostaria de saber?",
            "Oi! ⚽ Que bom te ver por aqui! Estou aqui para te ajudar com tudo sobre futebol. Pode me perguntar sobre tabelas, artilheiros, estatísticas de times... O que você quer saber?",
            "E aí! 🏆 Sou especialista em dados de futebol! Posso te mostrar tabelas de classificação, artilheiros, estatísticas de times e muito mais. Como posso ajudar?"
        ]
        import random
        return random.choice(greetings)
    
    def _handle_help(self) -> str:
        """Responde pedidos de ajuda"""
        return """🤖 **Como posso ajudar você:**

Posso responder perguntas sobre:

📊 **Tabelas e Classificações**
- "Mostre a tabela do Brasileirão"
- "Quem está em primeiro lugar?"
- "Qual a posição do Flamengo?"

⚽ **Artilheiros**
- "Quem são os artilheiros?"
- "Mostre os goleadores do Brasileirão"
- "Quem fez mais gols?"

🏆 **Times e Estatísticas**
- "Estatísticas do Flamengo"
- "Como está o Palmeiras?"
- "Mostre dados do Corinthians"

📈 **Ligas e Campeonatos**
- "Estatísticas do Brasileirão"
- "Quantos times tem na liga?"
- "Qual a média de gols?"

💬 **Comparações**
- "Compare Flamengo e Palmeiras"
- "Flamengo vs Corinthians"

Pode me perguntar de forma natural, como se estivesse conversando com um amigo! 😊"""
    
    def _format_context(self, data: List[Dict], intent_type: str) -> str:
        """Formata dados para contexto do LLM - OTIMIZADO para economia de tokens e comparação"""
        if not data:
            return "Nenhum dado encontrado no banco de dados."
        
        # Formatação especial para comparação
        if intent_type == "comparison" and len(data) > 0 and isinstance(data[0], dict) and "team1" in data[0]:
            comparison = data[0]
            context = "=== COMPARAÇÃO DE TIMES ===\n\n"
            
            # Time 1
            t1 = comparison.get("team1", {})
            context += f"TIME 1: {t1.get('team_name', 'N/A')}\n"
            context += f"  - Posição: {t1.get('rank', 0)}º\n"
            context += f"  - Pontos: {t1.get('points', 0)}\n"
            context += f"  - Jogos: {t1.get('matches_played', 0)}\n"
            context += f"  - Vitórias: {t1.get('wins', 0)} | Empates: {t1.get('draws', 0)} | Derrotas: {t1.get('losses', 0)}\n"
            context += f"  - Gols a favor: {t1.get('goals_for', 0)} | Gols contra: {t1.get('goals_against', 0)} | Saldo: {t1.get('goals_diff', 0)}\n"
            context += f"  - Aproveitamento: {t1.get('aproveitamento', 0)}%\n"
            
            # Top jogadores time 1
            players1 = t1.get('top_players', [])
            if players1:
                context += f"  - Top jogadores:\n"
                for p in players1[:3]:
                    context += f"    • {p.get('name', 'N/A')}: {p.get('goals', 0)} gols, {p.get('assists', 0)} assistências\n"
            
            context += "\n"
            
            # Time 2
            t2 = comparison.get("team2", {})
            context += f"TIME 2: {t2.get('team_name', 'N/A')}\n"
            context += f"  - Posição: {t2.get('rank', 0)}º\n"
            context += f"  - Pontos: {t2.get('points', 0)}\n"
            context += f"  - Jogos: {t2.get('matches_played', 0)}\n"
            context += f"  - Vitórias: {t2.get('wins', 0)} | Empates: {t2.get('draws', 0)} | Derrotas: {t2.get('losses', 0)}\n"
            context += f"  - Gols a favor: {t2.get('goals_for', 0)} | Gols contra: {t2.get('goals_against', 0)} | Saldo: {t2.get('goals_diff', 0)}\n"
            context += f"  - Aproveitamento: {t2.get('aproveitamento', 0)}%\n"
            
            # Top jogadores time 2
            players2 = t2.get('top_players', [])
            if players2:
                context += f"  - Top jogadores:\n"
                for p in players2[:3]:
                    context += f"    • {p.get('name', 'N/A')}: {p.get('goals', 0)} gols, {p.get('assists', 0)} assistências\n"
            
            # Confrontos diretos
            h2h = comparison.get("head_to_head", [])
            if h2h:
                context += f"\n=== CONFRONTOS DIRETOS (últimos {len(h2h)}) ===\n"
                for match in h2h[:5]:
                    context += f"  {match.get('home_team', 'N/A')} {match.get('home_goals', 0)} x {match.get('away_goals', 0)} {match.get('away_team', 'N/A')}\n"
            
            return context
        
        # Limita quantidade de itens para economia de tokens
        max_items = settings.CHATBOT_MAX_CONTEXT_ITEMS or 10
        limited_data = data[:max_items]
        
        # Formata de forma compacta (sem indentação excessiva)
        context_parts = []
        for item in limited_data:
            # Formata apenas campos relevantes de forma compacta
            if intent_type == "standings":
                context_parts.append(
                    f"{item.get('rank', 0)}º {item.get('team_name', 'N/A')}: "
                    f"{item.get('points', 0)}pts, {item.get('matches_played', 0)}J, "
                    f"{item.get('wins', 0)}V-{item.get('draws', 0)}E-{item.get('losses', 0)}D, "
                    f"SG:{item.get('goals_diff', 0)}"
                )
            elif intent_type == "scorers":
                context_parts.append(
                    f"{item.get('player_name', 'N/A')} ({item.get('team_name', 'N/A')}): "
                    f"{item.get('goals', 0)}gols, {item.get('assists', 0)}assists"
                )
            elif intent_type == "team_info":
                context_parts.append(
                    f"{item.get('team_name', 'N/A')}: {item.get('rank', 0)}º lugar, "
                    f"{item.get('points', 0)}pts, {item.get('matches_played', 0)}J, "
                    f"{item.get('goals_for', 0)}GF/{item.get('goals_against', 0)}GS"
                )
            else:
                # Formato genérico compacto
                key_items = {k: v for k, v in item.items() if v is not None and v != 0 and k not in ['id', 'created_at', 'updated_at']}
                context_parts.append(str(key_items))
        
        context_str = "\n".join(context_parts)
        
        # Limita tamanho total do contexto
        max_length = settings.CHATBOT_MAX_CONTEXT_LENGTH or 2000
        if len(context_str) > max_length:
            context_str = context_str[:max_length] + "... (dados truncados)"
        
        return context_str
    
    def _format_fallback_response(self, data: List[Dict], intent_type: str) -> str:
        """Resposta de fallback quando LLM falha"""
        if not data:
            return "Desculpe, não encontrei dados no banco de dados para responder sua pergunta."
        
        if intent_type == "standings":
            response = "🏆 Tabela de Classificação:\n\n"
            for team in data[:10]:
                response += f"{team.get('rank', 0)}º - {team.get('team_name', 'N/A')} - {team.get('points', 0)}pts\n"
            return response
        
        elif intent_type == "scorers":
            response = "⚽ Artilheiros:\n\n"
            for i, scorer in enumerate(data[:10], 1):
                response += f"{i}º - {scorer.get('player_name', 'N/A')} ({scorer.get('team_name', 'N/A')}) - {scorer.get('goals', 0)} gols\n"
            return response
        
        return f"Encontrei {len(data)} registro(s) no banco de dados."
    
    async def _fallback_response(self, query: str, db: AsyncSession) -> str:
        """Resposta de fallback quando RAG não está disponível - versão melhorada e restritiva"""
        query_lower = query.lower().strip()
        
        # Verifica se é sobre futebol
        football_keywords = ['futebol', 'football', 'soccer', 'liga', 'league', 'time', 'team', 'clube', 
                            'jogador', 'player', 'partida', 'match', 'jogo', 'game', 'gol', 'goal',
                            'tabela', 'standings', 'classificação', 'artilheiro', 'scorer', 'goleador',
                            'estatística', 'stat', 'brasileirão', 'brasileiro', 'campeonato', 'championship',
                            'vitória', 'win', 'derrota', 'loss', 'empate', 'draw', 'pontos', 'points',
                            'confronto', 'fixture', 'comparar', 'compare', 'flamengo', 'palmeiras', 'corinthians']
        
        is_football_related = any(keyword in query_lower for keyword in football_keywords)
        
        # Se não for sobre futebol, rejeita educadamente
        if not is_football_related and len(query) > 3:  # Ignora greetings muito curtos
            return "Desculpe, mas eu sou um assistente especializado exclusivamente em estatísticas de futebol. Posso te ajudar com informações sobre ligas, times, jogadores e partidas do nosso banco de dados. O que você gostaria de saber sobre futebol? ⚽"
        
        # Greetings
        if any(word in query_lower for word in ['oi', 'olá', 'hello', 'hi', 'hey', 'eae', 'e aí', 'tudo bem']):
            return self._handle_greeting()
        
        # Help
        if any(word in query_lower for word in ['ajuda', 'help', 'comandos', 'o que você pode', 'o que pode']):
            return self._handle_help()
        
        # Tenta buscar dados mesmo sem LLM
        intent = self._simple_intent_analysis(query)
        context_data = await self._retrieve_data(intent, query, db)
        
        if context_data:
            return self._format_fallback_response(context_data, intent.get("intent"))
        
        # Resposta genérica restritiva
        return """Olá! Sou seu assistente de futebol especializado em dados do nosso banco de dados.

⚠️ **Importante**: Eu só posso responder perguntas sobre futebol usando os dados disponíveis no banco.

📊 **O que posso fazer:**
- Buscar informações sobre ligas, times e jogadores no banco de dados
- Mostrar tabelas de classificação
- Listar artilheiros
- Comparar times

**Dica:** Tente perguntar de forma mais específica, como:
- "Tabela do Brasileirão"
- "Artilheiros da liga"
- "Estatísticas do Flamengo"

Infelizmente, o serviço de IA está temporariamente indisponível, mas posso buscar dados diretamente do banco! 😊"""


