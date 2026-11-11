/* =========================================================
   KANEMBERG PDV MOBILE — Service Worker (Offline-First Shell)
   Escopo: /  (cobre /, /app e /static/*)

   Objetivo: o app instalado (WebAPK) SEMPRE abre em tela cheia a
   partir da memória do celular, mesmo quando o túnel Cloudflare em
   que ele foi instalado já morreu (HTTP 530 / erro 1033 / offline).
   A troca de servidor acontece só na camada de API (conexao_dinamica.js),
   sem sair da origem instalada.
   ========================================================= */

const CACHE_NAME = "kanemberg-shell-v6";
const NETWORK_TIMEOUT_MS = 2500;

// Shell obrigatório (cache.addAll é atômico: precisa responder 200)
const SHELL_ASSETS = [
  "/",
  "/app",
  "/static/index.html",
  "/manifest.json",
  "/static/manifest.json",
  "/static/style.css?v=5",
  "/static/conexao_dinamica.js?v=1",
  "/static/app.js?v=5",
  "/static/icon-180.png",
  "/static/icon-192.png",
  "/static/icon-512.png"
];

// Bibliotecas externas (best-effort, resposta opaca)
const EXTERNAL_ASSETS = ["https://unpkg.com/html5-qrcode"];

const SHELL_FALLBACKS = ["/app", "/", "/static/index.html"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      await cache.addAll(SHELL_ASSETS.map((u) => new Request(u, { cache: "reload" })));
      await Promise.all(
        EXTERNAL_ASSETS.map(async (u) => {
          try {
            const resp = await fetch(u, { mode: "no-cors" });
            await cache.put(u, resp);
          } catch (_e) {
            /* sem internet externa: segue sem a lib em cache */
          }
        })
      );
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)));
      await self.clients.claim();
    })()
  );
});

function fetchComTimeout(request, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), ms);
    fetch(request).then(
      (resp) => {
        clearTimeout(timer);
        resolve(resp);
      },
      (err) => {
        clearTimeout(timer);
        reject(err);
      }
    );
  });
}

async function shellEmCache(request) {
  const cache = await caches.open(CACHE_NAME);
  const exato = await cache.match(request, { ignoreSearch: true });
  if (exato) return exato;
  for (const rota of SHELL_FALLBACKS) {
    const resp = await cache.match(rota);
    if (resp) return resp;
  }
  return null;
}

// Navegação HTML: rede com timeout curto; falha OU status >= 400 => shell em cache
async function tratarNavegacao(request) {
  try {
    const resp = await fetchComTimeout(request, NETWORK_TIMEOUT_MS);
    if (resp && resp.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, resp.clone()).catch(() => {});
      return resp;
    }
    const cached = await shellEmCache(request);
    return cached || resp;
  } catch (_err) {
    const cached = await shellEmCache(request);
    if (cached) return cached;
    return new Response(
      "<!DOCTYPE html><meta charset='utf-8'><title>Kanemberg</title>" +
        "<body style='background:#0b1120;color:#f8fafc;font-family:sans-serif;padding:24px'>" +
        "Servidor indisponível e aplicativo ainda não armazenado neste aparelho.</body>",
      { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
    );
  }
}

// Assets estáticos da mesma origem: rede com timeout; falha OU status >= 400 => cache
async function tratarAssetLocal(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const resp = await fetchComTimeout(request, NETWORK_TIMEOUT_MS);
    if (resp && resp.ok) {
      cache.put(request, resp.clone()).catch(() => {});
      return resp;
    }
    const cached = await cache.match(request, { ignoreSearch: false }) || await cache.match(request, { ignoreSearch: true });
    return cached || resp;
  } catch (_err) {
    const cached = await cache.match(request) || await cache.match(request, { ignoreSearch: true });
    return cached || Response.error();
  }
}

// Bibliotecas externas: cache-first
async function tratarAssetExterno(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request.url);
  if (cached) return cached;
  try {
    const resp = await fetch(request);
    if (resp && (resp.ok || resp.type === "opaque")) {
      cache.put(request.url, resp.clone()).catch(() => {});
    }
    return resp;
  } catch (_e) {
    return Response.error();
  }
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const mesmaOrigem = url.origin === self.location.origin;

  // API nunca passa pelo cache (inclusive chamadas para outro túnel / IP local)
  if (url.pathname.startsWith("/api/")) return;

  if (mesmaOrigem) {
    const ehShell =
      req.mode === "navigate" ||
      url.pathname === "/" ||
      url.pathname === "/app" ||
      url.pathname === "/app/" ||
      url.pathname === "/static/index.html";

    if (ehShell) {
      event.respondWith(tratarNavegacao(req));
      return;
    }
    if (url.pathname.startsWith("/static/") || url.pathname === "/manifest.json") {
      event.respondWith(tratarAssetLocal(req));
    }
    return;
  }

  if (EXTERNAL_ASSETS.some((u) => req.url.startsWith(u))) {
    event.respondWith(tratarAssetExterno(req));
  }
});
