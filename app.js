/* OP-18 Ticket Radar: device preferences remain local; status data is a published feed. */
(() => {
  'use strict';
  const STORAGE = 'op18-radar-prefs-v1';
  const seed = window.OP18_SEED;
  const fallbackPrefs = {favorites:['401-vaughan','401-downtown','dollys','game-shack','mintink'],tickets:[],customStores:[],notes:{},progress:{}};
  let prefs = loadPrefs();
  let data = seed;
  let tab = 'dashboard', area='All', eventFilter='All', search='';
  let lastFeedError = null;
  let toastTimer = null;
  const $ = id => document.getElementById(id);
  const safe = v => String(v ?? '').replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const safeUrl = s => { try { const u = new URL(s); return ['https:','http:'].includes(u.protocol) ? u.href : ''; } catch { return ''; } };
  const link = (url, label, className='action') => safeUrl(url) ? `<a href="${safe(safeUrl(url))}" target="_blank" rel="noopener noreferrer" class="${className}">${safe(label)} ↗</a>` : '';
  const money = v => v == null ? '' : `CA$${Number(v).toFixed(2)}`;
  const allStores = () => [...data.stores, ...prefs.customStores];
  const findStore = id => allStores().find(s=>s.id===id) || {name:'Unknown store', city:'GTA'};
  const allEvents = () => [...data.events].sort((a,b)=> (a.date+' '+a.time).localeCompare(b.date+' '+b.time));
  const dateLabel = e => new Date(`${e.date}T${e.time}:00-05:00`).toLocaleDateString('en-CA',{timeZone:'America/Toronto',weekday:'short',month:'short',day:'numeric'});
  const timeLabel = e => new Date(`${e.date}T${e.time}:00-05:00`).toLocaleTimeString('en-CA',{timeZone:'America/Toronto',hour:'numeric',minute:'2-digit'});
  const statusNames = {available:'TICKETS LIVE',sold_out:'SOLD OUT',unverified:'NOT VERIFIED',check_store:'CHECK STORE',no_event:'WATCHING'};
  const badge = status => `<span class="badge ${safe(status)}">${safe(statusNames[status]||'NOT VERIFIED')}</span>`;
  const firstArea = c => c==='Toronto' || c==='North York' ? 'Toronto' : c;
  function loadPrefs(){
    try {
      const p=JSON.parse(localStorage.getItem(STORAGE));
      if(!p || typeof p!=='object') return structuredClone(fallbackPrefs);
      return {...structuredClone(fallbackPrefs),...p};
    } catch { return structuredClone(fallbackPrefs); }
  }
  function save(){ try { localStorage.setItem(STORAGE, JSON.stringify(prefs)); } catch {} }
  function notify(msg){ const el=$('toast'); el.textContent=msg; el.classList.add('show'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove('show'),2900); }
  function lastChecked(){
    if(!data.meta.lastChecked) return 'Not connected to scheduled checks';
    const d=new Date(data.meta.lastChecked);
    if(Number.isNaN(d.getTime())) return 'Last check time unavailable';
    return `Published check: ${d.toLocaleString('en-CA',{timeZone:'America/Toronto',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})} ET`;
  }
  function isStale(e){
    if(!e.lastVerified) return true;
    const verified = new Date(`${e.lastVerified}T12:00:00-05:00`).getTime();
    return Date.now()-verified > 24*3600000;
  }
  function areaChip(a){return `<button class="chip ${area===a?'active':''}" data-area="${safe(a)}">${safe(a)}</button>`;}
  function chips(){return `<div class="filterbar" role="group" aria-label="Filter by location">${['All','Toronto','Scarborough','Vaughan','Richmond Hill','Markham'].map(areaChip).join('')}</div>`;}
  function stats(){
    const events=allEvents();
    return `<div class="statgrid"><div class="stat"><strong>${allStores().length}</strong><span>SHOPS WATCHED</span></div><div class="stat open"><strong>${events.filter(e=>e.status==='available').length}</strong><span>TICKETS LIVE*</span></div><div class="stat sold"><strong>${events.filter(e=>e.status==='sold_out').length}</strong><span>SOLD OUT*</span></div></div>`;
  }
  function eventRow(e){
    return `<div class="eventline"><div><div class="eventname">${safe(dateLabel(e))} · ${safe(timeLabel(e))}</div><div class="eventdesc">${safe(findStore(e.storeId).name)} ${e.price!=null?`· <span class="price">${money(e.price)}</span>`:''}</div></div>${badge(e.status)}</div>`;
  }
  function eventCard(e){
    const s=findStore(e.storeId), bought=prefs.tickets.includes(e.id);
    return `<article class="card ${e.status==='available'?'ticket':''}">
      <div class="cardtop"><div><div class="store-title">${safe(s.name)}</div><div class="area">${safe(s.city)} · ${safe(dateLabel(e))} at ${safe(timeLabel(e))}</div></div>${badge(e.status)}</div>
      <div class="mini-line">${e.price!=null?'Entry '+money(e.price)+' · ':''}${e.tcgPlus?'Bandai TCG+ also required · ':''}Status: ${safe(e.lastVerified||'not verified')} · ${safe(e.statusSource||'Store page')}${isStale(e)?' · <span class="recheck">stale: recheck store</span>':''}</div>
      <div class="actions">${link(e.url||s.url,'Open ticket page',e.status==='available'?'action primary':'action')}<button class="action" data-ticket="${safe(e.id)}">${bought?'✓ Ticket secured':'I got a ticket'}</button></div>
    </article>`;
  }
  function storeCard(s){
    const ev=allEvents().filter(e=>e.storeId===s.id);
    const fav=prefs.favorites.includes(s.id);
    const progress=prefs.progress[s.id]||'watching';
    const topStatus=ev.some(e=>e.status==='available')?'available':ev.length&&ev.every(e=>e.status==='sold_out')?'sold_out':ev.length?'check_store':'no_event';
    return `<article class="card" id="shop-${safe(s.id)}"><div class="cardtop"><div><div class="store-title">${safe(s.name)}</div><div class="area">${safe(s.city)} ${s.priority?'· Priority shop':''}</div></div><div class="row">${badge(topStatus)}<button class="plainicon ${fav?'saved':''}" data-fav="${safe(s.id)}" title="${fav?'Unpin':'Pin'} store" aria-label="${fav?'Unpin':'Pin'} ${safe(s.name)}">★</button></div></div>
    ${ev.length?`<div style="margin-top:11px">${ev.map(eventRow).join('')}</div>`:`<p class="helper">No OP-18 release event confirmed yet. Regular One Piece tournaments do not count.</p>`}
    <div class="actions">${link(s.url,'Open store / tickets')}${s.eventsUrl && s.eventsUrl!==s.url?link(s.eventsUrl,'Event calendar'):''}${s.id.startsWith('custom-')?`<button class="action" data-remove="${safe(s.id)}">Remove</button>`:''}</div>
    <div class="personalrow"><label for="progress-${safe(s.id)}">MY PROGRESS</label><select id="progress-${safe(s.id)}" data-progress="${safe(s.id)}">${[['watching','Watching'],['contacted','Asked store'],['waitlist','Waitlist / restock alert'],['tcg','Applied via TCG+']].map(([key,text])=>`<option value="${key}" ${progress===key?'selected':''}>${text}</option>`).join('')}</select><button class="note-btn" data-note="${safe(s.id)}">${prefs.notes[s.id]?'Edit note':'+ Note'}</button></div>
    ${prefs.notes[s.id]?`<p class="helper"><b>My note:</b> ${safe(prefs.notes[s.id])}</p>`:''}
    ${s.notes?`<p class="helper">${safe(s.notes)}</p>`:''}</article>`;
  }
  function discoveries(){
    const list=(data.discoveries||[]).slice().reverse();
    return !list.length ? '' : `<div class="sectionhead"><h2>Possible new listings</h2></div><div class="notice info">These links were discovered automatically, but <b>tickets have not been verified</b>. Open the store page before making plans.</div>${list.slice(0,8).map(d=>`<article class="card"><div class="cardtop"><div><div class="store-title">${safe(findStore(d.storeId).name)}</div><div class="area">${safe(d.title||'Possible OP-18 event')}</div></div>${badge('unverified')}</div><div class="actions">${link(d.url,'Review listing')}</div><p class="helper">Discovered ${safe(d.firstSeen||'recently')} · Not confirmed available.</p></article>`).join('')}`;
  }
  function dashboard(){
    const favorites=allStores().filter(s=>prefs.favorites.includes(s.id));
    const events=allEvents();
    const open=events.filter(e=>e.status==='available');
    const checked = data.checks||[];
    return `<section class="hero"><div class="kicker">✧ 4th anniversary release</div><h1>THE DOMINANCE<br>OF GOD</h1><p>Your personal GTA OP-18 event ticket mission control.</p><div class="hero-tag">SET RELEASE <b>20 NOV 2026</b></div></section>
    <div class="subbar"><span><i class="status-dot"></i>${safe(lastChecked())}</span><span>${data.meta.lastChecked?'ONLINE FEED':'STARTER SNAPSHOT'}</span></div>
    ${stats()}
    ${!data.meta.lastChecked?'<div class="notice info"><b>Setup needed for automatic app updates.</b> Your existing ChatGPT hourly ticket alerts are separate and remain active. Host this dashboard and enable its scheduled scanner to see new checks here.</div>':''}
    <div class="sectionhead"><h2>Ticket opportunities</h2><button class="linkbutton" data-go="events">View all →</button></div>
    ${open.length?open.slice(0,3).map(eventCard).join(''):'<div class="notice">No confirmed purchasable OP-18 tickets in the latest saved data. Sold-out listings may change; use the direct store links to check.</div>'}
    ${discoveries()}
    <div class="sectionhead"><h2>Your priority shops</h2><button class="linkbutton" data-go="stores">All shops →</button></div>
    ${favorites.slice(0,5).map(storeCard).join('')||'<div class="empty">Star a shop in the Shops tab to pin it here.</div>'}
    <div class="sectionhead"><h2>Upcoming event dates</h2><button class="linkbutton" data-go="events">Full schedule →</button></div>
    <div class="card">${events.slice(0,5).map(eventRow).join('')}</div>
    <p class="helper">*Statuses are a saved snapshot until the monitor has verified them again. Green means a confirmed positive check, not a guaranteed seat at checkout.</p>`;
  }
  function eventsPage(){
    const list=allEvents().filter(e=> (area==='All'||firstArea(findStore(e.storeId).city)===area) && (eventFilter==='All'||e.status===eventFilter) && `${findStore(e.storeId).name} ${findStore(e.storeId).city}`.toLowerCase().includes(search.toLowerCase()));
    let lastDate='';
    const cards=list.map(e=>{ const date=e.date; const label=date!==lastDate?`<div class="daylabel">${safe(dateLabel(e))}</div>`:''; lastDate=date; return label+eventCard(e); }).join('');
    return `<div class="pagehead"><div class="kicker">TICKET MISSION</div><h1>Release events</h1><p>Confirmed OP-18 dates, prices and direct pages. All event times Eastern.</p></div>
    <input class="searchbox" id="search" value="${safe(search)}" placeholder="Search shops or locations" aria-label="Search events">
    ${chips()}<div class="filterbar" role="group" aria-label="Filter event status">${[['All','All'],['available','Tickets live'],['sold_out','Sold out'],['check_store','Check store']].map(([id,label])=>`<button class="chip ${eventFilter===id?'active':''}" data-status="${safe(id)}">${safe(label)}</button>`).join('')}</div>
    <p class="helper">${list.length} listed event${list.length!==1?'s':''} · Prices in CAD · Check official tickets before travelling.</p>${cards||'<div class="empty">No events match these filters. Try All areas or another status.</div>'}${discoveries()}`;
  }
  function storesPage(){
    const list=allStores().filter(s=>(area==='All'||firstArea(s.city)===area) && `${s.name} ${s.city}`.toLowerCase().includes(search.toLowerCase())).sort((a,b)=>{const af=prefs.favorites.includes(a.id)?0:1,bf=prefs.favorites.includes(b.id)?0:1;return af-bf||a.name.localeCompare(b.name);});
    return `<div class="pagehead"><div class="kicker">GTA NETWORK</div><h1>Watched card shops</h1><p>Star shops to keep them on your dashboard. Store calendars are monitored where public pages allow it.</p></div>
    <input class="searchbox" id="search" value="${safe(search)}" placeholder="Search 401 Games, Dolly's, Game Shack…" aria-label="Search stores">
    ${chips()}<div class="row between" style="margin-bottom:13px"><span class="muted small">${list.length} shops displayed</span><button class="linkbutton" data-add="1">+ Add a shop</button></div>
    ${list.map(storeCard).join('')||'<div class="empty">No stores found. Try another area.</div>'}`;
  }
  function activityPage(){
    const checks = data.checks||[];
    const total=data.stores.length, checked=checks.filter(c=>c.ok).length;
    const activity=[...(data.activity||[])].sort((a,b)=>String(b.timestamp).localeCompare(String(a.timestamp)));
    const ratio=total?Math.round(100*checked/total):0;
    return `<div class="pagehead"><div class="kicker">WATCH PROGRESS</div><h1>Check history</h1><p>Shows the latest published scanner activity. It cannot read ChatGPT automation run history directly.</p></div>
    <div class="card"><div class="row between"><span class="store-title">Latest website scan</span><span class="badge unverified">${data.meta.lastChecked?'SCAN LOG':'NO LIVE FEED'}</span></div><p class="helper">${safe(lastChecked())}</p><div class="progress-track"><div style="width:${ratio}%"></div></div><p class="helper">${checked} of ${total} store pages successfully checked during the last published scan. Pages with access restrictions may require manual checks.</p></div>
    <div class="sectionhead"><h2>Recent changes & checks</h2></div>
    ${activity.length?activity.slice(0,70).map(a=>`<div class="checkrow"><h3>${safe(a.type==='available'?'Ticket availability detected':a.type==='discovery'?'New possible listing':a.type==='sold_out'?'Sold-out status confirmed':'Watch update')}</h3><p>${safe(a.message)}</p><time>${safe(new Date(a.timestamp).toLocaleString('en-CA',{timeZone:'America/Toronto',dateStyle:'medium',timeStyle:'short'}))} ET</time></div>`).join(''):'<div class="empty">No activity has been recorded yet.</div>'}
    ${checks.length?`<div class="sectionhead"><h2>Store scanner diagnostics</h2></div>${checks.map(c=>`<div class="eventline"><div><div class="eventname">${safe(findStore(c.storeId).name)}</div><div class="eventdesc">${safe(c.message||'')}</div></div><span class="badge ${c.ok?'check_store':'unverified'}">${c.ok?'CHECKED':'NOT CHECKED'}</span></div>`).join('')}`:''}`;
  }
  function settingsPage(){
    return `<div class="pagehead"><div class="kicker">CAPTAIN'S CONTROLS</div><h1>Settings & setup</h1><p>Keep your ticket watch organized and get it onto your iPhone Home Screen.</p></div>
    <div class="card"><div class="setting"><h3>🔔 ChatGPT ticket alerts</h3><p>Your existing <b>OP-18 GTA Ticket Watch</b> is a separate hourly condition-watch automation. It notifies you through ChatGPT when a meaningful new ticket opportunity is found. This web app does not send its own background push alerts.</p></div>
    <div class="setting"><h3>↻ Dashboard data checks</h3><p>${safe(lastChecked())}. To enable automatic web checks inside this app, deploy the included project to GitHub Pages and enable GitHub Actions. Scheduled checks can be delayed by GitHub.</p></div>
    <div class="setting"><h3>📲 Install on iPhone</h3><p>After hosting the app at an HTTPS URL, open it in Safari, tap <b>Share</b>, then <b>Add to Home Screen</b>. Opening a downloaded HTML file alone will not provide reliable app installation or synchronization.</p></div>
    <div class="setting"><h3>☠️ Ticket safety</h3><p>The monitor only treats product pages with confirmed ticket inventory as available. A product page, weekly local event, or third-party tracker label is not proof of an open seat. Always confirm at checkout.</p></div></div>
    <div class="card"><h3 style="margin:0 0 7px">Personal tracking</h3><p class="helper">You have marked <b>${prefs.tickets.length} ticket(s) secured</b> and pinned <b>${prefs.favorites.length} shop(s)</b>. Your choices are saved on this device, not shared with other devices.</p><div class="settingsbuttons"><button class="widebtn" data-export="1">Export my tracking</button><button class="widebtn" data-reset="1">Reset tracking</button></div></div>
    <p class="helper">Unofficial fan-made tracker. Not affiliated with Bandai, One Piece or the stores listed. No payments are processed in this app.</p>`;
  }
  function render(){
    const nav = document.querySelectorAll('[data-tab]');
    nav.forEach(el=>{el.classList.toggle('active',el.dataset.tab===tab);if(el.dataset.tab===tab) el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
    $('app').innerHTML=({dashboard,events:eventsPage,stores:storesPage,activity:activityPage,settings:settingsPage})[tab]();
  }
  function changeTab(newTab){ tab=newTab;area='All';eventFilter='All';search='';render();scrollTo({top:0,behavior:'instant'}); }
  async function refresh(silent=false){
    const btn=$('refreshBtn');btn.disabled=true;
    try {
      const res=await fetch(`./data/status.json?t=${Date.now()}`,{cache:'no-store'});
      if(!res.ok) throw Error(`HTTP ${res.status}`);
      const next=await res.json();
      if(!Array.isArray(next.stores)||!Array.isArray(next.events)||!next.meta) throw Error('Invalid feed');
      data=next;lastFeedError=null;
      if(!silent) notify(next.meta.lastChecked?'Latest published check loaded':'Starter snapshot loaded');
      render();
    } catch(err){ lastFeedError=err.message;if(!silent)notify('No hosted feed — showing saved snapshot'); }
    finally{btn.disabled=false;}
  }
  document.addEventListener('click',e=>{
    const n=e.target.closest('[data-tab]'); if(n){changeTab(n.dataset.tab);return;}
    const go=e.target.closest('[data-go]');if(go){changeTab(go.dataset.go);return;}
    const loc=e.target.closest('[data-area]');if(loc){area=loc.dataset.area;render();return;}
    const filter=e.target.closest('[data-status]');if(filter){eventFilter=filter.dataset.status;render();return;}
    const fav=e.target.closest('[data-fav]');if(fav){const id=fav.dataset.fav;prefs.favorites=prefs.favorites.includes(id)?prefs.favorites.filter(x=>x!==id):[...prefs.favorites,id];save();render();notify(prefs.favorites.includes(id)?'Store pinned':'Store unpinned');return;}
    const ticket=e.target.closest('[data-ticket]');if(ticket){const id=ticket.dataset.ticket;prefs.tickets=prefs.tickets.includes(id)?prefs.tickets.filter(x=>x!==id):[...prefs.tickets,id];save();render();notify(prefs.tickets.includes(id)?'Marked ticket secured':'Ticket mark removed');return;}
    if(e.target.closest('[data-add]')){$('storeDialog').showModal();return;}
    const note=e.target.closest('[data-note]');if(note){const id=note.dataset.note;const updated=prompt('Private note for this shop:',prefs.notes[id]||'');if(updated!==null){prefs.notes[id]=updated.slice(0,500);save();render();notify('Note saved on this device');}return;}
    const remove=e.target.closest('[data-remove]');if(remove){prefs.customStores=prefs.customStores.filter(s=>s.id!==remove.dataset.remove);prefs.favorites=prefs.favorites.filter(id=>id!==remove.dataset.remove);save();render();notify('Custom shop removed');return;}
    if(e.target.closest('[data-export]')){const out=new Blob([JSON.stringify({exportedAt:new Date().toISOString(),...prefs},null,2)],{type:'application/json'});const url=URL.createObjectURL(out);const a=document.createElement('a');a.href=url;a.download='op18-my-tracking.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('Export created');return;}
    if(e.target.closest('[data-reset]')){if(confirm('Reset saved stars, ticket marks and custom shops on this device?')){prefs=structuredClone(fallbackPrefs);save();render();notify('Personal tracking reset');}return;}
  });
  document.addEventListener('change',e=>{if(e.target.matches('[data-progress]')){prefs.progress[e.target.dataset.progress]=e.target.value;save();notify('Store progress updated');}});
  document.addEventListener('input',e=>{if(e.target.id==='search'){const at=e.target.selectionStart;search=e.target.value;render();const next=$('search');if(next){next.focus();next.setSelectionRange(at,at);}}});
  $('refreshBtn').addEventListener('click',()=>refresh());
  $('cancelDialog').addEventListener('click',()=>$('storeDialog').close());
  $('storeForm').addEventListener('submit',e=>{ e.preventDefault();
    const name=$('addName').value.trim(),city=$('addCity').value,url=$('addUrl').value.trim();
    if(!name) return;if(url&&!safeUrl(url)){notify('Use a valid https:// URL');return;}
    const id='custom-'+Date.now();
    prefs.customStores.push({id,name,city,url,eventsUrl:url,notes:'Manual entry — not included in automatic website scanner',priority:false});
    prefs.favorites.push(id); save();$('storeForm').reset();$('storeDialog').close();tab='stores';render();notify('Custom shop added');
  });
  render();refresh(true);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden) refresh(true);});
  setInterval(()=>{if(!document.hidden)refresh(true)},300000);
  if('serviceWorker' in navigator && (location.protocol==='https:'||location.hostname==='localhost')){
    window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
  }
})();
