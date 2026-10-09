/* The 25-second tour: a quick, watch-only animatic of the RELEASED app (v0.3.0-beta), derived from ../tour/proto.js.
   Same inert 1440 × 900 srcdoc frame, same released screens (release-screens.js), app.css and frame.css, same
   fictional account (Jordan Wexcombe, Halvard & Wren, INV1056). It skips Sign in and Your name and trims the idle
   holds, the typing and the glides, but stays calm (Daniel: "smooth and a bit draggy over rushed", never "spazzy"):
   ONE move at a time, every result holds >= HOLD before the next move starts, eased cursor glides.
   The timeline is BUILT by a sequencer below rather than hand-typed, so the holds are true by construction.
   Hash flags (any order, joined by &): embed (chrome-less, for the homepage's dialog), light / dark, reduced. */
(() => {
  'use strict';
  const $ = (s, scope = document) => scope.querySelector(s);
  const $$ = (s, scope = document) => [...scope.querySelectorAll(s)];
  const root = document.documentElement, frame = $('#app-frame');
  const { tween, smooth, glide } = window.FM;
  const flags = new Set(location.hash.slice(1).split(/[&,]/).filter(Boolean));
  const media = matchMedia('(prefers-reduced-motion: reduce)');
  let reduced = media.matches || flags.has('reduced');
  const embed = flags.has('embed');
  // the tour's canonical captions 3–7, verbatim (already queued for legal): one per chapter
  // (inside the template's fragment there is no #caption-copy ancestor, so the selector is plain 'p': '#caption-copy p'
  // matches nothing there and left every caption blank)
  const captions = $$('p', $('#caption-copy').content).map(p => p.textContent);

  /* ---------------- the sequencer: pages, cursor actions, typed fields ---------------- */
  const HOLD = .5;                                   // every result holds at least this long before the next move
  const PRESS = .22;                                 // a click's press (.22 s), then the page it opens
  const G = .45;                                     // a cursor glide (the full tour: .65 s); nearby targets glide less
  let t = 0;
  const PAGES = [], ACTIONS = [], FIELDS = [], AT = {};
  // a page arrives at the current time; `settle` = its released entry motion (riseIn .32 s + the filter bar's .08 s
  // delay; the dashboard: the 900 ms count-up with its 80 ms stagger = 1.06 s, outlasting sparkReveal and the bars)
  const page = (screen, settle) => { PAGES.push({ at: t, screen }); AT[screen] = t; t += settle; };
  // a cursor action: hold, glide (g), press; `settle` = how long its result takes to finish
  const click = (name, selector, settle, g = G) => {
    t += HOLD + g; AT[name] = t; ACTIONS.push({ name, at: t, g, selector }); t += settle;
  };
  // a typed field: hold, then either a cursor glide to it (the first field of a row) or the keyboard's Tab (the next)
  const type = (selector, value, duration, cursor, g = G) => {
    t += HOLD + (cursor ? g : 0);
    if (cursor) ACTIONS.push({ name: selector, at: t, g, selector, type: true });
    FIELDS.push({ at: t, duration, selector, value }); AT[selector] = t; t += duration;
  };
  const move = (name, duration) => { t += HOLD; AT[name] = t; t += duration; };   // a content scroll, on its own

  page('dashboard', 1.06); t += .3;                  // the count-up lands; a longer first hold reads the first caption
  click('nav-invoices', '.nav-item[title="Invoices"]', PRESS);
  page('invoices-all', .4);
  click('tab-overdue', '[data-tab-key="overdue"]', .16);           // --d-tab: 160 ms ink
  click('tab-paid', '[data-tab-key="paid"]', .16);
  click('new-invoice', '.page-actions .btn-primary', PRESS);
  page('form', .4);
  // the title is typed (the invoice, the email subject and the paper all say "October work" afterwards)
  type('[name="title"]', 'October work', .45, true);
  click('client-open', '#client-selector .custom-select-trigger', .15);
  click('client-pick', '#client-selector .custom-select-option[data-value="1"]', .2, .35);
  type('[name="desc_0"]', 'Project work', .45, true);
  type('[name="rate_0"]', '75', .2, false);
  type('[name="qty_0"]', '16', .15, false);
  click('add-line', '#invoice-form .mt-2', .1, .4);
  move('scroll', .5);                                 // the second row and Create into view (one scroll, its own move)
  type('[name="desc_1"]', 'Revisions', .4, true, .4);
  type('[name="rate_1"]', '75', .2, false);
  type('[name="qty_1"]', '4', .15, false);
  click('create', '.form-actions .btn-primary', PRESS);
  page('detail', .4);
  click('email', '.page-actions .btn-primary', .15);
  click('send', '#email-compose-send-btn', PRESS + .28);           // compose closes, then the toast's flashIn (.28 s)
  AT.toast = AT.send + PRESS;
  const PAID_CHAPTER = t + .2;
  click('toggle', '.page-actions .status-toggle', .45);            // statusPop (.4 s), then the paid invoice's paper
  AT.paper = AT.toggle + .45;
  click('nav-dashboard', '.nav-item[title="Dashboard"]', PRESS);
  page('dashboard-paid', 1.06);
  const TOTAL = Math.round((t + .2) * 10) / 10;

  const STEPS = [
    { title: 'Dashboard', start: 0 },
    { title: 'Invoices', start: AT['invoices-all'] },
    { title: 'New invoice', start: AT.form },
    { title: 'Email', start: AT.detail },
    { title: 'Paid', start: PAID_CHAPTER },
  ];
  // the cursor: visible from just before each glide to just after its press; short gaps are bridged (no blinking),
  // longer ones fade it out and back in (150 ms), so it never pops
  const SPANS = [];
  ACTIONS.forEach(a => {
    const s = a.at - a.g - .15, e = a.at + .7, last = SPANS.at(-1);
    if (last && s - last.e < .6) last.e = e; else SPANS.push({ s, e });
  });

  const Q = { ready: false, playing: false, chapter: 0, t: 0, total: TOTAL };
  let doc, screen, cursor, ghost, modal, toast, rendered = '', screenAt = 0;
  let raf = 0, last = 0, animationStarts = new WeakMap(), autoplay = !reduced;
  const local = selector => $(selector, screen) || $(selector, modal);
  const money = n => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  const pageAt = s => PAGES.findLast(p => p.at <= s);
  const chapterAt = s => STEPS.findLastIndex(c => c.start <= s);
  const setValue = (el, value) => { if (el && el.value !== value) el.value = value; };
  const typed = (f, s) => f.value.slice(0, Math.floor(f.value.length * tween(s, f.at, f.duration)));
  const ended = () => Q.t >= Q.total;

  function fitFrame() {
    const box = $('#pframe-box');
    if (embed) {
      // the dialog's iframe: the 16:10 window gets whatever height the bar and notes leave, never more than the width
      const player = $('.player'), kids = [...player.children].filter(el => el.getClientRects().length);
      const span = kids.at(-1).getBoundingClientRect().bottom - kids[0].getBoundingClientRect().top;
      const others = span - box.offsetHeight + parseFloat(getComputedStyle(player).paddingBottom);
      const w = Math.floor(Math.min(player.clientWidth, (innerHeight - others) * 1.6));
      if (Math.abs((parseFloat(player.style.getPropertyValue('--fw')) || 0) - w) >= 1) player.style.setProperty('--fw', `${Math.max(160, w)}px`);
    }
    frame.style.transform = `scale(${box.clientWidth / 1440})`;
  }
  function setTheme(theme) {
    root.dataset.theme = theme;
    $$('[data-theme-set]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.themeSet === theme)));
    if (!doc) return;
    if ($('.app', screen) && !reduced) {             // main's app shell crossfades its theme for 240 ms
      doc.documentElement.classList.add('theme-transitioning');
      setTimeout(() => doc.documentElement.classList.remove('theme-transitioning'), 300);
    }
    doc.documentElement.dataset.theme = theme;
  }
  function ui() {
    Q.chapter = chapterAt(Q.t);
    const play = $('#play');
    play.innerHTML = Q.playing ? 'Ⅱ <span>Pause</span>' : '▶ <span>Play</span>';
    play.setAttribute('aria-label', Q.playing ? 'Pause tour' : 'Play tour');
    play.hidden = reduced || ended();
    $('#end-actions').hidden = !reduced && !ended();
    $('#replay').hidden = reduced;
    $('#progress').hidden = reduced;
    $('#progress-fill').style.transform = `scaleX(${Q.t / Q.total})`;
    $('#progress').setAttribute('aria-valuenow', Q.t.toFixed(1));
    $('#time').textContent = reduced ? '' : `${fmt(Q.t)} / ${fmt(Q.total)}`;
    $('#caption-number').textContent = `0${Q.chapter + 1} / 0${STEPS.length}`;
    const cap = captions[Q.chapter + 2];             // captions 3–7 of the full tour
    if ($('#caption').textContent !== cap) $('#caption').textContent = cap;
    $('#player-note').hidden = !reduced;
  }
  function positionInk() {
    $$('.tabs, .invoice-tab-bar', screen).forEach(container => {
      const ink = $('.tab-ink', container), active = $('.active', container);
      if (!ink || !active) return;
      const cr = container.getBoundingClientRect(), r = active.getBoundingClientRect();
      ink.style.transform = `translateX(${r.left - cr.left}px) scaleX(${r.width})`;
    });
  }
  function choose(selector, value) {
    const select = local(selector); if (!select) return;
    select.value = value;
    const wrap = select.closest('.custom-select-wrap');
    $('.custom-select-text', wrap).textContent = select.options[select.selectedIndex].textContent;
    $$('.custom-select-option', wrap).forEach(o => o.classList.toggle('selected', o.dataset.value === value));
  }
  function install(p, force = false) {
    if (rendered === p.screen && !force) return;
    // main/base.html's 150 ms app-page crossfade
    const crossfade = $('.app', screen) && Q.playing && !reduced && !force;
    ghost.replaceChildren();
    if (crossfade) ghost.appendChild(screen.cloneNode(true));
    screen.innerHTML = window.TOUR_SCREENS[p.screen];
    delete screen.dataset.paperPaid;
    rendered = p.screen; screenAt = p.at;
    animationStarts = new WeakMap();
    modal.innerHTML = p.screen === 'detail' ? window.TOUR_SCREENS.email : '';
    toast.innerHTML = '';
    if (p.screen === 'detail') {
      // main's compose shell, populated with this fictional invoice (email preconfigured), as ../tour does
      const input = $('#email-compose-to-input', modal);
      input.insertAdjacentHTML('beforebegin', '<span class="email-tag" data-email="hello@halvardwren.example">hello@halvardwren.example<button type="button" class="email-tag-remove">×</button></span>');
      input.placeholder = '';
      setValue($('#email-compose-subject', modal), 'Invoice INV1056 from Jordan Wexcombe - October work');
      setValue($('#email-compose-body-text', modal), 'Hi,\n\nPlease find attached invoice INV1056 for October work ($1,500.00).\n\nThank you,\nJordan Wexcombe');
      // attachment row: main/app.js::_renderComposeAttachments markup
      $('#email-compose-attachments', modal).innerHTML = '<div class="email-compose-att-row"><span class="email-compose-att-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 1.5H4a1.5 1.5 0 00-1.5 1.5v10A1.5 1.5 0 004 14.5h8a1.5 1.5 0 001.5-1.5V6L9 1.5z"/><path d="M9 1.5V6h4.5"/></svg></span><a href="#" class="email-compose-att-name">INV1056.pdf</a><span class="email-compose-att-type email-compose-att-type-invoice">Invoice</span><button type="button" class="email-tag-remove" title="Remove from this email">×</button></div>';
    }
    positionInk();
  }
  function listState(s) {
    if (!rendered.startsWith('invoices-')) return;
    const tab = s >= AT['tab-paid'] ? 'paid' : s >= AT['tab-overdue'] ? 'overdue' : 'all';
    $$('.tab', screen).forEach(b => b.classList.toggle('active', b.dataset.tabKey === tab));
    let sum = 0;
    $$('tr[data-total]', screen).forEach(row => {
      const show = tab === 'all' || row.dataset.effectiveStatus === tab;
      row.style.display = show ? '' : 'none';
      if (show) sum += +row.dataset.total;
    });
    $('.year-total', screen).textContent = money(sum);
    positionInk();
  }
  function formState(s) {
    if (rendered !== 'form') return;
    const picked = AT['client-pick'] + .2;
    $('#client-dropdown', screen).closest('.custom-select-wrap').classList.toggle('open', s >= AT['client-open'] && s < picked);
    if (s >= picked) {
      choose('#client-dropdown', '1'); choose('#payment-terms-select', 'net_30');
      setValue($('#date-due-input', screen), '2026-11-04');
      const fields = { name: 'Halvard & Wren', email: 'hello@halvardwren.example', city: 'Nashville', state: 'TN' };
      Object.entries(fields).forEach(([k, v]) => setValue($('#cf-' + k, screen), v));
      $$('#client-fields input', screen).forEach(el => { el.readOnly = true; el.classList.add('field-readonly'); });
      const country = $('#cf-country', screen)?.closest('.custom-select-wrap');
      if (country) { country.classList.add('is-locked'); $('.custom-select-trigger', country).disabled = true; }
    }
    if (s >= AT['add-line'] + .1 && !$('[name="desc_1"]', screen)) {
      const row = $('.line-item-row', screen).cloneNode(true);
      $$('input, textarea', row).forEach(el => {
        el.name = el.name.replace('_0', '_1');
        el.value = el.name.startsWith('qty') ? '1' : el.name.startsWith('rate') ? '0.00' : '';
      });
      $('tbody#line-items-body', screen).appendChild(row);
    }
    // row one and Add line sit above the fold at 1440 × 900; ONE eased scroll then brings row two and Create in
    const w = $('.main-wrap', screen);
    w.scrollTop = s >= AT.scroll ? (w.scrollHeight - w.clientHeight) * smooth(tween(s, AT.scroll, .5)) : 0;
  }
  function amounts() {
    if (rendered !== 'form') return;
    let total = 0;
    $$('.line-item-row', screen).forEach(row => {
      const amount = (+$('[name^="rate_"]', row).value || 0) * (+$('[name^="qty_"]', row).value || 0);
      $('.amount-display', row).textContent = money(amount); total += amount;
    });
    ['#invoice-total', '#invoice-balance'].forEach(id => { if (local(id)) local(id).textContent = money(total); });
  }
  function detailState(s) {
    if (rendered !== 'detail') return;
    $('#email-compose-overlay', modal).style.display = s >= AT.email && s < AT.toast ? 'flex' : 'none';
    if (s >= AT.toast && s < AT.toggle && !toast.firstChild) toast.innerHTML = '<div class="flash flash-success" role="status">Email sent.</div>';
    if (s >= AT.toggle) toast.innerHTML = '';
    // main/app.js: status-pop class, the optimistic label/class change after 120 ms, the pop removed 80 ms later
    const pill = $('.page-actions .status-toggle', screen);
    const paid = s >= AT.toggle + .12, pop = s >= AT.toggle && s < AT.toggle + .2;
    const cls = `status-toggle status-${paid ? 'paid' : 'outstanding'}${pop ? ' status-pop' : ''}`;
    if (pill.className !== cls) pill.className = cls;
    pill.textContent = paid ? 'Paid' : 'Outstanding';
    if (s >= AT.paper && !screen.dataset.paperPaid) {
      const tmp = doc.createElement('div'); tmp.innerHTML = window.TOUR_SCREENS['detail-paid'];
      $('.preview-body', screen).innerHTML = $('.preview-body', tmp).innerHTML;
      screen.dataset.paperPaid = 'yes';
    }
  }
  function dashboardState(s) {
    if (!rendered.startsWith('dashboard')) return;
    $$('.kpi-value[data-target]', screen).forEach((el, i) => {
      const target = +el.dataset.target;
      // main/dashboard.html: 900 ms, 80 ms stagger, 30 precomputed frames, easeOutCubic
      const p = reduced ? 1 : Math.round(tween(s, screenAt + i * .08, .9) * 30) / 30;
      el.textContent = '$' + Math.round(target * (1 - (1 - p) ** 3)).toLocaleString('en-US');
    });
  }
  function clockAnimations(s) {
    doc.getAnimations().forEach(a => {
      if (!animationStarts.has(a)) {
        const n = a.animationName;
        const start = ['riseIn', 'sparkReveal', 'barRise'].includes(n) ? screenAt : n === 'statusPop' ? AT.toggle : ['flashIn', 'flashOut'].includes(n) ? AT.toast : s;
        animationStarts.set(a, start);
        a.pause();
      }
      // every app motion runs on the player's one clock: pause freezes it, reduced motion shows its end
      a.currentTime = reduced ? 100000 : Math.max(0, (s - animationStarts.get(a)) * 1000);
    });
  }
  function cursorState(s) {
    const span = SPANS.find(x => s >= x.s && s <= x.e);
    if (reduced || !span) { cursor.style.opacity = 0; return; }
    const idx = ACTIONS.findLastIndex(a => a.at - a.g <= s);
    const a = ACTIONS[Math.max(0, idx)], target = local(a.selector);
    if (target) {
      const r = target.getBoundingClientRect();
      if (r.width && r.height) a.pos = { x: r.left + r.width * .5, y: r.top + r.height * .55 };
    }
    const prev = ACTIONS[idx - 1], from = (prev && prev.pos) || { x: 1260, y: 800 };
    const to = a.pos || from;
    const p = idx < 0 ? from : glide(from, to, tween(s, a.at - a.g, a.g));
    cursor.style.translate = `${p.x - 3}px ${p.y - 3}px`;
    cursor.style.opacity = Math.min(tween(s, span.s, .15), 1 - tween(s, span.e - .15, .15));
    cursor.style.scale = a.type || idx < 0 ? 1 : 1 - .14 * Math.sin(Math.PI * tween(s, a.at, .22));
  }
  function render(force = false) {
    const s = Q.t;
    install(pageAt(s), force);
    screen.style.opacity = 1;
    if (ghost.firstChild) {
      const p = tween(s, screenAt, .15);
      ghost.style.opacity = 1 - p; screen.style.opacity = p;
      if (p === 1) ghost.innerHTML = '';
    }
    listState(s); formState(s);
    FIELDS.forEach(f => { const el = local(f.selector); if (el && s >= f.at) setValue(el, typed(f, s)); });
    amounts(); detailState(s); dashboardState(s);
    clockAnimations(s); cursorState(s); ui();
  }
  function tick(now) {
    if (!Q.playing) return;
    // a stalled frame (a busy page, a throttled window) slows the tour for a moment instead of skipping a move: <= .1 s
    Q.t = Math.min(Q.total, Q.t + Math.min(.1, Math.max(0, now - last) / 1000)); last = now;
    render();
    // plays ONCE, never loops; focus stays where the visitor left it (the dialog's Close, say), never pulled in here
    if (ended()) { pause(); return; }
    raf = requestAnimationFrame(tick);
  }
  function play() {
    if (!Q.ready || reduced || ended() || Q.playing) return;
    autoplay = false;
    Q.playing = true; last = performance.now(); ui(); raf = requestAnimationFrame(tick);
  }
  function pause() { Q.playing = false; cancelAnimationFrame(raf); ui(); }
  function replay() {
    if (!Q.ready || reduced) return;
    pause(); Q.t = 0; render(true); play();
    $('#play').focus({ preventScroll: true });
  }
  window.__tourQuick = {
    get ready() { return Q.ready; }, play, pause, replay,
    state: () => ({ playing: Q.playing, chapter: Q.chapter, t: Q.t, total: Q.total, ended: ended(), reduced }),
    timeline: () => ({ total: TOTAL, hold: HOLD, chapters: STEPS.map(c => ({ ...c })), marks: { ...AT } }),
  };
  $('#play').addEventListener('click', () => Q.playing ? pause() : play());
  $('#replay').addEventListener('click', replay);
  $$('[data-theme-set]').forEach(b => b.addEventListener('click', () => setTheme(b.dataset.themeSet)));
  document.addEventListener('keydown', e => {
    if (e.code !== 'Space' || e.repeat || e.altKey || e.ctrlKey || e.metaKey || e.target.closest?.('button, a, input, textarea, select, [contenteditable]')) return;
    e.preventDefault();
    if (reduced) return;
    if (ended()) replay(); else Q.playing ? pause() : play();
  });
  // #embed: Esc pressed with focus in here (after Tab, or a click on Play) never reaches the homepage's <dialog>, so
  // the embed asks its parent to close it (a bare flag; tour-modal.js only accepts it from its own iframe)
  if (embed && window.parent !== window) document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    e.preventDefault();
    window.parent.postMessage({ tourQuick: 'close' }, location.origin === 'null' ? '*' : location.origin);
  });
  window.addEventListener('resize', fitFrame);
  if (window.ResizeObserver) new ResizeObserver(fitFrame).observe($('#pframe-box'));
  // a hidden tab pauses (the dialog's iframe reports its tab's visibility too); a pending autoplay waits for it
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && Q.playing) pause();
    else if (!document.hidden && autoplay) play();
  });
  media.addEventListener('change', e => {
    reduced = e.matches || flags.has('reduced');
    if (!Q.ready) return;
    doc.documentElement.dataset.motion = reduced ? 'reduced' : 'full';
    pause();
    if (reduced) Q.t = Q.total;
    render(true);
  });
  root.dataset.theme = flags.has('light') ? 'light' : 'dark';
  root.classList.toggle('embed', embed);
  $('#progress').setAttribute('aria-valuemax', String(TOTAL));
  if (embed) $$('a[data-full-tour]').forEach(a => { a.target = '_top'; });   // in the dialog: leave the homepage for it
  frame.addEventListener('load', async () => {
    doc = frame.contentDocument;
    screen = $('#screen', doc); cursor = $('#fe-cursor', doc); ghost = $('#page-ghost', doc);
    modal = $('#modal-root', doc); toast = $('#tour-flash', doc);
    doc.documentElement.dataset.motion = reduced ? 'reduced' : 'full';
    setTheme(root.dataset.theme); fitFrame();
    install(PAGES[0], true);
    await doc.fonts.load('400 14px Inter');
    await doc.fonts.load('600 14px Inter');
    await doc.fonts.ready;
    Q.ready = true;
    // reduced motion: no playback, the final dashboard with its caption
    if (reduced) Q.t = Q.total;
    render(true);
    if (!document.hidden) play();
  }, { once: true });
  frame.srcdoc = `<!doctype html><html lang="en" data-theme="${root.dataset.theme}"><head><meta charset="utf-8"><link rel="stylesheet" href="app.css"><link rel="stylesheet" href="frame.css"></head><body inert><div id="screen"></div><div id="page-ghost" aria-hidden="true"></div><div id="modal-root"></div><div id="tour-flash" class="flash-container"></div><svg id="fe-cursor" class="fe-cursor" viewBox="0 0 28 40" aria-hidden="true"><path d="M3 3 L3 31.5 L10 25 L14.6 35.6 L19.3 33.6 L14.8 23.2 L24.2 23.2 Z" fill="#111" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/></svg></body></html>`;
})();
