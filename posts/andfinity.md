---
title: cf: ANDfinity
date: 2026-10-24
description: fix the zeros, try one change, and let the largest lowbit handle everything else. bitwise connectivity with a surprisingly small answer.
tags: competitive programming,bitmasks,dsu,editorial
---

# ANDfinity

the graph can have millions of edges. fortunately, i don't actually need to build any of them. (a recurring theme in problems where building the graph looks miserable.)

every zero is isolated, so increment all zeros to one first. these operations are mandatory. call their number $z$.

to check connectivity, use a dsu over the **bits**. for each number, unite all its set bits. the graph is connected exactly when every number is positive and all used bits belong to one component.

now try the obvious things: check the current array, then try incrementing or decrementing each element once. if anything works, the answer is $z$ or $z+1$.

and if none of that works? **two more operations are always enough.**

let $L$ be the largest lowbit in the array, where `lowbit(x) = x & -x`. pick a number $x$ with lowbit $L$. decrementing it sets every bit below $L$ to one, so $x-1$ connects to every number with a smaller lowbit.

if $x$ were the only number with lowbit $L$, that would already solve it. we tried that and it failed, so there must be another such number $y$.

decrement $x$ and increment $y$. since the graph was disconnected, $L>1$. so $y+1$ keeps bit $L$ and gains bit zero:

- every number with lowbit $L$ connects to $y+1$.
- every number with a smaller lowbit connects to $x-1$.
- $x-1$ and $y+1$ share bit zero.

connected. that's the entire construction.

it's also minimal: with only $z$ operations, every original zero must become one. with $z+1$, there's only one extra increment or decrement to try, including turning an original zero from one into two. we've exhausted both possibilities.

$O(n^2)$ time for fixed 31-bit integers, $O(n)$ space. the answer is always between $z$ and $z+2$, which is very considerate of a problem with a four-second time limit.
