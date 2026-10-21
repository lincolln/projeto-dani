"""
utils_cores.py — Utilitário de Cores para o Sistema Kanemberg
================================================================
Responsabilidades:
  1. Manter um dicionário padrão que mapeia nomes de cores comuns
     para seus respectivos códigos hexadecimais.
  2. Resolver automaticamente o hex de qualquer cor digitada pelo Daniel:
       • Se o nome estiver no dicionário → retorna o hex diretamente.
       • Se NÃO estiver → abre o Círculo de Cores nativo do Windows
         (tkinter.colorchooser.askcolor) para seleção visual.
  3. Fornecer utilitários de contraste para renderização dos círculos
     coloridos nos cards da vitrine.
"""

from __future__ import annotations

import re


# ──────────────────────────────────────────────────────────────────────────────
# DICIONÁRIO PADRÃO  (nome normalizado → hexadecimal)
# ──────────────────────────────────────────────────────────────────────────────

DICIONARIO_CORES: dict[str, str] = {
    # ── Neutros ──────────────────────────────────────────────────────────────
    "preto":         "#1A1A1A",
    "branco":        "#F8F8F8",
    "cinza":         "#808080",
    "cinza claro":   "#C0C0C0",
    "cinza escuro":  "#404040",
    "chumbo":        "#3D3D3D",
    "off white":     "#FAF9F6",
    "creme":         "#FFFDD0",
    "marfim":        "#FFFFF0",

    # ── Azuis ────────────────────────────────────────────────────────────────
    "azul":          "#1E90FF",
    "azul claro":    "#87CEEB",
    "azul escuro":   "#00008B",
    "azul marinho":  "#001F5B",
    "azul royal":    "#4169E1",
    "azul turquesa": "#40E0D0",
    "turquesa":      "#40E0D0",
    "azul petróleo": "#005F73",
    "petroleo":      "#005F73",
    "jeans":         "#3A6FA5",
    "denim":         "#3A6FA5",

    # ── Vermelhos e rosas ────────────────────────────────────────────────────
    "vermelho":      "#DC143C",
    "vermelho escuro":"#8B0000",
    "rosa":          "#FF69B4",
    "rosa claro":    "#FFB6C1",
    "rosa escuro":   "#C71585",
    "pink":          "#FF1493",
    "salmão":        "#FA8072",
    "salmon":        "#FA8072",
    "coral":         "#FF6B6B",
    "bordo":         "#800020",
    "vinho":         "#722F37",
    "marsala":       "#955251",

    # ── Verdes ───────────────────────────────────────────────────────────────
    "verde":         "#228B22",
    "verde claro":   "#90EE90",
    "verde escuro":  "#006400",
    "verde militar": "#4B5320",
    "verde oliva":   "#808000",
    "oliva":         "#808000",
    "verde musgo":   "#8A9A5B",
    "musgo":         "#8A9A5B",
    "mint":          "#98FF98",
    "verde água":    "#00CED1",
    "esmeralda":     "#50C878",
    "verde limão":   "#9ACD32",

    # ── Amarelos e laranjas ──────────────────────────────────────────────────
    "amarelo":       "#FFD700",
    "amarelo claro": "#FFFFE0",
    "amarelo escuro":"#FFB300",
    "laranja":       "#FF8C00",
    "laranja claro": "#FFB347",
    "mostarda":      "#FFDB58",
    "ouro":          "#FFD700",

    # ── Roxos ────────────────────────────────────────────────────────────────
    "roxo":          "#8B008B",
    "roxo claro":    "#DA70D6",
    "violeta":       "#7F00FF",
    "lilás":         "#C8A2C8",
    "lilas":         "#C8A2C8",
    "lavanda":       "#E6E6FA",
    "ametista":      "#9966CC",
    "uva":           "#6F2DA8",

    # ── Marrons e terrosos ───────────────────────────────────────────────────
    "marrom":        "#8B4513",
    "marrom claro":  "#A0522D",
    "marrom escuro": "#5C3317",
    "caramelo":      "#C68642",
    "bege":          "#F5F5DC",
    "caqui":         "#C3B091",
    "khaki":         "#C3B091",
    "areia":         "#D4B896",
    "nude":          "#E8BEAC",
    "cobre":         "#B87333",
    "café":          "#6F4E37",
    "cafe":          "#6F4E37",
    "chocolate":     "#7B3F00",
    "terracota":     "#CC4E38",

    # ── Tons especiais ───────────────────────────────────────────────────────
    "prata":         "#C0C0C0",
    "dourado":       "#D4AF37",
    "bronze":        "#CD7F32",
    "neon verde":    "#39FF14",
    "neon laranja":  "#FF6700",
    "neon rosa":     "#FF6EC7",
    "tie dye":       "#9B59B6",
}


# ──────────────────────────────────────────────────────────────────────────────
# NORMALIZAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

_MAPA_ACENTOS = str.maketrans(
    "áàãâéêíîóôõúûç",
    "aaaaeeiiooouuc"
)

def _normalizar(nome: str) -> str:
    """Remove acentos simples e normaliza espaços/case para comparação."""
    nome = nome.strip().lower()
    nome = nome.translate(_MAPA_ACENTOS)
    return " ".join(nome.split())


# ──────────────────────────────────────────────────────────────────────────────
# RESOLUÇÃO PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

def resolver_cor_hex(nome_cor: str, parent_widget=None, permitir_dialog: bool = True) -> str | None:
    """Resolve o hexadecimal de uma cor pelo nome.

    Fluxo:
      1. Tenta encontrar o nome no ``DICIONARIO_CORES`` (case/acento insensível).
      2. Se não encontrar, abre o seletor de cor nativo do Windows
         (``tkinter.colorchooser.askcolor``).
      3. Retorna o código hex (ex: '#FFD700') ou None se o usuário cancelar.

    Args:
        nome_cor:      Nome da cor digitado pelo usuário (ex: 'Azul Marinho').
        parent_widget: Widget tkinter pai para posicionar o color picker.

    Returns:
        String no formato '#RRGGBB' ou None.
    """
    chave = _normalizar(nome_cor)

    # ── 1. Busca no dicionário padrão ─────────────────────────────────────
    if chave in DICIONARIO_CORES:
        return DICIONARIO_CORES[chave]

    # ── 2. Busca parcial (ex: "escuro" -> "azul escuro") ──────────────────
    # Só vale se o texto digitado for um fragmento (palavras inteiras) de
    # UMA única cor do dicionário. Nunca o inverso: "rosa bebe" não deve
    # cair em "rosa". Cores compostas desconhecidas abrem o seletor.
    palavras = set(chave.split())
    candidatos = [
        hex_val for nome_dict, hex_val in DICIONARIO_CORES.items()
        if palavras and palavras <= set(nome_dict.split())
    ]
    if len(candidatos) == 1:
        return candidatos[0]

    # ── 3. Color Picker nativo do Windows ─────────────────────────────────
    if not permitir_dialog:
        return None

    try:
        from tkinter.colorchooser import askcolor

        cor_inicial = "#808080"  # cinza como ponto de partida visual

        resultado = askcolor(
            color=cor_inicial,
            parent=parent_widget,
            title=f"Selecione a cor exata para '{nome_cor}'",
        )
        # resultado = ((R, G, B), '#rrggbb') ou (None, None) se cancelado
        if resultado and resultado[1]:
            return resultado[1].upper()
    except Exception as e:
        print(f"[utils_cores] Erro ao abrir color picker: {e}")

    return None


# ──────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS DE CONTRASTE
# ──────────────────────────────────────────────────────────────────────────────

def _hex_para_rgb(hex_str: str) -> tuple[int, int, int]:
    """Converte '#RRGGBB' ou '#RGB' para tupla (R, G, B)."""
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return r, g, b


def cor_texto_sobre_fundo(hex_fundo: str) -> str:
    """Retorna '#FFFFFF' ou '#1A1A1A' dependendo da luminância do fundo.

    Garante contraste mínimo WCAG AA para texto sobre círculos coloridos.

    Args:
        hex_fundo: Cor de fundo no formato '#RRGGBB'.

    Returns:
        Cor do texto adequada para o fundo.
    """
    try:
        r, g, b = _hex_para_rgb(hex_fundo)
        # Luminância relativa (fórmula ITU-R BT.709)
        luminancia = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        return "#1A1A1A" if luminancia > 0.45 else "#FFFFFF"
    except Exception:
        return "#FFFFFF"


_RE_HEX = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")

def hex_valido(hex_str: str) -> bool:
    """Valida se uma string é um hexadecimal de cor válido (#RRGGBB ou #RGB)."""
    if not hex_str:
        return False
    return bool(_RE_HEX.match(hex_str.strip()))


def hex_para_display(hex_str: str, fallback: str = "#808080") -> str:
    """Retorna o hex se válido, ou o fallback (cinza) se inválido/vazio."""
    return hex_str.strip() if hex_valido(hex_str) else fallback


# ──────────────────────────────────────────────────────────────────────────────
# AUTO-TESTE
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    testes = ["Preto", "Azul Marinho", "Mostarda", "Cor de Rosa", "Petróleo", "xpto123"]
    print("=== Teste do Dicionário de Cores ===")
    for nome in testes:
        resultado = resolver_cor_hex(nome)
        print(f"  {nome!r:25} → {resultado}")
