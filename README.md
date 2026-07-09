My personal site — **Riverxia the Hacker** — plus a little markdown blog. A tabbed
profile card (about / awards / skills / projects) and a blog that renders markdown in
the browser. No framework, no build step, no `node_modules`. Pure HTML/CSS/JS. :heart:

## What's in it

**`index.html`** — a single-page profile card:
- Four tabs (**About Me / Awards / Skills / Projects**) with an animated sliding indicator
- A `<canvas>`-drawn avatar (rendered in JS, no image asset)
- **Data-driven content** — the tabs are populated from plain JS objects near the bottom
  of the file (`achievementsData`, `skillsData`, `projectsData`), so adding a skill or a
  project is a one-line edit, no markup wrangling
- Links out to GitHub, Discord, CTFtime, osu!, AO3, and the blog

**`blog/`** — a tiny client-side blog:
- `blog/index.html` `fetch`es `posts/postN.md` and renders it with
  [marked](https://github.com/markedjs/marked)
- Posts live in `blog/posts/*.md` — currently 14 of them

## Tech

- **HTML + vanilla JS** — zero framework, zero bundler
- **[Tailwind CSS](https://tailwindcss.com/)** via CDN for styling
- **[Lucide](https://lucide.dev/)** via CDN for icons
- **[marked](https://github.com/markedjs/marked)** for markdown → HTML in the blog
- Canvas 2D for the avatar

That's the whole dependency list — it's all CDN `<script>` tags. Clone it and it runs.

## Run it locally

The profile page opens straight from disk, but the **blog uses `fetch()`**, which browsers
block on `file://` — so serve it over HTTP:

```sh
python3 -m http.server 8000
# then open http://localhost:8000/           (profile)
#           http://localhost:8000/blog/      (blog)
```

## Editing content

- **Skills / projects / awards:** edit the `skillsData`, `projectsData`, and
  `achievementsData` objects in `index.html` — the page renders straight from them.
- **New blog post:** drop a `blog/posts/postN.md` file and bump the post count in the
  `CONFIG` block at the top of `blog/index.html`.

## Structure

```
index.html          the profile card (markup + data + render JS, all in one file)
blog/
  index.html        markdown blog renderer
  posts/*.md        the posts
  assets/           blog images
```

## Deploy

It's fully static — push and point GitHub Pages (or any static host) at the repo root.
Nothing to build.
(I use a lost vercel account)

---

made with love and questionable life choices by [river](https://github.com/TogiFerretFerret) 🦊

---
bonus: dear hackclub reviewers:

i would appreciate it if before you called my site simple you actually looked at it :smile:
the blog is relatively complex, i mostly designed the site to troll around by having it be all single-files. 

thought it would be funny. it was. it is. 

thank you for your time and consideration!

best,
river

ALSO PLZ PLZ PLZ READ MY EPIC BLOG
it's really cool i promise and i talk about cool and interesting things
