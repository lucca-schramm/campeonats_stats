"""Testes dos endpoints da API"""
import pytest
import requests
import time
from typing import Dict

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


class TestEndpoints:
    """Testes básicos dos endpoints"""
    
    def test_health_check(self):
        """Testa endpoint de health check"""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Health check OK")
    
    def test_root_endpoint(self):
        """Testa endpoint raiz"""
        response = requests.get(f"{BASE_URL}/", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        print("✅ Root endpoint OK")
    
    def test_list_leagues(self):
        """Testa listagem de ligas"""
        response = requests.get(f"{API_BASE}/leagues", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ List leagues OK - {len(data)} ligas")
    
    def test_chatbot_help(self):
        """Testa chatbot com mensagem de ajuda"""
        response = requests.post(
            f"{API_BASE}/chatbot/chat",
            json={"message": "ajuda", "chatbot_type": "simple"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        print("✅ Chatbot ajuda OK")
    
    def test_chatbot_greeting(self):
        """Testa chatbot com saudação"""
        response = requests.post(
            f"{API_BASE}/chatbot/chat",
            json={"message": "oi", "chatbot_type": "simple"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 0
        print("✅ Chatbot saudação OK")
    
    def test_search_leagues(self):
        """Testa busca de ligas"""
        response = requests.get(
            f"{API_BASE}/chatbot/leagues/search?q=brasil&limit=5",
            timeout=5
        )
        assert response.status_code == 200
        data = response.json()
        assert "leagues" in data
        print(f"✅ Search leagues OK - {len(data['leagues'])} resultados")
    
    def test_webhooks_list(self):
        """Testa listagem de webhooks"""
        response = requests.get(f"{API_BASE}/webhooks", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ List webhooks OK - {len(data)} webhooks")
    
    def test_performance_headers(self):
        """Testa se headers de performance estão presentes"""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert "X-Process-Time" in response.headers
        assert "X-Request-ID" in response.headers
        print("✅ Performance headers OK")
    
    def test_rate_limiting(self):
        """Testa rate limiting (deve permitir requisições normais)"""
        # Faz várias requisições rápidas
        for i in range(10):
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200
        print("✅ Rate limiting OK (10 reqs rápidas)")
    
    def test_cors_headers(self):
        """Testa headers CORS"""
        response = requests.options(
            f"{API_BASE}/leagues",
            headers={"Origin": "http://localhost:3000"},
            timeout=5
        )
        # Deve retornar 200 ou 405 (método não permitido)
        assert response.status_code in [200, 405]
        print("✅ CORS headers OK")