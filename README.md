# riverxia.sh

Personal site of **riverxia** (river). Hand-made 90s-geocities-style pages, pre-rendered to plain
HTML/CSS. One tiny inline script (the visitor counter), no trackers, no framework.

| site | what |
|------|------|
| `riverxia.sh` | home: about, awards, skills, latest posts |
| `blog.riverxia.sh` | blog (markdown posts in `posts/`) |
| `projects.riverxia.sh` | projects |

## Layout

- `comments.js` — blog comments (Firestore), loaded on post pages.
- `build.py` — static generator (Python 3 + the `markdown` package). Content data (about, awards,
  projects, ...) lives at the top of this file.
- `style.css` — the one stylesheet, copied into each site.
- `render_math.js` + `package.json` — build-time KaTeX: `$inline$` and `$$display$$` math in posts becomes static HTML (no client-side math script).
- `posts/*.md` — blog posts with `title/date/description/tags` front matter.
- `assets/` — images used by posts.
- `deploy.sh` — build and deploy all three sites.

The visitor counter is one Firestore REST call (`counters/visits`, project `riverxia-dev-portfolio`),
once per browser session. Firestore rules needed:

```
match /counters/visits {
  allow read: if true;
  allow create: if request.resource.data.count == 1 && request.resource.data.keys().hasOnly(['count']);
  allow update: if request.resource.data.count == resource.data.count + 1 && request.resource.data.keys().hasOnly(['count']);
}
```

## Develop

```sh
pip install markdown
npm install                            # KaTeX, for math in blog posts
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
