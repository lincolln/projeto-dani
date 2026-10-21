"""
tela_venda.py — PDV / Caixa
Refatorado para CustomTkinter 5.x:
  • CTkFrame com fg_color dinâmico — zero blocos brancos/cinzentos do SO
  • Três Treeviews (carrinho, histórico) com ttk.Style casado ao tema escuro
  • CTkComboBox para seleção de produto
  • CTkEntry para quantidade, desconto e data
  • CTkButton com corner_radius=8 e hover_color nativo para todos os botões
  • CTkRadioButton para formas de pagamento
  • Popup de fechamento convertido para CTkToplevel com estilo integrado
  • Toda a lógica de negócio e carrinho preservada sem alterações
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import estoque_ctrl

# ── Paletas dinâmicas (claro, escuro — Tema Slate Dark Mobile) ──────────────
_BG_WINDOW   = ("#F0F2F8", "#0f172a")
_BG_CARD     = ("#FFFFFF", "#1e293b")
_BG_HOVER    = ("#E8ECF4", "#0f172a")
_BG_CHECKOUT = ("#F8FAFF", "#0f172a")
_FG_PRIMARY  = ("#1A1D2E", "#f8fafc")
_FG_MUTED    = ("#6B7280", "#94a3b8")
_FG_LABEL    = ("#4B5563", "#cbd5e1")
_ACCENT_GOLD = ("#d97706", "#f59e0b")
_ACCENT_BLUE = ("#2563eb", "#3b82f6")
_BORDER      = ("#DDE3EE", "#334155")

_BTN_ADD     = ("#2563eb", "#3b82f6")
_BTN_FIN     = ("#16a34a", "#22c55e")
_BTN_DEL     = ("#dc2626", "#ef4444")
_BTN_FILT    = ("#334155", "#475569")


def _hex(color_tuple) -> str:
    mode = ctk.get_appearance_mode()
    return color_tuple[1] if mode == "Dark" else color_tuple[0]


def _aplicar_estilo_treeview(nome: str, bg_hex: str, heading_fg: str):
    """Configura um estilo TTK nomeado para o Treeview, casando o fundo ao tema CTk."""
    s = ttk.Style()
    s.configure(
        f"{nome}.Treeview",
        rowheight=28,
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
    s.configure(
        "Venda.Vertical.TScrollbar",
        troughcolor=_hex(_BG_WINDOW),
        background=_hex(_ACCENT_BLUE),
        arrowcolor=_hex(_FG_PRIMARY),
        relief="flat", borderwidth=0,
    )


class TelaVenda(ctk.CTkFrame):
    """
    PDV com carrinho estilo Mobile Slate Dark, desconto proporcional e histórico diário.
    Herda de CTkFrame para theming nativo claro/escuro sem conflitos.
    """

    def __init__(self, parent, controller, variacao_id_inicial: int | None = None):
        super().__init__(
            parent,
            corner_radius=0,
            fg_color=_BG_WINDOW,
        )
        self.controller = controller
        self._variacao_id_inicial = variacao_id_inicial
        self._carrinho: list[dict] = []
        self._data_filtro = datetime.now().strftime("%d/%m/%Y")
        self._dados_combo: dict = {}
        self._forma_pagamento = ctk.StringVar(value="DINHEIRO")
        self._debounce_desconto_id = None

        # Grid raiz
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)   # frame_corpo expande verticalmente

        self._construir_interface()

    # ════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DA INTERFACE
    # ════════════════════════════════════════════════════════════════════

    def _construir_interface(self):
        # ── Cabeçalho ───────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="🛒  Caixa e Ponto de Venda (PDV)",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=25, pady=(14, 6))

        # Carrega produtos com estoque (alimenta _dados_combo para vitrine e bipe)
        self._combo_valores = []
        for v in estoque_ctrl.listar_variacoes_com_estoque():
            texto = (
                f"ID:{v['variacao_id']} | {v['modelo_nome']} ({v['marca']}) "
                f"— {v['cor']} / Tam:{v['tamanho']} | "
                f"R$ {v['preco_venda']:.2f} — {v['estoque']} un."
            )
            self._combo_valores.append(texto)
            self._dados_combo[texto] = v

        # ── Corpo: Vitrine | Carrinho | Histórico ────────────────────
        frame_corpo = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_corpo.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 15))
        frame_corpo.grid_columnconfigure(0, weight=2)  # vitrine lateral de busca
        frame_corpo.grid_columnconfigure(1, weight=4)  # carrinho principal
        frame_corpo.grid_columnconfigure(2, weight=3)  # histórico de vendas
        frame_corpo.grid_rowconfigure(0, weight=1)

        self._construir_vitrine_lateral(frame_corpo)
        self._construir_carrinho(frame_corpo)
        self._construir_historico(frame_corpo)

        # Se vier da vitrine com variacao_id_inicial, adiciona direto ao carrinho
        if self._variacao_id_inicial:
            self.after(150, lambda: self._adicionar_variacao_direta(
                self._variacao_id_inicial, qtd=1
            ))

        self._atualizar_tabela_carrinho()
        self._atualizar_historico()

    # ── CARRINHO (ESTILO CARDS MOBILE COM + / - / 🗑️) ─────────────────

    def _construir_carrinho(self, parent):
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=14,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=1, sticky="nsew", padx=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header_cart = ctk.CTkFrame(frame, fg_color="transparent")
        header_cart.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 6))
        header_cart.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_cart, text="🛍️  Carrinho de Compras",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_badge_itens = ctk.CTkLabel(
            header_cart, text="0 itens",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#2563eb", "#60a5fa"),
            fg_color=("#dbeafe", "#172554"),
            corner_radius=999,
            padx=10, pady=2,
        )
        self.lbl_badge_itens.grid(row=0, column=1, sticky="e")

        # Treeview oculta mantida em memória para retrocompatibilidade 100%
        bg_cart = _hex(_BG_CARD)
        _aplicar_estilo_treeview("Cart", bg_cart, _hex(_ACCENT_GOLD))
        frame_tv_hidden = tk.Frame(frame, bg=bg_cart)
        colunas = ("Modelo", "Qtd", "Unitario", "Subtotal")
        self.tabela_carrinho = ttk.Treeview(
            frame_tv_hidden, columns=colunas, show="headings",
            height=1, style="Cart.Treeview",
        )

        # Lista visual de Cards do Carrinho (igual ao Mobile PWA)
        self.frame_cards_carrinho = ctk.CTkScrollableFrame(
            frame,
            fg_color=_BG_WINDOW,
            corner_radius=10,
            border_width=1,
            border_color=_BORDER,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self.frame_cards_carrinho.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.frame_cards_carrinho.grid_columnconfigure(0, weight=1)

        # ── Painel de Checkout ───────────────────────────────────────
        frame_checkout = ctk.CTkFrame(
            frame, fg_color=_BG_CHECKOUT, corner_radius=10,
            border_width=1, border_color=_BORDER,
        )
        frame_checkout.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

        # Linha 1: subtotal + desconto
        linha1 = ctk.CTkFrame(frame_checkout, fg_color="transparent")
        linha1.pack(fill="x", padx=12, pady=(10, 6))

        self.lbl_subtotal = ctk.CTkLabel(
            linha1, text="Subtotal: R$ 0,00",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=_FG_PRIMARY,
        )
        self.lbl_subtotal.pack(side="left")

        ctk.CTkLabel(
            linha1, text="Desconto R$:",
            font=ctk.CTkFont(size=13), text_color=_FG_MUTED,
        ).pack(side="left", padx=(20, 5))

        self.entry_desconto = ctk.CTkEntry(
            linha1, width=90, height=30,
            font=ctk.CTkFont(size=13),
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=6, justify="center",
        )
        self.entry_desconto.pack(side="left")
        self.entry_desconto.insert(0, "0.00")
        self.entry_desconto.bind("<KeyRelease>", self._on_desconto_keyrelease)

        self.lbl_percentual = ctk.CTkLabel(
            linha1, text="(0,0%)",
            font=ctk.CTkFont(size=13),
            text_color=_FG_MUTED,
        )
        self.lbl_percentual.pack(side="left", padx=6)

        # Linha 2: formas de pagamento — botões pill selecionáveis
        linha_pgto = ctk.CTkFrame(frame_checkout, fg_color="transparent")
        linha_pgto.pack(fill="x", padx=12, pady=(4, 8))

        ctk.CTkLabel(
            linha_pgto, text="Pagamento:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=_FG_LABEL,
        ).pack(side="left", padx=(0, 10))

        _FORMAS_PGTO = [
            ("💵 Dinheiro", "DINHEIRO", ("#059669", "#34D399")),
            ("📱 PIX",     "PIX",      _ACCENT_BLUE),
            ("💳 Cartão",  "CARTAO",   ("#7C3AED", "#A78BFA")),
            ("📒 Fiado",   "FIADO",    ("#DC2626", "#F87171")),
        ]
        self._btns_pgto = {}

        def _selecionar_pgto(valor):
            self._forma_pagamento.set(valor)
            for v, btn_info in self._btns_pgto.items():
                ativo = (v == valor)
                cor_pill = btn_info["cor"]
                btn_info["btn"].configure(
                    fg_color=cor_pill if ativo else _BG_HOVER,
                    text_color=("#FFFFFF", "#FFFFFF") if ativo else _FG_MUTED,
                    border_color=cor_pill if ativo else _BORDER,
                    border_width=2 if ativo else 1,
                )

        for label, valor, cor in _FORMAS_PGTO:
            btn_pill = ctk.CTkButton(
                linha_pgto,
                text=label,
                command=lambda v=valor: _selecionar_pgto(v),
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color=_BG_HOVER,
                hover_color=cor,
                text_color=_FG_MUTED,
                border_color=_BORDER,
                border_width=1,
                corner_radius=20,
                height=30, width=100,
            )
            btn_pill.pack(side="left", padx=4)
            self._btns_pgto[valor] = {"btn": btn_pill, "cor": cor}

        # Seleciona o padrão visualmente
        _selecionar_pgto("DINHEIRO")

        # Divider
        ctk.CTkFrame(frame_checkout, height=1, fg_color=_BORDER, corner_radius=0
                     ).pack(fill="x", padx=12, pady=(0, 8))

        # Linha 3: total + botão finalizar (destaque premium)
        linha2 = ctk.CTkFrame(frame_checkout, fg_color="transparent")
        linha2.pack(fill="x", padx=12, pady=(0, 12))

        # Bloco do total
        frame_total = ctk.CTkFrame(linha2, fg_color=("#F0FDF4", "#0D3B26"), corner_radius=8)
        frame_total.pack(side="left", padx=(0, 10), pady=2)

        ctk.CTkLabel(
            frame_total, text="TOTAL A PAGAR",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=_FG_MUTED,
        ).pack(padx=14, pady=(6, 0))

        self.lbl_total = ctk.CTkLabel(
            frame_total, text="R$ 0,00",
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=("#059669", "#34D399"),
        )
        self.lbl_total.pack(padx=14, pady=(0, 6))

        ctk.CTkButton(
            linha2,
            text="✔  Finalizar Venda",
            command=self._finalizar_venda,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=_BTN_FIN, hover_color=("#155F3C", "#047857"),
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=10, height=44,
        ).pack(side="right", fill="y")

    # ── HISTÓRICO ─────────────────────────────────────────────────────

    def _construir_historico(self, parent):
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text="📅  Histórico de Vendas por Dia",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 6))

        # Filtro de data
        frame_filtro = ctk.CTkFrame(frame, fg_color="transparent")
        frame_filtro.grid(row=0, column=0, sticky="e", padx=15, pady=(12, 6))

        ctk.CTkLabel(
            frame_filtro, text="Data:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=_FG_LABEL,
        ).pack(side="left", padx=(0, 5))

        self.entry_data = ctk.CTkEntry(
            frame_filtro, width=100, height=30,
            font=ctk.CTkFont(size=13),
            fg_color=_BG_WINDOW, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=6, justify="center",
        )
        self.entry_data.pack(side="left")
        self.entry_data.insert(0, self._data_filtro)
        self.entry_data.bind("<KeyRelease>", self._mascara_data)

        ctk.CTkButton(
            frame_filtro,
            text="🔍 Filtrar",
            command=self._atualizar_historico,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=_BTN_FILT, hover_color=_ACCENT_BLUE,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=6, height=30, width=80,
        ).pack(side="left", padx=(6, 0))

        # Treeview histórico
        bg_hist = _hex(_BG_CARD)
        _aplicar_estilo_treeview("Hist", bg_hist, _hex(_ACCENT_GOLD))

        frame_tv = tk.Frame(frame, bg=bg_hist)
        frame_tv.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        colunas = ("ID", "Modelo", "Cor/Tam", "Qtd", "Total")
        self.tabela_historico = ttk.Treeview(
            frame_tv, columns=colunas, show="headings",
            height=14, style="Hist.Treeview",
        )
        for col, w, anc in [
            ("ID", 40, "center"), ("Modelo", 200, "w"),
            ("Cor/Tam", 100, "center"), ("Qtd", 40, "center"),
            ("Total", 80, "center"),
        ]:
            self.tabela_historico.heading(col, text=col)
            self.tabela_historico.column(col, width=w, anchor=anc)

        scroll_hist = ttk.Scrollbar(
            frame_tv, orient="vertical",
            command=self.tabela_historico.yview,
            style="Venda.Vertical.TScrollbar",
        )
        self.tabela_historico.configure(yscrollcommand=scroll_hist.set)
        self.tabela_historico.pack(side="left", fill="both", expand=True)
        scroll_hist.pack(side="right", fill="y")

    # ════════════════════════════════════════════════════════════════════
    # LÓGICA — CARRINHO (preservada integralmente)
    # ════════════════════════════════════════════════════════════════════

    def _adicionar_ao_carrinho(self):
        """Mantido por compatibilidade. Fluxo primário via vitrine lateral / bipe."""
        pass

    # ─────────────────────────────────────────────────────────────────────
    # CORE DE ADIÇÃO — AGRUPAMENTO INTELIGENTE
    # ─────────────────────────────────────────────────────────────────────

    def _adicionar_variacao_direta(self, variacao_id: int, qtd: int = 1):
        """Core interno: adiciona ou agrupa variacao_id no carrinho.

        Não exibe popup de sucesso — permanece silencioso para não
        interromper fluxos de caixa rápidos (bipes consecutivos).
        """
        info = next(
            (v for v in self._dados_combo.values() if v["variacao_id"] == variacao_id),
            None,
        )
        if not info:
            return

        vid = variacao_id
        item_existente = next(
            (i for i in self._carrinho if i["variacao_id"] == vid), None
        )
        qtd_atual = item_existente["qtd"] if item_existente else 0
        nova_qtd  = qtd_atual + qtd

        if nova_qtd > info["estoque"]:
            messagebox.showerror(
                "Estoque Insuficiente",
                f"Disponível: {info['estoque']} un.  |  Já no carrinho: {qtd_atual} un.",
            )
            return

        if item_existente:
            item_existente["qtd"]     = nova_qtd
            item_existente["subtotal"] = info["preco_venda"] * nova_qtd
        else:
            self._carrinho.append({
                "variacao_id": vid,
                "modelo":  info["modelo_nome"],
                "marca":   info["marca"],
                "cor":     info["cor"],
                "tamanho": info["tamanho"],
                "preco":   info["preco_venda"],
                "qtd":     qtd,
                "subtotal": info["preco_venda"] * qtd,
            })

        self._atualizar_tabela_carrinho()
        self.update_idletasks()

    def adicionar_via_bipe(self, variacao_id: int):
        """Ponto de entrada PÚBLICO para o Bipe Global e o Picker de Tamanho.

        Recarrega o combo se necessário (ex: após uma venda) e chama o core.
        """
        ids_disponiveis = {v["variacao_id"] for v in self._dados_combo.values()}
        if variacao_id not in ids_disponiveis:
            self._recarregar_combo()
        self._adicionar_variacao_direta(variacao_id, qtd=1)

    def _remover_do_carrinho(self):
        selecao = self.tabela_carrinho.selection()
        if not selecao:
            return
        idx = self.tabela_carrinho.index(selecao[0])
        if 0 <= idx < len(self._carrinho):
            self._carrinho.pop(idx)
            self._atualizar_tabela_carrinho()

    # ─────────────────────────────────────────────────────────────────────
    # VITRINE LATERAL DE BUSCA RÁPIDA (Fluxo Manual Veloz)
    # ─────────────────────────────────────────────────────────────────────

    def _construir_vitrine_lateral(self, parent):
        """Painel esquerdo: busca em tempo real + grid de produtos clicáveis."""
        frame = ctk.CTkFrame(
            parent, fg_color=_BG_CARD, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            frame, text="🔍  Busca Rápida",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        self.entry_busca_vitrine = ctk.CTkEntry(
            frame,
            placeholder_text="Modelo ou marca...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=_BG_WINDOW, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=8,
            height=32,
        )
        self.entry_busca_vitrine.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.entry_busca_vitrine.bind("<KeyRelease>", self._on_busca_keyrelease)

        self.frame_vitrine_venda = ctk.CTkScrollableFrame(
            frame,
            fg_color=_BG_WINDOW,
            corner_radius=8,
            scrollbar_button_color=_ACCENT_BLUE,
            scrollbar_button_hover_color=_ACCENT_GOLD,
        )
        self.frame_vitrine_venda.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 10))

        self._dados_vitrine: list[dict] = []
        self._picker_popup = None
        # Popula após layout estabilizar
        self.after(100, self._atualizar_dados_vitrine)

    def _atualizar_dados_vitrine(self):
        """Agrupa _dados_combo por (modelo, marca) para a vitrine lateral."""
        grupos: dict = {}
        for v in self._dados_combo.values():
            key = (v["modelo_nome"], v["marca"])
            if key not in grupos:
                grupos[key] = {
                    "modelo": v["modelo_nome"],
                    "marca":  v["marca"],
                    "variacoes": [],
                }
            grupos[key]["variacoes"].append(v)
        self._dados_vitrine = sorted(grupos.values(), key=lambda p: p["modelo"])
        self._renderizar_vitrine()

    def _on_busca_keyrelease(self, event=None):
        if hasattr(self, '_busca_after_id') and self._busca_after_id:
            self.after_cancel(self._busca_after_id)
        self._busca_after_id = self.after(300, self._filtrar_vitrine)

    def _filtrar_vitrine(self):
        """Filtra a vitrine em tempo real — busca bruta AND sobre ficha completa do produto."""
        termo = self.entry_busca_vitrine.get().strip().lower()

        if not termo:
            self._renderizar_vitrine(self._dados_vitrine)
            return

        tokens = termo.split()
        filtrados = []

        for p in self._dados_vitrine:
            var_base = p.get('variacoes', [{}])[0]
            metadados = ' '.join([
                p.get('modelo', ''),
                p.get('marca', ''),
                var_base.get('corte', ''),
                var_base.get('tecido', ''),
            ]).lower()

            # Filtro AND: só exibe se TODOS os tokens estiverem na ficha completa
            if all(tk in metadados for tk in tokens):
                filtrados.append(p)

        self._renderizar_vitrine(filtrados)


    def _renderizar_vitrine(self, produtos: list | None = None):
        """Reconstrói a vitrine lateral com cards no estilo Mobile Slate Dark."""
        for w in self.frame_vitrine_venda.winfo_children():
            w.destroy()

        if produtos is None:
            produtos = self._dados_vitrine

        if not produtos:
            ctk.CTkLabel(
                self.frame_vitrine_venda,
                text="Nenhum produto\ncom estoque.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=_FG_MUTED,
                justify="center",
            ).pack(pady=24)
            return

        for p in produtos:
            variacoes = p.get("variacoes", [{}])
            var_base  = variacoes[0]
            nome   = p.get("modelo", var_base.get("modelo_nome", "Peça"))
            marca  = p.get("marca",  var_base.get("marca",  "N/A"))
            corte  = var_base.get("corte",  "") or ""
            tecido = var_base.get("tecido", "") or ""
            preco  = var_base.get("preco_venda", 0.0)
            est_tot = sum(v.get("estoque", 0) for v in variacoes)

            card_item = ctk.CTkFrame(
                self.frame_vitrine_venda,
                fg_color=_BG_CARD,
                corner_radius=10,
                border_width=1,
                border_color=_BORDER,
                cursor="hand2",
            )
            card_item.pack(fill="x", padx=4, pady=4)
            card_item.grid_columnconfigure(0, weight=1)

            lbl_tit = ctk.CTkLabel(
                card_item,
                text=f"{nome} — {marca}",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=_FG_PRIMARY,
                anchor="w",
            )
            lbl_tit.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 1))

            sub_parts = [s for s in (corte.strip(), tecido.strip()) if s]
            sub_txt   = " • ".join(sub_parts) if sub_parts else "Toque para escolher tamanho"
            lbl_sub = ctk.CTkLabel(
                card_item,
                text=sub_txt,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=_FG_MUTED,
                anchor="w",
            )
            lbl_sub.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 4))

            lbl_pr = ctk.CTkLabel(
                card_item,
                text=f"R$ {preco:.2f}",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=("#16a34a", "#22c55e"),
                anchor="w",
            )
            lbl_pr.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 8))

            lbl_est = ctk.CTkLabel(
                card_item,
                text=f"+ {est_tot} un.",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=("#2563eb", "#60a5fa"),
                fg_color=("#dbeafe", "#172554"),
                corner_radius=999,
                padx=8, pady=1,
            )
            lbl_est.grid(row=2, column=1, sticky="e", padx=10, pady=(0, 8))

            def _click_vit(e, prod=p):
                self._abrir_picker_tamanho(prod)

            for w_child in (card_item, lbl_tit, lbl_sub, lbl_pr, lbl_est):
                w_child.bind("<Button-1>", _click_vit)

    def _abrir_picker_tamanho(self, produto_dados: dict):
        """Abre popup centralizado com botões quadrados para cada tamanho disponível."""
        variacoes_disp = [
            v for v in produto_dados["variacoes"]
            if v.get("estoque", 0) > 0
        ]
        if not variacoes_disp:
            messagebox.showwarning(
                "Sem Estoque",
                f"{produto_dados['modelo']} não tem estoque disponível.",
            )
            return

        # Fecha picker anterior se existir
        if self._picker_popup and self._picker_popup.winfo_exists():
            try:
                self._picker_popup.destroy()
            except Exception:
                pass

        picker = ctk.CTkToplevel(self.winfo_toplevel())
        picker.wm_overrideredirect(True)
        picker.attributes("-topmost", True)
        picker.configure(fg_color="#0f172a")
        self._picker_popup = picker

        # Borda decorativa azul
        borda = ctk.CTkFrame(picker, fg_color="#3b82f6", corner_radius=14)
        borda.pack(padx=1, pady=1)
        inner = ctk.CTkFrame(borda, fg_color="#1e293b", corner_radius=13)
        inner.pack(padx=1, pady=1)

        ctk.CTkLabel(
            inner,
            text=f"⚡  {produto_dados['modelo']}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#f8fafc",
        ).pack(padx=24, pady=(14, 2))

        ctk.CTkLabel(
            inner,
            text=f"{produto_dados['marca']}  —  Selecione o tamanho",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#94a3b8",
        ).pack(padx=24, pady=(0, 12))

        # Grade de botões quadrados
        frame_sizes = ctk.CTkFrame(inner, fg_color="transparent")
        frame_sizes.pack(padx=16, pady=(0, 10))

        MAX_COLS = 4
        for idx, v in enumerate(variacoes_disp):
            tam = v.get("tamanho", "?")
            est = v.get("estoque", 0)
            vid = v.get("variacao_id")
            row = idx // MAX_COLS
            col = idx % MAX_COLS

            def _on_click(variacao_id=vid):
                try:
                    if picker.winfo_exists():
                        picker.destroy()
                except Exception:
                    pass
                self.adicionar_via_bipe(variacao_id)

            bloco = ctk.CTkFrame(frame_sizes, fg_color="transparent")
            bloco.grid(row=row, column=col, padx=5, pady=5)

            ctk.CTkButton(
                bloco,
                text=tam,
                command=_on_click,
                font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
                fg_color="#2563eb",
                hover_color="#3b82f6",
                text_color="#FFFFFF",
                corner_radius=10,
                width=72, height=72,
            ).pack()

            ctk.CTkLabel(
                bloco,
                text=f"{est} un.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#94a3b8",
            ).pack()

        # Botão cancelar
        ctk.CTkButton(
            inner,
            text="✕  Cancelar",
            command=lambda: picker.destroy() if picker.winfo_exists() else None,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="transparent",
            hover_color="#334155",
            text_color="#94a3b8",
            corner_radius=6,
            height=28,
        ).pack(pady=(0, 12))

        # Centraliza na tela
        picker.update_idletasks()
        pw = picker.winfo_reqwidth()
        ph = picker.winfo_reqheight()
        sw = picker.winfo_screenwidth()
        sh = picker.winfo_screenheight()
        picker.geometry(f"+{(sw - pw) // 2}+{(sh - ph) // 2}")

        def _verificar_foco(e):
            if not picker.winfo_exists():
                return
            try:
                foco = picker.focus_get()
                if foco is None or (foco != picker and foco.winfo_toplevel() != picker):
                    picker.destroy()
            except Exception:
                pass

        picker.bind("<Escape>", lambda e: picker.destroy() if picker.winfo_exists() else None)
        picker.bind("<FocusOut>", lambda e: picker.after(150, lambda: _verificar_foco(e)))
        picker.focus_set()

    # ─────────────────────────────────────────────────────────────────────

    def _on_desconto_keyrelease(self, event=None):
        if self._debounce_desconto_id:
            self.after_cancel(self._debounce_desconto_id)
        self._debounce_desconto_id = self.after(200, self._recalcular_live)

    def _alterar_qtd_item(self, idx: int, delta: int):
        """Altera a quantidade de um item do carrinho via botões [-] e [+]."""
        if not (0 <= idx < len(self._carrinho)):
            return
        item = self._carrinho[idx]
        nova_qtd = item["qtd"] + delta
        if nova_qtd <= 0:
            self._carrinho.pop(idx)
            self._atualizar_tabela_carrinho()
            return

        vid = item["variacao_id"]
        info = next(
            (v for v in self._dados_combo.values() if v["variacao_id"] == vid),
            None,
        )
        estoque_max = info["estoque"] if info else nova_qtd
        if nova_qtd > estoque_max:
            messagebox.showwarning(
                "Limite de Estoque",
                f"Estoque máximo disponível para esta peça: {estoque_max} un.",
            )
            return

        item["qtd"] = nova_qtd
        item["subtotal"] = item["preco"] * nova_qtd
        self._atualizar_tabela_carrinho()

    def _remover_item_idx(self, idx: int):
        if 0 <= idx < len(self._carrinho):
            self._carrinho.pop(idx)
            self._atualizar_tabela_carrinho()

    def _atualizar_tabela_carrinho(self):
        # 1. Mantém Treeview sincronizada em memória
        for linha in self.tabela_carrinho.get_children():
            self.tabela_carrinho.delete(linha)

        # 2. Reconstrói os Cards visuais estilo Mobile PWA
        if hasattr(self, "frame_cards_carrinho"):
            for w in self.frame_cards_carrinho.winfo_children():
                w.destroy()

        subtotal = 0.0
        total_pecas = sum(i["qtd"] for i in self._carrinho)
        if hasattr(self, "lbl_badge_itens"):
            self.lbl_badge_itens.configure(
                text=f"{total_pecas} {'item' if total_pecas == 1 else 'itens'}"
            )

        if not self._carrinho and hasattr(self, "frame_cards_carrinho"):
            ctk.CTkLabel(
                self.frame_cards_carrinho,
                text="🛒  Carrinho vazio\nBipe uma etiqueta ou clique em um produto ao lado.",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                text_color=_FG_MUTED,
                justify="center",
            ).grid(row=0, column=0, padx=20, pady=50)

        for idx, item in enumerate(self._carrinho):
            subtotal += item["subtotal"]
            self.tabela_carrinho.insert(
                "", tk.END,
                values=(
                    f"{item['modelo']} ({item['cor']}/{item['tamanho']})",
                    item["qtd"],
                    f"R$ {item['preco']:.2f}",
                    f"R$ {item['subtotal']:.2f}",
                ),
            )

            if hasattr(self, "frame_cards_carrinho"):
                card = ctk.CTkFrame(
                    self.frame_cards_carrinho,
                    fg_color=_BG_CARD,
                    corner_radius=10,
                    border_width=1,
                    border_color=_BORDER,
                )
                card.grid(row=idx, column=0, sticky="ew", padx=4, pady=4)
                card.grid_columnconfigure(0, weight=1)

                # Info esquerda: Nome + Detalhes + Subtotal
                info_f = ctk.CTkFrame(card, fg_color="transparent")
                info_f.grid(row=0, column=0, sticky="ew", padx=12, pady=8)

                ctk.CTkLabel(
                    info_f,
                    text=f"{item['modelo']} — {item.get('marca', '')}",
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    text_color=_FG_PRIMARY,
                    anchor="w",
                ).pack(anchor="w")

                ctk.CTkLabel(
                    info_f,
                    text=f"Tam: {item['tamanho']}  •  Cor: {item['cor']}  •  Unit: R$ {item['preco']:.2f}",
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color=_FG_MUTED,
                    anchor="w",
                ).pack(anchor="w", pady=(1, 2))

                ctk.CTkLabel(
                    info_f,
                    text=f"R$ {item['subtotal']:.2f}",
                    font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                    text_color=("#16a34a", "#22c55e"),
                    anchor="w",
                ).pack(anchor="w")

                # Controles direita: [−] Qtd [+] [🗑️]
                ctrl_f = ctk.CTkFrame(card, fg_color="transparent")
                ctrl_f.grid(row=0, column=1, sticky="e", padx=10, pady=8)

                ctk.CTkButton(
                    ctrl_f,
                    text="−",
                    width=32, height=32,
                    corner_radius=8,
                    fg_color=_BG_WINDOW,
                    hover_color=_ACCENT_BLUE,
                    border_width=1,
                    border_color=_BORDER,
                    font=ctk.CTkFont(size=16, weight="bold"),
                    command=lambda i=idx: self._alterar_qtd_item(i, -1),
                ).pack(side="left", padx=2)

                ctk.CTkLabel(
                    ctrl_f,
                    text=str(item["qtd"]),
                    width=28,
                    font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                    text_color=_FG_PRIMARY,
                ).pack(side="left", padx=4)

                ctk.CTkButton(
                    ctrl_f,
                    text="+",
                    width=32, height=32,
                    corner_radius=8,
                    fg_color=_BG_WINDOW,
                    hover_color=_ACCENT_BLUE,
                    border_width=1,
                    border_color=_BORDER,
                    font=ctk.CTkFont(size=16, weight="bold"),
                    command=lambda i=idx: self._alterar_qtd_item(i, +1),
                ).pack(side="left", padx=2)

                ctk.CTkButton(
                    ctrl_f,
                    text="🗑️",
                    width=32, height=32,
                    corner_radius=8,
                    fg_color=("#fee2e2", "#2d161d"),
                    hover_color=_BTN_DEL,
                    border_width=1,
                    border_color=("#fca5a5", "#5c1d24"),
                    font=ctk.CTkFont(size=14),
                    command=lambda i=idx: self._remover_item_idx(i),
                ).pack(side="left", padx=(6, 0))

        self.lbl_subtotal.configure(text=f"Subtotal: R$ {subtotal:.2f}")
        self._recalcular_live()

    def _recalcular_live(self):
        subtotal = sum(i["subtotal"] for i in self._carrinho)
        try:
            desconto = float(self.entry_desconto.get().replace(",", ".") or "0")
        except ValueError:
            desconto = 0.0
        desconto = min(desconto, subtotal)
        total    = subtotal - desconto
        pct      = (desconto / subtotal * 100) if subtotal > 0 else 0.0
        self.lbl_percentual.configure(text=f"({pct:.1f}%)")
        # Formata o total em pt-BR (R$ 1.234,56)
        total_fmt = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.lbl_total.configure(text=f"R$ {total_fmt}")

    # ════════════════════════════════════════════════════════════════════
    # POPUP DE FECHAMENTO — convertido para CTkToplevel
    # ════════════════════════════════════════════════════════════════════

    def _finalizar_venda(self):
        if not self._carrinho:
            messagebox.showerror("Erro", "O carrinho está vazio.")
            return

        subtotal = sum(item["subtotal"] for item in self._carrinho)
        try:
            desconto_total = float(self.entry_desconto.get().replace(",", ".")) if self.entry_desconto.get() else 0.0
        except Exception:
            desconto_total = 0.0
        
        desconto_total = max(0.0, min(desconto_total, subtotal))
        total_final = max(0.0, subtotal - desconto_total)

        from controllers import estoque_ctrl, fiado_ctrl

        popup = ctk.CTkToplevel(self.winfo_toplevel())
        popup.title("Finalizar Venda — Kanemberg Multimarcas")
        popup.geometry("480x700")
        popup.configure(fg_color=_hex(_BG_WINDOW))
        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        popup.resizable(False, False)

        ctk.CTkLabel(
            popup, text="Fechamento de Caixa",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=_FG_PRIMARY,
        ).pack(pady=(16, 6))

        # Resumo de valores
        frame_resumo = ctk.CTkFrame(
            popup, fg_color=("#EAECEE", "#1A2236"), corner_radius=8,
        )
        frame_resumo.pack(fill="x", padx=18, pady=(0, 10))
        ctk.CTkLabel(
            frame_resumo,
            text=f"Total Líquido: R$ {total_final:.2f}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("#27AE60", "#34D399"),
        ).pack(padx=14, pady=10)

        # Forma de pagamento
        ctk.CTkLabel(
            popup, text="Forma de Pagamento:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=_FG_LABEL,
        ).pack(pady=(0, 4))

        combo_pagamento = ctk.CTkComboBox(
            popup,
            values=["DINHEIRO", "CARTAO", "PIX", "FIADO"],
            state="readonly",
            width=260, height=36,
            font=ctk.CTkFont(size=15),
            fg_color=_BG_CARD, border_color=_BORDER,
            button_color=_ACCENT_BLUE, button_hover_color=_ACCENT_GOLD,
            text_color=_FG_PRIMARY, corner_radius=8,
        )
        combo_pagamento.set(self._forma_pagamento.get())
        combo_pagamento.pack(pady=(0, 6))

        # Painel do Fiado (oculto inicialmente)
        frame_fiado = ctk.CTkFrame(
            popup, fg_color=_BG_CARD, corner_radius=10,
            border_width=1, border_color=_BORDER,
        )

        ctk.CTkLabel(
            frame_fiado,
            text="Vinculação de Conta Corrente / Fiado",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=_FG_PRIMARY,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(frame_fiado, text="Cliente Cadastrado:",
                     font=ctk.CTkFont(size=13), text_color=_FG_LABEL).pack(anchor="w", padx=12)
        lista_clientes_db = fiado_ctrl.listar_clientes()
        dict_clientes = {c["nome"]: c["id"] for c in lista_clientes_db}
        combo_clientes = ctk.CTkComboBox(
            frame_fiado,
            values=list(dict_clientes.keys()) if dict_clientes else ["—"],
            state="readonly", width=400, height=32,
            font=ctk.CTkFont(size=13),
            fg_color=_BG_WINDOW, border_color=_BORDER,
            button_color=_ACCENT_BLUE, text_color=_FG_PRIMARY, corner_radius=6,
        )
        combo_clientes.pack(padx=12, pady=(0, 6))

        ctk.CTkLabel(
            frame_fiado, text="— OU CADASTRAR CLIENTE NOVO AGORA —",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=_FG_MUTED,
        ).pack(pady=(4, 0))

        ctk.CTkLabel(frame_fiado, text="Nome do Cliente:",
                     font=ctk.CTkFont(size=13), text_color=_FG_LABEL).pack(anchor="w", padx=12)
        entry_nome_novo = ctk.CTkEntry(
            frame_fiado, width=400, height=30,
            font=ctk.CTkFont(size=13),
            fg_color=_BG_WINDOW, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=6,
        )
        entry_nome_novo.pack(padx=12, pady=(0, 6))

        ctk.CTkLabel(frame_fiado, text="Data Combinada (DD/MM/AAAA):",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=_FG_LABEL).pack(anchor="w", padx=12)
        entry_vencimento = ctk.CTkEntry(
            frame_fiado, width=200, height=30,
            font=ctk.CTkFont(size=14),
            fg_color=_BG_WINDOW, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=6, justify="center",
        )
        from datetime import timedelta
        data_sugerida = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
        entry_vencimento.pack(padx=12, pady=(0, 12))
        entry_vencimento.insert(0, data_sugerida)

        def _toggle_fiado(choice=None):
            if combo_pagamento.get() == "FIADO":
                frame_fiado.pack(fill="x", padx=18, pady=(0, 10))
            else:
                frame_fiado.pack_forget()

        combo_pagamento.configure(command=_toggle_fiado)
        if self._forma_pagamento.get() == "FIADO":
            frame_fiado.pack(fill="x", padx=18, pady=(0, 10))

        def confirmar_fechamento_caixa():
            forma_pgto = combo_pagamento.get()
            c_id    = None
            dt_venc = None

            if forma_pgto == "FIADO":
                try:
                    dt_venc = datetime.strptime(entry_vencimento.get().strip(), "%d/%m/%Y")
                except Exception:
                    messagebox.showerror("Erro", "Formato de data inválido! Use DD/MM/AAAA.")
                    return
                nome_existente = combo_clientes.get()
                nome_novo      = entry_nome_novo.get().strip()
                if nome_existente and nome_existente != "—" and nome_existente in dict_clientes:
                    c_id = dict_clientes[nome_existente]
                elif nome_novo:
                    dia_p = dt_venc.day
                    sucesso_c, msg_c = fiado_ctrl.adicionar_cliente(nome=nome_novo, telefone="Sem Telefone", limite=1000.0, dia_preferencial=dia_p)
                    if not sucesso_c:
                        messagebox.showerror("Erro", msg_c)
                        return
                    c_id = fiado_ctrl.buscar_cliente_por_nome(nome_novo)["id"]
                else:
                    messagebox.showerror("Erro", "Selecione um cliente ou preencha o cadastro do novo.")
                    return

            try:
                lista_itens_motor = [{
                    "variacao_id": item["variacao_id"],
                    "modelo":      item["modelo"],
                    "cor":         item.get("cor", "Padrão"),
                    "tamanho":     item.get("tamanho", "U"),
                    "qtd":         item["qtd"],
                    "subtotal":    item["subtotal"],
                    "marca":       item.get("marca", "Sem Marca"),
                } for item in self._carrinho]

                sucesso, msg = estoque_ctrl.registrar_venda_lote(
                    itens_carrinho=lista_itens_motor,
                    desconto_total=desconto_total,
                    forma_pagamento=forma_pgto,
                    cliente_id=c_id,
                    dt_vencimento=dt_venc,
                )
                if sucesso:
                    messagebox.showinfo("Sucesso", "Venda finalizada com sucesso!")
                    self._limpar_pos_venda()
                    popup.destroy()
                else:
                    messagebox.showerror("Erro", msg)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao processar: {e}")

        ctk.CTkButton(
            popup,
            text="✔  FINALIZAR E SALVAR ESTOQUE",
            command=confirmar_fechamento_caixa,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=_BTN_FIN, hover_color=("#155F3C", "#047857"),
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=10, height=44,
        ).pack(side="bottom", fill="x", padx=18, pady=14)

    # ════════════════════════════════════════════════════════════════════
    # LÓGICA — HISTÓRICO (preservada integralmente)
    # ════════════════════════════════════════════════════════════════════

    def _mascara_data(self, event):
        if event.keysym == "BackSpace":
            return
        texto = self.entry_data.get().replace("/", "")
        novo  = ""
        if len(texto) > 0: novo += texto[:2]
        if len(texto) > 2: novo += "/" + texto[2:4]
        if len(texto) > 4: novo += "/" + texto[4:8]
        self.entry_data.delete(0, tk.END)
        self.entry_data.insert(0, novo)

    def _atualizar_historico(self):
        for linha in self.tabela_historico.get_children():
            self.tabela_historico.delete(linha)
        data = self.entry_data.get().strip() or self._data_filtro
        self._data_filtro = data
        for v in estoque_ctrl.buscar_vendas_por_data(data):
            self.tabela_historico.insert(
                "", tk.END,
                values=(
                    v["id"], v["modelo_nome"],
                    f"{v['cor']} / {v['tamanho']}",
                    v["quantidade"],
                    f"R$ {v['valor_total']:.2f}",
                ),
            )

    def _limpar_pos_venda(self):
        self._carrinho = []
        self.entry_desconto.delete(0, tk.END)
        self.entry_desconto.insert(0, "0.00")
        self._forma_pagamento.set("DINHEIRO")
        self._atualizar_tabela_carrinho()
        self._recarregar_combo()
        self._atualizar_historico()

    def _recarregar_combo(self):
        """Recarrega _dados_combo do banco (alimenta vitrine lateral e bipe global)."""
        self._combo_valores = []
        self._dados_combo   = {}
        for v in estoque_ctrl.listar_variacoes_com_estoque():
            texto = (
                f"ID:{v['variacao_id']} | {v['modelo_nome']} ({v['marca']}) "
                f"— {v['cor']} / Tam:{v['tamanho']} | "
                f"R$ {v['preco_venda']:.2f} — {v['estoque']} un."
            )
            self._combo_valores.append(texto)
            self._dados_combo[texto] = v
        # Atualiza a vitrine lateral com os dados frescos
        if hasattr(self, "_dados_vitrine"):
            self._atualizar_dados_vitrine()

    def atualizar_dados(self):
        """Recarrega vitrine lateral e histórico do dia ao voltar para a aba de Venda (preservando o carrinho)."""
        self._recarregar_combo()
        self._atualizar_historico()
        self._atualizar_tabela_carrinho()
