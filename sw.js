const CACHE = 'sermonseek-v1';
const SHELL = [
  './',
  './index.html',
  './manifest.json',
  './data/pastors.json',
  './data/playlists.json',
  './data/search_index.json',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
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
  if (url.origin !== self.location.origin) return;   // let youtube etc. bypass

  // Stale-while-revalidate for data files; cache-first for shell
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

  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
      if (resp.ok && resp.type === 'basic') {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return resp;
    }).catch(() => caches.match('./index.html')))
  );
});
