"""
tela_saude_margens.py — Painel de Saúde das Margens (Design Premium)
Sistema Kanemberg Multimarcas

Funcionalidades:
  • Cards de Métricas com barra de progresso visual (margem e markup)
  • Indicador de tendência (↑ / → / ↓) baseado na saúde da margem
  • Tabela de Desempenho por Categoria com cores semáforo
  • Ordenação clicável por coluna
  • Estado vazio com mensagem amigável
  • Dados via estoque_ctrl.buscar_dados_dashboard() sem dependência de Pandas
"""

import os
import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from collections import defaultdict

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import estoque_ctrl

# ── Paletas Dark Premium ─────────────────────────────────────────────────────
_BG_WINDOW    = ("#F0F2F8", "#0F1117")
_BG_CARD      = ("#FFFFFF", "#16191F")
_BG_HOVER     = ("#E8ECF4", "#22273A")
_FG_PRIMARY   = ("#1A1D2E", "#F0F2F8")
_FG_MUTED     = ("#6B7280", "#8A8FA8")
_FG_LABEL     = ("#4B5563", "#A0A8C0")
_ACCENT_GOLD  = ("#B8861F", "#E1B12C")
_ACCENT_BLUE  = ("#1B4F8A", "#2D7DD2")
_BORDER       = ("#DDE3EE", "#22273A")

# KPI card colours
_KPI_GOLD_BG  = ("#FFFBEB", "#2A1F00")
_KPI_GOLD_FG  = ("#92670A", "#E1B12C")
_KPI_BLUE_BG  = ("#EFF6FF", "#0A1A3B")
_KPI_BLUE_FG  = ("#1B4F8A", "#60A5FA")
_KPI_GRN_BG   = ("#F0FDF4", "#0D3B26")
_KPI_GRN_FG   = ("#15803D", "#34D399")
_KPI_RED_BG   = ("#FEF2F2", "#3B0A0A")
_KPI_RED_FG   = ("#DC2626", "#F87171")
_KPI_ORG_FG   = ("#D97706", "#F97316")

# Classificação de margens
_MARGEM_BOA   = 50.0
_MARGEM_MEDIA = 30.0

# Cores das tags da Treeview
_TV_BOA     = "#E1B12C"   # dourado
_TV_MEDIA   = "#F97316"   # laranja
_TV_RUIM    = "#F87171"   # vermelho

BTN_RELOAD  = ("#1B4F8A", "#2D7DD2")


def _hex(color_tuple) -> str:
    mode = ctk.get_appearance_mode()
    return color_tuple[1] if mode != "Light" else color_tuple[0]


def _aplicar_estilo_treeview_margens(bg_hex: str):
    s = ttk.Style()
    s.configure(
        "Margens.Treeview",
        rowheight=32,
        font=("Segoe UI", 10),
        background=bg_hex,
        fieldbackground=bg_hex,
        foreground=_hex(_FG_PRIMARY),
        borderwidth=0,
    )
    s.configure(
        "Margens.Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        background=_hex(_BG_HOVER),
        foreground=_hex(_ACCENT_GOLD),
        relief="flat",
    )
    s.map(
        "Margens.Treeview",
        background=[("selected", _hex(_ACCENT_BLUE))],
        foreground=[("selected", "#FFFFFF")],
    )
    s.configure(
        "Margens.Vertical.TScrollbar",
        troughcolor=_hex(_BG_WINDOW),
        background=_hex(_ACCENT_BLUE),
        arrowcolor=_hex(_FG_PRIMARY),
        relief="flat", borderwidth=0,
    )


# ── Cálculos de margem em Python puro ────────────────────────────────────────

def _calcular_metricas(dados: list) -> dict:
    if not dados:
        return {
            "margem_media_loja": 0.0,
            "markup_medio_loja": 0.0,
            "faturamento_total": 0.0,
            "total_vendas": 0,
            "por_categoria": {},
        }

    margens_item   = []
    markups_item   = []
    fat_total      = 0.0
    custo_total_loja = 0.0
    total_vendas   = 0

    categ = defaultdict(lambda: {
        "qtd": 0, "faturamento": 0.0,
        "custo_total": 0.0, "margens": [], "markups": [],
    })

    for v in dados:
        venda      = float(v.get("valor_total") or 0)
        custo_unit = float(v.get("preco_custo") or 0)
        qtd        = int(v.get("quantidade") or 1)
        custo      = custo_unit * qtd
        tipo       = str(v.get("tipo") or "Sem Categoria").strip() or "Sem Categoria"

        fat_total    += venda
        custo_total_loja += custo
        total_vendas += qtd

        if venda > 0:
            margem = ((venda - custo) / venda) * 100
            markup = ((venda - custo) / custo) * 100
            margens_item.append(margem)
            markups_item.append(markup)
            categ[tipo]["margens"].append(margem)
            categ[tipo]["markups"].append(markup)

        categ[tipo]["qtd"]         += qtd
        categ[tipo]["faturamento"] += venda
        categ[tipo]["custo_total"] += custo

    margem_media_loja = ((fat_total - custo_total_loja) / fat_total * 100) if fat_total > 0 else 0.0
    markup_medio_loja = ((fat_total - custo_total_loja) / custo_total_loja * 100) if custo_total_loja > 0 else 0.0

    por_categoria = {}
    for tipo, agg in categ.items():
        f = agg["faturamento"]
        c = agg["custo_total"]
        m_media = ((f - c) / f * 100) if f > 0 else 0.0
        mk_med  = ((f - c) / c * 100) if c > 0 else 0.0
        por_categoria[tipo] = {
            "qtd":        agg["qtd"],
            "faturamento": agg["faturamento"],
            "margem":     m_media,
            "markup":     mk_med,
        }

    return {
        "margem_media_loja": margem_media_loja,
        "markup_medio_loja": markup_medio_loja,
        "faturamento_total": fat_total,
        "total_vendas":      total_vendas,
        "por_categoria":     por_categoria,
    }


def _tendencia(valor, limiar_bom, limiar_medio):
    """Retorna ícone de tendência baseado no valor."""
    if valor >= limiar_bom:
        return "↑", _TV_BOA
    elif valor >= limiar_medio:
        return "→", _TV_MEDIA
    else:
        return "↓", _TV_RUIM


# ── Classe principal ──────────────────────────────────────────────────────────

class TelaSaudeMargens(ctk.CTkFrame):
    """Painel de Saúde das Margens com indicadores visuais premium."""

    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=_BG_WINDOW)
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construir_interface()
        self.after(150, self._recarregar_dados)

    def destroy(self):
        for widget in self.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass
        super().destroy()

    # ── Construção ───────────────────────────────────────────────────

    def _construir_interface(self):
        self._construir_header()
        frame_corpo = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_corpo.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        frame_corpo.grid_columnconfigure(0, weight=1)
        frame_corpo.grid_columnconfigure(1, weight=2)
        frame_corpo.grid_rowconfigure(0, weight=1)
        self._construir_coluna_cards(frame_corpo)
        self._construir_coluna_tabela(frame_corpo)

    # ── Cabeçalho ────────────────────────────────────────────────────

    def _construir_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="📈  Saúde das Margens",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            frame,
            text="Análise de Margem Real vs. Markup — todos os períodos",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkButton(
            frame,
            text="↻  Atualizar",
            command=self._recarregar_dados,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=BTN_RELOAD,
            hover_color=_ACCENT_GOLD,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=32, width=120,
        ).grid(row=0, column=1, rowspan=2, sticky="e")

    # ── Coluna Esquerda: KPI Cards ────────────────────────────────────

    def _construir_coluna_cards(self, parent):
        self._frame_cards = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        self._frame_cards.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._frame_cards.grid_columnconfigure(0, weight=1)

        # Card de margem com barra de progresso
        self._card_margem, self._canvas_margem = self._criar_kpi_card_com_gauge(
            0, "Margem Real Média", "— %", "Lucro / Venda × 100",
            _KPI_GOLD_BG, _KPI_GOLD_FG
        )
        self._card_markup, self._canvas_markup = self._criar_kpi_card_com_gauge(
            1, "Markup Médio Aplicado", "— %", "Lucro / Custo × 100",
            _KPI_BLUE_BG, _KPI_BLUE_FG
        )
        self._card_fat  = self._criar_kpi_card_simples(
            2, "Faturamento Total", "R$ —", "Soma de todas as vendas",
            _KPI_GRN_BG, _KPI_GRN_FG
        )
        self._card_qtd  = self._criar_kpi_card_simples(
            3, "Peças Vendidas", "—", "Total de unidades vendidas",
            _KPI_BLUE_BG, _KPI_BLUE_FG
        )
        self._construir_legenda()

    def _criar_kpi_card_com_gauge(self, row, titulo, valor, subtitulo, bg_t, fg_t):
        """Card KPI com barra de progresso horizontal (gauge)."""
        card = ctk.CTkFrame(
            self._frame_cards, fg_color=bg_t,
            corner_radius=12, border_width=1, border_color=_BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 2))

        lbl_val = ctk.CTkLabel(
            card, text=valor,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=fg_t, anchor="w",
        )
        lbl_val.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))

        # Barra de progresso (gauge)
        gauge_bg  = _hex(bg_t)
        gauge_fg  = _hex(fg_t)
        canvas = tk.Canvas(
            card, height=6, bg=gauge_bg,
            bd=0, highlightthickness=0,
        )
        canvas.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))
        # Trilha de fundo
        canvas.bind("<Configure>", lambda e, c=canvas, fg=gauge_fg: self._desenhar_gauge(c, 0, fg))

        ctk.CTkLabel(
            card, text=subtitulo,
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))

        return lbl_val, canvas

    def _criar_kpi_card_simples(self, row, titulo, valor, subtitulo, bg_t, fg_t):
        """Card KPI simples sem gauge."""
        card = ctk.CTkFrame(
            self._frame_cards, fg_color=bg_t,
            corner_radius=12, border_width=1, border_color=_BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 2))

        lbl_val = ctk.CTkLabel(
            card, text=valor,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=fg_t, anchor="w",
        )
        lbl_val.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 2))

        ctk.CTkLabel(
            card, text=subtitulo,
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))

        return lbl_val

    def _desenhar_gauge(self, canvas, pct, cor_hex):
        """Desenha a barra de progresso no canvas. pct = 0 a 100."""
        w = canvas.winfo_width()
        h = canvas.winfo_height() or 6
        if w <= 1:
            return
        
        fill_w = max(0, min(w, int(w * pct / 100)))
        
        if not hasattr(canvas, "_bg_rect"):
            canvas._bg_rect = canvas.create_rectangle(0, 0, w, h, fill=_hex(_BG_HOVER), outline="")
            canvas._fg_rect = canvas.create_rectangle(0, 0, fill_w, h, fill=cor_hex, outline="")
        else:
            canvas.coords(canvas._bg_rect, 0, 0, w, h)
            canvas.itemconfig(canvas._bg_rect, fill=_hex(_BG_HOVER))
            canvas.coords(canvas._fg_rect, 0, 0, fill_w, h)
            canvas.itemconfig(canvas._fg_rect, fill=cor_hex)

    def _construir_legenda(self):
        frame_leg = ctk.CTkFrame(
            self._frame_cards, fg_color=_BG_CARD,
            corner_radius=10, border_width=1, border_color=_BORDER,
        )
        frame_leg.grid(row=4, column=0, sticky="ew", pady=(4, 0))

        ctk.CTkLabel(
            frame_leg, text="Legenda da Tabela:",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=_FG_LABEL, anchor="w",
        ).pack(anchor="w", padx=14, pady=(10, 4))

        for cor_hex, descricao in [
            (_TV_BOA,   "↑  Margem ≥ 50%  — Excelente"),
            (_TV_MEDIA, "→  Margem 30–49% — Atenção"),
            (_TV_RUIM,  "↓  Margem < 30%  — Risco"),
        ]:
            linha = ctk.CTkFrame(frame_leg, fg_color="transparent")
            linha.pack(anchor="w", padx=14, pady=2)
            ctk.CTkLabel(
                linha, text="■",
                font=ctk.CTkFont(size=14),
                text_color=cor_hex, fg_color="transparent",
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                linha, text=descricao,
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color=_FG_MUTED, fg_color="transparent",
            ).pack(side="left")

        ctk.CTkFrame(frame_leg, height=1, fg_color=_BORDER, corner_radius=0).pack(fill="x", padx=10, pady=(8, 6))

        for formula in [
            "Margem = (Venda − Custo) ÷ Venda × 100",
            "Markup  = (Venda − Custo) ÷ Custo  × 100",
        ]:
            ctk.CTkLabel(
                frame_leg, text=formula,
                font=ctk.CTkFont(family="Consolas", size=9),
                text_color=_ACCENT_GOLD, anchor="w",
            ).pack(anchor="w", padx=14, pady=1)

        ctk.CTkFrame(frame_leg, height=6, fg_color="transparent").pack()

    # ── Coluna Direita: Treeview de Categorias ────────────────────────

    def _construir_coluna_tabela(self, parent):
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD,
            corner_radius=12, border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text="Desempenho por Categoria de Produto",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        bg_tv = _hex(_BG_CARD)
        _aplicar_estilo_treeview_margens(bg_tv)

        frame_tv = tk.Frame(frame, bg=bg_tv)
        frame_tv.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        colunas = ("categoria", "qtd", "faturamento", "markup", "margem", "status")
        self.tree = ttk.Treeview(
            frame_tv, columns=colunas, show="headings",
            style="Margens.Treeview",
        )

        self.tree.tag_configure("boa",   foreground=_TV_BOA)
        self.tree.tag_configure("media", foreground=_TV_MEDIA)
        self.tree.tag_configure("ruim",  foreground=_TV_RUIM)

        for col, label, w, anc in [
            ("categoria",   "Categoria / Modelo",   180, "w"),
            ("qtd",         "Qtd",                   60, "center"),
            ("faturamento", "Faturamento (R$)",      130, "e"),
            ("markup",      "Markup %",               90, "center"),
            ("margem",      "Margem Real %",          100, "center"),
            ("status",      "Status",                 80, "center"),
        ]:
            self.tree.heading(col, text=label, command=lambda c=col: self._ordenar_por(c))
            self.tree.column(col, width=w, anchor=anc, minwidth=50)

        scroll_v = ttk.Scrollbar(frame_tv, orient="vertical", command=self.tree.yview,
                                  style="Margens.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scroll_v.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_v.pack(side="right", fill="y")

        self._ordem_col = None
        self._ordem_asc = True

    # ── Carregamento de dados ─────────────────────────────────────────

    def _recarregar_dados(self):
        try:
            dados_brutos = estoque_ctrl.buscar_dados_dashboard()
            metricas     = _calcular_metricas(dados_brutos)
        except Exception as e:
            print(f"[SaudeMargens] Erro ao carregar dados: {e}")
            metricas = {
                "margem_media_loja": 0.0, "markup_medio_loja": 0.0,
                "faturamento_total": 0.0, "total_vendas": 0, "por_categoria": {},
            }
        self._atualizar_cards(metricas)
        self._atualizar_tabela(metricas["por_categoria"])

    def _atualizar_cards(self, m: dict):
        margem = m["margem_media_loja"]
        markup = m["markup_medio_loja"]
        fat    = m["faturamento_total"]
        qtd    = m["total_vendas"]

        # Cor dinâmica do card de margem
        if margem >= _MARGEM_BOA:
            cor_margem = _KPI_GRN_FG
        elif margem >= _MARGEM_MEDIA:
            cor_margem = _KPI_ORG_FG
        else:
            cor_margem = _KPI_RED_FG

        seta_m, _ = _tendencia(margem, _MARGEM_BOA, _MARGEM_MEDIA)
        seta_mk, _ = _tendencia(markup, 80, 40)

        self._card_margem.configure(text=f"{seta_m}  {margem:.1f}%", text_color=cor_margem)
        self._card_markup.configure(text=f"{seta_mk}  {markup:.1f}%")
        self._card_fat.configure(
            text=f"R$ {fat:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        self._card_qtd.configure(text=str(qtd))

        # Atualiza os gauges
        self.after(100, lambda: self._desenhar_gauge(
            self._canvas_margem, min(margem, 100), _hex(cor_margem)
        ))
        self.after(100, lambda: self._desenhar_gauge(
            self._canvas_markup, min(markup / 2, 100), _hex(_KPI_BLUE_FG)
        ))

    def _atualizar_tabela(self, por_categoria: dict):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if not por_categoria:
            self.tree.insert("", "end", values=(
                "Nenhuma venda registrada", "—", "—", "—", "—", "—"
            ))
            return

        itens = sorted(
            por_categoria.items(),
            key=lambda x: x[1]["faturamento"],
            reverse=True,
        )

        for tipo, agg in itens:
            margem = agg["margem"]
            markup = agg["markup"]
            fat    = agg["faturamento"]
            qtd    = agg["qtd"]

            fat_str = f"R$ {fat:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            if margem >= _MARGEM_BOA:
                tag    = "boa"
                status = "✅ Ótimo"
            elif margem >= _MARGEM_MEDIA:
                tag    = "media"
                status = "⚠️ Atenção"
            else:
                tag    = "ruim"
                status = "🔴 Risco"

            self.tree.insert(
                "", "end",
                values=(tipo, str(qtd), fat_str, f"{markup:.1f}%", f"{margem:.1f}%", status),
                tags=(tag,),
            )

    # ── Ordenação clicável ────────────────────────────────────────────

    def _ordenar_por(self, coluna: str):
        if self._ordem_col == coluna:
            self._ordem_asc = not self._ordem_asc
        else:
            self._ordem_col = coluna
            self._ordem_asc = True

        itens = [
            (self.tree.set(child, coluna), child)
            for child in self.tree.get_children("")
        ]

        def _chave(tupla):
            val = tupla[0].replace("R$ ", "").replace(".", "").replace(",", ".").replace("%", "")
            try:
                return float(val)
            except ValueError:
                return val.lower()

        itens.sort(key=_chave, reverse=not self._ordem_asc)
        for idx, (_, child) in enumerate(itens):
            self.tree.move(child, "", idx)
