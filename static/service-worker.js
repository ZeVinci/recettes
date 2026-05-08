// Service worker minimal : met en cache les pages visitées pour un usage hors-ligne.
const CACHE = "recettes-v1";

self.addEventListener("install", e => {
    self.skipWaiting();
});

self.addEventListener("activate", e => {
    e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", e => {
    e.respondWith(
        caches.match(e.request).then(cached => {
            return cached || fetch(e.request).then(response => {
                // On met en cache les réponses GET réussies.
                if (e.request.method === "GET" && response.status === 200) {
                    const copy = response.clone();
                    caches.open(CACHE).then(c => c.put(e.request, copy));
                }
                return response;
            }).catch(() => cached);
        })
    );
});
