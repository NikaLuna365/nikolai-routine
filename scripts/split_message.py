#!/usr/bin/env python3
"""Split a long text into Telegram-sized parts on paragraph boundaries.

Usage: split_message.py INPUT.txt [--limit 3500] [--out-dir DIR]
Without --out-dir, prints parts separated by a '=== PART n/N (len) ===' header.
"""
import argparse
import pathlib


def split_text(text: str, limit: int = 3500) -> list[str]:
    parts, cur = [], ""
    paras, carry = [], ""
    for para in text.split("\n\n"):  # glue short header-like paragraphs to the next one
        if len(para) < 40:
            carry = f"{carry}\n\n{para}" if carry else para
            continue
        paras.append(f"{carry}\n\n{para}" if carry else para)
        carry = ""
    if carry:
        paras.append(carry)
    for para in paras:
        while len(para) > limit:  # hard-split an oversized paragraph on a newline/space
            cut = max(para.rfind("\n", 0, limit), para.rfind(" ", 0, limit), limit // 2)
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(para[:cut].rstrip())
            para = para[cut:].lstrip()
        if len(cur) + len(para) + 2 > limit and cur:
            parts.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        parts.append(cur)
    return parts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--limit", type=int, default=3500)
    ap.add_argument("--out-dir")
    args = ap.parse_args()
    parts = split_text(pathlib.Path(args.input).read_text(encoding="utf-8"), args.limit)
    if args.out_dir:
        out = pathlib.Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(parts, 1):
            (out / f"part_{i:02d}.txt").write_text(p, encoding="utf-8")
    for i, p in enumerate(parts, 1):
        first = p.split("\n", 1)[0][:60]
        print(f"=== PART {i}/{len(parts)} ({len(p)} chars) :: {first}")


if __name__ == "__main__":
    main()
