/**
 * core.js — Núcleo Global Compartilhado do Sistema Desktop (Kanemberg v2)
 * Padrão Visual: Slate Neutro Corporativo (Zero Emojis)
 * Fornece configurações de grupos/perfis, estado reativo compartilhado, referências DOM,
 * cliente HTTP com header Desktop, toasts corporativos, navegação SPA, modais e
 * Painel de Controle de Conexão Mobile (ON/OFF + QR Wi-Fi), Backup 1-Clique e Desligamento Seguro.
 */

/* eslint-disable no-unused-vars */

// Registro central de eventos e inicializadores consumido por aba_*.js
const KanembergApp = window.KanembergApp || {
  eventos: [],
  inicializadores: [],
};
window.KanembergApp = KanembergApp;

// ============================================================================
// 1. CONFIGURAÇÃO DOS 5 GRANDES GRUPOS (SLATE NEUTRO — ZERO EMOJIS)
// ============================================================================
const GRUPOS_CONFIG = {
  cima: {
    chave: "cima",
    nome: "Parte de Cima",
    emoji: "",
    rotulo: "Cima",
    cor: "#38bdf8",
    palavras: [
      "blusa", "camisa", "camiseta", "casaco", "vestido",
      "regata", "cropped", "sueter", "suéter", "moletom", "polo", "jaqueta",
    ],
  },
  baixo: {
    chave: "baixo",
    nome: "Parte de Baixo / Praia",
    emoji: "",
    rotulo: "Baixo",
    cor: "#34d399",
    palavras: [
      "calça", "calca", "shorts", "short", "bermuda",
      "sunga", "saia", "biquini", "biquíni", "maio", "maiô",
    ],
  },
  calcados: {
    chave: "calcados",
    nome: "Calçados / Meias",
    emoji: "",
    rotulo: "Calçados",
    cor: "#fb923c",
    palavras: [
      "chinelo", "meia", "sandalia", "sandália",
      "tenis", "tênis", "sapato", "bota", "sapatenis", "sapatênis",
    ],
  },
  acessorios: {
    chave: "acessorios",
    nome: "Acessórios",
    emoji: "",
    rotulo: "Acessórios",
    cor: "#f87171",
    palavras: [
      "boné", "bone", "óculos", "oculos", "relógio", "relogio",
      "cinto", "carteira", "bolsa", "corrente", "pulseira", "chapéu", "chapeu", "touca",
    ],
  },
  perfumaria: {
    chave: "perfumaria",
    nome: "Perfumaria",
    emoji: "",
    rotulo: "Perfumes",
    cor: "#fbbf24",
    palavras: [
      "perfume", "colonia", "colônia", "fragrancia",
      "fragrância", "desodorante", "body splash", "hidratante",
    ],
  },
};

const ORDEM_TAMANHOS = {
  PP: 0, P: 1, M: 2, G: 3, GG: 4, XG: 5, XXG: 6, G1: 7, G2: 8, G3: 9,
  "ÚNICO": 10, UNICO: 10, U: 10,
  "34": 20, "35": 21, "35/36": 22, "36": 23, "37": 24, "37/38": 25, "38": 26,
  "39": 27, "39/40": 28, "40": 29, "41": 30, "41/42": 31, "42": 32,
  "43": 33, "43/44": 34, "44": 35, "46": 36, "48": 37, "50": 38, "52": 39,
  "30ML": 50, "50ML": 51, "100ML": 52, "150ML": 53, "200ML": 54,
  "30ml": 50, "50ml": 51, "100ml": 52, "150ml": 53, "200ml": 54,
};

const MARCAS_POR_GRUPO = {
  cima: [
    "Nike", "Adidas", "Lacoste", "Tommy Hilfiger", "Reserva",
    "Zara", "Levi's", "Calvin Klein", "Hugo Boss", "Renner", "Sem Marca",
  ],
  baixo: [
    "Levi's", "Zara", "Nike", "Adidas", "Reserva",
    "Calvin Klein", "Diesel", "Oakley", "Renner", "Sem Marca",
  ],
  calcados: [
    "Nike", "Adidas", "Havaianas", "Kenner", "Oakley",
    "Puma", "Vans", "Lupo", "Mizuno", "Sem Marca",
  ],
  acessorios: [
    "Oakley", "Ray-Ban", "New Era", "Nike", "Lacoste",
    "Casio", "Tommy Hilfiger", "Invicta", "Sem Marca",
  ],
  perfumaria: [
    "Lattafa", "Afnan", "Al Wataniah", "Armaf", "Paco Rabanne",
    "Carolina Herrera", "Dior", "O Boticário", "Natura", "Sem Marca",
  ],
};

const MARCAS_PADRAO = [
  "Nike", "Adidas", "Zara", "Levi's", "H&M", "Renner",
  "Lacoste", "Tommy Hilfiger", "Reserva", "Oakley", "Havaianas",
  "Lattafa", "O Boticário", "Natura", "Casio", "Sem Marca",
];

const PALETA_CORES_PADRAO = [
  { nome: "Preto", cor_hex: "#1A1A1A" },
  { nome: "Branco", cor_hex: "#F8F8F8" },
  { nome: "Cinza", cor_hex: "#808080" },
  { nome: "Cinza Claro", cor_hex: "#C0C0C0" },
  { nome: "Chumbo", cor_hex: "#3D3D3D" },
  { nome: "Off White", cor_hex: "#FAF9F6" },
  { nome: "Azul Marinho", cor_hex: "#001F5B" },
  { nome: "Azul Royal", cor_hex: "#4169E1" },
  { nome: "Azul Claro", cor_hex: "#87CEEB" },
  { nome: "Jeans", cor_hex: "#3A6FA5" },
  { nome: "Verde", cor_hex: "#228B22" },
  { nome: "Verde Militar", cor_hex: "#4B5320" },
  { nome: "Verde Musgo", cor_hex: "#8A9A5B" },
  { nome: "Vermelho", cor_hex: "#DC143C" },
  { nome: "Vinho", cor_hex: "#722F37" },
  { nome: "Rosa", cor_hex: "#FF69B4" },
  { nome: "Amarelo", cor_hex: "#FFD700" },
  { nome: "Mostarda", cor_hex: "#FFDB58" },
  { nome: "Laranja", cor_hex: "#FF8C00" },
  { nome: "Roxo", cor_hex: "#8B008B" },
  { nome: "Lilás", cor_hex: "#C8A2C8" },
  { nome: "Marrom", cor_hex: "#8B4513" },
  { nome: "Caramelo", cor_hex: "#C68642" },
  { nome: "Bege", cor_hex: "#F5F5DC" },
  { nome: "Caqui", cor_hex: "#C3B091" },
  { nome: "Areia", cor_hex: "#D4B896" },
  { nome: "Dourado", cor_hex: "#D4AF37" },
  { nome: "Prata", cor_hex: "#C0C0C0" },
];

// Perfis Oficiais do Cadastro Camaleão v6.0 (Zero Emojis)
const PERFIS_CAMALEAO = {
  cima: {
    chave: "cima",
    titulo: "Parte de Cima",
    cor: "#3b82f6",
    tipos: ["Camiseta", "Camisa", "Polo", "Blusa", "Casaco", "Moletom", "Regata", "Vestido"],
    marcas: MARCAS_POR_GRUPO.cima,
    labelCorte: "3. Corte / Caimento",
    opcoesCorte: ["Regular", "Slim", "Slim Fit", "Oversized", "Regata", "Manga Longa", "Reto"],
    labelTecido: "4. Tecido",
    opcoesTecido: ["Algodão", "Malha Peruana", "Piquet", "Moletom", "Linho", "Viscose", "Dry Fit", "Poliéster"],
    tamanhos: ["PP", "P", "M", "G", "GG", "XG", "XXG", "ÚNICO"],
    labelGrade: "7. Grade de Tamanhos & Quantidades (Letras)",
  },
  baixo: {
    chave: "baixo",
    titulo: "Parte de Baixo / Praia",
    cor: "#3b82f6",
    tipos: ["Calça", "Bermuda", "Shorts", "Sunga"],
    marcas: MARCAS_POR_GRUPO.baixo,
    labelCorte: "3. Corte / Modelo",
    opcoesCorte: ["Reta", "Skinny", "Cargo", "Jogger", "Tradicional", "Slim Fit", "Oversized"],
    labelTecido: "4. Tecido",
    opcoesTecido: ["Jeans", "Sarja", "Tactel", "Moletom", "Lycra/Poliamida", "Algodão", "Linho"],
    tamanhosNumericos: ["36", "38", "40", "42", "44", "46", "48", "50"],
    tamanhosLetras: ["PP", "P", "M", "G", "GG", "XG"],
    tamanhos: ["36", "38", "40", "42", "44", "46", "48", "P", "M", "G", "GG"],
    labelGrade: "7. Grade de Tamanhos & Quantidades",
  },
  calcados: {
    chave: "calcados",
    titulo: "Calçados / Meias",
    cor: "#3b82f6",
    tipos: ["Chinelo", "Tênis", "Meia", "Sandália"],
    marcas: MARCAS_POR_GRUPO.calcados,
    labelCorte: "3. Estilo / Cano",
    opcoesCorte: ["Tradicional", "Slide", "Correia", "Cano Baixo", "Cano Alto", "Invisível"],
    labelTecido: "4. Material / Tecido",
    opcoesTecido: ["Borracha", "Couro Sintético", "Algodão", "Poliamida", "Algodão/Poliamida", "Mesh"],
    tamanhos: ["35/36", "37/38", "39/40", "41/42", "43/44", "38", "39", "40", "41", "42", "ÚNICO"],
    labelGrade: "7. Grade de Numeração & Quantidades (Calçados / Meias)",
  },
  acessorios: {
    chave: "acessorios",
    titulo: "Acessórios",
    cor: "#3b82f6",
    tipos: ["Boné", "Óculos", "Relógio", "Cinto", "Carteira", "Bolsa"],
    marcas: MARCAS_POR_GRUPO.acessorios,
    labelCorte: "3. Formato / Estilo",
    opcoesCorte: ["Aba Curva", "Aba Reta", "Aviador", "Quadrado", "Digital", "Analógico", "Tradicional"],
    labelTecido: "4. Material / Acabamento",
    opcoesTecido: ["Tactel", "Algodão", "Sarja", "Couro", "Metal", "Acetato", "Polarizado", "Silicone"],
    tamanhos: ["ÚNICO"],
    labelGrade: "7. Quantidade em Estoque (Tamanho ÚNICO)",
  },
  perfumaria: {
    chave: "perfumaria",
    titulo: "Perfumaria",
    cor: "#3b82f6",
    tipos: ["Perfume", "Colônia", "Body Splash", "Hidratante"],
    marcas: MARCAS_POR_GRUPO.perfumaria,
    labelCorte: "3. Família / Gênero",
    opcoesCorte: ["Masculino", "Feminino", "Unissex", "Árabe", "Amadeirado", "Doce", "Cítrico"],
    labelTecido: "4. Tecido",
    opcoesTecido: [],
    tamanhos: ["30ml", "50ml", "100ml", "150ml", "200ml"],
    labelGrade: "7. Grade de Volumes (ml) & Quantidades",
  },
};

const DICIONARIO_CORES_HEX = {
  preto: "#1A1A1A",
  branco: "#F8F8F8",
  cinza: "#808080",
  "cinza claro": "#C0C0C0",
  "cinza escuro": "#404040",
  chumbo: "#3D3D3D",
  "off white": "#FAF9F6",
  creme: "#FFFDD0",
  marfim: "#FFFFF0",
  azul: "#1E90FF",
  "azul claro": "#87CEEB",
  "azul escuro": "#00008B",
  "azul marinho": "#001F5B",
  "azul royal": "#4169E1",
  turquesa: "#40E0D0",
  petroleo: "#005F73",
  "azul petróleo": "#005F73",
  jeans: "#3A6FA5",
  vermelho: "#DC143C",
  "vermelho escuro": "#8B0000",
  rosa: "#FF69B4",
  "rosa claro": "#FFB6C1",
  "rosa escuro": "#C71585",
  pink: "#FF1493",
  salmao: "#FA8072",
  "salmão": "#FA8072",
  coral: "#FF6B6B",
  bordo: "#800020",
  vinho: "#722F37",
  marsala: "#955251",
  verde: "#228B22",
  "verde claro": "#90EE90",
  "verde escuro": "#006400",
  "verde militar": "#4B5320",
  "verde oliva": "#808000",
  oliva: "#808000",
  "verde musgo": "#8A9A5B",
  musgo: "#8A9A5B",
  esmeralda: "#50C878",
  amarelo: "#FFD700",
  laranja: "#FF8C00",
  mostarda: "#FFDB58",
  ouro: "#FFD700",
  dourado: "#D4AF37",
  "padrão": "#D4AF37",
  padrao: "#D4AF37",
  prata: "#C0C0C0",
  roxo: "#8B008B",
  lilas: "#C8A2C8",
  "lilás": "#C8A2C8",
  lavanda: "#E6E6FA",
  marrom: "#8B4513",
  caramelo: "#C68642",
  bege: "#F5F5DC",
  caqui: "#C3B091",
  areia: "#D4B896",
  nude: "#E8BEAC",
  cafe: "#6F4E37",
  "café": "#6F4E37",
  terracota: "#CC4E38",
};

const VALORES_VAZIOS = new Set(["", "—", "-", "N/A", "NA", "NONE", "NULL"]);

// ============================================================================
// 2. ESTADO GLOBAL REATIVO DA APLICAÇÃO
// ============================================================================
const estado = {
  viewAtual: "estoque",
  modoEscuro: true,
  produtos: [],
  clientesFiado: [],
  atributos: {},
  filtroGrupo: "todos",
  termoBusca: "",
  ordenacaoEstoque: "recentes",
  produtoEditando: null,
  coresEditando: [],
  produtoExcluindo: null,
  produtoDetalhes: null,
  filaNovaVenda: [],

  // Estado do Cadastro Camaleão v6.0
  camaleao: {
    grupoAtivo: null,
    tipoPeca: "",
    detalheModelo: "",
    marca: "",
    corte: "N/A",
    tecido: "N/A",
    ocultarCorte: false,
    ocultarTecido: false,
    corTravadaPerfumaria: false,
    tamanhoTravadoUnico: false,
    modoGradeBaixo: "numerico", // 'numerico' | 'letras' | 'ambos'
    mostrarMaisMarcas: false,
    mostrarMaisCortes: false,
    mostrarMaisTecidos: false,
    mostrarMaisCores: false,
    coresSelecionadas: [],
    gradeQuantidades: {},
    marcasCatalogo: [...MARCAS_PADRAO],
    cortesExtras: [],
    tecidosExtras: [],
    paletaCores: [...PALETA_CORES_PADRAO],
  },

  // Estado da Aba 3: PDV de Balcão Widescreen (Nova Venda)
  pdv: {
    carrinho: [],
    filtroGrupo: "todos",
    termoBusca: "",
    modoDesconto: "RS", // 'RS' | 'PCT'
    valorDescontoInput: 0,
    formaPagamento: "PIX", // 'PIX' | 'CARTAO' | 'DINHEIRO' | 'FIADO'
    valorRecebido: "",
    clientes: [],
    buscaCliente: "",
    clienteIdSelecionado: "",
    enviandoVenda: false,
    ultimoItemKeyAnimado: null,
  },

  // Estado de Conexão & Servidor
  conexao: {
    online: true,
    acessoMobileAtivo: true,
    tunelAtivo: false,
    iniciandoTunel: false,
    urlCloudflare: "",
    urlPorteiroFixo: "https://lincolln.github.io/projeto-dani/",
    ipRede: "http://127.0.0.1:8000",
    hostname: "",
    porta: 8000,
    urlMobile: "",
    origemChromeFlag: "",
    chromeFlagUrl: "chrome://flags/#unsafely-treat-insecure-origin-as-secure",
    tamanhoBancoKb: 0,
    ultimoBackup: null,
  },
};

// Aliases de compatibilidade sem quebrar referências diretas
Object.defineProperties(estado, {
  viewAtiva: {
    get() { return this.viewAtual; },
    set(v) { this.viewAtual = v; },
    enumerable: false,
  },
  buscaEstoque: {
    get() { return this.termoBusca; },
    set(v) { this.termoBusca = v; },
    enumerable: false,
  },
  grupoFiltroEstoque: {
    get() { return this.filtroGrupo; },
    set(v) { this.filtroGrupo = v; },
    enumerable: false,
  },
  carrinhoPdv: {
    get() { return this.pdv.carrinho; },
    set(v) { if (Array.isArray(v)) this.pdv.carrinho = v; },
    enumerable: false,
  },
});

window.estado = estado;
window.GRUPOS_CONFIG = GRUPOS_CONFIG;
window.PERFIS_CAMALEAO = PERFIS_CAMALEAO;
window.MARCAS_PADRAO = MARCAS_PADRAO;
window.MARCAS_POR_GRUPO = MARCAS_POR_GRUPO;
window.PALETA_CORES_PADRAO = PALETA_CORES_PADRAO;
window.DICIONARIO_CORES_HEX = DICIONARIO_CORES_HEX;
window.ORDEM_TAMANHOS = ORDEM_TAMANHOS;

// ============================================================================
// 3. REFERÊNCIAS GLOBAIS DE DOM
// ============================================================================
const $ = (id) => document.getElementById(id);
window.$ = $;

const dom = {};
window.dom = dom;

function atualizarReferenciasDomCore() {
  Object.assign(dom, {
    logoImg: $("sidebar-logo-img"),
    logoFallback: $("sidebar-logo-fallback"),
    toggleModoEscuro: $("toggle-modo-escuro"),
    labelModoTema: $("label-modo-tema"),
    navItems: document.querySelectorAll(".sidebar-nav .nav-item[data-view]"),
    mainScrollArea: $("main-scroll-area"),
    views: {
      estoque: $("view-estoque"),
      cadastro: $("view-cadastro"),
      venda: $("view-venda"),
      fiado: $("view-fiado"),
      dashboard: $("view-dashboard"),
    },
    badgeFilaVenda: $("badge-fila-venda"),

    // Conexão & Servidor (Sidebar + Modal)
    btnConexaoServidor: $("btn-conexao-servidor"),
    conexaoDot: $("conexao-dot"),
    conexaoBadge: $("conexao-badge"),
    modalConexaoServidor: $("modal-conexao-servidor"),

    // Vitrine de Estoque
    btnIrCadastroTopo: $("btn-ir-cadastro-topo"),
    inputBuscaVitrine: $("input-busca-vitrine"),
    btnLimparBusca: $("btn-limpar-busca"),
    barraGrupos: $("barra-grupos"),
    contadorModelos: $("contador-modelos"),
    gridVitrine: $("grid-vitrine"),

    // Aba 2: Cadastro Camaleão v6.0
    btnResetarCamaleao: $("btn-resetar-camaleao"),
    bannerSucessoCadastro: $("banner-sucesso-cadastro"),
    tituloSucessoCadastro: $("titulo-sucesso-cadastro"),
    detalheSucessoCadastro: $("detalhe-sucesso-cadastro"),
    btnSucessoVerVitrine: $("btn-sucesso-ver-vitrine"),
    btnFecharBannerSucesso: $("btn-fechar-banner-sucesso"),
    seletorGruposCamaleao: $("seletor-grupos-camaleao"),
    bannerAguardandoGrupo: $("banner-aguardando-grupo"),
    formCamaleaoContainer: $("form-camaleao-container"),
    camaleaoBadgeAtivo: $("camaleao-badge-ativo"),
    camaleaoRegraAtiva: $("camaleao-regra-ativa"),
    camaleaoPreviewModelo: $("camaleao-preview-modelo"),
    chipsTipoPeca: $("chips-tipo-peca"),
    labelDetalheModelo: $("label-detalhe-modelo"),
    inputDetalheModelo: $("input-detalhe-modelo"),
    blocoCamaleaoMarca: $("bloco-camaleao-marca"),
    marcaSelecionadaLabel: $("marca-selecionada-label"),
    chipsMarca: $("chips-marca"),
    boxOutraMarca: $("box-outra-marca"),
    inputOutraMarca: $("input-outra-marca"),
    btnConfirmarOutraMarca: $("btn-confirmar-outra-marca"),
    blocoCamaleaoCorte: $("bloco-camaleao-corte"),
    labelCamaleaoCorte: $("label-camaleao-corte"),
    corteSelecionadoLabel: $("corte-selecionado-label"),
    chipsCorte: $("chips-corte"),
    boxOutroCorte: $("box-outro-corte"),
    inputOutroCorte: $("input-outro-corte"),
    btnConfirmarOutroCorte: $("btn-confirmar-outro-corte"),
    blocoCamaleaoTecido: $("bloco-camaleao-tecido"),
    labelCamaleaoTecido: $("label-camaleao-tecido"),
    tecidoSelecionadoLabel: $("tecido-selecionado-label"),
    chipsTecido: $("chips-tecido"),
    boxOutroTecido: $("box-outro-tecido"),
    inputOutroTecido: $("input-outro-tecido"),
    btnConfirmarOutroTecido: $("btn-confirmar-outro-tecido"),
    camaleaoPrecoCusto: $("camaleao-preco-custo"),
    camaleaoPrecoVenda: $("camaleao-preco-venda"),
    vivoStatusBadge: $("vivo-status-badge"),
    cardLucroVivo: $("card-lucro-vivo"),
    vivoLucroRs: $("vivo-lucro-rs"),
    vivoMargemPct: $("vivo-margem-pct"),
    vivoMarkupPct: $("vivo-markup-pct"),
    blocoCamaleaoCores: $("bloco-camaleao-cores"),
    resumoCoresSelecionadas: $("resumo-cores-selecionadas"),
    btnLimparCoresCamaleao: $("btn-limpar-cores-camaleao"),
    avisoCorPerfumaria: $("aviso-cor-perfumaria"),
    conteudoPaletaCores: $("conteudo-paleta-cores"),
    paletaCoresCamaleao: $("paleta-cores-camaleao"),
    inputNovaCorHex: $("input-nova-cor-hex"),
    inputNovaCorNome: $("input-nova-cor-nome"),
    btnAddNovaCorCamaleao: $("btn-add-nova-cor-camaleao"),
    blocoCamaleaoGrade: $("bloco-camaleao-grade"),
    labelCamaleaoGrade: $("label-camaleao-grade"),
    btnGradeMaisUm: $("btn-grade-mais-um"),
    btnGradeZerar: $("btn-grade-zerar"),
    avisoTamanhoUnico: $("aviso-tamanho-unico"),
    gridTamanhosCamaleao: $("grid-tamanhos-camaleao"),
    resumoQtdTamanhos: $("resumo-qtd-tamanhos"),
    resumoTotalPecas: $("resumo-total-pecas"),
    resumoCustoTotal: $("resumo-custo-total"),
    resumoVendaTotal: $("resumo-venda-total"),
    btnSalvarCamaleao: $("btn-salvar-camaleao"),

    // Aba 3: PDV de Balcão Widescreen (Nova Venda)
    pdvKpiVendasHoje: $("pdv-kpi-vendas-hoje"),
    pdvKpiPecasHoje: $("pdv-kpi-pecas-hoje"),
    btnAbrirHistoricoVendas: $("btn-abrir-historico-vendas"),
    modalHistoricoVendas: $("modal-historico-vendas"),
    listaHistoricoVendas: $("lista-historico-vendas"),
    inputBipePdv: $("input-bipe-pdv"),
    btnLimparBuscaPdv: $("btn-limpar-busca-pdv"),
    btnBiparManualPdv: $("btn-bipar-manual-pdv"),
    pdvBarraGrupos: $("pdv-barra-grupos"),
    pdvContadorCatalogo: $("pdv-contador-catalogo"),
    gridCatalogoPdv: $("grid-catalogo-pdv"),
    pdvBadgeQtdCarrinho: $("pdv-badge-qtd-carrinho"),
    btnPdvLimparCarrinho: $("btn-pdv-limpar-carrinho"),
    listaItensCarrinhoPdv: $("lista-itens-carrinho-pdv"),
    pdvSubtotalBruto: $("pdv-subtotal-bruto"),
    btnDescModoRs: $("btn-desc-modo-rs"),
    btnDescModoPct: $("btn-desc-modo-pct"),
    inputPdvDesconto: $("input-pdv-desconto"),
    pdvResumoDesconto: $("pdv-resumo-desconto"),
    pdvTotalSubinfo: $("pdv-total-subinfo"),
    pdvTotalLiquido: $("pdv-total-liquido"),
    pdvSeletorPagamento: $("pdv-seletor-pagamento"),
    painelPgtoDinheiro: $("painel-pgto-dinheiro"),
    inputPdvValorRecebido: $("input-pdv-valor-recebido"),
    pdvValorTroco: $("pdv-valor-troco"),
    painelPgtoFiado: $("painel-pgto-fiado"),
    btnAbrirModalClienteRapido: $("btn-abrir-modal-cliente-rapido"),
    inputBuscaClientePdv: $("input-busca-cliente-pdv"),
    selectClienteFiadoPdv: $("select-cliente-fiado-pdv"),
    inputDataVencimentoPdv: $("input-data-vencimento-pdv"),
    cardInfoClientePdv: $("card-info-cliente-pdv"),
    pdvCliSaldo: $("pdv-cli-saldo"),
    pdvCliLimite: $("pdv-cli-limite"),
    pdvCliDisponivel: $("pdv-cli-disponivel"),
    btnPdvFinalizarVenda: $("btn-pdv-finalizar-venda"),

    // Modal Cliente Rápido (PDV Fiado)
    modalClienteRapido: $("modal-cliente-rapido"),
    formClienteRapido: $("form-cliente-rapido"),
    rapidoCliNome: $("rapido-cli-nome"),
    rapidoCliTelefone: $("rapido-cli-telefone"),
    rapidoCliLimite: $("rapido-cli-limite"),
    rapidoCliDia: $("rapido-cli-dia"),
    btnSalvarClienteRapido: $("btn-salvar-cliente-rapido"),

    // Modal Recibo Resumido da Venda (Pós-Venda PDV)
    modalReciboVenda: $("modal-recibo-venda"),
    reciboDataHora: $("recibo-data-hora"),
    reciboListaItens: $("recibo-lista-itens"),
    reciboSubtotal: $("recibo-subtotal"),
    reciboLinhaDesconto: $("recibo-linha-desconto"),
    reciboDesconto: $("recibo-desconto"),
    reciboTotalFinal: $("recibo-total-final"),
    reciboFormaPgto: $("recibo-forma-pgto"),
    reciboLinhaExtra: $("recibo-linha-extra"),
    reciboExtraLabel: $("recibo-extra-label"),
    reciboExtraValor: $("recibo-extra-valor"),
    btnReciboNovaVenda: $("btn-recibo-nova-venda"),

    // Modal Editar Produto
    modalEditar: $("modal-editar"),
    modalEditarBadge: $("modal-editar-badge"),
    formEditarProduto: $("form-editar-produto"),
    editProdutoId: $("edit-produto-id"),
    editModeloNome: $("edit-modelo-nome"),
    editMarca: $("edit-marca"),
    editCorte: $("edit-corte"),
    editTecido: $("edit-tecido"),
    editPrecoCusto: $("edit-preco-custo"),
    editPrecoVenda: $("edit-preco-venda"),
    editResumoMargem: $("edit-resumo-margem"),
    editListaCores: $("edit-lista-cores"),
    editNovaCorHex: $("edit-nova-cor-hex"),
    editNovaCorNome: $("edit-nova-cor-nome"),
    btnAddCorEdit: $("btn-add-cor-edit"),
    btnAddTamanhoEdit: $("btn-add-tamanho-edit"),
    editListaVariacoes: $("edit-lista-variacoes"),
    btnSalvarEdicao: $("btn-salvar-edicao"),

    // Modal Excluir Produto
    modalExcluir: $("modal-excluir"),
    excluirNomeProduto: $("excluir-nome-produto"),
    excluirResumoEstoque: $("excluir-resumo-estoque"),
    btnConfirmarExclusao: $("btn-confirmar-exclusao"),

    // Modal Detalhes / Calculadora
    modalDetalhes: $("modal-detalhes"),
    detalhesBadgeGrupo: $("detalhes-badge-grupo"),
    detalhesSubtitulo: $("detalhes-subtitulo"),
    detCusto: $("det-custo"),
    detVenda: $("det-venda"),
    detLucroUn: $("det-lucro-un"),
    detMargem: $("det-margem"),
    simPrecoVenda: $("sim-preco-venda"),
    simDesconto: $("sim-desconto"),
    simResultadoLucro: $("sim-resultado-lucro"),
    detalhesListaVariacoes: $("detalhes-lista-variacoes"),
    btnDetalhesAbrirEditar: $("btn-detalhes-abrir-editar"),

    // Modal Vender Rápido (Escolher Tamanho)
    modalVender: $("modal-vender"),
    venderNomeProduto: $("vender-nome-produto"),
    venderOpcoesTamanhos: $("vender-opcoes-tamanhos"),

    toastContainer: $("toast-container"),
  });
}

// Popula imediatamente caso os elementos do body já estejam carregados
atualizarReferenciasDomCore();

// ============================================================================
// 4. UTILITÁRIOS GLOBAIS DE FORMATAÇÃO, CORES E CLASSIFICAÇÃO
// ============================================================================
function escapeHtml(valor) {
  return String(valor ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const escaparHtml = escapeHtml;

function num(valor, padrao = 0) {
  if (typeof valor === "string") {
    const limpo = valor.replace(/\s/g, "").replace(",", ".");
    const parsed = Number(limpo);
    return Number.isFinite(parsed) ? parsed : padrao;
  }
  const n = Number(valor);
  return Number.isFinite(n) ? n : padrao;
}

function formatarMoeda(valor) {
  return num(valor).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  });
}

function formatarCustoCurto(valor) {
  const v = num(valor);
  if (Number.isInteger(v)) {
    return `Custo R$${v}`;
  }
  return `Custo R$${v.toFixed(2).replace(".", ",")}`;
}

function valorValido(v) {
  if (v === null || v === undefined) return false;
  const limpo = String(v).trim().toUpperCase();
  return !VALORES_VAZIOS.has(limpo);
}

function normalizarTamanhoFront(tamRaw) {
  const t = String(tamRaw || "U").trim();
  if (!t) return "U";
  if (t.toLowerCase().endsWith("ml") && /^\d+$/.test(t.slice(0, -2).trim())) {
    return `${t.slice(0, -2).trim()}ml`;
  }
  const up = t.toUpperCase();
  return up === "UNICO" ? "ÚNICO" : up;
}

function resolverCorHex(nomeCor, hexAtual = "") {
  const h = String(hexAtual || "").trim();
  if (/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(h)) {
    return h;
  }
  const chave = String(nomeCor || "").trim().toLowerCase();
  return DICIONARIO_CORES_HEX[chave] || "#808080";
}

function obterGrupoProduto(modeloNome, tipoPeca = "") {
  const chaveDireta = String(modeloNome || "").trim().toLowerCase();
  if (GRUPOS_CONFIG[chaveDireta] && !tipoPeca) {
    return GRUPOS_CONFIG[chaveDireta];
  }
  const texto = `${modeloNome || ""} ${tipoPeca || ""}`.toLowerCase().trim();
  for (const dados of Object.values(GRUPOS_CONFIG)) {
    for (const palavra of dados.palavras) {
      if (texto.startsWith(palavra) || texto.includes(` ${palavra}`)) {
        return dados;
      }
    }
  }
  return GRUPOS_CONFIG.cima;
}

function obterConfigGrupo(chaveOuTexto, tipoPeca = "") {
  const k = String(chaveOuTexto || "").trim().toLowerCase();
  if (GRUPOS_CONFIG[k]) {
    return GRUPOS_CONFIG[k];
  }
  return obterGrupoProduto(chaveOuTexto, tipoPeca);
}

function extrairCoresProduto(produto) {
  if (!produto || typeof produto !== "object") return [];

  if (Array.isArray(produto.cores_lista) && produto.cores_lista.length > 0) {
    return produto.cores_lista
      .map((c) => {
        if (Array.isArray(c)) {
          return { nome: String(c[0] || "").trim(), cor_hex: resolverCorHex(c[0], c[1]) };
        }
        return {
          nome: String(c.nome || c.cor || "").trim(),
          cor_hex: resolverCorHex(c.nome || c.cor, c.cor_hex || c.hex),
        };
      })
      .filter((c) => c.nome && c.nome.toLowerCase() !== "padrão");
  }

  const mapa = new Map();
  const tags = String(produto.cores_tags || "").trim();
  if (tags) {
    tags.split(",").forEach((tag) => {
      const t = tag.trim();
      if (!t) return;
      if (t.includes("|")) {
        const [n, h] = t.split("|");
        const nome = n.trim();
        if (nome && nome.toLowerCase() !== "padrão") {
          mapa.set(nome, resolverCorHex(nome, h));
        }
      } else if (t.toLowerCase() !== "padrão") {
        mapa.set(t, resolverCorHex(t, ""));
      }
    });
  }

  const vars = Array.isArray(produto.variacoes) ? produto.variacoes : [];
  vars.forEach((v) => {
    const n = String(v.cor || "").trim();
    if (n && n.toLowerCase() !== "padrão" && !mapa.has(n)) {
      mapa.set(n, resolverCorHex(n, v.cor_hex));
    }
  });

  return Array.from(mapa.entries()).map(([nome, cor_hex]) => ({ nome, cor_hex }));
}

function agruparTamanhosProduto(produto) {
  const vars = Array.isArray(produto?.variacoes) ? produto.variacoes : [];
  const mapa = new Map();

  vars.forEach((v) => {
    const tam = normalizarTamanhoFront(v.tamanho || "U");
    const qtd = num(v.estoque, 0);
    if (!mapa.has(tam)) {
      mapa.set(tam, {
        tamanho: tam,
        estoque: 0,
        variacao_id: v.id,
        codigo_barras: v.codigo_barras || "",
        preco_venda: num(v.preco_venda || produto?.preco_venda),
      });
    }
    const item = mapa.get(tam);
    item.estoque += qtd;
    if (qtd > 0) {
      item.variacao_id = v.id;
      item.codigo_barras = v.codigo_barras || item.codigo_barras;
    }
  });

  return Array.from(mapa.values()).sort((a, b) => {
    const oa = ORDEM_TAMANHOS[a.tamanho] ?? ORDEM_TAMANHOS[a.tamanho.toUpperCase()] ?? 99;
    const ob = ORDEM_TAMANHOS[b.tamanho] ?? ORDEM_TAMANHOS[b.tamanho.toUpperCase()] ?? 99;
    if (oa !== ob) return oa - ob;
    return a.tamanho.localeCompare(b.tamanho, "pt-BR");
  });
}

// ============================================================================
// 5. COMUNICAÇÃO COM A API BACK-END (requisitarApi / apiFetch)
// ============================================================================
async function requisitarApi(url, opcoes = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Sistema-Desktop": "1",
    ...(opcoes.headers || {}),
  };

  const tokenSalvo = localStorage.getItem("kanemberg_token");
  if (tokenSalvo && !headers.Authorization) {
    headers.Authorization = `Bearer ${tokenSalvo}`;
  }

  const metodo = (opcoes.metodo || opcoes.method || "GET").toUpperCase();
  const config = {
    method: metodo,
    headers,
  };

  if (opcoes.corpo !== undefined) {
    config.body = typeof opcoes.corpo === "string" ? opcoes.corpo : JSON.stringify(opcoes.corpo);
  } else if (opcoes.body !== undefined) {
    config.body = typeof opcoes.body === "string" ? opcoes.body : JSON.stringify(opcoes.body);
  }

  const resposta = await fetch(url, config);
  let dados = {};
  try {
    dados = await resposta.json();
  } catch (_e) {
    dados = {};
  }

  if (!resposta.ok) {
    const mensagemErro = dados.detail || dados.mensagem || `Erro HTTP ${resposta.status}`;
    throw new Error(mensagemErro);
  }

  return dados;
}

const apiFetch = requisitarApi;

// ============================================================================
// 6. SISTEMA DE TOASTS CORPORATIVOS (ZERO EMOJIS)
// ============================================================================
function limparEmojisTexto(texto) {
  return String(texto ?? "")
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function exibirToast(mensagem, tipo = "info", duracao = 3200) {
  const container = dom.toastContainer || $("toast-container");
  if (!container) return;

  const tipoNorm = ["sucesso", "erro", "aviso", "info"].includes(tipo) ? tipo : "info";
  const toast = document.createElement("div");
  toast.className = `sistema-toast ${tipoNorm} toast-${tipoNorm}`;

  const msgLimpa = limparEmojisTexto(mensagem) || String(mensagem ?? "");
  toast.innerHTML = `<span class="toast-indicador" aria-hidden="true"></span><span>${escapeHtml(msgLimpa)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.2s ease";
    setTimeout(() => toast.remove(), 220);
  }, duracao);
}

const mostrarToast = exibirToast;

// ============================================================================
// 7. TEMA, NAVEGAÇÃO ENTRE AS 5 ABAS E CONTROLE DE MODAIS
// ============================================================================
function aplicarTema(modoEscuro) {
  estado.modoEscuro = Boolean(modoEscuro);
  document.documentElement.setAttribute("data-theme", estado.modoEscuro ? "dark" : "light");
  if (dom.toggleModoEscuro) {
    dom.toggleModoEscuro.checked = estado.modoEscuro;
  }
  if (dom.labelModoTema) {
    dom.labelModoTema.textContent = estado.modoEscuro ? "Modo Escuro" : "Modo Claro";
  }
  localStorage.setItem("kanemberg_sistema_tema", estado.modoEscuro ? "dark" : "light");
}

function alternarView(nomeView) {
  let destino = String(nomeView || "estoque").trim().toLowerCase();
  let abrirSubvisaoMargens = false;

  if (destino === "margens") {
    destino = "dashboard";
    abrirSubvisaoMargens = true;
  }

  atualizarReferenciasDomCore();
  if (!dom.views[destino]) return;

  estado.viewAtual = destino;

  document.querySelectorAll(".sidebar-nav .nav-item[data-view]").forEach((btn) => {
    btn.classList.toggle("ativo", btn.dataset.view === destino);
  });

  Object.entries(dom.views).forEach(([chave, sec]) => {
    if (!sec) return;
    const ativa = chave === destino;
    sec.classList.toggle("hidden", !ativa);
    sec.classList.toggle("ativa", ativa);
  });

  if (dom.mainScrollArea) {
    dom.mainScrollArea.scrollTop = 0;
  }

  if (destino === "estoque") {
    if (typeof window.carregarEstoque === "function") {
      window.carregarEstoque(true);
    }
  } else if (destino === "cadastro") {
    if (typeof window.carregarAtributosCamaleao === "function") {
      window.carregarAtributosCamaleao();
    }
  } else if (destino === "venda") {
    if (typeof window.carregarKpisVendasHoje === "function") {
      window.carregarKpisVendasHoje();
    }
    if (typeof window.renderizarCatalogoPDV === "function") {
      window.renderizarCatalogoPDV();
    }
    if (typeof window.renderizarCarrinhoPDV === "function") {
      window.renderizarCarrinhoPDV();
    }
    if (
      estado.pdv.formaPagamento === "FIADO" &&
      !estado.pdv.clientes.length &&
      typeof window.carregarClientesPDV === "function"
    ) {
      window.carregarClientesPDV(true);
    }
    setTimeout(() => {
      $("input-bipe-pdv")?.focus();
    }, 60);
  } else if (destino === "fiado") {
    if (typeof window.carregarFiado === "function") {
      window.carregarFiado(true);
    }
  } else if (destino === "dashboard") {
    if (typeof window.carregarDashboard === "function") {
      window.carregarDashboard(true);
    }
    if (abrirSubvisaoMargens && typeof window.selecionarVisaoDashboard === "function") {
      window.selecionarVisaoDashboard("MARGENS", true);
    }
  }
}

const alternarAba = alternarView;

function abrirModal(idModal) {
  const el = $(idModal);
  if (el) {
    el.classList.remove("hidden");
  }
}

function fecharModal(idModal) {
  const el = $(idModal);
  if (el) {
    el.classList.add("hidden");
  }
}

function fecharTodosModais() {
  const idsConhecidos = [
    "modal-editar",
    "modal-editar-produto",
    "modal-excluir",
    "modal-excluir-produto",
    "modal-detalhes",
    "modal-detalhes-produto",
    "modal-vender",
    "modal-cliente-rapido",
    "modal-recibo-venda",
    "modal-fiado-cliente",
    "modal-fiado-pagamento",
    "modal-fiado-debito",
    "modal-qrcode",
    "modal-conexao-servidor",
    "modal-historico-vendas",
  ];
  idsConhecidos.forEach((id) => {
    $(id)?.classList.add("hidden");
  });
  document.querySelectorAll(".modal-backdrop:not(.hidden)").forEach((m) => {
    m.classList.add("hidden");
  });
}

function atualizarBadgeFilaVenda() {
  const badge = dom.badgeFilaVenda || $("badge-fila-venda");
  if (!badge) return;
  const totalCarrinho = (estado.pdv?.carrinho || []).reduce(
    (acc, item) => acc + num(item.quantidade, 0),
    0
  );
  const total = totalCarrinho || (estado.filaNovaVenda || []).length;
  badge.textContent = String(total);
  badge.classList.toggle("hidden", total <= 0);
}

// ============================================================================
// 8. FALLBACKS SEGUROS PARA INTEGRAÇÃO ENTRE MÓDULOS (ETAPA A -> ETAPA B)
// ============================================================================
if (typeof window.sincronizarLimitesCarrinhoComEstoque !== "function") {
  window.sincronizarLimitesCarrinhoComEstoque = function () {};
}
if (typeof window.renderizarCatalogoPDV !== "function") {
  window.renderizarCatalogoPDV = function () {};
}
if (typeof window.renderizarCarrinhoPDV !== "function") {
  window.renderizarCarrinhoPDV = function () {};
}
if (typeof window.carregarKpisVendasHoje !== "function") {
  window.carregarKpisVendasHoje = function () {};
}
if (typeof window.carregarClientesPDV !== "function") {
  window.carregarClientesPDV = function () {};
}
if (typeof window.carregarAtributosCamaleao !== "function") {
  window.carregarAtributosCamaleao = function () {};
}
if (typeof window.finalizarVendaPDV !== "function") {
  window.finalizarVendaPDV = function () {};
}
if (typeof window.acionarEnviarParaVenda !== "function") {
  window.acionarEnviarParaVenda = function (produtoId, tamanhoOpcional) {
    const prod = (estado.produtos || []).find(
      (p) => Number(p.id || p.produto_id) === Number(produtoId)
    );
    if (!prod) return;
    fecharModal("modal-vender");
    alternarView("venda");
    exibirToast(
      `Produto "${prod.modelo_nome}" selecionado${tamanhoOpcional ? ` (${tamanhoOpcional})` : ""}.`,
      "info"
    );
  };
}

// ============================================================================
// 9. PAINEL DE CONEXÃO MOBILE (ON/OFF COM QR WI-FI), BACKUP & SERVIDOR
// ============================================================================
function atualizarIndicadoresConexaoSidebar(dados) {
  const dot = $("conexao-dot");
  const badge = $("conexao-badge");
  const ativo = Boolean(dados?.acesso_mobile_ativo);

  if (dot) {
    dot.classList.toggle("on", ativo);
    dot.classList.toggle("local", !ativo);
  }
  if (badge) {
    badge.textContent = ativo ? "ON" : "OFF";
    badge.classList.toggle("on", ativo);
  }
}

function renderizarDadosModalConexao(dados) {
  const ativo = Boolean(dados?.acesso_mobile_ativo);
  const urlCloudflare = (dados?.url_cloudflare || "").trim();
  const tunelAtivo = Boolean(urlCloudflare);
  const ipRedeRaw = dados?.ip_rede || "http://127.0.0.1:8000";
  const ipRedeHttp = ipRedeRaw.startsWith("http")
    ? ipRedeRaw
    : `http://${ipRedeRaw}:${dados?.porta || 8000}`;
  const urlPorteiro = dados?.url_porteiro_fixo || "https://lincolln.github.io/projeto-dani/";
  const urlMobile = urlCloudflare || dados?.url_mobile || `${ipRedeHttp}/app`;

  const toggleMob = $("toggle-acesso-mobile");
  const blocoQr = $("conexao-bloco-qr");
  const avisoOff = $("conexao-aviso-off");
  const badgeTunel = $("conexao-status-tunel-badge");
  const blocoAtivarTunel = $("conexao-bloco-ativar-tunel");
  const btnRecriarTunel = $("btn-recriar-tunel");
  const btnCopiarUrl = $("btn-copiar-url-mobile");
  const dicaPrincipal = $("conexao-dica-principal");
  const imgQr = $("conexao-qr-img");
  const inpUrl = $("conexao-url-mobile");
  const txtPorteiro = $("conexao-url-porteiro");
  const txtIp = $("conexao-ip-porta");
  const txtBanco = $("conexao-info-banco");

  if (toggleMob) {
    toggleMob.checked = ativo;
  }
  if (blocoQr) {
    blocoQr.classList.toggle("hidden", !ativo);
  }
  if (avisoOff) {
    avisoOff.classList.toggle("hidden", ativo);
  }

  if (badgeTunel) {
    if (tunelAtivo) {
      badgeTunel.textContent = "HTTPS ATIVO";
      badgeTunel.style.background = "rgba(16, 185, 129, 0.16)";
      badgeTunel.style.color = "#10b981";
      badgeTunel.style.borderColor = "rgba(16, 185, 129, 0.35)";
    } else {
      badgeTunel.textContent = dados?.iniciando_tunel ? "INICIANDO..." : "AGUARDANDO TÚNEL";
      badgeTunel.style.background = "rgba(245, 158, 11, 0.16)";
      badgeTunel.style.color = "#f59e0b";
      badgeTunel.style.borderColor = "rgba(245, 158, 11, 0.35)";
    }
  }

  if (blocoAtivarTunel) {
    blocoAtivarTunel.classList.toggle("hidden", tunelAtivo);
  }
  if (btnRecriarTunel) {
    btnRecriarTunel.classList.toggle("hidden", !tunelAtivo);
  }
  if (btnCopiarUrl) {
    btnCopiarUrl.textContent = tunelAtivo ? "Copiar Link HTTPS" : "Copiar Link do App";
  }
  if (dicaPrincipal) {
    dicaPrincipal.innerHTML = tunelAtivo
      ? 'Leia o QR Code acima no Chrome/Safari para instalar o <strong>App Nativo (WebAPK sem ícone do Chrome)</strong>.'
      : 'Túnel HTTPS ainda não ativo. Clique em <strong>Ativar Link HTTPS (Cloudflare)</strong> acima ou use o Wi-Fi Local.';
  }

  if (ativo && imgQr) {
    imgQr.src = `/api/sistema/qrcode-acesso?url=${encodeURIComponent(urlMobile)}&t=${Date.now()}`;
  }
  if (inpUrl) {
    inpUrl.value = urlMobile;
  }
  if (txtPorteiro) {
    txtPorteiro.textContent = urlPorteiro;
  }
  if (txtIp) {
    txtIp.textContent = ipRedeHttp;
  }
  if (txtBanco) {
    const tamKb = num(dados?.tamanho_banco_kb, 0).toFixed(1);
    const ult = dados?.ultimo_backup ? `Último backup: ${dados.ultimo_backup}` : "Nenhum backup registrado ainda";
    txtBanco.textContent = `Banco local: ${tamKb} KB · ${ult}`;
  }
}

async function carregarStatusConexao(silencioso = true) {
  try {
    const dados = await requisitarApi("/api/sistema/status");
    const ipRedeRaw = dados.ip_rede || "http://127.0.0.1:8000";
    const ipRedeHttp = ipRedeRaw.startsWith("http")
      ? ipRedeRaw
      : `http://${ipRedeRaw}:${dados.porta || 8000}`;
    const urlCloudflare = (dados.url_cloudflare || "").trim();

    estado.conexao = {
      online: Boolean(dados.online),
      acessoMobileAtivo: Boolean(dados.acesso_mobile_ativo),
      tunelAtivo: Boolean(urlCloudflare),
      iniciandoTunel: Boolean(dados.iniciando_tunel),
      urlCloudflare,
      urlPorteiroFixo: dados.url_porteiro_fixo || "https://lincolln.github.io/projeto-dani/",
      ipRede: ipRedeHttp,
      hostname: dados.hostname || "",
      porta: dados.porta || 8000,
      urlMobile: urlCloudflare || dados.url_mobile || `${ipRedeHttp}/app`,
      origemChromeFlag: dados.origem_chrome_flag || ipRedeHttp,
      chromeFlagUrl: dados.chrome_flag_url || "chrome://flags/#unsafely-treat-insecure-origin-as-secure",
      tamanhoBancoKb: num(dados.tamanho_banco_kb, 0),
      ultimoBackup: dados.ultimo_backup || null,
    };
    atualizarIndicadoresConexaoSidebar(dados);
    renderizarDadosModalConexao(dados);
    return dados;
  } catch (erro) {
    if (!silencioso) {
      exibirToast(`Falha ao consultar status do servidor: ${erro.message}`, "erro");
    }
    return null;
  }
}

async function abrirModalConexaoServidor() {
  abrirModal("modal-conexao-servidor");
  const dados = await carregarStatusConexao(false);
  // Se o túnel ainda estiver subindo em background, faz uma nova checagem após 3s
  if (dados && !dados.url_cloudflare && dados.iniciando_tunel) {
    setTimeout(() => {
      carregarStatusConexao(true);
    }, 3000);
  }
}

async function iniciarOuRecriarTunelCloudflare(reiniciar = false) {
  const btnAtivar = $("btn-ativar-tunel");
  const btnRecriar = $("btn-recriar-tunel");
  const txtOriginalAtivar = btnAtivar?.textContent || "Ativar Link HTTPS (Cloudflare)";
  const txtOriginalRecriar = btnRecriar?.textContent || "Recriar Túnel";

  if (btnAtivar) {
    btnAtivar.disabled = true;
    btnAtivar.textContent = "Gerando Link HTTPS Cloudflare...";
  }
  if (btnRecriar) {
    btnRecriar.disabled = true;
    btnRecriar.textContent = "Recriando...";
  }

  try {
    const resp = await requisitarApi("/api/sistema/iniciar-tunel", {
      metodo: "POST",
      corpo: { reiniciar: Boolean(reiniciar) },
    });
    await carregarStatusConexao(true);
    if (resp?.url_cloudflare) {
      exibirToast("Link HTTPS Cloudflare ativo e sincronizado com o Porteiro PWA.", "sucesso");
    } else {
      exibirToast(resp?.mensagem || "Não foi possível obter a URL do Cloudflare agora.", "aviso");
    }
  } catch (erro) {
    exibirToast(`Falha ao iniciar túnel Cloudflare: ${erro.message}`, "erro");
  } finally {
    if (btnAtivar) {
      btnAtivar.disabled = false;
      btnAtivar.textContent = txtOriginalAtivar;
    }
    if (btnRecriar) {
      btnRecriar.disabled = false;
      btnRecriar.textContent = txtOriginalRecriar;
    }
  }
}

async function alternarAcessoMobile(ativo) {
  try {
    const dados = await requisitarApi("/api/sistema/mobile-toggle", {
      metodo: "POST",
      corpo: { ativo: Boolean(ativo) },
    });
    await carregarStatusConexao(true);
    exibirToast(
      dados.mensagem ||
        (dados.acesso_mobile_ativo
          ? "Acesso Mobile liberado."
          : "Acesso Mobile bloqueado (somente este computador)."),
      dados.acesso_mobile_ativo ? "sucesso" : "aviso"
    );
  } catch (erro) {
    exibirToast(`Não foi possível alterar o Acesso Mobile: ${erro.message}`, "erro");
    await carregarStatusConexao(true);
  }
}

async function copiarTextoAreaTransferencia(texto, inputFallback, mensagemSucesso) {
  if (!texto) return;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(texto);
    } else if (inputFallback && typeof inputFallback.select === "function") {
      inputFallback.select();
      document.execCommand("copy");
    } else {
      const temp = document.createElement("textarea");
      temp.value = texto;
      temp.style.position = "fixed";
      temp.style.opacity = "0";
      document.body.appendChild(temp);
      temp.select();
      document.execCommand("copy");
      temp.remove();
    }
    exibirToast(mensagemSucesso, "sucesso");
  } catch (_e) {
    exibirToast("Não foi possível copiar automaticamente. Selecione o texto manualmente.", "aviso");
  }
}

async function copiarLinkMobileConexao() {
  const inp = $("conexao-url-mobile");
  const url = inp?.value || estado.conexao.urlCloudflare || estado.conexao.urlMobile;
  await copiarTextoAreaTransferencia(
    url,
    inp,
    "Link HTTPS do App copiado para a área de transferência."
  );
}

async function copiarLinkPorteiroFixo() {
  const url =
    $("conexao-url-porteiro")?.textContent?.trim() ||
    estado.conexao.urlPorteiroFixo ||
    "https://lincolln.github.io/projeto-dani/";
  await copiarTextoAreaTransferencia(
    url,
    null,
    "Link do Porteiro Fixo PWA copiado para a área de transferência."
  );
}

async function copiarIpLocalConexao() {
  const ip =
    $("conexao-ip-porta")?.textContent?.trim() ||
    estado.conexao.ipRede ||
    "http://127.0.0.1:8000";
  await copiarTextoAreaTransferencia(
    ip,
    null,
    "Endereço IP da Rede Local copiado para a área de transferência."
  );
}

function baixarBackupSistema() {
  const link = document.createElement("a");
  link.href = `/api/sistema/backup?t=${Date.now()}`;
  link.setAttribute("download", "");
  document.body.appendChild(link);
  link.click();
  link.remove();

  exibirToast("Download do backup seguro iniciado.", "sucesso");
  setTimeout(() => {
    carregarStatusConexao(true);
  }, 1200);
}

async function encerrarServidorSistema() {
  const confirmar = window.confirm(
    "Deseja criar um backup automático na pasta backups/ e encerrar o servidor Kanemberg agora?"
  );
  if (!confirmar) return;

  try {
    const resp = await requisitarApi("/api/sistema/desligar", { metodo: "POST" });
    const dot = $("conexao-dot");
    const badge = $("conexao-badge");
    if (dot) {
      dot.classList.remove("on", "local");
    }
    if (badge) {
      badge.textContent = "OFF";
      badge.classList.remove("on");
    }

    const corpo = $("conexao-modal-conteudo");
    if (corpo) {
      corpo.innerHTML = `
        <div class="conexao-desligado">
          <strong>Servidor encerrado com segurança</strong>
          <p style="margin-top:8px;font-size:13px;color:var(--fg-muted);">
            ${escapeHtml(resp.mensagem || "Backup automático salvo na pasta backups/.")}
            ${resp.backup_gerado ? ` (${escapeHtml(resp.backup_gerado)})` : ""}
          </p>
          <p style="margin-top:10px;font-size:12px;color:var(--fg-subtle);">
            Você já pode fechar esta aba do navegador.
          </p>
        </div>
      `;
    }
  } catch (erro) {
    exibirToast(`Erro ao desligar o servidor: ${erro.message}`, "erro");
  }
}

// ============================================================================
// 10. REGISTRO DE EVENTOS DO CORE E INICIALIZAÇÃO DO SISTEMA
// ============================================================================
function registrarEventosCore() {
  atualizarReferenciasDomCore();

  // Switch Modo Escuro / Claro
  dom.toggleModoEscuro?.addEventListener("change", (e) => {
    aplicarTema(e.target.checked);
  });

  // Navegação principal da Sidebar
  document.querySelectorAll(".sidebar-nav .nav-item[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => {
      alternarView(btn.dataset.view);
    });
  });

  // Botões internos com atributo [data-ir-view]
  document.addEventListener("click", (e) => {
    const btnIr = e.target.closest("[data-ir-view]");
    if (btnIr) {
      alternarView(btnIr.dataset.irView);
      return;
    }

    const btnFechar = e.target.closest("[data-fechar-modal]");
    if (btnFechar) {
      fecharModal(btnFechar.dataset.fecharModal);
      return;
    }

    if (e.target.classList && e.target.classList.contains("modal-backdrop")) {
      e.target.classList.add("hidden");
    }
  });

  // Painel de Conexão & Servidor
  $("btn-conexao-servidor")?.addEventListener("click", abrirModalConexaoServidor);
  $("toggle-acesso-mobile")?.addEventListener("change", (e) => {
    alternarAcessoMobile(e.target.checked);
  });
  $("btn-ativar-tunel")?.addEventListener("click", () => {
    iniciarOuRecriarTunelCloudflare(false);
  });
  $("btn-recriar-tunel")?.addEventListener("click", () => {
    iniciarOuRecriarTunelCloudflare(true);
  });
  $("btn-copiar-url-mobile")?.addEventListener("click", copiarLinkMobileConexao);
  $("btn-copiar-porteiro")?.addEventListener("click", copiarLinkPorteiroFixo);
  $("btn-copiar-ip-local")?.addEventListener("click", copiarIpLocalConexao);
  $("btn-baixar-backup")?.addEventListener("click", baixarBackupSistema);
  $("btn-encerrar-servidor")?.addEventListener("click", encerrarServidorSistema);

  // Atalhos globais de teclado (ESC, F2 para Busca/Bipe PDV, F12 para Finalizar Venda)
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      fecharTodosModais();
      return;
    }

    const modalAberto = Boolean(document.querySelector(".modal-backdrop:not(.hidden)"));

    if (e.key === "F2" && !modalAberto) {
      e.preventDefault();
      if (estado.viewAtual !== "venda") {
        alternarView("venda");
      }
      setTimeout(() => {
        const inp = $("input-bipe-pdv");
        inp?.focus();
        inp?.select();
      }, 30);
      return;
    }

    if (e.key === "F12" && estado.viewAtual === "venda" && !modalAberto) {
      e.preventDefault();
      if (typeof window.finalizarVendaPDV === "function") {
        window.finalizarVendaPDV();
      }
    }
  });
}

function iniciarMonitorSincronizacao() {
  setInterval(() => {
    const algumModalAberto = Boolean(document.querySelector(".modal-backdrop:not(.hidden)"));
    if (
      (estado.viewAtual === "estoque" || estado.viewAtual === "venda") &&
      !algumModalAberto &&
      !document.hidden &&
      typeof window.carregarEstoque === "function"
    ) {
      window.carregarEstoque(true);
    }
  }, 5000);
}

function inicializarSistema() {
  atualizarReferenciasDomCore();

  const temaSalvo = localStorage.getItem("kanemberg_sistema_tema");
  aplicarTema(temaSalvo !== "light");

  registrarEventosCore();

  // Executa todos os registradores de eventos dos módulos aba_*.js
  KanembergApp.eventos.forEach((fn) => {
    try {
      if (typeof fn === "function") fn();
    } catch (err) {
      console.error("[Kanemberg] Erro ao registrar eventos de módulo:", err);
    }
  });

  // Executa todos os inicializadores de dados dos módulos aba_*.js
  KanembergApp.inicializadores.forEach((fn) => {
    try {
      if (typeof fn === "function") fn();
    } catch (err) {
      console.error("[Kanemberg] Erro ao inicializar módulo:", err);
    }
  });

  carregarStatusConexao(true);
  iniciarMonitorSincronizacao();
}

// Exporta utilitários para escopo global explícito (window.*)
window.escapeHtml = escapeHtml;
window.escaparHtml = escaparHtml;
window.num = num;
window.formatarMoeda = formatarMoeda;
window.formatarCustoCurto = formatarCustoCurto;
window.valorValido = valorValido;
window.normalizarTamanhoFront = normalizarTamanhoFront;
window.resolverCorHex = resolverCorHex;
window.obterGrupoProduto = obterGrupoProduto;
window.obterConfigGrupo = obterConfigGrupo;
window.extrairCoresProduto = extrairCoresProduto;
window.agruparTamanhosProduto = agruparTamanhosProduto;
window.requisitarApi = requisitarApi;
window.apiFetch = apiFetch;
window.exibirToast = exibirToast;
window.mostrarToast = mostrarToast;
window.aplicarTema = aplicarTema;
window.alternarView = alternarView;
window.alternarAba = alternarAba;
window.abrirModal = abrirModal;
window.fecharModal = fecharModal;
window.fecharTodosModais = fecharTodosModais;
window.atualizarBadgeFilaVenda = atualizarBadgeFilaVenda;
window.abrirModalConexaoServidor = abrirModalConexaoServidor;
window.alternarAcessoMobile = alternarAcessoMobile;
window.baixarBackupSistema = baixarBackupSistema;
window.encerrarServidorSistema = encerrarServidorSistema;
window.carregarStatusConexao = carregarStatusConexao;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", inicializarSistema);
} else {
  inicializarSistema();
}
