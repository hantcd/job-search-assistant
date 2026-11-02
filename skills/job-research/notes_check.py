#!/usr/bin/env python3
"""Check company notes before anyone relies on them: every finding labelled, linked and dated.

    python3 notes_check.py acme.md [--today 2026-10-16]

A finding is a bullet line ('- ' or '* '). Each needs:
  a label: OFFICIAL, SEVERAL REPORTS, ONE REPORT or GUESS
  a link (http...) unless it's a GUESS
  a date (YYYY-MM or YYYY-MM-DD)
Notes older than 90 days (the 'Researched:' line, or the newest finding date) are due a refresh.
Lines with '(fill in)' are allowed and listed, never filled from memory.
Exit 1 if any finding is missing its label or link.
"""

import argparse
import datetime
import re
import sys

LABELS = ("OFFICIAL", "SEVERAL REPORTS", "ONE REPORT", "GUESS")
DATE = re.compile(r"\b(20\d\d-\d\d(?:-\d\d)?)\b")


def check(text, today):
    errors, todo, dates = [], [], []
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        m = re.match(r"Researched:\s*(20\d\d-\d\d-\d\d)", s, re.I)
        if m:
            dates.append(datetime.date.fromisoformat(m.group(1)))
        if not s.startswith(("- ", "* ")):
            continue
        if "(fill in)" in s:
            todo.append("line %d: %s" % (n, s[2:60]))
            continue
        label = next((l for l in LABELS if l in s), None)
        if not label:
            errors.append("line %d: no label (%s): %s" % (n, " / ".join(LABELS), s[2:70]))
        elif label != "GUESS" and "http" not in s:
            errors.append("line %d: %s finding has no link: %s" % (n, label, s[2:70]))
        d = DATE.search(s)
        if not d:
            errors.append("line %d: no date: %s" % (n, s[2:70]))
        else:
            v = d.group(1)
            try:
                dates.append(datetime.date.fromisoformat(v if len(v) == 10 else v + "-01"))
            except ValueError:
                errors.append("line %d: bad date %s" % (n, v))
    newest = max(dates) if dates else None
    stale = newest is None or (today - newest).days > 90
    return errors, todo, newest, stale


def main(argv=None):
    p = argparse.ArgumentParser(description="Every company-notes finding labelled, linked and dated.")
    p.add_argument("file")
    p.add_argument("--today")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    errors, todo, newest, stale = check(open(a.file, encoding="utf-8").read(), today)
    for e in errors:
        print("FAIL  " + e)
    for t in todo:
        print("TODO  " + t)
    print("Newest finding: %s%s" % (newest or "none", "  (over 3 months old: refresh)" if stale else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
