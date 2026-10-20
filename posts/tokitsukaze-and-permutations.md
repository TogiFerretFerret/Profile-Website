---
title: cf: tokitsukaze and permutations
date: 2026-10-20
description: counting backwards through bubble sort with inversion sequences, where the whole answer collapses into a single product. suspiciously easy for something that took this long to see.
tags: competitive programming,combinatorics,editorial
---

# tokitsukaze and permutations

bubble sort, except we're counting backwards. okay. i'd like to formally apologize to every bubble sort i've ever mocked in a class where i was supposed to be learning something.

for each **value** $x$, let $c_x$ be the number of larger elements to its left. one pass decreases every positive $c_x$ by exactly one. after $k$ passes:

$$c'_x=\max(c_x-k,0).$$

these counts uniquely describe a permutation, and each original $c_x$ can independently be anything from $0$ to $n-x$.

after $k$ passes, the largest $k$ values are sitting in their sorted positions at the end. any known positive $v_i$ there makes the answer zero.

let $N=n-k$. for a fixed resulting permutation of the first $N$ values:

- if an element has a positive inversion count, its original count was exactly $k$ larger. **one choice**.
- if its inversion count is zero, its original count could have been $0,\ldots,k$. **$k+1$ choices**.

the largest $k$ values contribute another $k!$ choices altogether.

now the nice part: positional inversion sequences are also independent, with $v_i\in[0,i-1]$. so initialize the answer to $k!$, then for each $i\le N$:

- known positive: multiply by $1$.
- known zero: multiply by $k+1$.
- unknown: there are $i-1$ positive choices and one zero choice, so multiply by $(i-1)+(k+1)=i+k$.

everything is modulo $998244353$. the entire solution is just that product.

$O(n)$ time, $O(1)$ extra space. that's right: after all that bubble sort backwards nonsense, the answer is a for loop with a multiplication in it. this is, i'm told, what usaco platinum looks like.
