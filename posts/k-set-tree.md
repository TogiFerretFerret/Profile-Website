---
title: cf: k-set tree
date: 2026-10-24
description: start by counting the whole tree, then subtract the component excluded by each possible root and lca. one dfs and some binomial coefficients.
tags: competitive programming,trees,combinatorics,editorial
---

# k-set tree

the definition of subtree is doing a lot of work here. it includes **all descendants**, so for a fixed root $r$, the answer for a set $S$ is the size of the subtree rooted at $\operatorname{lca}(S)$.

i could reroot a dp. i could also count everything first and subtract what shouldn't be there, which feels more manageable.

pretend every pair $(r,S)$ contributes all $n$ vertices. that's

$$n^2\binom nk.$$

now fix a vertex $u$. removing it splits the tree into components of sizes $x_1,\ldots,x_d$. define

$$B_u=\sum_i\binom{x_i}{k}.$$

suppose the root lies in component $i$, whose size is $s=x_i$, and the lca of $S$ is $u$. the rooted subtree at $u$ contains exactly the other $n-s$ vertices, so our initial count overcounted by $s$.

which sets have lca $u$? all their vertices must lie outside component $i$, but they can't all lie inside any one of the other components. therefore there are

$$W_{u,i}=\binom{n-s}{k}-B_u+\binom{s}{k}$$

such sets. containing $u$ is fine; spreading across multiple other branches is also fine. being entirely inside one other branch is what the subtraction removes.

there are $s$ choices of root in component $i$, and each overcounts $s$ vertices. subtract

$$s^2W_{u,i}.$$

do this for every vertex and every adjacent component. when $r=u$, the lca's subtree really is the whole tree, so there's nothing to subtract.

one dfs gives every component size: across an edge it's either the child's subtree size or its complement. precompute factorials and inverse factorials for the binomial coefficients, treating $\binom{x}{k}$ as zero when $x<k$.

$O(n)$ time and space, modulo $10^9+7$. and use an iterative traversal. the tree is allowed to be a chain, because apparently recursion deserves enemies.
