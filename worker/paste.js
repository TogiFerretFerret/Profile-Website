// paste.riverxia.sh: tiny text pastebin on Workers KV.
//   echo hi | curl --data-binary @- paste.riverxia.sh        curl -T file.txt paste.riverxia.sh        (url comes back on stdout)
//   ttl: ?ttl=1h|1d|7d|30d (default 7d, max 30d, nothing lives forever). delete token comes back in the x-delete-token header.
// abuse guards: text only, 256 KiB cap, 30 writes/hour/ip, served as text/plain + nosniff + sandbox CSP, html view escapes everything.
const MAX = 256 * 1024, LIMIT = 30, TTLS = { "1h": 3600, "1d": 86400, "7d": 604800, "30d": 2592000 }, ALPHA = "abcdefghijkmnpqrstuvwxyz23456789";
const RAW = { "content-type": "text/plain; charset=utf-8", "x-content-type-options": "nosniff", "content-security-policy": "sandbox; default-src 'none'", "x-robots-tag": "noindex", "cache-control": "no-store" };
const esc = s => s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const rid = n => Array.from(crypto.getRandomValues(new Uint8Array(n)), b => ALPHA[b % ALPHA.length]).join("");
const sha = async s => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s))), b => b.toString(16).padStart(2, "0")).join("");
const text = (s, status = 200, h = {}) => new Response(s, { status, headers: { ...RAW, ...h } });
const wantsHtml = r => (r.headers.get("accept") || "").includes("text/html");

function page(title, body) {
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${esc(title)}</title><link rel="stylesheet" href="/style.css"></head><body><main style="max-width:60rem;margin:0 auto"><div class="logo"><a href="https://riverxia.sh">riverxia<span>.sh</span></a></div>${body}</main></body></html>`,
    { headers: { "content-type": "text/html; charset=utf-8", "x-robots-tag": "noindex", "cache-control": "no-store", "content-security-policy": "default-src 'none'; style-src 'self'; form-action 'self'" } });
}

async function readBody(request) {
  const ct = request.headers.get("content-type") || "";
  if (ct.includes("multipart/form-data")) {  // curl -F 'c=<-'
    const f = await request.formData();
    const v = f.get("c") ?? f.get("content") ?? f.get("text");
    return { body: typeof v === "string" ? v : v ? await v.text() : "", ttl: f.get("ttl") };
  }
  const buf = await request.arrayBuffer();
  if (buf.byteLength > MAX + 4096) return { error: "too big" };
  let body;
  try { body = new TextDecoder("utf-8", { fatal: true }).decode(buf); } catch { return { error: "text only" }; }
  // curl --data-binary sends urlencoded by default, so only treat it as a form when it really has our field
  if (ct.includes("application/x-www-form-urlencoded")) {
    const f = new URLSearchParams(body), v = f.get("c") ?? f.get("content") ?? f.get("text");
    if (v !== null) return { body: v, ttl: f.get("ttl") };
  }
  return { body };
}

async function create(request, env, url) {
  const ip = request.headers.get("cf-connecting-ip") || "?", rk = `rl:${ip}:${Math.floor(Date.now() / 3600000)}`;
  const n = parseInt((await env.PASTES.get(rk)) || "0", 10);
  if (n >= LIMIT) return text("slow down: 30 pastes/hour\n", 429);
  const { body, error, ttl } = await readBody(request);
  if (error) return text(error === "too big" ? "too big (256 KiB max)\n" : "text only\n", error === "too big" ? 413 : 415);
  if (!body || !body.trim()) return text("empty paste\n", 400);
  if (new TextEncoder().encode(body).length > MAX) return text("too big (256 KiB max)\n", 413);
  if (body.includes("\0")) return text("text only\n", 415);
  const key = url.searchParams.get("ttl") || request.headers.get("x-ttl") || ttl || "7d";
  const secs = TTLS[key];
  if (!secs) return text("ttl must be one of 1h 1d 7d 30d\n", 400);
  const id = rid(8), token = rid(24);
  await env.PASTES.put(`p:${id}`, body, { expirationTtl: secs, metadata: { d: await sha(token), t: Date.now() } });
  await env.PASTES.put(rk, String(n + 1), { expirationTtl: 3700 });
  const link = `https://${url.host}/${id}`;
  if (wantsHtml(request)) {
    return page("pasted", `<h1>pasted!</h1><section class="box"><p><a href="${link}">${link}</a> <span class="dim">(expires in ${esc(key)})</span></p>
<p class="dim">delete it with:</p><pre class="wrap"><code>curl -X DELETE -H 'x-delete-token: ${token}' ${link}</code></pre><p class="dim">that token is shown once.</p></section>`);
  }
  return text(link + "\n", 201, { "x-delete-token": token });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url), path = url.pathname;
    if (path === "/" && (request.method === "POST" || request.method === "PUT")) return create(request, env, url);
    if (request.method === "GET" || request.method === "HEAD") {
      const m = path.match(/^\/(raw\/)?([a-z0-9]{8})$/);
      if (m) {
        const { value, metadata } = await env.PASTES.getWithMetadata(`p:${m[2]}`);
        if (value === null) return wantsHtml(request) ? page("gone", `<h1>404</h1><p>no such paste. it expired or never existed.</p>`) : text("not found\n", 404);
        if (m[1] || !wantsHtml(request)) return text(value);
        const when = new Date(metadata?.t || 0).toISOString().slice(0, 16).replace("T", " ");
        return page(`paste ${m[2]}`, `<h1>paste ${m[2]}</h1><p class="dim">${when} utc &middot; <a href="/raw/${m[2]}">raw</a> &middot; <a href="/">new paste</a></p><pre class="wrap"><code>${esc(value)}</code></pre>`);
      }
      return env.ASSETS.fetch(request);
    }
    const m = path.match(/^\/([a-z0-9]{8})$/);
    if (request.method === "DELETE" && m) {
      const { value, metadata } = await env.PASTES.getWithMetadata(`p:${m[1]}`);
      if (value === null) return text("not found\n", 404);
      const tok = request.headers.get("x-delete-token") || "";
      if (!tok || (await sha(tok)) !== metadata?.d) return text("bad delete token\n", 403);
      await env.PASTES.delete(`p:${m[1]}`);
      return text("deleted\n");
    }
    return text("method not allowed\n", 405);
  },
};
