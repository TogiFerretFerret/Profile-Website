---
title: cf: boboniu and jianghu
date: 2026-10-20
time: 18:44
description: a tree dp problem about tourists and mountains that makes me wonder how i got usaco platinum. direct the roads uphill, pair incoming and outgoing edges, then run the dp on the equal-height choices.
tags: competitive programming,trees,dp,editorial
---

# boboniu and jianghu

this is a codeforces problem about tourists, mountains and a tree, and it's the kind of problem that makes me wonder how i got usaco platinum. 

the answer is a tree dp. i'll explain it slowly, mostly for my own benefit.

direct every road uphill. equal-height roads can go either way, which is where the actual problem lives.

suppose a mountain has $I$ incoming roads and $O$ outgoing roads. i can pair an incoming road with an outgoing road to continue one challenge through it. each pair saves one occurrence of that mountain.

pair as many as possible, and its contribution becomes

$$t_v\bigl(I+O-\min(I,O)\bigr)=t_v\max(I,O).$$

because the graph is a tree, these local pairings can't form cycles. they give valid uphill paths. so the whole job is choosing directions for the equal-height edges to minimize

$$\sum_v t_v\max(I_v,O_v).$$

tree dp time. (the four most dreaded words in my vocabulary.)

root the tree and let `dp[v][0]` mean the minimum subtree cost when the parent edge points **out of** $v$, and `dp[v][1]` when it points **into** $v$.

different-height child edges have forced directions, which is the nice part. for equal-height children, initially point every edge from $v$ to the child. child $u$ then contributes `dp[u][1]`. reversing that edge changes its contribution by

$$\Delta_u=\operatorname{dp}[u][0]-\operatorname{dp}[u][1].$$

sort these differences. if i reverse exactly $j$ equal-height edges, the cheapest choice is the first $j$ differences. which children get chosen doesn't otherwise matter: the cost at $v$ only depends on how many roads enter and leave. (this is the observation that makes the whole thing work. it's embarrassingly simple in hindsight, and it took me embarrassingly long to see, which is how i know it's the real answer.)

try every $j$, add the corresponding child costs and $t_v\max(I_v,O_v)$, and minimize separately for the two parent directions. at the root, leave out the parent edge.

$O(n\log n)$ time, $O(n)$ space. use an iterative traversal so a chain of $200000$ mountains doesn't murder the stack. (recursion depth 200,000 is a very efficient way to find out how much you trust your language runtime.)

so that's it. a sort, a loop, and some casing on parent directions. 
