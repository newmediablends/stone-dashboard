#!/usr/bin/env python3
"""
Stone Dashboard — local HTTPS server
Serves the dashboard + reads/writes live files from your Second Brain over WiFi.
HTTPS enables voice narration on iPhone.

Usage:
  cd ~/stone-dashboard && python3 server.py

First run: generates a certificate. AirDrop it to your iPhone and trust it
in Settings → General → VPN & Device Management → [cert name] → Trust.
"""

import http.server
import json
import re
import socket
import ssl
import subprocess
from pathlib import Path

BRAIN     = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/2-Areas/AI Second Brain"
DASHBOARD = Path(__file__).parent
PORT      = 3000

DAILY_DIR = BRAIN / "Daily"
TRACKER   = BRAIN / "3-Resources" / "Network-Tracker.md"
PROJECTS  = BRAIN / "1-Projects"
CERT      = DASHBOARD / "cert.pem"
KEY       = DASHBOARD / "key.pem"


# ── SSL cert ──────────────────────────────────────────────────────────────────

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ensure_cert(ip):
    if CERT.exists() and KEY.exists():
        return
    print("  Generating SSL certificate (first run)...")
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(KEY), "-out", str(CERT),
        "-days", "825", "-nodes",
        "-subj", "/CN=Stone Dashboard",
        "-addext", f"subjectAltName=IP:{ip},IP:127.0.0.1,DNS:localhost",
    ], check=True, capture_output=True)
    print(f"  Certificate saved to {CERT}")
    print()
    print("  ── iPhone trust (one-time) ─────────────────────────────")
    print(f"  1. AirDrop  {CERT}  to your iPhone")
    print("  2. iPhone: Settings → General → VPN & Device Management")
    print("     → Stone Dashboard → Install")
    print("  3. Settings → General → About → Certificate Trust Settings")
    print("     → Stone Dashboard → toggle ON")
    print("  4. Reload the app — voice narration now works")
    print("  ────────────────────────────────────────────────────────")


# ── Log write-back ────────────────────────────────────────────────────────────

def append_log(date_str, time_str, entry):
    note_path = DAILY_DIR / f"{date_str}.md"
    if not note_path.exists():
        return False
    lines = note_path.read_text(encoding="utf-8").splitlines(keepends=True)
    log_line = f"- {time_str} - {entry}\n" if time_str else f"- {entry}\n"
    in_log = False
    last_entry_idx = -1
    log_section_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "## Log":
            in_log = True
            log_section_idx = i
            continue
        if in_log:
            if stripped.startswith("## ") or stripped == "---":
                break
            if stripped.startswith("- "):
                last_entry_idx = i
    if last_entry_idx >= 0:
        lines.insert(last_entry_idx + 1, log_line)
    elif log_section_idx >= 0:
        lines.insert(log_section_idx + 1, log_line)
    else:
        lines.append("\n## Log\n")
        lines.append(log_line)
    note_path.write_text("".join(lines), encoding="utf-8")
    return True


# ── Request handler ───────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"

        if path in ("/", "/index.html"):
            self.serve(DASHBOARD / "index.html", "text/html")

        elif path == "/icon.svg":
            self.serve(DASHBOARD / "icon.svg", "image/svg+xml")

        elif path == "/cert.pem":
            self.serve(CERT, "application/x-pem-file")

        elif path == "/daily/Network-Tracker.md":
            self.serve(TRACKER, "text/plain")

        elif path.startswith("/daily/"):
            fname = path[len("/daily/"):]
            if len(fname) == 13 and fname.endswith(".md") and fname[:4].isdigit():
                self.serve(DAILY_DIR / fname, "text/plain")
            else:
                self.send_error(404)

        elif path == "/projects":
            try:
                names = [d.name for d in sorted(PROJECTS.iterdir()) if d.is_dir()
                         and not d.name.startswith(".")]
                body = "\n".join(names).encode()
                self._respond(200, "text/plain", body)
            except Exception:
                self.send_error(500)

        elif path.startswith("/projects/"):
            parts = path[len("/projects/"):].split("/", 1)
            if len(parts) == 2 and parts[1] == "Status.md":
                folder = parts[0].replace("%20", " ").replace("%E2%80%94", "—")
                self.serve(PROJECTS / folder / "Status.md", "text/plain")
            else:
                self.send_error(404)

        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/daily/log":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                date_s = body.get("date", "")
                time_s = body.get("time", "")
                entry  = body.get("entry", "").strip()
                if date_s and entry and re.match(r"\d{4}-\d{2}-\d{2}$", date_s):
                    ok = append_log(date_s, time_s, entry)
                    self._respond(200, "application/json", json.dumps({"ok": ok}).encode())
                else:
                    self.send_error(400)
            except Exception as e:
                self.send_error(500)
        else:
            self.send_error(404)

    def serve(self, filepath, content_type):
        try:
            data = filepath.read_bytes()
            self._respond(200, content_type, data)
        except FileNotFoundError:
            self.send_error(404)
        except Exception:
            self.send_error(500)

    def _respond(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ip   = local_ip()
    host = socket.gethostname()

    ensure_cert(ip)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(CERT), str(KEY))

    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print(f"\nStone server — HTTPS — reading live from Second Brain")
    print(f"  On this Mac:  https://localhost:{PORT}")
    print(f"  On iPhone:    https://{ip}:{PORT}")
    print(f"  Or try:       https://{host}.local:{PORT}")
    print(f"\n  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
