"""
tela_config.py — Painel de Configurações (Redesign Premium CTk)
Cada aba gerencia um tipo de atributo (Marcas, Cores, etc.)
Convertido de tk puro para CustomTkinter com tema escuro unificado.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers import config_ctrl

# ── Paleta (espelha o resto do app) ──────────────────────────────────────────
_BG_WINDOW  = ("#F0F2F8", "#0F1117")
_BG_CARD    = ("#FFFFFF",  "#16191F")
_BG_HOVER   = ("#E8ECF4",  "#22273A")
_FG_PRIMARY = ("#1A1D2E",  "#F0F2F8")
_FG_MUTED   = ("#6B7280",  "#8A8FA8")
_FG_LABEL   = ("#4B5563",  "#A0A8C0")
_ACCENT_G   = ("#B8861F",  "#E1B12C")   # dourado
_ACCENT_B   = ("#1B4F8A",  "#2D7DD2")   # azul
_BORDER     = ("#DDE3EE",  "#22273A")
_BTN_ADD    = ("#1B7A4C",  "#059669")   # verde
_BTN_DEL    = ("#B91C1C",  "#DC2626")   # vermelho

ICONES = {
    "marca":     "🏷️",
    "tipo_peca": "👕",
    "tecido":    "🧵",
    "corte":     "✂️",
    "cor":       "🎨",
}


def _hex(t):
    mode = ctk.get_appearance_mode()
    return t[1] if mode != "Light" else t[0]


class TelaConfiguracoes(ctk.CTkFrame):
    """Painel de configurações de atributos com abas CTk premium."""

    CATEGORIAS = [
        ("Marcas",        "marca"),
        ("Tipos de Peça", "tipo_peca"),
        ("Tecidos",       "tecido"),
        ("Cortes",        "corte"),
        ("Cores",         "cor"),
    ]

    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color=_BG_WINDOW)
        self.controller  = controller
        self._aba_ativa  = self.CATEGORIAS[0][1]
        self._btn_abas   = {}
        self._tabelas    = {}
        self._frames_aba = {}
        self._abas_montadas = set()
        self._dados_alterados = {cat: True for _, cat in self.CATEGORIAS}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construir_interface()

    # ══════════════════════════════════════════════════════════════════════
    # DESTRUIÇÃO SEGURA
    # ══════════════════════════════════════════════════════════════════════

    def destroy(self):
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        super().destroy()

    # ══════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════

    def _construir_interface(self):
        self._construir_cabecalho()
        self._construir_corpo()

    # ── Cabeçalho ──────────────────────────────────────────────────────

    def _construir_cabecalho(self):
        frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 0))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="⚙️  Painel de Atributos",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            frame,
            text="Gerencie as opções disponíveis nos formulários de cadastro",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=_FG_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Divider
        ctk.CTkFrame(
            self, height=1, fg_color=_BORDER, corner_radius=0
        ).grid(row=0, column=0, sticky="ews", padx=28, pady=(62, 0))

    # ── Corpo: barra de abas + conteúdo ────────────────────────────────

    def _construir_corpo(self):
        frame_corpo = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        frame_corpo.grid(row=1, column=0, sticky="nsew", padx=28, pady=16)
        frame_corpo.grid_columnconfigure(1, weight=1)
        frame_corpo.grid_rowconfigure(0, weight=1)

        self._construir_barra_abas(frame_corpo)

        self._area_conteudo = ctk.CTkScrollableFrame(
            frame_corpo, fg_color=_BG_CARD,
            corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        self._area_conteudo.grid(row=0, column=1, sticky="nsew")
        self._area_conteudo.grid_columnconfigure(0, weight=1)
        self._area_conteudo.grid_rowconfigure(1, weight=1)

        for titulo, categoria in self.CATEGORIAS:
            frame_aba = ctk.CTkFrame(
                self._area_conteudo,
                fg_color="transparent",
                corner_radius=0,
            )
            frame_aba.grid(row=0, column=0, rowspan=2, sticky="nsew")
            frame_aba.grid_columnconfigure(0, weight=1)
            frame_aba.grid_rowconfigure(1, weight=1)
            self._frames_aba[categoria] = frame_aba

        self._exibir_aba(self._aba_ativa)

    def _construir_barra_abas(self, parent):
        outer = ctk.CTkScrollableFrame(
            parent, fg_color=_BG_CARD,
            corner_radius=12,
            border_width=1, border_color=_BORDER,
            width=180,
        )
        outer.grid(row=0, column=0, sticky="ns", padx=(0, 12))

        ctk.CTkLabel(
            outer,
            text="CATEGORIAS",
            font=ctk.CTkFont(family="Segoe UI", size=8, weight="bold"),
            text_color=_FG_MUTED, anchor="w",
        ).pack(anchor="w", padx=16, pady=(16, 8))

        ctk.CTkFrame(outer, height=1, fg_color=_BORDER, corner_radius=0).pack(
            fill="x", padx=12, pady=(0, 8)
        )

        for titulo, categoria in self.CATEGORIAS:
            icon = ICONES.get(categoria, "📁")
            self._criar_btn_aba(outer, titulo, categoria, icon)

    def _criar_btn_aba(self, parent, titulo, categoria, icon):
        container = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=8)
        container.pack(fill="x", padx=8, pady=2)

        barra = ctk.CTkFrame(container, fg_color="transparent", width=3, corner_radius=2)
        barra.pack(side="left", fill="y")

        btn_frame = ctk.CTkFrame(container, fg_color="transparent", corner_radius=8)
        btn_frame.pack(side="left", fill="x", expand=True)

        icon_lbl = ctk.CTkLabel(
            btn_frame, text=icon,
            font=ctk.CTkFont(size=16),
            text_color=_FG_MUTED,
            fg_color="transparent",
        )
        icon_lbl.pack(anchor="w", padx=(10, 0), pady=(8, 0))

        txt_lbl = ctk.CTkLabel(
            btn_frame, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=_FG_MUTED,
            fg_color="transparent",
            anchor="w",
        )
        txt_lbl.pack(anchor="w", padx=10, pady=(0, 8))

        def _click(e, c=categoria):
            self._exibir_aba(c)

        def _enter(e, cf=container, bf=btn_frame, il=icon_lbl, tl=txt_lbl):
            if self._aba_ativa != categoria:
                for w in (cf, bf, il, tl):
                    try:
                        w.configure(fg_color=_BG_HOVER)
                    except Exception:
                        pass

        def _leave(e, cf=container, bf=btn_frame, il=icon_lbl, tl=txt_lbl):
            if self._aba_ativa != categoria:
                for w in (cf, bf, il, tl):
                    try:
                        w.configure(fg_color="transparent")
                    except Exception:
                        pass

        for w in (container, btn_frame, icon_lbl, txt_lbl):
            w.bind("<Button-1>", _click)
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)

        self._btn_abas[categoria] = {
            "container": container,
            "btn_frame": btn_frame,
            "icon":      icon_lbl,
            "text":      txt_lbl,
            "barra":     barra,
        }

    def _exibir_aba(self, categoria):
        """Troca a aba visível e atualiza o estado dos botões."""
        self._aba_ativa = categoria

        if categoria not in self._abas_montadas:
            self._montar_aba(self._frames_aba[categoria], categoria)
            self._abas_montadas.add(categoria)

        for cat, frame in self._frames_aba.items():
            if frame.winfo_exists():
                if cat == categoria:
                    frame.tkraise()
                else:
                    frame.lower()

        for cat, widgets in self._btn_abas.items():
            ativo = (cat == categoria)
            for w in (widgets["container"], widgets["btn_frame"],
                      widgets["icon"], widgets["text"]):
                try:
                    w.configure(fg_color=("#E8ECF4", "#1E3A5F") if ativo else "transparent")
                except Exception:
                    pass
            try:
                widgets["icon"].configure(
                    text_color=_ACCENT_G if ativo else _FG_MUTED
                )
                widgets["text"].configure(
                    text_color=_ACCENT_G if ativo else _FG_MUTED
                )
                widgets["barra"].configure(
                    fg_color=_ACCENT_G if ativo else "transparent"
                )
            except Exception:
                pass

        if categoria in self._tabelas and self._dados_alterados.get(categoria, True):
            self._recarregar_tabela(self._tabelas[categoria], categoria)
            self._dados_alterados[categoria] = False

    # ══════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DE CADA ABA
    # ══════════════════════════════════════════════════════════════════════

    def _montar_aba(self, frame, categoria):
        """Monta o layout de uma aba: campo de adição + tabela."""
        icon  = ICONES.get(categoria, "📁")
        nomes = {"marca": "Marcas", "tipo_peca": "Tipos de Peça",
                 "tecido": "Tecidos", "corte": "Cortes", "cor": "Cores"}
        titulo_aba = nomes.get(categoria, categoria.title())

        # ── Cabeçalho da aba
        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text=f"{icon}  {titulo_aba}",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_FG_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # ── Linha de adição (canto direito do header)
        linha_add = ctk.CTkFrame(frame, fg_color="transparent")
        linha_add.grid(row=0, column=0, sticky="se", padx=20, pady=(16, 0))

        entry_novo = ctk.CTkEntry(
            linha_add,
            placeholder_text=f"Novo(a) {titulo_aba.lower().rstrip('s')}...",
            width=220, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=_BG_WINDOW, border_color=_BORDER,
            text_color=_FG_PRIMARY, corner_radius=8,
        )
        entry_novo.pack(side="left", padx=(0, 8))

        lbl_status = ctk.CTkLabel(
            linha_add, text="",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=("#059669", "#34D399"),
            width=200,
        )

        def _salvar(e=None):
            nome = entry_novo.get().strip()
            sucesso, msg = config_ctrl.adicionar_atributo(categoria, nome)
            if sucesso:
                entry_novo.delete(0, tk.END)
                self._dados_alterados[categoria] = True
                self._recarregar_tabela(self._tabelas[categoria], categoria)
                self._dados_alterados[categoria] = False
                lbl_status.configure(
                    text=f"✅  {msg}",
                    text_color=("#059669", "#34D399")
                )
            else:
                lbl_status.configure(
                    text=f"❌  {msg}",
                    text_color=("#DC2626", "#F87171")
                )
            self.after(3000, lambda: lbl_status.configure(text=""))

        ctk.CTkButton(
            linha_add,
            text="Adicionar  ➕",
            command=_salvar,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            fg_color=_BTN_ADD,
            hover_color=("#155F3C", "#047857"),
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=8, height=34,
        ).pack(side="left")

        lbl_status.pack(side="left", padx=10)
        entry_novo.bind("<Return>", _salvar)

        # ── Divider
        ctk.CTkFrame(
            frame, height=1, fg_color=_BORDER, corner_radius=0
        ).grid(row=0, column=0, sticky="ews", padx=16, pady=(68, 0))

        # ── Tabela (Treeview estilizado tema escuro)
        frame_tv = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        frame_tv.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))
        frame_tv.grid_columnconfigure(0, weight=1)
        frame_tv.grid_rowconfigure(0, weight=1)

        bg_tv = _hex(_BG_CARD)
        s = ttk.Style()
        s.configure(
            f"Cfg_{categoria}.Treeview",
            background=bg_tv,
            fieldbackground=bg_tv,
            foreground=_hex(_FG_PRIMARY),
            rowheight=32,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        s.configure(
            f"Cfg_{categoria}.Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background=_hex(_BG_HOVER),
            foreground=_hex(_ACCENT_G),
            relief="flat",
        )
        s.map(
            f"Cfg_{categoria}.Treeview",
            background=[("selected", _hex(_ACCENT_B))],
            foreground=[("selected", "#FFFFFF")],
        )
        s.configure(
            "Cfg.Vertical.TScrollbar",
            troughcolor=_hex(_BG_WINDOW),
            background=_hex(_ACCENT_B),
            arrowcolor=_hex(_FG_PRIMARY),
            relief="flat", borderwidth=0,
        )

        wrapper = tk.Frame(frame_tv, bg=bg_tv)
        wrapper.grid(row=0, column=0, sticky="nsew")

        colunas = ("ID", "Nome Cadastrado", "Acao")
        tabela = ttk.Treeview(
            wrapper,
            columns=colunas,
            show="headings",
            style=f"Cfg_{categoria}.Treeview",
        )
        tabela.heading("ID",              text="ID")
        tabela.heading("Nome Cadastrado", text="Nome Cadastrado")
        tabela.heading("Acao",            text="Duplo clique para excluir")
        tabela.column("ID",              width=55,  anchor="center")
        tabela.column("Nome Cadastrado", width=400, anchor="w")
        tabela.column("Acao",            width=220, anchor="center")

        tabela.tag_configure("par",   background=_hex(_BG_CARD))
        tabela.tag_configure("impar", background=_hex(_BG_HOVER))

        scroll = ttk.Scrollbar(wrapper, orient="vertical", command=tabela.yview)
        tabela.configure(yscrollcommand=scroll.set)
        tabela.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        tabela.bind("<Double-1>", lambda e, t=tabela, c=categoria: self._excluir_selecionado(t, c))

        self._tabelas[categoria] = tabela
        self._recarregar_tabela(tabela, categoria)

    # ══════════════════════════════════════════════════════════════════════
    # LÓGICA DE DADOS (preservada integralmente)
    # ══════════════════════════════════════════════════════════════════════

    def _recarregar_tabela(self, tabela: ttk.Treeview, categoria: str):
        """Limpa e recarrega os dados da tabela a partir do controller."""
        for item in tabela.get_children():
            tabela.delete(item)
        itens = config_ctrl.listar_atributos(categoria)
        for i, item in enumerate(itens):
            tag = "par" if i % 2 == 0 else "impar"
            tabela.insert(
                "", tk.END,
                values=(item["id"], item["nome"], "🖱️  Duplo clique para excluir"),
                tags=(tag,),
            )

    def _excluir_selecionado(self, tabela: ttk.Treeview, categoria: str):
        """Exclui o item selecionado na tabela após confirmação."""
        selecao = tabela.selection()
        if not selecao:
            return
        valores = tabela.item(selecao[0])["values"]
        atributo_id   = valores[0]
        atributo_nome = valores[1]
        confirmar = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja remover '{atributo_nome}' permanentemente?\n\n"
            "Isso não afeta produtos já cadastrados."
        )
        if confirmar:
            sucesso, msg = config_ctrl.excluir_atributo(atributo_id)
            if sucesso:
                self._dados_alterados[categoria] = True
                self._recarregar_tabela(tabela, categoria)
                self._dados_alterados[categoria] = False
            else:
                messagebox.showerror("Erro", msg)


