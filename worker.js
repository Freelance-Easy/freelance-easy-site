/* Freelance Easy — site Worker.
 *
 * Three jobs, nothing else:
 *   1. Serve the static site (everything under this folder) through the
 *      ASSETS binding, so `_redirects` and `_headers` keep working exactly as
 *      before this file existed.
 *   2. Serve the Mac installer from this domain at /dl/mac/<label> and
 *      /download/mac (see macDownload below; wrangler.toml runs the Worker
 *      first for those paths).
 *   3. Proxy Plausible Analytics through our own domain — the script at
 *      /js/script.js and the event endpoint at /api/event. Plausible is
 *      cookieless and records no personal data; proxying is disclosed in
 *      /privacy ("served through our own domain"). Only the headers Plausible
 *      needs are forwarded (no cookies; there are none on this site anyway).
 *
 * THE SWITCH is SCRIPT_UPSTREAM. While it holds "REPLACE_ME", analytics is
 * off: the script route answers an empty script (a 200, cached briefly, so no
 * page logs an error) and the event route drops anything sent to it, so
 * nothing leaves the site. Switching on = putting the site's own script URL
 * from Plausible (Site settings → General → Site installation) here, the same
 * day /privacy describes the analytics (legal v2). Even then, only the
 * production hostnames count: a branch preview (*.workers.dev) or a local
 * server gets the empty script and its events are dropped, so our own test
 * visits never reach the statistics. And only the events /privacy lists are
 * forwarded (FORWARDED_EVENTS: pageviews, Plausible's engagement event, and
 * Download Click with its four properties); anything else stops here.
 */

const SCRIPT_PATH = "/js/script.js";
const EVENT_PATH = "/api/event";

// Plausible issues a per-site script (https://plausible.io/js/pa-<id>.js).
// Keep "REPLACE_ME" until the day analytics is switched on.
const SCRIPT_UPSTREAM = "https://plausible.io/js/pa-REPLACE_ME.js";
const EVENT_UPSTREAM = "https://plausible.io/api/event";

// The only hostnames whose visits are counted, and the site's domain as
// Plausible knows it (the `d` its script sends).
const COUNTED_HOSTS = new Set(["freelance-easy.com", "www.freelance-easy.com"]);
const SITE_DOMAIN = "freelance-easy.com";

// The only events forwarded, with the only properties each may carry: what
// /privacy §3 lists (legal v2: the pages viewed, how long they stay open and
// how far they're scrolled, and which download button was clicked). Plausible's
// script sends "engagement" on its own (time on page, scroll depth). Anything
// else is dropped here. Adding an event or a property needs a §3 line first,
// then an entry here.
const FORWARDED_EVENTS = new Map([
  ["pageview", new Set()],
  ["engagement", new Set()],
  ["Download Click", new Set(["os", "campaign", "page", "placement"])],
]);
const MAX_EVENT_BYTES = 8192;

function counted(url) {
  return !SCRIPT_UPSTREAM.includes("REPLACE_ME") && COUNTED_HOSTS.has(url.hostname);
}

// At most `max` bytes of the body, decoded as strict UTF-8; null when it is
// larger (a declared Content-Length over the cap is refused before reading;
// an undeclared one is cut off at the cap), not UTF-8, or unreadable.
async function readCapped(request, max) {
  const declared = Number(request.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > max) return null;
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > max) {
        await reader.cancel().catch(() => {});
        return null;
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(total);
    let at = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, at);
      at += chunk.byteLength;
    }
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (e) {
    return null;
  }
}

const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const isText = (v, max) => typeof v === "string" && v.length <= max;
const isCount = (v) => typeof v === "number" && Number.isFinite(v) && v >= 0;
const MAX_URL = 2048;

// An http(s) URL without credentials, parsed by the WHATWG parser, or null.
// Plausible is sent its canonical form (href), so Plausible's own URL parser
// reads the same host that was checked here: an input such as
// "https://freelance-easy.com\\@evil.example/x" parses differently elsewhere,
// its canonical form doesn't.
function httpUrl(value) {
  try {
    const url = new URL(value);
    const ok = (url.protocol === "https:" || url.protocol === "http:") && !url.username && !url.password;
    return ok ? url : null;
  } catch (err) {
    return null;
  }
}

// The referrer the script sends (document.referrer, or null), canonical; null
// when it isn't an http(s) URL; cut to its origin and path when it's too long.
// A referrer never drops the event it came with.
function referrer(value) {
  const url = typeof value === "string" && value ? httpUrl(value) : null;
  if (!url) return null;
  return url.href.length <= MAX_URL ? url.href : (url.origin + url.pathname).slice(0, MAX_URL);
}

// The event the page sent, in the browser format of Plausible's script
// ({n: name, u: page URL, d: domain, r: referrer, v: script version, p: props,
// and for engagement sd: scroll depth, e: time}), rebuilt from those known
// fields only; null to drop it. Plausible gets the rebuilt copy, never the
// raw body, so a field nobody listed here (a legacy property field such as
// `m`, `meta` or `props`, revenue `$`, anything new) can't reach it, and what
// it parses is exactly what was checked.
function rebuild(text) {
  let e;
  try {
    e = JSON.parse(text);
  } catch (err) {
    return null;
  }
  if (!isObject(e)) return null;
  const allowedProps = typeof e.n === "string" ? FORWARDED_EVENTS.get(e.n) : undefined;
  if (!allowedProps || e.d !== SITE_DOMAIN) return null;
  const page = isText(e.u, MAX_URL) ? httpUrl(e.u) : null;
  if (!page || !COUNTED_HOSTS.has(page.hostname) || page.href.length > MAX_URL) return null;
  const out = { n: e.n, u: page.href, d: e.d };
  if (e.r !== undefined) out.r = referrer(e.r);
  if (e.v !== undefined) {
    if (!isCount(e.v) && !isText(e.v, 32)) return null;
    out.v = e.v;
  }
  if (e.h !== undefined) {
    if (![0, 1, true, false].includes(e.h)) return null;
    out.h = e.h;
  }
  if (e.i !== undefined) {
    if (typeof e.i !== "boolean") return null;
    out.i = e.i;
  }
  if (e.n === "engagement") {
    if (!isCount(e.sd) || !isCount(e.e)) return null;
    out.sd = e.sd;
    out.e = e.e;
  }
  if (e.p !== undefined && e.p !== null) {
    if (!isObject(e.p)) return null;
    const keys = Object.keys(e.p);
    if (!keys.every((k) => allowedProps.has(k) && isText(e.p[k], 64))) return null;
    if (keys.length) out.p = Object.fromEntries(keys.map((k) => [k, e.p[k]]));
  }
  return out;
}

// ---- The Mac download, served from this domain -------------------------------
// Google's "Free desktop software" policy (13528034) wants the installer
// "directly downloadable from your website", so /dl/mac/<label> and
// /download/mac answer with the DMG itself as a 200 from freelance-easy.com,
// not a redirect to GitHub. The file stays on GitHub Releases: the Worker
// resolves "latest" to its tag (the redirect GitHub's latest/download link
// answers with, cached for a few minutes) and streams the versioned asset
// through, so a new release never mixes with an old one. Rules kept from the
// old _redirects lines: the label (/dl/mac/<label>) never reaches the file or
// GitHub, nor does any query string; the visitor's IP, cookies and user agent
// never reach GitHub either. A Range request passes through (206), so a
// resumed download works; an upstream error keeps its status (never a 200
// with an error page saved as a .dmg). App updates still come from GitHub.
const DL_ORIGIN = "https://github.com";
const DL_REPO_PATH = "/Freelance-Easy/InvoiceGenerator-releases/releases";
const DL_RELEASES = DL_ORIGIN + DL_REPO_PATH;
const DL_FILE = "Freelance-Easy.dmg";
const DL_TAG_OK = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const DL_TAG_KEY = "https://freelance-easy.com/__internal/latest-mac-tag";
const DL_TAG_SECONDS = 300; // the only thing cached: latest -> tag metadata, never the installer or a 206
const DL_UA = "freelance-easy-site (download proxy)";
const REDIRECTS = new Set([301, 302, 303, 307, 308]);

function isMacDownload(pathname) {
  return pathname === "/download/mac" || pathname.startsWith("/dl/mac/");
}

// The tag in a redirect target, only if it is exactly
// https://github.com/<our repo>/releases/download/<tag>/Freelance-Easy.dmg.
function tagFromLocation(location) {
  let url;
  try {
    url = new URL(location, DL_ORIGIN);
  } catch (err) {
    return null;
  }
  if (url.origin !== DL_ORIGIN || url.search || url.hash) return null;
  const prefix = DL_REPO_PATH + "/download/";
  const suffix = "/" + DL_FILE;
  if (!url.pathname.startsWith(prefix) || !url.pathname.endsWith(suffix)) return null;
  const tag = url.pathname.slice(prefix.length, url.pathname.length - suffix.length);
  return DL_TAG_OK.test(tag) ? tag : null;
}

// The latest release's tag: { tag } or { status } (the resolver's own error
// status when GitHub answered one, else 502).
async function latestMacTag(ctx) {
  const cache = caches.default;
  const key = new Request(DL_TAG_KEY);
  try {
    const hit = await cache.match(key);
    if (hit) {
      const tag = (await hit.text()).trim();
      if (DL_TAG_OK.test(tag)) return { tag };
    }
  } catch (err) {
    // a cache read failure is a miss
  }
  let res;
  try {
    res = await fetch(`${DL_RELEASES}/latest/download/${DL_FILE}`, {
      method: "HEAD",
      redirect: "manual",
      headers: { "user-agent": DL_UA },
    });
  } catch (err) {
    return { status: 502 };
  }
  if (res.status >= 400) return { status: res.status };
  const tag = REDIRECTS.has(res.status) ? tagFromLocation(res.headers.get("location") || "") : null;
  if (!tag) return { status: 502 };
  ctx.waitUntil(
    Promise.resolve()
      .then(() => cache.put(key, new Response(tag, { headers: { "cache-control": `public, max-age=${DL_TAG_SECONDS}` } })))
      .catch(() => {}),
  );
  return { tag };
}

function downloadUnavailable(status, extra = {}) {
  return new Response("The download is unavailable right now. Please try again in a minute.\n", {
    status,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store", ...extra },
  });
}

async function macDownload(request, ctx) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response(null, { status: 405, headers: { allow: "GET, HEAD", "cache-control": "no-store" } });
  }
  const latest = await latestMacTag(ctx);
  if (!latest.tag) return downloadUnavailable(latest.status);
  const tag = latest.tag;
  // A fresh header set: only our user agent, a best-effort identity encoding
  // (Cloudflare may rewrite Accept-Encoding on the way out; the content-encoding
  // check below is what guarantees an unencoded body) and the visitor's Range /
  // If-Range. Seen on a deployed preview: outside servers get Cloudflare's
  // addresses, never the visitor's IP.
  const headers = new Headers({ "user-agent": DL_UA, "accept-encoding": "identity" });
  for (const name of ["range", "if-range"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  let upstream;
  try {
    upstream = await fetch(`${DL_RELEASES}/download/${tag}/${DL_FILE}`, { method: request.method, headers, redirect: "follow" });
  } catch (err) {
    return downloadUnavailable(502);
  }
  if (upstream.status !== 200 && upstream.status !== 206) {
    if (upstream.body) await upstream.body.cancel().catch(() => {});
    if (upstream.status === 416) {
      const range = upstream.headers.get("content-range");
      return downloadUnavailable(416, range ? { "content-range": range } : {});
    }
    return downloadUnavailable(upstream.status >= 400 ? upstream.status : 502);
  }
  const out = new Headers({
    "content-type": "application/x-apple-diskimage",
    "content-disposition": `attachment; filename="${DL_FILE}"`,
    "accept-ranges": "bytes",
    "cache-control": "no-store, no-transform",
    "x-robots-tag": "noindex",
  });
  if (upstream.headers.get("content-encoding")) {
    // Never pass on an encoded body under the DMG's name and length.
    if (upstream.body) await upstream.body.cancel().catch(() => {});
    return downloadUnavailable(502);
  }
  for (const name of ["content-length", "content-range", "etag", "last-modified"]) {
    const value = upstream.headers.get(name);
    if (value) out.set(name, value);
  }
  if (request.method === "HEAD" && upstream.body) await upstream.body.cancel().catch(() => {});
  return new Response(request.method === "HEAD" ? null : upstream.body, { status: upstream.status, headers: out });
}

function dropped() {
  return new Response(null, { status: 202, headers: { "cache-control": "no-store" } });
}

async function proxyScript(request, ctx, url) {
  if (!counted(url)) {
    return new Response("/* analytics off here */\n", {
      status: 200,
      headers: {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "public, max-age=300",
      },
    });
  }
  const cache = caches.default;
  const cacheKey = new Request(url.origin + SCRIPT_PATH, {
    method: "GET",
  });
  let response = await cache.match(cacheKey);
  if (!response) {
    const upstream = await fetch(SCRIPT_UPSTREAM, {
      headers: { "user-agent": request.headers.get("user-agent") || "" },
      cf: { cacheTtl: 86400, cacheEverything: true },
    });
    response = new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "public, max-age=86400",
      },
    });
    if (upstream.ok) ctx.waitUntil(cache.put(cacheKey, response.clone()));
  }
  return response;
}

async function proxyEvent(request, url) {
  // Dropped, not forwarded: analytics is off, or this isn't production.
  if (!counted(url)) return dropped();
  // Only the content types Plausible's script sends, and the rebuilt event
  // goes on as text/plain, so Plausible reads the JSON this Worker checked
  // (a form-encoded body would be read as form fields instead).
  const type = (request.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
  if (type !== "text/plain" && type !== "application/json") return dropped();
  const text = await readCapped(request, MAX_EVENT_BYTES);
  const event = text === null ? null : rebuild(text);
  if (!event) return dropped();
  const body = JSON.stringify(event);
  const headers = new Headers();
  headers.set("content-type", "text/plain");
  headers.set("user-agent", request.headers.get("user-agent") || "");
  // Plausible derives country/visitor hash from the client IP and discards it;
  // without this header it would see Cloudflare's edge IP instead.
  const ip = request.headers.get("cf-connecting-ip");
  if (ip) headers.set("x-forwarded-for", ip);
  const upstream = await fetch(EVENT_UPSTREAM, {
    method: "POST",
    headers,
    body,
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "cache-control": "no-store" },
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === SCRIPT_PATH && request.method === "GET") {
      return proxyScript(request, ctx, url);
    }
    if (url.pathname === EVENT_PATH && request.method === "POST") {
      return proxyEvent(request, url);
    }
    if (isMacDownload(url.pathname)) {
      return macDownload(request, ctx);
    }
    return env.ASSETS.fetch(request);
  },
};
