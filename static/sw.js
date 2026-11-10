/* =========================================================
   KANEMBERG PDV MOBILE — Service Worker (PWA Installable)
   Escopo: / (cobre / e /app na rede Wi-Fi local)
   ========================================================= */

const CACHE_NAME = "kanemberg-pwa-v4";
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
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
          return null;
        })
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") {
    return;
  }

  const url = new URL(req.url);

  // Requisições de API sempre vão direto para a rede (tempo real)
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Estratégia Network-First com fallback para Cache (exigido pelo Chrome PWA)
  event.respondWith(
    fetch(req)
      .then((networkResp) => {
        if (networkResp && networkResp.status === 200 && networkResp.type === "basic") {
          const respClone = networkResp.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(req, respClone).catch(() => {});
          });
        }
        return networkResp;
      })
      .catch(() => caches.match(req))
  );
});
