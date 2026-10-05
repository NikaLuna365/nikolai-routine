#!/usr/bin/env python3
"""Split a long text into Telegram-sized parts (default limit 3500 chars).

Splits on paragraph breaks first, then line breaks, then hard-cuts as a last
resort, so a part never exceeds the limit and never breaks mid-line when it
can be avoided.

Usage:
  split_message.py FILE [--limit 3500] [--out-dir DIR]
Writes DIR/part_01.txt, part_02.txt, ... and prints the part count.
With --out-dir omitted, prints a JSON list of parts to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def split_text(text: str, limit: int = 3500) -> list[str]:
    parts: list[str] = []
    cur = ""

    def flush() -> None:
        nonlocal cur
        if cur.strip():
            parts.append(cur.rstrip())
        cur = ""

    def add(chunk: str, sep: str) -> None:
        nonlocal cur
        if len(chunk) > limit:
            flush()
            for line in chunk.split("\n"):
                while len(line) > limit:
                    parts.append(line[:limit])
                    line = line[limit:]
                if len(cur) + len(line) + 1 > limit:
                    flush()
                cur += line + "\n"
            return
        if len(cur) + len(sep) + len(chunk) > limit:
            flush()
        cur += (sep if cur else "") + chunk

    for para in text.strip().split("\n\n"):
        add(para, "\n\n")
    flush()
    return parts


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--limit", type=int, default=3500)
    p.add_argument("--out-dir")
    args = p.parse_args()
    with open(args.file, encoding="utf-8") as f:
        parts = split_text(f.read(), args.limit)
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        for i, part in enumerate(parts, 1):
            with open(os.path.join(args.out_dir, f"part_{i:02d}.txt"), "w", encoding="utf-8") as f:
                f.write(part)
        print(len(parts))
    else:
        json.dump(parts, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
