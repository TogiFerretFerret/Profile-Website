---
title: cf: sanae and giant robot
date: 2026-10-20
description: copying intervals sounds annoying. prefix sums turn it into propagating zeros with a queue and a set, which is a fancy way of saying bfs where the graph is also a set.
tags: competitive programming,prefix sums,editorial
---

# sanae and giant robot

copying intervals sounds annoying. prefix sums make it considerably less annoying. (this is the entire reason prefix sums exist, and the entire reason i occasionally get to call myself a competitive programmer.)

define the **current** difference prefix sums:

$$s_i=\sum_{j=1}^{i}(a_j-b_j),\qquad s_0=0.$$

an operation on $[l,r]$ is legal exactly when $s_{l-1}=s_r$. after copying, all differences inside the interval become zero, so every prefix sum from $l$ through $r$ becomes $s_{l-1}$.

i want every prefix sum to become zero. here's the useful observation: **an operation can only create new zero prefix sums when both endpoints are already zero.** equal nonzero endpoints just produce more nonzero entries, which is the problem equivalent of rearranging deck chairs.

so start with all initially zero positions in a queue. each given interval watches its two endpoints, $l-1$ and $r$. once both have become zero, activate it and mark everything between them zero too.

keep the remaining nonzero positions in a `set`. when an interval activates, use `lower_bound` and erase the positions it covers, pushing each into the queue. each position gets erased once; each interval activates at most once. that's the whole reason this isn't quadratic, and it's the kind of detail that is obvious in hindsight and invisible beforehand.

why can i ignore operations with nonzero endpoints? they never create a zero. any position that eventually becomes zero must get it from an operation whose endpoints are already zero, which is exactly what the queue processes.

if the set ends up empty, print `YES`.

$O((n+m)\log n)$ time, $O(n+m)$ space. use `long long` for the prefix sums, unless you want to find out what overflow feels like on a platinum-adjacent problem.

so: a queue, a set, and the realization that "copy" really means "spread zeros". i would like to formally thank prefix sums for carrying a division's worth of my career.
