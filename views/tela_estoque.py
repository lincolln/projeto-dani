"""
tela_estoque.py — Vitrine Visual de Estoque (Grade de Produtos Pai/Filho)
=========================================================================
Versão 3.0 — Card Vertical Premium com:
  • CardProdutoVertical — layout vertical com imagem, círculos coloridos
    por cor_hex, grade de tamanhos/quantidades e rodapé de preços.
  • Busca intensiva com Pandas em tempo real (<KeyRelease>).
  • Menu flutuante (CTkToplevel sem bordas) ao clicar no card:
    [Editar] [Apagar] [Vender] [Gerar Código de Barras].
  • Dados agrupados por produto PAI (um card por modelo, não por SKU).
  • Geração de código de barras em PNG via lib 'barcode' (ou fallback texto).
  • Toda a conexão variacao_id → tela_venda preservada intacta.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import estoque_ctrl

# ── Paletas dinâmicas (claro, escuro) ───────────────────────────────────────
_BG_WINDOW    = ("#F0F2F8", "#0F1117")
_BG_CARD      = ("#FFFFFF", "#16191F")
_BG_CARD_SUB  = ("#F4F6FB", "#1C202B")
_BG_HOVER     = ("#E8ECF4", "#22273A")
_FG_PRIMARY   = ("#1A1D2E", "#F0F2F8")
_FG_MUTED     = ("#6B7280", "#8A8FA8")
_FG_LABEL     = ("#4B5563", "#A0A8C0")
_ACCENT_GOLD  = ("#B8861F", "#E1B12C")
_ACCENT_BLUE  = ("#1B4F8A", "#2D7DD2")
_ACCENT_GREEN = ("#1B7A4C", "#059669")
_ACCENT_RED   = ("#B91C1C", "#DC2626")
_ACCENT_PURP  = ("#6B21A8", "#A855F7")
_BORDER       = ("#DDE3EE", "#22273A")
_BORDER_HOVER = ("#2D7DD2", "#7C83FD")
_SEARCH_BG    = ("#FFFFFF", "#1C202B")

# Dimensões do card
_CARD_W       = 230   # largura fixa de cada card em px
_IMG_SIZE     = 160   # tamanho da imagem do produto
_CIRCLE_SIZE  = 22    # diâmetro dos círculos de cor


# ════════════════════════════════════════════════════════════════════════════
# HELPER — Gera imagem circular colorida para CTkLabel
# ════════════════════════════════════════════════════════════════════════════

_CACHE_CIRCULOS = {}

def _criar_circulo_imagem(hex_cor: str, tamanho: int = _CIRCLE_SIZE) -> ctk.CTkImage:
    """Retorna um CTkImage de um círculo sólido na cor dada."""
    cache_key = (hex_cor, tamanho)
    if cache_key in _CACHE_CIRCULOS:
        return _CACHE_CIRCULOS[cache_key]

    from utils_cores import hex_para_display
    hex_cor = hex_para_display(hex_cor, "#808080")
    if len(hex_cor) == 4:  # #RGB -> #RRGGBB
        hex_cor = '#' + hex_cor[1]*2 + hex_cor[2]*2 + hex_cor[3]*2

    # Converte '#RRGGBB' para tupla RGB
    h = hex_cor.lstrip("#")
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    # Cria imagem RGBA com anti-aliasing (4× e reduz)
    s = tamanho * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Desenha a borda (um círculo um pouco maior, cinza suave)
    draw.ellipse((0, 0, s, s), fill=(200, 200, 200, 255))
    # Desenha a cor real por cima (um círculo um pouco menor)
    draw.ellipse((4, 4, s - 4, s - 4), fill=(*rgb, 255))
    img = img.resize((tamanho, tamanho), Image.Resampling.LANCZOS)

    img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(tamanho, tamanho))
    _CACHE_CIRCULOS[cache_key] = img_ctk
    return img_ctk


# ════════════════════════════════════════════════════════════════════════════
# CLASSE — CARD PRODUTO VERTICAL
# ════════════════════════════════════════════════════════════════════════════

class CardProdutoVertical(ctk.CTkFrame):
    """
    Card vertical premium para exibição de um produto Pai com todas as suas
    variações (cores e tamanhos) consolidadas.

    Layout de cima para baixo:
      [TIPO DE PEÇA]         ← badge de cabeçalho
      [Imagem CTkImage]      ← 160×160, centralizada
      [Marca / Corte]        ← labels informativos
      ┌─────────┬─────────┐
      │Círculos │Tamanhos │  ← miolo dinâmico lado a lado
      │coloridos│+ qtds   │
      └─────────┴─────────┘
      [Custo] / [Venda]      ← rodapé de preços
    """

    def __init__(
        self,
        parent,
        dados_produto: dict,
        on_editar,
        on_apagar,
        on_vender,
        on_barcode,
        cache_imgs: dict,
        cache_circles: list,
        on_ver_qr=None,
    ):
        super().__init__(
            parent,
            fg_color=_BG_CARD,
            corner_radius=15,
            border_width=1,
            border_color=_BORDER,
        )
        # Removido grid_propagate(False) para permitir que a altura seja flexível
        # Trava a largura mínima do card com um widget invisível depois
        ctk.CTkFrame(self, width=240, height=0, fg_color="transparent").grid(row=5, column=0)

        self._dados    = dados_produto
        self._on_edit  = on_editar
        self._on_del   = on_apagar
        self._on_sell  = on_vender
        self._on_bar   = on_barcode
        self._on_ver_qr = on_ver_qr
        self._cache_imgs    = cache_imgs
        self._cache_circles = cache_circles

        # ── Controle de menu singleton ───────────────────────────────
        # Armazena a referência do popup aberto. Garante que apenas
        # UM menu flutuante exista na tela por vez.
        self._menu_atual: ctk.CTkToplevel | None = None

        # ── Layout proporcional por linhas (Grid Pesado) ────────────────
        # Coluna única se expande para preencher a largura do card
        self.grid_columnconfigure(0, weight=1)
        # Linhas com weight=0 → encolhem ao conteúdo (fixas)
        # Linha 3 com weight=1 → absorve TODA a altura sobrando
        # Isso empurra o rodé (linha 4) para sempre ficar na BASE do card
        self.grid_rowconfigure(0, weight=0)   # Badge tipo de peça
        self.grid_rowconfigure(1, weight=0)   # Imagem do produto
        self.grid_rowconfigure(2, weight=0)   # Marca / Corte
        self.grid_rowconfigure(3, weight=1)   # Miolo (Cores + Tamanhos) ← flexível
        self.grid_rowconfigure(4, weight=0)   # Rodé precos ← sempre na base

        self._construir()
        self._bind_hover_e_click()

    # ── Construção ──────────────────────────────────────────────────────────

    def _construir(self):
        d = self._dados

        # ── 0. Badge tipo de peça ────────────────────────────────────────
        frame_badge = ctk.CTkFrame(self, fg_color=_ACCENT_BLUE, corner_radius=10)
        frame_badge.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        frame_badge.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame_badge,
            text=d.get("tipo_peca", "—").upper(),
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=("#FFFFFF", "#FFFFFF"),
            anchor="center",
        ).grid(row=0, column=0, sticky="ew", padx=6, pady=4)

        # ── 1. Imagem do produto ─────────────────────────────────────────
        foto_path = d.get("foto_path")
        chave_img = foto_path or "__padrao__"

        if chave_img not in self._cache_imgs:
            if foto_path and os.path.exists(foto_path):
                raw = Image.open(foto_path).resize(
                    (_IMG_SIZE, _IMG_SIZE), Image.Resampling.LANCZOS
                )
            else:
                # Placeholder degradê cinza-azulado
                raw = Image.new("RGBA", (_IMG_SIZE, _IMG_SIZE), (30, 35, 50, 255))
                draw = ImageDraw.Draw(raw)
                draw.text(
                    (_IMG_SIZE // 2 - 12, _IMG_SIZE // 2 - 12),
                    "👕", fill=(140, 150, 180, 200)
                )
            self._cache_imgs[chave_img] = ctk.CTkImage(
                light_image=raw, dark_image=raw, size=(_IMG_SIZE, _IMG_SIZE)
            )

        ctk_img = self._cache_imgs[chave_img]
        lbl_img = ctk.CTkLabel(
            self,
            text="",
            image=ctk_img,
            fg_color=_BG_CARD_SUB,
            corner_radius=10,
            width=_IMG_SIZE,
            height=_IMG_SIZE,
        )
        lbl_img.grid(row=1, column=0, padx=14, pady=6, sticky="ew")

        # ── 2. Marca e corte ─────────────────────────────────────────────
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 4))
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            info_frame,
            text=f"Marca:  {d.get('marca', '—')}",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_LABEL,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            info_frame,
            text=f"Corte:   {d.get('corte', '—') or '—'}",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=_FG_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(
            info_frame,
            text=f"Tecido: {d.get('tecido', '') or '—'}",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=_FG_MUTED,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew")

        # ── 3. Miolo (linha flexível sem trava de altura) ───────
        frame_miolo = ctk.CTkFrame(
            self,
            fg_color=_BG_CARD_SUB,
            corner_radius=10,
        )
        frame_miolo.grid(row=3, column=0, sticky="nsew", padx=14, pady=4)
        
        # Sem grid_propagate(False), o miolo expande para caber todos os tamanhos e cores
        
        frame_miolo.grid_columnconfigure(0, weight=1)
        frame_miolo.grid_columnconfigure(1, weight=1)
        frame_miolo.grid_rowconfigure(0, weight=0)
        frame_miolo.grid_rowconfigure(1, weight=1)

        cores_unicas = d.get("cores_lista", [])   # lista de (nome, hex)
        tams_resumo  = d.get("tamanhos_resumo", {}) # {tamanho: total_estoque}

        # ── Título Cores ─────────────────────────────────────────────
        ctk.CTkLabel(
            frame_miolo,
            text="Cores",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_FG_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(2, 5))

        # ── Conteúdo Cores ───────────────────────────────────────────
        if cores_unicas:
            frame_grid_cores = ctk.CTkFrame(frame_miolo, fg_color="transparent")
            frame_grid_cores.grid(row=1, column=0, sticky="nw", padx=10, pady=(2, 5))

            for idx, (nome_cor, hex_cor) in enumerate(cores_unicas):
                row_c = idx // 4
                col_c = idx % 4
                try:
                    circ = _criar_circulo_imagem(hex_cor, _CIRCLE_SIZE)
                    self._cache_circles.append(circ)
                    lbl = ctk.CTkLabel(
                        frame_grid_cores,
                        text="",
                        image=circ,
                        fg_color="transparent",
                        width=_CIRCLE_SIZE,
                        height=_CIRCLE_SIZE,
                        cursor="hand2",
                    )
                    lbl.grid(row=row_c, column=col_c, padx=2, pady=2)
                    lbl.bind("<Enter>", lambda e, n=nome_cor: self._tooltip_show(e, n))
                    lbl.bind("<Leave>", self._tooltip_hide)
                except Exception:
                    pass
        else:
            # ── Fallback: produto sem variações de cor ainda ──────────
            ctk.CTkLabel(
                frame_miolo,
                text="Nenhuma",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=_FG_MUTED,
                justify="left",
                anchor="w",
            ).grid(row=1, column=0, sticky="nw", padx=10, pady=(2, 5))

        # ── Título Estoque ───────────────────────────────────────────
        ctk.CTkLabel(
            frame_miolo,
            text="Estoque",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_FG_MUTED,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=10, pady=(2, 5))

        # ── Conteúdo Estoque ─────────────────────────────────────────
        if tams_resumo:
            linhas = [f"{t}: {q}" for t, q in sorted(
                tams_resumo.items(),
                key=lambda x: _ORDEM_TAMANHOS.get(x[0].upper(), 99)
            )]
            ctk.CTkLabel(
                frame_miolo,
                text="\n".join(linhas),
                font=ctk.CTkFont(family="Consolas", size=13),
                text_color=_FG_PRIMARY,
                anchor="w",
                justify="left",
            ).grid(row=1, column=1, sticky="nw", padx=10, pady=(2, 5))
        else:
            # ── Fallback: produto sem variações de tamanho ainda ──────
            ctk.CTkLabel(
                frame_miolo,
                text="Grade:\nVazia",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=_FG_MUTED,
                justify="left",
                anchor="w",
            ).grid(row=1, column=1, sticky="nw", padx=10, pady=(2, 5))

        # ── 4. Rodapé: preços ────────────────────────────────────────────
        frame_precos = ctk.CTkFrame(self, fg_color="transparent")
        frame_precos.grid(row=4, column=0, sticky="ew", padx=14, pady=(6, 14))
        frame_precos.grid_columnconfigure(0, weight=1)
        frame_precos.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame_precos,
            text=f"Custo\nR${d.get('preco_custo', 0.0):.2f}",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=_FG_MUTED,
            anchor="center",
            justify="center",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            frame_precos,
            text=f"Venda\nR${d.get('preco_venda', 0.0):.2f}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("#059669", "#34D399"),
            anchor="center",
            justify="center",
        ).grid(row=0, column=1, sticky="ew")

    # ── Hover e clique ───────────────────────────────────────────────────────

    def _bind_hover_e_click(self):
        """Aplica hover de borda e evento de clique recursivamente."""
        def _hover_on(e):
            self.configure(border_color=_BORDER_HOVER, border_width=2)

        def _hover_off(e):
            self.configure(border_color=_BORDER, border_width=1)

        def _click(e):
            self._abrir_menu_flutuante(e)

        for widget in [self, *self._todos_filhos(self)]:
            widget.bind("<Enter>", _hover_on, add="+")
            widget.bind("<Leave>", _hover_off, add="+")
            widget.bind("<Button-1>", _click, add="+")

    def _todos_filhos(self, w) -> list:
        filhos = []
        for c in w.winfo_children():
            filhos.append(c)
            filhos.extend(self._todos_filhos(c))
        return filhos

    # ── Tooltip simples ──────────────────────────────────────────────────────

    def _tooltip_show(self, event, texto: str):
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        x = event.x_root + 14
        y = event.y_root - 22
        self._tooltip.geometry(f"+{x}+{y}")
        tk.Label(
            self._tooltip,
            text=texto,
            bg="#1A1D2E",
            fg="#E1B12C",
            font=("Segoe UI", 9),
            padx=6,
            pady=3,
        ).pack()

    def _tooltip_hide(self, event=None):
        if hasattr(self, "_tooltip") and self._tooltip:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None

    # ── Menu flutuante (singleton) ───────────────────────────────────────────
    _menu_aberto_global = None

    def _abrir_menu_flutuante(self, event):
        """Abre popup flutuante próximo ao cursor.

        Garante singleton global: se já existe um menu aberto (deste card OU de
        qualquer outro), ele é destruído antes de criar o novo. O usuário nunca
        verá dois menus sobrepostos ao clicar rapidamente em cards diferentes.
        """
        # ── SINGLETON GLOBAL: fecha o popup anterior se ainda estiver vivo ──
        if CardProdutoVertical._menu_aberto_global is not None:
            try:
                if CardProdutoVertical._menu_aberto_global.winfo_exists():
                    CardProdutoVertical._menu_aberto_global.destroy()
            except Exception:
                pass
            CardProdutoVertical._menu_aberto_global = None

        d = self._dados

        popup = ctk.CTkToplevel(self)
        popup.wm_overrideredirect(True)   # sem borda/título do OS
        popup.attributes("-topmost", True)
        popup.configure(fg_color="#16191F")

        # Registra o novo popup como o menu atual global e deste card
        CardProdutoVertical._menu_aberto_global = popup
        self._menu_atual = popup

        # Garante que _menu_atual seja limpo quando o popup for destruído
        def _on_popup_destroy(e=None):
            if CardProdutoVertical._menu_aberto_global == popup:
                CardProdutoVertical._menu_aberto_global = None
            self._menu_atual = None
        popup.bind("<Destroy>", _on_popup_destroy)

        # Borda manual via frame externo
        borda = ctk.CTkFrame(popup, fg_color="#2D7DD2", corner_radius=12)
        borda.pack(padx=1, pady=1)

        inner = ctk.CTkFrame(borda, fg_color="#16191F", corner_radius=11)
        inner.pack(padx=1, pady=1)

        # Título do popup
        ctk.CTkLabel(
            inner,
            text=f"⚡  {d.get('tipo_peca', 'Produto')}",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E1B12C",
            anchor="center",
        ).pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkFrame(inner, height=1, fg_color="#22273A", corner_radius=0).pack(
            fill="x", padx=8, pady=(0, 6)
        )

        # Definição dos botões do menu
        produto_id = d.get("produto_id")
        variacoes  = d.get("variacoes_ids", [])   # lista de variacao_id para venda
        primeiro_vid = variacoes[0] if variacoes else None

        botoes_menu = [
            ("✏️   Editar",                 "#1B4F8A", "#2D7DD2",
             lambda: (popup.destroy(), self._on_edit(produto_id))),
            ("🗑   Apagar",                 "#7F1D1D", "#DC2626",
             lambda: (popup.destroy(), self._on_del(produto_id))),
            ("🛒   Vender",                 "#14532D", "#059669",
             lambda: (popup.destroy(), self._on_sell(primeiro_vid))),
            ("📱   Ver QR Code na Tela",    "#4C1D95", "#7C3AED",
             lambda: (popup.destroy(), self._on_ver_qr(d) if self._on_ver_qr else None)),
            ("🖨️   Imprimir Etiquetas",     "#1E3A5F", "#2D7DD2",
             lambda: (popup.destroy(), self._on_bar(d))),
        ]

        for texto, fg_cor, hover_cor, cmd in botoes_menu:
            ctk.CTkButton(
                inner,
                text=texto,
                command=cmd,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                fg_color=fg_cor,
                hover_color=hover_cor,
                text_color="#FFFFFF",
                corner_radius=8,
                height=36,
                width=200,
                anchor="w",
            ).pack(fill="x", padx=10, pady=3)

        ctk.CTkFrame(inner, height=4, fg_color="transparent").pack()

        # Posiciona próximo ao cursor
        popup.update_idletasks()
        pw = popup.winfo_reqwidth()
        ph = popup.winfo_reqheight()
        sx = self.winfo_screenwidth()
        sy = self.winfo_screenheight()
        x  = min(event.x_root + 8, sx - pw - 10)
        y  = min(event.y_root - 10, sy - ph - 10)
        popup.geometry(f"+{x}+{y}")

        # Fecha ao perder o foco ou pressionar Escape
        popup.bind("<FocusOut>", lambda e: popup.destroy())
        popup.bind("<Escape>",   lambda e: popup.destroy())
        popup.focus_set()


# ── Ordem lógica de tamanhos para ordenação ─────────────────────────────────
_ORDEM_TAMANHOS = {
    "PP": 0, "P": 1, "M": 2, "G": 3, "GG": 4, "XG": 5, "XXG": 6,
    "ÚNICO": 7, "UNICO": 7,
    "36": 10, "38": 11, "40": 12, "42": 13, "44": 14, "46": 15,
    "48": 16, "50": 17, "52": 18,
}


# ════════════════════════════════════════════════════════════════════════════
# TELA PRINCIPAL DE ESTOQUE
# ════════════════════════════════════════════════════════════════════════════

class TelaEstoque(ctk.CTkFrame):
    """
    Vitrine de Cards Verticais responsiva com busca Pandas em tempo real.
    Dados agrupados por produto PAI (um card por modelo).
    Herda de CTkFrame para theming nativo claro/escuro.
    """

    def __init__(self, parent, controller):
        super().__init__(
            parent,
            corner_radius=0,
            fg_color=_BG_WINDOW,
        )
        self.controller = controller
        self._cache_imgs:    dict = {}   # chave → CTkImage de foto
        self._cache_circles: list = []   # referências CTkImage de círculos (anti-GC)
        self._popup_barcode  = None      # janela de impressão de etiquetas
        self._popup_ver_qr   = None      # janela modal de visualização de QR Code
        self._debounce_busca_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._construir_interface()

    # ════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DA INTERFACE
    # ════════════════════════════════════════════════════════════════════

    def _construir_interface(self):

        # ── CABEÇALHO ────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_header.grid(row=0, column=0, sticky="ew", padx=25, pady=(18, 8))
        frame_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame_header,
            text="📦  Vitrine de Estoque",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=_FG_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            frame_header,
            text="➕  Cadastrar Nova Peça",
            command=self.controller._ir_cadastro,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=_ACCENT_BLUE,
            hover_color=_ACCENT_GOLD,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8,
            height=36,
            width=185,
        ).grid(row=0, column=1, sticky="e")

        # ── BARRA DE BUSCA INTENSIVA ──────────────────────────────────
        frame_busca = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_busca.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 10))
        frame_busca.grid_columnconfigure(0, weight=1)

        frame_entrada = ctk.CTkFrame(
            frame_busca,
            fg_color=_SEARCH_BG,
            corner_radius=12,
            border_width=1,
            border_color=_BORDER,
            height=44,
        )
        frame_entrada.grid(row=0, column=0, sticky="ew")
        frame_entrada.grid_columnconfigure(1, weight=1)
        frame_entrada.grid_propagate(False)

        ctk.CTkLabel(
            frame_entrada,
            text="🔍",
            font=ctk.CTkFont(size=19),
            text_color=_FG_MUTED,
            fg_color="transparent",
        ).grid(row=0, column=0, padx=(14, 4), pady=0)

        self.entry_busca = ctk.CTkEntry(
            frame_entrada,
            placeholder_text="Buscar por tipo, marca ou corte...",
            font=ctk.CTkFont(family="Segoe UI", size=15),
            fg_color="transparent",
            border_width=0,
            text_color=_FG_PRIMARY,
            placeholder_text_color=_FG_MUTED,
            height=40,
        )
        self.entry_busca.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        # Foco automático na barra de busca ao abrir a tela
        self.after(300, lambda: self.entry_busca.focus_set())
        # Filtragem em tempo real a cada tecla pressionada
        self.entry_busca.bind("<KeyRelease>", self._on_busca_keyrelease)

        self.lbl_contagem = ctk.CTkLabel(
            frame_busca,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=_FG_MUTED,
            anchor="e",
        )
        self.lbl_contagem.grid(row=1, column=0, sticky="e", pady=(4, 0))

        # ── ÁREA DE CARDS (CTkScrollableFrame) ───────────────────────
        self.frame_vitrine = ctk.CTkScrollableFrame(
            self,
            fg_color=_BG_WINDOW,
            corner_radius=0,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self.frame_vitrine.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.frame_vitrine.bind("<Configure>", self._on_vitrine_resize)
        self._resize_after_id = None
        self._largura_anterior = 0

        # Dispara renderização inicial com delay seguro
        self.after(250, self._renderizar_cards)

    def _on_vitrine_resize(self, event=None):
        """Só re-renderiza se a largura mudou o suficiente para alterar o número de colunas."""
        largura_atual = self.frame_vitrine.winfo_width()
        if largura_atual <= 1:
            return
        # Calcula colunas com a largura atual e a anterior
        colunas_atual = max(1, min(largura_atual // (_CARD_W + 30), 6))
        colunas_anterior = max(1, min(self._largura_anterior // (_CARD_W + 30), 6)) if self._largura_anterior > 0 else 0
        if colunas_atual == colunas_anterior:
            return
        self._largura_anterior = largura_atual
        if self._resize_after_id:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(300, self._renderizar_cards)

    # ════════════════════════════════════════════════════════════════════
    # DESTRUIÇÃO SEGURA
    # ════════════════════════════════════════════════════════════════════

    def destroy(self):
        """Encerramento seguro: limpa caches e destrói filhos sem race condition."""
        self._cache_imgs.clear()
        self._cache_circles.clear()
        if self._popup_barcode:
            try:
                self._popup_barcode.destroy()
            except Exception:
                pass
        for widget in self.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass
        super().destroy()

    # ════════════════════════════════════════════════════════════════════
    # BUSCA + RENDERIZAÇÃO COM PANDAS
    # ════════════════════════════════════════════════════════════════════

    def _on_busca_keyrelease(self, event=None):
        if self._debounce_busca_id:
            self.after_cancel(self._debounce_busca_id)
        self._debounce_busca_id = self.after(300, self._renderizar_cards)

    def _get_termo(self) -> str:
        return self.entry_busca.get().strip()

    def _renderizar_cards(self):
        """
        Busca todos os produtos agrupados por PAI via Pandas,
        filtra pelo termo digitado e reconstrói o grid de cards.
        """
        # Limpa a vitrine
        for w in self.frame_vitrine.winfo_children():
            w.destroy()
        # self._cache_circles.clear() removido para cache global

        # Carrega dados agrupados
        dados_brutos = estoque_ctrl.listar_produtos_vitrine_grade()

        # ── Filtragem Pandas ──────────────────────────────────────────
        try:
            import pandas as pd
            df = pd.DataFrame(dados_brutos)
            termo = self._get_termo()

            if not df.empty and termo:
                t = termo.lower()
                mask = (
                    df["tipo_peca"].str.lower().str.contains(t, na=False) |
                    df["marca"].str.lower().str.contains(t, na=False)     |
                    df["corte"].str.lower().str.contains(t, na=False)
                )
                df = df[mask]

            produtos = df.to_dict("records") if not df.empty else []
        except ImportError:
            # Fallback sem Pandas (busca simples)
            termo = self._get_termo().lower()
            produtos = [
                p for p in dados_brutos
                if not termo or termo in (
                    p.get("tipo_peca", "") + p.get("marca", "") + p.get("corte", "")
                ).lower()
            ]

        total = len(produtos)
        self.lbl_contagem.configure(
            text=f"{total} modelo(s) encontrado(s)"
        )

        if not produtos:
            ctk.CTkLabel(
                self.frame_vitrine,
                text="Nenhum produto encontrado no estoque.",
                font=ctk.CTkFont(family="Segoe UI", size=17),
                text_color=_FG_MUTED,
            ).grid(row=0, column=0, padx=40, pady=60)
            return

        # ── Grid responsivo de Cards ──────────────────────────────────
        largura_area = self.frame_vitrine.winfo_width()
        largura_area = max(largura_area, 800)
        # Cada card ocupa _CARD_W + margens (~260px)
        colunas = max(1, min(largura_area // (_CARD_W + 30), 6))

        for c in range(colunas):
            self.frame_vitrine.grid_columnconfigure(c, weight=1)

        for idx, produto in enumerate(produtos):
            row = idx // colunas
            col = idx % colunas
            card = CardProdutoVertical(
                parent=self.frame_vitrine,
                dados_produto=produto,
                on_editar=self._acao_editar,
                on_apagar=self._acao_apagar,
                on_vender=self._acao_vender,
                on_barcode=self._acao_barcode,
                on_ver_qr=self._acao_ver_qrcode,
                cache_imgs=self._cache_imgs,
                cache_circles=self._cache_circles,
            )
            card.grid(row=row, column=col, padx=10, pady=10, sticky="n")

    # ════════════════════════════════════════════════════════════════════
    # AÇÕES DO MENU FLUTUANTE
    # ════════════════════════════════════════════════════════════════════

    def _acao_editar(self, produto_id: int):
        """Navega para a tela de cadastro no modo edição."""
        self.controller._ir_cadastro(produto_id=produto_id)

    def _acao_apagar(self, produto_id: int):
        """Confirma e remove o produto PAI e todas as suas variações."""
        confirmar = messagebox.askyesno(
            "Confirmar Exclusão",
            "Deseja apagar este produto e TODAS as suas variações permanentemente?\n"
            "Esta ação não pode ser desfeita.",
        )
        if not confirmar:
            return

        from controllers.estoque_ctrl import excluir_produto
        sucesso, msg, fotos = excluir_produto(produto_id)
        if sucesso:
            for foto in fotos:
                if foto and os.path.exists(foto):
                    try:
                        os.remove(foto)
                    except OSError:
                        pass
            messagebox.showinfo("Produto Removido", msg)
            self._renderizar_cards()
        else:
            messagebox.showerror("Erro", msg)

    def _acao_vender(self, variacao_id: int | None):
        """Navega para a tela de venda com a variação pré-selecionada."""
        if variacao_id is None:
            messagebox.showwarning(
                "Sem Estoque",
                "Este produto não possui variações com estoque disponível."
            )
            return
        self.controller._ir_venda(variacao_id=variacao_id)

    def _acao_ver_qrcode(self, dados_produto: dict):
        """
        Abre uma janela modal com o QR Code nítido em tamanho grande para
        permitir que o usuário aponte a câmera do celular e teste imediatamente.
        """
        produto_id = dados_produto.get("produto_id", 0)
        tipo_peca  = dados_produto.get("tipo_peca", "Produto")
        marca      = dados_produto.get("marca", "")
        preco_pad  = dados_produto.get("preco_venda", 0.0)

        from controllers.estoque_ctrl import buscar_produto_completo
        from utils_impressao import gerar_qrcode_preview, gerar_etiqueta, imprimir_etiqueta

        dados_completos = buscar_produto_completo(produto_id)
        variacoes = dados_completos.get("variacoes", []) if dados_completos else []

        if not variacoes:
            variacoes = [{
                "id": None,
                "codigo_barras": f"KNB{produto_id:05d}0001",
                "tamanho": "Único",
                "preco_venda": preco_pad,
                "estoque": 0,
            }]

        if hasattr(self, '_popup_ver_qr') and self._popup_ver_qr and self._popup_ver_qr.winfo_exists():
            self._popup_ver_qr.destroy()

        win = ctk.CTkToplevel(self)
        win.title(f"📱 QR Code — {tipo_peca} {marca}")
        win.geometry("460x570")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(fg_color="#0F1117")
        self._popup_ver_qr = win

        # Título
        ctk.CTkLabel(
            win,
            text=f"📱  {tipo_peca}  —  {marca}",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#E1B12C",
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            win,
            text="Aponte a câmera do celular para testar a leitura do QR Code!",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8A8FA8",
        ).pack(pady=(0, 10))

        # Seletor de variação / tamanho
        frame_tam = ctk.CTkFrame(win, fg_color="transparent")
        frame_tam.pack(fill="x", padx=30, pady=(0, 8))

        ctk.CTkLabel(
            frame_tam,
            text="Selecione o Tamanho:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#A0A8C0",
        ).pack(side="left", padx=(0, 10))

        tams = [f"Tam: {v.get('tamanho', '?')}  ·  {v.get('codigo_barras', '') or f'KNB{produto_id:05d}{i+1:04d}'}" for i, v in enumerate(variacoes)]
        var_opcao = ctk.StringVar(value=tams[0])

        # Card branco central para contraste do QR Code
        card_qr = ctk.CTkFrame(win, fg_color="#FFFFFF", corner_radius=14, width=270, height=270)
        card_qr.pack(pady=8)
        card_qr.pack_propagate(False)

        lbl_qr = ctk.CTkLabel(card_qr, text="", fg_color="#FFFFFF")
        lbl_qr.pack(expand=True, fill="both", padx=10, pady=10)

        # Informações complementares
        frame_info = ctk.CTkFrame(win, fg_color="#16191F", corner_radius=10)
        frame_info.pack(fill="x", padx=30, pady=(8, 12))

        lbl_cod = ctk.CTkLabel(
            frame_info,
            text="",
            font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
            text_color="#34D399",
        )
        lbl_cod.pack(pady=(6, 2))

        lbl_detalhes = ctk.CTkLabel(
            frame_info,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#F0F2F8",
        )
        lbl_detalhes.pack(pady=(0, 6))

        # Variável anti-garbage collection
        self._qr_preview_img = None

        def _atualizar_qr(escolha=None):
            idx = 0
            if escolha in tams:
                idx = tams.index(escolha)
            v_atual = variacoes[idx]

            cod = v_atual.get("codigo_barras", "") or f"KNB{produto_id:05d}{idx+1:04d}"
            tam = v_atual.get("tamanho", "?")
            preco = v_atual.get("preco_venda", preco_pad)
            est = v_atual.get("estoque", 0)

            img_pil = gerar_qrcode_preview(cod, tamanho_px=250)
            ctk_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(250, 250))
            self._qr_preview_img = ctk_img
            lbl_qr.configure(image=ctk_img)

            lbl_cod.configure(text=f"QR Code: {cod}")
            preco_fmt = f"R$ {preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            lbl_detalhes.configure(text=f"Tamanho: {tam}   |   Preço: {preco_fmt}   |   Estoque: {est} un.")

        combo_tam = ctk.CTkComboBox(
            frame_tam,
            values=tams,
            variable=var_opcao,
            command=_atualizar_qr,
            state="readonly",
            font=ctk.CTkFont(size=13),
            width=240,
        )
        combo_tam.pack(side="left")

        # Botões de ação no rodapé
        frame_rodape = ctk.CTkFrame(win, fg_color="transparent")
        frame_rodape.pack(fill="x", padx=30, pady=(4, 16))

        def _imprimir_este():
            idx = tams.index(var_opcao.get()) if var_opcao.get() in tams else 0
            v_sel = variacoes[idx]
            cod = v_sel.get("codigo_barras", "") or f"KNB{produto_id:05d}{idx+1:04d}"
            c = gerar_etiqueta(
                codigo_barras=cod,
                nome_produto=f"{tipo_peca} {marca}".strip(),
                tamanho=v_sel.get("tamanho", "?"),
                preco=v_sel.get("preco_venda", preco_pad),
                quantidade=1,
            )
            if c:
                ok, msg = imprimir_etiqueta(c)
                if ok:
                    messagebox.showinfo("Impressão", f"Etiqueta QR Code ({cod}) enviada para a impressora!")
                else:
                    messagebox.showwarning("Aviso", f"Gerada com sucesso, mas envio falhou: {msg}")

        ctk.CTkButton(
            frame_rodape,
            text="🖨️  Imprimir Esta Etiqueta",
            command=_imprimir_este,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#1B7A4C",
            hover_color="#059669",
            height=38,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            frame_rodape,
            text="✕  Fechar",
            command=win.destroy,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#22273A",
            hover_color="#2D7DD2",
            height=38,
            width=90,
        ).pack(side="right")

        _atualizar_qr()

    def _acao_barcode(self, dados_produto: dict):
        """
        Abre o Carrinho de Impressão em Lote para Etiquetas QR Code.
        Lista todos os tamanhos/variações do produto com campos de
        quantidade individuais. Um único botão envia tudo para a impressora.
        """
        produto_id = dados_produto.get("produto_id", 0)
        tipo_peca  = dados_produto.get("tipo_peca", "Produto")
        marca      = dados_produto.get("marca", "")
        preco_pad  = dados_produto.get("preco_venda", 0.0)

        from controllers.estoque_ctrl import buscar_produto_completo
        dados_completos = buscar_produto_completo(produto_id)
        variacoes = dados_completos.get("variacoes", []) if dados_completos else []

        # ── Singleton ────────────────────────────────────────────────────
        if self._popup_barcode and self._popup_barcode.winfo_exists():
            self._popup_barcode.destroy()

        win = ctk.CTkToplevel(self)
        win.title(f"🖨️  Fila de Impressão de Etiquetas QR Code — {tipo_peca}")
        win.geometry("500x540")
        win.resizable(False, True)
        win.attributes("-topmost", True)
        win.configure(fg_color="#0F1117")
        self._popup_barcode = win

        # ── Cabeçalho ────────────────────────────────────────────────────
        ctk.CTkLabel(
            win,
            text="🏷️  Carrinho de Impressão de Etiquetas QR Code",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#E1B12C",
        ).pack(pady=(18, 2))

        ctk.CTkLabel(
            win,
            text=f"{tipo_peca}  —  {marca}  |  Defina a quantidade de etiquetas com QR Code de cada tamanho",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8A8FA8",
        ).pack(pady=(0, 8))

        ctk.CTkFrame(win, height=1, fg_color="#22273A", corner_radius=0).pack(
            fill="x", padx=18, pady=(0, 2)
        )

        # ── Grade scrollável de tamanhos ──────────────────────────────────
        scroll_area = ctk.CTkScrollableFrame(
            win,
            fg_color="#16191F",
            corner_radius=10,
            scrollbar_button_color="#2D7DD2",
            scrollbar_button_hover_color="#E1B12C",
            height=300,
        )
        scroll_area.pack(fill="x", padx=18, pady=10)
        scroll_area.grid_columnconfigure(0, weight=1)
        scroll_area.grid_columnconfigure(1, weight=0)
        scroll_area.grid_columnconfigure(2, weight=0)

        # Linha de cabeçalho
        for col, txt, anc in [
            (0, "Tamanho  /  QR Code",           "w"),
            (1, "Estoque",                       "center"),
            (2, "Qtd. Etiquetas",                "center"),
        ]:
            ctk.CTkLabel(
                scroll_area,
                text=txt,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#6B7280",
                anchor=anc,
            ).grid(row=0, column=col, sticky="ew", padx=(12, 4), pady=(6, 10))

        # Prepara fallback se produto não tiver variações registradas
        itens = variacoes if variacoes else [{
            "codigo_barras": f"KNB{produto_id:05d}0001",
            "tamanho":       "Único",
            "preco_venda":   preco_pad,
            "estoque":       0,
        }]

        nome_prod = f"{tipo_peca} {marca}".strip()
        fila: list[dict] = []   # [{codigo, tamanho, preco, entry}]

        for row_i, v in enumerate(itens, start=1):
            cb      = v.get("codigo_barras", "") or f"KNB{produto_id:05d}{row_i:04d}"
            tam     = v.get("tamanho", "?")
            est     = v.get("estoque", 0)
            preco_v = v.get("preco_venda", preco_pad)

            # Linha separadora entre itens (exceto o primeiro)
            if row_i > 1:
                ctk.CTkFrame(scroll_area, height=1, fg_color="#22273A", corner_radius=0).grid(
                    row=row_i * 2 - 1, column=0, columnspan=3, sticky="ew", padx=8
                )

            grid_row = row_i * 2

            # Col 0 — tamanho + código
            ctk.CTkLabel(
                scroll_area,
                text=f"  {tam}   ·   {cb}",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                text_color="#F0F2F8",
                anchor="w",
            ).grid(row=grid_row, column=0, sticky="ew", padx=(12, 4), pady=5)

            # Col 1 — estoque (verde se > 0, vermelho se zerado)
            cor_est = "#34D399" if est > 0 else "#F87171"
            ctk.CTkLabel(
                scroll_area,
                text=f"{est} un.",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=cor_est,
                anchor="center",
            ).grid(row=grid_row, column=1, padx=12, pady=5)

            # Col 2 — entry de quantidade
            entry = ctk.CTkEntry(
                scroll_area,
                width=70, height=30,
                font=ctk.CTkFont(size=15),
                fg_color="#0F1117",
                border_color="#22273A",
                text_color="#F0F2F8",
                corner_radius=6,
                justify="center",
            )
            entry.insert(0, "0")
            entry.grid(row=grid_row, column=2, padx=(4, 14), pady=5)

            fila.append({
                "codigo":  cb,
                "tamanho": tam,
                "preco":   preco_v,
                "entry":   entry,
            })

        # ── Status e botões ───────────────────────────────────────────────
        lbl_status = ctk.CTkLabel(
            win, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8A8FA8",
        )
        lbl_status.pack(pady=(2, 4))

        frame_btns = ctk.CTkFrame(win, fg_color="transparent")
        frame_btns.pack(fill="x", padx=18, pady=(0, 16))

        def _imprimir_tudo():
            from utils_impressao import gerar_etiqueta, imprimir_etiqueta

            enviadas = 0
            erros    = []

            for item in fila:
                try:
                    qtd = int(item["entry"].get().strip() or "0")
                except ValueError:
                    qtd = 0
                if qtd <= 0:
                    continue

                lbl_status.configure(
                    text=f"⏳  Imprimindo Tam:{item['tamanho']}  ×{qtd}...",
                    text_color="#E1B12C",
                )
                win.update_idletasks()

                try:
                    caminho = gerar_etiqueta(
                        codigo_barras=item["codigo"],
                        nome_produto=nome_prod,
                        tamanho=item["tamanho"],
                        preco=item["preco"],
                        quantidade=qtd,
                    )
                    if caminho:
                        ok, msg_imp = imprimir_etiqueta(caminho)
                        if ok:
                            enviadas += qtd
                        else:
                            erros.append(f"Tam {item['tamanho']}: {msg_imp}")
                    else:
                        erros.append(f"Tam {item['tamanho']}: falha na geração")
                except Exception as exc:
                    erros.append(f"Tam {item['tamanho']}: {exc}")

            if enviadas > 0 and not erros:
                lbl_status.configure(
                    text=f"✅  {enviadas} etiqueta(s) enviadas com sucesso!",
                    text_color="#34D399",
                )
            elif enviadas > 0:
                lbl_status.configure(
                    text=f"⚠️  {enviadas} enviadas · {len(erros)} erro(s): {erros[0]}",
                    text_color="#F59E0B",
                )
            elif not erros:
                lbl_status.configure(
                    text="ℹ️  Defina qtd > 0 em pelo menos um tamanho.",
                    text_color="#8A8FA8",
                )
            else:
                lbl_status.configure(
                    text=f"❌  {erros[0]}",
                    text_color="#DC2626",
                )

        ctk.CTkButton(
            frame_btns,
            text="🖨️  Imprimir Etiquetas QR Code",
            command=_imprimir_tudo,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#4C1D95",
            hover_color="#A855F7",
            text_color="#FFFFFF",
            corner_radius=8,
            height=40,
            width=240,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            frame_btns,
            text="✕  Fechar",
            command=win.destroy,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#22273A",
            hover_color="#2D7DD2",
            text_color="#F0F2F8",
            corner_radius=8,
            height=40,
            width=100,
        ).pack(side="left")
