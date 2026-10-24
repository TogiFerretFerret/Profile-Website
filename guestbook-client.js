// client for guestbook.riverxia.sh (talks to worker/guestbook.js on the same origin). all text goes in with textContent.
// admin = the same firebase google login as the blog comments; the worker verifies the id token before deleting anything.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
const auth = getAuth(initializeApp({
  apiKey: "AIzaSyC1dC4f5h8_WeOQnvrblH3VJ8pdeU4Iey4",
  authDomain: "riverxia-dev-portfolio.firebaseapp.com",
  projectId: "riverxia-dev-portfolio",
  appId: "1:921793007466:web:bd7d01052795a5b6b21f13",
}));
const ADMIN_HASH = "faf863681b8a634b1a95cb3058937ce4e69cee4c2b3459b137c61c4d1e49f0c9"; // sha256 of admin email
const sha256 = async s => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)))].map(b => b.toString(16).padStart(2, "0")).join("");
const $ = (tag, props = {}, ...kids) => { const el = Object.assign(document.createElement(tag), props); kids.forEach(k => el.append(k)); return el; };
const root = document.getElementById("guestbook");
let cursor = null, admin = false;

function entry(e) {
  const head = $("div", { className: "chead" }, $("b", { textContent: e.name }), $("span", { className: "dim", textContent: " " + new Date(e.t).toLocaleDateString() }));
  if (e.website && /^https?:\/\//.test(e.website)) head.append(" ", $("a", { href: e.website, rel: "nofollow noopener noreferrer ugc", textContent: "[site]" }));
  const box = $("div", { className: "gbe" }, head, $("p", { className: "cbody", textContent: e.message }));
  if (admin) {
    const del = $("button", { type: "button", className: "link", textContent: "[delete]" });
    del.onclick = async () => {
      if (!confirm("delete this entry?")) return;
      const tok = await auth.currentUser.getIdToken();
      const r = await fetch("/api/entries/" + encodeURIComponent(e.id), { method: "DELETE", headers: { authorization: "Bearer " + tok } });
      if (r.ok) box.remove(); else alert("delete failed: " + ((await r.json().catch(() => ({}))).error || r.status));
    };
    box.append($("div", { className: "cact" }, del));
  }
  return box;
}

async function load(reset) {
  const list = document.getElementById("gblist"), more = document.getElementById("gbmore");
  if (reset) { list.replaceChildren($("p", { className: "dim", textContent: "loading..." })); cursor = null; }
  try {
    const r = await (await fetch("/api/entries" + (cursor ? "?cursor=" + encodeURIComponent(cursor) : ""), { cache: "no-store" })).json();
    if (reset) list.replaceChildren();
    if (reset && !r.entries.length) list.append($("p", { className: "dim", textContent: "nobody yet. be the first!" }));
    r.entries.forEach(e => list.append(entry(e)));
    cursor = r.cursor; more.hidden = !cursor;
  } catch { list.textContent = "could not load the guestbook."; }
}

function form() {
  const name = $("input", { type: "text", placeholder: "your name", maxLength: 49 });
  const msg = $("textarea", { placeholder: "say hi! (500 characters max)", maxLength: 499, rows: 4 });
  const site = $("input", { type: "url", placeholder: "your website (optional, https://...)", maxLength: 199 });
  const trap = $("input", { type: "text", className: "hp", tabIndex: -1, autocomplete: "off" });
  const note = $("p", { className: "dim", role: "status" });
  const btn = $("button", { type: "button", textContent: "sign it" });
  btn.onclick = async () => {
    if (!name.value.trim() || !msg.value.trim()) { note.textContent = "please fill in your name and a message."; return; }
    btn.disabled = true; btn.textContent = "signing...";
    try {
      const r = await fetch("/api/entries", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ name: name.value, message: msg.value, website: site.value, hp: trap.value }) });
      const j = await r.json().catch(() => ({}));
      if (r.ok) {
        // kv listings are eventually consistent (up to ~a minute), so show the new entry right away instead of reloading
        const list = document.getElementById("gblist");
        if (!list.querySelector(".gbe")) list.replaceChildren();
        list.prepend(entry({ id: j.id, name: name.value.trim(), message: msg.value.trim(), website: site.value.trim() || null, t: Date.now() }));
        name.value = msg.value = site.value = ""; note.textContent = "thanks for signing!";
      }
      else note.textContent = j.error || "could not sign the guestbook.";
    } catch { note.textContent = "could not reach the guestbook."; }
    btn.disabled = false; btn.textContent = "sign it";
  };
  return $("div", { className: "cform" }, name, msg, site, trap, btn, note);
}

function mount() {
  const adm = $("button", { type: "button", className: "link", textContent: admin ? "[log out]" : "[admin]" });
  adm.onclick = () => (auth.currentUser ? signOut(auth) : signInWithPopup(auth, new GoogleAuthProvider()).catch(() => alert("login failed.")));
  const more = $("button", { type: "button", id: "gbmore", hidden: true, textContent: "load more" });
  more.onclick = () => load(false);
  root.replaceChildren($("h2", { textContent: "sign the guestbook" }), form(), $("h2", { textContent: "entries" }),
    $("div", { id: "gblist" }), more, $("p", { className: "dim" }, adm));
}
mount(); load(true);
// re-render only when the admin state actually changes
onAuthStateChanged(auth, async user => {
  const now = !!user?.email && (await sha256(user.email)) === ADMIN_HASH;
  if (now === admin) return;
  admin = now; mount(); load(true);
});
