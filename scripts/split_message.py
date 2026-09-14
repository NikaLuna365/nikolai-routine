#!/usr/bin/env python3
"""Split a long digest into Telegram-sized chunks.

Used by the weekly Routine (step 5b) to send the full digest as several
sequential messages instead of one link. Splits on paragraph/section
boundaries first (blank lines, then `---` rules, then single newlines),
falling back to a hard cut only if a single paragraph exceeds the limit.

Usage:
    python scripts/split_message.py --input digest.md --limit 3500
    cat digest.md | python scripts/split_message.py --limit 3500

Output: the parts, separated by a line containing exactly
"\x1e" (ASCII record separator) so a caller can split on it unambiguously
even if a part itself contains blank lines or "---".
"""
from __future__ import annotations

import argparse
import sys

PART_SEP = "\x1e"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", help="path to the text file; omit to read stdin")
    p.add_argument("--limit", type=int, default=3500,
                   help="max characters per part (default 3500)")
    return p.parse_args()


def split_message(text: str, limit: int) -> list[str]:
    """Greedily pack paragraphs into parts <= limit chars each."""
    text = text.strip("\n")
    if len(text) <= limit:
        return [text] if text else []

    # split into paragraphs on blank lines, keeping the separator info
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

        # candidate too big: flush what we have, then handle this paragraph alone
        flush()

        if len(para) <= limit:
            current = para
            continue

        # a single paragraph is itself too long -> split on single newlines
        lines = para.split("\n")
        for line in lines:
            candidate2 = f"{current}\n{line}" if current else line
            if len(candidate2) <= limit:
                current = candidate2
                continue
            flush()
            if len(line) <= limit:
                current = line
            else:
                # last resort: hard cut mid-line
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

    parts = split_message(text, args.limit)

    for i, part in enumerate(parts):
        if i > 0:
            sys.stdout.write(PART_SEP + "\n")
        sys.stdout.write(part)
        if not part.endswith("\n"):
            sys.stdout.write("\n")

    print(f"[{len(parts)} part(s), limit={args.limit}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
