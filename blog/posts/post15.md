---
title: cctf.rs — I rebuilt CTFd from scratch in Rust
date: 2026-07-09
description: Why I wrote my own CTF platform from zero in Rust. Hand-rolled SMTP and JWT, sandboxed rhai scripting in every corner, per-team Kubernetes instancing, SSE notifications, and a fully headless API. A build log.
tags: rust,ctf,webdev,backend
---

# cctf.rs

I used to run a CTF team and I managed their infra for 6 months, constantly keeping up a in-house CTFd instance for practice. Running a CTF means, at some point, staring at your platform and going "I could do this better." Everyone says that. 

Almost nobody is dumb enough to actually do it. (Other than redpwn)

Dear reader, I did it. (I'm autism)


`cctf.rs` is a CTF platform — think CTFd — rebuilt from zero in Rust as a **headless API**.

no template soup, no monolith, no "just fork it and edit the Jinja." (booo ctfd having to do stupid css to make the chall layout different)

just a JSON + SSE API you point whatever frontend you want at. 

this is the log of how it went and which parts I hand-rolled that I probably shouldn't have.

## headless on purpose

the first decision was the load-bearing one: **the backend renders nothing.** 
every response is JSON, the whole surface is described by an OpenAPI spec, and the actual UI is a separate app that just consumes it. want a different theme? a CLI? a Discord bot that submits flags? go nuts — the platform doesn't care.

this sounds like extra work and it is, but it's the good kind. the backend has exactly one job (be correct about CTF rules) and it never gets tangled up in "how do I center this div." (that's for the disgusting frontend devs)

stack: **axum + sqlx/Postgres**, layered repo → service → handler, everything behind traits so `AppState` doesn't explode into a generic hydra. boring, solid, fast. i wish i hand-rolled this but was too scared. 

## the "hand-roll everything" disease

here's where it stops being sensible. I decided the fun parts should be *mine*, so:

- **JWT, by hand.** and not naively — the classic JWT footgun is the `alg` confusion attack, where you hand the server a token that says "actually verify me with algorithm `none`" or swap HS/RS. so mine verifies the HMAC *before* it trusts a single byte of the header. constant-time compare on the way out. writing your own crypto plumbing is generally a war crime; writing it *carefully, knowing exactly the attack you're defending* is one of the more educational things I've done. (unsurprising cuz im pretty dum)
- **an SMTP client, from scratch.** EHLO, STARTTLS, AUTH LOGIN, MAIL/RCPT/DATA, dot-stuffing, the whole handshake, over rustls. no `lettre`, no library. plus a dev catcher and a Cloudflare Worker that forwards inbound mail to a webhook. do you need to write your own SMTP client in 2026? no. did I learn how email actually works at the wire level? extremely yes. did i already know it from managing a postfix server for 6 months? also yes. 
- **Argon2id** for passwords, because if you're going to store secrets you do it right. lmao

## rhai in every corner

the thing I'm proudest of: there's a little sandboxed scripting engine ([rhai](https://rhai.rs)) threaded through the whole platform, and once it was in one place I couldn't stop.

- **flag validators** can be scripts, not just static strings or regex.
- **hint costs** can be a script — `cost = 50 + solves * 10`, whatever you want. dynamic pricing for hints.
- **registration brackets** (divisions) are gated by a script: `email.ends_with(".edu")` and you're in the collegiate bracket.
- **notification targeting** — you can broadcast an announcement to "everyone who has solved challenge X" by writing a rhai filter that runs over each player's solved set.

every one of those is bounded (max ops, max stack, max string size) so nobody drops an infinite loop into a flag check. it turns "hardcoded feature" into "config," and config is where flexibility lives.

i may eventually handroll this lmao

## the features that were just fun to build

- **per-team Kubernetes instancing.** each team gets their own pod for an instanced challenge, routed by subdomain through a reverse proxy. spin up, reap on a timer, renew lifespans. genuinely one of my favorite subsystems.
- **dynamic-decay scoring** — points fall as more people solve, first blood eats the full value.
- **weighted multi-flag challenges** — partial credit for partial solves.
- **hidden / locked challenges** with *per-field* reveal control (leak the title but not the files, say), max-attempt limits, and prerequisite unlock chains.
- **real-time notifications over SSE** — announcements plus automatic solve / first-blood broadcasts, streamed live, targetable (everyone / specific teams / specific players / a rhai filter).
- **i18n from day one** via Fluent — not just error messages, the *OpenAPI spec itself* gets localized per `Accept-Language`.

that OpenAPI spec, by the way, is hand-written and **drift-guarded**: a test asserts `spec ≡ the route table ≡ the actual router`. if I add an endpoint and forget the docs, CI yells at me. I love a good tripwire.

the opanapi ui is custom too

and all the errors are localized. why am i like this

## war stories

it wasn't all clean. some highlights from the trenches:

- a single **missing comma** in a `CREATE TABLE` statement — valid Rust string, invalid SQL — sat there silently because all the unit tests used an in-memory store and never touched real Postgres. I added a `sqlparser`-based test that parses every DDL statement at `cargo test` time... and *it still didn't catch it*, because the parser was more lenient than Postgres and happily read the following keyword as a "custom type." the thing that actually caught it was wiring up a `make test-all` that boots real Postgres, runs the migrations, and wipes it after. moral: your DB schema is only tested by a database.
- `api.rs` hit **2,000 lines** and I finally split it into per-domain modules. mechanical, satisfying, 0 warnings the whole way.
- when i got so burnt out i spent the entire time watching isthatdecay instead of programming and ended up making them a custom pp counter lmao
## the philosophy

my one rule on this project has been: **more code is fine if it buys flexibility.** YAGNI is good advice right up until you're building the thing you specifically wish existed — then the "extra" abstraction (pluggable storage backends! scriptable everything! a config for every knob!) *is* the point. I'd rather have five storage backends behind a trait than one hardcoded folder path.

## what's next

it's live, it's on [GitHub](https://github.com/TogiFerretFerret/cctf.rs), and it's still cooking — first-blood scoring curves, admin CRUD, import/export, and getting the Astro frontend fully wired to the OpenAPI client. but the core is real: you could run a CTF on this today.

was rebuilding CTFd from scratch a reasonable use of my time? absolutely not. would I do it again? I'm literally still doing it.

— river
