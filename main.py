"""
main.py — Launcher Oficial do Sistema Desktop Kanemberg v2 (Interface CSS/GPU)
==============================================================================
Responsabilidades:
  1. Garantir inicialização do banco de dados e disparar backup automático
     de segurança (loja_daniel_v2.db -> backups_kanemberg/).
  2. Verificar se o servidor FastAPI (api_mobile.py) já está ativo na porta 8000.
  3. Caso não esteja ativo, iniciar o Uvicorn em background e aguardar resposta
     (timeout rápido de 5s).
  4. Abrir o Sistema de Gestão Kanemberg em janela nativa Widescreen
     (--app=http://localhost:8000/sistema --start-maximized) no Edge ou Chrome.
  5. Manter o servidor ativo enquanto a janela do sistema estiver aberta
     (sem interferir caso o servidor já tenha sido iniciado pelo iniciar_mobile.bat).
"""

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

# Garante que o diretório raiz do projeto esteja no path do Python
_PROJETO_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJETO_DIR not in sys.path:
    sys.path.insert(0, _PROJETO_DIR)

# Proteção para execução via pythonw.exe (sem console no Windows),
# evitando que loggers como o do Uvicorn falhem ao acessar sys.stdout/stderr None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

HOST_API = "127.0.0.1"
PORTA_API = 8000
URL_SISTEMA_CHECK = f"http://{HOST_API}:{PORTA_API}/sistema"
URL_SISTEMA_APP = f"http://localhost:{PORTA_API}/sistema"


def _servidor_esta_ativo(url: str = URL_SISTEMA_CHECK, timeout: float = 1.0) -> bool:
    """Verifica se o servidor FastAPI já está respondendo na rota /sistema."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _aguardar_servidor(timeout_segundos: float = 5.0) -> bool:
    """Aguarda até que o servidor responda em http://127.0.0.1:8000/sistema."""
    inicio = time.monotonic()
    while (time.monotonic() - inicio) < timeout_segundos:
        if _servidor_esta_ativo(timeout=0.6):
            return True
        time.sleep(0.15)
    return _servidor_esta_ativo(timeout=1.0)


def _iniciar_servidor_background():
    """Inicia o servidor Uvicorn (api_mobile:app) na porta 8000 em uma Thread daemon."""
    import uvicorn
    from api_mobile import app as fastapi_app

    config = uvicorn.Config(
        app=fastapi_app,
        host="0.0.0.0",
        port=PORTA_API,
        log_level="warning",
        access_log=False,
    )
    servidor = uvicorn.Server(config)

    thread_srv = threading.Thread(
        target=servidor.run,
        name="Kanemberg-FastAPI-Thread",
        daemon=True,
    )
    thread_srv.start()
    return servidor, thread_srv


def _localizar_navegador_chromium() -> str | None:
    """Localiza o executável do Microsoft Edge ou Google Chrome instalado no Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidatos = [
        # Microsoft Edge (nativo no Windows 10/11)
        os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
        # Google Chrome
        os.path.join(prog_files, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(prog_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
    ]

    for caminho in candidatos:
        if caminho and os.path.isfile(caminho):
            return caminho
    return None


def _abrir_janela_app(url: str) -> subprocess.Popen | None:
    """Abre a URL em modo aplicativo nativo (--app=... --start-maximized) sem barras do navegador."""
    navegador_exe = _localizar_navegador_chromium()
    if not navegador_exe:
        webbrowser.open(url)
        return None

    # Perfil dedicado para garantir que:
    # 1) --start-maximized e --app funcionem mesmo com o navegador já aberto em outras abas.
    # 2) O processo retornado permaneça ativo enquanto a janela do Sistema Kanemberg estiver aberta.
    pasta_perfil = os.path.join(
        os.environ.get("LOCALAPPDATA", _PROJETO_DIR),
        "Kanemberg_Sistema_Desktop_App",
    )
    os.makedirs(pasta_perfil, exist_ok=True)

    argumentos = [
        navegador_exe,
        f"--app={url}",
        "--start-maximized",
        f"--user-data-dir={pasta_perfil}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
    ]

    try:
        return subprocess.Popen(
            argumentos,
            cwd=_PROJETO_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as erro:
        print(f"[Sistema] Aviso ao abrir navegador em modo app: {erro}")
        webbrowser.open(url)
        return None


def _inicializar_banco_e_backup():
    """Executa a inicialização das tabelas, dados padrão e backup automático de segurança."""
    try:
        from database.conexao import inicializar_banco
        inicializar_banco()
    except Exception as erro:
        print(f"[Sistema] Aviso ao verificar tabelas do banco: {erro}")

    try:
        from controllers.config_ctrl import popular_dados_padrao
        popular_dados_padrao()
    except Exception as erro:
        print(f"[Sistema] Aviso ao popular dados padrão: {erro}")

    try:
        from backup import disparar_backup
        disparar_backup(motivo="inicialização")
    except Exception as erro:
        print(f"[Sistema] Aviso ao disparar backup inicial: {erro}")


def inicializar():
    """Fluxo principal do Launcher do Sistema Desktop Kanemberg v2."""
    print("[Sistema] Iniciando Sistema de Gestão Kanemberg v2 (Modo App Widescreen)...")

    # ① Inicializa banco e dispara backup automático em background
    _inicializar_banco_e_backup()

    # ② Verifica se a porta 8000 já está respondendo (ex.: iniciar_mobile.bat aberto)
    servidor_ja_ativo = _servidor_esta_ativo()
    servidor_uvicorn = None

    if servidor_ja_ativo:
        print(f"[Sistema] Servidor já ativo em {URL_SISTEMA_APP}. Reaproveitando instância...")
    else:
        print(f"[Sistema] Subindo servidor FastAPI na porta {PORTA_API}...")
        servidor_uvicorn, _ = _iniciar_servidor_background()
        if not _aguardar_servidor(timeout_segundos=5.0):
            print("[Sistema] Aviso: O servidor demorou mais de 5s, mas tentaremos abrir a janela.")

    # ③ Abre a janela nativa Widescreen (--app=http://localhost:8000/sistema --start-maximized)
    proc_janela = _abrir_janela_app(URL_SISTEMA_APP)

    # ④ Se o servidor foi iniciado por este main.py, mantém vivo enquanto a janela estiver aberta
    if not servidor_ja_ativo and servidor_uvicorn is not None:
        try:
            if proc_janela is not None:
                inicio_proc = time.monotonic()
                proc_janela.wait()
                duracao = time.monotonic() - inicio_proc
                # Caso o navegador tenha delegado a janela a outro processo existente (< 2s),
                # mantém o servidor vivo em loop até encerramento manual (Ctrl+C / fechamento)
                if duracao < 2.0:
                    while True:
                        time.sleep(1.0)
            else:
                while True:
                    time.sleep(1.0)
        except KeyboardInterrupt:
            pass
        finally:
            servidor_uvicorn.should_exit = True

    # ⑤ Backup de segurança no encerramento limpo
    try:
        from backup import disparar_backup
        t_backup = disparar_backup(motivo="encerramento")
        if t_backup:
            t_backup.join(timeout=8)
    except Exception:
        pass

    print("[Sistema] Encerramento limpo concluído.")


if __name__ == "__main__":
    inicializar()
