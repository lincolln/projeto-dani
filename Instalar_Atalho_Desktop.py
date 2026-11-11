r"""
Instalar_Atalho_Desktop.py — Gerador do Ícone Oficial (.ico) e Atalho Profissional
do Sistema Kanemberg v2 na Área de Trabalho (OneDrive\Desktop ou Desktop local).

- Gera 'static/icon.ico' a partir de 'static/icon-512.png' (ou 'static/icon-192.png')
  com múltiplos tamanhos nativos do Windows (256, 128, 64, 48, 32, 16).
- Obtém o caminho real da Área de Trabalho via WScript.Shell.SpecialFolders("Desktop").
- Cria o atalho 'Sistema Kanemberg.lnk' apontando para 'Iniciar_Kanemberg.bat'
  com IconLocation absoluto para 'static/icon.ico' e WindowStyle = 7 (Minimizado).
- Remove lançadores/atalhos antigos duplicados da Área de Trabalho com os.unlink().
"""

import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ICO_PATH = os.path.abspath(os.path.join(STATIC_DIR, "icon.ico"))
BAT_PATH = os.path.abspath(os.path.join(BASE_DIR, "Iniciar_Kanemberg.bat"))
SHORTCUT_NAME = "Sistema Kanemberg.lnk"

ATALHOS_ANTIGOS = (
    "Kanemberg - Sistema PC.lnk",
    "Kanemberg - App Celular HTTPS.lnk",
    "Kanemberg - Sistema PC.bat",
    "Kanemberg - App Celular HTTPS.bat",
    "Kanemberg_Sistema_PC.bat",
    "abrir_sistema_pc.bat",
    "iniciar_mobile.bat",
)


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
    """Obtém o caminho real da Área de Trabalho usando WScript.Shell.SpecialFolders('Desktop')."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        res = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=flags,
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


def limpar_atalhos_antigos_desktop(desktop_dir: str) -> list[str]:
    """Remove apenas os atalhos/lançadores antigos duplicados na Área de Trabalho via os.unlink."""
    removidos = []
    if not os.path.isdir(desktop_dir):
        return removidos

    for nome in ATALHOS_ANTIGOS:
        alvo = os.path.join(desktop_dir, nome)
        if os.path.isfile(alvo):
            try:
                os.unlink(alvo)
                removidos.append(alvo)
            except Exception as exc:
                print(f"[AVISO] Nao foi possivel remover atalho antigo {alvo}: {exc}")
    return removidos


def criar_atalho_desktop() -> str:
    """Cria o atalho 'Sistema Kanemberg.lnk' no Desktop real com WindowStyle=7 (Minimizado)."""
    ico_gerado = gerar_icone_ico()
    desktop_dir = obter_pasta_desktop()
    removidos = limpar_atalhos_antigos_desktop(desktop_dir)
    for r in removidos:
        print(f"[LIMPEZA] Atalho antigo removido da Area de Trabalho: {r}")

    atalho_path = os.path.join(desktop_dir, SHORTCUT_NAME)

    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$desk = $ws.SpecialFolders('Desktop')
$lnk = $ws.CreateShortcut((Join-Path $desk '{SHORTCUT_NAME}'))
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
