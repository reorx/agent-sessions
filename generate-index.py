#!/usr/bin/env python3
"""Generate index.html pages that list files in a directory."""

import argparse
import html
from pathlib import Path


def generate_index(directory: Path, title: str, base_path: str = '') -> str:
    """Generate an index.html listing all files (excluding index.html itself)."""
    entries = sorted(directory.iterdir())
    items = []
    for entry in entries:
        if entry.name == 'index.html':
            continue
        name = entry.name
        if entry.is_dir():
            name += '/'
        href = name
        items.append(f'        <li><a href="{html.escape(href)}">{html.escape(name)}</a></li>')

    items_html = '\n'.join(items)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
:root {{
    --bg: #0d1117;
    --fg: #e6edf3;
    --link: #58a6ff;
    --link-hover: #79c0ff;
    --border: #30363d;
    --font-mono: "Mononoki Nerd Font Mono", Hack, "Berkeley Mono", "JetBrains Mono", "Fira Code", "SF Mono", Menlo, Consolas, monospace;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    background: var(--bg);
    color: var(--fg);
    font-family: var(--font-mono);
    font-size: 14px;
    line-height: 1.6;
    padding: 24px;
    max-width: 800px;
    margin: 0 auto;
}}
h1 {{
    color: var(--fg);
    font-size: 18px;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}}
ul {{
    list-style: none;
}}
li {{
    padding: 4px 0;
}}
a {{
    color: var(--link);
    text-decoration: none;
}}
a:hover {{
    color: var(--link-hover);
    text-decoration: underline;
}}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<ul>
{items_html}
</ul>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description='Generate index.html for a directory')
    parser.add_argument('directory', help='Directory to index')
    parser.add_argument('-t', '--title', help='Page title (default: directory name)')
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f'Error: {directory} is not a directory')
        raise SystemExit(1)

    title = args.title or directory.name
    index_html = generate_index(directory, title)
    output = directory / 'index.html'
    output.write_text(index_html, encoding='utf-8')
    print(f'Written to {output}')


if __name__ == '__main__':
    main()
