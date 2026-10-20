---
title: reversing my school's lms login with mitmproxy
date: 2026-09-30
time: 12:30
description: my school's lms changed its sign-in endpoints and broke my hand-written client. i recorded a real browser session with mitmproxy and rebuilt the login from the capture. a b2c + google flow with a two-host cookie handoff, an api that says "expired" four different ways, and a login trick that only works because the page fails.
tags: reversing,mitmproxy,python,writeup
---

# reversing my school's lms login

my school's lms (a blackbaud k-12 deployment) changed its sign-in endpoints one day, and my hand-written client for it just... died. the old endpoints `azureadb2c/state` and `azureadb2c/callback/bbid/B2C_1A_OIDC` started returning 404.

so i did what you do when someone changes an api on you without telling you: i recorded a real browser session and read the dump.

(i'll write `<school>` for my school's hostname and `<user>` for my username. no tokens, cookies, ids or emails in here, and the raw captures stay on my machine because they contain my live session.)

## the setup

i already had a client called bromine, part of a custom frontend i'd built for the same lms. it had two problems. the endpoints were gone, and it parsed `Set-Cookie` by array position (`split(";")[9]`, `split(";")[6]`), which is exactly as fragile as it sounds.

before going back to a capture, i'd tried a few things for the *login itself*, and they all lost:

- **a full web proxy (ultraviolet + wisp):** too heavy, and the public wisp instances were geoblocked or flagged by google.
- **mitmproxy / a hosts-file MITM as the login mechanism:** works, but needs a local CA to be trusted.
- **playwright:** my daily browser is a firefox fork that playwright can't drive.
- **what i landed on:** a tiny local listener plus a userscript.

the irony is that mitmproxy lost as the *login mechanism* and came right back as the *analysis tool*.

## the captures

two recordings, both of me logging in and clicking around:

| capture | size | flows | time | what's in it |
|---|---|---|---|---|
| `flows` | 26,039,946 bytes | 911 | 2 min 58 s | login, then browsing the lms |
| `flows-tasks` | 1,815,025 bytes | 153 | 1 min 16 s | login, then creating/ticking/deleting a throwaway personal task |

26 mb is too much to read by eye, so i started with the shape, not the bodies: `mitmdump -nr flows -v "~u azureadb2c/v2/state"`, and the same for `callback`, `oauth2/token` and `session/csrf`. then a small script using mitmproxy's `FlowReader` to list every distinct `(method, normalized path)`.

(first attempt died with `ModuleNotFoundError: No module named 'mitmproxy'`. `uv run --with mitmproxy` fixed it.)

## the new login

here's the new sign-in as it appears in the capture (host, path, status):

```text
POST sts.sky.blackbaud.com   /azureadb2c/v2/state        200   <- replaces the old .../azureadb2c/state
GET  id.blackbaud.com        .../B2C_1A_OIDC/oauth2/v2.0/authorize   302
GET  accounts.google.com     /o/oauth2/v2/auth           200   (the google sign-in)
POST id.blackbaud.com        .../oauth2/authresp         302
GET  sts.sky.blackbaud.com   /azureadb2c/v2/callback/bbid 302   <- carries ?state&code
POST sts.sky.blackbaud.com   /oauth2/token               200
POST sts.sky.blackbaud.com   /session/csrf               200
POST sts.sky.blackbaud.com   /oauth2/token               200
POST sts-sso.myschoolapp.com /cookie                     302   <- hands off to the school's host
POST sts-sso.myschoolapp.com /oauth2/token               200
POST sts-sso.myschoolapp.com /session/renew|csrf|ttl     200   <- then repeats as a keep-alive loop
```

three services are involved:

- **`id.blackbaud.com`:** azure b2c, the identity provider, which hands off to google.
- **`sts.sky.blackbaud.com`:** blackbaud's token service.
- **`sts-sso.myschoolapp.com` and `<school>.myschoolapp.com`:** the school's sso and the lms itself, where a cookie called `t` authenticates api calls.

the shape that my library ended up implementing:

1. `POST .../azureadb2c/v2/state` returns a `state` value. build the authorize url from it and open it in the browser.
2. you sign in with google, and the browser lands on `.../v2/callback/bbid?state=...&code=...`.
3. exchange that `code` for an `AuthSvcToken` cookie, then `POST /session/csrf` and `POST /oauth2/token`.
4. `POST sts-sso/cookie`, then `POST sts-sso/oauth2/token`, then `GET /api/bbid/login?loginTypeId=1`, which finally sets the lms cookie `t`.
5. `session/renew` rotates credentials later, which is what lets the app mint a new `t` without opening a browser.

## the capture trick

this is my favorite part. the hard step is getting the single-use `code` out of the redirect without a proxy, a headless browser, or touching the login page.

the trick is that the app registers the login attempt from code, so *the browser you sign in with never got the state cookie*. when google redirects back, the callback page fails and renders an error instead of redirecting. that failure leaves the `code` sitting in the url, readable. so a userscript just posts the url to a local listener:

```js
// the TUI/login.py registered the login attempt from code, so this browser lacks the
// state cookie and the callback renders an error page instead of redirecting.
// That leaves the single-use `code` sitting in the URL for us to hand over.
GM_xmlhttpRequest({ method: "POST", url: "http://127.0.0.1:8420/cb", data: location.href, ... });
```

661 bytes of javascript. no proxy, no CA, no browser automation. the page "fails" and the failure is the feature.

## war stories

**1. http 400 on the school handoff.** after step 4 i got `sts-sso/cookie: unexpected HTTP 400`, with this body:

```json
{"errors":{"StsDestinationUrl":["The StsDestinationUrl field is required."]},"type":"urn:blackbaud:model-validation-error",...}
```

the `/cookie` form needs a `stsDestinationUrl` field that my first reconstruction left out. add it, done.

**2. two cookies with one name.** the sign-in sets `AuthSvcToken` on *two different hosts* (the token service and the school's sso), and mixing them up breaks later steps. the fix was to stop treating cookies as one jar and track them per phase, by name instead of by position. the rust test for it is named `the_login_flow_keeps_the_two_auth_svc_tokens_apart`, which i'm pretty proud of.

**3. "expired" has four faces.** a stale `t` cookie produced a 302, or a 401, or a 403, or a 200 with an anonymous page. worse, a genuine 403 (a teacher not sharing their gradebook, say) looks the same as an expired token. so:

- a 302 or 401 means expired,
- a 403 means expired *only if* `/api/webapp/userstatus` says `TokenValid` is false,
- a 200 whose context has no `UserId` also means expired.

a real refusal becomes its own separate error. in the rust client:

```rust
if status.as_u16() == 401 || status.is_redirection() { return Err(Error::SessionExpired); }
if status.as_u16() == 403 && !self.token_valid() { return Err(Error::SessionExpired); }
```

**4. the assignment center lies about things due today.** i found this by comparing the center's status for an item against the assignment's *own* record for the same item. they disagree for the missing/overdue/due-today buckets, so the fix is to take the status from the item's own record there (a rust constant called `STALE_STATUS_BUCKETS`).

**5. the gradebook's 403.** `hydrategradebook` returns 403 unless you send `studentUserId`. also, the school hides cumulative grades (`Access.HasCumulativeAccess` is false), so only per-assignment scores are available and any total is just points earned / points possible, unweighted.

**6. task links can't be removed by omission.** at some point i asked "why can't we remove a link once set?" the task edit endpoint takes the *full object*, and omitting `SectionId`/`AssignmentId` is what unlinks. my first edit method preserved the old link, which is why it looked impossible.

## numbers

| thing | value | where it came from |
|---|---|---|
| distinct hosts in the first capture | 37 | count of `request.host` |
| busiest hosts | 295 lms, 138 cdn, 101 `src-e1`, 70 `sts-sso` | same |
| distinct lms `/api/` endpoints | 86 (30 in the tasks capture) | normalized `(method, path)` |
| responses by type | 321 json, 146 html, 124 jpeg, 61 js | `content-type` |
| auth-related flows | 89 and 51 | hosts with `sts`, `id.blackbaud`, `accounts.google`, `b2c` |

one read of one capture each, nothing averaged.

## rough edges

- i only wrapped about a third of the 86 endpoints. the rest are written up as "reads worth wrapping".
- login still depends on a userscript and a fixed local port (8420).
- the captures contain live session cookies and bearer tokens. they don't go in a repo, and they shouldn't sit in a downloads folder either.

the next two posts are what i built on top of this: a python mcp server, and a rust terminal ui.
