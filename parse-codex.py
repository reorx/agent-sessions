#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic"]
# ///
"""
Parse Codex CLI exported .jsonl rollouts into standard JSONL format.

Usage:
    uv run parse-codex.py codex/raw/rollout-xxx.jsonl [-o output.jsonl]
    uv run parse-codex.py codex/raw/  # batch: all .jsonl files in directory
"""

import argparse
import json
import sys
from pathlib import Path

from models import SessionMeta, Message


def extract_message_text(content: list[dict]) -> str:
    """Extract text from a message content array."""
    parts = []
    for item in content:
        if item.get('type') in ('input_text', 'output_text'):
            parts.append(item['text'])
    return '\n\n'.join(parts)


def extract_title(items: list[dict]) -> str:
    """Extract title from the first user message."""
    for item in items:
        payload = item['payload']
        if payload.get('type') == 'message' and payload.get('role') == 'user':
            text = extract_message_text(payload.get('content', []))
            first_line = text.split('\n', 1)[0].strip()
            if len(first_line) > 80:
                return first_line[:77] + '...'
            return first_line
    return 'Codex Conversation'


def extract_description(items: list[dict]) -> str:
    """Extract description from the first assistant final_answer message."""
    for item in items:
        payload = item['payload']
        if (
            payload.get('type') == 'message'
            and payload.get('role') == 'assistant'
            and payload.get('phase') == 'final_answer'
        ):
            text = extract_message_text(payload.get('content', []))
            desc = ' '.join(text.split())
            if len(desc) > 200:
                return desc[:197] + '...'
            return desc
    # Fallback: first assistant message of any phase
    for item in items:
        payload = item['payload']
        if payload.get('type') == 'message' and payload.get('role') == 'assistant':
            text = extract_message_text(payload.get('content', []))
            desc = ' '.join(text.split())
            if len(desc) > 200:
                return desc[:197] + '...'
            return desc
    return 'A Codex conversation'


def format_function_call(payload: dict) -> str:
    """Format a function_call payload into readable text."""
    name = payload.get('name', '')
    args_str = payload.get('arguments', '{}')
    try:
        args = json.loads(args_str)
    except (json.JSONDecodeError, TypeError):
        args = {}

    if name == 'exec_command':
        cmd = args.get('cmd', args_str)
        workdir = args.get('workdir', '')
        if workdir:
            return f'$ cd {workdir} && {cmd}'
        return f'$ {cmd}'

    # Generic function call
    return f'{name}({args_str})'


def format_function_call_output(payload: dict) -> str:
    """Format a function_call_output payload."""
    return payload.get('output', '')


def format_custom_tool_call(payload: dict) -> str:
    """Format a custom_tool_call (e.g. apply_patch)."""
    name = payload.get('name', 'tool')
    input_text = payload.get('input', '')
    return f'{name}:\n{input_text}'


def format_custom_tool_call_output(payload: dict) -> str:
    """Format a custom_tool_call_output."""
    return payload.get('output', '')


def format_web_search(payload: dict) -> str:
    """Format a web_search_call."""
    action = payload.get('action', {})
    action_type = action.get('type', '')
    if action_type == 'search':
        queries = action.get('queries', [])
        query = queries[0] if queries else action.get('query', '')
        return f'[web search] {query}'
    elif action_type == 'open_page':
        return '[web search] opening page'
    return '[web search]'


def convert_file(input_path: Path, output_path: Path):
    """Convert a single Codex raw .jsonl to standard JSONL."""
    raw_lines = input_path.read_text(encoding='utf-8').strip().split('\n')

    # Parse all lines
    items = []
    for line in raw_lines:
        if not line.strip():
            continue
        items.append(json.loads(line))

    # Filter to response_items only (for message extraction)
    response_items = [i for i in items if i['type'] == 'response_item']

    title = extract_title(response_items)
    description = extract_description(response_items)

    meta = SessionMeta(
        title=title,
        description=description,
        agent='codex',
        source=input_path.stem,
    )

    lines_out = [meta.model_dump_json()]

    for item in items:
        top_type = item['type']
        payload = item.get('payload', {})
        payload_type = payload.get('type', '')

        # Only process response_item lines
        if top_type != 'response_item':
            continue

        if payload_type == 'message':
            role = payload.get('role', '')
            # Skip developer messages (system prompts)
            if role == 'developer':
                continue
            if role not in ('user', 'assistant'):
                continue

            content = extract_message_text(payload.get('content', []))
            if not content.strip():
                continue

            message = Message(
                role=role,
                content=content,
                is_navigable=True,
            )
            lines_out.append(message.model_dump_json())

        elif payload_type == 'function_call':
            content = format_function_call(payload)
            message = Message(
                role='assistant',
                content=content,
                is_navigable=False,
            )
            lines_out.append(message.model_dump_json())

        elif payload_type == 'function_call_output':
            content = format_function_call_output(payload)
            if not content.strip():
                continue
            message = Message(
                role='system',
                content=content,
            )
            lines_out.append(message.model_dump_json())

        elif payload_type == 'custom_tool_call':
            content = format_custom_tool_call(payload)
            is_write = payload.get('name', '') == 'apply_patch'
            message = Message(
                role='assistant',
                content=content,
                is_navigable=False,
                is_write_file=is_write,
            )
            lines_out.append(message.model_dump_json())

        elif payload_type == 'custom_tool_call_output':
            content = format_custom_tool_call_output(payload)
            if not content.strip():
                continue
            message = Message(
                role='system',
                content=content,
            )
            lines_out.append(message.model_dump_json())

        elif payload_type == 'web_search_call':
            content = format_web_search(payload)
            message = Message(
                role='assistant',
                content=content,
                is_navigable=False,
            )
            lines_out.append(message.model_dump_json())

        # Skip: reasoning (encrypted), other types

    output_path.write_text('\n'.join(lines_out) + '\n', encoding='utf-8')
    print(f'Parsed {input_path} -> {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Parse Codex raw .jsonl to standard JSONL')
    parser.add_argument('input', help='Input .jsonl file or directory containing .jsonl files')
    parser.add_argument('-o', '--output', help='Output .jsonl file (only for single file input)')
    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_dir():
        if args.output:
            print('Error: -o cannot be used with directory input', file=sys.stderr)
            sys.exit(1)
        jsonl_files = sorted(input_path.glob('*.jsonl'))
        if not jsonl_files:
            print(f'No .jsonl files found in {input_path}', file=sys.stderr)
            sys.exit(1)
        out_dir = input_path.parent
        for f in jsonl_files:
            convert_file(f, out_dir / f'{f.stem}.jsonl')
    elif input_path.is_file():
        if args.output:
            output_path = Path(args.output)
        else:
            # Input is already .jsonl, so default output goes to parent of raw/
            if input_path.parent.name == 'raw':
                out_dir = input_path.parent.parent
            else:
                out_dir = input_path.parent
            output_path = out_dir / f'{input_path.stem}.jsonl'
        if output_path.resolve() == input_path.resolve():
            print(
                'Error: output path is the same as input path. Use -o to specify a different output.', file=sys.stderr
            )
            sys.exit(1)
        convert_file(input_path, output_path)
    else:
        print(f'Error: {input_path} not found', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
