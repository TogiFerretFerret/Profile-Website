---
title: bazel vs buck2 vs scons vs cmake vs meson vs make (a tour of my regrets)
date: 2026-10-25
description: i've bounced between every build system i could find, and i ended up with two that speak the same language. bazel for my go and c++ monorepo, buck2 for the rust things, make for glue, and an honest look at starlark, the weirdly great language they share.
tags: buildsystems,bazel,buck2,starlark,devops
---

# bazel vs buck2 vs scons vs cmake vs meson vs make (a tour of my regrets)

i have switched build systems an embarrassing number of times.

i've used make, scons, cmake, meson, bazel and buck2, and for the last stretch i've been happy with two of them: **bazel** for the big go and c++ project, and **buck2** for anything with rust in it. and the funny part is they speak the same language, which i'll get to, because it's the best part.

this is not a neutral review. it's a list of opinions with receipts. (the receipts are my git log, which is a very unflattering document.)

## the cast, in one line each

- **make:** you write recipes, it compares timestamps and runs shell commands. it's from 1976 and it's still the right answer for a lot of things.
- **scons:** like make, but the build file is python and it decides what to rebuild by content, not timestamps. godot uses it.
- **cmake:** doesn't build anything itself. it *generates* the real build files (make, ninja, visual studio). it's the lingua franca of c++ libraries.
- **meson:** a nicer, more declarative take on the cmake idea, with ninja underneath. very pleasant for plain c and c++.
- **bazel:** google's build system (internally called blaze). hermetic, cached, and built around the idea that every input and output is declared.
- **buck2:** meta's build system, written in rust, same family and same configuration language as bazel.

## my project: go, c++, and a godot fork

here's what my project actually is, since it decides everything: a go server, a c++ client built from a godot fork (which we call strongdot), and a growing pile of tools around them. one repo, several languages, and it has to cross-compile.

and here's the funny part: **the godot fork still builds with scons.** godot's whole build is scons, and ripping that out to port to something else would be insane. so the bazel build contains a small python script whose entire job is "build one strongdot target through scons from a bazel workspace". bazel is the boss, scons is the employee who knows where the bodies are buried.

the numbers today: **365 `BUILD.bazel` files**, using `rules_go`, `gazelle`, `rules_cc` and `rules_python`, plus a zig toolchain for cross-compiling.

## the day i switched, in commit messages

the git history knows exactly when i committed to bazel: **september 15, 2026**. these four commits landed within a seven-minute window, and they read like a three-act play:

```
update gitignore so bazel doesn't murder me
Switch to bazel for the build system
bazel has the worst toolchain setup i have ever seen ...
we cool like bazel
```

(the third one trails off into a plea i'll leave out.) the first three are all stamped 18:07. the last one, "we cool like bazel", is 18:14. that's anxiety, despair and acceptance in seven minutes. the phrase "switch to bazel" shows up again on september 24, which is the most honest summary of how any migration actually goes: you switch, and then you switch again.

## the windows saga

the best story from the whole migration is cross-compiling for windows, on a laptop that isn't even x86. (my main machine is an apple silicon mac running asahi linux.)

the compiler and linker for windows are **zig**. zig bundles clang and a pile of cross-compilation support, and you can use `zig cc` as a drop-in cross compiler. it is one of the most underrated tools of the decade.

but a windows build isn't only a compiler. you also need packaging tools like `ar`, `ranlib` and `windres`, and zig doesn't provide those. the usual answer is "install the mingw binutils from your distro", except there is no such package for my machine.

so on **september 28** i vendored **gnu binutils 2.47, the whole source tree**, right into the repo, so the windows build doesn't depend on a distro package that might not exist. i even had to prune it: `gas`, `ld`, `gprof` and friends were over 75% of the tree and i don't use them, so it went from **392 MB down to 138 MB**. one commit of it contains a changelog file with 351,000 lines. it's a very normal thing to put in a git repo.

on **september 29** i added a thin wrapper that points the windows toolchain commands at zig for the godot fork, and then the next three days were commits like:

- link `libmingwex.a` for a couple of math functions
- pass `libmsvcrt.a` as a direct archive path, not `-lmsvcrt`
- check `libmincore.a` directly across distro lib layouts
- make the zig fallback search not depend on `$HOME`, because a hermetic toolchain that reads your home directory isn't hermetic

moral: a hermetic toolchain is a *lot* of work to build, and a very small amount of work to live with afterwards.

## what each one is actually good at

### make

i'll start with the one i *still* use daily. this website is built by a makefile: [it's the whole deploy system](website-is-a-makefile.html). make is perfect for gluing commands together and tracking "did this file change". it falls over when you need correct incremental builds across a huge dependency graph, because it only knows timestamps and whatever you wrote down by hand.

### scons

python as a build language is both its best and worst feature. you can do anything, including things you shouldn't. it's content-signature based, which is good, and it has a reputation for being slow on very large trees. i'm using it because i have to, and it works.

### cmake

if you're writing a c++ library other people will consume, cmake is just the thing everyone already has. its generator model is great for ide support. its scripting language is... a scripting language. dependency management and cross-compiling depend heavily on the toolchain files and package managers you bolt on.

### meson

genuinely nice. a clean declarative language, fast builds through ninja, good defaults, and `wrap` for pulling in subprojects. for a pure c or c++ project where you control the dependencies, i'd happily use it. where it gets thin is polyglot repos and strict hermeticity.

### bazel

the cost of bazel is up front, and it's real: toolchain setup (see: my commit message), strict dependency declarations everywhere, and a mental model that's nothing like make. the payoff is that **every action declares its inputs, its tool and its outputs**, builds run in sandboxes, and results are cached by content. nothing "works by accident". that last part is exactly why it was the right pick for a monorepo that mixes go, c++, python and a scons-built godot fork, and has to cross-compile to windows and arm.

### buck2

same family as bazel, with a few things i like: it's written in rust, it's fast, it supports remote execution, and its rules (including the whole standard set, the "prelude") are written in starlark instead of being baked into the tool's internals. rust support is first-class. for projects where the code is rust, it's a natural fit, so that's where it lives for me. the tradeoff is the same one you'd expect from a younger tool: a smaller community and fewer worked examples when you get stuck.

## starlark is the real star

here's the thing i find genuinely cool. **bazel and buck2 both use starlark.**

starlark is a python dialect designed specifically for build configuration. it looks like python, but it's deliberately limited:

- it's **deterministic**: the same input always evaluates the same way
- it's **hermetic**: a build file can't read the filesystem, the clock or the network as it loads
- values get **frozen** after a file is loaded, so there's no spooky action at a distance between files
- in bazel's flavor there are no `while` loops or recursion, so evaluating a build file always finishes

those constraints are the whole point. build files can be evaluated in parallel, cached, and trusted, because they can't do anything surprising. it's python with the dangerous parts removed.

and because both tools use it, the *shape* of a build file transfers. `cc_library` and `rust_library` look the same. learning one means you can already read the other.

### real starlark from my repo

here's a rule from my project. it's a rule that makes a test pass **only if a program crashes**. (we have tests that confirm certain bad inputs kill the process on purpose.)

```python
def _expected_failure_impl(ctx):
    stamp = ctx.actions.declare_file(ctx.label.name + ".stamp")
    ctx.actions.run(
        executable = ctx.executable._runner,
        arguments = [ctx.executable.child.path, stamp.path],
        tools = [ctx.attr.child[DefaultInfo].files_to_run],
        outputs = [stamp],
        mnemonic = "ExpectedNativeFailure",
        progress_message = "Checking expected fatal outcome for %{label}",
    )
    return [DefaultInfo(files = depset([stamp]))]

expected_failure = rule(
    implementation = _expected_failure_impl,
    attrs = {
        "child": attr.label(mandatory = True, executable = True, cfg = "exec"),
        "_runner": attr.label(
            default = Label("//tools/check:expected_failure_runner"),
            executable = True,
            cfg = "exec",
        ),
    },
)
```

about twenty lines, and now "this binary must fail" is a first-class thing the build understands, cached like everything else. try doing that in a makefile without crying.

another one from the same repo is a **configuration transition**, which is one of bazel's superpowers. my go server needs to be built for linux/amd64 no matter what machine you're on, so there's a rule that tells bazel "build this dependency under a different platform than the rest of the build":

```python
def _go_linux_amd64_transition_impl(settings, attr):
    return {
        "linux_amd64": {"//command_line_option:platforms": "@rules_go//go/toolchain:linux_amd64"}
    }

go_linux_amd64_transition = transition(
    implementation = _go_linux_amd64_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)
```

that's one build graph that builds some things for your laptop and some things for a server, correctly, with caching. i'd have written a shell script for this in any other system, and it would have been wrong.

### where bazel and buck2 differ in starlark

the *language* is the same. the *rule api* is different, and that's where you'll trip:

- bazel reads rule attributes with `ctx.attr.x`; buck2 uses `ctx.attrs.x` (one letter, many typos)
- they name and wire up providers and actions differently, and buck2 wants a `category` on actions
- bazel build files are `BUILD.bazel` and buck2's are `BUCK`
- buck2's starlark supports type annotations, which is a nice touch if you like your build code checked

so knowing starlark gets you reading both. writing rules still means reading each tool's docs.

## so which one should you use?

here's my honest cheat sheet, based entirely on my own opinions:

| situation | what i'd pick |
|---|---|
| glue, scripts, a small site, anything "run these commands in order" | **make** |
| a pure c or c++ project, you control the dependencies | **meson** (or cmake if it needs to be universally consumable) |
| you're stuck with godot or scons already | keep scons, wrap it if you need to |
| a polyglot monorepo, cross-compiling, caring about correct caches | **bazel** |
| a project that's mostly rust | **buck2** |

and the thing i'd tell my past self is: **switching costs are real, so only switch when the shape of the project demands it.** every migration costs you days, and you don't get them back.

## what i learned

1. **pick the tool for the shape of your project, not the trend.** polyglot and cross-compiling points at bazel. one language points at that language's tool.
2. **hermetic toolchains are an investment.** it hurts for a week and pays off for years.
3. **wrap, don't rewrite.** my scons-built godot fork lives happily inside a bazel build.
4. **starlark is a surprisingly good idea.** a configuration language that can't surprise you is what a build system should have been all along.
5. **read your own commit messages.** mine are a better record of how that migration felt than anything i could write now.
