"""
utils_impressao.py — Motor de Impressão de Etiquetas Térmicas (Kanemberg PDV v4)

Gera etiquetas comerciais em formato de imagem (PNG) com:
  • Nome da loja (Kanemberg)
  • Código de barras (Code128 ou EAN-13)
  • Tamanho em fonte grande
  • Preço legível

Dependências:
  pip install python-barcode Pillow
"""

import os
import sys
import tempfile
import functools
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

# ── Tentativa de importar qrcode e python-barcode ───────────────────────────
try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    _TEM_QRCODE = True
except ImportError:
    _TEM_QRCODE = False

try:
    import barcode
    from barcode.writer import ImageWriter
    _TEM_BARCODE = True
except ImportError:
    _TEM_BARCODE = False


# ════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE LAYOUT (proporção 40mm × 30mm a 300 DPI)
# ════════════════════════════════════════════════════════════════════════════

_DPI           = 300
_ETIQUETA_W_MM = 40
_ETIQUETA_H_MM = 30

# Converte mm para pixels: 1mm = DPI / 25.4 px
_MM_PX = _DPI / 25.4
_ETQ_W = int(_ETIQUETA_W_MM * _MM_PX)   # ~472 px
_ETQ_H = int(_ETIQUETA_H_MM * _MM_PX)   # ~354 px

_NOME_LOJA = "KANEMBERG"

# Cores
_COR_FUNDO  = (255, 255, 255)
_COR_TEXTO  = (30, 30, 30)
_COR_PRECO  = (180, 30, 30)
_COR_ACCENT = (200, 160, 60)


# ════════════════════════════════════════════════════════════════════════════
# FONTES — fallback seguro para Windows e Linux
# ════════════════════════════════════════════════════════════════════════════

@functools.lru_cache(maxsize=32)
def _carregar_fonte(tamanho: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Tenta carregar Segoe UI / Arial. Fallback para default do Pillow."""
    nomes = []
    if bold:
        nomes += ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
    else:
        nomes += ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]

    for nome in nomes:
        try:
            return ImageFont.truetype(nome, tamanho)
        except (OSError, IOError):
            pass

    # Último recurso
    try:
        return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", tamanho)
    except Exception:
        return ImageFont.load_default()


# ════════════════════════════════════════════════════════════════════════════
# GERADOR DE CÓDIGO DE BARRAS (imagem PIL)
# ════════════════════════════════════════════════════════════════════════════

# ── Tabela Code128-B simplificada para fallback manual ─────────────────────
_CODE128B_START = [2, 1, 1, 4, 1, 2]
_CODE128_STOP   = [2, 3, 3, 1, 1, 1, 2]
_CODE128B_PATTERNS = {
    ' ': [2,1,2,2,4,1], '!': [2,2,2,1,4,1], '"': [2,2,2,2,4,1],
    '#': [1,2,1,1,2,4], '$': [1,2,1,4,2,1], '%': [1,4,1,1,2,2],
    '&': [1,4,1,2,2,1], "'": [1,1,2,2,4,1], '(': [1,2,2,1,4,1],
    ')': [1,2,2,4,1,1], '*': [1,1,4,2,2,1], '+': [1,2,4,1,2,1],
    ',': [1,2,4,2,2,1], '-': [4,1,1,2,2,1], '.': [4,2,1,1,2,1],
    '/': [4,2,1,2,2,1], '0': [2,1,2,1,4,2], '1': [2,1,2,4,1,2],
    '2': [2,4,2,1,1,2], '3': [4,1,2,1,2,2], '4': [2,1,1,1,4,4],
    '5': [2,1,4,1,1,4], '6': [4,1,1,1,2,4], '7': [4,1,1,4,2,1],
    '8': [2,1,4,4,1,1], '9': [4,1,1,1,4,2], ':': [1,1,2,1,4,2],
    ';': [1,1,2,4,1,2], '<': [1,4,2,1,1,2], '=': [1,1,4,1,2,2],
    '>': [1,1,4,2,1,2], '?': [1,2,4,2,1,1], '@': [1,1,1,2,4,2],
    'A': [1,4,1,2,1,2], 'B': [1,2,1,2,4,2], 'C': [1,2,4,2,1,2],
    'D': [1,1,4,1,4,1], 'E': [1,4,2,1,2,1], 'F': [4,1,2,1,1,2],
    'G': [2,1,1,4,1,4], 'H': [2,1,1,2,1,4], 'I': [2,1,1,2,4,1],
    'J': [2,4,1,2,1,1], 'K': [2,1,4,1,1,2], 'L': [2,1,4,2,1,1],
    'M': [4,1,1,2,1,2], 'N': [2,4,1,1,1,2], 'O': [4,2,1,1,1,2],
    'P': [1,1,2,4,2,1], 'Q': [1,1,4,2,2,1], 'R': [1,2,2,4,2,1],
    'S': [1,2,4,1,4,1], 'T': [1,1,2,1,2,4], 'U': [1,2,1,1,2,4],
    'V': [1,2,1,4,1,2], 'W': [1,4,2,1,2,1], 'X': [1,2,4,1,2,1],
    'Y': [2,1,1,2,4,1], 'Z': [2,1,1,4,2,1],
}
# Valores numéricos Code128-B (para checksum)
_CODE128B_VALUES = {}
for _i, _c in enumerate(range(32, 127)):
    _CODE128B_VALUES[chr(_c)] = _i

_ALL_PATTERNS_LIST = list(_CODE128B_PATTERNS.values())
_ALL_CHARS_LIST = list(_CODE128B_PATTERNS.keys())


def _desenhar_barcode_manual(codigo: str, largura: int, altura: int = 80) -> Image.Image | None:
    """Desenha um código de barras Code128-B manualmente com PIL como fallback."""
    try:
        # Montar sequência de módulos (barras e espaços)
        modulos = list(_CODE128B_START)  # Start Code B (valor 104)

        checksum = 104
        for pos, ch in enumerate(codigo, start=1):
            padrao = _CODE128B_PATTERNS.get(ch)
            if padrao is None:
                # Caractere não suportado, usa espaço
                padrao = _CODE128B_PATTERNS[' ']
            modulos.extend(padrao)
            val = _CODE128B_VALUES.get(ch, 0)
            checksum += val * pos

        # Checksum
        checksum_val = checksum % 103
        # Encontrar padrão do checksum (mapeamento inverso)
        if checksum_val < len(_ALL_PATTERNS_LIST):
            modulos.extend(_ALL_PATTERNS_LIST[checksum_val])
        else:
            modulos.extend(_CODE128B_PATTERNS['0'])

        modulos.extend(_CODE128_STOP)

        # Calcular largura total em módulos
        total_modulos = sum(modulos)
        if total_modulos == 0:
            return None

        # Escalar para caber na largura desejada
        escala = largura / total_modulos
        if escala < 1:
            escala = 1

        img_w = int(total_modulos * escala)
        img_h = altura
        img = Image.new("RGB", (img_w, img_h), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        x = 0
        is_bar = True  # Começa com barra
        for modulo in modulos:
            w = int(modulo * escala)
            if is_bar:
                draw.rectangle([x, 0, x + w - 1, img_h - 1], fill=(0, 0, 0))
            x += w
            is_bar = not is_bar

        # Redimensionar para a largura desejada mantendo proporção
        if img.width != largura:
            img = img.resize((largura, img_h), Image.Resampling.NEAREST)

        return img
    except Exception:
        return None


def _gerar_barcode_image(codigo: str, largura: int) -> Image.Image | None:
    """Gera uma imagem PIL do código de barras usando python-barcode.
    Se falhar, usa fallback manual desenhando com PIL."""

    # ── Tentativa 1: python-barcode ─────────────────────────────────────
    if _TEM_BARCODE:
        # Escolhe o formato pelo tamanho do código
        if len(codigo) == 13 and codigo.isdigit():
            tipo = "ean13"
        elif len(codigo) == 8 and codigo.isdigit():
            tipo = "ean8"
        else:
            tipo = "code128"

        try:
            writer = ImageWriter()
            bc = barcode.get(tipo, codigo, writer=writer)

            buffer = BytesIO()
            bc.write(buffer, options={
                "module_width":  0.3,
                "module_height": 8.0,
                "font_size":     8,
                "text_distance": 2.0,
                "quiet_zone":    2.0,
                "write_text":    True,
            })
            buffer.seek(0)
            img = Image.open(buffer).convert("RGBA")

            # Manter proporção original do código de barras
            novo_h = img.height
            fator = novo_h / img.height
            nova_largura = int(img.width * fator)
            if nova_largura > largura:
                fator = largura / img.width
                nova_largura = largura
                novo_h = int(img.height * fator)
            img = img.resize((nova_largura, novo_h), Image.Resampling.NEAREST)
            return img
        except Exception as e:
            print(f"[Kanemberg] Aviso: python-barcode falhou ({e}), usando fallback manual.")

    # ── Tentativa 2: desenho manual ─────────────────────────────────────
    img = _desenhar_barcode_manual(codigo, largura, altura=80)
    if img:
        return img

    return None


# ════════════════════════════════════════════════════════════════════════════
# GERADOR DE QR CODE (imagem PIL)
# ════════════════════════════════════════════════════════════════════════════

def _gerar_qrcode_image(conteudo: str, tamanho_px: int = 195) -> Image.Image:
    """Gera uma imagem PIL com QR Code de alta nitidez e resolução para etiquetas térmicas."""
    if _TEM_QRCODE:
        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=ERROR_CORRECT_M,
                box_size=8,
                border=1,
            )
            qr.add_data(conteudo)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            if tamanho_px:
                img = img.resize((tamanho_px, tamanho_px), Image.Resampling.NEAREST)
            return img
        except Exception as e:
            print(f"[Kanemberg] Erro ao gerar QR Code via qrcode: {e}")

    # Fallback simples caso a lib qrcode falhe
    img = Image.new("RGB", (tamanho_px, tamanho_px), _COR_FUNDO)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (tamanho_px - 1, tamanho_px - 1)], outline=(0, 0, 0), width=3)
    draw.text((10, tamanho_px // 2 - 10), conteudo, fill=(0, 0, 0))
    return img


def gerar_qrcode_preview(conteudo: str, tamanho_px: int = 250) -> Image.Image:
    """Gera uma imagem PIL de QR Code avulsa para exibição em janelas de preview na tela."""
    return _gerar_qrcode_image(conteudo, tamanho_px)


# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL — GERAR ETIQUETA COM QR CODE
# ════════════════════════════════════════════════════════════════════════════

def gerar_etiqueta(
    codigo_barras: str,
    nome_produto:  str,
    tamanho:       str,
    preco:         float,
    quantidade:    int = 1,
    diretorio:     str | None = None,
) -> str | None:
    """Gera uma imagem PNG com o layout da etiqueta comercial com QR Code.

    Args:
        codigo_barras: Código identificador (ex: 'KNB000010001').
        nome_produto:  Nome/modelo do produto.
        tamanho:       Tamanho da peça (ex: "M", "42").
        preco:         Preço de venda.
        quantidade:    Quantidade de etiquetas (repetições na mesma imagem).
        diretorio:     Pasta onde salvar. Se None, usa temp do SO.

    Returns:
        Caminho absoluto do arquivo PNG gerado, ou None em caso de erro.
    """
    if not diretorio:
        diretorio = tempfile.gettempdir()

    # ── Fontes ────────────────────────────────────────────────────────────
    font_loja    = _carregar_fonte(26, bold=True)
    font_produto = _carregar_fonte(16, bold=True)
    font_codigo  = _carregar_fonte(13, bold=True)
    font_tam_lbl = _carregar_fonte(13)
    font_tam_val = _carregar_fonte(36, bold=True)
    font_preco   = _carregar_fonte(28, bold=True)

    # ── Cria uma etiqueta individual (40mm × 30mm a 300 DPI) ──────────────
    etq = Image.new("RGB", (_ETQ_W, _ETQ_H), _COR_FUNDO)
    draw = ImageDraw.Draw(etq)

    margem_x = 18
    y_cursor = 10

    # 1. Nome da loja (topo, centralizado)
    bbox_loja = draw.textbbox((0, 0), _NOME_LOJA, font=font_loja)
    w_loja = bbox_loja[2] - bbox_loja[0]
    draw.text(
        ((_ETQ_W - w_loja) // 2, y_cursor),
        _NOME_LOJA,
        fill=_COR_ACCENT,
        font=font_loja,
    )
    y_cursor += (bbox_loja[3] - bbox_loja[1]) + 4

    # Linha divisória dourada
    draw.line(
        [(margem_x, y_cursor), (_ETQ_W - margem_x, y_cursor)],
        fill=_COR_ACCENT, width=2,
    )
    y_cursor += 6

    # 2. Nome do produto (truncado se muito longo)
    nome_display = nome_produto[:26] + "…" if len(nome_produto) > 26 else nome_produto
    bbox_prod = draw.textbbox((0, 0), nome_display, font=font_produto)
    w_prod = bbox_prod[2] - bbox_prod[0]
    draw.text(
        ((_ETQ_W - w_prod) // 2, y_cursor),
        nome_display,
        fill=_COR_TEXTO,
        font=font_produto,
    )
    y_cursor += (bbox_prod[3] - bbox_prod[1]) + 8

    # 3. Miolo: QR Code na esquerda + Dados do produto na direita
    qr_size = 195
    qr_x = margem_x + 6
    qr_y = y_cursor

    qr_img = _gerar_qrcode_image(codigo_barras, qr_size)
    etq.paste(qr_img, (qr_x, qr_y))

    # Painel direito
    dir_x = qr_x + qr_size + 14

    # Código legível (para operador conferir)
    draw.text((dir_x, qr_y + 4), "CÓDIGO:", fill=(110, 110, 110), font=font_tam_lbl)
    draw.text((dir_x, qr_y + 20), codigo_barras, fill=_COR_TEXTO, font=font_codigo)

    # Divisor suave
    draw.line([(dir_x, qr_y + 46), (_ETQ_W - margem_x, qr_y + 46)], fill=(220, 220, 220), width=1)

    # Tamanho da peça
    draw.text((dir_x, qr_y + 54), "TAMANHO:", fill=(110, 110, 110), font=font_tam_lbl)
    draw.text((dir_x, qr_y + 70), str(tamanho).upper(), fill=_COR_TEXTO, font=font_tam_val)

    # Divisor suave
    draw.line([(dir_x, qr_y + 124), (_ETQ_W - margem_x, qr_y + 124)], fill=(220, 220, 220), width=1)

    # Preço de venda
    preco_text = f"R$ {preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    draw.text((dir_x, qr_y + 130), "PREÇO:", fill=(110, 110, 110), font=font_tam_lbl)
    draw.text((dir_x, qr_y + 148), preco_text, fill=_COR_PRECO, font=font_preco)

    # ── Monta a folha final ───────────────────────────────────────────────
    if quantidade <= 1:
        folha = etq
        nome_arquivo = f"etiqueta_{codigo_barras}_{tamanho}.png"
        caminho = os.path.join(diretorio, nome_arquivo)
        folha.save(caminho, "PNG", dpi=(_DPI, _DPI))
        return caminho
    else:
        ultimo_caminho = None
        for i in range(1, quantidade + 1):
            nome_arquivo = f"etiqueta_{codigo_barras}_{tamanho}_{i}.png"
            caminho = os.path.join(diretorio, nome_arquivo)
            etq.save(caminho, "PNG", dpi=(_DPI, _DPI))
            imprimir_etiqueta(caminho)
            ultimo_caminho = caminho
        return ultimo_caminho


# ════════════════════════════════════════════════════════════════════════════
# IMPRESSÃO SILENCIOSA (Windows)
# ════════════════════════════════════════════════════════════════════════════

def imprimir_etiqueta(caminho_imagem: str) -> tuple[bool, str]:
    """Envia a imagem da etiqueta para a impressora padrão do Windows.

    Returns:
        Tupla (sucesso, mensagem).
    """
    if not os.path.exists(caminho_imagem):
        return False, f"Arquivo não encontrado: {caminho_imagem}"

    try:
        os.startfile(caminho_imagem, "print")
        return True, "Etiqueta enviada para a impressora padrão."
    except AttributeError:
        # Não está no Windows — fallback via lpr (Linux/Mac)
        try:
            import subprocess
            subprocess.run(["lpr", caminho_imagem], check=True)
            return True, "Etiqueta enviada para impressão (lpr)."
        except Exception as e:
            return False, f"Erro ao imprimir: {e}"
    except Exception as e:
        return False, f"Erro ao imprimir: {e}"
