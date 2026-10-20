---
title: I self-host my email now (and every wrong turn I took)
date: 2026-10-20
description: Postfix, Dovecot, Rspamd, OpenDKIM and Roundcube on a cheap VPS, with a real address on my own domain. What the stack looks like, the DNS you actually need, and every dumb thing that broke along the way.
tags: email,selfhosting,linux,devops,postfix
---

## why

I wanted `me@my-domain` instead of a school address or a random gmail. A game I help build also needs to send verification emails sooner or later, so there was going to be a mail backend on a VPS anyway. Might as well let it carry my own mailbox too.

Everyone says "never self-host email". Receiving is easy, sending is where it gets spicy: you are fighting reputation, not software. Here is how it went.

(Everything below uses `example.com` / `mail.example.com` as placeholders.)

## the stack

| job | thing |
|-----|-------|
| accept mail from the internet, send mail out | **Postfix** |
| store mail, serve IMAP, do auth | **Dovecot** |
| sign outgoing mail (DKIM) | **OpenDKIM** |
| spam filtering | **Rspamd** + Redis |
| webmail | **Roundcube** (in docker) |
| TLS certs | **certbot**, DNS-01 challenge |
| brute-force protection | **fail2ban** |

Postfix already existed on the box as a send-only relay for the game, so I extended it instead of ripping it out. One Postfix now does two jobs: verification emails from the game over localhost, and my mailbox over the internet.

Mailboxes are *virtual* users: one unix user (`vmail`) owns everything under `/var/vmail`, and accounts live in a flat password file. No unix accounts per mailbox. For a personal server that is plenty.

## the DNS you need

This is the part that decides whether Gmail puts you in the inbox or the bin. All of these matter:

```
mail.example.com.          A      <your server ip>          # NOT proxied
example.com.               MX 10  mail.example.com.
example.com.               TXT    "v=spf1 mx -all"
mail.example.com.          TXT    "v=spf1 a -all"           # SPF for the HELO name too
mail._domainkey.example.com. TXT  "v=DKIM1; h=sha256; k=rsa; p=<public key>"
_dmarc.example.com.        TXT    "v=DMARC1; p=quarantine; adkim=r; aspf=r; rua=mailto:<you>"
_imaps._tcp.example.com.   SRV    0 1 993 mail.example.com.
_submissions._tcp.example.com. SRV 0 1 465 mail.example.com.
```

Plus **reverse DNS** (PTR) on the server's IP, which you set at your VPS provider, not in your DNS zone. More on that below because it bit me.

Do not put the mail hostname behind a CDN proxy. SMTP is not HTTP.

## setup, short version

**1. TLS cert.** Port 80/443 on my box were already taken by other stuff, so HTTP validation was out. DNS-01 with certbot's Cloudflare plugin works without touching ports. I made an API token that can only edit DNS for that one zone, so a leaked token on the server cannot do much.

**2. DKIM key.** `opendkim-genkey -b 2048 -s mail -d example.com`, publish the public half in DNS, point OpenDKIM's `KeyTable` and `SigningTable` at the private half. Keep the existing domain's key working while you add the new one.

**3. Dovecot.** IMAP over TLS only (993), no plain IMAP, no POP. Dovecot also does auth for Postfix over a unix socket, and delivers mail via LMTP.

**4. Postfix.** The important knobs:

```
virtual_mailbox_domains = example.com
virtual_transport       = lmtp:unix:private/dovecot-lmtp
smtpd_tls_auth_only     = yes
smtpd_sasl_type         = dovecot
smtpd_sasl_path         = private/auth
```

and two extra listeners in `master.cf`: submission (587, STARTTLS) and smtps (465), both requiring SASL login. Port 25 is for server-to-server delivery only.

**5. Spam.** Rspamd runs as a milter in front of OpenDKIM. Scores over 6 get flagged, over 15 get rejected, and a one-line Sieve rule files flagged mail into Junk. Mail *I* send through submission skips Rspamd and just gets signed.

**6. Webmail.** Roundcube in a container, bound to localhost, with the reverse proxy I already had in front. It talks to Dovecot and Postfix over TLS like any other client.

## everything that went wrong

**Dovecot 2.4 is a different config language.** Every guide online is for 2.3. Variables are `%{user | domain}` now, `mail_plugins` is a block of `name = yes`, and a `mailbox X { ... }` on one line is a syntax error. `doveconf -n` is your friend.

**OpenDKIM refuses keys it thinks are insecure.** It runs as root here and complained that the key directory was owned by another user ("not secure"), then tempfailed every message. The log line was clear; I just had not read it yet. Fix: `chown -R root:root` the key dir.

**I pasted `p=` twice into the DKIM record.** Public key records look like `p=MIIB...`. My script stripped the prefix, then I added it back, giving `p=p=MIIB...`. `opendkim-testkey` said "key missing". Always run the tester.

**Greylisting made a normal message "try again later".** Rspamd's greylist is on by default. It is fine in theory but I do not want my own first email to wait. Off.

**Let's Encrypt validation flaked once.** "Networking error looking up TXT during secondary validation." Retry with a longer propagation wait and it went through.

**My resolver remembered the domain did not exist.** I looked up the new hostname before creating the record, and my router cached the NXDOMAIN. Everything was fine on the server, and unreachable from my own laptop for a while. If it works from a public resolver but not from you, that is why.

**Webmail could read but not send.** Roundcube was not authenticating to SMTP, so Postfix correctly rejected it as "Client host rejected". It needs `smtp_user = '%u'` and `smtp_pass = '%p'`.

**fail2ban will ban your own webmail.** Roundcube logs in from the docker bridge address, so a few bad passwords there bans the container. Add the docker range to `ignoreip`.

**And then spam. Of course spam.** My first test to Gmail landed in the spam folder. SPF, DKIM and DMARC all passed, so what was wrong? The reverse DNS. My server introduced itself as `mail.example.com` while the IP's PTR record said something else (the provider's default hostname). I do not control the PTR on this VPS. The fix was to make outgoing mail introduce itself with the name the PTR already uses, which does resolve back to the IP:

```
smtp_helo_name = <the provider's default hostname for the ip>
```

(only the outgoing HELO changes; the banner and TLS name stay as they were.) Next test went to the inbox.

## checklist for the next person

1. Check that your provider allows outbound port 25 *before* you start. Some block it.
2. Get the PTR/HELO situation sorted first. It is the most common reason for spam-foldering.
3. Publish SPF, DKIM and DMARC, then **test each one** instead of trusting that you typed them right.
4. Send a test to a Gmail address and look at "Show original". You want `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS`.
5. Back up your configs before editing, and use `postfix check` and `doveconf -n` before restarting.
6. Rate limits and fail2ban are not optional on a mail server. Bots will find port 25 in hours.

## do i recommend it

For one mailbox and a tiny volume: yes, it is a good weekend project and I learned a lot about how email really works. For anything business-critical: no, use a hosted provider, or at least relay your outgoing mail through one and self-host only the receiving side.

My inbox is mine now though, and that is pretty cool.
