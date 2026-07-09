---
title: Crypto: Baby ZKP
date: 2026-07-05
description: A Schnorr proof whose response is reduced mod the wrong prime. Two stages, two RNGs — a truncated LCG cracked with a lattice, and MT19937 rebuilt from GF(2) relations on the leaked responses.
tags: ctf,crypto,writeup
---

# baby zkp

no hack no ctf. we get a schnorr-style proof-of-knowledge over a netcat service. two stages, a different RNG each, and one bug that ties them together. beat both stages and it prints the flag.

## the setup

each stage picks a secret witness `w` and runs a schnorr identification loop. `G = 2`.

```python
w = rng.next()
y = pow(G, w, p)                 # never printed
while oracle_count < ORACLE_LIMIT:
    r = rng.next()
    a = pow(G, r, p)
    print(f"{a=}")               # commitment
    e = int(input("e="))         # OUR challenge
    if e.bit_length() < 1023 or e > q - 1 or e < 0:
        exit()
    z = (r + e * w) % pp          # <-- the bug
    print(f"{z=}")
    status = input("verifier accept? (Y/N)")
    if status == "Y":
        break

inp_w = int(input("w="))
if inp_w != w:                   # we must hand back the secret
    exit()
```

in a real schnorr the response is `z = r + e·w mod q`, where `q` is the group order. here it's reduced mod `pp = getPrime(1024)` — a **fresh random prime with nothing to do with the group**. and we choose `e` (with `bit_length ≥ 1023`). the only leaks per round are `a = 2^r mod p` and `z`. to clear a stage we have to *recover* `w` and type it back.

so this is an extraction problem. and the mod-`pp` slip is what makes it possible.

## stage 1: the truncated LCG

stage 1's rng is a truncated LCG with the multiplier, increment and modulus **printed for us**:

```python
class TLCG:
    MASK = (1 << 512) - 1
    def next(self):
        self.x = (self.A * self.x + self.C) % self.p     # A, C, p known
        return self.x & self.MASK                        # low 512 bits of a 1024-bit state
```

so `w` and every `r_i` are the low 512 bits of a known LCG. they're **small** (512 bits) relative to `pp` (1024 bits). that's the crack.

send the *same* `e` every round. then `z_i = (r_i + e·w) mod pp`, and since `e·w mod pp` is one fixed constant `s0` and `r_i < 2^512 ≪ pp`, the addition never wraps:

$$z_i = s_0 + r_i \quad\Rightarrow\quad z_i - z_1 = r_i - r_1 \ \text{(exact)}$$

no `pp` needed. we now know every truncated output up to one shared offset. write each full state as `x_{i+1} = 2^512·h_i + r_i` with `h_i` the unknown high half, plug into the recurrence `x_{i+2} = A·x_{i+1} + C mod p`, and every unknown (`h_i`, and the base `r_1`) is bounded by `2^512` while the modulus is `2^1024`. classic small-solutions-to-modular-relations → LLL:

```python
# c[i] = z[i]-z[0] (exact r_i - r_1); recover h_i and r_1 with a Kannan embedding
for i in range(T - 1):
    b_i = (c[i+1] - A*c[i] - C) % p            # constant term
    # 2^512·h_{i+1} - A·2^512·h_i + (1-A)·r_1 + b_i ≡ 0 (mod p)
```

the lattice hands back the seed, step the LCG back one call (`x_1 = A^{-1}(x_2 - C) mod p`), and `w = x_1 & MASK`. the printed `a_i = 2^{r_i}` are a free oracle to confirm the recovered `r_i`. six rounds is plenty; solves in under a second.

## stage 2: mersenne twister

stage 2 swaps the rng for `getrandbits(1024)` — plain MT19937. now `w` and `r_i` are **full** 1024-bit outputs. no smallness, so the stage-1 trick is dead, and `pp` is genuinely unrecoverable (it only ever shows up as `2^{pp} mod p`, a discrete log). so we can't touch `pp` or peel `r_i` out of `z_i` arithmetically.

but MT19937 is a linear map over GF(2). if we can pin enough **output bits**, we solve for the 19937-bit state and roll it back to output 0 = `w`. so where do clean output bits come from?

**step 1 — recover the wrap count.** with fixed `e`, `z_i = (r_i + s0) mod pp` wraps `κ_i ∈ {0,1,2}` times. compute

$$u_i = 2^{z_i}\cdot a_i^{-1} \bmod p = 2^{s_0}\cdot(2^{pp})^{-\kappa_i}$$

and it collapses to just 2–3 distinct values. same value ⇒ same `κ_i`. so we can label every round by its wrap count for free.

**step 2 — clean GF(2) relations.** two facts, both borrow-free:

- **bit 0**, every round: `bit0(r_i) = bit0(z_i) ^ (κ_i & 1) ^ bit0(s0)` — one unknown global bit.
- **same-`κ` close pairs**: if `z_i ≡ z_j (mod 2^k)` then `r_i ≡ r_j (mod 2^k)`, so their low `k` bits agree. `pp` and `s0` cancel. birthday over ~3300 rounds gives thousands of these.

that's it — everything else drowns in carries, but these are exactly linear. feed them into [`gf2bv`](https://github.com/maple3142/gf2bv) (fast MT recovery via GF(2) over m4ri):

```python
lin = LinearSystem([32]*624); rng = MT19937(lin.gens())
_w  = rng.getrandbits(1024)                       # output 0 = w, unconstrained
sy  = [rng.getrandbits(1024) for _ in range(N)]   # r_1 .. r_N
zeros = []
for i in range(N):                                # bit0 (try both global B)
    zeros.append((sy[i] & 1) ^ (z0[i] ^ (kap[i] & 1) ^ B))
for idxs in buckets.values():                     # same-κ, z≡ (mod 2^k)
    for j in idxs[1:]:
        for t in range(1, k):
            zeros.append(((sy[idxs[0]] >> t) & 1) ^ ((sy[j] >> t) & 1))
sol = lin.solve_one(zeros)                         # -> 624-word MT state
```

rebuild a `random.Random` from the recovered state, and the very first `getrandbits(1024)` **is** `w`. verify against the `a_i` and type it back.

one wrinkle for the remote: it's ~3300 rounds and the box has real latency (~0.4 s/round), so the connection sits open ~20 minutes. it survives. the solve itself is ~35 s.

## why it falls over

- **wrong modulus.** reducing the response mod a random `pp` instead of the group order turns `z` into a leak. stage 1 it's a straight hidden-number / truncated-LCG lattice; stage 2 it's an MT bit-oracle.
- **choosing `e` + fixed `e`** freezes `e·w mod pp` into a single constant, which is what makes the no-wrap (stage 1) and the `κ` clustering (stage 2) work.
- **MT19937 is just linear algebra.** you never need `pp` or a discrete log — a few thousand borrow-free bit relations rebuild the whole state.

## flag

```
NHNC{wow_i_am_wondering_about_if_there_are_any_in_the_wild_exploitable_zkp_like_this_:D}
```
