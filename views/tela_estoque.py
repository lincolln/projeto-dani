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

# ── Paletas dinâmicas (claro, escuro — Tema Slate Dark Mobile) ──────────────
_BG_WINDOW    = ("#F0F2F8", "#0f172a")
_BG_CARD      = ("#FFFFFF", "#1e293b")
_BG_CARD_SUB  = ("#F4F6FB", "#0f172a")
_BG_HOVER     = ("#E8ECF4", "#334155")
_FG_PRIMARY   = ("#1A1D2E", "#f8fafc")
_FG_MUTED     = ("#6B7280", "#94a3b8")
_FG_LABEL     = ("#4B5563", "#cbd5e1")
_ACCENT_GOLD  = ("#d97706", "#f59e0b")
_ACCENT_BLUE  = ("#2563eb", "#3b82f6")
_ACCENT_GREEN = ("#16a34a", "#22c55e")
_ACCENT_RED   = ("#dc2626", "#ef4444")
_ACCENT_PURP  = ("#6B21A8", "#A855F7")
_BORDER       = ("#DDE3EE", "#334155")
_BORDER_HOVER = ("#2563eb", "#3b82f6")
_SEARCH_BG    = ("#FFFFFF", "#1e293b")

# Dimensões do card (layout horizontal/compacto estilo Mobile sem foto)
_CARD_W       = 310   # largura fixa de cada card em px
_IMG_SIZE     = 150   # mantido por compatibilidade
_CIRCLE_SIZE  = 16    # diâmetro dos círculos de cor


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
# CLASSE — CARD PRODUTO (DESIGN IDÊNTICO AO MOBILE PWA SEM FOTO)
# ════════════════════════════════════════════════════════════════════════════

class CardProdutoVertical(ctk.CTkFrame):
    """
    Card compacto idêntico ao card de Estoque do PWA Mobile (sem área de foto):
      • Linha 0: [Modelo — Marca] .......................... [R$ 100,00]
      • Linha 1: [Corte | Tecido]
      • Linha 2: [6 un. em estoque]  + círculos de cores
      • Linha 3: Divisor sutil
      • Linha 4: Pílulas de tamanhos [ P ×0 ] [ M ×5 ] [ G ×1 ]
      • Linha 5: Divisor sutil
      • Linha 6: Custo discreto + 5 botões minimalistas só com emojis:
                 [🛒 Vender] [📱 Ver QR] [🖨️ Imprimir] [✏️ Editar] [🗑️ Apagar]
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
            corner_radius=14,
            border_width=1,
            border_color=_BORDER,
        )
        ctk.CTkFrame(self, width=_CARD_W, height=0, fg_color="transparent").grid(row=7, column=0)

        self._dados    = dados_produto
        self._on_edit  = on_editar
        self._on_del   = on_apagar
        self._on_sell  = on_vender
        self._on_bar   = on_barcode
        self._on_ver_qr = on_ver_qr
        self._cache_imgs    = cache_imgs
        self._cache_circles = cache_circles
        self._botoes_acao: list = []

        self._menu_atual: ctk.CTkToplevel | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)   # Linha das pílulas de tamanho absorve diferença de altura

        self._construir()
        self._bind_hover_e_click()

    # ── Construção ──────────────────────────────────────────────────────────

    def _construir(self):
        d = self._dados
        tams_resumo = d.get("tamanhos_resumo", {})
        estoque_total = sum(tams_resumo.values()) if tams_resumo else 0

        # ── 0. Linha 1: Título (esquerda) + Preço Verde (direita) ────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        frame_header.grid_columnconfigure(0, weight=1)

        modelo_str = d.get("tipo_peca", "—")
        marca_str  = d.get("marca", "")
        titulo_card = f"{modelo_str} — {marca_str}" if marca_str else modelo_str

        ctk.CTkLabel(
            frame_header,
            text=titulo_card,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=_FG_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=185,
        ).grid(row=0, column=0, sticky="w")

        preco_venda = d.get("preco_venda", 0.0)
        preco_fmt = f"R$ {preco_venda:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ctk.CTkLabel(
            frame_header,
            text=preco_fmt,
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=_ACCENT_GREEN,
            anchor="e",
        ).grid(row=0, column=1, sticky="ne", padx=(8, 0))

        # ── 1. Linha 2: Subtítulo (Corte | Tecido) ───────────────────────
        partes_sub = [p.strip() for p in (d.get("corte", ""), d.get("tecido", "")) if p and p.strip()]
        subtitulo = " | ".join(partes_sub) if partes_sub else "Padrão"
        ctk.CTkLabel(
            self,
            text=subtitulo,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=_FG_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 6))

        # ── 2. Linha 3: Badge "X un. em estoque" + Círculos de Cores ─────
        frame_badge_row = ctk.CTkFrame(self, fg_color="transparent")
        frame_badge_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        frame_badge_row.grid_columnconfigure(1, weight=1)

        if estoque_total <= 0:
            cor_badge_bg = ("#fee2e2", "#3b1824")
            cor_badge_fg = ("#dc2626", "#f87171")
            txt_badge = "Esgotado"
        elif estoque_total <= 3:
            cor_badge_bg = ("#fef3c7", "#382814")
            cor_badge_fg = ("#d97706", "#fbbf24")
            txt_badge = f"{estoque_total} un. restantes"
        else:
            cor_badge_bg = ("#dbeafe", "#1e3a5f")
            cor_badge_fg = ("#2563eb", "#60a5fa")
            txt_badge = f"{estoque_total} un. em estoque"

        badge_est = ctk.CTkFrame(frame_badge_row, fg_color=cor_badge_bg, corner_radius=999)
        badge_est.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            badge_est,
            text=txt_badge,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=cor_badge_fg,
        ).pack(padx=10, pady=2)

        cores_unicas = d.get("cores_lista", [])
        if cores_unicas:
            frame_cores = ctk.CTkFrame(frame_badge_row, fg_color="transparent")
            frame_cores.grid(row=0, column=1, sticky="e")
            for idx, (nome_cor, hex_cor) in enumerate(cores_unicas[:6]):
                try:
                    circ = _criar_circulo_imagem(hex_cor, _CIRCLE_SIZE)
                    self._cache_circles.append(circ)
                    lbl = ctk.CTkLabel(
                        frame_cores,
                        text="",
                        image=circ,
                        fg_color="transparent",
                        width=_CIRCLE_SIZE,
                        height=_CIRCLE_SIZE,
                    )
                    lbl.grid(row=0, column=idx, padx=2)
                    lbl.bind("<Enter>", lambda e, n=nome_cor: self._tooltip_show(e, n))
                    lbl.bind("<Leave>", self._tooltip_hide)
                except Exception:
                    pass

        # ── 3. Divisor tracejado/sutil 1 ─────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=_BORDER, corner_radius=0).grid(
            row=3, column=0, sticky="ew", padx=16, pady=(0, 10)
        )

        # ── 4. Pílulas de Tamanhos (estilo [ P ×0 ] [ M ×5 ] [ G ×1 ]) ───
        frame_pills = ctk.CTkFrame(self, fg_color="transparent")
        frame_pills.grid(row=4, column=0, sticky="nw", padx=16, pady=(0, 10))

        tams_vid_map = d.get("tamanhos_vid_map", {})
        if tams_resumo:
            tams_ord = sorted(
                tams_resumo.items(),
                key=lambda x: _ORDEM_TAMANHOS.get(x[0].upper(), 99)
            )
            max_cols_pills = 4
            for idx_t, (tam_k, qtd_v) in enumerate(tams_ord):
                r_t = idx_t // max_cols_pills
                c_t = idx_t % max_cols_pills
                sem_est = (qtd_v <= 0)
                vid_tam = tams_vid_map.get(tam_k)
                pill = ctk.CTkFrame(
                    frame_pills,
                    fg_color=("#F4F6FB", "#0f172a"),
                    corner_radius=8,
                    border_width=1,
                    border_color=("#E2E8F0", "#1e293b") if sem_est else _BORDER,
                    cursor="arrow" if sem_est else "hand2",
                )
                pill.grid(row=r_t, column=c_t, padx=(0, 6), pady=3, sticky="w")

                inner_p = ctk.CTkFrame(pill, fg_color="transparent")
                inner_p.pack(padx=10, pady=4)

                lbl_t = ctk.CTkLabel(
                    inner_p,
                    text=str(tam_k),
                    font=ctk.CTkFont(
                        family="Segoe UI", size=13, weight="bold",
                        overstrike=sem_est,
                    ),
                    text_color=("#94a3b8", "#475569") if sem_est else _FG_PRIMARY,
                )
                lbl_t.pack(side="left")

                lbl_q = ctk.CTkLabel(
                    inner_p,
                    text=f" ×{qtd_v}",
                    font=ctk.CTkFont(
                        family="Segoe UI", size=13,
                        overstrike=sem_est,
                    ),
                    text_color=("#94a3b8", "#475569") if sem_est else _FG_MUTED,
                )
                lbl_q.pack(side="left")

                if not sem_est and vid_tam is not None:
                    dica_tam = f"Vender Tam. {tam_k} ({qtd_v} disp.)"
                    for w_p in (pill, inner_p, lbl_t, lbl_q):
                        w_p.bind("<Button-1>", lambda e, v=vid_tam: self._on_sell(v))
                        w_p.bind("<Enter>", lambda e, t=dica_tam: self._tooltip_show(e, t), add="+")
                        w_p.bind("<Leave>", self._tooltip_hide, add="+")
        else:
            ctk.CTkLabel(
                frame_pills,
                text="Sem grade cadastrada",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=_FG_MUTED,
            ).grid(row=0, column=0, sticky="w")

        # ── 5. Divisor sutil 2 ───────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=_BORDER, corner_radius=0).grid(
            row=5, column=0, sticky="ew", padx=16, pady=(0, 10)
        )

        # ── 6. Rodapé: 5 Botões Minimalistas SÓ COM EMOJIS ───────────────
        # Funções do PC: (1) Vender 🛒 | (2) Ver QR 📱 | (3) Imprimir 🖨️ | (4) Editar ✏️ | (5) Apagar 🗑️
        frame_rodape = ctk.CTkFrame(self, fg_color="transparent")
        frame_rodape.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 12))
        frame_rodape.grid_columnconfigure(0, weight=1)

        # Custo discreto à esquerda
        custo_val = d.get("preco_custo", 0.0)
        ctk.CTkLabel(
            frame_rodape,
            text=f"Custo R${custo_val:.0f}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=_FG_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # Container dos 5 botões de emoji à direita (igual ao print do mobile)
        frame_btns = ctk.CTkFrame(frame_rodape, fg_color="transparent")
        frame_btns.grid(row=0, column=1, sticky="e")

        produto_id   = d.get("produto_id")

        acoes_config = [
            # (emoji, tooltip, fg_color, hover_color, border_color, command)
            (
                "🛒", "Vender no PDV",
                ("#dcfce7", "#143325"), _ACCENT_GREEN, ("#86efac", "#1e4d38"),
                lambda: self._on_sell(d),
            ),
            (
                "📱", "Ver QR Code na Tela",
                _BG_CARD_SUB, _ACCENT_BLUE, _BORDER,
                lambda: self._on_ver_qr(d) if self._on_ver_qr else self._on_bar(d),
            ),
            (
                "🖨️", "Imprimir Etiquetas",
                _BG_CARD_SUB, _ACCENT_BLUE, _BORDER,
                lambda: self._on_bar(d),
            ),
            (
                "✏️", "Editar Produto",
                _BG_CARD_SUB, _ACCENT_BLUE, _BORDER,
                lambda: self._on_edit(produto_id),
            ),
            (
                "🗑️", "Apagar Produto",
                ("#fee2e2", "#2d161d"), _ACCENT_RED, ("#fca5a5", "#5c1d24"),
                lambda: self._on_del(produto_id),
            ),
        ]

        self._botoes_acao = []
        for idx_b, (emoji, dica, fg_c, hov_c, brd_c, cmd) in enumerate(acoes_config):
            btn = ctk.CTkButton(
                frame_btns,
                text=emoji,
                width=36,
                height=34,
                corner_radius=8,
                fg_color=fg_c,
                hover_color=hov_c,
                border_width=1,
                border_color=brd_c,
                font=ctk.CTkFont(size=15),
                command=cmd,
            )
            btn.grid(row=0, column=idx_b, padx=(4, 0))
            btn.bind("<Enter>", lambda e, t=dica: self._tooltip_show(e, t), add="+")
            btn.bind("<Leave>", self._tooltip_hide, add="+")
            self._botoes_acao.append(btn)

    # ── Hover visual na borda do card (sem popup ao clicar no card) ──────────

    def _bind_hover_e_click(self):
        """Aplica apenas efeito de destaque na borda ao passar o mouse (sem menu popup ao clicar)."""
        def _hover_on(e):
            self.configure(border_color=_BORDER_HOVER, border_width=2)

        def _hover_off(e):
            self.configure(border_color=_BORDER, border_width=1)

        for widget in [self, *self._todos_filhos(self)]:
            widget.bind("<Enter>", _hover_on, add="+")
            widget.bind("<Leave>", _hover_off, add="+")

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

    def atualizar_dados(self):
        """Recarrega os cards da vitrine ao retornar para a aba de Estoque."""
        self._renderizar_cards()

    def _on_busca_keyrelease(self, event=None):
        if self._debounce_busca_id:
            self.after_cancel(self._debounce_busca_id)
        self._debounce_busca_id = self.after(300, self._renderizar_cards)

    def _get_termo(self) -> str:
        return self.entry_busca.get().strip()

    def _renderizar_cards(self):
        """
        Busca todos os produtos agrupados por PAI, aplica busca tokenizada AND
        (modelo, marca, corte, tecido, cores e tamanhos) e reconstrói o grid de cards.
        """
        # Limpa a vitrine
        for w in self.frame_vitrine.winfo_children():
            w.destroy()

        # Carrega dados agrupados
        dados_brutos = estoque_ctrl.listar_produtos_vitrine_grade()
        termo = self._get_termo().lower()

        if termo:
            tokens = termo.split()
            produtos = []
            for p in dados_brutos:
                cores_str = " ".join(c[0] for c in p.get("cores_lista", []))
                tams_str  = " ".join(k for k, v in p.get("tamanhos_resumo", {}).items() if v > 0)
                ficha = " ".join([
                    p.get("tipo_peca", ""),
                    p.get("marca", ""),
                    p.get("corte", ""),
                    p.get("tecido", ""),
                    cores_str,
                    tams_str,
                ]).lower()
                if all(tk in ficha for tk in tokens):
                    produtos.append(p)
        else:
            produtos = dados_brutos

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
        # Cada card ocupa _CARD_W + margens
        colunas = max(1, min(largura_area // (_CARD_W + 30), 6))

        for c in range(7):
            self.frame_vitrine.grid_columnconfigure(c, weight=0)
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
    # AÇÕES DOS CARDS
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

    def _acao_vender(self, alvo):
        """Navega para a tela de venda com a variação pré-selecionada.
        Aceita um variacao_id (int) ao clicar direto na pílula de tamanho,
        ou o dict do produto ao clicar no botão 🛒 (abre seletor se houver >1 tamanho).
        """
        if isinstance(alvo, int):
            self.controller._ir_venda(variacao_id=alvo)
            return

        if isinstance(alvo, dict):
            tams_resumo  = alvo.get("tamanhos_resumo", {})
            tams_vid_map = alvo.get("tamanhos_vid_map", {})
            disponiveis  = [
                (tam, qtd, tams_vid_map.get(tam))
                for tam, qtd in sorted(
                    tams_resumo.items(),
                    key=lambda x: _ORDEM_TAMANHOS.get(x[0].upper(), 99),
                )
                if qtd > 0 and tams_vid_map.get(tam) is not None
            ]
            if not disponiveis:
                messagebox.showwarning(
                    "Sem Estoque",
                    "Este produto não possui variações com estoque disponível.",
                )
                return
            if len(disponiveis) == 1:
                self.controller._ir_venda(variacao_id=disponiveis[0][2])
                return

            # Mais de um tamanho disponível: abre seletor rápido
            win = ctk.CTkToplevel(self)
            win.title("Escolher Tamanho")
            win.geometry("320x260")
            win.resizable(False, False)
            win.attributes("-topmost", True)
            win.configure(fg_color="#0f172a")
            win.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() - 320) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 260) // 2
            win.geometry(f"+{max(20, x)}+{max(20, y)}")

            ctk.CTkLabel(
                win,
                text=f"🛒  {alvo.get('tipo_peca', 'Produto')}",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#f8fafc",
            ).pack(pady=(16, 2))
            ctk.CTkLabel(
                win,
                text="Qual tamanho deseja enviar para a Venda?",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#94a3b8",
            ).pack(pady=(0, 12))

            frame_b = ctk.CTkFrame(win, fg_color="transparent")
            frame_b.pack(padx=16, pady=4)
            for idx_b, (tam_k, qtd_v, vid_k) in enumerate(disponiveis):
                ctk.CTkButton(
                    frame_b,
                    text=f"{tam_k}  (×{qtd_v})",
                    width=82,
                    height=38,
                    corner_radius=8,
                    fg_color="#1e293b",
                    hover_color="#22c55e",
                    border_width=1,
                    border_color="#334155",
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    command=lambda v=vid_k: (win.destroy(), self.controller._ir_venda(variacao_id=v)),
                ).grid(row=idx_b // 3, column=idx_b % 3, padx=5, pady=5)
            return

        messagebox.showwarning(
            "Sem Estoque",
            "Este produto não possui variações com estoque disponível.",
        )

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
                        ok, msg_imp = True, ""
                        for _ in range(qtd):
                            ok, msg_imp = imprimir_etiqueta(caminho)
                            if not ok:
                                break
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
