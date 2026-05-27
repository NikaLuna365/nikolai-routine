#!/usr/bin/env python3
"""Fetch the top-N Telegram chats where *I* wrote >= N messages in a period.

Metadata only — message bodies are NOT downloaded here (see fetch_messages.py).
This is the production (Telethon) path for the weekly Routine, which runs on a
server where the session strings live. Gentle by design: sequential dialogs,
a pause between each, FloodWait retry, and periodic checkpointing so a restart
loses nothing.

Env (loaded from .env in the working dir):
  TELEGRAM_API_ID, TELEGRAM_API_HASH
  PERSONAL_TELEGRAM_SESSION_STRING  (when --account personal)
  WORK_TELEGRAM_SESSION_STRING      (when --account work)

Output (chats.json): list of
  {chat_id, title, type, account, my_messages_count,
   total_messages_count, last_my_message_date}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--account", choices=["personal", "work"], required=True)
    p.add_argument("--days", type=int, default=90, help="look-back window (default 90)")
    p.add_argument("--top", type=int, default=30, help="keep this many chats (default 30)")
    p.add_argument("--min-my-messages", type=int, default=1,
                   help="drop chats where I wrote fewer than this (default 1)")
    p.add_argument("--output", default="chats.json")
    p.add_argument("--pause", type=float, default=1.5,
                   help="seconds to sleep between dialogs (default 1.5)")
    p.add_argument("--checkpoint-every", type=int, default=5,
                   help="flush partial output every N dialogs (default 5)")
    return p.parse_args()


def chat_type(entity) -> str:
    from telethon.tl.types import User, Chat, Channel
    if isinstance(entity, User):
        return "private"
    if isinstance(entity, Channel):
        return "channel" if getattr(entity, "broadcast", False) else "group"
    if isinstance(entity, Chat):
        return "group"
    return "unknown"


def with_floodwait(fn, *args, **kwargs):
    """Call fn, retrying on FloodWaitError (wait Retry-After + 5s)."""
    from telethon.errors import FloodWaitError
    while True:
        try:
            return fn(*args, **kwargs)
        except FloodWaitError as e:
            wait = int(getattr(e, "seconds", 0)) + 5
            print(f"[floodwait] sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)


def main() -> int:
    args = parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session = os.environ.get(f"{args.account.upper()}_TELEGRAM_SESSION_STRING")
    if not (api_id and api_hash and session):
        sys.exit("Missing TELEGRAM_API_ID / TELEGRAM_API_HASH / "
                 f"{args.account.upper()}_TELEGRAM_SESSION_STRING in env")

    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    results: list[dict] = []

    def flush():
        ranked = sorted(results, key=lambda c: c["my_messages_count"], reverse=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(ranked[: args.top], f, ensure_ascii=False, indent=2)

    with TelegramClient(StringSession(session), int(api_id), api_hash) as client:
        me = client.get_me()
        for i, dialog in enumerate(with_floodwait(client.get_dialogs), start=1):
            my_count = total = 0
            last_my = None

            def scan():
                nonlocal my_count, total, last_my
                for msg in client.iter_messages(dialog.id):
                    if msg.date < since:
                        break
                    total += 1
                    if msg.sender_id == me.id:
                        my_count += 1
                        if last_my is None:
                            last_my = msg.date

            with_floodwait(scan)

            if my_count >= args.min_my_messages:
                results.append({
                    "chat_id": dialog.id,
                    "title": dialog.name or "",
                    "type": chat_type(dialog.entity),
                    "account": args.account,
                    "my_messages_count": my_count,
                    "total_messages_count": total,
                    "last_my_message_date": last_my.isoformat() if last_my else None,
                })

            if i % args.checkpoint_every == 0:
                flush()
                print(f"[checkpoint] scanned {i} dialogs, kept {len(results)}",
                      file=sys.stderr)
            time.sleep(args.pause)

    flush()
    print(f"Wrote top {min(args.top, len(results))} of {len(results)} chats "
          f"to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
