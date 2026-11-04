#!/usr/bin/env python3
"""The one-page proof pack before an interview: check it holds only what the evidence supports.

    python3 proofpack.py check pack.json --source EVIDENCE.md

pack.json:
  {"job": "...", "stage": "...", "date": "...",
   "proofs": [{"claim": "I can build dashboards people use", "quote": "<words copied from EVIDENCE.md>"}] x3,
   "gaps": [{"gap": "no Power BI", "say": "an honest line on how you'd close it"}] x3,
   "stories": [{"name": "claims dashboard", "for": "a result with numbers"}] 3-5,
   "follow_ups": ["where did the 6 hours come from?", ...] x10,
   "plan": [{"minutes": 10, "do": "say the three proofs out loud"}, ...] totalling 30}

Each proof's quote must appear word for word in EVIDENCE.md (no source, no
claim). Gaps stay visible: three real ones, each with what to say. The plan is
30 minutes, the night before or the morning of. Idea from InterviewThread's
Interview Proof Pack (Wei Yu); none of its text is used.
"""

import argparse
import json
import re
import sys


def flat(s):
    return " ".join(re.sub(r"[*_`>#-]", " ", str(s)).lower().split())


def check(pack, evidence):
    out = []
    ev = flat(evidence)
    proofs = pack.get("proofs") or []
    if len(proofs) != 3:
        out.append(("FAIL", "proofs", "three strongest proofs (%d given)" % len(proofs)))
    for i, pr in enumerate(proofs, 1):
        q = flat(pr.get("quote", ""))
        if len(q) < 12:
            out.append(("FAIL", "proof %d" % i, "copy the supporting words from EVIDENCE.md"))
        elif q not in ev:
            out.append(("FAIL", "proof %d" % i, "the quote isn't in EVIDENCE.md: no source, no claim"))
    gaps = pack.get("gaps") or []
    if len(gaps) != 3:
        out.append(("FAIL", "gaps", "three real gaps, each with what to say (%d given)" % len(gaps)))
    for i, g in enumerate(gaps, 1):
        if not str(g.get("say", "")).strip():
            out.append(("FAIL", "gap %d" % i, "add an honest line to say about it"))
    n = len(pack.get("stories") or [])
    if not 3 <= n <= 5:
        out.append(("FAIL", "stories", "3 to 5 stories (%d given)" % n))
    n = len(pack.get("follow_ups") or [])
    if n != 10:
        out.append(("FAIL", "follow_ups", "ten likely follow-up questions (%d given)" % n))
    mins = sum(int(p.get("minutes", 0)) for p in pack.get("plan") or [])
    if mins != 30:
        out.append(("FAIL", "plan", "a 30-minute plan (%d minutes given)" % mins))
    if not any(r[0] == "FAIL" for r in out):
        out.append(("PASS", "proof pack", "3 proofs, 3 gaps, %d stories, 10 follow-ups, 30 minutes"
                    % len(pack.get("stories"))))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Check an interview proof pack against EVIDENCE.md.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("pack")
    c.add_argument("--source", required=True)
    a = p.parse_args(argv)
    res = check(json.load(open(a.pack, encoding="utf-8")), open(a.source, encoding="utf-8").read())
    for st, what, detail in res:
        print("%-4s %-11s %s" % (st, what, detail))
    return 1 if any(r[0] == "FAIL" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
