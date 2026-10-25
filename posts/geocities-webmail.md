---
title: i themed my webmail like geocities and the whole inbox went invisible
date: 2026-10-26
description: turning roundcube into a 1997 homepage, and the css selector that matched an attribute roundcube never changes, which hid every email i opened. plus the white reading pane, the starfield that leaked into forms, and a screenshot method that doesn't need my real inbox.
tags: css,roundcube,webdev,debugging,design
---

# i themed my webmail like geocities and the whole inbox went invisible

my website is a deliberate 1997 geocities page: starfield background, a chunky title with a drop shadow, ridge borders, a scrolling marquee. at some point i looked at my webmail, which was roundcube's default skin (clean, modern, and absolutely nothing like the rest of my site), and thought: no. that has to match.

so i put roundcube in a geocities costume. here are the screenshots, then the part where i couldn't read my own email.

![the webmail login page: a starfield background and a small bordered box with a yellow "riverxia.sh" title banner and a yellow login button](/blog/assets/webmail-login.png)

![the webmail inbox: a navy interface with a yellow selected folder, a pink compose button, a message list with white text on navy, and a white reading pane showing a newsletter](/blog/assets/webmail-message.png)

(everything in those screenshots is fake mail seeded into a throwaway account. more on that at the end.)

## how the costume works

roundcube lets you add a tiny plugin. mine is a few lines of php whose entire job is to load **one css file** on every page. all the styling lives in that file, mounted into the container, so roundcube updates can't wipe it. it sits on top of roundcube's default skin and just overrides colors, fonts and borders.

the first version was a cute, cluttered, hard-to-read mess, and i couldn't read my own inbox. i'll get to why.

## bug 1: a background that wasn't

my starfield was two radial gradients layered on a dark color. nothing showed up. the page stayed white.

the css shorthand `background:` requires the plain color to come **last** in a stack of layers. i'd put it first. an invalid shorthand isn't a warning, it just throws the whole declaration away. moving the color to the end, or splitting it into `background-color` and `background-image`, fixed it.

## bug 2: the invisible emails

this one's the good one.

roundcube shows an empty-state graphic in the preview pane before you pick a message: a big pale logo on white, which looked terrible on my navy theme. i wanted it gone, so i wrote a rule to hide it:

```css
iframe[src*="watermark"] { opacity: 0; }
```

the placeholder is a page called `watermark.html` loaded into an iframe, so matching on `src` felt perfectly reasonable. it worked: the logo vanished.

and then **every email i opened was invisible too.**

roundcube doesn't change the iframe's `src` *attribute* when you open a message. it loads the message by setting the frame's location directly, so the attribute still says `watermark.html` forever, even while the frame is showing a message. my rule matched the iframe the entire time and hid whatever was inside it. i had built a theme where reading mail was impossible.

the fix is to hide the placeholder only when nothing is selected:

```css
body:not(:has(table.messagelist tr.selected)) iframe#messagecontframe { opacity: 0; }
```

`:has()` lets the css look at the *selection state of the list*, which is the thing that actually changes.

## a misdiagnosis i'm not proud of

at one point the new styling wasn't showing up in a screenshot, and my coding agent announced "the new css isn't being served" and started checking the deploy. the css *was* being served. the screenshot was stale, because the script that retakes it hadn't actually run. we blamed the server for a picture nobody had re-taken. the evidence was a timestamp on a png, and nobody looked at it.

## bugs 3 to 5: small crimes

- **the mysterious empty boxes.** each message row had a little empty square on the right. they were the flag icons, and i'd earlier given them a beveled border for a retro look. the border applied to the *empty* icon too. removing it fixed it.
- **buttons on top of the text.** hovering a row pops up a little bar of flag and delete buttons that covers the sender and date. i hid it. you can still flag and delete from the toolbar.
- **the starfield leaking into forms.** the settings pages are loaded inside iframes, and the page behind the text was the starfield showing through the form labels, which made them hard to read. i'd written a rule for `body.iframe`. roundcube puts the `iframe` class on the **`<html>`** element, not `<body>`. same selector, one level off, nothing matched.

## the big design change: the reading pane is just white

when i tried to make the *emails themselves* match the theme, i forced a cream background and dark text on every message with `!important`. that worked for plain text.

then i seeded a test newsletter that brought its own dark background and light text. my forced cream background clashed with the mail's own styling, and the heading, which was white, disappeared into the cream.

the lesson is that **you don't get to restyle someone else's html email.** each mail knows what colors it wants. so i did two things:

1. removed every `!important` override on message content, so the mail's own inline styles win
2. made the whole reading view one plain white page: subject, sender block, attachment bar and body, all on white with dark text

now a normal mail looks normal, and a mail with its own dark design keeps it. the rest of the interface keeps the geocities look. it was a big readability win for almost no code.

## how i took screenshots without showing my inbox

i didn't want to screenshot my real mail. so every time i changed the css:

1. create a throwaway mailbox with a random password
2. seed it with a few fake messages over imap: plain text, a light newsletter, a dark newsletter, a reply with quoted text
3. log in with a headless browser and take screenshots of the login, inbox, message, compose and settings pages
4. **delete the mailbox**, its mail and roundcube's saved profile for it

when a style didn't apply, i'd ask the browser what was *actually* on top at a pixel, with `document.elementsFromPoint(x, y)`. that call told me exactly which element was painting the grey patch i couldn't track down. it beats guessing at selectors.

## lessons

1. **match on state, not on attributes that look like state.** an `src` attribute that never changes isn't a switch.
2. **check what's really being shown before blaming the server.** i lost time to a stale screenshot.
3. **don't force colors on content you don't own.** let html email keep its own look.
4. **an invalid css declaration fails silently.** if something doesn't show up, suspect the syntax before the cascade.
5. **look at the element, not the rule.** `elementsFromPoint` in a headless browser is a debugger for "why is this patch grey".
