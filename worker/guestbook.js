// guestbook.riverxia.sh: open guestbook, one SQLite Durable Object holds everything (strongly consistent: a signed entry is readable immediately).
// anyone can sign and entries show up right away.   browser: the form on the page.   terminal: curl guestbook.riverxia.sh  /  curl -d name=you -d message=hi guestbook.riverxia.sh
// abuse guards: per-ip limits (3/hour, 30s apart, hashed ip), a global flood cap (100/hour), length limits, reserved names, max 2 links
// per message, honeypot field, same-origin check for browsers, text rendered with textContent. the admin deletes with their firebase google login:
// the client sends its firebase id token and the worker verifies it (signature, audience, issuer, expiry) and checks the email hash.
import { DurableObject } from "cloudflare:workers";
const NAME_MAX = 49, MSG_MAX = 499, SITE_MAX = 199, PER_HOUR = 3, GAP = 30, GLOBAL_HOUR = 100, PAGE = 40;
const FIREBASE_PROJECT = "riverxia-dev-portfolio";
const ADMIN_HASH = "faf863681b8a634b1a95cb3058937ce4e69cee4c2b3459b137c61c4d1e49f0c9"; // sha256 of the admin email (same as comments.js)
const JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com";
const RESERVED = ["rivercodes", "riverc", "riverxia", "admin", "owner"];
const HDR = { "cache-control": "no-store", "x-content-type-options": "nosniff" };
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { ...HDR, "content-type": "application/json; charset=utf-8" } });
const text = (s, status = 200) => new Response(s, { status, headers: { ...HDR, "content-type": "text/plain; charset=utf-8" } });
const rid = n => Array.from(crypto.getRandomValues(new Uint8Array(n)), b => "abcdefghijkmnpqrstuvwxyz23456789"[b % 32]).join("");
const sha = async s => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s))), b => b.toString(16).padStart(2, "0")).join("");

const b64 = s => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), c => c.charCodeAt(0));
let jwks = null, jwksAt = 0;

// verify a firebase id token (RS256, google's securetoken keys) and return its claims, or throw
async function verifyFirebase(token) {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("malformed");
  const header = JSON.parse(new TextDecoder().decode(b64(parts[0]))), claims = JSON.parse(new TextDecoder().decode(b64(parts[1])));
  if (header.alg !== "RS256" || !header.kid) throw new Error("bad alg");
  if (!jwks || Date.now() - jwksAt > 3600e3 || !jwks.keys.some(k => k.kid === header.kid)) {
    jwks = await (await fetch(JWKS_URL)).json(); jwksAt = Date.now();
  }
  const jwk = jwks.keys.find(k => k.kid === header.kid);
  if (!jwk) throw new Error("unknown key");
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1]));
  const now = Math.floor(Date.now() / 1000);
  if (!ok || claims.aud !== FIREBASE_PROJECT || claims.iss !== `https://securetoken.google.com/${FIREBASE_PROJECT}` || !claims.sub || claims.exp <= now || claims.iat > now + 60) throw new Error("invalid token");
  return claims;
}

async function isAdmin(request) {
  const m = (request.headers.get("authorization") || "").match(/^Bearer (.+)$/);
  if (!m) return { ok: false, error: "sign in as admin" };
  try {
    const c = await verifyFirebase(m[1]);
    if (!c.email || c.email_verified !== true || (await sha(c.email)) !== ADMIN_HASH) return { ok: false, error: "not admin" };
    return { ok: true };
  } catch { return { ok: false, error: "bad token" }; }
}

async function readBody(request) {
  const ct = request.headers.get("content-type") || "";
  if (ct.includes("application/json")) { try { return await request.json(); } catch { return null; } }
  if (ct.includes("form")) { const f = await request.formData(); return Object.fromEntries([...f.entries()].map(([k, v]) => [k, typeof v === "string" ? v : ""])); }
  return null;
}

export class Guestbook extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec("CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, message TEXT NOT NULL, website TEXT, t INTEGER NOT NULL)");
    this.sql.exec("CREATE TABLE IF NOT EXISTS hits (h TEXT NOT NULL, t INTEGER NOT NULL)");
  }
  list(before, limit) {
    const rows = this.sql.exec("SELECT id, name, message, website, t FROM entries WHERE id < ? ORDER BY id DESC LIMIT ?", before, limit + 1).toArray();
    const entries = rows.slice(0, limit).map(r => ({ id: r.id, name: r.name, message: r.message, website: r.website, t: r.t }));
    return { entries, cursor: rows.length > limit ? entries[entries.length - 1].id : null };
  }
  sign(e, h) { // rate limits and the insert happen in one step, so they cannot race
    const now = Date.now();
    this.sql.exec("DELETE FROM hits WHERE t < ?", now - 3600000);
    const g = this.sql.exec("SELECT COUNT(*) AS c FROM hits").one().c;
    const mine = this.sql.exec("SELECT COUNT(*) AS c, MAX(t) AS last FROM hits WHERE h = ?", h).one();
    if (g >= GLOBAL_HOUR) return { status: 429, error: "the guestbook is getting a lot of traffic. try again in a bit." };
    if (mine.c >= PER_HOUR) return { status: 429, error: `you can sign ${PER_HOUR} times an hour.` };
    if (mine.last && now - mine.last < GAP * 1000) return { status: 429, error: `slow down, wait ${Math.ceil(GAP - (now - mine.last) / 1000)}s.` };
    this.sql.exec("INSERT INTO hits (h, t) VALUES (?, ?)", h, now);
    const id = this.sql.exec("INSERT INTO entries (name, message, website, t) VALUES (?, ?, ?, ?) RETURNING id", e.name, e.message, e.website, now).one().id;
    return { status: 201, id };
  }
  remove(id) { this.sql.exec("DELETE FROM entries WHERE id = ?", id); }
}

const stubFor = env => env.GB.get(env.GB.idFromName("main"));

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
  const stub = stubFor(env);
  const h = (await sha("gb:" + (request.headers.get("cf-connecting-ip") || "?"))).slice(0, 16);
  const r = await stub.sign({ name, message, website: website || null }, h);
  return r.error ? json({ error: r.error }, r.status) : json({ ok: true, id: r.id }, 201);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url), path = url.pathname, ua = request.headers.get("user-agent") || "";
    if (path === "/api/entries" && request.method === "GET") return json(await (stubFor(env)).list(parseInt(url.searchParams.get("cursor"), 10) || 9e15, PAGE));
    if ((path === "/api/entries" || path === "/") && request.method === "POST") return sign(request, env, url);
    if (path.startsWith("/api/entries/") && request.method === "DELETE") {
      const id = parseInt(decodeURIComponent(path.slice(13)), 10), who = await isAdmin(request);
      if (!who.ok) return json({ error: who.error }, 403);
      if (!Number.isInteger(id)) return json({ error: "bad id" }, 400);
      await (stubFor(env)).remove(id);
      return json({ ok: true });
    }
    if (path === "/" && request.method === "GET" && (/^(curl\/|wget|gnu wget)/i.test(ua) || (request.headers.get("accept") || "").startsWith("text/plain"))) {
      const { entries } = await (stubFor(env)).list(9e15, 20);
      const body = entries.map(e => `${new Date(e.t).toISOString().slice(0, 10)}  ${e.name}${e.website ? "  <" + e.website + ">" : ""}\n  ${e.message.replace(/\n/g, "\n  ")}`).join("\n\n");
      return text(`~*~ guestbook ~*~\n\n${body || "nobody yet. be the first!"}\n\nsign it: curl -d name=you -d message='hi!' https://${url.host}\n`);
    }
    const r = await env.ASSETS.fetch(request);
    if (path === "/") { const h = new Headers(r.headers); h.append("vary", "user-agent, accept"); return new Response(r.body, { status: r.status, headers: h }); }
    return r;
  },
};
