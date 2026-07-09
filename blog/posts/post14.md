---
title: Misc: TEAGod Staff WiFi
date: 2026-07-05
description: An enterprise WiFi RADIUS server that trusts a public CA for client auth. Grab a free Actalis S/MIME cert, present it as your EAP-TLS client cert, and you're staff.
tags: ctf,misc,writeup
---

# teagod staff wifi

no hack no ctf. the brief: they exposed the RADIUS server used for employees' internal WiFi auth. "can you try logging in?"

```
udp://tearoam.teagod.tech:18120
```

udp `18120` is `1812` (RADIUS auth) with a `0` stapled on. enterprise WiFi = 802.1X / EAP. they handed us the whole FreeRADIUS docker bundle, so this is a config-reading challenge before it's anything else.

## recon

three things jump out of the config.

`clients.conf` — the shared secret is the default, and it accepts **any** source IP:

```
client public_ipv4 {
    ipaddr = 0.0.0.0/0
    secret = testing123
}
```

the `Dockerfile` sneaks the flag into `post-auth` right after `remove_reply_message_if_eap`:

```
update reply {
    Reply-Message := "NHNC{...}"
}
```

`remove_reply_message_if_eap` normally strips `Reply-Message` on EAP — but the flag is added *after* it, so it survives. so the whole game is: **get one Access-Accept and read `Reply-Message`.**

and `mods-enabled/eap` — the auth methods. PEAP/TTLS tunnel into inner MSCHAPv2/PAP, which needs a username+password we don't have and aren't meant to brute. that leaves **EAP-TLS** (client certificate, no password):

```
tls-config tls-common {
    certificate_file = ${certdir}/server.pem
    ca_file          = ${cadir}/ca.pem      # <-- validates CLIENT certs
    ...
}
```

so a client cert that chains to `ca.pem` logs in. what's `ca.pem`?

## the CA is a real public root

```bash
$ openssl x509 -in ca.pem -noout -subject -fingerprint -sha256
subject= CN=Actalis Authentication Root CA, O=Actalis S.p.A., L=Milan, C=IT
sha256 Fingerprint=55:92:60:84:EC:96:3A:64:B9:6E:2A:BE:01:CE:0B:A8:...:76:60:66
```

that's not a self-signed lab CA. that's the **genuine, publicly-trusted Actalis Authentication Root CA** (fingerprint matches the real one). they set the EAP-TLS `ca_file` to a public root, which means the server accepts **any certificate issued anywhere under the Actalis PKI** as a valid staff login.

(the bundled `server.pem`/`server.key` are a dead end — that cert chains to a *different* Actalis root, "TLS Server RSA Root CA 2025", not the Authentication Root, so it won't validate against `ca_file`.)

this is a real reported class of bug — the flag even links [ZD-2025-00549](https://zeroday.hitcon.org/vulnerability/ZD-2025-00549). trust a public CA for client auth and "authorized" means "owns a certificate," which anyone can get.

## the free cert

"everything required can be obtained for free." Actalis issues **free S/MIME email certificates**, and they chain exactly to *Actalis Authentication Root CA* with `clientAuth` in the EKU. that's our staff badge.

grab one at `extrassl.actalis.it/portal/uapub/freemail` — email + terms + captcha, they email a code, you download a `.p12` and they email its password. burner email is fine; the cert CN ends up being that address, nobody checks it. checking what we got:

```bash
$ openssl x509 -in leaf.pem -noout -issuer -ext extendedKeyUsage
issuer= CN=Actalis Client Authentication CA G3, O=Actalis S.p.A., ...
X509v3 Extended Key Usage: TLS Web Client Authentication, E-mail Protection
$ openssl verify -purpose sslclient -CAfile ca.pem -untrusted g3_intermediate.pem leaf.pem
leaf.pem: OK
```

`clientAuth` present, chains clean to the exact root the server trusts. game over, basically.

## the login

drive EAP-TLS with `eapol_test` (from wpa_supplicant). extract key + leaf + intermediate from the `.p12`, and set `client_cert` to **leaf + intermediate only** — drop the root. that's the "if it works locally but not remote, your packet may be too large" hint: the client's Certificate message gets fragmented over RADIUS, and shipping the root too can push it over the edge.

```ini
network={
    key_mgmt=IEEE8021X
    eap=TLS
    identity="whatever@teagod.tech"
    client_cert="leaf_plus_intermediate.pem"
    private_key="key.pem"
    fragment_size=1300
}
```

```bash
$ eapol_test -c eap.conf -a 35.206.253.234 -p 18120 -s testing123
```

the one gotcha that ate a few tries: with `ca_cert` set, **our client** tried to validate the *server's* cert, failed ("unknown CA"), and killed the handshake before ever sending our cert. we don't care who the server is — drop `ca_cert`, don't verify the server. then:

```
RADIUS message: code=2 (Access-Accept) identifier=12 length=275
   Attribute 18 (Reply-Message) length=86
      Value: 'NHNC{Huh...HoW_did_U_10g_iN?_https://zeroday.hitcon.org/vulnerability/ZD-2025-00549}'
SUCCESS
```

the server built the chain leaf → G3 → Actalis Authentication Root CA, saw a trusted root, and let us in.

## why it falls over

- **`ca_file` is a public CA.** for EAP-TLS the client-cert CA should be your *own* internal issuer. point it at a public root and every free cert on the internet is a valid credential. "authenticated" collapses into "has $0 and five minutes."
- **the secret was `testing123`** and clients were `0.0.0.0/0`, so RADIUS itself let anyone talk to it.

fix: private internal CA for client certs, real shared secret, scoped client IPs.

## flag

```
NHNC{Huh...HoW_did_U_10g_iN?_https://zeroday.hitcon.org/vulnerability/ZD-2025-00549}
```
