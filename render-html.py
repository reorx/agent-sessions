#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic"]
# ///
"""
Render standard JSONL session files into terminal-style HTML pages.

Usage:
    uv run render-html.py session.jsonl [-o output.html]
"""

import argparse
import html
import json
import sys
from pathlib import Path

from models import SessionMeta, Message


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSS = SCRIPT_DIR / 'static' / 'conversation.css'
DEFAULT_JS = SCRIPT_DIR / 'static' / 'conversation.js'


def load_jsonl(path: Path) -> tuple[SessionMeta, list[Message]]:
    """Load a JSONL file and return (meta, messages)."""
    lines = path.read_text(encoding='utf-8').strip().split('\n')

    meta_data = json.loads(lines[0])
    meta = SessionMeta(**meta_data)

    messages = []
    for line in lines[1:]:
        if not line.strip():
            continue
        data = json.loads(line)
        messages.append(Message(**data))

    return meta, messages


def render_content(content: str) -> str:
    """Render content into HTML-safe text."""
    return html.escape(content)


def generate_html(
    meta: SessionMeta,
    messages: list[Message],
    max_line_len: int,
    css_url: str | None = None,
    js_url: str | None = None,
) -> str:
    """Generate the full HTML document."""
    msg_blocks = []
    nav_index = 0

    for msg in messages:
        if msg.role == 'header':
            content = render_content(msg.content)
            msg_blocks.append(f'<div class="message header"><pre>{content}</pre></div>')
            continue

        if msg.role == 'system':
            content = render_content(msg.content)
            msg_blocks.append(f'<div class="message system"><pre>{content}</pre></div>')
            continue

        role_class = msg.role
        extra_class = ' write-file' if msg.is_write_file else ''
        content = render_content(msg.content)

        if msg.is_navigable:
            msg_blocks.append(
                f'<div class="message {role_class}{extra_class}" data-nav="{nav_index}" tabindex="-1"><pre>{content}</pre></div>'
            )
            nav_index += 1
        else:
            msg_blocks.append(f'<div class="message {role_class}{extra_class}"><pre>{content}</pre></div>')

    messages_html = '\n'.join(msg_blocks)

    # CSS: external link or inline
    if css_url:
        css_block = f'<link rel="stylesheet" href="{html.escape(css_url, quote=True)}">'
    else:
        css_content = DEFAULT_CSS.read_text(encoding='utf-8')
        css_block = f'<style>\n{css_content}</style>'

    # Per-document dynamic style
    dynamic_css = f'<style>@media (min-width: 1040px) {{ .content {{ width: calc({max_line_len}ch + 4px); }} }}</style>'

    # JS: external src or inline
    if js_url:
        js_block = f'<script src="{html.escape(js_url, quote=True)}"></script>'
    else:
        js_content = DEFAULT_JS.read_text(encoding='utf-8')
        js_block = f'<script>\n{js_content}</script>'

    title = html.escape(meta.title)
    description = html.escape(meta.description, quote=True)
    source = html.escape(meta.source)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(meta.title, quote=True)}">
<meta property="og:description" content="{description}">
<meta property="og:site_name" content="Agent Sessions">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{html.escape(meta.title, quote=True)}">
<meta name="twitter:description" content="{description}">
{css_block}
{dynamic_css}
</head>
<body>

<div class="terminal-window">
    <div class="title-bar">
        <div class="dots">
            <div class="dot red"></div>
            <div class="dot yellow"></div>
            <div class="dot green"></div>
        </div>
        <div class="title">{source}</div>
    </div>
    <div class="content" id="content">
        <div class="inline-title">{source}</div>
        {messages_html}
    </div>
</div>

<div class="nav-hint" id="navHint">
    <kbd>j</kbd><kbd>k</kbd> or <kbd>↑</kbd><kbd>↓</kbd> navigate &nbsp; <kbd>click</kbd> focus
</div>

{js_block}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description='Render standard JSONL to HTML')
    parser.add_argument('input', help='Input .jsonl file')
    parser.add_argument('-o', '--output', help='Output .html file (default: same name as input)')
    parser.add_argument('--css', help='URL/path to external CSS file (default: inline)')
    parser.add_argument('--js', help='URL/path to external JS file (default: inline)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'Error: {input_path} not found', file=sys.stderr)
        sys.exit(1)

    meta, messages = load_jsonl(input_path)

    # Compute max line length from all message content
    all_content = '\n'.join(msg.content for msg in messages)
    max_line_len = max((len(line) for line in all_content.split('\n')), default=80)

    output_html = generate_html(
        meta,
        messages,
        max_line_len,
        css_url=args.css,
        js_url=args.js,
    )

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.html')

    output_path.write_text(output_html, encoding='utf-8')
    print(f'Rendered {input_path} -> {output_path}')


if __name__ == '__main__':
    main()
