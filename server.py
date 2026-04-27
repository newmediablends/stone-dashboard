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
TRACKER   = BRAIN / "1-Projects" / "Job Search — VP or CPO Role" / "Network-Tracker.md"
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


# ── Network contacts parser ───────────────────────────────────────────────────

from datetime import date as _date

def parse_contacts(max_rows=12):
    try:
        txt = TRACKER.read_text(encoding="utf-8")
    except Exception:
        return {"contacts": [], "batchQueue": None}
    today = _date.today()
    results, hdr = [], None
    in_queue_section = False
    queue_count = 0
    queue_earliest_due = None

    for line in txt.split("\n"):
        if line.startswith("## "):
            in_queue_section = "priority import queue" in line.lower()
            hdr = None
            continue
        if "|" not in line:
            continue
        parts = line.split("|")
        cells = [c.strip() for c in parts[1:len(parts)-1]]
        if not cells:
            continue
        if all(re.match(r"^-*$", c) for c in cells):
            continue
        lower = [c.lower() for c in cells]
        if lower[0] == "name" and "status" in lower:
            hdr = {
                "name":    0,
                "company": lower.index("company") if "company" in lower else -1,
                "status":  lower.index("status"),
                "action":  next((i for i, c in enumerate(lower) if "next action" in c), -1),
                "due":     lower.index("due") if "due" in lower else -1,
                "last_touch": next((i for i, c in enumerate(lower) if "last touch" in c), -1),
                "notes":   lower.index("notes") if "notes" in lower else -1,
            }
            continue
        if hdr is None:
            continue
        name = cells[hdr["name"]] if hdr["name"] < len(cells) else ""
        if not name or re.match(r"^[-–—]+$", name):
            continue
        if hdr["status"] >= 0 and len(cells) <= hdr["status"]:
            continue
        raw_status = cells[hdr["status"]] if hdr["status"] < len(cells) else ""
        action = cells[hdr["action"]] if hdr["action"] >= 0 and hdr["action"] < len(cells) else ""
        due_str = cells[hdr["due"]] if hdr["due"] >= 0 and hdr["due"] < len(cells) else ""
        company = cells[hdr["company"]] if hdr["company"] >= 0 and hdr["company"] < len(cells) else ""
        last_touch = cells[hdr["last_touch"]] if hdr["last_touch"] >= 0 and hdr["last_touch"] < len(cells) else ""
        notes = cells[hdr["notes"]] if hdr["notes"] >= 0 and hdr["notes"] < len(cells) else ""
        initials = "".join(w[0] for w in name.split() if w)[:2].upper()
        sl = raw_status.lower()
        due_match = re.match(r"(\d{2})/(\d{2})/(\d{4})", due_str)
        past_due = False
        due_date = None
        if due_match:
            try:
                due_date = _date(int(due_match.group(3)), int(due_match.group(1)), int(due_match.group(2)))
                past_due = due_date < today
            except Exception:
                pass
        if past_due:
            status, av = "overdue", "av-red"
        elif "priority" in sl:
            status, av = "send", "av-green"
        else:
            status, av = "active", "av-gray"

        if in_queue_section and due_date:
            days_left = (due_date - today).days
            if 0 <= days_left <= 3:
                queue_count += 1
                if queue_earliest_due is None or due_date < queue_earliest_due:
                    queue_earliest_due = due_date

        results.append({
            "initials": initials, "name": name, "role": company,
            "action": action, "status": status, "time": due_str, "av": av,
            "lastTouch": last_touch, "notes": notes,
        })

    results.sort(key=lambda c: {"overdue": 0, "send": 1, "active": 2}.get(c["status"], 2))

    batch_queue = None
    if queue_count >= 10 and queue_earliest_due:
        days_left = (queue_earliest_due - today).days
        label = "today" if days_left == 0 else ("tomorrow" if days_left == 1 else f"in {days_left} days")
        batch_queue = {
            "count": queue_count,
            "due": queue_earliest_due.strftime("%m/%d/%Y"),
            "daysLeft": days_left,
            "label": label,
        }

    return {"contacts": results[:max_rows], "batchQueue": batch_queue}


# ── MASK write-back ───────────────────────────────────────────────────────────

def write_mask_response(date_str, letter, response):
    note_path = DAILY_DIR / f"{date_str}.md"
    if not note_path.exists():
        return False
    lines = note_path.read_text(encoding="utf-8").splitlines(keepends=True)

    in_mask = False
    prompt_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r'^##\s+MASK Journal', stripped):
            in_mask = True
            continue
        if in_mask:
            if stripped.startswith("## "):
                break
            if re.match(rf'^\*\*{re.escape(letter)}:\*\*', stripped):
                prompt_idx = i
                break

    if prompt_idx < 0:
        return False

    # Find boundary: next **X:** or section heading or end
    search_end = len(lines)
    for i in range(prompt_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if re.match(r'^\*\*[MASK]:\*\*', stripped) or stripped.startswith("## "):
            search_end = i
            break

    # Replace existing blockquote or insert after prompt
    response_line = f"> {response}\n"
    existing = -1
    for i in range(prompt_idx + 1, search_end):
        if lines[i].strip().startswith(">"):
            existing = i
            break

    if existing >= 0:
        lines[existing] = response_line
    else:
        lines.insert(prompt_idx + 1, response_line)

    note_path.write_text("".join(lines), encoding="utf-8")
    return True


# ── 10x toggle ────────────────────────────────────────────────────────────────

def toggle_tenx(date_str, row_index, done):
    note_path = DAILY_DIR / f"{date_str}.md"
    if not note_path.exists():
        return False
    lines = note_path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_sec = False
    rows_seen = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r'^##\s+(Section 2|10x Items)', s, re.IGNORECASE):
            in_sec = True
            continue
        if in_sec:
            if s.startswith("##"):
                break
            if re.match(r'^\|\s*(?:\d+|⚠️)', s):
                if rows_seen == row_index:
                    new = re.sub(r'\[\s*\]', '[x]', line) if done else re.sub(r'\[x\]|\[X\]|✅', '[ ]', line)
                    lines[i] = new
                    note_path.write_text("".join(lines), encoding="utf-8")
                    return True
                rows_seen += 1
    return False


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

        elif path == "/manifest.json":
            self.serve(DASHBOARD / "manifest.json", "application/manifest+json")

        elif path == "/sw.js":
            self.serve(DASHBOARD / "sw.js", "text/javascript")

        elif path in ("/icon-180.png", "/icon-512.png"):
            self.serve(DASHBOARD / path[1:], "image/png")

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

        elif path == "/api/contacts":
            try:
                contacts = parse_contacts()
                body = json.dumps(contacts, ensure_ascii=False).encode("utf-8")
                self._respond(200, "application/json", body)
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

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
            except Exception:
                self.send_error(500)

        elif path == "/daily/tenx":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                date_s = body.get("date", "")
                idx    = body.get("index", -1)
                done   = bool(body.get("done", False))
                if date_s and isinstance(idx, int) and idx >= 0 and re.match(r"\d{4}-\d{2}-\d{2}$", date_s):
                    ok = toggle_tenx(date_s, idx, done)
                    self._respond(200, "application/json", json.dumps({"ok": ok}).encode())
                else:
                    self.send_error(400)
            except Exception as e:
                import traceback; traceback.print_exc()
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/daily/mask":
            try:
                length   = int(self.headers.get("Content-Length", 0))
                body     = json.loads(self.rfile.read(length))
                date_s   = body.get("date", "")
                letter   = body.get("letter", "").upper()
                response = body.get("response", "").strip()
                if date_s and letter in "MASK" and len(letter) == 1 and response and re.match(r"\d{4}-\d{2}-\d{2}$", date_s):
                    ok = write_mask_response(date_s, letter, response)
                    self._respond(200, "application/json", json.dumps({"ok": ok}).encode())
                else:
                    self.send_error(400)
            except Exception:
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
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

HTTP_PORT = 3001

if __name__ == "__main__":
    import threading

    ip   = local_ip()
    host = socket.gethostname()

    ensure_cert(ip)

    # HTTPS server (port 3000) — full features including voice narration
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(CERT), str(KEY))
    https_server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    https_server.socket = ctx.wrap_socket(https_server.socket, server_side=True)

    # HTTP server (port 3001) — no cert needed, works on any device immediately
    http_server = http.server.HTTPServer(("0.0.0.0", HTTP_PORT), Handler)

    print(f"\nStone server — reading live from Second Brain")
    print(f"  HTTPS (voice on): https://{ip}:{PORT}")
    print(f"  HTTP  (no cert):  http://{ip}:{HTTP_PORT}   ← use this on iPhone")
    print(f"\n  Press Ctrl+C to stop\n")

    threading.Thread(target=https_server.serve_forever, daemon=True).start()

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
