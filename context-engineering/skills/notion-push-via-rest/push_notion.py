#!/usr/bin/env python3
"""Convert markdown to Notion blocks and push as a child page."""
import json, re, sys, urllib.request, os
from pathlib import Path

TOKEN = Path.home().joinpath('.notion_token').read_text().strip()
PARENT = "34912c45-68fd-8096-a17c-e8c4600487d5"
MD_PATH = "/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/experiments/exp_cpp_match_engine/SP500_STATUS_2026-04-20.md"
TITLE = "SP500 M0→OB10 + GPU Matching Engine — 2026-04-20"
NOTION_BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def api(method, path, data=None):
    url = f"{NOTION_BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}")
        print(e.read().decode())
        raise


def rich_text(content, bold=False, code=False):
    """Return a Notion rich_text array from a single string.
    Notion caps rich_text element at 2000 chars, so split if needed."""
    if not content:
        return []
    out = []
    while content:
        chunk = content[:1900]
        content = content[1900:]
        out.append({
            "type": "text",
            "text": {"content": chunk},
            "annotations": {
                "bold": bold, "italic": False, "strikethrough": False,
                "underline": False, "code": code, "color": "default"
            }
        })
    return out


def inline_equation(expr):
    """Return a Notion rich_text segment for an inline equation."""
    return {"type": "equation", "equation": {"expression": expr}}


def parse_inline(text):
    """Parse **bold**, `code`, $inline math$, plain runs → list of rich_text segments."""
    segs = []
    i = 0
    while i < len(text):
        # inline math: $...$ (but not $$)
        if text[i] == '$' and (i == 0 or text[i-1] != '$') and not text[i:].startswith('$$'):
            m = re.match(r'\$([^$]+)\$', text[i:])
            if m and not m.group(0).startswith('$$'):
                segs.append(inline_equation(m.group(1)))
                i += m.end()
                continue
        # code spans
        m = re.match(r'`([^`]+)`', text[i:])
        if m:
            segs.extend(rich_text(m.group(1), code=True))
            i += m.end()
            continue
        # bold
        m = re.match(r'\*\*([^*]+)\*\*', text[i:])
        if m:
            segs.extend(rich_text(m.group(1), bold=True))
            i += m.end()
            continue
        # plain run up to next delimiter
        m = re.match(r'[^`*$]+', text[i:])
        if m:
            segs.extend(rich_text(m.group(0)))
            i += m.end()
            continue
        # stray * or ` or $ — emit literal
        segs.extend(rich_text(text[i]))
        i += 1
    return segs


def _make_equation_block(expr):
    """Build a Notion block-level equation block. Replaces align→aligned for KaTeX."""
    # Notion KaTeX supports \begin{aligned} but not \begin{align}
    expr = re.sub(r'\\begin\{align\*?\}', r'\\begin{aligned}', expr)
    expr = re.sub(r'\\end\{align\*?\}', r'\\end{aligned}', expr)
    expr = re.sub(r'\\begin\{gather\*?\}', r'\\begin{aligned}', expr)
    expr = re.sub(r'\\end\{gather\*?\}', r'\\end{aligned}', expr)
    return {"object": "block", "type": "equation", "equation": {"expression": expr.strip()}}


def md_to_blocks(md):
    blocks = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        # block equation: $$ ... $$ (opening $$ alone on a line or inline $$..$$)
        if line.strip() == '$$':
            i += 1
            math_lines = []
            while i < len(lines) and lines[i].strip() != '$$':
                math_lines.append(lines[i])
                i += 1
            i += 1  # skip closing $$
            blocks.append(_make_equation_block('\n'.join(math_lines)))
            continue

        # block equation: $$ ... $$ on a single line: $$expr$$
        m = re.match(r'^\$\$(.+)\$\$$', line.strip())
        if m:
            blocks.append(_make_equation_block(m.group(1)))
            i += 1
            continue

        # block equation: \begin{align} / \begin{equation} / \begin{gather}
        m = re.match(r'^\\begin\{(align\*?|equation\*?|gather\*?|aligned)\}', line.strip())
        if m:
            env = m.group(1)
            # collect until \end{env}
            math_lines = [line]
            i += 1
            end_pat = re.compile(r'\\end\{' + re.escape(env) + r'\}')
            while i < len(lines) and not end_pat.search(lines[i]):
                math_lines.append(lines[i])
                i += 1
            if i < len(lines):
                math_lines.append(lines[i])
                i += 1
            expr = '\n'.join(math_lines)
            blocks.append(_make_equation_block(expr))
            continue

        # block equation: \[ ... \]
        if line.strip() == r'\[':
            i += 1
            math_lines = []
            while i < len(lines) and lines[i].strip() != r'\]':
                math_lines.append(lines[i])
                i += 1
            i += 1
            blocks.append(_make_equation_block('\n'.join(math_lines)))
            continue

        # code fence
        if line.startswith('```'):
            lang = line[3:].strip() or 'plain text'
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": rich_text('\n'.join(code)),
                    "language": lang if lang in {"python","bash","c++","javascript","json","shell","plain text","markdown"} else "plain text",
                }
            })
            continue

        # heading
        m = re.match(r'^(#{1,3}) +(.+)$', line)
        if m:
            level = len(m.group(1))
            key = {1: "heading_1", 2: "heading_2", 3: "heading_3"}[level]
            blocks.append({
                "object": "block", "type": key,
                key: {"rich_text": parse_inline(m.group(2))}
            })
            i += 1
            continue

        # divider
        if line.strip() == '---':
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # table: line starts with | and next line is separator |---
        if line.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[-:| ]+\|$', lines[i+1]):
            header = [c.strip() for c in line.strip('|').split('|')]
            i += 2  # skip header + separator
            rows = [header]
            while i < len(lines) and lines[i].startswith('|'):
                row = [c.strip() for c in lines[i].strip('|').split('|')]
                rows.append(row)
                i += 1
            ncols = max(len(r) for r in rows)
            # normalize
            rows = [r + [''] * (ncols - len(r)) for r in rows]
            table_rows = []
            for r in rows:
                table_rows.append({
                    "object": "block", "type": "table_row",
                    "table_row": {"cells": [parse_inline(c) for c in r]}
                })
            blocks.append({
                "object": "block", "type": "table",
                "table": {
                    "table_width": ncols,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": table_rows
                }
            })
            continue

        # bullet list
        m = re.match(r'^[-*] +(.+)$', line)
        if m:
            blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": parse_inline(m.group(1))}
            })
            i += 1
            continue

        # numbered list
        m = re.match(r'^\d+\. +(.+)$', line)
        if m:
            blocks.append({
                "object": "block", "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": parse_inline(m.group(1))}
            })
            i += 1
            continue

        # blank line
        if not line.strip():
            i += 1
            continue

        # paragraph (merge consecutive non-blank non-special lines)
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,3} |```|\||[-*] |\d+\. |\$\$|\\begin\{|\\end\{|\\\[|\\\])', lines[i]) and lines[i].strip() != '---':
            para.append(lines[i])
            i += 1
        blocks.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": parse_inline(' '.join(para))}
        })

    return blocks


def main():
    md = Path(MD_PATH).read_text()
    blocks = md_to_blocks(md)
    print(f"converted {len(blocks)} blocks")

    # Create child page. Notion POST /v1/pages takes up to 100 children inline
    # We'll send first 100 with the page, then append the rest.
    first_batch = blocks[:100]
    create_body = {
        "parent": {"page_id": PARENT},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": TITLE}}]}
        },
        "children": first_batch,
    }
    created = api("POST", "/pages", create_body)
    child_id = created["id"]
    print(f"created child page {child_id}")
    print(f"url: {created.get('url')}")

    # Append remaining in batches of 100
    remaining = blocks[100:]
    batch_i = 0
    while remaining:
        batch = remaining[:100]
        remaining = remaining[100:]
        api("PATCH", f"/blocks/{child_id}/children", {"children": batch})
        batch_i += 1
        print(f"appended batch {batch_i} ({len(batch)} blocks)")

    print(f"\ndone. {len(blocks)} total blocks pushed to:")
    print(created.get('url'))


if __name__ == "__main__":
    main()
