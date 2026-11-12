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

export async function purgeServiceWorkerCache(): Promise<void> {
  // Always clear CacheStorage directly if supported in the window context
  if (typeof window !== 'undefined' && 'caches' in window) {
    try {
      const keys = await window.caches.keys();
      await Promise.all(keys.map((key) => window.caches.delete(key)));
    } catch (err) {
      console.warn('[PWA] Error al limpiar CacheStorage:', err);
    }
  }

  // Also ask active Service Worker to purge any caches it holds
  if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator && navigator.serviceWorker.controller) {
    await new Promise<void>((resolve) => {
      const channel = new MessageChannel();
      const timeout = window.setTimeout(() => resolve(), 500);
      channel.port1.onmessage = () => {
        window.clearTimeout(timeout);
        resolve();
      };
      try {
        navigator.serviceWorker.controller?.postMessage({ action: 'PURGE_CACHE' }, [channel.port2]);
      } catch {
        window.clearTimeout(timeout);
        resolve();
      }
    });
  }
}
