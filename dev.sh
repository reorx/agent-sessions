#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PORT=8001

./build.sh

# Kill existing process on the port
PID=$(lsof -ti :"$PORT" 2>/dev/null) && kill "$PID" && echo "Killed existing process $PID on port $PORT"

# Start HTTP server in background
python -m http.server "$PORT" -d dist &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT
echo "Serving dist/ at http://localhost:$PORT (PID $SERVER_PID)"

# Watch for changes and rebuild
watchexec -e py,css,js,txt -w . -- ./build.sh
