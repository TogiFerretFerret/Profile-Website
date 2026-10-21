---
title: curl riverxia.sh | bash — a terminal version of my site, a dotfiles installer, and a pastebin
date: 2026-10-21
description: how one cloudflare worker makes riverxia.sh answer curl and wget with a bash tui instead of html, why `wget riverxia.sh; bash riverxia.sh` can never work, the one-line installer behind dots.riverxia.sh, and a tiny pastebin on workers kv. plus the dumb thing i found in my fish config.
tags: webdev,cloudflare,bash,dotfiles,writeup
---

# curl riverxia.sh | bash

i have too many subdomains and i regret nothing. 

this started as a joke: what if you could run my website? not open it, *run* it. `curl riverxia.sh | bash` and you get a tui version of the site in your terminal. then it got out of hand, and now there's a dotfiles installer and a pastebin too. this is how all of it works.

## the trick

the site is a pile of static html on cloudflare workers (one worker per subdomain). static assets can't look at who's asking, so for the homepage i put a tiny worker in front that can:

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ua = request.headers.get("user-agent") || "";
    if (url.pathname === "/" && request.method === "GET" && /^(curl\/|wget|gnu wget)/i.test(ua)) {
      const r = await env.ASSETS.fetch(new Request(new URL(env.SCRIPT, url), request));
      return new Response(r.body, { status: r.status, headers: { "content-type": "text/x-shellscript; charset=utf-8", vary: "user-agent", "cache-control": "no-store" } });
    }
    return env.ASSETS.fetch(request);
  },
};
```

if the user agent is curl or wget and they asked for `/`, hand back the script. otherwise it's the normal page. browsers never notice.

two details that matter. first, `run_worker_first: ["/"]` in the wrangler config, so *only* the root goes through the worker and every other file is still a plain static asset (fast, free, cached). second, `vary: user-agent` and `no-store`, so no cache anywhere can hand curl the html or hand a browser the script.

## the part where i was wrong

my original plan was `wget riverxia.sh; bash riverxia.sh`. cute, symmetrical, and **impossible**.

wget names the downloaded file after the url you typed. the url is `riverxia.sh/`, there's no filename in it, so you get `index.html`. always. i tried the clever fix: redirect wget to `/riverxia.sh` so the *final* url ends in the right name. wget2 (the new one, what i have) still saves `index.html`, because it keeps the original name unless you pass `--trust-server-names`. same for `--content-disposition`. both off by default.

so what works is:

```sh
curl -s riverxia.sh | bash                   # the normal way
wget riverxia.sh; bash index.html            # yes, really
wget riverxia.sh/riverxia.sh; bash riverxia.sh
```

`bash index.html` is honestly kind of funny. i kept it.

## the tui is just bash

no python, no dependencies, just bash and the usual coreutils. the script is a template (`tui/riverxia.sh`) with a `#@DATA@` marker. my build script (`build.py`) already knows everything on the site, my about text, awards, posts, projects, so it dumps all of it into the template as shell strings with `shlex.quote` and writes `riverxia.sh` next to the html. the terminal version updates itself every time i deploy, because it's built from the same data as the website.

some things that were annoying:

- **stdin is the script.** when you pipe into bash, stdin is the pipe, so `read` would eat the rest of the script. every keypress read has to come from `/dev/tty` explicitly.
- **no tty, no tui.** if stdout isn't a terminal or there's no `/dev/tty`, it falls back to dumping everything as plain text (`--plain` forces it).
- **posts are fetched lazily.** the script embeds the post *list* but not the post bodies. pressing enter runs `curl blog.riverxia.sh/<slug>.md | less -R`, so i copy each post's markdown next to its html at build time.
- **old-bash manners.** no associative arrays and no `mapfile`, so it mostly behaves on macos's ancient bash 3.2. (i haven't tested it there, and the arrow keys probably want bash 4 for `read -t 0.05`. `h`/`j`/`k`/`l` will work regardless.)
- **testing a tui without tmux.** i don't have tmux installed, so i drove it with a python `pty`, sent it keypresses, and read the screen back. it works!

keys: `h`/`l` or arrows for tabs, `j`/`k` to move, `enter` opens a post, `t` cycles through tags, `q` quits.

## dots.riverxia.sh

i have a dozen-ish dotfile repos (hyprland, quickshell, neovim, fish, fastfetch, ghostty, mpv, yazi, rofi, swaync, matugen...) and a combined one with screenshots. i wanted the same trick for those: `curl -s dots.riverxia.sh | bash`.

installing someone else's dotfiles is a thing people do with `curl | bash` and a lot of crossed fingers, so the installer is built to be boring and safe:

- it shows a numbered list and asks what you want, then asks again before doing anything. `--only nvim,fish`, `--all`, `--yes` skip the questions, **`--dry-run` changes nothing**.
- it shallow-clones each component's repo into `~/.local/share/riverxia-dots` and **symlinks** it into `~/.config`. so you get real git clones you can edit and pull.
- whatever was already at the target is **moved** (never deleted) to `~/.config/.riverxia-dots-backup/<timestamp>/`.
- no sudo, no package installs. the sddm theme needs root so it just links you to the repo.
- the page says clearly: these were written for one machine (hyprland on an m-series mac running asahi), so expect to fix paths and monitors.

the dots page also has a screenshot gallery. the originals are 2-6 mb pngs, so i shrank them to 1600px webp (40-160 kb each) and checked every one for personal stuff before publishing. one screenshot of my browser had my bookmarks in it. it did not make the cut.

the same worker that serves the tui serves this installer, just with a different script. i made the worker generic (`env.SCRIPT` says which file to hand out) so adding more `curl | bash` subdomains is a config line.

## the dumb thing i found

while reading my own repos to write the installer, i found two things i'm not proud of:

1. a wallhaven api key committed in a public repo. (it's a wallpaper site's key. i've decided i'm not going to rotate it. the worst case is i make a new wallpaper account.)
2. my fish config repo tracks `fish_variables`, the file fish uses to store *universal* variables, and i had exported some api keys with `set -Ux`. that file is just plain text inside a git repo, and i have a function that runs `git add .`, commits, and pushes. it was one command away from publishing my cloudflare key. 

(it never actually got committed, i checked the history.) the fix is to keep secrets in a file *outside* the repo, source it from `config.fish`, erase the universal variables, and put `fish_variables*` in `.gitignore` and untrack it. if you've ever typed `set -Ux SOMETHING_KEY ...`, go look at your own.

## paste.riverxia.sh

a pastebin, because every project needs one and workers kv is *right there*.

```sh
echo hello | curl --data-binary @- paste.riverxia.sh
curl -T notes.txt "paste.riverxia.sh?ttl=1d"
```

you get a url back. an 8-character random id maps to the text in kv. it's tiny on purpose:

- **everything expires.** kv has `expirationTtl` built in, so pastes live 1 hour, 1 day, 7 days (default) or 30 days. nothing is permanent.
- **delete tokens.** each paste gets a random token returned in an `x-delete-token` header. only its sha-256 hash is stored, and `curl -X DELETE -H 'x-delete-token: ...'` removes it.
- **text only, 256 kb.** binary uploads get a 415.
- **30 pastes per hour per ip**, counted in kv, because a public write endpoint on my domain is an invitation.
- **served safely.** raw pastes come back as `text/plain` with `nosniff` and a sandbox csp, and the html view escapes everything, so a paste can never become a page on my domain.

the one bug: `curl --data-binary` sends `content-type: application/x-www-form-urlencoded` by default, so my first version tried to parse every raw paste as a form, found no field, and answered "empty paste" to everything. now it only treats a body as a form if it really has the field it wants.

also: don't paste secrets. i can read the database. (see above.)

## the boring glue

adding a subdomain used to mean clicking around in the cloudflare dashboard. now `scripts/deploy-site.sh` does it: it generates a wrangler config for each site, and after deploying it asks the cloudflare api whether the hostname is attached to the worker yet. if not, it attaches it, which also makes the dns record and the certificate. the paste worker's kv namespace is created the same way if it's missing. `make all` builds, checks, deploys, and then fetches every page on every site and makes sure it's a 200.

it also fixed a bug i didn't know i had: my 404 page existed but wasn't being served, because static assets need `not_found_handling: "404-page"` set explicitly. now it's a real 404 with a tiny ascii cat on it.

## so

- try it: `curl -s riverxia.sh | bash`
- steal my dots (carefully): `curl -s dots.riverxia.sh | bash -s -- --dry-run`
- paste something: `echo hi | curl --data-binary @- paste.riverxia.sh`

and [read the scripts](https://riverxia.sh/riverxia.sh) before you pipe them into your shell. you should do that for everyone, including me.
