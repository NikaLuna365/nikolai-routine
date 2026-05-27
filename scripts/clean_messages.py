#!/usr/bin/env python3
"""Strip noise from a messages JSONL dump.

Input JSONL (from fetch_messages.py) -> output JSONL, dropping:
  * messages shorter than --min-len characters ("+", "ок", "👍")
  * emoji-only / punctuation-only messages (no letter or digit)
  * duplicate forwards (same forwarded text seen before -> keep the first)
  * bot / auto-reply senders (name ends with "bot"), unless --keep-bots

Pure stdlib, so it runs anywhere — no Telegram access needed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--min-len", type=int, default=5)
    p.add_argument("--keep-bots", action="store_true",
                   help="do not drop messages from *bot senders")
    return p.parse_args()


def has_alnum(text: str) -> bool:
    return any(ch.isalnum() for ch in text)


def is_bot(name: str) -> bool:
    n = (name or "").strip().lower()
    return n.endswith("bot")


_WS = re.compile(r"\s+")


def norm(text: str) -> str:
    return _WS.sub(" ", text.strip().lower())


def main() -> int:
    args = parse_args()
    kept = dropped = 0
    seen_forwards: set[str] = set()

    with open(args.input, encoding="utf-8") as fin, \
         open(args.output, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            text = (msg.get("text") or "").strip()

            if len(text) < args.min_len:
                dropped += 1
                continue
            if not has_alnum(text):
                dropped += 1
                continue
            if not args.keep_bots and is_bot(msg.get("from_name", "")):
                dropped += 1
                continue
            if msg.get("is_forward"):
                key = norm(text)
                if key in seen_forwards:
                    dropped += 1
                    continue
                seen_forwards.add(key)

            fout.write(json.dumps(msg, ensure_ascii=False) + "\n")
            kept += 1

    print(f"kept {kept}, dropped {dropped} -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
