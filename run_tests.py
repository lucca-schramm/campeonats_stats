"""Script para executar testes da API"""
import sys
import requests
import time

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_endpoint(name, method, url, data=None, expected_status=200):
    """Testa um endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"❌ Método {method} não suportado")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {name}: OK")
            return True
        else:
            print(f"❌ {name}: Status {response.status_code} (esperado {expected_status})")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name}: API não está rodando")
        return False
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

def main():
    print("🧪 Testando Endpoints da API")
    print("=" * 60)
    
    # Verifica se API está rodando
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except:
        print("❌ API não está rodando!")
        print("   Execute: python run.py")
        print("   ou: uvicorn app.main:app --reload")
        sys.exit(1)
    
    tests = [
        ("Health Check", "GET", f"{BASE_URL}/health"),
        ("Root", "GET", f"{BASE_URL}/"),
        ("List Leagues", "GET", f"{API_BASE}/leagues?limit=5"),
        ("Chatbot Ajuda", "POST", f"{API_BASE}/chatbot/chat", 
         {"message": "ajuda", "chatbot_type": "simple"}),
        ("Chatbot Oi", "POST", f"{API_BASE}/chatbot/chat",
         {"message": "oi", "chatbot_type": "simple"}),
        ("Search Leagues", "GET", f"{API_BASE}/chatbot/leagues/search?q=brasil&limit=3"),
        ("List Webhooks", "GET", f"{API_BASE}/webhooks"),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, method, url, *args in tests:
        data = args[0] if args else None
        if test_endpoint(test_name, method, url, data):
            passed += 1
        else:
            failed += 1
        time.sleep(0.5)  # Delay entre testes
    
    print("\n" + "=" * 60)
    print(f"📊 Resultado: {passed} passou, {failed} falhou")
    
    if failed == 0:
        print("🎉 Todos os testes passaram!")
        return 0
    else:
        print("⚠️  Alguns testes falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())

