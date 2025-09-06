// Simple service worker for caching
const CACHE_NAME = 'menu-analyzer-v1';

self.addEventListener('install', (event) => {
    console.log('Service worker installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Opened cache');
                // Don't try to cache files that might not exist
                return Promise.resolve();
            })
            .catch((error) => {
                console.log('Cache install failed:', error);
            })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                return response || fetch(event.request);
            })
            .catch((error) => {
                console.log('Fetch failed:', error);
                return fetch(event.request);
            })
    );
});
