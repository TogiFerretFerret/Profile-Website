load("//:defs.bzl", "sh_run")

# Checks pre-deploy sanity: front matter, images, no credentials
sh_run(
    name = "check",
    script = """
if [ -f .venv/bin/python3 ]; then
    .venv/bin/python3 scripts/check.py
else
    python3 scripts/check.py
fi
""",
)

# Build static sites using build.py
sh_run(
    name = "build-site",
    script = """
if [ -f .venv/bin/python3 ]; then
    .venv/bin/python3 build.py --prod
else
    python3 build.py --prod
fi
""",
)

# Build the single Rust backend binary
sh_run(
    name = "build-server",
    script = """
cd server && cargo build
""",
)

# Build both static site and Rust server
sh_run(
    name = "build",
    script = """
if [ -f .venv/bin/python3 ]; then
    .venv/bin/python3 build.py --prod
else
    python3 build.py --prod
fi
cd server && cargo build
""",
)

# Run the single Rust backend server
sh_run(
    name = "server",
    script = """
cd server && LOCAL=1 DIST_DIR=../dist cargo run
""",
)

# Run local preview with the Rust backend
sh_run(
    name = "preview",
    script = """
if [ -f .venv/bin/python3 ]; then
    INCLUDE_FUTURE=1 .venv/bin/python3 build.py
else
    INCLUDE_FUTURE=1 python3 build.py
fi
cd server && LOCAL=1 DIST_DIR=../dist cargo run
""",
)

# Full automated test suite against the Rust server
sh_run(
    name = "test",
    script = """
if [ -f .venv/bin/python3 ]; then
    .venv/bin/python3 scripts/test_local.py
else
    python3 scripts/test_local.py
fi
""",
)
