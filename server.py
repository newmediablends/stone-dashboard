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


def _cat(path, binary=False):
    """Read a file — tries /bin/cat first (triggers iCloud download-on-demand), falls back to direct open."""
    r = subprocess.run(["/bin/cat", str(path)], capture_output=True)
    if r.returncode == 0:
        return r.stdout if binary else r.stdout.decode("utf-8")
    # Fallback: direct read (works once Full Disk Access is granted to Python.app)
    try:
        return path.read_bytes() if binary else path.read_text(encoding="utf-8")
    except Exception:
        raise PermissionError(f"cat failed (rc={r.returncode}): {r.stderr.decode()[:200]}")

BRAIN     = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/AI Second Brain"
DASHBOARD = Path(__file__).parent
PORT      = 3000

DAILY_DIR    = BRAIN / "Daily"
DAILY_LOCAL  = DASHBOARD / "daily"                          # local synced copies — always readable by launchd
CONTACTS_CACHE_ICLOUD = DAILY_DIR / "contacts-cache.json"
CONTACTS_CACHE_LOCAL  = DASHBOARD / "contacts-cache.json"   # always accessible by launchd
CONTACTS_CACHE = CONTACTS_CACHE_LOCAL                        # server reads local; Stone syncs from iCloud
PENDING_WRITES = DASHBOARD / "pending-writes.json"           # queued writes when iCloud is inaccessible
PROJECTS     = BRAIN / "1-Projects"
CERT      = DASHBOARD / "cert.pem"
KEY       = DASHBOARD / "key.pem"


# ── Pending-writes queue (processed by Stone at next session) ─────────────────

def queue_write(op: dict):
    """Append an operation to pending-writes.json for Stone to process at next session."""
    try:
        existing = json.loads(PENDING_WRITES.read_text(encoding="utf-8")) if PENDING_WRITES.exists() else []
        existing.append(op)
        PENDING_WRITES.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


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
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign,digitalSignature",
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


# ── Network contacts (Notion-backed cache) ────────────────────────────────────
# Source of truth: Notion Network Tracker (Data Source ID: cc5179f8-7c9d-4f04-bd77-b9e5ec48ee60)
# Stone writes Daily/contacts-cache.json after every Notion contact update and at wrap.
# server.py reads the cache — no Notion API key required.

from datetime import date as _date

def _read_json_file(path):
    """Read a JSON file — direct open for local paths, cat for iCloud paths."""
    if "Mobile Documents" in str(path):
        try:
            return _cat(path)
        except Exception:
            pass
    return path.read_text(encoding="utf-8")

def parse_contacts(max_rows=12):
    try:
        raw = _read_json_file(CONTACTS_CACHE)
        data = json.loads(raw)
        contacts = data.get("contacts", [])
        # Re-evaluate overdue status in case cache is from a previous day
        today = _date.today()
        for c in contacts:
            due_str = c.get("time", "")
            due_match = re.match(r"(\d{2})/(\d{2})/(\d{4})", due_str)
            if due_match:
                try:
                    due_date = _date(int(due_match.group(3)), int(due_match.group(1)), int(due_match.group(2)))
                    if due_date < today:
                        c["status"] = "overdue"
                        c["av"] = "av-red"
                except Exception:
                    pass
        contacts.sort(key=lambda c: {"overdue": 0, "send": 1, "nurture": 2, "active": 3}.get(c["status"], 3))
        focus_names = {c.lower() for c in data.get("focusToday", [])}
        sliced = contacts[:max_rows]
        in_slice = {c["name"].lower() for c in sliced}
        extras = [c for c in contacts[max_rows:] if c["name"].lower() in focus_names and c["name"].lower() not in in_slice]
        return {"contacts": sliced + extras, "batchQueue": data.get("batchQueue"), "focusToday": data.get("focusToday", [])}
    except Exception:
        return {"contacts": [], "batchQueue": None, "focusToday": []}


# ── Home data (Day Score, reflection, tomorrow) ───────────────────────────────

def parse_home_data(date_str):
    # Match write-side path resolution: prefer local mirror (always readable by launchd),
    # fall back to iCloud DAILY_DIR. Without this, launchd-spawned servers see empty
    # iCloud paths and return blank reflections even when the file exists locally.
    local_note  = DAILY_LOCAL / f"{date_str}.md"
    note_path   = local_note if local_note.exists() else DAILY_DIR / f"{date_str}.md"
    local_brief = DAILY_LOCAL / "Tomorrow-Brief.md"
    brief_path  = local_brief if local_brief.exists() else DAILY_DIR / "Tomorrow-Brief.md"

    tenx_done = 0
    tenx_total = 0
    outreach_sent = 0
    win = ""
    gap = ""
    next_up = ""
    tomorrow_items = []
    txt = ""

    if note_path.exists():
        try:
            txt = _cat(note_path)
        except Exception:
            txt = ""

        # ── 10x items (Section 2) ──────────────────────────────────────────────
        sec2_m = re.search(r"##\s+Section 2[^\n]*\n([\s\S]+?)(?=\n##|\Z)", txt)
        if sec2_m:
            for line in sec2_m.group(1).split("\n"):
                if "|" not in line:
                    continue
                cells = [c.strip() for c in line.split("|")]
                cells = [c for c in cells if c]
                if len(cells) < 5:
                    continue
                if all(re.match(r"^-+$", c) for c in cells):
                    continue
                if not re.match(r"^\d+$", cells[0]) and cells[0] != "⚠️":
                    continue
                item = cells[1]
                if not item or item.lower() in ("item", "---") or len(item) < 3:
                    continue
                done_cell = cells[-1]
                tenx_total += 1
                if re.search(r"[xX]|✅", done_cell):
                    tenx_done += 1
                elif not gap:
                    gap = item + " — not completed today"

        # ── Log entries ────────────────────────────────────────────────────────
        all_log_lines = []
        for log_re in (r"##\s+Section 3[^\n]*\n([\s\S]+?)(?=\n##|\n---|\Z)",
                       r"(?<!\S)##\s+Log\s*\n([\s\S]+?)(?=\n##|\n---|\Z)"):
            lm = re.search(log_re, txt)
            if lm:
                all_log_lines += re.findall(r"^-\s+(.+)$", lm.group(1), re.MULTILINE)

        outreach_sent = sum(
            1 for l in all_log_lines
            if re.search(r"outreach|sent|contacted|touched|messaged|reached out|follow.?up", l, re.IGNORECASE)
        )

        # Best win: log entry with positive signal, avoiding negatives and trivial entries
        _pos = re.compile(r"\bcomplete|complet|done\b|confirmed|closed|booked|signed|shipped|fixed|resolved|sent\b|finished|launch|deliver", re.IGNORECASE)
        _neg = re.compile(r"did not|didn't|no response|waiting|outstanding|not yet|blocked|pending|still open|not happen", re.IGNORECASE)
        _trivial = re.compile(r"\btest\b|hello|is this working|is it working", re.IGNORECASE)
        timestamped = [(m.group(1).strip(), line) for line in all_log_lines
                       for m in [re.match(r"\d[\d:]+\s*(?:AM|PM)?\s*[-–]\s*(.{40,})", line)] if m]
        # Prefer positive-signal entries
        for txt_part, _ in reversed(timestamped):
            if _pos.search(txt_part) and not _neg.search(txt_part) and not _trivial.search(txt_part):
                win = txt_part[:160]
                break
        # Fallback: any non-negative substantive entry
        if not win:
            for txt_part, _ in reversed(timestamped):
                if not _neg.search(txt_part) and not _trivial.search(txt_part):
                    win = txt_part[:160]
                    break

        # ── End-of-Day Reflection ──────────────────────────────────────────────
        # Section marker: accept either `## End-of-Day Reflection` heading or `**End-of-Day Reflection**` bold inline.
        # Answer position: accept either same-line (`1. **Q?** answer`) or next-line.
        refl_m = re.search(
            r"(?:^##\s+End-of-Day Reflection|\*\*End-of-Day Reflection\*\*)[^\n]*\n([\s\S]+?)(?=\n---|\n##|\Z)",
            txt, re.MULTILINE,
        )
        if refl_m:
            refl = refl_m.group(1)
            # Each pattern allows: optional **bold** wrapper around the question, then either
            # the answer on the same line after the question, or on the next line.
            q1 = re.search(r"1\.\s*\*{0,2}What got done\?\*{0,2}\s*(.{10,}?)(?=\n\d\.|\n\n|\Z)", refl, re.DOTALL)
            q2 = re.search(r"2\.\s*\*{0,2}What didn[^\n*]*\?\*{0,2}\s*(.{10,}?)(?=\n\d\.|\n\n|\Z)", refl, re.DOTALL)
            q4 = re.search(r"4\.\s*\*{0,2}What would make tomorrow better\?\*{0,2}\s*(.{10,}?)(?=\n\d\.|\n\n|\Z)", refl, re.DOTALL)
            def _clean(s):
                return re.sub(r"\s+", " ", s).strip()
            if q1:
                ans = _clean(q1.group(1))
                if ans and not ans.startswith(("2.", "3.", "4.")):
                    win = ans
            if q2:
                ans = _clean(q2.group(1))
                if ans and not ans.startswith(("3.", "4.")):
                    gap = ans
            if q4:
                ans = _clean(q4.group(1))
                if ans and not ans.startswith("-"):
                    next_up = ans

    # ── Score: 70% 10x + 30% log density ──────────────────────────────────────
    score = round((tenx_done / tenx_total) * 70) if tenx_total else 0
    log_density = min(30, len(all_log_lines if 'all_log_lines' in dir() else []) * 2)
    score = min(100, score + log_density)

    # ── Tomorrow's Top 3 ───────────────────────────────────────────────────────
    if brief_path.exists():
        try:
            tb = _cat(brief_path)
        except Exception:
            tb = ""
        loops_m = re.search(r"##\s+Open Loops[^\n]*\n([\s\S]+?)(?=\n##|\Z)", tb)
        if loops_m:
            items = re.findall(r"^-\s+(.+)$", loops_m.group(1), re.MULTILINE)
            tomorrow_items = [i.strip().strip("*").strip() for i in items if i.strip()][:3]

    if not tomorrow_items and txt:
        sec2_m = re.search(r"##\s+Section 2[^\n]*\n([\s\S]+?)(?=\n##|\Z)", txt)
        if sec2_m:
            for line in sec2_m.group(1).split("\n"):
                if "|" not in line or len(tomorrow_items) >= 3:
                    continue
                cells = [c.strip() for c in line.split("|")]
                cells = [c for c in cells if c]
                if len(cells) < 5 or not re.match(r"^\d+$", cells[0]):
                    continue
                if re.search(r"\[\s*\]", cells[-1]):
                    item = cells[1]
                    if item and item.lower() not in ("item", "---") and len(item) > 3:
                        tomorrow_items.append(item)

    stats = [
        {"dot": "#D1FAE5", "text": f"{tenx_done} of {tenx_total} 10x done" if tenx_total else "No 10x yet", "color": "#D1FAE5"},
        {"dot": "#FCD34D", "text": f"{outreach_sent} outreach logged", "color": "#FCD34D"},
        {"dot": "#6B7280", "text": f"{tenx_total - tenx_done} items open" if tenx_total else "—", "color": "#9CA3AF"},
    ]

    reflection = []
    if win:
        reflection.append({"label": "Win", "border": "#D1FAE5", "lc": "#1A4731", "text": win})
    if gap:
        reflection.append({"label": "Gap", "border": "#FCD34D", "lc": "#D97706", "text": gap})
    reflection.append({
        "label": "Next",
        "border": "#E5E7EB",
        "lc": "#6B7280",
        "text": next_up or "Stone is staging tomorrow's brief.",
    })

    return {"score": score, "stats": stats, "reflection": reflection, "tomorrow": tomorrow_items}


# ── MASK write-back ───────────────────────────────────────────────────────────

def write_mask_response(date_str, letter, response):
    local_path = DAILY_LOCAL / f"{date_str}.md"
    note_path = local_path if local_path.exists() else DAILY_DIR / f"{date_str}.md"
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
            # Match both **M:** and **M — Mindset** formats
            if re.match(rf'^\*\*{re.escape(letter)}[\s:—–\-]', stripped):
                prompt_idx = i
                break

    if prompt_idx < 0:
        return False

    # Find boundary: next MASK letter heading or section heading
    search_end = len(lines)
    for i in range(prompt_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if re.match(r'^\*\*[MASK][\s:—–\-]', stripped) or stripped.startswith("## "):
            search_end = i
            break

    # Replace existing blockquote or insert after last non-empty prompt line
    response_line = f"> {response}\n"
    existing = -1
    for i in range(prompt_idx + 1, search_end):
        if lines[i].strip().startswith(">"):
            existing = i
            break

    if existing >= 0:
        lines[existing] = response_line
    else:
        # Insert after the last non-empty line in the block (end of prompt text)
        insert_at = prompt_idx + 1
        for i in range(prompt_idx + 1, search_end):
            if lines[i].strip():
                insert_at = i + 1
        lines.insert(insert_at, response_line)

    try:
        note_path.write_text("".join(lines), encoding="utf-8")
        return True
    except Exception:
        queue_write({"type": "mask", "date": date_str, "letter": letter, "response": response})
        return False


# ── 10x toggle ────────────────────────────────────────────────────────────────

def toggle_tenx(date_str, row_index, done):
    local_path = DAILY_LOCAL / f"{date_str}.md"
    note_path = local_path if local_path.exists() else DAILY_DIR / f"{date_str}.md"
    try:
        if not note_path.exists():
            raise FileNotFoundError
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
    except Exception:
        queue_write({"type": "tenx", "date": date_str, "index": row_index, "done": done})
        return False


# ── Contact tracker write-back ────────────────────────────────────────────────

import datetime as _dt

def update_contact_in_tracker(name, updates, clear_focus=False):
    """
    Updates a contact in Daily/contacts-cache.json (Notion is source of truth;
    cache is the local mirror the dashboard reads).
    updates: dict with any of: status, last_touch, due (MM/DD/YYYY string)
    clear_focus: if True, removes this contact from the focusToday list
    """
    try:
        raw = _cat(CONTACTS_CACHE)
        data = json.loads(raw)
        contacts = data.get("contacts", [])
        clean = lambda s: re.sub(r"[^\w\s''-]", "", s).strip().lower()
        target = clean(name)
        today = _date.today()
        matched = False
        for c in contacts:
            if clean(c.get("name", "")) != target:
                continue
            matched = True
            if "last_touch" in updates:
                c["lastTouch"] = updates["last_touch"]
            if "due" in updates:
                c["time"] = updates["due"]
            if "status" in updates:
                # Remap markdown status values to cache format
                sl = updates["status"].lower()
                if "priority" in sl:
                    c["status"], c["av"] = "send", "av-green"
                elif "active" in sl:
                    c["status"], c["av"] = "send", "av-green"
                else:
                    c["status"], c["av"] = "active", "av-gray"
            # Re-evaluate overdue after any update
            due_str = c.get("time", "")
            due_match = re.match(r"(\d{2})/(\d{2})/(\d{4})", due_str)
            if due_match:
                try:
                    due_date = _date(int(due_match.group(3)), int(due_match.group(1)), int(due_match.group(2)))
                    if due_date < today:
                        c["status"], c["av"] = "overdue", "av-red"
                except Exception:
                    pass
            break
        if not matched:
            return False
        if clear_focus:
            ft = data.get("focusToday", [])
            data["focusToday"] = [n for n in ft if clean(n) != target]
        contacts.sort(key=lambda c: {"overdue": 0, "send": 1, "nurture": 2, "active": 3}.get(c["status"], 3))
        data["contacts"] = contacts
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        CONTACTS_CACHE_LOCAL.write_text(payload, encoding="utf-8")
        try:  # best-effort sync back to iCloud
            CONTACTS_CACHE_ICLOUD.write_text(payload, encoding="utf-8")
        except Exception:
            pass
        return True
    except Exception:
        return False


# ── End-of-Day Wrap write-back ────────────────────────────────────────────────

def write_wrap_reflection(date_str, answers):
    """answers: dict with keys win, gap, worked, better"""
    local_path = DAILY_LOCAL / f"{date_str}.md"
    note_path = local_path if local_path.exists() else DAILY_DIR / f"{date_str}.md"
    if not note_path.exists():
        return False
    txt = note_path.read_text(encoding="utf-8")
    refl_m = re.search(
        r"(\*\*End-of-Day Reflection\*\*[^\n]*\n)"
        r"(1\.[\s\S]+?)"
        r"(?=\n---|\n##|\Z)",
        txt,
    )
    if not refl_m:
        return False
    block = (
        refl_m.group(1)
        + f"1. What got done?\n{answers.get('win','').strip()}\n\n"
        + f"2. What didn't get done?\n{answers.get('gap','').strip()}\n\n"
        + f"3. What worked?\n{answers.get('worked','').strip()}\n\n"
        + f"4. What would make tomorrow better?\n{answers.get('better','').strip()}"
    )
    note_path.write_text(txt[:refl_m.start()] + block + txt[refl_m.end():], encoding="utf-8")
    return True


# ── Log write-back ────────────────────────────────────────────────────────────

def append_log(date_str, time_str, entry):
    local_path = DAILY_LOCAL / f"{date_str}.md"
    note_path = local_path if local_path.exists() else DAILY_DIR / f"{date_str}.md"
    log_line = f"- {time_str} - {entry}\n" if time_str else f"- {entry}\n"
    try:
        if not note_path.exists():
            raise FileNotFoundError
        lines = note_path.read_text(encoding="utf-8").splitlines(keepends=True)
        in_log = False
        last_entry_idx = -1
        log_section_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r"##\s+Section 3|##\s+Log$", stripped):
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
    except Exception:
        queue_write({"type": "log", "date": date_str, "time": time_str, "entry": entry})
        return False


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

        elif path == "/daily/contacts-cache.json":
            self.serve(CONTACTS_CACHE, "application/json")

        elif path == "/outreach-drafts.json":
            self.serve(DASHBOARD / "outreach-drafts.json", "application/json")

        elif path.startswith("/daily/"):
            fname = path[len("/daily/"):]
            if len(fname) == 13 and fname.endswith(".md") and fname[:4].isdigit():
                local = DAILY_LOCAL / fname
                icloud = DAILY_DIR / fname
                if local.exists():
                    self.serve(local, "text/plain")
                elif icloud.exists():
                    self.serve(icloud, "text/plain")
                else:
                    self.send_error(404)
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

        elif path == "/api/pending-writes":
            try:
                ops = json.loads(PENDING_WRITES.read_text(encoding="utf-8")) if PENDING_WRITES.exists() else []
                self._respond(200, "application/json", json.dumps(ops, ensure_ascii=False).encode())
            except Exception:
                self._respond(200, "application/json", b"[]")

        elif path == "/api/contacts":
            try:
                contacts = parse_contacts()
                body = json.dumps(contacts, ensure_ascii=False).encode("utf-8")
                self._respond(200, "application/json", body)
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/api/home":
            from urllib.parse import parse_qs, urlparse as _up
            qs = parse_qs(_up(self.path).query)
            date_s = (qs.get("date") or [None])[0] or _date.today().isoformat()
            if not re.match(r"\d{4}-\d{2}-\d{2}$", date_s):
                self.send_error(400); return
            try:
                body = json.dumps(parse_home_data(date_s), ensure_ascii=False).encode("utf-8")
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

        elif path == "/api/contact/touch":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                name   = body.get("name", "").strip()
                if not name:
                    self.send_error(400); return
                today     = _dt.date.today()
                due_date  = (today + _dt.timedelta(days=7)).strftime("%m/%d/%Y")
                today_str = today.strftime("%m/%d/%Y")
                ok = update_contact_in_tracker(name, {
                    "status":       "🟢 Active",
                    "last_contact": today_str,
                    "last_touch":   f"Touched via Stone Dashboard ({today_str})",
                    "due":          due_date,
                }, clear_focus=True)
                self._respond(200, "application/json", json.dumps({"ok": ok}).encode())
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/api/contact/snooze":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                name   = body.get("name", "").strip()
                days   = int(body.get("days", 7))
                if not name:
                    self.send_error(400); return
                due_date = (_dt.date.today() + _dt.timedelta(days=days)).strftime("%m/%d/%Y")
                ok = update_contact_in_tracker(name, {"due": due_date})
                self._respond(200, "application/json", json.dumps({"ok": ok}).encode())
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/api/wrap":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                date_s = body.get("date", "")
                if not date_s or not re.match(r"\d{4}-\d{2}-\d{2}$", date_s):
                    self.send_error(400); return
                ok = write_wrap_reflection(date_s, {
                    "win":    body.get("win", ""),
                    "gap":    body.get("gap", ""),
                    "worked": body.get("worked", ""),
                    "better": body.get("better", ""),
                })
                self._respond(200, "application/json", json.dumps({"ok": ok}).encode())
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/api/pending-writes/clear":
            try:
                PENDING_WRITES.write_text("[]", encoding="utf-8")
                self._respond(200, "application/json", b'{"ok":true}')
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/api/draft-message":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                name   = body.get("name", "").strip()
                draft  = body.get("draft", "").strip()
                if not name:
                    self.send_error(400); return
                drafts_path = DASHBOARD / "outreach-drafts.json"
                try:
                    drafts = json.loads(drafts_path.read_text(encoding="utf-8")) if drafts_path.exists() else {}
                except Exception:
                    drafts = {}
                if draft:
                    drafts[name] = {"draft": draft, "saved": _dt.datetime.now().isoformat()}
                else:
                    drafts.pop(name, None)
                drafts_path.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
                self._respond(200, "application/json", b'{"ok":true}')
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/api/contact/note":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                name   = body.get("name", "").strip()
                note   = body.get("note", "").strip()
                action = body.get("action", "").strip()
                if not name:
                    self.send_error(400); return
                updates = {}
                if note:
                    updates["notes"] = note
                if action:
                    updates["next_action"] = action
                ok = update_contact_in_tracker(name, updates) if updates else True
                self._respond(200, "application/json", json.dumps({"ok": ok}).encode())
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        elif path == "/api/focus/sync":
            # Stone calls this at Plan My Day with the names that Notion marks Focus="Next".
            # Sets focus:true for those contacts, clears it for everyone else, updates focusToday.
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length))
                names  = [n.strip() for n in body.get("names", []) if isinstance(n, str) and n.strip()]
                clean  = lambda s: re.sub(r"[^\w\s''-]", "", s).strip().lower()
                focus_set = {clean(n) for n in names}
                raw  = _cat(CONTACTS_CACHE)
                data = json.loads(raw)
                contacts = data.get("contacts", [])
                synced = cleared = 0
                for c in contacts:
                    cn = clean(c.get("name", ""))
                    was = bool(c.get("focus"))
                    now = cn in focus_set
                    c["focus"] = now
                    if now and not was:
                        synced += 1
                    elif not now and was:
                        cleared += 1
                data["focusToday"] = names
                contacts.sort(key=lambda c: {"overdue": 0, "send": 1, "nurture": 2, "active": 3}.get(c["status"], 3))
                data["contacts"] = contacts
                payload = json.dumps(data, ensure_ascii=False, indent=2)
                CONTACTS_CACHE_LOCAL.write_text(payload, encoding="utf-8")
                try:
                    CONTACTS_CACHE_ICLOUD.write_text(payload, encoding="utf-8")
                except Exception:
                    pass
                self._respond(200, "application/json", json.dumps({"ok": True, "synced": synced, "cleared": cleared, "total_focus": len(names)}).encode())
            except Exception as e:
                self._respond(500, "application/json", json.dumps({"error": str(e)}).encode())

        else:
            self.send_error(404)

    def serve(self, filepath, content_type):
        try:
            if not filepath.exists():
                self.send_error(404); return
            # Use cat for iCloud paths to trigger download-on-demand
            if "Mobile Documents" in str(filepath):
                data = _cat(filepath, binary=True)
            else:
                data = filepath.read_bytes()
            self._respond(200, content_type, data)
        except FileNotFoundError:
            self.send_error(404)
        except Exception as e:
            import traceback; traceback.print_exc()
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
