/* =========================================================
   KANEMBERG PDV MOBILE — Service Worker (PWA + Reconexão Porteiro)
   Escopo: / (cobre / e /app via Cloudflare HTTPS e LAN)
   ========================================================= */

const CACHE_NAME = "kanemberg-pwa-v5";
const STATIC_ASSETS = [
  "/app",
  "/",
  "/manifest.json",
  "/static/manifest.json",
  "/static/style.css?v=5",
  "/static/app.js?v=5",
  "/static/icon-180.png",
  "/static/icon-192.png",
  "/static/icon-512.png"
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => (key !== CACHE_NAME ? caches.delete(key) : null))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.pathname.startsWith("/api/")) return;

  event.respondWith(
    fetch(req)
      .then((networkResp) => {
        // Se um túnel trycloudflare antigo expirou (HTTP 530/502/504), entrega o app em cache para acionar o reconector
        if (
          req.mode === "navigate" &&
          networkResp &&
          (networkResp.status === 530 || networkResp.status === 502 || networkResp.status === 504)
        ) {
          return caches.match("/app").then((cached) => cached || caches.match("/") || networkResp);
        }
        if (networkResp && networkResp.status === 200 && networkResp.type === "basic") {
          const respClone = networkResp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, respClone).catch(() => {}));
        }
        return networkResp;
      })
      .catch(() =>
        caches.match(req).then((cached) => {
          if (cached) return cached;
          if (req.mode === "navigate") {
            return caches.match("/app").then((c) => c || caches.match("/"));
          }
          return cached;
        })
      )
  );
});
