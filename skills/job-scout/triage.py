#!/usr/bin/env python3
"""Cheap first pass: drop what plainly doesn't fit before Claude reads or scores anything.

    python3 triage.py --rows found.json --pipeline jobsearch/pipeline.json --prefs PREFERENCES_AND_SCORING.md [--json]

found.json: the raw rows from every source in one list ({title, company, location, url,
posted, remote, ref}; feeds.py shortlist, the Indeed connector and alert emails all give
these). The scoring JSON's optional "triage" block sets the rules:
  {"titles": ["account executive", "business development"],   # at least one must appear
   "exclude_titles": ["senior", "principal", "director", "intern"],
   "locations": ["dublin", "ireland", "remote"], "days": 30,
   "exclude_companies": ["Acme"]}
A job already on the job list (by link or reference), a duplicate within the batch, a
title outside the families or with an excluded word, the wrong place, an ad older than
`days`, or an excluded company is dropped here, with a count by reason. Only the rest
go through the posting check, the gates and scoring, which is where the usage goes.
career-ops showed deduplication saves more than better scoring; this is that, at no
cost. Nothing is dropped for being a stretch: level and fit are scored, not filtered.
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from feeds import seen_keys  # noqa: E402


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def rules_from(prefs_path):
    if not prefs_path or not os.path.exists(prefs_path):
        return {}
    text = open(prefs_path, encoding="utf-8").read()
    if prefs_path.endswith(".json"):
        return json.loads(text).get("triage", {})
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    return json.loads(m.group(1)).get("triage", {}) if m else {}


def triage(rows, rules, seen=(), today=None):
    today = today or datetime.date.today()
    titles = [norm(t) for t in rules.get("titles", [])]
    excl = [norm(t) for t in rules.get("exclude_titles", [])]
    places = [norm(p) for p in rules.get("locations", [])]
    companies = {norm(c) for c in rules.get("exclude_companies", [])}
    days = rules.get("days")
    keep, dropped, batch = [], {}, set()

    def drop(reason):
        dropped[reason] = dropped.get(reason, 0) + 1

    for r in rows:
        url = str(r.get("url", "")).rstrip("/").lower()
        key = url or "%s|%s|%s" % (norm(r.get("company")), norm(r.get("title")), norm(r.get("location")))
        dup_key = "%s|%s" % (norm(r.get("company")), norm(r.get("title")))
        t = " %s " % norm(r.get("title"))
        if url in seen or (r.get("ref") and str(r["ref"]).lower() in seen):
            drop("already on the job list")
        elif key in batch or dup_key in batch:
            drop("duplicate in this batch")
        elif norm(r.get("company")) in companies:
            drop("excluded company")
        elif titles and not any(" %s " % x in t or x in t for x in titles):
            drop("title outside the role families")
        elif any(" %s " % x in t for x in excl):
            drop("excluded title word")
        elif places and not (any(p in norm(r.get("location")) for p in places)
                             or (r.get("remote") and "remote" in places)):
            drop("wrong place")
        elif days and r.get("posted") and _age(r["posted"], today) is not None and _age(r["posted"], today) > days:
            drop("older than %d days" % days)
        else:
            keep.append(r)
            batch.update([key, dup_key])
            continue
        batch.add(key)
    return {"read": len(rows), "keep": keep, "dropped": dropped}


def _age(posted, today):
    try:
        return (today - datetime.date.fromisoformat(str(posted)[:10])).days
    except ValueError:
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description="Free first-pass filter before scoring.")
    p.add_argument("--rows", required=True)
    p.add_argument("--pipeline")
    p.add_argument("--prefs")
    p.add_argument("--today")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    rows = json.load(open(a.rows, encoding="utf-8"))
    seen = seen_keys(json.load(open(a.pipeline, encoding="utf-8"))) if a.pipeline else set()
    out = triage(rows, rules_from(a.prefs), seen, today)
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        print("Read %d, kept %d for scoring; dropped: %s" % (out["read"], len(out["keep"]), ", ".join(
            "%d %s" % (n, k) for k, n in sorted(out["dropped"].items(), key=lambda x: -x[1])) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
