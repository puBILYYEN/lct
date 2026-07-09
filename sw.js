// 物流控制塔 v2 · service worker（network-first）
// 策略：優先抓網路最新版（開發時永遠看到新東西），失敗才退回快取（離線可用）。
const CACHE = "control-tower-v2-1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(clients.claim()));

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches
          .open(CACHE)
          .then((c) => c.put(e.request, copy))
          .catch(() => {});
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
