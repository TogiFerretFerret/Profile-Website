// Comments for blog posts. Firestore collection "comments", same schema as the old blog:
// {postId:number, parentId:string|null, name, body, uid, verified, timestamp}
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getFirestore, collection, addDoc, deleteDoc, doc, query, where, onSnapshot, serverTimestamp }
  from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { getAuth, signInAnonymously, GoogleAuthProvider, signInWithPopup, onAuthStateChanged, signOut }
  from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

const app = initializeApp({
  apiKey: "AIzaSyC1dC4f5h8_WeOQnvrblH3VJ8pdeU4Iey4",
  authDomain: "riverxia-dev-portfolio.firebaseapp.com",
  projectId: "riverxia-dev-portfolio",
  appId: "1:921793007466:web:bd7d01052795a5b6b21f13",
});
const db = getFirestore(app);
const auth = getAuth(app);
const ADMIN_HASH = "faf863681b8a634b1a95cb3058937ce4e69cee4c2b3459b137c61c4d1e49f0c9"; // sha256 of admin email
const RESERVED = ["rivercodes", "riverc", "riverxia", "admin", "owner"];

const root = document.getElementById("comments");
const postId = Number(root.dataset.post);
let isAdmin = false;
let comments = [];

const $ = (tag, props = {}, ...kids) => {
  const el = Object.assign(document.createElement(tag), props);
  kids.forEach(k => el.append(k));
  return el;
};

async function sha256(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function submit(parentId, nameEl, bodyEl, btn) {
  const name = isAdmin ? "Riverxia" : nameEl.value.trim();
  const body = bodyEl.value.trim();
  if (!name) return alert("please enter your name.");
  if (!body) return alert("please write a comment.");
  if (!isAdmin && RESERVED.some(r => name.toLowerCase().includes(r))) return alert("that name is reserved.");
  btn.disabled = true; btn.textContent = "posting...";
  try {
    if (!auth.currentUser) await signInAnonymously(auth);
    await addDoc(collection(db, "comments"), {
      postId, parentId, name, body, uid: auth.currentUser.uid, verified: isAdmin, timestamp: serverTimestamp(),
    });
    bodyEl.value = ""; nameEl.value = "";
    if (parentId) btn.closest(".reply-form").hidden = true;
  } catch (e) {
    console.error(e); alert("could not post comment.");
  } finally {
    btn.disabled = false; btn.textContent = parentId ? "reply" : "post comment";
  }
}

function form(parentId) {
  const name = $("input", { type: "text", placeholder: "your name", maxLength: 49 });
  if (isAdmin) { name.value = "Riverxia"; name.disabled = true; }
  const body = $("textarea", { placeholder: parentId ? "write a reply..." : "write a comment...", maxLength: 1999, rows: 4 });
  const btn = $("button", { type: "button", textContent: parentId ? "reply" : "post comment" });
  btn.onclick = () => submit(parentId, name, body, btn);
  return $("div", { className: "cform" }, name, body, btn);
}

function node(c, byParent) {
  const when = c.timestamp?.toDate ? c.timestamp.toDate().toLocaleString() : "just now";
  const head = $("div", { className: "chead" }, $("b", { textContent: c.name }));
  if (c.verified) head.append($("span", { className: "tag", textContent: "verified" }));
  head.append($("span", { className: "dim", textContent: " " + when }));
  const actions = $("div", { className: "cact" });
  const rf = $("div", { className: "reply-form", hidden: true }, form(c.id));
  const rb = $("button", { type: "button", className: "link", textContent: "[reply]" });
  rb.onclick = () => { rf.hidden = !rf.hidden; };
  actions.append(rb);
  if (isAdmin) {
    const del = $("button", { type: "button", className: "link", textContent: "[delete]" });
    del.onclick = async () => { if (confirm("delete this comment?")) await deleteDoc(doc(db, "comments", c.id)).catch(e => alert("delete failed")); };
    actions.append(del);
  }
  const kids = $("div", { className: "cthread" });
  (byParent.get(c.id) || []).forEach(k => kids.append(node(k, byParent)));
  return $("div", { className: "comment" }, head, $("p", { className: "cbody", textContent: c.body }), actions, rf, kids);
}

function render() {
  const list = document.getElementById("clist");
  list.replaceChildren();
  if (!comments.length) return list.append($("p", { className: "dim", textContent: "no comments yet. be the first!" }));
  const byParent = new Map();
  const ids = new Set(comments.map(c => c.id));
  comments.forEach(c => {
    const p = c.parentId && ids.has(c.parentId) ? c.parentId : null;
    if (!byParent.has(p)) byParent.set(p, []);
    byParent.get(p).push(c);
  });
  (byParent.get(null) || []).forEach(c => list.append(node(c, byParent)));
}

function mount() {
  root.replaceChildren(
    $("h2", { textContent: "comments" }),
    $("div", { id: "cnew" }, form(null)),
    $("div", { id: "clist" }, $("p", { className: "dim", textContent: "loading comments..." })),
    $("p", { className: "dim", id: "cadmin" }),
  );
  const a = document.getElementById("cadmin");
  const b = $("button", { type: "button", className: "link", textContent: isAdmin || auth.currentUser?.email ? "[log out]" : "[admin]" });
  b.onclick = () => (auth.currentUser && !auth.currentUser.isAnonymous)
    ? signOut(auth) : signInWithPopup(auth, new GoogleAuthProvider()).catch(() => alert("login failed."));
  a.append(b);
  render();
}

onAuthStateChanged(auth, async user => {
  if (!user) return signInAnonymously(auth).catch(console.error);
  isAdmin = !!user.email && (await sha256(user.email)) === ADMIN_HASH;
  mount();
});

onSnapshot(query(collection(db, "comments"), where("postId", "==", postId)), snap => {
  comments = snap.docs.map(d => ({ id: d.id, ...d.data() }))
    .sort((a, b) => (a.timestamp?.seconds ?? 1e12) - (b.timestamp?.seconds ?? 1e12));
  if (document.getElementById("clist")) render();
}, err => {
  console.error(err);
  const l = document.getElementById("clist");
  if (l) l.textContent = "could not load comments.";
});
