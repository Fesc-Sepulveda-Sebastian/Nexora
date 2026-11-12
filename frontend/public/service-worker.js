const CACHE_NAME = 'nexora-shell-v1.0.1';
const STATIC_SHELL_ROUTES = new Set([
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
  '/icons.svg',
]);

const STATIC_ASSET_EXTENSIONS = [
  '.js',
  '.css',
  '.svg',
  '.png',
  '.jpg',
  '.jpeg',
  '.webp',
  '.woff',
  '.woff2',
  '.ico',
];

function isPublicStaticAssetRequest(request) {
  if (request.method !== 'GET') return false;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return false;

  // Never cache API endpoints, WebSockets, or uploaded private objects (H13, RNF-02, RNF-13)
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) {
    return false;
  }

  if (STATIC_SHELL_ROUTES.has(url.pathname)) {
    return true;
  }

  if (url.pathname.startsWith('/assets/')) {
    return true;
  }

  const lowerPath = url.pathname.toLowerCase();
  return STATIC_ASSET_EXTENSIONS.some((ext) => lowerPath.endsWith(ext));
}

// Install: Cache App Shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(['/', '/index.html', '/manifest.json', '/favicon.svg']);
    })
  );
  self.skipWaiting();
});

// Activate: Clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: Strict allowlist for public static assets only; never cache API responses
self.addEventListener('fetch', (event) => {
  if (!isPublicStaticAssetRequest(event.request)) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            return caches.match('/index.html');
          }
          return Response.error();
        });
      })
  );
});

// Message listener for RNF-21: Purge cache on logout or account switch
self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'PURGE_CACHE') {
    const port = event.ports && event.ports[0];
    event.waitUntil(
      caches.keys()
        .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
        .then(() => {
          if (port) port.postMessage({ ok: true });
          console.log('[ServiceWorker] Caches purged successfully (RNF-21).');
        })
        .catch((err) => {
          if (port) port.postMessage({ ok: false, error: String(err) });
        })
    );
  }
});
