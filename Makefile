# riverxia.sh build system.   make        -> same as `make all`
# Note: buck2 is now also supported: `buck2 run :check`, `buck2 run :build`, `buck2 run :test`, `buck2 run :preview`
#
#   make all      deps + checks + production build + deploy all 7 sites + verify every page is live
#                 (does NOT make the offline blog copy, and does NOT commit or push)
#   make help     list every target
#
# deploy credentials come from the environment or a gitignored .env (see .env.example). nothing is stored in this file.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
MAKEFLAGS += --no-print-directory

-include .env
export

SITES  := www blog projects uses dots paste guestbook
SRC    := build.py tui/riverxia.sh dots/install.sh $(wildcard dots/shots/*) worker/front.js worker/paste.js guestbook-client.js worker/guestbook.js button/riverxia.png button/riverxia.gif scripts/deploy-site.sh style.css comments.js bimi.svg render_math.js package.json $(wildcard posts/*.md assets/*)
OFFLINE_OUT ?= $(HOME)/riverxia-blog-offline.html
PYTHON ?= $(shell if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; elif command -v python3 >/dev/null 2>&1; then echo python3; else echo python; fi)
PORT   ?= 8000

.PHONY: all help deps pydeps check build deploy verify preview offline push clean distclean publish test FORCE

all: deploy  ## everything: deps, checks, production build, deploy 7 sites, verify (not offline)

help:  ## list targets
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

deps: pydeps node_modules/katex/package.json  ## python + npm deps (katex renders blog math at build time)

pydeps:
	@$(PYTHON) -c "import markdown" 2>/dev/null || { \
		if command -v uv >/dev/null 2>&1; then \
			[ -d .venv ] || uv venv .venv; \
			uv pip install markdown; \
		else \
			echo "python 'markdown' package is missing: pip install markdown" >&2; exit 1; \
		fi \
	}

node_modules/katex/package.json: package.json package-lock.json
	npm install --no-audit --no-fund
	@touch $@

check:  ## fast pre-deploy sanity checks: front matter, images, no credentials
	@$(PYTHON) scripts/check.py

build: dist/.built  ## production build into dist/ and Rust server (skipped if nothing changed)

# the build also depends on today's date: a post scheduled for a future day stays hidden, and the first
# `make all` on (or after) its day sees .today change, rebuilds, and publishes it. .today only changes when the date does.
TODAY := $(shell TZ=America/New_York date +%F)
.today: FORCE
	@[ "$$(cat .today 2>/dev/null)" = "$(TODAY)" ] || echo "$(TODAY)" > .today

dist/.built: $(SRC) .today | deps check
	$(PYTHON) build.py --prod
	cd server && cargo build
	@touch $@

deploy: .deploy-stamp  ## build if needed, deploy www/blog/projects/uses/dots/paste/guestbook, verify every page (skipped if nothing changed)

.deploy-stamp: dist/.built
	@[ -n "$${CLOUDFLARE_ACCOUNT_ID:-}" ] || { echo "CLOUDFLARE_ACCOUNT_ID is not set (see .env.example)" >&2; exit 1; }
	@{ [ -n "$${CLOUDFLARE_API_TOKEN:-}" ] || { [ -n "$${CLOUDFLARE_EMAIL:-}" ] && [ -n "$${CLOUDFLARE_API_KEY:-}" ]; }; } || { echo "set CLOUDFLARE_API_TOKEN, or CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY (see .env.example)" >&2; exit 1; }
	@for s in $(SITES); do scripts/deploy-site.sh $$s; done
	@touch $@

publish:  ## deploy a fresh clone of origin/main, never your working tree (this is what the daily timer runs)
	scripts/publish-scheduled.sh

verify:  ## check every page on the live sites answers 200 (no upload)
	@for s in $(SITES); do scripts/deploy-site.sh $$s verify; done

preview: | deps  ## local preview at http://localhost:8000/ (runs single Rust backend; PORT=n to change)
	INCLUDE_FUTURE=1 $(PYTHON) build.py
	@rm -f dist/.built .deploy-stamp
	cd server && PORT=$(PORT) cargo run

test: | deps  ## run full local automated test suite for all static and dynamic features against Rust backend
	@$(PYTHON) scripts/test_local.py

offline: | deps  ## one-file offline copy of the whole blog -> ~/riverxia-blog-offline.html (not part of `make all`)
	$(PYTHON) offline.py
	cp dist/blog-offline.html "$(OFFLINE_OUT)"
	@ls -lh "$(OFFLINE_OUT)" | awk '{print "wrote", $$9, "(" $$5 ")"}'

push:  ## git push origin main (not part of `make all`)
	git push origin main

clean:  ## remove build output, server binaries and stamps
	rm -rf dist .deploy-stamp .today __pycache__ .data buck-out server/target

distclean: clean  ## clean + remove node_modules and .venv
	rm -rf node_modules .venv
