---
title: Fixing a (albeit relatively minor) rendering bug in Zen Browser
date: 2026-01-27
description: Wow! I patched a minor bug in a major browser! Cool!
tags: browsers,open source,zen,css
---
So I just squashed a (minor) bug in Zen Browser!

Which is great because it's my daily driver... basically it boiled down to window sync doing weird scaling stuff when swapping when zoomed. 

Basically, in short, the image it captured was correct but the image was scaled incorrectly, so it took three lines of CSS to get the image to scale correctly and we were done, everything was fixed. 

But it still made me so happy!
