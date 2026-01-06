---
title: Building a Serverless, Dynamic Blog with Pure HTML and JS
date: 2026-01-06
description: How I built a (somewhat) secure markdown-based blog engine that compiles at runtime using vanilla JS and Firebase, completely skipping modern build steps or server infrastructure.
tags: webdev,javascript,firebase,innovative
---
## The Problem with Modern Web Dev
Everywhere I go, I hear people ranting about the next big new framework. "Use Next.js" "Use Gatsby" "use Hugo".

Everything needs a "build step";
You write markdown, run a command, and it spits out static HTML.

One little issue - to do that, you need infrastructure. Actually scratch that, you basically need infrastructure for everything. 

Nothing is plain-ol' HTML anymore, and with compute becoming more and more expensive because every ol' AI startup can get a ton of money for doing basically nothing, 

So I wanted to do something different for my blog. Something I (hope) no one had done before. 
Pure HTML. Pure Markdown. No build step.
(and later on, we'll talk about how I added comments while keeping it FREE [I hope])

## The "Runtime Compilation" Approach
Instead of compiling my blog posts to HTML *before* I deploy, I decided to compile *while you are reading them*.

The architecture is surprisingly simple but powerful. 
1. **Storage:** All my posts are just raw `.md` files sitting in a `posts/` directory.
1. **Fetching:** When you load the page, a simple JavaScript loop uses the `fetch()` API to grab these files. 
1. **Parsing:** I use a client-side library (`marked.js`) to turn that raw Markdown text into HTML instantly.

Here is the core logic that powers this engine:
```javascript
// Fetch markdown files dynamically
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

This also makes the site incredibly lightweight. There is no routing library, no virtual DOM, and no hydration errors. Just requests and text manipulation. And at that, all the HTML/JS pretty much is all in one file too (for... reasons) so it's even more lightweight (arguably).

## Making it Social (Serverless Comments)
A blog isn't a blog without comments, but static HTML files can't store data. To keep this "serverless" (and free!), I integrated **Google Firebase**.

The comment section you see below connects directly to a Firestore NoSQL database (read: free database).

* **Reads:** Open to the public.
* **Writes:** Anyone can write (authenticated anonymously for throttling/security)
* **Admin:** I have a special verified badge logic that checks my email **hash** against the database to prove it's me, without exposing my email in the source code. While it is possibly this might be able to be bypassed, the admin badge is set based on poster ID, which I don't believe can be spoofed; while it might be possible to fake the username, I don't think it is possible to spoof the badge, and either way only an admin can delete posts at the **Firestore** level.

