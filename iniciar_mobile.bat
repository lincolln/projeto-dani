@echo off
rem ==========================================================================
rem  iniciar_mobile.bat - Sobe a API Mobile Kanemberg (FastAPI :8000) e abre
rem  um tunel HTTPS gratuito (Cloudflare Quick Tunnel) para liberar a camera
rem  no Safari do iPhone.
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion
title KANEMBERG - Servidor Mobile
cd /d "%~dp0"

set "PORTA=8000"
set "URL_LOCAL=http://localhost:%PORTA%"
set "LOG=%TEMP%\kanemberg_tunnel.log"

cls
echo.
echo  ============================================================
echo           === INICIANDO SERVIDOR MOBILE KANEMBERG ===
echo  ============================================================
echo.

rem --------------------------------------------------------------------------
rem  [1/4] Localizar o Python (venv do projeto > py launcher > python > padrao)
rem --------------------------------------------------------------------------
echo  [1/4] Procurando o Python...
set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "%~dp0venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not defined PYTHON_EXE for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"

if not defined PYTHON_EXE (
    echo.
    echo  [ERRO] Python nao encontrado.
    echo         Instale com:  winget install --id Python.Python.3.12
    echo.
    pause
    exit /b 1
)
echo        OK: %PYTHON_EXE%

rem Verifica dependencias da API
"%PYTHON_EXE%" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [AVISO] FastAPI/Uvicorn nao estao instalados neste Python.
    choice /C SN /M "        Instalar agora (pip install fastapi uvicorn)"
    if errorlevel 2 (
        echo  Cancelado. Rode manualmente: "%PYTHON_EXE%" -m pip install fastapi uvicorn
        pause
        exit /b 1
    )
    "%PYTHON_EXE%" -m pip install --upgrade fastapi uvicorn
    if errorlevel 1 (
        echo  [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
)

rem --------------------------------------------------------------------------
rem  [2/4] Localizar o cloudflared (pasta do projeto > PATH > instalacao winget)
rem --------------------------------------------------------------------------
echo.
echo  [2/4] Procurando o cloudflared...
call :localizar_cloudflared

if not defined CLOUDFLARED (
    echo.
    echo  ------------------------------------------------------------
    echo   [X] cloudflared NAO encontrado.
    echo.
    echo   Instale em ~10 segundos com o comando:
    echo.
    echo       winget install --id Cloudflare.cloudflared
    echo.
    echo   Ou baixe o cloudflared.exe e coloque nesta pasta:
    echo   https://github.com/cloudflare/cloudflared/releases/latest
    echo  ------------------------------------------------------------
    echo.
    choice /C SN /M "  Deseja executar o winget agora"
    if errorlevel 2 (
        pause
        exit /b 1
    )
    winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
    call :localizar_cloudflared
    if not defined CLOUDFLARED (
        echo.
        echo  [AVISO] Instalado, mas o PATH ainda nao foi atualizado.
        echo          Feche esta janela e execute o iniciar_mobile.bat novamente.
        pause
        exit /b 1
    )
)
echo        OK: %CLOUDFLARED%

rem --------------------------------------------------------------------------
rem  [3/4] Subir a API FastAPI em janela minimizada
rem --------------------------------------------------------------------------
echo.
echo  [3/4] Iniciando a API FastAPI na porta %PORTA%...
set "API_JA_RODANDO=0"
netstat -ano | findstr /R /C:":%PORTA% .*LISTENING" >nul && set "API_JA_RODANDO=1"

if "%API_JA_RODANDO%"=="1" (
    echo        Porta %PORTA% ja esta em uso - reaproveitando o servidor existente.
) else (
    start "KANEMBERG-API" /min cmd /k ""%PYTHON_EXE%" "%~dp0api_mobile.py""
)

timeout /t 3 /nobreak >nul

rem Confirma que a API respondeu (ate ~10s extras)
set /a TENTATIVAS=0
:aguardar_api
curl -s -o nul "%URL_LOCAL%/" >nul 2>&1 && goto api_ok
set /a TENTATIVAS+=1
if !TENTATIVAS! GEQ 10 (
    echo.
    echo  [ERRO] A API nao respondeu em %URL_LOCAL%.
    echo         Abra a janela minimizada "KANEMBERG-API" na barra de tarefas para ver o erro.
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto aguardar_api

:api_ok
echo        OK: API respondendo em %URL_LOCAL%
echo        Abrindo interface Desktop no PC...
start "" msedge --app=%URL_LOCAL% 2>nul || start "" %URL_LOCAL%

rem --------------------------------------------------------------------------
rem  [4/4] Abrir o tunel HTTPS (Cloudflare Quick Tunnel)
rem --------------------------------------------------------------------------
echo.
echo  [4/4] Abrindo tunel HTTPS... aguarde o link aparecer abaixo.
echo.
echo  ------------------------------------------------------------
echo   Para ENCERRAR tudo: pressione Ctrl+C e responda N.
echo  ------------------------------------------------------------
echo.

if exist "%LOG%" del /q "%LOG%" >nul 2>&1

rem Vigia em segundo plano: captura o link do log, destaca na tela e copia
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -Command "$f=$env:LOG; for($i=0;$i -lt 120;$i++){ if(Test-Path $f){ $m = Select-String -Path $f -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1; if($m){ $u=$m.Matches[0].Value; try{ Set-Clipboard -Value $u }catch{}; Write-Host ''; Write-Host ('#'*64) -ForegroundColor Green; Write-Host ''; Write-Host ('   LINK DO APP (abra no Safari do iPhone):') -ForegroundColor Green; Write-Host ''; Write-Host ('   ' + $u) -ForegroundColor Yellow; Write-Host ''; Write-Host ('   (link copiado para a area de transferencia)') -ForegroundColor DarkGray; Write-Host ''; Write-Host ('#'*64) -ForegroundColor Green; Write-Host ''; break } }; Start-Sleep -Milliseconds 500 }"

"%CLOUDFLARED%" tunnel --no-autoupdate --logfile "%LOG%" --url %URL_LOCAL%

rem --------------------------------------------------------------------------
rem  Encerramento: derruba a API que este script abriu
rem --------------------------------------------------------------------------
echo.
echo  Tunel encerrado. Desligando a API...
if "%API_JA_RODANDO%"=="0" taskkill /FI "WINDOWTITLE eq KANEMBERG-API*" /T /F >nul 2>&1
echo  Pronto. Ate logo!
timeout /t 3 >nul
endlocal
exit /b 0


rem ==========================================================================
rem  Sub-rotina: procura o cloudflared.exe
rem ==========================================================================
:localizar_cloudflared
set "CLOUDFLARED="
if exist "%~dp0cloudflared.exe" set "CLOUDFLARED=%~dp0cloudflared.exe"
if not defined CLOUDFLARED for /f "delims=" %%C in ('where cloudflared 2^>nul') do if not defined CLOUDFLARED set "CLOUDFLARED=%%C"
if not defined CLOUDFLARED if exist "%ProgramFiles(x86)%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%ProgramFiles(x86)%\cloudflared\cloudflared.exe"
if not defined CLOUDFLARED if exist "%ProgramFiles%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%ProgramFiles%\cloudflared\cloudflared.exe"
if not defined CLOUDFLARED if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe" set "CLOUDFLARED=%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe"
exit /b 0


rem ==========================================================================
rem  INSTALAR NO IPHONE COMO APLICATIVO (3 toques no Safari):
rem
rem    1. Abra o link https://....trycloudflare.com no SAFARI (nao no Chrome).
rem    2. Toque em "Compartilhar" (quadrado com seta para cima, na barra inferior).
rem    3. Role e toque em "Adicionar a Tela de Inicio" -> "Adicionar".
rem
rem  O icone KANEMBERG aparece na tela inicial e abre em tela cheia, sem
rem  barra do navegador. A camera so funciona porque o link e HTTPS.
rem
rem  ATENCAO: o link trycloudflare MUDA a cada vez que este script e executado.
rem  Se reiniciar o servidor, apague o icone antigo e adicione o novo link.
rem ==========================================================================
