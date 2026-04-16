#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

rm -rf dist
mkdir -p dist/static
cp -r static/* dist/static/

# === Parse stage ===
echo "=== Parsing raw files ==="
[ "$(ls claude-code/raw/*.txt 2>/dev/null)" ] && uv run parse-claude-code.py claude-code/raw/
[ "$(ls codex/raw/*.jsonl 2>/dev/null)" ] && uv run parse-codex.py codex/raw/

# === Render stage ===
echo "=== Rendering HTML ==="
for agent_dir in claude-code codex; do
    mkdir -p "dist/$agent_dir"
    for f in "$agent_dir"/*.jsonl; do
        [ -f "$f" ] || continue
        name="$(basename "${f%.jsonl}")"
        uv run render-html.py "$f" -o "dist/$agent_dir/${name}.html" \
            --css ../static/conversation.css --js ../static/conversation.js
    done
done

# === Index stage ===
echo "=== Generating indexes ==="
for agent_dir in claude-code codex; do
    if [ -d "dist/$agent_dir" ] && [ "$(ls -A "dist/$agent_dir" 2>/dev/null)" ]; then
        python generate-index.py "dist/$agent_dir" -t "$agent_dir"
    fi
done
python generate-index.py dist -t "agent-sessions"

echo "Build complete: dist/"
