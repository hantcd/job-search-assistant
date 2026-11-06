#!/usr/bin/env python3
"""Companies most applicants miss: find, keep and rank growing, lesser-known companies.

    python3 hidden.py sources [--country IE]                      # where to look (hidden_sources.json)
    python3 hidden.py queries --industry fintech --place Dublin [--country IE] [--title "Account Executive"] [--big Stripe]
    python3 hidden.py add --file jobsearch/pipeline.json --company "Acme Ltd" --source "Silicon Republic" \
        --url URL --why "Series A, EUR 8m" [--funded 2026-09-14] [--size 40] [--industry fintech] [--location Dublin]
    python3 hidden.py feeds "Acme Ltd"                            # the public job feeds to try for it
    python3 hidden.py set-feed --file jobsearch/pipeline.json --company "Acme Ltd" --kind greenhouse --token acme [--open-roles 3]
    python3 hidden.py rank --file jobsearch/pipeline.json [--industry fintech --place Dublin] [--top 10]

The job list's `hidden` table keeps each company: company, found, source, url, why,
funded (date of the latest round), size, industry, location, status (candidate,
feed found, no feed, dropped), feed {kind, token}, open_roles. job-weekly adds about
10 a week; the daily job search reads the feeds of those with one, so their roles
are scored like any other; the connection queue includes their people. Nothing is
added to the watched list without the person's yes.

add refuses companies already watched, already in the table, or over 1,000 staff
(not hidden). rank scores what makes a company worth the effort:
  funding in the last 3 months 30, 6 months 20, a year 10
  10-250 staff 25, 251-500 15, 1-9 5, unknown 10
  in the person's places 20, in their industries 15
  open roles matching the search 10 (from the feed)
Per-job applications aren't lower at small firms in Ashby's data, but at small,
growing firms the hiring manager often reads applications and outreach reaches the
person deciding, and roles posted only on their own page get fewer applicants.
"""

import argparse
import datetime
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def norm(name):
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(ltd|limited|plc|inc|llc|gmbh|dac|uc|teoranta|group|holdings|technologies|technology)\b\.?", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def slugs(name):
    base = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"\b(ltd|limited|plc|inc|llc|dac)\b\.?", "", base).strip()
    words = re.findall(r"[a-z0-9]+", base)
    out = []
    for s in ("".join(words), "-".join(words), words[0] if words else "", "".join(words) + "hq"):
        if s and s not in out:
            out.append(s)
    return out


def load_sources(country=None):
    with open(os.path.join(HERE, "hidden_sources.json"), encoding="utf-8") as fh:
        src = json.load(fh)["sources"]
    if country:
        src = [s for s in src if country.upper() in s["countries"] or "any" in s["countries"]]
    return src


def queries(industry, place, country=None, title="", big=(), year=None):
    year = year or datetime.date.today().year
    out = []
    for s in load_sources(country):
        if "query" not in s:
            out.append({"source": s["name"], "fetch": s["url"], "extract": s["extract"], "cadence": s["cadence"]})
            continue
        if "{big_name}" in s["query"]:
            for b in big or ():
                out.append({"source": s["name"], "search": s["query"].format(big_name=b, industry=industry),
                            "extract": s["extract"], "cadence": s["cadence"]})
            continue
        if "{title}" in s["query"] and not title:
            continue
        out.append({"source": s["name"], "cadence": s["cadence"], "extract": s["extract"],
                    "search": s["query"].format(industry=industry, place=place, year=year, title=title)})
    return out


def table(data):
    return data.setdefault("hidden", [])


def add(data, company, source, url, why, today, funded=None, size=None, industry="", location=""):
    watched = {norm(w.get("company") or w.get("name")) for w in data.get("watched", []) if isinstance(w, dict)}
    key = norm(company)
    if not key:
        return "REFUSED", "no company name"
    if key in watched:
        return "SKIPPED", "%s is already watched" % company
    rows = table(data)
    if any(norm(r.get("company")) == key for r in rows):
        return "SKIPPED", "%s is already in the hidden table" % company
    if size is not None and size > 1000:
        return "SKIPPED", "%s has %d staff: not a hidden company" % (company, size)
    rows.append({"company": company, "found": today.isoformat(), "source": source, "url": url, "why": why,
                 "funded": funded, "size": size, "industry": industry, "location": location,
                 "status": "candidate", "feed": None, "open_roles": None})
    return "ADDED", company


def feeds(company):
    from feeds import LIGHT  # noqa: E402
    return [{"kind": k, "token": s, "url": LIGHT[k].format(token=s)} for s in slugs(company) for k in LIGHT]


def set_feed(data, company, kind, token, open_roles=None):
    for r in table(data):
        if norm(r.get("company")) == norm(company):
            if kind == "none":
                r["status"], r["feed"] = "no feed", None
            else:
                r["status"], r["feed"] = "feed found", {"kind": kind, "token": token}
            if open_roles is not None:
                r["open_roles"] = open_roles
            return r
    raise SystemExit("not in the hidden table: %s" % company)


def score(r, today, industries=(), places=()):
    pts, why = 0, []
    try:
        months = (today - datetime.date.fromisoformat(str(r.get("funded"))[:10])).days / 30.4
    except (TypeError, ValueError):
        months = None
    if months is not None:
        p = 30 if months <= 3 else 20 if months <= 6 else 10 if months <= 12 else 0
        pts += p
        if p:
            why.append("funded %d months ago" % round(months))
    size = r.get("size")
    pts += 10 if size is None else 25 if 10 <= size <= 250 else 15 if 251 <= size <= 500 else 5 if size < 10 else 0
    loc = (r.get("location") or "").lower()
    if any(p.lower() in loc for p in places if p):
        pts += 20
        why.append("in %s" % r.get("location"))
    ind = (r.get("industry") or "").lower()
    if any(i.lower() in ind for i in industries if i):
        pts += 15
    if r.get("open_roles"):
        pts += 10
        why.append("%d matching roles open" % r["open_roles"])
    return pts, why


def rank(data, today, industries=(), places=(), top=10):
    rows = [r for r in table(data) if r.get("status") != "dropped"]
    scored = []
    for r in rows:
        p, why = score(r, today, industries, places)
        scored.append(dict(r, score=p, reasons=why))
    scored.sort(key=lambda r: (-r["score"], r["company"].lower()))
    return scored[:top]


def main(argv=None):
    p = argparse.ArgumentParser(description="Companies most applicants miss.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sources")
    s.add_argument("--country")
    q = sub.add_parser("queries")
    q.add_argument("--industry", required=True)
    q.add_argument("--place", required=True)
    q.add_argument("--country")
    q.add_argument("--title", default="")
    q.add_argument("--big", action="append", default=[])
    q.add_argument("--year", type=int)
    a_ = sub.add_parser("add")
    for x in ("--file", "--company", "--source", "--url", "--why"):
        a_.add_argument(x, required=x in ("--file", "--company", "--source", "--why"), default="")
    a_.add_argument("--funded")
    a_.add_argument("--size", type=int)
    a_.add_argument("--industry", default="")
    a_.add_argument("--location", default="")
    a_.add_argument("--today")
    f = sub.add_parser("feeds")
    f.add_argument("company")
    sf = sub.add_parser("set-feed")
    sf.add_argument("--file", required=True)
    sf.add_argument("--company", required=True)
    sf.add_argument("--kind", required=True, choices=("greenhouse", "lever", "ashby", "none"))
    sf.add_argument("--token", default="")
    sf.add_argument("--open-roles", type=int)
    r = sub.add_parser("rank")
    r.add_argument("--file", required=True)
    r.add_argument("--industry", action="append", default=[])
    r.add_argument("--place", action="append", default=[])
    r.add_argument("--top", type=int, default=10)
    r.add_argument("--today")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if getattr(a, "today", None) else datetime.date.today()
    if a.cmd == "sources":
        print(json.dumps(load_sources(a.country), indent=1))
        return 0
    if a.cmd == "queries":
        print(json.dumps(queries(a.industry, a.place, a.country, a.title, a.big, a.year), indent=1))
        return 0
    if a.cmd == "feeds":
        print(json.dumps(feeds(a.company), indent=1))
        return 0
    data = json.load(open(a.file, encoding="utf-8"))
    if a.cmd == "add":
        status, msg = add(data, a.company, a.source, a.url, a.why, today, a.funded, a.size, a.industry, a.location)
        print("%s %s" % (status, msg))
    elif a.cmd == "set-feed":
        print(json.dumps(set_feed(data, a.company, a.kind, a.token, a.open_roles), indent=1))
    elif a.cmd == "rank":
        for row in rank(data, today, a.industry, a.place, a.top):
            print("%3d  %-28s %s" % (row["score"], row["company"][:28], "; ".join(row["reasons"]) or row.get("why", "")))
        return 0
    with open(a.file, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
