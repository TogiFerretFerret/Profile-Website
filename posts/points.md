---
title: cf: points
date: 2026-10-24
description: count triples by their leftmost point, then maintain the resulting binomial coefficients with a lazy segment tree.
tags: competitive programming,segment tree,combinatorics,editorial
---

# points

count each beautiful triple by its **leftmost** point. that gives it exactly one owner, which is always a good start.

for an active point $x$, let $c_x$ be the number of active points in $(x,x+d]$. any two of those form a beautiful triple with $x$, so the answer is

$$\sum_{x\text{ active}}\binom{c_x}{2}.$$

inserting a point $y$ increases $c_x$ by one for every active $x\in[y-d,y-1]$. deleting it decreases those counts by one. so now the problem wants a range addition and a sum of quadratic expressions. hello, lazy segment tree.

each node stores, over its active points:

- $C$: how many points are active.
- $S$: the sum of their $c_x$ values.
- $P$: the sum of $\binom{c_x}{2}$.

adding $\delta$ to all those counts gives

$$P\gets P+\delta S+C\frac{\delta(\delta-1)}2,$$

$$S\gets S+C\delta.$$

use the **old** $S$ in the first formula. updating it first is a very small way to ruin the entire solution.

for insertion, query how many active points lie in $(y,y+d]$ to get the new point's own $c_y$. apply $+1$ to $[y-d,y-1]$, then activate its leaf with that value.

for deletion, deactivate the leaf and apply $-1$ to the same range. the root's $P$ is the answer after every query.

inactive positions contribute nothing, even if lazy updates pass through them. when activating a leaf, overwrite its count with the freshly queried value; whatever lazy history it accumulated while absent isn't useful.

$O(q\log A)$ time, $O(A)$ space, where $A=200000$. answers need `long long`: there can be more than a quadrillion triples, which is slightly more than an `int` is interested in holding.
