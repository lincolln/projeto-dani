"""
Instalar_Atalho_Desktop.py — Gerador do Ícone Oficial (.ico) e Atalho Profissional
do Sistema Kanemberg v2 na Área de Trabalho (Windows).

- Gera 'static/icon.ico' a partir de 'static/icon-512.png' (ou 'static/icon-192.png')
  com múltiplos tamanhos nativos do Windows (256, 128, 64, 48, 32, 16).
- Cria o atalho 'Sistema Kanemberg.lnk' na Área de Trabalho apontando para
  'Iniciar_Kanemberg.bat' com WindowStyle = 7 (Minimizado na barra de tarefas).
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ICO_PATH = os.path.join(STATIC_DIR, "icon.ico")
BAT_PATH = os.path.join(BASE_DIR, "Iniciar_Kanemberg.bat")
SHORTCUT_NAME = "Sistema Kanemberg.lnk"


def gerar_icone_ico() -> str:
    """Converte static/icon-512.png (ou icon-192.png / logo_kanemberg.png) para static/icon.ico."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    candidatos_png = [
        os.path.join(STATIC_DIR, "icon-512.png"),
        os.path.join(STATIC_DIR, "icon-192.png"),
        os.path.join(BASE_DIR, "logo_kanemberg.png"),
    ]
    origem_png = next((p for p in candidatos_png if os.path.isfile(p)), None)
    if not origem_png:
        return ICO_PATH

    try:
        from PIL import Image

        with Image.open(origem_png) as img:
            img_rgba = img.convert("RGBA")
            tamanhos = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
            img_rgba.save(ICO_PATH, format="ICO", sizes=tamanhos)
    except Exception as exc:
        print(f"[AVISO] Nao foi possivel converter PNG para ICO via Pillow: {exc}")

    return ICO_PATH


def obter_pasta_desktop() -> str:
    """Descobre o caminho real da Área de Trabalho do usuário no Windows (incluindo OneDrive)."""
    try:
        res = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "[Environment]::GetFolderPath('Desktop')",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        caminho = (res.stdout or "").strip()
        if caminho and os.path.isdir(caminho):
            return caminho
    except Exception:
        pass

    userprofile = os.environ.get("USERPROFILE", "")
    for cand in (
        os.path.join(userprofile, "OneDrive", "Desktop"),
        os.path.join(userprofile, "OneDrive", "Área de Trabalho"),
        os.path.join(userprofile, "Desktop"),
    ):
        if cand and os.path.isdir(cand):
            return cand
    return os.path.join(userprofile, "Desktop")


def criar_atalho_desktop() -> str:
    """Cria o atalho 'Sistema Kanemberg.lnk' na Área de Trabalho com WindowStyle=7 (Minimizado)."""
    ico_gerado = gerar_icone_ico()
    desktop_dir = obter_pasta_desktop()
    atalho_path = os.path.join(desktop_dir, SHORTCUT_NAME)

    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut('{atalho_path.replace("'", "''")}')
$lnk.TargetPath = '{BAT_PATH.replace("'", "''")}'
$lnk.WorkingDirectory = '{BASE_DIR.replace("'", "''")}'
$lnk.IconLocation = '{ico_gerado.replace("'", "''")},0'
$lnk.WindowStyle = 7
$lnk.Description = 'Sistema Kanemberg v2 — Gestao Comercial, PDV e App Mobile'
$lnk.Save()
"""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    res = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=flags,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Erro ao criar atalho via WScript.Shell: {res.stderr}")

    return atalho_path


if __name__ == "__main__":
    caminho_lnk = criar_atalho_desktop()
    print(f"[OK] Icone oficial: {ICO_PATH} ({os.path.getsize(ICO_PATH) if os.path.isfile(ICO_PATH) else 0} bytes)")
    print(f"[OK] Atalho criado com sucesso em: {caminho_lnk}")
