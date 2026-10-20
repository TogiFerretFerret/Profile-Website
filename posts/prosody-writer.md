---
title: prosody writer — a poetry editor that scans your verse as you type
date: 2026-10-07
description: a realtime poetry editor that shows stress, meter, rhyme, sound devices and form while you write. the parser is an incremental dynamic program that picks the best scansion without ever enumerating the exponential pile of pronunciations. i wrote it by hand because i ran out of codex usage.
tags: python,nlp,poetry,algorithms,writeup
---

# prosody writer

this started because of [versepad](https://versepad.com).

versepad is a text editor for poets with automatic syllable counts, meter detection and rhyme scheme, made by one person, and it's genuinely good at what it does. i used it, i liked it, and then i did the thing i always do, which is look at something that works and think "i bet i could build that, but with a *real prosody library* behind it, and way more complicated than anyone asked for."

the creator is pretty open about the limits, which is what pointed me at the gap. in a hacker news thread they called the meter detector "by far the most complex piece of this code", said it "tends to behave poorly when there's a word it doesn't recognize", said rhyme scheme "currently only considers words at the end of each line", and said multi-stanza forms like villanelles need more thought. that's a fair and honest list. it's also, more or less, the spec for what i wanted to build:

- a **real, maintained prosody library** doing the pronunciations and the metrical parsing,
- a **fallback for words it's never seen**, so invented words still scan,
- rhyme computed from the actual **sounds** (the last stressed vowel onward), with near-rhymes, plus alliteration and assonance per line,
- and **multi-stanza forms** like villanelles and terza rima.

to be clear about the scale of what i'm comparing: **versepad's meter detector next to full prosodic is like four lines of javascript next to the v8 source.** that's a joke about *size*, not a review. versepad is one person's project, its creator calls the meter detector the most complex part of it, and it works. prosodic is just a different kind of animal: a big library with its own stanford project page and a whole constraint system behind it, and i wanted to see what happens when you put *that* behind a live editor.

(none of this is a dig at versepad. i'm a chronic overbuilder, and this was an excuse to build an algorithm.)

i was going to have codex build it. then i hit my usage limit. so i wrote it myself, by hand, which turned out to be the better outcome, because the interesting part is an algorithm and i wanted to get it right.

the repo is [prosody-writer](https://github.com/TogiFerretFerret/prosody-writer). it's three commits, october 7 to 8, and a bit under 850 lines of python in the package, plus 357 lines of tests.

(yes, the last commit has a `Co-Authored-By: Claude` tag on it. i was running out the door and had claude push it for me. it didn't write any of the code, it just pressed the button.)

## what it does

type a poem into the editor and, a fraction of a second after you stop, every line gets annotated:

- **syllables and stress.** weak and strong positions, and which constraints each syllable violates.
- **meter.** the scansion gets named: iambic, trochaic, anapestic or dactylic, with a foot count (`iambic pentameter`). variations are reported instead of counted against you: a feminine ending, a catalectic last foot, substituted feet (`foot 1: trochee`).
- **rhyme.** each line gets a rhyme letter computed from the last stressed vowel onward, rhyming syllables are underlined, and near-rhymes get a tilde (`B~`).
- **sound devices.** alliteration and assonance, per line.
- **form.** the scheme and syllable counts are matched against haiku, tanka, limerick, shakespearean and petrarchan sonnets, villanelle, terza rima, couplets and quatrains. a blank line starts a new stanza.
- **echoes.** repeated content words across the poem.

it saves your draft in the browser's local storage, and the server never stores your poem.

## the hard part: scansion is exponential

the pronunciations and the metrical parsing come from [prosodic](https://github.com/quadrismegistus/prosodic) 3.10.0, a python library. i use the full library, including its eSpeak fallback for words that aren't in the dictionary, so an invented word still gets scanned.

prosodic scans a line by trying readings against a handful of constraints and keeping the best one. that's great for a batch job and terrible for an editor, for two reasons:

1. **words have several pronunciations.** `temperate`, `heaven` and `every` can each be one syllable or two, depending on who's reading. a line with n such words has 2^n pronunciation combinations.
2. **each combination has many possible scansions.**

enumerate everything and typing slows to a crawl on any line that isn't trivial. i wanted *realtime*, so i replaced the enumeration with a dynamic program.

## the dynamic program

`dp.py` walks the line one syllable at a time. each partial parse is a **state** that remembers only what matters for the future:

- the last three metrical values (strong or weak),
- how big the currently open position is,
- a pending weak position before an open strong one,
- a bitset of which foot shapes have closed,
- two counters for how regular the pattern is (period-2 and period-3 matches),
- the syllable count, and whether the last word was a function word.

every state carries a **score** (how many constraint violations so far), a strong-resolution count, some tie-break bits, the pronunciation choices made, and a backpointer to rebuild the winning path at the end.

every pronunciation alternative of a word is consumed *as its own branch*, then branches that land in the same state **merge**, keeping the better one. the cartesian product of pronunciations is **never constructed**.

the scoring matches prosodic's six default constraints with unit weights (`w_peak`, `w_stress`, `s_unstress`, `unres_within`, `unres_across` and a foot-size constraint), with strong and weak positions capped at two syllables.

### why pruning is safe

this is the part i'm proudest of. every constraint weight is strictly positive, so a path that is already worse than another path in an *equivalent* state, on score and strong-resolution count, can never recover when more syllables are appended. so after each word i throw away everything that can't win. the tie-breakers still get honored, because states only merge when their remaining ranking information is equivalent. the point is that the answer matches prosodic's own tie-breaking exactly, not an approximation of it.

the result: the state space is polynomial for this fixed grammar. it's not constant time (the frontier can grow, changed suffixes get recomputed, and rebuilding the displayed scan is linear), but nothing exponential is left in the editor's path.

### incremental, too

after each word the DP stores its whole frontier as a **checkpoint**. when you type:

- **append a word:** resume from the last checkpoint.
- **edit mid-line:** roll back to the checkpoint just before the first changed word and recompute from there.
- **insert or delete a line:** other lines keep their frontiers. results are cached per line.

on top of that the engine caches pronunciation blocks per token, so changing the last word only re-pronounces the last word.

## how i know it's right

"it's faster" means nothing if the answer is wrong, so the tests compare against the real thing. they check best scansions, scores, violation counts and chosen pronunciations against full prosodic, including:

- 150 seeded synthetic pronunciation lattices,
- append and rollback behaviour, checkpoint identity, and line movement,
- an invented word that needs eSpeak,
- and **32 independent binary pronunciations**, which is 2^32 combinations, scanned without enumerating a single path.

i re-ran all of it for this post on my asahi machine (fedora asahi remix 43, aarch64, python 3.12, on 2026-10-20). the readme says "execution on Asahi hardware has not been tested here", so that's now tested: **60 tests passed in 5.89 seconds.**

## the benchmark

the repo has a benchmark script that types `To be or not to be` after a first line and compares an incremental update with a full-document prosodic parse (median of 5):

| appended text | incremental | full parse | dp transitions |
|---|---|---|---|
| `To be or` | 1.65 ms | 5.03 ms | 12 |
| `To be or not` | 3.08 ms | 5.31 ms | 24 |
| `To be or not to` | 3.22 ms | 5.34 ms | 36 |
| `To be or not to be` | 3.23 ms | 5.70 ms | 48 |

i'll be honest about this table. on ordinary lines the win is modest: the full parser is already about 5 ms, and the incremental update is 3 to 5 ms. nothing exponential is going on in a line this short.

the interesting number is the last row of the benchmark. take a line of 64 words, `be be be be ...`, where every word is an ambiguous monosyllable. that's **2^64 = 18,446,744,073,709,551,616 pronunciation combinations.** appending the 64th word took **8.04 ms**, with 1,444 dp transitions, 488 peak states, and **zero materialized paths**. there's no full-parser time to compare against, because the full parser can't do it. the repo's comparison against full prosodic is limited to 18 syllables and 4,096 combinations for exactly that reason. past that, the tests check the dp's own invariants instead.

so the honest summary: it matches prosodic where prosodic can finish, and it keeps going where prosodic can't.

## the analysis layer

`analysis.py` is the second half of the project and the part that actually feels like a writing tool. it's pure functions over the pronunciation the scanner *already chose*, so it adds no second parse and gets cached per line like everything else. (the dp now returns the chosen pronunciation, so word boundaries and rhyme tails are exact.)

the rhyme assignment runs in **two passes** so a weak echo never steals a line from its perfect rhyme. pass one lays down the perfect and identical rhymes, pass two attaches leftover lines to the nearest near-rhyme (a shared vowel or a shared closing sound) and tags them with a tilde. a line with no echo at all is greyed out. form detection then looks at the rhyme scheme, the syllable counts, the meters and the stanza sizes together.

these parts are **heuristics over the dictionary pronunciation**, and the readme says so. if the dictionary stresses a word differently from how a poet would read it (`temperate` as a rhyme for `date`), the tool can only catch it as a near rhyme.

## the editor itself

the front end is vanilla javascript, about 180 lines:

- it scans **180 ms after you stop typing**,
- keeps **at most one request in flight**,
- numbers every request with a **revision** and throws away any response for an older revision,
- and the server refuses to queue work: if the scanner is busy it answers `429` and the client retries the latest revision.

the limits are explicit: 128 syllables across every pronunciation, 300 characters per line, and 200 lines or 12,000 characters per request. an over-budget line shows a limit message instead of silently approximating. sessions are bounded (16 per server) and caches are bounded per session, so no poetry outlives a session.

## what it isn't

- it's a prototype. there's no authentication and no production deployment, so run it on a machine you trust.
- it does **not** claim compatibility with fitted zone weights, zero or negative weights, phrasal stress or arbitrary extra constraints. the proof above only covers the fixed default grammar.
- optional syntax models, configurable grammars and enumeration of every unbounded alternative are not implemented.
- the whole thing assumes prosodic's default english grammar, and the rhyme and meter naming is heuristic.

the small `graph.py` is still in the repo as a slow reference enumerator, used only by the tests to check the dp.

## try it

on fedora asahi (or any linux with python 3.12 and `espeak-ng`):

```sh
sudo dnf install python3.12 espeak-ng
git clone https://github.com/TogiFerretFerret/prosody-writer.git
cd prosody-writer
PYTHON_BIN=python3.12 bash scripts/setup.sh
.venv/bin/python -m uvicorn prosody_writer.app:app --port 8000
```

then open `localhost:8000` and write something. there's also a codespaces setup if you'd rather not install anything.

it started because i looked at a working poetry tool and thought "i could make this 2^64 times more complicated", and it ended up as the most fun algorithm i've written this month.
