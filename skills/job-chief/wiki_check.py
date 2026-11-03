#!/usr/bin/env python3
"""Lint the job-search wiki: a dated history of decisions and lessons.

    python3 wiki_check.py jobsearch/wiki [--today 2026-11-03] [--stale-days 90]

The wiki is a folder of markdown pages with an index.md. Checks:
  FAIL  a page missing from index.md, or an index link to a page that doesn't exist
  FAIL  a claim line (a bullet) with no date (YYYY-MM-DD): the wiki records
        history, so every claim says when it was true
  WARN  a page no other page or the index links to (orphan)
  WARN  "currently", "now" or "at the moment" without a date on the same line
  WARN  a page whose newest date is older than --stale-days (worth a review)
  WARN  a superseded claim with no pointer to what replaced it

Adapted from Matt Pocock's chief-of-staff skill (MIT): pages cite sources
rather than copying them, and old claims are marked superseded, never rewritten.
Exits 1 on any FAIL.
"""

import argparse
import datetime as dt
import os
import re
import sys

DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
LINK = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
NOW = re.compile(r"\b(currently|right now|at the moment|nowadays|now)\b", re.I)
BULLET = re.compile(r"^\s*[-*]\s+\S")
SUPERSEDED = re.compile(r"superseded", re.I)


def pages(folder):
    out = {}
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, f), folder).replace(os.sep, "/")
                out[rel] = open(os.path.join(root, f), encoding="utf-8").read()
    return out


def links(text, here):
    base = os.path.dirname(here)
    return {os.path.normpath(os.path.join(base, l)).replace(os.sep, "/") for l in LINK.findall(text)
            if not l.startswith(("http://", "https://"))}


def check(folder, today, stale_days=90):
    results = []
    ps = pages(folder)
    if "index.md" not in ps:
        return [("FAIL", "index.md", "no index.md: it lists every page with a one-line summary")]
    indexed = links(ps["index.md"], "index.md")
    for target in sorted(indexed - set(ps)):
        results.append(("FAIL", "index.md", "links to a page that doesn't exist: %s" % target))
    for name in sorted(ps):
        if name == "index.md":
            continue
        text = ps[name]
        if name not in indexed:
            results.append(("FAIL", name, "not listed in index.md"))
        elif not any(name in links(t, n) for n, t in ps.items() if n not in (name, "index.md")):
            results.append(("WARN", name, "only the index links here; link related pages to it"))
        dates = []
        for i, line in enumerate(text.splitlines(), 1):
            found = DATE.findall(line)
            dates += found
            if BULLET.match(line) and not found and not LINK.search(line):
                results.append(("FAIL", name, "line %d: a claim with no date: %s" % (i, line.strip()[:70])))
            elif NOW.search(line) and not found:
                results.append(("WARN", name, "line %d: 'now' with no date: %s" % (i, line.strip()[:70])))
            if SUPERSEDED.search(line) and not LINK.search(line) and "by " not in line.lower():
                results.append(("WARN", name, "line %d: superseded, but by what? link or name it" % i))
        if dates:
            newest = max(dt.date.fromisoformat(d) for d in dates if _ok(d))
            if (today - newest).days > stale_days:
                results.append(("WARN", name, "newest entry %s: over %d days old, worth a review" % (newest, stale_days)))
    if not results:
        results.append(("PASS", "wiki", "%d pages, all indexed and dated" % (len(ps) - 1)))
    return results


def _ok(d):
    try:
        dt.date.fromisoformat(d)
        return True
    except ValueError:
        return False


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder")
    p.add_argument("--today")
    p.add_argument("--stale-days", type=int, default=90)
    a = p.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    results = check(a.folder, today, a.stale_days)
    for status, page, detail in results:
        print("%-4s %-28s %s" % (status, page, detail))
    return 1 if any(r[0] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
