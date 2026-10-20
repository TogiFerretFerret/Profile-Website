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
- `posts/<slug>.md` — blog posts; the filename is the url (`blog.riverxia.sh/<slug>`). front matter: `title`, `date`, `description`, `tags`. `time: HH:MM` (optional) orders posts that share a date, newest first; the date on the page never shows it. `id:` is only set on the first 16 posts: it's their old numeric comment key, so existing comments stay attached. new posts need no `id` (comments are keyed by slug). old `/postN` urls redirect to the slugs via `dist/blog/_redirects`.
- `assets/` — images used by posts.
- `offline.py` — builds one self-contained `dist/blog-offline.html` with every post (css, math fonts and images embedded) for offline reading: `python3 offline.py`.
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

Adding a post: drop `posts/<slug>.md` (no number needed) and deploy.
