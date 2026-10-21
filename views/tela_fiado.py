"""
tela_fiado.py — Controle de Fiado (Contas a Receber) — Slate Dark Mobile UI
===========================================================================
Interface 100% em Cards estilo Mobile PWA (sem tabelas ttk.Treeview aparentes):
  • Coluna 1 (Esquerda): Busca + Filtros Rápidos (Todos | Devendo | Atrasados | Em Dia)
    + Cards finos/compactos de clientes com barra de limite + Cadastro Rápido legível.
  • Coluna 2 (Centro): Header do Cliente com botões [💬 WhatsApp] [✏️ Editar] [🗑️ Excluir]
    + Painel de Recebimento Rápido com atalhos [Total] [50%] e meio (PIX/Dinheiro/Cartão)
    + Timeline de Extrato 100% em Cards (Compras com status FIFO e Pagamentos).
  • Coluna 3 (Direita): Central de Cobranças Prioritárias (Atrasados + Vencendo Hoje)
    100% em Cards interativos com atalho direto para Receber e WhatsApp.
"""

import os
import sys
import urllib.parse
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import fiado_ctrl

# ── Paleta Slate Dark Mobile ────────────────────────────────────────────────
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
_BORDER       = ("#DDE3EE", "#334155")

# KPI
_KPI_RED_BG  = ("#FEE2E2", "#2d161d");  _KPI_RED_FG  = ("#dc2626", "#f87171")
_KPI_YEL_BG  = ("#FEF3C7", "#382814");  _KPI_YEL_FG  = ("#d97706", "#fbbf24")
_KPI_BLU_BG  = ("#EFF6FF", "#172554");  _KPI_BLU_FG  = ("#2563eb", "#60a5fa")

# Botões de ação
_BTN_ADD = ("#2563eb", "#3b82f6")
_BTN_REC = ("#16a34a", "#22c55e")
_BTN_DEL = ("#dc2626", "#ef4444")


class TelaFiado(ctk.CTkFrame):
    """
    Tela de controle de fiado 100% remodelada no padrão Slate Dark Mobile:
      • Coluna 0: Carteira de Clientes (Cards finos e filtros rápidos)
      • Coluna 1: Ficha do Cliente + Recebimento Rápido + Timeline de Extrato em Cards
      • Coluna 2: Cobranças Prioritárias (Atrasados + Vencendo Hoje) em Cards
    """

    def __init__(self, parent, controller):
        super().__init__(
            parent,
            corner_radius=0,
            fg_color=_BG_WINDOW,
        )
        self.controller = controller
        self._cliente_ativo_id   = None
        self._cliente_ativo_nome = None
        self._cliente_ativo_dict = None
        self._debounce_busca_id  = None
        self._filtro_status      = "TODOS"  # TODOS | DEVENDO | ATRASADOS | EM_DIA
        self._meio_pgto_fiado    = ctk.StringVar(value="PIX")
        self._modal_editar       = None

        # Grid raiz
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construir_interface()

    # ════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO PRINCIPAL
    # ════════════════════════════════════════════════════════════════════

    def _construir_interface(self):
        self._construir_header()

        frame_corpo = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_corpo.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))
        frame_corpo.grid_columnconfigure(0, weight=32, uniform="col_fiado")
        frame_corpo.grid_columnconfigure(1, weight=44, uniform="col_fiado")
        frame_corpo.grid_columnconfigure(2, weight=24, uniform="col_fiado")
        frame_corpo.grid_rowconfigure(0, weight=1)

        self._construir_coluna_esquerda(frame_corpo)
        self._construir_coluna_direita(frame_corpo)
        self._construir_coluna_alertas(frame_corpo)

        self._recarregar_clientes()
        self._atualizar_kpis()
        self.atualizar_tabela_alertas_do_dia()

    # ── HEADER COM KPIs ─────────────────────────────────────────────

    def _construir_header(self):
        frame_header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 10))
        frame_header.grid_columnconfigure(0, weight=1)

        bloco_titulo = ctk.CTkFrame(frame_header, fg_color="transparent")
        bloco_titulo.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            bloco_titulo,
            text="💳  Controle de Fiado",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=_FG_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            bloco_titulo,
            text="Gestão de carteira de clientes, limites de crédito e recebimentos",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=_FG_MUTED,
            anchor="w",
        ).pack(anchor="w")

        # KPI cards à direita
        frame_kpis = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_kpis.grid(row=0, column=1, sticky="e")

        self.kpi_total_aberto   = self._criar_kpi_card(frame_kpis, "TOTAL EM ABERTO",   "R$ 0,00", _KPI_RED_BG, _KPI_RED_FG, ("#fca5a5", "#5c1d24"), 0)
        self.kpi_qtd_devedores  = self._criar_kpi_card(frame_kpis, "CLIENTES DEVENDO",  "0",       _KPI_YEL_BG, _KPI_YEL_FG, ("#fde68a", "#5c4014"), 1)
        self.kpi_total_clientes = self._criar_kpi_card(frame_kpis, "TOTAL DE CLIENTES", "0",       _KPI_BLU_BG, _KPI_BLU_FG, ("#93c5fd", "#1e3a8a"), 2)

    def _criar_kpi_card(self, parent, titulo, valor, bg_tuple, fg_tuple, brd_tuple, col) -> ctk.CTkLabel:
        """Cria um card de métrica CTk moderno com borda sutil e tipografia nítida."""
        card = ctk.CTkFrame(
            parent,
            fg_color=bg_tuple,
            corner_radius=12,
            border_width=1,
            border_color=brd_tuple,
        )
        card.grid(row=0, column=col, padx=5, sticky="ew")

        ctk.CTkLabel(
            card, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=_FG_MUTED,
        ).pack(padx=18, pady=(8, 0))

        lbl = ctk.CTkLabel(
            card, text=valor,
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=fg_tuple,
        )
        lbl.pack(padx=18, pady=(2, 8))
        return lbl

    # ════════════════════════════════════════════════════════════════════
    # COLUNA ESQUERDA — CARTEIRA DE CLIENTES (CARDS FINOS + FILTROS)
    # ════════════════════════════════════════════════════════════════════

    def _construir_coluna_esquerda(self, parent):
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=14,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)

        # Cabeçalho da coluna
        topo_esq = ctk.CTkFrame(frame, fg_color="transparent")
        topo_esq.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        topo_esq.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            topo_esq, text="👥  Carteira de Clientes",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_contador_lista = ctk.CTkLabel(
            topo_esq, text="0 clientes",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=_FG_MUTED, anchor="e",
        )
        self.lbl_contador_lista.grid(row=0, column=1, sticky="e")

        # ── Busca ──────────────────────────────────────────────────
        self.entry_busca = ctk.CTkEntry(
            frame,
            placeholder_text="🔍  Buscar por nome ou telefone...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=_BG_CARD_SUB,
            border_color=_BORDER,
            text_color=_FG_PRIMARY,
            placeholder_text_color=_FG_MUTED,
            corner_radius=10,
            height=36,
        )
        self.entry_busca.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.entry_busca.bind("<KeyRelease>", self._on_busca_keyrelease)

        # ── Pílulas de Filtro Rápido ───────────────────────────────
        frame_filtros = ctk.CTkFrame(frame, fg_color="transparent")
        frame_filtros.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        for i in range(4):
            frame_filtros.grid_columnconfigure(i, weight=1)

        self._btns_filtro: dict[str, ctk.CTkButton] = {}
        opcoes_filtro = [
            ("TODOS",     "Todos"),
            ("DEVENDO",   "🔴 Devendo"),
            ("ATRASADOS", "⚠️ Atrasados"),
            ("EM_DIA",    "✅ Em Dia"),
        ]
        for idx_f, (chave_f, rotulo_f) in enumerate(opcoes_filtro):
            btn_f = ctk.CTkButton(
                frame_filtros,
                text=rotulo_f,
                height=26,
                corner_radius=8,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color=_ACCENT_BLUE if chave_f == "TODOS" else _BG_CARD_SUB,
                hover_color=_ACCENT_BLUE,
                text_color=("#FFFFFF", "#FFFFFF") if chave_f == "TODOS" else _FG_MUTED,
                border_width=1,
                border_color=_BORDER,
                command=lambda k=chave_f: self._set_filtro_status(k),
            )
            btn_f.grid(row=0, column=idx_f, padx=2, sticky="ew")
            self._btns_filtro[chave_f] = btn_f

        # ── Treeview oculta mantida para compatibilidade 100% ───────
        frame_tv_hidden = tk.Frame(frame)
        colunas = ("ID", "Nome", "Saldo Devedor", "Dia Acerto", "Ranking", "Perfil de Tempo")
        self.tabela_clientes = ttk.Treeview(
            frame_tv_hidden, columns=colunas, show="headings", height=1,
        )
        self.tabela_clientes.bind("<<TreeviewSelect>>", self._ao_selecionar_cliente)

        # ── Lista visual de Cards Finos de Clientes ─────────────────
        self.frame_cards_clientes = ctk.CTkScrollableFrame(
            frame,
            fg_color=_BG_CARD_SUB,
            corner_radius=10,
            border_width=1,
            border_color=_BORDER,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self.frame_cards_clientes.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.frame_cards_clientes.grid_columnconfigure(0, weight=1)

        # ── Cadastro Rápido de Novo Cliente (Modernizado) ───────────
        frame_novo = ctk.CTkFrame(
            frame, fg_color=_BG_CARD_SUB, corner_radius=10,
            border_width=1, border_color=_BORDER,
        )
        frame_novo.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            frame_novo,
            text="➕  Novo Cliente no Fiado",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_FG_LABEL,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        # Linha 0: Nome + Tel
        frame_l0 = ctk.CTkFrame(frame_novo, fg_color="transparent")
        frame_l0.pack(fill="x", padx=10, pady=(0, 6))
        frame_l0.grid_columnconfigure(0, weight=3)
        frame_l0.grid_columnconfigure(1, weight=2)

        self.entry_novo_nome = ctk.CTkEntry(
            frame_l0, height=32, placeholder_text="Nome do cliente...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=8,
        )
        self.entry_novo_nome.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.entry_novo_tel = ctk.CTkEntry(
            frame_l0, height=32, placeholder_text="WhatsApp (xx) 9xxxx-xxxx",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=8,
        )
        self.entry_novo_tel.grid(row=0, column=1, sticky="ew")

        # Linha 1: Limite + Dia + Botão
        frame_l1 = ctk.CTkFrame(frame_novo, fg_color="transparent")
        frame_l1.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            frame_l1, text="Limite R$:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=_FG_MUTED,
        ).pack(side="left", padx=(0, 4))

        self.entry_novo_limite = ctk.CTkEntry(
            frame_l1, height=32, width=76,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=8, justify="center",
        )
        self.entry_novo_limite.insert(0, "500")
        self.entry_novo_limite.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            frame_l1, text="Dia Venc.:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=_FG_MUTED,
        ).pack(side="left", padx=(0, 4))

        self.entry_novo_dia = ctk.CTkEntry(
            frame_l1, height=32, width=48,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=8, justify="center",
        )
        self.entry_novo_dia.insert(0, "5")
        self.entry_novo_dia.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            frame_l1, text="➕ Cadastrar",
            command=self._cadastrar_cliente,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=_BTN_ADD, hover_color=_ACCENT_GOLD,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=32, width=105,
        ).pack(side="right")

        self.entry_novo_nome.bind("<Return>", lambda e: self._cadastrar_cliente())

    # ════════════════════════════════════════════════════════════════════
    # COLUNA CENTRAL — FICHA DO CLIENTE + PAGAMENTO + EXTRATO EM CARDS
    # ════════════════════════════════════════════════════════════════════

    def _construir_coluna_direita(self, parent):
        self.frame_direito = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=14,
            border_width=1, border_color=_BORDER,
        )
        self.frame_direito.grid(row=0, column=1, sticky="nsew", padx=6)
        self.frame_direito.grid_columnconfigure(0, weight=1)
        self.frame_direito.grid_rowconfigure(3, weight=1)

        # ── 0. Card Cabeçalho do Cliente Selecionado ────────────────
        frame_ch = ctk.CTkFrame(
            self.frame_direito,
            fg_color=_BG_CARD_SUB,
            corner_radius=12,
            border_width=1,
            border_color=_BORDER,
        )
        frame_ch.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        frame_ch.grid_columnconfigure(0, weight=1)

        # Barra superior do cabeçalho: Nome à esquerda + Botões [💬] [✏️] [🗑️] à direita
        topo_ch = ctk.CTkFrame(frame_ch, fg_color="transparent")
        topo_ch.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        topo_ch.grid_columnconfigure(0, weight=1)

        self.lbl_cliente_nome = ctk.CTkLabel(
            topo_ch, text="← Selecione um cliente na lista",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=_FG_MUTED,
            anchor="w",
        )
        self.lbl_cliente_nome.grid(row=0, column=0, sticky="w")

        self.frame_acoes_cliente = ctk.CTkFrame(topo_ch, fg_color="transparent")
        self.frame_acoes_cliente.grid(row=0, column=1, sticky="e")

        self.btn_whatsapp_cliente = ctk.CTkButton(
            self.frame_acoes_cliente,
            text="💬 WhatsApp",
            command=self._cobrar_whatsapp_ativo,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=("#dcfce7", "#143325"),
            hover_color=_ACCENT_GREEN,
            text_color=("#15803d", "#4ade80"),
            border_width=1,
            border_color=("#86efac", "#1e4d38"),
            corner_radius=8,
            height=30,
            width=105,
        )
        self.btn_whatsapp_cliente.pack(side="left", padx=(0, 5))

        self.btn_editar_cliente = ctk.CTkButton(
            self.frame_acoes_cliente,
            text="✏️ Editar",
            command=self._abrir_modal_editar_cliente,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=_BG_CARD,
            hover_color=_ACCENT_BLUE,
            text_color=_FG_PRIMARY,
            border_width=1,
            border_color=_BORDER,
            corner_radius=8,
            height=30,
            width=82,
        )
        self.btn_editar_cliente.pack(side="left", padx=(0, 5))

        self.btn_excluir_cliente = ctk.CTkButton(
            self.frame_acoes_cliente,
            text="🗑️",
            command=self._excluir_cliente_ativo,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            fg_color=("#FEE2E2", "#2d161d"),
            hover_color=_ACCENT_RED,
            text_color=_KPI_RED_FG,
            border_width=1,
            border_color=("#FCA5A5", "#5c1d24"),
            corner_radius=8,
            height=30,
            width=36,
        )
        self.btn_excluir_cliente.pack(side="left")

        # Oculta botões até um cliente ser selecionado
        self.frame_acoes_cliente.grid_remove()

        # Saldo em destaque + Resumo de Limite/Vencimento
        self.lbl_cliente_saldo = ctk.CTkLabel(
            frame_ch, text="",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=_FG_MUTED,
            anchor="w",
        )
        self.lbl_cliente_saldo.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 2))

        self.lbl_cliente_limite = ctk.CTkLabel(
            frame_ch, text="Clique em qualquer cliente à esquerda para ver o extrato e registrar pagamentos.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=_FG_MUTED,
            anchor="w",
        )
        self.lbl_cliente_limite.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))

        # ── 1. Painel de Pagamento Rápido (oculto inicialmente) ─────
        self.frame_pagamento = ctk.CTkFrame(
            self.frame_direito,
            fg_color=("#F0FDF4", "#0f291e"),
            corner_radius=12,
            border_width=1,
            border_color=("#86efac", "#1e4d38"),
        )
        self.frame_pagamento.grid_columnconfigure(0, weight=1)

        # Linha 1 do pagamento: Valor + Atalhos [Quitar Total] [50%] + Meio (PIX/Dinheiro/Cartão)
        row_pgt1 = ctk.CTkFrame(self.frame_pagamento, fg_color="transparent")
        row_pgt1.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            row_pgt1, text="💵 Receber (R$):",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#14532D", "#4ade80"),
        ).pack(side="left", padx=(0, 6))

        self.entry_pagamento = ctk.CTkEntry(
            row_pgt1, width=105, height=34,
            placeholder_text="0,00",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=_BG_CARD_SUB,
            border_color=("#86efac", "#22c55e"),
            text_color=_FG_PRIMARY,
            corner_radius=8,
            justify="center",
        )
        self.entry_pagamento.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            row_pgt1, text="Quitar Total",
            width=86, height=30, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=_BG_CARD, hover_color=_ACCENT_BLUE,
            text_color=_FG_PRIMARY, border_width=1, border_color=_BORDER,
            command=lambda: self._preencher_valor_rapido(1.0),
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            row_pgt1, text="50%",
            width=48, height=30, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=_BG_CARD, hover_color=_ACCENT_BLUE,
            text_color=_FG_PRIMARY, border_width=1, border_color=_BORDER,
            command=lambda: self._preencher_valor_rapido(0.5),
        ).pack(side="left", padx=(0, 8))

        # Seletor rápido de Meio de Pagamento
        self.seg_meio_pgto = ctk.CTkSegmentedButton(
            row_pgt1,
            values=["PIX", "Dinheiro", "Cartão"],
            variable=self._meio_pgto_fiado,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=_BG_CARD_SUB,
            selected_color=_ACCENT_BLUE,
            selected_hover_color=_ACCENT_BLUE,
            unselected_color=_BG_CARD,
            unselected_hover_color=_BG_HOVER,
            height=30,
        )
        self.seg_meio_pgto.pack(side="right")

        # Linha 2 do pagamento: Observação + Botão Confirmar
        row_pgt2 = ctk.CTkFrame(self.frame_pagamento, fg_color="transparent")
        row_pgt2.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        row_pgt2.grid_columnconfigure(0, weight=1)

        self.entry_obs_pgt = ctk.CTkEntry(
            row_pgt2,
            height=34,
            placeholder_text="Observação opcional (ex: Pagou parte em mãos)...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=_BG_CARD_SUB,
            border_color=_BORDER,
            text_color=_FG_PRIMARY,
            corner_radius=8,
        )
        self.entry_obs_pgt.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row_pgt2, text="✔  Confirmar Recebimento",
            command=self._confirmar_pagamento,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=_BTN_REC, hover_color=("#155F3C", "#16a34a"),
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=34, width=185,
        ).grid(row=0, column=1, sticky="e")

        self.entry_pagamento.bind("<Return>", lambda e: self._confirmar_pagamento())
        self.entry_obs_pgt.bind("<Return>", lambda e: self._confirmar_pagamento())

        self._pagamento_visivel = False

        # ── 2. Cabeçalho do Extrato ─────────────────────────────────
        header_ext = ctk.CTkFrame(self.frame_direito, fg_color="transparent")
        header_ext.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 4))
        header_ext.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_ext, text="📜  Histórico e Extrato de Movimentações",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_contagem_extrato = ctk.CTkLabel(
            header_ext, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=_FG_MUTED, anchor="e",
        )
        self.lbl_contagem_extrato.grid(row=0, column=1, sticky="e")

        # Treeview oculta mantida por compatibilidade
        frame_ext_hidden = tk.Frame(self.frame_direito)
        colunas_ext = ("Data", "Tipo", "Valor", "Vencimento", "Observacao")
        self.tabela_extrato = ttk.Treeview(
            frame_ext_hidden, columns=colunas_ext, show="headings", height=1,
        )

        # ── 3. Timeline de Extrato em Cards (Slate Dark) ────────────
        self.frame_cards_extrato = ctk.CTkScrollableFrame(
            self.frame_direito,
            fg_color=_BG_CARD_SUB,
            corner_radius=10,
            border_width=1,
            border_color=_BORDER,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self.frame_cards_extrato.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.frame_cards_extrato.grid_columnconfigure(0, weight=1)

        self._renderizar_estado_vazio_extrato()

    # ════════════════════════════════════════════════════════════════════
    # COLUNA DIREITA (3) — COBRANÇAS PRIORITÁRIAS (CARDS SLATE DARK)
    # ════════════════════════════════════════════════════════════════════

    def _construir_coluna_alertas(self, parent):
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=14,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        topo_alerta = ctk.CTkFrame(frame, fg_color="transparent")
        topo_alerta.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
        topo_alerta.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            topo_alerta, text="🔔  Cobranças Prioritárias",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_badge_alertas = ctk.CTkLabel(
            topo_alerta, text="0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_KPI_RED_FG,
        )
        self.lbl_badge_alertas.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            frame,
            text="Clientes com parcelas vencidas ou agendadas para hoje",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=_FG_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))

        # Treeview oculta mantida por compatibilidade
        frame_tv_hidden = tk.Frame(frame)
        colunas = ("Nome", "Saldo Devedor", "Telefone")
        self.tree_alertas_dia = ttk.Treeview(
            frame_tv_hidden, columns=colunas, show="headings", height=1,
        )

        # Lista de Cards de Cobrança Prioritária
        self.frame_cards_alertas = ctk.CTkScrollableFrame(
            frame,
            fg_color=_BG_CARD_SUB,
            corner_radius=10,
            border_width=1,
            border_color=_BORDER,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self.frame_cards_alertas.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.frame_cards_alertas.grid_columnconfigure(0, weight=1)

    # ════════════════════════════════════════════════════════════════════
    # LÓGICA DE FILTROS E CARDS FINOS DE CLIENTES
    # ════════════════════════════════════════════════════════════════════

    def _set_filtro_status(self, chave: str):
        self._filtro_status = chave
        for k, btn in self._btns_filtro.items():
            ativo = (k == chave)
            btn.configure(
                fg_color=_ACCENT_BLUE if ativo else _BG_CARD_SUB,
                text_color=("#FFFFFF", "#FFFFFF") if ativo else _FG_MUTED,
            )
        self._recarregar_clientes(self.entry_busca.get().strip())

    def _on_busca_keyrelease(self, event=None):
        if self._debounce_busca_id:
            self.after_cancel(self._debounce_busca_id)
        self._debounce_busca_id = self.after(250, lambda: self._recarregar_clientes(self.entry_busca.get().strip()))

    def _recarregar_clientes(self, termo: str = ""):
        for item in self.tabela_clientes.get_children():
            self.tabela_clientes.delete(item)

        if hasattr(self, "frame_cards_clientes"):
            for w in self.frame_cards_clientes.winfo_children():
                w.destroy()

        todos_clientes = fiado_ctrl.listar_clientes("")
        # Filtro por texto (nome ou telefone)
        if termo:
            t_low = termo.lower()
            todos_clientes = [
                c for c in todos_clientes
                if t_low in (c.get("nome", "") or "").lower()
                or t_low in (c.get("telefone", "") or "").lower()
            ]

        # Filtro por aba de status
        clientes = []
        for c in todos_clientes:
            saldo = float(c.get("saldo_devedor", 0.0) or 0.0)
            st_tempo = c.get("status_tempo", "") or ""
            atrasado = "Vencido" in st_tempo
            if self._filtro_status == "DEVENDO" and saldo <= 0:
                continue
            if self._filtro_status == "ATRASADOS" and not (saldo > 0 and atrasado):
                continue
            if self._filtro_status == "EM_DIA" and saldo > 0:
                continue
            clientes.append(c)

        if hasattr(self, "lbl_contador_lista"):
            self.lbl_contador_lista.configure(text=f"{len(clientes)} cliente(s)")

        if not clientes and hasattr(self, "frame_cards_clientes"):
            ctk.CTkLabel(
                self.frame_cards_clientes,
                text="Nenhum cliente encontrado neste filtro.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=_FG_MUTED,
            ).grid(row=0, column=0, padx=20, pady=35)
            return

        for idx, c in enumerate(clientes):
            saldo  = float(c.get("saldo_devedor", 0.0) or 0.0)
            limite = float(c.get("limite_credito", 0.0) or 0.0)
            disp   = max(0.0, limite - saldo)
            st_tempo = c.get("status_tempo", "") or ""
            atrasado = (saldo > 0 and "Vencido" in st_tempo)

            tag = "devedor" if saldo > 0 else "zerado"
            self.tabela_clientes.insert(
                "", tk.END,
                values=(
                    c["id"], c["nome"], f"R$ {saldo:.2f}",
                    c["proximo_vencimento"], c["ranking"], st_tempo,
                ),
                tags=(tag,),
            )

            if hasattr(self, "frame_cards_clientes"):
                ativo = (self._cliente_ativo_id == c["id"])
                if ativo:
                    cor_borda = _ACCENT_BLUE
                elif atrasado:
                    cor_borda = ("#dc2626", "#991b1b")
                elif saldo > 0:
                    cor_borda = ("#fca5a5", "#4c1d24")
                else:
                    cor_borda = _BORDER

                # ── CARD FINO E COMPACTO ──────────────────────────────
                card = ctk.CTkFrame(
                    self.frame_cards_clientes,
                    fg_color=("#EFF6FF", "#172554") if ativo else _BG_CARD,
                    corner_radius=10,
                    border_width=2 if ativo else 1,
                    border_color=cor_borda,
                    cursor="hand2",
                )
                card.grid(row=idx, column=0, sticky="ew", padx=3, pady=3)
                card.grid_columnconfigure(1, weight=1)

                # Faixa lateral fina (4px)
                cor_faixa = _ACCENT_RED if saldo > 0 else _ACCENT_GREEN
                faixa = ctk.CTkFrame(card, width=4, fg_color=cor_faixa, corner_radius=2)
                faixa.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(4, 6), pady=5)

                # Linha 0: Nome + Telefone/Vencimento + Ranking na direita
                linha0 = ctk.CTkFrame(card, fg_color="transparent")
                linha0.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(5, 1))
                linha0.grid_columnconfigure(0, weight=1)

                bloco_nome = ctk.CTkFrame(linha0, fg_color="transparent")
                bloco_nome.grid(row=0, column=0, sticky="w")

                ctk.CTkLabel(
                    bloco_nome,
                    text=c["nome"],
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color=_FG_PRIMARY,
                ).pack(side="left")

                tel_curto = c.get("telefone") or ""
                venc_curto = c.get("proximo_vencimento", "Nenhum")
                info_meio = []
                if tel_curto and tel_curto != "Sem Telefone":
                    info_meio.append(f"📞 {tel_curto}")
                if saldo > 0 and venc_curto and venc_curto != "Nenhum":
                    info_meio.append(f"Venc: {venc_curto}")
                if info_meio:
                    ctk.CTkLabel(
                        bloco_nome,
                        text="  ·  " + " · ".join(info_meio),
                        font=ctk.CTkFont(family="Segoe UI", size=11),
                        text_color=("#dc2626", "#f87171") if atrasado else _FG_MUTED,
                    ).pack(side="left")

                ctk.CTkLabel(
                    linha0,
                    text=c.get("ranking", ""),
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    text_color=_ACCENT_GOLD,
                ).grid(row=0, column=1, sticky="e")

                # Linha 1: Saldo Devedor + Limite Disponível + Botão compacto [💵 Receber]
                linha1 = ctk.CTkFrame(card, fg_color="transparent")
                linha1.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 3))
                linha1.grid_columnconfigure(0, weight=1)

                if saldo > 0:
                    txt_saldo = f"Deve: R$ {saldo:.2f}" + ("  ⚠️" if atrasado else "")
                    cor_saldo = _ACCENT_RED
                else:
                    txt_saldo = "Em dia (R$ 0,00)"
                    cor_saldo = _ACCENT_GREEN

                ctk.CTkLabel(
                    linha1,
                    text=txt_saldo,
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    text_color=cor_saldo,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                ctk.CTkLabel(
                    linha1,
                    text=f"Disp: R$ {disp:.0f}/{limite:.0f}",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=_FG_MUTED,
                ).grid(row=0, column=1, sticky="e", padx=(0, 6 if saldo > 0 else 0))

                if saldo > 0:
                    btn_rec = ctk.CTkButton(
                        linha1,
                        text="💵 Receber",
                        width=78,
                        height=22,
                        corner_radius=6,
                        fg_color=_BTN_REC,
                        hover_color=("#155F3C", "#16a34a"),
                        text_color=("#FFFFFF", "#FFFFFF"),
                        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                        command=lambda cli=c: self._selecionar_cliente_card(cli, focar_pagamento=True),
                    )
                    btn_rec.grid(row=0, column=2, sticky="e")

                # Linha 2: Barra de Progresso ultrafina (4px)
                frac = min(1.0, max(0.0, saldo / limite)) if limite > 0 else (1.0 if saldo > 0 else 0.0)
                if frac >= 0.9:
                    cor_bar = _ACCENT_RED
                elif frac >= 0.7:
                    cor_bar = _ACCENT_GOLD
                else:
                    cor_bar = _ACCENT_BLUE

                pb = ctk.CTkProgressBar(
                    card,
                    height=4,
                    corner_radius=999,
                    fg_color=_BG_CARD_SUB,
                    progress_color=cor_bar,
                )
                pb.set(frac)
                pb.grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(0, 5))

                def _bind_card_click(w, cli_data=c):
                    if isinstance(w, ctk.CTkButton):
                        return
                    w.bind("<Button-1>", lambda e, cd=cli_data: self._selecionar_cliente_card(cd, focar_pagamento=False))
                    for ch in w.winfo_children():
                        _bind_card_click(ch, cli_data)

                _bind_card_click(card, c)

    # ════════════════════════════════════════════════════════════════════
    # SELEÇÃO DE CLIENTE, EXTRATO EM CARDS E AÇÕES (WHATSAPP / EDITAR)
    # ════════════════════════════════════════════════════════════════════

    def _selecionar_cliente_card(self, dados_cli: dict, focar_pagamento: bool = False):
        """Seleciona um cliente clicando no Card e carrega seu extrato em Cards."""
        self._cliente_ativo_id   = dados_cli["id"]
        self._cliente_ativo_nome = str(dados_cli["nome"])

        dados_frescos = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id) or dados_cli
        self._cliente_ativo_dict = dados_frescos

        saldo  = float(dados_frescos.get("saldo_devedor", 0.0) or 0.0)
        limite = float(dados_frescos.get("limite_credito", 0.0) or 0.0)
        disp   = max(0.0, limite - saldo)
        tel    = dados_frescos.get("telefone") or "Sem telefone"
        venc   = dados_frescos.get("proximo_vencimento", "—")
        rank   = dados_frescos.get("ranking", "N/A")
        st_tmp = dados_frescos.get("status_tempo", "")

        self.lbl_cliente_nome.configure(text=self._cliente_ativo_nome, text_color=_FG_PRIMARY)
        if saldo > 0:
            self.lbl_cliente_saldo.configure(
                text=f"⚠️  Saldo Devedor: R$ {saldo:.2f}   ({st_tmp})",
                text_color=_KPI_RED_FG,
            )
        else:
            self.lbl_cliente_saldo.configure(
                text="✅  Sem dívida (R$ 0,00)",
                text_color=_ACCENT_GREEN,
            )

        self.lbl_cliente_limite.configure(
            text=f"📞 {tel}   •   Limite: R$ {limite:.2f} (Disp: R$ {disp:.2f})   •   Próx. Venc.: {venc}   •   {rank}",
            text_color=_FG_MUTED,
        )

        # Mostra botões de ação do cliente e painel de pagamento
        self.frame_acoes_cliente.grid()
        if not self._pagamento_visivel:
            self.frame_pagamento.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
            self._pagamento_visivel = True

        self.entry_pagamento.delete(0, tk.END)
        self.entry_obs_pgt.delete(0, tk.END)
        if focar_pagamento and saldo > 0:
            self.entry_pagamento.insert(0, f"{saldo:.2f}")
            self.after(50, lambda: self.entry_pagamento.focus_set())

        self._recarregar_extrato()
        self._recarregar_clientes(self.entry_busca.get().strip())

    def _preencher_valor_rapido(self, fracao: float):
        """Preenche o input de pagamento com 100% ou 50% do saldo devedor atual."""
        if not self._cliente_ativo_id:
            return
        dados = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
        if not dados:
            return
        saldo = float(dados.get("saldo_devedor", 0.0) or 0.0)
        if saldo <= 0:
            messagebox.showinfo("Conta em Dia", f"{dados['nome']} não possui saldo devedor em aberto.")
            return
        valor_calc = round(saldo * fracao, 2)
        self.entry_pagamento.delete(0, tk.END)
        self.entry_pagamento.insert(0, f"{valor_calc:.2f}")
        self.entry_pagamento.focus_set()

    def _cobrar_whatsapp_ativo(self):
        if not self._cliente_ativo_id:
            return
        dados = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
        if dados:
            self._abrir_whatsapp_cliente(dados)

    def _abrir_whatsapp_cliente(self, dados_cli: dict):
        nome  = dados_cli.get("nome", "Cliente")
        tel   = "".join(ch for ch in (dados_cli.get("telefone") or "") if ch.isdigit())
        saldo = float(dados_cli.get("saldo_devedor", 0.0) or 0.0)
        venc  = dados_cli.get("proximo_vencimento", "—")

        if saldo > 0:
            msg = (
                f"Olá {nome}, tudo bem? Passando da loja *Kanemberg* para lembrar do seu "
                f"saldo em aberto de *R$ {saldo:.2f}* (vencimento: {venc}). "
                f"Qualquer dúvida estamos à disposição!"
            )
        else:
            msg = f"Olá {nome}, tudo bem? Aqui é da loja *Kanemberg*! Sua conta está 100% em dia. Obrigado pela preferência!"

        texto_url = urllib.parse.quote(msg)
        if tel:
            if len(tel) in (10, 11) and not tel.startswith("55"):
                tel = "55" + tel
            url = f"https://wa.me/{tel}?text={texto_url}"
        else:
            url = f"https://api.whatsapp.com/send?text={texto_url}"
        webbrowser.open(url)

    def _abrir_modal_editar_cliente(self):
        """Abre modal Slate Dark para editar Nome, Telefone, Limite e Dia Preferencial do cliente."""
        if not self._cliente_ativo_id:
            return
        dados = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
        if not dados:
            return

        if self._modal_editar and self._modal_editar.winfo_exists():
            self._modal_editar.destroy()

        win = ctk.CTkToplevel(self)
        win.title(f"Editar Cliente — {dados['nome']}")
        win.geometry("400x360")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(fg_color="#0f172a")
        self._modal_editar = win

        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 400) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 360) // 2
        win.geometry(f"+{max(20, x)}+{max(20, y)}")

        card = ctk.CTkFrame(win, fg_color="#1e293b", corner_radius=14, border_width=1, border_color="#334155")
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            card, text="✏️  Editar Dados do Cliente",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#f8fafc",
        ).pack(anchor="w", padx=16, pady=(14, 10))

        def _campo(rotulo, valor_ini):
            ctk.CTkLabel(
                card, text=rotulo,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#cbd5e1",
            ).pack(anchor="w", padx=16, pady=(4, 2))
            ent = ctk.CTkEntry(
                card, height=34,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#0f172a", border_color="#334155", text_color="#f8fafc",
                corner_radius=8,
            )
            ent.pack(fill="x", padx=16, pady=(0, 4))
            ent.insert(0, str(valor_ini))
            return ent

        ent_nome = _campo("Nome Completo:", dados.get("nome", ""))
        ent_tel  = _campo("Telefone / WhatsApp:", dados.get("telefone", "") or "")

        row_lim = ctk.CTkFrame(card, fg_color="transparent")
        row_lim.pack(fill="x", padx=16, pady=(6, 12))
        row_lim.grid_columnconfigure(0, weight=1)
        row_lim.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row_lim, text="Limite de Crédito (R$):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#cbd5e1").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ctk.CTkLabel(row_lim, text="Dia Pref. Vencimento:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#cbd5e1").grid(row=0, column=1, sticky="w", padx=(6, 0))

        ent_lim = ctk.CTkEntry(row_lim, height=34, font=ctk.CTkFont(size=13), fg_color="#0f172a", border_color="#334155", text_color="#f8fafc", corner_radius=8)
        ent_lim.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))
        ent_lim.insert(0, f"{float(dados.get('limite_credito', 500.0)):.2f}")

        ent_dia = ctk.CTkEntry(row_lim, height=34, font=ctk.CTkFont(size=13), fg_color="#0f172a", border_color="#334155", text_color="#f8fafc", corner_radius=8)
        ent_dia.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(2, 0))
        ent_dia.insert(0, str(dados.get("dia_preferencial_pagamento", 5) or 5))

        def _salvar_edicao():
            novo_nome = ent_nome.get().strip()
            novo_tel  = ent_tel.get().strip()
            if not novo_nome:
                messagebox.showerror("Erro", "O nome não pode ficar vazio.", parent=win)
                return
            try:
                novo_lim = float(ent_lim.get().replace(",", ".").strip() or "500")
            except ValueError:
                messagebox.showerror("Erro", "Limite de crédito inválido.", parent=win)
                return
            try:
                novo_dia = max(1, min(31, int(ent_dia.get().strip() or "5")))
            except ValueError:
                novo_dia = 5

            ok, msg = fiado_ctrl.atualizar_cliente(
                self._cliente_ativo_id, novo_nome, novo_tel, novo_lim, novo_dia
            )
            if ok:
                win.destroy()
                atualizado = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
                if atualizado:
                    self._selecionar_cliente_card(atualizado, focar_pagamento=False)
                self._atualizar_kpis()
                self.atualizar_tabela_alertas_do_dia()
            else:
                messagebox.showerror("Erro", msg, parent=win)

        ctk.CTkButton(
            card, text="💾  Salvar Alterações",
            command=_salvar_edicao,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#3b82f6", hover_color="#2563eb",
            text_color="#FFFFFF", corner_radius=8, height=38,
        ).pack(fill="x", padx=16, pady=(6, 12))

    # ════════════════════════════════════════════════════════════════════
    # CADASTRO, EXCLUSÃO E PAGAMENTO
    # ════════════════════════════════════════════════════════════════════

    def _cadastrar_cliente(self):
        nome = self.entry_novo_nome.get().strip()
        tel  = self.entry_novo_tel.get().strip()
        try:
            limite = float(self.entry_novo_limite.get().replace(",", ".") or "500")
        except ValueError:
            limite = 500.0
        try:
            dia = int(self.entry_novo_dia.get() or "5")
            if not (1 <= dia <= 31):
                raise ValueError
        except ValueError:
            dia = 5

        sucesso, msg = fiado_ctrl.adicionar_cliente(nome, tel, limite, dia)
        if sucesso:
            self.entry_novo_nome.delete(0, tk.END)
            self.entry_novo_tel.delete(0, tk.END)
            self.entry_novo_limite.delete(0, tk.END)
            self.entry_novo_limite.insert(0, "500")
            self.entry_novo_dia.delete(0, tk.END)
            self.entry_novo_dia.insert(0, "5")
            self._recarregar_clientes(self.entry_busca.get().strip())
            self._atualizar_kpis()
            self.atualizar_tabela_alertas_do_dia()
        else:
            messagebox.showerror("Erro", msg)

    def _ao_selecionar_cliente(self, event):
        selecao = self.tabela_clientes.selection()
        if not selecao:
            return
        valores = self.tabela_clientes.item(selecao[0])["values"]
        cid = valores[0]
        dados = fiado_ctrl.buscar_cliente_por_id(cid)
        if dados:
            self._selecionar_cliente_card(dados, focar_pagamento=False)

    def _excluir_cliente_ativo(self):
        if not self._cliente_ativo_id:
            return
        confirmar = messagebox.askyesno(
            "Remover Cliente",
            f"Deseja remover '{self._cliente_ativo_nome}' permanentemente?\n"
            "Isso apaga todo o histórico de fiado (permitido apenas com saldo R$ 0,00).",
        )
        if not confirmar:
            return
        sucesso, msg = fiado_ctrl.excluir_cliente(self._cliente_ativo_id)
        if sucesso:
            self._cliente_ativo_id   = None
            self._cliente_ativo_nome = None
            self._cliente_ativo_dict = None
            self.lbl_cliente_nome.configure(text="← Selecione um cliente na lista", text_color=_FG_MUTED)
            self.lbl_cliente_saldo.configure(text="", text_color=_FG_MUTED)
            self.lbl_cliente_limite.configure(
                text="Clique em qualquer cliente à esquerda para ver o extrato e registrar pagamentos.",
            )
            self.frame_pagamento.grid_remove()
            self._pagamento_visivel = False
            self.frame_acoes_cliente.grid_remove()
            self._renderizar_estado_vazio_extrato()
            self._recarregar_clientes(self.entry_busca.get().strip())
            self._atualizar_kpis()
            self.atualizar_tabela_alertas_do_dia()
        else:
            messagebox.showerror("Não Permitido", msg)

    def _confirmar_pagamento(self):
        if not self._cliente_ativo_id:
            return
        try:
            valor = float(self.entry_pagamento.get().replace(",", ".").strip())
        except ValueError:
            messagebox.showerror("Erro", "Digite um valor numérico válido para o recebimento.")
            return

        meio = self._meio_pgto_fiado.get() or "PIX"
        obs_digitada = self.entry_obs_pgt.get().strip()
        if obs_digitada:
            obs = f"Pagamento ({meio}) — {obs_digitada}"
        else:
            obs = f"Pagamento recebido via {meio}"

        sucesso, msg = fiado_ctrl.registrar_pagamento(self._cliente_ativo_id, valor, obs)
        if sucesso:
            self.entry_pagamento.delete(0, tk.END)
            self.entry_obs_pgt.delete(0, tk.END)
            dados = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
            if dados:
                self._selecionar_cliente_card(dados, focar_pagamento=False)
            self._atualizar_kpis()
            self.atualizar_tabela_alertas_do_dia()
        else:
            messagebox.showerror("Erro", msg)

    # ════════════════════════════════════════════════════════════════════
    # RENDERIZAÇÃO DO EXTRATO EM CARDS (TIMELINE SLATE DARK)
    # ════════════════════════════════════════════════════════════════════

    def _renderizar_estado_vazio_extrato(self, texto: str = "Selecione um cliente à esquerda para visualizar o extrato detalhado."):
        for item in self.tabela_extrato.get_children():
            self.tabela_extrato.delete(item)
        if hasattr(self, "frame_cards_extrato"):
            for w in self.frame_cards_extrato.winfo_children():
                w.destroy()
            ctk.CTkLabel(
                self.frame_cards_extrato,
                text=f"📄\n{texto}",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=_FG_MUTED,
                justify="center",
            ).grid(row=0, column=0, padx=20, pady=50)
        if hasattr(self, "lbl_contagem_extrato"):
            self.lbl_contagem_extrato.configure(text="")

    def _recarregar_extrato(self):
        for item in self.tabela_extrato.get_children():
            self.tabela_extrato.delete(item)
        if hasattr(self, "frame_cards_extrato"):
            for w in self.frame_cards_extrato.winfo_children():
                w.destroy()

        if not self._cliente_ativo_id:
            self._renderizar_estado_vazio_extrato()
            return

        movs = fiado_ctrl.buscar_extrato(self._cliente_ativo_id)
        if hasattr(self, "lbl_contagem_extrato"):
            self.lbl_contagem_extrato.configure(text=f"{len(movs)} lançamento(s)")

        if not movs:
            self._renderizar_estado_vazio_extrato("Nenhuma compra ou pagamento registrado para este cliente.")
            return

        for idx, m in enumerate(movs):
            eh_debito = (m["tipo"] == "DEBITO")
            icone = "🔴 COMPRA" if eh_debito else "🟢 PAGTO"
            self.tabela_extrato.insert(
                "", tk.END,
                values=(m["data"], icone, f"R$ {m['valor']:.2f}", m["vencimento_lote"], m["obs"]),
                tags=(m["tipo"],),
            )

            # ── Card de Lançamento na Timeline ────────────────────────
            card_m = ctk.CTkFrame(
                self.frame_cards_extrato,
                fg_color=_BG_CARD,
                corner_radius=10,
                border_width=1,
                border_color=_BORDER,
            )
            card_m.grid(row=idx, column=0, sticky="ew", padx=4, pady=3)
            card_m.grid_columnconfigure(1, weight=1)

            cor_faixa = _ACCENT_RED if eh_debito else _ACCENT_GREEN
            faixa_m = ctk.CTkFrame(card_m, width=4, fg_color=cor_faixa, corner_radius=2)
            faixa_m.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(4, 8), pady=5)

            # Linha 0: Badge Tipo + Data/Hora + Valor à direita
            topo_m = ctk.CTkFrame(card_m, fg_color="transparent")
            topo_m.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(6, 2))
            topo_m.grid_columnconfigure(1, weight=1)

            rotulo_tipo = "🔴 COMPRA NO FIADO" if eh_debito else "🟢 PAGAMENTO RECEBIDO"
            cor_tipo    = ("#dc2626", "#f87171") if eh_debito else ("#16a34a", "#4ade80")

            ctk.CTkLabel(
                topo_m,
                text=rotulo_tipo,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=cor_tipo,
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                topo_m,
                text=f"  •  {m['data']}",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=_FG_MUTED,
            ).grid(row=0, column=1, sticky="w")

            sinal = "+" if eh_debito else "−"
            ctk.CTkLabel(
                topo_m,
                text=f"{sinal} R$ {m['valor']:.2f}",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=cor_tipo,
            ).grid(row=0, column=2, sticky="e")

            # Linha 1: Descrição / Peças + Badge de Vencimento / Status FIFO
            base_m = ctk.CTkFrame(card_m, fg_color="transparent")
            base_m.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))
            base_m.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                base_m,
                text=m.get("obs") or "—",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=_FG_LABEL,
                anchor="w",
                justify="left",
                wraplength=310,
            ).grid(row=0, column=0, sticky="w")

            if eh_debito:
                st_lote = m.get("status_lote", "ABERTO")
                venc_lote = m.get("vencimento_lote", "—")
                if st_lote == "PAGO":
                    txt_b = f"✅ Quitado (Venc: {venc_lote})"
                    bg_b  = ("#dcfce7", "#143325")
                    fg_b  = ("#15803d", "#4ade80")
                elif st_lote == "ATRASADO":
                    txt_b = f"⚠️ Vencido em {venc_lote}"
                    bg_b  = ("#fee2e2", "#3b1824")
                    fg_b  = ("#dc2626", "#f87171")
                elif st_lote == "HOJE":
                    txt_b = f"📅 Vence Hoje ({venc_lote})"
                    bg_b  = ("#fef3c7", "#382814")
                    fg_b  = ("#d97706", "#fbbf24")
                else:
                    txt_b = f"⏳ Venc: {venc_lote}"
                    bg_b  = ("#dbeafe", "#1e3a5f")
                    fg_b  = ("#2563eb", "#60a5fa")

                pill_v = ctk.CTkFrame(base_m, fg_color=bg_b, corner_radius=6)
                pill_v.grid(row=0, column=1, sticky="e", padx=(6, 0))
                ctk.CTkLabel(
                    pill_v, text=txt_b,
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    text_color=fg_b,
                ).pack(padx=7, pady=2)

    # ════════════════════════════════════════════════════════════════════
    # KPIS E COBRANÇAS PRIORITÁRIAS EM CARDS (COLUNA 3)
    # ════════════════════════════════════════════════════════════════════

    def _atualizar_kpis(self):
        resumo = fiado_ctrl.resumo_fiado()
        self.kpi_total_aberto.configure(text=f"R$ {resumo['total_em_aberto']:.2f}")
        self.kpi_qtd_devedores.configure(text=str(resumo["clientes_devedores"]))
        self.kpi_total_clientes.configure(text=str(resumo["total_clientes"]))

    def atualizar_tabela_alertas_do_dia(self):
        for item in self.tree_alertas_dia.get_children():
            self.tree_alertas_dia.delete(item)
        if hasattr(self, "frame_cards_alertas"):
            for w in self.frame_cards_alertas.winfo_children():
                w.destroy()

        alertas = fiado_ctrl.listar_clientes_acerto_hoje()
        if hasattr(self, "lbl_badge_alertas"):
            self.lbl_badge_alertas.configure(text=f"{len(alertas)} pendente(s)")

        if not alertas:
            if hasattr(self, "frame_cards_alertas"):
                ctk.CTkLabel(
                    self.frame_cards_alertas,
                    text="🎉\nNenhum cliente vencido\nou agendado para hoje!",
                    font=ctk.CTkFont(family="Segoe UI", size=13),
                    text_color=_FG_MUTED,
                    justify="center",
                ).grid(row=0, column=0, padx=16, pady=45)
            return

        for idx, c in enumerate(alertas):
            self.tree_alertas_dia.insert(
                "", "end",
                values=(c["nome"], f"R$ {c['saldo_devedor']:.2f}", c["telefone"]),
            )

            if hasattr(self, "frame_cards_alertas"):
                eh_atrasado = (c.get("urgencia") == "ATRASADO")
                cor_faixa = _ACCENT_RED if eh_atrasado else _ACCENT_GOLD
                cor_borda = ("#fca5a5", "#7f1d1d") if eh_atrasado else ("#fde68a", "#78350f")

                card_a = ctk.CTkFrame(
                    self.frame_cards_alertas,
                    fg_color=_BG_CARD,
                    corner_radius=10,
                    border_width=1,
                    border_color=cor_borda,
                    cursor="hand2",
                )
                card_a.grid(row=idx, column=0, sticky="ew", padx=3, pady=3)
                card_a.grid_columnconfigure(1, weight=1)

                faixa_a = ctk.CTkFrame(card_a, width=4, fg_color=cor_faixa, corner_radius=2)
                faixa_a.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(4, 6), pady=5)

                # Linha 0: Nome + Valor
                topo_a = ctk.CTkFrame(card_a, fg_color="transparent")
                topo_a.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(6, 1))
                topo_a.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    topo_a,
                    text=c["nome"],
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color=_FG_PRIMARY,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                ctk.CTkLabel(
                    topo_a,
                    text=f"R$ {c['saldo_devedor']:.2f}",
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color=_ACCENT_RED,
                    anchor="e",
                ).grid(row=0, column=1, sticky="e")

                # Linha 1: Status de atraso / vencimento hoje
                if eh_atrasado:
                    dias = c.get("dias_atraso", 0)
                    txt_urg = f"⚠️ Vencido há {dias} dia(s) ({c.get('proximo_vencimento', '')})"
                    cor_urg = ("#dc2626", "#f87171")
                else:
                    txt_urg = "📅 Acerto combinado para HOJE"
                    cor_urg = ("#d97706", "#fbbf24")

                ctk.CTkLabel(
                    card_a,
                    text=txt_urg,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color=cor_urg,
                    anchor="w",
                ).grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 4))

                # Linha 2: Botões rápidos [💵 Receber] e [💬 WhatsApp]
                btns_a = ctk.CTkFrame(card_a, fg_color="transparent")
                btns_a.grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(0, 6))
                btns_a.grid_columnconfigure(0, weight=1)

                ctk.CTkButton(
                    btns_a,
                    text="💵 Receber Agora",
                    height=24,
                    corner_radius=6,
                    fg_color=_BTN_REC,
                    hover_color=("#155F3C", "#16a34a"),
                    text_color=("#FFFFFF", "#FFFFFF"),
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    command=lambda cli=c: self._selecionar_cliente_card(cli, focar_pagamento=True),
                ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

                ctk.CTkButton(
                    btns_a,
                    text="💬",
                    width=32,
                    height=24,
                    corner_radius=6,
                    fg_color=("#dcfce7", "#143325"),
                    hover_color=_ACCENT_GREEN,
                    text_color=("#15803d", "#4ade80"),
                    border_width=1,
                    border_color=("#86efac", "#1e4d38"),
                    font=ctk.CTkFont(size=12),
                    command=lambda cli=c: self._abrir_whatsapp_cliente(cli),
                ).grid(row=0, column=1, sticky="e")

    def atualizar_dados(self):
        """Recarrega clientes, KPIs, extrato ativo e alertas ao retornar para a aba de Fiado."""
        termo = self.entry_busca.get().strip() if hasattr(self, "entry_busca") else ""
        self._recarregar_clientes(termo)
        self._atualizar_kpis()
        self.atualizar_tabela_alertas_do_dia()
        if self._cliente_ativo_id:
            dados = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
            if dados:
                self._selecionar_cliente_card(dados, focar_pagamento=False)
