"""
tela_fiado.py — Controle de Fiado (Contas a Receber)
Refatorado para CustomTkinter 5.x:
  • CTkFrame com fg_color dinâmico — zero blocos brancos/cinzentos do SO
  • Três Treeviews (clientes, extrato, alertas) com ttk.Style casado ao tema
  • KPI cards em CTkFrame com cores dinâmicas
  • CTkEntry para busca e formulário de cadastro rápido
  • CTkButton com corner_radius=8 e hover_color nativo
  • Scrollbars estilizados com paleta escura via ttk.Style
  • Toda a lógica de negócio preservada sem alterações
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import fiado_ctrl

# ── Paletas dinâmicas (claro, escuro) ───────────────────────────────────────
_BG_WINDOW   = ("#F0F2F8", "#0F1117")
_BG_CARD     = ("#FFFFFF", "#16191F")
_BG_HOVER    = ("#E8ECF4", "#22273A")
_FG_PRIMARY  = ("#1A1D2E", "#F0F2F8")
_FG_MUTED    = ("#6B7280", "#8A8FA8")
_FG_LABEL    = ("#4B5563", "#A0A8C0")
_ACCENT_GOLD = ("#B8861F", "#E1B12C")
_ACCENT_BLUE = ("#1B4F8A", "#2D7DD2")
_BORDER      = ("#DDE3EE", "#22273A")

# KPI
_KPI_RED_BG  = ("#FEE2E2", "#3B0A0A");  _KPI_RED_FG  = ("#DC2626", "#F87171")
_KPI_YEL_BG  = ("#FEF3C7", "#3B2200");  _KPI_YEL_FG  = ("#D97706", "#FBBF24")
_KPI_BLU_BG  = ("#EFF6FF", "#0A1A3B");  _KPI_BLU_FG  = ("#2563EB", "#60A5FA")

# Botões de ação
_BTN_ADD    = ("#1B4F8A", "#7C83FD")
_BTN_REC    = ("#1B7A4C", "#059669")
_BTN_DEL    = ("#B91C1C", "#DC2626")


def _hex(color_tuple) -> str:
    """Retorna a cor hex correta para o modo atual do CTk."""
    mode = ctk.get_appearance_mode()
    return color_tuple[1] if mode != "Light" else color_tuple[0]


def _aplicar_estilo_treeview(nome: str, bg_hex: str, heading_fg: str):
    """
    Configura um estilo TTK nomeado para o Treeview, casando o fundo
    exatamente com a cor do tema CTk ativo — sem blocos brancos residuais.
    """
    s = ttk.Style()
    s.configure(
        f"{nome}.Treeview",
        rowheight=30,
        font=("Segoe UI", 9),
        background=bg_hex,
        fieldbackground=bg_hex,
        foreground=_hex(_FG_PRIMARY),
        borderwidth=0,
    )
    s.configure(
        f"{nome}.Treeview.Heading",
        font=("Segoe UI", 9, "bold"),
        background=_hex(_BG_HOVER),
        foreground=heading_fg,
        relief="flat",
    )
    s.map(
        f"{nome}.Treeview",
        background=[("selected", _hex(_ACCENT_BLUE))],
        foreground=[("selected", "#FFFFFF")],
    )
    # Scrollbar da paleta escura
    s.configure(
        "Dark.Vertical.TScrollbar",
        troughcolor=_hex(_BG_WINDOW),
        background=_hex(_ACCENT_BLUE),
        arrowcolor=_hex(_FG_PRIMARY),
        relief="flat",
        borderwidth=0,
    )


class TelaFiado(ctk.CTkFrame):
    """
    Tela de controle de fiado com gestão completa de clientes e extratos.
    Três colunas: clientes | extrato/pagamento | alertas do dia.
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
        self._debounce_busca_id  = None

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
        frame_corpo.grid_columnconfigure(0, weight=1)
        frame_corpo.grid_columnconfigure(1, weight=1)
        frame_corpo.grid_columnconfigure(2, weight=1)
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
        frame_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        frame_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame_header,
            text="💳  Controle de Fiado",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=_FG_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # KPI cards à direita
        frame_kpis = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_kpis.grid(row=0, column=1, sticky="e")

        self.kpi_total_aberto   = self._criar_kpi_card(frame_kpis, "Total em Aberto",   "R$ 0,00", _KPI_RED_BG, _KPI_RED_FG, 0)
        self.kpi_qtd_devedores  = self._criar_kpi_card(frame_kpis, "Clientes Devendo",  "0",       _KPI_YEL_BG, _KPI_YEL_FG, 1)
        self.kpi_total_clientes = self._criar_kpi_card(frame_kpis, "Total de Clientes", "0",       _KPI_BLU_BG, _KPI_BLU_FG, 2)

    def _criar_kpi_card(self, parent, titulo, valor, bg_tuple, fg_tuple, col) -> ctk.CTkLabel:
        """Cria um card de métrica CTk e retorna o CTkLabel do valor."""
        card = ctk.CTkFrame(
            parent,
            fg_color=bg_tuple,
            corner_radius=10,
            border_width=0,
        )
        card.grid(row=0, column=col, padx=6, sticky="ew")

        ctk.CTkLabel(
            card, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color=_FG_MUTED,
        ).pack(padx=16, pady=(8, 0))

        lbl = ctk.CTkLabel(
            card, text=valor,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=fg_tuple,
        )
        lbl.pack(padx=16, pady=(2, 8))
        return lbl

    # ════════════════════════════════════════════════════════════════════
    # COLUNA ESQUERDA — LISTA DE CLIENTES
    # ════════════════════════════════════════════════════════════════════

    def _construir_coluna_esquerda(self, parent):
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            frame, text="Clientes Cadastrados",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 4))

        # ── Busca ──────────────────────────────────────────────────
        frame_busca = ctk.CTkFrame(frame, fg_color="transparent")
        frame_busca.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        frame_busca.grid_columnconfigure(0, weight=1)

        self.entry_busca = ctk.CTkEntry(
            frame_busca,
            placeholder_text="🔍  Buscar cliente...",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=_BG_WINDOW,
            border_color=_BORDER,
            text_color=_FG_PRIMARY,
            placeholder_text_color=_FG_MUTED,
            corner_radius=8,
            height=34,
        )
        self.entry_busca.grid(row=0, column=0, sticky="ew")
        self.entry_busca.bind(
            "<KeyRelease>",
            self._on_busca_keyrelease
        )

        # ── Treeview de clientes ────────────────────────────────────
        bg_tv = _hex(_BG_CARD)
        _aplicar_estilo_treeview("Fiado", bg_tv, _hex(_ACCENT_GOLD))

        frame_tv = tk.Frame(frame, bg=bg_tv)
        frame_tv.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))

        colunas = ("ID", "Nome", "Saldo Devedor", "Dia Acerto", "Ranking", "Perfil de Tempo")
        self.tabela_clientes = ttk.Treeview(
            frame_tv, columns=colunas, show="headings",
            height=14, style="Fiado.Treeview",
        )
        self.tabela_clientes.tag_configure("devedor", foreground="#F87171", font=("Segoe UI", 9, "bold"))
        self.tabela_clientes.tag_configure("zerado",  foreground="#34D399")

        for col, w, anc, label in [
            ("ID",             40,  "center", "ID"),
            ("Nome",          150,  "w",      "Nome do Cliente"),
            ("Saldo Devedor", 100,  "center", "Saldo Devedor"),
            ("Dia Acerto",    110,  "center", "Próx. Vencimento"),
            ("Ranking",       110,  "center", "Fidelidade"),
            ("Perfil de Tempo", 140, "w",     "Status de Caixa"),
        ]:
            self.tabela_clientes.heading(col, text=label)
            self.tabela_clientes.column(col, width=w, anchor=anc)

        scroll_cli = ttk.Scrollbar(
            frame_tv, orient="vertical",
            command=self.tabela_clientes.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.tabela_clientes.configure(yscrollcommand=scroll_cli.set)
        self.tabela_clientes.pack(side="left", fill="both", expand=True)
        scroll_cli.pack(side="right", fill="y")

        self.tabela_clientes.bind("<<TreeviewSelect>>", self._ao_selecionar_cliente)

        # ── Cadastro Rápido ─────────────────────────────────────────
        frame_novo = ctk.CTkFrame(
            frame, fg_color=_BG_HOVER, corner_radius=8,
            border_width=1, border_color=_BORDER,
        )
        frame_novo.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))

        # Linha 0: Nome + Tel
        frame_l0 = ctk.CTkFrame(frame_novo, fg_color="transparent")
        frame_l0.pack(fill="x", padx=10, pady=(8, 4))
        frame_l0.grid_columnconfigure(1, weight=1)
        frame_l0.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(frame_l0, text="Nome:", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=_FG_LABEL).grid(row=0, column=0, padx=(0, 4), sticky="w")
        self.entry_novo_nome = ctk.CTkEntry(frame_l0, height=30, placeholder_text="Nome do cliente...",
                                            font=ctk.CTkFont(size=9), fg_color=_BG_CARD,
                                            border_color=_BORDER, text_color=_FG_PRIMARY, corner_radius=6)
        self.entry_novo_nome.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(frame_l0, text="Tel:", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=_FG_LABEL).grid(row=0, column=2, padx=(0, 4), sticky="w")
        self.entry_novo_tel = ctk.CTkEntry(frame_l0, height=30, placeholder_text="(xx) xxxxx",
                                           font=ctk.CTkFont(size=9), fg_color=_BG_CARD,
                                           border_color=_BORDER, text_color=_FG_PRIMARY, corner_radius=6)
        self.entry_novo_tel.grid(row=0, column=3, sticky="ew")

        # Linha 1: Limite + Dia + Botão
        frame_l1 = ctk.CTkFrame(frame_novo, fg_color="transparent")
        frame_l1.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame_l1, text="Limite R$:", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=_FG_LABEL).pack(side="left", padx=(0, 4))
        self.entry_novo_limite = ctk.CTkEntry(frame_l1, height=30, width=70,
                                              font=ctk.CTkFont(size=9), fg_color=_BG_CARD,
                                              border_color=_BORDER, text_color=_FG_PRIMARY, corner_radius=6)
        self.entry_novo_limite.insert(0, "500")
        self.entry_novo_limite.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(frame_l1, text="Dia Acerto:", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=_FG_LABEL).pack(side="left", padx=(0, 4))
        self.entry_novo_dia = ctk.CTkEntry(frame_l1, height=30, width=50,
                                           font=ctk.CTkFont(size=9), fg_color=_BG_CARD,
                                           border_color=_BORDER, text_color=_FG_PRIMARY, corner_radius=6)
        self.entry_novo_dia.insert(0, "5")
        self.entry_novo_dia.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            frame_l1, text="➕ Adicionar",
            command=self._cadastrar_cliente,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            fg_color=_BTN_ADD, hover_color=_ACCENT_GOLD,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=30,
        ).pack(side="right")

        self.entry_novo_nome.bind("<Return>", lambda e: self._cadastrar_cliente())

    # ════════════════════════════════════════════════════════════════════
    # COLUNA DIREITA — EXTRATO + PAGAMENTO
    # ════════════════════════════════════════════════════════════════════

    def _construir_coluna_direita(self, parent):
        self.frame_direito = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        self.frame_direito.grid(row=0, column=1, sticky="nsew", padx=6)
        self.frame_direito.grid_columnconfigure(0, weight=1)
        self.frame_direito.grid_rowconfigure(3, weight=1)

        # ── Cabeçalho do cliente ativo ──────────────────────────────
        frame_ch = ctk.CTkFrame(
            self.frame_direito, fg_color=_BG_HOVER, corner_radius=8,
        )
        frame_ch.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self.lbl_cliente_nome = ctk.CTkLabel(
            frame_ch, text="← Selecione um cliente",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_MUTED,
        )
        self.lbl_cliente_nome.pack(pady=(10, 2))

        self.lbl_cliente_saldo = ctk.CTkLabel(
            frame_ch, text="",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=_FG_MUTED,
        )
        self.lbl_cliente_saldo.pack()

        self.lbl_cliente_limite = ctk.CTkLabel(
            frame_ch, text="",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=_FG_MUTED,
        )
        self.lbl_cliente_limite.pack(pady=(2, 10))

        # ── Painel de Pagamento (oculto inicialmente) ───────────────
        self.frame_pagamento = ctk.CTkFrame(
            self.frame_direito, fg_color=("#F0FDF4", "#0D3B26"),
            corner_radius=8, border_width=1,
            border_color=("#BBF7D0", "#1A5C34"),
        )
        # Não o colocamos no grid ainda — aparece ao selecionar cliente

        row_pgt = ctk.CTkFrame(self.frame_pagamento, fg_color="transparent")
        row_pgt.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(
            row_pgt, text="Receber Valor (R$):",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=("#14532D", "#34D399"),
        ).pack(side="left", padx=(0, 8))

        self.entry_pagamento = ctk.CTkEntry(
            row_pgt, width=100, height=32,
            font=ctk.CTkFont(size=11),
            fg_color=_BG_CARD, border_color=("#BBF7D0", "#1A5C34"),
            text_color=_FG_PRIMARY, corner_radius=6,
        )
        self.entry_pagamento.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            row_pgt, text="Obs:",
            font=ctk.CTkFont(size=9),
            text_color=_FG_MUTED,
        ).pack(side="left", padx=(0, 4))

        self.entry_obs_pgt = ctk.CTkEntry(
            row_pgt, width=160, height=32,
            font=ctk.CTkFont(size=9),
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=6,
        )
        self.entry_obs_pgt.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            row_pgt, text="✔ Confirmar",
            command=self._confirmar_pagamento,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            fg_color=_BTN_REC, hover_color=("#155F3C", "#047857"),
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=32, width=120,
        ).pack(side="left")

        self.entry_pagamento.bind("<Return>", lambda e: self._confirmar_pagamento())

        # ── Extrato ─────────────────────────────────────────────────
        ctk.CTkFrame(
            self.frame_direito, height=1, corner_radius=0, fg_color=_BORDER,
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 4))

        ctk.CTkLabel(
            self.frame_direito, text="Extrato Detalhado:",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=15, pady=(8, 2))

        bg_ext = _hex(_BG_CARD)
        _aplicar_estilo_treeview("Extrato", bg_ext, _hex(_ACCENT_GOLD))

        frame_ext = tk.Frame(self.frame_direito, bg=bg_ext)
        frame_ext.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))

        colunas_ext = ("Data", "Tipo", "Valor", "Vencimento", "Observacao")
        self.tabela_extrato = ttk.Treeview(
            frame_ext, columns=colunas_ext, show="headings",
            height=12, style="Extrato.Treeview",
        )
        self.tabela_extrato.tag_configure("DEBITO",  foreground="#F87171", font=("Segoe UI", 9, "bold"))
        self.tabela_extrato.tag_configure("CREDITO", foreground="#34D399", font=("Segoe UI", 9, "bold"))

        for col, w, anc, label in [
            ("Data",       110, "center", "Data Mov."),
            ("Tipo",        70, "center", "Tipo"),
            ("Valor",       90, "e",      "Valor"),
            ("Vencimento", 130, "center", "Vencimento Combinado"),
            ("Observacao", 220, "w",      "Observação / Peças"),
        ]:
            self.tabela_extrato.heading(col, text=label)
            self.tabela_extrato.column(col, width=w, anchor=anc)

        scroll_ext = ttk.Scrollbar(
            frame_ext, orient="vertical",
            command=self.tabela_extrato.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.tabela_extrato.configure(yscrollcommand=scroll_ext.set)
        self.tabela_extrato.pack(side="left", fill="both", expand=True)
        scroll_ext.pack(side="right", fill="y")

        # ── Botão Excluir Cliente ────────────────────────────────────
        self.btn_excluir_cliente = ctk.CTkButton(
            self.frame_direito,
            text="🗑  Remover Cliente (apenas se saldo = R$ 0,00)",
            command=self._excluir_cliente_ativo,
            font=ctk.CTkFont(family="Segoe UI", size=8),
            fg_color=("#FEE2E2", "#3B0A0A"),
            hover_color=("#FCA5A5", "#7F1D1D"),
            text_color=_KPI_RED_FG,
            corner_radius=6,
            height=28,
        )
        # Oculto até cliente ser selecionado (usa grid_remove)
        self.btn_excluir_cliente.grid(row=4, column=0, sticky="e", padx=12, pady=(0, 10))
        self.btn_excluir_cliente.grid_remove()

        # Linha de pagamento — inicialmente oculta
        self._pagamento_visivel = False

    # ════════════════════════════════════════════════════════════════════
    # COLUNA DE ALERTAS
    # ════════════════════════════════════════════════════════════════════

    def _construir_coluna_alertas(self, parent):
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text="📅  Acertos Agendados para Hoje",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 6))

        bg_alerta = _hex(_BG_CARD)
        _aplicar_estilo_treeview("Alertas", bg_alerta, _hex(_ACCENT_GOLD))

        frame_tv = tk.Frame(frame, bg=bg_alerta)
        frame_tv.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        colunas = ("Nome", "Saldo Devedor", "Telefone")
        self.tree_alertas_dia = ttk.Treeview(
            frame_tv, columns=colunas, show="headings",
            height=14, style="Alertas.Treeview",
        )

        for col, w, anc in [
            ("Nome", 120, "w"), ("Saldo Devedor", 90, "center"), ("Telefone", 90, "center")
        ]:
            self.tree_alertas_dia.heading(col, text=col)
            self.tree_alertas_dia.column(col, width=w, anchor=anc)

        scroll_alert = ttk.Scrollbar(
            frame_tv, orient="vertical",
            command=self.tree_alertas_dia.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.tree_alertas_dia.configure(yscrollcommand=scroll_alert.set)
        self.tree_alertas_dia.pack(side="left", fill="both", expand=True)
        scroll_alert.pack(side="right", fill="y")

    # ════════════════════════════════════════════════════════════════════
    # LÓGICA DE NEGÓCIO — preservada integralmente
    # ════════════════════════════════════════════════════════════════════

    def _on_busca_keyrelease(self, event=None):
        if self._debounce_busca_id:
            self.after_cancel(self._debounce_busca_id)
        self._debounce_busca_id = self.after(300, lambda: self._recarregar_clientes(self.entry_busca.get()))

    def _recarregar_clientes(self, termo: str = ""):
        for item in self.tabela_clientes.get_children():
            self.tabela_clientes.delete(item)
        for c in fiado_ctrl.listar_clientes(termo):
            saldo = c["saldo_devedor"]
            tag   = "devedor" if saldo > 0 else "zerado"
            self.tabela_clientes.insert(
                "", tk.END,
                values=(
                    c["id"], c["nome"], f"R$ {saldo:.2f}",
                    c["proximo_vencimento"], c["ranking"], c["status_tempo"],
                ),
                tags=(tag,),
            )

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
            self._recarregar_clientes()
            self._atualizar_kpis()
            self.atualizar_tabela_alertas_do_dia()
        else:
            messagebox.showerror("Erro", msg)

    def _ao_selecionar_cliente(self, event):
        selecao = self.tabela_clientes.selection()
        if not selecao:
            return
        valores = self.tabela_clientes.item(selecao[0])["values"]
        self._cliente_ativo_id   = valores[0]
        self._cliente_ativo_nome = str(valores[1])
        saldo_str = str(valores[2])
        saldo = float(saldo_str.replace("R$ ", "").replace(".", "").replace(",", "."))

        self.lbl_cliente_nome.configure(text=self._cliente_ativo_nome, text_color=_FG_PRIMARY)
        if saldo > 0:
            self.lbl_cliente_saldo.configure(text=f"⚠️  Deve: {saldo_str}", text_color=_KPI_RED_FG)
        else:
            self.lbl_cliente_saldo.configure(text="✅  Sem dívida", text_color=("#059669", "#34D399"))

        dados = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
        if dados:
            self.lbl_cliente_limite.configure(
                text=f"Limite: R$ {dados['limite_credito']:.2f} | Venc.: {dados.get('proximo_vencimento','—')} | Fidelidade: {dados.get('ranking','N/A')}",
                text_color=_FG_MUTED,
            )

        # Exibe painel de pagamento e botão de exclusão
        if not self._pagamento_visivel:
            self.frame_pagamento.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
            self._pagamento_visivel = True
        self.btn_excluir_cliente.grid()

        self.entry_pagamento.delete(0, tk.END)
        self.entry_obs_pgt.delete(0, tk.END)
        self._recarregar_extrato()

    def _excluir_cliente_ativo(self):
        if not self._cliente_ativo_id:
            return
        confirmar = messagebox.askyesno(
            "Remover Cliente",
            f"Deseja remover '{self._cliente_ativo_nome}' permanentemente?\n"
            "Isso apaga todo o histórico de fiado.",
        )
        if not confirmar:
            return
        sucesso, msg = fiado_ctrl.excluir_cliente(self._cliente_ativo_id)
        if sucesso:
            self._cliente_ativo_id   = None
            self._cliente_ativo_nome = None
            self.lbl_cliente_nome.configure(text="← Selecione um cliente", text_color=_FG_MUTED)
            self.lbl_cliente_saldo.configure(text="", text_color=_FG_MUTED)
            self.lbl_cliente_limite.configure(text="")
            self.frame_pagamento.grid_remove()
            self._pagamento_visivel = False
            self.btn_excluir_cliente.grid_remove()
            for item in self.tabela_extrato.get_children():
                self.tabela_extrato.delete(item)
            self._recarregar_clientes()
            self._atualizar_kpis()
            self.atualizar_tabela_alertas_do_dia()
        else:
            messagebox.showerror("Não Permitido", msg)

    def _confirmar_pagamento(self):
        if not self._cliente_ativo_id:
            return
        try:
            valor = float(self.entry_pagamento.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Digite um valor numérico válido.")
            return
        obs = self.entry_obs_pgt.get().strip() or "Pagamento recebido"
        sucesso, msg = fiado_ctrl.registrar_pagamento(self._cliente_ativo_id, valor, obs)
        if sucesso:
            self.entry_pagamento.delete(0, tk.END)
            self.entry_obs_pgt.delete(0, tk.END)
            self._recarregar_clientes(self.entry_busca.get())
            self._recarregar_extrato()
            self._atualizar_kpis()
            self.atualizar_tabela_alertas_do_dia()
            dados = fiado_ctrl.buscar_cliente_por_id(self._cliente_ativo_id)
            if dados:
                novo_saldo = dados["saldo_devedor"]
                if novo_saldo > 0:
                    self.lbl_cliente_saldo.configure(text=f"⚠️  Deve: R$ {novo_saldo:.2f}", text_color=_KPI_RED_FG)
                else:
                    self.lbl_cliente_saldo.configure(text="✅  Sem dívida — conta zerada!", text_color=("#059669", "#34D399"))
        else:
            messagebox.showerror("Erro", msg)

    def _recarregar_extrato(self):
        for item in self.tabela_extrato.get_children():
            self.tabela_extrato.delete(item)
        if not self._cliente_ativo_id:
            return
        for m in fiado_ctrl.buscar_extrato(self._cliente_ativo_id):
            icone = "🔴 COMPRA" if m["tipo"] == "DEBITO" else "🟢 PAGTO"
            self.tabela_extrato.insert(
                "", tk.END,
                values=(m["data"], icone, f"R$ {m['valor']:.2f}", m["vencimento_lote"], m["obs"]),
                tags=(m["tipo"],),
            )

    def _atualizar_kpis(self):
        resumo = fiado_ctrl.resumo_fiado()
        self.kpi_total_aberto.configure(text=f"R$ {resumo['total_em_aberto']:.2f}")
        self.kpi_qtd_devedores.configure(text=str(resumo["clientes_devedores"]))
        self.kpi_total_clientes.configure(text=str(resumo["total_clientes"]))

    def atualizar_tabela_alertas_do_dia(self):
        for item in self.tree_alertas_dia.get_children():
            self.tree_alertas_dia.delete(item)
        for c in fiado_ctrl.listar_clientes_acerto_hoje():
            self.tree_alertas_dia.insert(
                "", "end",
                values=(c["nome"], f"R$ {c['saldo_devedor']:.2f}", c["telefone"]),
            )
