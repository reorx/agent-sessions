#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic"]
# ///
"""
Parse Claude Code exported .txt conversations into standard JSONL format.

Usage:
    uv run parse-claude-code.py claude-code/raw/conversation.txt [-o output.jsonl]
    uv run parse-claude-code.py claude-code/raw/  # batch: all .txt files in directory
"""

import argparse
import re
import sys
from pathlib import Path

from models import SessionMeta, Message


WRITE_FILE_RE = re.compile(r'^⏺ (?:Update|Write|Create|Edit)\(.*\)')


def parse_messages(text: str) -> list[dict]:
    """Parse the exported .txt into a list of raw message dicts.

    Each dict has:
      - role: "user" | "assistant" | "system" | "header"
      - lines: list of raw text lines
    """
    lines = text.split('\n')
    messages: list[dict] = []
    current: dict | None = None
    header_done = False

    for line in lines:
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
            if current:
                messages.append(current)
            current = {'role': 'system', 'lines': [line]}
        elif current is not None:
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
            if messages and messages[0]['role'] == 'header':
                messages[0]['lines'].append(line)
            elif line.strip():
                messages.insert(0, {'role': 'header', 'lines': [line]})
            elif messages and messages[0]['role'] == 'header':
                messages[0]['lines'].append(line)

    if current:
        messages.append(current)

    return messages


def raw_to_content(lines: list[str]) -> str:
    """Convert raw lines to content string, preserving prefixes."""
    cleaned = list(lines)

    # Trim trailing empty lines
    while cleaned and not cleaned[-1].strip():
        cleaned = cleaned[:-1]

    return '\n'.join(cleaned)


def extract_title(messages: list[dict]) -> str:
    """Extract a title from the first user message."""
    for msg in messages:
        if msg['role'] == 'user':
            first_line = msg['lines'][0].strip()
            if first_line.startswith('❯ '):
                first_line = first_line[2:]
            if len(first_line) > 80:
                return first_line[:77] + '...'
            return first_line
    return 'Claude Conversation'


def extract_description(messages: list[dict]) -> str:
    """Extract a description from the first assistant message."""
    for msg in messages:
        if msg['role'] == 'assistant':
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


def is_write_file(content: str) -> bool:
    """Check if content represents a file write operation."""
    first_line = content.split('\n', 1)[0].strip()
    return bool(WRITE_FILE_RE.match(first_line))


def convert_file(input_path: Path, output_path: Path):
    """Convert a single .txt file to standard JSONL."""
    text = input_path.read_text(encoding='utf-8')
    raw_messages = parse_messages(text)

    title = extract_title(raw_messages)
    description = extract_description(raw_messages)

    meta = SessionMeta(
        title=title,
        description=description,
        agent='claude-code',
        source=input_path.stem,
    )

    lines_out = [meta.model_dump_json()]

    for msg in raw_messages:
        content = raw_to_content(msg['lines'])
        message = Message(
            role=msg['role'],
            content=content,
            is_navigable=msg['role'] in ('user', 'assistant'),
            is_write_file=msg['role'] == 'assistant' and is_write_file(content),
        )
        lines_out.append(message.model_dump_json())

    output_path.write_text('\n'.join(lines_out) + '\n', encoding='utf-8')
    print(f'Parsed {input_path} -> {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Parse Claude Code .txt to standard JSONL')
    parser.add_argument('input', help='Input .txt file or directory containing .txt files')
    parser.add_argument('-o', '--output', help='Output .jsonl file (only for single file input)')
    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_dir():
        if args.output:
            print('Error: -o cannot be used with directory input', file=sys.stderr)
            sys.exit(1)
        txt_files = sorted(input_path.glob('*.txt'))
        if not txt_files:
            print(f'No .txt files found in {input_path}', file=sys.stderr)
            sys.exit(1)
        # Output JSONL to parent directory of the raw/ directory
        out_dir = input_path.parent
        for f in txt_files:
            convert_file(f, out_dir / f'{f.stem}.jsonl')
    elif input_path.is_file():
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix('.jsonl')
        convert_file(input_path, output_path)
    else:
        print(f'Error: {input_path} not found', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
