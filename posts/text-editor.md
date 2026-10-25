---
title: cf: text editor
date: 2026-10-24
description: preserve one matching block, delete from the right, then use home to handle the prefix. counting cursor moves gives a quadratic solution with linear memory.
tags: competitive programming,strings,dp,editorial
---

# text editor

the editor has five buttons and somehow none of them insert text. so first check that $t$ is a subsequence of $s$. if it isn't, print `-1` and spare the cursor the trouble.

every successful plan deletes exactly $n-m$ characters. the actual optimization is how much walking the cursor does between those deletions.

an optimal plan can be arranged as a sweep from the right, optionally followed by `home` and a sweep from the left. handle the right side before jumping home; returning there with `end` just revisits work that could already be done. repeated home jumps similarly don't help the left sweep.

between the two sweeps, leave a contiguous matching block untouched. i like this part. the cheapest cursor movement is the movement i don't do.

use zero-based indices. suppose the left sweep turns $s[0:L)$ into $t[0:p)$, and the untouched block has length

$$c=\operatorname{lcp}(s[L:],t[p:]).$$

the right sweep processes the $n-L-c$ characters after that block. each takes one move: backspace if deleted, left if kept.

then press `home`. processing the first $L$ characters takes $L$ right presses and $L-p$ backspaces. total:

$$n-L-c+1+L+(L-p)=n+1+L-p-c.$$

## which splits work

greedily precompute `pref[p]`, the earliest position after matching the first $p$ target characters, and `suff[p]`, the latest position where a subsequence matching $t[p:]$ can start. use `pref[0] = 0` and `suff[m] = n`.

the split is feasible exactly when

$$\operatorname{pref}[p]\le L\le\operatorname{suff}[p].$$

the left inequality lets the prefix fit before the block; the right lets the suffix fit after the split. taking their common prefix immediately is safe, since greedy earliest matches never hurt subsequence matching.

try every feasible $(L,p)$ and minimize the cost above. also consider using no home press at all: leave the common prefix of $s$ and $t$ untouched, and sweep everything else from the right. that costs

$$n-\operatorname{lcp}(s,t).$$

compute the lcp values with

$$\operatorname{lcp}(L,p)=
\begin{cases}
1+\operatorname{lcp}(L+1,p+1),&s_L=t_p,\\
0,&\text{otherwise}.
\end{cases}$$

process $L$ backwards and keep one row. update $p$ forwards so the old value at $p+1$ survives until it's needed.

$O(nm)$ time, $O(n+m)$ space. all that machinery to avoid pressing left a few times. competitive programming remains an excellent use of an evening.
