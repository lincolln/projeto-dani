/* =========================================================
   KANEMBERG MOBILE — conexao_dinamica.js
   Descoberta automática do servidor ativo + API_BASE dinâmica.

   O app instalado continua na MESMA origem (tela cheia, sem barra
   do Chrome). Quando o túnel Cloudflare muda, apenas as chamadas
   fetch("/api/...") são redirecionadas para o novo endereço
   (window.KANEMBERG_API_BASE), sem alterar window.location.

   Carregar ANTES do app.js (sem defer).
   ========================================================= */

(function () {
  "use strict";

  const STORAGE_BASE = "kanemberg_api_base";
  const STORAGE_IP = "kanemberg_last_local_ip";
  const STORAGE_TUNNEL = "kanemberg_last_tunnel_url";

  const FONTES_PORTEIRO = [
    "https://raw.githubusercontent.com/lincolln/projeto-dani/main/docs/tunnel_status.json",
    "https://lincolln.github.io/projeto-dani/tunnel_status.json",
  ];
  const ROTA_SONDA = "/api/sistema/tunnel-status";
  const TIMEOUT_SONDA_MS = 3500;
  const TIMEOUT_PORTEIRO_MS = 4500;
  // Status que indicam túnel morto / origem inalcançável (530 = erro 1033 Cloudflare)
  const STATUS_TUNEL_MORTO = [502, 503, 504, 521, 522, 523, 524, 530];

  const fetchNativo = window.fetch.bind(window);
  const ORIGEM_ATUAL = window.location.origin.replace(/\/+$/, "");

  function normalizarBase(valor) {
    if (!valor) return "";
    try {
      const u = new URL(String(valor).trim());
      if (u.protocol !== "http:" && u.protocol !== "https:") return "";
      return u.origin.replace(/\/+$/, "");
    } catch (_e) {
      return "";
    }
  }

  let baseAtual = normalizarBase(localStorage.getItem(STORAGE_BASE)) || ORIGEM_ATUAL;
  window.KANEMBERG_API_BASE = baseAtual;

  function definirBase(novaBase, info) {
    const b = normalizarBase(novaBase);
    if (!b) return false;
    baseAtual = b;
    window.KANEMBERG_API_BASE = b;
    localStorage.setItem(STORAGE_BASE, b);
    if (b.includes("trycloudflare.com")) localStorage.setItem(STORAGE_TUNNEL, b);
    if (info && info.ip_local) {
      const ip = normalizarBase(info.ip_local);
      if (ip) localStorage.setItem(STORAGE_IP, ip);
    }
    if (info && info.url_ativa) {
      const t = normalizarBase(info.url_ativa);
      if (t) localStorage.setItem(STORAGE_TUNNEL, t);
    }
    atualizarStatusUi();
    window.dispatchEvent(new CustomEvent("kanemberg:servidor-alterado", { detail: { base: b } }));
    return true;
  }

  function fetchComTimeout(url, ms, opcoes) {
    const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = setTimeout(() => ctrl && ctrl.abort(), ms);
    return fetchNativo(url, Object.assign({ cache: "no-store" }, opcoes || {}, ctrl ? { signal: ctrl.signal } : {}))
      .finally(() => clearTimeout(timer));
  }

  // Resolve com o primeiro sucesso; rejeita só se todas falharem (Promise.any compatível)
  function primeiroSucesso(promessas) {
    return new Promise((resolve, reject) => {
      let pendentes = promessas.length;
      if (!pendentes) {
        reject(new Error("sem candidatos"));
        return;
      }
      promessas.forEach((p) => {
        Promise.resolve(p).then(resolve, () => {
          pendentes -= 1;
          if (pendentes === 0) reject(new Error("nenhum servidor respondeu"));
        });
      });
    });
  }

  async function testarBase(base) {
    const b = normalizarBase(base);
    if (!b) throw new Error("base inválida");
    const resp = await fetchComTimeout(`${b}${ROTA_SONDA}?t=${Date.now()}`, TIMEOUT_SONDA_MS);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const dados = await resp.json().catch(() => ({}));
    return { base: b, dados };
  }

  async function lerPorteiroPublico() {
    const info = await primeiroSucesso(
      FONTES_PORTEIRO.map(async (fonte) => {
        const resp = await fetchComTimeout(`${fonte}?t=${Date.now()}`, TIMEOUT_PORTEIRO_MS);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const json = await resp.json();
        if (!json || (!json.url_ativa && !json.ip_local)) throw new Error("vazio");
        return json;
      })
    );
    return info;
  }

  let descobertaEmAndamento = null;

  function descobrirServidorAtivo() {
    if (descobertaEmAndamento) return descobertaEmAndamento;

    descobertaEmAndamento = (async () => {
      const candidatos = [];
      const adicionar = (u) => {
        const b = normalizarBase(u);
        if (b && !candidatos.includes(b)) candidatos.push(b);
      };
      adicionar(ORIGEM_ATUAL); // a) origem instalada ainda responde?
      adicionar(baseAtual);
      adicionar(localStorage.getItem(STORAGE_TUNNEL));
      adicionar(localStorage.getItem(STORAGE_IP)); // c) último IP local Wi-Fi

      const tarefas = candidatos.map((c) => testarBase(c));

      // b) arquivo público do Porteiro (GitHub raw / Pages)
      tarefas.push(
        lerPorteiroPublico().then((info) => {
          const novos = [info.url_ativa, info.ip_local]
            .map(normalizarBase)
            .filter((b) => b && !candidatos.includes(b));
          if (!novos.length) throw new Error("porteiro sem novidade");
          return primeiroSucesso(novos.map((b) => testarBase(b)));
        })
      );

      try {
        const vencedor = await primeiroSucesso(tarefas);
        definirBase(vencedor.base, vencedor.dados);
        return vencedor.base;
      } catch (_e) {
        atualizarStatusUi("Servidor da loja não encontrado. Use \"Sincronizar via QR Code / Wi-Fi\".");
        return null;
      }
    })().finally(() => {
      setTimeout(() => {
        descobertaEmAndamento = null;
      }, 0);
    });

    return descobertaEmAndamento;
  }

  // -------------------------------------------------------
  // Interceptor global de fetch: "/api/..." => KANEMBERG_API_BASE + "/api/..."
  // -------------------------------------------------------
  function extrairCaminhoApi(input) {
    const bruto = typeof input === "string" ? input : input && input.url ? input.url : "";
    if (!bruto) return null;
    if (bruto.startsWith("/api/")) return bruto;
    try {
      const u = new URL(bruto, window.location.href);
      if (u.origin === ORIGEM_ATUAL && u.pathname.startsWith("/api/")) {
        return u.pathname + u.search;
      }
    } catch (_e) {
      /* ignora */
    }
    return null;
  }

  async function apiMobileFetch(input, init) {
    const caminho = extrairCaminhoApi(input);
    if (!caminho || caminho.startsWith(ROTA_SONDA)) {
      return fetchNativo(input, init);
    }

    // Se uma descoberta já estiver rodando (ex: na abertura do app), espera por ela
    if (descobertaEmAndamento) {
      try {
        await descobertaEmAndamento;
      } catch (_e) {
        /* segue com a base atual */
      }
    }

    const baseUsada = baseAtual;
    let resposta = null;
    let erroRede = null;
    try {
      resposta = await fetchNativo(baseUsada + caminho, init);
    } catch (err) {
      erroRede = err;
    }

    const tunelMorto = erroRede || (resposta && STATUS_TUNEL_MORTO.includes(resposta.status));
    if (!tunelMorto) return resposta;

    const novaBase = await descobrirServidorAtivo();
    // Só reenvia se o servidor mudou (a requisição original não chegou ao servidor)
    if (novaBase && novaBase !== baseUsada) {
      return fetchNativo(novaBase + caminho, init);
    }
    if (erroRede) throw erroRede;
    return resposta;
  }

  window.fetch = apiMobileFetch;

  // -------------------------------------------------------
  // UI: "Sincronizar via QR Code / Wi-Fi" (tela de login)
  // -------------------------------------------------------
  let scannerSync = null;

  function atualizarStatusUi(mensagem) {
    const elStatus = document.getElementById("sync-servidor-status");
    if (!elStatus) return;
    elStatus.textContent = mensagem || `Servidor conectado: ${baseAtual}`;
  }

  async function aplicarEnderecoLido(texto) {
    const base = normalizarBase(texto);
    if (!base) {
      atualizarStatusUi("Endereço inválido. Use https://...trycloudflare.com ou http://192.168.x.x:8000");
      return false;
    }
    atualizarStatusUi(`Testando ${base} ...`);
    try {
      const r = await testarBase(base);
      definirBase(r.base, r.dados);
      atualizarStatusUi(`Sincronizado com sucesso: ${r.base}`);
      return true;
    } catch (_e) {
      atualizarStatusUi(`Servidor não respondeu em ${base}. Confira se o PC do caixa está ligado.`);
      return false;
    }
  }

  async function pararScannerSync() {
    if (!scannerSync) return;
    try {
      await scannerSync.stop();
    } catch (_e) {
      /* ignora */
    }
    scannerSync = null;
    const caixa = document.getElementById("sync-qr-reader");
    if (caixa) caixa.innerHTML = "";
  }

  async function iniciarScannerSync() {
    const caixa = document.getElementById("sync-qr-reader");
    if (!caixa) return;
    if (!window.Html5Qrcode || !window.isSecureContext) {
      atualizarStatusUi("Câmera indisponível aqui. Cole o endereço exibido no PC do caixa abaixo.");
      return;
    }
    await pararScannerSync();
    scannerSync = new window.Html5Qrcode("sync-qr-reader");
    try {
      await scannerSync.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 200, height: 200 } },
        async (texto) => {
          await pararScannerSync();
          await aplicarEnderecoLido(texto);
        },
        () => {}
      );
      atualizarStatusUi("Aponte para o QR Code da tela Conexão & Servidor no PC.");
    } catch (_e) {
      scannerSync = null;
      atualizarStatusUi("Não foi possível abrir a câmera. Cole o endereço abaixo.");
    }
  }

  function registrarUiSync() {
    const btn = document.getElementById("btn-sync-servidor");
    const box = document.getElementById("sync-servidor-box");
    const inp = document.getElementById("sync-url-manual");
    const btnAplicar = document.getElementById("btn-sync-aplicar");
    if (!btn || !box) return;

    btn.addEventListener("click", async () => {
      const abrindo = box.classList.contains("hidden");
      box.classList.toggle("hidden", !abrindo);
      if (abrindo) {
        atualizarStatusUi();
        descobrirServidorAtivo();
        iniciarScannerSync();
      } else {
        pararScannerSync();
      }
    });

    if (btnAplicar && inp) {
      btnAplicar.addEventListener("click", () => aplicarEnderecoLido(inp.value));
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          aplicarEnderecoLido(inp.value);
        }
      });
    }
  }

  window.KanembergConexao = {
    descobrirServidorAtivo,
    definirBase,
    testarBase,
    apiMobileFetch,
    obterBase: () => baseAtual,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", registrarUiSync);
  } else {
    registrarUiSync();
  }

  // Sempre que o app abre (ou volta a ficar online), confirma o servidor ativo em background
  descobrirServidorAtivo();
  window.addEventListener("online", () => descobrirServidorAtivo());
})();
