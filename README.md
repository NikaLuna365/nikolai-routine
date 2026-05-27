# nikolai-routine

A personal AI-assistant infrastructure. Every Monday a **weekly Routine** scans the
last 7 days of my context — both Telegram accounts, calendar, mail, Notion/n8n/GitHub
activity — and produces a digest: main themes, key contacts, research suggestions, and
"you missed this" items from chats I don't actively track.

This repo holds the **machinery**: data-preprocessing scripts, sub-agent definitions,
and the Routine prompts. The **knowledge base and all private context live in Notion**,
not here.

> 🔗 **Notion knowledge base:** _(link added after bootstrap — see `🧠 Nikolai Context`)_

## How it works (short)

1. `scripts/` fetch + clean + structure Telegram data (run on a server where Telegram
   session strings live; never in this public repo).
2. The weekly Routine (`prompts/weekly.md`) reads the Notion knowledge base for context,
   spawns analysis sub-agents, and writes a digest into Notion's `📰 Digests`.
3. A short notification with the digest link is sent to my Telegram **Saved Messages**.

See [`docs/architecture.md`](docs/architecture.md) for the full picture.

## Repo layout

```
nikolai-routine/
├── README.md            # this file
├── CLAUDE.md            # system instructions read by every Routine run
├── .env.example         # required env vars (copy to .env, never commit .env)
├── .gitignore           # ignores secrets AND all data artifacts
├── .claude/agents/      # sub-agent definitions for the weekly Routine
├── scripts/             # Python data-preprocessing (Telethon + cleaning)
│   └── requirements.txt
├── prompts/
│   ├── bootstrap.md     # the one-time setup prompt (for reproducibility)
│   └── weekly.md        # the recurring Monday Routine prompt
└── docs/
    └── architecture.md
```

## Forking for your own use

This is built around one person's context, but the structure generalizes:

1. Fork the repo. Create your own Notion workspace with the same page/database shapes
   (`docs/architecture.md` describes them).
2. Replace the "About Me" / context in `CLAUDE.md` with your own.
3. Fill `.env` from `.env.example` (your Telegram API creds + session strings).
4. Run the bootstrap flow (`prompts/bootstrap.md`) once to populate your knowledge base.
5. Schedule the weekly Routine (`prompts/weekly.md`).

## Disclaimer

**This repo is public; the context is not.** No chat content, contact names, real
chat IDs, or personal details are ever committed here — they live exclusively in the
private Notion workspace. All secrets are passed via environment variables (see
`.env.example`) and are git-ignored. Data artifacts produced by the scripts
(`*.jsonl`, `*_raw.json`, `chats.json`) are git-ignored for the same reason.
