@echo off
cd /d "%~dp0"
start "Tunnel" cmd /c "cloudflared.exe tunnel --url http://localhost:5000"
timeout /t 3 /nobreak >nul
set FLASK_SKIP_DOTENV=1
python server.py
pause
