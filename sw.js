const VERSION='op18-radar-v1';
const ASSETS=['./','./index.html','./styles.css','./app.js','./data/seed.js','./manifest.webmanifest','./icons/icon-192.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(VERSION).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==VERSION).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const req=event.request;
  if(req.method!=='GET'||new URL(req.url).origin!==location.origin)return;
  // Never cache the availability feed; stale tickets are misleading.
  if(new URL(req.url).pathname.endsWith('/data/status.json')){event.respondWith(fetch(req,{cache:'no-store'}));return;}
  event.respondWith(fetch(req).then(res=>{if(res.ok){const clone=res.clone();caches.open(VERSION).then(cache=>cache.put(req,clone));}return res;}).catch(()=>caches.match(req)));
});
