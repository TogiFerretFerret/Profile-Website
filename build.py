#!/usr/bin/env python3
"""Static build: python3 build.py [--prod]  ->  dist/{www,blog,projects}/
--prod uses real riverxia.sh links; default uses local paths for preview.
Each dist/<sub> is one deployable site root (see deploy.sh)."""
import html, json, re, shutil, subprocess, sys
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
POSTS = ROOT / "posts"
DIST = ROOT / "dist"
DOMAIN = "riverxia.sh"
PROD = "--prod" in sys.argv

CONTACT = "river&#64;riverxia.sh"  # @ as an entity: mild protection from naive scrapers
TEAMS = [
    ("idktheflag", "founded and captained (formerly)", "#58 global, #7 in the US (2026)", "https://ctftime.org/team/419270"),
    ("B4 (Bishkek Bureau of Binary Bandits)", "member (team founded and captained by Vakuum)", "#10 global (2026)", "https://ctftime.org/team/431075"),
]
SOCIALS = [
    ("github", "https://github.com/TogiFerretFerret"),
    ("ctftime", "https://ctftime.org/user/249194"),
    ("osu!", "https://osu.ppy.sh/users/34415790"),
    ("ao3", "https://archiveofourown.org/users/Riverxia"),
]
SUBS = [("home", "www"), ("blog", "blog"), ("projects", "projects")]

ABOUT = [
    "hi! i'm riverxia (i go by river). rawr.",
    "i like competitive programming, cybersecurity and software development. when i'm not solving CTFs i'm poking at new tech.",
    "started programming at 7 and never stopped. i like algorithms, data structures, and web dev. also osu! (top 200k global).",
]
AWARDS = [
    ("National Cyber League 2026", "#1 HS / #5 overall. captain of the top high school team."),
    ("Lockheed CyberQuest 2026", "1st place, full solve, 5230 pts."),
    ("picoCTF 2026", "#14 HS / #35 global, full solve (14,500 pts)."),
    ("picoCTF 2025", "2nd place, middle school."),
    ("USACO Platinum", "full score on Gold, in-contest promotion."),
    ("CMIMC Programming 2025", "1st in the DE-Shaw problem."),
    ("MetaCTF Flash CTF 2026", "12th, full solve (individual)."),
    ("picoMini by CMU-Africa 2025", "20th globally."),
    ("Science Bowl MS 2024", "9th place."),
]
SKILLS = {
    "languages": "Python, JS/TS, C++, Java, Rust, Go",
    "tools": "React/Next.js, Node.js, TensorFlow, Q#, Git, Azure",
    "areas": "algorithms, web, cybersecurity, game dev",
}
PROJECTS = [
    ("aimrpg", "in development", "indie game i'm lead dev on. someone else's project, i run the dev side.", "Go, Postgres", ""),
    ("cctf.rs", "2026", "CTFd rebuilt from scratch in Rust. hand-rolled SMTP/JWT, rhai scripting, per-team k8s instancing.", "Rust, Kubernetes", "post15"),
    ("Personal Website", "2026", "this site. static, no build framework.", "HTML, CSS, Markdown", ""),
    ("AI Vision Assistant", "2025, wip", "real-time visual analysis assistant.", "Python, TensorFlow, OpenCV", ""),
    ("Neovim Dots", "2025-2026, wip", "custom neovim config for speed and competitive programming.", "Lua, Vimscript", ""),
    ("Aluminum (HCHS Alt)", "2025-2026, wip", "reverse engineered Blackbaud client. closed source.", "Python, Flask, Node.js", ""),
    ("CP Trainer", "2024", "practice algorithm problems with automated testing.", "Next.js, Node.js, PostgreSQL", ""),
    ("osu! Analyzer", "2024, deprecated", "gameplay data analysis.", "Python, Flask, TensorFlow", ""),
]
PROJECT_LINKS = {
    "aimrpg": [("website", "https://aimrpg.com"), ("steam", "https://store.steampowered.com/app/4947810")],
    "cctf.rs": [("repo", "https://github.com/TogiFerretFerret/cctf.rs")],
}
BUTTONS = [("GitHub", "#000", "#fff", SOCIALS[0][1]), ("CTFtime", "#900", "#fff", SOCIALS[1][1]),
           ("osu!", "#e4a", "#fff", SOCIALS[2][1]), ("AO3", "#900", "#fc9", SOCIALS[3][1]),
           ("Rust", "#b7410e", "#fff", "https://www.rust-lang.org"), ("any browser", "#006", "#ff0", "")]

e = html.escape

# visitor counter: one Firestore REST call per browser session (rules: see README)
COUNTER_JS = """(function(){var P="riverxia-dev-portfolio",K="AIzaSyC1dC4f5h8_WeOQnvrblH3VJ8pdeU4Iey4",
D="projects/"+P+"/databases/(default)/documents",U="https://firestore.googleapis.com/v1/",el=document.getElementById("hits");
function show(n){el.textContent=String(n).padStart(7,"0")}
function seen(){try{return sessionStorage.getItem("hit")}catch(x){return 1}}
function mark(){try{sessionStorage.setItem("hit","1")}catch(x){}}
if(seen()){fetch(U+D+"/counters/visits?key="+K).then(function(r){return r.json()}).then(function(d){show(d.fields.count.integerValue)}).catch(function(){})}
else{fetch(U+D+":commit?key="+K,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({writes:[{transform:{document:D+"/counters/visits",fieldTransforms:[{fieldPath:"count",increment:{integerValue:"1"}}]}}]})})
.then(function(r){return r.json()}).then(function(d){show(d.writeResults[0].transformResults[0].integerValue);mark()}).catch(function(){})}})();"""


# --- math: $inline$ and $$display$$ are rendered to static HTML at build time with KaTeX (node) ---
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.S)
INLINE_RE = re.compile(r"(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)")


def extract_math(text):
    """swap math for MATHXnX tokens (code spans/blocks are left alone); returns (text, [(display, latex)])."""
    codes, exprs = [], []
    t = CODE_RE.sub(lambda m: (codes.append(m.group(0)), f"\x01C{len(codes) - 1}\x01")[1], text)

    def disp(m):
        exprs.append((True, m.group(1).strip()))
        return f"\n\nMATHX{len(exprs) - 1}X\n\n"

    def inl(m):
        exprs.append((False, m.group(1)))
        return f"MATHX{len(exprs) - 1}X"

    t = INLINE_RE.sub(inl, DISPLAY_RE.sub(disp, t))
    t = re.sub(r"\x01C(\d+)\x01", lambda m: codes[int(m.group(1))], t)
    return t, exprs


def render_math(htmltext, exprs):
    if not exprs:
        return htmltext
    out = subprocess.run(["node", str(ROOT / "render_math.js")], input=json.dumps([{"e": e, "d": d} for d, e in exprs]),
                         capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        sys.exit("math rendering failed (run `npm install` first):\n" + out.stderr)
    rendered = json.loads(out.stdout)
    for i, (d, _) in enumerate(exprs):
        tok = f"MATHX{i}X"
        if d:
            htmltext = htmltext.replace(f"<p>{tok}</p>", f'<div class="math-display">{rendered[i]}</div>').replace(tok, rendered[i])
        else:
            htmltext = htmltext.replace(tok, rendered[i])
    return htmltext


def url(sub, path=""):
    if not PROD:
        return f"/{sub}/{path}"
    host = DOMAIN if sub == "www" else f"{sub}.{DOMAIN}"
    return f"https://{host}/{path}"


def page(sub, title, body, desc="", extra="", head_extra=""):
    nav = "".join(f'<li><a class="{"on" if s == sub else ""}" href="{url(s)}">{n}</a></li>' for n, s in SUBS)
    btns = "".join(f'<a class="b88" style="background:{bg};color:{fg}" href="{u or "#"}">{e(n)}</a>' for n, bg, fg, u in BUTTONS)
    mq = " &#9733; ".join(["welcome to riverxia.sh", "CTF player", "competitive programmer", "osu! enjoyer", "rust haver", "thanks for visiting"] * 2)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc or title)}">
<link rel="stylesheet" href="style.css">
{head_extra}</head><body>
<div class="top"><div class="logo"><a href="{url('www')}">riverxia<span>.sh</span></a></div>
<div class="marq"><span>{mq}</span></div></div>
<div class="frame">
<aside>
<div class="box"><h3>~ menu ~</h3><ul class="menu">{nav}</ul></div>
<div class="box"><h3>email me</h3><p class="mailme"><a href="mailto:{CONTACT}">{CONTACT}</a></p></div>
<div class="box"><h3>elsewhere</h3><div class="btns">{btns}</div></div>
<div class="box"><h3>stats</h3><p class="cnt">you are visitor<br><b id="hits">???????</b></p></div>
</aside>
<main>
{body}
<footer><hr>this page is best viewed in anything, at any resolution.<br>hand-made, no trackers. js only for the visitor counter and blog comments. &copy; 2026 riverxia &middot; <a href="https://github.com/TogiFerretFerret/Profile-Website">source</a></footer>
</main>
</div>
<script>{COUNTER_JS}</script>
{extra}
</body></html>
"""


def load_posts():
    out = []
    for f in sorted(POSTS.glob("post*.md"), key=lambda p: int(re.sub(r"\D", "", p.stem))):
        t = f.read_text()
        meta, body = {}, t
        m = re.match(r"---\n(.*?)\n---\n(.*)", t, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = m.group(2)
        out.append(dict(slug=f.stem, title=meta.get("title", f.stem), date=meta.get("date", ""),
                        desc=meta.get("description", ""), tags=[x.strip() for x in meta.get("tags", "").split(",") if x.strip()], body=body))
    out.sort(key=lambda p: p["date"], reverse=True)
    return out


def build(posts):
    if DIST.exists():
        shutil.rmtree(DIST)
    css = (ROOT / "style.css").read_text()
    for _, sub in SUBS:
        (DIST / sub).mkdir(parents=True)
        (DIST / sub / "style.css").write_text(css)

    aw = "".join(f"<li><b>{e(a)}</b> <span class='dim'>&mdash; {e(b)}</span></li>" for a, b in AWARDS)
    sk = "".join(f"<li><b>{k}</b>: {e(v)}</li>" for k, v in SKILLS.items())
    teams = "".join(f'<li><b><a href="{u}">{e(n)}</a></b> <br><span class="dim">{e(r)} &middot; {e(k)}</span></li>' for n, r, k, u in TEAMS)
    latest = "".join(f'<li><span class="dim">{p["date"]}</span> <a href="{url("blog", p["slug"] + ".html")}">{e(p["title"])}</a></li>' for p in posts[:6])
    body = f"""<h1>~*~ hi, i'm river ~*~</h1>
<p class="tagline">ur friendly pansexual paragirlflux genderfae hecker :3<br>aka gaslight gatekeep get shell (she/her/they/them)</p>
<div class="cols">
<section class="box"><h2>about me</h2>{''.join(f'<p>{e(x)}</p>' for x in ABOUT)}</section>
<section class="box"><h2>latest posts</h2><ul>{latest}</ul><p><a href="{url('blog')}">&gt;&gt; all posts</a> <span class='new'>NEW!</span></p></section>
<section class="box"><h2>ctf teams</h2><ul>{teams}</ul><p><a href="{SOCIALS[1][1]}">&gt;&gt; my ctftime profile</a></p></section>
<section class="box"><h2>awards &amp; stuff</h2><ul>{aw}</ul></section>
<section class="box"><h2>contact</h2><p>email me: <a href="mailto:{CONTACT}">{CONTACT}</a></p><p class="dim">writeup questions, collabs, bug reports, or just saying hi. you can also find me on github, ctftime and osu! (links on the left).</p></section>
<section class="box"><h2>skills</h2><ul>{sk}</ul>
<h2>site map</h2><ul><li><a href="{url('blog')}">blog</a> <span class="dim">writeups, rants, build logs</span></li>
<li><a href="{url('projects')}">projects</a> <span class="dim">things i made</span></li></ul></section>
</div>"""
    (DIST / "www" / "index.html").write_text(page("www", "riverxia", body, "river's corner of the internet"))

    items = ""
    for t, y, d, s, post in PROJECTS:
        ls = list(PROJECT_LINKS.get(t, []))
        if post:
            ls.append(("writeup", url("blog", post + ".html")))
        l = "<p>" + " ".join(f'<a href="{e(u)}">[{e(n)}]</a>' for n, u in ls) + "</p>" if ls else ""
        items += f"<section class='box'><h2>{e(t)}</h2><p class='dim'>{e(y)}</p><p>{e(d)}</p><p class='dim'>stack: {e(s)}</p>{l}</section>"
    (DIST / "projects" / "index.html").write_text(page("projects", "projects - riverxia", f"<h1>projects.{DOMAIN}</h1><div class='cols'>{items}</div>"))

    md = markdown.Markdown(extensions=["fenced_code", "tables", "codehilite"],
                           extension_configs={"codehilite": {"noclasses": True, "pygments_style": "native"}})
    rows = ""
    for p in posts:
        md.reset()
        tags = " ".join(f"<span class='tag'>{e(t)}</span>" for t in p["tags"])
        text, exprs = extract_math(p["body"].replace("/blog/assets/", "assets/"))
        content = render_math(md.convert(text), exprs)
        has_math = bool(exprs)
        (DIST / "blog" / f"{p['slug']}.html").write_text(page("blog", p["title"] + " - riverxia",
            f"<p><a href='{url('blog')}'>&lt;&lt; back to blog</a></p><h1>{e(p['title'])}</h1><p class='dim'>{p['date']} {tags}</p><article class='box'>{content}</article><section class='box' id='comments' data-post='{re.sub(r'\D', '', p['slug'])}'><noscript>comments need javascript.</noscript></section>", desc=p["desc"], extra='<script type="module" src="comments.js"></script>',
            head_extra='<link rel="stylesheet" href="katex/katex.min.css">\n' if has_math else ""))
        rows += f"<li><span class='dim'>{p['date']}</span> <a href='{p['slug']}.html'>{e(p['title'])}</a><br><span class='dim'>{e(p['desc'])}</span></li>"
    (DIST / "blog" / "index.html").write_text(page("blog", "blog - riverxia", f"<h1>~*~ blog ~*~</h1><p><a href='rss.xml'>[rss]</a></p><section class='box'><ul class='loose'>{rows}</ul></section>"))
    feed = "".join(f"<item><title>{e(p['title'])}</title><link>{url('blog', p['slug'] + '.html')}</link><description>{e(p['desc'])}</description></item>" for p in posts)
    (DIST / "blog" / "rss.xml").write_text(f'<?xml version="1.0"?><rss version="2.0"><channel><title>riverxia</title><link>{url("blog")}</link><description>blog</description>{feed}</channel></rss>')
    shutil.copy(ROOT / "comments.js", DIST / "blog" / "comments.js")
    kdist = ROOT / "node_modules" / "katex" / "dist"
    if kdist.exists():
        (DIST / "blog" / "katex" / "fonts").mkdir(parents=True)
        shutil.copy(kdist / "katex.min.css", DIST / "blog" / "katex" / "katex.min.css")
        for f in (kdist / "fonts").glob("*.woff2"):
            shutil.copy(f, DIST / "blog" / "katex" / "fonts" / f.name)
    shutil.copytree(ROOT / "assets", DIST / "blog" / "assets")
    shutil.copy(ROOT / "bimi.svg", DIST / "www" / "bimi.svg")  # BIMI logo (SVG Tiny PS)
    for sub in ("www", "blog", "projects"):
        (DIST / sub / "404.html").write_text(page(sub, "404", "<h1>404</h1><p>nothing here. sorry!</p>"))


if __name__ == "__main__":
    posts = load_posts()
    build(posts)
    print("built", len(posts), "posts")
