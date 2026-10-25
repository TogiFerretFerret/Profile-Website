---
title: my website is a makefile now (and it 404'd itself once)
date: 2026-10-24
time: 20:10
description: seven cloudflare workers, one makefile, math rendered at build time, and the day a half-finished upload made every page on my blog 404. the build system story, including a scheduled-posts feature i built and immediately ignored.
tags: webdev,make,cloudflare,devops,python
---

# my website is a makefile now

this site is a pile of small static things: a python script that turns markdown posts into html, one stylesheet, some javascript, and a handful of cloudflare workers that serve the results. no framework, no bundler. (i have opinions about frameworks. see post 1.)

the one thing it needed was a single command that does *all of it*. so now i type `make all`. here's what that turned into, mostly through things going wrong.

## what `make all` does

1. installs the two dependencies it needs (a python markdown package, and katex from npm)
2. runs sanity checks (more on those)
3. builds every site into `dist/`, with real production links
4. deploys each one to its own worker (there are seven now)
5. then **checks every single page on the live site actually answers 200**

it skips whatever hasn't changed. the second time you run it, the whole thing takes about 0.18 seconds and does nothing. that part is satisfying in a way i can't explain to normal people.

the trick is plain make: `dist/.built` depends on every source file (all the posts, the stylesheet, the scripts), and a `.deploy-stamp` depends on `dist/.built`. touch a post and make rebuilds and redeploys. touch nothing and it doesn't. i'm not clever, make is just good.

## math, without a script on the page

some of my posts have math in them, like the cryptography writeups. i didn't want to ship a math-rendering javascript library to every reader.

so the math is turned into html **at build time**. the build pulls every `$...$` and `$$...$$` out of the markdown (carefully skipping code blocks, so a shell `$PATH` doesn't get "rendered"), sends them all to a tiny node script that calls katex, and swaps the rendered html back in. katex's fonts get copied to the blog's assets. the pages that have no math don't even load the katex stylesheet.

there is exactly zero client-side math code. it just shows up rendered.

## the checks that save me from myself

a short script runs before every build:

- every post has a title, date, description and tags, and the date is a real date
- no two posts share a legacy comment id (they key my old comments)
- every image a post mentions actually exists
- **nothing in any published file looks like a credential.** it looks for the shapes of api keys and private key blocks. it only checks high-confidence patterns, so it never cries wolf, and the day it does catch something it will have paid for itself

## the day every page 404'd

this is the story i actually wanted to tell.

i deployed the blog. wrangler said it deployed. a minute later i checked a post: 404. the index: 404. the css? fine, 200. the old `/post15` redirect? 301, working perfectly. only the html pages were gone.

what happened: the upload of the site's files had been **partial**. the small files made it, the html didn't, and the deploy still reported success. so for a few minutes the blog was a stylesheet and some redirects pointing at nothing.

re-running the upload fixed it. the thing i took away: *deploy success is not site success*. so now the deploy script verifies, for real:

- after uploading a site, it requests **every page it just built** from the live domain
- anything that isn't 200 gets reported
- if anything is missing it re-uploads and checks again, up to three times
- if it's *still* missing, it exits non-zero and says so loudly

that last bit means a bad deploy can't get past me anymore. it also made `make verify` possible, which just runs the check without uploading anything.

## the build that crashed itself

another one: a build died with `FileExistsError` while creating a folder. nothing was wrong with the code. i ran the build again with nothing else running and it worked fine.

as far as i can tell, two builds were running at the same time and writing into the same output folder, one deleting what the other was creating. (i had more than one thing poking at the repo that day.) so the build now takes a lock before it starts, and a second build just waits its turn. one `flock` call. embarrassing how long it took me to think of it.

## small things that turned out to matter

**posts on the same day.** i have several posts dated the same day, and without a rule they'd sort by filename. so there's an optional `time:` field in the front matter that orders same-day posts (newest first). the page never shows the time. posts without one fall back to their old numeric id.

**an offline copy.** one command builds a single html file with every post, the stylesheet, the math fonts and the images all embedded, so i can read the blog on a train with no signal. no network requests, tested with the network switched off.

**sizing code.** inline code in a different font looked huge next to my serif body text. monospace fonts have a much taller x-height, so at the same size they look bigger. the fix was scaling code to 85% so the letters match in size. i measured the x-height in a real browser to make sure instead of squinting.

## scheduled posts (that i built and then didn't use)

i wanted to drip four posts out over four days, so i built scheduled publishing:

- the build **hides any post whose date is in the future** (in my timezone, new york)
- the makefile writes today's date into a stamp file and the build depends on it, so the first `make all` on or after a post's day would rebuild and publish it
- `make preview` shows the scheduled posts so i can check them before they go live
- there's a script that deploys from a **fresh clone of the main branch**, never from my working folder, so an unattended run can't publish a half-edited file

it all works. then i decided i didn't want to wait, changed the dates, and published all four posts at once. the feature is still in there, quietly hiding any post i date in the future, waiting for the next time i have patience.

## what i'd tell you if you're about to do this

1. **verify after deploy.** "uploaded" and "live" are different facts.
2. **make the date an input** if you want scheduled posts. a build that doesn't know what day it is can't know when to publish. (and then be patient enough to use it.)
3. **lock your build.** the first time two of them collide you will lose twenty minutes to a confusing error.
4. **keep the whole thing boring.** a python script, a stylesheet and make will outlive whatever framework i am tempted by next.
