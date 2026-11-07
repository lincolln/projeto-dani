@echo off
rem Iniciar_Kanemberg.bat - Inicia o servidor (se necessario) e abre o sistema em modo aplicativo.
setlocal EnableExtensions
cd /d "%~dp0"
set "PORTA=8000"
set "URL=http://localhost:%PORTA%/sistema"

netstat -ano | findstr /R /C:":%PORTA% .*LISTENING" >nul
if %errorlevel%==0 goto abrir

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")
start "Kanemberg Servidor" /min %PY% api_mobile.py

set /a TENT=0
:aguardar
set /a TENT+=1
if %TENT% GTR 40 goto abrir
powershell -NoProfile -Command "try{(Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:%PORTA%/robots.txt' -TimeoutSec 1)|Out-Null;exit 0}catch{exit 1}" >nul 2>nul
if errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto aguardar
)

:abrir
start "" msedge --app=%URL% 2>nul
if %errorlevel%==0 goto fim
start "" chrome --app=%URL% 2>nul
if %errorlevel%==0 goto fim
start "" %URL%
:fim
endlocal