@echo off
cd /d %~dp0
call .venv\Scripts\activate.bat
start "CDSS API" cmd /k "uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000"
timeout /t 3
start "CDSS Web" cmd /k "cd web && npm run dev"
