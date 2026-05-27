#!/usr/bin/env python3
"""Download text message bodies for the chats selected by fetch_active_chats.py.

Production (Telethon) path for the weekly Routine. Text only — stickers, voice,
and media without a caption are skipped, as are service messages (joins/leaves).
Gentle: sequential chats, pause between each, FloodWait retry, and a progress
file so a restart skips already-finished chats.

Env: same as fetch_active_chats.py (TELEGRAM_API_ID/HASH + per-account session).

Output (messages.jsonl, one JSON object per line):
  {chat_id, chat_title, account, message_id, date, from_id, from_name,
   is_me, is_forward, reply_to_id, text}
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
    p.add_argument("--chats", required=True, help="chats.json from fetch_active_chats.py")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--output", default="messages.jsonl")
    p.add_argument("--exclude", help="JSON file: list of chat_ids to skip")
    p.add_argument("--pause", type=float, default=1.5,
                   help="seconds to sleep between chats (default 1.5)")
    p.add_argument("--checkpoint-every", type=int, default=5,
                   help="persist progress every N chats (default 5)")
    return p.parse_args()


def load_id_list(path: str | None) -> set:
    if not path:
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("chat_ids", [])
    return {int(x) for x in data}


def sender_name(msg) -> str:
    s = getattr(msg, "sender", None)
    if s is None:
        return ""
    parts = [getattr(s, "first_name", None), getattr(s, "last_name", None)]
    name = " ".join(p for p in parts if p)
    return name or getattr(s, "title", None) or getattr(s, "username", None) or ""


def with_floodwait(fn, *args, **kwargs):
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

    with open(args.chats, encoding="utf-8") as f:
        chats = json.load(f)
    exclude = load_id_list(args.exclude)

    progress_path = args.output + ".progress.json"
    done: set = set()
    if os.path.exists(progress_path):
        with open(progress_path, encoding="utf-8") as f:
            done = {int(x) for x in json.load(f).get("done", [])}
        print(f"[resume] {len(done)} chats already done", file=sys.stderr)

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    # append mode so a resume keeps prior lines
    out = open(args.output, "a", encoding="utf-8")

    def save_progress():
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump({"done": sorted(done)}, f)

    # group chats by account so we use the right session for each
    by_account: dict[str, list] = {}
    for c in chats:
        by_account.setdefault(c.get("account", "personal"), []).append(c)

    processed = 0
    for account, account_chats in by_account.items():
        session = os.environ.get(f"{account.upper()}_TELEGRAM_SESSION_STRING")
        if not (api_id and api_hash and session):
            sys.exit(f"Missing creds for account '{account}' in env")

        with TelegramClient(StringSession(session), int(api_id), api_hash) as client:
            me = client.get_me()
            for chat in account_chats:
                cid = int(chat["chat_id"])
                if cid in exclude or cid in done:
                    continue

                def pull():
                    for msg in client.iter_messages(cid):
                        if msg.date < since:
                            break
                        if getattr(msg, "action", None) is not None:
                            continue  # service message
                        text = (msg.message or "").strip()
                        if not text:
                            continue  # sticker / voice / media w/o caption
                        out.write(json.dumps({
                            "chat_id": cid,
                            "chat_title": chat.get("title", ""),
                            "account": account,
                            "message_id": msg.id,
                            "date": msg.date.isoformat(),
                            "from_id": msg.sender_id,
                            "from_name": sender_name(msg),
                            "is_me": msg.sender_id == me.id,
                            "is_forward": msg.forward is not None,
                            "reply_to_id": msg.reply_to_msg_id,
                            "text": text,
                        }, ensure_ascii=False) + "\n")

                with_floodwait(pull)
                out.flush()
                done.add(cid)
                processed += 1
                if processed % args.checkpoint_every == 0:
                    save_progress()
                    print(f"[checkpoint] {processed} chats pulled", file=sys.stderr)
                time.sleep(args.pause)

    save_progress()
    out.close()
    print(f"Done. Pulled {processed} chats -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
