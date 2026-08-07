// Bump this version whenever the app shell (index.html / sw.js) changes.
// Any change to CACHE flushes all previously-cached shells on activate.
const CACHE = 'sermonseek-v3';

const DATA = [
  './data/pastors.json',
  './data/playlists.json',
  './data/search_index.json',
];

self.addEventListener('install', e => {
  // Warm the data cache (never the HTML — that must always come from network).
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(DATA).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // NETWORK-FIRST for the HTML shell + JS + manifest so users always see
  // the latest deployed code. Falls back to cache only when offline.
  const isShell = url.pathname === '/' ||
                  url.pathname.endsWith('/index.html') ||
                  url.pathname.endsWith('/manifest.json') ||
                  url.pathname.endsWith('/sw.js');

  if (isShell) {
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match(e.request).then(cached => cached || caches.match('./index.html')))
    );
    return;
  }

  // STALE-WHILE-REVALIDATE for data files.
  if (url.pathname.includes('/data/')) {
    e.respondWith(
      caches.open(CACHE).then(cache =>
        cache.match(e.request).then(cached => {
          const fetchP = fetch(e.request).then(resp => {
            if (resp.ok) cache.put(e.request, resp.clone());
            return resp;
          }).catch(() => cached);
          return cached || fetchP;
        })
      )
    );
    return;
  }

  // CACHE-FIRST for images, fonts, icons — they rarely change.
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
      if (resp.ok && resp.type === 'basic') {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return resp;
    }))
  );
});
