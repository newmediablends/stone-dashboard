#!/bin/zsh
# Stone Dashboard — start server + optional Cloudflare tunnel
# Run once: bash ~/stone-dashboard/start.sh
# Auto-start: install com.stone.dashboard.plist as a LaunchAgent

DIR="$(cd "$(dirname "$0")" && pwd)"

# Kill anything already on port 3000
kill "$(lsof -ti:3000)" 2>/dev/null || true
sleep 0.5

cd "$DIR"
python3 server.py &
SERVER_PID=$!
IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
echo "Stone server → https://${IP}:3000  (PID ${SERVER_PID})"

# Optional: Cloudflare tunnel for anywhere access
if command -v cloudflared &>/dev/null; then
    cloudflared tunnel --url "https://localhost:3000" --no-tls-verify 2>&1 \
      | grep --line-buffered -E 'tunnel|https://[a-z]|error' &
    echo "Cloudflare tunnel started"
fi

wait
