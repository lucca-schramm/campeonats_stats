#!/usr/bin/env python3
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
    env_content = """# API Football API-Sports
# Obtenha sua chave em: https://www.api-sports.io/
APISPORTS_KEY=sua_chave_api_aqui

# GitHub Token (opcional - para salvar dados no GitHub)
# Obtenha em: https://github.com/settings/tokens
GITHUB_TOKEN=seu_token_github_aqui
"""
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ Arquivo .env criado")
    print("⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua chave da API")

def create_directories():
    """Cria diretórios necessários"""
    directories = ["data", "logs", "exports"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Diretórios criados")

def test_api_connection():
    """Testa a conexão com a API"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("APISPORTS_KEY")
        if not api_key or api_key == "sua_chave_api_aqui":
            print("⚠️  API key não configurada. Configure no arquivo .env")
            return False
        
        import requests
        headers = {"x-apisports-key": api_key}
        response = requests.get("https://v3.football.api-sports.io/status", headers=headers)
        
        if response.status_code == 200:
            print("✅ Conexão com a API testada com sucesso")
            return True
        else:
            print(f"❌ Erro na conexão com a API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar API: {e}")
        return False

def main():
    """Função principal de configuração"""
    print("🚀 CONFIGURAÇÃO DO PROJETO FOOTBALL STATISTICS DATABASE")
    print("=" * 60)
    
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
    
    print("\n" + "=" * 60)
    print("🎉 CONFIGURAÇÃO CONCLUÍDA!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Edite o arquivo .env e adicione sua chave da API")
    print("2. Execute: python main.py")
    print("3. Para análise: python queries.py")
    print("\n📚 DOCUMENTAÇÃO:")
    print("- Leia o README.md para mais informações")
    print("- Consulte a documentação da API: https://www.api-sports.io/football-api")

if __name__ == "__main__":
    main()
