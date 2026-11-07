/**
 * js/aba_dashboard.js — Kanemberg Sistema Desktop
 * Aba 5 Unificada: Painel Executivo (BI) + Saúde das Margens + Giro de Estoque.
 * Zero dependências externas (Gráficos 100% em SVG/CSS nativo a 60fps).
 * Rota principal: GET /api/dashboard/completo?periodo=30d&grupo=todos
 */

const estadoDash = {
  periodo: "30d", // hoje | 7d | 30d | mes | tudo
  grupo: "todos", // todos | cima | baixo | calcados | acessorios | perfumaria
  visao: "LINHA", // LINHA | MARGENS | ROSCA | MARCA | TIPO | ATRIBUTOS | ALERTAS
  dados: null,
  carregando: false,
  relogioTimer: null,
  // Filtros internos da sub-visão Saúde das Margens
  filtroFaixaMargem: "todas", // todas | critica | moderada | saudavel
  buscaMargem: "",
  ordemMargem: "menor_margem", // menor_margem | maior_margem | menor_lucro | maior_estoque
};

const DASH_META_VISOES = {
  LINHA: {
    titulo: "Evolução Temporal de Vendas e Recebimentos",
    subtitulo: "Curva diária de faturamento bruto, lucro líquido e divisão por meio de pagamento no período",
  },
  MARGENS: {
    titulo: "Auditoria de Saúde das Margens e Lucratividade",
    subtitulo: "Inspeção completa de custo, preço de venda, lucro por peça e reajuste rápido de preços",
  },
  ROSCA: {
    titulo: "Raio-X do Estoque pelos 5 Grandes Grupos",
    subtitulo: "Distribuição física de peças, capital investido (custo) e potencial de venda por categoria",
  },
  MARCA: {
    titulo: "Ranking de Desempenho por Marca",
    subtitulo: "Marcas campeãs em faturamento bruto, volume de peças vendidas e lucro líquido deixado na loja",
  },
  TIPO: {
    titulo: "Ranking por Tipo de Peça / Modelo",
    subtitulo: "Peças e modelos mais vendidos no período selecionado com análise de rentabilidade",
  },
  ATRIBUTOS: {
    titulo: "Desempenho por Corte e Tecido (Lado a Lado)",
    subtitulo: "Comparativo estratégico das modelagens e materiais preferidos pelos clientes",
  },
  ALERTAS: {
    titulo: "Alertas de Reposição Urgente e Capital Parado",
    subtitulo: "Peças acabando que precisam de compra no fornecedor vs. produtos sem giro sugeridos para promoção",
  },
};

function dashEl(id) {
  return document.getElementById(id);
}

// ============================================================================
// 1. RELÓGIO AO VIVO NO CABEÇALHO
// ============================================================================
function atualizarRelogioDashboard() {
  const elHora = dashEl("dash-relogio-hora");
  const elData = dashEl("dash-relogio-data");
  if (!elHora || !elData) return;

  const agora = new Date();
  const hh = String(agora.getHours()).padStart(2, "0");
  const mm = String(agora.getMinutes()).padStart(2, "0");
  const ss = String(agora.getSeconds()).padStart(2, "0");
  elHora.textContent = `${hh}:${mm}:${ss}`;

  const diasSemana = [
    "Domingo",
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
  ];
  const meses = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
  ];
  elData.textContent = `${diasSemana[agora.getDay()]}, ${agora.getDate()} de ${meses[agora.getMonth()]} de ${agora.getFullYear()}`;
}

function iniciarRelogioDashboard() {
  atualizarRelogioDashboard();
  if (estadoDash.relogioTimer) clearInterval(estadoDash.relogioTimer);
  estadoDash.relogioTimer = setInterval(atualizarRelogioDashboard, 1000);
}

// ============================================================================
// 2. CARREGAMENTO DE DADOS DO BACK-END
// ============================================================================
async function carregarDashboard(silencioso = false) {
  if (estadoDash.carregando) return;
  estadoDash.carregando = true;

  const palco = dashEl("dash-stage-body");
  if (palco && !estadoDash.dados) {
    palco.innerHTML = `<div class="estado-vazio"><p>Carregando inteligência do negócio...</p></div>`;
  }

  try {
    const qs = `periodo=${encodeURIComponent(estadoDash.periodo)}&grupo=${encodeURIComponent(estadoDash.grupo)}`;
    const resposta = await requisitarApi(`/api/dashboard/completo?${qs}`);
    estadoDash.dados = resposta;
    renderizarKpisDashboard();
    renderizarVisaoAtivaDashboard();
  } catch (erro) {
    console.error("[Dashboard] Erro ao carregar /api/dashboard/completo:", erro);
    if (!silencioso) {
      exibirToast(erro.message || "Não foi possível carregar o Dashboard.", "erro");
    }
    if (palco) {
      palco.innerHTML = `
        <div class="estado-vazio" style="padding: 32px; text-align: center;">
          <p style="color: #ef4444; font-weight: 700; margin-bottom: 10px;">
            Erro ao carregar indicadores: ${escapeHtml(erro.message || String(erro))}
          </p>
          <button type="button" class="btn-secundario-sistema" onclick="carregarDashboard(false)">
            Tentar Novamente
          </button>
        </div>
      `;
    }
  } finally {
    estadoDash.carregando = false;
  }
}

// ============================================================================
// 3. RENDERIZAÇÃO DOS 4 CARDS KPI DO TOPO (COUNT-UP 380ms) E BADGES DO MENU
// ============================================================================
function animarCountUpElemento(el, callbackFrame, duracaoMs = 380) {
  if (!el) return;
  if (el._rafCountUp) {
    cancelAnimationFrame(el._rafCountUp);
  }
  const inicio = performance.now();
  const passo = (agora) => {
    const dec = Math.max(0, agora - inicio);
    const t = Math.min(1, dec / duracaoMs);
    // Easing suave equivalente a cubic-bezier(0.22, 1, 0.36, 1)
    const ease = 1 - Math.pow(1 - t, 3);
    callbackFrame(ease);
    if (t < 1) {
      el._rafCountUp = requestAnimationFrame(passo);
    } else {
      el._rafCountUp = null;
    }
  };
  el._rafCountUp = requestAnimationFrame(passo);
}

function dispararAnimacoesPalcoDashboard(container) {
  if (!container) return;

  // 1. Entrada escalonada (Stagger Fade-in) nos cards, rankings e linhas da tabela
  const itensStagger = container.querySelectorAll(
    ".dash-card-interno, .dash-margem-mini-kpi, .dash-rank-row, .dash-grupo-card, .dash-alerta-card, #dash-tbody-margens tr"
  );
  itensStagger.forEach((item, idx) => {
    item.classList.add("dash-stagger-in");
    item.style.setProperty("--stagger-idx", String(Math.min(idx, 12)));
  });

  // 2. Crescimento fluido das barras horizontais (0% -> largura final) e gráficos SVG
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      container.querySelectorAll(".dash-barra-fill[data-target-width]").forEach((barra) => {
        barra.style.width = barra.dataset.targetWidth;
      });

      container.querySelectorAll(".dash-line-svg path.dash-svg-line-anim").forEach((caminho) => {
        try {
          const comp = caminho.getTotalLength();
          if (comp > 0) {
            caminho.style.strokeDasharray = `${comp}`;
            caminho.style.strokeDashoffset = `${comp}`;
            caminho.getBoundingClientRect();
            caminho.style.transition = "stroke-dashoffset 0.45s cubic-bezier(0.22, 1, 0.36, 1)";
            caminho.style.strokeDashoffset = "0";
          }
        } catch (_e) {
          // Fallback silencioso
        }
      });

      container.querySelectorAll(".dash-donut-svg circle.dash-donut-segment").forEach((fatia) => {
        const alvoArray = fatia.dataset.targetDasharray;
        if (alvoArray) {
          fatia.style.strokeDasharray = alvoArray;
          fatia.style.opacity = "1";
        }
      });
    });
  });
}

function renderizarKpisDashboard() {
  const d = estadoDash.dados;
  if (!d || !d.kpis) return;
  const k = d.kpis;

  const elFat = dashEl("dash-kpi-faturamento");
  const elFatSub = dashEl("dash-kpi-faturamento-sub");
  const fatAlvo = num(k.faturamento_bruto);
  const qtdVendasAlvo = num(k.qtd_vendas);
  const pecasVendidasAlvo = num(k.pecas_vendidas);

  animarCountUpElemento(elFat, (ease) => {
    elFat.textContent = formatarMoeda(fatAlvo * ease);
  });
  animarCountUpElemento(elFatSub, (ease) => {
    const vds = Math.round(qtdVendasAlvo * ease);
    const pcs = Math.round(pecasVendidasAlvo * ease);
    elFatSub.textContent = `${vds} venda(s) realizada(s) • ${pcs} peça(s) vendida(s)`;
  });

  const elCaixa = dashEl("dash-kpi-caixa");
  const elCaixaSub = dashEl("dash-kpi-caixa-sub");
  const caixaAlvo = num(k.caixa_real_recebido);
  const avistaAlvo = num(k.vendas_avista_periodo);
  const abatAlvo = num(k.abatimentos_fiado_periodo);

  animarCountUpElemento(elCaixa, (ease) => {
    elCaixa.textContent = formatarMoeda(caixaAlvo * ease);
  });
  animarCountUpElemento(elCaixaSub, (ease) => {
    elCaixaSub.textContent = `À vista: ${formatarMoeda(avistaAlvo * ease)} • Abat. Fiado: ${formatarMoeda(abatAlvo * ease)}`;
  });

  const elLucro = dashEl("dash-kpi-lucro");
  const elMargemBadge = dashEl("dash-kpi-margem-badge");
  const elLucroSub = dashEl("dash-kpi-lucro-sub");
  const lucroAlvo = num(k.lucro_liquido);
  const ticketAlvo = num(k.ticket_medio);
  const cmvAlvo = num(k.custo_mercadoria_vendida);

  animarCountUpElemento(elLucro, (ease) => {
    elLucro.textContent = formatarMoeda(lucroAlvo * ease);
  });
  if (elMargemBadge) {
    const mPct = num(k.margem_media_pct, 0).toFixed(1);
    elMargemBadge.textContent = `Margem ${mPct}%`;
    elMargemBadge.className = `dash-kpi-badge-inline ${
      k.margem_media_pct < 25 ? "critica" : k.margem_media_pct <= 45 ? "moderada" : "saudavel"
    }`;
  }
  animarCountUpElemento(elLucroSub, (ease) => {
    elLucroSub.textContent = `Ticket Médio: ${formatarMoeda(ticketAlvo * ease)} • CMV: ${formatarMoeda(cmvAlvo * ease)}`;
  });

  const elPat = dashEl("dash-kpi-patrimonio");
  const elPatSub = dashEl("dash-kpi-patrimonio-sub");
  const patAlvo = num(k.estoque_venda_potencial);
  const custoEstAlvo = num(k.estoque_custo_total);
  const pecasEstAlvo = num(k.estoque_pecas);
  const fiadoRuaAlvo = num(k.fiado_a_receber);

  animarCountUpElemento(elPat, (ease) => {
    elPat.textContent = formatarMoeda(patAlvo * ease);
  });
  animarCountUpElemento(elPatSub, (ease) => {
    const pcs = Math.round(pecasEstAlvo * ease);
    elPatSub.textContent = `Custo: ${formatarMoeda(custoEstAlvo * ease)} (${pcs} pçs) • Fiado Rua: ${formatarMoeda(fiadoRuaAlvo * ease)}`;
  });

  // Badges laterais nas 7 visualizações
  const badgeCriticas = dashEl("dash-badge-criticas");
  const qtdCrit = num(d.resumo_margens?.criticas, 0);
  if (badgeCriticas) {
    badgeCriticas.textContent = String(qtdCrit);
    badgeCriticas.classList.toggle("hidden", qtdCrit <= 0);
  }

  const badgeAlertas = dashEl("dash-badge-alertas");
  const qtdRep = (d.alertas?.reposicao_estoque_baixo || []).length;
  if (badgeAlertas) {
    badgeAlertas.textContent = String(qtdRep);
    badgeAlertas.classList.toggle("hidden", qtdRep <= 0);
  }
}

// ============================================================================
// 4. SELEÇÃO E ROTEAMENTO DAS 7 VISUALIZAÇÕES
// ============================================================================
function selecionarVisaoDashboard(novaVisao, reRenderizar = true) {
  if (!DASH_META_VISOES[novaVisao]) novaVisao = "LINHA";
  estadoDash.visao = novaVisao;

  document.querySelectorAll(".dash-visao-btn[data-dash-visao]").forEach((btn) => {
    btn.classList.toggle("ativo", btn.dataset.dashVisao === novaVisao);
  });

  const meta = DASH_META_VISOES[novaVisao];
  const elTit = dashEl("dash-stage-titulo");
  const elSub = dashEl("dash-stage-subtitulo");
  if (elTit) elTit.textContent = meta.titulo;
  if (elSub) elSub.textContent = meta.subtitulo;

  if (reRenderizar && estadoDash.dados) {
    renderizarVisaoAtivaDashboard();
  }
}

function renderizarVisaoAtivaDashboard() {
  const palco = dashEl("dash-stage-body");
  const controles = dashEl("dash-stage-controles");
  if (!palco || !estadoDash.dados) return;

  if (controles) controles.innerHTML = "";

  const meta = DASH_META_VISOES[estadoDash.visao] || DASH_META_VISOES.LINHA;
  const elTit = dashEl("dash-stage-titulo");
  const elSub = dashEl("dash-stage-subtitulo");
  if (elTit) elTit.textContent = meta.titulo;
  if (elSub) elSub.textContent = meta.subtitulo;

  switch (estadoDash.visao) {
    case "LINHA":
      renderizarVisaoLinhaSVG(palco);
      break;
    case "MARGENS":
      renderizarVisaoSaudeMargens(palco, controles);
      break;
    case "ROSCA":
      renderizarVisaoRoscaEstoque(palco);
      break;
    case "MARCA":
      renderizarVisaoBarrasRanking(palco, estadoDash.dados.ranking_marcas || [], "#3b82f6", "Marca");
      break;
    case "TIPO":
      renderizarVisaoBarrasRanking(palco, estadoDash.dados.ranking_tipos || [], "#f59e0b", "Tipo / Modelo");
      break;
    case "ATRIBUTOS":
      renderizarVisaoCorteTecido(palco);
      break;
    case "ALERTAS":
      renderizarVisaoAlertasGiro(palco);
      break;
    default:
      renderizarVisaoLinhaSVG(palco);
  }

  dispararAnimacoesPalcoDashboard(palco);
}

// ============================================================================
// VISÃO 1: EVOLUÇÃO TEMPORAL (GRÁFICO DE LINHA SVG NATIVO + MEIOS DE PAGAMENTO)
// ============================================================================
function renderizarVisaoLinhaSVG(palco) {
  const serie = estadoDash.dados?.serie_temporal || [];
  const pagamentos = estadoDash.dados?.por_pagamento || [];

  const largura = 740;
  const altura = 290;
  const padEsq = 66;
  const padDir = 24;
  const padTopo = 24;
  const padBase = 42;
  const wUtil = largura - padEsq - padDir;
  const hUtil = altura - padTopo - padBase;

  let svgHtml = "";
  if (!serie.length || serie.every((p) => num(p.faturamento) === 0)) {
    svgHtml = `
      <div class="dash-empty-chart">
        <strong>Sem vendas registradas neste período/filtro</strong>
        <p>Assim que novas vendas forem realizadas no PDV, a curva de faturamento e lucro aparecerá aqui.</p>
      </div>
    `;
  } else {
    const maxVal = Math.max(...serie.map((s) => Math.max(num(s.faturamento), num(s.lucro))), 10);
    const teto = Math.ceil(maxVal * 1.12);

    const coordX = (i) =>
      serie.length === 1 ? padEsq + wUtil / 2 : padEsq + (i / (serie.length - 1)) * wUtil;
    const coordY = (val) => padTopo + hUtil - (Math.max(0, val) / teto) * hUtil;

    const pontosFat = serie.map((s, i) => ({
      x: coordX(i),
      y: coordY(num(s.faturamento)),
      ...s,
    }));
    const pontosLucro = serie.map((s, i) => ({
      x: coordX(i),
      y: coordY(num(s.lucro)),
      ...s,
    }));

    const linhaFat = pontosFat.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const linhaLucro = pontosLucro.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

    const primeiroX = pontosFat[0].x.toFixed(1);
    const ultimoX = pontosFat[pontosFat.length - 1].x.toFixed(1);
    const baseLineY = (padTopo + hUtil).toFixed(1);
    const areaFat = `${linhaFat} L${ultimoX},${baseLineY} L${primeiroX},${baseLineY} Z`;

    // Linhas horizontais de grade (4 níveis)
    const grades = [0, 0.25, 0.5, 0.75, 1].map((f) => {
      const val = teto * (1 - f);
      const y = (padTopo + hUtil * f).toFixed(1);
      const label = val >= 1000 ? `R$ ${(val / 1000).toFixed(1)}k` : `R$ ${Math.round(val)}`;
      return `
        <line x1="${padEsq}" y1="${y}" x2="${largura - padDir}" y2="${y}" stroke="#1e293b" stroke-dasharray="4 4" stroke-width="1"/>
        <text x="${padEsq - 8}" y="${Number(y) + 4}" text-anchor="end" fill="#94a3b8" font-size="10.5" font-weight="600">${label}</text>
      `;
    });

    const passoRotulo = Math.max(1, Math.ceil(pontosFat.length / 10));
    const circulosHtml = pontosFat
      .map((p, i) => {
        const mostrarLabel = i % passoRotulo === 0 || i === pontosFat.length - 1;
        const pLuc = pontosLucro[i];
        return `
          <g class="dash-svg-point-group">
            <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4.5" fill="#3b82f6" stroke="#0f172a" stroke-width="2">
              <title>${p.data_label} — Faturamento: ${formatarMoeda(p.faturamento)} | Lucro: ${formatarMoeda(p.lucro)} (${p.qtd} pçs)</title>
            </circle>
            <circle cx="${pLuc.x.toFixed(1)}" cy="${pLuc.y.toFixed(1)}" r="3.5" fill="#22c55e" stroke="#0f172a" stroke-width="1.5">
              <title>${p.data_label} — Lucro Líquido: ${formatarMoeda(p.lucro)}</title>
            </circle>
            ${
              mostrarLabel
                ? `<text x="${p.x.toFixed(1)}" y="${altura - 12}" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="700">${escapeHtml(p.data_label)}</text>`
                : ""
            }
          </g>
        `;
      })
      .join("");

    svgHtml = `
      <div class="dash-svg-wrap">
        <div class="dash-chart-legenda">
          <span><i style="background:#3b82f6"></i> Faturamento Bruto (R$)</span>
          <span><i style="background:#22c55e"></i> Lucro Líquido (R$)</span>
        </div>
        <svg viewBox="0 0 ${largura} ${altura}" class="dash-line-svg" role="img" aria-label="Gráfico de evolução temporal">
          <defs>
            <linearGradient id="dashGradAzul" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.38"/>
              <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          ${grades.join("")}
          <path class="dash-svg-area-anim" d="${areaFat}" fill="url(#dashGradAzul)"/>
          <path class="dash-svg-line-anim" d="${linhaFat}" fill="none" stroke="#3b82f6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          <path class="dash-svg-dashed-anim" d="${linhaLucro}" fill="none" stroke="#22c55e" stroke-width="2.2" stroke-dasharray="5 3" stroke-linecap="round" stroke-linejoin="round"/>
          ${circulosHtml}
        </svg>
      </div>
    `;
  }

  const coresPgto = {
    PIX: "#38bdf8",
    CARTAO: "#3b82f6",
    DINHEIRO: "#22c55e",
    FIADO: "#f59e0b",
  };

  const pgtoHtml = pagamentos
    .map((p) => {
      const cor = coresPgto[p.chave] || "#3b82f6";
      const pctAlvo = Math.min(100, num(p.pct)).toFixed(1);
      return `
        <div class="dash-pgto-item">
          <div class="dash-pgto-topo">
            <span class="dash-pgto-nome">${escapeHtml(p.forma)} <small>(${num(p.qtd)} vds)</small></span>
            <strong class="dash-pgto-val">${formatarMoeda(p.valor)} <small>${pctAlvo}%</small></strong>
          </div>
          <div class="dash-barra-trilha">
            <div class="dash-barra-fill" style="width:0%; background:${cor};" data-target-width="${pctAlvo}%"></div>
          </div>
        </div>
      `;
    })
    .join("");

  palco.innerHTML = `
    <div class="dash-linha-layout">
      <div class="dash-card-interno">
        <h3>Curva de Faturamento vs. Lucro Real</h3>
        ${svgHtml}
      </div>
      <div class="dash-card-interno">
        <h3>Divisão por Meio de Pagamento</h3>
        <div class="dash-pgto-lista">
          ${pgtoHtml}
        </div>
      </div>
    </div>
  `;
}

// ============================================================================
// VISÃO 2: SAÚDE DAS MARGENS (AUDITORIA COMPLETA + REAJUSTE DE PREÇO)
// ============================================================================
function renderizarVisaoSaudeMargens(palco, controles) {
  const resumo = estadoDash.dados?.resumo_margens || {};
  const listaBruta = estadoDash.dados?.auditoria_margens || [];

  if (controles) {
    controles.innerHTML = `
      <div class="dash-margens-toolbar">
        <input
          type="search"
          id="dash-input-busca-margem"
          class="dash-input-mini"
          placeholder="Filtrar modelo ou marca..."
          value="${escapeHtml(estadoDash.buscaMargem)}"
          autocomplete="off"
        >
        <select id="dash-select-ordem-margem" class="dash-select-mini" aria-label="Ordenar auditoria de margens">
          <option value="menor_margem" ${estadoDash.ordemMargem === "menor_margem" ? "selected" : ""}>Menor Margem Primeiro</option>
          <option value="maior_margem" ${estadoDash.ordemMargem === "maior_margem" ? "selected" : ""}>Maior Margem Primeiro</option>
          <option value="menor_lucro" ${estadoDash.ordemMargem === "menor_lucro" ? "selected" : ""}>Menor Lucro (R$) Primeiro</option>
          <option value="maior_estoque" ${estadoDash.ordemMargem === "maior_estoque" ? "selected" : ""}>Maior Estoque Primeiro</option>
        </select>
      </div>
    `;

    dashEl("dash-input-busca-margem")?.addEventListener("input", (e) => {
      estadoDash.buscaMargem = e.target.value;
      atualizarTabelaAuditoriaMargens();
    });
    dashEl("dash-select-ordem-margem")?.addEventListener("change", (e) => {
      estadoDash.ordemMargem = e.target.value;
      atualizarTabelaAuditoriaMargens();
    });
  }

  palco.innerHTML = `
    <div class="dash-margens-kpis">
      <button type="button" class="dash-margem-mini-kpi ${estadoDash.filtroFaixaMargem === "todas" ? "ativo" : ""}" data-faixa-margem="todas">
        <small>Catálogo Auditado</small>
        <strong>${num(resumo.total_modelos)} modelos</strong>
        <span>Markup médio: <b>${num(resumo.markup_medio_pct).toFixed(1)}%</b></span>
      </button>

      <button type="button" class="dash-margem-mini-kpi critica ${estadoDash.filtroFaixaMargem === "critica" ? "ativo" : ""}" data-faixa-margem="critica">
        <small>Margem Crítica (&lt; 25%)</small>
        <strong>${num(resumo.criticas)} modelo(s)</strong>
        <span>Risco de lucro baixo — reajustar</span>
      </button>

      <button type="button" class="dash-margem-mini-kpi moderada ${estadoDash.filtroFaixaMargem === "moderada" ? "ativo" : ""}" data-faixa-margem="moderada">
        <small>Margem Moderada (25%–45%)</small>
        <strong>${num(resumo.moderadas)} modelo(s)</strong>
        <span>Faixa intermediária de operação</span>
      </button>

      <button type="button" class="dash-margem-mini-kpi saudavel ${estadoDash.filtroFaixaMargem === "saudavel" ? "ativo" : ""}" data-faixa-margem="saudavel">
        <small>Margem Saudável (&gt; 45%)</small>
        <strong>${num(resumo.saudaveis)} modelo(s)</strong>
        <span>Excelente rentabilidade por peça</span>
      </button>
    </div>

    <div class="dash-tabela-margens-wrap">
      <table class="dash-tabela-margens">
        <thead>
          <tr>
            <th>Modelo — Marca</th>
            <th>Estoque</th>
            <th>Custo (R$)</th>
            <th>Venda (R$)</th>
            <th>Lucro / Peça</th>
            <th>Margem (%) &amp; Markup</th>
            <th style="text-align:right;">Ação Rápida</th>
          </tr>
        </thead>
        <tbody id="dash-tbody-margens"></tbody>
      </table>
    </div>
  `;

  palco.querySelectorAll("[data-faixa-margem]").forEach((btn) => {
    btn.addEventListener("click", () => {
      estadoDash.filtroFaixaMargem = btn.dataset.faixaMargem;
      palco.querySelectorAll("[data-faixa-margem]").forEach((b) => b.classList.toggle("ativo", b === btn));
      atualizarTabelaAuditoriaMargens();
    });
  });

  atualizarTabelaAuditoriaMargens();
}

function atualizarTabelaAuditoriaMargens() {
  const tbody = dashEl("dash-tbody-margens");
  if (!tbody) return;

  const listaBruta = [...(estadoDash.dados?.auditoria_margens || [])];
  const termo = (estadoDash.buscaMargem || "").trim().toLowerCase();

  const filtrada = listaBruta.filter((item) => {
    if (estadoDash.filtroFaixaMargem !== "todas" && item.faixa !== estadoDash.filtroFaixaMargem) {
      return false;
    }
    if (!termo) return true;
    const alvo = `${item.modelo_nome} ${item.marca} ${item.corte} ${item.tecido}`.toLowerCase();
    return alvo.includes(termo);
  });

  if (estadoDash.ordemMargem === "maior_margem") {
    filtrada.sort((a, b) => b.margem_pct - a.margem_pct);
  } else if (estadoDash.ordemMargem === "menor_lucro") {
    filtrada.sort((a, b) => a.lucro_unitario - b.lucro_unitario);
  } else if (estadoDash.ordemMargem === "maior_estoque") {
    filtrada.sort((a, b) => b.estoque_total - a.estoque_total);
  } else {
    filtrada.sort((a, b) => a.margem_pct - b.margem_pct);
  }

  if (!filtrada.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding: 28px; color: #94a3b8;">
          Nenhum produto encontrado para este filtro de margem.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtrada
    .map((p) => {
      const corFaixa =
        p.faixa === "critica" ? "#ef4444" : p.faixa === "moderada" ? "#f59e0b" : "#22c55e";
      const labelFaixa =
        p.faixa === "critica" ? "Crítica" : p.faixa === "moderada" ? "Moderada" : "Saudável";
      const pctBarra = Math.max(4, Math.min(100, num(p.margem_pct))).toFixed(1);

      const rotuloLimpo = String(p.grupo_rotulo || p.grupo_nome || "Peça").replace(/^[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]+\s*/gu, "");
      return `
        <tr>
          <td>
            <div class="dash-td-produto">
              <span class="dash-grupo-chip">${escapeHtml(rotuloLimpo)}</span>
              <div>
                <strong>${escapeHtml(p.modelo_nome)}</strong>
                <small>${escapeHtml(p.marca)}</small>
              </div>
            </div>
          </td>
          <td><strong>${num(p.estoque_total)} un.</strong></td>
          <td class="txt-muted">${formatarMoeda(p.preco_custo)}</td>
          <td><strong>${formatarMoeda(p.preco_venda)}</strong></td>
          <td style="color:${corFaixa}; font-weight:800;">${formatarMoeda(p.lucro_unitario)}</td>
          <td>
            <div class="dash-margem-cell">
              <div class="dash-margem-cell-topo">
                <strong style="color:${corFaixa};">${num(p.margem_pct).toFixed(1)}%</strong>
                <span class="dash-faixa-pill ${p.faixa}">${labelFaixa} • Markup ${num(p.markup_pct).toFixed(0)}%</span>
              </div>
              <div class="dash-barra-trilha">
                <div class="dash-barra-fill" style="width:0%; background:${corFaixa};" data-target-width="${pctBarra}%"></div>
              </div>
            </div>
          </td>
          <td style="text-align:right;">
            <button
              type="button"
              class="btn-secundario-sistema btn-sm"
              onclick="reajustarPrecoProdutoDash(${Number(p.id)})"
            >
              Reajustar Preço
            </button>
          </td>
        </tr>
      `;
    })
    .join("");

  dispararAnimacoesPalcoDashboard(tbody);
}

async function reajustarPrecoProdutoDash(produtoId) {
  if (!estado.produtos || !estado.produtos.length) {
    if (typeof carregarEstoque === "function") {
      await carregarEstoque(true);
    }
  }
  if (typeof abrirModalEditar === "function") {
    abrirModalEditar(Number(produtoId));
  } else {
    exibirToast("Abra a aba Estoque para editar este produto.", "aviso");
  }
}

// ============================================================================
// VISÃO 3: RAIO-X DO ESTOQUE (GRÁFICO DONUT SVG + CARDS DOS 5 GRANDES GRUPOS)
// ============================================================================
function renderizarVisaoRoscaEstoque(palco) {
  const grupos = estadoDash.dados?.estoque_por_grupo || [];
  const totalPecas = grupos.reduce((acc, g) => acc + num(g.pecas), 0);
  const totalCusto = grupos.reduce((acc, g) => acc + num(g.custo_total), 0);
  const totalVenda = grupos.reduce((acc, g) => acc + num(g.venda_potencial), 0);

  const raio = 78;
  const circunferencia = 2 * Math.PI * raio;
  let offsetAcumulado = 0;

  const paletaSobria = ["#3b82f6", "#64748b", "#0ea5e9", "#475569", "#94a3b8"];

  const fatiasSvg =
    totalPecas > 0
      ? grupos
          .map((g, idx) => {
            const corSobria = paletaSobria[idx % paletaSobria.length];
            const fracao = num(g.pecas) / totalPecas;
            const comp = fracao * circunferencia;
            const dashArray = `${comp.toFixed(2)} ${(circunferencia - comp).toFixed(2)}`;
            const dashInitial = `0 ${circunferencia.toFixed(2)}`;
            const dashOffset = (-offsetAcumulado).toFixed(2);
            offsetAcumulado += comp;
            return `
              <circle
                class="dash-donut-segment"
                cx="110"
                cy="110"
                r="${raio}"
                fill="transparent"
                stroke="${corSobria}"
                stroke-width="26"
                stroke-dasharray="${dashInitial}"
                data-target-dasharray="${dashArray}"
                stroke-dashoffset="${dashOffset}"
                transform="rotate(-90 110 110)"
                style="opacity: 0;"
              >
                <title>${g.nome}: ${g.pecas} peças (${g.pct_pecas}%)</title>
              </circle>
            `;
          })
          .join("")
      : `<circle cx="110" cy="110" r="${raio}" fill="transparent" stroke="#1e293b" stroke-width="26"/>`;

  const cardsGruposHtml = grupos
    .map((g, idx) => {
      const corSobria = paletaSobria[idx % paletaSobria.length];
      const lucroPot = Math.max(0, num(g.venda_potencial) - num(g.custo_total));
      const rotuloLimpo = String(g.rotulo || g.nome || "").replace(/^[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]+\s*/gu, "");
      return `
        <div class="dash-grupo-card" style="border-left: 3px solid ${corSobria};">
          <div class="dash-grupo-card-topo">
            <div>
              <strong style="color:#f8fafc;">${escapeHtml(rotuloLimpo)}</strong>
              <small>${escapeHtml(g.nome)} (${num(g.modelos)} modelos)</small>
            </div>
            <span class="dash-grupo-pecas-badge">${num(g.pecas)} pçs (${num(g.pct_pecas).toFixed(1)}%)</span>
          </div>
          <div class="dash-grupo-metricas">
            <div><small>Capital Investido</small><strong>${formatarMoeda(g.custo_total)}</strong></div>
            <div><small>Venda Potencial</small><strong>${formatarMoeda(g.venda_potencial)}</strong></div>
            <div><small>Lucro Esperado</small><strong class="txt-verde">${formatarMoeda(lucroPot)}</strong></div>
          </div>
        </div>
      `;
    })
    .join("");

  palco.innerHTML = `
    <div class="dash-rosca-layout">
      <div class="dash-card-interno dash-rosca-box">
        <svg viewBox="0 0 220 220" class="dash-donut-svg" role="img" aria-label="Gráfico de rosca do estoque">
          ${fatiasSvg}
          <text x="110" y="102" text-anchor="middle" fill="#f8fafc" font-size="22" font-weight="900">${totalPecas} pçs</text>
          <text x="110" y="124" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="700">${formatarMoeda(totalCusto)}</text>
        </svg>
        <div class="dash-rosca-resumo">
          <div><small>Custo Total em Estoque</small><strong>${formatarMoeda(totalCusto)}</strong></div>
          <div><small>Potencial Total de Venda</small><strong class="txt-verde">${formatarMoeda(totalVenda)}</strong></div>
        </div>
      </div>

      <div class="dash-grupos-lista">
        ${cardsGruposHtml}
      </div>
    </div>
  `;
}

// ============================================================================
// VISÕES 4 e 5: RANKING DE BARRAS HORIZONTAIS (POR MARCA E POR TIPO DE PEÇA)
// ============================================================================
function renderizarVisaoBarrasRanking(palco, lista, corPadrao, rotuloEixo) {
  if (!lista || !lista.length) {
    palco.innerHTML = `
      <div class="dash-empty-chart">
        <strong>Nenhuma venda registrada por ${escapeHtml(rotuloEixo)} neste período</strong>
        <p>Selecione um período mais amplo (ex: "30 Dias" ou "Tudo") para visualizar o ranking acumulado.</p>
      </div>
    `;
    return;
  }

  const maxFat = Math.max(...lista.map((it) => num(it.faturamento)), 1);

  const linhasHtml = lista
    .map((it, idx) => {
      const corBarra = corPadrao || "#3b82f6";
      const pct = Math.max(4, (num(it.faturamento) / maxFat) * 100).toFixed(1);
      return `
        <div class="dash-rank-row">
          <div class="dash-rank-topo">
            <span class="dash-rank-pos">#${idx + 1}</span>
            <strong class="dash-rank-nome">${escapeHtml(it.nome)}</strong>
            <span class="dash-rank-qtd">${num(it.qtd)} pç(s)</span>
            <strong class="dash-rank-fat">${formatarMoeda(it.faturamento)}</strong>
            <span class="dash-rank-lucro">Lucro: ${formatarMoeda(it.lucro)} (${num(it.margem_pct).toFixed(0)}%)</span>
          </div>
          <div class="dash-barra-trilha">
            <div class="dash-barra-fill" style="width:0%; background:${corBarra};" data-target-width="${pct}%"></div>
          </div>
        </div>
      `;
    })
    .join("");

  palco.innerHTML = `<div class="dash-rank-lista">${linhasHtml}</div>`;
}

// ============================================================================
// VISÃO 6: POR CORTE & TECIDO (COMPARATIVO LADO A LADO)
// ============================================================================
function renderizarVisaoCorteTecido(palco) {
  const cortes = estadoDash.dados?.ranking_cortes || [];
  const tecidos = estadoDash.dados?.ranking_tecidos || [];

  const montarColuna = (titulo, lista, cor) => {
    if (!lista.length) {
      return `
        <div class="dash-card-interno">
          <h3>${titulo}</h3>
          <div class="estado-vazio"><p>Sem vendas registradas no período.</p></div>
        </div>
      `;
    }
    const maxF = Math.max(...lista.map((x) => num(x.faturamento)), 1);
    const itens = lista
      .map((it, idx) => {
        const pct = Math.max(5, (num(it.faturamento) / maxF) * 100).toFixed(1);
        return `
          <div class="dash-rank-row compacto">
            <div class="dash-rank-topo">
              <span class="dash-rank-pos">#${idx + 1}</span>
              <strong class="dash-rank-nome">${escapeHtml(it.nome)}</strong>
              <span class="dash-rank-qtd">${num(it.qtd)} pçs</span>
              <strong class="dash-rank-fat">${formatarMoeda(it.faturamento)}</strong>
            </div>
            <div class="dash-barra-trilha">
              <div class="dash-barra-fill" style="width:0%; background:${cor};" data-target-width="${pct}%"></div>
            </div>
          </div>
        `;
      })
      .join("");
    return `
      <div class="dash-card-interno">
        <h3>${titulo}</h3>
        <div class="dash-rank-lista">${itens}</div>
      </div>
    `;
  };

  palco.innerHTML = `
    <div class="dash-duas-colunas">
      ${montarColuna("Ranking por Corte / Modelagem", cortes, "#3b82f6")}
      ${montarColuna("Ranking por Tecido / Material", tecidos, "#64748b")}
    </div>
  `;
}

// ============================================================================
// VISÃO 7: ALERTAS DE REPOSIÇÃO URGENTE & CAPITAL PARADO (SUGESTÃO DE PROMO)
// ============================================================================
function renderizarVisaoAlertasGiro(palco) {
  const reposicao = estadoDash.dados?.alertas?.reposicao_estoque_baixo || [];
  const encalhados = estadoDash.dados?.alertas?.encalhados_sem_giro || [];

  const htmlReposicao = reposicao.length
    ? reposicao
        .map(
          (p) => `
          <div class="dash-alerta-card urgente">
            <div class="dash-alerta-info">
              <div class="dash-alerta-topo">
                <strong>${escapeHtml(p.modelo_nome)} — ${escapeHtml(p.marca)}</strong>
                <span class="dash-alerta-tag vermelho">Restam ${num(p.estoque_total)} un.</span>
              </div>
              <small>Grades: ${escapeHtml(p.tamanhos_resumo)} • Vendidos no período: <b>${num(p.qtd_vendida_periodo)} pç(s)</b></small>
            </div>
            <button type="button" class="btn-secundario-sistema btn-sm" onclick="reajustarPrecoProdutoDash(${Number(p.id)})">
              Repor
            </button>
          </div>
        `
        )
        .join("")
    : `<div class="estado-vazio"><p>Tudo abastecido. Nenhuma peça com estoque crítico (≤ 2 un.).</p></div>`;

  const htmlEncalhados = encalhados.length
    ? encalhados
        .map(
          (p) => `
          <div class="dash-alerta-card parado">
            <div class="dash-alerta-info">
              <div class="dash-alerta-topo">
                <strong>${escapeHtml(p.modelo_nome)} — ${escapeHtml(p.marca)}</strong>
                <span class="dash-alerta-tag ambar">Parado: ${formatarMoeda(p.capital_parado)}</span>
              </div>
              <small>${num(p.estoque_total)} un. paradas (0 vendas no período) • Atual: ${formatarMoeda(p.preco_venda)} → <b>Sugestão -15%: ${formatarMoeda(p.sugestao_promo_15)}</b></small>
            </div>
            <button type="button" class="btn-secundario-sistema btn-sm" onclick="reajustarPrecoProdutoDash(${Number(p.id)})">
              Promover
            </button>
          </div>
        `
        )
        .join("")
    : `<div class="estado-vazio"><p>Excelente giro. Todos os modelos em estoque tiveram saída no período.</p></div>`;

  palco.innerHTML = `
    <div class="dash-duas-colunas">
      <div class="dash-card-interno">
        <h3>Reposição Urgente (Estoque ≤ 2 un.)</h3>
        <div class="dash-alertas-lista">${htmlReposicao}</div>
      </div>
      <div class="dash-card-interno">
        <h3>Capital Parado / Sugestão de Promoção (0 Vendas)</h3>
        <div class="dash-alertas-lista">${htmlEncalhados}</div>
      </div>
    </div>
  `;
}

// ============================================================================
// 5. EVENTOS E REGISTRO NO CORE
// ============================================================================
function registrarEventosDashboard() {
  iniciarRelogioDashboard();

  dashEl("dash-btn-atualizar")?.addEventListener("click", () => {
    carregarDashboard(false);
    exibirToast("Indicadores do Dashboard atualizados!", "info", 2000);
  });

  dashEl("dash-pills-periodo")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-dash-periodo]");
    if (!btn) return;
    estadoDash.periodo = btn.dataset.dashPeriodo;
    dashEl("dash-pills-periodo")
      .querySelectorAll(".dash-pill")
      .forEach((b) => b.classList.toggle("ativo", b === btn));
    carregarDashboard(false);
  });

  dashEl("dash-pills-grupo")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-dash-grupo]");
    if (!btn) return;
    estadoDash.grupo = btn.dataset.dashGrupo;
    dashEl("dash-pills-grupo")
      .querySelectorAll(".pill-grupo")
      .forEach((b) => b.classList.toggle("ativo", b === btn));
    carregarDashboard(false);
  });

  document.querySelectorAll(".dash-visao-btn[data-dash-visao]").forEach((btn) => {
    btn.addEventListener("click", () => {
      selecionarVisaoDashboard(btn.dataset.dashVisao, true);
    });
  });

  // Quando o modal de edição de produto salvar alterações, atualiza o Dashboard se estiver ativo
  const formEditar = document.getElementById("form-editar-produto");
  formEditar?.addEventListener("submit", () => {
    setTimeout(() => {
      if (estado.viewAtual === "dashboard") {
        carregarDashboard(true);
      }
    }, 450);
  });
}

window.carregarDashboard = carregarDashboard;
window.selecionarVisaoDashboard = selecionarVisaoDashboard;
window.reajustarPrecoProdutoDash = reajustarPrecoProdutoDash;

KanembergApp.eventos.push(registrarEventosDashboard);
KanembergApp.inicializadores.push(() => carregarDashboard(true));
