/* Public price observations only. Scheduled checks run on GitHub, not on this device. */
(() => {
  'use strict';
  const PRIMARY_URL = 'https://enterthebattlefield.ca/products/nico-robin-010-alternate-art-eb05-010-extra-booster-one-piece-heroines-edition-vol-2-foil';
  const THRESHOLD = 50;
  const MAX_AGE = 2 * 60 * 60 * 1000;
  const EXTERNAL_ICON = '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 19 19 5M8 5h11v11"/></svg>';
  const DROP_ICON = '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="m5 5 14 14M8 19h11V8"/></svg>';
  const app = document.getElementById('app');
  const refreshButton = document.getElementById('refreshBtn');
  let feed = null;
  let feedError = null;
  let view = 'offers';
  let filter = 'all';
  let loading = false;
  let toastTimer;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeUrl = value => {
    if (typeof value !== 'string' || !value.trim()) return '';
    try { const url = new URL(value, location.href); return ['https:', 'http:'].includes(url.protocol) ? url.href : ''; }
    catch { return ''; }
  };
  const validPrice = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const money = value => validPrice(value) ? new Intl.NumberFormat('en-CA', {minimumFractionDigits:2, maximumFractionDigits:2}).format(value) : '—';
  const date = value => {
    const time = Date.parse(value);
    return Number.isFinite(time) ? new Intl.DateTimeFormat('en-CA', {timeZone:'America/Toronto', month:'short', day:'numeric', hour:'numeric', minute:'2-digit'}).format(time) + ' ET' : 'Not checked yet';
  };
  const ageIsValid = value => {
    const time = Date.parse(value);
    return Number.isFinite(time) && Date.now() - time <= MAX_AGE && time - Date.now() < 5 * 60 * 1000;
  };
  const isFresh = () => !!feed && !feedError && ageIsValid(feed.meta.lastChecked);
  const offers = () => feed ? feed.offers : [];
  const stores = () => feed ? feed.stores : [];
  const storeFor = offer => stores().find(store => store.id === offer.storeId) || {name:'Unknown retailer', status:'error'};
  const verified = offer => isFresh() && !offer.stale && ageIsValid(offer.lastSeen) && storeFor(offer).status === 'ok' && offer.currency === 'CAD' && validPrice(offer.price);
  const inStock = offer => verified(offer) && offer.inStock === true && offer.eligible === true;
  const below = offer => inStock(offer) && offer.price < THRESHOLD;
  const link = (url, text, className = '') => safeUrl(url) ? `<a class="${escape(className)}" href="${escape(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${text}</a>` : '';
  const badge = (text, type) => `<span class="badge ${escape(type)}">${escape(text)}</span>`;
  function notify(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
  }
  function empty(title, description, primaryLink = false) {
    return `<div class="empty-state" data-empty-state><div class="empty-icon" aria-hidden="true">${DROP_ICON}</div><h3>${escape(title)}</h3><p>${escape(description)}</p>${primaryLink ? link(PRIMARY_URL, 'Open your original listing ' + EXTERNAL_ICON) : ''}</div>`;
  }
  function hero() {
    return `<section class="hero" aria-labelledby="watch-title"><div><div class="eyebrow"><span class="tiny-line" aria-hidden="true"></span>A little patience. A better price.</div><h1 id="watch-title">Nico Robin.<br><em>Your price.</em></h1><p class="hero-description">Watching Canadian sellers for the same alternate-art foil card, in stock and below your target.</p><div class="product-tags"><span>EB05-010</span><span>ALTERNATE ART</span><span>FOIL · ENGLISH</span></div></div><div class="target-card"><div class="target-label">YOUR TARGET · STRICTLY BELOW</div><div class="target-price"><small>CA$</small>50</div><div class="target-foot">In stock · before shipping & tax<br>CA$50.00 does not qualify</div></div></section>`;
  }
  function notices() {
    if (feedError) return `<div class="notice error" role="status">${escape(feed ? 'The latest feed could not be loaded. Previously loaded prices are shown as unverified; they are not counted as current deals.' : 'The published price feed is unavailable. No current price or stock has been verified on this screen.')} ${escape(!navigator.onLine ? 'You appear to be offline.' : 'Try refreshing shortly.')}</div>`;
    if (!feed) return '<div class="notice info">Waiting for the first published price check. The dashboard is ready; there are no verified price observations yet.</div>';
    if (!isFresh()) return '<div class="notice">The last published check is more than two hours old, or its timestamp could not be verified. Historical prices are shown below, but none are counted as current deals.</div>';
    const failed = stores().filter(store => !['ok', 'no_match'].includes(store.status));
    return failed.length ? `<div class="notice">${failed.length} ${failed.length === 1 ? 'store could' : 'stores could'} not be verified on the latest run. A blocked or failed check does not mean the card is sold out. See Store checks for details.</div>` : '';
  }
  function stats() {
    const current = offers().filter(inStock);
    const lowest = current.length ? Math.min(...current.map(offer => offer.price)) : null;
    const checked = stores().filter(store => ['ok','no_match'].includes(store.status)).length;
    const total = stores().length;
    return `<div class="stats" aria-label="Watchlist summary"><div class="stat"><div class="stat-label">Lowest in stock</div><div class="stat-value" data-lowest-price>${lowest !== null ? `<small>CA$</small>${money(lowest)}` : '—'}</div><div class="stat-desc">${current.length ? 'Verified exact-card listing' : 'No current in-stock price verified'}</div></div><div class="stat match-stat"><div class="stat-label">Below your target</div><div class="stat-value" data-match-count>${offers().filter(below).length}<small> ${offers().filter(below).length === 1 ? 'listing' : 'listings'}</small></div><div class="stat-desc">In stock and strictly under CA$50</div></div><div class="stat"><div class="stat-label">Stores checked</div><div class="stat-value" data-store-count>${feed ? `${checked}<small> / ${total}</small>` : '—'}</div><div class="stat-desc">${feed ? 'Successful public-page checks' : 'Awaiting the first published run'}</div></div><div class="stat"><div class="stat-label">Scheduled interval</div><div class="stat-value">${feed ? escape(feed.meta.intervalMinutes || 30) : '30'}<small> min</small></div><div class="stat-desc">GitHub schedules can be delayed</div></div></div>`;
  }
  function priceCard(offer, index) {
    const store = storeFor(offer);
    const fresh = verified(offer);
    const match = below(offer);
    const stock = inStock(offer);
    const priceAvailable = offer.currency === 'CAD' && validPrice(offer.price);
    const dropped = fresh && stock && validPrice(offer.previousPrice) && offer.previousPrice > offer.price;
    const condition = offer.condition && offer.condition !== offer.variant ? `${offer.variant || ''}${offer.variant ? ' · ' : ''}${offer.condition}` : offer.variant || offer.condition || 'Condition not specified';
    const state = !fresh ? badge('Unverified / past check', 'warning') : match ? badge('Below target', 'match') : stock ? badge('In stock', 'instock') : badge('Out of stock', 'soldout');
    const context = !fresh ? 'Last observed price' : match ? `<span class="drop-text">CA$${money(THRESHOLD - offer.price)} below target</span>` : stock ? `CA$${money(Math.max(0, offer.price - THRESHOLD))} ${offer.price === THRESHOLD ? 'at the limit · does not qualify' : 'above target'}` : 'Not counted as a deal';
    return `<article class="offer-card ${match ? 'match' : ''} ${!fresh ? 'stale' : ''}" data-offer-id="${escape(offer.id)}" data-qualified="${match}" data-stock="${stock}"><div class="offer-top"><span class="retailer">${escape(store.name)}</span>${state}</div><h3 class="offer-title">Nico Robin · EB05-010</h3><p class="variant">${escape(condition)}</p><div class="price-row"><div class="offer-price">${priceAvailable ? `<small>CA$</small>${money(offer.price)}` : 'Unverified'}</div><div class="price-context">${context}</div></div>${dropped ? `<div class="drop-text">↓ CA$${money(offer.previousPrice - offer.price)} price drop <span class="price-previous">· was CA$${money(offer.previousPrice)}</span></div>` : ''}<div class="price-facts"><span>Alternate art · English foil</span>${validPrice(offer.minPrice) ? `<span>Lowest seen CA$${money(offer.minPrice)}</span>` : ''}</div><div class="offer-bottom"><span class="checked-time">${escape(date(offer.lastSeen))}</span>${link(offer.url, 'Check retailer ' + EXTERNAL_ICON, 'buy-link')}</div>${!fresh ? '<p class="offer-warning">Current stock and price have not been verified. Check the store directly.</p>' : ''}</article>`;
  }
  function offerSection() {
    let list = [...offers()];
    if (filter === 'instock') list = list.filter(inStock);
    if (filter === 'below') list = list.filter(below);
    list.sort((a,b) => Number(below(b)) - Number(below(a)) || Number(inStock(b)) - Number(inStock(a)) || Number(verified(b)) - Number(verified(a)) || (validPrice(a.price) ? a.price : Infinity) - (validPrice(b.price) ? b.price : Infinity));
    const header = `<div class="section-top"><div><h2 class="section-title">The Canadian watchlist</h2><p class="section-subtitle">Exact-card listings. Stock and price checked together.</p></div><div class="filters" aria-label="Filter listings">${[['all','All listings'],['instock','In stock'],['below','Below CA$50']].map(([id,label]) => `<button type="button" class="filter ${filter === id ? 'active' : ''}" data-filter="${id}" aria-pressed="${filter === id}">${label}</button>`).join('')}</div></div>`;
    if (!feed) return header + empty(feedError ? 'Waiting for a verified check' : 'Your card is on the list', 'A scheduled scan will publish exact matches here. No price or stock is assumed before the first successful check.', true);
    if (!list.length) {
      if (filter === 'below') return header + empty('No verified listings below CA$50', 'Only in-stock, Canadian-dollar listings strictly below your target count. Unverified or older prices are excluded.', true);
      if (filter === 'instock') return header + empty('No current in-stock listings verified', 'Stores may be sold out, unavailable to the checker, or still waiting for a verified match. See Store checks for coverage.', true);
      return header + empty('No exact-card listing verified yet', 'The scanner will only add confirmed EB05-010 alternate-art English foil matches. See Store checks to distinguish no match from an unavailable store.', true);
    }
    return header + `<div class="offer-list">${list.map(priceCard).join('')}</div>`;
  }
  function storeSection() {
    const header = '<div class="section-top"><div><h2 class="section-title">Store checks</h2><p class="section-subtitle">A clear result for each store on the latest scheduled run.</p></div></div>';
    if (!stores().length) return header + empty('First scan pending', 'Store-by-store results will appear after a published scan. The original Enter the Battlefield link is included in the watchlist.', true);
    const labels = {ok:['Checked','instock'],no_match:['No exact match','soldout'],blocked:['Access blocked','warning'],error:['Check failed','error']};
    return header + `<div class="store-list">${stores().map(store => {
      const label = labels[store.status] || ['Not verified','warning'];
      return `<article class="store-row" data-store-id="${escape(store.id)}"><div class="store-top">${link(store.url, escape(store.name), 'store-name') || `<span class="store-name">${escape(store.name)}</span>`}${badge(label[0], label[1])}</div><p class="store-message">${escape(store.message || 'No details available for this check.')}</p><div class="store-check-time">${escape(date(store.checkedAt))}${!isFresh() ? ' · past check' : ''}</div></article>`;
    }).join('')}</div>`;
  }
  function render() {
    app.setAttribute('aria-busy', String(loading));
    const status = !feed ? 'First published check pending' : `${isFresh() ? 'Last published check' : 'Last recorded check'}: ${date(feed.meta.lastChecked)}`;
    app.innerHTML = hero() + `<div class="status-strip"><span class="status-summary"><i class="status-dot ${!feed ? 'pending' : !isFresh() ? 'warning' : ''}" aria-hidden="true"></i><span data-last-checked>${escape(status)}</span></span><span class="cad-note">CANADIAN SELLERS · CAD</span></div>` + notices() + stats() + `<div class="view-tabs" aria-label="Watchlist views"><button type="button" class="view-tab ${view === 'offers' ? 'active' : ''}" data-view="offers" aria-pressed="${view === 'offers'}">Listings<span class="tab-count">${offers().length}</span></button><button type="button" class="view-tab ${view === 'stores' ? 'active' : ''}" data-view="stores" aria-pressed="${view === 'stores'}">Store checks<span class="tab-count">${stores().length}</span></button></div>` + (view === 'stores' ? storeSection() : offerSection()) + `<details class="explanation"><summary>How this watchlist works</summary><div class="explanation-grid"><div><h3>The exact card</h3><p>Nico Robin EB05-010, alternate-art English foil from One Piece Heroines Edition Vol. 2. Other card numbers, regular art, graded cards, and ambiguous listings are excluded.</p></div><div><h3>Your CA$50 rule</h3><p>A qualifying listing must be verified in stock and priced below CA$50.00 in Canadian dollars. Shipping and tax are extra. A first verified find below the target can qualify without a previous price.</p></div><div><h3>Scheduled, with limits</h3><p>Checks run on GitHub approximately every 30 minutes; schedules can be delayed. Refresh loads the latest published results, not a new store scan. Failed checks and observations over two hours old never count as current deals. ${link('./notifications.html', 'Manage alerts ' + EXTERNAL_ICON)}</p></div></div></details>`;
  }
  async function refresh(silent = false) {
    if (loading) return;
    loading = true;
    refreshButton.disabled = true;
    app.setAttribute('aria-busy','true');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`./data/prices.json?t=${Date.now()}`, {cache:'no-store', signal:controller.signal});
      if (!response.ok) throw new Error(`Price feed HTTP ${response.status}`);
      const next = await response.json();
      if (!next || !next.meta || !Array.isArray(next.stores) || !Array.isArray(next.offers) || next.watch?.currency !== 'CAD' || next.watch?.cardId !== 'EB05-010' || Number(next.watch?.threshold) !== THRESHOLD || next.watch?.comparison !== 'below') throw new Error('Invalid or unexpected watchlist feed');
      feed = next;
      feedError = null;
      if (!silent) notify('Latest published price check loaded');
    } catch (error) {
      feedError = error.message;
      if (!silent) notify('Could not load a current price check');
    } finally {
      clearTimeout(timer);
      loading = false;
      refreshButton.disabled = false;
      render();
    }
  }
  document.addEventListener('click', event => {
    const tab = event.target.closest('[data-view]');
    if (tab) { view = tab.dataset.view; render(); return; }
    const selected = event.target.closest('[data-filter]');
    if (selected) { filter = selected.dataset.filter; render(); }
  });
  refreshButton.addEventListener('click', () => refresh());
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(true); });
  window.addEventListener('online', () => refresh(true));
  window.addEventListener('offline', () => { feedError = 'Offline'; render(); });
  setInterval(() => { if (!document.hidden) refresh(true); }, 5 * 60 * 1000);
  setInterval(() => { if (!loading && feed) render(); }, 60 * 1000);
  render();
  refresh(true);
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
  }
})();
