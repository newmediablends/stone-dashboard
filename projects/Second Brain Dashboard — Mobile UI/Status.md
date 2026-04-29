# Stone Dashboard — Status

**Last updated:** 2026-04-29
**Priority:** H
**Status:** In Progress — Session 10 complete; daily note reads fixed; Full Disk Access pending Mike action

---

## What's Live

| Feature | Status | Notes |
|---------|--------|-------|
| Shell + energy modes (all 5) | Done | Prime, Peak, Rebuild, Execute, Wrap |
| All 4 tabs | Done | Home, Day, People, Projects |
| Dark mode + theme toggle | Done | localStorage + auto system preference |
| Day navigation ‹/› | Done | Back/forward between daily notes |
| Real data parsing | Done | Handles ## Schedule / ## 10x Items / ## Log and Section 1/2/3 formats |
| Network Tracker → contacts + outreach | Done | Server-side parse via /api/contacts; People tab + Execute queue from real tracker |
| No-plan banner | Done | Amber notice when today's note missing |
| Local HTTPS server | Done | `python3 server.py` — auto-generates SSL cert |
| HTTP fallback (port 3001) | Done | No cert needed; all features except voice narration |
| Log write-back | Done | Narration bar POSTs to server → appended to iCloud daily note |
| 10x checkbox write-back | Done | Tap to toggle done/undone → writes back to daily note markdown |
| Real Projects tab | Done | Reads actual 1-Projects/ Status.md files |
| Favicon + apple-touch-icon | Done | Stone glyph, dark green, mint gradient |
| PWA manifest + icons | Done | Installable from Safari; manifest.json + icon-180.png + icon-512.png |
| Service worker (PWA) | Done | stone-v3; never caches HTML or /api/ or /daily/ endpoints |
| Auto-start on login | Done | StoneServer.app (compiled AppleScript) as Login Item; restarts on crash |
| Quick Hits in Day tab | Done | ## Quick Hits bullets parsed; Stone-owned items tagged mint |
| MASK Journal in Day tab | Done | M/A/S/K cards with prompt + response (or "Not yet answered") |
| No-cache headers | Done | All server responses include Cache-Control: no-cache, no-store |
| GitHub Pages (anywhere) | Done | `./sync.sh` to push synced files |
| Cloudflare Tunnel | Done | `./tunnel.sh` — no account needed, auto-installs cloudflared |
| Responsive sidebar nav | Done | Sidebar replaces tab bar at 768px+; Projects 2-col/3-col grid |
| Day tab 2-col at tablet | Done | Schedule left \| 10x+QH+MASK+Log right; `.day-cols` flex layout; mobile unchanged |
| Focus Sync endpoint | Done | `POST /api/focus/sync` — Stone passes Notion Focus="Next" names; server sets cache; dashboard auto-reflects |
| Focus Sync in Plan My Day | Done | CLAUDE.md: 4th parallel read queries Notion + POSTs to endpoint every session |
| focusToday mint dot | Done | Contacts in focusToday array show mint dot everywhere they appear |
| Overview mode | Done | 6th mode picker option (indigo); full-picture scan — schedule + 10x + focus contacts |
| Contact interactions everywhere | Done | showContactDetail() wired in Rebuild, Execute, Overview, and People tab |
| Draft message persistence | Done | Execute mode msg area is contenteditable; saves to outreach-drafts.json on blur |
| Contact note edits write-back | Done | Next Action + Notes editable in contact sheet; saves to contacts-cache.json |
| Pending-writes buffer | Done | Failed iCloud writes queue to pending-writes.json; Stone processes at next session |

---

## Session 10 — 2026-04-29 (what changed)

- **Bug fix — daily notes returning 500**: Root cause was macOS TCC restriction. `Python.app` (launchd server process) lacks Full Disk Access, so it cannot read `~/Library/Mobile Documents/` (iCloud Drive). Every `/daily/*.md` request returned 500 silently; dashboard fell back to hardcoded sample data. Contacts still loaded because they live in local `stone-dashboard/contacts-cache.json`.
- **Fix — serve local synced copies first**: Added `DAILY_LOCAL = DASHBOARD / "daily"` constant. GET handler now serves from `stone-dashboard/daily/` first, iCloud fallback only when local copy doesn't exist. Write-back functions (append_log, toggle_tenx, write_mask_response, write_wrap_reflection) read/write the same local path for immediate read-back after writes.
- **sync.sh run**: Apr 28 + Apr 29 daily notes pulled into `stone-dashboard/daily/`. GitHub Pages updated.
- **Pending**: System Settings → Privacy & Security → Full Disk Access → add `Python.app` at `/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app`. Eliminates local-copy dependency entirely.
- **Protocol**: sync.sh must run each Plan My Day after Stone writes today's note.

## Session 4 — 2026-04-27 (what changed)

- **Sliding pill indicator**: Tab-bar active state replaced with a JS-positioned `#tab-slider` div that animates between tabs via spring cubic-bezier (0.34, 1.56, 0.64, 1) — native iOS feel
- **Mode picker entrance animation**: Dropdown now scale+fades in from top-left origin (0.18s); no more snap
- **Content fade on tab switch**: `#content` fades opacity 0→1 on every tab change (120ms)
- **Overlay fade**: Contact sheet backdrop fades in/out (200ms) instead of snapping
- **Checkmark draw animation**: 10x toggle checkmark animates via stroke-dashoffset (220ms)
- **Contact sheet action buttons**: 4 actions below the contact info — Draft Message (→ execute mode + outreach queue), Mark Touched (→ logs + resets status), Add to Queue, Snooze 7 Days (→ removes from view)

## Session 5 — 2026-04-27 (what changed)

- **Projects tab — filter pills**: All / Active / Blocked / High Pri pills above the list; animated active state
- **Projects tab — visual signals**: Blocked cards get red border; slow/stale get amber border + amber dot; summary header shows "N slow" in amber
- **Projects tab — per-card actions**: Log Update (pre-fills mic input with project name), Mark Blocked / Unblock (toggles state + haptic)
- **Projects tab — expand/collapse**: H-priority always expanded; M/L start collapsed (one-line with chevron); tap to expand/collapse

## Session 9 — 2026-04-28 (what changed)

- **`POST /api/focus/sync` endpoint**: Stone calls this at Plan My Day with the names Notion has marked Focus="Next". Server sets `focus: true` for matched contacts, clears all others, updates `focusToday` array, writes both cache files (local + iCloud). Returns `{ok, synced, cleared, total_focus}`. Name matching is clean/normalized (strips punctuation, lowercased).
- **CLAUDE.md — Focus Sync as 4th parallel Step 1 read**: Plan My Day now queries Notion for Focus="Next" contacts and immediately POSTs names to `/api/focus/sync`. Runs every session, no confirmation needed. Dashboard People tab auto-surfaces Today's Focus at top.
- **Loop closed**: Notion is source of truth → Stone syncs to cache at Plan My Day → dashboard reflects it. No manual cache editing needed.

## Session 8 — 2026-04-28 (what changed)

- **Day tab 2-col at 768px+**: Schedule section in `day-col-1` (left, flex: 1, border-right); 10x Items + Quick Hits + MASK Journal + Log in `day-col-2` (right, flex: 1). `.day-cols` is `display: flex; align-items: start` at 768px+; transparent on mobile (no layout change). Faith anchor stays full-width above both columns.

## Session 7 — 2026-04-28 (what changed)

- **Sidebar nav at 768px+**: Left sidebar (220px tablet, 260px desktop) replaces bottom tab bar. Contains Stone wordmark, 4 nav items with icons, theme toggle + avatar at footer.
- **App layout switches to flex row at tablet**: Header, status-bar, and tab-bar hidden. `#main-col` wrapper takes remaining width as flex: 1.
- **Mobile unchanged**: `#main-col` uses `display: contents` on mobile — transparent wrapper, existing layout unaffected.
- **Projects tab 2-col at 768px+, 3-col at 1280px+**: Cards use `.proj-cards-wrap` CSS grid; no JS changes needed.
- **Theme toggle synced**: Both header and sidebar theme buttons share the same applyTheme() call; icons sync across both.
- **Sidebar active state**: `render()` syncs `.sb-item.active` on every tab switch, same as tab pills.

## Session 6 — 2026-04-28 (what changed)

- **TODAY'S FOCUS section in People tab**: New mint-labeled strip at the top of People tab renders contacts where `focus: true` in the cache. Appears above Overdue. Hidden when empty.
- **`focus` field added to contacts-cache.json**: 6 contacts flagged for Apr 28 — Jeff Mask, Jake Thompson (JT), Daniel O'Donnell, Sakina Groth, Matt Moss, Amy Dredge.
- **`nurture` status bucket**: New fourth status in People tab between Send and Active. Amber section header. `statusBadge()` updated to show amber "Nurture" pill. Sort key updated in `server.py`.
- **`av-amber` CSS class**: Added for nurture contact avatars when Stone sets it explicitly.
- **People tab bucketing fully segmented**: Overdue / Send / Nurture / Active — no longer a flat "Priority" catch-all.
- **Mark Touched already clears focus**: `clear_focus=True` was already wired in `/api/contact/touch` — no change needed.

### Stone's Plan My Day protocol (goes live next session)

Each Plan My Day, Stone:
1. Queries Notion for contacts with Focus = "Next"
2. Sets `focus: true` in contacts-cache.json for those contacts; clears all others
3. Writes cache before dashboard opens
4. Dashboard auto-surfaces Today's Focus at top of People tab

---

## Session 6 — 2026-04-28 (Implementation Note: Daily Focus + Notion View Sync)

### What changed in Notion

Three new views were added to the Network Tracker DB (`cc5179f8-7c9d-4f04-bd77-b9e5ec48ee60`):

| View | Filter | Sort | Purpose |
|------|--------|------|---------|
| Daily Focus | Focus = "Next" | Due ASC | Today's action set — Stone flags these each morning |
| Outreach Next | Status = "0 Needs Contact" | Priority + Due ASC | Cold/warm contacts ready for first or re-touch |
| Nurture Next | Status = "2 Nurturing" | Due ASC | Active relationships to maintain — don't let them go cold |

A `Focus` select field exists on each contact page. Stone sets it to "Next" on the contacts Mike should act on today. It gets cleared after action (Mark Touched in dashboard, or manual clear in Notion).

6 contacts flagged Focus: Next on Apr 28: Sakina Groth, Daniel O'Donnell, Matt Moss, Amy Dredge, JT/Jake Thompson, Jeff Mask.

---

### Gap: Dashboard doesn't reflect this yet

**Current state:** `contacts-cache.json` has no `focus` field. The People tab shows all contacts bucketed by `status` (overdue / send / active). There's no Daily Focus surface.

**What needs to change — 3 parts:**

**Part 1 — Add `focus` field to contacts-cache.json**

Each contact entry gains one new boolean:
```json
{
  "name": "Sakina Groth",
  "status": "active",
  "focus": true,
  ...
}
```
Default is `false` (omitted is fine). Stone sets `focus: true` during Plan My Day for any contact flagged Focus: Next in Notion, then writes the cache. Cleared to `false` after Mark Touched is tapped in the dashboard.

**Part 2 — Add "Daily Focus" section to People tab**

At the top of the People tab (above the overdue/send/active buckets), add a "Today's Focus" card strip:
- Shows only contacts where `focus === true`
- Each card is the same row format as existing contacts — name, action, due, av dot
- Header: "TODAY'S FOCUS" in mint caps, same style as existing section headers
- If focus list is empty, hide the section entirely (no empty state)
- Tap opens the same contact detail slide-up sheet with the 4 action buttons

This becomes the first thing Mike sees when he opens the People tab each morning.

**Part 3 — Add `nurture` as a valid status value**

Nurture Next in Notion maps to Status = "2 Nurturing". The cache currently uses `overdue / send / active`. Add `nurture` as a fourth status:
- `overdue` → red av dot, surfaced first
- `send` → Execute queue (outreach ready)
- `nurture` → Nurture Next bucket in People tab (below send, above active)
- `active` → standard active

Stone's job: when a contact's Notion status is "2 Nurturing," write `status: "nurture"` to the cache entry. The dashboard then surfaces them in the right bucket without any code changes to filtering logic — just a new CSS class and section header.

---

### Stone's role each Plan My Day

1. Query Notion for contacts with Focus = "Next" (or contacts Mike names during planning)
2. For each: set `focus: true` in contacts-cache.json
3. Clear `focus: true` from contacts NOT in today's set
4. Write cache back before dashboard opens
5. Dashboard auto-surfaces today's Focus list at top of People tab

This means the dashboard always reflects what Plan My Day decided — no manual dashboard edits needed.

---

### Implementation order (when this session is picked up)

1. Add `focus` field to contacts-cache.json schema and seed today's 6 contacts
2. Update `server.py` `/api/contacts` to pass `focus` through in the response
3. Add "TODAY'S FOCUS" section to `index.html` People tab — render above overdue bucket
4. Add `nurture` status handling to contact row rendering + section grouping
5. Update Mark Touched action to clear `focus: true` on that contact in cache (POST to server)
6. Update Session 5 "Next Up" table to reflect these as the actual next items

---

## Design Session — 2026-04-28 (Responsive Breakpoints in Paper.design)

Created 8 new artboards in Paper.design ("Plan My Day - Dashboard UI") — tablet and desktop variants of all 4 tabs.

**Tablet (768x1024px) — sidebar nav (220px) replaces tab bar:**
- Home: Intention + Next Up two-col → MASK full-width 4-card strip → Gym row → narration bar
- Day: faith anchor → Schedule | 10x Items + Log two-col
- People: Overdue + Priority | Active two-col contact list
- Projects: filter pills → 2-col card grid

**Desktop (1280x900px) — sidebar nav (260px), max-content layouts:**
- Home: hero row (greeting + Next Up card) → 3-col (Intention+Gym | MASK vertical | Quick Hits+narration)
- Day: faith anchor → 3-col (Schedule | 10x Items | Log+narration)
- People: 360px contact list panel + flex detail panel (split-pane — Jason Richards selected)
- Projects: 3-col card grid with per-card mini stat tiles

These artboards are the design spec for implementing responsive CSS breakpoints in `index.html`.

---

## Session 7 — 2026-04-28 (what changed)

- **Pending-writes buffer**: All iCloud write failures (log entries, 10x toggles, MASK responses) queue to `~/stone-dashboard/pending-writes.json` instead of silently dropping. `GET /api/pending-writes` returns queue; `POST /api/pending-writes/clear` wipes it after Stone processes.
- **Draft message persistence**: Execute mode message area is now `contenteditable`. Edits save on blur via `POST /api/draft-message` → `outreach-drafts.json`. Loaded from server at startup; shown as "Saved Draft" preview at top of contact sheet.
- **Contact note edits write-back**: Next Action and Notes in the contact detail sheet are editable textareas. "Save Notes / Next Action" button POSTs to `POST /api/contact/note` → updates `contacts-cache.json`.
- **write_mask_response fallback**: Now catches iCloud write errors and queues to pending-writes, matching append_log and toggle_tenx behavior.
- **Overview mode**: 6th option in mode picker (indigo theme, manual-only, no LIVE badge). Shows schedule + 10x items + Today's Focus contacts. Full-picture scan without switching to a specific energy mode.
- **Contact interactions everywhere**: `showContactDetail()` wired to all contact rows in Rebuild, Execute, Overview, and People tab — consistent sheet behavior throughout.
- **focusToday mint dot**: Contacts flagged in `focusToday` array show a mint dot next to their name anywhere they appear.

**Pending action (Mike):** System Settings → Privacy & Security → Full Disk Access → add `Python.app` at `/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app`. This gives the launchd server direct iCloud write access and eliminates the pending-writes queue entirely.

---

## Next Up

| Item | Owner | Notes |
|------|-------|-------|
| Full Disk Access — Python.app | Mike | System Settings → Privacy & Security → Full Disk Access → add Python.app at `/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app`. Eliminates pending-writes queue. |
| Voice narration on iPhone | Mike | AirDrop `cert.pem` to iPhone → Settings → General → VPN & Device Management → install → Certificate Trust Settings → full trust. Then HTTPS mic works. |
| Remote R/W research | Jerry | Task brief at `Team Inbox/task-stone-dashboard-remote-rw.md`. Evaluate Tailscale, persistent Cloudflare tunnel, hosted server options. Output to Staging. |
| Process pending-writes at session start | Stone | Stone checks `~/stone-dashboard/pending-writes.json` each Plan My Day; applies queued ops; clears file. Moot once Full Disk Access is granted. |

---

## Session 3 — 2026-04-27 (what changed)

- **Pull-to-refresh**: Removed 60s auto-poll; swipe-down from top of content triggers doRefresh() with mint spinner; SW bumped to v3
- **Desktop polish (Option A)**: `body` gets surface background on screens >500px; `#app` gets border + drop shadow + rounded corners — intentional device-frame look
- **Batch queue alert**: Server detects `## Priority Import Queue` section; amber card surfaces in People tab + Execute mode when 10+ contacts are due within 3 days
- **Contact detail slide-up**: Tap any contact row → sheet slides up with Last Touch, Next Action, Due, Notes; swipe down or tap overlay to dismiss
- **Server returns richer contact data**: `lastTouch` and `notes` now passed through `/api/contacts`

---

## Open / Next Session

| Item | Status | Notes |
|------|--------|-------|
| Voice narration on iPhone (cert trust) | Pending | Requires one-time AirDrop of cert.pem + Settings trust |
| GitHub Pages shows no contacts | Known gap | sync.sh excludes tracker (privacy); contacts only load on local server |

---

## How to Run

**Local HTTPS (live from iCloud, same WiFi — recommended):**
```bash
# Auto-starts on login via StoneServer.app (Login Item)
# Manual start: open ~/Applications/StoneServer.app
# iPhone (HTTPS, voice): https://192.168.68.91:3000
# iPhone (HTTP, no cert): http://192.168.68.91:3001
```

**GitHub Pages (anywhere, synced snapshot):**
```bash
cd ~/stone-dashboard && ./sync.sh
# iPhone: newmediablends.github.io/stone-dashboard
```

---

## Key Files

| File | Purpose |
|------|---------|
| `~/stone-dashboard/index.html` | Full dashboard app |
| `~/stone-dashboard/server.py` | Local HTTPS+HTTP server (reads + writes iCloud); /api/contacts endpoint |
| `~/stone-dashboard/sw.js` | Service worker v2; never caches HTML or live data |
| `~/stone-dashboard/manifest.json` | PWA manifest |
| `~/stone-dashboard/sync.sh` | Push markdown files to GitHub Pages |
| `~/stone-dashboard/StoneServer.app` | Login Item — auto-starts server at login |
| `~/stone-dashboard/tunnel.sh` | Cloudflare quick tunnel — anywhere access |
| `~/stone-dashboard/cert.pem` | SSL cert — AirDrop to iPhone once to enable voice |

**Repo:** github.com/newmediablends/stone-dashboard
**Live (GitHub Pages):** newmediablends.github.io/stone-dashboard
**Live (local HTTPS):** https://192.168.68.91:3000
**Live (local HTTP):** http://192.168.68.91:3001
