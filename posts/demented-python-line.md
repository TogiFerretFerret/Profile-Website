---
title: the most demented python line i have ever written (probably)
date: 2026-01-13
id: 3
description: lambdas lambda'ing all over control codes. don't you love it?
tags: lambda functions, python, school, code golf
---

# the most demented python line i have ever written

well, first of all, to kick us off, here it is.

```python
(lambda: (lambda p: [print("\033c", end=""), [None, lambda: (lambda nums: print("Numbers:", nums) or print((acc := 1, [acc := acc * x for x in nums], acc)[-1]))([int(i) for i in input("Enter integers separated by a space: ").split()]), lambda: (lambda nums: print("Numbers:", nums) or print([v for v in nums if v != int(input("What should be removed: "))]))([int(i) for i in input("Enter integers separated by a space: ").split()]), lambda: (lambda s: print("New list:", s.replace(input("Enter a value to remove: "), "")))(input("Enter a string: ")), lambda: (lambda s: print("Is", s, "a palindrome?", s == s[::-1]))(input("Enter a string: ")), lambda: print("Number of words:", len(input("Enter a sentence: ").split())), lambda: (lambda n: print("Factors of", str(n) + ":", sorted({f for i in range(1, int(n**0.5) + 1) if n % i == 0 for f in (i, n // i)})))(int(input("Enter a number: "))), lambda: (lambda nums: print("Numbers:", nums) or (lambda s: s.remove(max(s)) or print("Second largest:", max(s)))(set(nums)))([int(i) for i in input("Enter integers separated by a space: ").split()])][p]()])(int((ask := lambda: p if (p := input("Enter 1, 2, 3, 4, 5, 6, or 7: ")) in [str(i) for i in range(1, 8)] else (print("\033cThat's not a valid input!") or ask()))
```

is that too hard to read? okay, we can break it down (or more accurately, first let it wrap lines):

<pre class="wrap"><code>(lambda: (lambda p: [print("\033c", end=""), [None, lambda: (lambda nums: print("Numbers:", nums) or print((acc := 1, [acc := acc * x for x in nums], acc)[-1]))([int(i) for i in input("Enter integers separated by a space: ").split()]), lambda: (lambda nums: print("Numbers:", nums) or print([v for v in nums if v != int(input("What should be removed: "))]))([int(i) for i in input("Enter integers separated by a space: ").split()]), lambda: (lambda s: print("New list:", s.replace(input("Enter a value to remove: "), "")))(input("Enter a string: ")), lambda: (lambda s: print("Is", s, "a palindrome?", s == s[::-1]))(input("Enter a string: ")), lambda: print("Number of words:", len(input("Enter a sentence: ").split())), lambda: (lambda n: print("Factors of", str(n) + ":", sorted({f for i in range(1, int(n**0.5) + 1) if n % i == 0 for f in (i, n // i)})))(int(input("Enter a number: "))), lambda: (lambda nums: print("Numbers:", nums) or (lambda s: s.remove(max(s)) or print("Second largest:", max(s)))(set(nums)))([int(i) for i in input("Enter integers separated by a space: ").split()])][p]()])(int((ask := lambda: p if (p := input("Enter 1, 2, 3, 4, 5, 6, or 7: ")) in [str(i) for i in range(1, 8)] else (print("\033cThat's not a valid input!") or ask()))</code></pre>

that should help you see its complete and utter demonic beauty. if you're wondering what it does: it's part of a class i have to take at school where we learn basic python.

if you've actually... read my site, you know i'm *somewhat* overqualified for it. so to challenge me, the intern, a senior who is **also USACO gold**, dared me to code golf it (kind of). could i take the whole assignment, which is meant to be split across files and written with overcomplicated syntax like `os.system("clear")` and lots of if statements, and do it in:

1. 1 line of code
1. 0 import statements
1. 0 semicolons
1. 100% of the greatest/worst python you may have ever seen?

the answer is yes. of course yes.

here's the autopsy of how i killed readability.

## crime #1: the infinite recursion loop

normal people use `while True` to make a menu loop, but as we've established by now, i'm not normal. also, `while` is a statement, not an expression, and lambdas can only contain **expressions**.

so i made a **self-defining recursive lambda** (hereon an SDRL) inside an assignment expression:

```python
(ask := lambda: p if (p := input("Enter 1-7: ")) in valid_list
      else (print("Invalid!") or ask()))
```

- **the walrus (`:=`):** i define `ask` inside the line that calls it.
- **the `or` hack:** `print()` returns `None`, which is falsy. so `print(...) or ask()` prints the error and then forces python to evaluate the right side, calling the function again. infinite loop achieved.

pretty neat, huh?

## crime #2: the dispatch table

`if` and `else` statements are also forbidden inside lambdas. go figure. so how do we switch between the 7 tasks? (7? look, i wrote this code weeks ago and didn't get around to writing this post until now, cut me some slack.)

we use a list as a lookup table (instead of a dictionary, python's actual lookup datatype):

```python
[None, task1, task2, ...][p]()
```

if the user types `1`, i index the list at 1, grab the lambda stored there, and immediately call it with `()`. it's essentially a jump table, but uglier.

## not-quite-crime #3: the "0 imports" screen clear

the assignment **required** clearing the terminal. (the teacher implemented it, but i was re-implementing everything anyway.)

usually you'd do `import os; os.system('clear')`. but imports are statements, so they're banned.

so i just printed the raw ansi escape code for "reset terminal":

```python
print("\033c", end="")
```

it's faster, cleaner, and strictly follows the "no imports" rule while being arguably more confusing to read.

i'm calling this a *not*-quite-crime because it's actually better practice: it's terminal-dependent instead of system-dependent, and it doesn't call a shell command. and trust me, as a CTF player i have absolutely path-injected `clear` before. say this was meant to be a "safe" program that ran with the setuid bit? good thing i made it not call a shell command :-)

## crime #4/3: the side-effect accumulator

is it three? does not-quite-crime #3 count? whatever, i'll say this is 4 anyways.

task #1 was to calculate the product of a list of numbers. usually you'd loop. i did this:

```python
(acc := 1, [acc := acc * x for x in nums], acc)[-1]
```

this is a tuple containing three things:

1. initialize `acc` to 1.
1. run a list comprehension that updates `acc` for every number (ignoring the resulting list).
1. return `acc`.

then i grab the last item `[-1]` to get the result. it turns an imperative loop into a single expression.

by the way, since i **finally added markdown support** to the blog, here's the math syntax for that:

$$ \prod_{x \in \text{nums}} x $$

look at that rendering. crisp. now, back to the carnage.

## crime #5: the optimization disguised as garbage

task #6 was to find the factors of a number. a naive programmer loops from $1$ to $n$. a decent programmer loops to $\frac{n}{2}$.

i, however, decided to actually write an efficient $O(\sqrt{n})$ algorithm, and then hid it inside a set comprehension so it looks like keyboard mash. (sorry, competitive programmer brain couldn't help it!!! it's not my fault!!)

```python
{f for i in range(1, int(n**0.5) + 1) if n % i == 0 for f in (i, n // i)}
```

here's the logic:

1. loop `i` from $1$ to $\sqrt{n}$.
1. if `i` divides `n`, we add **two** numbers to the set: `i` and its pair `n//i`.
1. why a set and not a list? because if $n$ is a perfect square (like 36), this logic adds $6$ twice. the set swallows the duplicate automatically (minimalist), even if it's slightly slower (at least it would be in c++; python arrays are notoriously slow anyway, so i'd guess sets are about the same speed here).

it's arguably the only "good" code in this entire script, and i ruined it by removing all the whitespace.

## crime #6: the destructive lambda

task #7 asked for the **second largest number** in a list, a task that has never ever been asked of competitive programmers before. (slightly different problem, but you get the point... i didn't look that hard. any problem like this would normally be some sort of set problem [update/query] or maybe HLD? idk, it's **SUCH** a simple concept there aren't really any problems about it.) ([codeforces 1491A](https://codeforces.com/problemset/problem/1491/A))

the normal way: sort the list, take the second to last index.

the code golf way: delete the biggest, find the biggest again.

```python
(lambda s: s.remove(max(s)) or print("Second largest:", max(s)))(set(nums))
```

1. `set(nums)`: first i cast to a set to remove duplicates (because if the input is `[5, 5, 4]`, the second largest is 4, not 5).
1. `s.remove(max(s))`: i literally delete the maximum value from the data structure.
1. `or`: again, `remove` returns `None`, so the `or` lets us chain execution into the print statement.
1. `max(s)`: since the old max is gone, the new max is the second largest.

is it efficient? no. does it destroy the data you passed into it? yes. does it work? also yes.

## conclusion

this code handles errors, clears the screen (safely!), and performs 7 different operations. it also violates every single principle of the **zen of python**.

- **beautiful is better than ugly:** failed. ugly is king.
- **simple is better than complex:** failed. i don't think a single thing here is simpler rather than complex.
- **readability counts:** i think i killed tim peters with this.

but hey, it runs. and i didn't use a single semicolon.
