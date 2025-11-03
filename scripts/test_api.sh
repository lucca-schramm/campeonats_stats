#!/bin/bash
# Script para testar endpoints da API

BASE_URL="http://localhost:8000"
API_BASE="${BASE_URL}/api/v1"

echo "🚀 Testando endpoints da API..."
echo "================================"

# Health Check
echo -e "\n1. Health Check:"
curl -s "${BASE_URL}/health" | jq '.' || echo "❌ Falhou"

# Root
echo -e "\n2. Root Endpoint:"
curl -s "${BASE_URL}/" | jq '.message' || echo "❌ Falhou"

# List Leagues
echo -e "\n3. List Leagues:"
curl -s "${API_BASE}/leagues?limit=5" | jq 'length' || echo "❌ Falhou"

# Chatbot
echo -e "\n4. Chatbot (ajuda):"
curl -s -X POST "${API_BASE}/chatbot/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "ajuda", "chatbot_type": "simple"}' | jq '.response' || echo "❌ Falhou"

# Search Leagues
echo -e "\n5. Search Leagues:"
curl -s "${API_BASE}/chatbot/leagues/search?q=brasil&limit=3" | jq '.leagues | length' || echo "❌ Falhou"

echo -e "\n✅ Testes concluídos!"

