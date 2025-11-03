# Script PowerShell para testar endpoints da API

$BASE_URL = "http://localhost:8000"
$API_BASE = "$BASE_URL/api/v1"

Write-Host "🚀 Testando endpoints da API..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Health Check
Write-Host "`n1. Health Check:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Status: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ Falhou: $_" -ForegroundColor Red
}

# Root
Write-Host "`n2. Root Endpoint:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/" -Method Get -TimeoutSec 5
    Write-Host "✅ Message: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "❌ Falhou: $_" -ForegroundColor Red
}

# List Leagues
Write-Host "`n3. List Leagues:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/leagues?limit=5" -Method Get -TimeoutSec 5
    Write-Host "✅ Encontradas $($response.Count) ligas" -ForegroundColor Green
} catch {
    Write-Host "❌ Falhou: $_" -ForegroundColor Red
}

# Chatbot
Write-Host "`n4. Chatbot (ajuda):" -ForegroundColor Yellow
try {
    $body = @{
        message = "ajuda"
        chatbot_type = "simple"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$API_BASE/chatbot/chat" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
    Write-Host "✅ Response recebido (${($response.response.Length)} chars)" -ForegroundColor Green
} catch {
    Write-Host "❌ Falhou: $_" -ForegroundColor Red
}

# Search Leagues
Write-Host "`n5. Search Leagues:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/chatbot/leagues/search?q=brasil&limit=3" -Method Get -TimeoutSec 5
    Write-Host "✅ Encontradas $($response.leagues.Count) ligas" -ForegroundColor Green
} catch {
    Write-Host "❌ Falhou: $_" -ForegroundColor Red
}

Write-Host "`n✅ Testes concluídos!" -ForegroundColor Green

