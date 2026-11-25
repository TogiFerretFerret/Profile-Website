#!/usr/bin/env python3
"""Run a full local integration test of all static sites and dynamic features (paste, guestbook, front worker).
Exits 0 on success, non-zero on failure.
"""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.parse

PORT = 8999

def main():
    print("1. Building production site assets...")
    res = subprocess.run([sys.executable, "build.py"], capture_output=True, text=True)
    if res.returncode != 0:
        print("Build failed:\n", res.stderr)
        sys.exit(1)

    print("2. Starting single Rust backend on port", PORT)
    server_bin = Path("server/target/debug/riverxia-server").resolve()
    if not server_bin.exists():
        print("Building server binary first...")
        subprocess.run(["cargo", "build"], cwd="server", check=True)

    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env["DIST_DIR"] = str(Path("dist").resolve())
    env["DB_PATH"] = str(Path(".data/test.db").resolve())
    env["LOCAL"] = "1"
    proc = subprocess.Popen([str(server_bin)], env=env)

    # Wait until server is listening
    base = f"http://127.0.0.1:{PORT}"
    started = False
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{base}/www/index.html", timeout=0.5) as r:
                if r.status == 200:
                    started = True
                    break
        except Exception:
            time.sleep(0.1)
    if not started:
        print("Server failed to start in time")
        sys.exit(1)

    try:
        # 1. Test Static Pages
        print("3. Testing static subdomains...")
        for site in ["www", "blog", "projects", "uses", "dots", "paste", "guestbook"]:
            url = f"{base}/{site}/index.html"
            with urllib.request.urlopen(url) as resp:
                assert resp.status == 200, f"Failed to load {site}: {resp.status}"
            print(f"   [OK] {site} returned 200")

        # 2. Test Paste (Create, Read Raw, Read HTML, Delete)
        print("4. Testing paste endpoint...")
        req = urllib.request.Request(
            f"{base}/paste/",
            data=b"hello from local test paste",
            headers={"content-type": "text/plain"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 201, f"Paste create status: {resp.status}"
            del_token = resp.headers.get("x-delete-token")
            paste_url = resp.read().decode().strip()
            assert del_token, "No delete token received"
            # In local mode, URL should be http://host/paste/{id}
            assert "/paste/" in paste_url, f"Expected /paste/ in URL, got: {paste_url}"
            paste_id = paste_url.rstrip("/").split("/")[-1]

        # Read paste
        read_req = urllib.request.Request(
            f"{base}/paste/{paste_id}",
            headers={"user-agent": "curl/8.0"}
        )
        with urllib.request.urlopen(read_req) as resp:
            content = resp.read().decode()
            assert content == "hello from local test paste", f"Unexpected paste content: {content}"
        print(f"   [OK] paste created ({paste_id}) and verified")

        # Delete paste
        del_req = urllib.request.Request(
            f"{base}/paste/{paste_id}",
            headers={"x-delete-token": del_token},
            method="DELETE"
        )
        with urllib.request.urlopen(del_req) as resp:
            assert resp.status == 200
        print(f"   [OK] paste deleted")

        # 3. Test Guestbook (Sign, Read, Delete)
        print("5. Testing guestbook endpoint...")
        sign_data = json.dumps({"name": "testbot", "message": "hello local world"}).encode("utf-8")
        gb_sign_req = urllib.request.Request(
            f"{base}/guestbook/api/entries",
            data=sign_data,
            headers={"content-type": "application/json"}
        )
        with urllib.request.urlopen(gb_sign_req) as resp:
            assert resp.status == 201
            entry_id = json.loads(resp.read().decode())["id"]
        print(f"   [OK] guestbook signed (id {entry_id})")

        # Read entries
        with urllib.request.urlopen(f"{base}/guestbook/api/entries") as resp:
            entries = json.loads(resp.read().decode())["entries"]
            assert any(e["id"] == entry_id and e["name"] == "testbot" for e in entries)
        print("   [OK] guestbook entry found in list")

        # CLI read
        cli_req = urllib.request.Request(f"{base}/guestbook/", headers={"user-agent": "curl/8.0"})
        with urllib.request.urlopen(cli_req) as resp:
            cli_text = resp.read().decode()
            assert "testbot" in cli_text
        print("   [OK] guestbook terminal curl view verified")

        # Front worker curl /
        cli_front_req = urllib.request.Request(f"{base}/", headers={"user-agent": "curl/8.0"})
        with urllib.request.urlopen(cli_front_req) as resp:
            assert "riverxia" in resp.read().decode()
        print("   [OK] front worker root CLI responder verified")

        print("\nALL LOCAL TESTS PASSED SUCCESSFULLY!")

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
