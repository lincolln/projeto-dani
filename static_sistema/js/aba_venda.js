/**
 * aba_venda.js — Aba 3: Nova Venda / PDV de Balcão Widescreen + Estorno de Vendas Recentes
 * Padrão Visual: Slate Neutro Corporativo (Zero Emojis) + Física Silk UI
 *
 * Funcionalidades:
 * - Leitor instantâneo de código de barras / QR Code (KNB...) em memória + fallback /api/qrcode/{codigo}
 * - Catálogo rápido com filtro por Grande Grupo, busca textual multi-termo e clique direto no tamanho
 * - Integração com a Vitrine de Estoque via acionarEnviarParaVenda(produtoId, tamanhoEspecifico)
 * - Cupom/Carrinho interativo com física Silk UI (.item-novo), trava de estoque máximo e descontos (R$ / %)
 * - Meios de pagamento (PIX, CARTAO, DINHEIRO com calculadora de troco + cédulas rápidas, FIADO com limite + cliente rápido)
 * - Checkout atômico em POST /api/vendas + Recibo pós-venda + atalhos F2 (Busca/Bipe) e F12 (Finalizar)
 * - Modal Histórico & Estorno de Vendas Recentes (GET /api/vendas/recentes + POST /api/vendas/{id}/estornar)
 */

/* global KanembergApp, estado, dom, $, ORDEM_TAMANHOS,
          escapeHtml, num, formatarMoeda, valorValido, normalizarTamanhoFront,
          resolverCorHex, obterGrupoProduto, extrairCoresProduto, agruparTamanhosProduto,
          requisitarApi, exibirToast, alternarView, abrirModal, fecharModal, atualizarBadgeFilaVenda */

let eventosVendaRegistrados = false;
let audioCtxPDV = null;

const ROTULOS_FORMA_PGTO = {
  PIX: "PIX",
  CARTAO: "Cartão",
  DINHEIRO: "Dinheiro",
  FIADO: "Fiado / Crediário",
};

// ============================================================================
// 1. FEEDBACK SONORO SUTIL DE BALCÃO (WEBAUDIO — SEM ARQUIVOS EXTERNOS)
// ============================================================================
function tocarSomPDV(tipo = "bipe") {
  try {
    const AudioContextRef = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextRef) return;
    if (!audioCtxPDV) {
      audioCtxPDV = new AudioContextRef();
    }
    if (audioCtxPDV.state === "suspended") {
      audioCtxPDV.resume().catch(() => {});
    }

    const agora = audioCtxPDV.currentTime;
    const osc = audioCtxPDV.createOscillator();
    const gain = audioCtxPDV.createGain();
    osc.connect(gain);
    gain.connect(audioCtxPDV.destination);

    if (tipo === "erro") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(210, agora);
      osc.frequency.linearRampToValueAtTime(150, agora + 0.16);
      gain.gain.setValueAtTime(0.05, agora);
      gain.gain.exponentialRampToValueAtTime(0.001, agora + 0.18);
      osc.start(agora);
      osc.stop(agora + 0.18);
    } else if (tipo === "venda") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, agora);
      osc.frequency.setValueAtTime(880, agora + 0.08);
      gain.gain.setValueAtTime(0.06, agora);
      gain.gain.exponentialRampToValueAtTime(0.001, agora + 0.24);
      osc.start(agora);
      osc.stop(agora + 0.24);
    } else {
      osc.type = "sine";
      osc.frequency.setValueAtTime(780, agora);
      gain.gain.setValueAtTime(0.04, agora);
      gain.gain.exponentialRampToValueAtTime(0.001, agora + 0.07);
      osc.start(agora);
      osc.stop(agora + 0.07);
    }
  } catch (_e) {
    // Ambientes sem suporte a WebAudio ignoram silenciosamente
  }
}

function flashInputBipePDV(sucesso = true) {
  const inp = dom.inputBipePdv;
  if (!inp) return;
  const classe = sucesso ? "flash-sucesso" : "flash-erro";
  inp.classList.remove("flash-sucesso", "flash-erro");
  void inp.offsetWidth;
  inp.classList.add(classe);
  setTimeout(() => inp.classList.remove(classe), 420);
}

// ============================================================================
// 2. KPIs DO DIA NO TOPO DO PDV (GET /api/vendas/hoje)
// ============================================================================
async function carregarKpisVendasHoje() {
  try {
    const dados = await requisitarApi("/api/vendas/hoje");
    const faturamento = num(dados.faturamento_hoje ?? dados.total_vendido, 0);
    const pecas = parseInt(dados.pecas_hoje ?? dados.pecas_vendidas ?? 0, 10) || 0;

    if (dom.pdvKpiVendasHoje) {
      dom.pdvKpiVendasHoje.textContent = formatarMoeda(faturamento);
    }
    if (dom.pdvKpiPecasHoje) {
      dom.pdvKpiPecasHoje.textContent = String(pecas);
    }
  } catch (_erro) {
    // Mantém último valor renderizado em caso de oscilação momentânea
  }
}

// ============================================================================
// 3. LOCALIZAÇÃO DE VARIAÇÕES, SINCRONIZAÇÃO DE ESTOQUE E CARRINHO PDV
// ============================================================================
function obterChaveUnicaVariacao(prod, variacao) {
  if (variacao?.id) return `vid:${variacao.id}`;
  if (variacao?.codigo_barras) return `cod:${String(variacao.codigo_barras).toUpperCase()}`;
  const pid = prod?.id || prod?.produto_id || 0;
  const tam = normalizarTamanhoFront(variacao?.tamanho || "U");
  return `pt:${pid}:${tam}`;
}

function encontrarVariacaoEmMemoria({ variacaoId = null, codigoBarras = "", produtoId = null, tamanho = "" }) {
  const codAlvo = String(codigoBarras || "").trim().toUpperCase();
  const vidAlvo = variacaoId ? Number(variacaoId) : 0;
  const pidAlvo = produtoId ? Number(produtoId) : 0;
  const tamAlvo = tamanho ? normalizarTamanhoFront(tamanho) : "";

  for (const prod of estado.produtos || []) {
    const pid = Number(prod.id || prod.produto_id || 0);
    const vars = Array.isArray(prod.variacoes) ? prod.variacoes : [];

    for (const v of vars) {
      if (vidAlvo && Number(v.id) === vidAlvo) {
        return { prod, variacao: v };
      }
      if (codAlvo && String(v.codigo_barras || "").trim().toUpperCase() === codAlvo) {
        return { prod, variacao: v };
      }
      if (pidAlvo && pid === pidAlvo && tamAlvo && normalizarTamanhoFront(v.tamanho) === tamAlvo) {
        if (num(v.estoque, 0) > 0) {
          return { prod, variacao: v };
        }
      }
    }

    if (pidAlvo && pid === pidAlvo && tamAlvo && vars.length > 0) {
      const fallbackVar = vars.find((v) => normalizarTamanhoFront(v.tamanho) === tamAlvo);
      if (fallbackVar) return { prod, variacao: fallbackVar };
    }
  }

  return null;
}

function sincronizarLimitesCarrinhoComEstoque() {
  if (!Array.isArray(estado.pdv.carrinho) || !estado.pdv.carrinho.length) return;

  const novoCarrinho = [];
  for (const item of estado.pdv.carrinho) {
    const achado = encontrarVariacaoEmMemoria({
      variacaoId: item.variacao_id,
      codigoBarras: item.codigo_barras,
      produtoId: item.produto_id,
      tamanho: item.tamanho,
    });

    if (!achado || !achado.variacao) {
      novoCarrinho.push(item);
      continue;
    }

    const estAtual = Math.max(0, parseInt(achado.variacao.estoque ?? 0, 10) || 0);
    if (estAtual <= 0) {
      continue;
    }

    item.estoque_max = estAtual;
    item.preco_venda = num(achado.variacao.preco_venda || achado.prod.preco_venda, item.preco_venda);
    if (item.quantidade > estAtual) {
      item.quantidade = estAtual;
    }
    novoCarrinho.push(item);
  }

  estado.pdv.carrinho = novoCarrinho;
  atualizarBadgeFilaVenda();
  if (estado.viewAtual === "venda") {
    renderizarCarrinhoPDV();
  }
}

function adicionarVariacaoAoCarrinhoPDV(prod, variacao, silencioso = false) {
  if (!prod || !variacao) return false;

  const estoqueDisp = Math.max(0, parseInt(variacao.estoque ?? 0, 10) || 0);
  const tamFormatado = normalizarTamanhoFront(variacao.tamanho || "U");

  if (estoqueDisp <= 0) {
    tocarSomPDV("erro");
    exibirToast(` "${prod.modelo_nome}" (${tamFormatado}) está sem estoque disponível.`, "aviso");
    return false;
  }

  const chave = obterChaveUnicaVariacao(prod, variacao);
  const existente = estado.pdv.carrinho.find((i) => i.chave === chave);

  if (existente) {
    existente.estoque_max = estoqueDisp;
    if (existente.quantidade >= estoqueDisp) {
      tocarSomPDV("erro");
      exibirToast(
        `Limite em estoque atingido para "${prod.modelo_nome}" Tam. ${tamFormatado} (${estoqueDisp} disp.).`,
        "aviso"
      );
      return false;
    }
    existente.quantidade += 1;
  } else {
    const coresExtraidas = extrairCoresProduto(prod);
    const corVar = String(variacao.cor || prod.cor || coresExtraidas[0]?.nome || "Padrão").trim();
    const hexVar = resolverCorHex(corVar, variacao.cor_hex || prod.cor_hex || coresExtraidas[0]?.cor_hex);

    estado.pdv.carrinho.push({
      chave,
      produto_id: prod.id || prod.produto_id || null,
      variacao_id: variacao.id || null,
      codigo_barras: variacao.codigo_barras || "",
      modelo_nome: prod.modelo_nome || "Produto",
      marca: valorValido(prod.marca) ? prod.marca : "",
      tamanho: tamFormatado,
      cor: corVar,
      cor_hex: hexVar,
      preco_venda: num(variacao.preco_venda || prod.preco_venda, 0),
      quantidade: 1,
      estoque_max: estoqueDisp,
    });
  }

  // Ativa animação Silk UI de entrada/destaque para o item adicionado
  estado.pdv.ultimoItemKeyAnimado = chave;
  tocarSomPDV("bipe");
  atualizarBadgeFilaVenda();
  renderizarCarrinhoPDV();
  renderizarCatalogoPDV();

  if (!silencioso) {
    // Mantém fluxo ágil sem poluir com toasts repetitivos a cada clique no balcão
  }
  return true;
}

/**
 * Integração direta com os cards da Vitrine de Estoque ("Enviar para Venda" ou clique em pílula de tamanho).
 */
function acionarEnviarParaVenda(produtoId, tamanhoEspecifico = null) {
  const prod = (estado.produtos || []).find(
    (p) => Number(p.id || p.produto_id) === Number(produtoId)
  );
  if (!prod) {
    exibirToast("Produto não localizado na memória do estoque.", "erro");
    return;
  }

  const tamanhosAgrupados = agruparTamanhosProduto(prod).filter((t) => num(t.estoque, 0) > 0);
  if (!tamanhosAgrupados.length) {
    exibirToast(`"${prod.modelo_nome}" está esgotado no estoque.`, "aviso");
    return;
  }

  let infoTam = null;
  if (tamanhoEspecifico) {
    const tamNorm = normalizarTamanhoFront(tamanhoEspecifico);
    infoTam = tamanhosAgrupados.find((t) => normalizarTamanhoFront(t.tamanho) === tamNorm) || null;
    if (!infoTam) {
      exibirToast(`Tamanho ${tamNorm} sem estoque disponível.`, "aviso");
      return;
    }
  } else if (tamanhosAgrupados.length === 1) {
    infoTam = tamanhosAgrupados[0];
  } else {
    // Múltiplos tamanhos com estoque: abre modal seletor rápido (#modal-vender)
    const pid = prod.id || prod.produto_id;
    if (dom.venderNomeProduto) {
      const marcaTxt = valorValido(prod.marca) ? ` — ${prod.marca}` : "";
      dom.venderNomeProduto.textContent = `${prod.modelo_nome}${marcaTxt}`;
    }
    if (dom.venderOpcoesTamanhos) {
      dom.venderOpcoesTamanhos.innerHTML = tamanhosAgrupados
        .map(
          (t) => `
            <button
              type="button"
              class="btn-opcao-vender-tam"
              data-vender-pid="${pid}"
              data-vender-tam="${escapeHtml(t.tamanho)}"
            >
              <strong>${escapeHtml(t.tamanho)}</strong>
              <span>${t.estoque} disp. · ${formatarMoeda(t.preco_venda || prod.preco_venda)}</span>
            </button>
          `
        )
        .join("");
    }
    abrirModal("modal-vender");
    return;
  }

  fecharModal("modal-vender");

  const achado = encontrarVariacaoEmMemoria({
    variacaoId: infoTam.variacao_id,
    codigoBarras: infoTam.codigo_barras,
    produtoId: prod.id || prod.produto_id,
    tamanho: infoTam.tamanho,
  });

  const variacaoAlvo = achado?.variacao || {
    id: infoTam.variacao_id || null,
    codigo_barras: infoTam.codigo_barras || "",
    tamanho: infoTam.tamanho,
    estoque: infoTam.estoque,
    preco_venda: infoTam.preco_venda || prod.preco_venda,
  };

  const adicionou = adicionarVariacaoAoCarrinhoPDV(prod, variacaoAlvo, true);
  if (adicionou) {
    const titulo = [prod.modelo_nome, prod.marca].filter(valorValido).join(" — ");
    exibirToast(`${titulo} (Tam. ${infoTam.tamanho}) adicionado ao PDV.`, "sucesso", 2400);
    alternarView("venda");
  }
}

// ============================================================================
// 4. LEITOR DE CÓDIGO DE BARRAS / QR (KNB...) E CATÁLOGO RÁPIDO DO PDV
// ============================================================================
function filtrarProdutosCatalogoPDV() {
  const grupoFiltro = estado.pdv.filtroGrupo || "todos";
  const termo = String(estado.pdv.termoBusca || "").trim().toLowerCase();
  const tokens = termo ? termo.split(/\s+/) : [];

  return (estado.produtos || []).filter((p) => {
    const varsDisp = (Array.isArray(p.variacoes) ? p.variacoes : []).filter(
      (v) => num(v.estoque, 0) > 0
    );
    if (!varsDisp.length) return false;

    const infoGrupo = obterGrupoProduto(p.modelo_nome, p.tipo_peca);
    if (grupoFiltro !== "todos" && infoGrupo.chave !== grupoFiltro) {
      return false;
    }

    if (!tokens.length) return true;

    const cores = extrairCoresProduto(p)
      .map((c) => c.nome)
      .join(" ");
    const codigosETamanhos = varsDisp
      .map((v) => `${v.tamanho || ""} ${v.codigo_barras || ""} ${v.cor || ""}`)
      .join(" ");

    const ficha = [
      p.modelo_nome || "",
      p.tipo_peca || "",
      p.marca || "",
      p.corte || "",
      p.tecido || "",
      infoGrupo.nome,
      cores,
      codigosETamanhos,
    ]
      .join(" ")
      .toLowerCase();

    return tokens.every((tk) => ficha.includes(tk));
  });
}

async function processarBipeOuBuscaEnterPDV() {
  const texto = String(dom.inputBipePdv?.value || "").trim();
  if (!texto) return;

  const codigoUpper = texto.toUpperCase();

  // 1. Código de barras KNB... exato em memória
  const achadoMemoria = encontrarVariacaoEmMemoria({ codigoBarras: codigoUpper });
  if (achadoMemoria && achadoMemoria.variacao) {
    const ok = adicionarVariacaoAoCarrinhoPDV(achadoMemoria.prod, achadoMemoria.variacao);
    flashInputBipePDV(ok);
    if (ok && dom.inputBipePdv) {
      dom.inputBipePdv.value = "";
      estado.pdv.termoBusca = "";
      dom.btnLimparBuscaPdv?.classList.add("hidden");
      renderizarCatalogoPDV();
      dom.inputBipePdv.focus();
    }
    return;
  }

  // 2. Fallback na API /api/qrcode/{codigo} caso o código tenha acabado de ser gerado no celular
  if (codigoUpper.startsWith("KNB")) {
    try {
      const resQr = await requisitarApi(`/api/qrcode/${encodeURIComponent(codigoUpper)}`);
      const p = resQr?.produto || resQr?.variacao || (resQr?.variacao_id ? resQr : null);
      if (p) {
        if (typeof window.carregarEstoque === "function") {
          await window.carregarEstoque(true);
        }
        const recarregado = encontrarVariacaoEmMemoria({
          variacaoId: p.variacao_id || p.id,
          codigoBarras: p.codigo_barras || codigoUpper,
        });
        const ok = recarregado
          ? adicionarVariacaoAoCarrinhoPDV(recarregado.prod, recarregado.variacao)
          : adicionarVariacaoAoCarrinhoPDV(
              {
                id: p.produto_id,
                modelo_nome: p.modelo_nome,
                marca: p.marca,
                cor: p.cor,
                cor_hex: p.cor_hex,
                preco_venda: p.preco_venda,
              },
              {
                id: p.variacao_id || p.id,
                codigo_barras: p.codigo_barras || codigoUpper,
                tamanho: p.tamanho,
                cor: p.cor,
                cor_hex: p.cor_hex,
                estoque: p.estoque,
                preco_venda: p.preco_venda,
              }
            );
        flashInputBipePDV(ok);
        if (ok && dom.inputBipePdv) {
          dom.inputBipePdv.value = "";
          estado.pdv.termoBusca = "";
          dom.btnLimparBuscaPdv?.classList.add("hidden");
          renderizarCatalogoPDV();
          dom.inputBipePdv.focus();
        }
        return;
      }
    } catch (_erroQr) {
      tocarSomPDV("erro");
      flashInputBipePDV(false);
      exibirToast(`Código "${codigoUpper}" não encontrado no estoque.`, "erro");
      dom.inputBipePdv?.select();
      return;
    }
  }

  // 3. Se a busca textual isolou exatamente 1 modelo com 1 único tamanho disponível, adiciona direto
  const filtrados = filtrarProdutosCatalogoPDV();
  if (filtrados.length === 1) {
    const unicoProd = filtrados[0];
    const varsDisp = (Array.isArray(unicoProd.variacoes) ? unicoProd.variacoes : []).filter(
      (v) => num(v.estoque, 0) > 0
    );
    if (varsDisp.length === 1) {
      const ok = adicionarVariacaoAoCarrinhoPDV(unicoProd, varsDisp[0]);
      flashInputBipePDV(ok);
      if (ok && dom.inputBipePdv) {
        dom.inputBipePdv.value = "";
        estado.pdv.termoBusca = "";
        dom.btnLimparBuscaPdv?.classList.add("hidden");
        renderizarCatalogoPDV();
        dom.inputBipePdv.focus();
      }
      return;
    }
  }

  exibirToast(
    filtrados.length > 0
      ? `Selecione o tamanho desejado nos ${filtrados.length} modelo(s) listados abaixo.`
      : `Nenhuma peça com estoque para "${texto}".`,
    filtrados.length > 0 ? "info" : "aviso"
  );
}

function renderizarCatalogoPDV() {
  if (!dom.gridCatalogoPdv) return;

  const produtosDisp = filtrarProdutosCatalogoPDV();
  if (dom.pdvContadorCatalogo) {
    dom.pdvContadorCatalogo.textContent = `${produtosDisp.length} ${
      produtosDisp.length === 1 ? "modelo com estoque" : "modelos com estoque"
    }`;
  }

  if (!produtosDisp.length) {
    dom.gridCatalogoPdv.innerHTML = `
      <div class="estado-vazio" style="grid-column: 1 / -1;">
        <p>Nenhuma peça com estoque disponível para este filtro ou busca.</p>
      </div>
    `;
    return;
  }

  const mapaNoCarrinho = new Map();
  for (const item of estado.pdv.carrinho) {
    mapaNoCarrinho.set(item.chave, num(item.quantidade, 0));
  }

  dom.gridCatalogoPdv.innerHTML = produtosDisp
    .map((p) => {
      const pid = p.id || p.produto_id;
      const infoGrupo = obterGrupoProduto(p.modelo_nome, p.tipo_peca);
      const cores = extrairCoresProduto(p);
      const subPartes = [p.marca, p.corte, p.tecido].filter(valorValido);

      const bolinhasCoresHtml = cores
        .slice(0, 4)
        .map(
          (c) =>
            `<span class="bolinha-cor" style="background-color:${escapeHtml(c.cor_hex)};width:10px;height:10px;" title="${escapeHtml(c.nome)}"></span>`
        )
        .join("");

      const vars = (Array.isArray(p.variacoes) ? p.variacoes : [])
        .filter((v) => num(v.estoque, 0) > 0)
        .sort((a, b) => {
          const ta = normalizarTamanhoFront(a.tamanho || "U");
          const tb = normalizarTamanhoFront(b.tamanho || "U");
          const oa = ORDEM_TAMANHOS[ta] ?? ORDEM_TAMANHOS[ta.toUpperCase()] ?? 99;
          const ob = ORDEM_TAMANHOS[tb] ?? ORDEM_TAMANHOS[tb.toUpperCase()] ?? 99;
          if (oa !== ob) return oa - ob;
          return ta.localeCompare(tb, "pt-BR");
        });

      const botoesTamanhoHtml = vars
        .map((v) => {
          const tam = normalizarTamanhoFront(v.tamanho || "U");
          const est = num(v.estoque, 0);
          const chave = obterChaveUnicaVariacao(p, v);
          const qtdNoCarrinho = mapaNoCarrinho.get(chave) || 0;
          const esgotadoNoCarrinho = qtdNoCarrinho >= est;
          const classeNoCarrinho = qtdNoCarrinho > 0 ? "no-carrinho" : "";
          const labelQtd = qtdNoCarrinho > 0 ? `${qtdNoCarrinho}/${est}` : `${est}`;
          const titleBtn = v.codigo_barras
            ? `Adicionar Tam. ${tam} (${v.codigo_barras}) — Disponível: ${est}`
            : `Adicionar Tam. ${tam} — Disponível: ${est}`;

          return `
            <button
              type="button"
              class="btn-tam-pdv ${classeNoCarrinho}"
              data-pdv-add-pid="${pid}"
              data-pdv-add-vid="${v.id || ""}"
              data-pdv-add-cod="${escapeHtml(v.codigo_barras || "")}"
              data-pdv-add-tam="${escapeHtml(tam)}"
              title="${escapeHtml(titleBtn)}"
              ${esgotadoNoCarrinho ? "disabled" : ""}
            >
              <strong>${escapeHtml(tam)}</strong>
              <span class="qtd-disp-mini">(${labelQtd})</span>
            </button>
          `;
        })
        .join("");

      return `
        <article class="card-pdv-item" style="--cor-borda-pdv: ${infoGrupo.cor};">
          <div class="card-pdv-top">
            <div class="card-pdv-ident">
              <div class="card-pdv-nome" title="${escapeHtml(p.modelo_nome)}">
                ${escapeHtml(p.modelo_nome)}
              </div>
              <div class="card-pdv-sub">
                <span>${escapeHtml(subPartes.join(" · ") || infoGrupo.nome)}</span>
                ${bolinhasCoresHtml}
              </div>
            </div>
            <span class="card-pdv-preco">${formatarMoeda(p.preco_venda)}</span>
          </div>
          <div class="card-pdv-variacoes">
            ${botoesTamanhoHtml}
          </div>
        </article>
      `;
    })
    .join("");
}

// ============================================================================
// 5. CARRINHO / CUPOM INTERATIVO (SILK UI), DESCONTOS, TROCO E FIADO
// ============================================================================
function calcularResumoFinanceiroPDV() {
  const subtotalBruto = estado.pdv.carrinho.reduce(
    (acc, item) => acc + num(item.preco_venda, 0) * num(item.quantidade, 0),
    0
  );

  const valorDigitado = Math.max(0, num(estado.pdv.valorDescontoInput, 0));
  let descontoRs = 0;
  let descontoPct = 0;

  if (subtotalBruto > 0) {
    if (estado.pdv.modoDesconto === "PCT") {
      descontoPct = Math.min(100, valorDigitado);
      descontoRs = (subtotalBruto * descontoPct) / 100;
    } else {
      descontoRs = Math.min(subtotalBruto, valorDigitado);
      descontoPct = (descontoRs / subtotalBruto) * 100;
    }
  }

  descontoRs = Number(descontoRs.toFixed(2));
  const totalLiquido = Math.max(0, Number((subtotalBruto - descontoRs).toFixed(2)));
  const totalPecas = estado.pdv.carrinho.reduce((acc, i) => acc + num(i.quantidade, 0), 0);

  return {
    subtotalBruto,
    descontoRs,
    descontoPct,
    totalLiquido,
    totalPecas,
  };
}

function renderizarCarrinhoPDV() {
  if (!dom.listaItensCarrinhoPdv) return;

  const itens = estado.pdv.carrinho;
  const totalPecas = itens.reduce((acc, i) => acc + num(i.quantidade, 0), 0);
  const chaveAnimada = estado.pdv.ultimoItemKeyAnimado;
  estado.pdv.ultimoItemKeyAnimado = null;

  if (dom.pdvBadgeQtdCarrinho) {
    dom.pdvBadgeQtdCarrinho.textContent = `${totalPecas} ${totalPecas === 1 ? "peça" : "peças"}`;
  }

  if (dom.btnPdvFinalizarVenda) {
    dom.btnPdvFinalizarVenda.disabled = itens.length === 0 || Boolean(estado.pdv.enviandoVenda);
  }

  if (!itens.length) {
    dom.listaItensCarrinhoPdv.innerHTML = `
      <div class="pdv-cart-vazio">
        <svg class="pdv-cart-vazio-svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <path d="M16 10a4 4 0 0 1-8 0"></path>
        </svg>
        <strong>Carrinho vazio</strong>
        <p>Bipe uma etiqueta <code>KNB...</code> ou clique em um tamanho no catálogo ao lado.</p>
      </div>
    `;
  } else {
    dom.listaItensCarrinhoPdv.innerHTML = itens
      .map((item, idx) => {
        const subtotalItem = num(item.preco_venda, 0) * num(item.quantidade, 0);
        const noLimite = item.quantidade >= item.estoque_max;
        const animarNovo = chaveAnimada && item.chave === chaveAnimada ? "item-novo" : "";
        const corDot =
          item.cor && item.cor.toLowerCase() !== "padrão"
            ? `<span class="bolinha-cor" style="background-color:${escapeHtml(item.cor_hex)};width:9px;height:9px;"></span><span>${escapeHtml(item.cor)}</span>`
            : "";

        return `
          <div class="item-carrinho-pdv ${animarNovo}">
            <div class="item-cart-info">
              <div class="item-cart-titulo" title="${escapeHtml(item.modelo_nome)}">
                ${escapeHtml(item.modelo_nome)} ${
                  item.marca
                    ? `<small style="color:var(--fg-muted);">(${escapeHtml(item.marca)})</small>`
                    : ""
                }
              </div>
              <div class="item-cart-meta">
                <span class="badge-tam-cor-cart">
                  Tam. ${escapeHtml(item.tamanho)}
                  ${corDot}
                </span>
                ${
                  item.codigo_barras
                    ? `<span class="badge-sku-cart">${escapeHtml(item.codigo_barras)}</span>`
                    : ""
                }
              </div>
            </div>

            <div class="item-cart-qty-ctrl">
              <button
                type="button"
                class="btn-cart-step"
                data-cart-idx="${idx}"
                data-cart-step="-1"
                title="Diminuir quantidade"
              >&minus;</button>
              <span class="item-cart-qty-val">${item.quantidade}</span>
              <button
                type="button"
                class="btn-cart-step"
                data-cart-idx="${idx}"
                data-cart-step="1"
                title="${noLimite ? `Limite máximo em estoque (${item.estoque_max})` : "Aumentar quantidade"}"
                ${noLimite ? "disabled" : ""}
              >+</button>
            </div>

            <div class="item-cart-valores">
              <div class="item-cart-subtotal">
                <strong>${formatarMoeda(subtotalItem)}</strong>
                <small>${item.quantidade}x ${formatarMoeda(item.preco_venda)}</small>
              </div>
              <button
                type="button"
                class="btn-remover-item-cart"
                data-cart-remove="${idx}"
                title="Remover item do cupom"
                aria-label="Remover item"
              >&times;</button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  atualizarTotaisCheckoutPDV();
}

function atualizarTotaisCheckoutPDV() {
  const { subtotalBruto, descontoRs, descontoPct, totalLiquido } = calcularResumoFinanceiroPDV();

  if (dom.pdvSubtotalBruto) {
    dom.pdvSubtotalBruto.textContent = formatarMoeda(subtotalBruto);
  }
  if (dom.pdvResumoDesconto) {
    dom.pdvResumoDesconto.textContent =
      descontoRs > 0
        ? `- ${formatarMoeda(descontoRs)} (${descontoPct.toFixed(1)}%)`
        : "- R$ 0,00";
  }
  if (dom.pdvTotalSubinfo) {
    dom.pdvTotalSubinfo.textContent =
      descontoRs > 0
        ? `Desconto aplicado: ${formatarMoeda(descontoRs)} (${descontoPct.toFixed(1)}%)`
        : "Sem desconto aplicado";
  }
  if (dom.pdvTotalLiquido) {
    dom.pdvTotalLiquido.textContent = formatarMoeda(totalLiquido);
  }

  atualizarCalculoTrocoPDV(totalLiquido);
  atualizarCardClienteSelecionadoPDV();
}

function atualizarCalculoTrocoPDV(totalLiquido = null) {
  if (!dom.pdvValorTroco) return;
  const total = totalLiquido !== null ? totalLiquido : calcularResumoFinanceiroPDV().totalLiquido;
  const recebidoStr = String(dom.inputPdvValorRecebido?.value ?? "").trim();
  const boxTroco = dom.pdvValorTroco.closest(".pdv-troco-display");

  if (!recebidoStr || num(recebidoStr, 0) === 0) {
    dom.pdvValorTroco.textContent = "R$ 0,00";
    boxTroco?.classList.remove("insuficiente");
    return;
  }

  const recebido = num(recebidoStr, 0);
  const diferenca = recebido - total;

  if (diferenca < -0.009) {
    dom.pdvValorTroco.textContent = `Falta ${formatarMoeda(Math.abs(diferenca))}`;
    boxTroco?.classList.add("insuficiente");
  } else {
    dom.pdvValorTroco.textContent = formatarMoeda(Math.max(0, diferenca));
    boxTroco?.classList.remove("insuficiente");
  }
}

function selecionarFormaPagamentoPDV(forma) {
  const pgto = String(forma || "PIX").toUpperCase();
  estado.pdv.formaPagamento = pgto;

  if (dom.pdvSeletorPagamento) {
    dom.pdvSeletorPagamento.querySelectorAll(".btn-pgto-pdv").forEach((btn) => {
      btn.classList.toggle("ativo", btn.dataset.pgto === pgto);
    });
  }

  // Painéis com transição fluida Silk UI (silkPanel no CSS quando :not(.hidden))
  dom.painelPgtoDinheiro?.classList.toggle("hidden", pgto !== "DINHEIRO");
  dom.painelPgtoFiado?.classList.toggle("hidden", pgto !== "FIADO");

  if (pgto === "DINHEIRO") {
    atualizarCalculoTrocoPDV();
    setTimeout(() => dom.inputPdvValorRecebido?.focus(), 40);
  } else if (pgto === "FIADO") {
    definirDataVencimentoPadraoPDV();
    carregarClientesPDV(true);
  }
}

function definirDataVencimentoPadraoPDV(diaPreferencial = null) {
  if (!dom.inputDataVencimentoPdv) return;
  if (dom.inputDataVencimentoPdv.value && !diaPreferencial) return;

  const hoje = new Date();
  const alvo = new Date(hoje.getTime());
  alvo.setDate(alvo.getDate() + 30);

  if (diaPreferencial && diaPreferencial >= 1 && diaPreferencial <= 28) {
    alvo.setDate(diaPreferencial);
  }

  const yyyy = alvo.getFullYear();
  const mm = String(alvo.getMonth() + 1).padStart(2, "0");
  const dd = String(alvo.getDate()).padStart(2, "0");
  dom.inputDataVencimentoPdv.value = `${yyyy}-${mm}-${dd}`;
}

async function carregarClientesPDV(silencioso = false) {
  try {
    const dados = await requisitarApi("/api/clientes");
    estado.pdv.clientes = Array.isArray(dados.clientes)
      ? dados.clientes
      : Array.isArray(dados)
        ? dados
        : [];
    renderizarSeletorClientesPDV();
  } catch (erro) {
    if (!silencioso) {
      exibirToast(erro.message || "Erro ao carregar clientes do fiado.", "erro");
    }
  }
}

function renderizarSeletorClientesPDV() {
  if (!dom.selectClienteFiadoPdv) return;
  const termo = String(estado.pdv.buscaCliente || "").trim().toLowerCase();
  const selecionadaId = String(estado.pdv.clienteIdSelecionado || "");

  const filtrados = estado.pdv.clientes.filter((c) => {
    if (!termo) return true;
    return (
      String(c.nome || "").toLowerCase().includes(termo) ||
      String(c.telefone || "").toLowerCase().includes(termo)
    );
  });

  const opcoesHtml = [
    `<option value="">Selecione um cliente (${filtrados.length} encontrado${
      filtrados.length === 1 ? "" : "s"
    })...</option>`,
    ...filtrados.map((c) => {
      const saldo = num(c.saldo_devedor, 0);
      const sel = String(c.id) === selecionadaId ? "selected" : "";
      const infoSaldo = saldo > 0 ? ` — Deve ${formatarMoeda(saldo)}` : " — Em dia";
      return `<option value="${c.id}" ${sel}>${escapeHtml(c.nome)}${escapeHtml(infoSaldo)}</option>`;
    }),
  ];

  dom.selectClienteFiadoPdv.innerHTML = opcoesHtml.join("");
  if (termo && filtrados.length === 1 && !selecionadaId) {
    estado.pdv.clienteIdSelecionado = String(filtrados[0].id);
    dom.selectClienteFiadoPdv.value = estado.pdv.clienteIdSelecionado;
  }
  atualizarCardClienteSelecionadoPDV();
}

function atualizarCardClienteSelecionadoPDV() {
  if (!dom.cardInfoClientePdv) return;
  const idSel = Number(estado.pdv.clienteIdSelecionado || 0);
  const cliente = estado.pdv.clientes.find((c) => Number(c.id) === idSel);

  if (!cliente) {
    dom.cardInfoClientePdv.classList.add("hidden");
    return;
  }

  dom.cardInfoClientePdv.classList.remove("hidden");
  const saldoAtual = num(cliente.saldo_devedor, 0);
  const limiteTotal = num(cliente.limite_credito, 800);
  const disponivel = Math.max(0, limiteTotal - saldoAtual);

  if (dom.pdvCliSaldo) dom.pdvCliSaldo.textContent = formatarMoeda(saldoAtual);
  if (dom.pdvCliLimite) dom.pdvCliLimite.textContent = formatarMoeda(limiteTotal);
  if (dom.pdvCliDisponivel) {
    dom.pdvCliDisponivel.textContent = formatarMoeda(disponivel);
    const { totalLiquido } = calcularResumoFinanceiroPDV();
    const estouraLimite = totalLiquido > disponivel && limiteTotal > 0;
    dom.pdvCliDisponivel.className = estouraLimite ? "txt-vermelho" : "txt-verde";
  }
}

async function submeterNovoClienteRapidoPDV(evento) {
  evento.preventDefault();
  const nome = String(dom.rapidoCliNome?.value || "").trim();
  const telefone = String(dom.rapidoCliTelefone?.value || "").trim();
  const limite = num(dom.rapidoCliLimite?.value, 800);
  const dia = parseInt(dom.rapidoCliDia?.value || "10", 10) || 10;

  if (!nome) {
    exibirToast("Informe o nome completo do cliente.", "aviso");
    dom.rapidoCliNome?.focus();
    return;
  }

  if (dom.btnSalvarClienteRapido) {
    dom.btnSalvarClienteRapido.disabled = true;
    dom.btnSalvarClienteRapido.textContent = "Salvando...";
  }

  try {
    const res = await requisitarApi("/api/clientes", {
      metodo: "POST",
      corpo: {
        nome,
        telefone,
        limite_credito: limite,
        dia_preferencial_pagamento: dia,
        dia_vencimento: dia,
      },
    });

    await carregarClientesPDV(true);
    const novoId = res.cliente_id || res.id;
    if (novoId) {
      estado.pdv.clienteIdSelecionado = String(novoId);
      estado.pdv.buscaCliente = "";
      if (dom.inputBuscaClientePdv) dom.inputBuscaClientePdv.value = "";
      renderizarSeletorClientesPDV();
      definirDataVencimentoPadraoPDV(dia);
    }

    if (typeof window.carregarFiado === "function") {
      window.carregarFiado(true);
    }

    fecharModal("modal-cliente-rapido");
    if (dom.rapidoCliNome) dom.rapidoCliNome.value = "";
    if (dom.rapidoCliTelefone) dom.rapidoCliTelefone.value = "";
    exibirToast(res.mensagem || `Cliente "${nome}" cadastrado e selecionado.`, "sucesso");
  } catch (erro) {
    exibirToast(erro.message || "Não foi possível cadastrar o cliente.", "erro");
  } finally {
    if (dom.btnSalvarClienteRapido) {
      dom.btnSalvarClienteRapido.disabled = false;
      dom.btnSalvarClienteRapido.textContent = "Cadastrar & Selecionar";
    }
  }
}

function limparCarrinhoPDV(silencioso = false) {
  estado.pdv.carrinho = [];
  estado.pdv.valorDescontoInput = 0;
  estado.pdv.valorRecebido = "";
  if (dom.inputPdvDesconto) dom.inputPdvDesconto.value = "0";
  if (dom.inputPdvValorRecebido) dom.inputPdvValorRecebido.value = "";
  atualizarBadgeFilaVenda();
  renderizarCarrinhoPDV();
  renderizarCatalogoPDV();
  if (!silencioso) {
    exibirToast("Carrinho esvaziado.", "info", 2000);
  }
}

// ============================================================================
// 6. FINALIZAÇÃO DE VENDA (POST /api/vendas) E MODAL DE RECIBO
// ============================================================================
async function finalizarVendaPDV() {
  if (estado.pdv.enviandoVenda) return;

  if (!estado.pdv.carrinho.length) {
    tocarSomPDV("erro");
    exibirToast("O carrinho está vazio. Adicione pelo menos uma peça para finalizar.", "aviso");
    dom.inputBipePdv?.focus();
    return;
  }

  const { subtotalBruto, descontoRs, totalLiquido } = calcularResumoFinanceiroPDV();
  const formaPgto = estado.pdv.formaPagamento;

  if (formaPgto === "DINHEIRO") {
    const valRecStr = String(dom.inputPdvValorRecebido?.value || "").trim();
    if (valRecStr && num(valRecStr, 0) < totalLiquido - 0.009) {
      tocarSomPDV("erro");
      exibirToast("O valor recebido em dinheiro é menor que o total a pagar.", "aviso");
      dom.inputPdvValorRecebido?.focus();
      return;
    }
  }

  let clienteIdPayload = null;
  let dataVencPayload = "";
  if (formaPgto === "FIADO") {
    const cliId = Number(estado.pdv.clienteIdSelecionado || dom.selectClienteFiadoPdv?.value || 0);
    if (!cliId) {
      tocarSomPDV("erro");
      exibirToast("Selecione um cliente cadastrado para registrar a venda no Fiado.", "aviso");
      dom.selectClienteFiadoPdv?.focus();
      return;
    }
    clienteIdPayload = cliId;
    dataVencPayload = String(dom.inputDataVencimentoPdv?.value || "").trim();
  }

  const snapshotItens = estado.pdv.carrinho.map((i) => ({ ...i }));
  const valorRecebidoNum = num(dom.inputPdvValorRecebido?.value, 0);
  const trocoCalculado =
    formaPgto === "DINHEIRO" && valorRecebidoNum > totalLiquido
      ? valorRecebidoNum - totalLiquido
      : 0;

  const payload = {
    itens: estado.pdv.carrinho.map((item) => ({
      codigo_barras: item.codigo_barras || "",
      variacao_id: item.variacao_id || null,
      quantidade: item.quantidade,
      preco_unitario: item.preco_venda,
    })),
    desconto_total: descontoRs,
    desconto: descontoRs,
    forma_pagamento: formaPgto,
    cliente_id: clienteIdPayload,
    data_vencimento_lote: dataVencPayload,
  };

  estado.pdv.enviandoVenda = true;
  if (dom.btnPdvFinalizarVenda) {
    dom.btnPdvFinalizarVenda.disabled = true;
    dom.btnPdvFinalizarVenda.innerHTML = `<span>Processando venda...</span>`;
  }

  try {
    const res = await requisitarApi("/api/vendas", {
      metodo: "POST",
      corpo: payload,
    });

    tocarSomPDV("venda");
    exibirModalReciboVenda({
      resposta: res,
      itens: snapshotItens,
      subtotalBruto,
      descontoRs,
      totalLiquido,
      formaPgto,
      trocoCalculado,
      valorRecebidoNum,
    });

    limparCarrinhoPDV(true);
    selecionarFormaPagamentoPDV("PIX");

    await Promise.all([
      typeof window.carregarEstoque === "function" ? window.carregarEstoque(true) : Promise.resolve(),
      carregarKpisVendasHoje(),
      formaPgto === "FIADO" ? carregarClientesPDV(true) : Promise.resolve(),
      formaPgto === "FIADO" && typeof window.carregarFiado === "function"
        ? window.carregarFiado(true)
        : Promise.resolve(),
    ]);
  } catch (erro) {
    tocarSomPDV("erro");
    exibirToast(erro.message || "Falha ao finalizar a venda.", "erro", 4500);
  } finally {
    estado.pdv.enviandoVenda = false;
    if (dom.btnPdvFinalizarVenda) {
      dom.btnPdvFinalizarVenda.innerHTML = `<span>Finalizar Venda</span><kbd>F12</kbd>`;
      dom.btnPdvFinalizarVenda.disabled = estado.pdv.carrinho.length === 0;
    }
  }
}

function exibirModalReciboVenda({
  resposta,
  itens,
  subtotalBruto,
  descontoRs,
  totalLiquido,
  formaPgto,
  trocoCalculado,
  valorRecebidoNum,
}) {
  if (!dom.modalReciboVenda) return;

  if (dom.reciboDataHora) {
    dom.reciboDataHora.textContent = resposta.data_hora || new Date().toLocaleString("pt-BR");
  }

  if (dom.reciboListaItens) {
    dom.reciboListaItens.innerHTML = itens
      .map(
        (i) => `
          <li>
            <span>${i.quantidade}x <strong>${escapeHtml(i.modelo_nome)}</strong> (${escapeHtml(i.tamanho)})</span>
            <strong>${formatarMoeda(i.preco_venda * i.quantidade)}</strong>
          </li>
        `
      )
      .join("");
  }

  if (dom.reciboSubtotal) dom.reciboSubtotal.textContent = formatarMoeda(subtotalBruto);
  if (dom.reciboDesconto) dom.reciboDesconto.textContent = `- ${formatarMoeda(descontoRs)}`;
  if (dom.reciboLinhaDesconto) {
    dom.reciboLinhaDesconto.classList.toggle("hidden", descontoRs <= 0);
  }
  if (dom.reciboTotalFinal) dom.reciboTotalFinal.textContent = formatarMoeda(totalLiquido);

  if (dom.reciboFormaPgto) {
    dom.reciboFormaPgto.textContent = ROTULOS_FORMA_PGTO[formaPgto] || formaPgto;
  }

  if (dom.reciboLinhaExtra && dom.reciboExtraLabel && dom.reciboExtraValor) {
    if (formaPgto === "DINHEIRO" && valorRecebidoNum > 0) {
      dom.reciboLinhaExtra.classList.remove("hidden");
      dom.reciboExtraLabel.textContent = `Troco (Recebido ${formatarMoeda(valorRecebidoNum)}):`;
      dom.reciboExtraValor.textContent = formatarMoeda(trocoCalculado);
    } else if (formaPgto === "FIADO") {
      const cliNome =
        resposta.cliente_nome ||
        estado.pdv.clientes.find((c) => Number(c.id) === Number(estado.pdv.clienteIdSelecionado))
          ?.nome ||
        "Cliente Fiado";
      dom.reciboLinhaExtra.classList.remove("hidden");
      dom.reciboExtraLabel.textContent = "Lançado na conta de:";
      dom.reciboExtraValor.textContent = cliNome;
    } else {
      dom.reciboLinhaExtra.classList.add("hidden");
    }
  }

  dom.modalReciboVenda.classList.remove("hidden");
  setTimeout(() => dom.btnReciboNovaVenda?.focus(), 60);
}

// ============================================================================
// 7. HISTÓRICO & ESTORNO DE VENDAS RECENTES (#modal-historico-vendas)
// ============================================================================
async function carregarHistoricoVendasRecentes() {
  const container = dom.listaHistoricoVendas || $("lista-historico-vendas");
  if (!container) return;

  container.innerHTML = `<p class="hv-vazio">Carregando vendas recentes...</p>`;

  try {
    const dados = await requisitarApi("/api/vendas/recentes?limite=15");
    const vendas = Array.isArray(dados.vendas) ? dados.vendas : [];

    if (!vendas.length) {
      container.innerHTML = `<p class="hv-vazio">Nenhuma venda registrada recentemente.</p>`;
      return;
    }

    container.innerHTML = vendas
      .map((v) => {
        const vendaId = v.id;
        const formaLabel = ROTULOS_FORMA_PGTO[v.forma_pagamento] || v.forma_pagamento || "Dinheiro";
        const clienteInfo = v.cliente_nome ? ` · Cliente: ${v.cliente_nome}` : "";
        const resumoItens =
          v.resumo_itens ||
          (Array.isArray(v.itens)
            ? v.itens.map((it) => `${it.quantidade}x ${it.modelo_nome} (${it.tamanho})`).join(", ")
            : "Itens da venda");
        const qtdPecas =
          v.pecas_total ||
          (Array.isArray(v.itens) ? v.itens.reduce((a, b) => a + num(b.quantidade, 0), 0) : 1);
        const valorFormatado = formatarMoeda(v.valor_total);

        return `
          <div class="hv-item" data-hv-id="${vendaId}">
            <div class="hv-info">
              <strong>#${vendaId} · ${escapeHtml(v.data_venda || "—")} · ${escapeHtml(formaLabel)}${escapeHtml(clienteInfo)}</strong>
              <div class="hv-itens">${escapeHtml(resumoItens)}</div>
              <small>${qtdPecas} ${qtdPecas === 1 ? "peça vendida" : "peças vendidas"}</small>
            </div>
            <div class="hv-valor">${valorFormatado}</div>
            <button
              type="button"
              class="btn-estornar-venda"
              data-estornar-venda-id="${vendaId}"
              data-estornar-resumo="${escapeHtml(resumoItens)}"
              data-estornar-valor="${escapeHtml(valorFormatado)}"
            >
              Estornar Venda
            </button>
          </div>
        `;
      })
      .join("");
  } catch (erro) {
    container.innerHTML = `<p class="hv-vazio">Erro ao consultar histórico: ${escapeHtml(erro.message)}</p>`;
  }
}

async function abrirModalHistoricoVendas() {
  abrirModal("modal-historico-vendas");
  await carregarHistoricoVendasRecentes();
}

async function confirmarEstornoVendaRecente(vendaId, resumoItens, valorFormatado, btnElemento) {
  const confirmar = window.confirm(
    `Confirmar estorno da Venda #${vendaId} (${valorFormatado})?\n\nItens: ${resumoItens}\n\nAs peças retornarão automaticamente ao estoque e eventual débito no Fiado será revertido.`
  );
  if (!confirmar) return;

  if (btnElemento) {
    btnElemento.disabled = true;
    btnElemento.textContent = "Estornando...";
  }

  try {
    const resp = await requisitarApi(`/api/vendas/${encodeURIComponent(vendaId)}/estornar`, {
      metodo: "POST",
    });

    exibirToast(
      resp.mensagem || `Venda #${vendaId} estornada com sucesso e estoque recomposto.`,
      "sucesso"
    );

    await Promise.all([
      carregarHistoricoVendasRecentes(),
      typeof window.carregarEstoque === "function" ? window.carregarEstoque(true) : Promise.resolve(),
      carregarKpisVendasHoje(),
      carregarClientesPDV(true),
      typeof window.carregarFiado === "function" ? window.carregarFiado(true) : Promise.resolve(),
      typeof window.carregarDashboard === "function"
        ? window.carregarDashboard(true)
        : Promise.resolve(),
    ]);
  } catch (erro) {
    exibirToast(`Falha ao estornar venda #${vendaId}: ${erro.message}`, "erro");
    if (btnElemento) {
      btnElemento.disabled = false;
      btnElemento.textContent = "Estornar Venda";
    }
  }
}

// ============================================================================
// 8. REGISTRO DE EVENTOS DA ABA NOVA VENDA / PDV
// ============================================================================
function registrarEventosVenda() {
  if (eventosVendaRegistrados) return;
  eventosVendaRegistrados = true;

  // Histórico & Estorno de Vendas Recentes
  dom.btnAbrirHistoricoVendas?.addEventListener("click", abrirModalHistoricoVendas);

  dom.listaHistoricoVendas?.addEventListener("click", (e) => {
    const btnEstornar = e.target.closest("[data-estornar-venda-id]");
    if (!btnEstornar) return;
    const vendaId = Number(btnEstornar.dataset.estornarVendaId);
    if (!vendaId) return;
    confirmarEstornoVendaRecente(
      vendaId,
      btnEstornar.dataset.estornarResumo || "",
      btnEstornar.dataset.estornarValor || "",
      btnEstornar
    );
  });

  // Barra de Bipe / Busca Rápida no Catálogo PDV
  dom.inputBipePdv?.addEventListener("input", (e) => {
    const valor = e.target.value || "";
    estado.pdv.termoBusca = valor;
    dom.btnLimparBuscaPdv?.classList.toggle("hidden", valor.length === 0);
    renderizarCatalogoPDV();
  });

  dom.inputBipePdv?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      processarBipeOuBuscaEnterPDV();
    }
  });

  dom.btnLimparBuscaPdv?.addEventListener("click", () => {
    if (dom.inputBipePdv) dom.inputBipePdv.value = "";
    estado.pdv.termoBusca = "";
    dom.btnLimparBuscaPdv.classList.add("hidden");
    renderizarCatalogoPDV();
    dom.inputBipePdv?.focus();
  });

  dom.btnBiparManualPdv?.addEventListener("click", processarBipeOuBuscaEnterPDV);

  // Filtro de Grandes Grupos do Catálogo PDV
  dom.pdvBarraGrupos?.addEventListener("click", (e) => {
    const pill = e.target.closest("[data-pdv-grupo]");
    if (!pill) return;
    const grupo = pill.dataset.pdvGrupo || "todos";
    estado.pdv.filtroGrupo = grupo;
    dom.pdvBarraGrupos.querySelectorAll("[data-pdv-grupo]").forEach((b) => {
      b.classList.toggle("ativo", b.dataset.pdvGrupo === grupo);
    });
    renderizarCatalogoPDV();
  });

  // Clique direto em um tamanho no Catálogo Rápido
  dom.gridCatalogoPdv?.addEventListener("click", (e) => {
    const btnTam = e.target.closest("[data-pdv-add-pid]");
    if (!btnTam || btnTam.disabled) return;
    const pid = Number(btnTam.dataset.pdvAddPid);
    const vid = btnTam.dataset.pdvAddVid ? Number(btnTam.dataset.pdvAddVid) : null;
    const cod = btnTam.dataset.pdvAddCod || "";
    const tam = btnTam.dataset.pdvAddTam || "";

    const achado = encontrarVariacaoEmMemoria({
      variacaoId: vid,
      codigoBarras: cod,
      produtoId: pid,
      tamanho: tam,
    });
    if (achado && achado.prod && achado.variacao) {
      adicionarVariacaoAoCarrinhoPDV(achado.prod, achado.variacao);
    }
  });

  // Controles do Carrinho (- / + / Remover / Limpar)
  dom.listaItensCarrinhoPdv?.addEventListener("click", (e) => {
    const btnStep = e.target.closest("[data-cart-step]");
    if (btnStep) {
      const idx = Number(btnStep.dataset.cartIdx);
      const delta = Number(btnStep.dataset.cartStep);
      const item = estado.pdv.carrinho[idx];
      if (!item) return;

      const novaQtd = item.quantidade + delta;
      if (novaQtd <= 0) {
        estado.pdv.carrinho.splice(idx, 1);
      } else if (novaQtd <= item.estoque_max) {
        item.quantidade = novaQtd;
        if (delta > 0) {
          estado.pdv.ultimoItemKeyAnimado = item.chave;
        }
      } else {
        exibirToast(`Limite em estoque atingido (${item.estoque_max} disp.).`, "aviso");
        return;
      }

      atualizarBadgeFilaVenda();
      renderizarCarrinhoPDV();
      renderizarCatalogoPDV();
      return;
    }

    const btnRem = e.target.closest("[data-cart-remove]");
    if (btnRem) {
      const idx = Number(btnRem.dataset.cartRemove);
      if (Number.isInteger(idx) && idx >= 0 && idx < estado.pdv.carrinho.length) {
        estado.pdv.carrinho.splice(idx, 1);
        atualizarBadgeFilaVenda();
        renderizarCarrinhoPDV();
        renderizarCatalogoPDV();
      }
    }
  });

  dom.btnPdvLimparCarrinho?.addEventListener("click", () => {
    if (!estado.pdv.carrinho.length) return;
    limparCarrinhoPDV(false);
  });

  // Controles de Desconto (Modo R$ / % + Input + Atalhos 5%, 10%, 15%, Zerar)
  dom.btnDescModoRs?.addEventListener("click", () => {
    estado.pdv.modoDesconto = "RS";
    dom.btnDescModoRs.classList.add("ativo");
    dom.btnDescModoPct?.classList.remove("ativo");
    atualizarTotaisCheckoutPDV();
  });

  dom.btnDescModoPct?.addEventListener("click", () => {
    estado.pdv.modoDesconto = "PCT";
    dom.btnDescModoPct.classList.add("ativo");
    dom.btnDescModoRs?.classList.remove("ativo");
    atualizarTotaisCheckoutPDV();
  });

  dom.inputPdvDesconto?.addEventListener("input", (e) => {
    estado.pdv.valorDescontoInput = Math.max(0, num(e.target.value, 0));
    atualizarTotaisCheckoutPDV();
  });

  document.querySelectorAll("#view-venda [data-desc-rapido]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pct = num(btn.dataset.descRapido, 0);
      if (pct <= 0) {
        estado.pdv.valorDescontoInput = 0;
        if (dom.inputPdvDesconto) dom.inputPdvDesconto.value = "0";
      } else {
        estado.pdv.modoDesconto = "PCT";
        dom.btnDescModoPct?.classList.add("ativo");
        dom.btnDescModoRs?.classList.remove("ativo");
        estado.pdv.valorDescontoInput = pct;
        if (dom.inputPdvDesconto) dom.inputPdvDesconto.value = String(pct);
      }
      atualizarTotaisCheckoutPDV();
    });
  });

  // Seletor de Forma de Pagamento (PIX, CARTAO, DINHEIRO, FIADO)
  dom.pdvSeletorPagamento?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-pgto]");
    if (!btn) return;
    selecionarFormaPagamentoPDV(btn.dataset.pgto);
  });

  // Painel Dinheiro: valor recebido + cédulas rápidas
  dom.inputPdvValorRecebido?.addEventListener("input", () => {
    estado.pdv.valorRecebido = dom.inputPdvValorRecebido.value;
    atualizarCalculoTrocoPDV();
  });

  dom.painelPgtoDinheiro?.addEventListener("click", (e) => {
    const btnCed = e.target.closest("[data-cedula]");
    if (!btnCed || !dom.inputPdvValorRecebido) return;
    const ced = btnCed.dataset.cedula;
    if (ced === "exato") {
      const { totalLiquido } = calcularResumoFinanceiroPDV();
      dom.inputPdvValorRecebido.value = totalLiquido.toFixed(2);
    } else {
      dom.inputPdvValorRecebido.value = Number(num(ced, 0)).toFixed(2);
    }
    estado.pdv.valorRecebido = dom.inputPdvValorRecebido.value;
    atualizarCalculoTrocoPDV();
  });

  // Painel Fiado: busca/seleção de cliente + Novo Cliente Rápido
  dom.inputBuscaClientePdv?.addEventListener("input", (e) => {
    estado.pdv.buscaCliente = e.target.value || "";
    renderizarSeletorClientesPDV();
  });

  dom.selectClienteFiadoPdv?.addEventListener("change", (e) => {
    estado.pdv.clienteIdSelecionado = e.target.value || "";
    const cli = estado.pdv.clientes.find(
      (c) => Number(c.id) === Number(estado.pdv.clienteIdSelecionado)
    );
    if (cli?.dia_preferencial_pagamento) {
      definirDataVencimentoPadraoPDV(Number(cli.dia_preferencial_pagamento));
    }
    atualizarCardClienteSelecionadoPDV();
  });

  dom.btnAbrirModalClienteRapido?.addEventListener("click", () => {
    abrirModal("modal-cliente-rapido");
    setTimeout(() => dom.rapidoCliNome?.focus(), 50);
  });

  dom.formClienteRapido?.addEventListener("submit", submeterNovoClienteRapidoPDV);

  // Botão Finalizar Venda (F12) + Botão Nova Venda no Recibo
  dom.btnPdvFinalizarVenda?.addEventListener("click", finalizarVendaPDV);

  dom.btnReciboNovaVenda?.addEventListener("click", () => {
    fecharModal("modal-recibo-venda");
    setTimeout(() => dom.inputBipePdv?.focus(), 40);
  });
}

function inicializarDadosPdv() {
  carregarKpisVendasHoje();
  carregarClientesPDV(true);
  renderizarCarrinhoPDV();
  renderizarCatalogoPDV();
}

// Exportações globais para integração com core.js e aba_estoque.js
window.sincronizarLimitesCarrinhoComEstoque = sincronizarLimitesCarrinhoComEstoque;
window.renderizarCatalogoPDV = renderizarCatalogoPDV;
window.renderizarCarrinhoPDV = renderizarCarrinhoPDV;
window.carregarKpisVendasHoje = carregarKpisVendasHoje;
window.carregarClientesPDV = carregarClientesPDV;
window.finalizarVendaPDV = finalizarVendaPDV;
window.acionarEnviarParaVenda = acionarEnviarParaVenda;
window.abrirModalHistoricoVendas = abrirModalHistoricoVendas;

KanembergApp.eventos.push(registrarEventosVenda);
KanembergApp.inicializadores.push(inicializarDadosPdv);

if (document.readyState !== "loading") {
  registrarEventosVenda();
  inicializarDadosPdv();
}
