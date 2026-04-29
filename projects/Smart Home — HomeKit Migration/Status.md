# Smart Home — HomeKit Migration — Status

**Last Updated:** 2026-04-29
**Current Phase:** Phase 1 — Inventory
**Status:** Not Started

---

## Current Phase Details

**Phase 1 — Inventory**
Goal: Document every device currently on the Pi + any Google/other devices not yet bridged.
Mike's action: List all Homebridge plugins installed and all smart home devices by room.
Output: feeds directly into Jerry's migration mapping.

---

## Active Next Steps

| # | Action | Owner | Priority |
|---|--------|-------|----------|
| 1 | List every Homebridge plugin installed on the Pi | Mike | First |
| 2 | List all smart home devices by room/type | Mike | First |
| 3 | Jerry produces HA setup guide + platform migration map | Jerry | After inventory |
| 4 | Install Docker on Mac Mini | Mike | Phase 2 |
| 5 | Adjust Mac Mini Energy Saver (prevent sleep) | Mike | Phase 2 |

---

## Blockers

None yet. Inventory is the unlocker.

---

## Phase Tracker

| Phase | Status |
|-------|--------|
| 1 — Inventory | Not Started |
| 2 — Install | Not Started |
| 3 — Configure | Not Started |
| 4 — Migrate | Not Started |
| 5 — Decommission | Not Started |

---

## Notes

- Google Nest API requires one-time Google Cloud project setup (free tier). Stone handles the guide.
- Mac Mini must stay awake 24/7 -- set Energy Saver to never sleep while plugged in.
- Pi should stay live and untouched until Phase 5 is fully verified.
