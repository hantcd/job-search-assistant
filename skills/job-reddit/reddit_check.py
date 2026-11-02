#!/usr/bin/env python3
"""Check a Reddit reply draft before the person posts it, and the weekly cap.

    python3 reddit_check.py check draft.json [--previous replies.json]
    python3 reddit_check.py cap reddit.json --today 2026-10-27 [--max 3]

draft.json:   {"kind": "HELP" | "HIRING", "text": "...", "links_allowed": false}
replies.json: earlier replies, a list of strings or of rows with "draft"/"text"
reddit.json:  the job list's reddit rows: [{"url", "subreddit", "kind", "posted": "YYYY-MM-DD"}]

HELP replies (answering a question in the person's field) are 25-55 words,
never mention the job search, and carry no links. HIRING replies (to someone
hiring) are at most 90 words. Both: experience grammar, not advice grammar;
no stock openers; one hedge on any absolute claim; no stacked credentials;
wording not reused from earlier replies.

Adapted from reddit-automation (MIT, Copyright (c) 2026 doany.ai).
"""

import argparse
import datetime as dt
import json
import re
import sys

WORDS = {"HELP": (25, 55), "HIRING": (15, 90)}
ADVICE = re.compile(r"^\s*(you should|you need to|you must|i'?d just|just use|the best way|the answer is|"
                    r"simply|make sure you|always|never)\b", re.I)
ADVICE_ANY = re.compile(r"\b(you should|you need to|you must|the best way is)\b", re.I)
STOCK = re.compile(r"^\s*(great (question|post)|good question|as an? |hope this helps|i'?d be happy to)", re.I)
SEEKING = re.compile(r"\b(looking for (?:[\w-]+ ){0,3}(?:job|role|work|position|opportunit\w*)|"
                     r"open to (?:[\w-]+ )?(?:work|roles|opportunities)|"
                     r"hire me|my (cv|resume|résumé|portfolio)|dm me|job[- ]?hunting|job[- ]?seeking|"
                     r"available for (work|hire))\b", re.I)
LINK = re.compile(r"https?://|www\.|\]\(", re.I)
ABSOLUTE = re.compile(r"\b(always|never|best|the only|guaranteed|everyone|nobody|definitely)\b", re.I)
HEDGE = re.compile(r"\b(in my case|for me|i found|at least|in my experience|i think|for us|ymmv|"
                   r"what worked for me|i ran into|i had)\b", re.I)
CREDENTIAL = re.compile(r"\b(msc|bsc|phd|mba|certified|certification|years of experience|award[- ]winning|"
                        r"top \d+%|first[- ]class|distinction)\b", re.I)
HASHTAG = re.compile(r"(^|\s)#\w")


def words(text):
    return re.findall(r"[\w'’-]+", text)


def trigrams(text):
    w = [x.lower() for x in words(text)]
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}


def overlap(a, b):
    ta, tb = trigrams(a), trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def check(draft, previous=()):
    """Return a list of (PASS | WARN | FAIL, check, detail)."""
    kind = (draft.get("kind") or "").upper()
    text = draft.get("text") or ""
    out = []
    if kind not in WORDS:
        return [("FAIL", "kind", "kind must be HELP or HIRING, not %r" % kind)]
    lo, hi = WORDS[kind]
    n = len(words(text))
    out.append(("PASS" if lo <= n <= hi else "FAIL", "length", "%d words (%s: %d-%d)" % (n, kind, lo, hi)))

    first = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0] if text.strip() else ""
    if ADVICE.search(first) or STOCK.search(first):
        out.append(("FAIL", "opening", "opens with a verdict or stock phrase: %r; react to something the poster wrote" % first[:60]))
    else:
        out.append(("PASS", "opening", "reacts rather than lectures"))
    adv = ADVICE_ANY.findall(text)
    out.append(("WARN" if adv else "PASS", "experience grammar",
                "advice grammar: %s; say what worked for you instead" % ", ".join(sorted(set(a.lower() for a in adv)))
                if adv else "no 'you should'"))

    seeking = SEEKING.findall(text)
    if kind == "HELP" and seeking:
        out.append(("FAIL", "no pitch", "a HELP reply mentions the job search: %s" % ", ".join(sorted(set(s[0].lower() for s in seeking)))))
    elif kind == "HIRING" and not seeking:
        out.append(("WARN", "disclosure", "a HIRING reply should say plainly that the person is looking"))
    else:
        out.append(("PASS", "pitch", "pitch only where it belongs"))

    if LINK.search(text) and not draft.get("links_allowed"):
        out.append(("FAIL", "links", "a link, and this subreddit or thread doesn't invite them"))
    if HASHTAG.search(text):
        out.append(("WARN", "hashtags", "hashtags read as marketing on Reddit"))

    absolutes = ABSOLUTE.findall(text)
    if absolutes and not HEDGE.search(text):
        out.append(("WARN", "hedge", "absolute words (%s) with no hedge; add one ('at least in my case')"
                    % ", ".join(sorted(set(a.lower() for a in absolutes)))))
    creds = CREDENTIAL.findall(text)
    if len(creds) >= 2:
        out.append(("WARN", "credentials", "%d credentials stacked; one proof point is enough" % len(creds)))

    worst = max(((overlap(text, p), p) for p in previous), default=(0.0, ""))
    if worst[0] >= 0.3:
        out.append(("FAIL", "reused wording", "%.0f%% of its phrases are in an earlier reply: %r" % (worst[0] * 100, worst[1][:60])))
    elif previous:
        out.append(("PASS", "reused wording", "fresh wording"))
    return out


def cap(rows, today, maximum=3):
    """(ok, posted_in_last_7_days)."""
    start = today - dt.timedelta(days=6)
    n = 0
    for r in rows:
        try:
            d = dt.date.fromisoformat(str(r.get("posted") or "")[:10])
        except ValueError:
            continue
        if start <= d <= today:
            n += 1
    return n < maximum, n


def _texts(rows):
    out = []
    for r in rows:
        if isinstance(r, str):
            out.append(r)
        elif isinstance(r, dict):
            out.append(r.get("draft") or r.get("text") or "")
    return [t for t in out if t]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("draft")
    c.add_argument("--previous")
    k = sub.add_parser("cap")
    k.add_argument("rows")
    k.add_argument("--today")
    k.add_argument("--max", type=int, default=3)
    a = p.parse_args(argv)
    if a.cmd == "check":
        draft = json.load(open(a.draft, encoding="utf-8"))
        prev = _texts(json.load(open(a.previous, encoding="utf-8"))) if a.previous else []
        results = check(draft, prev)
        for status, name, detail in results:
            print("%-4s %-18s %s" % (status, name, detail))
        return 1 if any(r[0] == "FAIL" for r in results) else 0
    rows = json.load(open(a.rows, encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("reddit", [])
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    ok, n = cap(rows, today, a.max)
    print("%s %d of %d replies posted in the last 7 days" % ("OK" if ok else "BLOCK", n, a.max))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
