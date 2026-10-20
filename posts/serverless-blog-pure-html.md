---
title: building a serverless, dynamic blog with pure html and js
date: 2026-01-05
id: 1
description: how i built a (somewhat) secure markdown blog engine that compiles at runtime with vanilla js and firebase, skipping every modern build step and all server infrastructure.
tags: webdev,javascript,firebase,innovative
---

# a blog with no build step

> **update (oct 2026):** this is the story of the *first* version of this blog. i've since rebuilt the whole site as plain pre-rendered html on cloudflare, with a tiny python script instead of runtime compilation. the posts are still just markdown files and the comments are still firebase, but the "compile in your browser" part below is history now. i'm leaving it up because it was a fun idea and i don't delete my crimes.

## the problem with modern web dev

everywhere i go i hear people ranting about the next big framework. "use next.js." "use gatsby." "use hugo."

everything needs a **build step**. you write markdown, run a command, and it spits out static html.

one little issue: to do that you need infrastructure. actually scratch that, you basically need infrastructure for everything now. nothing is plain-ol' html anymore, and compute keeps getting more expensive because every ai startup can raise a ton of money for doing basically nothing.

so i wanted to do something different for my blog. something i (hope) nobody had done before.

pure html. pure markdown. no build step.

(and later on we'll talk about how i added comments while keeping it FREE. i hope.)

## the "runtime compilation" approach

instead of compiling my posts to html *before* i deploy, i compile them *while you're reading them*.

the architecture is surprisingly simple:

1. **storage:** every post is a raw `.md` file in a `posts/` folder.
1. **fetching:** when you load the page, a javascript loop uses `fetch()` to grab those files.
1. **parsing:** a client-side library (`marked.js`) turns the raw markdown into html instantly.

here's the core of the engine:

```javascript
// fetch markdown files dynamically
async function loadPosts() {
    const fetchPromises = [];
    for (let i = 1; i <= CONFIG.postCount; i++) {
        fetchPromises.push(
            fetch(`${CONFIG.postsDir}post${i}.md`)
                .then(response => response.text())
                .then(text => parsePostMetadata(text, i))
        );
    }
    // ... render logic
}
```

this also makes the site incredibly lightweight. no routing library, no virtual dom, no hydration errors. just requests and text manipulation. and all the html/js is in one file too (for... reasons), so it's even more lightweight. (arguably.)

## making it social (serverless comments)

a blog isn't a blog without comments, but static html can't store data. to keep this "serverless" (and free!) i used **google firebase**.

the comment section connects straight to a firestore nosql database (read: free database).

- **reads:** open to the public.
- **writes:** anyone can write (authenticated anonymously, for throttling/security).
- **admin:** i have a verified-badge check that compares my email **hash** against the database to prove it's me, without putting my email in the source. could this be bypassed? possibly. but the badge is set from the poster's id, which i don't believe can be spoofed. someone might fake the *username*, but i don't think they can fake the *badge*, and either way only an admin can delete things at the **firestore** level.

## why this matters

we over-engineer simple problems all the time. (one could make a valid argument that my entire blog is overengineered.)

but by stripping away the frameworks i ended up with a blog that is:

1. **fast:** the "compile" step takes milliseconds on your device.
1. **cheap:** hosted on vercel (frontend) and firebase (backend) for free. *(at the time. see the update at the top.)*
1. **flexible:** i drop a new `.md` file in the folder, bump a number in the config, and it's live.

it's a pile of steaming code, perhaps. but it's *my* pile of steaming code, and it works beautifully.
