# Weekly Routine

> Run every **Monday**. Analyze the last **7 days** of Nikolai's context across both
> Telegram accounts (+ calendar/mail signal) and produce a digest in Notion, then ping
> Saved Messages. Read [`CLAUDE.md`](../CLAUDE.md) first — its hard constraints are binding.

## Knowledge base (read at the start of every run)

Source of truth — the `🧠 Nikolai Context` workspace:
- Root: https://www.notion.so/36d2cfd3c7288129a56cca41ceb5bc3c
- 📖 About Me: https://www.notion.so/36d2cfd3c7288110b20cc473195dabc6
- 👥 People: https://www.notion.so/ebe20bb0a4274a4d83f981bf019cb139
- 🏢 Projects: https://www.notion.so/4448db9e2ac548579d2c5e57ba4510f9
- 👀 Monitored Chats: https://www.notion.so/33331984443d4a488761d1150b70a377
- ⛔ Excluded Chats: https://www.notion.so/9412fee2da7a401db962aa1b76f3603b
- 💡 Topics & Interests: https://www.notion.so/36d2cfd3c72881afa2d0cb781746092d
- 💰 Obligations: https://www.notion.so/36d2cfd3c728817dbaa8cd5099cc5c19
- 📰 Digests: https://www.notion.so/36d2cfd3c72881229937fb98150b3f3f
- 📝 feedback_log: https://www.notion.so/36d2cfd3c72881aba869d1c321611a89

## Hard constraints (see CLAUDE.md)

- Telegram is **read-only** + send only to **Saved Messages**. No other writes anywhere.
- **Never read Excluded Chats** content into any output. Load their `chat_id`s first and
  skip them everywhere.
- Use `scripts/` for raw data work, not hundreds of MCP calls in the main context.
- On FloodWait / rate-limit / timeout: produce a **`[partial]`** digest, never hammer.

## Step 1 — Load context

Fetch from Notion: About Me, the People DB (esp. Daily/Weekly importance), Projects (Active),
the full Monitored Chats list (with `chat_id` + priority), the Excluded Chats `chat_id` set,
and the feedback_log. Build an in-memory `exclude_ids` set and a `monitored` list.

## Step 2 — Fetch the last 7 days (gentle)

Window = last 7 days. Two execution modes:

**A. Server / Telethon (preferred when session strings are present in env):**
```
python3 scripts/fetch_active_chats.py --account personal --days 7 --output data/chats_p.json
python3 scripts/fetch_active_chats.py --account work     --days 7 --output data/chats_w.json
# merge chats_*.json, then:
python3 scripts/fetch_messages.py --chats data/chats_all.json --days 7 \
        --exclude data/exclude_ids.json --output data/messages.jsonl
```
The scripts already pace (`--pause`), retry FloodWait, and checkpoint. Also pull any
**Monitored** chat that isn't in the active set (you read it even if you don't post there).

**B. MCP connectors (when running without session strings):**
Fetch via `get_history` **gently — lessons from bootstrap**: go sequentially, ~8s pause
between chats, process in small chunks (≤4 chats), and **abort after 3 consecutive
failures** (the backend floods under bursts; `get_me` may still work while `get_history`
is rate-limited). Write the same `messages.jsonl` schema. **Redact** any secret-looking
strings (API keys, tokens, JWTs, passwords) to `[REDACTED]` before storing.

Either way: skip every `chat_id` in `exclude_ids`. Detect "me" by display name
(personal: `Nikolai Lu@`/`Nik_Ly`/`Lushok@`; work: `Nikolay Lu`/`NikolaiLu9`). Voice notes
are **not** transcribed (text only — `transcribe_voice.py` is a stub).

## Step 3 — Clean + extract

```
python3 scripts/clean_messages.py  --input data/messages.jsonl --output data/cleaned.jsonl
python3 scripts/extract_metadata.py --input data/cleaned.jsonl --outdir data
```
→ `people_raw.json`, `topics_raw.json`, `money_raw.json`.

## Step 4 — Analysis sub-agents (spawn in parallel)

Orchestrate; let the sub-agents do the reading. Definitions in [`.claude/agents/`](../.claude/agents/):
- **theme-analyser** — the week's main themes, ranked, tied to active Projects.
- **contact-tracker** — who was active, who went quiet, and **which threads are awaiting
  Nikolai's reply** (he wrote last vs they did). Cross-ref People importance.
- **research-suggester** — 2–4 things worth digging deeper, grounded in the week's topics.
  **Must cross-reference feedback_log** and never re-suggest anything in "Don't suggest again".
- **missed-items-scanner** — scan **Monitored Chats** (high→low priority) for items Nikolai
  likely missed: questions directed at him, decisions, deadlines, mentions of his projects.

Each returns compact structured findings (no raw message dumps, no secrets, nothing from
Excluded chats).

## Step 5 — Write the digest to Notion

Create a sub-page under 📰 Digests named by ISO week, e.g. **`2026-W23`**. Structure (Russian):
```
# Дайджест 2026-W23 (DD–DD месяц)
## 🔑 Главные темы недели
## 👥 Контакты — кто активен / где висит ответ
## ❗ Ты пропустил (из monitored-чатов)
## 💡 Research-предложения
## 💰 Обязательства (изменения за неделю, без сумм)
## ⚠️ Заметки / [partial] (если что-то не дочитали)
```
Keep it skimmable. Update `Last reviewed` (today) on the Monitored rows you scanned.

## Step 6 — Notify

Send a short message to **Saved Messages** (your own chat) on the personal account:
the digest title + a one-line highlight + the Notion link. Nothing else, nowhere else.

## Failure handling

If fetching is incomplete (FloodWait, outage, partial chunk), still write the digest from
what you have and tag it `[partial]`, listing which chats/accounts were not fully read so
next week can catch up. Never retry aggressively.

## Feedback loop

Before finalizing research-suggester output, re-read feedback_log:
- "Don't suggest again" → exclude those topics.
- "More of this" → bias toward them.
- "Format notes" → adjust the digest layout accordingly.
