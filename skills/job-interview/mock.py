#!/usr/bin/env python3
"""Mock interview reports: check one, and see progress across them.

    python3 mock.py check mock.json [--source EVIDENCE.md]
    python3 mock.py progress mock-1.json mock-2.json ...

mock.json:
  {"date": "2026-11-03", "job": "acme-junior-data-analyst", "round": "hiring manager",
   "mode": "real" | "practice", "pressure": false,
   "scores": {"structure": {"score": 4, "why": "..."}, "evidence": {...}, "fit": {...},
              "follow_ups": {...}, "delivery": {...}},
   "questions": [{"question": "...", "story": "claims dashboard", "held_to": 2, "score": 3,
                  "stronger": "a better opening line, from the person's evidence"}],
   "fixes": ["...", "...", "..."]}

check:    every dimension scored 1-5 with a reason; held_to (how many steps of
          the follow-up chain the answer held, 0-5) on each question; three
          fixes; a story used for 3+ questions flagged; with --source, any
          number in a 'stronger' line that isn't in EVIDENCE.md fails (coaching
          never invents a result).
progress: each dimension across mocks, oldest first, and the weakest one now.

The follow-up chain on a result: where the number comes from; how much was
down to the person; what would have happened otherwise; whether it holds
elsewhere; what exactly they did. Exits 1 on any FAIL.
"""

import argparse
import json
import re
import sys
from collections import Counter

DIMENSIONS = ("structure", "evidence", "fit", "follow_ups", "delivery")
NUMBER = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(%|percent|k\b|m\b|x\b)?", re.I)


def numbers(text):
    return {m.group(1).replace(",", "") for m in NUMBER.finditer(text or "")}


def check(mock, evidence=None):
    out = []
    scores = mock.get("scores") or {}
    for d in DIMENSIONS:
        s = scores.get(d) or {}
        v = s.get("score")
        if not isinstance(v, int) or not 1 <= v <= 5:
            out.append(("FAIL", d, "needs a score from 1 to 5"))
        elif not (s.get("why") or "").strip():
            out.append(("FAIL", d, "needs one line on why"))
    qs = mock.get("questions") or []
    if not qs:
        out.append(("FAIL", "questions", "no questions recorded"))
    for i, q in enumerate(qs, 1):
        h = q.get("held_to")
        if not isinstance(h, int) or not 0 <= h <= 5:
            out.append(("FAIL", "question %d" % i, "held_to: how many follow-up steps the answer held (0-5)"))
        if evidence is not None and q.get("stronger"):
            new = sorted(n for n in numbers(q["stronger"]) - numbers(evidence) if len(n.replace(".", "")) > 0)
            if new:
                out.append(("FAIL", "question %d" % i, "the stronger version uses %s, which isn't in EVIDENCE.md"
                            % ", ".join(new)))
    used = Counter((q.get("story") or "").strip().lower() for q in qs if q.get("story"))
    for story, n in used.items():
        if n >= 3:
            out.append(("WARN", "stories", "'%s' used for %d questions: interviewers notice a thin bank" % (story, n)))
    fixes = [f for f in mock.get("fixes") or [] if str(f).strip()]
    if len(fixes) != 3:
        out.append(("FAIL", "fixes", "three fixes, each naming a question and what to change (%d given)" % len(fixes)))
    if not any(r[0] == "FAIL" for r in out):
        total = sum(scores[d]["score"] for d in DIMENSIONS)
        weakest = min(DIMENSIONS, key=lambda d: scores[d]["score"])
        out.append(("PASS", "report", "%d/25; weakest: %s" % (total, weakest.replace("_", " "))))
    return out


def progress(mocks):
    mocks = sorted(mocks, key=lambda m: m.get("date", ""))
    lines = ["%-12s %s" % ("dimension", "  ".join(m.get("date", "?")[5:] for m in mocks))]
    for d in DIMENSIONS:
        row = [str(((m.get("scores") or {}).get(d) or {}).get("score", "-")) for m in mocks]
        lines.append("%-12s %s" % (d.replace("_", " "), "  ".join("%5s" % r for r in row)))
    last = (mocks[-1].get("scores") or {}) if mocks else {}
    scored = [d for d in DIMENSIONS if isinstance((last.get(d) or {}).get("score"), int)]
    weakest = min(scored, key=lambda d: last[d]["score"]) if scored else None
    return lines, weakest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("mock")
    c.add_argument("--source")
    g = sub.add_parser("progress")
    g.add_argument("mocks", nargs="+")
    a = p.parse_args(argv)
    if a.cmd == "check":
        mock = json.load(open(a.mock, encoding="utf-8"))
        ev = open(a.source, encoding="utf-8").read() if a.source else None
        res = check(mock, ev)
        for status, what, detail in res:
            print("%-4s %-12s %s" % (status, what, detail))
        return 1 if any(r[0] == "FAIL" for r in res) else 0
    lines, weakest = progress([json.load(open(f, encoding="utf-8")) for f in a.mocks])
    print("\n".join(lines))
    if weakest:
        print("practise next: %s" % weakest.replace("_", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
