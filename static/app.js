/* =========================================================
   KANEMBERG PDV UNIFICADO (MOBILE + PC DESKTOP) — app.js
   Controlador completo: Login, Estoque, CRUD Produtos, Etiquetas QR,
   PDV 2 Colunas, Bipe USB Global, Vendas do Dia e Controle de Fiado.
   ========================================================= */

(() => {
  "use strict";

  // -------------------------------------------------------
  // CONFIGURAÇÃO
  // -------------------------------------------------------
  const API_BASE = "";
  const STORAGE_TOKEN = "kanemberg_token";
  const STORAGE_USUARIO = "kanemberg_usuario";
  const STORAGE_ROLE = "kanemberg_role";
  const SCAN_COOLDOWN_MS = 1500;
  const DEBOUNCE_BUSCA_MS = 300;
  const LIMITE_EXTRATO_VISIVEL = 3;

  // -------------------------------------------------------
  // ESTADO GLOBAL
  // -------------------------------------------------------
  const estado = {
    token: localStorage.getItem(STORAGE_TOKEN) || "",
    usuario: localStorage.getItem(STORAGE_USUARIO) || "",
    role: localStorage.getItem(STORAGE_ROLE) || "",
    abaAtual: "aba-estoque",
    filtroEstoque: "todos",
    filtroGrupoEstoque: "todos",
    produtos: [],
    clientes: [],
    vendasHoje: [],
    faturamentoHoje: 0,
    pecasHoje: 0,
    clientesCarregados: false,
    carrinho: new Map(),
    scanner: null,
    cameraAtiva: false,
    cameraIniciando: false,
    scanBloqueadoAte: 0,
    buscandoCodigo: false,
    seqBuscaEstoque: 0,
    vendaEmAndamento: false,
    pagamentoEmAndamento: false,
    extratosAbertos: new Set(),
    // Buffer do leitor de código de barras USB
    bipeBuffer: "",
    bipeUltimoTempo: 0,
  };

  // -------------------------------------------------------
  // ATALHOS DE DOM
  // -------------------------------------------------------
  const $ = (id) => document.getElementById(id);

  const el = {
    telaLogin: $("tela-login"),
    formLogin: $("form-login"),
    inputUsuario: $("input-usuario"),
    inputSenha: $("input-senha"),
    loginErro: $("login-erro"),
    btnLogin: $("btn-login"),

    app: $("app-container"),
    topoUsuario: $("topo-usuario"),
    sidebarUsuario: $("sidebar-usuario"),
    btnSair: $("btn-sair"),
    btnSairPc: $("btn-sair-pc"),
    conteudo: document.querySelector(".conteudo"),

    tabs: {
      "aba-estoque": $("tab-estoque"),
      "aba-vender": $("tab-vender"),
      "aba-fiado": $("tab-fiado"),
      "tab-caixa": $("btn-nav-caixa"),
    },
    sidebarBtns: document.querySelectorAll(".sidebar-btn[data-aba]"),
    abas: {
      "aba-estoque": $("aba-estoque"),
      "aba-vender": $("aba-vender"),
      "aba-fiado": $("aba-fiado"),
      "tab-caixa": $("tab-caixa"),
    },
    btnNavCaixa: $("btn-nav-caixa"),
    btnSidebarCaixa: $("btn-sidebar-caixa"),
    btnAtualizarCaixa: $("btn-atualizar-caixa"),
    finHojeBruto: $("fin-hoje-bruto"),
    finHojeCusto: $("fin-hoje-custo"),
    finHojeLucro: $("fin-hoje-lucro"),
    finHojePecas: $("fin-hoje-pecas"),
    finPgtoPix: $("fin-pgto-pix"),
    finPgtoCartao: $("fin-pgto-cartao"),
    finPgtoDinheiro: $("fin-pgto-dinheiro"),
    finPgtoFiado: $("fin-pgto-fiado"),
    finSemanaBruto: $("fin-semana-bruto"),
    finSemanaCusto: $("fin-semana-custo"),
    finSemanaLucro: $("fin-semana-lucro"),
    finSemanaPecas: $("fin-semana-pecas"),

    // Estoque
    btnNovoProduto: $("btn-novo-produto"),
    inputBuscaEstoque: $("input-busca-estoque"),
    filtrosEstoque: $("filtros-estoque"),
    filtrosGruposEstoque: $("filtros-grupos-estoque"),
    kpisEstoque: $("kpis-estoque"),
    listaEstoque: $("lista-estoque"),

    // Vender (PDV)
    btnCamera: $("btn-toggle-camera"),
    qrReader: $("qr-reader"),
    formCodigoManual: $("form-codigo-manual"),
    inputCodigoManual: $("input-codigo-manual"),
    inputBuscaCatalogoPdv: $("input-busca-catalogo-pdv"),
    listaCatalogoPdv: $("lista-catalogo-pdv"),
    resumoVendasHoje: $("resumo-vendas-hoje"),
    listaVendasHoje: $("lista-vendas-hoje"),
    listaCarrinho: $("lista-carrinho"),
    btnLimparCarrinho: $("btn-limpar-carrinho"),
    badgeCarrinho: $("badge-carrinho"),
    badgeCarrinhoPc: $("badge-carrinho-pc"),
    inputDesconto: $("input-desconto"),
    grupoPagamento: $("grupo-pagamento"),
    wrapClienteVenda: $("wrap-cliente-venda"),
    selectClienteVenda: $("select-cliente-venda"),
    valorSubtotal: $("valor-subtotal"),
    valorDesconto: $("valor-desconto"),
    valorTotal: $("valor-total"),
    btnFinalizarVenda: $("btn-finalizar-venda"),

    // Fiado
    btnNovoCliente: $("btn-novo-cliente"),
    inputBuscaFiado: $("input-busca-fiado"),
    kpisFiado: $("kpis-fiado"),
    listaFiado: $("lista-fiado"),

    // Modal Pagamento
    modalPagamento: $("modal-pagamento"),
    formPagamento: $("form-pagamento"),
    modalClienteNome: $("modal-cliente-nome"),
    modalClienteSaldo: $("modal-cliente-saldo"),
    modalClienteId: $("modal-cliente-id"),
    inputValorPagamento: $("input-valor-pagamento"),
    btnQuitarTotal: $("btn-quitar-total"),
    inputObsPagamento: $("input-obs-pagamento"),
    btnCancelarPagamento: $("btn-cancelar-pagamento"),
    btnConfirmarPagamento: $("btn-confirmar-pagamento"),

    // Modal Produto
    modalProduto: $("modal-produto"),
    formProduto: $("form-produto"),
    modalProdutoTitulo: $("modal-produto-titulo"),
    produtoEditId: $("produto-edit-id"),
    prodModelo: $("prod-modelo"),
    prodMarca: $("prod-marca"),
    prodTecido: $("prod-tecido"),
    prodCorte: $("prod-corte"),
    btnAddVariacao: $("btn-add-variacao"),
    listaVariacoesForm: $("lista-variacoes-form"),
    btnCancelarProduto: $("btn-cancelar-produto"),
    btnSalvarProduto: $("btn-salvar-produto"),

    // Modal Cliente
    modalCliente: $("modal-cliente"),
    formCliente: $("form-cliente"),
    cliNome: $("cli-nome"),
    cliTelefone: $("cli-telefone"),
    cliLimite: $("cli-limite"),
    cliDia: $("cli-dia"),
    btnCancelarCliente: $("btn-cancelar-cliente"),

    // Modal Etiquetas QR
    modalEtiquetas: $("modal-etiquetas"),
    modalEtiquetasTitulo: $("modal-etiquetas-titulo"),
    areaImpressaoEtiquetas: $("area-impressao-etiquetas"),
    btnImprimirEtiquetas: $("btn-imprimir-etiquetas"),
    btnFecharEtiquetas: $("btn-fechar-etiquetas"),

    toast: $("toast"),
    loader: $("loader"),
  };

  // -------------------------------------------------------
  // UTILITÁRIOS
  // -------------------------------------------------------
  const formatadorBRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

  function brl(valor) {
    return formatadorBRL.format(Number(valor) || 0);
  }

  function num(valor, padrao = 0) {
    if (valor === null || valor === undefined || valor === "") return padrao;
    const n = Number(String(valor).replace(",", "."));
    return Number.isFinite(n) ? n : padrao;
  }

  function arred(valor) {
    return Math.round((Number(valor) || 0) * 100) / 100;
  }

  function escapeHtml(texto) {
    return String(texto ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function hexValido(hex) {
    return typeof hex === "string" && /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(hex.trim());
  }

  // -------------------------------------------------------
  // CLASSIFICAÇÃO LUMINESCENTE DE GRUPOS (ESTOQUE)
  // -------------------------------------------------------
  const GRUPOS_PRODUTO = {
    cima: {
      nome: "Parte de Cima",
      emoji: "",
      rotulo: "Cima",
      cor: "#00d2ff",
      classe: "card-grupo-cima",
      badgeClasse: "badge-grupo-cima",
      palavras: ["blusa", "camisa", "camiseta", "casaco", "vestido", "regata", "cropped", "sueter", "moletom", "polo", "jaqueta"],
    },
    baixo: {
      nome: "Parte de Baixo / Praia",
      emoji: "",
      rotulo: "Baixo",
      cor: "#52b788",
      classe: "card-grupo-baixo",
      badgeClasse: "badge-grupo-baixo",
      palavras: ["calça", "calca", "shorts", "short", "bermuda", "sunga", "saia"],
    },
    calcados: {
      nome: "Calçados / Meias",
      emoji: "",
      rotulo: "Calçados",
      cor: "#ff7b00",
      classe: "card-grupo-calcados",
      badgeClasse: "badge-grupo-calcados",
      palavras: ["chinelo", "meia", "sandalia", "sandália", "tenis", "tênis", "sapato"],
    },
    acessorios: {
      nome: "Acessórios",
      emoji: "",
      rotulo: "Acessórios",
      cor: "#ff1744",
      classe: "card-grupo-acessorios",
      badgeClasse: "badge-grupo-acessorios",
      palavras: ["boné", "bone", "óculos", "oculos", "relógio", "relogio", "cinto", "carteira", "bolsa"],
    },
    perfumaria: {
      nome: "Perfumaria",
      emoji: "",
      rotulo: "Perfumaria",
      cor: "#ffd700",
      classe: "card-grupo-perfumaria",
      badgeClasse: "badge-grupo-perfumaria",
      palavras: ["perfume", "colonia", "colônia", "fragrancia", "fragrância", "desodorante"],
    },
  };

  function obterCorGrupo(modeloNome, tipoPeca = "") {
    const texto = `${modeloNome || ""} ${tipoPeca || ""}`.toLowerCase().trim();
    for (const [chave, dados] of Object.entries(GRUPOS_PRODUTO)) {
      for (const p of dados.palavras) {
        if (texto.startsWith(p) || texto.includes(` ${p}`)) {
          return { chave, ...dados };
        }
      }
    }
    return { chave: "cima", ...GRUPOS_PRODUTO.cima };
  }

  function debounce(fn, ms) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  function formatarData(valor) {
    if (!valor) return "";
    const m = String(valor).match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/);
    if (!m) return String(valor);
    const [, ano, mes, dia, hh, mm] = m;
    return hh ? `${dia}/${mes}/${ano.slice(2)} ${hh}:${mm}` : `${dia}/${mes}/${ano}`;
  }

  function normalizarCodigoLido(texto) {
    let codigo = String(texto || "").trim();
    if (codigo.includes("/")) codigo = codigo.replace(/\/+$/, "").split("/").pop().trim();
    if (codigo.includes("=")) codigo = codigo.split("=").pop().trim();
    return codigo;
  }

  function chaveCarrinho(codigo) {
    return String(codigo || "").trim().toUpperCase();
  }

  function vibrar(ms = 60) {
    try {
      if (navigator.vibrate) navigator.vibrate(ms);
    } catch (_) {}
  }

  // -------------------------------------------------------
  // TOAST & LOADER
  // -------------------------------------------------------
  let toastTimer = null;

  function toast(mensagem, tipo = "info", duracao = 2300) {
    clearTimeout(toastTimer);
    el.toast.textContent = mensagem;
    el.toast.classList.remove("hidden", "sucesso", "erro");
    if (tipo === "sucesso") el.toast.classList.add("sucesso");
    if (tipo === "erro") el.toast.classList.add("erro");
    void el.toast.offsetWidth;
    toastTimer = setTimeout(() => el.toast.classList.add("hidden"), duracao);
  }

  let loaderContador = 0;

  function mostrarLoader() {
    loaderContador += 1;
    el.loader.classList.remove("hidden");
  }

  function esconderLoader() {
    loaderContador = Math.max(0, loaderContador - 1);
    if (loaderContador === 0) el.loader.classList.add("hidden");
  }

  // -------------------------------------------------------
  // CLIENTE HTTP
  // -------------------------------------------------------
  class ErroApi extends Error {
    constructor(mensagem, status) {
      super(mensagem);
      this.status = status;
    }
  }

  function extrairMensagemErro(dados, status) {
    if (!dados) return `Erro ${status} na comunicação com o servidor.`;
    if (typeof dados.detail === "string") return dados.detail;
    if (Array.isArray(dados.detail) && dados.detail.length) {
      return dados.detail
        .map((d) => {
          const campo = Array.isArray(d.loc) ? d.loc.filter((p) => p !== "body").join(".") : "";
          return campo ? `${campo}: ${d.msg}` : d.msg;
        })
        .join(" | ");
    }
    if (typeof dados.mensagem === "string") return dados.mensagem;
    if (typeof dados.erro === "string") return dados.erro;
    return `Erro ${status} na comunicação com o servidor.`;
  }

  async function api(caminho, { metodo = "GET", corpo = null, comLoader = false, autenticado = true } = {}) {
    const headers = {
      Accept: "application/json",
      "Cache-Control": "no-cache, no-store, must-revalidate",
      Pragma: "no-cache",
    };
    if (corpo !== null) headers["Content-Type"] = "application/json";
    if (autenticado && estado.token) headers.Authorization = `Bearer ${estado.token}`;

    // Cache Busting p/ iOS/Safari em todas as requisições GET
    let urlFinal = API_BASE + caminho;
    if (metodo.toUpperCase() === "GET" && !/[?&]_t=/.test(urlFinal)) {
      const sep = urlFinal.includes("?") ? "&" : "?";
      urlFinal = `${urlFinal}${sep}_t=${Date.now()}`;
    }

    if (comLoader) mostrarLoader();
    let resposta;
    try {
      resposta = await fetch(urlFinal, {
        method: metodo,
        headers,
        body: corpo !== null ? JSON.stringify(corpo) : undefined,
        cache: "no-store",
      });
    } catch (_) {
      if (comLoader) esconderLoader();
      throw new ErroApi("Sem conexão com o servidor da loja. Verifique a rede.", 0);
    }

    let dados = null;
    try {
      const texto = await resposta.text();
      dados = texto ? JSON.parse(texto) : null;
    } catch (_) {
      dados = null;
    }
    if (comLoader) esconderLoader();

    if (resposta.status === 401 && autenticado) {
      encerrarSessao("Sessão expirada. Faça login novamente.");
      throw new ErroApi("Sessão expirada.", 401);
    }

    if (!resposta.ok) {
      throw new ErroApi(extrairMensagemErro(dados, resposta.status), resposta.status);
    }

    if (dados && dados.sucesso === false) {
      throw new ErroApi(extrairMensagemErro(dados, resposta.status), resposta.status);
    }

    return dados;
  }

  function extrairLista(dados, chave) {
    if (Array.isArray(dados)) return dados;
    if (dados && Array.isArray(dados[chave])) return dados[chave];
    return [];
  }

  // -------------------------------------------------------
  // SESSÃO / LOGIN
  // -------------------------------------------------------
  function mostrarErroLogin(msg) {
    el.loginErro.textContent = msg;
    el.loginErro.classList.remove("hidden");
  }

  async function fazerLogin(evento) {
    evento.preventDefault();
    el.loginErro.classList.add("hidden");

    const usuario = el.inputUsuario.value.trim();
    const senha = el.inputSenha.value;
    if (!usuario || !senha) {
      mostrarErroLogin("Informe usuário e senha.");
      return;
    }

    el.btnLogin.disabled = true;
    el.btnLogin.textContent = "Entrando...";
    try {
      const dados = await api("/api/login", {
        metodo: "POST",
        corpo: { usuario, senha },
        autenticado: false,
      });
      const token = dados.token || dados.access_token;
      if (!token) throw new ErroApi("Servidor não retornou o token de acesso.", 500);

      estado.token = token;
      estado.usuario = dados.usuario || usuario;
      estado.role = dados.role || "vendedor";
      localStorage.setItem(STORAGE_TOKEN, estado.token);
      localStorage.setItem(STORAGE_USUARIO, estado.usuario);
      localStorage.setItem(STORAGE_ROLE, estado.role);

      el.inputSenha.value = "";
      el.inputUsuario.blur();
      el.inputSenha.blur();
      abrirApp();
      toast(`Bem-vindo, ${estado.usuario}!`, "sucesso");
    } catch (erro) {
      mostrarErroLogin(erro.message || "Falha no login.");
    } finally {
      el.btnLogin.disabled = false;
      el.btnLogin.textContent = "Entrar no Sistema";
    }
  }

  function abrirApp() {
    el.telaLogin.classList.add("hidden");
    el.app.classList.remove("hidden");
    const ehAdmin = estado.role === "admin";
    const papel = ehAdmin ? "Administrador" : "Vendedor";
    const infoUsuario = `${estado.usuario} · ${papel}`;
    el.topoUsuario.textContent = infoUsuario;
    if (el.sidebarUsuario) el.sidebarUsuario.textContent = infoUsuario;

    // Controle de Permissão: Vendedores comuns não veem a aba Caixa (lucro líquido / custo)
    if (el.btnNavCaixa) el.btnNavCaixa.classList.toggle("hidden", !ehAdmin);
    if (el.btnSidebarCaixa) el.btnSidebarCaixa.classList.toggle("hidden", !ehAdmin);

    trocarAba("aba-estoque", true);
    carregarEstoque("");
    carregarClientes();
    carregarVendasHoje();
    if (ehAdmin) carregarResumoFinanceiro();
  }

  function encerrarSessao(mensagem) {
    pararCamera();
    fecharTodosModais();
    estado.token = "";
    estado.usuario = "";
    estado.role = "";
    estado.produtos = [];
    estado.clientes = [];
    estado.clientesCarregados = false;
    estado.carrinho.clear();
    estado.extratosAbertos.clear();
    localStorage.removeItem(STORAGE_TOKEN);
    localStorage.removeItem(STORAGE_USUARIO);
    localStorage.removeItem(STORAGE_ROLE);

    el.inputBuscaEstoque.value = "";
    el.inputBuscaFiado.value = "";
    el.inputDesconto.value = "";
    estado.filtroEstoque = "todos";
    estado.filtroGrupoEstoque = "todos";
    if (el.filtrosEstoque) {
      el.filtrosEstoque.querySelectorAll(".chip-filtro").forEach((b) => b.classList.toggle("ativo", b.dataset.filtro === "todos"));
    }
    if (el.filtrosGruposEstoque) {
      el.filtrosGruposEstoque.querySelectorAll(".chip-grupo").forEach((b) => b.classList.toggle("ativo", b.dataset.grupo === "todos"));
    }
    selecionarFormaPagamento("DINHEIRO");
    renderizarCarrinho();

    el.app.classList.add("hidden");
    el.telaLogin.classList.remove("hidden");
    if (mensagem) mostrarErroLogin(mensagem);
  }

  // -------------------------------------------------------
  // NAVEGAÇÃO POR ABAS (MOBILE TAB BAR + PC SIDEBAR)
  // -------------------------------------------------------
  const ABAS_ADMIN = ["tab-caixa"];

  function trocarAba(abaId, forcar = false) {
    if (abaId === "aba-caixa") abaId = "tab-caixa";
    if (ABAS_ADMIN.includes(abaId) && estado.role !== "admin") return;
    if (!el.abas[abaId]) return;
    if (!forcar && estado.abaAtual === abaId) return;

    if (estado.abaAtual === "aba-vender" && abaId !== "aba-vender") {
      pararCamera();
    }

    estado.abaAtual = abaId;
    Object.entries(el.abas).forEach(([id, secao]) => {
      if (secao) secao.classList.toggle("hidden", id !== abaId);
    });
    Object.entries(el.tabs).forEach(([id, botao]) => {
      if (botao) botao.classList.toggle("ativo", id === abaId);
    });
    el.sidebarBtns.forEach((btn) => btn.classList.toggle("ativo", btn.dataset.aba === abaId));
    el.conteudo.scrollTop = 0;

    if (abaId === "aba-estoque" && !forcar) {
      carregarEstoque(el.inputBuscaEstoque.value.trim());
    }
    if (abaId === "aba-fiado") {
      carregarClientes();
    }
    if (abaId === "aba-vender") {
      if (!estado.clientesCarregados) carregarClientes();
      renderizarCatalogoPdv();
      carregarVendasHoje();
    }
    if (abaId === "tab-caixa") {
      carregarResumoFinanceiro();
    }
  }

  // -------------------------------------------------------
  // ABA CAIXA / GANHOS (RESUMO FINANCEIRO — ADMIN)
  // -------------------------------------------------------
  async function carregarResumoFinanceiro() {
    if (estado.role !== "admin") return;
    try {
      const dados = await api(`/api/financeiro/resumo?_t=${Date.now()}`);
      if (!dados) return;

      const hoje = dados.hoje || {};
      const semana = dados.semana || {};
      const pgto = dados.por_pagamento_hoje || {};

      if (el.finHojeBruto) el.finHojeBruto.textContent = brl(hoje.faturamento_bruto);
      if (el.finHojeCusto) el.finHojeCusto.textContent = brl(hoje.custo_total);
      if (el.finHojeLucro) el.finHojeLucro.textContent = brl(hoje.lucro_liquido);
      if (el.finHojePecas) el.finHojePecas.textContent = `${num(hoje.pecas_vendidas)} peça(s) vendida(s)`;

      if (el.finPgtoPix) el.finPgtoPix.textContent = brl(pgto.PIX);
      if (el.finPgtoCartao) el.finPgtoCartao.textContent = brl(pgto.CARTAO);
      if (el.finPgtoDinheiro) el.finPgtoDinheiro.textContent = brl(pgto.DINHEIRO);
      if (el.finPgtoFiado) el.finPgtoFiado.textContent = brl(pgto.FIADO);

      if (el.finSemanaBruto) el.finSemanaBruto.textContent = brl(semana.faturamento_bruto);
      if (el.finSemanaCusto) el.finSemanaCusto.textContent = brl(semana.custo_total);
      if (el.finSemanaLucro) el.finSemanaLucro.textContent = brl(semana.lucro_liquido);
      if (el.finSemanaPecas) el.finSemanaPecas.textContent = `${num(semana.pecas_vendidas)} peça(s) vendida(s)`;
    } catch (erro) {
      if (erro.status !== 401) {
        toast(erro.message || "Erro ao carregar resumo financeiro.", "erro");
      }
    }
  }

  // -------------------------------------------------------
  // ABA ESTOQUE & CATÁLOGO RÁPIDO DO PDV
  // -------------------------------------------------------
  async function carregarEstoque(termo) {
    const filtroBusca = termo !== undefined ? termo : (el.inputBuscaEstoque ? el.inputBuscaEstoque.value.trim() : "");
    const seq = ++estado.seqBuscaEstoque;
    if (!estado.produtos.length) {
      el.listaEstoque.innerHTML = '<p class="vazio">Carregando estoque...</p>';
    }
    try {
      const query = filtroBusca
        ? `?busca=${encodeURIComponent(filtroBusca)}&_t=${Date.now()}`
        : `?_t=${Date.now()}`;
      const dados = await api(`/api/estoque${query}`);
      if (seq !== estado.seqBuscaEstoque) return;
      estado.produtos = extrairLista(dados, "produtos");
      renderizarEstoque();
      renderizarCatalogoPdv();
    } catch (erro) {
      if (seq !== estado.seqBuscaEstoque || erro.status === 401) return;
      el.listaEstoque.innerHTML = `<p class="vazio">${escapeHtml(erro.message)}</p>`;
    }
  }

  function renderizarKpisEstoque() {
    if (!el.kpisEstoque) return;
    const totalModelos = estado.produtos.length;
    let totalPecas = 0;
    let valorTotalEstoque = 0;
    let baixoEstoque = 0;

    estado.produtos.forEach((p) => {
      const vars = Array.isArray(p.variacoes) ? p.variacoes : [];
      const est = vars.reduce((s, v) => s + num(v.estoque), 0);
      totalPecas += est;
      if (est > 0 && est <= 3) baixoEstoque += 1;
      vars.forEach((v) => {
        valorTotalEstoque += num(v.estoque) * num(v.preco_venda || p.preco_venda);
      });
    });

    el.kpisEstoque.innerHTML = `
      <div class="kpi-box">
        <small>Modelos Cadastrados</small>
        <strong>${totalModelos}</strong>
      </div>
      <div class="kpi-box">
        <small>Peças em Estoque</small>
        <strong class="texto-primario">${totalPecas} un.</strong>
      </div>
      <div class="kpi-box">
        <small>Valor em Vitrine</small>
        <strong class="texto-sucesso">${brl(valorTotalEstoque)}</strong>
      </div>
      <div class="kpi-box">
        <small>Estoque Baixo (≤ 3)</small>
        <strong class="${baixoEstoque > 0 ? "texto-perigo" : ""}">${baixoEstoque}</strong>
      </div>
    `;
  }

  function atualizarUiFiltrosEstoque() {
    if (!el.filtrosEstoque) return;
    const grupoAtivo = estado.filtroGrupoEstoque || "todos";
    const statusAtivo = estado.filtroEstoque || "todos";
    const nenhumAtivo = grupoAtivo === "todos" && statusAtivo === "todos";

    const btnTodos = el.filtrosEstoque.querySelector('[data-acao-filtro="limpar"]');
    if (btnTodos) {
      btnTodos.classList.toggle("ativo", nenhumAtivo);
    }
    el.filtrosEstoque.querySelectorAll("button[data-grupo]").forEach((btn) => {
      btn.classList.toggle("ativo", btn.dataset.grupo === grupoAtivo);
    });
    el.filtrosEstoque.querySelectorAll("button[data-filtro]").forEach((btn) => {
      btn.classList.toggle("ativo", btn.dataset.filtro === statusAtivo);
    });
  }

  function renderizarEstoque() {
    atualizarUiFiltrosEstoque();

    const filtro = estado.filtroEstoque;
    const filtroGrupo = estado.filtroGrupoEstoque;
    const produtosFiltrados = estado.produtos.filter((p) => {
      const vars = Array.isArray(p.variacoes) ? p.variacoes : [];
      const total = p.estoque_total !== undefined ? num(p.estoque_total) : vars.reduce((s, v) => s + num(v.estoque), 0);
      if (filtro === "com-estoque" && total <= 0) return false;
      if (filtro === "baixo" && (total <= 0 || total > 3)) return false;
      if (filtro === "zerado" && total > 0) return false;

      if (filtroGrupo && filtroGrupo !== "todos") {
        const g = obterCorGrupo(p.modelo_nome, p.tipo_peca);
        if (g.chave !== filtroGrupo) return false;
      }
      return true;
    });

    if (!produtosFiltrados.length) {
      const termo = el.inputBuscaEstoque.value.trim();
      el.listaEstoque.innerHTML = termo
        ? `<p class="vazio">Nenhum produto encontrado para "${escapeHtml(termo)}".</p>`
        : '<p class="vazio">Nenhum produto neste filtro.</p>';
      return;
    }

    const svgTag = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>`;
    const svgEdit = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>`;
    const svgTrash = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;

    const html = produtosFiltrados
      .map((p) => {
        const variacoes = Array.isArray(p.variacoes) ? p.variacoes : [];
        const estoqueTotal =
          p.estoque_total !== undefined && p.estoque_total !== null
            ? num(p.estoque_total)
            : variacoes.reduce((soma, v) => soma + num(v.estoque), 0);

        let precoVenda = num(p.preco_venda);
        if (!precoVenda && variacoes.length) {
          precoVenda = Math.max(...variacoes.map((v) => num(v.preco_venda)));
        }

        let classeChip = "";
        if (estoqueTotal <= 0) classeChip = "zerado";
        else if (estoqueTotal <= 3) classeChip = "baixo";

        const VAZIOS = ["", "—", "-", "N/A", "NA", "NONE", "NULL"];
        const valido = (x) => x != null && !VAZIOS.includes(String(x).trim().toUpperCase());
        const corteTecido = [p.corte, p.tecido].filter(valido).map((x) => String(x).trim()).join(" | ");
        const titulo = [p.modelo_nome, p.marca].filter((x) => x && String(x).trim()).join(" — ");
        const grupo = obterCorGrupo(p.modelo_nome, p.tipo_peca);

        const pills = variacoes.length
          ? variacoes
              .map((v) => {
                const qtd = num(v.estoque);
                const corPadrao = String(v.cor || "").trim().toLowerCase() === "padrão";
                const bolinha = hexValido(v.cor_hex) && !corPadrao
                  ? `<span class="bolinha-cor" style="background:${v.cor_hex.trim()}"></span>`
                  : "";
                const cor = v.cor && !corPadrao ? ` ${escapeHtml(v.cor)}` : "";
                const codigo = escapeHtml(v.codigo_barras || "");
                if (qtd <= 0) {
                  return `
                    <span class="variacao-pill sem-estoque" title="Sem estoque">
                      ${bolinha}
                      <span>${escapeHtml(v.tamanho || "—")}${cor}</span>
                      <span class="variacao-qtd">×0</span>
                    </span>`;
                }
                return `
                  <button type="button" class="variacao-pill clicavel" data-acao="vender-variacao" data-codigo="${codigo}" title="Toque para enviar +1 ao Carrinho (${codigo})">
                    ${bolinha}
                    <span>${escapeHtml(v.tamanho || "—")}${cor}</span>
                    <span class="variacao-qtd">×${qtd}</span>
                  </button>`;
              })
              .join("")
          : '<span class="variacao-pill sem-estoque">Sem variações</span>';

        return `
          <article class="card-produto ${grupo.classe}">
            <div>
              <div class="card-produto-topo">
                <div>
                  <div class="badge-grupo-produto ${grupo.badgeClasse}">${escapeHtml(grupo.nome)}</div>
                  <div class="card-produto-nome">${escapeHtml(titulo || "Produto sem nome")}</div>
                  ${corteTecido ? `<div class="card-produto-meta">${escapeHtml(corteTecido)}</div>` : ""}
                  <span class="chip-estoque ${classeChip}">${estoqueTotal} un. em estoque</span>
                </div>
                <div class="card-produto-preco">${brl(precoVenda)}</div>
              </div>
              <div class="grade-variacoes">${pills}</div>
            </div>

            <div class="card-produto-rodape">
              <button type="button" class="btn-icone-mini" data-acao="etiquetas-produto" data-id="${p.id}" title="Etiquetas QR Code">${svgTag}</button>
              <button type="button" class="btn-icone-mini" data-acao="editar-produto" data-id="${p.id}" title="Editar produto">${svgEdit}</button>
              <button type="button" class="btn-icone-mini perigo" data-acao="excluir-produto" data-id="${p.id}" title="Excluir produto">${svgTrash}</button>
            </div>
          </article>`;
      })
      .join("");

    el.listaEstoque.innerHTML = html;
  }

  /** Renderiza o catálogo rápido dentro da tela de Venda (PDV) para adicionar com 1 clique. */
  function renderizarCatalogoPdv() {
    if (!el.listaCatalogoPdv) return;
    const termo = (el.inputBuscaCatalogoPdv ? el.inputBuscaCatalogoPdv.value : "").trim().toLowerCase();
    const tokens = termo ? termo.split(/\s+/) : [];

    const disponiveis = estado.produtos.filter((p) => {
      const vars = Array.isArray(p.variacoes) ? p.variacoes : [];
      const temEstoque = vars.some((v) => num(v.estoque) > 0);
      if (!temEstoque) return false;
      if (!tokens.length) return true;
      const texto = JSON.stringify(p).toLowerCase();
      return tokens.every((t) => texto.includes(t));
    });

    if (!disponiveis.length) {
      el.listaCatalogoPdv.innerHTML = '<p class="vazio">Nenhuma peça com estoque encontrada.</p>';
      return;
    }

    el.listaCatalogoPdv.innerHTML = disponiveis
      .map((p) => {
        const vars = (p.variacoes || []).filter((v) => num(v.estoque) > 0);
        const titulo = [p.modelo_nome, p.marca].filter(Boolean).join(" — ");
        const pills = vars
          .map((v) => {
            const bolinha = hexValido(v.cor_hex)
              ? `<span class="bolinha-cor" style="background:${v.cor_hex.trim()}"></span>`
              : "";
            const cor = v.cor ? ` ${escapeHtml(v.cor)}` : "";
            return `
              <button type="button" class="variacao-pill clicavel" data-acao="vender-variacao" data-codigo="${escapeHtml(v.codigo_barras)}">
                ${bolinha}
                <span>+ ${escapeHtml(v.tamanho)}${cor}</span>
                <span class="variacao-qtd">(${num(v.estoque)})</span>
              </button>`;
          })
          .join("");

        return `
          <div class="item-catalogo-pdv">
            <div>
              <div class="item-catalogo-titulo">${escapeHtml(titulo)}</div>
              <div class="item-catalogo-preco">${brl(p.preco_venda)}</div>
            </div>
            <div class="item-catalogo-pills">${pills}</div>
          </div>`;
      })
      .join("");
  }

  const buscarEstoqueDebounced = debounce(() => {
    carregarEstoque(el.inputBuscaEstoque.value.trim());
  }, DEBOUNCE_BUSCA_MS);

  // -------------------------------------------------------
  // HISTÓRICO DE VENDAS DE HOJE (PDV)
  // -------------------------------------------------------
  async function carregarVendasHoje() {
    if (!el.listaVendasHoje) return;
    try {
      const dados = await api("/api/vendas/hoje");
      estado.vendasHoje = extrairLista(dados, "vendas");
      estado.faturamentoHoje = num(dados && dados.faturamento_hoje);
      estado.pecasHoje = num(dados && dados.pecas_hoje);
      renderizarVendasHoje();
    } catch (_) {
      /* silencioso */
    }
  }

  function renderizarVendasHoje() {
    if (!el.listaVendasHoje) return;
    if (el.resumoVendasHoje) {
      el.resumoVendasHoje.textContent = `${brl(estado.faturamentoHoje)} (${estado.pecasHoje} pçs)`;
    }
    if (!estado.vendasHoje.length) {
      el.listaVendasHoje.innerHTML = '<p class="vazio">Nenhuma venda registrada hoje.</p>';
      return;
    }

    el.listaVendasHoje.innerHTML = estado.vendasHoje
      .slice(0, 20)
      .map((v) => {
        const hora = String(v.data_venda || "").split(" ")[1] || "";
        return `
          <div class="linha-venda-hoje">
            <div>
              <strong>${v.quantidade}× ${escapeHtml(v.modelo_nome)} (${escapeHtml(v.tamanho)})</strong>
              <small> · ${escapeHtml(v.forma_pagamento)} ${hora ? `às ${escapeHtml(hora)}` : ""}</small>
            </div>
            <strong class="texto-sucesso">${brl(v.valor_total)}</strong>
          </div>`;
      })
      .join("");
  }

  // -------------------------------------------------------
  // CÂMERA / QR CODE (Html5Qrcode)
  // -------------------------------------------------------
  function atualizarBotaoCamera() {
    const span = el.btnCamera.querySelector("span");
    if (estado.cameraAtiva) {
      el.btnCamera.classList.add("btn-camera-ativa");
      span.textContent = "Fechar Câmera";
    } else {
      el.btnCamera.classList.remove("btn-camera-ativa");
      span.textContent = "Abrir Câmera QR Code";
    }
    el.btnCamera.disabled = estado.cameraIniciando;
  }

  async function iniciarCamera() {
    if (estado.cameraAtiva || estado.cameraIniciando) return;

    if (typeof Html5Qrcode === "undefined") {
      toast("Leitor de QR Code não carregou. Verifique a internet.", "erro", 3500);
      return;
    }
    if (!window.isSecureContext) {
      toast("A câmera exige HTTPS ou localhost. Use o campo manual ou leitor USB.", "erro", 4000);
      return;
    }

    estado.cameraIniciando = true;
    atualizarBotaoCamera();
    el.qrReader.classList.remove("hidden");

    try {
      if (!estado.scanner) {
        estado.scanner = new Html5Qrcode("qr-reader", { verbose: false });
      }
      const config = {
        fps: 10,
        qrbox: (larguraVisor, alturaVisor) => {
          const menor = Math.min(larguraVisor, alturaVisor);
          const lado = Math.max(160, Math.floor(menor * 0.7));
          return { width: lado, height: lado };
        },
        aspectRatio: 1.0,
        disableFlip: true,
      };
      await estado.scanner.start({ facingMode: "environment" }, config, aoLerCodigo, () => {});
      estado.cameraAtiva = true;
      const video = el.qrReader.querySelector("video");
      if (video) {
        video.setAttribute("playsinline", "true");
        video.setAttribute("muted", "true");
      }
    } catch (erro) {
      el.qrReader.classList.add("hidden");
      const nome = erro && erro.name ? erro.name : "";
      const texto = String(erro && erro.message ? erro.message : erro);
      if (nome === "NotAllowedError" || /permission|denied/i.test(texto)) {
        toast("Permissão da câmera negada. Libere nos Ajustes do navegador.", "erro", 4000);
      } else if (nome === "NotFoundError" || /not found|no camera/i.test(texto)) {
        toast("Nenhuma câmera encontrada neste aparelho.", "erro", 3500);
      } else {
        toast("Não foi possível abrir a câmera.", "erro", 3500);
      }
    } finally {
      estado.cameraIniciando = false;
      atualizarBotaoCamera();
    }
  }

  let audioContextGlobal = null;
  let ultimoCodigoLido = null;
  let ultimoTimestampLeitura = 0;

  function tocarBipeLeitura() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!audioContextGlobal) {
        audioContextGlobal = new AudioCtx();
      }
      if (audioContextGlobal.state === "suspended") {
        audioContextGlobal.resume();
      }
      const osc = audioContextGlobal.createOscillator();
      const gain = audioContextGlobal.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(1200, audioContextGlobal.currentTime);

      gain.gain.setValueAtTime(0.25, audioContextGlobal.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioContextGlobal.currentTime + 0.12);

      osc.connect(gain);
      gain.connect(audioContextGlobal.destination);

      osc.start(audioContextGlobal.currentTime);
      osc.stop(audioContextGlobal.currentTime + 0.12);
    } catch (_) {}
  }

  function dispararFeedbackLeitura() {
    // A) Haptic / Vibração Física (Android + Truque Taptic Engine iOS 18+)
    if (navigator.vibrate) {
      try {
        navigator.vibrate([120]);
      } catch (_) {}
    }

    try {
      let iosTrigger = document.getElementById("ios-haptic-trigger");
      let iosLabel = document.getElementById("ios-haptic-label");
      if (!iosTrigger) {
        iosTrigger = document.createElement("input");
        iosTrigger.type = "checkbox";
        iosTrigger.setAttribute("switch", "");
        iosTrigger.id = "ios-haptic-trigger";
        iosTrigger.style.cssText = "position:fixed; opacity:0; pointer-events:none; left:-9999px;";
        document.body.appendChild(iosTrigger);
      }
      if (!iosLabel) {
        iosLabel = document.createElement("label");
        iosLabel.htmlFor = "ios-haptic-trigger";
        iosLabel.id = "ios-haptic-label";
        iosLabel.style.cssText = "position:fixed; opacity:0; pointer-events:none; left:-9999px;";
        document.body.appendChild(iosLabel);
      }
      document.getElementById("ios-haptic-label").click();
    } catch (_) {}

    // B) Bipe Sonoro de Caixa (Web Audio API nativa sem arquivos externos)
    tocarBipeLeitura();

    // C) Flash Visual Verde no Scanner
    const targetReader = el.qrReader || document.getElementById("qr-reader");
    if (targetReader) {
      targetReader.classList.add("qr-flash-sucesso");
      setTimeout(() => {
        targetReader.classList.remove("qr-flash-sucesso");
      }, 350);
    }
  }

  async function pararCamera() {
    const scanner = estado.scanner;
    estado.cameraAtiva = false;
    el.qrReader.classList.add("hidden");
    el.qrReader.classList.remove("qr-flash-sucesso");
    atualizarBotaoCamera();
    ultimoCodigoLido = null;
    ultimoTimestampLeitura = 0;
    if (!scanner) return;
    try {
      if (scanner.isScanning) {
        await scanner.stop();
      }
    } catch (_) {}
  }

  function alternarCamera() {
    try {
      if (!audioContextGlobal) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) audioContextGlobal = new AudioCtx();
      }
      if (audioContextGlobal && audioContextGlobal.state === "suspended") {
        audioContextGlobal.resume();
      }
    } catch (_) {}

    if (estado.cameraAtiva) pararCamera();
    else iniciarCamera();
  }

  async function aoLerCodigo(decodedText) {
    if (!decodedText || estado.buscandoCodigo) return;

    const agora = Date.now();
    const tempoDecorrido = agora - ultimoTimestampLeitura;

    // REGRA A (Mesma Peça): Se decodedText === ultimoCodigoLido e tempoDecorrido < 4500 (4,5 segundos), IGNORE silenciosamente
    if (decodedText === ultimoCodigoLido && tempoDecorrido < 4500) {
      return;
    }

    // REGRA B (Peça Diferente): Se decodedText !== ultimoCodigoLido e tempoDecorrido < 2000 (2 segundos), IGNORE
    if (decodedText !== ultimoCodigoLido && tempoDecorrido < 2000) {
      return;
    }

    const codigo = normalizarCodigoLido(decodedText);
    if (!codigo) return;

    // Atualiza controle da trava anti-duplicação
    ultimoCodigoLido = decodedText;
    ultimoTimestampLeitura = agora;

    // Feedback sensorial triplo (Haptic, Bipe, Flash Verde)
    dispararFeedbackLeitura();

    await adicionarPorCodigo(codigo);
  }

  // -------------------------------------------------------
  // CARRINHO
  // -------------------------------------------------------
  async function adicionarPorCodigo(codigo) {
    const codigoLimpo = String(codigo || "").trim();
    if (!codigoLimpo) {
      toast("Informe o código da etiqueta.", "erro");
      return false;
    }

    const chave = chaveCarrinho(codigoLimpo);
    const existente = estado.carrinho.get(chave);

    if (existente) {
      if (existente.quantidade + 1 > existente.estoque) {
        toast(`Estoque máximo atingido: ${existente.estoque} un. de ${existente.modelo_nome} (${existente.tamanho}).`, "erro", 3000);
        return false;
      }
      existente.quantidade += 1;
      renderizarCarrinho();
      toast(`+1 ${existente.modelo_nome} (${existente.tamanho}) — ${existente.quantidade} no carrinho`, "sucesso", 1600);
      return true;
    }

    estado.buscandoCodigo = true;
    try {
      const dados = await api(`/api/qrcode/${encodeURIComponent(codigoLimpo)}`);
      const item = dados && dados.item ? dados.item : dados;
      if (!item || (!item.variacao_id && !item.id)) {
        throw new ErroApi("Peça não encontrada.", 404);
      }

      const estoque = num(item.estoque);
      if (estoque <= 0) {
        toast(`${item.modelo_nome} (${item.tamanho}) está sem estoque.`, "erro", 3000);
        return false;
      }

      const codigoReal = item.codigo_barras || codigoLimpo;
      const chaveReal = chaveCarrinho(codigoReal);
      const jaExiste = estado.carrinho.get(chaveReal);
      if (jaExiste) {
        if (jaExiste.quantidade + 1 > estoque) {
          toast(`Estoque máximo atingido: ${estoque} un.`, "erro", 3000);
          return false;
        }
        jaExiste.quantidade += 1;
        jaExiste.estoque = estoque;
      } else {
        estado.carrinho.set(chaveReal, {
          variacao_id: item.variacao_id ?? item.id,
          produto_id: item.produto_id,
          codigo_barras: codigoReal,
          modelo_nome: item.modelo_nome || "Peça",
          marca: item.marca || "",
          tamanho: item.tamanho || "",
          cor: item.cor || "",
          cor_hex: item.cor_hex || "",
          preco_venda: num(item.preco_venda),
          estoque,
          quantidade: 1,
        });
      }

      renderizarCarrinho();
      toast(`${item.modelo_nome} (${item.tamanho}) adicionada — ${brl(item.preco_venda)}`, "sucesso", 1800);
      return true;
    } catch (erro) {
      if (erro.status !== 401) {
        const msg = erro.status === 404 ? `Código "${codigoLimpo}" não encontrado.` : erro.message;
        toast(msg, "erro", 3000);
      }
      return false;
    } finally {
      estado.buscandoCodigo = false;
    }
  }

  function alterarQuantidade(chave, delta) {
    const item = estado.carrinho.get(chave);
    if (!item) return;

    const novaQtd = item.quantidade + delta;
    if (novaQtd <= 0) {
      estado.carrinho.delete(chave);
      toast(`${item.modelo_nome} removida do carrinho.`, "info", 1500);
    } else if (novaQtd > item.estoque) {
      toast(`Apenas ${item.estoque} un. disponíveis desta variação.`, "erro", 2500);
      return;
    } else {
      item.quantidade = novaQtd;
    }
    renderizarCarrinho();
  }

  function limparCarrinho(confirmar = true) {
    if (!estado.carrinho.size) return;
    if (confirmar && !window.confirm("Remover todos os itens do carrinho?")) return;
    estado.carrinho.clear();
    renderizarCarrinho();
  }

  function calcularTotais() {
    let subtotal = 0;
    let quantidadeTotal = 0;
    estado.carrinho.forEach((item) => {
      subtotal += item.preco_venda * item.quantidade;
      quantidadeTotal += item.quantidade;
    });
    subtotal = arred(subtotal);
    const descontoDigitado = Math.max(0, num(el.inputDesconto.value));
    const desconto = arred(Math.min(descontoDigitado, subtotal));
    const total = arred(subtotal - desconto);
    return { subtotal, desconto, total, quantidadeTotal };
  }

  function atualizarResumo() {
    const { subtotal, desconto, total, quantidadeTotal } = calcularTotais();
    el.valorSubtotal.textContent = brl(subtotal);
    el.valorDesconto.textContent = `- ${brl(desconto)}`;
    el.valorTotal.textContent = brl(total);

    const txtBadge = quantidadeTotal > 99 ? "99+" : String(quantidadeTotal);
    if (quantidadeTotal > 0) {
      el.badgeCarrinho.textContent = txtBadge;
      el.badgeCarrinho.classList.remove("hidden");
      if (el.badgeCarrinhoPc) {
        el.badgeCarrinhoPc.textContent = txtBadge;
        el.badgeCarrinhoPc.classList.remove("hidden");
      }
    } else {
      el.badgeCarrinho.classList.add("hidden");
      if (el.badgeCarrinhoPc) el.badgeCarrinhoPc.classList.add("hidden");
    }

    el.btnFinalizarVenda.disabled = quantidadeTotal === 0 || estado.vendaEmAndamento;
  }

  function renderizarCarrinho() {
    if (!estado.carrinho.size) {
      el.listaCarrinho.innerHTML = '<p class="vazio">Nenhum item no carrinho. Escaneie ou clique numa peça.</p>';
      atualizarResumo();
      return;
    }

    const html = Array.from(estado.carrinho.entries())
      .map(([chave, item]) => {
        const detalhes = [item.marca, item.tamanho ? `Tam ${item.tamanho}` : "", item.cor]
          .filter((x) => x && String(x).trim())
          .join(" · ");
        const chaveAttr = escapeHtml(chave);
        return `
          <div class="item-carrinho">
            <div class="item-carrinho-info">
              <div class="item-carrinho-nome">${escapeHtml(item.modelo_nome)}</div>
              <div class="item-carrinho-detalhe">${escapeHtml(detalhes)}</div>
              <div class="item-carrinho-detalhe">Cód: ${escapeHtml(item.codigo_barras)} · Estoque: ${item.estoque}</div>
              <div class="item-carrinho-preco">${brl(item.preco_venda)} × ${item.quantidade} = ${brl(item.preco_venda * item.quantidade)}</div>
            </div>
            <div class="controle-qtd">
              <button type="button" class="btn-qtd menos" data-acao="menos" data-chave="${chaveAttr}" aria-label="Diminuir">−</button>
              <span class="qtd-valor">${item.quantidade}</span>
              <button type="button" class="btn-qtd mais" data-acao="mais" data-chave="${chaveAttr}" aria-label="Aumentar"${item.quantidade >= item.estoque ? ' disabled style="opacity:.4"' : ""}>+</button>
            </div>
          </div>`;
      })
      .join("");

    el.listaCarrinho.innerHTML = html;
    atualizarResumo();
  }

  // -------------------------------------------------------
  // FORMA DE PAGAMENTO
  // -------------------------------------------------------
  function formaPagamentoSelecionada() {
    const marcado = el.grupoPagamento.querySelector('input[name="forma_pagamento"]:checked');
    return marcado ? marcado.value : "DINHEIRO";
  }

  function selecionarFormaPagamento(valor) {
    const radio = el.grupoPagamento.querySelector(`input[name="forma_pagamento"][value="${valor}"]`);
    if (radio) radio.checked = true;
    atualizarVisibilidadeCliente();
  }

  function atualizarVisibilidadeCliente() {
    const ehFiado = formaPagamentoSelecionada() === "FIADO";
    el.wrapClienteVenda.classList.toggle("hidden", !ehFiado);
    el.selectClienteVenda.classList.toggle("hidden", !ehFiado);
    el.selectClienteVenda.required = ehFiado;
    if (ehFiado && !estado.clientesCarregados) {
      carregarClientes();
    }
  }

  function popularSelectClientes() {
    const selecionadoAntes = el.selectClienteVenda.value;
    const opcoes = ['<option value="">Selecione o cliente...</option>'];
    estado.clientes
      .slice()
      .sort((a, b) => String(a.nome).localeCompare(String(b.nome), "pt-BR"))
      .forEach((c) => {
        const disponivel = disponivelCliente(c);
        const rotulo = `${c.nome} — Disp. ${brl(disponivel)}${c.saldo_devedor > 0 ? ` (deve ${brl(c.saldo_devedor)})` : ""}`;
        opcoes.push(`<option value="${escapeHtml(c.id)}">${escapeHtml(rotulo)}</option>`);
      });
    el.selectClienteVenda.innerHTML = opcoes.join("");
    if (selecionadoAntes && estado.clientes.some((c) => String(c.id) === selecionadoAntes)) {
      el.selectClienteVenda.value = selecionadoAntes;
    }
  }

  // -------------------------------------------------------
  // FINALIZAR VENDA
  // -------------------------------------------------------
  async function finalizarVenda() {
    if (estado.vendaEmAndamento) return;
    if (!estado.carrinho.size) {
      toast("O carrinho está vazio.", "erro");
      return;
    }

    const forma = formaPagamentoSelecionada();
    const { subtotal, desconto, total } = calcularTotais();
    let clienteId = null;
    let cliente = null;

    if (forma === "FIADO") {
      clienteId = parseInt(el.selectClienteVenda.value, 10);
      if (!clienteId) {
        toast("Selecione o cliente para vender no Fiado.", "erro", 3000);
        el.selectClienteVenda.focus();
        return;
      }
      cliente = estado.clientes.find((c) => Number(c.id) === clienteId) || null;
      if (cliente) {
        const disponivel = disponivelCliente(cliente);
        if (total > disponivel) {
          const continuar = window.confirm(
            `Atenção: ${cliente.nome} tem apenas ${brl(disponivel)} de limite disponível.\n` +
              `Esta compra é de ${brl(total)}.\n\nDeseja lançar mesmo assim?`
          );
          if (!continuar) return;
        }
      }
    }

    const qtdPecas = Array.from(estado.carrinho.values()).reduce((s, i) => s + i.quantidade, 0);
    const resumo =
      `Confirmar venda de ${qtdPecas} peça(s)?\n\n` +
      `Subtotal: ${brl(subtotal)}\n` +
      (desconto > 0 ? `Desconto: - ${brl(desconto)}\n` : "") +
      `Total: ${brl(total)}\n` +
      `Pagamento: ${forma}${cliente ? ` (${cliente.nome})` : ""}`;
    if (!window.confirm(resumo)) return;

    const corpo = {
      itens: Array.from(estado.carrinho.values()).map((i) => ({
        codigo_barras: i.codigo_barras,
        quantidade: i.quantidade,
      })),
      desconto_total: desconto,
      forma_pagamento: forma,
      cliente_id: forma === "FIADO" ? clienteId : null,
    };

    estado.vendaEmAndamento = true;
    el.btnFinalizarVenda.disabled = true;
    try {
      const dados = await api("/api/vendas", { metodo: "POST", corpo, comLoader: true });
      const cobrado = num(dados.total_cobrado ?? dados.valor_total, total);

      pararCamera();
      estado.carrinho.clear();
      el.inputDesconto.value = "";
      el.selectClienteVenda.value = "";
      selecionarFormaPagamento("DINHEIRO");
      renderizarCarrinho();
      vibrar(120);
      toast(`Venda finalizada! Total: ${brl(cobrado)}`, "sucesso", 3200);

      await Promise.all([
        carregarEstoque(el.inputBuscaEstoque ? el.inputBuscaEstoque.value.trim() : ""),
        carregarClientesFiado(),
        carregarResumoFinanceiro(),
        carregarVendasHoje(),
      ]);
    } catch (erro) {
      if (erro.status !== 401) toast(erro.message || "Erro ao finalizar a venda.", "erro", 4000);
    } finally {
      estado.vendaEmAndamento = false;
      atualizarResumo();
    }
  }

  // -------------------------------------------------------
  // MODAL DE PRODUTO (CRIAR / EDITAR) & ETIQUETAS QR
  // -------------------------------------------------------
  function adicionarLinhaVariacaoForm(v = {}) {
    const div = document.createElement("div");
    div.className = "linha-variacao-form";
    div.dataset.vid = v.id || "";
    div.innerHTML = `
      <input type="text" class="var-tam" placeholder="Tam (M)" value="${escapeHtml(v.tamanho || "M")}" title="Tamanho" required>
      <input type="text" class="var-cor" placeholder="Cor (Preto)" value="${escapeHtml(v.cor || "")}" title="Nome da Cor">
      <input type="color" class="var-hex" value="${hexValido(v.cor_hex) ? v.cor_hex.trim() : "#3b82f6"}" title="Cor Visual">
      <input type="number" class="var-custo" placeholder="Custo R$" step="0.01" min="0" value="${v.preco_custo !== undefined ? v.preco_custo : ""}" title="Preço de Custo">
      <input type="number" class="var-venda" placeholder="Venda R$" step="0.01" min="0" value="${v.preco_venda !== undefined ? v.preco_venda : ""}" title="Preço de Venda" required>
      <input type="number" class="var-est" placeholder="Estoque" step="1" min="0" value="${v.estoque !== undefined ? v.estoque : 1}" title="Quantidade em Estoque" required>
      <button type="button" class="btn btn-secundario btn-sm texto-perigo btn-rem-var" title="Remover tamanho">&times;</button>
    `;
    div.querySelector(".btn-rem-var").addEventListener("click", () => {
      if (el.listaVariacoesForm.children.length <= 1) {
        toast("O produto precisa ter pelo menos um tamanho.", "erro");
        return;
      }
      div.remove();
    });
    el.listaVariacoesForm.appendChild(div);
  }

  function abrirModalNovoProduto() {
    el.produtoEditId.value = "";
    el.modalProdutoTitulo.textContent = "Cadastrar Novo Produto";
    el.prodModelo.value = "";
    el.prodMarca.value = "";
    el.prodTecido.value = "";
    el.prodCorte.value = "";
    el.listaVariacoesForm.innerHTML = "";
    ["P", "M", "G"].forEach((tam) =>
      adicionarLinhaVariacaoForm({ tamanho: tam, cor: "Preto", cor_hex: "#111827", preco_custo: 0, preco_venda: 99.9, estoque: 1 })
    );
    el.modalProduto.classList.remove("hidden");
    setTimeout(() => el.prodModelo.focus(), 150);
  }

  function abrirModalEditarProduto(produtoId) {
    const prod = estado.produtos.find((p) => String(p.id) === String(produtoId));
    if (!prod) return;

    el.produtoEditId.value = prod.id;
    el.modalProdutoTitulo.textContent = `Editar: ${prod.modelo_nome}`;
    el.prodModelo.value = prod.modelo_nome || "";
    el.prodMarca.value = prod.marca || "";
    el.prodTecido.value = prod.tecido || "";
    el.prodCorte.value = prod.corte || "";
    el.listaVariacoesForm.innerHTML = "";

    const vars = Array.isArray(prod.variacoes) && prod.variacoes.length ? prod.variacoes : [{ tamanho: "U", estoque: 0, preco_venda: prod.preco_venda || 0 }];
    vars.forEach((v) => adicionarLinhaVariacaoForm(v));
    el.modalProduto.classList.remove("hidden");
  }

  async function salvarProduto(evento) {
    evento.preventDefault();
    const editId = el.produtoEditId.value.trim();
    const modelo_nome = el.prodModelo.value.trim();
    if (!modelo_nome) {
      toast("Informe o nome/modelo da peça.", "erro");
      return;
    }

    const linhas = Array.from(el.listaVariacoesForm.querySelectorAll(".linha-variacao-form"));
    const variacoes = linhas.map((div) => ({
      id: div.dataset.vid ? parseInt(div.dataset.vid, 10) : null,
      tamanho: div.querySelector(".var-tam").value.trim().toUpperCase() || "U",
      cor: div.querySelector(".var-cor").value.trim(),
      cor_hex: div.querySelector(".var-hex").value || "#3b82f6",
      preco_custo: num(div.querySelector(".var-custo").value),
      preco_venda: num(div.querySelector(".var-venda").value),
      estoque: Math.max(0, parseInt(div.querySelector(".var-est").value, 10) || 0),
    }));

    const corpo = {
      modelo_nome,
      marca: el.prodMarca.value.trim(),
      tecido: el.prodTecido.value.trim(),
      corte: el.prodCorte.value.trim(),
      variacoes,
    };

    try {
      const caminho = editId ? `/api/estoque/produto/${editId}` : "/api/estoque/produto";
      const metodo = editId ? "PUT" : "POST";
      const res = await api(caminho, { metodo, corpo, comLoader: true });
      el.modalProduto.classList.add("hidden");
      toast(res.mensagem || "Produto salvo com sucesso!", "sucesso");
      carregarEstoque(el.inputBuscaEstoque.value.trim());
    } catch (erro) {
      toast(erro.message || "Erro ao salvar produto.", "erro", 3500);
    }
  }

  async function confirmarExclusaoProduto(produtoId) {
    const prod = estado.produtos.find((p) => String(p.id) === String(produtoId));
    if (!prod) return;
    if (!window.confirm(`Deseja realmente excluir "${prod.modelo_nome}" e todas as suas variações?`)) return;

    try {
      const res = await api(`/api/estoque/produto/${prod.id}`, { metodo: "DELETE", comLoader: true });
      toast(res.mensagem || "Produto excluído.", "sucesso");
      carregarEstoque(el.inputBuscaEstoque.value.trim());
    } catch (erro) {
      toast(erro.message || "Erro ao excluir produto.", "erro");
    }
  }

  function abrirModalEtiquetas(produtoId) {
    const prod = estado.produtos.find((p) => String(p.id) === String(produtoId));
    if (!prod) return;

    el.modalEtiquetasTitulo.textContent = `Etiquetas QR — ${prod.modelo_nome}`;
    const vars = Array.isArray(prod.variacoes) ? prod.variacoes : [];

    if (!vars.length) {
      el.areaImpressaoEtiquetas.innerHTML = '<p class="vazio">Sem variações cadastradas.</p>';
    } else {
      el.areaImpressaoEtiquetas.innerHTML = vars
        .map((v) => {
          const codigo = v.codigo_barras || `KNB${String(prod.id).padStart(5, "0")}${String(v.id).padStart(4, "0")}`;
          const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=4&data=${encodeURIComponent(codigo)}`;
          return `
            <div class="etiqueta-card">
              <div class="etiqueta-loja">KANEMBERG</div>
              <div class="etiqueta-modelo">${escapeHtml(prod.modelo_nome)}</div>
              <div class="etiqueta-detalhe">Tam: ${escapeHtml(v.tamanho)} ${v.cor ? `· ${escapeHtml(v.cor)}` : ""}</div>
              <img class="etiqueta-qr" src="${qrUrl}" alt="QR ${escapeHtml(codigo)}">
              <div class="etiqueta-codigo">${escapeHtml(codigo)}</div>
              <div class="etiqueta-preco">${brl(v.preco_venda || prod.preco_venda)}</div>
            </div>`;
        })
        .join("");
    }
    el.modalEtiquetas.classList.remove("hidden");
  }

  // -------------------------------------------------------
  // ABA FIADO
  // -------------------------------------------------------
  function disponivelCliente(c) {
    if (c.disponivel !== undefined && c.disponivel !== null) return arred(num(c.disponivel));
    return arred(Math.max(0, num(c.limite_credito) - Math.max(0, num(c.saldo_devedor))));
  }

  function normalizarCliente(c) {
    const historicoBruto = c.historico || c.ultimos_lancamentos || c.lancamentos || [];
    return {
      id: c.id,
      nome: c.nome || "Sem nome",
      telefone: c.telefone || "",
      limite_credito: num(c.limite_credito),
      saldo_devedor: arred(num(c.saldo_devedor)),
      disponivel: c.disponivel,
      historico: (Array.isArray(historicoBruto) ? historicoBruto : []).map((h) => ({
        tipo: String(h.tipo_movimentacao || h.tipo || "").toUpperCase(),
        valor: num(h.valor),
        data: h.data_movimentacao || h.data || "",
        descricao: h.descricao || h.obs || h.observacao || "",
      })),
    };
  }

  async function carregarClientes() {
    if (!estado.clientes.length) {
      el.listaFiado.innerHTML = '<p class="vazio">Carregando clientes...</p>';
    }
    try {
      const dados = await api(`/api/fiado/clientes?_t=${Date.now()}`);
      estado.clientes = extrairLista(dados, "clientes").map(normalizarCliente);
      estado.clientesCarregados = true;
      renderizarFiado();
      popularSelectClientes();
    } catch (erro) {
      if (erro.status === 401) return;
      el.listaFiado.innerHTML = `<p class="vazio">${escapeHtml(erro.message)}</p>`;
    }
  }

  const carregarClientesFiado = carregarClientes;

  function renderizarFiado() {
    const totalAbertoGeral = arred(estado.clientes.reduce((s, c) => s + Math.max(0, c.saldo_devedor), 0));
    const devedoresGeral = estado.clientes.filter((c) => c.saldo_devedor > 0).length;
    const disponivelGeral = arred(estado.clientes.reduce((s, c) => s + disponivelCliente(c), 0));

    if (el.kpisFiado) {
      el.kpisFiado.innerHTML = `
        <div class="kpi-box">
          <small>Total em Aberto na Loja</small>
          <strong class="texto-perigo">${brl(totalAbertoGeral)}</strong>
        </div>
        <div class="kpi-box">
          <small>Clientes Devedores</small>
          <strong>${devedoresGeral} de ${estado.clientes.length}</strong>
        </div>
        <div class="kpi-box">
          <small>Crédito Disponível Total</small>
          <strong class="texto-sucesso">${brl(disponivelGeral)}</strong>
        </div>
      `;
    }

    const termo = el.inputBuscaFiado.value.trim().toLowerCase();
    const tokens = termo ? termo.split(/\s+/) : [];

    let clientes = estado.clientes.filter((c) => {
      if (!tokens.length) return true;
      const alvo = `${c.nome} ${c.telefone}`.toLowerCase();
      return tokens.every((t) => alvo.includes(t));
    });

    clientes = clientes.sort((a, b) => {
      if (b.saldo_devedor !== a.saldo_devedor) return b.saldo_devedor - a.saldo_devedor;
      return String(a.nome).localeCompare(String(b.nome), "pt-BR");
    });

    if (!clientes.length) {
      el.listaFiado.innerHTML = tokens.length
        ? `<p class="vazio">Nenhum cliente encontrado para "${escapeHtml(termo)}".</p>`
        : '<p class="vazio">Nenhum cliente cadastrado.</p>';
      return;
    }

    const cards = clientes
      .map((c) => {
        const devedor = c.saldo_devedor > 0;
        const disponivel = disponivelCliente(c);
        const usoPct = c.limite_credito > 0 ? Math.min(100, (Math.max(0, c.saldo_devedor) / c.limite_credito) * 100) : devedor ? 100 : 0;
        let classeBarra = "";
        if (usoPct >= 100) classeBarra = "estourado";
        else if (usoPct >= 75) classeBarra = "alerta";

        const extratoAberto = estado.extratosAbertos.has(String(c.id));
        const historicoVisivel = extratoAberto ? c.historico : c.historico.slice(0, LIMITE_EXTRATO_VISIVEL);
        const extratoHtml = c.historico.length
          ? `
            <div class="extrato">
              ${historicoVisivel
                .map((h) => {
                  const ehDebito = h.tipo === "DEBITO";
                  return `
                    <div class="extrato-item">
                      <span class="extrato-item-desc">${escapeHtml(formatarData(h.data))} · ${escapeHtml(h.descricao || (ehDebito ? "Compra" : "Pagamento"))}</span>
                      <span class="extrato-item-valor ${ehDebito ? "debito" : "credito"}">${ehDebito ? "+" : "−"} ${brl(h.valor)}</span>
                    </div>`;
                })
                .join("")}
              ${
                c.historico.length > LIMITE_EXTRATO_VISIVEL
                  ? `<button type="button" class="btn-link" data-acao="extrato" data-id="${escapeHtml(c.id)}">${extratoAberto ? "Ver menos" : `Ver últimos ${c.historico.length} lançamentos`}</button>`
                  : ""
              }
            </div>`
          : "";

        const telefoneLimpo = String(c.telefone).replace(/\D/g, "");
        const botaoWhats =
          telefoneLimpo && devedor
            ? `<a class="btn btn-secundario" href="https://wa.me/55${escapeHtml(telefoneLimpo.replace(/^55/, ""))}?text=${encodeURIComponent(
                `Olá ${c.nome}! Passando para lembrar do seu saldo em aberto na Kanemberg: ${brl(c.saldo_devedor)}.`
              )}" target="_blank" rel="noopener" style="flex:0 0 auto;text-decoration:none">WhatsApp</a>`
            : "";

        const svgTrashCli = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;
        const botaoExcluir = !devedor
          ? `<button type="button" class="btn btn-secundario texto-perigo" data-acao="excluir-cliente" data-id="${escapeHtml(c.id)}" style="flex:0 0 42px" title="Remover cliente">${svgTrashCli}</button>`
          : "";

        return `
          <article class="card-cliente ${devedor ? "devedor" : "em-dia"}">
            <div>
              <div class="card-cliente-topo">
                <div>
                  <div class="card-cliente-nome">${escapeHtml(c.nome)}</div>
                  ${c.telefone ? `<div class="card-cliente-tel">${escapeHtml(c.telefone)}</div>` : ""}
                </div>
                <div class="card-cliente-saldo">
                  <small>${devedor ? "Saldo devedor" : "Em dia"}</small>
                  <strong>${brl(Math.max(0, c.saldo_devedor))}</strong>
                </div>
              </div>

              <div class="card-cliente-limite">
                <div class="limite-texto">
                  <span>Disponível: <strong>${brl(disponivel)}</strong></span>
                  <span>Limite: ${brl(c.limite_credito)}</span>
                </div>
                <div class="barra-limite">
                  <div class="barra-limite-preenchida ${classeBarra}" style="width:${usoPct.toFixed(1)}%"></div>
                </div>
              </div>

              <div class="card-cliente-acoes">
                <button type="button" class="btn ${devedor ? "btn-sucesso" : "btn-secundario"}" data-acao="pagar" data-id="${escapeHtml(c.id)}" ${devedor ? "" : "disabled"}>
                  Receber Pagamento
                </button>
                ${botaoWhats}
                ${botaoExcluir}
              </div>
              ${extratoHtml}
            </div>
          </article>`;
      })
      .join("");

    el.listaFiado.innerHTML = cards;
  }

  // -------------------------------------------------------
  // MODAL DE NOVO CLIENTE & PAGAMENTO (FIADO)
  // -------------------------------------------------------
  function abrirModalNovoCliente() {
    el.cliNome.value = "";
    el.cliTelefone.value = "";
    el.cliLimite.value = "500";
    el.cliDia.value = "5";
    el.modalCliente.classList.remove("hidden");
    setTimeout(() => el.cliNome.focus(), 150);
  }

  async function salvarNovoCliente(evento) {
    evento.preventDefault();
    const nome = el.cliNome.value.trim();
    if (!nome) {
      toast("Digite o nome do cliente.", "erro");
      return;
    }

    try {
      const res = await api("/api/fiado/clientes", {
        metodo: "POST",
        corpo: {
          nome,
          telefone: el.cliTelefone.value.trim(),
          limite_credito: num(el.cliLimite.value, 500),
          dia_preferencial_pagamento: parseInt(el.cliDia.value, 10) || 5,
        },
        comLoader: true,
      });
      el.modalCliente.classList.add("hidden");
      toast(res.mensagem || "Cliente cadastrado!", "sucesso");
      carregarClientes();
    } catch (erro) {
      toast(erro.message || "Erro ao cadastrar cliente.", "erro");
    }
  }

  async function confirmarExclusaoCliente(clienteId) {
    const cli = estado.clientes.find((c) => String(c.id) === String(clienteId));
    if (!cli) return;
    if (!window.confirm(`Deseja remover o cadastro de "${cli.nome}"?`)) return;

    try {
      const res = await api(`/api/fiado/clientes/${cli.id}`, { metodo: "DELETE", comLoader: true });
      toast(res.mensagem || "Cliente removido.", "sucesso");
      carregarClientes();
    } catch (erro) {
      toast(erro.message || "Erro ao remover cliente.", "erro");
    }
  }

  function abrirModalPagamento(clienteId) {
    const cliente = estado.clientes.find((c) => String(c.id) === String(clienteId));
    if (!cliente) {
      toast("Cliente não encontrado.", "erro");
      return;
    }
    el.modalClienteId.value = cliente.id;
    el.modalClienteNome.textContent = cliente.nome;
    el.modalClienteSaldo.textContent = brl(Math.max(0, cliente.saldo_devedor));
    el.inputValorPagamento.value = "";
    el.inputValorPagamento.max = Math.max(0, cliente.saldo_devedor).toFixed(2);
    el.inputValorPagamento.placeholder = `Total: ${Math.max(0, cliente.saldo_devedor).toFixed(2).replace(".", ",")}`;
    el.inputObsPagamento.value = "";
    el.modalPagamento.classList.remove("hidden");
    setTimeout(() => el.inputValorPagamento.focus(), 200);
  }

  function fecharModalPagamento() {
    el.modalPagamento.classList.add("hidden");
    el.inputValorPagamento.blur();
    el.inputObsPagamento.blur();
  }

  function fecharTodosModais() {
    fecharModalPagamento();
    if (el.modalProduto) el.modalProduto.classList.add("hidden");
    if (el.modalCliente) el.modalCliente.classList.add("hidden");
    if (el.modalEtiquetas) el.modalEtiquetas.classList.add("hidden");
  }

  async function confirmarPagamento(evento) {
    evento.preventDefault();
    if (estado.pagamentoEmAndamento) return;

    const clienteId = parseInt(el.modalClienteId.value, 10);
    const cliente = estado.clientes.find((c) => Number(c.id) === clienteId);
    const valor = arred(num(el.inputValorPagamento.value));

    if (!clienteId || !cliente) {
      toast("Cliente inválido.", "erro");
      return;
    }
    if (valor <= 0) {
      toast("Digite um valor maior que zero.", "erro");
      el.inputValorPagamento.focus();
      return;
    }
    if (valor > cliente.saldo_devedor + 0.001) {
      toast(`O valor excede o saldo devedor (${brl(cliente.saldo_devedor)}).`, "erro", 3000);
      el.inputValorPagamento.focus();
      return;
    }

    const quitacao = Math.abs(valor - cliente.saldo_devedor) < 0.01;
    const descricao =
      el.inputObsPagamento.value.trim() ||
      (quitacao ? "Quitação total no Caixa" : "Pagamento parcial no Caixa");

    estado.pagamentoEmAndamento = true;
    el.btnConfirmarPagamento.disabled = true;
    el.btnConfirmarPagamento.textContent = "Salvando...";
    try {
      const dados = await api("/api/fiado/pagar", {
        metodo: "POST",
        corpo: { cliente_id: clienteId, valor, descricao },
        comLoader: true,
      });
      fecharModalPagamento();
      vibrar(100);
      toast(dados && dados.mensagem ? dados.mensagem : `Pagamento de ${brl(valor)} registrado.`, "sucesso", 3000);
      await Promise.all([
        carregarEstoque(el.inputBuscaEstoque ? el.inputBuscaEstoque.value.trim() : ""),
        carregarClientesFiado(),
        carregarResumoFinanceiro(),
        carregarVendasHoje(),
      ]);
    } catch (erro) {
      if (erro.status !== 401) toast(erro.message || "Erro ao registrar pagamento.", "erro", 4000);
    } finally {
      estado.pagamentoEmAndamento = false;
      el.btnConfirmarPagamento.disabled = false;
      el.btnConfirmarPagamento.textContent = "Confirmar";
    }
  }

  // -------------------------------------------------------
  // LEITOR DE CÓDIGO DE BARRAS USB GLOBAL & ATALHOS PC
  // -------------------------------------------------------
  function tratarTecladoGlobal(e) {
    if (!estado.token) return;

    // Atalhos rápidos de função no PC
    if (e.key === "F1") {
      e.preventDefault();
      trocarAba("aba-estoque");
      return;
    }
    if (e.key === "F2") {
      e.preventDefault();
      trocarAba("aba-vender");
      return;
    }
    if (e.key === "F3") {
      e.preventDefault();
      trocarAba("aba-fiado");
      return;
    }
    if (e.key === "F4" && estado.role === "admin") {
      e.preventDefault();
      trocarAba("tab-caixa");
      return;
    }
    if (e.key === "F9" && estado.abaAtual === "aba-vender") {
      e.preventDefault();
      finalizarVenda();
      return;
    }
    if (e.key === "Escape") {
      fecharTodosModais();
      return;
    }

    // Bipe Global USB (ignora se o foco estiver dentro de um input/select/textarea)
    const tag = (e.target && e.target.tagName ? e.target.tagName : "").toUpperCase();
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;

    const agora = performance.now();
    if (agora - estado.bipeUltimoTempo > 80) {
      estado.bipeBuffer = "";
    }
    estado.bipeUltimoTempo = agora;

    if (e.key === "Enter") {
      if (estado.bipeBuffer.length >= 4) {
        e.preventDefault();
        const codBipado = normalizarCodigoLido(estado.bipeBuffer);
        estado.bipeBuffer = "";
        if (codBipado) {
          trocarAba("aba-vender");
          adicionarPorCodigo(codBipado);
        }
      }
      estado.bipeBuffer = "";
    } else if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
      estado.bipeBuffer += e.key;
    }
  }

  // -------------------------------------------------------
  // EVENTOS
  // -------------------------------------------------------
  function registrarEventos() {
    // Login / Logout
    el.formLogin.addEventListener("submit", fazerLogin);
    const acaoSair = () => {
      if (estado.carrinho.size && !window.confirm("Há itens no carrinho. Deseja sair mesmo assim?")) return;
      encerrarSessao();
      el.loginErro.classList.add("hidden");
    };
    el.btnSair.addEventListener("click", acaoSair);
    if (el.btnSairPc) el.btnSairPc.addEventListener("click", acaoSair);

    // Abas (Mobile + PC Sidebar)
    Object.entries(el.tabs).forEach(([abaId, botao]) => {
      if (botao) botao.addEventListener("click", () => trocarAba(abaId));
    });
    el.sidebarBtns.forEach((btn) => {
      btn.addEventListener("click", () => trocarAba(btn.dataset.aba));
    });

    // Caixa / Ganhos: botão atualizar
    if (el.btnAtualizarCaixa) {
      el.btnAtualizarCaixa.addEventListener("click", () => {
        carregarResumoFinanceiro();
        toast("Resumo financeiro atualizado!", "info", 1800);
      });
    }

    // Estoque: busca + barra única combinável de filtros + cliques nos cards
    el.inputBuscaEstoque.addEventListener("input", buscarEstoqueDebounced);
    el.inputBuscaEstoque.addEventListener("search", buscarEstoqueDebounced);
    if (el.filtrosEstoque) {
      el.filtrosEstoque.addEventListener("click", (e) => {
        const btnLimpar = e.target.closest('button[data-acao-filtro="limpar"]');
        if (btnLimpar) {
          estado.filtroGrupoEstoque = "todos";
          estado.filtroEstoque = "todos";
          atualizarUiFiltrosEstoque();
          renderizarEstoque();
          return;
        }

        const btnGrupo = e.target.closest("button[data-grupo]");
        if (btnGrupo) {
          const g = btnGrupo.dataset.grupo;
          estado.filtroGrupoEstoque = estado.filtroGrupoEstoque === g ? "todos" : g;
          atualizarUiFiltrosEstoque();
          renderizarEstoque();
          return;
        }

        const btnStatus = e.target.closest("button[data-filtro]");
        if (btnStatus) {
          const f = btnStatus.dataset.filtro;
          estado.filtroEstoque = estado.filtroEstoque === f ? "todos" : f;
          atualizarUiFiltrosEstoque();
          renderizarEstoque();
        }
      });
    }
    el.listaEstoque.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-acao]");
      if (!btn) return;
      const acao = btn.dataset.acao;
      if (acao === "vender-variacao") {
        const codigo = btn.dataset.codigo;
        if (codigo) await adicionarPorCodigo(codigo);
      } else if (acao === "editar-produto") {
        abrirModalEditarProduto(btn.dataset.id);
      } else if (acao === "excluir-produto") {
        confirmarExclusaoProduto(btn.dataset.id);
      } else if (acao === "etiquetas-produto") {
        abrirModalEtiquetas(btn.dataset.id);
      }
    });

    // Modal de Produto & Etiquetas
    if (el.btnNovoProduto) el.btnNovoProduto.addEventListener("click", abrirModalNovoProduto);
    if (el.btnAddVariacao) el.btnAddVariacao.addEventListener("click", () => adicionarLinhaVariacaoForm({ tamanho: "M", estoque: 1, preco_venda: 99.9 }));
    if (el.btnCancelarProduto) el.btnCancelarProduto.addEventListener("click", () => el.modalProduto.classList.add("hidden"));
    if (el.formProduto) el.formProduto.addEventListener("submit", salvarProduto);
    if (el.btnFecharEtiquetas) el.btnFecharEtiquetas.addEventListener("click", () => el.modalEtiquetas.classList.add("hidden"));
    if (el.btnImprimirEtiquetas) el.btnImprimirEtiquetas.addEventListener("click", () => window.print());

    // Câmera & Código manual
    el.btnCamera.addEventListener("click", alternarCamera);
    el.formCodigoManual.addEventListener("submit", async (e) => {
      e.preventDefault();
      const codigo = normalizarCodigoLido(el.inputCodigoManual.value);
      if (!codigo) {
        toast("Digite o código da etiqueta.", "erro");
        return;
      }
      const ok = await adicionarPorCodigo(codigo);
      if (ok) el.inputCodigoManual.value = "";
    });

    // Catálogo Rápido dentro do PDV
    if (el.inputBuscaCatalogoPdv) {
      el.inputBuscaCatalogoPdv.addEventListener("input", debounce(renderizarCatalogoPdv, 200));
    }
    if (el.listaCatalogoPdv) {
      el.listaCatalogoPdv.addEventListener("click", async (e) => {
        const btn = e.target.closest("[data-acao='vender-variacao']");
        if (!btn) return;
        await adicionarPorCodigo(btn.dataset.codigo);
      });
    }

    // Carrinho (+ / −)
    el.listaCarrinho.addEventListener("click", (e) => {
      const botao = e.target.closest("button[data-acao]");
      if (!botao) return;
      const chave = botao.dataset.chave;
      if (botao.dataset.acao === "mais") alterarQuantidade(chave, +1);
      if (botao.dataset.acao === "menos") alterarQuantidade(chave, -1);
    });
    el.btnLimparCarrinho.addEventListener("click", () => limparCarrinho(true));

    // Desconto e pagamento
    el.inputDesconto.addEventListener("input", atualizarResumo);
    el.inputDesconto.addEventListener("blur", () => {
      const { subtotal } = calcularTotais();
      const valor = num(el.inputDesconto.value);
      if (valor > subtotal) {
        el.inputDesconto.value = subtotal ? subtotal.toFixed(2) : "";
        toast("O desconto não pode ser maior que o subtotal.", "erro");
        atualizarResumo();
      } else if (valor < 0) {
        el.inputDesconto.value = "";
        atualizarResumo();
      }
    });
    el.grupoPagamento.addEventListener("change", atualizarVisibilidadeCliente);
    el.btnFinalizarVenda.addEventListener("click", finalizarVenda);

    // Fiado
    if (el.btnNovoCliente) el.btnNovoCliente.addEventListener("click", abrirModalNovoCliente);
    if (el.btnCancelarCliente) el.btnCancelarCliente.addEventListener("click", () => el.modalCliente.classList.add("hidden"));
    if (el.formCliente) el.formCliente.addEventListener("submit", salvarNovoCliente);

    el.inputBuscaFiado.addEventListener("input", debounce(renderizarFiado, DEBOUNCE_BUSCA_MS));
    el.listaFiado.addEventListener("click", (e) => {
      const botao = e.target.closest("button[data-acao]");
      if (!botao) return;
      const id = botao.dataset.id;
      if (botao.dataset.acao === "pagar") abrirModalPagamento(id);
      if (botao.dataset.acao === "excluir-cliente") confirmarExclusaoCliente(id);
      if (botao.dataset.acao === "extrato") {
        if (estado.extratosAbertos.has(id)) estado.extratosAbertos.delete(id);
        else estado.extratosAbertos.add(id);
        renderizarFiado();
      }
    });

    // Modal Pagamento
    if (el.btnQuitarTotal) {
      el.btnQuitarTotal.addEventListener("click", () => {
        const clienteId = parseInt(el.modalClienteId.value, 10);
        const cliente = estado.clientes.find((c) => Number(c.id) === clienteId);
        if (cliente && cliente.saldo_devedor > 0) {
          el.inputValorPagamento.value = cliente.saldo_devedor.toFixed(2);
        }
      });
    }
    el.formPagamento.addEventListener("submit", confirmarPagamento);
    el.btnCancelarPagamento.addEventListener("click", fecharModalPagamento);

    // Fechar modais clicando fora
    [el.modalPagamento, el.modalProduto, el.modalCliente, el.modalEtiquetas].forEach((m) => {
      if (!m) return;
      m.addEventListener("click", (e) => {
        if (e.target === m) m.classList.add("hidden");
      });
    });

    document.addEventListener("keydown", tratarTecladoGlobal);

    document.addEventListener("visibilitychange", () => {
      if (document.hidden && estado.cameraAtiva) pararCamera();
    });
    window.addEventListener("pagehide", () => {
      if (estado.cameraAtiva) pararCamera();
    });

    window.addEventListener("offline", () => toast("Você está offline.", "erro", 3000));
    window.addEventListener("online", () => toast("Conexão restabelecida.", "sucesso", 2000));
  }

  // -------------------------------------------------------
  // SINCRONIZAÇÃO EM SEGUNDO PLANO (POLLING LEVE DE 8s)
  // -------------------------------------------------------
  let timerPollingSync = null;

  function iniciarPollingSincronizacao() {
    if (timerPollingSync) clearInterval(timerPollingSync);
    timerPollingSync = setInterval(() => {
      if (!estado.token || document.hidden) return;
      if (estado.vendaEmAndamento || estado.pagamentoEmAndamento) return;

      // Não interrompe se o usuário estiver digitando em um <input>, <select> ou <textarea>
      const elAtivo = document.activeElement;
      const tagAtiva = (elAtivo && elAtivo.tagName ? elAtivo.tagName : "").toUpperCase();
      if (tagAtiva === "INPUT" || tagAtiva === "SELECT" || tagAtiva === "TEXTAREA") return;

      // Não interrompe se algum modal estiver aberto
      const modalAberto = [el.modalPagamento, el.modalProduto, el.modalCliente, el.modalEtiquetas].some(
        (m) => m && !m.classList.contains("hidden")
      );
      if (modalAberto) return;

      // Atualiza silenciosamente a aba visível no momento
      if (estado.abaAtual === "aba-estoque") {
        carregarEstoque(el.inputBuscaEstoque ? el.inputBuscaEstoque.value.trim() : "");
      } else if (estado.abaAtual === "aba-vender") {
        Promise.all([
          carregarEstoque(el.inputBuscaEstoque ? el.inputBuscaEstoque.value.trim() : ""),
          carregarVendasHoje(),
        ]);
      } else if (estado.abaAtual === "aba-fiado") {
        carregarClientesFiado();
      } else if (estado.abaAtual === "tab-caixa" && estado.role === "admin") {
        carregarResumoFinanceiro();
      }
    }, 8000);
  }

  // -------------------------------------------------------
  // INICIALIZAÇÃO
  // -------------------------------------------------------
  function iniciar() {
    registrarEventos();
    selecionarFormaPagamento("DINHEIRO");
    renderizarCarrinho();
    iniciarPollingSincronizacao();

    if (estado.token) {
      abrirApp();
    } else {
      el.app.classList.add("hidden");
      el.telaLogin.classList.remove("hidden");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
