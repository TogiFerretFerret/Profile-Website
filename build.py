#!/usr/bin/env python3
"""Static build: python3 build.py [--prod]  ->  dist/{www,blog,projects,uses}/
--prod uses real riverxia.sh links; default uses local paths for preview.
Each dist/<sub> is one deployable site root (see deploy.sh)."""
import html, json, re, shlex, shutil, subprocess, sys
from collections import Counter
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
POSTS = ROOT / "posts"
DIST = ROOT / "dist"
DOMAIN = "riverxia.sh"
PROD = "--prod" in sys.argv
# scheduled posts: a post whose `date:` is after today (America/New_York) is hidden until that day.
# INCLUDE_FUTURE=1 shows them anyway (the preview target does).
TODAY = datetime.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
INCLUDE_FUTURE = os.environ.get("INCLUDE_FUTURE") == "1"
HIDDEN = []  # slugs held back as scheduled; filled by load_posts

CONTACT = "river&#64;riverxia.sh"  # @ as an entity: mild protection from naive scrapers
TEAMS = [
    ("idktheflag", "founded and captained (formerly)", "#58 global, #7 in the US (2026)", "https://ctftime.org/team/419270"),
    ("B4 (Bishkek Bureau of Binary Bandits)", "one of ~5 core members (team founded and captained by Vakuum)", "#10 global (2026)", "https://ctftime.org/team/431075"),
]
SOCIALS = [
    ("github", "https://github.com/TogiFerretFerret"),
    ("ctftime", "https://ctftime.org/user/249194"),
    ("osu!", "https://osu.ppy.sh/users/34415790"),
    ("ao3", "https://archiveofourown.org/users/Riverxia"),
]
SUBS = [("home", "www"), ("blog", "blog"), ("projects", "projects"), ("uses", "uses"), ("dots", "dots"), ("paste", "paste"), ("guestbook", "guestbook")]

ABOUT = [
    "hi! i'm riverxia (i go by river). rawr. i'm a high school hacker and programmer who lives mostly in a terminal.",
    "i captain idktheflag, one of the top high school CTF teams in the US, and mostly play crypto, web and reversing. when i'm not solving CTFs i'm building things: a CTF platform in rust, a poetry editor that scans your verse as you type, a self-hosted mail server, a school LMS client for my terminal.",
    "started programming at 7 and never stopped. competitive programming (USACO Platinum), algorithms, data structures, web dev. also osu! (top 200k global). this blog is where the writeups, rants and build logs end up.",
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
USES = {
    "desktop & shell": [("arch + hyprland", "daily driver, tiling wm (fedora userland with mostly arch components)"), ("ghostty", "terminal. i do basically everything in it"),
                        ("fish + zoxide", "shell, and `z` instead of `cd`"), ("neovim", "custom config tuned for speed and competitive programming (see Neovim Dots on the projects page)"),
                        ("mpv, ffmpeg, yt-dlp", "media, from the terminal")],
    "languages & tooling": [("python + uv", "scripts, CTF tooling, this site's build"), ("rust + cargo", "cctf.rs, bromine-tui, anything that should be fast and correct"),
                            ("c++", "competitive programming"), ("js/ts + bun", "web stuff"), ("go", "game server work"), ("git + gh", "obviously")],
    "ctf toolbox": [("ida pro + binary ninja", "reversing, personal licenses for both"), ("pwntools, z3, sage", "the usual crypto and pwn kit"),
                    ("binwalk, zsteg, exiftool", "forensics and stego triage"), ("netcat, curl, mitmproxy", "web and traffic poking, all from the terminal")],
    "infra": [("cloudflare workers", "all four sites here are static-asset workers, plus dns"), ("ovh vps", "mail (postfix, dovecot, rspamd, opendkim, roundcube) and dev stacks"),
              ("docker + kubernetes", "per-team challenge instancing for cctf.rs"), ("tailscale", "private networking between machines")],
    "this site": [("python-markdown + pygments", "posts are markdown files, built to static html"), ("katex", "math rendered at build time, no client js"),
                  ("make", "one command builds, checks, deploys and verifies everything")],
}
# (name, github repo, short description, install note). name = the ~/.config/<name> it links to.
DOTS = [
    ("hypr", "TogiFerretFerret/hypr", "hyprland lua config (EVA-00 // ASAHI): modules, binds, animations, a CIELAB k-means color pipeline, QML lockscreen", "built for apple silicon / asahi; needs a hyprland with lua config support"),
    ("quickshell", "TogiFerretFerret/quickshell", "the bar, wallpaper picker, mpris + karaoke lyrics, notification daemon, weather dashboard (Material You via matugen)", "needs quickshell and matugen; wallpaper picker: touch /tmp/qs-wallpaper-picker"),
    ("nvim", "TogiFerretFerret/nvim-dots", "neovim, from the ground up. lazy.nvim, custom dashboard", "avante.nvim needs `make BUILD_FROM_SOURCE=true` in its lazy dir"),
    ("fish", "TogiFerretFerret/fish-config", "fish shell: tide prompt, abbreviations, zoxide, helper functions", "some functions assume my machine (playerctl, zenity, ...)"),
    ("fastfetch", "TogiFerretFerret/fastfetch", "the NERV / MAGI fastfetch layouts, wide and narrow, with colorsync", "wants a terminal that can show images (ghostty)"),
    ("ghostty", "TogiFerretFerret/ghostty", "terminal config plus GLSL shaders", ""),
    ("mpv", "TogiFerretFerret/mpv", "mpv config, scripts and fonts", ""),
    ("yazi", "TogiFerretFerret/yazi", "yazi file manager keymap and theme", ""),
    ("rofi", "TogiFerretFerret/rofi", "launcher, clipboard and wallpaper menus", ""),
    ("swaync", "TogiFerretFerret/swaync", "notification center theme and toggles", ""),
    ("matugen", "TogiFerretFerret/matugen", "color templates that retheme everything from the wallpaper", "templates write into the other configs, install it alongside them"),
]
DOT_SHOTS = [("terminal-wide", "terminal + fastfetch (NERV layout)"), ("wallpaper-switcher-1", "wallpaper picker in quickshell"), ("dashboard-clear", "weather / calendar dashboard"),
             ("quickshell-mpris", "mpris player"), ("quickshell-karaoke", "karaoke lyrics + cava visualizer"), ("rofi", "rofi launcher"),
             ("nvim-dash", "neovim dashboard"), ("fastfetch-colorsync-wide", "colorsync: everything recolors from the wallpaper"), ("lockscreen", "QML lockscreen")]
PROJECTS = [
    ("aimrpg", "in development", "indie game i'm lead dev on. someone else's project, i run the dev side.", "Go, Postgres", ""),
    ("cctf.rs", "2026", "CTFd rebuilt from scratch in Rust. hand-rolled SMTP/JWT, rhai scripting, per-team k8s instancing.", "Rust, Kubernetes", "cctf-rs"),
    ("Prosody Writer", "2026", "realtime poetry editor: live stress, meter, rhyme, sound devices and form detection. an incremental DP over the full Prosodic library, so scansion never enumerates pronunciations.", "Python, FastAPI, Prosodic, JavaScript", "prosody-writer"),
    ("Personal Website", "2026", "this site. static, no build framework. six subdomains, a curl-able terminal version of it, and a one-line dotfiles installer.", "Python, HTML, CSS, Cloudflare Workers", ""),
    ("paste.riverxia.sh", "2026", "tiny text pastebin: curl it, expiring pastes, delete tokens, rate limited.", "JavaScript, Cloudflare Workers KV", ""),
    ("Hyprland dots", "2025-2026", "from-scratch hyprland rice on apple silicon: lua config, quickshell UI, CIELAB wallpaper color pipeline. installs with one curl.", "Lua, QML, Python, GLSL", ""),
    ("AI Vision Assistant", "2025, wip", "real-time visual analysis assistant.", "Python, TensorFlow, OpenCV", ""),
    ("Neovim Dots", "2025-2026, wip", "custom neovim config for speed and competitive programming.", "Lua, Vimscript", ""),
    ("Aluminum (HCHS Alt)", "2025-2026, wip", "reverse engineered Blackbaud client. closed source.", "Python, Flask, Node.js", ""),
    ("CP Trainer", "2024", "practice algorithm problems with automated testing.", "Next.js, Node.js, PostgreSQL", ""),
    ("osu! Analyzer", "2024, deprecated", "gameplay data analysis.", "Python, Flask, TensorFlow", ""),
]
PROJECT_LINKS = {
    "paste.riverxia.sh": [("try it", "https://paste.riverxia.sh")],
    "Hyprland dots": [("gallery + installer", "https://dots.riverxia.sh"), ("repo", "https://github.com/TogiFerretFerret/dotfiles")],
    "aimrpg": [("website", "https://aimrpg.com"), ("steam", "https://store.steampowered.com/app/4947810")],
    "cctf.rs": [("repo", "https://github.com/TogiFerretFerret/cctf.rs")],
    "Prosody Writer": [("repo", "https://github.com/TogiFerretFerret/prosody-writer")],
}
BUTTONS = [("GitHub", "#000", "#fff", SOCIALS[0][1]), ("CTFtime", "#900", "#fff", SOCIALS[1][1]),
           ("osu!", "#e4a", "#fff", SOCIALS[2][1]), ("AO3", "#900", "#fc9", SOCIALS[3][1])]

e = html.escape

# my own 88x31 (drawn by a friend; source in button/). hotlinking is fine, it is 2 KB.
BUTTON_HTML = f'<a href="https://{DOMAIN}/"><img src="https://{DOMAIN}/riverxia.gif" width="88" height="31" alt="riverxia.sh"></a>'

# visitor counter: one Firestore REST call per browser session (rules: see README)
COUNTER_JS = """(function(){var P="riverxia-dev-portfolio",K="AIzaSyC1dC4f5h8_WeOQnvrblH3VJ8pdeU4Iey4",
D="projects/"+P+"/databases/(default)/documents",U="https://firestore.googleapis.com/v1/",el=document.getElementById("hits");
function show(n){el.textContent=String(n).padStart(7,"0")}
function seen(){try{return sessionStorage.getItem("hit")}catch(x){return 1}}
function mark(){try{sessionStorage.setItem("hit","1")}catch(x){}}
if(seen()){fetch(U+D+"/counters/visits?key="+K).then(function(r){return r.json()}).then(function(d){show(d.fields.count.integerValue)}).catch(function(){})}
else{fetch(U+D+":commit?key="+K,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({writes:[{transform:{document:D+"/counters/visits",fieldTransforms:[{fieldPath:"count",increment:{integerValue:"1"}}]}}]})})
.then(function(r){return r.json()}).then(function(d){show(d.writeResults[0].transformResults[0].integerValue);mark()}).catch(function(){})}})();"""


# blog tag filter: progressive enhancement, without js the full list just stays visible
TAG_JS = "<script>" + """(function(){var li=[].slice.call(document.querySelectorAll("#posts li")),ch=[].slice.call(document.querySelectorAll("#tagbar a")),none=document.getElementById("none");
function cur(){return new URLSearchParams(location.search).get("tag")||""}
function apply(t){var n=0;li.forEach(function(x){var hide=!!t&&(","+x.dataset.tags+",").indexOf(","+t+",")<0;x.hidden=hide;if(!hide)n++});
ch.forEach(function(a){a.classList.toggle("on",a.dataset.tag===t)});none.hidden=n>0;document.title=(t?"#"+t+" - ":"")+"blog - riverxia"}
document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a[data-tag]");if(!a||e.metaKey||e.ctrlKey||e.shiftKey)return;
e.preventDefault();var t=a.dataset.tag;history.pushState(null,"",t?"?tag="+encodeURIComponent(t):location.pathname);apply(t)});
window.addEventListener("popstate",function(){apply(cur())});apply(cur())})();""" + "</script>"


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
<div class="box mybtn"><h3>link to me</h3><p><picture><source media="(prefers-reduced-motion: reduce)" srcset="riverxia.png"><img src="riverxia.gif" width="88" height="31" alt="riverxia.sh"></picture></p>
<details><summary class="dim">copy the html</summary><textarea readonly rows="5" onfocus="this.select()">{e(BUTTON_HTML)}</textarea></details></div>
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
    """posts/<slug>.md -> url /<slug>.html. `id:` in front matter is the legacy numeric comment id (keeps old Firestore
    comments attached); posts without one use their slug as the comment key."""
    out = []
    for f in sorted(POSTS.glob("*.md")):
        t = f.read_text()
        meta, body = {}, t
        m = re.match(r"---\n(.*?)\n---\n(.*)", t, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = m.group(2)
        legacy = int(meta["id"]) if meta.get("id", "").isdigit() else None
        # optional `time: HH:MM` orders posts that share a date (display shows only the date)
        when = meta.get("time", "") if re.fullmatch(r"\d{1,2}:\d{2}", meta.get("time", "")) else ""
        out.append(dict(slug=f.stem, title=meta.get("title", f.stem), date=meta.get("date", ""), time=when.zfill(5) if when else "",
                        desc=meta.get("description", ""), tags=[x.strip() for x in meta.get("tags", "").split(",") if x.strip()],
                        body=body, legacy_id=legacy, comment_key=str(legacy) if legacy is not None else f.stem))
    HIDDEN.clear()
    if not INCLUDE_FUTURE:
        HIDDEN.extend(p["slug"] for p in out if p["date"] > TODAY)
        out = [p for p in out if p["date"] <= TODAY]
    # newest first. same date: later `time:` first; posts without a time sort after those with one,
    # then by legacy id (higher = newer), then by slug so the order is always deterministic.
    out.sort(key=lambda p: (p["date"], p["time"], p["legacy_id"] or 0, p["slug"]), reverse=True)
    return out


def build_tui(posts):
    """dist/www/riverxia.sh: bash TUI of the site (template in tui/riverxia.sh, site data embedded as shell strings)."""
    host = lambda sub: f"https://{DOMAIN}" if sub == "www" else f"https://{sub}.{DOMAIN}"
    contact = html.unescape(CONTACT)
    nl = "\n\n"
    texts = [
        nl.join(["## about", *ABOUT, "## contact", f"* email: {contact}", *[f"* {n}: {u}" for n, u in SOCIALS],
                 "## skills", *[f"* {k}: {v}" for k, v in SKILLS.items()],
                 "## around the site", f"* {host('blog')} - writeups, rants, build logs", f"* {host('projects')} - things i made", f"* {host('uses')} - tools, languages, infra",
                 f"* {host('dots')} - hyprland rice + one-line installer (see the dots tab)",
                 f"* {host('guestbook')} - guestbook, open to everyone: curl -d name=you -d message=hi guestbook.{DOMAIN}",
                 f"* {host('paste')} - tiny text pastebin: echo hi | curl --data-binary @- paste.{DOMAIN}"]),
        "",  # posts tab is a list, generated at runtime
        nl.join(["## ctf teams", *[f"* {n} - {r}, {k} {u}" for n, r, k, u in TEAMS], "## awards & stuff", *[f"* {a} - {b}" for a, b in AWARDS]]),
        nl.join(["## projects", *[f"* {t} ({y}) - {d} stack: {s}" + "".join(f" [{n}: {u}]" for n, u in PROJECT_LINKS.get(t, [])) + (f" [writeup: {host('blog')}/{post}]" if post else "")
                                  for t, y, d, s, post in PROJECTS]]),
        nl.join(f"## {k}\n" + "\n".join(f"* {n} - {d}" for n, d in v) for k, v in USES.items()),
        nl.join(["## dots", f"hyprland on apple silicon, built from scratch. gallery: {host('dots')}",
                 "## install", f"* all of it, interactively: curl -s dots.{DOMAIN} | bash", f"* just some: curl -s dots.{DOMAIN} | bash -s -- --only nvim,ghostty,fish",
                 "* flags: --list --dry-run --all --yes. existing configs are moved to a backup, never deleted. no sudo.",
                 "## components", *[f"* {n} - {d} (github.com/{r})" for n, r, d, _ in DOTS]]),
    ]
    data = ["TAB_NAMES=(home posts ctf projects uses dots)"]
    data += [f"TEXT_{i}={shlex.quote(t)}" for i, t in enumerate(texts)]
    for var, key in (("P_SLUG", "slug"), ("P_DATE", "date"), ("P_TITLE", "title")):
        data.append(f"{var}=(" + " ".join(shlex.quote(p[key]) for p in posts) + ")")
    data.append("P_TAGS=(" + " ".join(shlex.quote(",".join(p["tags"])) for p in posts) + ")")
    data.append(f"BLOG={shlex.quote(host('blog'))}\nSITE={shlex.quote(host('www'))}")
    tpl = (ROOT / "tui" / "riverxia.sh").read_text()
    (DIST / "www" / "riverxia.sh").write_text(tpl.replace("#@DATA@", "\n".join(data)))


def build(posts):
    if DIST.exists():
        shutil.rmtree(DIST)
    css = (ROOT / "style.css").read_text()
    for _, sub in SUBS:
        (DIST / sub).mkdir(parents=True)
        (DIST / sub / "style.css").write_text(css)
        for f in ("riverxia.png", "riverxia.gif"):
            shutil.copy(ROOT / "button" / f, DIST / sub / f)

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
<section class="box"><h2>skills</h2><ul>{sk}</ul></section>
<section class="box"><h2>site map</h2><ul><li><a href="{url('blog')}">blog</a> <span class="dim">writeups, rants, build logs</span></li>
<li><a href="{url('projects')}">projects</a> <span class="dim">things i made</span></li>
<li><a href="{url('uses')}">uses</a> <span class="dim">tools, languages, infra</span></li>
<li><a href="{url('dots')}">dots</a> <span class="dim">hyprland rice + one-line installer</span></li>
<li><a href="{url('paste')}">paste</a> <span class="dim">tiny text pastebin</span></li>
<li><a href="{url('guestbook')}">guestbook</a> <span class="dim">say hi!</span></li></ul></section>
<section class="box"><h2>terminal version</h2><p>prefer a terminal? this site has a tui:</p>
<pre class="wrap"><code>curl -s riverxia.sh | bash</code></pre>
<p class="dim">or with wget (it always saves as index.html):</p>
<pre class="wrap"><code>wget riverxia.sh; bash index.html</code></pre>
<p>and my dotfiles, one line:</p>
<pre class="wrap"><code>curl -s dots.{DOMAIN} | bash</code></pre>
<p class="dim">plain bash, <a href="{url('www', 'riverxia.sh')}">read it first</a> if you like. h/l tabs, j/k move, enter reads a post, q quits.</p></section>
</div>"""
    (DIST / "www" / "index.html").write_text(page("www", "riverxia", body, "river's corner of the internet"))
    gb = f"""<h1>~*~ guestbook ~*~</h1><p class="tagline">sign it! no account, no approval. entries show up right away (rate limited, so be nice).</p>
<section class="box" id="guestbook"><noscript>the guestbook form needs javascript. from a terminal: <code>curl -d name=you -d message=hi guestbook.{DOMAIN}</code></noscript></section>
<p class="dim">terminal: <code>curl guestbook.{DOMAIN}</code> to read it, <code>curl -d name=you -d message='hi!' guestbook.{DOMAIN}</code> to sign it.</p>"""
    (DIST / "guestbook" / "index.html").write_text(page("guestbook", "guestbook - riverxia", gb, "sign river's guestbook", extra='<script type="module" src="guestbook.js"></script>'))
    shutil.copy(ROOT / "guestbook-client.js", DIST / "guestbook" / "guestbook.js")
    (DIST / "www" / "_redirects").write_text(f"/guestbook https://guestbook.{DOMAIN}/ 301\n/guestbook.html https://guestbook.{DOMAIN}/ 301\n")

    items = ""
    for t, y, d, s, post in PROJECTS:
        ls = list(PROJECT_LINKS.get(t, []))
        if post:
            ls.append(("writeup", url("blog", post + ".html")))
        l = "<p>" + " ".join(f'<a href="{e(u)}">[{e(n)}]</a>' for n, u in ls) + "</p>" if ls else ""
        items += f"<section class='box'><h2>{e(t)}</h2><p class='dim'>{e(y)}</p><p>{e(d)}</p><p class='dim'>stack: {e(s)}</p>{l}</section>"
    (DIST / "projects" / "index.html").write_text(page("projects", "projects - riverxia", f"<h1>projects.{DOMAIN}</h1><div class='cols'>{items}</div>"))

    shots = "".join(f"<figure class='shot'><a href='shots/{f}.webp'><img src='shots/{f}.webp' alt='{e(c)}' loading='lazy'></a><figcaption class='dim'>{e(c)}</figcaption></figure>" for f, c in DOT_SHOTS)
    comps = "".join(f"<li><b><a href='https://github.com/{r}'>{e(n)}</a></b> <span class='dim'>&mdash; {e(d)}</span>" + (f"<br><span class='dim'>note: {e(note)}</span>" if note else "") + "</li>" for n, r, d, note in DOTS)
    dots_body = f"""<h1>dots.{DOMAIN}</h1><p class="tagline">hyprland on apple silicon, built from scratch. nothing copied from anyone else.</p>
<section class="box"><h2>install</h2><p>pick what you want, it asks first:</p><pre class="wrap"><code>curl -s dots.{DOMAIN} | bash</code></pre>
<p class="dim">or just some of it (no questions beyond the confirm):</p><pre class="wrap"><code>curl -s dots.{DOMAIN} | bash -s -- --only nvim,ghostty,fish</code></pre>
<p class="dim">wget: <code>wget dots.{DOMAIN}; bash index.html</code>. flags: <code>--list</code> <code>--dry-run</code> <code>--all</code> <code>--yes</code>.
it shallow-clones each repo into <code>~/.local/share/riverxia-dots</code> and symlinks it into <code>~/.config</code>. anything already there is <b>moved</b> to a timestamped backup, never deleted. no sudo, no package installs.
<a href="{url('dots', 'dots.sh')}">read the script first</a>, please.</p>
<p class="dim">heads up: these were written for one machine (an M-series macbook running asahi). expect to adjust monitors, paths and packages.</p></section>
<section class="box"><h2>components</h2><ul>{comps}</ul>
<p class="dim">sddm (NERV theme) needs root so the installer skips it: <a href="https://github.com/TogiFerretFerret/nerv-sddm">nerv-sddm</a>. everything also lives together in <a href="https://github.com/TogiFerretFerret/dotfiles">dotfiles</a>.</p></section>
<h2>screenshots</h2><div class="shots">{shots}</div>"""
    (DIST / "dots" / "index.html").write_text(page("dots", "dots - riverxia", dots_body, "river's hyprland dotfiles and a one-line installer"))
    inst = (ROOT / "dots" / "install.sh").read_text()
    data = ["C_NAME=(" + " ".join(shlex.quote(n) for n, *_ in DOTS) + ")", "C_REPO=(" + " ".join(shlex.quote(r) for _, r, *_ in DOTS) + ")",
            "C_DESC=(" + " ".join(shlex.quote(d) for _, _, d, _ in DOTS) + ")", "C_NOTE=(" + " ".join(shlex.quote(n) for *_, n in DOTS) + ")"]
    (DIST / "dots" / "dots.sh").write_text(inst.replace("#@DATA@", "\n".join(data)))
    shutil.copytree(ROOT / "dots" / "shots", DIST / "dots" / "shots")

    paste_body = f"""<h1>paste.{DOMAIN}</h1><p class="tagline">a tiny text pastebin. pastes expire; nothing lives forever.</p>
<section class="box"><h2>new paste</h2><form method="post" action="/" class="cform"><textarea name="c" rows="14" required placeholder="paste text here" maxlength="262144"></textarea>
<label>expires in <select name="ttl"><option value="1h">1 hour</option><option value="1d">1 day</option><option value="7d" selected>7 days</option><option value="30d">30 days</option></select></label>
<button type="submit">paste it</button></form></section>
<section class="box"><h2>from a terminal</h2><pre class="wrap"><code>echo hello | curl --data-binary @- paste.{DOMAIN}
curl -T notes.txt "paste.{DOMAIN}?ttl=1d"
some-command 2>&1 | curl --data-binary @- paste.{DOMAIN}</code></pre>
<p class="dim">you get the url back. the delete token comes back in the <code>x-delete-token</code> header (<code>curl -i</code> to see it): <code>curl -X DELETE -H 'x-delete-token: ...' url</code>.
text only, 256 KiB max, 30 pastes per hour per ip, ttl one of 1h 1d 7d 30d. raw: <code>/raw/&lt;id&gt;</code>. don't paste secrets, i can read the database.</p></section>"""
    (DIST / "paste" / "index.html").write_text(page("paste", "paste - riverxia", paste_body, "text pastebin on cloudflare workers kv"))

    ub = "".join(f"<section class='box'><h2>{e(k)}</h2><ul>" + "".join(f"<li><b>{e(n)}</b> <span class='dim'>&mdash; {e(d)}</span></li>" for n, d in v) + "</ul></section>" for k, v in USES.items())
    (DIST / "uses" / "index.html").write_text(page("uses", "uses - riverxia", f"<h1>uses.{DOMAIN}</h1><p class='tagline'>the tools, languages and infra i actually use</p><div class='cols'>{ub}</div>"))

    md = markdown.Markdown(extensions=["fenced_code", "tables", "codehilite"],
                           extension_configs={"codehilite": {"noclasses": True, "pygments_style": "native"}})
    rows = ""
    for p in posts:
        md.reset()
        tags = " ".join(f"<a class='tag' href='{url('blog')}?tag={e(t)}'>{e(t)}</a>" for t in p["tags"])
        text, exprs = extract_math(p["body"].replace("/blog/assets/", "assets/"))
        content = render_math(md.convert(text), exprs)
        has_math = bool(exprs)
        (DIST / "blog" / f"{p['slug']}.html").write_text(page("blog", p["title"] + " - riverxia",
            f"<p><a href='{url('blog')}'>&lt;&lt; back to blog</a></p><h1>{e(p['title'])}</h1><p class='dim'>{p['date']} {tags}</p><article class='box'>{content}</article><section class='box' id='comments' data-post='{e(p['comment_key'])}'><noscript>comments need javascript.</noscript></section>", desc=p["desc"], extra='<script type="module" src="comments.js"></script>',
            head_extra='<link rel="stylesheet" href="katex/katex.min.css">\n' if has_math else ""))
        chips = " ".join(f"<a class='tag' href='?tag={e(t)}' data-tag='{e(t)}'>{e(t)}</a>" for t in p["tags"])
        rows += f"<li data-tags='{e(','.join(p['tags']))}'><span class='dim'>{p['date']}</span> <a href='{p['slug']}.html'>{e(p['title'])}</a> {chips}<br><span class='dim'>{e(p['desc'])}</span></li>"
        (DIST / "blog" / f"{p['slug']}.md").write_text(f"# {p['title']}\n{p['date']}  [{', '.join(p['tags'])}]\n\n{p['body'].strip()}\n")
    counts = Counter(t for p in posts for t in p["tags"])
    tagbar = ("<div class='box' id='tagbar'><b>filter by tag:</b> <a class='tag on' href='.' data-tag=''>all</a> "
              + " ".join(f"<a class='tag' href='?tag={e(t)}' data-tag='{e(t)}'>{e(t)} ({n})</a>" for t, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])))
              + "</div>")
    (DIST / "blog" / "index.html").write_text(page("blog", "blog - riverxia", f"<h1>~*~ blog ~*~</h1><p><a href='rss.xml'>[rss]</a></p>{tagbar}<section class='box'><ul class='loose' id='posts'>{rows}</ul><p id='none' class='dim' hidden>no posts with that tag.</p></section>", extra=TAG_JS))
    feed = "".join(f"<item><title>{e(p['title'])}</title><link>{url('blog', p['slug'] + '.html')}</link><description>{e(p['desc'])}</description></item>" for p in posts)
    (DIST / "blog" / "rss.xml").write_text(f'<?xml version="1.0"?><rss version="2.0"><channel><title>riverxia</title><link>{url("blog")}</link><description>blog</description>{feed}</channel></rss>')
    redirects = []  # old /postN urls -> new slugs (cloudflare workers static assets honours _redirects)
    for p in posts:
        if p["legacy_id"] is not None:
            redirects += [f"/post{p['legacy_id']} /{p['slug']} 301", f"/post{p['legacy_id']}.html /{p['slug']} 301"]
    (DIST / "blog" / "_redirects").write_text("\n".join(redirects) + "\n")
    shutil.copy(ROOT / "comments.js", DIST / "blog" / "comments.js")
    kdist = ROOT / "node_modules" / "katex" / "dist"
    if kdist.exists():
        (DIST / "blog" / "katex" / "fonts").mkdir(parents=True)
        shutil.copy(kdist / "katex.min.css", DIST / "blog" / "katex" / "katex.min.css")
        for f in (kdist / "fonts").glob("*.woff2"):
            shutil.copy(f, DIST / "blog" / "katex" / "fonts" / f.name)
    shutil.copytree(ROOT / "assets", DIST / "blog" / "assets")
    shutil.copy(ROOT / "bimi.svg", DIST / "www" / "bimi.svg")  # BIMI logo (SVG Tiny PS)
    recent = "".join(f'<li><a href="{url("blog", p["slug"] + ".html")}">{e(p["title"])}</a></li>' for p in posts[:5])
    nf = f"""<h1>404</h1>
<pre class="wrap" aria-hidden="true">  ,_,     ~ page not found ~
 (o,o)    this url went off to play osu!
 {{`"'}}    and never came back.
 -"-"-</pre>
<p>whatever you were looking for isn't here (or moved). try one of these:</p>
<ul><li><a href="{url('www')}">home</a></li><li><a href="{url('blog')}">blog</a> <span class="dim">(filterable by tag)</span></li>
<li><a href="{url('projects')}">projects</a></li><li><a href="{url('uses')}">uses</a></li></ul>
<h2>latest posts</h2><ul>{recent}</ul>"""
    for _, sub in SUBS:
        (DIST / sub / "404.html").write_text(page(sub, "404 - riverxia", nf))
    build_tui(posts)


if __name__ == "__main__":
    import fcntl  # one build at a time: two builds racing in dist/ crash each other (a second one waits here)
    _lock = open(ROOT / ".build.lock", "w")
    fcntl.flock(_lock, fcntl.LOCK_EX)
    posts = load_posts()
    build(posts)
    print("built", len(posts), "posts" + (f" ({len(HIDDEN)} scheduled, hidden until their date: {', '.join(HIDDEN)})" if HIDDEN else ""))
