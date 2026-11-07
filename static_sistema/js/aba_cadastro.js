/**
 * aba_cadastro.js — Aba 2: Cadastrar Produto (Formulário Camaleão Contextual v6.0)
 * Padrão Visual: Slate Neutro Corporativo (Zero Emojis) + Física Silk UI
 *
 * Funcionalidades:
 * - Seleção dos 5 Grandes Grupos (cima, baixo, calcados, acessorios, perfumaria) com silkReveal
 * - Filtros contextuais reais por grupo e sub-regras dinâmicas em Acessórios (Boné, Óculos, Relógio, etc.)
 * - Grade inteligente em Parte de Baixo / Praia (Shorts/Sunga -> Letras; Calça/Bermuda -> Numeração + toggle)
 * - Perfumaria enxuta (oculta bloco de cores e envia cor "Padrão" automática; grade de volumes ml)
 * - Acessórios enxuto (tamanho ÚNICO sem alertas vermelhos nem botões +1 em Todos desnecessários)
 * - Motor "Top 5 Mais Usados" baseado na frequência real do estoque + chip "Mostrar mais (+X)"
 * - Calculadora viva de Custo / Venda / Margem / Markup e resumo financeiro do lote
 * - Salvamento em POST /api/produtos + atalhos pós-cadastro ("Ver na Vitrine" e "Imprimir Etiquetas deste Lote")
 */

/* global KanembergApp, estado, dom, $, PERFIS_CAMALEAO, MARCAS_POR_GRUPO, PALETA_CORES_PADRAO,
          escapeHtml, num, formatarMoeda, valorValido, resolverCorHex, obterGrupoProduto,
          extrairCoresProduto, requisitarApi, exibirToast, alternarView */

const LIMITE_TOP_CHIPS = 5;

let eventosCadastroRegistrados = false;
let ultimoProdutoIdCadastrado = null;
let timerFadeChips = null;

// Marcas extras adicionadas manualmente na sessão por grupo
const marcasExtrasPorGrupo = {
  cima: [],
  baixo: [],
  calcados: [],
  acessorios: [],
  perfumaria: ["Importado"],
};

// Sub-regras contextuais para Acessórios conforme o Tipo da Peça selecionado
const SUBREGRAS_ACESSORIOS = {
  "Boné": {
    labelCorte: "3. Estilo / Aba",
    opcoesCorte: ["Aba Curva", "Aba Reta", "Trucker", "Dad Hat", "Snapback"],
    labelTecido: "4. Material",
    opcoesTecido: ["Algodão", "Tactel", "Sarja", "Camurça", "Telinha"],
  },
  "Óculos": {
    labelCorte: "3. Formato / Armação",
    opcoesCorte: ["Aviador", "Quadrado", "Redondo", "Esportivo", "Retrô"],
    labelTecido: "4. Lente / Material",
    opcoesTecido: ["Polarizado", "Acetato", "Metal", "UV400", "Policarbonato"],
  },
  "Relógio": {
    labelCorte: "3. Mecanismo / Estilo",
    opcoesCorte: ["Analógico", "Digital", "Esportivo", "Social", "Cronógrafo"],
    labelTecido: "4. Pulseira / Caixa",
    opcoesTecido: ["Aço Inox", "Silicone", "Couro", "Metal", "Resina"],
  },
  "Cinto": {
    labelCorte: "3. Estilo / Fivela",
    opcoesCorte: ["Social", "Casual", "Dupla Face", "Fivela Automática", "Tradicional"],
    labelTecido: "4. Material",
    opcoesTecido: ["Couro Legítimo", "Couro Sintético", "Lona", "Gorgurão", "Elástico"],
  },
  "Carteira": {
    labelCorte: "3. Formato",
    opcoesCorte: ["Slim", "Porta-Cartão", "Tradicional", "Com Zíper", "Bifold"],
    labelTecido: "4. Material",
    opcoesTecido: ["Couro Legítimo", "Couro Sintético", "Lona", "Nylon"],
  },
  "Bolsa": {
    labelCorte: "3. Modelo",
    opcoesCorte: ["Shoulder Bag", "Tiracolo", "Pochete", "Mochila", "Necessaire"],
    labelTecido: "4. Material",
    opcoesTecido: ["Couro Sintético", "Nylon", "Tactel", "Lona", "Poliéster"],
  },
};

// Resumos limpos e diretos por grupo (Zero jargão técnico, Zero Emojis)
const RESUMOS_GRUPO_LIMPOS = {
  cima: "Defina tipo da peça, marca, corte, tecido, cores e quantidades por tamanho.",
  baixo: "Grade adaptada automaticamente ao tipo da peça, com opção de alternar entre letras e numeração.",
  calcados: "Selecione o modelo, marca, numeração e quantidades disponíveis no lote.",
  acessorios: "Opções de estilo e material filtradas conforme o acessório escolhido.",
  perfumaria: "Informe o tipo, nome da fragrância, marca, família olfativa e volumes em ml.",
};

// ============================================================================
// 1. UTILITÁRIOS DE SILK UI E RANKING "TOP 5 MAIS USADOS"
// ============================================================================
function acionarFadeChipsSilk() {
  document.body.setAttribute("data-chip-fade", "1");
  if (timerFadeChips) clearTimeout(timerFadeChips);
  timerFadeChips = setTimeout(() => {
    document.body.removeAttribute("data-chip-fade");
  }, 220);
}

function normalizarChaveComparacao(txt) {
  return String(txt || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function deduplicarStringsPreservandoOrdem(lista) {
  const vistos = new Set();
  const resultado = [];
  for (const item of lista) {
    const limpo = String(item || "").trim();
    if (!limpo) continue;
    const chave = normalizarChaveComparacao(limpo);
    if (vistos.has(chave)) continue;
    vistos.add(chave);
    resultado.push(limpo);
  }
  return resultado;
}

/**
 * Ordena opções pela frequência real de uso em `estado.produtos`,
 * dando peso maior para produtos cadastrados no mesmo Grande Grupo.
 */
function ordenarOpcoesPorFrequencia(opcoesBase, campoExtrator, grupoAlvo) {
  const unicas = deduplicarStringsPreservandoOrdem(opcoesBase);
  const contagem = new Map();
  const produtos = Array.isArray(estado.produtos) ? estado.produtos : [];

  for (const prod of produtos) {
    const grupoProd = obterGrupoProduto(prod.modelo_nome || "")?.chave || "";
    const peso = grupoAlvo && grupoProd === grupoAlvo ? 3 : 1;
    const valores = campoExtrator(prod);
    const listaValores = Array.isArray(valores) ? valores : [valores];

    for (const val of listaValores) {
      if (!valorValido(val)) continue;
      const k = normalizarChaveComparacao(val);
      if (!k) continue;
      contagem.set(k, (contagem.get(k) || 0) + peso);
    }
  }

  return unicas
    .map((item, idxOriginal) => ({
      item,
      idxOriginal,
      score: contagem.get(normalizarChaveComparacao(item)) || 0,
      isSemMarca: normalizarChaveComparacao(item) === "sem marca",
    }))
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      if (a.isSemMarca !== b.isSemMarca) return a.isSemMarca ? 1 : -1;
      return a.idxOriginal - b.idxOriginal;
    })
    .map((x) => x.item);
}

function ordenarPaletaCoresPorFrequencia(paletaBase, grupoAlvo) {
  const mapaCores = new Map();
  for (const cor of paletaBase) {
    const nome = String(cor?.nome || "").trim();
    if (!nome || normalizarChaveComparacao(nome) === "padrao") continue;
    const k = normalizarChaveComparacao(nome);
    if (!mapaCores.has(k)) {
      mapaCores.set(k, {
        nome,
        cor_hex: resolverCorHex(nome, cor.cor_hex),
      });
    }
  }

  const contagem = new Map();
  const produtos = Array.isArray(estado.produtos) ? estado.produtos : [];
  for (const prod of produtos) {
    const grupoProd = obterGrupoProduto(prod.modelo_nome || "")?.chave || "";
    const peso = grupoAlvo && grupoProd === grupoAlvo ? 3 : 1;
    const coresProd = extrairCoresProduto(prod);
    for (const c of coresProd) {
      const k = normalizarChaveComparacao(c.nome);
      if (!k || k === "padrao") continue;
      contagem.set(k, (contagem.get(k) || 0) + peso);
      if (!mapaCores.has(k)) {
        mapaCores.set(k, { nome: c.nome, cor_hex: resolverCorHex(c.nome, c.cor_hex) });
      }
    }
  }

  return Array.from(mapaCores.entries())
    .map(([k, obj], idxOriginal) => ({
      obj,
      idxOriginal,
      score: contagem.get(k) || 0,
    }))
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.idxOriginal - b.idxOriginal;
    })
    .map((x) => x.obj);
}

/**
 * Retorna a fatia visível (Top 5 + item selecionado caso esteja fora do Top 5)
 * e quantos itens ficaram ocultos para o chip "Mostrar mais (+X)".
 */
function fatiarTopOpcoes(listaOrdenada, mostrarMaisAtivo, selecionadosSet) {
  if (mostrarMaisAtivo || listaOrdenada.length <= LIMITE_TOP_CHIPS) {
    return {
      visiveis: listaOrdenada,
      ocultosCount: 0,
      podeRecolher: listaOrdenada.length > LIMITE_TOP_CHIPS && mostrarMaisAtivo,
    };
  }

  const visiveis = listaOrdenada.slice(0, LIMITE_TOP_CHIPS);
  const chavesVisiveis = new Set(visiveis.map((v) => normalizarChaveComparacao(typeof v === "string" ? v : v.nome)));

  for (const item of listaOrdenada.slice(LIMITE_TOP_CHIPS)) {
    const k = normalizarChaveComparacao(typeof item === "string" ? item : item.nome);
    if (selecionadosSet && selecionadosSet.has(k) && !chavesVisiveis.has(k)) {
      visiveis.push(item);
      chavesVisiveis.add(k);
    }
  }

  return {
    visiveis,
    ocultosCount: Math.max(0, listaOrdenada.length - visiveis.length),
    podeRecolher: false,
  };
}

// ============================================================================
// 2. RESOLUÇÃO DE PERFIL CONTEXTUAL, MARCAS E TAMANHOS POR GRUPO / SUBTIPO
// ============================================================================
function obterPerfilContextualCamaleao() {
  const chave = estado.camaleao.grupoAtivo;
  const base = PERFIS_CAMALEAO[chave];
  if (!base) return null;

  if (chave === "acessorios") {
    const sub = SUBREGRAS_ACESSORIOS[estado.camaleao.tipoPeca];
    if (sub) {
      return {
        ...base,
        labelCorte: sub.labelCorte,
        opcoesCorte: sub.opcoesCorte,
        labelTecido: sub.labelTecido,
        opcoesTecido: sub.opcoesTecido,
      };
    }
  }

  return base;
}

function obterMarcasContextuaisDoGrupo(chaveGrupo) {
  const marcasBase = Array.isArray(MARCAS_POR_GRUPO[chaveGrupo])
    ? [...MARCAS_POR_GRUPO[chaveGrupo]]
    : [];

  if (chaveGrupo === "perfumaria" && !marcasBase.includes("Importado")) {
    marcasBase.splice(Math.max(0, marcasBase.length - 1), 0, "Importado");
  }

  const extrasSessao = marcasExtrasPorGrupo[chaveGrupo] || [];

  // Inclui marcas já utilizadas em produtos reais pertencentes ao mesmo grupo
  const marcasUsadasNoGrupo = [];
  for (const p of estado.produtos || []) {
    const g = obterGrupoProduto(p.modelo_nome || "")?.chave;
    if (g === chaveGrupo && valorValido(p.marca)) {
      marcasUsadasNoGrupo.push(String(p.marca).trim());
    }
  }

  const combinadas = [...marcasBase, ...extrasSessao, ...marcasUsadasNoGrupo];
  return ordenarOpcoesPorFrequencia(combinadas, (p) => p.marca, chaveGrupo);
}

function ehPecaBaixoLetrasPorPadrao(tipoPeca) {
  const t = normalizarChaveComparacao(tipoPeca);
  return t === "shorts" || t === "short" || t === "sunga";
}

function obterTamanhosAtivosCamaleao() {
  const chave = estado.camaleao.grupoAtivo;
  const perfil = PERFIS_CAMALEAO[chave];
  if (!perfil) return [];

  if (chave === "acessorios") {
    return ["ÚNICO"];
  }

  if (chave === "baixo") {
    if (estado.camaleao.modoGradeBaixo === "letras") {
      return ["P", "M", "G", "GG", "XG"];
    }
    return ["36", "38", "40", "42", "44", "46", "48"];
  }

  return Array.isArray(perfil.tamanhos) ? [...perfil.tamanhos] : ["ÚNICO"];
}

// ============================================================================
// 3. CARREGAMENTO DE ATRIBUTOS DO BACK-END E PERSISTÊNCIA DE EXTRAS
// ============================================================================
async function carregarAtributosCamaleao() {
  try {
    const dados = await requisitarApi("/api/atributos");
    const atr = dados.atributos || dados || {};
    estado.atributos = atr;

    // Mescla cores customizadas cadastradas no banco sem perder a paleta padrão
    if (Array.isArray(atr.cor) && atr.cor.length > 0) {
      const mapa = new Map();
      for (const c of PALETA_CORES_PADRAO) {
        mapa.set(normalizarChaveComparacao(c.nome), { ...c });
      }
      for (const item of atr.cor) {
        const valorBruto = typeof item === "string" ? item : item?.valor || item?.nome || "";
        if (!valorBruto) continue;
        const [nomeParte, hexParte] = String(valorBruto).split("|");
        const nomeLimpo = String(nomeParte || "").trim();
        const k = normalizarChaveComparacao(nomeLimpo);
        if (!nomeLimpo || k === "padrao") continue;
        if (!mapa.has(k)) {
          mapa.set(k, {
            nome: nomeLimpo,
            cor_hex: resolverCorHex(nomeLimpo, hexParte),
          });
        }
      }
      estado.camaleao.paletaCores = Array.from(mapa.values());
    }

    if (estado.camaleao.grupoAtivo) {
      renderizarChipsMarcaCamaleao();
      renderizarPaletaCoresCamaleao();
    }
  } catch (_erro) {
    // Fallback silencioso usando os catálogos locais do core.js
  }
}

async function salvarAtributoCustomizadoApi(tipo, valor) {
  try {
    await requisitarApi("/api/atributos", {
      metodo: "POST",
      corpo: { tipo, valor },
    });
  } catch (_e) {
    // Não interrompe o fluxo de cadastro caso já exista ou falhe
  }
}

// ============================================================================
// 4. SELEÇÃO DE GRANDE GRUPO E REVELAÇÃO SILK UI
// ============================================================================
function comporModeloNomeCamaleao() {
  const tipo = String(estado.camaleao.tipoPeca || "").trim();
  const det = String(estado.camaleao.detalheModelo || "").trim();
  if (!tipo && !det) return "Selecione o Tipo da Peça";
  if (tipo && det) return `${tipo} ${det}`;
  return tipo || det;
}

function atualizarPreviewModeloCamaleao() {
  const texto = comporModeloNomeCamaleao();
  if (dom.camaleaoPreviewModelo) {
    dom.camaleaoPreviewModelo.textContent = `Modelo: ${texto}`;
  }
}

function selecionarGrandeGrupoCamaleao(chaveGrupo) {
  const perfil = PERFIS_CAMALEAO[chaveGrupo];
  if (!perfil) return;

  const trocouGrupo = estado.camaleao.grupoAtivo !== chaveGrupo;
  estado.camaleao.grupoAtivo = chaveGrupo;

  // Destaca card ativo nos 5 Grandes Grupos
  document.querySelectorAll("#seletor-grupos-camaleao [data-camaleao-grupo]").forEach((btn) => {
    btn.classList.toggle("ativo", btn.dataset.camaleaoGrupo === chaveGrupo);
  });

  // Oculta banner inicial e revela formulário com animação Silk UI
  dom.bannerAguardandoGrupo?.classList.add("hidden");
  if (dom.formCamaleaoContainer) {
    const estavaOculto = dom.formCamaleaoContainer.classList.contains("hidden");
    dom.formCamaleaoContainer.classList.remove("hidden");
    if (!estavaOculto && trocouGrupo) {
      dom.formCamaleaoContainer.style.animation = "none";
      void dom.formCamaleaoContainer.offsetWidth;
      dom.formCamaleaoContainer.style.animation = "";
    }
  }

  // Reseta seleções contextuais ao trocar de grupo
  const primeiroTipo = perfil.tipos[0] || "";
  estado.camaleao.tipoPeca = primeiroTipo;
  estado.camaleao.detalheModelo = "";
  estado.camaleao.marca = "";
  estado.camaleao.corte = "N/A";
  estado.camaleao.tecido = "N/A";
  estado.camaleao.mostrarMaisMarcas = false;
  estado.camaleao.mostrarMaisCortes = false;
  estado.camaleao.mostrarMaisTecidos = false;
  estado.camaleao.mostrarMaisCores = false;
  estado.camaleao.gradeQuantidades = {};

  if (dom.inputDetalheModelo) dom.inputDetalheModelo.value = "";
  dom.boxOutraMarca?.classList.add("hidden");
  dom.boxOutroCorte?.classList.add("hidden");
  dom.boxOutroTecido?.classList.add("hidden");

  // Regras específicas por grupo
  const ehPerfumaria = chaveGrupo === "perfumaria";
  const ehAcessorios = chaveGrupo === "acessorios";
  const ehBaixo = chaveGrupo === "baixo";

  estado.camaleao.corTravadaPerfumaria = ehPerfumaria;
  estado.camaleao.tamanhoTravadoUnico = ehAcessorios;
  estado.camaleao.ocultarTecido = ehPerfumaria;
  estado.camaleao.ocultarCorte = false;

  if (ehBaixo) {
    estado.camaleao.modoGradeBaixo = ehPecaBaixoLetrasPorPadrao(primeiroTipo) ? "letras" : "numerico";
  }

  if (ehPerfumaria) {
    estado.camaleao.coresSelecionadas = [{ nome: "Padrão", cor_hex: "#D4AF37" }];
  } else {
    estado.camaleao.coresSelecionadas = [];
  }

  if (ehAcessorios) {
    estado.camaleao.gradeQuantidades = { "ÚNICO": 1 };
  }

  // Atualiza cabeçalhos e textos contextuais
  if (dom.camaleaoBadgeAtivo) {
    dom.camaleaoBadgeAtivo.textContent = perfil.titulo;
  }
  if (dom.camaleaoRegraAtiva) {
    dom.camaleaoRegraAtiva.textContent = RESUMOS_GRUPO_LIMPOS[chaveGrupo] || "";
  }

  if (dom.labelDetalheModelo) {
    dom.labelDetalheModelo.textContent = ehPerfumaria
      ? "1.2 Nome da Fragrância / Linha *"
      : "1.2 Complemento do Modelo (Opcional)";
  }
  if (dom.inputDetalheModelo) {
    dom.inputDetalheModelo.placeholder = ehPerfumaria
      ? "Ex: Asad, Fakhar, 212 VIP, Sauvage..."
      : "Ex: Básica, Listrada, Estampada, Cargo...";
  }

  // Visibilidade contextual dos blocos (Perfumaria oculta Cores e Tecido)
  dom.blocoCamaleaoCores?.classList.toggle("hidden", ehPerfumaria);
  dom.avisoCorPerfumaria?.classList.add("hidden");
  dom.blocoCamaleaoTecido?.classList.toggle("hidden", ehPerfumaria);

  // Acessórios: sem banner vermelho e sem botões em massa desnecessários
  dom.avisoTamanhoUnico?.classList.add("hidden");
  dom.btnGradeMaisUm?.classList.toggle("hidden", ehAcessorios);
  dom.btnGradeZerar?.classList.toggle("hidden", ehAcessorios);

  atualizarPreviewModeloCamaleao();
  renderizarChipsTipoPecaCamaleao();
  renderizarChipsMarcaCamaleao();
  renderizarChipsCorteETecidoCamaleao();
  renderizarPaletaCoresCamaleao();
  sincronizarBotaoAlternarGradeBaixo();
  renderizarGradeTamanhosCamaleao();
  atualizarCalculadoraCamaleao();
}

// ============================================================================
// 5. RENDERIZAÇÃO DE CHIPS (TIPO, MARCA, CORTE, TECIDO, CORES) COM TOP 5
// ============================================================================
function renderizarChipsTipoPecaCamaleao() {
  if (!dom.chipsTipoPeca) return;
  const perfil = PERFIS_CAMALEAO[estado.camaleao.grupoAtivo];
  if (!perfil) {
    dom.chipsTipoPeca.innerHTML = "";
    return;
  }

  const tiposOrdenados = ordenarOpcoesPorFrequencia(
    perfil.tipos,
    (p) => String(p.modelo_nome || "").split(" ")[0],
    estado.camaleao.grupoAtivo
  );

  dom.chipsTipoPeca.innerHTML = tiposOrdenados
    .map((tipo) => {
      const ativo = estado.camaleao.tipoPeca === tipo;
      return `
        <button
          type="button"
          class="chip-camaleao ${ativo ? "ativo" : ""}"
          data-camaleao-tipo="${escapeHtml(tipo)}"
        >
          ${escapeHtml(tipo)}
        </button>
      `;
    })
    .join("");
}

function renderizarChipsMarcaCamaleao() {
  if (!dom.chipsMarca) return;
  const chaveGrupo = estado.camaleao.grupoAtivo;
  if (!chaveGrupo) return;

  const marcasOrdenadas = obterMarcasContextuaisDoGrupo(chaveGrupo);
  const selSet = new Set(
    estado.camaleao.marca ? [normalizarChaveComparacao(estado.camaleao.marca)] : []
  );
  const { visiveis, ocultosCount, podeRecolher } = fatiarTopOpcoes(
    marcasOrdenadas,
    estado.camaleao.mostrarMaisMarcas,
    selSet
  );

  if (dom.marcaSelecionadaLabel) {
    dom.marcaSelecionadaLabel.textContent = estado.camaleao.marca || "Selecione";
  }

  const htmlMarcas = visiveis
    .map((marca) => {
      const ativo = normalizarChaveComparacao(estado.camaleao.marca) === normalizarChaveComparacao(marca);
      return `
        <button
          type="button"
          class="chip-camaleao ${ativo ? "ativo" : ""}"
          data-camaleao-marca="${escapeHtml(marca)}"
        >
          ${escapeHtml(marca)}
        </button>
      `;
    })
    .join("");

  let htmlToggle = "";
  if (ocultosCount > 0) {
    htmlToggle = `
      <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="marcas">
        Mostrar mais (+${ocultosCount})
      </button>
    `;
  } else if (podeRecolher) {
    htmlToggle = `
      <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="marcas">
        Mostrar menos
      </button>
    `;
  }

  const htmlOutra = `
    <button type="button" class="chip-camaleao chip-outro" data-abrir-outra="marca">
      + Outra
    </button>
  `;

  dom.chipsMarca.innerHTML = htmlMarcas + htmlToggle + htmlOutra;
}

function renderizarChipsCorteETecidoCamaleao() {
  const perfil = obterPerfilContextualCamaleao();
  if (!perfil) return;
  const chaveGrupo = estado.camaleao.grupoAtivo;

  // --- CORTE / ESTILO ---
  if (dom.labelCamaleaoCorte) {
    dom.labelCamaleaoCorte.textContent = perfil.labelCorte || "3. Corte / Caimento";
  }
  if (dom.corteSelecionadoLabel) {
    dom.corteSelecionadoLabel.textContent =
      valorValido(estado.camaleao.corte) ? estado.camaleao.corte : "N/A";
  }

  if (dom.chipsCorte) {
    const baseCortes = [...(perfil.opcoesCorte || []), ...(estado.camaleao.cortesExtras || [])];
    const cortesOrdenados = ordenarOpcoesPorFrequencia(baseCortes, (p) => p.corte, chaveGrupo);
    const selCorte = new Set(
      valorValido(estado.camaleao.corte) ? [normalizarChaveComparacao(estado.camaleao.corte)] : []
    );
    const { visiveis, ocultosCount, podeRecolher } = fatiarTopOpcoes(
      cortesOrdenados,
      estado.camaleao.mostrarMaisCortes,
      selCorte
    );

    const htmlNa = `
      <button
        type="button"
        class="chip-camaleao ${!valorValido(estado.camaleao.corte) ? "ativo" : ""}"
        data-camaleao-corte="N/A"
      >
        N/A
      </button>
    `;

    const htmlOpcoes = visiveis
      .map((op) => {
        const ativo = normalizarChaveComparacao(estado.camaleao.corte) === normalizarChaveComparacao(op);
        return `
          <button
            type="button"
            class="chip-camaleao ${ativo ? "ativo" : ""}"
            data-camaleao-corte="${escapeHtml(op)}"
          >
            ${escapeHtml(op)}
          </button>
        `;
      })
      .join("");

    let htmlToggle = "";
    if (ocultosCount > 0) {
      htmlToggle = `
        <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="cortes">
          Mostrar mais (+${ocultosCount})
        </button>
      `;
    } else if (podeRecolher) {
      htmlToggle = `
        <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="cortes">
          Mostrar menos
        </button>
      `;
    }

    const htmlOutro = `
      <button type="button" class="chip-camaleao chip-outro" data-abrir-outra="corte">
        + Outra
      </button>
    `;

    dom.chipsCorte.innerHTML = htmlNa + htmlOpcoes + htmlToggle + htmlOutro;
  }

  // --- TECIDO / MATERIAL ---
  const ocultarTecido = Boolean(estado.camaleao.ocultarTecido || chaveGrupo === "perfumaria");
  dom.blocoCamaleaoTecido?.classList.toggle("hidden", ocultarTecido);
  if (ocultarTecido) return;

  if (dom.labelCamaleaoTecido) {
    dom.labelCamaleaoTecido.textContent = perfil.labelTecido || "4. Tecido";
  }
  if (dom.tecidoSelecionadoLabel) {
    dom.tecidoSelecionadoLabel.textContent =
      valorValido(estado.camaleao.tecido) ? estado.camaleao.tecido : "N/A";
  }

  if (dom.chipsTecido) {
    const baseTecidos = [...(perfil.opcoesTecido || []), ...(estado.camaleao.tecidosExtras || [])];
    const tecidosOrdenados = ordenarOpcoesPorFrequencia(baseTecidos, (p) => p.tecido, chaveGrupo);
    const selTecido = new Set(
      valorValido(estado.camaleao.tecido) ? [normalizarChaveComparacao(estado.camaleao.tecido)] : []
    );
    const { visiveis, ocultosCount, podeRecolher } = fatiarTopOpcoes(
      tecidosOrdenados,
      estado.camaleao.mostrarMaisTecidos,
      selTecido
    );

    const htmlNa = `
      <button
        type="button"
        class="chip-camaleao ${!valorValido(estado.camaleao.tecido) ? "ativo" : ""}"
        data-camaleao-tecido="N/A"
      >
        N/A
      </button>
    `;

    const htmlOpcoes = visiveis
      .map((op) => {
        const ativo = normalizarChaveComparacao(estado.camaleao.tecido) === normalizarChaveComparacao(op);
        return `
          <button
            type="button"
            class="chip-camaleao ${ativo ? "ativo" : ""}"
            data-camaleao-tecido="${escapeHtml(op)}"
          >
            ${escapeHtml(op)}
          </button>
        `;
      })
      .join("");

    let htmlToggle = "";
    if (ocultosCount > 0) {
      htmlToggle = `
        <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="tecidos">
          Mostrar mais (+${ocultosCount})
        </button>
      `;
    } else if (podeRecolher) {
      htmlToggle = `
        <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="tecidos">
          Mostrar menos
        </button>
      `;
    }

    const htmlOutro = `
      <button type="button" class="chip-camaleao chip-outro" data-abrir-outra="tecido">
        + Outra
      </button>
    `;

    dom.chipsTecido.innerHTML = htmlNa + htmlOpcoes + htmlToggle + htmlOutro;
  }
}

function renderizarPaletaCoresCamaleao() {
  if (!dom.paletaCoresCamaleao) return;
  if (estado.camaleao.grupoAtivo === "perfumaria") {
    dom.blocoCamaleaoCores?.classList.add("hidden");
    return;
  }

  dom.blocoCamaleaoCores?.classList.remove("hidden");

  const selecionadas = estado.camaleao.coresSelecionadas || [];
  const setSel = new Set(selecionadas.map((c) => normalizarChaveComparacao(c.nome)));

  if (dom.resumoCoresSelecionadas) {
    if (selecionadas.length === 0) {
      dom.resumoCoresSelecionadas.textContent = "Nenhuma selecionada";
    } else if (selecionadas.length <= 3) {
      dom.resumoCoresSelecionadas.textContent = selecionadas.map((c) => c.nome).join(", ");
    } else {
      dom.resumoCoresSelecionadas.textContent = `${selecionadas.length} cores selecionadas`;
    }
  }
  dom.btnLimparCoresCamaleao?.classList.toggle("hidden", selecionadas.length === 0);

  const coresOrdenadas = ordenarPaletaCoresPorFrequencia(
    estado.camaleao.paletaCores,
    estado.camaleao.grupoAtivo
  );

  const { visiveis, ocultosCount, podeRecolher } = fatiarTopOpcoes(
    coresOrdenadas,
    estado.camaleao.mostrarMaisCores,
    setSel
  );

  const htmlCores = visiveis
    .map((cor) => {
      const ativa = setSel.has(normalizarChaveComparacao(cor.nome));
      const hex = resolverCorHex(cor.nome, cor.cor_hex);
      return `
        <button
          type="button"
          class="chip-cor-camaleao ${ativa ? "ativo" : ""}"
          data-camaleao-cor="${escapeHtml(cor.nome)}"
          data-camaleao-hex="${escapeHtml(hex)}"
          title="${escapeHtml(cor.nome)} (${escapeHtml(hex)})"
        >
          <span class="bolinha-paleta-cor" style="background-color: ${escapeHtml(hex)};"></span>
          <span>${escapeHtml(cor.nome)}</span>
        </button>
      `;
    })
    .join("");

  let htmlToggle = "";
  if (ocultosCount > 0) {
    htmlToggle = `
      <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="cores">
        Mostrar mais (+${ocultosCount})
      </button>
    `;
  } else if (podeRecolher) {
    htmlToggle = `
      <button type="button" class="chip-camaleao chip-mostrar-mais" data-toggle-mais="cores">
        Mostrar menos
      </button>
    `;
  }

  dom.paletaCoresCamaleao.innerHTML = htmlCores + htmlToggle;
}

// ============================================================================
// 6. GRADE DE TAMANHOS INTELIGENTE (COM TOGGLE EM BAIXO E PULSO SILK UI)
// ============================================================================
function sincronizarBotaoAlternarGradeBaixo() {
  const containerBtns = dom.blocoCamaleaoGrade?.querySelector(".camaleao-header-inline-btns");
  if (!containerBtns) return;

  let btnToggle = document.getElementById("btn-alternar-grade-baixo");
  if (estado.camaleao.grupoAtivo !== "baixo") {
    btnToggle?.classList.add("hidden");
    return;
  }

  if (!btnToggle) {
    btnToggle = document.createElement("button");
    btnToggle.type = "button";
    btnToggle.id = "btn-alternar-grade-baixo";
    btnToggle.className = "btn-alternar-grade";
    containerBtns.insertBefore(btnToggle, containerBtns.firstChild);
    btnToggle.addEventListener("click", () => {
      estado.camaleao.modoGradeBaixo =
        estado.camaleao.modoGradeBaixo === "letras" ? "numerico" : "letras";
      sincronizarBotaoAlternarGradeBaixo();
      renderizarGradeTamanhosCamaleao();
      atualizarCalculadoraCamaleao();
    });
  }

  btnToggle.classList.remove("hidden");
  const usandoLetras = estado.camaleao.modoGradeBaixo === "letras";
  btnToggle.textContent = usandoLetras ? "Usar Numeração (36–48)" : "Usar Letras (P–XG)";
}

function renderizarGradeTamanhosCamaleao() {
  if (!dom.gridTamanhosCamaleao) return;
  const chave = estado.camaleao.grupoAtivo;
  const perfil = PERFIS_CAMALEAO[chave];
  if (!perfil) {
    dom.gridTamanhosCamaleao.innerHTML = "";
    return;
  }

  const tamanhos = obterTamanhosAtivosCamaleao();

  if (dom.labelCamaleaoGrade) {
    if (chave === "baixo") {
      dom.labelCamaleaoGrade.textContent =
        estado.camaleao.modoGradeBaixo === "letras"
          ? "7. Grade de Tamanhos & Quantidades (Letras)"
          : "7. Grade de Tamanhos & Quantidades (Numeração)";
    } else {
      dom.labelCamaleaoGrade.textContent = perfil.labelGrade || "7. Grade de Tamanhos & Quantidades";
    }
  }

  dom.gridTamanhosCamaleao.classList.toggle("grade-tamanho-unico", tamanhos.length === 1);

  dom.gridTamanhosCamaleao.innerHTML = tamanhos
    .map((tam) => {
      const qtd = Math.max(0, parseInt(estado.camaleao.gradeQuantidades[tam] ?? 0, 10) || 0);
      return `
        <div class="celula-tamanho-camaleao ${qtd > 0 ? "com-estoque" : ""}" data-celula-tam="${escapeHtml(tam)}">
          <span class="celula-tam-rotulo">${escapeHtml(tam)}</span>
          <div class="celula-tam-controles">
            <button type="button" class="btn-step-camaleao" data-step-tam="${escapeHtml(tam)}" data-delta="-1" aria-label="Diminuir ${escapeHtml(tam)}">&minus;</button>
            <input
              type="number"
              min="0"
              step="1"
              class="inp-qtd-camaleao"
              data-input-tam="${escapeHtml(tam)}"
              value="${qtd}"
            />
            <button type="button" class="btn-step-camaleao" data-step-tam="${escapeHtml(tam)}" data-delta="1" aria-label="Aumentar ${escapeHtml(tam)}">+</button>
          </div>
        </div>
      `;
    })
    .join("");
}

function definirQuantidadeTamanhoCamaleao(tam, novaQtd, atualizarInput = true) {
  const limpa = Math.max(0, Math.min(9999, parseInt(novaQtd, 10) || 0));
  const anterior = Math.max(0, parseInt(estado.camaleao.gradeQuantidades[tam] ?? 0, 10) || 0);
  estado.camaleao.gradeQuantidades[tam] = limpa;

  const seletorSeguro = Array.from(
    dom.gridTamanhosCamaleao?.querySelectorAll(".celula-tamanho-camaleao") || []
  ).find((el) => el.dataset.celulaTam === tam);

  if (seletorSeguro) {
    if (limpa > 0 && anterior === 0) {
      seletorSeguro.classList.remove("com-estoque");
      void seletorSeguro.offsetWidth;
      seletorSeguro.classList.add("com-estoque");
    } else if (limpa === 0) {
      seletorSeguro.classList.remove("com-estoque");
    } else {
      seletorSeguro.classList.add("com-estoque");
    }

    if (atualizarInput) {
      const inp = seletorSeguro.querySelector(".inp-qtd-camaleao");
      if (inp) inp.value = String(limpa);
    }
  }

  atualizarCalculadoraCamaleao();
}

// ============================================================================
// 7. CALCULADORA VIVA DE PRECIFICAÇÃO, MARGEM E TOTAIS DO LOTE
// ============================================================================
function atualizarCalculadoraCamaleao() {
  const custo = Math.max(0, num(dom.camaleaoPrecoCusto?.value, 0));
  const venda = Math.max(0, num(dom.camaleaoPrecoVenda?.value, 0));
  const temValores = custo > 0 || venda > 0;

  const lucroUn = venda - custo;
  const margemPct = venda > 0 ? (lucroUn / venda) * 100 : 0;
  const markupPct = custo > 0 ? (lucroUn / custo) * 100 : 0;

  if (dom.vivoLucroRs) {
    dom.vivoLucroRs.textContent = formatarMoeda(temValores ? lucroUn : 0);
  }
  if (dom.vivoMargemPct) {
    dom.vivoMargemPct.textContent = `${(temValores ? margemPct : 0).toFixed(1)}%`;
  }
  if (dom.vivoMarkupPct) {
    dom.vivoMarkupPct.textContent = `${(temValores ? markupPct : 0).toFixed(1)}%`;
  }

  let classeStatus = "neutro";
  let textoBadge = "Aguardando valores";

  if (temValores && venda > 0) {
    if (lucroUn < 0) {
      classeStatus = "baixa";
      textoBadge = "Prejuízo Operacional";
    } else if (margemPct < 15) {
      classeStatus = "baixa";
      textoBadge = "Margem Baixa (< 15%)";
    } else if (margemPct < 30) {
      classeStatus = "atencao";
      textoBadge = "Margem Moderada";
    } else {
      classeStatus = "saudavel";
      textoBadge = "Margem Saudável";
    }
  }

  if (dom.cardLucroVivo) {
    dom.cardLucroVivo.className = `card-lucro-vivo ${classeStatus}`;
  }
  if (dom.vivoStatusBadge) {
    dom.vivoStatusBadge.className = `badge-margem-status ${classeStatus}`;
    dom.vivoStatusBadge.textContent = textoBadge;
  }

  // Totais do Lote conforme os tamanhos visíveis no perfil atual
  const tamanhosAtivos = obterTamanhosAtivosCamaleao();
  let qtdTamanhosComEstoque = 0;
  let totalPecas = 0;

  for (const tam of tamanhosAtivos) {
    const q = Math.max(0, parseInt(estado.camaleao.gradeQuantidades[tam] ?? 0, 10) || 0);
    if (q > 0) {
      qtdTamanhosComEstoque += 1;
      totalPecas += q;
    }
  }

  if (dom.resumoQtdTamanhos) {
    dom.resumoQtdTamanhos.textContent = String(qtdTamanhosComEstoque);
  }
  if (dom.resumoTotalPecas) {
    dom.resumoTotalPecas.textContent = `${totalPecas} ${totalPecas === 1 ? "peça" : "peças"}`;
  }
  if (dom.resumoCustoTotal) {
    dom.resumoCustoTotal.textContent = formatarMoeda(totalPecas * custo);
  }
  if (dom.resumoVendaTotal) {
    dom.resumoVendaTotal.textContent = formatarMoeda(totalPecas * venda);
  }
}

// ============================================================================
// 8. SUBMISSÃO DO CADASTRO (POST /api/produtos) + BANNER PÓS-CADASTRO COM QR
// ============================================================================
function garantirBotaoQrNoBannerSucesso() {
  const containerAcoes = dom.bannerSucessoCadastro?.querySelector(".banner-sucesso-acoes");
  if (!containerAcoes) return null;

  let btnQr = document.getElementById("btn-sucesso-imprimir-qr");
  if (!btnQr) {
    btnQr = document.createElement("button");
    btnQr.type = "button";
    btnQr.id = "btn-sucesso-imprimir-qr";
    btnQr.className = "btn-secundario-sistema btn-compacto";
    btnQr.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right:5px;vertical-align:-2px;">
        <rect x="3" y="3" width="7" height="7"></rect>
        <rect x="14" y="3" width="7" height="7"></rect>
        <rect x="3" y="14" width="7" height="7"></rect>
        <path d="M14 14h3v3h-3z"></path>
        <path d="M20 14v3"></path>
        <path d="M14 20h7"></path>
      </svg>
      <span>Imprimir Etiquetas deste Lote</span>
    `;
    const btnFechar = document.getElementById("btn-fechar-banner-sucesso");
    if (btnFechar) {
      containerAcoes.insertBefore(btnQr, btnFechar);
    } else {
      containerAcoes.appendChild(btnQr);
    }

    btnQr.addEventListener("click", () => {
      if (!ultimoProdutoIdCadastrado) {
        exibirToast("Nenhum lote recém-cadastrado selecionado.", "aviso");
        return;
      }
      if (typeof window.abrirModalQrCodeProduto === "function") {
        window.abrirModalQrCodeProduto(ultimoProdutoIdCadastrado);
      } else {
        exibirToast("Gerador de etiquetas indisponível no momento.", "erro");
      }
    });
  }

  return btnQr;
}

function resetarFormularioCamaleaoCompleto() {
  estado.camaleao.grupoAtivo = null;
  estado.camaleao.tipoPeca = "";
  estado.camaleao.detalheModelo = "";
  estado.camaleao.marca = "";
  estado.camaleao.corte = "N/A";
  estado.camaleao.tecido = "N/A";
  estado.camaleao.coresSelecionadas = [];
  estado.camaleao.gradeQuantidades = {};

  if (dom.inputDetalheModelo) dom.inputDetalheModelo.value = "";
  if (dom.camaleaoPrecoCusto) dom.camaleaoPrecoCusto.value = "";
  if (dom.camaleaoPrecoVenda) dom.camaleaoPrecoVenda.value = "";

  document.querySelectorAll("#seletor-grupos-camaleao [data-camaleao-grupo]").forEach((btn) => {
    btn.classList.remove("ativo");
  });

  dom.formCamaleaoContainer?.classList.add("hidden");
  dom.bannerAguardandoGrupo?.classList.remove("hidden");
  atualizarCalculadoraCamaleao();
}

async function salvarProdutoCamaleao(evento) {
  if (evento) evento.preventDefault();

  const chaveGrupo = estado.camaleao.grupoAtivo;
  if (!chaveGrupo) {
    exibirToast("Selecione primeiro um dos 5 Grandes Grupos.", "aviso");
    return;
  }

  const tipoPeca = String(estado.camaleao.tipoPeca || "").trim();
  const detalhe = String(dom.inputDetalheModelo?.value || estado.camaleao.detalheModelo || "").trim();
  estado.camaleao.detalheModelo = detalhe;

  if (!tipoPeca) {
    exibirToast("Selecione o Tipo da Peça no item 1.1.", "aviso");
    return;
  }

  if (chaveGrupo === "perfumaria" && !detalhe) {
    exibirToast("Informe o nome da fragrância ou linha no item 1.2.", "aviso");
    dom.inputDetalheModelo?.focus();
    return;
  }

  const marca = String(estado.camaleao.marca || "").trim() || "Sem Marca";

  const precoCusto = Math.max(0, num(dom.camaleaoPrecoCusto?.value, 0));
  const precoVenda = Math.max(0, num(dom.camaleaoPrecoVenda?.value, 0));
  if (precoVenda <= 0) {
    exibirToast("Informe um Preço de Venda válido maior que zero.", "aviso");
    dom.camaleaoPrecoVenda?.focus();
    return;
  }

  let corPrincipalNome = "Padrão";
  let corPrincipalHex = "#D4AF37";
  let coresTagsStr = "Padrão|#D4AF37";

  if (chaveGrupo !== "perfumaria") {
    const coresMarcadas = (estado.camaleao.coresSelecionadas || []).map((c) => ({
      nome: c.nome,
      cor_hex: resolverCorHex(c.nome, c.cor_hex),
    }));
    if (coresMarcadas.length > 0) {
      corPrincipalNome = coresMarcadas[0].nome;
      corPrincipalHex = coresMarcadas[0].cor_hex;
      coresTagsStr = coresMarcadas.map((c) => `${c.nome}|${c.cor_hex}`).join(",");
    } else {
      corPrincipalNome = "Padrão";
      corPrincipalHex = PERFIS_CAMALEAO[chaveGrupo]?.cor || "#3b82f6";
      coresTagsStr = "";
    }
  }

  const tamanhosVisiveis = obterTamanhosAtivosCamaleao();
  const gradeEnvio = [];
  let totalPecasLote = 0;

  for (const tam of tamanhosVisiveis) {
    const qtd = Math.max(0, parseInt(estado.camaleao.gradeQuantidades[tam] ?? 0, 10) || 0);
    if (qtd > 0) {
      gradeEnvio.push({ tamanho: tam, quantidade: qtd });
      totalPecasLote += qtd;
    }
  }

  if (gradeEnvio.length === 0 || totalPecasLote <= 0) {
    exibirToast("Informe a quantidade em estoque de pelo menos um tamanho na grade.", "aviso");
    return;
  }

  const modeloNome = comporModeloNomeCamaleao();
  const corteEnvio = valorValido(estado.camaleao.corte) ? estado.camaleao.corte : "N/A";
  const tecidoEnvio =
    chaveGrupo === "perfumaria" || !valorValido(estado.camaleao.tecido)
      ? "N/A"
      : estado.camaleao.tecido;

  const variacoesPayload = gradeEnvio.map((g) => ({
    tamanho: window.normalizarTamanhoFront ? window.normalizarTamanhoFront(g.tamanho) : g.tamanho,
    cor: corPrincipalNome,
    cor_hex: corPrincipalHex,
    codigo_barras: "",
    estoque: g.quantidade,
    preco_custo: precoCusto,
    preco_venda: precoVenda,
  }));

  const btnSalvar = dom.btnSalvarCamaleao;
  const textoOriginalBtn = btnSalvar?.textContent || "Salvar Produto no Estoque";
  if (btnSalvar) {
    btnSalvar.disabled = true;
    btnSalvar.textContent = "Salvando lote no estoque...";
  }

  try {
    const resposta = await requisitarApi("/api/produtos", {
      metodo: "POST",
      corpo: {
        modelo_nome: modeloNome,
        marca,
        corte: corteEnvio,
        tecido: tecidoEnvio,
        cores_tags: coresTagsStr,
        cor: corPrincipalNome,
        cor_hex: corPrincipalHex,
        preco_custo: precoCusto,
        preco_venda: precoVenda,
        variacoes: variacoesPayload,
      },
    });

    ultimoProdutoIdCadastrado = Number(resposta.produto_id || resposta.id || 0) || null;

    // Atualiza o estoque global em memória imediatamente (necessário para o modal de etiquetas QR e PDV)
    if (typeof window.carregarEstoque === "function") {
      await window.carregarEstoque(true);
    }

    // Exibe banner de sucesso no topo com atalhos diretos ("Ver na Vitrine" + "Imprimir Etiquetas deste Lote")
    garantirBotaoQrNoBannerSucesso();
    if (dom.tituloSucessoCadastro) {
      dom.tituloSucessoCadastro.textContent = `${modeloNome} (${marca}) salvo no estoque`;
    }
    if (dom.detalheSucessoCadastro) {
      const resumoGrades = gradeEnvio.map((g) => `${g.tamanho}: ${g.quantidade}`).join(" · ");
      dom.detalheSucessoCadastro.textContent = `${totalPecasLote} ${
        totalPecasLote === 1 ? "peça registrada" : "peças registradas"
      } (${resumoGrades}) · Venda ${formatarMoeda(precoVenda)}`;
    }
    dom.bannerSucessoCadastro?.classList.remove("hidden");

    exibirToast(`Produto "${modeloNome}" cadastrado com sucesso.`, "sucesso");

    // Prepara formulário limpo no mesmo grupo para agilizar cadastros em sequência
    estado.camaleao.detalheModelo = "";
    if (dom.inputDetalheModelo) dom.inputDetalheModelo.value = "";
    if (dom.camaleaoPrecoCusto) dom.camaleaoPrecoCusto.value = "";
    if (dom.camaleaoPrecoVenda) dom.camaleaoPrecoVenda.value = "";
    estado.camaleao.gradeQuantidades = chaveGrupo === "acessorios" ? { "ÚNICO": 1 } : {};
    if (chaveGrupo !== "perfumaria") {
      estado.camaleao.coresSelecionadas = [];
    }

    atualizarPreviewModeloCamaleao();
    renderizarPaletaCoresCamaleao();
    renderizarGradeTamanhosCamaleao();
    atualizarCalculadoraCamaleao();
    dom.mainScrollArea?.scrollTo({ top: 0, behavior: "smooth" });
  } catch (erro) {
    exibirToast(`Erro ao cadastrar produto: ${erro.message}`, "erro");
  } finally {
    if (btnSalvar) {
      btnSalvar.disabled = false;
      btnSalvar.textContent = textoOriginalBtn;
    }
  }
}

// ============================================================================
// 9. REGISTRO DE EVENTOS DA ABA CADASTRAR
// ============================================================================
function adicionarOpcaoInlineCustomizada(tipoCampo) {
  const chaveGrupo = estado.camaleao.grupoAtivo;
  if (!chaveGrupo) return;

  if (tipoCampo === "marca") {
    const val = String(dom.inputOutraMarca?.value || "").trim();
    if (!val) return;
    if (!marcasExtrasPorGrupo[chaveGrupo]) marcasExtrasPorGrupo[chaveGrupo] = [];
    marcasExtrasPorGrupo[chaveGrupo].push(val);
    estado.camaleao.marca = val;
    if (dom.inputOutraMarca) dom.inputOutraMarca.value = "";
    dom.boxOutraMarca?.classList.add("hidden");
    salvarAtributoCustomizadoApi("marca", val);
    renderizarChipsMarcaCamaleao();
    return;
  }

  if (tipoCampo === "corte") {
    const val = String(dom.inputOutroCorte?.value || "").trim();
    if (!val) return;
    estado.camaleao.cortesExtras.push(val);
    estado.camaleao.corte = val;
    if (dom.inputOutroCorte) dom.inputOutroCorte.value = "";
    dom.boxOutroCorte?.classList.add("hidden");
    salvarAtributoCustomizadoApi("corte", val);
    renderizarChipsCorteETecidoCamaleao();
    return;
  }

  if (tipoCampo === "tecido") {
    const val = String(dom.inputOutroTecido?.value || "").trim();
    if (!val) return;
    estado.camaleao.tecidosExtras.push(val);
    estado.camaleao.tecido = val;
    if (dom.inputOutroTecido) dom.inputOutroTecido.value = "";
    dom.boxOutroTecido?.classList.add("hidden");
    salvarAtributoCustomizadoApi("tecido", val);
    renderizarChipsCorteETecidoCamaleao();
  }
}

function adicionarNovaCorCustomizadaCamaleao() {
  const nome = String(dom.inputNovaCorNome?.value || "").trim();
  const hex = resolverCorHex(nome, dom.inputNovaCorHex?.value || "#2563eb");
  if (!nome) {
    exibirToast("Digite o nome da nova cor antes de adicionar.", "aviso");
    dom.inputNovaCorNome?.focus();
    return;
  }

  const chave = normalizarChaveComparacao(nome);
  const existePaleta = estado.camaleao.paletaCores.some(
    (c) => normalizarChaveComparacao(c.nome) === chave
  );
  if (!existePaleta) {
    estado.camaleao.paletaCores.unshift({ nome, cor_hex: hex });
    salvarAtributoCustomizadoApi("cor", `${nome}|${hex}`);
  }

  const jaSelecionada = estado.camaleao.coresSelecionadas.some(
    (c) => normalizarChaveComparacao(c.nome) === chave
  );
  if (!jaSelecionada) {
    estado.camaleao.coresSelecionadas.push({ nome, cor_hex: hex });
  }

  if (dom.inputNovaCorNome) dom.inputNovaCorNome.value = "";
  renderizarPaletaCoresCamaleao();
}

function registrarEventosCadastro() {
  if (eventosCadastroRegistrados) return;
  eventosCadastroRegistrados = true;

  // Seleção dos 5 Grandes Grupos
  dom.seletorGruposCamaleao?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-camaleao-grupo]");
    if (!btn) return;
    selecionarGrandeGrupoCamaleao(btn.dataset.camaleaoGrupo);
  });

  // Limpar / Trocar grupo
  dom.btnResetarCamaleao?.addEventListener("click", resetarFormularioCamaleaoCompleto);

  // Banner de sucesso pós-cadastro
  dom.btnFecharBannerSucesso?.addEventListener("click", () => {
    dom.bannerSucessoCadastro?.classList.add("hidden");
  });
  dom.btnSucessoVerVitrine?.addEventListener("click", () => {
    dom.bannerSucessoCadastro?.classList.add("hidden");
    alternarView("estoque");
  });

  // 1.1 Tipo da Peça (aciona sub-regras de Acessórios e grade inteligente de Baixo)
  dom.chipsTipoPeca?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-camaleao-tipo]");
    if (!btn) return;
    const novoTipo = btn.dataset.camaleaoTipo || "";
    estado.camaleao.tipoPeca = novoTipo;
    atualizarPreviewModeloCamaleao();
    renderizarChipsTipoPecaCamaleao();

    if (estado.camaleao.grupoAtivo === "acessorios") {
      const sub = SUBREGRAS_ACESSORIOS[novoTipo];
      if (sub) {
        const corteValido = sub.opcoesCorte.some(
          (op) => normalizarChaveComparacao(op) === normalizarChaveComparacao(estado.camaleao.corte)
        );
        const tecidoValido = sub.opcoesTecido.some(
          (op) => normalizarChaveComparacao(op) === normalizarChaveComparacao(estado.camaleao.tecido)
        );
        if (!corteValido) estado.camaleao.corte = "N/A";
        if (!tecidoValido) estado.camaleao.tecido = "N/A";
      }
      acionarFadeChipsSilk();
      renderizarChipsCorteETecidoCamaleao();
    } else if (estado.camaleao.grupoAtivo === "baixo") {
      const novoModo = ehPecaBaixoLetrasPorPadrao(novoTipo) ? "letras" : "numerico";
      if (estado.camaleao.modoGradeBaixo !== novoModo) {
        estado.camaleao.modoGradeBaixo = novoModo;
        sincronizarBotaoAlternarGradeBaixo();
        renderizarGradeTamanhosCamaleao();
        atualizarCalculadoraCamaleao();
      }
    }
  });

  // 1.2 Complemento do Modelo / Fragrância
  dom.inputDetalheModelo?.addEventListener("input", (e) => {
    estado.camaleao.detalheModelo = e.target.value;
    atualizarPreviewModeloCamaleao();
  });

  // 2. Marca (seleção, Mostrar mais e + Outra)
  dom.chipsMarca?.addEventListener("click", (e) => {
    const btnMarca = e.target.closest("[data-camaleao-marca]");
    if (btnMarca) {
      estado.camaleao.marca = btnMarca.dataset.camaleaoMarca || "";
      renderizarChipsMarcaCamaleao();
      return;
    }

    const btnMais = e.target.closest('[data-toggle-mais="marcas"]');
    if (btnMais) {
      estado.camaleao.mostrarMaisMarcas = !estado.camaleao.mostrarMaisMarcas;
      acionarFadeChipsSilk();
      renderizarChipsMarcaCamaleao();
      return;
    }

    const btnOutra = e.target.closest('[data-abrir-outra="marca"]');
    if (btnOutra) {
      dom.boxOutraMarca?.classList.toggle("hidden");
      if (!dom.boxOutraMarca?.classList.contains("hidden")) {
        dom.inputOutraMarca?.focus();
      }
    }
  });

  dom.btnConfirmarOutraMarca?.addEventListener("click", () => adicionarOpcaoInlineCustomizada("marca"));
  dom.inputOutraMarca?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      adicionarOpcaoInlineCustomizada("marca");
    }
  });

  // 3. Corte / Estilo (seleção, Mostrar mais e + Outra)
  dom.chipsCorte?.addEventListener("click", (e) => {
    const btnCorte = e.target.closest("[data-camaleao-corte]");
    if (btnCorte) {
      estado.camaleao.corte = btnCorte.dataset.camaleaoCorte || "N/A";
      renderizarChipsCorteETecidoCamaleao();
      return;
    }

    const btnMais = e.target.closest('[data-toggle-mais="cortes"]');
    if (btnMais) {
      estado.camaleao.mostrarMaisCortes = !estado.camaleao.mostrarMaisCortes;
      acionarFadeChipsSilk();
      renderizarChipsCorteETecidoCamaleao();
      return;
    }

    const btnOutra = e.target.closest('[data-abrir-outra="corte"]');
    if (btnOutra) {
      dom.boxOutroCorte?.classList.toggle("hidden");
      if (!dom.boxOutroCorte?.classList.contains("hidden")) {
        dom.inputOutroCorte?.focus();
      }
    }
  });

  dom.btnConfirmarOutroCorte?.addEventListener("click", () => adicionarOpcaoInlineCustomizada("corte"));
  dom.inputOutroCorte?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      adicionarOpcaoInlineCustomizada("corte");
    }
  });

  // 4. Tecido / Material (seleção, Mostrar mais e + Outra)
  dom.chipsTecido?.addEventListener("click", (e) => {
    const btnTecido = e.target.closest("[data-camaleao-tecido]");
    if (btnTecido) {
      estado.camaleao.tecido = btnTecido.dataset.camaleaoTecido || "N/A";
      renderizarChipsCorteETecidoCamaleao();
      return;
    }

    const btnMais = e.target.closest('[data-toggle-mais="tecidos"]');
    if (btnMais) {
      estado.camaleao.mostrarMaisTecidos = !estado.camaleao.mostrarMaisTecidos;
      acionarFadeChipsSilk();
      renderizarChipsCorteETecidoCamaleao();
      return;
    }

    const btnOutra = e.target.closest('[data-abrir-outra="tecido"]');
    if (btnOutra) {
      dom.boxOutroTecido?.classList.toggle("hidden");
      if (!dom.boxOutroTecido?.classList.contains("hidden")) {
        dom.inputOutroTecido?.focus();
      }
    }
  });

  dom.btnConfirmarOutroTecido?.addEventListener("click", () => adicionarOpcaoInlineCustomizada("tecido"));
  dom.inputOutroTecido?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      adicionarOpcaoInlineCustomizada("tecido");
    }
  });

  // 5. Precificação & Margem ao Vivo
  dom.camaleaoPrecoCusto?.addEventListener("input", atualizarCalculadoraCamaleao);
  dom.camaleaoPrecoVenda?.addEventListener("input", atualizarCalculadoraCamaleao);

  // 6. Paleta de Cores (múltipla seleção, Mostrar mais, Limpar e Nova Cor)
  dom.paletaCoresCamaleao?.addEventListener("click", (e) => {
    const btnMais = e.target.closest('[data-toggle-mais="cores"]');
    if (btnMais) {
      estado.camaleao.mostrarMaisCores = !estado.camaleao.mostrarMaisCores;
      acionarFadeChipsSilk();
      renderizarPaletaCoresCamaleao();
      return;
    }

    const btnCor = e.target.closest("[data-camaleao-cor]");
    if (!btnCor) return;
    const nomeCor = btnCor.dataset.camaleaoCor || "";
    const hexCor = btnCor.dataset.camaleaoHex || resolverCorHex(nomeCor, "");
    const chave = normalizarChaveComparacao(nomeCor);

    const idx = estado.camaleao.coresSelecionadas.findIndex(
      (c) => normalizarChaveComparacao(c.nome) === chave
    );
    if (idx >= 0) {
      estado.camaleao.coresSelecionadas.splice(idx, 1);
    } else {
      estado.camaleao.coresSelecionadas.push({ nome: nomeCor, cor_hex: hexCor });
    }
    renderizarPaletaCoresCamaleao();
  });

  dom.btnLimparCoresCamaleao?.addEventListener("click", () => {
    estado.camaleao.coresSelecionadas = [];
    renderizarPaletaCoresCamaleao();
  });

  dom.btnAddNovaCorCamaleao?.addEventListener("click", adicionarNovaCorCustomizadaCamaleao);
  dom.inputNovaCorNome?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      adicionarNovaCorCustomizadaCamaleao();
    }
  });

  // 7. Grade de Tamanhos & Quantidades (+1 em Todos, Zerar, +/- e digitação direta)
  dom.btnGradeMaisUm?.addEventListener("click", () => {
    const tamanhos = obterTamanhosAtivosCamaleao();
    for (const tam of tamanhos) {
      const atual = Math.max(0, parseInt(estado.camaleao.gradeQuantidades[tam] ?? 0, 10) || 0);
      definirQuantidadeTamanhoCamaleao(tam, atual + 1, true);
    }
  });

  dom.btnGradeZerar?.addEventListener("click", () => {
    const tamanhos = obterTamanhosAtivosCamaleao();
    for (const tam of tamanhos) {
      definirQuantidadeTamanhoCamaleao(tam, 0, true);
    }
  });

  dom.gridTamanhosCamaleao?.addEventListener("click", (e) => {
    const btnStep = e.target.closest("[data-step-tam]");
    if (!btnStep) return;
    const tam = btnStep.dataset.stepTam;
    const delta = parseInt(btnStep.dataset.delta || "0", 10);
    if (!tam || !delta) return;
    const atual = Math.max(0, parseInt(estado.camaleao.gradeQuantidades[tam] ?? 0, 10) || 0);
    definirQuantidadeTamanhoCamaleao(tam, Math.max(0, atual + delta), true);
  });

  dom.gridTamanhosCamaleao?.addEventListener("input", (e) => {
    const inp = e.target.closest("[data-input-tam]");
    if (!inp) return;
    const tam = inp.dataset.inputTam;
    if (!tam) return;
    definirQuantidadeTamanhoCamaleao(tam, inp.value, false);
  });

  // Submissão do formulário Camaleão
  dom.formCamaleaoContainer?.addEventListener("submit", salvarProdutoCamaleao);
}

// Exportações globais para integração com core.js e demais módulos
window.carregarAtributosCamaleao = carregarAtributosCamaleao;
window.selecionarGrandeGrupoCamaleao = selecionarGrandeGrupoCamaleao;
window.resetarFormularioCamaleaoCompleto = resetarFormularioCamaleaoCompleto;

KanembergApp.eventos.push(registrarEventosCadastro);
KanembergApp.inicializadores.push(carregarAtributosCamaleao);

if (document.readyState !== "loading") {
  registrarEventosCadastro();
  carregarAtributosCamaleao();
}
