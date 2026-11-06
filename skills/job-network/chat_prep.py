#!/usr/bin/env python3
"""Check the prep for an informational chat before the person goes in.

    python3 chat_prep.py check prep.md

The prep (David DeGenova's conversation-prep method, Post Grad Project; ideas
only, none of his text is used) has three parts:

  ## Research      what their profile shows from school to today, recent company
                  news (with its link and date), what the role involves
  ## Questions    4-5 specific questions, each under one of three headings:
                  ### Their story, ### The industry, ### Things you can do
  ## Close        one ask about next steps; for a job they've applied to, the
                  job-specific asks (what matters in the process, what to
                  highlight, may I come back with small questions, would you
                  look at a few core interview answers)

FAIL  fewer than 3 or more than 7 questions; no 'Things you can do' question; no
      closing ask; a request for a job or a referral in a first chat
WARN  only one question heading used; no dated company news with a link; a
      generic question ('tell me about yourself', 'what's it like?')
"""

import argparse
import re
import sys

BUCKETS = {"story": r"their story", "industry": r"the industry", "do": r"things you can do"}
JOB_ASK = re.compile(r"\b(?:get me (?:a|the) job|hire me|refer me|referral|give me a job|any (?:openings|jobs) for me)\b", re.I)
GENERIC = re.compile(r"tell me about yourself|what'?s it like\??$|what do you do\??$|any advice\??$", re.I)
NEWS = re.compile(r"https?://\S+.*\b(?:19|20)\d\d\b|\b(?:19|20)\d\d\b.*https?://\S+")


def sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^\s*(#{2,3})\s*(.+?)\s*$", line)
        if m:
            cur = m.group(2).lower()
            out.setdefault(cur, [])
            continue
        if cur is not None:
            out[cur].append(line)
    return out


def check(text):
    res = []

    def add(status, name, detail):
        res.append((status, name, detail))

    sec = sections(text)
    questions, used = [], set()
    for head, lines in sec.items():
        qs = [l.strip(" -*\t") for l in lines if l.strip().endswith("?")]
        for key, rx in BUCKETS.items():
            if re.search(rx, head):
                used |= {key} if qs else set()
                questions += qs
    n = len(questions)
    add("PASS" if 3 <= n <= 7 else "FAIL", "questions", "%d (prepare 4-5, under the three headings)" % n)
    add("PASS" if "do" in used else "FAIL", "things you can do",
        "at least one question on what the person can do next" if "do" not in used else "present")
    add("PASS" if len(used) >= 2 else "WARN", "range", "headings used: %s" % (", ".join(sorted(used)) or "none"))
    close = [l for h, ls in sec.items() if h.startswith("close") for l in ls if l.strip()]
    add("PASS" if close else "FAIL", "closing ask", "end with one ask about next steps")
    asks = [q for q in questions + close if JOB_ASK.search(q)]
    add("FAIL" if asks else "PASS", "no job or referral ask",
        ("a first chat asks for insight, not a job or referral: %r" % asks[0][:60]) if asks else "none")
    gen = [q for q in questions if GENERIC.search(q)]
    if gen:
        add("WARN", "specific", "generic question: %r; ask about something their profile or the company news shows" % gen[0][:60])
    research = "\n".join(l for h, ls in sec.items() if h.startswith("research") for l in ls)
    add("PASS" if NEWS.search(research) else "WARN", "company news", "recent company news with its link and date")
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description="Check an informational chat prep.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    a = p.parse_args(argv)
    res = check(open(a.file, encoding="utf-8").read())
    for status, name, detail in res:
        print("%-4s  %-22s %s" % (status, name, detail))
    return 1 if any(s == "FAIL" for s, _, _ in res) else 0


if __name__ == "__main__":
    sys.exit(main())
