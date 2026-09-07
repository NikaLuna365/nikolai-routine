#!/usr/bin/env python3
"""Split a long message into Telegram-safe chunks for sequential sending.

Splits on paragraph boundaries first, falling back to line and then hard
character splits, so a chunk never exceeds --limit characters and content
is never cut mid-word if a cleaner break is available nearby.

Usage:
  python3 split_message.py --input digest.txt --limit 3500
  cat digest.txt | python3 split_message.py --limit 3500

Output: prints one chunk per line to stdout, chunks separated by a line
containing exactly "-----8<-----" (so a caller can split on it), OR with
--json, prints a JSON array of chunk strings.
"""
from __future__ import annotations

import argparse
import json
import sys

SEP = "-----8<-----"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", help="path to text file; omit to read stdin")
    p.add_argument("--limit", type=int, default=3500)
    p.add_argument("--json", action="store_true", help="emit a JSON array instead")
    return p.parse_args()


def split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text] if text.strip() else []

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        # prefer splitting on a blank line (paragraph break), then a newline,
        # then a space -- always searching from the end of the window back.
        split_at = -1
        for sep in ("\n\n", "\n", " "):
            idx = window.rfind(sep)
            if idx > limit * 0.4:  # don't split too early in the window
                split_at = idx + len(sep)
                break
        if split_at == -1:
            split_at = limit  # hard cut, no good boundary found
        chunk = remaining[:split_at].rstrip("\n")
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].lstrip("\n")
    if remaining.strip():
        chunks.append(remaining)
    return chunks


def main() -> int:
    args = parse_args()
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    chunks = split_text(text, args.limit)

    if args.json:
        print(json.dumps(chunks, ensure_ascii=False, indent=2))
    else:
        print(f"\n{SEP}\n".join(chunks))

    print(f"[split_message] {len(chunks)} chunk(s), limit={args.limit}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
