"""
Script de configuração inicial para o projeto Football Statistics Database
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 ou superior é necessário")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")

def install_dependencies():
    """Instala as dependências do projeto"""
    print("📦 Instalando dependências...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependências instaladas com sucesso")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        sys.exit(1)

def create_env_file():
    """Cria o arquivo .env se não existir"""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ Arquivo .env já existe")
        return
    
    print("🔧 Criando arquivo .env...")
    env_content = """
FOOTYSTATS_API_KEY=sua_chave_footystats_aqui

GITHUB_TOKEN=seu_token_github_aqui

ENCRYPTION_KEY=sua_chave_criptografia_aqui
"""
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ Arquivo .env criado")
    print("⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua chave da FootyStats API")

def create_directories():
    """Cria diretórios necessários"""
    directories = ["data", "logs", "exports"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Diretórios criados")

def test_api_connection():
    """Testa a conexão com a FootyStats API"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("FOOTYSTATS_API_KEY")
        if not api_key or api_key == "sua_chave_footystats_aqui":
            print("⚠️  FootyStats API key não configurada. Configure no arquivo .env")
            return False
        
        import requests
        params = {"key": api_key, "chosen_leagues_only": "true"}
        response = requests.get("https://api.football-data-api.com/league-list", params=params)
        
        if response.status_code == 200:
            data = response.json()
            leagues_count = len(data) if isinstance(data, list) else len(data.get("data", []))
            print(f"✅ Conexão com FootyStats API testada com sucesso")
            print(f"📊 {leagues_count} ligas disponíveis encontradas")
            return True
        else:
            print(f"❌ Erro na conexão com a FootyStats API: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar FootyStats API: {e}")
        return False

def main():
    """Função principal de configuração"""
    # Verificar versão do Python
    check_python_version()
    
    # Instalar dependências
    install_dependencies()
    
    # Criar arquivo .env
    create_env_file()
    
    # Criar diretórios
    create_directories()
    
    # Testar API (se configurada)
    test_api_connection()
    
    print("🎉 CONFIGURAÇÃO CONCLUÍDA!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Edite o arquivo .env e adicione sua chave da FootyStats API")
    print("2. Execute: python main.py")
    print("3. Para análise: python queries.py")
    print("\n📚 DOCUMENTAÇÃO:")
    print("- FootyStats API: https://footystats.org/api/documentations")
    print("- Endpoint principal: https://api.football-data-api.com/league-list")
    print("\n🔑 CHAVE DA API:")
    print("- Obtenha sua chave em: https://footystats.org/api/documentations")
    print("- Use o parâmetro 'chosen_leagues_only=true' para obter ligas selecionadas")

if __name__ == "__main__":
    main()
