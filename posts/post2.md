---
title: why c++ will never die (and why it shouldn't!)
date: 2026-01-06
description: it's not because it's such a perfect language...
tags: cpp,rant,competitive programming,lambda functions
---

# why c++ will never die

okay so i get that not everyone likes c++. it's a difficult language to learn and use, and it has MANY quirks that just... piss you off.

like seriously, it's a strictly typed language that oh-so-also happens to have the `auto` type.

but i'm a firm believer that c++ is still good and relevant (not that i'm sure anyone was arguing otherwise). i just wanted to talk about **MY** gripes with c++, and also what i love about it.

## lambda functions and auto

you may be awfully confused why i'd put these two seemingly unrelated things in one category, but trust me, they're pretty similar.

in c++ there are lambda functions. here's how most (competitive programmers) write them:

```cpp
// some stuff here
auto lambdafunction = [&] (int a, string b) {
    return something;
};
```

or something like that. note the semicolon at the end (very important, because we're defining a variable here!)

pretty neat, huh?

but wait, we don't specify a return type, so how does that work?

the magic of **`auto`**. it just... resolves?

but this is a strictly typed language! we cannot have a system that doesn't let us strictly type things! so what's the proper way to define this?

well, to know that we obviously need to know the return type. let's say it's `size_t` (what a `vector.size()` would return).

`size_t` is actually just an `unsigned long`, which is actually just a 32-bit unsigned integer (exactly like an `unsigned int`, but whatever, because a `long` is exactly the same as an `int` for some reason...)

so because of that, and because `size_t` isn't actually a type we can reference (but `size_type` is? which is also an `unsigned long`?), our return type will be unsigned long.

here's the proper syntax for defining it then (you might need to scroll right to see the whole block):

```cpp
function<unsigned long(int,string)> lambdafunction = [&] (int a, string b) -> unsigned long {
    return something;
};
```

wait, what? it just got like... twice as long!

yes! yes it did!

so what's that whole `<unsigned long(int,string)>` thing? i couldn't find much documentation on it (or i didn't look hard enough), so i basically tried enough stuff until it worked, and now i'm graciously sparing YOU from having to do the same.

basically it's `<return type(parameter types in order, comma separated)>`. except we already wrote the parameter types `(int a, string b)` and the return type `-> unsigned long`! so why do we need to do it again?

**because c++ is redundant, and that is good.**

redundancy is rarely the worst solution. all it can do is catch mistakes from higher levels. so now that you've joined me in the cult of lambda functions, let's move on to literally anything else!

## why are preprocessor macros turing complete again?

yes, i checked. preprocessor macros are apparently turing complete. you could write basically anything with them (in theory) given enough time and effort.

so why does something meant for convenience have to be turing complete?

i have no answer for you. moving on, i just thought that was pretty cool.

## see you next time!

i ran out of c++ stuff to rant about for now (at least that i could think of just now).

see you next time!
