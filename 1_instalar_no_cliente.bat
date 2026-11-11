@echo off
rem ==========================================================================
rem  1_instalar_no_cliente.bat
rem  Instala Python (se necessario), bibliotecas (requirements.txt),
rem  Cloudflare Tunnel (cloudflared) e cria os atalhos na Area de Trabalho.
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion
title KANEMBERG - Instalador Automatico para Notebook do Cliente
cd /d "%~dp0"

cls
echo.
echo  ============================================================
echo       === INSTALADOR AUTOMATICO - SISTEMA KANEMBERG ===
echo  ============================================================
echo.

rem --------------------------------------------------------------------------
rem  [1/4] Verificar / Instalar Python 3.12
rem --------------------------------------------------------------------------
echo  [1/4] Verificando instalacao do Python...
set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "%~dp0venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not defined PYTHON_EXE for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not defined PYTHON_EXE (
    echo        Python nao encontrado. Instalando Python 3.12 via winget...
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if not defined PYTHON_EXE for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
)

if not defined PYTHON_EXE (
    echo.
    echo  [AVISO] O Python foi instalado, mas o Windows pede para fechar e
    echo          abrir esta janela novamente para atualizar o sistema.
    pause
    exit /b 1
)
echo        OK: %PYTHON_EXE%

rem --------------------------------------------------------------------------
rem  [2/4] Instalar bibliotecas do requirements.txt
rem --------------------------------------------------------------------------
echo.
echo  [2/4] Instalando bibliotecas do sistema (aguarde ~1 minuto)...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo  [ERRO] Falha ao instalar algumas bibliotecas. Verifique a internet.
    pause
    exit /b 1
)
echo        OK: Bibliotecas instaladas com sucesso!

rem --------------------------------------------------------------------------
rem  [3/4] Verificar / Instalar Cloudflare Tunnel (cloudflared)
rem --------------------------------------------------------------------------
echo.
echo  [3/4] Verificando o Cloudflare Tunnel (HTTPS para o celular)...
set "CLOUDFLARED="
if exist "%~dp0cloudflared.exe" set "CLOUDFLARED=%~dp0cloudflared.exe"
if not defined CLOUDFLARED for /f "delims=" %%C in ('where cloudflared 2^>nul') do if not defined CLOUDFLARED set "CLOUDFLARED=%%C"
if not defined CLOUDFLARED if exist "%ProgramFiles(x86)%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%ProgramFiles(x86)%\cloudflared\cloudflared.exe"
if not defined CLOUDFLARED if exist "%ProgramFiles%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%ProgramFiles%\cloudflared\cloudflared.exe"
if not defined CLOUDFLARED if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe" set "CLOUDFLARED=%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe"

if not defined CLOUDFLARED (
    echo        Instalando Cloudflare Tunnel via winget...
    winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
)
echo        OK: Cloudflare configurado!

rem --------------------------------------------------------------------------
rem  [4/4] Criar atalho oficial "Sistema Kanemberg" na Area de Trabalho
rem --------------------------------------------------------------------------
echo.
echo  [4/4] Gerando icone oficial (.ico) e atalho na Area de Trabalho...
"%PYTHON_EXE%" "%~dp0Instalar_Atalho_Desktop.py"

echo.
echo  ============================================================
echo       === INSTALACAO CONCLUIDA COM SUCESSO! ===
echo.
echo   Foi criado o atalho oficial na Area de Trabalho:
echo     - "Sistema Kanemberg" (abre o sistema maximizado com
echo       o servidor minimizado na barra de tarefas)
echo  ============================================================
echo.
pause
exit /b 0
