// Minimal service worker for PWA installability.
// This app is a local tool - no offline caching needed.

const CACHE_NAME = 'resume-gen-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Network-first: always try network, this is a local app
  event.respondWith(fetch(event.request));
});
