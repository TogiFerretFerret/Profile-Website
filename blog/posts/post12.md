---
title: Crypto: Needle in a Multivariate
date: 2026-06-29
description: A multivariate-quadratic signature with no norm check. The 200 published signatures leak the hidden basis — BKZ it back, read off the secret p·I/q·I blocks, and forge with four squares.
tags: ctf,crypto,writeup
---

# needle in a multivariate

sekai ctf. hard crypto. we get a multivariate-quadratic signature scheme and a server that hands over the flag if we can sign `STAGE OF SEKAI`. they give us the public key, 200 example signatures, and the source.

the whole thing hinges on one line in the verifier.

## the scheme

a signature is just an integer vector `s`. verification:

```python
def verify(self, message, signature):
    t = int.from_bytes(b"\x01" + sha256(message).digest(), 'big')
    signature = vector(ZZ, signature)
    return signature * self.pk * signature == t
```

`pk` is a $144 \times 144$ symmetric positive-definite integer matrix `Q`. that's it. verify checks $s \cdot Q \cdot s = t$ and **nothing else**. no norm bound, no size check, no distribution check. so we don't need to produce a *legit* signature — we just need any integer vector in $\mathbb{Z}^{144}$ that hits the target quadratic value. the needle.

keygen builds a secret "nice basis" gram matrix with a very specific block structure:

$$
M_{\text{struct}} = \begin{bmatrix} p\,I_8 & 0 & M_1^{\top} \\ 0 & q\,I_8 & M_2^{\top} \\ M_1 & M_2 & M_0 \end{bmatrix}, \qquad n = m + 2k = 128 + 16 = 144
$$

`p` and `q` are two 80-bit primes ($B_1 = 2^{80}$). then it publishes $pk = U^{\top} M_{\text{struct}}\, U$ for a secret unimodular `U`, which scrambles the basis so you can't see the blocks. a real signature is $s = U^{-1} x$ where `x` are "nice" coordinates with small entries ($\sim 2^{89}$), while the published `s` entries are bigger ($\sim 2^{111}$).

in nice coordinates the quadratic form is exactly $x^{\top} M_{\text{struct}}\, x$. if we could *see* that basis, forgery would be trivial. so let's see it.

## the signatures are the leak

here's the thing. they published 200 signatures. every one is $s_i = U^{-1} x_i$ with $x_i$ small. that means there's a unimodular `T` that simultaneously shrinks every published signature back down to nice coordinates. and "find the unimodular transform that makes a bunch of vectors short" is just lattice reduction.

stack the signatures as columns, glue on an identity to track the transform, and reduce:

```python
Aug = block_matrix(ZZ, [[S.transpose(), identity_matrix(ZZ, 144)]])   # 144 x 344
Aug = Aug.LLL()
```

plain LLL got the coordinates down to $\sim 2^{92}$ — close, but a mixed basis, not the clean one. the real nice basis sits right at the gaussian-heuristic bound, so it needs a stronger hammer. progressive BKZ:

```python
for bs in (10, 20, 30):
    Aug = Aug.BKZ(block_size=bs)
# bs=10 done 45s  max coord nbits=92
# bs=20 done 110s max coord nbits=92
# bs=30 done 44s  max coord nbits=89   <- there it is
```

BKZ-30 drops the max coordinate to $2^{89}$, exactly the true nice basis. pull out the transform `T` from the right block ($\det = \pm 1$, unimodular ✓).

## reading off the secret blocks

now compute the gram matrix in the recovered basis, $F = T^{-\top} Q\, T^{-1}$, and look at the diagonal:

```
F diag nbits sorted: [68,69,69,...,70,70,   80,80,80,80,80,80,80,80,  80,80,80,80,80,80,80,80]
repeated diag values: [(80, 8), (80, 8)]
8x-repeated diag values: prime? [True, True]
d1 block == p*I : True
d2 block == q*I : True
d1-d2 block == 0: True
```

there it is, fully unscrambled. 128 diagonal entries around $2^{68}$–$2^{70}$ (that's the `M0` block), and exactly 16 entries that are **two distinct 80-bit primes, each repeated 8 times** — that's $p\,I_8$ and $q\,I_8$, with zero coupling between them. `p` and `q` recovered, both prime.

## forging with four squares

the `p`- and `q`-blocks are clean scaled identities, and the only thing coupling them to the rest is `M1`/`M2`, which touch the `M0` block. so if i zero out the entire `M0` part of `x`, every cross term dies and the 144-variable quadratic collapses to two terms:

$$
x^{\top} F x = p\,|d_1|^2 + q\,|d_2|^2
$$

i just need $pA + qB = t$ with $A, B \ge 0$. solve it modularly, then write `A` and `B` as sums of four squares (lagrange — every non-negative integer is one) and drop the squares into the four `p`-block and four `q`-block slots. map back with $s = T^{-1} x$ and you've got a forged signature.

here's the full solve, from the provided `pk.sobj` + `output.txt` straight to the signature:

```python
#!/usr/bin/env sage
# needle-in-a-multivariate-sekai — pk.sobj + output.txt -> forged signature for "STAGE OF SEKAI"
from sage.all import *
from hashlib import sha256
from collections import Counter
import ast

# --- load public key + the 200 published signatures ---------------------------------
Q = load("pk.sobj")['pk']                        # 144x144 symmetric PD public gram matrix
with open("output.txt") as f:
    sigs = ast.literal_eval(f.read())            # 200 signatures, 144 ints each
S = matrix(ZZ, sigs)                             # 200 x 144

# --- recover the unimodular basis T that shrinks every signature ---------------------
# reduce [ Sᵀ | I ]; the right block tracks T with  x_i = T·s_i  small (~2^89)
Aug = block_matrix(ZZ, [[S.transpose(), identity_matrix(ZZ, 144)]])   # 144 x 344
Aug = Aug.LLL()
for bs in (10, 20, 30):                          # progressive BKZ -> exact nice basis
    Aug = Aug.BKZ(block_size=bs)
T = Aug[:, 200:]
assert abs(T.det()) == 1
Tinv = T.inverse()

# --- expose the secret block structure  F = T^{-T} Q T^{-1} --------------------------
F = Tinv.transpose() * Q * Tinv
diag = [ZZ(F[i, i]) for i in range(144)]
reps = sorted([v for v, c in Counter(diag).items() if c == 8], reverse=True)
p, q = ZZ(reps[0]), ZZ(reps[1])                  # the two 80-bit prime diagonal blocks
assert p.is_prime() and q.is_prime()
p_idx = [i for i in range(144) if diag[i] == p]
q_idx = [i for i in range(144) if diag[i] == q]

# --- forge: solve p*A + q*B = t, four-squares into the p/q blocks --------------------
t = ZZ(int.from_bytes(b"\x01" + sha256(b"STAGE OF SEKAI").digest(), 'big'))
A = (t * inverse_mod(p, q)) % q
B = (t - p * A) // q
assert p * A + q * B == t and A >= 0 and B >= 0

def four_sq(N):                                  # N = a^2 + b^2 + c^2 + d^2
    N = ZZ(N)
    if N == 0:
        return [0, 0, 0, 0]
    while True:
        a = randint(0, isqrt(N))
        b = randint(0, isqrt(N - a * a))
        r = N - a * a - b * b
        if r == 0:
            return [a, b, 0, 0]
        if r % 4 == 1 and r.is_pseudoprime():
            c, d = two_squares(r)
            return [a, b, c, d]

x = vector(ZZ, [0] * 144)                        # zero M0-block kills all cross terms
for j, v in enumerate(four_sq(A)):
    x[p_idx[j]] = v
for j, v in enumerate(four_sq(B)):
    x[q_idx[j]] = v
assert x * F * x == t

s = Tinv * x                                      # forged signature in public coords
assert s * Q * s == t
print(" ".join(str(int(z)) for z in s))          # pipe into the server
```

```bash
$ sage solve.sage > forged_sig.txt
$ ( cat forged_sig.txt; echo ) | nc needle-in-a-multivariate-sekai.chals.sekai.team 1337
Signature: SEKAI{...}
```

the server reads the line, runs `verify(b"STAGE OF SEKAI", s)`, sees $s \cdot Q \cdot s = t$, and coughs up the flag.

## why it falls over

three things stack up:

- **no size check in verify.** a real signing run produces a small, carefully-distributed vector. the verifier never enforces that, so a junk integer vector with the right quadratic value is just as valid.
- **the signatures are the leak.** publishing 200 signatures $s_i = U^{-1} x_i$ with small $x_i$ is enough to reconstruct the hidden basis by reduction. the secret unimodular `U` gives you nothing once you can BKZ.
- **the block structure trivializes the forge.** clean $p\,I_8$/$q\,I_8$ blocks with no cross-coupling collapse the 144-var quadratic to $pA + qB = t$, which is inverse-mod plus four squares.

## flag

```
SEKAI{y0U_f0uND_th3_n33dL3!!!_https://youtu.be/Sloi-L5FHBY}
```
