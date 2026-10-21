// guestbook.riverxia.sh: open guestbook on Workers KV. anyone can sign; entries show up immediately.
//   browser: the form on the page.   terminal: curl guestbook.riverxia.sh   /   curl -d name=you -d message=hi guestbook.riverxia.sh
// abuse guards: per-ip limits (3/hour, 30s apart, hashed ip), a global flood cap (100/hour), length limits, reserved names, max 2 links
// per message, honeypot field, same-origin check for browsers, text rendered with textContent. the admin can delete via x-admin-token.
const NAME_MAX = 49, MSG_MAX = 499, SITE_MAX = 199, PER_HOUR = 3, GAP = 30, GLOBAL_HOUR = 100, PAGE = 40;
const RESERVED = ["rivercodes", "riverc", "riverxia", "admin", "owner"];
const HDR = { "cache-control": "no-store", "x-content-type-options": "nosniff" };
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { ...HDR, "content-type": "application/json; charset=utf-8" } });
const text = (s, status = 200) => new Response(s, { status, headers: { ...HDR, "content-type": "text/plain; charset=utf-8" } });
const rid = n => Array.from(crypto.getRandomValues(new Uint8Array(n)), b => "abcdefghijkmnpqrstuvwxyz23456789"[b % 32]).join("");
const sha = async s => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s))), b => b.toString(16).padStart(2, "0")).join("");

async function readBody(request) {
  const ct = request.headers.get("content-type") || "";
  if (ct.includes("application/json")) { try { return await request.json(); } catch { return null; } }
  if (ct.includes("form")) { const f = await request.formData(); return Object.fromEntries([...f.entries()].map(([k, v]) => [k, typeof v === "string" ? v : ""])); }
  return null;
}

async function limited(env, ip) {
  const h = (await sha("gb:" + ip)).slice(0, 16), hour = Math.floor(Date.now() / 3600000);
  const [n, last, g] = await Promise.all([env.GB.get(`rl:${h}:${hour}`), env.GB.get(`last:${h}`), env.GB.get(`rlg:${hour}`)]);
  if (+g >= GLOBAL_HOUR) return { msg: "the guestbook is getting a lot of traffic. try again in a bit.", h, hour, n: +n, g: +g };
  if (+n >= PER_HOUR) return { msg: `you can sign ${PER_HOUR} times an hour.`, h, hour, n: +n, g: +g };
  if (last && Date.now() - +last < GAP * 1000) return { msg: `slow down, wait ${Math.ceil(GAP - (Date.now() - +last) / 1000)}s.`, h, hour, n: +n, g: +g };
  return { h, hour, n: +n || 0, g: +g || 0 };
}

async function sign(request, env, url) {
  const origin = request.headers.get("origin");
  if (origin) { try { if (new URL(origin).host !== url.host) return json({ error: "bad origin" }, 403); } catch { return json({ error: "bad origin" }, 403); } }
  const b = await readBody(request);
  if (!b) return json({ error: "send json or a form with name and message" }, 400);
  if (b.hp) return json({ ok: true }); // honeypot: pretend it worked
  const name = String(b.name ?? "").trim(), message = String(b.message ?? "").trim(), website = String(b.website ?? "").trim();
  if (!name || name.length > NAME_MAX) return json({ error: `name is required (max ${NAME_MAX} characters)` }, 400);
  if (!message || message.length > MSG_MAX) return json({ error: `message is required (max ${MSG_MAX} characters)` }, 400);
  if (RESERVED.some(r => name.toLowerCase().includes(r))) return json({ error: "that name is reserved" }, 400);
  if (website && (website.length > SITE_MAX || !/^https?:\/\/[^\s]+$/.test(website))) return json({ error: "website must be an http(s) url" }, 400);
  if (/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(name + message)) return json({ error: "no control characters" }, 400);
  if ((message.match(/https?:\/\/|www\./gi) || []).length > 2) return json({ error: "too many links" }, 400);
  const lim = await limited(env, request.headers.get("cf-connecting-ip") || "?");
  if (lim.msg) return json({ error: lim.msg }, 429);
  const t = Date.now(), id = `e:${String(9999999999999 - t).padStart(13, "0")}:${rid(4)}`; // newest first when listed
  await env.GB.put(id, JSON.stringify({ n: name, m: message, ...(website ? { w: website } : {}), t }));
  await Promise.all([env.GB.put(`rl:${lim.h}:${lim.hour}`, String(lim.n + 1), { expirationTtl: 3700 }), env.GB.put(`last:${lim.h}`, String(t), { expirationTtl: 60 }),
    env.GB.put(`rlg:${lim.hour}`, String(lim.g + 1), { expirationTtl: 3700 })]);
  return json({ ok: true, id }, 201);
}

async function list(env, cursor, limit) {
  const r = await env.GB.list({ prefix: "e:", limit, cursor: cursor || undefined });
  const entries = (await Promise.all(r.keys.map(async k => { const v = await env.GB.get(k.name, "json"); return v && { id: k.name, name: v.n, message: v.m, website: v.w || null, t: v.t }; }))).filter(Boolean);
  return { entries, cursor: r.list_complete ? null : r.cursor };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url), path = url.pathname, ua = request.headers.get("user-agent") || "";
    if (path === "/api/entries" && request.method === "GET") return json(await list(env, url.searchParams.get("cursor"), PAGE));
    if ((path === "/api/entries" || path === "/") && request.method === "POST") return sign(request, env, url);
    if (path.startsWith("/api/entries/") && request.method === "DELETE") {
      const tok = request.headers.get("x-admin-token") || "", id = decodeURIComponent(path.slice(13));
      if (!env.ADMIN_TOKEN || !tok || (await sha(tok)) !== (await sha(env.ADMIN_TOKEN))) return json({ error: "forbidden" }, 403);
      if (!id.startsWith("e:")) return json({ error: "bad id" }, 400);
      await env.GB.delete(id);
      return json({ ok: true });
    }
    if (path === "/" && request.method === "GET" && (/^(curl\/|wget|gnu wget)/i.test(ua) || (request.headers.get("accept") || "").startsWith("text/plain"))) {
      const { entries } = await list(env, null, 20);
      const body = entries.map(e => `${new Date(e.t).toISOString().slice(0, 10)}  ${e.name}${e.website ? "  <" + e.website + ">" : ""}\n  ${e.message.replace(/\n/g, "\n  ")}`).join("\n\n");
      return text(`~*~ guestbook ~*~\n\n${body || "nobody yet. be the first!"}\n\nsign it: curl -d name=you -d message='hi!' https://${url.host}\n`);
    }
    const r = await env.ASSETS.fetch(request);
    if (path === "/") { const h = new Headers(r.headers); h.append("vary", "user-agent, accept"); return new Response(r.body, { status: r.status, headers: h }); }
    return r;
  },
};
