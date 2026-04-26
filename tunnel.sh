#!/bin/bash
# tunnel.sh — expose Stone Dashboard publicly via Cloudflare
# No Cloudflare account needed. Gives a temporary https://*.trycloudflare.com URL.
# Works anywhere — not just home WiFi.
#
# Usage:
#   cd ~/stone-dashboard && ./tunnel.sh
#
# Requires the local server to be running first:
#   python3 server.py &

set -euo pipefail

# Install cloudflared if missing
if ! command -v cloudflared &> /dev/null; then
  echo "Installing cloudflared..."
  if command -v brew &> /dev/null; then
    brew install cloudflare/cloudflare/cloudflared
  else
    echo "Homebrew not found. Install cloudflared manually:"
    echo "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    exit 1
  fi
fi

# Check server is running
if ! curl -sk https://localhost:3000/ > /dev/null 2>&1; then
  echo "Local server not running. Starting it..."
  cd "$(dirname "$0")"
  python3 server.py &
  sleep 3
fi

echo ""
echo "Stone Tunnel — starting..."
echo "Copy the https://...trycloudflare.com URL below and open it on any device."
echo "The URL changes each run. Ctrl+C to stop."
echo ""

cloudflared tunnel --url https://localhost:3000
