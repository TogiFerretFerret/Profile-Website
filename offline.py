#!/usr/bin/env python3
"""Build ONE self-contained html file with every blog post, styled like the site. No network needed:
css, KaTeX fonts and images are embedded. usage: python3 offline.py [out.html]"""
import base64, html, re, sys
from pathlib import Path
import markdown
import build  # reuses load_posts / extract_math / render_math

ROOT = Path(__file__).parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "blog-offline.html"
e = html.escape


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def katex_css():
    kd = ROOT / "node_modules" / "katex" / "dist"
    css = (kd / "katex.min.css").read_text()
    # keep only woff2 sources (smaller), embedded as data URIs
    css = re.sub(r",url\(fonts/[^)]+\.woff\) format\(\"woff\"\)", "", css)
    css = re.sub(r",url\(fonts/[^)]+\.ttf\) format\(\"truetype\"\)", "", css)
    css = re.sub(r"url\(fonts/([^)]+\.woff2)\)", lambda m: f"url({data_uri(kd / 'fonts' / m.group(1), 'font/woff2')})", css)
    return css


def main():
    posts = build.load_posts()
    slugs = {p["slug"] for p in posts}
    md = markdown.Markdown(extensions=["fenced_code", "tables", "codehilite"],
                           extension_configs={"codehilite": {"noclasses": True, "pygments_style": "native"}})
    site_css = (ROOT / "style.css").read_text()
    mimes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp"}
    img = {f"assets/{f.name}": data_uri(f, mimes[f.suffix.lower()]) for f in sorted((ROOT / "assets").iterdir()) if f.suffix.lower() in mimes}
    has_math = False
    toc, sections = [], []
    for p in posts:
        md.reset()
        text, exprs = build.extract_math(p["body"].replace("/blog/assets/", "assets/"))
        has_math |= bool(exprs)
        content = build.render_math(md.convert(text), exprs)
        for k, v in img.items():
            content = content.replace(f'src="{k}"', f'src="{v}"')
        content = re.sub(r'href="([a-z0-9-]+)\.html"', lambda m: f'href="#post-{m.group(1)}"' if m.group(1) in slugs else m.group(0), content)
        n = p["slug"]
        tags = " ".join(f"<span class='tag'>{e(t)}</span>" for t in p["tags"])
        toc.append(f'<li><a href="#post-{n}">{e(p["title"])}</a><br><span class="dim">{p["date"]}</span></li>')
        sections.append(f'<section class="box post" id="post-{n}"><h1>{e(p["title"])}</h1>'
                        f'<p class="dim">{p["date"]} {tags}</p><article>{content}</article>'
                        f'<p><a href="#top">^ back to top</a></p></section>')
    css = site_css + "\n" + (katex_css() if has_math else "") + """
.top{position:static}.marq span{animation:none;padding-left:0}
.post{scroll-margin-top:.5rem;margin-bottom:2rem}
aside .toc{padding-left:1rem;font-size:.9rem}aside .toc li{margin-bottom:.5rem}
@media(min-width:46.01rem){aside{position:sticky;top:0;align-self:start;max-height:100vh;overflow:auto}}
"""
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>riverxia.sh blog (offline)</title>
<style>{css}</style></head><body id="top">
<div class="top"><div class="logo"><a href="#top">riverxia<span>.sh</span></a></div>
<div class="marq"><span>blog - offline edition - {len(posts)} posts - no internet required</span></div></div>
<div class="frame">
<aside><div class="box"><h3>~ posts ~</h3><ul class="toc">{''.join(toc)}</ul></div></aside>
<main>{''.join(sections)}
<footer><hr>offline copy of blog.riverxia.sh. read online for comments. &copy; riverxia</footer></main>
</div></body></html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc)
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB, {len(posts)} posts)")


if __name__ == "__main__":
    main()
