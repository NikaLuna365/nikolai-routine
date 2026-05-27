#!/usr/bin/env python3
"""Turn a cleaned messages JSONL into structured inputs for the classifiers.

Reads cleaned JSONL (from clean_messages.py) and writes three files:

  people_raw.json  - per sender (excluding me): message_count, the chats they
                     appear in, and a few sample sentences.
  topics_raw.json  - top unigrams + bigrams (stopwords removed), @mentions and
                     #hashtags by frequency.
  money_raw.json   - messages that mention money / obligations (regex flag only;
                     NO amounts are parsed). Raw text is included for the
                     obligations-scanner to read context — amounts must NOT be
                     propagated into Notion.

Pure stdlib. Russian + English aware (case-folding, basic stopwords).
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="cleaned messages JSONL")
    p.add_argument("--outdir", default=".", help="where to write the three JSONs")
    p.add_argument("--top-ngrams", type=int, default=80)
    p.add_argument("--samples-per-person", type=int, default=3)
    return p.parse_args()


STOPWORDS = {
    # ru
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
    "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
    "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет",
    "о", "из", "ему", "теперь", "когда", "даже", "ну", "вдруг", "ли", "если",
    "уже", "или", "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять",
    "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей", "может", "они",
    "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем", "была",
    "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
    "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем",
    "ним", "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее", "были",
    "куда", "зачем", "всех", "никогда", "можно", "при", "наконец", "два", "об",
    "другой", "хоть", "после", "над", "больше", "тот", "через", "эти", "нас",
    "про", "всего", "них", "какая", "много", "разве", "три", "эту", "моя", "впрочем",
    "хорошо", "свою", "этой", "перед", "иногда", "лучше", "чуть", "том", "нельзя",
    "такой", "им", "более", "всегда", "конечно", "всю", "между", "это", "да",
    "ок", "оке", "окей", "спс", "плиз", "пжл", "норм", "блин",
    # en
    "the", "a", "an", "and", "or", "but", "if", "to", "of", "in", "on", "for",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "these",
    "those", "with", "as", "at", "by", "from", "i", "you", "he", "she", "we",
    "they", "me", "my", "your", "our", "their", "so", "not", "no", "yes", "ok",
    "okay", "do", "did", "does", "have", "has", "had", "will", "would", "can",
    "could", "just", "what", "when", "where", "who", "how", "there", "here",
}

MONEY_RE = re.compile(
    r"(должен|должна|должны|долг|верн[уи]|верну|занял|заняла|займ|одолж|переведи|"
    r"перевёл|перевел|переведу|перевод|оплат|плат[ие]|счёт|счет|деньг|бабк|косар|"
    r"тыс|ك|invoice|owe|owes|paid|refund|transfer|\$|€|₽|₾|\beur\b|\busd\b|\bgel\b|"
    r"\bлар[иа]\b|\bруб|\bgel\b)",
    re.IGNORECASE,
)

WORD_RE = re.compile(r"[\w]+", re.UNICODE)
MENTION_RE = re.compile(r"@([A-Za-z][\w]{3,})")
HASHTAG_RE = re.compile(r"#([\w]{2,})")


def tokens(text: str) -> list[str]:
    out = []
    for w in WORD_RE.findall(text.lower()):
        if len(w) < 3 or w.isdigit() or w in STOPWORDS:
            continue
        out.append(w)
    return out


def main() -> int:
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    people: dict = defaultdict(lambda: {
        "from_id": None, "names": Counter(), "message_count": 0,
        "chats": {}, "sample_sentences": [],
    })
    unigrams: Counter = Counter()
    bigrams: Counter = Counter()
    mentions: Counter = Counter()
    hashtags: Counter = Counter()
    money: list = []

    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            text = (msg.get("text") or "").strip()

            # topics (from everyone, including me — reflects what's discussed)
            toks = tokens(text)
            unigrams.update(toks)
            bigrams.update(f"{a} {b}" for a, b in zip(toks, toks[1:]))
            mentions.update(m.lower() for m in MENTION_RE.findall(text))
            hashtags.update(h.lower() for h in HASHTAG_RE.findall(text))

            # money / obligations flag (factual only)
            if MONEY_RE.search(text):
                money.append({
                    "chat_id": msg.get("chat_id"),
                    "chat_title": msg.get("chat_title"),
                    "account": msg.get("account"),
                    "message_id": msg.get("message_id"),
                    "date": msg.get("date"),
                    "from_name": msg.get("from_name"),
                    "is_me": msg.get("is_me"),
                    "text": text,
                })

            # people (skip myself)
            if msg.get("is_me"):
                continue
            fid = msg.get("from_id")
            if fid is None:
                continue
            rec = people[fid]
            rec["from_id"] = fid
            if msg.get("from_name"):
                rec["names"][msg["from_name"]] += 1
            rec["message_count"] += 1
            cid = msg.get("chat_id")
            if cid is not None and cid not in rec["chats"]:
                rec["chats"][cid] = {
                    "chat_id": cid,
                    "chat_title": msg.get("chat_title"),
                    "account": msg.get("account"),
                }
            if len(rec["sample_sentences"]) < args.samples_per_person and len(text) >= 15:
                rec["sample_sentences"].append(text[:280])

    people_out = []
    for rec in people.values():
        name = rec["names"].most_common(1)[0][0] if rec["names"] else ""
        people_out.append({
            "from_id": rec["from_id"],
            "from_name": name,
            "message_count": rec["message_count"],
            "chats": list(rec["chats"].values()),
            "sample_sentences": rec["sample_sentences"],
        })
    people_out.sort(key=lambda r: r["message_count"], reverse=True)

    topics_out = {
        "unigrams": unigrams.most_common(args.top_ngrams),
        "bigrams": bigrams.most_common(args.top_ngrams),
        "mentions": mentions.most_common(args.top_ngrams),
        "hashtags": hashtags.most_common(args.top_ngrams),
    }

    def dump(name, obj):
        path = os.path.join(args.outdir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return path

    dump("people_raw.json", people_out)
    dump("topics_raw.json", topics_out)
    dump("money_raw.json", money)
    print(f"people={len(people_out)} money_flags={len(money)} "
          f"unigrams={len(unigrams)} -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
