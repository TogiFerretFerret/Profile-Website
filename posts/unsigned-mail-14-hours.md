---
title: my email went out unsigned for 14 hours and nothing complained
date: 2026-10-24
description: i added spam filtering to my mail server and one postfix setting quietly stopped dkim from signing everything sent through webmail. no errors, no bounces, mail still arrived. here is how it hid, how i found it, and the one-line fix.
tags: email,postfix,dkim,debugging,devops
---

# my email went out unsigned for 14 hours and nothing complained

a quick refresher on the setup, because the bug only makes sense with it: my mail server is postfix, dovecot, opendkim for signing and (new that day) rspamd for spam filtering, and everything below uses `example.com` as a placeholder.

i added rspamd. i tested it. spam got rejected, normal mail got through, mail sent from the server itself still came out signed. i wrote "done" in my notes and went to bed.

what i did not notice: **everything sent through webmail and mail clients was now going out with no dkim signature at all.** for about 14 hours.

nothing broke. that's the entire problem.

## why nothing complained

this is the part worth writing down, because it's a pretty general lesson about email auth.

mail needs to pass **dmarc**, and dmarc passes if *either* spf or dkim passes and lines up with your domain. my spf record was fine, so every unsigned message sailed through on spf alone. no bounce. no spam folder. delivered, perfect, unsigned.

the three test emails i sent that night all went out unsigned, and all of them arrived (one landed in spam, for an unrelated reason that's its own story). i had no idea.

## the nudge

the next morning a google dmarc aggregate report landed in my inbox (the xml-in-a-zip kind that you get when you publish a `rua=` address). it listed three messages from my server's ip for my domain, with the result:

```
spf: pass     dkim: fail
```

a dkim "fail" with no signature recorded at all. that's what "no signature present" looks like in the report.

now, honesty about the timeline: that report covered the *previous* utc day, and ended before i even touched rspamd. so it did **not** catch this bug, and i can't tell you which three messages it counted. but a dkim fail on my own mail was enough to make me stop and test signing properly, instead of assuming. that's the real value of those reports: they're an alarm that goes off even when the cause is somewhere else.

## actually testing it

i made a throwaway mailbox, authenticated like a real mail client and sent mail through each submission port, to myself, then looked for the header:

```
smtps  (465): no DKIM-Signature
submission (587): no DKIM-Signature
local relay (25 from localhost): DKIM-Signature present
```

so mail injected locally (like my other service's verification emails) was fine. only mail from *logged-in users* wasn't signed. and an earlier test of 587, before rspamd, **had** been signed. so something i did that night had broken it.

a red herring worth knowing about: the "Sent" copy that webmail saves **never** has the dkim header, because it's saved before the mail goes through the milter. don't use your sent folder to check signatures. i nearly did.

## the cause: a milter macro list

opendkim signs mail that comes from "internal" hosts. mail from logged-in users arrives from outside, so how does opendkim know it's mine? postfix passes it a macro, `{auth_type}`, saying "this client authenticated". that's how opendkim decides to sign.

postfix's `milter_mail_macros` defaults to:

```
i {auth_type} {auth_authen} {auth_author} {mail_addr} {mail_host} {mail_mailer}
```

what i set it to (from the macro list i remembered from rspamd's milter instructions) was:

```
milter_mail_macros = i {mail_addr} {client_addr} {client_name} {auth_authen}
```

see it? **`{auth_type}` is gone.** rspamd is happy (it wants `{auth_authen}`). opendkim silently decides every authenticated message is external mail it shouldn't touch, and signs nothing. no log line, no warning.

## the fix

put the defaults back and add rspamd's extras on top:

```
milter_mail_macros = i {auth_type} {auth_authen} {auth_author} {mail_addr} {mail_host} {mail_mailer} {client_addr} {client_name}
```

then i tested again, on both ports, and this time instead of just *looking* for a `DKIM-Signature` header i verified it against the public key in dns:

```
$ opendkim-testmsg < message ; echo $?
0
```

(`opendkim-testmsg` prints nothing on success. an exit code of 0 means the signature actually verifies. i spent a minute confused that it was "doing nothing".)

after the fix: both ports signed, a message to gmail came back clean, rspamd still rejected my spam test string, and the local relay path still worked.

## the lessons

1. **dmarc passing on spf alone hides broken dkim.** if you want to know your signing works, check it directly. don't wait for something to bounce.
2. **a header being present isn't the same as a signature being valid.** verify it. `opendkim-testmsg` costs nothing.
3. **a setup guide for tool a can quietly break tool b.** always diff the setting you're overriding against its default first.
4. **publish a `rua=` address and actually read the reports.** mine didn't catch this one, and it still made me look.
5. **test every path.** i'd tested the local path, the spam path and the inbound path. i hadn't tested the one i use every day.
