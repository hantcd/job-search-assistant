#!/usr/bin/env python3
"""Read a company's public job feed (Greenhouse, Lever, Ashby) and turn it into job rows.

These boards publish their open roles as public JSON for job seekers and
aggregators, which is cheaper and more reliable than reading a careers page.
If this sandbox can't reach the internet, fetch the feed URL with Claude's web
fetch tool, save the JSON, and pass it with --from-file.

    python3 feeds.py url greenhouse intercom            # the feed address to fetch
    python3 feeds.py fetch greenhouse intercom --title analyst --location dublin
    python3 feeds.py fetch lever someco --from-file someco.json --days 30
    python3 feeds.py detect "https://job-boards.greenhouse.io/intercom/jobs/123"
    python3 feeds.py boards                             # the verified company list

Output: JSON rows {company, title, location, url, ref, posted, remote, text, source}.
Standard library only. Reads public pages only, one request per board, and
identifies itself. Never logs in and never reads a site whose terms say no
(see access.md).
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "job-search-assistant/1.0 (personal job search; one request per board)"

FEEDS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{token}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true",
}

# Which hiring system a job link belongs to (for company notes and for finding the feed).
ATS_PATTERNS = [
    ("greenhouse", r"(?:job-boards|boards)\.(?:eu\.)?greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)"),
    ("lever", r"jobs\.(?:eu\.)?lever\.co/([\w-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([\w.-]+)"),
    ("workday", r"([\w-]+)\.wd\d+\.myworkdayjobs\.com"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)"),
    ("successfactors", r"(?:career\d*\.successfactors\.(?:com|eu)|jobs\.sap\.com)"),
    ("taleo", r"([\w-]+)\.taleo\.net"),
    ("icims", r"([\w-]+)\.icims\.com"),
    ("workable", r"apply\.workable\.com/([\w-]+)"),
    ("teamtailor", r"([\w-]+)\.teamtailor\.com"),
    ("personio", r"([\w-]+)\.jobs\.personio\.(?:de|com)"),
    ("bamboohr", r"([\w-]+)\.bamboohr\.com"),
]


def detect(url):
    for name, pat in ATS_PATTERNS:
        m = re.search(pat, url or "", re.I)
        if m:
            token = m.group(1) if m.groups() else ""
            return name, token
    return None, ""


def strip_html(s):
    s = html.unescape(html.unescape(s or ""))
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", s).strip()


def iso_day(v):
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)):  # Lever: epoch milliseconds
        return datetime.datetime.fromtimestamp(v / 1000.0, datetime.timezone.utc).date().isoformat()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v))
    return m.group(1) if m else ""


def normalise(kind, data, company=""):
    rows = []
    if kind == "greenhouse":
        for j in (data or {}).get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            rows.append({"company": j.get("company_name") or company, "title": j.get("title", ""),
                         "location": loc, "url": j.get("absolute_url", ""),
                         "ref": j.get("requisition_id") or str(j.get("id", "")),
                         "posted": iso_day(j.get("first_published") or j.get("updated_at")),
                         "remote": "remote" in loc.lower(), "text": strip_html(j.get("content", "")),
                         "source": "greenhouse feed"})
    elif kind == "lever":
        for p in data or []:
            cat = p.get("categories") or {}
            loc = cat.get("location", "")
            rows.append({"company": company, "title": p.get("text", ""), "location": loc,
                         "url": p.get("hostedUrl", ""), "ref": p.get("id", ""),
                         "posted": iso_day(p.get("createdAt")),
                         "remote": (p.get("workplaceType") == "remote") or "remote" in loc.lower(),
                         "text": (p.get("descriptionPlain", "") + "\n" + p.get("additionalPlain", "")).strip(),
                         "source": "lever feed"})
    elif kind == "ashby":
        for j in (data or {}).get("jobs", []):
            if j.get("isListed") is False:
                continue
            rows.append({"company": company, "title": j.get("title", ""), "location": j.get("location", ""),
                         "url": j.get("jobUrl", ""), "ref": j.get("id", ""), "posted": iso_day(j.get("publishedAt")),
                         "remote": bool(j.get("isRemote")) or j.get("workplaceType") == "Remote",
                         "text": j.get("descriptionPlain", ""), "source": "ashby feed",
                         "pay_text": ((j.get("compensation") or {}).get("compensationTierSummary") or "")})
    else:
        raise ValueError("unsupported feed type %r (greenhouse, lever or ashby)" % kind)
    return rows


def keep(row, titles, locations, days, today, remote_only):
    t = row["title"].lower()
    if titles and not any(w.lower() in t for w in titles):
        return False
    if locations:
        loc = row["location"].lower()
        if not any(l.lower() in loc for l in locations) and not (row.get("remote") and "remote" in [x.lower() for x in locations]):
            return False
    if remote_only and not row.get("remote"):
        return False
    if days and row.get("posted"):
        try:
            age = (today - datetime.date.fromisoformat(row["posted"])).days
        except ValueError:
            return True
        if age > days:
            return False
    return True


def fetch(kind, token):
    req = urllib.request.Request(FEEDS[kind].format(token=token), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main(argv=None):
    p = argparse.ArgumentParser(description="Public job feeds -> job rows.")
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("url")
    u.add_argument("kind", choices=sorted(FEEDS))
    u.add_argument("token")
    f = sub.add_parser("fetch")
    f.add_argument("kind", choices=sorted(FEEDS))
    f.add_argument("token")
    f.add_argument("--company", default="")
    f.add_argument("--from-file")
    f.add_argument("--title", action="append", default=[])
    f.add_argument("--location", action="append", default=[])
    f.add_argument("--remote", action="store_true")
    f.add_argument("--days", type=int, default=0)
    f.add_argument("--today")
    f.add_argument("--no-text", action="store_true", help="leave out the ad text")
    d = sub.add_parser("detect")
    d.add_argument("url")
    sub.add_parser("boards")
    a = p.parse_args(argv)

    if a.cmd == "url":
        print(FEEDS[a.kind].format(token=a.token))
        return 0
    if a.cmd == "detect":
        name, token = detect(a.url)
        print(json.dumps({"ats": name or "unknown", "token": token,
                          "feed": FEEDS[name].format(token=token) if name in FEEDS and token else ""}))
        return 0
    if a.cmd == "boards":
        with open(os.path.join(HERE, "boards.json"), encoding="utf-8") as fh:
            b = json.load(fh)
        for row in b["boards"]:
            print("%-22s %-10s %s" % (row["company"], row["type"], row.get("token") or row.get("careers", "")))
        print("(checked %s; re-check a token that returns 404)" % b.get("verified", "?"))
        return 0
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    try:
        if a.from_file:
            with open(a.from_file, encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = fetch(a.kind, a.token)
    except Exception as e:  # network blocked, 404, bad JSON
        print("could not read the %s feed for %r: %s\nFetch %s with web fetch and pass --from-file."
              % (a.kind, a.token, e, FEEDS[a.kind].format(token=a.token)), file=sys.stderr)
        return 2
    rows = [r for r in normalise(a.kind, data, a.company or a.token)
            if keep(r, a.title, a.location, a.days, today, a.remote)]
    if a.no_text:
        for r in rows:
            r.pop("text", None)
    print(json.dumps(rows, indent=1, ensure_ascii=False))
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
