#!/usr/bin/env python3
"""
Stone Dashboard — local server
Serves the dashboard + reads live files from your Second Brain over WiFi.

Usage:
  cd ~/stone-dashboard && python3 server.py

Then open on iPhone:  http://[IP shown below]:3000
"""

import http.server
import os
import socket
from pathlib import Path

BRAIN    = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/2-Areas/AI Second Brain"
DASHBOARD = Path(__file__).parent
PORT     = 3000

DAILY_DIR   = BRAIN / "Daily"
TRACKER     = BRAIN / "3-Resources" / "Network-Tracker.md"
PROJECTS    = BRAIN / "1-Projects"

class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"

        if path in ("/", "/index.html"):
            self.serve(DASHBOARD / "index.html", "text/html")

        elif path == "/icon.svg":
            self.serve(DASHBOARD / "icon.svg", "image/svg+xml")

        elif path == "/daily/Network-Tracker.md":
            self.serve(TRACKER, "text/plain")

        elif path.startswith("/daily/"):
            fname = path[len("/daily/"):]
            # Only allow YYYY-MM-DD.md
            if len(fname) == 13 and fname.endswith(".md") and fname[:4].isdigit():
                self.serve(DAILY_DIR / fname, "text/plain")
            else:
                self.send_error(404)

        elif path.startswith("/projects/"):
            # /projects/Project-Name/Status.md
            parts = path[len("/projects/"):].split("/")
            if len(parts) == 2 and parts[1] == "Status.md":
                self.serve(PROJECTS / parts[0] / "Status.md", "text/plain")
            else:
                self.send_error(404)

        elif path == "/projects":
            # Return newline-separated list of project folder names
            try:
                names = [d.name for d in sorted(PROJECTS.iterdir()) if d.is_dir()]
                body = "\n".join(names).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_error(500)

        else:
            self.send_error(404)

    def serve(self, filepath, content_type):
        try:
            data = filepath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)
        except Exception as e:
            self.send_error(500)

    def log_message(self, fmt, *args):
        pass  # quiet — uncomment next line to debug
        # print(f"  {self.address_string()} {args[0]}")


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


if __name__ == "__main__":
    ip   = local_ip()
    host = socket.gethostname()
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)

    print(f"\nStone server running — reading live from Second Brain")
    print(f"  On this Mac:  http://localhost:{PORT}")
    print(f"  On iPhone:    http://{ip}:{PORT}")
    print(f"  Or try:       http://{host}.local:{PORT}")
    print(f"\n  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
