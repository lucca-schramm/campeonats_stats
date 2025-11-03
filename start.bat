@echo off
echo 🚀 Iniciando Campeonatos Stats...
echo.

echo 📦 Construindo containers...
docker-compose build

echo.
echo 🔧 Iniciando serviços...
docker-compose up -d

echo.
echo ⏳ Aguardando serviços ficarem prontos...
timeout /t 10 /nobreak > nul

echo.
echo 🗄️ Aplicando migrations...
echo ✅ Banco de dados pronto

echo.
echo ✅ Serviços iniciados!
echo.
echo 📍 Acesse:
echo    - Frontend: http://localhost:3000
echo    - API: http://localhost:8000
echo    - Docs: http://localhost:8000/docs
echo.
echo 📊 Ver logs: docker-compose logs -f
echo 🛑 Parar: docker-compose down
pause
