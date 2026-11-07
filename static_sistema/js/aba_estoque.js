/**
 * js/aba_estoque.js — Kanemberg Sistema Desktop (módulo carregado via <script defer>).
 * Aba 1 (Vitrine de Estoque): cards, filtros, modais Editar/Excluir/Detalhes e envio ao PDV.
 */

// =========================================================================
// 8. CARREGAMENTO E RENDERIZAÇÃO DA VITRINE DE ESTOQUE
// =========================================================================
async function carregarEstoque(silencioso = false) {
  if (!silencioso && dom.gridVitrine && !estado.produtos.length) {
    dom.gridVitrine.innerHTML = `
      <div class="estado-vazio">
        <div class="spinner-sistema"></div>
        <p>Carregando vitrine de estoque...</p>
      </div>
    `;
  }

  try {
    const dados = await requisitarApi("/api/estoque");
    estado.produtos = Array.isArray(dados.produtos) ? dados.produtos : [];
    renderizarVitrine();
    sincronizarLimitesCarrinhoComEstoque();
    renderizarCatalogoPDV();
  } catch (erro) {
    if (!silencioso && dom.gridVitrine) {
      dom.gridVitrine.innerHTML = `
        <div class="estado-vazio">
          <p>Não foi possível carregar o estoque: ${escapeHtml(erro.message)}</p>
        </div>
      `;
    }
  }
}

function filtrarProdutosVitrine() {
  const grupoFiltro = estado.filtroGrupo;
  const termo = estado.termoBusca.trim().toLowerCase();
  const tokens = termo ? termo.split(/\s+/) : [];

  return estado.produtos.filter((p) => {
    const infoGrupo = obterGrupoProduto(p.modelo_nome, p.tipo_peca);
    if (grupoFiltro !== "todos" && infoGrupo.chave !== grupoFiltro) {
      return false;
    }

    if (!tokens.length) return true;

    const cores = extrairCoresProduto(p).map((c) => c.nome).join(" ");
    const vars = Array.isArray(p.variacoes) ? p.variacoes : [];
    const tamanhos = vars.map((v) => `${v.tamanho || ""} ${v.codigo_barras || ""}`).join(" ");

    const fichaBusca = [
      p.modelo_nome || "",
      p.tipo_peca || "",
      p.marca || "",
      p.corte || "",
      p.tecido || "",
      infoGrupo.nome,
      cores,
      tamanhos,
    ]
      .join(" ")
      .toLowerCase();

    return tokens.every((tk) => fichaBusca.includes(tk));
  });
}

function renderizarVitrine() {
  if (!dom.gridVitrine) return;

  const filtrados = filtrarProdutosVitrine();
  const total = filtrados.length;

  if (dom.contadorModelos) {
    dom.contadorModelos.textContent = `${total} modelo(s) encontrado(s)`;
  }

  if (total === 0) {
    dom.gridVitrine.innerHTML = `
      <div class="estado-vazio">
        <p>Nenhum produto encontrado no estoque para os filtros selecionados.</p>
      </div>
    `;
    return;
  }

  const htmlCards = filtrados.map((prod, index) => montarHtmlCardProduto(prod, index)).join("");
  dom.gridVitrine.innerHTML = htmlCards;
}

function montarHtmlCardProduto(p, index = 0) {
  const pid = p.id || p.produto_id;
  const grupo = obterGrupoProduto(p.modelo_nome, p.tipo_peca);
  const vars = Array.isArray(p.variacoes) ? p.variacoes : [];

  const estoqueTotal =
    p.estoque_total !== undefined && p.estoque_total !== null
      ? num(p.estoque_total)
      : vars.reduce((acc, v) => acc + num(v.estoque), 0);

  const precoVenda =
    num(p.preco_venda) ||
    (vars.length ? Math.max(...vars.map((v) => num(v.preco_venda))) : 0);

  const precoCusto =
    num(p.preco_custo) ||
    (vars.length ? Math.max(...vars.map((v) => num(v.preco_custo))) : 0);

  // Título: Modelo — Marca
  const modeloStr = String(p.modelo_nome || p.tipo_peca || "Produto").trim();
  const marcaStr = valorValido(p.marca) ? String(p.marca).trim() : "";
  const tituloCard = marcaStr ? `${modeloStr} — ${marcaStr}` : modeloStr;

  // Subtítulo: Corte | Tecido (ocultando vazios ou "N/A")
  const partesSub = [p.corte, p.tecido]
    .filter(valorValido)
    .map((item) => String(item).trim());
  const subtituloHtml = partesSub.length
    ? `<div class="card-subtitulo-peca">${escapeHtml(partesSub.join(" | "))}</div>`
    : "";

  // Badge de quantidade total em estoque
  let classeBadgeEstoque = "estoque-ok";
  let textoBadgeEstoque = `${estoqueTotal} un. em estoque`;
  if (estoqueTotal <= 0) {
    classeBadgeEstoque = "estoque-esgotado";
    textoBadgeEstoque = "Esgotado";
  } else if (estoqueTotal <= 3) {
    classeBadgeEstoque = "estoque-baixo";
    textoBadgeEstoque = `${estoqueTotal} un. restantes`;
  }

  // Bolinhas de cores cadastradas (cor_hex)
  const listaCores = extrairCoresProduto(p);
  const bolinhasHtml = listaCores.length
    ? `<div class="card-bolinhas-cores">
        ${listaCores
          .slice(0, 8)
          .map(
            (c) =>
              `<span class="bolinha-cor-item" style="background-color: ${escapeHtml(c.cor_hex)};" title="${escapeHtml(c.nome)}"></span>`
          )
          .join("")}
      </div>`
    : `<div></div>`;

  // Grade de Tamanhos (Pills: P x0 riscado, M x4, G x1)
  const tamanhosOrdenados = agruparTamanhosProduto(p);
  const pillsTamanhosHtml = tamanhosOrdenados.length
    ? tamanhosOrdenados
        .map((t) => {
          const zerado = t.estoque <= 0;
          if (zerado) {
            return `
              <span class="pill-tamanho zerado" title="Tamanho ${escapeHtml(t.tamanho)} esgotado">
                <span class="tam-label">${escapeHtml(t.tamanho)}</span>
                <span class="tam-qtd">x0</span>
              </span>
            `;
          }
          return `
            <button
              type="button"
              class="pill-tamanho disponivel"
              data-acao="vender-tamanho"
              data-produto-id="${pid}"
              data-tamanho="${escapeHtml(t.tamanho)}"
              title="Enviar Tam. ${escapeHtml(t.tamanho)} (${t.estoque} disp.) para Nova Venda"
            >
              <span class="tam-label">${escapeHtml(t.tamanho)}</span>
              <span class="tam-qtd">x${t.estoque}</span>
            </button>
          `;
        })
        .join("")
    : `<span class="card-subtitulo-peca">Sem grade cadastrada</span>`;

  return `
    <article class="card-vitrine" data-produto-id="${pid}" style="--card-index: ${index};">
      <div>
        <!-- Topo do Card: Categoria Corporativa Neutra + Preço -->
        <div class="card-topo-row">
          <span class="badge-categoria-card">
            <span>${escapeHtml(grupo.nome)}</span>
          </span>
          <span class="card-preco-venda">${formatarMoeda(precoVenda)}</span>
        </div>

        <!-- Corpo: Nome do Modelo + Marca e Corte | Tecido -->
        <div class="card-corpo-info">
          <h2 class="card-titulo-modelo">${escapeHtml(tituloCard)}</h2>
          ${subtituloHtml}
        </div>

        <!-- Linha de Status (Qtd Total) e Bolinhas de Cores -->
        <div class="card-status-cores-row">
          <span class="badge-qtd-estoque ${classeBadgeEstoque}">${escapeHtml(textoBadgeEstoque)}</span>
          ${bolinhasHtml}
        </div>

        <div class="card-divisor"></div>

        <!-- Grade de Tamanhos (Pills) -->
        <div class="card-grade-tamanhos">
          ${pillsTamanhosHtml}
        </div>

        <div class="card-divisor"></div>
      </div>

      <!-- Rodapé do Card: Custo à esquerda + 5 Botões de Ação à direita -->
      <div class="card-rodape-row">
        <span class="card-custo-label">${escapeHtml(formatarCustoCurto(precoCusto))}</span>

        <div class="card-acoes-grupo">
          <button
            type="button"
            class="btn-card-acao acao-vender"
            data-acao="vender"
            data-produto-id="${pid}"
            title="Enviar para Nova Venda"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
          </button>

          <button
            type="button"
            class="btn-card-acao acao-escura"
            data-acao="detalhes"
            data-produto-id="${pid}"
            title="Detalhes e Calculadora de Margem"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="4" y="2" width="16" height="20" rx="2"></rect>
              <line x1="8" y1="6" x2="16" y2="6"></line>
              <line x1="16" y1="14" x2="16" y2="18"></line>
              <path d="M16 10h.01"></path>
              <path d="M12 10h.01"></path>
              <path d="M8 10h.01"></path>
              <path d="M12 14h.01"></path>
              <path d="M8 14h.01"></path>
              <path d="M12 18h.01"></path>
              <path d="M8 18h.01"></path>
            </svg>
          </button>

          <button
            type="button"
            class="btn-card-acao acao-escura"
            data-acao="qrcode"
            data-produto-id="${pid}"
            title="Imprimir Etiquetas QR Code"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="6 9 6 2 18 2 18 9"></polyline>
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
              <rect x="6" y="14" width="12" height="8"></rect>
            </svg>
          </button>

          <button
            type="button"
            class="btn-card-acao acao-escura"
            data-acao="editar"
            data-produto-id="${pid}"
            title="Editar Produto e Estoque"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
          </button>

          <button
            type="button"
            class="btn-card-acao acao-excluir"
            data-acao="excluir"
            data-produto-id="${pid}"
            title="Excluir Produto"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
    </article>
  `;
}

function buscarProdutoEmMemoria(produtoId) {
  const idNum = Number(produtoId);
  return estado.produtos.find((p) => Number(p.id || p.produto_id) === idNum) || null;
}

// =========================================================================
// 9. MODAL 1: EDITAR PRODUTO / ESTOQUE E PREÇOS (PUT /api/produtos/{id})
// =========================================================================
function abrirModalEditar(produtoId) {
  const prod = buscarProdutoEmMemoria(produtoId);
  if (!prod || !dom.modalEditar) return;

  estado.produtoEditando = prod;
  estado.coresEditando = extrairCoresProduto(prod);

  const grupo = obterGrupoProduto(prod.modelo_nome, prod.tipo_peca);
  if (dom.modalEditarBadge) {
    dom.modalEditarBadge.textContent = grupo.nome;
  }

  dom.editProdutoId.value = prod.id || prod.produto_id;
  dom.editModeloNome.value = prod.modelo_nome || "";
  dom.editMarca.value = valorValido(prod.marca) ? prod.marca : "";
  dom.editCorte.value = valorValido(prod.corte) ? prod.corte : "";
  dom.editTecido.value = valorValido(prod.tecido) ? prod.tecido : "";
  dom.editPrecoCusto.value = num(prod.preco_custo).toFixed(2);
  dom.editPrecoVenda.value = num(prod.preco_venda).toFixed(2);

  atualizarResumoMargemEdicao();
  renderizarChipsCoresEdicao();

  const vars = Array.isArray(prod.variacoes) && prod.variacoes.length
    ? prod.variacoes
    : [{ id: null, tamanho: "U", estoque: 0, preco_custo: prod.preco_custo || 0, preco_venda: prod.preco_venda || 0, codigo_barras: "" }];

  dom.editListaVariacoes.innerHTML = "";
  vars.forEach((v) => adicionarLinhaVariacaoEditor(v));

  dom.modalEditar.classList.remove("hidden");
  dom.editModeloNome.focus();
}

function atualizarResumoMargemEdicao() {
  const custo = num(dom.editPrecoCusto.value);
  const venda = num(dom.editPrecoVenda.value);
  const lucro = venda - custo;
  const margem = venda > 0 ? (lucro / venda) * 100 : 0;
  if (dom.editResumoMargem) {
    dom.editResumoMargem.textContent = `${formatarMoeda(lucro)} (${margem.toFixed(1)}%)`;
    dom.editResumoMargem.style.color = lucro >= 0 ? "#4ade80" : "#f87171";
  }
}

function renderizarChipsCoresEdicao() {
  if (!dom.editListaCores) return;
  if (!estado.coresEditando.length) {
    dom.editListaCores.innerHTML = `<span class="card-subtitulo-peca">Nenhuma cor específica cadastrada.</span>`;
    return;
  }

  dom.editListaCores.innerHTML = estado.coresEditando
    .map(
      (c, idx) => `
        <span class="chip-cor-edit">
          <span class="dot-cor" style="background-color: ${escapeHtml(c.cor_hex)};"></span>
          <span>${escapeHtml(c.nome)}</span>
          <button type="button" data-remover-cor="${idx}" title="Remover cor">✕</button>
        </span>
      `
    )
    .join("");
}

function adicionarLinhaVariacaoEditor(v = {}) {
  if (!dom.editListaVariacoes) return;
  const custoPadrao = num(dom.editPrecoCusto.value);
  const vendaPadrao = num(dom.editPrecoVenda.value);

  const linha = document.createElement("div");
  linha.className = "linha-variacao-edit";
  if (v.id) {
    linha.dataset.variacaoId = String(v.id);
  }

  const tam = v.tamanho || "M";
  const est = num(v.estoque, 0);
  const custo = v.preco_custo !== undefined ? num(v.preco_custo) : custoPadrao;
  const venda = v.preco_venda !== undefined ? num(v.preco_venda) : vendaPadrao;
  const codigo = v.codigo_barras || "";

  linha.innerHTML = `
    <input type="text" class="inp-var-tamanho" value="${escapeHtml(tam)}" placeholder="Tam." required>
    <div class="stepper-estoque">
      <button type="button" data-step="-1" title="Diminuir 1">−</button>
      <input type="number" class="inp-var-estoque" min="0" step="1" value="${est}" required>
      <button type="button" data-step="1" title="Aumentar 1">+</button>
    </div>
    <input type="number" class="inp-var-custo" min="0" step="0.01" value="${custo.toFixed(2)}" required>
    <input type="number" class="inp-var-venda" min="0" step="0.01" value="${venda.toFixed(2)}" required>
    <input type="text" class="inp-var-codigo cod-readonly" value="${escapeHtml(codigo)}" placeholder="Auto KNB" readonly>
    <button type="button" class="btn-card-acao acao-excluir btn-remover-var" title="Remover tamanho">✕</button>
  `;

  dom.editListaVariacoes.appendChild(linha);
}

async function salvarEdicaoProduto(evento) {
  evento.preventDefault();
  const pid = Number(dom.editProdutoId.value);
  if (!pid) return;

  const modeloNome = dom.editModeloNome.value.trim();
  if (!modeloNome) {
    exibirToast("Informe o nome/modelo da peça.", "aviso");
    return;
  }

  const linhas = Array.from(dom.editListaVariacoes.querySelectorAll(".linha-variacao-edit"));
  if (!linhas.length) {
    exibirToast("O produto precisa ter ao menos um tamanho na grade.", "aviso");
    return;
  }

  const custoPadrao = num(dom.editPrecoCusto.value);
  const vendaPadrao = num(dom.editPrecoVenda.value);
  const corPrincipal = estado.coresEditando[0] || { nome: "", cor_hex: "#3b82f6" };

  const variacoesPayload = linhas.map((row) => {
    const vid = row.dataset.variacaoId ? Number(row.dataset.variacaoId) : null;
    const tam = (row.querySelector(".inp-var-tamanho")?.value || "U").trim().toUpperCase();
    const est = Math.max(0, parseInt(row.querySelector(".inp-var-estoque")?.value || "0", 10) || 0);
    const cst = num(row.querySelector(".inp-var-custo")?.value, custoPadrao);
    const vnd = num(row.querySelector(".inp-var-venda")?.value, vendaPadrao);
    const cod = (row.querySelector(".inp-var-codigo")?.value || "").trim();

    return {
      id: vid,
      tamanho: tam || "U",
      cor: corPrincipal.nome || "",
      cor_hex: corPrincipal.cor_hex || "#3b82f6",
      codigo_barras: cod,
      estoque: est,
      preco_custo: cst,
      preco_venda: vnd,
    };
  });

  const coresTags = estado.coresEditando
    .map((c) => `${c.nome}|${c.cor_hex}`)
    .join(",");

  const payload = {
    modelo_nome: modeloNome,
    marca: dom.editMarca.value.trim(),
    corte: dom.editCorte.value.trim(),
    tecido: dom.editTecido.value.trim(),
    cores_tags: coresTags,
    preco_custo: custoPadrao,
    preco_venda: vendaPadrao,
    variacoes: variacoesPayload,
  };

  dom.btnSalvarEdicao.disabled = true;
  dom.btnSalvarEdicao.textContent = "Salvando...";

  try {
    const res = await requisitarApi(`/api/produtos/${pid}`, {
      metodo: "PUT",
      corpo: payload,
    });
    fecharModal("modal-editar");
    exibirToast(res.mensagem || "Produto atualizado com sucesso!", "sucesso");
    await carregarEstoque(true);
  } catch (erro) {
    exibirToast(erro.message || "Falha ao atualizar produto.", "erro");
  } finally {
    dom.btnSalvarEdicao.disabled = false;
    dom.btnSalvarEdicao.textContent = "Salvar Alterações";
  }
}

// =========================================================================
// 10. MODAL 2: EXCLUIR PRODUTO (DELETE /api/produtos/{id})
// =========================================================================
function abrirModalExcluir(produtoId) {
  const prod = buscarProdutoEmMemoria(produtoId);
  if (!prod || !dom.modalExcluir) return;

  estado.produtoExcluindo = prod;
  const titulo = [prod.modelo_nome, prod.marca].filter(valorValido).join(" — ");
  dom.excluirNomeProduto.textContent = titulo || `Produto #${produtoId}`;

  const vars = Array.isArray(prod.variacoes) ? prod.variacoes : [];
  const totalPecas = vars.reduce((s, v) => s + num(v.estoque), 0);
  dom.excluirResumoEstoque.textContent =
    `Este modelo possui ${vars.length} tamanho(s) cadastrado(s) e ${totalPecas} unidade(s) em estoque. ` +
    `Esta ação não pode ser desfeita.`;

  dom.modalExcluir.classList.remove("hidden");
}

async function confirmarExclusaoProduto() {
  const prod = estado.produtoExcluindo;
  if (!prod) return;
  const pid = prod.id || prod.produto_id;

  dom.btnConfirmarExclusao.disabled = true;
  dom.btnConfirmarExclusao.textContent = "Excluindo...";

  try {
    const res = await requisitarApi(`/api/produtos/${pid}`, {
      metodo: "DELETE",
    });
    fecharModal("modal-excluir");
    exibirToast(res.mensagem || "Produto removido do estoque!", "sucesso");
    await carregarEstoque(true);
  } catch (erro) {
    exibirToast(erro.message || "Erro ao excluir produto.", "erro");
  } finally {
    dom.btnConfirmarExclusao.disabled = false;
    dom.btnConfirmarExclusao.textContent = "Sim, Excluir Produto";
    estado.produtoExcluindo = null;
  }
}

// =========================================================================
// 11. MODAL 3: DETALHES & CALCULADORA DE MARGEM (BOTÃO 2 DO CARD)
// =========================================================================
function abrirModalDetalhes(produtoId) {
  const prod = buscarProdutoEmMemoria(produtoId);
  if (!prod || !dom.modalDetalhes) return;

  estado.produtoDetalhes = prod;
  const grupo = obterGrupoProduto(prod.modelo_nome, prod.tipo_peca);

  if (dom.detalhesBadgeGrupo) {
    dom.detalhesBadgeGrupo.textContent = grupo.nome;
  }

  const titulo = [prod.modelo_nome, prod.marca].filter(valorValido).join(" — ");
  const sub = [prod.corte, prod.tecido].filter(valorValido).join(" | ");
  dom.detalhesSubtitulo.textContent = sub ? `${titulo}  •  ${sub}` : titulo;

  const custo = num(prod.preco_custo);
  const venda = num(prod.preco_venda);
  const lucro = venda - custo;
  const margem = venda > 0 ? (lucro / venda) * 100 : 0;

  dom.detCusto.textContent = formatarMoeda(custo);
  dom.detVenda.textContent = formatarMoeda(venda);
  dom.detLucroUn.textContent = formatarMoeda(lucro);
  dom.detMargem.textContent = `${margem.toFixed(1)}%`;

  dom.simPrecoVenda.value = venda.toFixed(2);
  dom.simDesconto.value = "0";
  atualizarSimuladorDetalhes();

  const vars = Array.isArray(prod.variacoes) ? prod.variacoes : [];
  dom.detalhesListaVariacoes.innerHTML = vars
    .map(
      (v) => `
        <div class="item-detalhe-var">
          <div>
            <strong>Tam. ${escapeHtml(v.tamanho || "U")}</strong>
            <span> (${num(v.estoque)} un.)</span>
          </div>
          <code>${escapeHtml(v.codigo_barras || "—")}</code>
        </div>
      `
    )
    .join("");

  dom.modalDetalhes.classList.remove("hidden");
}

function atualizarSimuladorDetalhes() {
  if (!estado.produtoDetalhes) return;
  const custo = num(estado.produtoDetalhes.preco_custo);
  const precoSim = num(dom.simPrecoVenda.value);
  const descontoSim = num(dom.simDesconto.value);
  const liquido = Math.max(0, precoSim - descontoSim);
  const lucro = liquido - custo;
  const margem = liquido > 0 ? (lucro / liquido) * 100 : 0;

  dom.simResultadoLucro.textContent = `${formatarMoeda(lucro)} (${margem.toFixed(1)}%)`;
  dom.simResultadoLucro.style.color = lucro >= 0 ? "#4ade80" : "#f87171";
}

function registrarEventosEstoque() {
  // Busca instantânea na Vitrine de Estoque
  if (dom.inputBuscaVitrine) {
    const aoDigitarBusca = () => {
      estado.termoBusca = dom.inputBuscaVitrine.value;
      if (dom.btnLimparBusca) {
        dom.btnLimparBusca.classList.toggle("hidden", !estado.termoBusca.trim());
      }
      window.requestAnimationFrame(renderizarVitrine);
    };
    dom.inputBuscaVitrine.addEventListener("input", aoDigitarBusca);
    dom.inputBuscaVitrine.addEventListener("search", aoDigitarBusca);
  }

  if (dom.btnLimparBusca) {
    dom.btnLimparBusca.addEventListener("click", () => {
      dom.inputBuscaVitrine.value = "";
      estado.termoBusca = "";
      dom.btnLimparBusca.classList.add("hidden");
      renderizarVitrine();
      dom.inputBuscaVitrine.focus();
    });
  }

  // Filtro por Grande Grupo Luminescente (Todos | Cima | Baixo | Calçados | Acessórios | Perfumes)
  const barraGrupos = dom.barraGruposVitrine || dom.barraGrupos;
  if (barraGrupos) {
    barraGrupos.addEventListener("click", (e) => {
      const pill = e.target.closest(".pill-grupo[data-grupo]");
      if (!pill) return;

      estado.filtroGrupo = pill.dataset.grupo;
      barraGrupos.querySelectorAll(".pill-grupo").forEach((b) => {
        b.classList.toggle("ativo", b === pill);
      });
      renderizarVitrine();
    });
  }

  // Delegação de eventos nos Cards da Vitrine de Estoque
  if (dom.gridVitrine) {
    dom.gridVitrine.addEventListener("click", (e) => {
      const btnAcao = e.target.closest("[data-acao]");
      if (!btnAcao) return;

      const acao = btnAcao.dataset.acao;
      const pid = Number(btnAcao.dataset.produtoId);

      if (acao === "vender" || acao === "vender-tamanho") {
        const card = btnAcao.closest(".card-vitrine");
        if (card) {
          card.classList.remove("card-pulso-sucesso");
          void card.offsetWidth; // Força reflow para reiniciar animação
          card.classList.add("card-pulso-sucesso");
          setTimeout(() => card.classList.remove("card-pulso-sucesso"), 650);
        }

        if (acao === "vender") {
          acionarEnviarParaVenda(pid);
        } else {
          acionarEnviarParaVenda(pid, btnAcao.dataset.tamanho);
        }
      } else if (acao === "detalhes") {
        abrirModalDetalhes(pid);
      } else if (acao === "qrcode") {
        abrirModalQrCodeProduto(pid);
      } else if (acao === "editar") {
        abrirModalEditar(pid);
      } else if (acao === "excluir") {
        abrirModalExcluir(pid);
      }
    });
  }

  // Eventos do Modal Editar Produto
  if (dom.editPrecoCusto) {
    dom.editPrecoCusto.addEventListener("input", () => {
      atualizarResumoMargemEdicao();
      const novoCusto = num(dom.editPrecoCusto.value);
      dom.editListaVariacoes.querySelectorAll(".inp-var-custo").forEach((inp) => {
        inp.value = novoCusto.toFixed(2);
      });
    });
  }

  if (dom.editPrecoVenda) {
    dom.editPrecoVenda.addEventListener("input", () => {
      atualizarResumoMargemEdicao();
      const novaVenda = num(dom.editPrecoVenda.value);
      dom.editListaVariacoes.querySelectorAll(".inp-var-venda").forEach((inp) => {
        inp.value = novaVenda.toFixed(2);
      });
    });
  }

  if (dom.btnAddCorEdit) {
    dom.btnAddCorEdit.addEventListener("click", () => {
      const nome = dom.editNovaCorNome.value.trim();
      const hex = dom.editNovaCorHex.value;
      if (!nome) {
        exibirToast("Digite o nome da cor para adicionar.", "aviso");
        dom.editNovaCorNome.focus();
        return;
      }
      const hexFinal = DICIONARIO_CORES_HEX[nome.toLowerCase()] || hex;
      estado.coresEditando.push({ nome, cor_hex: hexFinal });
      dom.editNovaCorNome.value = "";
      renderizarChipsCoresEdicao();
    });
  }

  if (dom.editListaCores) {
    dom.editListaCores.addEventListener("click", (e) => {
      const btnRem = e.target.closest("[data-remover-cor]");
      if (!btnRem) return;
      const idx = Number(btnRem.dataset.removerCor);
      estado.coresEditando.splice(idx, 1);
      renderizarChipsCoresEdicao();
    });
  }

  if (dom.btnAddTamanhoEdit) {
    dom.btnAddTamanhoEdit.addEventListener("click", () => {
      adicionarLinhaVariacaoEditor({
        id: null,
        tamanho: "",
        estoque: 1,
        preco_custo: num(dom.editPrecoCusto.value),
        preco_venda: num(dom.editPrecoVenda.value),
        codigo_barras: "",
      });
      const inputsTam = dom.editListaVariacoes.querySelectorAll(".inp-var-tamanho");
      if (inputsTam.length) {
        inputsTam[inputsTam.length - 1].focus();
      }
    });
  }

  if (dom.editListaVariacoes) {
    dom.editListaVariacoes.addEventListener("click", (e) => {
      const btnStep = e.target.closest("button[data-step]");
      if (btnStep) {
        const delta = Number(btnStep.dataset.step);
        const inp = btnStep.parentElement.querySelector(".inp-var-estoque");
        if (inp) {
          const atual = parseInt(inp.value || "0", 10) || 0;
          inp.value = String(Math.max(0, atual + delta));
        }
        return;
      }

      const btnRemVar = e.target.closest(".btn-remover-var");
      if (btnRemVar) {
        const totalLinhas = dom.editListaVariacoes.querySelectorAll(".linha-variacao-edit").length;
        if (totalLinhas <= 1) {
          exibirToast("O produto deve possuir pelo menos 1 tamanho.", "aviso");
          return;
        }
        btnRemVar.closest(".linha-variacao-edit")?.remove();
      }
    });
  }

  if (dom.formEditarProduto) {
    dom.formEditarProduto.addEventListener("submit", salvarEdicaoProduto);
  }

  // Eventos do Modal Excluir
  if (dom.btnConfirmarExclusao) {
    dom.btnConfirmarExclusao.addEventListener("click", confirmarExclusaoProduto);
  }

  // Eventos do Modal Detalhes / Simulador
  if (dom.simPrecoVenda) {
    dom.simPrecoVenda.addEventListener("input", atualizarSimuladorDetalhes);
  }
  if (dom.simDesconto) {
    dom.simDesconto.addEventListener("input", atualizarSimuladorDetalhes);
  }
  if (dom.btnDetalhesAbrirEditar) {
    dom.btnDetalhesAbrirEditar.addEventListener("click", () => {
      const prod = estado.produtoDetalhes;
      fecharModal("modal-detalhes");
      if (prod) abrirModalEditar(prod.id || prod.produto_id);
    });
  }

  // Eventos do Modal Vender Rápido
  if (dom.venderOpcoesTamanhos) {
    dom.venderOpcoesTamanhos.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-vender-pid]");
      if (!btn) return;
      const pid = Number(btn.dataset.venderPid);
      const tam = btn.dataset.venderTam;
      acionarEnviarParaVenda(pid, tam);
    });
  }

  // Eventos do Modal de Etiquetas QR Code
  registrarEventosModalQrCode();
}

// =========================================================================
// GERADOR E IMPRESSÃO DE ETIQUETAS QR CODE (KNB...)
// =========================================================================
const estadoQrCode = {
  produto: null,
  orientacao: "vertical", // vertical | horizontal
  formato: "a4_3col", // a4_3col | a4_4col | termica_1col | termica_2col
  itens: [], // [{ idx, variacao_id, tamanho, codigo_barras, estoque, preco_venda, cor, qtd_imprimir }]
};

const QR_FORMATOS_INFO = {
  a4_3col: "Folha A4 Adesiva (3 Colunas)",
  a4_4col: "Folha A4 Compacta (4 Colunas)",
  termica_1col: "Rolo Térmico (1 Coluna 50x30mm)",
  termica_2col: "Rolo Térmico (2 Colunas)",
};

function formatarRotuloTamanhoEtiqueta(tamanho) {
  const t = String(tamanho || "").trim();
  if (!t) return "TAM: UN";
  if (/ml$/i.test(t)) return t;
  return `TAM: ${t}`;
}

async function abrirModalQrCodeProduto(produtoId, quantidadesPersonalizadas = null) {
  let prod = buscarProdutoEmMemoria(produtoId);
  if (!prod) {
    await carregarEstoque(true);
    prod = buscarProdutoEmMemoria(produtoId);
  }
  if (!prod) {
    exibirToast("Produto não encontrado no estoque.", "erro");
    return;
  }

  estadoQrCode.produto = prod;
  const pid = prod.id || prod.produto_id;
  const grupo = obterGrupoProduto(prod.modelo_nome);
  const coresExtraidas = extrairCoresProduto(prod);
  const corPadrao = coresExtraidas.length ? coresExtraidas.map((c) => c.nome).join(" / ") : "";

  const vars = Array.isArray(prod.variacoes) && prod.variacoes.length
    ? prod.variacoes
    : agruparTamanhosProduto(prod);

  const somaEstoqueTotal = vars.reduce((acc, v) => acc + Math.max(0, num(v.estoque, 0)), 0);

  estadoQrCode.itens = vars.map((v, idx) => {
    const vid = v.id || v.variacao_id || idx + 1;
    const tam = normalizarTamanhoFront(v.tamanho);
    const cod =
      (v.codigo_barras || "").trim() ||
      `KNB${String(pid).padStart(5, "0")}${String(vid).padStart(4, "0")}`;
    const est = Math.max(0, num(v.estoque, 0));
    const preco = num(v.preco_venda, prod.preco_venda || 0);
    const corVar = valorValido(v.cor) ? v.cor : corPadrao;

    let qtdInicial = est;
    if (quantidadesPersonalizadas && typeof quantidadesPersonalizadas === "object") {
      if (quantidadesPersonalizadas[tam] !== undefined) {
        qtdInicial = Math.max(0, parseInt(quantidadesPersonalizadas[tam], 10) || 0);
      }
    } else if (somaEstoqueTotal === 0) {
      qtdInicial = 1;
    }

    return {
      idx,
      variacao_id: vid,
      tamanho: tam,
      codigo_barras: cod,
      estoque: est,
      preco_venda: preco,
      cor: corVar,
      qtd_imprimir: qtdInicial,
    };
  });

  const elBadge = document.getElementById("qr-modal-badge");
  const elSub = document.getElementById("qr-modal-subtitulo");
  if (elBadge) {
    elBadge.textContent = String(grupo.nome || "ETIQUETAS").toUpperCase();
    elBadge.style.borderColor = "";
    elBadge.style.color = "";
  }
  if (elSub) {
    const marcaTxt = valorValido(prod.marca) ? prod.marca : "Sem Marca";
    elSub.textContent = `${prod.modelo_nome || "Produto"} — ${marcaTxt} (ID #${pid})`;
  }

  // Sincroniza estado visual do Segmented Control
  const segContainer = document.getElementById("qr-segmented-orientacao");
  if (segContainer) {
    segContainer.querySelectorAll(".qr-seg-btn").forEach((btn) => {
      btn.classList.toggle("ativo", btn.dataset.qrOrientacao === estadoQrCode.orientacao);
    });
  }

  renderizarListaTamanhosQrCode();
  renderizarPreviewQrCode();

  const modal = document.getElementById("modal-qrcode");
  if (modal) modal.classList.remove("hidden");
}

function renderizarListaTamanhosQrCode() {
  const container = document.getElementById("qr-lista-tamanhos");
  if (!container) return;

  container.innerHTML = estadoQrCode.itens
    .map(
      (item) => `
      <div class="qr-item-tamanho-row ${item.qtd_imprimir > 0 ? "ativo" : ""}" data-qr-idx="${item.idx}">
        <div class="qr-item-info">
          <span class="qr-badge-tam">${escapeHtml(item.tamanho)}</span>
          <div class="qr-item-meta">
            <strong class="qr-item-codigo">${escapeHtml(item.codigo_barras)}</strong>
            <span class="qr-item-estoque">Estoque: ${item.estoque} un.</span>
          </div>
        </div>
        <div class="qr-item-stepper">
          <button type="button" class="qr-step-btn" data-qr-step="-1" data-qr-idx="${item.idx}" aria-label="Diminuir">−</button>
          <input
            type="number"
            class="qr-input-qtd"
            data-qr-idx="${item.idx}"
            min="0"
            max="500"
            value="${item.qtd_imprimir}"
          >
          <button type="button" class="qr-step-btn" data-qr-step="1" data-qr-idx="${item.idx}" aria-label="Aumentar">+</button>
        </div>
      </div>
    `
    )
    .join("");
}

function gerarHtmlCardEtiquetaQr(prod, item, orientacao = "vertical") {
  const modelo = prod.modelo_nome || "Peça Kanemberg";
  const marca = valorValido(prod.marca) ? prod.marca : "Kanemberg";
  const cor = valorValido(item.cor) ? item.cor : "";
  const rotuloTam = formatarRotuloTamanhoEtiqueta(item.tamanho);
  const precoFormatado = formatarMoeda(item.preco_venda);
  const urlQr = `/api/qrcode/svg/${encodeURIComponent(item.codigo_barras)}`;

  if (orientacao === "vertical") {
    return `
      <div class="etiqueta-qr-card orientacao-vertical">
        <div class="etq-v-topo">
          <strong class="etq-v-brand">KANEMBERG</strong>
          <span class="etq-v-sub">MULTIMARCAS</span>
        </div>
        <div class="etq-v-identificacao">
          <div class="etq-v-modelo-marca">${escapeHtml(modelo)} — ${escapeHtml(marca)}</div>
          ${cor ? `<div class="etq-v-cor">${escapeHtml(cor)}</div>` : ""}
        </div>
        <div class="etq-v-centro">
          <img
            src="${urlQr}"
            alt="QR ${escapeHtml(item.codigo_barras)}"
            class="etq-qr-img"
          >
          <span class="etq-codigo-knb">${escapeHtml(item.codigo_barras)}</span>
        </div>
        <div class="etq-v-rodape">
          <span class="etq-box-tamanho">${escapeHtml(rotuloTam)}</span>
          <span class="etq-preco">${precoFormatado}</span>
        </div>
      </div>
    `;
  }

  return `
    <div class="etiqueta-qr-card orientacao-horizontal">
      <div class="etq-topo">KANEMBERG MULTIMARCAS</div>
      <div class="etq-corpo">
        <div class="etq-col-qr">
          <img
            src="${urlQr}"
            alt="QR ${escapeHtml(item.codigo_barras)}"
            class="etq-qr-img"
          >
          <span class="etq-codigo-knb">${escapeHtml(item.codigo_barras)}</span>
        </div>
        <div class="etq-col-dados">
          <div class="etq-modelo">${escapeHtml(modelo)} — ${escapeHtml(marca)}</div>
          ${cor ? `<div class="etq-marca-cor">${escapeHtml(cor)}</div>` : ""}
          <div class="etq-rodape-dados">
            <span class="etq-box-tamanho">${escapeHtml(rotuloTam)}</span>
            <span class="etq-preco">${precoFormatado}</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderizarPreviewQrCode() {
  const palco = document.getElementById("qr-preview-palco");
  const contador = document.getElementById("qr-contador-total");
  const infoPapel = document.getElementById("qr-preview-info-papel");
  const btnPrint = document.getElementById("qr-btn-imprimir-agora");
  if (!palco || !estadoQrCode.produto) return;

  const orientacao = estadoQrCode.orientacao || "vertical";
  palco.className = `qr-preview-palco formato-${estadoQrCode.formato} orientacao-${orientacao}`;

  if (infoPapel) {
    const labelOrientacao = orientacao === "vertical" ? "Vertical (Tag / Roupa)" : "Horizontal (Calçado / Caixa)";
    const labelPapel = QR_FORMATOS_INFO[estadoQrCode.formato] || "Folha A4";
    infoPapel.textContent = `${labelOrientacao} • ${labelPapel}`;
  }

  const totalEtiquetas = estadoQrCode.itens.reduce((acc, it) => acc + Math.max(0, it.qtd_imprimir), 0);
  if (contador) {
    contador.textContent = `Total: ${totalEtiquetas} etiqueta(s) selecionada(s)`;
  }
  if (btnPrint) {
    btnPrint.disabled = totalEtiquetas <= 0;
  }

  if (totalEtiquetas <= 0) {
    palco.innerHTML = `
      <div class="qr-preview-vazio">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="3" width="7" height="7"></rect>
          <rect x="14" y="3" width="7" height="7"></rect>
          <rect x="14" y="14" width="7" height="7"></rect>
          <rect x="3" y="14" width="7" height="7"></rect>
        </svg>
        <strong>Nenhuma etiqueta selecionada</strong>
        <p>Ajuste a quantidade em pelo menos um tamanho ao lado ou acione "Igualar ao Estoque".</p>
      </div>
    `;
    return;
  }

  const cards = [];
  const limitePreview = 60;
  for (const item of estadoQrCode.itens) {
    const qtd = Math.max(0, item.qtd_imprimir);
    for (let i = 0; i < qtd; i++) {
      if (cards.length < limitePreview) {
        cards.push(gerarHtmlCardEtiquetaQr(estadoQrCode.produto, item, orientacao));
      }
    }
  }

  palco.innerHTML = cards.join("");
}

async function imprimirEtiquetasQrCodeAgora() {
  if (!estadoQrCode.produto) return;
  const totalEtiquetas = estadoQrCode.itens.reduce((acc, it) => acc + Math.max(0, it.qtd_imprimir), 0);
  if (totalEtiquetas <= 0) {
    exibirToast("Selecione pelo menos 1 etiqueta para imprimir.", "aviso");
    return;
  }

  const areaPrint = document.getElementById("area-impressao-qrcode");
  if (!areaPrint) return;

  const orientacao = estadoQrCode.orientacao || "vertical";
  const todosCards = [];
  for (const item of estadoQrCode.itens) {
    const qtd = Math.max(0, item.qtd_imprimir);
    for (let i = 0; i < qtd; i++) {
      todosCards.push(gerarHtmlCardEtiquetaQr(estadoQrCode.produto, item, orientacao));
    }
  }

  areaPrint.innerHTML = `
    <div class="folha-impressao-qr formato-${estadoQrCode.formato} orientacao-${orientacao}">
      ${todosCards.join("")}
    </div>
  `;

  // Aguarda carregamento das imagens SVG do QR Code antes de abrir a janela nativa de impressão
  const imgs = Array.from(areaPrint.querySelectorAll("img"));
  await Promise.race([
    Promise.all(
      imgs.map(
        (img) =>
          new Promise((resolve) => {
            if (img.complete) return resolve();
            img.addEventListener("load", resolve, { once: true });
            img.addEventListener("error", resolve, { once: true });
          })
      )
    ),
    new Promise((resolve) => setTimeout(resolve, 450)),
  ]);

  window.print();
}

function registrarEventosModalQrCode() {
  const segOrientacao = document.getElementById("qr-segmented-orientacao");
  const selFormato = document.getElementById("qr-select-formato");
  const btnIgualar = document.getElementById("qr-btn-igualar-estoque");
  const btnUmCada = document.getElementById("qr-btn-um-cada");
  const btnZerar = document.getElementById("qr-btn-zerar-tudo");
  const listaTam = document.getElementById("qr-lista-tamanhos");
  const btnImprimir = document.getElementById("qr-btn-imprimir-agora");

  segOrientacao?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-qr-orientacao]");
    if (!btn) return;
    const novaOrientacao = btn.dataset.qrOrientacao;
    if (!novaOrientacao) return;
    estadoQrCode.orientacao = novaOrientacao;
    segOrientacao.querySelectorAll(".qr-seg-btn").forEach((b) => {
      b.classList.toggle("ativo", b.dataset.qrOrientacao === novaOrientacao);
    });
    renderizarPreviewQrCode();
  });

  selFormato?.addEventListener("change", (e) => {
    estadoQrCode.formato = e.target.value;
    renderizarPreviewQrCode();
  });

  btnIgualar?.addEventListener("click", () => {
    estadoQrCode.itens.forEach((it) => {
      it.qtd_imprimir = Math.max(0, it.estoque);
    });
    renderizarListaTamanhosQrCode();
    renderizarPreviewQrCode();
  });

  btnUmCada?.addEventListener("click", () => {
    estadoQrCode.itens.forEach((it) => {
      it.qtd_imprimir = 1;
    });
    renderizarListaTamanhosQrCode();
    renderizarPreviewQrCode();
  });

  btnZerar?.addEventListener("click", () => {
    estadoQrCode.itens.forEach((it) => {
      it.qtd_imprimir = 0;
    });
    renderizarListaTamanhosQrCode();
    renderizarPreviewQrCode();
  });

  listaTam?.addEventListener("click", (e) => {
    const btnStep = e.target.closest("[data-qr-step]");
    if (!btnStep) return;
    const idx = Number(btnStep.dataset.qrIdx);
    const delta = Number(btnStep.dataset.qrStep);
    const item = estadoQrCode.itens[idx];
    if (!item) return;
    item.qtd_imprimir = Math.max(0, Math.min(500, item.qtd_imprimir + delta));
    const row = btnStep.closest(".qr-item-tamanho-row");
    if (row) row.classList.toggle("ativo", item.qtd_imprimir > 0);
    const inp = listaTam.querySelector(`.qr-input-qtd[data-qr-idx="${idx}"]`);
    if (inp) inp.value = String(item.qtd_imprimir);
    renderizarPreviewQrCode();
  });

  listaTam?.addEventListener("input", (e) => {
    const inp = e.target.closest(".qr-input-qtd");
    if (!inp) return;
    const idx = Number(inp.dataset.qrIdx);
    const item = estadoQrCode.itens[idx];
    if (!item) return;
    item.qtd_imprimir = Math.max(0, Math.min(500, parseInt(inp.value || "0", 10) || 0));
    const row = inp.closest(".qr-item-tamanho-row");
    if (row) row.classList.toggle("ativo", item.qtd_imprimir > 0);
    renderizarPreviewQrCode();
  });

  btnImprimir?.addEventListener("click", imprimirEtiquetasQrCodeAgora);
}

window.abrirModalQrCodeProduto = abrirModalQrCodeProduto;
window.abrirModalEditar = abrirModalEditar;

KanembergApp.eventos.push(registrarEventosEstoque);
KanembergApp.inicializadores.push(() => carregarEstoque(false));
