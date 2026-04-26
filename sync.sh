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

# ---- Network Tracker ----
TRACKER="$BRAIN/3-Resources/Network-Tracker.md"
if [ -f "$TRACKER" ]; then
  cp "$TRACKER" "$DAILY_OUT/Network-Tracker.md"
  echo "  Network Tracker synced"
else
  echo "  Network Tracker not found — skipping"
fi

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
