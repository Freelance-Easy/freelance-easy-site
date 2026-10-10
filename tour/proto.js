/* Watch-only harness adapted from ../app/proto.js: STEPS / ENTER / PLAY, cursor,
   captions, chapter chips and scaled viewport. Application visuals are main's.
   A single timeline drives presentation and released-state mutations; no app APIs. */
(() => {
  'use strict';
  const $ = (s, scope = document) => scope.querySelector(s);
  const $$ = (s, scope = document) => [...scope.querySelectorAll(s)];
  const root = document.documentElement, frame = $('#app-frame');
  const { clamp, tween, smooth, glide } = window.FM;
  const media = matchMedia('(prefers-reduced-motion: reduce)');
  let reduced = media.matches || location.hash === '#reduced';
  // (a template's content has no #caption-copy inside it: select its paragraphs directly)
  const captions = $$('p', $('#caption-copy').content).map(p => p.textContent);
  const STEPS = [
    { title: 'Sign in', start: 0, end: 8 },
    { title: 'Your name', start: 8, end: 20 },
    { title: 'Dashboard', start: 20, end: 28 },
    { title: 'Invoices', start: 28, end: 40 },
    { title: 'New invoice', start: 40, end: 62 },
    { title: 'Email', start: 62, end: 72 },
    { title: 'Paid', start: 72, end: 80 },
  ];
  // Page changes match main/base.html's 150ms crossfade. The app's own riseIn,
  // sparkReveal and barRise run from the unmodified released CSS.
  const PAGES = [
    { at: 0, screen: 'login' }, { at: 8, screen: 'onboarding' },
    { at: 20, screen: 'dashboard' }, { at: 28, screen: 'invoices-all' },
    { at: 40, screen: 'form' }, { at: 60.2, screen: 'detail' },
    { at: 76.5, screen: 'dashboard-paid' },
  ];
  // All input is internal to the replay; these records can also drive a future scroll variant.
  const FIELDS = [
    { at: 9.8, duration: 1.5, selector: '#onboarding-name-input', value: 'Jordan Wexcombe' },
    { at: 42, duration: 1, selector: '[name="title"]', value: 'October work' },
    { at: 49, duration: .8, selector: '[name="desc_0"]', value: 'Project work' },
    { at: 50.7, duration: .3, selector: '[name="rate_0"]', value: '75' },
    { at: 51.9, duration: .2, selector: '[name="qty_0"]', value: '16' },
    { at: 54, duration: .6, selector: '[name="desc_1"]', value: 'Revisions' },
    { at: 55.5, duration: .3, selector: '[name="rate_1"]', value: '75' },
    { at: 56.7, duration: .2, selector: '[name="qty_1"]', value: '4' },
    { at: 66.2, duration: 1.3, selector: '#email-compose-body-text', prefix: 'Hi,\n\nPlease find attached invoice INV1056 for October work ($1,500.00).\n\nThank you,\nJordan Wexcombe', value: '\n\nThanks again.' },
  ];
  const ACTIONS = [
    { at: 2.8, selector: '#btn-google-oauth' },
    { at: 9.7, selector: '#onboarding-name-input', type: true },
    { at: 13, selector: '[name="accept_terms"]' },
    { at: 17.8, selector: '.onboarding-actions button' },
    { at: 27.4, selector: '.nav-item[title="Invoices"]' },
    { at: 30.2, selector: '[data-tab-key="outstanding"]' },
    { at: 32.6, selector: '[data-tab-key="overdue"]' },
    { at: 35, selector: '[data-tab-key="paid"]' },
    { at: 37.4, selector: '[data-tab-key="all"]' },
    { at: 39.4, selector: '.page-actions .btn-primary' },
    { at: 41.9, selector: '[name="title"]', type: true },
    { at: 44.4, selector: '#client-selector .custom-select-trigger' },
    { at: 46.2, selector: '#client-selector .custom-select-option[data-value="1"]' },
    { at: 48.9, selector: '[name="desc_0"]', type: true },
    { at: 50.6, selector: '[name="rate_0"]', type: true },
    { at: 51.8, selector: '[name="qty_0"]', type: true },
    { at: 53.1, selector: '#invoice-form .mt-2' },
    { at: 53.9, selector: '[name="desc_1"]', type: true },
    { at: 55.4, selector: '[name="rate_1"]', type: true },
    { at: 56.6, selector: '[name="qty_1"]', type: true },
    { at: 59.4, selector: '.form-actions .btn-primary' },
    { at: 64, selector: '.page-actions .btn-primary' },
    { at: 66.1, selector: '#email-compose-body-text', type: true },
    { at: 69.2, selector: '#email-compose-send-btn' },
    { at: 74, selector: '.page-actions .status-toggle' },
    { at: 75.9, selector: '.nav-item[title="Dashboard"]' },
  ];
  const TOUR = { ready: false, playing: false, chapter: 0, t: 0, total: 80 };
  let doc, screen, cursor, ghost, modal, toast, rendered = '', screenAt = 0;
  let staticPreview = false;
  let raf = 0, last = 0, animationStarts = new WeakMap(), cursorFrom = { x: 1260, y: 800 }, cursorTo = null, actionIndex = -1;
  const local = selector => $(selector, screen) || $(selector, modal);
  const money = n => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmt = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  const pageAt = t => PAGES.findLast(p => p.at <= t);
  const chapterAt = t => STEPS.findLastIndex(s => s.start <= t);
  const setValue = (el, value) => { if (el && el.value !== value) el.value = value; };
  const typed = (field, t) => (field.prefix || '') + field.value.slice(0, Math.floor(field.value.length * tween(t, field.at, field.duration)));
  function fitFrame() { frame.style.transform = `scale(${$('#pframe-box').clientWidth / 1440})`; }
  function setTheme(theme) {
    root.dataset.theme = theme;
    $$('[data-theme-set]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.themeSet === theme)));
    if (!doc) return;
    // Main's standalone auth pages change theme immediately; its app shell crossfades for 240ms.
    if ($('.app', screen) && !reduced) {
      doc.documentElement.classList.add('theme-transitioning');
      setTimeout(() => doc.documentElement.classList.remove('theme-transitioning'), 300);
    }
    doc.documentElement.dataset.theme = theme;
  }
  function ui() {
    TOUR.chapter = chapterAt(TOUR.t);
    $('#play').innerHTML = TOUR.playing ? 'Ⅱ <span>Pause</span>' : '▶ <span>Play</span>';
    $('#play').setAttribute('aria-label', TOUR.playing ? 'Pause tour' : 'Play tour');
    $('#play').hidden = reduced || TOUR.t >= TOUR.total;
    $('#replay').hidden = reduced || TOUR.t < TOUR.total;
    $('#progress-fill').style.transform = `scaleX(${TOUR.t / TOUR.total})`;
    $('#progress').setAttribute('aria-valuenow', TOUR.t.toFixed(1));
    $('#time').textContent = `${fmt(TOUR.t)} / ${fmt(TOUR.total)}`;
    $('#caption-number').textContent = `0${TOUR.chapter + 1} / 07`;
    if ($('#caption').textContent !== captions[TOUR.chapter]) $('#caption').textContent = captions[TOUR.chapter];
    $$('[data-chapter]').forEach(b => {
      if (+b.dataset.chapter === TOUR.chapter) b.setAttribute('aria-current', 'step');
      else b.removeAttribute('aria-current');
    });
    $('#player-note').textContent = reduced ? 'Reduced motion · Choose a chapter to view its final screen.' : 'Watch only · 1 min 20 sec · Space to play or pause';
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
  function install(page, force = false) {
    if (rendered === page.screen && !force) return;
    const crossfade = $('.app', screen) && !['login', 'onboarding'].includes(page.screen) && TOUR.playing && !reduced && !force;
    ghost.replaceChildren();
    if (crossfade) ghost.appendChild(screen.cloneNode(true));
    screen.innerHTML = window.TOUR_SCREENS[page.screen];
    delete screen.dataset.paperPaid;
    rendered = page.screen; screenAt = page.at;
    animationStarts = new WeakMap(); cursorFrom = { x: 1260, y: 800 }; cursorTo = null; actionIndex = -1;
    modal.innerHTML = page.screen === 'detail' ? window.TOUR_SCREENS.email : '';
    toast.innerHTML = '';
    if (page.screen === 'detail') {
      // Main's compose shell, populated with this fictional invoice (email preconfigured).
      const input = $('#email-compose-to-input', modal);
      input.insertAdjacentHTML('beforebegin', '<span class="email-tag" data-email="hello@halvardwren.example">hello@halvardwren.example<button type="button" class="email-tag-remove">×</button></span>');
      input.placeholder = '';
      setValue($('#email-compose-subject', modal), 'Invoice INV1056 from Jordan Wexcombe - October work');
      setValue($('#email-compose-body-text', modal), FIELDS.at(-1).prefix);
      // Attachment row uses main/app.js::_renderComposeAttachments markup.
      $('#email-compose-attachments', modal).innerHTML = '<div class="email-compose-att-row"><span class="email-compose-att-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 1.5H4a1.5 1.5 0 00-1.5 1.5v10A1.5 1.5 0 004 14.5h8a1.5 1.5 0 001.5-1.5V6L9 1.5z"/><path d="M9 1.5V6h4.5"/></svg></span><a href="#" class="email-compose-att-name">INV1056.pdf</a><span class="email-compose-att-type email-compose-att-type-invoice">Invoice</span><button type="button" class="email-tag-remove" title="Remove from this email">×</button></div>';
    }
    positionInk();
  }
  function listState(t) {
    if (!rendered.startsWith('invoices-')) return;
    const tab = t >= 37.4 ? 'all' : t >= 35 ? 'paid' : t >= 32.6 ? 'overdue' : t >= 30.2 ? 'outstanding' : 'all';
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
  function formState(t) {
    if (rendered !== 'form') return;
    const wrap = $('#client-dropdown', screen).closest('.custom-select-wrap');
    wrap.classList.toggle('open', t >= 44.4 && t < 46.4);
    if (t >= 46.4) {
      choose('#client-dropdown', '1'); choose('#payment-terms-select', 'net_30');
      setValue($('#date-due-input', screen), '2026-11-04');
      const fields = { name: 'Halvard & Wren', email: 'hello@halvardwren.example', city: 'Nashville', state: 'TN' };
      Object.entries(fields).forEach(([k, v]) => setValue($('#cf-' + k, screen), v));
      $$('#client-fields input', screen).forEach(el => { el.readOnly = true; el.classList.add('field-readonly'); });
      const country = $('#cf-country', screen)?.closest('.custom-select-wrap');
      if (country) { country.classList.add('is-locked'); $('.custom-select-trigger', country).disabled = true; }
    }
    if (t >= 53.1 && !$('[name="desc_1"]', screen)) {
      const row = $('.line-item-row', screen).cloneNode(true);
      $$('input, textarea', row).forEach(el => {
        el.name = el.name.replace('_0', '_1');
        el.value = el.name.startsWith('qty') ? '1' : el.name.startsWith('rate') ? '0.00' : '';
      });
      $('tbody#line-items-body', screen).appendChild(row);
    }
    const w = $('.main-wrap', screen);
    const line = $('.line-items-table', screen), create = $('.form-actions', screen);
    const topFor = el => el.getBoundingClientRect().top - w.getBoundingClientRect().top + w.scrollTop;
    const lineScroll = Math.max(0, topFor(line) - 260);
    const createScroll = Math.min(w.scrollHeight - w.clientHeight, Math.max(0, topFor(create) - 700));
    if (t >= 58) w.scrollTop = lineScroll + (createScroll - lineScroll) * smooth(tween(t, 58, .65));
    else if (t >= 47.5) w.scrollTop = lineScroll * smooth(tween(t, 47.5, .65));
    else w.scrollTop = 0;
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
  function detailState(t) {
    if (rendered !== 'detail') return;
    const overlay = $('#email-compose-overlay', modal);
    overlay.style.display = t >= 64 && t < 70.3 ? 'flex' : 'none';
    if (t >= 70.3 && t < 74.2 && !toast.firstChild) toast.innerHTML = '<div class="flash flash-success" role="status">Email sent.</div>';
    if (t >= 74.2) toast.innerHTML = '';
    const pill = $('.page-actions .status-toggle', screen);
    const paid = t >= 74.12;
    const pop = t >= 74 && t < 74.2;
    const cls = `status-toggle status-${paid ? 'paid' : 'outstanding'}${pop ? ' status-pop' : ''}`;
    if (pill.className !== cls) pill.className = cls;
    pill.textContent = paid ? 'Paid' : 'Outstanding';
    if (t >= 74.7 && !screen.dataset.paperPaid) {
      const tmp = doc.createElement('div'); tmp.innerHTML = window.TOUR_SCREENS['detail-paid'];
      $('.preview-body', screen).innerHTML = $('.preview-body', tmp).innerHTML;
      screen.dataset.paperPaid = 'yes';
    }
  }
  function dashboardState(t) {
    if (!rendered.startsWith('dashboard')) return;
    $$('.kpi-value[data-target]', screen).forEach((el, i) => {
      const target = +el.dataset.target;
      // Main/dashboard.html: 900ms, 80ms stagger, 30 precomputed frames, easeOutCubic.
      const progress = reduced || staticPreview ? 1 : Math.round(tween(t, screenAt + i * .08, .9) * 30) / 30;
      el.textContent = '$' + Math.round(target * (1 - (1 - progress) ** 3)).toLocaleString('en-US');
    });
  }
  function clockAnimations(t) {
    doc.getAnimations().forEach(a => {
      if (!animationStarts.has(a)) {
        const start = ['riseIn', 'sparkReveal', 'barRise'].includes(a.animationName) ? screenAt : a.animationName === 'statusPop' ? 74 : ['flashIn', 'flashOut'].includes(a.animationName) ? 70.3 : t;
        animationStarts.set(a, start);
        a.pause();
      }
      const elapsed = Math.max(0, (t - animationStarts.get(a)) * 1000);
      // Freeze all app motion on the same clock; pause must freeze spinner and CSS too.
      a.currentTime = reduced || staticPreview ? 100000 : elapsed;
    });
  }
  function cursorState(t) {
    if (reduced) { cursor.style.opacity = 0; return; }
    const idx = ACTIONS.findLastIndex(a => a.at - .65 <= t);
    const a = ACTIONS[idx], target = a && local(a.selector);
    if (!a || !target || t > a.at + .6) { cursor.style.opacity = 0; return; }
    const r = target.getBoundingClientRect();
    const to = r.width && r.height ? { x: r.left + r.width * .5, y: r.top + r.height * .55 } : cursorTo;
    if (!to) { cursor.style.opacity = 0; return; }
    cursorTo = to;
    if (actionIndex !== idx) {
      const previous = ACTIONS[idx - 1], prevEl = previous && local(previous.selector);
      if (prevEl) { const pr = prevEl.getBoundingClientRect(); cursorFrom = { x: pr.left + pr.width * .5, y: pr.top + pr.height * .55 }; }
      actionIndex = idx;
    }
    const p = glide(cursorFrom, to, tween(t, a.at - .65, .65));
    cursor.style.translate = `${p.x - 3}px ${p.y - 3}px`;
    cursor.style.opacity = 1;
    cursor.style.scale = a.type ? 1 : 1 - .14 * Math.sin(Math.PI * tween(t, a.at, .22));
  }
  function render(force = false, preview = false) {
    if (force) staticPreview = preview;
    const t = TOUR.t;
    install(pageAt(t), force);
    screen.style.opacity = 1;
    if (ghost.firstChild) {
      const p = tween(t, screenAt, .15);
      ghost.style.opacity = 1 - p; screen.style.opacity = p;
      if (p === 1) ghost.innerHTML = '';
    }
    if (rendered === 'login') {
      $('#login-state', screen).hidden = t >= 2.95;
      $('#waiting-state', screen).hidden = t < 2.95;
      $('#waiting-sub', screen).textContent = 'Sign in opened in your browser. This window will refresh once you finish.';
    }
    if (rendered === 'onboarding') $('[name="accept_terms"]', screen).checked = t >= 13;
    listState(t); formState(t);
    FIELDS.forEach(f => { const el = local(f.selector); if (el && t >= f.at) setValue(el, typed(f, t)); });
    amounts(); detailState(t); dashboardState(t);
    clockAnimations(t); cursorState(t); ui();
  }
  function tick(now) {
    if (!TOUR.playing) return;
    TOUR.t = Math.min(TOUR.total, TOUR.t + Math.max(0, now - last) / 1000); last = now;
    render();
    if (TOUR.t >= TOUR.total) { pause(); return; }
    raf = requestAnimationFrame(tick);
  }
  function play() {
    if (!TOUR.ready || reduced || TOUR.t >= TOUR.total || TOUR.playing) return;
    staticPreview = false;
    TOUR.playing = true; last = performance.now(); ui(); raf = requestAnimationFrame(tick);
  }
  function pause() { TOUR.playing = false; cancelAnimationFrame(raf); ui(); }
  function jump(k) {
    if (!TOUR.ready) return;
    if (typeof k === 'string') k = STEPS.findIndex(s => s.title.toLowerCase() === k.toLowerCase());
    if (!Number.isInteger(k) || k < 0 || k >= STEPS.length) throw new RangeError('Chapter must be 0–6 or its label.');
    const wasPlaying = TOUR.playing; pause();
    TOUR.t = reduced ? STEPS[k].end - .001 : STEPS[k].start;
    delete screen.dataset.paperPaid;
    render(true, !wasPlaying);
    if (wasPlaying && !reduced) play();
  }
  function replay() { pause(); TOUR.t = 0; delete screen.dataset.paperPaid; render(true); play(); }
  window.__tour = {
    get ready() { return TOUR.ready; }, play, pause, jump,
    state: () => ({ playing: TOUR.playing, chapter: TOUR.chapter, t: TOUR.t, total: TOUR.total }),
  };
  $('#play').addEventListener('click', () => TOUR.playing ? pause() : play());
  $('#replay').addEventListener('click', replay);
  $$('[data-chapter]').forEach(b => b.addEventListener('click', () => jump(+b.dataset.chapter)));
  $$('[data-theme-set]').forEach(b => b.addEventListener('click', () => setTheme(b.dataset.themeSet)));
  document.addEventListener('keydown', e => {
    if (e.code !== 'Space' || e.repeat || e.altKey || e.ctrlKey || e.metaKey || e.target.closest?.('input, textarea, select, [contenteditable]')) return;
    e.preventDefault();
    if (reduced) return;
    if (TOUR.t >= TOUR.total) replay(); else TOUR.playing ? pause() : play();
  });
  window.addEventListener('resize', fitFrame);
  document.addEventListener('visibilitychange', () => { if (document.hidden && TOUR.playing) pause(); });
  media.addEventListener('change', e => {
    reduced = e.matches || location.hash === '#reduced';
    if (!TOUR.ready) return;
    doc.documentElement.dataset.motion = reduced ? 'reduced' : 'full';
    pause(); jump(TOUR.chapter);
  });
  root.dataset.theme = location.hash === '#light' ? 'light' : 'dark';
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
    TOUR.ready = true;
    if (reduced) TOUR.t = STEPS[0].end - .001;
    render(true, true);
  }, { once: true });
  frame.srcdoc = `<!doctype html><html lang="en" data-theme="${root.dataset.theme}"><head><meta charset="utf-8"><link rel="stylesheet" href="app.css"><link rel="stylesheet" href="frame.css"></head><body inert><div id="screen"></div><div id="page-ghost" aria-hidden="true"></div><div id="modal-root"></div><div id="tour-flash" class="flash-container"></div><svg id="fe-cursor" class="fe-cursor" viewBox="0 0 28 40" aria-hidden="true"><path d="M3 3 L3 31.5 L10 25 L14.6 35.6 L19.3 33.6 L14.8 23.2 L24.2 23.2 Z" fill="#111" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/></svg></body></html>`;
})();
