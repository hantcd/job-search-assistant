#!/usr/bin/env python3
"""Interview answers and the story grid.

    python3 star.py check answer.txt          # Situation, Task, Action, Result, a number: one point each
    python3 star.py grid grid.json            # which common themes each story covers, and the gaps

check scores 0-5 and says which part is weak. Clues it looks for:
  Situation  when/where context: 'at', 'during', 'while', 'in my', a time or place
  Task       what was needed: 'needed to', 'my job was', 'goal', 'asked to', 'responsible for'
  Action     what *I* did: first-person verbs ('I built', 'I set up', 'I led'); 'we' alone is flagged
  Result     what changed: 'so', 'which', 'as a result', 'cut', 'raised', 'saved', 'won', 'led to'
  Number     any number or percentage in the result
Plus length: about 1-2 minutes spoken (150-300 words). The check is a prompt for
coaching, not a grade an interviewer uses. Adapted from hunter-skill (MIT).

grid.json: {"themes": [...optional, defaults below...], "stories": [{"name", "themes": [...]}]}
"""

import argparse
import json
import re
import sys

THEMES = ["a challenge", "a failure", "a conflict", "leadership", "feedback", "adaptability",
          "teamwork", "a result with numbers", "why this company"]

CLUES = {
    "situation": r"\b(at|during|while|when i was|in my (?:role|job|internship|final year|team)|last (?:year|summer)|in 20\d\d)\b",
    "task": r"\b(needed to|had to|my (?:job|task|goal|role) was|the goal|asked to|responsible for|the problem was|we needed)\b",
    "action": r"\bI (?:\w+ed|built|set up|led|wrote|made|ran|took|chose|decided|spoke|met|found|got|drew|began|began|did|put|sent|brought|taught|thought)\b",
    "result": r"\b(as a result|so that|which (?:meant|cut|saved|raised|led)|result was|led to|cut|raised|saved|reduced|increased|improved|won|grew|finished|delivered|launched|passed)\b",
}


def check(text):
    out = {}
    for part, pat in CLUES.items():
        out[part] = bool(re.search(pat, text, re.I if part != "action" else 0))
    out["number"] = bool(re.search(r"\d", text))
    words = len(re.findall(r"[A-Za-z0-9'’-]+", text))
    tips = []
    if not out["action"] and re.search(r"\bwe\b", text, re.I):
        tips.append("say what YOU did: 'I ...', not only 'we ...'")
    if not out["result"]:
        tips.append("end with what changed because of you")
    if not out["number"]:
        tips.append("add one true number (time saved, people, money, %)")
    if not out["situation"]:
        tips.append("one line of context first: where, when")
    if words < 150:
        tips.append("a little short (%d words); aim for 1-2 minutes" % words)
    elif words > 300:
        tips.append("long (%d words); cut the set-up, keep the action and result" % words)
    return sum(out.values()), out, tips


def grid(data):
    themes = data.get("themes") or THEMES
    stories = data.get("stories", [])
    cover = {t: [s["name"] for s in stories if t in s.get("themes", [])] for t in themes}
    gaps = [t for t, v in cover.items() if not v]
    thin = [t for t, v in cover.items() if len(v) == 1]
    return cover, gaps, thin


def main(argv=None):
    p = argparse.ArgumentParser(description="STAR check and story grid.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    g = sub.add_parser("grid")
    g.add_argument("file")
    a = p.parse_args(argv)
    if a.cmd == "check":
        score, parts, tips = check(open(a.file, encoding="utf-8").read())
        print("STAR check: %d/5  " % score + "  ".join("%s %s" % (k, "yes" if v else "no") for k, v in parts.items()))
        for t in tips:
            print("  - " + t)
        return 0
    cover, gaps, thin = grid(json.load(open(a.file, encoding="utf-8")))
    for t, names in cover.items():
        print("%-24s %s" % (t, ", ".join(names) or "-- GAP --"))
    if gaps:
        print("\nGaps: " + ", ".join(gaps) + ". Ask for a true story for each before the interview.")
    if thin:
        print("Only one story: " + ", ".join(thin) + ". A second helps when they ask for another example.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
