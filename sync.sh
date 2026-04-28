#!/bin/bash
# sync.sh — push Second Brain content to Stone Dashboard
# Run from Terminal: cd ~/stone-dashboard && ./sync.sh
# Or from anywhere: ~/stone-dashboard/sync.sh

set -euo pipefail

BRAIN="/Users/mikebairdm4mini/Library/Mobile Documents/com~apple~CloudDocs/2-Areas/AI Second Brain"
REPO="$(cd "$(dirname "$0")" && pwd)"
DAILY_OUT="$REPO/daily"

echo "Stone sync starting..."

# ---- Daily notes ----
mkdir -p "$DAILY_OUT"
COUNT=0
while IFS= read -r -d '' f; do
  fname="$(basename "$f")"
  # Only copy date-named files (YYYY-MM-DD.md)
  if [[ "$fname" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$ ]]; then
    cp "$f" "$DAILY_OUT/$fname"
    COUNT=$((COUNT + 1))
  fi
done < <(find "$BRAIN/Daily" -name "*.md" -print0 2>/dev/null)
echo "  $COUNT daily notes synced"

# ---- Contacts cache (Notion-backed) ----
CONTACTS_CACHE="$BRAIN/Daily/contacts-cache.json"
if [ -f "$CONTACTS_CACHE" ]; then
  cp "$CONTACTS_CACHE" "$DAILY_OUT/contacts-cache.json"
  echo "  Contacts cache synced"
else
  echo "  contacts-cache.json not found — skipping"
fi

# ---- Project Status files ----
PROJECTS_OUT="$REPO/projects"
mkdir -p "$PROJECTS_OUT"
PROJ_COUNT=0
PROJ_INDEX=""
while IFS= read -r -d '' d; do
  pname="$(basename "$d")"
  status_file="$d/Status.md"
  if [ -f "$status_file" ]; then
    mkdir -p "$PROJECTS_OUT/$pname"
    cp "$status_file" "$PROJECTS_OUT/$pname/Status.md"
    PROJ_INDEX="$PROJ_INDEX$pname"$'\n'
    PROJ_COUNT=$((PROJ_COUNT + 1))
  fi
done < <(find "$BRAIN/1-Projects" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
printf '%s' "$PROJ_INDEX" > "$PROJECTS_OUT/index.txt"
echo "  $PROJ_COUNT project Status.md files synced"

# ---- Commit and push ----
cd "$REPO"
git add daily/
if git diff --staged --quiet; then
  echo "  Nothing changed — already up to date"
else
  CHANGED=$(git diff --staged --name-only | wc -l | tr -d ' ')
  git commit -m "sync $(date '+%Y-%m-%d %H:%M')"
  echo "  Committed $CHANGED file(s)"
  git push
  echo "  Pushed. Live on your iPhone in ~60 seconds."
fi
