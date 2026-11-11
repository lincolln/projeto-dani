@echo off
rem Criar_Atalho.bat - Gera o icone oficial static\icon.ico e cria o atalho "Sistema Kanemberg" na Area de Trabalho.
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% "%~dp0Instalar_Atalho_Desktop.py"
if errorlevel 1 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desk = [Environment]::GetFolderPath('Desktop'); $dir = '%~dp0'.TrimEnd('\'); $lnk = $ws.CreateShortcut((Join-Path $desk 'Sistema Kanemberg.lnk')); $lnk.TargetPath = Join-Path $dir 'Iniciar_Kanemberg.bat'; $lnk.WorkingDirectory = $dir; $lnk.IconLocation = (Join-Path $dir 'static\icon.ico') + ',0'; $lnk.WindowStyle = 7; $lnk.Description = 'Sistema Kanemberg v2'; $lnk.Save()"
)

echo.
echo [OK] Atalho "Sistema Kanemberg" criado/atualizado na Area de Trabalho!
if "%~1"=="" timeout /t 3 >nul
endlocal
