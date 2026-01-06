---
title: Why C++ Will Never Die (and why it shouldn't!)
date: 2026-01-06
description: It's not because it's such a perfect language...
tags: cpp,rant,competitive programming,lambda functions
---
Okay, so I get that not everyone likes C++. It's a difficult language to learn and use, and it has MANY quirks that just... piss you off.

Like seriously, it's a strictly typed language that oh-so-also happens to have the `auto` type.

But, I'm a firm believer that C++ is still good and relevant (not that I'm sure anyone was arguing otherwise) but I just wanted to talk about **MY** gripes with C++, and also what I love about it. 

## Lambda Functions and Auto
You may be awfully confused why I would combine these two seemingly unrelated things in one category, but trust me, they are pretty similar. 
In C++, there are lambda functions. Here is how most (competitive programmers) write them.
```cpp
// some stuff here
auto lambdafunction = [&] (int a, string b) {
    return something;
};
```
or something like that. Note the semicolon at the end (very important, because we're defining a variable here!)

Pretty neat, huh?
But wait, we don't specify a return type, so how does that work?
The magic of **`auto`**.
It just... resolves?

But this is a strictly typed language! We cannot have a system that doesn't allow us to strictly type things! So what's the proper way to define this?

Well, to know that, we obviously need to know the return type. Let's say our return type is `size_t` (what a `vector.size()` would return)

Well, `size_t` is actually just an `unsigned long`, which is actually just a 32-bit unsigned integer (exactly like an `unsigned int`, but whatever, because a `long` is exactly the same as an `int` for some reason...)

So because of that, and because `size_t` isn't actually a type we can reference (but `size_type` is? which also is an `unsigned long`?), our returned type will be unsigned long.

Here's the proper syntax for defining it then (you might need to scroll to the right to see the whole block).

```cpp
function<unsigned long(int,string)> lambdafunction = [&] (int a, string b) -> unsigned long {
    return something;
};
```
Wait, what? It just got like... twice as long!

Yes! Yes it did!

So what's that whole `<unsigned long(int,string)>` thing? Well, I couldn't find too much documentation on it (or I didn't look hard enough), but I basically tried enough stuff until I figured it out, so I'll grace you with YOU not having to do the same thing.

Basically, it is `<return type(parameter types in order, comma separated)>`. Except, we already define the parameter types `(int a, string b)` and the return type `-> unsigned long`! So why do we need to do it again?

**Because C++ is redundant, and that is good.**

Redundancy is rarely the worst solution. All it can do is catch mistakes from higher levels. So now that you've joined me in the cult of lambda functions, let's move on to talking about literally anything else!

## Why are preprocessor macros Turing Complete again?
Yes, I checked, preprocessor macros are apparently Turing Complete. You could basically write anything with them (in theory) with enough time and effort.

So why are things meant more for convenience have to be Turing Complete?

I have no answer for you. Moving on, I just thought that was pretty cool.

## See you next time!
I ran out of C++ stuff to rant about for now (at least that I could think of just now).
See you next time!
