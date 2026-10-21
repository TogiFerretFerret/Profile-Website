# riverxia.sh

Personal site of **riverxia** (river). Hand-made 90s-geocities-style pages, pre-rendered to plain
HTML/CSS. One tiny inline script (the visitor counter), no trackers, no framework.

| site | what |
|------|------|
| `riverxia.sh` | home: about, awards, skills, latest posts |
| `blog.riverxia.sh` | blog (markdown posts in `posts/`) |
| `projects.riverxia.sh` | projects |
| `uses.riverxia.sh` | tools, languages and infra |
| `dots.riverxia.sh` | dotfiles gallery + `curl -s dots.riverxia.sh \| bash` installer (dots/install.sh) |
| `paste.riverxia.sh` | text pastebin on Workers KV (worker/paste.js) |
| `guestbook.riverxia.sh` | open guestbook on Workers KV (worker/guestbook.js) |

## Layout

- `comments.js` — blog comments (Firestore), loaded on post pages. `guestbook-client.js` — the guestbook page (served from guestbook.riverxia.sh).
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

The guestbook is `worker/guestbook.js` on `guestbook.riverxia.sh` (Workers KV `riverxia-guestbook`, no Firebase). Anyone can sign and
entries appear immediately; abuse is limited per hashed ip (3/hour, 30s apart), plus a global 100/hour cap, length limits, reserved names, a
2-link cap and a honeypot. Admin delete: click `[admin]` on the page and paste the token from `~/.config/private/guestbook-admin-token`
(created and uploaded as the `ADMIN_TOKEN` worker secret by deploy-site.sh), or `curl -X DELETE -H "x-admin-token: ..." https://guestbook.riverxia.sh/api/entries/<id>`.
The client is `guestbook-client.js`. From a terminal: `curl guestbook.riverxia.sh`, `curl -d name=you -d message=hi guestbook.riverxia.sh`.

## Develop

```sh
pip install markdown
npm install                            # KaTeX, for math in blog posts
python3 build.py                       # local links, output in dist/
python3 -m http.server -d dist 8000    # open http://localhost:8000/www/
```

## Deploy

Each of `dist/www`, `dist/blog`, `dist/projects`, `dist/uses` is its own Cloudflare Worker (static assets):
`riverxia-www`, `riverxia-blog`, `riverxia-projects`, `riverxia-uses`, `riverxia-dots`, `riverxia-paste`, `riverxia-guestbook`, bound to the seven hostnames (deploy-site.sh attaches a missing custom domain through the CF API).
`riverxia-www` and `riverxia-dots` also run `worker/front.js` on `/`: curl/wget get the bash script (`tui/riverxia.sh` or `dots/install.sh`), browsers get the page. `riverxia-paste` is `worker/paste.js` with a KV namespace `riverxia-pastes` (created by deploy-site.sh).

```sh
export CLOUDFLARE_ACCOUNT_ID=...
export CLOUDFLARE_API_TOKEN=...   # needs Workers edit
./deploy.sh                       # build.py --prod, then wrangler deploy x3
```

Adding a post: drop `posts/<slug>.md` (no number needed) and deploy.
