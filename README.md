# Stone Dashboard

Mobile web dashboard — a visual layer on top of the Second Brain. No new systems. Reads existing markdown files, surfaces the day in one view.

**Live:** https://newmediablends.github.io/stone-dashboard/

---

## What it does

- Auto-detects energy mode by time (Prime / Peak / Rebuild / Execute / Wrap) and switches the Home view accordingly
- Four tabs: Home, Day, People, Projects
- Narration input — type or speak to log entries (Web Speech API, no cost)
- Runs entirely in the browser. No server, no API calls, no subscriptions.

## Phases

| Phase | What | Status |
|---|---|---|
| 1 | Shell + design + energy modes + sample data | Done |
| 2 | File System Access — reads actual markdown files | Next |
| 3 | Real data rendering (daily note, network tracker, projects) | Upcoming |
| 4 | Narration writes back to daily note log | Upcoming |
| 5 | PWA manifest — full home screen app | Upcoming |

## Design reference

Paper file: **"Plan My Day - Dashboard UI"**
- v0 — original scrolling list
- v1 — native app with bottom nav (reference for future)
- v2 — mobile web with pill tabs (current build spec)

## Core constraint

This app is a visual layer only. It does not create or modify any Stone protocol, CLAUDE.md rule, PARA convention, or Plan My Day step. The system does not adapt to the app — the app adapts to the system.

## Updating

After editing `dashboard.html` in the Second Brain project folder:

```bash
cp "/path/to/AI Second Brain/1-Projects/Second Brain Dashboard — Mobile UI/dashboard.html" ~/stone-dashboard/index.html
cd ~/stone-dashboard
git add index.html
git commit -m "describe what changed"
git push
```

GitHub Pages redeploys in ~60 seconds.

## On iPhone

1. Open Safari → `newmediablends.github.io/stone-dashboard`
2. Share → Add to Home Screen → name it **Stone**
3. Opens full screen, no browser chrome
