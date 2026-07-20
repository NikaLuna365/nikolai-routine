#!/usr/bin/env python3
"""Split a long digest into Telegram-sized chunks.

Reads text (stdin or --input file), splits it into parts no longer than
--limit characters (default 3500), breaking on paragraph boundaries where
possible so sections don't get cut mid-sentence. Writes each part as its own
JSON string on a line to stdout (or --output), ready to send sequentially.

Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", help="path to text file (default: stdin)")
    p.add_argument("--output", help="path to write JSONL parts (default: stdout)")
    p.add_argument("--limit", type=int, default=3500)
    return p.parse_args()


def split_text(text: str, limit: int) -> list[str]:
    paragraphs = text.split("\n\n")
    parts: list[str] = []
    current = ""

    def flush():
        nonlocal current
        if current:
            parts.append(current.strip("\n"))
            current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para

        if len(candidate) <= limit:
            current = candidate
            continue

        # candidate too big: flush what we have, then handle this paragraph
        flush()
        if len(para) <= limit:
            current = para
            continue

        # single paragraph longer than limit: hard-split on line boundaries
        for line in para.split("\n"):
            piece = f"{current}\n{line}" if current else line
            if len(piece) <= limit:
                current = piece
            else:
                flush()
                # last resort: hard character split
                for i in range(0, len(line), limit):
                    chunk = line[i:i + limit]
                    if len(chunk) == limit:
                        parts.append(chunk)
                    else:
                        current = chunk

    flush()
    return parts


def main() -> int:
    args = parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    parts = split_text(text, args.limit)

    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        for part in parts:
            out.write(json.dumps(part, ensure_ascii=False) + "\n")
    finally:
        if args.output:
            out.close()

    print(f"split into {len(parts)} part(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
