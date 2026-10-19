/* Produkthelfer Automation – Service Worker (Offline-Betrieb)
   Bei jeder Aktualisierung einer App die VERSION erhöhen. */
const VERSION='V01.04-19.10.2026', CACHE='pc-auto-'+VERSION, DATA='pc-auto-daten';
const CORE=["./", "./index.html", "./manifest.webmanifest", "./apps/automatisierung.html", "./apps/kommunikation.html", "./apps/relais.html", "./apps/trennverstaerker.html", "./apps/sicherheit.html", "./apps/systemverkabelung.html", "./apps/ansprechpartner/index.html", "./icons/icon-180.png", "./icons/icon-192.png", "./icons/icon-512-maskable.png", "./icons/icon-512.png"];
self.addEventListener('install',e=>{ e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE))); self.skipWaiting(); });
self.addEventListener('activate',e=>{ e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x.startsWith('pc-auto-')&&x!==CACHE&&x!==DATA).map(x=>caches.delete(x)))).then(()=>self.clients.claim())); });
self.addEventListener('fetch',e=>{
  const req=e.request; if(req.method!=='GET') return; const url=new URL(req.url);
  /* Produktbilder von phoenixcontact.com: einmal laden, dann aus dem Speicher */
  if(url.hostname==='caas.phoenixcontact.com'){
    e.respondWith(caches.open(DATA).then(async c=>{ const hit=await c.match(req); if(hit) return hit; const r=await fetch(req); if(r.ok||r.type==='opaque') c.put(req,r.clone()); return r; })); return; }
  if(url.origin!==location.origin) return;
  /* Ansprechpartner-Daten und Fotos: erst Netz (aktuell), sonst letzte bekannte Version */
  if(/\/daten\.xlsx$/.test(url.pathname)||/\/bilder\//.test(url.pathname)){
    e.respondWith(fetch(req).then(r=>{ if(r.ok){ const cp=r.clone(); caches.open(DATA).then(c=>c.put(req,cp)); } return r; }).catch(()=>caches.match(req).then(h=>h||new Response('',{status:404})))); return; }
  /* Apps: aus dem Speicher (schnell, offline), im Hintergrund aktualisieren */
  e.respondWith(caches.match(req,{ignoreSearch:true}).then(hit=>{
    const net=fetch(req).then(r=>{ if(r.ok&&r.type==='basic'){ const cp=r.clone(); caches.open(CACHE).then(c=>c.put(req,cp)); } return r; });
    if(hit){ net.catch(()=>{}); return hit; }
    return net.catch(()=> req.mode==='navigate' ? caches.match('./index.html') : new Response('',{status:504}));
  }));
});
