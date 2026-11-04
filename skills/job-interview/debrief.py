#!/usr/bin/env python3
"""After a real interview: check the debrief, and add its questions to the question bank.

    python3 debrief.py check debrief.json
    python3 debrief.py bank debrief.json --bank question_bank.json

debrief.json, written within a day of the interview (5 minutes; a voice note is fine):
  {"date": "2026-11-10", "job": "acme-junior-data-analyst", "stage": "hiring manager",
   "interviewers": [{"name": "Siobhan Kelly", "role": "Analytics Manager"}],
   "questions": [{"q": "Tell me about a time a dashboard was wrong", "went": "good|ok|stuck",
                  "story": "claims dashboard", "note": "they pushed on how I checked the numbers"}],
   "stuck": "...", "went_well": "...", "promised": ["send the SQL sample"],
   "next_steps": "they'll be in touch by Friday", "gut": 3}

check: the parts that feed what comes next are there. The thank-you uses the
interviewers and what was promised; the next round's brief and the next mock
start from the 'stuck' questions; job-weekly reads the question bank.
bank: adds each question to question_bank.json (kept in the job list's
question_bank table): how often it has been asked, where, and how it went
last time. Questions asked twice or more are the ones to practise first.
Names stay in the person's own files; nothing here is shared.
"""

import argparse
import json
import re
import sys

WENT = ("good", "ok", "stuck")


def norm(q):
    q = re.sub(r"[^a-z0-9 ]+", " ", str(q).lower())
    q = re.sub(r"\b(can you|could you|please|tell me about|tell me|describe|give me|an example of|a time when|a time)\b", " ", q)
    return " ".join(q.split())


def check(d):
    out = []
    for f in ("date", "job", "stage"):
        if not str(d.get(f, "")).strip():
            out.append(("FAIL", f, "missing"))
    if not d.get("interviewers"):
        out.append(("FAIL", "interviewers", "who interviewed (name or role): the thank-you and next brief need it"))
    qs = d.get("questions") or []
    if not qs:
        out.append(("FAIL", "questions", "list the questions you remember, even roughly"))
    elif len(qs) < 3:
        out.append(("WARN", "questions", "only %d question(s): most interviews have more; add any you recall" % len(qs)))
    for i, q in enumerate(qs, 1):
        if q.get("went") not in WENT:
            out.append(("FAIL", "question %d" % i, "went: good, ok or stuck"))
    if any(q.get("went") == "stuck" for q in qs) and not str(d.get("stuck", "")).strip():
        out.append(("WARN", "stuck", "say where it went wrong, so the next mock starts there"))
    if "promised" not in d:
        out.append(("WARN", "promised", "anything you promised to send? (empty list if nothing)"))
    g = d.get("gut")
    if g is not None and not (isinstance(g, int) and 1 <= g <= 5):
        out.append(("FAIL", "gut", "a number from 1 to 5"))
    if not any(r[0] == "FAIL" for r in out):
        stuck = [q["q"] for q in qs if q.get("went") == "stuck"]
        out.append(("PASS", "debrief", "%d questions; practise next: %s" % (len(qs), "; ".join(stuck) or "nothing stuck")))
    return out


def bank(d, b):
    b = b or {"questions": []}
    idx = {norm(x["q"]): x for x in b["questions"]}
    new, again = [], []
    for q in d.get("questions", []):
        k = norm(q.get("q"))
        if not k:
            continue
        row = idx.get(k)
        where = {"date": d.get("date"), "job": d.get("job"), "stage": d.get("stage"), "went": q.get("went")}
        if row:
            row["times"] += 1
            row["asked"].append(where)
            again.append(row["q"])
        else:
            row = {"q": q.get("q"), "times": 1, "asked": [where]}
            b["questions"].append(row)
            idx[k] = row
            new.append(row["q"])
    b["questions"].sort(key=lambda r: (-r["times"], r["asked"][-1].get("went") != "stuck"))
    return b, new, again


def main(argv=None):
    p = argparse.ArgumentParser(description="Debrief a real interview and grow the question bank.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("debrief")
    k = sub.add_parser("bank")
    k.add_argument("debrief")
    k.add_argument("--bank", required=True)
    a = p.parse_args(argv)
    d = json.load(open(a.debrief, encoding="utf-8"))
    if a.cmd == "check":
        res = check(d)
        for st, what, detail in res:
            print("%-4s %-12s %s" % (st, what, detail))
        return 1 if any(r[0] == "FAIL" for r in res) else 0
    try:
        b = json.load(open(a.bank, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        b = None
    b, new, again = bank(d, b)
    with open(a.bank, "w", encoding="utf-8") as f:
        json.dump(b, f, indent=1, ensure_ascii=False)
    print("added %d new question(s); %d asked before: %s" % (len(new), len(again), "; ".join(again) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
