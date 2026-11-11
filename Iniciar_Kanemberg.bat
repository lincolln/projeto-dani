@echo off
rem Iniciar_Kanemberg.bat - Inicia o servidor minimizado e abre o sistema em modo aplicativo imediatamente.
setlocal EnableExtensions
cd /d "%~dp0"
set "PORTA=8000"
set "URL=http://localhost:%PORTA%/sistema"

rem 1. Verifica se a porta 8000 ja esta em uso
netstat -ano | findstr :%PORTA% | findstr LISTENING >nul 2>nul
if %errorlevel%==0 goto abrir_navegador

rem 2. Localiza o interpretador Python real (priorizando py -3 para evitar o alias da Microsoft Store)
set "PY_CMD=py -3"
py -3 -V >nul 2>nul
if errorlevel 1 (
    set "PY_CMD=python"
)

start "Kanemberg Servidor" /min %PY_CMD% api_mobile.py

rem 3. Aguarda ~2 segundos para o Uvicorn subir (ping funciona mesmo sem console interativo)
ping 127.0.0.1 -n 3 >nul 2>nul

:abrir_navegador
rem 4. Abre o navegador em modo App maximizado e encerra a janela lancadora imediatamente
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --app=%URL% --start-maximized
    exit
)
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    start "" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" --app=%URL% --start-maximized
    exit
)
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    start "" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" --app=%URL% --start-maximized
    exit
)
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --app=%URL% --start-maximized
    exit
)
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" --app=%URL% --start-maximized
    exit
)

start "" chrome --app=%URL% --start-maximized 2>nul
if %errorlevel%==0 exit
start "" msedge --app=%URL% --start-maximized 2>nul
if %errorlevel%==0 exit
start "" %URL%
exit
