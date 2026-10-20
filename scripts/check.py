#!/usr/bin/env python3
"""Pre-deploy sanity checks (fast, offline). Exits non-zero on any problem.
  - every post has front matter with title/date/description/tags, a valid date and optional time/id
  - no duplicate slugs or legacy ids, and every referenced local image exists
  - nothing that looks like a credential in the files that get published or committed
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
problems = []

def bad(msg):
    problems.append(msg)

ids = {}
for f in sorted((ROOT / "posts").glob("*.md")):
    t = f.read_text()
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not m:
        bad(f"{f.name}: missing front matter"); continue
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for key in ("title", "date", "description", "tags"):
        if not meta.get(key):
            bad(f"{f.name}: front matter is missing '{key}'")
    if meta.get("date") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"]):
        bad(f"{f.name}: date must be YYYY-MM-DD, got {meta['date']!r}")
    if meta.get("time") and not re.fullmatch(r"\d{1,2}:\d{2}", meta["time"]):
        bad(f"{f.name}: time must be HH:MM, got {meta['time']!r}")
    if meta.get("id"):
        if not meta["id"].isdigit():
            bad(f"{f.name}: id must be a number (it is the legacy comment key)")
        elif meta["id"] in ids:
            bad(f"{f.name}: id {meta['id']} is also used by {ids[meta['id']]}")
        else:
            ids[meta["id"]] = f.name
    for img in re.findall(r"!\[[^\]]*\]\(/blog/(assets/[^)\s]+)\)", t):
        if not (ROOT / img).exists():
            bad(f"{f.name}: image {img} does not exist")

# high-confidence credential shapes only, so this never cries wolf
PATTERNS = {
    "cloudflare key (cfk_...)": r"\bcfk_[A-Za-z0-9]{20,}",
    "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "github token": r"\bgh[pousr]_[A-Za-z0-9]{30,}",
    "aws access key": r"\bAKIA[0-9A-Z]{16}\b",
    "slack token": r"\bxox[abpr]-[A-Za-z0-9-]{10,}",
    "auth header with a value": r"X-Auth-Key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9]{20,}",
}
targets = [*ROOT.glob("posts/*.md"), ROOT / "README.md", ROOT / "build.py", ROOT / "offline.py", ROOT / "Makefile",
           ROOT / "comments.js", ROOT / "style.css", *ROOT.glob("scripts/*"), *ROOT.glob("webmail/**/*")]
for f in targets:
    if not f.is_file():
        continue
    try:
        t = f.read_text()
    except UnicodeDecodeError:
        continue
    for name, pat in PATTERNS.items():
        if re.search(pat, t):
            bad(f"{f.relative_to(ROOT)}: looks like a credential ({name})")

if problems:
    print("check FAILED:", *problems, sep="\n  - ")
    sys.exit(1)
print(f"check ok ({len(ids)} legacy ids, {len(list((ROOT / 'posts').glob('*.md')))} posts)")
