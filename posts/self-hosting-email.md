---
title: i self-host my email now (and every wrong turn i took)
date: 2026-10-19
id: 16
description: postfix, dovecot, rspamd, opendkim and roundcube on a cheap vps so i can have a real address on my own domain. the dns you actually need, and every dumb thing that broke on the way.
tags: email,selfhosting,linux,devops,postfix
---

# self-hosting email

everyone on the internet will tell you "never self-host email." 

so naturally i did it. (im autism, we've been over this)

i wanted `me@my-domain` instead of a school address or a random gmail, and a game i help build needs to send verification emails eventually anyway, so there was going to be a mail backend on a vps regardless. might as well let it hold my mailbox too.

receiving mail is easy. **sending** mail is where it gets spicy, because you're not fighting software, you're fighting reputation. this is the log of how it went.

(everything below uses `example.com` as a placeholder. no i'm not leaking my server, go away)

> **update (oct 24):** i eventually took my own advice from the end of this post and moved my *outgoing* mail onto a **cloudflare smtp relay**. the whole story is in the update at the bottom.

## the stack

- **postfix** — takes mail from the internet, sends mail out
- **dovecot** — stores the mail, serves imap, does auth
- **opendkim** — signs outgoing mail so people believe it's from you
- **rspamd** (+ redis) — spam filtering
- **roundcube** — webmail, in docker
- **certbot** — tls certs, dns-01 challenge
- **fail2ban** — because bots find port 25 in like an hour

postfix was already on the box as a send-only relay for the game, so i extended it instead of ripping it out. one postfix, two jobs: verification emails from the game over localhost, and my actual mailbox over the internet.

mailboxes are *virtual* users. one unix user (`vmail`) owns everything under `/var/vmail` and the accounts live in a flat password file. no unix account per mailbox. for a personal server this is plenty.

## the dns you actually need

this is the part that decides whether gmail puts you in the inbox or the bin. all of these matter:

```
mail.example.com.            A      <server ip>        # NOT proxied
example.com.                 MX 10  mail.example.com.
example.com.                 TXT    "v=spf1 mx -all"
mail.example.com.            TXT    "v=spf1 a -all"    # spf for the helo name too
mail._domainkey.example.com. TXT    "v=DKIM1; h=sha256; k=rsa; p=<public key>"
_dmarc.example.com.          TXT    "v=DMARC1; p=quarantine; adkim=r; aspf=r"
_imaps._tcp.example.com.     SRV    0 1 993 mail.example.com.
_submissions._tcp.example.com. SRV  0 1 465 mail.example.com.
```

plus **reverse dns** (PTR) on the server's ip, which you set at your vps provider, not in your zone. that one bites later, keep reading.

do not put the mail hostname behind a cdn proxy. smtp is not http. (cloudflare, i love you, but no)

## setup, short version

- **tls cert.** ports 80/443 on my box were already taken, so http validation was out. dns-01 through certbot's cloudflare plugin needs no ports at all. i made an api token that can *only* edit dns for that one zone, so if it leaks off the server it can't do much.
- **dkim.** `opendkim-genkey -b 2048 -s mail -d example.com`, publish the public half in dns, point opendkim's `KeyTable` and `SigningTable` at the private half. keep the old domain's key working while you add the new one.
- **dovecot.** imap over tls only (993). no plain imap, no pop. it also does auth for postfix over a unix socket and delivers mail via lmtp.
- **postfix.** the important knobs:

```
virtual_mailbox_domains = example.com
virtual_transport       = lmtp:unix:private/dovecot-lmtp
smtpd_tls_auth_only     = yes
smtpd_sasl_type         = dovecot
smtpd_sasl_path         = private/auth
```

plus two extra listeners in `master.cf`, submission (587, starttls) and smtps (465), both requiring a login. port 25 is for server-to-server delivery only.

- **spam.** rspamd runs as a milter in front of opendkim. score over 6 gets flagged, over 15 gets rejected outright, and a one-line sieve rule files the flagged stuff into Junk. mail *i* send through submission skips rspamd and just gets signed.
- **webmail.** roundcube in a container bound to localhost, behind the reverse proxy i already had. it talks to dovecot and postfix over tls like any other client. i also made it look like a 1997 geocities page, because of course i did.

## everything that went wrong

**dovecot 2.4 is a different config language.** every guide online is for 2.3. variables are `%{user | domain}` now, `mail_plugins` is a block of `name = yes`, and writing a `mailbox X { ... }` on one line is a syntax error. `doveconf -n` is your friend. 

**opendkim refused my key.** it runs as root here and decided the key directory was "not secure" because another user owned it, so it tempfailed *every message*. the log line was extremely clear. i just hadn't read it yet. fix was `chown -R root:root`.

**i pasted `p=` twice into the dkim record.** public key records look like `p=MIIB...`. my script stripped the prefix, then i added it back, so it was `p=p=MIIB...`. `opendkim-testkey` said "key missing" and i stared at it for a while. always run the tester, don't trust your eyes.

**greylisting made a normal email say "try again later".** rspamd's greylist is on by default. fine in theory, but i don't want my *own* first message to wait around. off.

**let's encrypt flaked once.** "networking error looking up TXT during secondary validation." retried with a longer propagation wait and it went through. 

**my router remembered the domain didn't exist.** i looked up the new hostname *before* making the record, and my resolver cached the NXDOMAIN. everything worked on the server and was unreachable from my own laptop for like 20 minutes. if it works from a public resolver but not from you, that's why.

**webmail could read but not send.** roundcube wasn't logging in to smtp, so postfix correctly said "Client host rejected." it needs `smtp_user = '%u'` and `smtp_pass = '%p'`. (postfix was right, i was wrong. as usual.)

**fail2ban will ban your own webmail.** roundcube logs in from the docker bridge address, so a few wrong passwords bans the container. add the docker range to `ignoreip`.

**and then: spam. of course spam.** my first test to gmail landed in the spam folder. spf, dkim, and dmarc all passed, so what was wrong? the reverse dns. my server introduced itself as `mail.example.com` but the ip's PTR record said something else (the provider's default hostname), and i don't control the PTR on this vps. 

the fix: make *outgoing* mail introduce itself with the name the PTR already uses, which does resolve back to the ip:

```
smtp_helo_name = <the provider's default hostname for the ip>
```

only the outgoing helo changes, the banner and tls name stay the same. next test landed in the inbox. 

## checklist for the next unfortunate soul

1. make sure your provider allows outbound port 25 *before* you start. some block it.
2. sort the PTR/helo thing first. it's the #1 reason for spam-foldering. (or skip the whole problem and relay your outgoing mail, see the update below.)
3. publish spf, dkim and dmarc, then **test each one** instead of trusting that you typed them right.
4. send a test to a gmail address and hit "show original". you want `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS`.
5. back up configs before editing, and run `postfix check` and `doveconf -n` before restarting anything.
6. fail2ban and rate limits are not optional. 

## do i recommend it

for one mailbox at tiny volume: yes, it's a great weekend project and i learned a ton about how email actually works. for anything business-critical: no, use a hosted provider, or relay your outgoing mail through one and only self-host the receiving side.

but my inbox is mine now and that's pretty cool. 

## update (oct 24): i took my own advice (a cloudflare smtp relay)

at the end of this post i said that for anything serious you should relay your outgoing mail through a hosted provider and only self-host the receiving side. five days later i did exactly that, because i'm a hypocrite, and also because it turns out "i don't control the PTR on this vps" is a pretty fragile foundation for your email.

i was already on cloudflare for my sites, and paying for workers gets you cloudflare's email sending, which you can use as a plain smtp relay. so i pointed postfix at the cloudflare smtp relay. the new split:

- **inbound is still entirely mine:** mx record, my server, dovecot, rspamd, my webmail.
- **outbound for my own domain is a rented lane:** postfix hands the message to cloudflare's smtp relay instead of delivering it directly.

the wiring, with placeholder names:

```
# master.cf: a separate smtp transport just for the relay
relay-cf  unix  -  -  n  -  -  smtp
  -o smtp_tls_wrappermode=yes
  -o smtp_tls_security_level=encrypt
  -o smtp_sasl_auth_enable=yes
  -o smtp_sasl_password_maps=hash:/etc/postfix/sasl_passwd
  -o smtp_sasl_security_options=noanonymous

# main.cf
sender_dependent_default_transport_maps = hash:/etc/postfix/sender_transport

# /etc/postfix/sender_transport  (then: postmap it)
@example.com   relay-cf:[smtp.relay.example]:465   # your cloudflare smtp relay host
```

a few gotchas, in the order they would have bitten me:

**keep the relay in its own transport.** port 465 is implicit tls, so it needs `smtp_tls_wrappermode = yes`. set that globally and every normal port-25 delivery to the rest of the internet breaks. a dedicated transport keeps the blast radius to one destination.

**only relay domains cloudflare knows about.** a relay like this generally only accepts mail from domains you've onboarded with it. my box also sends mail for a second domain that isn't in my cloudflare account, so i routed *only my own domain* through the relay and left the other one sending directly. otherwise i'd have been betting that domain's verification emails on a relay that probably wouldn't accept them.

**the "password" is a cloudflare api token.** it lives in `sasl_passwd`, owned by root, mode 600, run through `postmap`. it is not in any config i'd ever commit.

**the dns got fixed for me.** onboarding the domain in cloudflare added a bounce subdomain with its own spf record, and a dkim key for my domain. with relaxed dmarc alignment that's how mail coming from a completely different ip can still pass dmarc, even though my root spf record only lists my own server. (i haven't gone through the headers to see which signature gmail credited, so i'm not making claims about that.)

the result: a test message to gmail came back `250 2.0.0 Ok` from the relay and **did not go to spam**. no ptr, no helo gymnastics, and the thing that was blocking my own mail is now cloudflare's problem.

so it's not *purely* self-hosted anymore, and i'm fine with that. the mailbox, the spam filtering, the webmail and every message i receive are still mine. only the last hop out is rented, from the cloudflare smtp relay. the helo fix above still matters for anything that sends directly, so i left it in.
