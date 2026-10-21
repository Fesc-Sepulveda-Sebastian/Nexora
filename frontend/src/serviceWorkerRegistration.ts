export function registerServiceWorker() {
  if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/service-worker.js')
        .then((reg) => {
          console.log('[PWA] Service Worker registrado exitosamente:', reg.scope);
        })
        .catch((err) => {
          console.error('[PWA] Error al registrar Service Worker:', err);
        });
    });
  }
}

export function purgeServiceWorkerCache() {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ action: 'PURGE_CACHE' });
  }
}
