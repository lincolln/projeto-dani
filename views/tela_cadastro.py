"""
tela_cadastro.py — Cadastro de Produtos com Grade Dinâmica (Pai/Filho)
=======================================================================
Versão 4.0 — Totalmente reescrito com:
  • Seletor de Grade: [Letra: PP..XXG] ou [Número: 34..52]
  • Campos de Quantidade individuais por tamanho, gerados/destruídos
    dinamicamente ao marcar/desmarcar cada checkbox (sem freeze).
  • Integração com utils_cores.py: círculo colorido ao selecionar cor +
    color picker automático para cores fora do dicionário.
  • Salvamento Mestre/Detalhe via estoque_ctrl.salvar_grade_dinamica():
    INSERT no produto pai → N INSERTs nas variações (cor × tamanho)
    com cor_hex e codigo_barras gerado automaticamente.
  • destroy() seguro — nunca chama root.update() nem root.mainloop().
"""

from __future__ import annotations

import os
import shutil
import sys
import tkinter as tk
from tkinter import messagebox, filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import estoque_ctrl, config_ctrl
from utils_cores import resolver_cor_hex, hex_para_display, DICIONARIO_CORES

# ── Paletas dinâmicas (claro, escuro) ───────────────────────────────────────
_BG_WINDOW    = ("#F0F2F8", "#0F1117")
_BG_CARD      = ("#FFFFFF", "#16191F")
_BG_CARD_ALT  = ("#F9FAFB", "#1C202B")
_BG_HOVER     = ("#E8ECF4", "#22273A")
_FG_PRIMARY   = ("#1A1D2E", "#F0F2F8")
_FG_MUTED     = ("#6B7280", "#8A8FA8")
_FG_LABEL     = ("#4B5563", "#A0A8C0")
_ACCENT_GOLD  = ("#B8861F", "#E1B12C")
_ACCENT_BLUE  = ("#1B4F8A", "#2D7DD2")
_ACCENT_GREEN = ("#1B7A4C", "#059669")
_BORDER       = ("#DDE3EE", "#22273A")
_BTN_SAVE     = ("#1B7A4C", "#059669")
_BTN_SAVE_HV  = ("#155F3C", "#047857")
_BTN_BACK     = ("#374151", "#A0A8C0")
_BTN_IMG      = ("#4F46E5", "#7C83FD")
_BTN_IMG_HV   = ("#3730A3", "#6366F1")
_BTN_COR_ADD  = ("#065F46", "#10B981")

# Diretório de imagens
_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIR_IMAGENS  = os.path.join(_RAIZ_PROJETO, "imagens_produtos")

# Grades de tamanhos padrão
_GRADE_LETRA  = ["PP", "P", "M", "G", "GG", "XG", "XXG", "Único"]
_GRADE_NUMERO = [str(n) for n in range(34, 54, 2)]  # 34, 36, 38 … 52


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
        hex_cor = '#' + hex_cor[1]*2 + hex_cor[2]*2 + hex_cor[3]*2
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
    Cadastro de Grade de Produtos (Pai/Filho) com quantidades dinâmicas
    e integração total com o banco de dados atualizado.
    """

    def __init__(self, parent, controller, produto_id: int | None = None):
        super().__init__(parent, corner_radius=0, fg_color=_BG_WINDOW)
        self.controller  = controller
        self.produto_id  = produto_id
        self.caminho_imagem: str = ""

        # ── Estado do Grade Builder ──────────────────────────────────
        # {tamanho: {"var": StringVar, "chk": CTkCheckBox, "entry": CTkEntry|None}}
        self._tam_rows: dict[str, dict] = {}

        # {nome_cor: {"var": StringVar, "hex": str, "circ_lbl": CTkLabel|None,
        #             "circ_img_ref": CTkImage|None, "chk": CTkCheckBox}}
        self._cor_rows: dict[str, dict] = {}

        # Referências anti-GC dos círculos de cor
        self._circle_refs: list = []

        # Referências anti-GC de imagens
        self._preview_ref = None

        # Grid raiz
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

        titulo = "✏️  Editar Grade do Produto" if self.produto_id else "➕  Cadastrar Nova Grade"
        ctk.CTkLabel(
            frame_header,
            text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=_FG_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            frame_header,
            text="← Voltar ao Estoque",
            command=self.controller._ir_estoque,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=_BG_HOVER,
            text_color=_BTN_BACK,
            hover_color=_BORDER,
            corner_radius=8,
            height=34,
            width=165,
        ).grid(row=0, column=1, sticky="e")

        # ── CORPO — duas colunas ──────────────────────────────────────
        frame_corpo = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_corpo.grid(row=1, column=0, sticky="nsew", padx=25, pady=5)
        frame_corpo.grid_columnconfigure(0, weight=5)
        frame_corpo.grid_columnconfigure(1, weight=6)
        frame_corpo.grid_rowconfigure(0, weight=1)

        self._construir_col_atributos(frame_corpo)
        self._construir_col_grade(frame_corpo)

        # ── BOTÃO SALVAR ──────────────────────────────────────────────
        ctk.CTkButton(
            self,
            text="💾  Salvar Grade de Produtos",
            command=self._processar_salvamento,
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            fg_color=_BTN_SAVE,
            hover_color=_BTN_SAVE_HV,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=10,
            height=48,
        ).grid(row=2, column=0, sticky="ew", padx=25, pady=(10, 22))

    # ─────────────────────────────────────────────────────────────────
    # COLUNA ESQUERDA — Atributos do Produto + Imagem
    # ─────────────────────────────────────────────────────────────────

    def _construir_col_atributos(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=14,
            border_width=1, border_color=_BORDER,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        card.grid_columnconfigure(0, weight=1)

        # Título
        ctk.CTkLabel(
            card,
            text="📋  Características do Modelo",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=_FG_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 12))

        # Carrega atributos do banco
        tipos   = config_ctrl.listar_nomes("tipo_peca")
        marcas  = config_ctrl.listar_nomes("marca")
        tecidos = config_ctrl.listar_nomes("tecido")
        cortes  = config_ctrl.listar_nomes("corte")

        campos = [
            ("Tipo / Peça: *",  tipos,   "combo_tipo"),
            ("Marca: *",        marcas,  "combo_marca"),
            ("Tecido:",         tecidos, "combo_tecido"),
            ("Corte:",          cortes,  "combo_corte"),
        ]

        for linha, (label_txt, valores, attr) in enumerate(campos, start=1):
            ctk.CTkLabel(
                card, text=label_txt,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=_FG_LABEL, anchor="w",
            ).grid(row=linha * 2 - 1, column=0, sticky="ew", padx=20, pady=(8, 2))

            combo = ctk.CTkComboBox(
                card,
                values=valores if valores else ["—"],
                state="readonly",
                font=ctk.CTkFont(family="Segoe UI", size=15),
                fg_color=_BG_WINDOW,
                border_color=_BORDER,
                button_color=_ACCENT_BLUE,
                button_hover_color=_ACCENT_GOLD,
                text_color=_FG_PRIMARY,
                corner_radius=8,
                height=36,
            )
            combo.grid(row=linha * 2, column=0, sticky="ew", padx=20, pady=(0, 4))
            setattr(self, attr, combo)

        if cortes and "Regular" in cortes:
            self.combo_corte.set("Regular")
        elif cortes:
            self.combo_corte.set(cortes[0])

        # ── Preços ────────────────────────────────────────────────────
        row_preco = len(campos) * 2 + 1

        for i, (label, attr_entry) in enumerate([
            ("Preço Custo (R$): *", "entry_custo"),
            ("Preço Venda (R$): *", "entry_venda"),
        ]):
            ctk.CTkLabel(
                card, text=label,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=_FG_LABEL, anchor="w",
            ).grid(row=row_preco + i * 2, column=0, sticky="ew", padx=20, pady=(10, 2))
            entry = ctk.CTkEntry(
                card, placeholder_text="0,00",
                font=ctk.CTkFont(family="Segoe UI", size=15),
                fg_color=_BG_WINDOW, border_color=_BORDER,
                text_color=_FG_PRIMARY, corner_radius=8, height=36,
            )
            entry.grid(row=row_preco + i * 2 + 1, column=0, sticky="ew", padx=20, pady=(0, 4))
            setattr(self, attr_entry, entry)

        # ── Separador ────────────────────────────────────────────────
        row_img = row_preco + 5
        ctk.CTkFrame(card, height=1, corner_radius=0, fg_color=_BORDER).grid(
            row=row_img, column=0, sticky="ew", padx=14, pady=(8, 10)
        )

        # ── Imagem ────────────────────────────────────────────────────
        ctk.CTkLabel(
            card, text="Imagem do Produto:",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_LABEL, anchor="w",
        ).grid(row=row_img + 1, column=0, sticky="ew", padx=20, pady=(0, 6))

        frame_img_btn = ctk.CTkFrame(card, fg_color="transparent")
        frame_img_btn.grid(row=row_img + 2, column=0, sticky="ew", padx=20, pady=(0, 6))
        frame_img_btn.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            frame_img_btn, text="Selecionar 📷",
            command=self._selecionar_imagem,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=_BTN_IMG, hover_color=_BTN_IMG_HV,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=34, width=140,
        ).grid(row=0, column=0, sticky="w")

        self.lbl_imagem_confirmacao = ctk.CTkLabel(
            frame_img_btn,
            text="Nenhuma imagem selecionada",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=_FG_MUTED, anchor="w", wraplength=160,
        )
        self.lbl_imagem_confirmacao.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        self.lbl_preview = ctk.CTkLabel(
            card, text="",
            fg_color=_BG_HOVER, corner_radius=8, width=90, height=90,
        )
        self.lbl_preview.grid(row=row_img + 3, column=0, sticky="w", padx=20, pady=(0, 16))

    # ─────────────────────────────────────────────────────────────────
    # COLUNA DIREITA — Grade Builder (Tipo + Tamanhos + Cores)
    # ─────────────────────────────────────────────────────────────────

    def _construir_col_grade(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=14,
            border_width=1, border_color=_BORDER,
        )
        card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=3)   # área de tamanhos expande
        card.grid_rowconfigure(5, weight=2)   # área de cores expande

        # Título
        ctk.CTkLabel(
            card,
            text="👕  Variações da Grade",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))

        # ── 1. Seletor do tipo de grade ───────────────────────────────
        frame_tipo = ctk.CTkFrame(card, fg_color=_BG_CARD_ALT, corner_radius=10)
        frame_tipo.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        frame_tipo.grid_columnconfigure(0, weight=1)
        frame_tipo.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame_tipo, text="Tipo de Grade:",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_LABEL,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 6))

        self._var_tipo_grade = ctk.StringVar(value="letra")

        self._rb_letra = ctk.CTkRadioButton(
            frame_tipo,
            text="Letra  (PP → XXG)",
            variable=self._var_tipo_grade,
            value="letra",
            command=self._reconstruir_grade,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY,
            fg_color=_ACCENT_BLUE,
            hover_color=_ACCENT_GOLD,
        )
        self._rb_letra.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        self._rb_numero = ctk.CTkRadioButton(
            frame_tipo,
            text="Número  (34 → 52)",
            variable=self._var_tipo_grade,
            value="numero",
            command=self._reconstruir_grade,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY,
            fg_color=_ACCENT_BLUE,
            hover_color=_ACCENT_GOLD,
        )
        self._rb_numero.grid(row=1, column=1, sticky="w", padx=12, pady=(0, 10))

        # ── 2. Label seção tamanhos ───────────────────────────────────
        ctk.CTkLabel(
            card,
            text="Tamanhos  —  marque e informe a quantidade:",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 4))

        # ── 3. Frame de tamanhos (ScrollableFrame) ────────────────────
        self._frame_tamanhos = ctk.CTkScrollableFrame(
            card,
            fg_color=_BG_CARD_ALT,
            corner_radius=10,
            border_width=1,
            border_color=_BORDER,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self._frame_tamanhos.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 8))
        # Coluna 0 = checkbox, coluna 1 = entry Qtd, coluna 2 = espaçador
        self._frame_tamanhos.grid_columnconfigure(0, weight=0, minsize=90)
        self._frame_tamanhos.grid_columnconfigure(1, weight=0, minsize=70)
        self._frame_tamanhos.grid_columnconfigure(2, weight=1)

        # ── 4. Label seção cores ──────────────────────────────────────
        frame_cor_header = ctk.CTkFrame(card, fg_color="transparent")
        frame_cor_header.grid(row=4, column=0, sticky="ew", padx=20, pady=(4, 4))
        frame_cor_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame_cor_header,
            text="Cores  —  marque para selecionar:",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # Botão para adicionar cor nova (color picker direto)
        ctk.CTkButton(
            frame_cor_header,
            text="+ Nova Cor",
            command=self._adicionar_cor_personalizada,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=_BTN_COR_ADD,
            hover_color=_ACCENT_GREEN,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8,
            height=28,
            width=90,
        ).grid(row=0, column=1, sticky="e")

        # ── 5. Frame de cores (ScrollableFrame) ───────────────────────
        self._frame_cores = ctk.CTkScrollableFrame(
            card,
            fg_color=_BG_CARD_ALT,
            corner_radius=10,
            border_width=1,
            border_color=_BORDER,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self._frame_cores.grid(row=5, column=0, sticky="nsew", padx=20, pady=(0, 14))
        # Col 0 = checkbox, col 1 = círculo colorido, col 2 = espaçador
        self._frame_cores.grid_columnconfigure(0, weight=0, minsize=130)
        self._frame_cores.grid_columnconfigure(1, weight=0, minsize=26)
        self._frame_cores.grid_columnconfigure(2, weight=1)

        # Popula os widgets iniciais
        self._reconstruir_grade()
        self._popular_cores()

    # ════════════════════════════════════════════════════════════════════
    # GRADE DE TAMANHOS — construção dinâmica
    # ════════════════════════════════════════════════════════════════════

    def _reconstruir_grade(self):
        """Destrói os widgets de tamanho atuais e reconstrói com o novo tipo."""
        # Destrói tudo dentro do frame de tamanhos
        for row_data in self._tam_rows.values():
            try:
                row_data["chk"].destroy()
            except Exception:
                pass
            if row_data.get("entry"):
                try:
                    row_data["entry"].destroy()
                except Exception:
                    pass
        self._tam_rows.clear()

        # Escolhe a lista de tamanhos
        if self._var_tipo_grade.get() == "letra":
            lista = _GRADE_LETRA
        else:
            lista = _GRADE_NUMERO

        for idx, tam in enumerate(lista):
            self._adicionar_linha_tamanho(idx, tam)

    def _adicionar_linha_tamanho(self, row_idx: int, tam: str):
        """Cria um checkbox de tamanho na linha row_idx do grid."""
        var = ctk.StringVar(value="off")

        chk = ctk.CTkCheckBox(
            self._frame_tamanhos,
            text=tam,
            variable=var,
            onvalue="on",
            offvalue="off",
            command=lambda t=tam: self._toggle_qty_entry(t),
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=_FG_PRIMARY,
            fg_color=_ACCENT_BLUE,
            hover_color=_ACCENT_GOLD,
            border_color=_BORDER,
            checkmark_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=5,
            width=80,
        )
        chk.grid(row=row_idx, column=0, sticky="w", padx=(10, 4), pady=5)

        self._tam_rows[tam] = {
            "var":   var,
            "chk":   chk,
            "entry": None,     # criado dinamicamente ao marcar
            "row":   row_idx,
        }

    def _toggle_qty_entry(self, tam: str):
        """
        Cria ou destrói o CTkEntry de quantidade ao lado do checkbox.
        Chamado automaticamente ao marcar/desmarcar cada tamanho.
        """
        row_data = self._tam_rows.get(tam)
        if not row_data:
            return

        if row_data["var"].get() == "on":
            # ── Cria o entry de quantidade ────────────────────────────
            entry = ctk.CTkEntry(
                self._frame_tamanhos,
                placeholder_text="Qtd",
                font=ctk.CTkFont(family="Segoe UI", size=15),
                fg_color=_BG_WINDOW,
                border_color=_ACCENT_BLUE,
                text_color=_FG_PRIMARY,
                corner_radius=8,
                height=30,
                width=65,
                justify="center",
            )
            entry.insert(0, "1")    # pré-preenche com 1 para agilidade
            entry.grid(
                row=row_data["row"], column=1,
                padx=(4, 0), pady=5, sticky="w",
            )
            # Seleciona o conteúdo ao entrar (facilita edição rápida)
            entry.bind("<FocusIn>", lambda e, ent=entry: ent.select_range(0, "end"))
            row_data["entry"] = entry
        else:
            # ── Destrói o entry de quantidade ────────────────────────
            if row_data["entry"]:
                try:
                    row_data["entry"].destroy()
                except Exception:
                    pass
                row_data["entry"] = None

    # ════════════════════════════════════════════════════════════════════
    # GRADE DE CORES — checkboxes + círculos dinâmicos
    # ════════════════════════════════════════════════════════════════════

    def _popular_cores(self):
        """Popula o frame de cores com checkboxes vindos do banco de atributos."""
        cores_banco = config_ctrl.listar_nomes("cor")
        for idx, nome_cor in enumerate(cores_banco):
            self._adicionar_linha_cor(idx, nome_cor)

    def _adicionar_linha_cor(self, row_idx: int, nome_cor: str):
        """Cria uma linha de checkbox para uma cor no frame de cores."""
        if nome_cor in self._cor_rows:
            return   # evita duplicatas

        var = ctk.StringVar(value="off")

        chk = ctk.CTkCheckBox(
            self._frame_cores,
            text=nome_cor,
            variable=var,
            onvalue="on",
            offvalue="off",
            command=lambda n=nome_cor: self._toggle_cor(n),
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=_FG_PRIMARY,
            fg_color=_ACCENT_BLUE,
            hover_color=_ACCENT_GOLD,
            border_color=_BORDER,
            checkmark_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=4,
            width=110,
        )
        chk.grid(row=row_idx, column=0, sticky="w", padx=(10, 4), pady=4)

        # Círculo colorido — inicialmente oculto (sem imagem, sem cor de fundo)
        lbl_circ = ctk.CTkLabel(
            self._frame_cores,
            text="",
            fg_color="transparent",
            width=18,
            height=18,
        )
        lbl_circ.grid(row=row_idx, column=1, padx=(2, 4), pady=4, sticky="w")

        # Pré-resolve o hex para cores conhecidas (instantâneo — só dict lookup)
        hex_pre = DICIONARIO_CORES.get(nome_cor.strip().lower(), "")

        self._cor_rows[nome_cor] = {
            "var":          var,
            "hex":          hex_pre,
            "chk":          chk,
            "circ_lbl":     lbl_circ,
            "circ_img_ref": None,
            "row":          row_idx,
        }

    def _toggle_cor(self, nome_cor: str):
        """
        Ao marcar uma cor:
          1. Resolve o hex (dicionário → instantâneo; fora do dict → color picker).
          2. Exibe o círculo colorido ao lado do checkbox.
        Ao desmarcar: esconde o círculo.
        """
        row_data = self._cor_rows.get(nome_cor)
        if not row_data:
            return

        if row_data["var"].get() == "on":
            # ── Resolve o hexadecimal ────────────────────────────────
            hex_val = row_data["hex"]
            if not hex_val:
                # Não está no dicionário: abre o color picker nativo
                hex_val = resolver_cor_hex(nome_cor, self)
                if not hex_val:
                    # Usuário cancelou → desmarca o checkbox e sai
                    row_data["var"].set("off")
                    return
                row_data["hex"] = hex_val

            # ── Gera e exibe o círculo colorido ──────────────────────
            try:
                img = _circulo_mini(hex_val, 18)
                self._circle_refs.append(img)   # anti-GC
                row_data["circ_img_ref"] = img
                row_data["circ_lbl"].configure(image=img, fg_color="transparent")
            except Exception as e:
                print(f"[Cadastro] Erro ao gerar círculo para '{nome_cor}': {e}")
        else:
            # ── Remove o círculo ao desmarcar ─────────────────────────
            row_data["circ_lbl"].configure(image=None, fg_color="transparent")

    def _adicionar_cor_personalizada(self):
        """
        Abre o color picker diretamente para criar uma nova cor
        que não está na lista do banco.
        Solicita o nome via dialog simples antes de abrir o picker.
        """
        # Diálogo para o nome da cor
        dialog = ctk.CTkInputDialog(
            text="Digite o nome da nova cor (ex: 'Azul Petróleo'):",
            title="Nova Cor Personalizada",
        )
        nome_cor = dialog.get_input()
        if not nome_cor or not nome_cor.strip():
            return
        nome_cor = nome_cor.strip()

        if nome_cor in self._cor_rows:
            # Já existe: apenas marca
            self._cor_rows[nome_cor]["var"].set("on")
            self._toggle_cor(nome_cor)
            return

        # Abre o color picker para escolher o tom exato
        from tkinter.colorchooser import askcolor
        resultado = askcolor(
            color="#808080",
            parent=self,
            title=f"Selecione a cor exata para '{nome_cor}'",
        )
        if not resultado or not resultado[1]:
            return

        hex_val = resultado[1].upper()

        # Adiciona dinamicamente ao frame de cores
        novo_idx = len(self._cor_rows)
        self._adicionar_linha_cor(novo_idx, nome_cor)

        # Pré-armazena o hex e ativa o checkbox
        row_data = self._cor_rows[nome_cor]
        row_data["hex"] = hex_val
        row_data["var"].set("on")

        # Gera o círculo imediatamente
        try:
            img = _circulo_mini(hex_val, 18)
            self._circle_refs.append(img)
            row_data["circ_img_ref"] = img
            row_data["circ_lbl"].configure(image=img)
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════════════
    # SELEÇÃO DE IMAGEM
    # ════════════════════════════════════════════════════════════════════

    def _selecionar_imagem(self):
        """Abre o diálogo de arquivo, copia para imagens_produtos/ e exibe preview."""
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
        except Exception as e:
            messagebox.showerror("Erro ao copiar imagem", str(e))
            return

        self.caminho_imagem = caminho_destino
        self.lbl_imagem_confirmacao.configure(
            text=f"✅ {nome_arquivo}",
            text_color=("#059669", "#34D399"),
        )

        try:
            img = Image.open(caminho_destino).resize((90, 90), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(90, 90))
            self._preview_ref = ctk_img
            self.lbl_preview.configure(image=ctk_img, text="", width=90, height=90)
        except Exception:
            self.lbl_preview.configure(text="🖼", font=ctk.CTkFont(size=28))

    # ════════════════════════════════════════════════════════════════════
    # SALVAMENTO MESTRE / DETALHE
    # ════════════════════════════════════════════════════════════════════

    def _processar_salvamento(self):
        """
        Fluxo de salvamento:
          1. Valida os campos obrigatórios.
          2. Coleta tamanhos ativos com suas quantidades individuais.
          3. Coleta cores ativas com seus hexadecimais.
          4. Chama estoque_ctrl.salvar_grade_dinamica() → INSERT pai + N filhos.
          5. Navega de volta ao Estoque em caso de sucesso.
        """
        # ── Coleta e valida atributos ─────────────────────────────────
        tipo   = self.combo_tipo.get().strip()
        marca  = self.combo_marca.get().strip()
        tecido = self.combo_tecido.get().strip()
        corte  = self.combo_corte.get().strip()

        if not tipo or tipo == "—":
            messagebox.showerror("Campo obrigatório", "Selecione o Tipo / Peça.")
            return
        if not marca or marca == "—":
            messagebox.showerror("Campo obrigatório", "Selecione a Marca.")
            return

        # ── Valida e converte os preços ───────────────────────────────
        try:
            custo_str = self.entry_custo.get().strip().replace(",", ".")
            venda_str = self.entry_venda.get().strip().replace(",", ".")
            custo = float(custo_str) if custo_str else 0.0
            venda = float(venda_str) if venda_str else 0.0
        except ValueError:
            messagebox.showerror("Preço inválido", "Os preços devem ser números (use ponto ou vírgula).")
            return

        if venda <= 0:
            if not messagebox.askyesno(
                "Atenção",
                "O Preço de Venda está zerado. Deseja salvar mesmo assim?"
            ):
                return

        # ── Coleta tamanhos ativos com quantidades ────────────────────
        tamanhos_com_qtd: dict[str, int] = {}
        erros_qtd: list[str] = []

        for tam, row_data in self._tam_rows.items():
            if row_data["var"].get() == "on":
                qty_str = "1"
                if row_data["entry"] and row_data["entry"].winfo_exists():
                    qty_str = row_data["entry"].get().strip() or "1"
                try:
                    qty = int(qty_str)
                    if qty < 0:
                        raise ValueError
                    tamanhos_com_qtd[tam] = qty
                except ValueError:
                    erros_qtd.append(f"Tamanho '{tam}': quantidade inválida ('{qty_str}').")

        if erros_qtd:
            messagebox.showerror(
                "Quantidades inválidas",
                "Corrija os campos:\n" + "\n".join(erros_qtd)
            )
            return

        if not tamanhos_com_qtd:
            messagebox.showerror(
                "Sem tamanhos",
                "Marque pelo menos um tamanho e informe a quantidade."
            )
            return

        # ── Coleta cores ativas com hexadecimais ──────────────────────
        cores_com_hex: list[tuple[str, str]] = []
        cores_sem_hex: list[str] = []

        for nome_cor, row_data in self._cor_rows.items():
            if row_data["var"].get() == "on":
                hex_val = row_data["hex"]
                if not hex_val:
                    # Tentativa final de resolução antes de salvar
                    hex_val = resolver_cor_hex(nome_cor, self)
                    if not hex_val:
                        cores_sem_hex.append(nome_cor)
                        continue
                    row_data["hex"] = hex_val
                cores_com_hex.append((nome_cor, hex_val))

        if cores_sem_hex:
            messagebox.showwarning(
                "Cores sem hexadecimal",
                f"As cores abaixo foram ignoradas (sem hex definido):\n"
                f"{', '.join(cores_sem_hex)}\n\n"
                "Clique em cada cor novamente para escolher o tom."
            )

        if not cores_com_hex:
            messagebox.showerror(
                "Sem cores",
                "Selecione pelo menos uma cor para a grade."
            )
            return

        # ── Foto ─────────────────────────────────────────────────────
        foto = self.caminho_imagem if self.caminho_imagem else None

        # ── Chama o controller ────────────────────────────────────────
        try:
            sucesso, msg = estoque_ctrl.salvar_grade_dinamica(
                modelo_nome      = tipo,
                marca            = marca,
                tecido           = tecido,
                corte            = corte,
                tamanhos_com_qtd = tamanhos_com_qtd,
                cores_com_hex    = cores_com_hex,
                preco_custo      = custo,
                preco_venda      = venda,
                foto_path        = foto,
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
        """
        Pré-popula todos os campos com os dados de um produto existente
        para o fluxo de edição (produto_id fornecido no construtor).
        """
        dados = estoque_ctrl.buscar_produto_completo(self.produto_id)
        if not dados:
            messagebox.showwarning(
                "Produto não encontrado",
                f"Não foi possível carregar o produto ID {self.produto_id}."
            )
            return

        # Atributos mestre
        self.combo_tipo.set(dados.get("modelo_nome", ""))
        self.combo_marca.set(dados.get("marca", ""))
        self.combo_tecido.set(dados.get("tecido", ""))
        self.combo_corte.set(dados.get("corte", ""))

        variacoes = dados.get("variacoes", [])
        if not variacoes:
            return

        # Preços da primeira variação
        primeira = variacoes[0]
        self.entry_custo.delete(0, "end")
        self.entry_custo.insert(0, f"{primeira.get('preco_custo', 0.0):.2f}")
        self.entry_venda.delete(0, "end")
        self.entry_venda.insert(0, f"{primeira.get('preco_venda', 0.0):.2f}")

        # Imagem da primeira variação
        foto_existente = primeira.get("foto_path")
        if foto_existente and os.path.exists(foto_existente):
            self.caminho_imagem = foto_existente
            nome_arq = os.path.basename(foto_existente)
            self.lbl_imagem_confirmacao.configure(
                text=f"✅ {nome_arq}",
                text_color=("#059669", "#34D399"),
            )
            try:
                img = Image.open(foto_existente).resize((90, 90), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(90, 90))
                self._preview_ref = ctk_img
                self.lbl_preview.configure(image=ctk_img, text="", width=90, height=90)
            except Exception:
                pass

        # ── Detecta se a grade existente é por Letra ou Número ────────
        tamanhos_existentes = {v.get("tamanho", "").strip() for v in variacoes}
        tem_numero = any(t.isdigit() for t in tamanhos_existentes)
        if tem_numero:
            self._var_tipo_grade.set("numero")
            self._reconstruir_grade()

        # Marca os tamanhos e preenche quantidades
        # Agrupa estoque por tamanho (soma as novas sem cor)
        # Se for variacao antiga com cor, so pega a primeira de cada tamanho para evitar duplicar
        estoque_por_tam: dict[str, int] = {}
        for v in variacoes:
            tam = v.get("tamanho", "").strip()
            if tam:
                if v.get("cor"):
                    if tam not in estoque_por_tam:
                        estoque_por_tam[tam] = v.get("estoque", 0)
                else:
                    estoque_por_tam[tam] = estoque_por_tam.get(tam, 0) + v.get("estoque", 0)

        for tam, qtd_total in estoque_por_tam.items():
            if tam in self._tam_rows:
                row = self._tam_rows[tam]
                row["var"].set("on")
                self._toggle_qty_entry(tam)
                if row["entry"] and row["entry"].winfo_exists():
                    row["entry"].delete(0, "end")
                    row["entry"].insert(0, str(qtd_total))
            else:
                # Tamanho fora da grade atual → adiciona dinamicamente
                novo_idx = len(self._tam_rows)
                self._adicionar_linha_tamanho(novo_idx, tam)
                row = self._tam_rows[tam]
                row["var"].set("on")
                self._toggle_qty_entry(tam)
                if row["entry"] and row["entry"].winfo_exists():
                    row["entry"].delete(0, "end")
                    row["entry"].insert(0, str(qtd_total))

        # Marca as cores existentes (vindas do campo cores_tags do pai)
        cores_existentes = dados.get("cores_lista", [])
        
        for nome_c, hex_c in cores_existentes:
            if nome_c in self._cor_rows:
                row = self._cor_rows[nome_c]
                if hex_c:
                    row["hex"] = hex_c
                row["var"].set("on")
                self._toggle_cor(nome_c)
            else:
                # Cor fora da lista → adiciona
                novo_idx = len(self._cor_rows)
                self._adicionar_linha_cor(novo_idx, nome_c)
                row = self._cor_rows[nome_c]
                if hex_c:
                    row["hex"] = hex_c
                row["var"].set("on")
                self._toggle_cor(nome_c)
