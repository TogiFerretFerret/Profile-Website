---
title: cf: laboratory on pluto
date: 2026-10-24
description: minimum perimeter gives a nearly full rectangle. counting its four missing corners turns the geometry into integer partitions.
tags: competitive programming,combinatorics,dp,editorial
---

# laboratory on pluto

building a rectangle is easy. counting all the things that are almost rectangles is where the problem starts being rude.

an optimal lab is connected: otherwise, slide components together until they share a wall and reduce the perimeter. if its bounding rectangle is $h\times w$, each occupied row contributes at least two vertical walls and each column at least two horizontal walls. so

$$p\ge 2(h+w),\qquad hw\ge n.$$

let $s$ be the smallest integer satisfying

$$\left\lfloor\frac{s}{2}\right\rfloor\left\lceil\frac{s}{2}\right\rceil\ge n.$$

the minimum perimeter is $2s$. for construction, take the balanced rectangle with $h+w=s$ and remove $hw-n$ cells from one end of its top row. there are fewer than $h$ missing cells, so this keeps the bounding box and perimeter intact.

## counting the corners

for counting, consider every ordered pair $h+w=s$ with $hw\ge n$. write $D=hw-n$.

minimality of $s$ gives **$D<\min(h,w)$**. otherwise a rectangle with one fewer row or column would still fit $n$ cells, contradicting the choice of $s$.

to achieve perimeter $2(h+w)$, every row and column must contain one contiguous run of blocks. that forces the missing cells into staircase cuts at the four corners. each staircase is an integer partition: its row lengths are nonincreasing.

since $D<\min(h,w)$, the cuts can't overlap or erase an entire row or column. there are no extra size restrictions. so the number of shapes for this rectangle is the number of **four ordered partitions with total size $D$**.

precompute their counts $g_D$ using coin change: for each positive part size, process four copies of an unbounded coin. equivalently,

$$\sum_{D\ge0}g_Dx^D=\prod_{j\ge1}(1-x^j)^{-4}.$$

then the answer is

$$\sum_{\substack{h+w=s\\hw\ge n}}g_{hw-n}\pmod m.$$

ordered dimensions matter. a rotated rectangle is a different layout, unless the resulting cells are actually identical.

there can be $200000$ queries, so precompute all answers up to the largest queried $N$. for each $s$, its range starts just above the maximum area achievable with sum $s-1$. enumerate feasible rectangles and add their contributions across that range. only $O(\sqrt{s})$ widths are feasible, and each contributes to $O(s)$ values of $n$.

$O(N^{5/4})$ preprocessing, $O(N)$ space, $O(1)$ per counting query. construction takes $O(n)$ output. geometry has somehow become coin change. fine.
