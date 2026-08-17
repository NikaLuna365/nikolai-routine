#!/usr/bin/env python3
"""Split a long digest into Telegram-sized chunks.

Reads text from --input (or stdin), splits on a character limit without
breaking mid-word, and prefers to cut on blank lines / markdown section
breaks ("---", "## ") so each chunk stays readable on its own. Writes
JSON array of chunks to stdout (or --output), for the caller to send
sequentially with a pause between them.

Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", help="path to text file; omit to read stdin")
    p.add_argument("--output", help="path to write JSON array; omit to print to stdout")
    p.add_argument("--limit", type=int, default=3500, help="max chars per chunk (default 3500)")
    return p.parse_args()


def split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text] if text.strip() else []

    # Prefer splitting on paragraph/section boundaries; fall back to
    # word boundaries; fall back to a hard cut only as a last resort.
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    def flush():
        nonlocal current
        if current.strip():
            chunks.append(current.strip("\n"))
        current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
            continue

        flush()
        if len(para) <= limit:
            current = para
            continue

        # Single paragraph longer than the limit: break on word boundaries.
        words = para.split(" ")
        line = ""
        for w in words:
            piece = f"{line} {w}" if line else w
            if len(piece) <= limit:
                line = piece
            else:
                if line:
                    chunks.append(line)
                # word itself longer than limit (rare) -> hard cut
                while len(w) > limit:
                    chunks.append(w[:limit])
                    w = w[limit:]
                line = w
        current = line

    flush()
    return chunks


def main() -> int:
    args = parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    chunks = split_text(text, args.limit)

    out = json.dumps(chunks, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)

    print(f"split into {len(chunks)} chunk(s), limit={args.limit}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
