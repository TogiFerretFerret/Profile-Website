---
title: aevum — we wrote our own game engine because we're chudalinguses
date: 2026-10-20
description: a godot-derived, headless, bazel-built native runtime for aimrpgx, designed around declared builds and authenticated everything. 1,292 commits in eleven days, a vulkan driver that reported 88 surface formats to a renderer that expected 64, and an honest list of everything that still isn't done.
tags: gamedev,engine,cpp,bazel,writeup
---

# aevum

the aimrpgx codebase runs on strongdot, our godot fork. godot is great. we also decided it wasn't enough, because we're chudalinguses.

so we're writing our own engine. it's called **aevum**, it's a godot-derived native runtime plus a headless toolchain, and as of this post it's eleven days old, has 1,292 commits, renders a blue mesh on an apple m1 over native wayland and vulkan, and is nowhere near finished. all four of those are true and i'm happy about every one of them.

(aimrpg is a game i'm lead dev on, and i'm the one responsible for the engine's architecture and for driving its implementation. the repos are private, so there are no links.)

## why

the honest answer is "we wanted to". the repo's description is *"Aevi memor (aka fuck godot mannn)"*, which is about as close to a design doc as it gets.

what the docs say, which is also true: the readme's stated objective is a purpose-built runtime and toolchain for aimrpgx rather than a complete godot editor, and the build contract wants a declared, reproducible build where every action's inputs are accounted for. not a full editor, not mobile, not xr. a runtime, a command-line toolchain, and a build graph you can read.

so the scope is deliberately small: **the minimum engine needed.**

the git history has a moment that captures this better than any readme. on october 13 a **bulk import of runtime sources** landed. **sixteen minutes later** (16:03, then 16:19 utc), a commit titled *"Remove bulk runtime import and restore Aevum-owned architecture"* took it back out. that's the rule in action: aevum owns its architecture and *selectively* adapts narrow godot algorithms, instead of dragging in a mountain of code and hoping it behaves.

strongdot stays as a submodule until aevum can carry the whole game. removing it is a release gate, not a vibe.

## what it is

a headless native toolchain plus runtime, targeting linux x86-64, linux arm64 and windows x86-64. the source tree is split by subsystem: `core`, `world`, `render`, `platform`, `resources`, `audio`, `text`, `physics`, `lumen`, `runtime`, `input` and `animation`, plus `tests`, `tools` and a pile of `examples`.

what exists, per the readme and a very long todo file: an object, variant and class system with explicit ownership, scenes, nodes and transforms, animation and ui, resource and module loading, collision queries and physics, audio, mesh, texture and text rendering, and networking components. graphical backends exist for wayland and x11 with vulkan and opengl, and for windows with direct3d.

**"exists" is carrying a lot of weight in that paragraph.** components existing is not the same as the game running on them. i'll keep saying that, because it's the most important sentence in this post.

## the foundation

the bottom layer is a native foundation you can depend on directly, `@aevum//core:foundation`, and it's deliberately boring in the good way. lifecycle, atomics and reference counters, scalar math, `Vector2`, `Vector3`, `Quaternion`, `Rect2`, `Transform2D`, `Basis`, `Transform3D`, memory allocation, diagnostics, a unicode `String`, an interned `StringName`, an owning `Vector` and a `HashMap`.

two principles run through all of it:

- **fallible things report failure explicitly.** allocation and mutation return a result you have to look at. the one place that can't (a `String`'s ordinary copy) reports the failure and aborts, and fallible construction and mutation leave an existing string unchanged. no silent half-states.
- **the math is inherited, the infrastructure is ours.** the matrix and atomic algorithms keep their original per-file mit grants. memory, diagnostics, unicode strings and containers are intentional native rewrites with narrower apis, and each one has a provenance document explaining what was reviewed and what was deliberately changed.

there is no extension abi, no dynamic bridge, no runtime that translates between two worlds. game modules compile against native engine classes. that's in the build contract in plain words: *"No GDExtension runtime bridge is planned."*

## the build is the product

aevum is built with **bazel 9.2.0** and a pinned **zig toolchain** (`hermetic_cc_toolchain`), so the compiler, linker, c++ runtime and windows resource tools all come from a version-pinned zig sdk. there was never any scons: bazel showed up in the third commit.

the build contract is five short paragraphs, and every line is a decision:

- **build actions invoke declared executables, never tools found through `PATH` or machine-local caches.** host mingw archives and sdk discovery are prohibited.
- **supported build hosts need a runnable distribution of every execution tool.** "the toolchain *targets* your platform" is explicitly not enough.
- **offline builds after dependency provisioning, and minimal-host execution traces, are acceptance criteria.** they're written down as goals that aren't established yet, not as claims.
- **the old build's workarounds don't get copied.** strongdot's windows c-runtime hacks stay in strongdot. aevum starts by proving native c++ lifecycle and windows resource and linking behaviour in isolation, *then* imports bigger pieces.

headless checks use a static musl toolchain. graphics builds use a pinned **glibc 2.28** target, because a graphical program has to load the system's gpu drivers dynamically. a few lines from `.bazelrc`:

```bazel
build --incompatible_strict_action_env
build --action_env=PATH=
build --host_action_env=PATH=
build:linux_arm --platforms=@zig_sdk//platform:linux_arm64
```

yes, native actions run with an **empty `PATH`**. no, "no host executables whatsoever" is not a claim we can make: bazel's own linux sandbox bootstrap still calls `/bin/true`. so it's "as hermetic as bazel lets us be", and the honest label matters more to me than the impressive one.

the readme is careful to separate two things that are very easy to confuse: running the validation checks on a native host, and merely *cross-compiling* an artifact for another platform.

```sh
bazel build //:checks
bazel build --config=linux_arm_graphics //examples:windowed_scene
bazel build --config=win_x86 //examples:windowed_scene
```

the first one runs checks. the other two produce binaries that may or may not work on a real device. only a device test tells you that.

## how we know anything works

validation is a first-class part of the tree. `tests/` has 307 c++ source files covering everything from animation and audio to bodies, containers, buttons and publishers. the root `//:checks` target aggregates the declared validation probes, including **expected-fatal tests**: a separate checker that confirms certain bad inputs *do* kill the process, because "it crashed" is sometimes the correct behaviour.

one consolidated functional executable reuses the original fourteen probe bodies, plus a separate fatal checker. the stated ci requirement is a checksum-pinned bazel bootstrap and declared dependencies only, with sandbox networking disabled and `/usr` blocked.

the rule i enforce: a probe passing is not a feature shipping. the aggregate is a *component* check. it does not tell you the game runs.

## ideas we talked about

a lot of aevum's shape came out of chat conversations before any of it was code. i want to be careful here: **everything in this section is an idea or a plan, not a shipped feature.** i'll say which ones have actually turned into something.

- **latin names.** i wanted the engine and its parts to have latin-flavoured names. *aevum* (roughly "age" or "eternity") won for the engine, and *lumen* ("light") is the planned lighting system. we talked about other latin names too, but i won't pretend i remember the losers.
- **renderer profile names.** the idea was to rename godot's three renderer tiers to *excelsior* (the big desktop one), *stratosphere* (the mobile-ish one) and *terra* (the compatibility one). those names do show up in a lumen planning doc as profiles that need separate performance and memory measurements. they are **not** products you can select today.
- **"the minimum engine needed."** that was literally the phrase for the scope, and the git history agrees: the bulk import that got removed in sixteen minutes was the opposite of this.
- **godot-flavoured source, no bridge.** we talked about keeping a godot-extension-style api so existing habits carry over, while avoiding generated editor bindings and a json abi with its overhead. what survived into the written contract is narrower and, i think, better: game modules compile against native engine classes, no runtime bridge is planned, and similar source conventions are kept *only where they resolve directly to engine implementations.* the repo also has an api-coverage inventory so we can see exactly how close we are.
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

## from engine to game: the boot problem

an engine that can render a mesh is not a game runtime. the hard integration question is **boot**: how does a real game client start up on aevum, load its content and modules, and connect to a server without trusting anything it hasn't checked?

the design is worth describing because it's where the principles above turn into structure:

- **the shipping client loads a fixed set of native modules and asset packs** through an encrypted, signed download pipeline. aevum's module manager owns initialization order for static descriptors, and a separate native module image format (a restricted c abi, `aevum_native_module_v1`) handles dynamically loaded code. godot's old entry symbols are deliberately *not* that abi.
- **a signature has to bind everything.** the typed verifier consumes metadata that binds the executable bytes to the module's identity, version, abi and architecture. a signature over plaintext alone is explicitly not trusted to cover separately supplied dependency or entrypoint fields.
- **loaders exist for gnu linux and windows x86-64.** static-musl image loading is unsupported, so the headless static checks exercise module *registration*, not dynamic images. the docs say that too.
- **the boot coordinator owns exactly one pending attempt.** it holds the account and session identity, a generation counter, deadlines, a content snapshot and cancellation. a network channel is only committed after a *successful real handshake*, and old work gets cancelled and drained before anything new takes over.

this is the unglamorous part, and it's also the part that decides whether the project becomes a game or stays a very elaborate demo.

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

this is a demo fixture, not the game. it's also our own native vulkan renderer, presenting through native wayland, on an apple silicon laptop running asahi linux, which is a pretty niche driver stack to bring up in eleven days. i'll take it.

## eleven days, day by day

the history is in utc, and it's got a shape.

- **oct 9, 7 commits.** the initial commit. a bazel bootstrap with hermetic windows resource linking. then the first real extraction: native atomic ownership and scalar math pulled out of the godot-derived core.
- **oct 13, 17 commits.** the bulk import, and its sixteen-minute removal.
- **oct 14, 163 commits.** the engine starts looking like an engine. immutable native triangle mesh resources and procedural box geometry. native reflection and guarded object lifetimes. indexed meshes rendered through native linux opengl, with graphics ownership enforced. egl window handles passed using the declared pointer abi. box layouts and character contacts. clipped scrolling. the day ended with a commit recording **104 passing native engine integration suites**.
- **oct 15, 17 commits.** the first client-facing integration: a reusable native client scene driven by authored gameplay and input sources, bounded native json parsing, and aim direction and precision preserved across repeated turns.
- **oct 16, 67 commits.** the grown-up day. a comprehensive completion checklist was written, exact module identity exposed for boot admission, and real ipv4 and ipv6 tls, http and boot acceptance checkpoints recorded.
- **oct 19, 372 commits.** authenticated resource packs, atomic user files and native dns transport. inherited visibility for 3d nodes. mip chains uploaded and sampled in direct3d 11 and 12. one single hour (23:00 utc) saw **141 commits**.
- **oct 20, 649 commits.** the m1 day. bounded vulkan surface format enumeration landed, an explicit rgb and bgr lcd text policy was wired in, wayland pointer capture was made to fail closed after a transport failure, scaled vulkan scenes were rendered into fence-owned targets, and the day finished with a commit recording the 108-suite benchmark.

i don't read that and see a commit count. i see a project that went from "nothing" to "real renderer on real hardware with an honest checklist" in less time than it takes most teams to finish choosing a build system.

## war stories

**the driver that had too many formats.** the first launch on the m1 died with `windowed_scene: vulkan initialization failed (5)`. a gdb trace showed `vkGetPhysicalDeviceSurfaceFormatsKHR` returning **88 surface formats**. our renderer rejected anything over **64**.

so the failure wasn't "the gpu is too old". our enumeration policy was too narrow. the fix: bounded dynamic enumeration (up to 4,096 entries), retry when the count changes or the call returns `VK_INCOMPLETE`, and fail explicitly on malformed results. after that, wayland plus vulkan presented. the boring answer ("our code was too strict") beat the exciting one ("the driver is broken").

**an opengl failure we have not solved.** the default opengl path doesn't initialize on that machine: `EGL_BAD_MATCH` / `Unsupported surfacetype/colorspace configuration` at `eglCreateWindowSurface`. a mesa rgb10 override gets further, then fails to render a frame. root cause: not found. fix: none yet. it's on the list.

**files that exist but "don't".** on an arm64 aggregate test run, four probes failed to compile with `file not found` for headers that were very much on disk. nothing was missing. bazel just couldn't *see* them, because the targets didn't declare the dependencies. a few follow-up commits fixed the declarations. this is the kind of bug a hermetic build gives you on purpose: it refuses to let you rely on things you didn't declare.

**text that was readable but not crisp.** at a fractional scale (160/120, so 1.333...) the ui font looked slightly soft. maybe glyph positioning, maybe bilinear atlas filtering, maybe the compositor's own sampling. we don't know yet. the text path uses freetype and harfbuzz with bounded font memory accounting, and there's now an opt-in lcd subpixel mode, but whether it helps on real hardware is still an acceptance gate.

**a timed check is not a pass.** an arm64 `//:checks` run was interrupted at 120.055 seconds with four compile failures. the progress line said `1526/2147`, and that's bazel *actions*, not tests passed. it's very tempting to read that number as "70% green". it isn't, and i won't let it be quoted that way.

## how it's actually being built

this is the part people ask about, so here it is straight.

**i run aevum like a small engine studio with one very opinionated architect, and the architect is me.** the design, the scope, the module boundaries and the build approach are mine. a lot of the actual typing is done by coding agents (up to six parallel codex workers at the busiest points) while i review, redirect and integrate. that's a tool choice, and it works because the thing being decided is architecture, which doesn't get outsourced.

what that looks like day to day:

- **i set the scope and defend it.** "the minimum engine needed" wasn't a slogan, it was a filter. the bulk import coming out in sixteen minutes is that filter in action.
- **i refuse fake progress.** every time someone, human or otherwise, floated an optimistic completion percentage, i pushed back until the number either had a denominator or went away. the todo file now says out loud that component counts, cross-compilation and source size are not proof of a production game. that sentence exists in part because i kept making people prove it.
- **i drew the line between engine and client.** the recurring argument was whether game client work counts as engine work. my answer: no. runtime, platform backends, resources, rendering and extension parity are the engine, and client scenes are integration tests. that redirected a lot of effort in the right direction.
- **worker status isn't acceptance.** the agents regularly announce "scene implementation finished" or "transform implementation finished". that's a status report. an independent integration result is something else, and i don't confuse the two.
- **terminal-first, no gui in the loop.** headless neovim with lsp diagnostics, bazel checks and targeted tests tell me whether something is real.
- **a small crew with real range.** security, reverse engineering, infrastructure, physics and assets all live in a handful of heads. (i'm leaving the roster out on purpose.)

i jokingly called the setup a "commit factory" and a "compute incinerator", and myself a "1000x developer". the jokes are fun. the honest version is that 1,292 commits in eleven days says the machine is running, and the interesting numbers are the ones below: what's actually verified on real hardware, and what's still gated.

and yes, i was doing competitive programming and school stuff in the same stretch of days. one build even broke because two local variables in a container regression probe shared a name. the commit is literally called *"Fix duplicate local name blocking container regression compilation"*.

## numbers

- **commits:** 1,292, from october 9 to october 20: 7, 17, 163, 17, 67, 372 and **649 on october 20 alone**. the single busiest hour had 141.
- **authored code:** about **191,000 lines** of c and c++ (`scc`, excluding `third_party/` and `ext/`; that includes the tests). the whole checkout, vendored libraries included, is 3,867 files and 990,368 lines of code, because freetype, harfbuzz, libwebp, re2 and friends are in there.
- **tests:** 307 c++ test source files, and the latest commit message reports a 108-suite native engine benchmark passing. i'll quote it as "the commit says so" until i've read the raw log.
- **the fun number:** `scc`'s hypothetical estimator says the whole checkout would cost **$37.8 million**, take 54.67 months and need 61 people. that's a made-up model run over vendored code, not a budget and not a productivity claim. i'm including it as a joke.
- **the checklist:** `TODO.md` has 84 items checked and 170 unchecked. that is *not* a completion percentage. the repo itself says there's no defensible fixed denominator.
- **the m1 build:** 141.128 seconds, 295 actions, 1,034 cache hits.
- **the m1 formats:** 88 reported, 64 assumed, 4,096 allowed now.

## what i'm proud of

not the commit count. these:

- **the docs tell the truth.** this repo says "this is not a production game runtime yet" in the readme, in the todo and in the validation docs. it separates "compiled" from "ran on a device" from "passed". a lot of projects can't do that about themselves.
- **the build is declared, not assumed.** a pinned bazel, a pinned zig toolchain, an empty `PATH`, and a build graph that refuses to let a header "work by accident". that's why the missing-header failure was caught instead of lurking.
- **the m1 bring-up produced a real diagnosis.** a gdb trace, a count of 88 formats against an assumption of 64, and a fix with bounds and retries.
- **the security design has principles, not vibes.** authenticate before you trust, no deterministic nonces, fail closed, bound everything, wipe on failure, and keep the claims smaller than the code.
- **we wrote our own engine.** godot is great. we did it anyway, on purpose, with a plan, in eleven days, and the first thing it did on real hardware was tell us something true about our own assumptions.

## what isn't done

aevum is **not a production game runtime yet.** still open: migrating the shipping game modules, integrated boot, release acceptance, an end-to-end game run, controlled pointer capture and release on wayland, validating vulkan, opengl and direct3d on real devices (windows gpu execution especially), retesting the opengl and xwayland failures, finishing lumen (our planned lighting system, still an incomplete pipeline), and actually retiring strongdot.

cross-compiling for a platform is not the same as the game working on it. the repo's own todo says so, in bold, more than once, and i'd rather ship a project that's honest about that than one that isn't.

## the latin readme

one more detail. i had the aevum readme translated into latin, mostly to mess with friends who study it. it opens: *"Aevum est ambitus exsecutionis proprius, e Godot derivatus, una cum instrumentis operandi sine interfacie graphica ad aimRPGx destinatis."* i can't vouch for how good the latin is. it lives in my downloads folder, not in the repo.

more when something other than a blue mesh renders.
