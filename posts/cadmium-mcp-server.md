---
title: cadmium — an mcp server so an ai can read my school's lms
date: 2026-09-30
description: a local, single-user mcp server that lets an ai assistant read my classes, assignments, grades and files and update assignment status and tasks. output in a compact text format that's 40% to 99.9% smaller than the api's json. built and live-tested against my real account in one day.
tags: python,mcp,ai,writeup
---

# cadmium

after the [login reverse-engineering](lms-login-mitmproxy.html), i had a working client for my school's lms. the next obvious question: what if an ai assistant could use it?

so i built cadmium, a local mcp server (stdio, single user, runs on my machine) that exposes my school's lms to an ai: classes, assignments, grades, the activity feed, files. and a few write actions.

yes, an ai (claude code) wrote most of the code for a tool that lets an ai read my homework. i directed, it typed. the live testing against my real account was the fun part.

## where it started

the starting point was a handoff doc i pasted into the session. it described a fastmcp-based `server.py` with 4 tools (`list_classes`, `get_class_info`, `get_assignments`, `get_assignment_details`), a client `apiwrapper.py` with a stray `print(te)` (which is *bad* on a stdio transport, because stdout is the protocol), a broken `authwrapper.py`, and a mostly unused `CONFIG.py`.

the original brief said "read-only access, for personal use only". my first message in the session changed that: *"we aren't quite going full read-only, i want to be able to write like... assignment in-progress etc."*

i also said the old code was written before i'd started CTFs, back when i was around USACO bronze. so this wasn't a patch, it was a rewrite done properly. that's the "from the ground up".

## what it does

21 tools:

- **read:** `list_classes`, `get_class_info`, `get_assignments`, `get_assignment_details`, `get_assignment_center`, `get_activity_feed`, `list_class_topics`, `get_topic`, `get_announcements`, `list_class_files`, `list_school_files`, `get_roster`, `get_grades`
- **files:** `read_file` (text extraction), `download_file`, `view_file` (pdf pages as images), `print_file` (via `lpr`)
- **write:** `set_assignment_status`, `create_task`, `update_task`, `delete_task`

a typical session goes like this:

1. the assistant calls `get_assignment_center`. with no valid session, the server opens the sign-in page in my browser and returns "sign-in required, then retry".
2. i sign in with google. a userscript posts the callback url to `127.0.0.1:8420`, and the session is saved to `~/.bromine-mcp/session.json` (mode 0600) and renewed silently from then on.
3. the next call returns compact text, small enough to read in a chat.
4. "mark the english as in-progress" calls `set_assignment_status`. "make a study task for tomorrow" calls `create_task`.
5. for a file-submission assignment with no submission, asking to mark it completed is refused, with the reason.

## how it works

- **stack:** python 3.14, the `mcp` 2.x sdk (`MCPServer`), `requests`, `pypdf`, `pypdfium2`, `pillow`. tests use `pytest` and `responses`. managed with `uv`.
- **layout:** `server.py` (the tools, 423 lines), `apiwrapper.py` (typed api calls, 327), `authwrapper.py` (login, 231), `views.py` (projects raw api json into small dicts, 284), `lean.py` (the encoder, 119), `bb_login.py` (saved session, refresh, browser sign-in, 150), plus small `files.py`, `render.py`, `printing.py`, `capture_server.py` and `login.py`.

every read tool runs the same pipeline: `apiwrapper` fetches the raw json, `views` keeps only the useful fields (strips html, turns the api's `-2147483648` sentinel into null), and `lean.encode` writes the text.

that last step uses **LEAN**, a compact format [i was pointed to](https://github.com/fiialkod/lean-format): `key:value` lines and tab-separated tables like `name[n]:col<TAB>col`, with `T`/`F`/`_` for true/false/null. my encoder is encode-only. there's no decoder, since the only reader is the model.

errors go through a decorator so a failure reaches the model as text instead of the sdk's useless bare "Error executing tool".

## decisions

- **project the data first, encode second.** the raw assignment center response is 162,860 characters of json. the tool returns 1,264. most of the saving comes from deleting fields nobody needs, and LEAN is the cherry on top.
- **auto-login inside the tool call.** the first failing call starts the browser sign-in instead of just failing. clients that can't show an elicitation prompt get "sign in, then retry". (i tried elicitation first, then removed it.)
- **safety rules in code, not just in a prompt.** the client refuses to mark a file-submission assignment completed without a submission. i noticed this when i saw the history assignment was a file upload. task edits and deletes also refuse ids that aren't my own tasks.
- **printing: local pdfs inside `~/Downloads` only.** i added an in-server approval prompt, then removed it ("i'll have that be something i set inside claude") and left approval to the client's permission settings.
- **an audit script instead of restarting the server.** `scripts/audit_outputs.py` calls the tool functions directly and lints each output for leftover html, secret-looking words and always-null columns. i asked for it because i didn't want to keep restarting mcp stuff.
- **the name.** aluminum (the frontend) plus bromine (the api client) is an explosion in chemistry. cadmium is what's in control rods: the part that keeps it controlled.

## war stories

**1. fastmcp not found.** `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`, and the message went on to say this is mcp 2.x, where fastmcp was renamed. fix: use `MCPServer`, and set `structured_output=False` so results aren't wrapped as `{"result": ...}`.

**2. imports in the wrong directory.** `ModuleNotFoundError: No module named 'bb_login'` (and later `'server'`) whenever i ran tests or the audit script from somewhere else. fix: put the project root on `sys.path` in the script.

**3. tool failures hid their message.** the sdk showed only "Error executing tool ...", and the real reason (a 403, say) was swallowed. fix: a `ToolError` wrapper so the model sees the text. the test is called `test_tool_errors_reach_the_model_with_their_message`.

**4. a stale cookie and an uncaught 403.** in claude desktop, `get_assignment_center` failed with "Error executing tool", and underneath was `HTTP 403 ... {"Error":"Request authorization failed. Check your username & passw...`. an expired session returned a 403 instead of a redirect and nothing handled it. fix: ask `userstatus.TokenValid`, treat anonymous contexts as expired, retry once after a headless refresh, and otherwise start the browser login.

**5. claude desktop opened nothing.** "about:blank in the wrong browser". desktop launches servers with a stripped environment (no display variables), so `xdg-open` failed with "no method available". fix: `bb_login.desktop_env()` fills `DISPLAY`, `WAYLAND_DISPLAY`, `DBUS_SESSION_BUS_ADDRESS` and friends from `systemctl --user show-environment`, and the retry message includes the url so i can open it by hand.

**6. `lpr` rejected the file.** `lpr failed (1): lpr: Error - unknown option "-".` the code passed `--` before the filename, and this `lpr` treats that as an option. drop the `--`. duplex now uses `-o sides=two-sided-long-edge`. (i haven't actually confirmed duplex on paper yet.)

**7. the print approval dead end.** `Error executing tool print_file: This client can't show an approval prompt, so nothing was printed.` the server tried to ask the client to confirm, and claude code doesn't support that kind of prompt. fix: removed it (see above).

**8. an overbroad edit deleted the task methods.** the 51-test suite caught it: `test_create_and_delete_task` and `test_update_task_preserves_fields_and_resolves_links` both failed with `AttributeError`. the methods were restored. this is why you write tests when an ai is editing your code.

**9. things the first version got wrong,** each fixed with a test: the assignment center's wrong status for items due today, text submissions not being shown (i'd asked "i submitted as text... can we see that?"), and leftover html and the int sentinel in outputs.

## numbers

| thing | value | how |
|---|---|---|
| tools | 21 | `grep -c '^@_tool' server.py` |
| tests | 51 | `uv run pytest --collect-only -q` |
| python lines | 2,805 total (1,819 without tests and the audit script) | `wc -l` |
| assignment center, raw json | 162,860 chars | measured live |
| same, upcoming only, in LEAN | 1,264 chars (compact json of the same data: 2,047) | `get_assignment_center("upcoming")` |
| same, all buckets, in LEAN | 12,229 chars (compact json: 20,812) | `get_assignment_center("all")` |
| `list_classes`, LEAN vs compact json | 671 vs 1,212 | `list_classes()` |
| activity feed, raw json | 366,819 chars for 10 posts | measured live |
| same, in LEAN | 3,464 chars (compact json: 4,071) | `get_activity_feed()` |

these are characters, not tokens (i never ran a tokenizer), and each is a single measurement on live data. "compact json" means the same projected data re-serialized, not the raw api response.

## the day

i started the session around 12:30 and the last python-related request was around 21:00, with long gaps. the first working login with the rewritten auth code was at about 12:55. i renamed it cadmium at 13:20. i registered it in claude desktop at 13:32, and the browser and 403 problems came right after. the file-submission safety rule landed in the afternoon, pdf-as-image viewing around 15:45, printing in the early evening (that's where the three print errors came from), and i registered it in codex at 18:43. so the honest summary is "built and tested in one day", not "built in eight hours of straight work".

## rough edges

- there's no git history for this one, so the story above rests on file times and my memory of the session.
- it's one flat directory of modules, not a package.
- the output format has no decoder, so you can't pipe tool output into other programs.
- sign-in depends on the userscript and on port 8420 being free. two clients signing in at once can collide.
- duplex printing is untested on paper.
- it stays local-only. i have no plans to publish this one.

if you want something on a nicer surface than a chat window, that's the next post: a rust library and a terminal ui for the same lms.
