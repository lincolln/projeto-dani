"""
tela_principal.py — Janela raiz e estrutura base do Sistema Kanemberg
Versão definitiva CustomTkinter 5.x com zona de segurança retrocompatível.

Diretivas de estabilidade:
  ① self.area_conteudo é obrigatoriamente um tk.Frame clássico (NÃO CTkFrame)
    → zona de segurança que permite que sub-telas tk.Frame/ctk.CTkFrame
      coexistam sem travar o mainloop por conflito de herança.
  ② Logo carregada exclusivamente de "logo_kanemberg.png" via ctk.CTkImage
    size=(70,70) preservando canal alpha.
  ③ Inicia em Modo Escuro nativo (set_appearance_mode("dark"), "dark-blue").
  ④ CTkSwitch no topo da sidebar para alternar tema dinamicamente.
  ⑤ Sidebar CTkFrame fixa em 240px; área de conteúdo ocupa o restante (weight=1).
"""

import os
import sys
import time
import ctypes
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from PIL import Image

# ── Configuração global ANTES de qualquer instância ─────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Garante que o diretório raiz do projeto esteja no path
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

# Força ícone nativo na barra de tarefas do Windows
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "kanemberg.multimarcas.gestao.v2"
    )
except Exception:
    pass

# ── Constantes de layout ─────────────────────────────────────────────────────
SIDEBAR_W      = 240
NAV_BTN_H      = 44
LOGO_SIZE      = (70, 70)
LOGO_FILENAME  = "logo_kanemberg.png"   # nome oficial e definitivo

# ── Paletas (claro, escuro — Tema Slate Dark Mobile) ────────────────────────
DARK = {
    "bg_window":      "#0f172a",
    "bg_sidebar":     "#0b1120",
    "bg_hover":       "#1e293b",
    "accent":         "#3b82f6",    # azul primário mobile
    "accent2":        "#1e293b",    # slate card (fundo botão ativo)
    "fg_primary":     "#f8fafc",
    "fg_muted":       "#94a3b8",
    "divider":        "#334155",
    "btn_active_fg":  "#60a5fa",
}
LIGHT = {
    "bg_window":      "#F0F2F8",
    "bg_sidebar":     "#FFFFFF",
    "bg_hover":       "#E8ECF4",
    "accent":         "#2563eb",
    "accent2":        "#1B365D",
    "fg_primary":     "#1A1D2E",
    "fg_muted":       "#6B7280",
    "divider":        "#DDE3EE",
    "btn_active_fg":  "#FFFFFF",
}


class TelaPrincipal(ctk.CTk):
    """
    Janela raiz do Sistema Kanemberg.

    Arquitetura de dois painéis:
      • Coluna 0  →  CTkFrame sidebar (240px fixos, CTk puro)
      • Coluna 1  →  tk.Frame  área de conteúdo (expande com weight=1)
                     ↑ ZONA DE SEGURANÇA: tk.Frame clássico garante que
                       sub-telas (tk.Frame ou ctk.CTkFrame) se encaixem
                       sem conflito de mainloop.
    """

    def __init__(self):
        super().__init__()

        # ── Estado ──────────────────────────────────────────────────
        self._modo_escuro   = True
        self._tela_atual    = ""
        self._frame_atual   = None
        self._botoes_menu   = {}          # nome → CTkButton
        self._cache_telas   = {}

        # ── Bipe Global (Scanner USB) ────────────────────────────────
        self._bipe_buffer    = []       # acumula chars rápidos do scanner
        self._bipe_last_time = 0.0      # timestamp da última tecla
        self._BIPE_THRESHOLD = 0.05     # 50ms — abaixo disso é scanner
        self._BIPE_MIN_LEN   = 5        # mínimo de dígitos para considerar código
        self._BIPE_MAX_LEN   = 20       # máximo de chars no buffer

        # ── Configuração da janela ──────────────────────────────────
        self.title("Sistema de Gestão Kanemberg")
        self.geometry("1280x780")
        self.minsize(960, 660)

        # ── Motor de estilos TTK (Treeview / Combobox das sub-telas) ─
        self._style = ttk.Style(self)
        self._style.theme_use("clam")

        # ── Pipeline de inicialização ───────────────────────────────
        self._carregar_logo()
        self._montar_grid_raiz()
        self._montar_sidebar()
        self._montar_area_conteudo()   # ← tk.Frame puro (zona segura)
        self._sincronizar_ttk()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Bind global do scanner de código de barras
        self.bind("<Key>", self._capturar_bipe_global)

        # Tela inicial
        self.mostrar_tela("boas_vindas")

    # ════════════════════════════════════════════════════════════════
    # CARREGAMENTO DO LOGO
    # ════════════════════════════════════════════════════════════════

    def _carregar_logo(self):
        """
        Carrega a logo a partir do _MEIPASS (se for .exe) ou da pasta raiz (se script).
        Gera dois CTkImages (um para a sidebar, outro grande para a tela de boas-vindas).
        """
        def resource_path(relative_path):
            """Obtém o caminho absoluto para recursos empacotados pelo PyInstaller."""
            try:
                # PyInstaller cria uma pasta temporária em sys._MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = _RAIZ
            return os.path.join(base_path, relative_path)

        self._ctk_logo_sidebar  = None
        self._ctk_logo_welcome  = None
        self._ico_temp = os.path.join(_RAIZ, "_temp_logo.ico")

        caminho = resource_path(LOGO_FILENAME)
        if not os.path.exists(caminho):
            print(f"[Aviso] Imagem não encontrada: {caminho}")
            return

        try:
            img = Image.open(caminho).convert("RGBA")

            # Ícone da barra de tarefas
            img_ico = img.resize((32, 32), Image.Resampling.LANCZOS)
            img_ico.save(self._ico_temp, format="ICO", sizes=[(32, 32), (16, 16)])
            self.iconbitmap(self._ico_temp)

            # ① Logo da sidebar — 70×70 exatos, alpha preservado
            img_sb = img.resize(LOGO_SIZE, Image.Resampling.LANCZOS)
            self._ctk_logo_sidebar = ctk.CTkImage(
                light_image=img_sb,
                dark_image=img_sb,
                size=LOGO_SIZE,
            )

            # ② Logo da tela de boas-vindas — 280×280
            img_wl = img.resize((280, 280), Image.Resampling.LANCZOS)
            self._ctk_logo_welcome = ctk.CTkImage(
                light_image=img_wl,
                dark_image=img_wl,
                size=(280, 280),
            )

            print(f"[Logo] '{LOGO_FILENAME}' carregado com sucesso.")

        except Exception as e:
            print(f"[Logo] Erro ao carregar '{LOGO_FILENAME}': {e}")

    # ════════════════════════════════════════════════════════════════
    # GRID RAIZ
    # ════════════════════════════════════════════════════════════════

    def _montar_grid_raiz(self):
        """
        Coluna 0 = sidebar fixa (240px).
        Coluna 1 = conteúdo elástico (weight=1 → expande ao maximizar).
        """
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_W)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    # ════════════════════════════════════════════════════════════════
    # SIDEBAR (CTkFrame — theming nativo CTk)
    # ════════════════════════════════════════════════════════════════

    def _montar_sidebar(self):
        """Constrói a barra lateral premium com logo, switch de tema e navegação."""

        P = self._paleta()

        # Container principal da sidebar
        self.sidebar = ctk.CTkFrame(
            self,
            width=SIDEBAR_W,
            corner_radius=0,
            fg_color=P["bg_sidebar"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        # Linha 3 (nav) expande verticalmente
        self.sidebar.grid_rowconfigure(3, weight=1)

        # ── BLOCO 0: Logo + Identidade ──────────────────────────────
        frame_id = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        frame_id.grid(row=0, column=0, sticky="ew", pady=(20, 6))

        # Logo 70×70 com canal alpha
        self._lbl_logo = ctk.CTkLabel(
            frame_id,
            text="" if self._ctk_logo_sidebar else "🐅",
            image=self._ctk_logo_sidebar,
            font=ctk.CTkFont(size=32) if not self._ctk_logo_sidebar else ctk.CTkFont(size=1),
        )
        self._lbl_logo.pack(pady=(0, 6))

        self._lbl_marca = ctk.CTkLabel(
            frame_id,
            text="KANEMBERG",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=P["accent"],
        )
        self._lbl_marca.pack()

        self._lbl_submarca = ctk.CTkLabel(
            frame_id,
            text="Gestão Comercial",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=P["fg_muted"],
        )
        self._lbl_submarca.pack()

        # ── BLOCO 1: CTkSwitch de tema ──────────────────────────────
        frame_sw = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        frame_sw.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 4))

        ctk.CTkLabel(
            frame_sw, text="☀️",
            font=ctk.CTkFont(size=12),
            text_color=P["fg_muted"],
        ).pack(side="left")

        self._switch_tema = ctk.CTkSwitch(
            frame_sw,
            text="",
            width=46,
            command=self._alternar_tema,
            onvalue=True,
            offvalue=False,
            progress_color=P["accent2"],
            button_color=P["accent"],
            button_hover_color="#F5C842",
        )
        self._switch_tema.pack(side="left", padx=6)
        self._switch_tema.select()   # inicia ON = Modo Escuro

        ctk.CTkLabel(
            frame_sw, text="🌙",
            font=ctk.CTkFont(size=12),
            text_color=P["fg_muted"],
        ).pack(side="left")

        self._lbl_tema = ctk.CTkLabel(
            frame_sw,
            text="Modo Escuro",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=P["fg_muted"],
        )
        self._lbl_tema.pack(side="left", padx=(8, 0))

        # ── BLOCO 2: Separador decorativo ───────────────────────────
        self._sep_top = ctk.CTkFrame(
            self.sidebar, height=1, corner_radius=0, fg_color=P["divider"]
        )
        self._sep_top.grid(row=2, column=0, sticky="ew", padx=18, pady=(4, 8))

        # ── BLOCO 3: Botões de navegação ────────────────────────────
        frame_nav = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        frame_nav.grid(row=3, column=0, sticky="nsew", padx=0)
        frame_nav.grid_columnconfigure(0, weight=1)

        _nav = [
            ("estoque",   "📦   Estoque",         self._ir_estoque),
            ("cadastro",  "➕   Cadastrar",        self._ir_cadastro),
            ("venda",     "🛒   Nova Venda",       self._ir_venda),
            ("fiado",     "💳   Fiado",            self._ir_fiado),
            ("margens",   "📈   Saúde Margens",    self._ir_margens),
            ("dashboard", "📊   Dashboard",        self._ir_dashboard),
            ("config",    "⚙️    Configurações",   self._ir_config),
        ]

        for idx, (nome, texto, cmd) in enumerate(_nav):
            btn = ctk.CTkButton(
                frame_nav,
                text=texto,
                command=cmd,
                anchor="w",
                height=NAV_BTN_H,
                corner_radius=8,
                border_width=0,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color="transparent",
                text_color=P["fg_primary"],
                hover_color=P["bg_hover"],
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=10, pady=2)
            self._botoes_menu[nome] = btn

        # ── BLOCO 4: Rodapé ─────────────────────────────────────────
        self._sep_bot = ctk.CTkFrame(
            self.sidebar, height=1, corner_radius=0, fg_color=P["divider"]
        )
        self._sep_bot.grid(row=4, column=0, sticky="ew", padx=18, pady=(6, 4))

        self._lbl_versao = ctk.CTkLabel(
            self.sidebar,
            text="v2.0  •  Kanemberg Multimarcas",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=P["fg_muted"],
        )
        self._lbl_versao.grid(row=5, column=0, sticky="ew", padx=14, pady=(2, 12))

    # ════════════════════════════════════════════════════════════════
    # ÁREA DE CONTEÚDO — ⚠ tk.Frame clássico (ZONA DE SEGURANÇA)
    # ════════════════════════════════════════════════════════════════

    def _montar_area_conteudo(self):
        """
        DECISÃO ARQUITETURAL:
        Usa tk.Frame clássico (NÃO ctk.CTkFrame) para a área de conteúdo.

        Motivo: as sub-telas (tela_estoque, tela_venda, tela_fiado, etc.)
        herdam de tk.Frame ou ctk.CTkFrame e são instanciadas com 'parent'
        apontando para este container. Misturar hierarquias CTk/tk no mesmo
        container pode gerar deadlock no mainloop do Tcl/Tk se o container
        pai for um CTkFrame (que envolve um tk.Frame interno via CTk).
        Usar tk.Frame diretamente elimina essa camada de indireção e resolve
        o congelamento relatado.
        """
        P = self._paleta()

        self.area_conteudo = tk.Frame(
            self,
            bg=P["bg_window"],
            relief="flat",
            bd=0,
        )
        self.area_conteudo.grid(row=0, column=1, sticky="nsew")
        self.area_conteudo.grid_columnconfigure(0, weight=1)
        self.area_conteudo.grid_rowconfigure(0, weight=1)

        # Alias de compatibilidade com o resto do código e sub-telas
        self.frame_conteudo = self.area_conteudo

    # ════════════════════════════════════════════════════════════════
    # TELA DE BOAS-VINDAS
    # ════════════════════════════════════════════════════════════════

    def _frame_boas_vindas(self):
        """Painel central de entrada com logo em alta definição."""
        P = self._paleta()

        # tk.Frame como pai — compatível com a zona de segurança
        frame = tk.Frame(self.frame_conteudo, bg=P["bg_window"], bd=0)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Sub-container centralizado via place
        centro = tk.Frame(frame, bg=P["bg_window"], bd=0)
        centro.place(relx=0.5, rely=0.5, anchor="center")

        # Logo grande (CTkLabel dentro de tk.Frame é suportado)
        self._lbl_bv_logo = ctk.CTkLabel(
            centro,
            text="" if self._ctk_logo_welcome else "🐅",
            image=self._ctk_logo_welcome,
            font=ctk.CTkFont(size=60) if not self._ctk_logo_welcome else ctk.CTkFont(size=1),
            fg_color="transparent",
        )
        self._lbl_bv_logo.pack(pady=(0, 16))

        ctk.CTkLabel(
            centro,
            text="SISTEMA DE GESTÃO COMERCIAL",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=P["accent"],
            fg_color="transparent",
        ).pack()

        ctk.CTkLabel(
            centro,
            text="Painel Executivo pronto para atendimento.\nSelecione uma ação na barra lateral.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=P["fg_muted"],
            justify="center",
            fg_color="transparent",
        ).pack(pady=(8, 0))

        return frame

    def _frame_erro(self, erro: str, traceback_str: str = ""):
        """Frame de erro amigável com traceback colapsável."""
        frame = tk.Frame(self.frame_conteudo, bg="#1A0A0A", bd=0)

        ctk.CTkLabel(
            frame,
            text="⚠️  Erro ao carregar a tela",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#E74C3C",
            fg_color="transparent",
        ).pack(pady=24)

        ctk.CTkLabel(
            frame,
            text=erro,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#F5A0A0",
            wraplength=680,
            fg_color="transparent",
        ).pack()

        if traceback_str:
            txt = tk.Text(
                frame, height=12,
                font=("Consolas", 9),
                bg="#2A0A0A", fg="#F5A0A0",
                relief="flat", bd=0,
            )
            txt.insert("1.0", traceback_str)
            txt.config(state="disabled")
            txt.pack(fill="x", padx=24, pady=12)

        return frame

    # ════════════════════════════════════════════════════════════════
    # TROCA DE TELAS
    # ════════════════════════════════════════════════════════════════

    def mostrar_tela(self, nome_tela: str, **kwargs):
        """Alterna para a tela solicitada preservando cache e limpando instâncias temporárias."""
        if self._frame_atual:
            try:
                eh_cacheada = self._frame_atual in self._cache_telas.values()
                if eh_cacheada:
                    if hasattr(self._frame_atual, "grid_remove"):
                        self._frame_atual.grid_remove()
                    else:
                        self._frame_atual.pack_forget()
                else:
                    # Tela temporária não cacheada (ex: edição de produto) → destrói sem vazar RAM
                    self._frame_atual.destroy()
            except Exception:
                pass
            self._frame_atual = None

        self._destacar_menu(nome_tela)

        kwargs_validos = {k: v for k, v in kwargs.items() if v is not None}

        if not kwargs_validos and nome_tela in self._cache_telas:
            frame = self._cache_telas[nome_tela]
            if hasattr(frame, "atualizar_dados"):
                try:
                    frame.atualizar_dados()
                except Exception as exc:
                    print(f"[Aviso] Falha ao atualizar dados de '{nome_tela}': {exc}")
        else:
            frame = self._criar_tela(nome_tela, **kwargs_validos)
            if not kwargs_validos and frame is not None:
                self._cache_telas[nome_tela] = frame

        if frame:
            frame.grid(row=0, column=0, sticky="nsew")
            self._frame_atual = frame
            self._sincronizar_ttk()
        else:
            self.mostrar_tela("boas_vindas")

    def _criar_tela(self, nome: str, **kwargs):
        """Factory de instâncias de sub-telas."""
        try:
            if nome == "boas_vindas":
                return self._frame_boas_vindas()
            elif nome == "estoque":
                from views.tela_estoque import TelaEstoque
                return TelaEstoque(self.frame_conteudo, controller=self, **kwargs)
            elif nome == "cadastro":
                from views.tela_cadastro import TelaCadastro
                return TelaCadastro(self.frame_conteudo, controller=self, **kwargs)
            elif nome == "venda":
                from views.tela_venda import TelaVenda
                return TelaVenda(self.frame_conteudo, controller=self, **kwargs)
            elif nome == "config":
                from views.tela_config import TelaConfiguracoes
                return TelaConfiguracoes(self.frame_conteudo, controller=self, **kwargs)
            elif nome == "dashboard":
                from views.tela_dashboard import TelaDashboard
                return TelaDashboard(self.frame_conteudo, controller=self, **kwargs)
            elif nome == "margens":
                from views.tela_saude_margens import TelaSaudeMargens
                return TelaSaudeMargens(self.frame_conteudo, controller=self, **kwargs)
            elif nome == "fiado":
                from views.tela_fiado import TelaFiado
                return TelaFiado(self.frame_conteudo, controller=self, **kwargs)
        except Exception as e:
            import traceback
            return self._frame_erro(str(e), traceback.format_exc())

    # ════════════════════════════════════════════════════════════════
    # DESTAQUE DO BOTÃO ATIVO
    # ════════════════════════════════════════════════════════════════

    def _destacar_menu(self, tela_ativa: str):
        """Pinta o botão ativo com accent e reseta os demais."""
        self._tela_atual = tela_ativa
        P = self._paleta()

        for nome, btn in self._botoes_menu.items():
            if nome == tela_ativa:
                btn.configure(
                    fg_color=P["accent2"],
                    text_color=P["btn_active_fg"],
                    hover_color=P["accent2"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=P["fg_primary"],
                    hover_color=P["bg_hover"],
                )

    # ════════════════════════════════════════════════════════════════
    # ALTERNÂNCIA DE TEMA
    # ════════════════════════════════════════════════════════════════

    def _paleta(self) -> dict:
        return DARK if self._modo_escuro else LIGHT

    def _alternar_tema(self):
        """Inverte o tema global via CTk e sincroniza toda a interface."""
        self._modo_escuro = not self._modo_escuro
        modo = "dark" if self._modo_escuro else "light"
        ctk.set_appearance_mode(modo)

        P = self._paleta()

        # Atualiza label descritivo do switch
        self._lbl_tema.configure(
            text="Modo Escuro" if self._modo_escuro else "Modo Claro",
            text_color=P["fg_muted"],
        )

        # Atualiza cores da sidebar que usam variáveis hardcoded
        self.sidebar.configure(fg_color=P["bg_sidebar"])
        self._lbl_marca.configure(text_color=P["accent"])
        self._sep_top.configure(fg_color=P["divider"])
        self._sep_bot.configure(fg_color=P["divider"])

        # Atualiza a zona de segurança (tk.Frame clássico — usa bg=)
        self.area_conteudo.config(bg=P["bg_window"])

        # Re-destaca o botão ativo com as novas cores
        self._destacar_menu(self._tela_atual)

        # Sincroniza motor TTK para sub-telas legadas
        self._sincronizar_ttk()

        # Repinta widgets tk legados na tela atual
        if self._frame_atual and self._frame_atual.winfo_exists():
            self._repintar_legados(self._frame_atual)

    # ════════════════════════════════════════════════════════════════
    # MOTOR DE ESTILOS TTK
    # ════════════════════════════════════════════════════════════════

    def _sincronizar_ttk(self):
        """
        Mantém Treeview, Notebook, Combobox e Scrollbar das sub-telas
        sincronizados com a paleta ativa, evitando blocos brancos
        que o CustomTkinter não controla nesses widgets TTK nativos.
        """
        P  = self._paleta()
        bg = P["bg_window"]
        bp = P["bg_sidebar"]      # fundo de painéis
        fg = P["fg_primary"]
        ac = P["accent"]
        az = P["accent2"]
        dv = P["divider"]

        s = self._style

        # Treeview
        s.configure("Treeview",
            background=bp, foreground=fg,
            fieldbackground=bp, rowheight=26)
        s.configure("Treeview.Heading",
            background=dv, foreground=ac,
            font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("Treeview",
            background=[("selected", az)],
            foreground=[("selected", "#FFFFFF")])

        # Estilos nomeados usados nas sub-telas migradas
        for estilo in ("Fiado", "Extrato", "Alertas", "Cart", "Hist"):
            s.configure(f"{estilo}.Treeview",
                background=bp, foreground=fg, fieldbackground=bp, rowheight=28)
            s.configure(f"{estilo}.Treeview.Heading",
                background=dv, foreground=ac,
                font=("Segoe UI", 9, "bold"), relief="flat")
            s.map(f"{estilo}.Treeview",
                background=[("selected", az)],
                foreground=[("selected", "#FFFFFF")])

        # Scrollbars escuros
        for nome_sb in ("Dark.Vertical.TScrollbar", "Venda.Vertical.TScrollbar"):
            s.configure(nome_sb,
                troughcolor=bg, background=az,
                arrowcolor=fg, relief="flat", borderwidth=0)

        # Notebook
        s.configure("TNotebook", background=bg, borderwidth=0)
        s.configure("TNotebook.Tab",
            background=dv, foreground=fg,
            font=("Segoe UI", 9, "bold"), padding=[12, 4])
        s.map("TNotebook.Tab",
            background=[("selected", az)],
            foreground=[("selected", "#FFFFFF")])

        # Combobox TTK legado
        s.configure("TCombobox",
            fieldbackground=bp, background=dv,
            foreground=fg, arrowcolor=ac)
        s.map("TCombobox",
            fieldbackground=[("readonly", bp)],
            foreground=[("readonly", fg)])

        # Frames e Labels TTK
        s.configure("TFrame",          background=bg)
        s.configure("TLabel",          background=bg, foreground=fg)
        s.configure("TLabelframe",     background=bg, foreground=ac)
        s.configure("TLabelframe.Label", background=bg, foreground=ac)

        # Botões TTK
        s.configure("TButton",
            background=az, foreground="#FFFFFF",
            font=("Segoe UI", 9, "bold"), relief="flat", padding=6)
        s.map("TButton",
            background=[("active", ac)],
            foreground=[("active", "#121212")])

        # Trava todos os Comboboxes em readonly (segurança)
        self._travar_comboboxes(self)

    def _travar_comboboxes(self, container):
        for w in container.winfo_children():
            if isinstance(w, ttk.Combobox):
                w.config(state="readonly")
            if w.winfo_children():
                self._travar_comboboxes(w)

    # ════════════════════════════════════════════════════════════════
    # REPINTURA DE WIDGETS LEGADOS (tk puro)
    # ════════════════════════════════════════════════════════════════

    def _repintar_legados(self, container):
        """
        Varredura recursiva para repintar widgets tk puro (Frame, Label,
        Entry, Button, etc.) quando o tema é alternado pelo switch.
        Não toca em widgets CTk (identificados por classe CTk*).
        """
        P  = self._paleta()
        bg = P["bg_window"]
        bp = P["bg_sidebar"]
        fg = P["fg_primary"]
        ac = P["accent"]
        az = P["accent2"]

        KPI = {"#137333", "#C5221F", "#1A73E8", "#059669", "#DC2626"}

        for w in container.winfo_children():
            cls = w.winfo_class()
            try:
                if cls == "Frame":
                    w.config(bg=bg)
                elif cls == "Labelframe":
                    w.config(bg=bg, fg=ac, font=("Segoe UI", 10, "bold"))
                elif cls == "Canvas":
                    w.config(bg=bg, highlightbackground=bg)
                elif cls == "Label":
                    cor_fg = w.cget("fg")
                    if cor_fg not in KPI:
                        w.config(bg=bg, fg=fg)
                    else:
                        w.config(bg=bg)
                elif cls == "Button":
                    bg_at = w.cget("bg")
                    if bg_at in ("#F0F2F8", "#FFFFFF", "#F8F9FA", "#E2E8F0",
                                 "#1A1D2E", "SystemButtonFace", ""):
                        w.config(bg=bp, fg=fg)
                elif cls == "Entry":
                    if self._modo_escuro:
                        w.config(bg="#2D2D2D", fg="#FFFFFF",
                                 insertbackground="white", relief="flat")
                    else:
                        w.config(bg="#FFFFFF", fg="#1A1D2E",
                                 insertbackground="black", relief="solid", bd=1)
                elif cls == "Text":
                    if self._modo_escuro:
                        w.config(bg="#2D2D2D", fg="#FFFFFF", insertbackground="white")
                    else:
                        w.config(bg="#FFFFFF", fg="#1A1D2E", insertbackground="black")
                elif cls in ("Checkbutton", "Radiobutton"):
                    w.config(
                        bg=bg, fg=fg,
                        selectcolor=bp if self._modo_escuro else "#FFFFFF",
                        activebackground=bg, activeforeground=ac,
                    )
                elif cls == "Listbox":
                    if self._modo_escuro:
                        w.config(bg="#2D2D2D", fg="#FFFFFF",
                                 selectbackground=az, selectforeground="white")
                    else:
                        w.config(bg="#FFFFFF", fg="#1A1D2E",
                                 selectbackground=az, selectforeground="white")
            except Exception:
                pass

            if w.winfo_children():
                self._repintar_legados(w)

    # ════════════════════════════════════════════════════════════════
    # COMPATIBILIDADE COM SUB-TELAS LEGADAS
    # ════════════════════════════════════════════════════════════════

    @property
    def modo_escuro(self) -> bool:
        """Property pública para sub-telas que consultam controller.modo_escuro."""
        return self._modo_escuro

    # ════════════════════════════════════════════════════════════════
    # ATALHOS DE NAVEGAÇÃO
    # ════════════════════════════════════════════════════════════════

    def _ir_estoque(self):
        self.mostrar_tela("estoque")

    def _ir_cadastro(self, produto_id=None):
        # Sempre abre formulário limpo (ou carregado com produto_id de edição)
        antigo = self._cache_telas.pop("cadastro", None)
        if antigo and antigo is not self._frame_atual:
            try:
                antigo.destroy()
            except Exception:
                pass
        self.mostrar_tela("cadastro", produto_id=produto_id)

    def _ir_venda(self, variacao_id=None):
        # Preserva o carrinho existente ao navegar para o PDV ou clicar em 🛒 no Estoque
        self.mostrar_tela("venda")
        if variacao_id is not None and self._frame_atual and hasattr(self._frame_atual, "adicionar_via_bipe"):
            self.after(80, lambda vid=variacao_id: self._frame_atual.adicionar_via_bipe(vid))

    def _ir_fiado(self):
        self.mostrar_tela("fiado")

    def _ir_config(self):
        self.mostrar_tela("config")

    def _ir_dashboard(self):
        self.mostrar_tela("dashboard")

    def _ir_margens(self):
        self.mostrar_tela("margens")

    # ════════════════════════════════════════════════════════════════
    # BIPE GLOBAL — OUVINTE DE SCANNER USB
    # ════════════════════════════════════════════════════════════════

    def _capturar_bipe_global(self, event):
        """Captura teclas globais e detecta sequências rápidas de scanner USB.

        Scanners USB emulam teclado e enviam dígitos com intervalos < 50ms,
        finalizando com Return. Digitação humana é muito mais lenta.
        """
        widget = event.widget
        if isinstance(widget, (tk.Entry, tk.Text)) or widget.winfo_class() in ('Entry', 'Text', 'TEntry', 'CTkEntry', 'CTkTextbox'):
            return

        agora = time.time()
        delta = agora - self._bipe_last_time
        self._bipe_last_time = agora

        # Se o widget focado é um Entry/Text, o scanner pode estar atirando
        # dentro dele. Verificamos se a sequência é rápida o suficiente.
        widget_focado = self.focus_get()
        eh_entry = False
        if widget_focado:
            cls = widget_focado.winfo_class()
            eh_entry = cls in ('Entry', 'Text', 'TEntry', 'CTkEntry')

        # Return → tenta processar o buffer
        if event.keysym == 'Return':
            codigo = ''.join(self._bipe_buffer)
            self._bipe_buffer.clear()

            if len(codigo) >= self._BIPE_MIN_LEN:
                self._processar_bipe(codigo)
                return 'break'  # impede o Return de propagar
            return

        # Caractere imprimível
        char = event.char
        if not char or not char.isprintable():
            return

        # Se o intervalo é maior que o threshold, é digitação humana → reseta
        if delta > self._BIPE_THRESHOLD and self._bipe_buffer:
            self._bipe_buffer.clear()

        # Acumula no buffer
        self._bipe_buffer.append(char)

        # Segurança: não deixa o buffer crescer infinitamente
        if len(self._bipe_buffer) > self._BIPE_MAX_LEN:
            self._bipe_buffer.clear()

    def _processar_bipe(self, codigo: str):
        """Processa um código capturado pelo scanner.

        Regra de ouro: se o operador já está na tela de venda, adiciona
        direto ao carrinho SEM recriar a tela — preservando o estado atual.
        Só navega para 'venda' se estiver em outra tela.
        """
        from controllers.estoque_ctrl import buscar_por_codigo
        from tkinter import messagebox

        info = buscar_por_codigo(codigo)
        if info:
            vid = info['variacao_id']
            print(f"[Bipe] Código '{codigo}' → variação ID {vid} "
                  f"({info['modelo_nome']} / Tam:{info['tamanho']})")

            # Já está na tela de venda? Adiciona direto, sem destruir/recriar.
            if (self._tela_atual == "venda"
                    and self._frame_atual is not None
                    and hasattr(self._frame_atual, "adicionar_via_bipe")):
                try:
                    self._frame_atual.adicionar_via_bipe(vid)
                    return
                except Exception as err:
                    print(f"[Bipe] Falha ao adicionar diretamente: {err}")
                    # Fall through para navegação normal

            # Caso contrário, navega para a tela de venda com variação pré-selecionada
            self._ir_venda(variacao_id=vid)
        else:
            messagebox.showwarning(
                "Produto Não Encontrado",
                f"O código '{codigo}' não foi encontrado no estoque\n"
                f"ou está com estoque zerado.",
            )


    # ════════════════════════════════════════════════════════════════
    # FECHAMENTO LIMPO
    # ════════════════════════════════════════════════════════════════

    def _on_close(self):
        """
        Encerramento limpo ao fechar pelo botão X da janela.
        Dispara backup de segurança em thread daemon antes de destruir.
        """
        try:
            from backup import disparar_backup
            disparar_backup(motivo="encerramento pelo X")
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        try:
            if os.path.exists(self._ico_temp):
                os.remove(self._ico_temp)
        except Exception:
            pass
