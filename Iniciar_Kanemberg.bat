@echo off
rem Iniciar_Kanemberg.bat - Inicia o servidor em modo minimizado, garante o atalho oficial na Area de Trabalho e abre o sistema maximizado em primeiro plano.
setlocal EnableExtensions
cd /d "%~dp0"
set "PORTA=8000"
set "URL=http://localhost:%PORTA%/sistema"

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

rem 1. Cria automaticamente o icone static\icon.ico e o atalho "Sistema Kanemberg.lnk" (WindowStyle=7 Minimizado) na 1a execucao
powershell -NoProfile -ExecutionPolicy Bypass -Command "$desk = [Environment]::GetFolderPath('Desktop'); $lnkPath = Join-Path $desk 'Sistema Kanemberg.lnk'; $icoPath = Join-Path ('%~dp0'.TrimEnd('\')) 'static\icon.ico'; if (-not (Test-Path $lnkPath) -or -not (Test-Path $icoPath)) { exit 1 } else { exit 0 }" >nul 2>nul
if errorlevel 1 (
  %PY% "%~dp0Instalar_Atalho_Desktop.py" >nul 2>nul
)

rem 2. Verifica se o servidor ja esta rodando na porta 8000; se nao estiver, inicia minimizado na barra de tarefas
netstat -ano | findstr /R /C:":%PORTA% .*LISTENING" >nul
if %errorlevel%==0 goto abrir

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
rem 3. Abre a janela do navegador em modo Aplicativo, maximizada e em primeiro plano
start "" /max msedge --app=%URL% --start-maximized 2>nul
if %errorlevel%==0 goto fim
start "" /max chrome --app=%URL% --start-maximized 2>nul
if %errorlevel%==0 goto fim
start "" /max %URL%
:fim
endlocal
