// Retire the old cache-first worker so updates and menus are never stuck offline.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) {
        if (key.startsWith("menu-analyzer-")) await caches.delete(key);
      }
      await self.registration.unregister();
    })(),
  );
});
