"""
tela_cadastro.py — Cadastro de Produtos "Formulário Camaleão" em 2 Níveis (Pai/Filho)
=====================================================================================
Versão 6.0 — Hierarquia por 5 Grandes Grupos + Revelação Progressiva:
  • NÍVEL 1 (Topo em destaque): "1. ESCOLHA A CATEGORIA" com 5 Botões Grandes
    lado a lado (height=45):
      1) "👕 Parte de Cima"
      2) "👖 Parte de Baixo / Praia"
      3) "🩴 Calçados / Meias"
      4) "⌚ Acessórios"
      5) "🧴 Perfumaria"
    Enquanto nenhum grupo for clicado, todo o corpo do formulário abaixo
    (`self.frame_corpo_formulario`) permanece oculto (`pack_forget`).
  • NÍVEL 2 (Sub-opções dentro do grupo escolhido):
    Ao clicar em um grupo, revela o formulário abaixo e filtra o seletor de
    "Tipo de Peça" apenas para as peças daquele grupo (ou seleciona "Perfume"
    automaticamente no grupo Perfumaria).
  • Perfis Camaleão (A–E): rótulos, sugestões, visibilidade de Tecido/Cores
    e grade de tamanhos se adaptam automaticamente ao Grupo e Tipo escolhidos.
  • Persistência intacta: `estoque_ctrl.salvar_grade_dinamica()` grava em
    `produtos` / `produto_variacoes` com `modelo_nome = f"{tipo} {detalhe}".strip()`
    e `codigo_barras` `KNB...`.
"""

from __future__ import annotations

import os
import shutil
import sys
import unicodedata
from tkinter import messagebox, filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import estoque_ctrl, config_ctrl
from utils_cores import resolver_cor_hex, hex_para_display, DICIONARIO_CORES

# ── Paletas dinâmicas (claro, escuro — Tema Slate Dark Mobile) ──────────────
_BG_WINDOW    = ("#F0F2F8", "#0f172a")
_BG_CARD      = ("#FFFFFF", "#1e293b")
_BG_CARD_ALT  = ("#F4F6FB", "#0f172a")
_BG_HOVER     = ("#E8ECF4", "#334155")
_FG_PRIMARY   = ("#1A1D2E", "#f8fafc")
_FG_MUTED     = ("#6B7280", "#94a3b8")
_FG_LABEL     = ("#4B5563", "#cbd5e1")
_ACCENT_GOLD  = ("#d97706", "#f59e0b")
_ACCENT_BLUE  = ("#2563eb", "#3b82f6")
_ACCENT_GREEN = ("#16a34a", "#22c55e")
_BORDER       = ("#DDE3EE", "#334155")
_BTN_SAVE     = ("#16a34a", "#16a34a")
_BTN_SAVE_HV  = ("#15803d", "#15803d")
_BTN_BACK     = ("#374151", "#cbd5e1")
_BTN_IMG      = ("#4F46E5", "#6366F1")
_BTN_IMG_HV   = ("#3730A3", "#4F46E5")
_BTN_COR_ADD  = ("#065F46", "#10B981")

# Diretório de imagens
_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIR_IMAGENS  = os.path.join(_RAIZ_PROJETO, "imagens_produtos")

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DOS 5 GRANDES GRUPOS (FAMÍLIAS DE PRODUTOS)
# ════════════════════════════════════════════════════════════════════════════

_PLACEHOLDER_TIPO = "Selecione..."

# Tipos em que o "Nome / Detalhe do Modelo" é obrigatório
_DETALHE_OBRIGATORIO = {"Perfume", "Relógio", "Óculos", "Chinelo"}

# Cor automática usada quando o perfil esconde o seletor de cores (Perfumaria)
_COR_PADRAO_AUTO = ("Padrão", "#D4AF37")

_ORDEM_GRUPOS = ["A", "B", "C", "D", "E"]

_PERFIS: dict[str, dict] = {
    "A": {
        "chave":         "A",
        "botao":         "👕 Parte de Cima",
        "nome":          "Parte de Cima",
        "icone":         "👕",
        "tipos":         ["Blusa", "Camisa", "Camiseta", "Casaco", "Vestido"],
        "label_detalhe": "Detalhe do Modelo (Opcional — ex: Básica, Polo, Manga Longa...)",
        "placeholder_detalhe": "Ex: Básica, Polo, Oversized, Tricot...",
        "label_corte":   "Corte / Caimento",
        "opcoes_corte":  ["Regular", "Slim", "Oversized", "Regata", "Manga Longa"],
        "tecido":        True,
        "label_tecido":  "Tecido",
        "opcoes_tecido": ["Algodão", "Malha", "Moletom", "Linho", "Viscose"],
        "cores":         True,
        "tamanhos":      ["PP", "P", "M", "G", "GG", "XXG", "ÚNICO"],
        "unico_auto":    False,
    },
    "B": {
        "chave":         "B",
        "botao":         "👖 Parte de Baixo / Praia",
        "nome":          "Parte de Baixo / Praia",
        "icone":         "👖",
        "tipos":         ["Calça", "Shorts", "Bermuda", "Sunga"],
        "label_detalhe": "Detalhe do Modelo (Opcional — ex: Cargo, Skinny, Praia...)",
        "placeholder_detalhe": "Ex: Cargo, Jeans Skinny, Mauricinho...",
        "label_corte":   "Corte / Modelo",
        "opcoes_corte":  ["Reta", "Skinny", "Cargo", "Jogger", "Tradicional"],
        "tecido":        True,
        "label_tecido":  "Tecido",
        "opcoes_tecido": ["Jeans", "Sarja", "Tactel", "Moletom", "Lycra/Poliamida"],
        "cores":         True,
        "tamanhos":      ["P", "M", "G", "GG", "36", "38", "40", "42", "44", "46", "48"],
        "unico_auto":    False,
    },
    "C": {
        "chave":         "C",
        "botao":         "🩴 Calçados / Meias",
        "nome":          "Calçados / Meias",
        "icone":         "🩴",
        "tipos":         ["Chinelo", "Meia"],
        "label_detalhe": "Detalhe do Modelo (ex: Havaianas Top, Cano Alto...)",
        "placeholder_detalhe": "Ex: Havaianas Top, Kenner, Cano Alto...",
        "label_corte":   "Estilo / Cano",
        "opcoes_corte":  ["Slide", "Tradicional", "Correia", "Cano Alto", "Cano Baixo"],
        "tecido":        False,
        "label_tecido":  "Material",
        "opcoes_tecido": [],
        "cores":         True,
        "tamanhos":      ["35/36", "37/38", "39/40", "41/42", "43/44", "ÚNICO"],
        "unico_auto":    False,
    },
    "D": {
        "chave":         "D",
        "botao":         "⌚ Acessórios",
        "nome":          "Acessórios",
        "icone":         "⌚",
        "tipos":         ["Boné", "Óculos", "Relógio"],
        "label_detalhe": "Detalhe do Modelo (ex: G-Shock, Juliet, Aba Curva...)",
        "placeholder_detalhe": "Ex: G-Shock, Juliet, Aba Curva...",
        "label_corte":   "Formato / Estilo",
        "opcoes_corte":  ["Aba Curva", "Aba Reta", "Aviador", "Quadrado", "Digital", "Analógico"],
        "tecido":        True,
        "label_tecido":  "Material / Lente",
        "opcoes_tecido": ["Polarizado", "Metal", "Acetato", "Couro", "Silicone", "Tactel"],
        "cores":         True,
        "tamanhos":      ["ÚNICO"],
        "unico_auto":    True,
    },
    "E": {
        "chave":         "E",
        "botao":         "🧴 Perfumaria",
        "nome":          "Perfumaria",
        "icone":         "🧴",
        "tipos":         ["Perfume"],
        "label_detalhe": "Nome do Perfume * (Obrigatório — ex: Malbec, Kaiak, Asad...)",
        "placeholder_detalhe": "Ex: Malbec, Kaiak, Asad, 212 VIP...",
        "label_corte":   "Família / Gênero",
        "opcoes_corte":  ["Masculino", "Feminino", "Unissex", "Árabe", "Amadeirado", "Doce"],
        "tecido":        False,
        "label_tecido":  "Tecido",
        "opcoes_tecido": [],
        "cores":         False,
        "tamanhos":      ["30ml", "50ml", "100ml", "150ml", "200ml"],
        "unico_auto":    False,
    },
}

# Lista completa de tipos (mantida para compatibilidade e parsing de edição)
_TIPOS_PRODUTO = [_PLACEHOLDER_TIPO] + [
    t for g in _ORDEM_GRUPOS for t in _PERFIS[g]["tipos"]
]

# Ajustes finos por peça específica dentro de um grupo
_OVERRIDES_TIPO: dict[str, dict] = {
    "Chinelo": {
        "tecido":        False,
        "label_tecido":  "Material",
        "opcoes_tecido": [],
    },
    "Meia": {
        "tecido":        True,
        "label_tecido":  "Material",
        "opcoes_tecido": ["Algodão", "Poliamida", "Algodão/Poliamida"],
    },
}

_COLS_TAMANHOS = 4
_COLS_CORES    = 4


def _grupo_do_tipo(tipo: str) -> str:
    """Retorna a chave do grupo ('A'..'E') ao qual pertence a peça."""
    for chave in _ORDEM_GRUPOS:
        if tipo in _PERFIS[chave]["tipos"]:
            return chave
    return "A"


def _perfil_do_tipo(tipo: str, grupo_fallback: str = "A") -> dict:
    """Retorna a configuração efetiva (grupo + override da peça)."""
    base_key = _grupo_do_tipo(tipo) if tipo else grupo_fallback
    cfg = dict(_PERFIS.get(base_key, _PERFIS["A"]))
    cfg["chave"] = base_key
    if tipo:
        cfg.update(_OVERRIDES_TIPO.get(tipo, {}))
    return cfg


def _separar_tipo_detalhe(modelo_nome: str) -> tuple[str, str, bool]:
    """
    Separa um modelo_nome salvo ("Perfume Malbec") em (tipo, detalhe, reconhecido).
    Ignora diferenças de acentuação ("Calca" -> "Calça").
    Se nenhum tipo conhecido for prefixo, retorna (modelo_nome, "", False).
    """
    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s.casefold())
        return "".join(c for c in s if not unicodedata.combining(c))

    nome = (modelo_nome or "").strip()
    nome_n = _norm(nome)
    tipos = sorted(_TIPOS_PRODUTO[1:], key=len, reverse=True)
    for t in tipos:
        t_n = _norm(t)
        if nome_n == t_n:
            return t, "", True
        if nome_n.startswith(t_n + " "):
            return t, nome[len(t):].strip(), True
    return nome, "", False


# ════════════════════════════════════════════════════════════════════════════
# HELPER — círculo colorido mini (18×18) para os checkboxes de cor
# ════════════════════════════════════════════════════════════════════════════

_CACHE_CIRCULOS_MINI = {}


def _circulo_mini(hex_cor: str, size: int = 18) -> ctk.CTkImage:
    """Gera CTkImage de um círculo sólido anti-aliased na cor especificada."""
    cache_key = (hex_cor, size)
    if cache_key in _CACHE_CIRCULOS_MINI:
        return _CACHE_CIRCULOS_MINI[cache_key]

    hex_cor = hex_para_display(hex_cor, "#808080")
    if len(hex_cor) == 4:  # #RGB -> #RRGGBB
        hex_cor = "#" + hex_cor[1] * 2 + hex_cor[2] * 2 + hex_cor[3] * 2
    h = hex_cor.lstrip("#")
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, s - 2, s - 2), fill=(*rgb, 255))
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    _CACHE_CIRCULOS_MINI[cache_key] = img_ctk
    return img_ctk


# ════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

class TelaCadastro(ctk.CTkFrame):
    """
    Formulário Camaleão de Cadastro (Pai/Filho) em 2 níveis:
    Nível 1: 5 Grandes Grupos no topo -> Nível 2: Peças do Grupo + Campos adaptados.
    """

    def __init__(self, parent, controller, produto_id: int | None = None):
        super().__init__(parent, corner_radius=0, fg_color=_BG_WINDOW)
        self.controller  = controller
        self.produto_id  = produto_id
        self.caminho_imagem: str = ""

        # Estado do formulário
        self._grupo_atual: str = ""
        self._tipo_atual:  str = ""
        self._perfil:      dict = {}
        self._corpo_visivel = False

        # Botões dos 5 grupos no topo: {chave_grupo: CTkButton}
        self._btns_grupo: dict[str, ctk.CTkButton] = {}

        # Tamanhos vindos do banco na edição (preserva grafia exata)
        self._tam_existentes: list[str] = []

        # {tamanho: {"var", "chk", "entry", "cell"}}
        self._tam_rows: dict[str, dict] = {}
        # {nome_cor: {"var", "hex", "chk", "circ_lbl", "circ_img_ref", "cell"}}
        self._cor_rows: dict[str, dict] = {}

        self._circle_refs: list = []
        self._preview_ref = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construir_interface()

        if self.produto_id:
            self.after(100, self._carregar_produto_existente)

    # ════════════════════════════════════════════════════════════════════
    # DESTRUIÇÃO SEGURA
    # ════════════════════════════════════════════════════════════════════

    def destroy(self):
        """Limpa todos os estados e destrói filhos sem race condition."""
        self._tam_rows.clear()
        self._cor_rows.clear()
        self._btns_grupo.clear()
        self._circle_refs.clear()
        self._preview_ref = None
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        super().destroy()

    # ════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DA INTERFACE
    # ════════════════════════════════════════════════════════════════════

    def _construir_interface(self):
        # ── CABEÇALHO ────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_header.grid(row=0, column=0, sticky="ew", padx=25, pady=(18, 8))
        frame_header.grid_columnconfigure(0, weight=1)

        titulo = "✏️  Editar Produto" if self.produto_id else "➕  Cadastrar Novo Produto"
        ctk.CTkLabel(
            frame_header, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            frame_header, text="← Voltar ao Estoque",
            command=self.controller._ir_estoque,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=_BG_HOVER, text_color=_BTN_BACK, hover_color=_BORDER,
            corner_radius=8, height=34, width=165,
        ).grid(row=0, column=1, sticky="e")

        # ── ÁREA ROLÁVEL (todo o formulário) ─────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))

        self._construir_passo1_grupos(self._scroll)

        # Corpo do formulário — OCULTO até clicar em um dos 5 grupos
        self.frame_corpo_formulario = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self.frame_corpo_formulario.grid_columnconfigure(0, weight=5)
        self.frame_corpo_formulario.grid_columnconfigure(1, weight=6)
        self._construir_corpo(self.frame_corpo_formulario)

        # Aviso exibido enquanto nenhum grupo foi clicado
        self._lbl_aguardando = ctk.CTkLabel(
            self._scroll,
            text="👆  Clique em uma das 5 categorias acima para liberar o formulário.",
            font=ctk.CTkFont(family="Segoe UI", size=15),
            text_color=_FG_MUTED,
        )
        self._lbl_aguardando.pack(pady=30)

    # ─────────────────────────────────────────────────────────────────
    # NÍVEL 1 — 5 Grandes Grupos no Topo
    # ─────────────────────────────────────────────────────────────────

    def _construir_passo1_grupos(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=16,
            border_width=2, border_color=_ACCENT_BLUE,
        )
        card.pack(fill="x", padx=10, pady=(4, 12))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="1. ESCOLHA A CATEGORIA",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=_ACCENT_BLUE, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 2))

        ctk.CTkLabel(
            card,
            text="Selecione uma das 5 famílias de produtos para adaptar os campos e tamanhos automaticamente.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 12))

        # Barra com os 5 grandes botões lado a lado (height=45)
        frame_botoes = ctk.CTkFrame(card, fg_color="transparent")
        frame_botoes.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        for col in range(len(_ORDEM_GRUPOS)):
            frame_botoes.grid_columnconfigure(col, weight=1, uniform="grupo_top")

        for col, chave in enumerate(_ORDEM_GRUPOS):
            perfil_g = _PERFIS[chave]
            btn = ctk.CTkButton(
                frame_botoes,
                text=perfil_g["botao"],
                command=lambda k=chave: self._selecionar_grupo(k),
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color=_BG_CARD_ALT,
                hover_color=_BG_HOVER,
                text_color=_FG_PRIMARY,
                border_width=1,
                border_color=_BORDER,
                corner_radius=10,
                height=45,
            )
            btn.grid(row=0, column=col, sticky="ew", padx=4, pady=2)
            self._btns_grupo[chave] = btn

        self._lbl_perfil = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=_ACCENT_GOLD, anchor="w",
        )
        self._lbl_perfil.grid(row=3, column=0, sticky="ew", padx=22, pady=(2, 14))

    def _atualizar_destaque_botoes_grupo(self):
        """Destaca em azul o botão do grupo ativo e reseta os demais."""
        for chave, btn in self._btns_grupo.items():
            if chave == self._grupo_atual:
                btn.configure(
                    fg_color=_ACCENT_BLUE,
                    hover_color=("#1d4ed8", "#2563eb"),
                    text_color=("#FFFFFF", "#FFFFFF"),
                    border_color=_ACCENT_GOLD,
                    border_width=2,
                )
            else:
                btn.configure(
                    fg_color=_BG_CARD_ALT,
                    hover_color=_BG_HOVER,
                    text_color=_FG_PRIMARY,
                    border_color=_BORDER,
                    border_width=1,
                )

    # ─────────────────────────────────────────────────────────────────
    # CORPO — Nível 2 (Tipo de Peça + Detalhe) e Passos 3 a 5
    # ─────────────────────────────────────────────────────────────────

    def _novo_card(self, parent, titulo: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        return card

    def _label(self, parent, texto: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent, text=texto,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_FG_LABEL, anchor="w",
        )

    def _combo_editavel(self, parent) -> ctk.CTkComboBox:
        return ctk.CTkComboBox(
            parent, values=["—"], state="normal",
            font=ctk.CTkFont(family="Segoe UI", size=15),
            fg_color=_BG_CARD_ALT, border_color=_BORDER, border_width=1,
            button_color=_ACCENT_BLUE, button_hover_color=_ACCENT_GOLD,
            text_color=_FG_PRIMARY, corner_radius=8, height=38,
        )

    def _construir_corpo(self, corpo):
        # ── NÍVEL 2 — Tipo de Peça (filtrado pelo grupo) + Detalhe ───
        card2 = self._novo_card(corpo, "2. PEÇA E IDENTIFICAÇÃO DO MODELO")
        card2.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 12))

        frame_n2 = ctk.CTkFrame(card2, fg_color="transparent")
        frame_n2.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))
        frame_n2.grid_columnconfigure(0, weight=2)
        frame_n2.grid_columnconfigure(1, weight=5)

        # Coluna esquerda: Tipo de Peça (mostra apenas os itens do grupo)
        self._lbl_tipo_peca = ctk.CTkLabel(
            frame_n2, text="Tipo de Peça: *",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_FG_LABEL, anchor="w",
        )
        self._lbl_tipo_peca.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=(0, 4))

        self.combo_tipo = ctk.CTkComboBox(
            frame_n2,
            values=[_PLACEHOLDER_TIPO],
            state="readonly",
            command=self._on_tipo_selecionado,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=15),
            fg_color=_BG_CARD_ALT, border_color=_ACCENT_BLUE, border_width=1,
            button_color=_ACCENT_BLUE, button_hover_color=_ACCENT_GOLD,
            text_color=_FG_PRIMARY, corner_radius=8, height=45,
        )
        self.combo_tipo.set(_PLACEHOLDER_TIPO)
        self.combo_tipo.grid(row=1, column=0, sticky="ew", padx=(0, 12))

        # Coluna direita: Nome / Detalhe do Modelo
        self._lbl_detalhe = ctk.CTkLabel(
            frame_n2, text="Detalhe do Modelo:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_FG_LABEL, anchor="w",
        )
        self._lbl_detalhe.grid(row=0, column=1, sticky="ew", pady=(0, 4))

        self.entry_detalhe = ctk.CTkEntry(
            frame_n2,
            placeholder_text="Ex: Kaiak, Havaianas Top, G-Shock, Básica...",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color=_BG_CARD_ALT, border_color=_ACCENT_BLUE, border_width=1,
            text_color=_FG_PRIMARY, corner_radius=8, height=45,
        )
        self.entry_detalhe.grid(row=1, column=1, sticky="ew")
        self.entry_detalhe.bind("<KeyRelease>", lambda e: self._atualizar_preview_nome())

        self._lbl_preview_nome = ctk.CTkLabel(
            card2, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=_ACCENT_GREEN, anchor="w",
        )
        self._lbl_preview_nome.grid(row=2, column=0, sticky="ew", padx=20, pady=(2, 14))

        # ── PASSO 3 — Características (coluna esquerda) ──────────────
        card3 = self._novo_card(corpo, "3. CARACTERÍSTICAS")
        card3.grid(row=1, column=0, sticky="nsew", padx=(10, 6), pady=(0, 12))

        self._label(card3, "Marca: *").grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 2))
        self.combo_marca = self._combo_editavel(card3)
        marcas = config_ctrl.listar_nomes("marca")
        self.combo_marca.configure(values=marcas if marcas else ["—"])
        self.combo_marca.set("")
        self.combo_marca.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))

        self.lbl_corte = self._label(card3, "Corte:")
        self.lbl_corte.grid(row=3, column=0, sticky="ew", padx=20, pady=(6, 2))
        self.combo_corte = self._combo_editavel(card3)
        self.combo_corte.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 6))

        # Bloco de tecido (pode ser oculto pelo perfil)
        self._bloco_tecido = ctk.CTkFrame(card3, fg_color="transparent")
        self._bloco_tecido.grid_columnconfigure(0, weight=1)
        self.lbl_tecido = self._label(self._bloco_tecido, "Tecido:")
        self.lbl_tecido.grid(row=0, column=0, sticky="ew", pady=(6, 2))
        self.combo_tecido = self._combo_editavel(self._bloco_tecido)
        self.combo_tecido.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self._bloco_tecido.grid(row=5, column=0, sticky="ew", padx=20)

        # Preços lado a lado
        frame_precos = ctk.CTkFrame(card3, fg_color="transparent")
        frame_precos.grid(row=6, column=0, sticky="ew", padx=20, pady=(6, 4))
        frame_precos.grid_columnconfigure((0, 1), weight=1)
        for col, (label, attr) in enumerate([
            ("Preço Custo (R$): *", "entry_custo"),
            ("Preço Venda (R$): *", "entry_venda"),
        ]):
            self._label(frame_precos, label).grid(
                row=0, column=col, sticky="ew",
                padx=(0 if col == 0 else 6, 6 if col == 0 else 0), pady=(4, 2),
            )
            entry = ctk.CTkEntry(
                frame_precos, placeholder_text="0,00",
                font=ctk.CTkFont(family="Segoe UI", size=15),
                fg_color=_BG_CARD_ALT, border_color=_BORDER, border_width=1,
                text_color=_FG_PRIMARY, corner_radius=8, height=38,
            )
            entry.grid(
                row=1, column=col, sticky="ew",
                padx=(0 if col == 0 else 6, 6 if col == 0 else 0),
            )
            setattr(self, attr, entry)

        # Imagem (opcional, compacta)
        frame_img = ctk.CTkFrame(card3, fg_color="transparent")
        frame_img.grid(row=7, column=0, sticky="ew", padx=20, pady=(12, 16))
        frame_img.grid_columnconfigure(2, weight=1)

        self.lbl_preview = ctk.CTkLabel(
            frame_img, text="", fg_color=_BG_HOVER, corner_radius=8, width=48, height=48,
        )
        self.lbl_preview.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            frame_img, text="📷 Foto (opcional)",
            command=self._selecionar_imagem,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=_BTN_IMG, hover_color=_BTN_IMG_HV,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=32, width=140,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.lbl_imagem_confirmacao = ctk.CTkLabel(
            frame_img, text="Nenhuma imagem",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=_FG_MUTED, anchor="w", wraplength=180,
        )
        self.lbl_imagem_confirmacao.grid(row=0, column=2, sticky="ew", padx=(10, 0))

        # ── PASSO 4 e 5 — Tamanhos + Cores (coluna direita) ──────────
        coluna_dir = ctk.CTkFrame(corpo, fg_color="transparent")
        coluna_dir.grid(row=1, column=1, sticky="nsew", padx=(6, 10), pady=(0, 12))
        coluna_dir.grid_columnconfigure(0, weight=1)

        card4 = self._novo_card(coluna_dir, "4. TAMANHOS E QUANTIDADES")
        card4.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkLabel(
            card4, text="Marque os tamanhos e informe a quantidade de cada um.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))

        self._frame_tamanhos = ctk.CTkFrame(card4, fg_color="transparent")
        self._frame_tamanhos.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        for c in range(_COLS_TAMANHOS):
            self._frame_tamanhos.grid_columnconfigure(c, weight=1, uniform="tam")

        # Card de cores (oculto automaticamente no grupo Perfumaria)
        self._card_cores = self._novo_card(coluna_dir, "5. CORES")
        header_cor = ctk.CTkFrame(self._card_cores, fg_color="transparent")
        header_cor.grid(row=0, column=0, sticky="e", padx=20, pady=(14, 8))
        ctk.CTkButton(
            header_cor, text="+ Nova Cor",
            command=self._adicionar_cor_personalizada,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=_BTN_COR_ADD, hover_color=_ACCENT_GREEN,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=28, width=90,
        ).pack()

        self._frame_cores = ctk.CTkFrame(self._card_cores, fg_color="transparent")
        self._frame_cores.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        for c in range(_COLS_CORES):
            self._frame_cores.grid_columnconfigure(c, weight=1, uniform="cor")

        self._card_cores.grid(row=1, column=0, sticky="ew")

        # Aviso quando a cor é automática (Grupo E — Perfumaria)
        self._lbl_cor_auto = ctk.CTkLabel(
            coluna_dir,
            text=f"🟡  Cor definida automaticamente: {_COR_PADRAO_AUTO[0]} (Dourado)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=_ACCENT_GOLD, anchor="w",
        )

        self._popular_cores()

        # ── SALVAR ───────────────────────────────────────────────────
        ctk.CTkButton(
            corpo, text="💾  Salvar Produto",
            command=self._processar_salvamento,
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            fg_color=_BTN_SAVE, hover_color=_BTN_SAVE_HV,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=10, height=50,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 20))

    # ════════════════════════════════════════════════════════════════════
    # REVELAÇÃO PROGRESSIVA: NÍVEL 1 (GRUPO) -> NÍVEL 2 (TIPO DE PEÇA)
    # ════════════════════════════════════════════════════════════════════

    def _selecionar_grupo(self, chave_grupo: str, tipo_inicial: str | None = None):
        """
        Acionado ao clicar em um dos 5 grandes botões de Grupo no topo.
        Filtra o seletor de 'Tipo de Peça' para mostrar APENAS as peças do grupo
        e revela o corpo do formulário configurado para aquela categoria.
        """
        if chave_grupo not in _PERFIS:
            return

        self._grupo_atual = chave_grupo
        self._atualizar_destaque_botoes_grupo()

        pecas_grupo = list(_PERFIS[chave_grupo]["tipos"])
        if tipo_inicial and tipo_inicial not in pecas_grupo:
            pecas_grupo.append(tipo_inicial)

        self.combo_tipo.configure(values=pecas_grupo)

        # Seleciona a peça inicial (ou a 1ª peça do grupo; em Perfumaria já é "Perfume")
        peca_escolhida = tipo_inicial if (tipo_inicial and tipo_inicial in pecas_grupo) else pecas_grupo[0]
        self.combo_tipo.set(peca_escolhida)
        self._tipo_atual = peca_escolhida

        self._aplicar_perfil(_perfil_do_tipo(peca_escolhida, chave_grupo))
        self._mostrar_corpo()
        self.after(50, self.entry_detalhe.focus_set)

    def _on_tipo_selecionado(self, tipo: str):
        """
        Acionado ao escolher uma peça dentro do grupo (ou programaticamente).
        Se ainda nenhum grupo estiver ativo, descobre o grupo automaticamente.
        """
        tipo = (tipo or "").strip()
        if not tipo or tipo == _PLACEHOLDER_TIPO:
            self._tipo_atual = ""
            self._grupo_atual = ""
            self._perfil = {}
            self._atualizar_destaque_botoes_grupo()
            self._lbl_perfil.configure(text="")
            self._ocultar_corpo()
            return

        grupo_pertencente = _grupo_do_tipo(tipo)
        if self._grupo_atual != grupo_pertencente:
            self._selecionar_grupo(grupo_pertencente, tipo_inicial=tipo)
            return

        self._tipo_atual = tipo
        self._aplicar_perfil(_perfil_do_tipo(tipo, self._grupo_atual))
        self._mostrar_corpo()
        self.after(50, self.entry_detalhe.focus_set)

    def _mostrar_corpo(self):
        if not self._corpo_visivel:
            self._lbl_aguardando.pack_forget()
            self.frame_corpo_formulario.pack(fill="x", expand=True, pady=(0, 6))
            self._corpo_visivel = True

    def _ocultar_corpo(self):
        if self._corpo_visivel:
            self.frame_corpo_formulario.pack_forget()
            self._lbl_aguardando.pack(pady=30)
            self._corpo_visivel = False

    def _aplicar_perfil(self, perfil: dict):
        """Transforma rótulos, sugestões, visibilidade e grade conforme o perfil."""
        self._perfil = perfil
        tipo = self._tipo_atual

        pecas_txt = ", ".join(_PERFIS[self._grupo_atual]["tipos"]) if self._grupo_atual in _PERFIS else tipo
        self._lbl_perfil.configure(
            text=f"{perfil['icone']}  Grupo: {perfil['nome']} ({pecas_txt})   ·   "
                 f"Tamanhos: {', '.join(perfil['tamanhos'])}"
        )

        # Rótulo e placeholder do Detalhe do Modelo / Nome do Perfume
        if tipo == "Perfume":
            self._lbl_detalhe.configure(
                text="Nome do Perfume: * (Obrigatório — ex: Malbec, Kaiak, Asad)",
                text_color=_ACCENT_GOLD,
            )
        elif tipo in _DETALHE_OBRIGATORIO:
            self._lbl_detalhe.configure(
                text=f"Detalhe do Modelo: * (Obrigatório para {tipo})",
                text_color=_ACCENT_GOLD,
            )
        else:
            self._lbl_detalhe.configure(
                text=perfil.get("label_detalhe", "Detalhe do Modelo (Opcional):"),
                text_color=_FG_LABEL,
            )

        self.entry_detalhe.configure(
            placeholder_text=perfil.get(
                "placeholder_detalhe", "Ex: Kaiak, Havaianas Top, G-Shock, Básica..."
            )
        )
        self._atualizar_preview_nome()

        # Corte / Estilo / Formato / Família
        self.lbl_corte.configure(text=f"{perfil['label_corte']}:")
        valor_corte = self.combo_corte.get().strip()
        self.combo_corte.configure(values=perfil["opcoes_corte"] or ["—"])
        if valor_corte not in perfil["opcoes_corte"]:
            self.combo_corte.set("")

        # Tecido / Material / Lente
        if perfil["tecido"]:
            self.lbl_tecido.configure(text=f"{perfil['label_tecido']}:")
            valor_tec = self.combo_tecido.get().strip()
            self.combo_tecido.configure(values=perfil["opcoes_tecido"] or ["—"])
            if valor_tec not in perfil["opcoes_tecido"]:
                self.combo_tecido.set("")
            self._bloco_tecido.grid()
        else:
            self.combo_tecido.set("")
            self._bloco_tecido.grid_remove()

        # Cores
        if perfil["cores"]:
            self._lbl_cor_auto.grid_forget()
            self._card_cores.grid(row=1, column=0, sticky="ew")
        else:
            self._card_cores.grid_forget()
            self._lbl_cor_auto.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

        # Grade de tamanhos (preserva quantidades dos tamanhos que continuam)
        self._reconstruir_grade(perfil["tamanhos"])

        if perfil.get("unico_auto"):
            for tam, row in self._tam_rows.items():
                if tam.casefold() in ("único", "unico") and row["var"].get() != "on":
                    row["var"].set("on")
                    self._toggle_qty_entry(tam)
                    if row["entry"]:
                        self.after(80, row["entry"].focus_set)

    def _atualizar_preview_nome(self):
        if not self._tipo_atual:
            self._lbl_preview_nome.configure(text="")
            return
        nome = self._montar_modelo_nome()
        self._lbl_preview_nome.configure(text=f"Será salvo no banco como:  “{nome}”")

    def _montar_modelo_nome(self) -> str:
        detalhe = self.entry_detalhe.get().strip()
        return f"{self._tipo_atual} {detalhe}".strip()

    # ════════════════════════════════════════════════════════════════════
    # GRADE DE TAMANHOS — células dinâmicas
    # ════════════════════════════════════════════════════════════════════

    def _reconstruir_grade(self, lista_perfil: list[str]):
        """Reconstrói as células de tamanho mantendo quantidades já digitadas."""
        qtds_anteriores: dict[str, str] = {}
        for tam, row in self._tam_rows.items():
            if row["var"].get() == "on":
                qtd = row["entry"].get().strip() if row["entry"] else "1"
                qtds_anteriores[tam.casefold()] = qtd or "1"
            try:
                row["cell"].destroy()
            except Exception:
                pass
        self._tam_rows.clear()

        # Usa a grafia exata do banco quando bater (ex.: "Único" x "ÚNICO"),
        # evitando duplicar variações na edição.
        mapa_exist = {t.casefold(): t for t in self._tam_existentes}
        lista: list[str] = [mapa_exist.get(t.casefold(), t) for t in lista_perfil]
        vistos = {t.casefold() for t in lista}
        for t in self._tam_existentes:
            if t.casefold() not in vistos:
                lista.append(t)
                vistos.add(t.casefold())

        for idx, tam in enumerate(lista):
            self._adicionar_celula_tamanho(idx, tam)
            if tam.casefold() in qtds_anteriores:
                self._marcar_tamanho(tam, qtds_anteriores[tam.casefold()])

    def _adicionar_celula_tamanho(self, idx: int, tam: str):
        cell = ctk.CTkFrame(
            self._frame_tamanhos, fg_color=_BG_CARD_ALT, corner_radius=10,
            border_width=1, border_color=_BORDER, height=46,
        )
        cell.grid(
            row=idx // _COLS_TAMANHOS, column=idx % _COLS_TAMANHOS,
            sticky="ew", padx=4, pady=4,
        )

        var = ctk.StringVar(value="off")
        chk = ctk.CTkCheckBox(
            cell, text=tam, variable=var, onvalue="on", offvalue="off",
            command=lambda t=tam: self._toggle_qty_entry(t),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY, fg_color=_ACCENT_BLUE,
            hover_color=_ACCENT_GOLD, border_color=_BORDER,
            checkmark_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=5, width=20,
        )
        chk.pack(side="left", padx=(10, 4), pady=8)

        self._tam_rows[tam] = {"var": var, "chk": chk, "entry": None, "cell": cell}

    def _toggle_qty_entry(self, tam: str):
        """Cria/destrói o campo de quantidade dentro da célula do tamanho."""
        row = self._tam_rows.get(tam)
        if not row:
            return

        if row["var"].get() == "on":
            if row["entry"] is None:
                entry = ctk.CTkEntry(
                    row["cell"], placeholder_text="Qtd",
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    fg_color=_BG_CARD, border_color=_ACCENT_BLUE,
                    text_color=_FG_PRIMARY, corner_radius=8,
                    height=28, width=52, justify="center",
                )
                entry.insert(0, "1")
                entry.pack(side="right", padx=(4, 8), pady=8)
                entry.bind("<FocusIn>", lambda e, ent=entry: ent.select_range(0, "end"))
                row["entry"] = entry
            row["cell"].configure(border_color=_ACCENT_BLUE, border_width=2)
        else:
            if row["entry"]:
                try:
                    row["entry"].destroy()
                except Exception:
                    pass
                row["entry"] = None
            row["cell"].configure(border_color=_BORDER, border_width=1)

    def _marcar_tamanho(self, tam: str, qtd: str | int):
        row = self._tam_rows.get(tam)
        if not row:
            return
        row["var"].set("on")
        self._toggle_qty_entry(tam)
        if row["entry"]:
            row["entry"].delete(0, "end")
            row["entry"].insert(0, str(qtd))

    # ════════════════════════════════════════════════════════════════════
    # GRADE DE CORES — checkboxes + círculos dinâmicos
    # ════════════════════════════════════════════════════════════════════

    def _popular_cores(self):
        for nome_cor in config_ctrl.listar_nomes("cor"):
            self._adicionar_linha_cor(nome_cor)

    def _adicionar_linha_cor(self, nome_cor: str):
        if nome_cor in self._cor_rows:
            return
        idx = len(self._cor_rows)

        cell = ctk.CTkFrame(self._frame_cores, fg_color="transparent")
        cell.grid(row=idx // _COLS_CORES, column=idx % _COLS_CORES, sticky="w", padx=4, pady=3)

        var = ctk.StringVar(value="off")
        chk = ctk.CTkCheckBox(
            cell, text=nome_cor, variable=var, onvalue="on", offvalue="off",
            command=lambda n=nome_cor: self._toggle_cor(n),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=_FG_PRIMARY, fg_color=_ACCENT_BLUE,
            hover_color=_ACCENT_GOLD, border_color=_BORDER,
            checkmark_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=4, width=20,
        )
        chk.pack(side="left", padx=(6, 2))

        lbl_circ = ctk.CTkLabel(cell, text="", fg_color="transparent", width=18, height=18)
        lbl_circ.pack(side="left", padx=(2, 4))

        self._cor_rows[nome_cor] = {
            "var":          var,
            "hex":          DICIONARIO_CORES.get(nome_cor.strip().lower(), ""),
            "chk":          chk,
            "circ_lbl":     lbl_circ,
            "circ_img_ref": None,
            "cell":         cell,
        }

    def _toggle_cor(self, nome_cor: str):
        row = self._cor_rows.get(nome_cor)
        if not row:
            return

        if row["var"].get() == "on":
            hex_val = row["hex"]
            if not hex_val:
                hex_val = resolver_cor_hex(nome_cor, self)
                if not hex_val:
                    row["var"].set("off")
                    return
                row["hex"] = hex_val
            try:
                img = _circulo_mini(hex_val, 18)
                self._circle_refs.append(img)
                row["circ_img_ref"] = img
                row["circ_lbl"].configure(image=img)
            except Exception as e:
                print(f"[Cadastro] Erro ao gerar círculo para '{nome_cor}': {e}")
        else:
            row["circ_lbl"].configure(image=None)

    def _adicionar_cor_personalizada(self):
        dialog = ctk.CTkInputDialog(
            text="Digite o nome da nova cor (ex: 'Azul Petróleo'):",
            title="Nova Cor Personalizada",
        )
        nome_cor = dialog.get_input()
        if not nome_cor or not nome_cor.strip():
            return
        nome_cor = nome_cor.strip()

        if nome_cor in self._cor_rows:
            self._cor_rows[nome_cor]["var"].set("on")
            self._toggle_cor(nome_cor)
            return

        from tkinter.colorchooser import askcolor
        resultado = askcolor(
            color="#808080", parent=self,
            title=f"Selecione a cor exata para '{nome_cor}'",
        )
        if not resultado or not resultado[1]:
            return

        self._adicionar_linha_cor(nome_cor)
        row = self._cor_rows[nome_cor]
        row["hex"] = resultado[1].upper()
        row["var"].set("on")
        self._toggle_cor(nome_cor)

    # ════════════════════════════════════════════════════════════════════
    # SELEÇÃO DE IMAGEM
    # ════════════════════════════════════════════════════════════════════

    def _exibir_preview(self, caminho: str):
        try:
            img = Image.open(caminho).resize((48, 48), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
            self._preview_ref = ctk_img
            self.lbl_preview.configure(image=ctk_img, text="")
        except Exception:
            self.lbl_preview.configure(text="🖼", font=ctk.CTkFont(size=22))

    def _selecionar_imagem(self):
        caminho_origem = filedialog.askopenfilename(
            title="Selecionar Imagem do Produto",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg"), ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")],
        )
        if not caminho_origem:
            return

        os.makedirs(_DIR_IMAGENS, exist_ok=True)
        nome_arquivo    = os.path.basename(caminho_origem)
        caminho_destino = os.path.join(_DIR_IMAGENS, nome_arquivo)
        try:
            shutil.copy2(caminho_origem, caminho_destino)
        except shutil.SameFileError:
            pass
        except Exception as e:
            messagebox.showerror("Erro ao copiar imagem", str(e))
            return

        self.caminho_imagem = caminho_destino
        self.lbl_imagem_confirmacao.configure(text=f"✅ {nome_arquivo}", text_color=_ACCENT_GREEN)
        self._exibir_preview(caminho_destino)

    # ════════════════════════════════════════════════════════════════════
    # SALVAMENTO MESTRE / DETALHE
    # ════════════════════════════════════════════════════════════════════

    def _processar_salvamento(self):
        if not self._tipo_atual or self._tipo_atual == _PLACEHOLDER_TIPO:
            messagebox.showerror("Campo obrigatório", "Escolha a Categoria e o Tipo de Peça.")
            return

        perfil  = self._perfil or _perfil_do_tipo(self._tipo_atual, self._grupo_atual or "A")
        detalhe = self.entry_detalhe.get().strip()

        if self._tipo_atual in _DETALHE_OBRIGATORIO and not detalhe:
            campo_nome = "Nome do Perfume" if self._tipo_atual == "Perfume" else f"Detalhe do Modelo para {self._tipo_atual}"
            messagebox.showerror(
                "Campo obrigatório",
                f"Informe o {campo_nome}.\n"
                f"{perfil.get('placeholder_detalhe', '')}",
            )
            self.entry_detalhe.focus_set()
            return

        modelo_nome = self._montar_modelo_nome()
        marca  = self.combo_marca.get().strip()
        corte  = self.combo_corte.get().strip()
        tecido = self.combo_tecido.get().strip() if perfil["tecido"] else ""
        if corte == "—":
            corte = ""
        if tecido == "—":
            tecido = ""

        if not marca or marca == "—":
            messagebox.showerror("Campo obrigatório", "Informe a Marca.")
            return

        # ── Preços ────────────────────────────────────────────────────
        try:
            custo_str = self.entry_custo.get().strip().replace(",", ".")
            venda_str = self.entry_venda.get().strip().replace(",", ".")
            custo = float(custo_str) if custo_str else 0.0
            venda = float(venda_str) if venda_str else 0.0
        except ValueError:
            messagebox.showerror("Preço inválido", "Os preços devem ser números (use ponto ou vírgula).")
            return

        if venda <= 0 and not messagebox.askyesno(
            "Atenção", "O Preço de Venda está zerado. Deseja salvar mesmo assim?"
        ):
            return

        # ── Tamanhos ──────────────────────────────────────────────────
        tamanhos_com_qtd: dict[str, int] = {}
        erros_qtd: list[str] = []
        for tam, row in self._tam_rows.items():
            if row["var"].get() != "on":
                continue
            qty_str = (row["entry"].get().strip() if row["entry"] else "") or "1"
            try:
                qty = int(qty_str)
                if qty < 0:
                    raise ValueError
                tamanhos_com_qtd[tam] = qty
            except ValueError:
                erros_qtd.append(f"Tamanho '{tam}': quantidade inválida ('{qty_str}').")

        if erros_qtd:
            messagebox.showerror("Quantidades inválidas", "Corrija os campos:\n" + "\n".join(erros_qtd))
            return
        if not tamanhos_com_qtd:
            messagebox.showerror("Sem tamanhos", "Marque pelo menos um tamanho e informe a quantidade.")
            return

        # ── Cores ─────────────────────────────────────────────────────
        if not perfil["cores"]:
            cores_com_hex = [_COR_PADRAO_AUTO]
        else:
            cores_com_hex: list[tuple[str, str]] = []
            cores_sem_hex: list[str] = []
            for nome_cor, row in self._cor_rows.items():
                if row["var"].get() != "on":
                    continue
                hex_val = row["hex"] or resolver_cor_hex(nome_cor, self)
                if not hex_val:
                    cores_sem_hex.append(nome_cor)
                    continue
                row["hex"] = hex_val
                cores_com_hex.append((nome_cor, hex_val))

            if cores_sem_hex:
                messagebox.showwarning(
                    "Cores sem hexadecimal",
                    "As cores abaixo foram ignoradas (sem hex definido):\n"
                    f"{', '.join(cores_sem_hex)}\n\n"
                    "Clique em cada cor novamente para escolher o tom.",
                )
            if not cores_com_hex:
                messagebox.showerror("Sem cores", "Selecione pelo menos uma cor.")
                return

        # ── Persistência (formato intacto) ────────────────────────────
        try:
            sucesso, msg = estoque_ctrl.salvar_grade_dinamica(
                modelo_nome      = modelo_nome,
                marca            = marca,
                tecido           = tecido,
                corte            = corte,
                tamanhos_com_qtd = tamanhos_com_qtd,
                cores_com_hex    = cores_com_hex,
                preco_custo      = custo,
                preco_venda      = venda,
                foto_path        = self.caminho_imagem or None,
                produto_id       = self.produto_id,
            )
        except Exception as e:
            messagebox.showerror("Erro inesperado", str(e))
            return

        if sucesso:
            messagebox.showinfo("Sucesso!", msg)
            self.controller._ir_estoque()
        else:
            messagebox.showerror("Erro ao salvar", msg)

    # ════════════════════════════════════════════════════════════════════
    # CARREGAMENTO PARA EDIÇÃO
    # ════════════════════════════════════════════════════════════════════

    def _carregar_produto_existente(self):
        dados = estoque_ctrl.buscar_produto_completo(self.produto_id)
        if not dados:
            messagebox.showwarning(
                "Produto não encontrado",
                f"Não foi possível carregar o produto ID {self.produto_id}.",
            )
            return

        variacoes = dados.get("variacoes", []) or []

        # Tamanhos existentes (grafia exata do banco) — antes de montar a grade
        self._tam_existentes = []
        for v in variacoes:
            t = (v.get("tamanho") or "").strip()
            if t and t not in self._tam_existentes:
                self._tam_existentes.append(t)

        # Tipo + detalhe a partir do modelo_nome salvo
        tipo, detalhe, reconhecido = _separar_tipo_detalhe(dados.get("modelo_nome", ""))
        grupo_alvo = _grupo_do_tipo(tipo) if reconhecido else "A"

        self.entry_detalhe.delete(0, "end")
        if detalhe:
            self.entry_detalhe.insert(0, detalhe)

        self.combo_marca.set(dados.get("marca", "") or "")
        corte_salvo  = dados.get("corte", "") or ""
        tecido_salvo = dados.get("tecido", "") or ""

        # Seleciona o grupo e a peça correspondente, revelando o formulário
        self._selecionar_grupo(grupo_alvo, tipo_inicial=tipo or None)
        self.combo_corte.set(corte_salvo)
        if self._perfil.get("tecido"):
            self.combo_tecido.set(tecido_salvo)

        if not variacoes:
            return

        # Preços / foto da primeira variação
        primeira = variacoes[0]
        self.entry_custo.delete(0, "end")
        self.entry_custo.insert(0, f"{primeira.get('preco_custo', 0.0):.2f}")
        self.entry_venda.delete(0, "end")
        self.entry_venda.insert(0, f"{primeira.get('preco_venda', 0.0):.2f}")

        foto_existente = primeira.get("foto_path")
        if foto_existente and os.path.exists(foto_existente):
            self.caminho_imagem = foto_existente
            self.lbl_imagem_confirmacao.configure(
                text=f"✅ {os.path.basename(foto_existente)}", text_color=_ACCENT_GREEN,
            )
            self._exibir_preview(foto_existente)

        # Quantidades por tamanho
        for row in self._tam_rows.values():
            row["var"].set("off")
        for tam in list(self._tam_rows):
            self._toggle_qty_entry(tam)

        estoque_por_tam: dict[str, int] = {}
        for v in variacoes:
            tam = (v.get("tamanho") or "").strip()
            if not tam:
                continue
            if v.get("cor"):
                estoque_por_tam.setdefault(tam, v.get("estoque", 0))
            else:
                estoque_por_tam[tam] = estoque_por_tam.get(tam, 0) + v.get("estoque", 0)

        for tam, qtd_total in estoque_por_tam.items():
            if tam not in self._tam_rows:
                self._adicionar_celula_tamanho(len(self._tam_rows), tam)
            self._marcar_tamanho(tam, qtd_total)

        # Cores salvas no pai (cores_tags)
        if self._perfil.get("cores"):
            for nome_c, hex_c in dados.get("cores_lista", []):
                if nome_c not in self._cor_rows:
                    self._adicionar_linha_cor(nome_c)
                row = self._cor_rows[nome_c]
                if hex_c:
                    row["hex"] = hex_c
                row["var"].set("on")
                self._toggle_cor(nome_c)
