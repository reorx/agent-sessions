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
import re
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
            first_line = msg['lines'][0].strip()
            # Truncate to reasonable length
            if len(first_line) > 80:
                return first_line[:77] + '...'
            return first_line
    return 'Claude Conversation'


def generate_html(messages: list[dict], title: str, source_filename: str, max_line_len: int) -> str:
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
    total_nav = nav_index

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
:root {{
    --bg: #0d1117;
    --terminal-bg: #161b22;
    --terminal-border: #30363d;
    --user-color: #9ca3af;
    --assistant-color: #e6edf3;
    --system-color: #484f58;
    --header-color: #58a6ff;
    --focus-border: #58a6ff;
    --focus-bg: #1c2333;
    --user-focus-border: #3fb950;
    --user-focus-bg: #1a2332;
    --scrollbar-thumb: #30363d;
    --scrollbar-track: transparent;
    --font-mono: "Mononoki Nerd Font Mono", Hack, "Berkeley Mono", "JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", Menlo, Consolas, "DejaVu Sans Mono", monospace;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

html {{
    font-size: 14px;
}}

body {{
    background: var(--bg);
    color: var(--assistant-color);
    font-family: var(--font-mono);
    line-height: 1.6;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 0;
}}

/* Scrollbar */
::-webkit-scrollbar {{
    width: 8px;
}}
::-webkit-scrollbar-track {{
    background: var(--scrollbar-track);
}}
::-webkit-scrollbar-thumb {{
    background: var(--scrollbar-thumb);
}}

/* Terminal window */
.terminal-window {{
    width: 100%;
    min-height: 100vh;
    background: var(--terminal-bg);
    position: relative;
}}

.content {{
    width: calc({max_line_len}ch + 4px);
}}

@media (min-width: 1040px) {{
    body {{
        padding: 24px;
    }}
    .terminal-window {{
        width: fit-content;
        min-height: auto;
        border: 1px solid var(--terminal-border);
        border-radius: 8px;
        overflow: hidden;
    }}
}}

/* Title bar */
.title-bar {{
    display: none;
    height: 38px;
    background: #1c2128;
    border-bottom: 1px solid var(--terminal-border);
    align-items: center;
    padding: 0 16px;
    gap: 8px;
    user-select: none;
    position: sticky;
    top: 0;
    z-index: 10;
}}

@media (min-width: 1040px) {{
    .title-bar {{
        display: flex;
    }}
}}

.title-bar .dots {{
    display: flex;
    gap: 6px;
}}
.title-bar .dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
}}
.title-bar .dot.red {{ background: #ff5f57; }}
.title-bar .dot.yellow {{ background: #febc2e; }}
.title-bar .dot.green {{ background: #28c840; }}

.title-bar .title {{
    flex: 1;
    text-align: center;
    color: var(--system-color);
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

/* Messages */
.message {{
    position: relative;
    padding: 0 1px;
    border: 1px solid transparent;
    transition: border-color 0.15s ease, background-color 0.15s ease;
    cursor: pointer;
    margin-bottom: 1em;
}}

.message:hover {{
    background: rgba(88, 166, 255, 0.04);
}}
.message.user:hover {{
    background: rgba(63, 185, 80, 0.04);
}}

.message.focused {{
    border-color: var(--focus-border);
    background: var(--focus-bg);
}}
.message.user.focused {{
    border-color: var(--user-focus-border);
    background: var(--user-focus-bg);
}}

.message pre {{
    font-family: inherit;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: inherit;
    line-height: 1em;
}}

/* Role-specific styles */
.message.user pre {{
    color: var(--user-color);
}}

.message.assistant pre {{
    color: var(--assistant-color);
}}

.message.system {{
    cursor: default;
}}
.message.system pre {{
    color: var(--system-color);
    font-size: 12px;
    font-style: italic;
}}

.message.header {{
    cursor: default;
}}
.message.header pre {{
    color: var(--header-color);
}}

/* Inline title (narrow screens) */
.inline-title {{
    color: var(--system-color);
    font-size: 12px;
    margin-bottom: 1em;
}}

@media (min-width: 1040px) {{
    .inline-title {{
        display: none;
    }}
}}

/* Navigation hint */
.nav-hint {{
    position: fixed;
    bottom: 16px;
    right: 16px;
    background: rgba(22, 27, 34, 0.9);
    border: 1px solid var(--terminal-border);
    padding: 8px 14px;
    font-size: 11px;
    color: var(--system-color);
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s ease;
    z-index: 100;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}}

.nav-hint.visible {{
    opacity: 1;
}}

.nav-hint kbd {{
    display: inline-block;
    padding: 1px 5px;
    font-family: inherit;
    font-size: 11px;
    background: var(--terminal-border);
    margin: 0 2px;
}}
</style>
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

<script>
(function() {{
    const navItems = document.querySelectorAll('.message[data-nav]');
    const navHint = document.getElementById('navHint');
    let currentIndex = -1;
    let hintTimer = null;

    function showHint() {{
        navHint.classList.add('visible');
        clearTimeout(hintTimer);
        hintTimer = setTimeout(() => navHint.classList.remove('visible'), 2000);
    }}

    function focusMessage(index) {{
        if (index < 0 || index >= navItems.length) return;
        navItems.forEach(el => el.classList.remove('focused'));
        currentIndex = index;
        navItems[currentIndex].classList.add('focused');
        navItems[currentIndex].scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
    }}

    document.addEventListener('keydown', function(e) {{
        if (e.key === 'j' || e.key === 'ArrowDown') {{
            e.preventDefault();
            if (currentIndex === -1) {{
                focusMessage(0);
            }} else {{
                focusMessage(currentIndex + 1);
            }}
            showHint();
        }} else if (e.key === 'k' || e.key === 'ArrowUp') {{
            e.preventDefault();
            if (currentIndex === -1) {{
                focusMessage(navItems.length - 1);
            }} else {{
                focusMessage(currentIndex - 1);
            }}
            showHint();
        }} else if (e.key === 'Escape') {{
            navItems.forEach(el => el.classList.remove('focused'));
            currentIndex = -1;
        }}
    }});

    navItems.forEach((el, idx) => {{
        el.addEventListener('click', function() {{
            focusMessage(idx);
        }});
    }});

    // Show hint briefly on load
    setTimeout(showHint, 500);
}})();
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description='Convert Claude Code exported .txt to HTML')
    parser.add_argument('input', help='Input .txt file')
    parser.add_argument('-o', '--output', help='Output .html file (default: same name as input)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'Error: {input_path} not found', file=sys.stderr)
        sys.exit(1)

    text = input_path.read_text(encoding='utf-8')
    max_line_len = max((len(line) for line in text.split('\n')), default=80)
    messages = parse_messages(text)

    title = extract_title(messages)
    source_filename = input_path.stem

    output_html = generate_html(messages, title, source_filename, max_line_len)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.html')

    output_path.write_text(output_html, encoding='utf-8')
    print(f'Written to {output_path}')


if __name__ == '__main__':
    main()
