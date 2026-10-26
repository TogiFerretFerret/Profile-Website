---
title: a tour of all my dots (the wacky parts)
date: 2026-10-25
time: 23:00
description: hyprland on asahi in lua, a quickshell ui with 5,700 lines of qml, a cielab k-means color pipeline, a custom sddm login screen with a perspective-matched clock on an airship display, lyrics piped from my forks of lazyspotify and lrcsnc, and a fork of tauon. a long walk through ~/.config.
tags: dotfiles,linux,hyprland,quickshell,rice
---

# a tour of all my dots (the wacky parts)

i already wrote about [my neovim config](nvim-is-the-goat.html). that's one folder. `~/.config` on my laptop has well over two hundred, most of them kde and gtk leftovers i'm afraid to touch, and a smaller pile that i actually care about. this is the tour of that pile.

the machine: an apple silicon laptop running **asahi linux**, with **hyprland** on top. a lot of existing configs assume an x86 box with a normal gpu, so a fair amount of what's below exists because i had to build it myself.

the theme running through everything is neon genesis evangelion. the hyprland repo is literally called "EVA-00 // ASAHI". that's also why the login screen is the way it is, which i'll get to, because it's the part i'm proudest of.

## 1. hyprland, but in lua

the compositor config is not the usual `hyprland.conf`. it's **lua**: one `hyprland.lua` entry point and a folder of small modules.

```
hyprland.lua
modules/
  hardware.lua    monitors
  envvars.lua     wayland / xdg environment
  autostart.lua   things that launch on login
  graphics.lua    animations, blur, glow, borders, rounding
  colors.lua      accent colors, overwritten by the wallpaper scripts
  plugins.lua     hyprpm
  binds.lua       every keybinding
  rules.lua       window rules
```

about 400 lines total. the nice thing about lua is that i can share variables between modules and write actual logic instead of copy-pasting. the borders are a gradient (`rgba(5093e3ee)` to `rgba(f1afffee)` at 45 degrees), blue into lavender, which is the unit-00 palette i keep stealing from.

the readme for it says i made it because i was "frustrated with how most setups are just a mix of other people's configs glued together", which is a very serious sentence to put on a repo about a pretty desktop.

## 2. the color pipeline (k-means in a color space that makes sense)

this is the thing under the whole desktop. i change the wallpaper and **every color on the machine changes**: window borders, the glow around windows, the bar, popups, the notification center, rofi, discord, the terminal, even fastfetch.

most people use pywal for this. pywal works, but extracts colors naively and sometimes gives you muddy, low-contrast palettes. mine is a python script, `colorgen.py`, that:

1. loads the wallpaper
2. runs **k-means clustering in CIELAB**, a color space where distance roughly matches how different two colors *look* (rgb distance is a bad proxy for that)
3. builds a full dark-theme palette with contrast checks
4. caches the result by the md5 of the image, so a wallpaper you've used before is instant
5. writes `~/.cache/wal/colors.json`, in a shape compatible with pywal and with quickshell

then a small daemon watches `swww` (the wallpaper daemon) for changes, pushes the new colors to hyprland with `hyprctl keyword`, and tells everything else to reload. i also run **matugen** (material you colors) for the apps that want a material palette: it fills a template for discord's css and for rofi.

the pipeline fans out into: hyprland borders, quickshell, `swaync-colors.sh` for the notification center stylesheet, `fastfetch-colors.sh` for my terminal flex screen, and the discord theme. one wallpaper, a dozen apps, no manual steps.

a funny one: the daemon that watches for wallpaper changes isn't clever. it polls `swww query` **every two seconds** in a `while true` loop. it works and i'm not touching it.

## 3. quickshell: 5,700 lines of qml

my bar, popups, dashboard, notification center, power menu, wallpaper picker and lock-adjacent things are all **quickshell**: a toolkit for building shells in qml. the config is about **5,750 lines of qml**, and the readme for it opens with, in full:

> epic quickshell config
> trust guys

it goes on to say "i really do not like glsl", which is funny, because the folder is full of glsl.

some of what's in it:

- **a bar made of pills.** each little widget (battery, wifi, bluetooth, vpn, brightness, calendar) is a `Pill` with its own popup.
- **a dashboard** with a weather shader behind it.
- **a wallpaper picker** that's the front end of the color pipeline above.
- **an oscilloscope.** a python script reads the audio, a unix socket feeds the numbers to qml, and a fragment shader draws a scope, big or small, in time with the music.
- **a stats bridge.** a tiny python daemon multiplexes system metrics over a unix socket so many widgets can read the same numbers without each one polling.
- **a notification center and toasts**, backed by swaync's styling, recolored by the pipeline.
- **clipboard history**, an mpris media popup, and a power menu.

the shaders (`.frag` files compiled to `.qsb`) are a whole thing: a karaoke background, an album-art background, a glow behind the lyrics, a glow behind the media popup, a visualizer. it is, by my own readme, "a crazy over the top dashboard with unnecessary shaders", and there's a `quickshell.bak3` folder next to it with the old, less laggy version, in case i ever come to my senses.

## 4. the lyrics chain (four forks deep)

this is the part where it gets silly. i want synced lyrics everywhere: in my editor, on my desktop, in my media popup. none of the tools i wanted did it the way i wanted, so i forked them.

- **lazyspotify** is a terminal spotify client. i forked it and added **synced lyrics support**. the daemon exposes the current line over a **unix socket** (`/tmp/lazyspotify-lyrics.sock`) as json: whether it's playing, and the previous, current and next lines.
- **lrcsnc** is a tool that shows synced lyrics from `.lrc` files. my fork lives at `TogiFerretFerret/csync`, wired to the same idea.
- **quickshell** has a `LyricsProvider` service that does `socat` against the lazyspotify socket and exposes `prev2`, `prev`, `current`, `next`, `next2` as plain properties. any widget can bind to those. the media popup shows three lines of lyrics, and there's a full **karaoke overlay** with shaders behind it.
- **neovim** has the lualine plugin i mentioned in the nvim post, reading from `lrcsnc`, so the current lyric line sits in my statusline while i code.

one song, four places, all in sync. i do not have a good reason for this.

i also run a **fork of tauon**, a music player, with changes like hiding the client-side window buttons, extending transparency to every panel background, and live theme reload (via inotify, plus a `SIGUSR1` handler) so it picks up the wallpaper colors when they change. it has the whole upstream history, over five thousand commits, with mine on top.

## 5. the login screen, and the clock on the airship

the part i promised. my sddm (the login manager) theme is called **nerv**, and it's a still image from evangelion: the airship scene, with the display on the blimp.

i wanted the **time to appear on that display**, as if it's part of the picture. a flat text label pasted on top of an image looks fake. the blimp's screen is seen at an angle, so the text has to be skewed to match.

so the clock is **perspective-matched**. i found the four corners of the screen in the image, as fractions of the screen size:

```
// BLIMP CLOCK: perspective-matched overlay on the airship display
// Quad corners (calibrated):
//   TL(0.570, 0.320)  TR(0.655, 0.319)
//   BL(0.575, 0.385)  BR(0.6566, 0.3867)
```

the corners aren't a rectangle, which is the whole point. the clock element is positioned at the center of that quad (`x = width * 0.6153`, `y = height * 0.3526`), sized to fit it (8% of the width by 9% of the height), and then rotated in 3d:

```qml
transform: Rotation {
    axis { x: 0.04; y: 0.2; z: 0.0 }
    angle: 15
}
```

and the text itself is intentionally low-fi. it's an 18 pixel font with **antialiasing and smoothing turned off**, then scaled up by 2.5, so it comes out chunky and blocky like an old display:

```qml
Text {
    text: Qt.formatTime(new Date(), "hh:mm")
    font.pixelSize: 18
    smooth: false
    antialiasing: false
    transform: Scale { xScale: pixelScale(2.5); yScale: pixelScale(2.5) }
}
```

the result is a clock that sits on the blimp's screen at the correct angle, in pixels that match the artwork, and ticks over every minute. every time i log in, the airship tells me the time.

the rest of the theme is a dark panel in the jetbrains mono nerd font. the background image is baked into the theme folder (there's a `bg-original.png` next to the edited `bg.png`, because i edit things and then regret it).

there's a matching lock screen too. it lives in my hypr folder as a qml theme, shimmed in so the lock screen and the login screen look related.

## 6. the terminal side

- **ghostty** is my terminal, with 75% background opacity and 20 blur, and a **custom glsl cursor shader** that draws a hexagonal trail behind the cursor, built from signed distance fields for smooth edges. the shader is named `kitty.glsl` because i started from a kitty shader and rewrote it, and never renamed the file.
- **fish** with the tide prompt. the repo is `TogiFerretFerret/fish-config`, 67 functions in `functions/`, and universal variables (where fish keeps anything set with `set -Ux`) are gitignored on purpose. the git ignore file has a comment about it. i have a few small helpers i use constantly:
  - `gitsic`: `git add .`, commit with "Currently Listening To: (song) - (artist)" from `playerctl`, push. (the nvim post has the story.)
  - `gitsick`: the same, but romanizes japanese titles through `kakasi` first.
  - `listening`: same idea for posting what i'm playing to discord.
  - `fpush`: opens a **zenity dialog box** to type the commit message, so i can commit from a keybind without a terminal.
  - `update_website`: `git add .`, commit "Site Update", push, then count ten dots on screen while cloudflare catches up. (this site now uses a [makefile](website-is-a-makefile.html) instead, but the function remains for sentimental reasons.)
- **fastfetch** gets a lot of attention. it has 374 files: a pile of numbered "segment" configs, python scripts for the layout, a script that prints what's playing, and the color script that recolors it from the wallpaper. the screenshot in the repo is a wide fastfetch with the palette synced to the background.
- **yazi** is my file manager. i keep a `GUIDE.md` in the config as a cheat sheet "for nautilus switchers", with navigation keys, a fuzzy `z`, a frecent `Z` with zoxide, and `g` shortcuts like `gc` for `~/.config`.

## 7. mpv, and everything else

**mpv** has a lot: `modernx` for a modern on-screen controller, `thumbfast` for seek thumbnails, `sponsorblock`, `autoloop`, an `autolyrics` script that fetches lyrics for whatever is playing, and about a dozen more small scripts. the base config is [zydezu's mpvconfig](https://github.com/zydezu/mpvconfig), which i started from and then kept pushing on. nearly all of the 10,000 lines in that folder are other people's scripts. i'm just the curator.

and then, in no order:

- **rofi** for launcher, clipboard picker and wallpaper picker, colors from matugen
- **swaync** for notifications (7,000 lines, mostly css and icons)
- **waybar** and **wlogout** from before quickshell took over, kept around
- **fcitx5 + mozc** for typing japanese
- **cava** for the audio visualizer, and a `cava-scope.conf` that feeds the oscilloscope
- **nushell**, which i have and don't use
- **btop, lazygit, gh-dash, zathura, ncmpcpp, spotify-player, sptlrx**, i have too many music tools, you can tell
- backup folders for hypr, waybar and swaync dated `20260406`, because i back up before big rewrites and never delete the backups

## 8. installing it (if you hate yourself)

the dots have an installer: `curl -s dots.riverxia.sh | bash`. it shallow-clones each component repo and **symlinks it into `~/.config`**. anything already at the target is moved, never deleted, into a timestamped backup folder, and it doesn't use sudo or install packages. `--list` shows components, `--dry-run` changes nothing, `--only nvim,ghostty` picks a few.

(read the script before you pipe anything to bash. including mine.)

## what i actually like about all this

1. **the color pipeline is the glue.** one change (the wallpaper) propagates to everything. that's what makes it feel like one system instead of fifty configs.
2. **forks beat feature requests.** lazyspotify, lrcsnc and tauon each got a small patch for the exact thing i wanted. my desktop is full of small patches on other people's projects.
3. **small details are the whole point.** an airship clock at the right angle is not useful. it's the reason i like logging in.
4. **it's mine, and it's a mess.** there are backup folders, a shader named after the wrong terminal and a poll loop running every two seconds. the readme says "trust guys". do not trust guys.
