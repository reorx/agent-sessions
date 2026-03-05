#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Convert Claude Code exported .txt conversations into a terminal-style HTML viewer.

Usage:
    uv run claude-export-to-html.py conversation.txt [-o output.html]
"""

import argparse
import html
import sys
from pathlib import Path


def parse_messages(text: str) -> list[dict]:
    """Parse the exported .txt into a list of messages.

    Each message dict has:
      - role: "user" | "assistant" | "system"
      - lines: list of raw text lines
    """
    lines = text.split('\n')
    messages: list[dict] = []
    current: dict | None = None
    header_done = False

    for line in lines:
        # Detect message starts
        if line.startswith('❯ '):
            header_done = True
            if current:
                messages.append(current)
            current = {'role': 'user', 'lines': [line]}
        elif line.startswith('⏺ '):
            header_done = True
            if current:
                messages.append(current)
            current = {'role': 'assistant', 'lines': [line]}
        elif line.startswith('✻ '):
            # System line (e.g. "Cogitated for 2m 22s", "Worked for 7m 51s")
            if current:
                messages.append(current)
            current = {'role': 'system', 'lines': [line]}
        elif current is not None:
            # Continuation line — belongs to current message
            # User continuation lines have leading spaces (typically 2)
            # Assistant continuation lines may also have leading spaces
            messages.append(current) if current['role'] == 'system' and line.strip() else None
            if current['role'] == 'system' and line.strip():
                current = None
                continue
            if current['role'] == 'system' and not line.strip():
                messages.append(current)
                current = None
                continue
            current['lines'].append(line)
        elif not header_done:
            # Header lines before any message — collect as header
            if messages and messages[0]['role'] == 'header':
                messages[0]['lines'].append(line)
            elif line.strip():
                messages.insert(0, {'role': 'header', 'lines': [line]})
            elif messages and messages[0]['role'] == 'header':
                messages[0]['lines'].append(line)

    if current:
        messages.append(current)

    return messages


def render_content(lines: list[str], role: str) -> str:
    """Render lines into HTML content, escaping and preserving whitespace."""
    # Join lines, trim trailing empty lines
    while lines and not lines[-1].strip():
        lines = lines[:-1]

    text = '\n'.join(lines)
    escaped = html.escape(text)
    return escaped


def extract_title(messages: list[dict]) -> str:
    """Extract a title from the first user message."""
    for msg in messages:
        if msg['role'] == 'user':
            # Strip the leading "❯ " prefix
            first_line = msg['lines'][0].strip()
            if first_line.startswith('❯ '):
                first_line = first_line[2:]
            if len(first_line) > 80:
                return first_line[:77] + '...'
            return first_line
    return 'Claude Conversation'


def extract_description(messages: list[dict]) -> str:
    """Extract a description from the first assistant message for OG meta."""
    for msg in messages:
        if msg['role'] == 'assistant':
            # Collect text lines, strip markers and leading whitespace
            text_parts = []
            for line in msg['lines']:
                stripped = line.strip()
                if stripped.startswith('⏺ '):
                    stripped = stripped[2:]
                if stripped:
                    text_parts.append(stripped)
            desc = ' '.join(text_parts)
            if len(desc) > 200:
                return desc[:197] + '...'
            return desc
    return 'A Claude Code conversation'


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSS = SCRIPT_DIR / 'static' / 'conversation.css'
DEFAULT_JS = SCRIPT_DIR / 'static' / 'conversation.js'


def generate_html(
    messages: list[dict],
    title: str,
    description: str,
    source_filename: str,
    max_line_len: int,
    css_url: str | None = None,
    js_url: str | None = None,
) -> str:
    """Generate the full HTML document."""
    msg_blocks = []
    nav_index = 0

    for msg in messages:
        if msg['role'] == 'header':
            content = render_content(msg['lines'], 'header')
            msg_blocks.append(f'<div class="message header"><pre>{content}</pre></div>')
            continue

        if msg['role'] == 'system':
            content = render_content(msg['lines'], 'system')
            msg_blocks.append(f'<div class="message system"><pre>{content}</pre></div>')
            continue

        role_class = msg['role']
        content = render_content(msg['lines'], msg['role'])

        msg_blocks.append(
            f'<div class="message {role_class}" data-nav="{nav_index}" tabindex="-1"><pre>{content}</pre></div>'
        )
        nav_index += 1

    messages_html = '\n'.join(msg_blocks)

    # CSS: external link or inline
    if css_url:
        css_block = f'<link rel="stylesheet" href="{html.escape(css_url, quote=True)}">'
    else:
        css_content = DEFAULT_CSS.read_text(encoding='utf-8')
        css_block = f'<style>\n{css_content}</style>'

    # Per-document dynamic style (content width depends on max_line_len)
    dynamic_css = f'<style>@media (min-width: 1040px) {{ .content {{ width: calc({max_line_len}ch + 4px); }} }}</style>'

    # JS: external src or inline
    if js_url:
        js_block = f'<script src="{html.escape(js_url, quote=True)}"></script>'
    else:
        js_content = DEFAULT_JS.read_text(encoding='utf-8')
        js_block = f'<script>\n{js_content}</script>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:site_name" content="Agent Sessions">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{html.escape(title, quote=True)}">
<meta name="twitter:description" content="{html.escape(description, quote=True)}">
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
        <div class="title">{html.escape(source_filename)}</div>
    </div>
    <div class="content" id="content">
        <div class="inline-title">{html.escape(source_filename)}</div>
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
    parser = argparse.ArgumentParser(description='Convert Claude Code exported .txt to HTML')
    parser.add_argument('input', help='Input .txt file')
    parser.add_argument('-o', '--output', help='Output .html file (default: same name as input)')
    parser.add_argument('--css', help='URL/path to external CSS file (default: inline from static/conversation.css)')
    parser.add_argument('--js', help='URL/path to external JS file (default: inline from static/conversation.js)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'Error: {input_path} not found', file=sys.stderr)
        sys.exit(1)

    text = input_path.read_text(encoding='utf-8')
    max_line_len = max((len(line) for line in text.split('\n')), default=80)
    messages = parse_messages(text)

    title = extract_title(messages)
    description = extract_description(messages)
    source_filename = input_path.stem

    output_html = generate_html(
        messages,
        title,
        description,
        source_filename,
        max_line_len,
        css_url=args.css,
        js_url=args.js,
    )

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.html')

    output_path.write_text(output_html, encoding='utf-8')
    print(f'Written to {output_path}')


if __name__ == '__main__':
    main()
