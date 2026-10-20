---
title: aevum — we wrote our own game engine because we're chudalinguses
date: 2026-10-20
time: 18:28
description: eleven days, 1,292 commits, one blue mesh on an apple m1, and a vulkan driver that told us we were wrong about the number 64. the story of aevum, the godot-derived engine we started because we're chudalinguses.
tags: gamedev,engine,cpp,bazel,writeup
---

# aevum

so. the game i'm lead dev on (aimrpg, someone else's project, i just boss the code around) runs on a godot fork we call strongdot.

godot is great. we looked at it, appreciated it deeply, and decided to write our own engine instead. because we're chudalinguses.

that's the whole business case. the repo's description on github is *"Aevi memor (aka fuck godot mannn)"* and honestly that covers the strategy, the roadmap and the vibes.

it's called **aevum**. as i write this it's eleven days old, has 1,292 commits, draws a blue mesh on an apple m1, and is nowhere near done. all of that is true at the same time.

(the repos are private, so no links. you'll have to trust me, which, fair, is a lot to ask from someone with this commit history.)

## the sixteen minute bulk import

the first real "uh oh" moment came on october 13.

the plan was never "copy godot". it was a small, controlled engine with only the stuff the game needs. no editor, no mobile, no xr, just a runtime and a command-line toolchain. i kept calling it "the minimum engine needed" in chats, which sounds noble until you realize it mostly meant "stop me from importing everything".

then at 16:03 utc a commit landed that was called *"Import native engine runtime sources and declared dependency closure"*. a giant pile of runtime code, dropped in.

at 16:19 utc, sixteen minutes later, the next commit was *"Remove bulk runtime import and restore Aevum-owned architecture"*.

sixteen minutes. that's about how long it took to look at what we'd just done and go "no, that's the opposite of the plan". so the rule is now: aevum owns its architecture, and only *narrow* godot algorithms get adapted into it, selectively. everything else is ours or it isn't in.

strongdot stays in the repo as a submodule until aevum can carry the whole game. removing it is a release gate. it's not a vibe.

## i have a bazel problem

there was never any scons in this project. bazel showed up in the third commit, with a pinned **zig** toolchain, and it has been a problem ever since (a good one, i'm fine, i'm fine).

the idea is that the whole build is *declared*. compiler, linker, c++ runtime, windows resource tools: all of it comes from a version-pinned zig sdk. nothing gets discovered on your machine through `PATH` or some cache you forgot about. there's a little build contract in the docs that basically says that, and also says the old strongdot build's windows c-runtime hacks do **not** get to come along.

the funniest part of the config is this:

```bazel
build --incompatible_strict_action_env
build --action_env=PATH=
build --host_action_env=PATH=
build:linux_arm --platforms=@zig_sdk//platform:linux_arm64
```

yes, build actions run with an **empty `PATH`**. i'd love to say that means "no host executables whatsoever", but bazel's own linux sandbox bootstrap still calls `/bin/true`, so that would be a lie i'm not allowed to tell. it's "as hermetic as bazel lets us be", which is a less fun thing to put on a poster.

headless checks use a static musl build. graphics builds use a pinned glibc 2.28, because a graphical program has to load the system's gpu drivers dynamically, which a static binary can't do.

the readme also has a very annoying habit of being honest. it separates *running the checks on a real machine* from *cross-compiling for a platform*:

```sh
bazel build //:checks
bazel build --config=linux_arm_graphics //examples:windowed_scene
bazel build --config=win_x86 //examples:windowed_scene
```

the first one runs real checks. the other two just produce binaries that may or may not work on an actual computer. only a device can tell you that. (this will be important later. foreshadowing.)

## what's actually in there

a native foundation layer: lifecycle, atomics, reference counting, vectors, quaternions, transforms, a unicode string, an interned `StringName`, an owning vector and a hash map. things that fail return a result you're forced to look at, and the one spot that can't (a `String` copy) reports the failure and aborts instead of quietly doing something cursed. the matrix and atomic math is inherited from godot and keeps its original mit grants. the memory, diagnostics, strings and containers are our own rewrites, each with a provenance document saying what was reviewed.

on top of that: scenes, nodes, transforms, animation, ui, resource loading, collision, physics, audio, mesh and text rendering, networking pieces, and backends for wayland and x11 (vulkan and opengl) and windows (direct3d). there's no gdextension bridge anywhere. game modules compile directly against native engine classes. the contract literally says *"No GDExtension runtime bridge is planned."*

and here's the sentence i'll keep repeating because it's the most important one in this post: **"exists" is doing a lot of work in that paragraph.** a component existing is not the same as the game running on it.

## the day it all went sideways (on purpose)

i'll be honest about how this thing got written. a lot of the typing is done by coding agents, up to six codex workers at once during the busy stretches, while i review architecture, argue with them, and integrate. i called the setup a "commit factory" and a "compute incinerator" in a chat, and jokingly named myself a "1000x developer". it's a joke. i'm saying it before you do.

here's what that looks like in the git history (utc):

- **oct 9, 7 commits:** initial commit, bazel bootstrap, first extraction of atomic ownership and scalar math out of the godot-derived core.
- **oct 13, 17 commits:** the sixteen minute incident.
- **oct 14, 163 commits:** the engine starts looking like an engine. immutable mesh resources, procedural box geometry, native reflection, indexed meshes through opengl, egl window handles, clipped scrolling. it ended with a commit recording **104 passing engine integration suites**.
- **oct 15, 17 commits:** first client-facing stuff, a reusable native client scene, json parsing.
- **oct 16, 67 commits:** a completion checklist (more on that), module identity for boot admission, tls and http checkpoints.
- **oct 19, 372 commits:** authenticated resource packs, dns transport, mip chains in direct3d 11 and 12. one single hour, 23:00 utc, had **141 commits**.
- **oct 20, 649 commits:** the m1 day.

141 commits in an hour is not something a human does. it's something a human *supervises*, with increasing panic.

here's my github contribution graph for the same stretch, because i needed visual evidence that i'm not exaggerating:

![my github contribution graph from sept 20 to oct 20: a quiet month, small bumps on the 14th and 16th, nothing on the 17th and 18th, then 444 and 509 contributions on the 19th and 20th](/blog/assets/contribution-graph-2026-10-20.png)

a quiet month of me being a normal person with a normal number of commits, two days of nothing, and then a wall. (it counts contributions across all my repos, not just aevum, so the numbers don't match the git log above exactly.)

## the m1 day

so there's this machine: an apple m1 running fedora asahi remix. we built the arm64 graphics target and launched it directly:

```sh
bazelisk build --config=linux_arm_graphics --jobs=2 //examples:windowed_scene
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/asahi_icd.aarch64.json \
  bazel-bin/examples/windowed_scene \
  --window=wayland --renderer=vulkan \
  --font=/usr/share/fonts/google-noto/NotoSans-Regular.ttf
```

and it immediately died:

```
windowed_scene: vulkan initialization failed (5)
```

a gdb trace showed `vkGetPhysicalDeviceSurfaceFormatsKHR` returning **88 surface formats**. our renderer had been written to reject anything over **64**.

88 is more than 64. the driver wasn't broken. *we* were broken. it's the best kind of bug: a number we made up, standing between us and a pixel.

the fix was boring in the good way: bounded dynamic enumeration (up to 4,096 entries), retry if the count changes or the call returns `VK_INCOMPLETE`, and fail explicitly on garbage. after that (a 141 second build, 295 actions, 1,034 cache hits), a native wayland window opened and drew a **blue mesh** with readable text, and kept presenting through a resize sequence from 800x600 down to 320x240 and back to 1000x750.

i'd love to tell you i had a moment. i did not. cyberpunk edgerunners season 2 had come out like 13 minutes earlier, and i was significantly more hyped about that than about the blue mesh. a native vulkan renderer drawing its first pixels on a laptop gpu stack almost nobody targets, and i was thinking about anime. the mesh was fine. it's a good blue mesh. i just had other priorities. the compositor sent 995, 2,460 and 3,412 "presented" feedback events across three saved logs, and no, that's not an fps number, don't quote me on that, it's feedback events. it's also a demo fixture, not the game.

## the stuff that doesn't work

this is the part where i'm supposed to say the demo worked perfectly. it did not.

**opengl is broken on that machine.** `EGL_BAD_MATCH` / `Unsupported surfacetype/colorspace configuration` at `eglCreateWindowSurface`. a mesa override gets further and then fails to render a frame. i don't know why. nobody does yet.

**the text is slightly soft.** at a fractional scale of 160/120 the font was readable but not crisp. maybe glyph positioning, maybe bilinear atlas filtering, maybe the compositor. i don't know. there's an opt-in lcd subpixel mode now. whether it helps on a real display is still a gate.

**files that exist but "don't".** on an arm64 test run, four probes failed with `file not found` for headers that were sitting right there on disk. turns out bazel refuses to let you use headers you didn't declare, which is exactly the point of a hermetic build and exactly as fun as it sounds.

**a timed check is not a pass.** one arm64 `//:checks` run got cut off at 120 seconds, with four confirmed compile failures. that cutoff is my fault: i'm extremely impatient, so i capped test runs at two minutes. the progress line said `1526/2147`, and that's bazel *actions*, not tests. it's incredibly tempting to read that as "71% green". it is not. it's what a run looks like when its owner runs out of patience at 120.055 seconds. do not do that to me.

there's also a commit called *"Fix duplicate local name blocking container regression compilation"*. one of the builds broke because two variables had the same name. i was also doing competitive programming and school work during this stretch of days, so that's about my speed.

## things we talked about (that are not real yet)

a big part of aevum is stuff that started as a chat and may or may not become code. i'm labelling these very clearly, because i've been burned by my own enthusiasm.

- **the names.** i wanted latin ones. *aevum* roughly means "age" or "eternity", and *lumen* ("light") is the planned lighting system. we talked about other names too, and i forgot the losers, which feels fitting.
- **renderer profile names.** the idea: rename godot's three renderer tiers *excelsior*, *stratosphere* and *terra*. they show up in a lighting planning doc, but you can't select them in the engine today.
- **lighting.** the plan in the doc is baked indirect light for static geometry, probes for moving things and realtime direct light and shadows. we also talked about baking along expected player paths and a few fixed-camera tricks. that's the dream. the pipeline is still incomplete.
- **a movement experiment** with source-engine-style feel, and a multiplayer arena i'm not going to describe. both ideas. neither exists.

## the security brain

another thing we kept saying out loud was "the most secure indie game", as a joke. it's a goal. nobody has measured it against anything. here's what the code actually does, so you can judge the joke yourself:

signed things get verified before they're trusted: native modules and module catalogs use ed25519 with a manifest that binds identity, digest, abi, architecture and version. content packages are authenticated encrypted archives. network sessions use verified tls with a signed key exchange, and messages get sealed with xchacha20-poly1305.

the one rule i'm weirdly religious about: **no deterministic nonce fallback, ever.** (at one point i spent a long time yapping at the agents about how it is not okay to have a nonce reuse issue. not okay in any amount, not even for reproducible builds. that rant is more or less where the rule comes from.) every blob gets a fresh random nonce, and if the system's entropy source fails the publishing step aborts instead of limping along. "make the build reproducible" is a very tempting way to quietly ruin an aead.

rollback protection fails closed: a missing, corrupt or replayed floor file is a rejection, with no implicit "zero" default that quietly says yes. everything has size limits and key material gets wiped when stuff goes wrong.

and the docs are blunt about one thing i like a lot: **a signature tells you who wrote the code, not what the code is allowed to do.** so the module design has three tiers: trusted native code in-process, restricted bytecode (a deliberately tiny webassembly host with limits on memory, stack and fuel), and untrusted native code in a separate restricted process.

we also talked about binding keys to the hardware so a copied install can't decrypt. that one's an idea. it isn't in the code.

none of that is a security claim yet. no adversarial review, no production key management. it's principles with some code behind them.

## the boot problem

the boring answer to "is this an engine or a demo" is **boot**: can a real game client start up, load its modules and content, and connect to a server without trusting anything it hasn't checked?

the design says: one boot coordinator owns exactly one pending attempt, with the account and session identity, a generation counter, deadlines, a content snapshot and cancellation. a network channel only gets committed after a real handshake succeeds, and old work is cancelled and drained before new work takes over. dynamic native modules use a restricted c abi (`aevum_native_module_v1`), and godot's old entry symbols are deliberately *not* that.

it's the unglamorous part, and it decides whether this becomes a game or a very elaborate screensaver.

## the numbers (that i'm willing to stand behind)

- **1,292 commits** in eleven days, with 649 of them on october 20 alone.
- about **191,000 lines** of c and c++ written for this (`scc`, excluding vendored libraries and `ext/`, tests included). the whole checkout is 990,368 lines because freetype, harfbuzz, libwebp, re2 and friends live there too.
- 307 test source files. the latest commit message says a 108-suite engine benchmark passed. i'll say "the commit says so" until i've read the raw log.
- the todo file has **84 checked and 170 unchecked** items. that's *not* a completion percentage, and the repo says that itself, because i kept refusing to accept any percentage that didn't have a real denominator.
- `scc`'s cost estimator says this checkout would cost **$37.8 million**, take 54 months and need 61 people. that's a hypothetical model run over vendored code. it's a joke. i'm still going to screenshot it.

## what's not done

basically the game. the shipping modules aren't migrated, boot isn't integrated end to end, we have no full-game run, pointer capture on wayland isn't properly tested, vulkan/opengl/direct3d haven't been validated on real devices (windows gpu especially), the opengl and xwayland failures need retesting, lumen is incomplete, and strongdot is still holding the whole thing up.

cross-compiling for a platform is not the same as the game working on it. the todo says so in bold, many times, and i'd much rather be the person who wrote that than the person who didn't.

## the latin readme

one more thing. i had the aevum readme translated into latin to mess with some friends who study it. it opens with *"Aevum est ambitus exsecutionis proprius, e Godot derivatus, una cum instrumentis operandi sine interfacie graphica ad aimRPGx destinatis."* i cannot tell you if the latin is good. it lives in my downloads folder, not in the repo.

anyway. blue mesh. eleven days. more when something other than a blue mesh renders. (probably a red mesh, honestly.)
