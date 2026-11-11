@echo off
rem ==========================================================================
rem  Kanemberg_Sistema_PC.bat - Inicializador do Sistema Desktop Kanemberg v2
rem  Abre a interface Widescreen (http://localhost:8000/sistema) via main.py.
rem  Se o iniciar_mobile.bat ja estiver ativo na porta 8000, reaproveita o
rem  servidor existente instantaneamente sem conflito de porta.
rem ==========================================================================
setlocal EnableExtensions
title KANEMBERG - Sistema Desktop
cd /d "%~dp0"

set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\pythonw.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE if exist "%~dp0venv\Scripts\pythonw.exe" set "PYTHON_EXE=%~dp0venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Python\bin\pythonw.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\pythonw.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not defined PYTHON_EXE for /f "delims=" %%P in ('py -3 -c "import sys,os;p=os.path.join(os.path.dirname(sys.executable),'pythonw.exe');print(p if os.path.exists(p) else sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE for /f "delims=" %%P in ('python -c "import sys,os;p=os.path.join(os.path.dirname(sys.executable),'pythonw.exe');print(p if os.path.exists(p) else sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"

if not defined PYTHON_EXE (
    echo.
    echo  [ERRO] Python nao encontrado neste computador.
    echo         Execute primeiro o arquivo: 1_instalar_no_cliente.bat
    echo.
    pause
    exit /b 1
)

start "" "%PYTHON_EXE%" "%~dp0main.py"
exit /b 0
