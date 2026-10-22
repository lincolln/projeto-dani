@echo off
rem ==========================================================================
rem  abrir_sistema_pc.bat - Abre o Sistema Desktop Kanemberg (main.py)
rem ==========================================================================
setlocal EnableExtensions
title KANEMBERG - Sistema Desktop
cd /d "%~dp0"

set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\pythonw.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE if exist "%~dp0venv\Scripts\pythonw.exe" set "PYTHON_EXE=%~dp0venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Python\bin\pythonw.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\pythonw.exe"
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
