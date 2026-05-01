# Stone Dashboard

Mobile web dashboard — a visual layer on top of the Second Brain. No new systems. Reads existing markdown files, surfaces the day in one view.

**Live (anywhere):** https://newmediablends.github.io/stone-dashboard/
**Live (local, full read/write):** https://192.168.68.91:3000

---

## What it does

- Auto-detects energy mode by time (Prime / Peak / Rebuild / Execute / Wrap)
- Four tabs: Home, Day, People, Projects
- Narration input — type or speak to log entries (writes back to iCloud markdown)
- 10x checkboxes — tap to mark done, writes back to daily note
- MASK journal — tap to answer, saves to markdown
- Auto-refreshes every 60 seconds when on local server
- Installable as PWA (Add to Home Screen on iPhone)

## Auto-start setup (one-time)

The server starts automatically at login via `~/Applications/StoneServer.app` (Login Item).

To verify it's set up:
- System Settings → General → Login Items → should see "StoneServer"

To start it manually now:
```bash
open ~/Applications/StoneServer.app
```

To start with Cloudflare tunnel (anywhere access):
```bash
cd ~/stone-dashboard && ./tunnel.sh
```

## What's running where

| Context | URL | Writes? | Notes |
|---------|-----|---------|-------|
| Local WiFi — HTTP (recommended for iPhone) | http://[your-ip]:3001 | Yes | No voice narration |
| Local WiFi — HTTPS | https://[your-ip]:3000 | Yes | Cert must be trusted on device |
| Cloudflare tunnel | tunnel URL | Yes | Anywhere access |
| GitHub Pages (anywhere, synced) | newmediablends.github.io/stone-dashboard | No | Read-only snapshot |

## On iPhone — install as PWA

**Local — HTTP (recommended, no cert setup):**
1. On same WiFi: open Safari → `http://192.168.68.91:3001`
2. Share → Add to Home Screen → name it **Stone**
3. Full read/write. No voice narration on the mic button (Web Speech requires HTTPS).

**Local — HTTPS (only if you want iPhone voice narration):**
1. AirDrop `~/stone-dashboard/cert.pem` to the iPhone
2. iPhone: Settings → General → VPN & Device Management → install the profile
3. Settings → General → About → Certificate Trust Settings → enable full trust for the cert
4. Open Safari → `https://192.168.68.91:3000` → Share → Add to Home Screen
5. Skipping the trust step gives you a blank screen in standalone PWA mode (no UI to bypass cert warning).

**Anywhere (GitHub Pages snapshot):**
1. Open Safari → `newmediablends.github.io/stone-dashboard`
2. Share → Add to Home Screen → name it **Stone**
3. Read-only, shows last synced data

## Syncing to GitHub Pages

```bash
cd ~/stone-dashboard && ./sync.sh
```

## Files

| File | Purpose |
|------|---------|
| `index.html` | Full dashboard app |
| `server.py` | Local HTTPS server (reads + writes iCloud) |
| `sw.js` | Service worker (offline support, PWA cache) |
| `manifest.json` | PWA manifest (install prompt, icons) |
| `icon-180.png` / `icon-512.png` | Home screen icons |
| `start.sh` | Start server + optional Cloudflare tunnel |
| `StoneServer.app` | Login Item (auto-start at login, full iCloud access) |
| `sync.sh` | Push markdown files to GitHub Pages |
| `tunnel.sh` | Cloudflare quick tunnel — anywhere access |
| `cert.pem` | SSL cert — AirDrop to iPhone once to enable voice |

**Repo:** github.com/newmediablends/stone-dashboard

## Core constraint

This app is a visual layer only. It does not create or modify any Stone protocol, CLAUDE.md rule, PARA convention, or Plan My Day step. The system does not adapt to the app — the app adapts to the system.
