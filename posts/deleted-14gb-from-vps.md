---
title: i deleted 14 gb from my vps in one sitting
date: 2026-10-24
time: 20:30
description: a login banner said the disk was 21% full and i asked "what's using 20%?". the answer was one log database, some docker layers, an old stack and two gigabytes of journal. how i found it, what i checked before deleting, and what i backed up first.
tags: linux,docker,devops,sysadmin,disk
---

# i deleted 14 gb from my vps in one sitting

i ssh'd into my vps and the login banner said:

```
Usage of /:  21.0% of 95.85GB
```

21% is fine. nothing was wrong. but i looked at that number and asked the most dangerous question in sysadmin: *what is using 20%?*

by the end of the session the disk was at 7.1 GB used, which is 8%, and i'd freed about 14 GB. here's where it went and what i checked before touching anything.

## step 1: ask the disk, not your memory

```sh
sudo du -xh --max-depth=1 / | sort -rh | head
```

(`-x` keeps it on one filesystem, so it doesn't wander into other mounts.) the answer:

```
8.8G  /var
6.7G  /opt
3.1G  /usr
1.5G  /home
```

then i went one level deeper into the big ones. `/opt` was 6.7 GB, and **all 6.7 GB was one file**: the request-log database of an ai gateway container i'd stopped using. `/var` had 6.1 GB under `containerd` and 2 GB of system journal.

### a gotcha

`docker` itself only used 293 MB, which confused me, because i have a lot of images. the images weren't in docker's folder at all. they live in `containerd`'s, so `du` on docker's directory tells you almost nothing. the thing to run is:

```sh
docker system df
```

which reported the truth: about 6.4 GB of images, plus 2.8 GB of **build cache** that nothing was using.

## step 2: before you delete, check who's using it

the biggest single target was the 6.7 GB log database, belonging to an ai gateway i'd decided i didn't need anymore. before stopping it i checked three things:

- **does anything reference it?** i searched the configs of everything else on the box for its hostname and its port. nothing.
- **is anything connected to it right now?** `ss -tnp` filtered to its port. nobody.
- **is it doing anything?** `docker logs --since 30m`. silence.

only then did i stop it.

### the proxy that wasn't just a proxy

here's the near-miss. the gateway had a reverse proxy container in front of it, with a name that made it sound like part of the same thing. i went to remove it too.

that proxy was **also serving my webmail** and another site, because i'd been lazy and reused it. stopping it would have taken webmail down. so instead i edited its config to remove only the gateway's two routes, reloaded it, and checked that the other sites still answered 200.

a container's name tells you what it was *created* for, not what it does *now*.

## step 3: delete in the right order, and check after each step

1. **the gateway:** stopped it (and set its restart policy to `no` so a reboot wouldn't bring it back), removed the 6.7 GB log database, and kept its 41 MB config in case i ever want it back. later i removed the container and its 349 MB image too. disk: **21 GB → 14 GB**.
2. **an old web app of mine:** a container whose image alone was **2.7 GB**. the app's source lived in a folder that wasn't a git repository, so before deleting anything i downloaded that folder (111 KB) to my laptop. then i removed the container, the image, the source folder and its dns record. disk: 14 GB → 13 GB.
3. **the build cache and the journal:** `docker builder prune` cleared 2.8 GB of cached build steps nothing needed. the system journal had grown to about 2 GB, so i trimmed it to the newest 200 MB with `journalctl --vacuum-size=200M`. disk: 13 GB → 7.9 GB.
4. **an old stack:** four stopped containers from a previous version of a project, a network and three volumes. one volume was a **146 MB postgres data directory**, real data. i compressed it into a 66 MB tarball on the server before removing the volume. then i pruned images nothing was using anymore, which was another 177 MB. disk: 7.9 GB → **7.1 GB**.

after every step i checked that everything live was still up: the sites, the webmail, the containers that were supposed to be running.

## where the 14 GB went

| thing | size |
|---|---|
| one ai gateway's request-log database | 6.7 GB |
| docker build cache nobody used | 2.8 GB |
| an old app's image | 2.7 GB |
| system journal (kept 200 MB) | ~1.8 GB |
| unused images and leftovers | ~0.5 GB |

(the rows are rounded, so they add up to a bit more than the real total, which was 21 GB used down to 7.1 GB used: about 14 GB freed.)

what's left that's big, and is staying: a game's postgres data, some tooling the game pipeline depends on, and a couple of gigabytes of images i actually use.

## what i'd do the same next time

1. **look before you delete.** `du` for the filesystem, `docker system df` for docker, and remember the two don't agree.
2. **check references, connections and logs** before stopping anything. three one-liners, thirty seconds.
3. **never trust a container's name.** check what it's actually serving.
4. **back up first if it can't be recreated.** a 66 MB tarball and a 111 KB folder are nothing, and "i'm sure i don't need it" is how you lose a database.
5. **verify after every step.** a deletion that quietly breaks something is much cheaper to catch immediately than ten steps later.
6. **trim your journal.** i didn't know mine had quietly grown to 2 GB, because journald never complains.
