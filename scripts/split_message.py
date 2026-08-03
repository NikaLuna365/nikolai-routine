#!/usr/bin/env python3
"""Split a long digest into Telegram-sized chunks.

Splits on paragraph boundaries (blank lines) first, falling back to line
boundaries, so a chunk never cuts a sentence in half unless a single
paragraph alone exceeds the limit (rare for this use case).

Usage:
  python3 split_message.py --input digest.md --limit 3500 --output-dir parts/
Writes part_01.txt, part_02.txt, ... to --output-dir, and prints how many.
"""
from __future__ import annotations

import argparse
import os


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True)
    p.add_argument("--limit", type=int, default=3500)
    p.add_argument("--output-dir", required=True)
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
        # single paragraph itself exceeds limit: split on lines
        for line in para.split("\n"):
            candidate = f"{current}\n{line}" if current else line
            if len(candidate) <= limit:
                current = candidate
            else:
                flush()
                current = line[:limit]  # hard cut as last resort
    flush()
    return parts


def main() -> int:
    args = parse_args()
    with open(args.input, encoding="utf-8") as f:
        text = f.read()

    parts = split_text(text, args.limit)
    os.makedirs(args.output_dir, exist_ok=True)
    for i, part in enumerate(parts, start=1):
        path = os.path.join(args.output_dir, f"part_{i:02d}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(part)

    print(f"Split into {len(parts)} part(s) -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
