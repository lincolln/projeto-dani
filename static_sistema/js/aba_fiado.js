/**
 * js/aba_fiado.js — Kanemberg Sistema Desktop (módulo carregado via <script defer>).
 * Aba 4 (Fiado): KPIs, lista de clientes com barra de limite, ficha + extrato,
 * receber/abater pagamento, débito avulso, cadastro/edição de cliente e cobrança WhatsApp.
 * Rotas: GET /api/clientes, GET /api/fiado/resumo, GET /api/fiado/clientes/{id}/extrato,
 * POST /api/clientes, PUT /api/clientes/{id}, POST /api/fiado/pagar, POST /api/fiado/debito.
 */

const estadoFiado = {
  clientes: [],
  resumo: null,
  filtro: "todos", // todos | divida | estourado | quitado
  termo: "",
  selecionadoId: null,
  extrato: [],
  formaPgto: "PIX",
  salvando: false,
};

function fiEl(id) {
  return document.getElementById(id);
}

function fiNormalizar(txt) {
  return String(txt || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function fiStatusCliente(c) {
  const saldo = num(c.saldo_devedor, 0);
  const limite = num(c.limite_credito, 0);
  if (saldo <= 0.009) return "em-dia";
  return saldo >= limite ? "estourado" : "devedor";
}

function fiFormatarData(raw) {
  const s = String(raw || "");
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/);
  if (m) {
    return `${m[3]}/${m[2]}/${m[1]}${m[4] ? ` ${m[4]}:${m[5]}` : ""}`;
  }
  return s || "—";
}

function fiClienteSelecionado() {
  return estadoFiado.clientes.find((c) => Number(c.id) === Number(estadoFiado.selecionadoId)) || null;
}

// ---------------------------------------------------------------------------
// Carga de dados
// ---------------------------------------------------------------------------
async function carregarFiado(silencioso = false) {
  console.log("[Fiado] carregarFiado chamado. Silencioso:", silencioso);
  const lista = fiEl("fi-lista");
  try {
    const [resClientes, resResumo] = await Promise.all([
      requisitarApi("/api/clientes"),
      requisitarApi("/api/fiado/resumo"),
    ]);

    console.log("[Fiado] Respostas da API recebidas com sucesso:", {
      totalClientes: resClientes?.clientes?.length ?? 0,
      resumo: resResumo,
    });

    estadoFiado.clientes = Array.isArray(resClientes?.clientes) ? resClientes.clientes : [];
    estadoFiado.resumo = resResumo || null;

    renderizarKpisFiado();
    renderizarListaFiado();

    if (estadoFiado.selecionadoId) {
      const existe = fiClienteSelecionado();
      if (existe) {
        renderizarFichaFiado();
      } else {
        estadoFiado.selecionadoId = null;
        renderizarFichaFiado();
      }
    }
  } catch (erro) {
    console.error("[Fiado] Erro ao carregar dados do fiado:", erro);
    if (!silencioso) {
      exibirToast(erro.message || "Erro ao carregar o fiado.", "erro");
    }
    if (lista) {
      lista.innerHTML = `
        <div class="estado-vazio" style="padding: 24px 16px; text-align: center;">
          <p style="color: #ef4444; font-weight: 700; margin-bottom: 8px;">
            Erro ao carregar clientes: ${escapeHtml(erro.message || String(erro))}
          </p>
          <p style="color: var(--fg-muted, #94a3b8); font-size: 12px; margin-bottom: 12px;">
            Verifique se o servidor FastAPI está ativo na porta 8000.
          </p>
          <button type="button" class="btn-secundario-sistema" onclick="carregarFiado(false)" style="margin: 0 auto; cursor: pointer;">
            Tentar Novamente
          </button>
        </div>
      `;
    }
  }
}

// Atualiza o cache do seletor Fiado da aba Nova Venda
function fiSincronizarPdv() {
  if (typeof carregarClientesPDV === "function") {
    carregarClientesPDV(true);
  }
}

async function fiCarregarExtrato(clienteId) {
  try {
    const res = await requisitarApi(`/api/fiado/clientes/${clienteId}/extrato`);
    estadoFiado.extrato = Array.isArray(res.movimentacoes) ? res.movimentacoes : [];
  } catch (erro) {
    estadoFiado.extrato = [];
    exibirToast(erro.message || "Erro ao carregar o extrato.", "erro");
  }
  renderizarExtratoFiado();
}

// ---------------------------------------------------------------------------
// Renderização
// ---------------------------------------------------------------------------
function renderizarKpisFiado() {
  try {
    const r = estadoFiado.resumo;
    if (!r) return;
    const elRec = fiEl("fi-kpi-receber");
    const elDev = fiEl("fi-kpi-devedores");
    const elEst = fiEl("fi-kpi-estourados");
    const elRec30 = fiEl("fi-kpi-recebido");

    if (elRec) elRec.textContent = formatarMoeda(r.total_a_receber);
    if (elDev) elDev.textContent = `${num(r.clientes_com_divida)} de ${num(r.total_clientes)}`;
    if (elEst) elEst.textContent = String(num(r.clientes_estourados));
    if (elRec30) elRec30.textContent = formatarMoeda(r.recebido_30_dias);
  } catch (err) {
    console.error("[Fiado] Erro ao renderizar KPIs:", err);
  }
}

function fiClassePercentual(pct) {
  if (pct >= 100) return "vermelha";
  if (pct > 60) return "amarela";
  return "";
}

function fiFiltrarClientes() {
  const termo = fiNormalizar(estadoFiado.termo).trim();
  const termoDigitos = termo.replace(/\D/g, "");
  return estadoFiado.clientes.filter((c) => {
    const st = fiStatusCliente(c);
    if (estadoFiado.filtro === "divida" && st === "em-dia") return false;
    if (estadoFiado.filtro === "estourado" && st !== "estourado") return false;
    if (estadoFiado.filtro === "quitado" && st !== "em-dia") return false;
    if (!termo) return true;
    if (fiNormalizar(c.nome).includes(termo)) return true;
    const telDigitos = String(c.telefone || "").replace(/\D/g, "");
    return termoDigitos.length > 0 && telDigitos.includes(termoDigitos);
  });
}

function renderizarListaFiado() {
  const lista = fiEl("fi-lista");
  if (!lista) return;

  // Se nenhum cliente cadastrado no banco:
  if (!estadoFiado.clientes || estadoFiado.clientes.length === 0) {
    lista.innerHTML = `
      <div class="estado-vazio" style="padding: 28px 14px; text-align: center;">
        <p style="font-size: 13.5px; color: var(--fg-secondary, #cbd5e1); margin-bottom: 12px;">
          Nenhum cliente cadastrado ainda. Clique em <strong>'+ Novo Cliente'</strong> no topo para começar.
        </p>
        <button type="button" class="btn-cadastrar-peca" onclick="abrirModalClienteFiado(null)" style="margin: 0 auto; font-size: 12.5px; padding: 6px 14px;">
          + Novo Cliente
        </button>
      </div>
    `;
    return;
  }

  const filtrados = fiFiltrarClientes();

  // Se nenhum cliente bater com o filtro selecionado / termo de busca:
  if (!filtrados.length) {
    lista.innerHTML = `<div class="estado-vazio"><p>Nenhum cliente encontrado para este filtro.</p></div>`;
    return;
  }

  const rotulos = { "em-dia": "Em dia", devedor: "Devedor", estourado: "Limite Excedido" };

  lista.innerHTML = filtrados
    .map((c) => {
      const st = fiStatusCliente(c);
      const saldo = Math.max(0, num(c.saldo_devedor, 0));
      const limite = num(c.limite_credito, 0);
      const pct = limite > 0 ? (saldo / limite) * 100 : saldo > 0 ? 100 : 0;
      const sel = Number(c.id) === Number(estadoFiado.selecionadoId) ? "selecionado" : "";
      const classeBadge = st === "em-dia" ? "em-dia" : st;
      return `
        <button type="button" class="fi-card-cliente ${sel}" data-fi-id="${c.id}">
          <div class="fi-card-topo">
            <div>
              <div class="fi-card-nome">${escapeHtml(c.nome)}</div>
              <div class="fi-card-tel">${escapeHtml(c.telefone || "Sem telefone")}</div>
            </div>
            <span class="fi-badge ${classeBadge}">${rotulos[st]}</span>
          </div>
          <div class="fi-limite-texto">Deve ${formatarMoeda(saldo)} / Limite ${formatarMoeda(limite)}</div>
          <div class="fi-barra">
            <div class="fi-barra-fill ${fiClassePercentual(pct)}" style="width:${Math.min(100, pct).toFixed(1)}%"></div>
          </div>
        </button>
      `;
    })
    .join("");
}

function renderizarFichaFiado() {
  const c = fiClienteSelecionado();
  const vazia = fiEl("fi-ficha-vazia");
  const ficha = fiEl("fi-ficha");
  if (!c) {
    vazia.classList.remove("hidden");
    ficha.classList.add("hidden");
    return;
  }
  vazia.classList.add("hidden");
  ficha.classList.remove("hidden");

  const saldo = Math.max(0, num(c.saldo_devedor, 0));
  const limite = num(c.limite_credito, 0);
  const disponivel = Math.max(0, limite - saldo);
  const pct = limite > 0 ? (saldo / limite) * 100 : saldo > 0 ? 100 : 0;

  fiEl("fi-nome").textContent = c.nome;
  fiEl("fi-tel").textContent = c.telefone ? `Tel: ${c.telefone}` : "Sem telefone cadastrado";
  fiEl("fi-info-extra").textContent = `Dia preferencial de pagamento: ${c.dia_preferencial_pagamento || "—"}`;
  fiEl("fi-saldo").textContent = formatarMoeda(saldo);
  fiEl("fi-disponivel").textContent = formatarMoeda(disponivel);
  fiEl("fi-limite-total").textContent = formatarMoeda(limite);

  const fill = fiEl("fi-barra-fill");
  fill.style.width = `${Math.min(100, pct).toFixed(1)}%`;
  fill.className = `fi-barra-fill ${fiClassePercentual(pct)}`;

  fiEl("fi-btn-receber").disabled = saldo <= 0.009;
  fiEl("fi-btn-receber").style.opacity = saldo <= 0.009 ? "0.5" : "1";
}

function renderizarExtratoFiado() {
  const box = fiEl("fi-extrato");
  if (!box) return;
  if (!estadoFiado.extrato.length) {
    box.innerHTML = `<div class="estado-vazio"><p>Nenhuma movimentação registrada para este cliente.</p></div>`;
    return;
  }
  box.innerHTML = estadoFiado.extrato
    .map((m) => {
      const debito = String(m.tipo_movimentacao).toUpperCase() === "DEBITO";
      const venc = debito && m.data_vencimento_lote ? ` • Venc.: ${fiFormatarData(m.data_vencimento_lote).slice(0, 10)}` : "";
      return `
        <div class="fi-mov ${debito ? "debito" : "credito"}">
          <div class="fi-mov-info">
            <span class="fi-mov-desc">${escapeHtml(m.descricao || (debito ? "Compra no fiado" : "Pagamento"))}</span>
            <span class="fi-mov-data">${fiFormatarData(m.data_movimentacao)}${venc}</span>
          </div>
          <span class="fi-mov-valor">${debito ? "+" : "−"} ${formatarMoeda(m.valor)}</span>
        </div>
      `;
    })
    .join("");
}

async function selecionarClienteFiado(id) {
  estadoFiado.selecionadoId = Number(id);
  renderizarListaFiado();
  renderizarFichaFiado();
  estadoFiado.extrato = [];
  fiEl("fi-extrato").innerHTML = `<div class="estado-vazio"><p>Carregando extrato...</p></div>`;
  await fiCarregarExtrato(id);
}

// ---------------------------------------------------------------------------
// Modais: cliente (novo/editar)
// ---------------------------------------------------------------------------
function abrirModalClienteFiado(cliente = null) {
  fiEl("fi-cli-id").value = cliente ? cliente.id : "";
  fiEl("fi-cli-titulo").textContent = cliente ? "Editar Cliente / Limite" : "Novo Cliente";
  fiEl("fi-cli-nome").value = cliente ? cliente.nome : "";
  fiEl("fi-cli-telefone").value = cliente ? cliente.telefone || "" : "";
  fiEl("fi-cli-limite").value = cliente ? num(cliente.limite_credito, 500) : 500;
  fiEl("fi-cli-dia").value = cliente ? cliente.dia_preferencial_pagamento || 5 : 5;
  fiEl("modal-fiado-cliente").classList.remove("hidden");
  setTimeout(() => fiEl("fi-cli-nome").focus(), 50);
}

async function salvarClienteFiado(evento) {
  evento.preventDefault();
  if (estadoFiado.salvando) return;
  const id = fiEl("fi-cli-id").value;
  const corpo = {
    nome: fiEl("fi-cli-nome").value.trim(),
    telefone: fiEl("fi-cli-telefone").value.trim(),
    limite_credito: num(fiEl("fi-cli-limite").value, 0),
    dia_preferencial_pagamento: parseInt(fiEl("fi-cli-dia").value || "5", 10) || 5,
  };
  if (!corpo.nome) {
    exibirToast("Informe o nome do cliente.", "aviso");
    return;
  }

  estadoFiado.salvando = true;
  const btn = fiEl("fi-btn-salvar-cliente");
  btn.disabled = true;
  try {
    const res = id
      ? await requisitarApi(`/api/clientes/${id}`, { metodo: "PUT", corpo })
      : await requisitarApi("/api/clientes", { metodo: "POST", corpo });
    fecharModal("modal-fiado-cliente");
    exibirToast(res.mensagem || "Cliente salvo com sucesso!", "sucesso");
    if (!id && res.cliente_id) {
      estadoFiado.selecionadoId = Number(res.cliente_id);
    }
    await carregarFiado(true);
    if (estadoFiado.selecionadoId) {
      await fiCarregarExtrato(estadoFiado.selecionadoId);
    }
    fiSincronizarPdv();
  } catch (erro) {
    exibirToast(erro.message || "Não foi possível salvar o cliente.", "erro");
  } finally {
    estadoFiado.salvando = false;
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Modais: pagamento / abatimento
// ---------------------------------------------------------------------------
function abrirModalPagamentoFiado() {
  const c = fiClienteSelecionado();
  if (!c) return;
  const saldo = Math.max(0, num(c.saldo_devedor, 0));
  if (saldo <= 0.009) {
    exibirToast("Este cliente não possui dívida em aberto.", "info");
    return;
  }
  fiEl("fi-pgto-resumo").textContent = `${c.nome} — Saldo devedor atual: ${formatarMoeda(saldo)}`;
  fiEl("fi-pgto-valor").value = saldo.toFixed(2);
  fiEl("fi-pgto-valor").max = saldo.toFixed(2);
  fiEl("fi-pgto-obs").value = "";
  definirFormaPagamentoFiado("PIX");
  fiEl("modal-fiado-pagamento").classList.remove("hidden");
  setTimeout(() => {
    fiEl("fi-pgto-valor").focus();
    fiEl("fi-pgto-valor").select();
  }, 50);
}

function definirFormaPagamentoFiado(forma) {
  estadoFiado.formaPgto = forma;
  fiEl("fi-pgto-formas")
    .querySelectorAll(".fi-forma")
    .forEach((b) => b.classList.toggle("ativo", b.dataset.fiForma === forma));
}

async function confirmarPagamentoFiado(evento) {
  evento.preventDefault();
  if (estadoFiado.salvando) return;
  const c = fiClienteSelecionado();
  if (!c) return;
  const saldo = Math.max(0, num(c.saldo_devedor, 0));
  let valor = num(fiEl("fi-pgto-valor").value, 0);
  if (valor <= 0) {
    exibirToast("Informe um valor maior que zero.", "aviso");
    return;
  }
  if (valor > saldo + 0.009) {
    valor = saldo;
    exibirToast(`Valor limitado ao saldo devedor (${formatarMoeda(saldo)}).`, "aviso");
  }
  const obs = fiEl("fi-pgto-obs").value.trim();
  const descricao = `Pagamento (${estadoFiado.formaPgto})${obs ? ` — ${obs}` : ""}`;

  estadoFiado.salvando = true;
  const btn = fiEl("fi-btn-confirmar-pgto");
  btn.disabled = true;
  try {
    const res = await requisitarApi("/api/fiado/pagar", {
      metodo: "POST",
      corpo: { cliente_id: c.id, valor: Number(valor.toFixed(2)), descricao },
    });
    fecharModal("modal-fiado-pagamento");
    exibirToast(res.mensagem || "Pagamento registrado!", "sucesso");
    await carregarFiado(true);
    await fiCarregarExtrato(c.id);
    fiSincronizarPdv();
  } catch (erro) {
    exibirToast(erro.message || "Não foi possível registrar o pagamento.", "erro");
  } finally {
    estadoFiado.salvando = false;
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Modais: débito avulso
// ---------------------------------------------------------------------------
function abrirModalDebitoFiado() {
  const c = fiClienteSelecionado();
  if (!c) return;
  const saldo = Math.max(0, num(c.saldo_devedor, 0));
  const disp = Math.max(0, num(c.limite_credito, 0) - saldo);
  fiEl("fi-deb-resumo").textContent = `${c.nome} — Saldo: ${formatarMoeda(saldo)} • Disponível: ${formatarMoeda(disp)}`;
  fiEl("fi-deb-valor").value = "";
  fiEl("fi-deb-desc").value = "";
  const venc = new Date();
  venc.setDate(venc.getDate() + 30);
  fiEl("fi-deb-venc").value = `${venc.getFullYear()}-${String(venc.getMonth() + 1).padStart(2, "0")}-${String(venc.getDate()).padStart(2, "0")}`;
  fiEl("modal-fiado-debito").classList.remove("hidden");
  setTimeout(() => fiEl("fi-deb-valor").focus(), 50);
}

async function confirmarDebitoFiado(evento) {
  evento.preventDefault();
  if (estadoFiado.salvando) return;
  const c = fiClienteSelecionado();
  if (!c) return;
  const valor = num(fiEl("fi-deb-valor").value, 0);
  const descricao = fiEl("fi-deb-desc").value.trim();
  if (valor <= 0 || !descricao) {
    exibirToast("Informe valor e descrição do débito.", "aviso");
    return;
  }
  const saldo = Math.max(0, num(c.saldo_devedor, 0));
  const limite = num(c.limite_credito, 0);
  if (saldo + valor > limite && limite > 0) {
    exibirToast("Atenção: este débito ultrapassa o limite de crédito do cliente.", "aviso", 4200);
  }

  estadoFiado.salvando = true;
  const btn = fiEl("fi-btn-confirmar-deb");
  btn.disabled = true;
  try {
    const res = await requisitarApi("/api/fiado/debito", {
      metodo: "POST",
      corpo: {
        cliente_id: c.id,
        valor: Number(valor.toFixed(2)),
        descricao: `Débito avulso: ${descricao}`,
        data_vencimento_lote: fiEl("fi-deb-venc").value || "",
      },
    });
    fecharModal("modal-fiado-debito");
    exibirToast(res.mensagem || "Débito lançado!", "sucesso");
    await carregarFiado(true);
    await fiCarregarExtrato(c.id);
    fiSincronizarPdv();
  } catch (erro) {
    exibirToast(erro.message || "Não foi possível lançar o débito.", "erro");
  } finally {
    estadoFiado.salvando = false;
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Cobrança via WhatsApp (copia texto para a área de transferência)
// ---------------------------------------------------------------------------
async function copiarCobrancaWhatsApp() {
  const c = fiClienteSelecionado();
  if (!c) return;
  const saldo = Math.max(0, num(c.saldo_devedor, 0));
  const primeiroNome = String(c.nome || "").trim().split(/\s+/)[0] || "cliente";

  let msg;
  if (saldo <= 0.009) {
    msg =
      `Olá ${primeiroNome}, tudo bem? Passando para informar que sua conta na Kanemberg Multimarcas ` +
      `está em dia, sem pendências. Obrigado pela confiança!`;
  } else {
    const ultimas = estadoFiado.extrato
      .filter((m) => String(m.tipo_movimentacao).toUpperCase() === "DEBITO")
      .slice(0, 3)
      .map((m) => `• ${fiFormatarData(m.data_movimentacao).slice(0, 10)} — ${m.descricao || "Compra"} (${formatarMoeda(m.valor)})`);
    msg =
      `Olá ${primeiroNome}, tudo bem? Passando para enviar o resumo atualizado da sua conta na Kanemberg Multimarcas:\n\n` +
      `Saldo atual: ${formatarMoeda(saldo)}\n` +
      (ultimas.length ? `\nÚltimas compras:\n${ultimas.join("\n")}\n` : "") +
      `\nQuando puder, me avise a melhor forma de acerto (PIX, dinheiro ou cartão). Qualquer dúvida, estou à disposição!`;
  }

  try {
    await navigator.clipboard.writeText(msg);
  } catch (_e) {
    const ta = document.createElement("textarea");
    ta.value = msg;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (_e2) {
      // sem suporte
    }
    ta.remove();
  }
  exibirToast("Cobrança copiada! Cole no WhatsApp do cliente.", "sucesso");
}

// ---------------------------------------------------------------------------
// Eventos
// ---------------------------------------------------------------------------
function registrarEventosFiado() {
  fiEl("fi-btn-novo-cliente")?.addEventListener("click", () => abrirModalClienteFiado(null));
  fiEl("fi-btn-editar")?.addEventListener("click", () => {
    const c = fiClienteSelecionado();
    if (c) abrirModalClienteFiado(c);
  });
  fiEl("fi-btn-receber")?.addEventListener("click", abrirModalPagamentoFiado);
  fiEl("fi-btn-debito")?.addEventListener("click", abrirModalDebitoFiado);
  fiEl("fi-btn-whats")?.addEventListener("click", copiarCobrancaWhatsApp);

  const inputBusca = fiEl("fi-busca");
  const btnLimpar = fiEl("fi-btn-limpar-busca");

  inputBusca?.addEventListener("input", (e) => {
    estadoFiado.termo = e.target.value;
    if (btnLimpar) {
      btnLimpar.classList.toggle("hidden", !e.target.value);
    }
    renderizarListaFiado();
  });

  btnLimpar?.addEventListener("click", () => {
    if (inputBusca) {
      inputBusca.value = "";
      estadoFiado.termo = "";
      btnLimpar.classList.add("hidden");
      renderizarListaFiado();
      inputBusca.focus();
    }
  });

  fiEl("fi-pills")?.addEventListener("click", (e) => {
    const pill = e.target.closest("[data-fi-filtro]");
    if (!pill) return;
    estadoFiado.filtro = pill.dataset.fiFiltro;
    fiEl("fi-pills")
      .querySelectorAll(".fi-pill, .pill-grupo")
      .forEach((b) => b.classList.toggle("ativo", b === pill));
    renderizarListaFiado();
  });

  fiEl("fi-lista")?.addEventListener("click", (e) => {
    const card = e.target.closest("[data-fi-id]");
    if (card) selecionarClienteFiado(card.dataset.fiId);
  });

  fiEl("fi-form-cliente")?.addEventListener("submit", salvarClienteFiado);
  fiEl("fi-form-pagamento")?.addEventListener("submit", confirmarPagamentoFiado);
  fiEl("fi-form-debito")?.addEventListener("submit", confirmarDebitoFiado);

  fiEl("fi-pgto-formas")?.addEventListener("click", (e) => {
    const b = e.target.closest("[data-fi-forma]");
    if (b) definirFormaPagamentoFiado(b.dataset.fiForma);
  });

  document.querySelectorAll("[data-fi-pgto-atalho]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const c = fiClienteSelecionado();
      if (!c) return;
      const saldo = Math.max(0, num(c.saldo_devedor, 0));
      const v = btn.dataset.fiPgtoAtalho === "total" ? saldo : saldo / 2;
      const elValor = fiEl("fi-pgto-valor");
      if (elValor) elValor.value = v.toFixed(2);
    });
  });
}

// Exposição global
window.carregarFiado = carregarFiado;
window.abrirModalClienteFiado = abrirModalClienteFiado;
window.selecionarClienteFiado = selecionarClienteFiado;

KanembergApp.eventos.push(registrarEventosFiado);
KanembergApp.inicializadores.push(() => carregarFiado(true));
