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

