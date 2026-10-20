---
title: bromine-tui — my school's lms in my terminal (in rust)
date: 2026-10-20
time: 18:23
description: a mouse-and-keyboard terminal ui and a typed rust client for my school's lms. a persistent cache (first screen in 0.07 s warm), per-kind freshness with quiet background refresh, a feed that stays complete even though the server only returns 10 posts, and one worker thread that renews a lapsed session for all the others.
tags: rust,tui,ratatui,writeup
---

# bromine-tui

the [python server](cadmium-mcp-server.html) was built for an ai to read my lms. this one is for me: a terminal ui with a typed rust client library underneath, for the same lms. it's public and mit licensed: [blackbaud-tui](https://github.com/TogiFerretFerret/blackbaud-tui).

like the others, this was built with claude code. my first message was basically *"make a rust library and start working on a full on mouse+keyboard enabled TUI for blackbaud"*, and then a lot of me steering. the architecture critique in the middle of the day was mine, and it changed the whole thing.

## what it does

four views: **assignments** (grouped by due date, with status buttons and personal tasks: new, edit, link to an assignment, delete), **classes** (about, work, topics, news, files, grades, people), **feed**, and **files**. mouse and keyboard both work. flags: `--demo`, `--no-cache`, `--clear-cache`.

```sh
git clone https://github.com/TogiFerretFerret/blackbaud-tui
cd blackbaud-tui
cargo install --path bromine-tui
bromine-tui --demo   # fake data, no account
bromine-tui          # prompts once for the school username, opens a browser to sign in
```

press `4` for school files, `o` opens a file with the system opener, `d` saves it to downloads, and `P` prints a pdf double-sided after a confirm dialog. `r` refreshes the view you're on, `R` refreshes everything, and old data stays on screen while it does.

## how it's put together

it's a workspace of two crates (rust 2024): `bromine` (the library: sign-in, session file, typed `Client`, models) and `bromine-tui` (the app).

- **dependencies:** `reqwest` (blocking), `ratatui` 0.30, `crossterm` 0.29, `serde`, `chrono`, `dirs`, `open`, `thiserror`, `url`. tests use `mockito` and `tempfile`. no async runtime at all: threads and channels.
- **the tui's modules:** `data.rs` (the `Store`, keyed by a `Key` enum, with fetch times and per-kind lifetimes), `cache.rs` (json on disk, written on its own thread), `worker.rs` (a pool of 4 readers plus one ordered writer, sharing one session), `app/` (pure state and input handling), `ui/` (one file per view), and `demo.rs` (a fake lms).
- **the ui never touches the network.** `App` sends `Cmd`s over a channel and applies the `Event`s that come back.

every kind of data gets its own freshness window:

```rust
pub fn ttl(key: &Key) -> Duration {
    Duration::seconds(match key {
        Key::Center | Key::Feed => 60,
        Key::Detail(_) | Key::ClassRows(_) | Key::News(_) => 300,
        Key::Topics(_) | Key::TopicItems { .. } | Key::ClassFiles(_) | Key::Grades(_) => 600,
        Key::Classes | Key::ClassInfo(_) | Key::People(_) | Key::UserFiles => 3600,
    })
}
```

## the feed that wouldn't page

this was the best bug. the server returns only the newest 10 feed posts. the capture showed `ActivityFeedGet?lastDate=` and `ActivityFeedRefresh?firstDate=<ticks>`, so i tried `lastDate` as both tick fields, as date strings, as an old value, plus `pageSize`, `count` and `top`. every variant returned the identical newest 10.

the endpoint just ignores paging parameters. so the fix isn't a request, it's a data structure: archive every post ever seen, and merge new ones in.

```rust
fn merge_posts(&mut self, fresh: &[FeedItem], now: NaiveDateTime) {
    let mut all = self.posts.take().map(|e| e.value).unwrap_or_default();
    for entry in fresh.iter().map(FeedEntry::post) {
        match all.iter_mut().find(|e| e.key == entry.key) {
            Some(old) => *old = entry,
            None => all.push(entry),
        }
    }
    all.sort_by(|a, b| b.when.cmp(&a.when).then_with(|| a.key.cmp(&b.key)));
    all.truncate(MAX_FEED);
    self.posts = Some(Entry { value: all, fetched: now });
}
```

on top of that, each class's announcements and topics (which *are* complete) get folded into the feed. on my account the header went from `Feed` with 10 items to `Feed (60)`. the limit: posts older than the first run's 10 can't be recovered. history starts the first time you run it.

## one thread renews the session for everybody

with a pool of readers sharing one session, a lapsed session is a thundering herd: four threads all notice at once and all try to log in. so a single thread renews while the others reuse the result:

```rust
fn renew(&self, generation: u64) -> Result<(Arc<Client>, u64), Error> {
    let mut auth = lock(&self.auth);
    if auth.generation != generation
        && let Some(c) = &auth.client
    {
        return Ok((c.clone(), auth.generation));
    }
    auth.client = None;
    let client = self.sessions.renew(&self.tx)?;
    auth.client = Some(client.clone());
    auth.generation += 1;
    Ok((client, auth.generation))
}
```

the `generation` counter is the trick: if somebody renewed since you started your request, just take their client.

## decisions

- **blocking http and threads instead of async.** the load is a few calls at a time. the cost is no cancelling in-flight requests.
- **reads in parallel, writes in order.** two quick status toggles on one assignment must arrive in order.
- **optimistic status changes with undo,** because the ui should respond at once and the server sometimes refuses.
- **stale data stays visible.** a refresh never replaces a filled pane with "loading...". a failed refresh keeps the old data, says so once, and isn't retried for 60 seconds.
- **one json file as the cache** (mode 0600 in a 0700 directory), ignored if its version or owner differs. details capped at 300 entries, the feed at 600.
- **a `Sessions` trait as the seam,** so the session-sharing logic is tested against mock servers.
- **safety rules live in the library,** not only the ui: no completing an unsubmitted file assignment, only your own tasks are editable, and downloads are limited to two lms path prefixes.
- **windows dropped on purpose,** and macOS supported. the `open` crate replaced a hand-rolled `xdg-open` call.

## more war stories

**the download url check ignored the port.** a test caught a url on a different port of the same host being accepted. the check now compares scheme, host *and* port, and the test rejects `http://127.0.0.1:1/ftpimages/a`.

**a pending-set collision.** a class's assignments were never requested when its section id equalled its lead section id, because two sets were keyed alike. i split them, and later the `Store` replaced pending sets entirely.

**first-frame scroll.** the first section header scrolled off at startup, because the list height isn't known until the first draw. `keep_visible` is a no-op at height 0 and gets re-run at draw time.

**a closure is not generic.** `E0308: mismatched types` when one `let entry = |value| Entry {...}` closure was used for different value types inside `Store::apply`. fix: write the struct literal in each arm.

**over-eager fetching.** a test failed with `left: [] right: [ClassInfo(101), ClassRows(101)]`, because loading the topics list called `want_class_data()` even when the classes tab wasn't open. fix: return early when `self.tab != Tab::Classes`.

**a test helper that drained its own evidence.** the freshness tests failed because `loads(&rx)` removes the requests, so the app believed they were in flight forever. fix: an `answered()` helper that answers whatever it drains.

**macos can't be checked locally.** `cargo check --target aarch64-apple-darwin` fails in the c build of `aws-lc-sys`, because there's no macos toolchain on my linux box. macos is only verified by the ci matrix, which passed all three commits.

**a repo that already existed.** after an interrupted `gh repo create`, the retry printed `GraphQL: Name already exists on this account (createRepository)`. the first call had already created the empty repo, so the push just went to it.

**a compile-fix cascade.** splitting `app.rs`, `ui.rs` and `tests.rs` into modules produced about 80 errors at once (`E0432 unresolved import`, `E0609 no field ...`, `E0282 type annotations needed`), cleared module by module. the test suite was ported, not rewritten.

## numbers

| thing | value | how |
|---|---|---|
| commits | 3 | `git log --oneline` |
| rust lines | 8,705 (library 2,046, library tests 812, tui 5,761 including its tests) | `git ls-files '*.rs'` with `wc -l` |
| tests | 105 (bromine: 6 unit, 11 auth, 18 client; tui: 69; 1 doctest) | `cargo test --workspace` |
| dependency crates | 255 unique in the tree | `cargo tree --workspace --prefix none`, deduplicated |
| binary size | debug 84,514,392 bytes, release 9,493,648 bytes | `ls -l target/{debug,release}/bromine-tui` |
| release build | 2 min 36 s cold on my machine | cargo's "Finished" line |
| start to first content, cold | 0.41 s | a pty script on my live account with `--clear-cache` |
| start to first content, warm | 0.07 s | same script, second run |
| feed entries | 10 before, 60 after | same account |
| read threads, feed cap, detail cap, retry | 4, 600, 300, 60 s | `READERS`, `MAX_FEED`, `MAX_DETAILS`, `RETRY_AFTER` |

the timings are single runs, no repeats and no variance.

## rough edges

- windows is unsupported, by choice.
- feed history starts at your first run. older posts can't be fetched.
- the cache is one file rewritten whole, with a version check but no migration.
- cache and session files hold personal school data unencrypted (mode 0600).
- sign-in still needs a userscript and a fixed local port.
- not done: submitting work, anything beyond per-assignment scores, opening links inside topics.
- macos has never been run by hand.
- the library is tied to one school's lms deployment.

if you want to poke at it without an account, `bromine-tui --demo` runs against a fake lms.
