---
title: neovim is the goat (a tour of my dots: 70 plugins and one casing script)
date: 2026-10-25
time: 22:00
description: why i live in neovim, shown with receipts from my own config. 17 language servers in 64 lines, competitive programming on two keys, a python script that generates every capitalization of my commands, tetris, and a commit workflow that tells you what song i was listening to.
tags: neovim,vim,lua,tooling,devops
---

# neovim is the goat

the readme of my neovim config says, in full:

> actually high quality neovim dots
>
> built from the ground up by me
> don't expect competence
> installation: something?? i dont remember

and the repo description on github says "i actually worked hard on this". both of those are true at the same time, which is the most neovim thing imaginable.

the repo is [nvim-dots](https://github.com/TogiFerretFerret/nvim-dots). i wrote it by hand, and over the last year ai has helped fix parts of it. here's why i'd pick neovim over anything else, with receipts from my own config.

## 1. the config is code, and it's mine

my config is about **1,500 lines of lua**, spread over 69 small files, managed by `lazy.nvim`, with a `lazy-lock.json` that pins every plugin to an exact commit. everything my editor does is a file i can open and read.

that matters more than it sounds. nothing is hidden in a settings gui. when something is annoying, i can find the line responsible, because i probably wrote it.

it's not tidy. a comment at the top of my keybinds file reads:

```lua
-- TODO: Refactor keybinds to be more organized (date: never [will do never, probably])
```

and my git log has commit messages like `fix`, `some`, `something somewhere once`, `LYRICS`, and `wait i never fixed dat before?`. this is what 80 honest commits look like. (the config is older than the repo, as the readme admits: "i started pushing it to git only recently but its older trust".)

## 2. one editor, seventeen languages, sixty-four lines

my main project is a monorepo with go, c++ and python in it (zig as the toolchain, and rust in my other projects). in most editors that's a plugin and a settings screen per language, and a pile of things that break after an update.

in mine, language servers are one list in one 64-line file:

```lua
local servers = {
  "lua_ls", "jsonls", "html", "cssls", "yamlls", "eslint", "eslint_d",
  "pyright", "rust_analyzer", "ast_grep", "zls", "qmlls",
  "arduino_language_server", "clangd", "gopls", "jdtls", "gdscript",
}

for _, server_name in ipairs(servers) do
  local opts = { autostart = true }
  -- ...a couple of per-server tweaks...
  vim.lsp.config(server_name, opts)
  vim.lsp.enable(server_name)
end
```

17 servers, plus `ts_ls` and `astro` set up separately with a fallback that looks for the typescript library in `frontend/node_modules` when it's not at the root (monorepos!). the important part is `vim.lsp.config` and `vim.lsp.enable`: that's neovim's **built-in** lsp api. no framework in between. clangd for the engine, gopls for the server, `zls` for zig, `rust_analyzer` for the rust things. one setup, every language.

snippets are native too. i use `vim.snippet`, neovim's own snippet engine, with `ctrl-n` and `ctrl-p` to jump between placeholders. (the snippet plugin i used to have, luasnip, got removed in a memory-trimming pass. more on that below.)

## 3. competitive programming on two keys

this is the part i'm proudest of. (i do competitive programming. it's on the front page of this site.)

```lua
vim.keymap.set("n", "<M-p>", function() vim.cmd[[CompetiTest receive problem]] end)
vim.keymap.set({"n","v","i"}, "<M-r>", function() vim.cmd[[CompetiTest run]] end)
```

- **alt+p** waits for a problem from the browser and creates the sample test cases automatically. i click the extension on a codeforces page and the tests show up in my editor.
- **alt+r** compiles with `g++ -std=c++20 -O2 -DLOCAL_JUDGE -lm`, runs every sample test and shows pass or fail in a floating window.

on top of that i have a few local plugins from my cptools folder: `cfsubmit`, a cses submit plugin and `usaco-tools`. the loop of read problem, write code, test it and submit all lives in the editor.

## 4. the python script that generates every capitalization of a command

this one is dumb, and i love it.

vim command abbreviations are case-sensitive. i type fast and my pinky is sometimes late on shift, so `:Crun` or `:cRun` or `:CRUN` gives me "not an editor command". that's annoying when you're trying to run a test case.

so i wrote a script, `rns.py`, that reads a list of command pairs and generates **every possible capitalization** of each one as a vim abbreviation. `pairs.txt` has 16 entries (like `crun` becoming `CompetiTest run`, plus `ct`, `q`, `qa` and `wq`), and the script spits out a file with 108 abbreviation lines:

```vim
ca crun CompetiTest run
ca Crun CompetiTest run
ca cRun CompetiTest run
ca CRun CompetiTest run
ca crUn CompetiTest run
" ...and so on, for every casing
```

so `crun`, `Crun`, `cRuN` and `CRUN` all do the same thing. i have a generator script whose job is forgiving my typing. best use of python all year.

## 5. my editor has games in it

here's the bit that makes people stare. my config includes:

- **tetris** and **minesweeper**, both inside neovim
- a **typing test**
- an **epub reader**
- **synced lyrics in the statusline**: a 160-line lualine plugin of mine that shows the current line of the song from `lrcsnc`, wired in as a statusline component. the commit that added it is literally named `LYRICS`
- **discord rich presence**, using my own plugin, `presencectl.nvim`
- a **pomodoro timer** wired into telescope

i'm not claiming a text editor *should* have tetris. i'm saying that when the whole editor is a pile of lua you can read, adding tetris takes about a minute, and that's a good sign about the architecture.

## 6. my commits tell you what i was listening to

my commit workflow is a fish function. i type `gitsic` and it does three things:

```fish
git add .
git commit -m "(acm) Currently Listening To: $(playerctl metadata title) - $(playerctl metadata artist)"
git push
```

so a lot of my commits in my git history look like this:

```
(acm) Currently Listening To: We are - ONE OK ROCK
(acm) Currently Listening To: Walk This Way! - Kano
```

there's a second function, `gitsick`, for when the song title is in japanese: it pipes the title and artist through `kakasi` to romanize them first, and tags the commit `(acm-kakasi)`. this has nothing to do with neovim. it just lives in the same terminal-shaped corner of my life, and it makes my history a playlist.

## 7. the costs, honestly

it isn't free:

- **70 plugins is a lot.** every plugin is something that can break after an update. the lockfile pins versions, which helps, and i still have a readme that says "installation: something?? i dont remember".
- **memory.** at one point my editor used too much, so i went through trimming: a github copilot agent made a few commits on october 20, 2025 removing neorg and luasnip and turning off the minimap and file tree auto-open. (it's 4 of the 80 commits. every other commit is me, under three different git names. and i won't pretend that's the only help i've had from ai along the way.)
- **there's a learning curve.** modal editing feels wrong at first and then feels like the only way to edit text.
- **you build your own editor.** that's the entire point, and it's also a lot of weekends.

## why i'd still pick it every time

1. **it runs wherever a terminal does.** over ssh, in a tmux session, on a server with no gui. there's even a plugin in my config for mounting a remote filesystem. i've also used it headless with lsp diagnostics as part of checking engine code.
2. **everything is composable.** the editor, the language servers, the test runner, the build tool and git all talk to each other through the terminal.
3. **it's a language, not an app.** i can read the code, fix it, and share it. (the repo is public.)
4. **my hands never leave the keyboard.** that is the whole product.
5. **it's scriptable all the way down.** a casing generator, a lyrics statusline and tetris are all just lua and a bit of python.

neovim isn't popular because it's easy. it's popular because once you've built your own editor, you can't go back to using someone else's.
