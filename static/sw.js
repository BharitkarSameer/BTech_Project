// Service Worker for Crop Recommendation PWA
const CACHE_NAME = 'crop-ai-v1';

// On install: cache the app shell
self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll([
        '/',
        '/app/static/manifest.json',
        '/app/static/icon.png',
        '/app/static/icon-512.png',
      ]);
    })
  );
});

// On activate: clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    })
  );
  return self.clients.claim();
});

// On fetch: network-first strategy (falls back to cache if offline)
self.addEventListener('fetch', function(event) {
  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Clone and cache the fresh response
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, responseClone);
        });
        return response;
      })
      .catch(function() {
        // Network failed — serve from cache
        return caches.match(event.request);
      })
  );
});
