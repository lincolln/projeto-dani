"""
tela_dashboard.py — Painel de Business Intelligence Unificado (Redesign Premium)
Exibe cards KPI financeiros e gráficos Matplotlib com tema escuro unificado.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports adiados (lazy loading)

from controllers import estoque_ctrl, config_ctrl
from controllers.dash_ctrl import DashboardController

# ── Paleta Premium (herdada do tema escuro do app) ─────────────────────────────
C = {
    "bg":          "#0F1117",   # fundo principal
    "panel":       "#16191F",   # painéis, cards, sidebar
    "border":      "#22273A",   # bordas e hover
    "border_lite": "#2C3249",   # borda mais suave
    "accent":      "#E1B12C",   # dourado — ativo / destaque
    "accent2":     "#1E3A5F",   # azul executivo
    "fg":          "#F0F2F8",   # texto principal
    "fg_muted":    "#8A8FA8",   # texto secundário
    "green":       "#1DB954",   # recebimentos
    "red":         "#E74C3C",   # gastos
    "blue":        "#4A90D9",   # lucro
    "plot_bg":     "#16191F",   # fundo do gráfico
    "plot_ax":     "#1C2233",   # área do eixo
    "plot_grid":   "#2C3249",   # grid
}

# Cores de cada visão de gráfico (alinhadas com a paleta)
VISAO_CORES = {
    "LINHA":  {"cor": C["accent"],  "icon": "📈", "label": "Histórico Temporal"},
    "ROSCA":  {"cor": C["green"],   "icon": "🍩", "label": "Raio-X do Estoque"},
    "MARCA":  {"cor": C["blue"],    "icon": "🏷️", "label": "Por Marca"},
    "TIPO":   {"cor": "#E67E22",    "icon": "👕", "label": "Por Tipo de Peça"},
    "CORTE":  {"cor": "#9B59B6",    "icon": "✂️", "label": "Por Corte"},
    "TECIDO": {"cor": "#1ABC9C",    "icon": "🧵", "label": "Por Tecido"},
}

# Cores para o gráfico de rosca
ROSCA_CORES = ["#E1B12C", "#4A90D9", "#1DB954", "#E67E22", "#9B59B6", "#1ABC9C"]

# A configuração do Matplotlib foi movida para carregar_dados_e_renderizar_dashboard

def _hex_to_rgb(hex_color):
    """Converte cor hex para tupla RGB 0–1."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


class TelaDashboard(tk.Frame):
    """Dashboard BI premium com cartões KPI e visualizações alternáveis."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["bg"])
        self.controller = controller
        self.root = self
        self.dash_db = DashboardController()
        self.visao_atual = "LINHA"
        self._btn_visao = {}       # chave → tk.Frame (container do botão)
        self._clock_id = None      # referência para cancelar after()

        self._montar_cabecalho()
        self._montar_filtros()
        self._montar_cards_kpi()
        self._montar_conteudo_principal()
        self._iniciar_relogio()
        self.carregar_dados_e_renderizar_dashboard()

    # ══════════════════════════════════════════════════════════════════
    # DESTRUIÇÃO LIMPA
    # ══════════════════════════════════════════════════════════════════
    def destroy(self):
        if self._clock_id:
            self.after_cancel(self._clock_id)
        super().destroy()

    # ══════════════════════════════════════════════════════════════════
    # 1. CABEÇALHO
    # ══════════════════════════════════════════════════════════════════
    def _montar_cabecalho(self):
        frame = tk.Frame(self.root, bg=C["bg"])
        frame.pack(fill="x", padx=28, pady=(18, 6))

        # Lado esquerdo — título
        esq = tk.Frame(frame, bg=C["bg"])
        esq.pack(side="left")

        tk.Label(
            esq, text="Painel Executivo  ·  Business Intelligence",
            font=("Segoe UI", 20, "bold"), bg=C["bg"], fg=C["fg"]
        ).pack(anchor="w")

        tk.Label(
            esq, text="Kanemberg Multimarcas — Visão Estratégica de Negócio",
            font=("Segoe UI", 10), bg=C["bg"], fg=C["fg_muted"]
        ).pack(anchor="w")

        # Lado direito — data/hora ao vivo
        dir_ = tk.Frame(frame, bg=C["panel"], padx=14, pady=8)
        dir_.pack(side="right")
        self.lbl_relogio = tk.Label(
            dir_, text="", font=("Segoe UI", 11, "bold"),
            bg=C["panel"], fg=C["accent"]
        )
        self.lbl_relogio.pack()
        self.lbl_data = tk.Label(
            dir_, text="", font=("Segoe UI", 9),
            bg=C["panel"], fg=C["fg_muted"]
        )
        self.lbl_data.pack()

        # Divider
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x", padx=28, pady=(0, 10))

    def _iniciar_relogio(self):
        if not self.winfo_exists():
            return
        agora = datetime.now()
        self.lbl_relogio.config(text=agora.strftime("%H:%M:%S"))
        _DIAS_PT = {0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira', 3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'}
        _MESES_PT = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
        dia_nome = _DIAS_PT[agora.weekday()]
        mes_nome = _MESES_PT[agora.month]
        self.lbl_data.config(text=f"{dia_nome}, {agora.day} de {mes_nome} de {agora.year}")
        self._clock_id = self.after(1000, self._iniciar_relogio)

    # ══════════════════════════════════════════════════════════════════
    # 2. BARRA DE FILTROS
    # ══════════════════════════════════════════════════════════════════
    def _montar_filtros(self):
        outer = tk.Frame(self.root, bg=C["border"], pady=1)
        outer.pack(fill="x", padx=28, pady=(0, 12))

        frame = tk.Frame(outer, bg=C["panel"])
        frame.pack(fill="x")

        row = tk.Frame(frame, bg=C["panel"])
        row.pack(fill="x", padx=16, pady=10)

        def _combo(parent, label, values, width=11):
            tk.Label(
                parent, text=label, font=("Segoe UI", 8, "bold"),
                bg=C["panel"], fg=C["fg_muted"]
            ).pack(side="left", padx=(0, 3))
            cb = ttk.Combobox(parent, values=values, width=width,
                              font=("Segoe UI", 9), state="readonly")
            cb.pack(side="left", padx=(0, 12))
            return cb

        self.combo_filtro_tipo   = _combo(row, "TIPO/PEÇA",  ["TODOS"]  + config_ctrl.listar_nomes("tipo_peca"))
        self.combo_filtro_tipo.set("TODOS")

        self.combo_filtro_marca  = _combo(row, "MARCA",      ["TODAS"]  + config_ctrl.listar_nomes("marca"))
        self.combo_filtro_marca.set("TODAS")

        self.combo_filtro_tecido = _combo(row, "TECIDO",     ["TODOS"]  + config_ctrl.listar_nomes("tecido"))
        self.combo_filtro_tecido.set("TODOS")

        self.combo_filtro_corte  = _combo(row, "CORTE",      ["TODOS"]  + config_ctrl.listar_nomes("corte"))
        self.combo_filtro_corte.set("TODOS")

        self.combo_filtro_cor    = _combo(row, "COR",        ["TODAS"]  + config_ctrl.listar_nomes("cor"))
        self.combo_filtro_cor.set("TODAS")

        self.combo_escala_tempo  = _combo(row, "PERÍODO",    ["Diário", "Semanal", "Mensal"], width=9)
        self.combo_escala_tempo.set("Semanal")

        # Botão Filtrar — estilo premium
        btn = tk.Button(
            row, text="⟳  Aplicar Filtros",
            command=self.carregar_dados_e_renderizar_dashboard,
            font=("Segoe UI", 9, "bold"),
            bg=C["accent"], fg="#0F1117",
            relief="flat", bd=0,
            padx=14, pady=5, cursor="hand2",
            activebackground="#F5C842", activeforeground="#0F1117"
        )
        btn.pack(side="left", padx=(4, 0))

    # ══════════════════════════════════════════════════════════════════
    # 3. CARDS KPI
    # ══════════════════════════════════════════════════════════════════
    def _montar_cards_kpi(self):
        self.frame_cards = tk.Frame(self.root, bg=C["bg"])
        self.frame_cards.pack(fill="x", padx=28, pady=(0, 12))
        self.frame_cards.columnconfigure(0, weight=1, uniform="kpi")
        self.frame_cards.columnconfigure(1, weight=1, uniform="kpi")
        self.frame_cards.columnconfigure(2, weight=1, uniform="kpi")

        specs = [
            ("💰", "Recebimentos",         "Faturamento Bruto Total",  C["green"],  "lbl_card_recebido"),
            ("💸", "Gastos com Roupas",     "Custo de Compra",          C["red"],    "lbl_card_gasto"),
            ("📊", "Lucro Real Líquido",    "Receita − Custo",          C["blue"],   "lbl_card_lucro"),
        ]

        for col, (icon, titulo, subtitulo, cor, attr) in enumerate(specs):
            pad_l = (0, 8) if col == 0 else (4, 4) if col == 1 else (8, 0)

            # Container externo (borda colorida no topo)
            outer = tk.Frame(self.frame_cards, bg=cor, pady=3)
            outer.grid(row=0, column=col, padx=pad_l, sticky="nsew")

            # Painel interno escuro
            inner = tk.Frame(outer, bg=C["panel"], padx=20, pady=16)
            inner.pack(fill="both", expand=True)

            # Cabeçalho do card: ícone + título
            top = tk.Frame(inner, bg=C["panel"])
            top.pack(fill="x")

            tk.Label(top, text=icon, font=("Segoe UI", 18),
                     bg=C["panel"], fg=cor).pack(side="left", padx=(0, 8))

            info = tk.Frame(top, bg=C["panel"])
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=titulo, font=("Segoe UI", 9, "bold"),
                     bg=C["panel"], fg=C["fg"]).pack(anchor="w")
            tk.Label(info, text=subtitulo, font=("Segoe UI", 8),
                     bg=C["panel"], fg=C["fg_muted"]).pack(anchor="w")

            # Divider
            tk.Frame(inner, bg=C["border"], height=1).pack(fill="x", pady=(10, 8))

            # Valor
            lbl_valor = tk.Label(
                inner, text="R$ 0,00",
                font=("Segoe UI", 22, "bold"),
                bg=C["panel"], fg=cor
            )
            lbl_valor.pack(anchor="w")

            setattr(self, attr, lbl_valor)

    # ══════════════════════════════════════════════════════════════════
    # 4. CONTEÚDO PRINCIPAL: MENU LATERAL + GRÁFICO
    # ══════════════════════════════════════════════════════════════════
    def _montar_conteudo_principal(self):
        self.frame_conteudo = tk.Frame(self.root, bg=C["bg"])
        self.frame_conteudo.pack(fill="both", expand=True, padx=28, pady=(0, 16))

        self._montar_menu_lateral()
        self._montar_container_grafico()

    def _montar_menu_lateral(self):
        # Painel lateral
        outer = tk.Frame(self.frame_conteudo, bg=C["border"], padx=1, pady=1)
        outer.pack(side="left", fill="y", padx=(0, 12))

        panel = tk.Frame(outer, bg=C["panel"], width=170)
        panel.pack(fill="both", expand=True)
        panel.pack_propagate(False)

        tk.Label(
            panel, text="VISUALIZAÇÕES",
            font=("Segoe UI", 8, "bold"),
            bg=C["panel"], fg=C["fg_muted"]
        ).pack(anchor="w", padx=16, pady=(14, 8))

        for chave, meta in VISAO_CORES.items():
            self._criar_btn_visao(panel, chave, meta["icon"], meta["label"], meta["cor"])

    def _criar_btn_visao(self, parent, chave, icon, label, cor_acento):
        """Cria um botão de visão com efeito hover e destaque ao ativo."""
        container = tk.Frame(parent, bg=C["panel"], cursor="hand2")
        container.pack(fill="x", pady=1)

        # Barra lateral de cor (indicador ativo — aparece depois)
        barra = tk.Frame(container, bg=C["panel"], width=3)
        barra.pack(side="left", fill="y")

        # Conteúdo do botão
        btn_inner = tk.Frame(container, bg=C["panel"], padx=10, pady=10)
        btn_inner.pack(side="left", fill="x", expand=True)

        icon_lbl = tk.Label(btn_inner, text=icon, font=("Segoe UI", 14),
                            bg=C["panel"], fg=C["fg_muted"])
        icon_lbl.pack(anchor="w")

        txt_lbl = tk.Label(btn_inner, text=label, font=("Segoe UI", 9, "bold"),
                           bg=C["panel"], fg=C["fg_muted"])
        txt_lbl.pack(anchor="w")

        # Hover
        def _on_enter(e, c=container, bi=btn_inner, il=icon_lbl, tl=txt_lbl):
            if self.visao_atual != chave:
                for w in (c, bi, il, tl): w.config(bg=C["border"])

        def _on_leave(e, c=container, bi=btn_inner, il=icon_lbl, tl=txt_lbl):
            if self.visao_atual != chave:
                for w in (c, bi, il, tl): w.config(bg=C["panel"])

        def _click(e, k=chave):
            self.mudar_visao(k)

        for widget in (container, btn_inner, icon_lbl, txt_lbl):
            widget.bind("<Enter>", _on_enter)
            widget.bind("<Leave>", _on_leave)
            widget.bind("<Button-1>", _click)

        self._btn_visao[chave] = {
            "container": container,
            "inner": btn_inner,
            "icon": icon_lbl,
            "text": txt_lbl,
            "barra": barra,
            "cor": cor_acento,
        }

    def _atualizar_estado_botoes(self):
        """Aplica destaque ao botão da visão ativa e reset nos demais."""
        for chave, widgets in self._btn_visao.items():
            ativo = (chave == self.visao_atual)
            bg_btn  = C["accent2"] if ativo else C["panel"]
            fg_icon = VISAO_CORES[chave]["cor"] if ativo else C["fg_muted"]
            fg_txt  = C["accent"] if ativo else C["fg_muted"]
            bg_barra = VISAO_CORES[chave]["cor"] if ativo else C["panel"]

            for w in (widgets["container"], widgets["inner"],
                      widgets["icon"], widgets["text"]):
                w.config(bg=bg_btn)
            widgets["icon"].config(fg=fg_icon)
            widgets["text"].config(fg=fg_txt)
            widgets["barra"].config(bg=bg_barra)

    def _montar_container_grafico(self):
        outer = tk.Frame(self.frame_conteudo, bg=C["border"], padx=1, pady=1)
        outer.pack(side="right", fill="both", expand=True)
        self.frame_grafico_principal = tk.Frame(outer, bg=C["plot_bg"])
        self.frame_grafico_principal.pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════════════
    # 5. LÓGICA DE TROCA DE VISÃO
    # ══════════════════════════════════════════════════════════════════
    def mudar_visao(self, nova_visao):
        self.visao_atual = nova_visao
        self._atualizar_estado_botoes()
        self.carregar_dados_e_renderizar_dashboard()

    # ══════════════════════════════════════════════════════════════════
    # 6. CARREGAMENTO DE DADOS E RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════════════
    def carregar_dados_e_renderizar_dashboard(self):
        """Carrega dados e renderiza o gráfico da visão ativa com tema escuro."""
        import pandas as pd
        import matplotlib
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        if not hasattr(self, "_matplotlib_configurado"):
            matplotlib.use('Agg')
            matplotlib.rcParams.update({
                "font.family":        "Segoe UI",
                "axes.spines.top":    False,
                "axes.spines.right":  False,
                "axes.spines.left":   False,
                "axes.spines.bottom": False,
                "axes.grid":          True,
                "grid.alpha":         0.15,
                "grid.color":         C["plot_grid"],
                "text.color":         C["fg"],
                "axes.labelcolor":    C["fg_muted"],
                "xtick.color":        C["fg_muted"],
                "ytick.color":        C["fg_muted"],
                "axes.titlecolor":    C["fg"],
            })
            self._matplotlib_configurado = True

        # Não destrói mais os filhos, apenas limpa a figura se necessário

        # Busca dados filtrados
        df_filtrado = self.dash_db.obter_dados_vendas_filtrados(
            self.combo_filtro_tipo.get()   if hasattr(self, "combo_filtro_tipo")   else "TODOS",
            self.combo_filtro_marca.get()  if hasattr(self, "combo_filtro_marca")  else "TODAS",
            self.combo_filtro_tecido.get() if hasattr(self, "combo_filtro_tecido") else "TODOS",
            self.combo_filtro_corte.get()  if hasattr(self, "combo_filtro_corte")  else "TODOS",
            self.combo_filtro_cor.get()    if hasattr(self, "combo_filtro_cor")    else "TODAS",
        )

        # Atualiza cards KPI
        metricas = self.dash_db.calcular_metricas_financeiras(df_filtrado)
        if hasattr(self, "lbl_card_recebido"):
            self.lbl_card_recebido.config(text=f"R$ {metricas['faturamento']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        if hasattr(self, "lbl_card_gasto"):
            self.lbl_card_gasto.config(text=f"R$ {metricas['gastos_custo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        if hasattr(self, "lbl_card_lucro"):
            self.lbl_card_lucro.config(text=f"R$ {metricas['lucro_real']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Atualiza destaque do botão ativo
        self._atualizar_estado_botoes()

        # Reutiliza ou cria figura Matplotlib
        if not hasattr(self, "_fig"):
            self._fig, self._ax = plt.subplots(figsize=(9, 4.8))
            self._fig.patch.set_facecolor(C["plot_bg"])
            self._canvas = FigureCanvasTkAgg(self._fig, master=self.frame_grafico_principal)
            self._canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            self._ax.clear()

        fig = self._fig
        ax = self._ax
        ax.set_facecolor(C["plot_ax"])

        meta = VISAO_CORES[self.visao_atual]

        # ── LINHA ────────────────────────────────────────────────────
        if self.visao_atual == "LINHA":
            escala_map = {"Diário": "D", "Semanal": "W", "Mensal": "M"}
            escala = escala_map.get(
                self.combo_escala_tempo.get() if hasattr(self, "combo_escala_tempo") else "Semanal",
                "W"
            )
            dados = self.dash_db.processar_historico_temporal(df_filtrado, escala)
            if not dados.empty:
                xs = list(range(len(dados)))
                ys = dados.values

                # Área abaixo da linha (gradiente simulado)
                ax.fill_between(xs, ys, alpha=0.12, color=meta["cor"])
                ax.plot(xs, ys, marker="o", color=meta["cor"],
                        linewidth=2.5, markersize=6,
                        markerfacecolor=C["plot_bg"], markeredgewidth=2)

                ax.set_xticks(xs)
                ax.set_xticklabels(dados.index.strftime("%d/%m"), rotation=30,
                                   fontsize=8, ha="right")
                ax.set_title(
                    f"Evolução de Faturamento  ·  {self.combo_escala_tempo.get() if hasattr(self, 'combo_escala_tempo') else 'Semanal'}",
                    fontsize=13, fontweight="bold", pad=14
                )
                ax.grid(True, linestyle=":", alpha=0.2, color=C["plot_grid"])
            else:
                _sem_dados(ax, "Nenhum dado no período selecionado")

        # ── ROSCA ────────────────────────────────────────────────────
        elif self.visao_atual == "ROSCA":
            dados = self.dash_db.processar_dados_estoque_rosca()
            ax.set_facecolor(C["plot_bg"])
            if not dados.empty:
                wedges, texts, autotexts = ax.pie(
                    dados.values, labels=None,
                    autopct="%1.1f%%", startangle=90,
                    pctdistance=0.78,
                    colors=ROSCA_CORES[:len(dados)],
                    wedgeprops={"linewidth": 2, "edgecolor": C["plot_bg"]}
                )
                plt.setp(autotexts, size=9, weight="bold", color=C["fg"])
                # Círculo central (donut)
                ax.add_artist(plt.Circle((0, 0), 0.58, fc=C["plot_bg"]))
                # Texto central
                ax.text(0, 0, "ESTOQUE", ha="center", va="center",
                        fontsize=10, fontweight="bold", color=C["fg_muted"])
                # Legenda manual
                patches = [mpatches.Patch(color=ROSCA_CORES[i], label=dados.index[i])
                           for i in range(len(dados))]
                ax.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5, -0.05),
                          ncol=3, frameon=False, fontsize=8,
                          labelcolor=C["fg"])
                ax.set_title("Distribuição do Estoque por Categoria",
                             fontsize=13, fontweight="bold", pad=14)
            else:
                _sem_dados(ax, "Estoque vazio")

        # ── MARCA, TIPO, CORTE, TECIDO (barras horizontais) ──────────
        elif self.visao_atual in ("MARCA", "TIPO", "CORTE", "TECIDO"):
            mapa_func = {
                "MARCA":  self.dash_db.processar_demanda_por_marca,
                "TIPO":   self.dash_db.processar_demanda_por_tipo,
                "CORTE":  self.dash_db.processar_demanda_por_corte,
                "TECIDO": self.dash_db.processar_demanda_por_tecido,
            }
            titulos = {
                "MARCA":  "Faturamento e Saídas por Marca",
                "TIPO":   "Ranking de Vendas por Tipo de Peça",
                "CORTE":  "Ranking de Vendas por Tipo de Corte",
                "TECIDO": "Ranking de Vendas por Tipo de Tecido",
            }
            dados = mapa_func[self.visao_atual](df_filtrado)
            cor   = meta["cor"]
            if not dados.empty:
                ys = list(range(len(dados)))
                bars = ax.barh(ys, dados.values, height=0.55,
                               color=cor, alpha=0.85,
                               linewidth=0)

                # Rótulo de valor dentro/fora da barra
                max_val = max(dados.values) if len(dados.values) else 1
                max_val = max(max_val, 1)
                for bar, val in zip(bars, dados.values):
                    x_pos = bar.get_width() - max_val * 0.02
                    ha = "right" if bar.get_width() > max_val * 0.15 else "left"
                    x_pos = bar.get_width() + max_val * 0.01 if ha == "left" else x_pos
                    ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                            f"{int(val)}", va="center", ha=ha,
                            fontsize=8, fontweight="bold",
                            color=C["fg"] if ha == "right" else cor)

                ax.set_yticks(ys)
                ax.set_yticklabels(dados.index, fontsize=9)
                ax.set_xlabel("Quantidade Vendida", fontsize=9, labelpad=8)
                ax.grid(axis="x", linestyle=":", alpha=0.2, color=C["plot_grid"])
                ax.set_title(titulos[self.visao_atual],
                             fontsize=13, fontweight="bold", pad=14)
                ax.invert_yaxis()
            else:
                _sem_dados(ax, f"Sem dados de {meta['label']}")

        # Ajuste final do layout e injeção no Tkinter
        fig.tight_layout(pad=2.0)
        self._canvas.draw_idle()


# ──────────────────────────────────────────────────────────────────────────────
# UTILITÁRIO: mensagem de "sem dados"
# ──────────────────────────────────────────────────────────────────────────────
def _sem_dados(ax, mensagem="Sem dados disponíveis"):
    ax.set_facecolor(C["plot_bg"])
    ax.text(0.5, 0.5, mensagem,
            ha="center", va="center",
            fontsize=12, color=C["fg_muted"],
            transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])
