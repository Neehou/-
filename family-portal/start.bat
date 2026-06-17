@echo off
cd /d "%~dp0"
start "Tunnel" cmd /c "cloudflared.exe tunnel --url http://localhost:5000"
timeout /t 3 /nobreak >nul
python server.py
pause
