# riverxia.sh

Personal site of **riverxia** (river). Hand-made 90s-geocities-style pages, pre-rendered to plain
HTML/CSS. No JavaScript, no trackers, no framework.

| site | what |
|------|------|
| `riverxia.sh` | home: about, awards, skills, latest posts |
| `blog.riverxia.sh` | blog (markdown posts in `posts/`) |
| `projects.riverxia.sh` | projects |

## Layout

- `build.py` — static generator (Python 3 + the `markdown` package). Content data (about, awards,
  projects, ...) lives at the top of this file.
- `style.css` — the one stylesheet, copied into each site.
- `posts/*.md` — blog posts with `title/date/description/tags` front matter.
- `assets/` — images used by posts.
- `deploy.sh` — build and deploy all three sites.

The "now playing" box is read from the latest `Currently Listening To:` git commit message at build time.

## Develop

```sh
pip install markdown
python3 build.py                       # local links, output in dist/
python3 -m http.server -d dist 8000    # open http://localhost:8000/www/
```

## Deploy

Each of `dist/www`, `dist/blog`, `dist/projects` is its own Cloudflare Worker (static assets):
`riverxia-www`, `riverxia-blog`, `riverxia-projects`, bound to the three hostnames.

```sh
export CLOUDFLARE_ACCOUNT_ID=...
export CLOUDFLARE_API_TOKEN=...   # needs Workers edit
./deploy.sh                       # build.py --prod, then wrangler deploy x3
```

Adding a post: drop `posts/postN.md` (next number) and deploy.
