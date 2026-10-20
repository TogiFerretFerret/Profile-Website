---
title: aevum — we wrote our own game engine because we're chudalinguses
date: 2026-10-20
description: a godot-derived, headless, bazel-built native runtime for aimrpgx. 1,292 commits in eleven days, a vulkan driver that reported 88 surface formats to a renderer that expected 64, and an honest list of everything that isn't done yet.
tags: gamedev,engine,cpp,bazel,writeup
---

# aevum

the aimrpgx codebase runs on strongdot, our godot fork. godot is great. we also decided it wasn't enough, because we're chudalinguses.

so we're writing our own engine. it's called **aevum**, it's a godot-derived runtime and headless toolchain, and as of this post it's eleven days old.

(aimrpg is a game i'm lead dev on. it's someone else's project, and this post is about the engine side. the repos are private, so there are no links, and i'm not going into the security design here.)

## why

the honest answer is "we wanted to". the repo's description is *"Aevi memor (aka fuck godot mannn)"*, which is about as close to a design doc as it gets.

the less honest answer, which is also true: we wanted a smaller, controlled engine that does exactly what the game needs, with a build graph we can fully account for. not a full godot editor, not mobile, not xr. just a runtime and a command-line toolchain.

the git history has a revealing moment. on october 13 a **bulk import of runtime sources** landed. **sixteen minutes later** (16:03, then 16:19 utc), a commit titled *"Remove bulk runtime import and restore Aevum-owned architecture"* took it back out. the rule we settled on: aevum owns its architecture and *selectively* adapts narrow godot algorithms, instead of dragging in a giant pile of code and hoping it behaves.

strongdot stays as a submodule until aevum can carry the whole game. removing it is a release gate, not a vibe.

## what it is

headless native toolchain plus runtime, targeting linux x86-64, linux arm64 and windows x86-64. the source tree is split by subsystem: `core`, `world`, `render`, `platform`, `resources`, `audio`, `text`, `physics`, `lumen`, `runtime`, `input`, `animation`, plus `tests` and `tools`.

what exists (per the readme and a long todo file): an object, variant and class system with explicit ownership, scenes, nodes and transforms, animation and ui, resource and module loading, collision queries and physics, audio, mesh, texture and text rendering, and networking components. graphical backends exist for wayland and x11 with vulkan and opengl, and for windows with direct3d.

**"exists" is carrying a lot of weight in that paragraph.** components existing is not the same as the game running on them. more on that below.

## ideas we talked about

a lot of aevum's shape came out of chat conversations before any of it was code. i want to be careful here: **everything in this section is an idea or a plan, not a shipped feature.** i'll say which ones have actually turned into something.

- **latin names.** i wanted the engine and its parts to have latin-flavoured names. *aevum* (roughly "age" or "eternity") won for the engine, and *lumen* ("light") is the planned lighting system. we talked about other latin names too, but i won't pretend i remember the losers.
- **renderer profile names.** the idea was to rename godot's three renderer tiers to *excelsior* (the big desktop one), *stratosphere* (the mobile-ish one) and *terra* (the compatibility one). those names do show up in a lumen planning doc as profiles that need separate performance and memory measurements. they are **not** products you can select today.
- **"the minimum engine needed."** that was literally the phrase for the scope. the git history agrees: the bulk import that got removed in sixteen minutes was the opposite of this.
- **keep the extension api, skip the codegen.** we discussed staying compatible with the godot-extension style of api while avoiding generated editor bindings and a json abi with its overhead. the repo has an api-coverage inventory for this. how much compatibility we really keep is something to check against actual module call sites, not against my memory of a chat.
- **lighting.** the lumen planning doc is the written-down version: offline baked indirect diffuse light for static geometry, irradiance probes for moving objects, and runtime direct lighting and shadows. we also talked about baking along anticipated player paths, fixed-camera geometry tricks and a specialised coordinate representation. of those, only the first group is in the doc, and the whole lighting pipeline is still incomplete.
- **a source-accurate movement experiment** (as in: source-engine-feel movement) and a multiplayer arena i'm not going to describe. both are ideas. nothing about them is implemented in the engine.

## how we think about security

the design goal, said jokingly in chat, was "the most secure indie game". that's a **goal**, not a result. nobody has measured it against anyone, and i'm not going to claim it. what i can describe are the principles, and which parts of them exist in code today:

- **nothing trusted is used before it's authenticated.** native module images and module catalogs are signed (ed25519, with an exact manifest that binds the module's identity, payload digest, abi, architecture and version). content packages are authenticated encrypted archives. network sessions use verified tls with a signed key exchange (x25519), and messages are sealed with xchacha20-poly1305.
- **no deterministic nonce fallback, ever.** the package format derives keys with hkdf-sha-256 and uses a **fresh random nonce for every blob**. if the system's entropy source fails, publishing the package aborts. an aead is only as good as its nonce discipline, and "make builds reproducible" is a very tempting way to wreck it.
- **fail closed, with explicit policy.** the rollback protection that stops old content from being replayed treats a missing, corrupt or replayed floor file as a rejection. there is no implicit zero floor and no default that quietly says yes. trust keys and minimum versions are passed in by the caller on purpose.
- **bound everything, wipe on failure.** hashing, hmac and package reads all have explicit size ceilings (64 mib of input in the hashing context, 1 mib for hmac keys), and key material gets wiped when something goes wrong.
- **a signature says who wrote the code, not what the code may do.** the module design separates three modes: authenticated trusted native code in process, capability-limited bytecode (a deliberately restricted webassembly host with limits on memory, stack and fuel), and untrusted native code in a separately restricted process. the first one gives you provenance, not isolation, and the docs say so.
- **an idea we talked about:** binding keys to the hardware, so a copied install can't be decrypted somewhere else. i'm listing that as an idea. it isn't in the code.

none of this makes a security claim yet. adversarial review, production key management and the full game integration are all still ahead.

## the build is the interesting part

aevum is built with **bazel 9.2.0** and a pinned **zig toolchain** (`hermetic_cc_toolchain`), so the compiler, linker, c++ runtime and windows resource tools all come from a version-pinned zig sdk. there was never any scons: bazel showed up in the third commit.

headless checks use a static musl toolchain. graphics builds use a pinned **glibc 2.28** target, because a graphical program has to load the system's gpu drivers dynamically. a few lines from `.bazelrc`:

```bazel
build --incompatible_strict_action_env
build --action_env=PATH=
build --host_action_env=PATH=
build:linux_arm --platforms=@zig_sdk//platform:linux_arm64
```

yes, native actions run with an **empty `PATH`**. no, "no host executables whatsoever" is not a claim we can make: bazel's own linux sandbox bootstrap still calls `/bin/true`. so it's "as hermetic as bazel lets us be".

the readme is careful to separate two things that are easy to confuse: running the validation checks on a native host, and merely *cross-compiling* an artifact for another platform.

```sh
bazel build //:checks
bazel build --config=linux_arm_graphics //examples:windowed_scene
bazel build --config=win_x86 //examples:windowed_scene
```

the first one runs checks. the other two produce binaries that may or may not work on a real device. only a device test tells you that.

## the apple m1 demo

on a fedora asahi remix machine (apple m1), we built the arm64 graphics target and launched it directly:

```sh
bazelisk build --config=linux_arm_graphics --jobs=2 //examples:windowed_scene
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/asahi_icd.aarch64.json \
  bazel-bin/examples/windowed_scene \
  --window=wayland --renderer=vulkan \
  --font=/usr/share/fonts/google-noto/NotoSans-Regular.ttf
```

the build took 141.128 seconds (295 executed actions, 1,034 action-cache hits). the result was a native wayland window with a **blue mesh** and readable font ui, and it kept presenting through a resize sequence (800x600, 1280x720, 640x480, 320x240, 1000x750 logical). the compositor sent 995, 2,460 and 3,412 "presented" feedback events across three saved logs.

(that last number is *not* fps. it's presentation feedback events. i'm not going to dress it up.)

this is a demo fixture, not the game.

## war stories

**the driver that had too many formats.** the first launch on the m1 died with `windowed_scene: vulkan initialization failed (5)`. a gdb trace showed `vkGetPhysicalDeviceSurfaceFormatsKHR` returning **88 surface formats**. our renderer rejected anything over **64**.

so the failure wasn't "the gpu is too old". our enumeration policy was too narrow. the fix: bounded dynamic enumeration (up to 4,096 entries), retry when the count changes or the call returns `VK_INCOMPLETE`, and fail explicitly on malformed results. after that, wayland plus vulkan presented.

**an opengl failure we have not solved.** the default opengl path doesn't initialize on that machine: `EGL_BAD_MATCH` / `Unsupported surfacetype/colorspace configuration` at `eglCreateWindowSurface`. a mesa rgb10 override gets further, then fails to render a frame. root cause: not found. fix: none yet. it's on the list.

**files that exist but "don't".** on an arm64 aggregate test run, four probes failed to compile with `file not found` for headers that were very much on disk. nothing was missing. bazel just couldn't *see* them, because the targets didn't declare the dependencies. a few follow-up commits fixed the declarations. this is the kind of bug a hermetic build gives you on purpose: it refuses to let you rely on things you didn't declare.

**text that was readable but not crisp.** at a fractional scale (160/120, so 1.333...) the ui font looked slightly soft. maybe glyph positioning, maybe bilinear atlas filtering, maybe the compositor's own sampling. we don't know yet. there's now an opt-in lcd subpixel mode, but whether it helps on real hardware is still an acceptance gate.

**a timed check is not a pass.** an arm64 `//:checks` run was interrupted at 120.055 seconds with four compile failures. the progress line said `1526/2147`, and that's bazel *actions*, not tests passed. i'm mentioning it because it's very tempting to read that number as "70% green". it isn't.

## how it's actually being built

this part is the least conventional, so i'll just describe it:

- **a small group with different specialities.** security, reverse engineering, infrastructure, physics and assets all live in a handful of heads. i'm leaving the roster out on purpose.
- **a lot of the typing is done by coding agents.** during the busy stretches i sometimes had up to six parallel codex workers going, while i reviewed architecture, build failures and integration. i called the setup a "commit factory" and a "compute incinerator" in chat, and jokingly called myself a "1000x developer". that's a joke. commits are not the same as engineering labour, and i'm not going to compare them to it.
- **terminal-first.** headless neovim with lsp diagnostics, bazel checks, and targeted tests as the way to tell whether something works.
- **the recurring argument.** every time we looked at progress, someone would ask whether the *game client* work counted as *engine* work. my answer became no: runtime, platform backends, resources, rendering and extension parity are the engine, and client scenes are there to serve as integration tests.
- **never trust a percentage.** i kept challenging optimistic completion numbers. the todo file now warns, in so many words, that component counts, cross-compilation and source size are not proof of a production game.
- **status is not acceptance.** the agents regularly announce things like "scene implementation finished" or "transform implementation finished". that's a worker's status report, not an independent integration result.
- **small human moments.** i was doing competitive programming and school stuff in the same stretch of days. and one build failed because two local variables in a container regression probe had the same name. the commit is literally called *"Fix duplicate local name blocking container regression compilation"*.

## numbers

- **commits:** 1,292, from october 9 to october 20. the days with commits: 7, 17, 163, 17, 67, 372 and **649 on october 20 alone**. (a lot of the typing was done by parallel coding agents while i reviewed and argued about architecture. i called it a "commit factory" in a chat and that's about right.)
- **authored code:** about **191,000 lines** of c and c++ (`scc`, excluding `third_party/` and `ext/`; that includes the tests). the whole checkout, vendored libraries included, is 3,867 files and 990,368 lines of code, because freetype, harfbuzz, libwebp, re2 and friends are in there.
- **the fun number:** `scc`'s hypothetical estimator says the whole checkout would cost **$37.8 million**, take 54.67 months and need 61 people. that's a made-up model run over vendored code, not a budget and not a productivity claim. i'm including it as a joke.
- **the checklist:** `TODO.md` has 84 items checked and 170 unchecked. that is *not* a completion percentage. the repo itself says there's no defensible fixed denominator.
- **the engine suite:** the latest commit message says a 108-suite native engine benchmark passed. i'll believe it fully when i've read the raw log, so i'm reporting it as "the commit says so".

## what isn't done

aevum is **not a production game runtime yet.** still open: migrating the shipping game modules, integrated boot, release acceptance, an end-to-end game run, controlled pointer capture and release on wayland, validating vulkan, opengl and direct3d on real devices (windows gpu execution especially), retesting the opengl and xwayland failures, finishing lumen (our planned lighting system, still an incomplete pipeline), and actually retiring strongdot.

cross-compiling for a platform is not the same as the game working on it. the repo's own todo says so, in bold, more than once.

## the latin readme

one more detail. i had the aevum readme translated into latin, mostly to mess with friends who study it. it opens: *"Aevum est ambitus exsecutionis proprius, e Godot derivatus, una cum instrumentis operandi sine interfacie graphica ad aimRPGx destinatis."* i can't vouch for how good the latin is. it lives in my downloads folder, not in the repo.

more when something other than a blue mesh renders.
