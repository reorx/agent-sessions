#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

rm -rf dist
mkdir -p dist/claude-code
cp -r static dist/static

for f in claude-code/*.txt; do
    [ -f "$f" ] || continue
    basename="${f##*/}"
    name="${basename%.txt}"
    uv run claude-export-to-html.py "$f" -o "dist/claude-code/${name}.html" \
        --css ../static/conversation.css --js ../static/conversation.js
done

python generate-index.py dist/claude-code -t "claude-code"
python generate-index.py dist -t "agent-sessions"

echo "Build complete: dist/"
