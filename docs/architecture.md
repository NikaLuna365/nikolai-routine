# Architecture

## Big picture

```
                         ┌─────────────────────────────────────────┐
                         │  Notion: 🧠 Nikolai Context (private)     │
                         │  About Me · People · Projects · Topics ·  │
                         │  Obligations · Monitored · Excluded ·     │
                         │  Digests · feedback_log                   │
                         └───────────────▲───────────────┬──────────┘
                                  reads context     writes digest
                                         │               │
   Telegram (2 accts) ─┐                 │               │
   Calendar / Gmail ───┤  fetch     ┌────┴───────────────▼────┐
   Drive / GitHub  ────┘  + clean   │   Weekly Routine (Mon)   │── notify ──▶ Saved Messages
                          ──────────▶│  prompts/weekly.md       │              (Telegram)
   scripts/ (Telethon) ─────────────│  + analysis sub-agents   │
                                     └──────────────────────────┘
```

## Data pipeline (scripts/)

Run order, all parameterized via argparse + env (`.env`):

1. **`fetch_active_chats.py`** — lists top-N chats where *I* wrote ≥1 message in the
   period. Metadata only (no message bodies). → `chats.json`
2. **`fetch_messages.py`** — pulls message bodies for the selected chats, skipping
   excluded ones. Text only; skips service/media-only messages. Gentle rate limiting +
   FloodWait handling. → `messages.jsonl`
3. **`clean_messages.py`** — drops noise (sub-5-char messages, emoji-only, duplicate
   forwards, bots/auto-replies). → cleaned `*.jsonl`
4. **`extract_metadata.py`** — produces three structured artifacts for classification:
   `people_raw.json`, `topics_raw.json`, `money_raw.json` (money = factual flag only, no
   amounts).
5. **`transcribe_voice.py`** — stub (voice transcription intentionally disabled).

All artifacts are git-ignored. In production they live only on the runner (a server where
Telegram session strings are stored encrypted), never in this public repo.

> **Bootstrap note:** the bootstrap session pulled Telegram data through the authorized
> Telegram MCP connectors (no session strings in the sandbox) but produced the *same*
> `chats.json` / `messages.jsonl` schemas, so the cleaning/extraction scripts run
> identically. `fetch_*.py` are the Telethon production path for the scheduled weekly run.

## Notion knowledge base shape

`🧠 Nikolai Context` (root page) contains:

| Page | Kind | Purpose |
|---|---|---|
| `📖 About Me` | page | who Nikolai is — read for context each run |
| `👥 People` | database | Name, Telegram handle, Affiliation, Role, Last interaction context, Importance, Notes |
| `🏢 Projects` | database | Name, Type, Status, Stack, Key people (→People), Description, Links |
| `💡 Topics & Interests` | page | recurring themes + interest categories |
| `💰 Obligations` | page | "owed to me" / "I owe" — no sensitive amounts |
| `👀 Monitored Chats` | database | Chat name, Chat ID, Account, Priority, Why monitored, Last reviewed |
| `⛔ Excluded Chats` | database | Chat name, Chat ID, Account, Reason — **content never stored** |
| `📰 Digests` | page | weekly Routine writes sub-pages `YYYY-Www` here |

A `feedback_log` page (created/used by the weekly Routine) records topics Nikolai marked
as uninteresting so they stop being suggested.

## Weekly Routine flow (prompts/weekly.md)

1. Read `🧠 Nikolai Context` (people, projects, monitored, excluded, feedback_log).
2. Fetch last 7 days (`--days 7`) for monitored + active chats; clean + extract.
3. Spawn analysis sub-agents: **theme analyser**, **contact tracker**,
   **research suggester**, **missed-items scanner**.
4. Write a digest sub-page in `📰 Digests`; send a short link notification to Saved Messages.
5. Respect all hard constraints in `CLAUDE.md` (read-only Telegram, excluded chats,
   `[partial]` on FloodWait).
