#!/usr/bin/env python3
"""LinkedIn's public job listings (logged out), as job rows. OPT-IN, low volume.

    python3 linkedin_jobs.py search -q "data analyst" -l "Dublin, County Dublin, Ireland" --days 1 [--remote hybrid] [--pages 2]
    python3 linkedin_jobs.py detail 4425498329            # or a linkedin.com/jobs/view/... URL
    python3 linkedin_jobs.py search ... --from-file saved.html   # parse a page saved another way

Reads LinkedIn's public "jobs-guest" listing pages, the ones anyone can see
without an account. No login, no cookies, no profiles, no people, no messages:
job listings only.

Read this first: LinkedIn's User Agreement forbids automated access, including to
public pages, and its robots.txt asks crawlers to stay out. Using this is the
person's own decision (MASTER_PLAN.md must say LinkedIn listings are on), for
their own job search only, never for bulk collection. The person's LinkedIn
account is never involved, but LinkedIn may block the IP address. To keep it
small: at most 3 pages (30 listings) per search, a 3-second pause between
requests, backing off on 429 and stopping after repeated refusals. Every row is
then verified on the company's own page, as with any job site.

Output: JSON rows {company, title, location, url, ref, posted, source} (detail
adds text, seniority, employment_type, job_function, industries, active).
Ported from ai-job-search's linkedin-search CLI (MIT, Mads Lorentzen).
"""

import argparse
import html as htmlmod
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"
UA = "Mozilla/5.0 (compatible; job-search-assistant/1.0; personal job search)"
MAX_PAGES = 3
PAUSE = 3.0


def decode(text):
    text = (text or "").replace("&nbsp;", " ")
    return htmlmod.unescape(text)


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def clean(s):
    return decode(strip_tags(s))


def div_content(page, class_name):
    """Inner HTML of the first <div> with this class, handling nested divs."""
    m = re.search(r'<div[^>]*class="[^"]*%s[^"]*"[^>]*>' % re.escape(class_name), page, re.I)
    if not m:
        return None
    i, depth = m.end(), 1
    while depth > 0 and i < len(page):
        nxt_open, nxt_close = page.find("<div", i), page.find("</div>", i)
        if nxt_close == -1:
            return None
        if nxt_open != -1 and nxt_open < nxt_close:
            depth, i = depth + 1, nxt_open + 4
        else:
            depth, i = depth - 1, nxt_close + 6
    return page[m.end(): i - 6]


def parse_cards(page):
    rows = []
    for chunk in re.split(r'data-entity-urn="urn:li:jobPosting:', page)[1:]:
        m = re.match(r"(\d+)", chunk)
        if not m:
            continue
        jid = m.group(1)
        link = re.search(r'class="base-card__full-link[^"]*"[^>]*href="([^"]+)"', chunk, re.I)
        url = decode(link.group(1)).split("?")[0] if link else ""
        title = None
        h3 = re.search(r'class="base-search-card__title"[^>]*>([\s\S]*?)</h3>', chunk, re.I)
        if h3:
            title = clean(h3.group(1))
        if not title:
            sr = re.search(r'class="sr-only"[^>]*>([\s\S]*?)</span>', chunk, re.I)
            title = clean(sr.group(1)) if sr else None
        if not title:
            continue
        company = None
        sub = re.search(r'class="base-search-card__subtitle"[^>]*>([\s\S]*?)</h4>', chunk, re.I)
        if sub:
            company = clean(sub.group(1)) or None
        loc = re.search(r'class="job-search-card__location"[^>]*>([\s\S]*?)</span>', chunk, re.I)
        dt = re.search(r'class="job-search-card__listdate[^"]*"[^>]*datetime="([^"]+)"', chunk, re.I)
        rows.append({"company": company or "", "title": title, "location": clean(loc.group(1)) if loc else "",
                     "url": url or "https://www.linkedin.com/jobs/view/%s" % jid, "ref": "linkedin:" + jid,
                     "posted": dt.group(1) if dt else "", "source": "linkedin listings"})
    return rows


def parse_detail(page, jid):
    title = re.search(r'class="(?:top-card-layout__title|topcard__title)[^"]*"[^>]*>([\s\S]*?)</h[12]>', page, re.I)
    org = re.search(r'class="topcard__org-name-link[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', page, re.I)
    loc = re.search(r'class="topcard__flavor topcard__flavor--bullet"[^>]*>([\s\S]*?)</span>', page, re.I)
    desc_html = div_content(page, "show-more-less-html__markup") or div_content(page, "description__text")
    text = ""
    if desc_html:
        s = re.sub(r"\s+", " ", desc_html)
        s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
        s = re.sub(r"</(p|li|ul|ol|div|h\d)>", "\n", s, flags=re.I)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(clean(x) for x in s.split("\n"))).strip()
    criteria = {}
    for m in re.finditer(r'class="description__job-criteria-subheader"[^>]*>([\s\S]*?)</h3>[\s\S]*?'
                         r'class="description__job-criteria-text[^"]*"[^>]*>([\s\S]*?)</span>', page, re.I):
        criteria[clean(m.group(1)).lower()] = clean(m.group(2))
    start = re.search(r'class="(?:show-more-less-html__markup|description__text)', page, re.I)
    top = page[: start.start()] if start else page
    return {"ref": "linkedin:" + jid, "title": clean(title.group(1)) if title else "(untitled)",
            "company": clean(org.group(2)) if org else "", "location": clean(loc.group(1)) if loc else "",
            "url": "https://www.linkedin.com/jobs/view/%s" % jid, "text": text,
            "seniority": criteria.get("seniority level"), "employment_type": criteria.get("employment type"),
            "job_function": criteria.get("job function"), "industries": criteria.get("industries"),
            "active": not re.search(r"closed-job__flavor|no longer accepting applications", top, re.I),
            "source": "linkedin listings"}


def job_id(value):
    m = re.search(r"-(\d{6,})(?:\?|/|$)", value) or re.search(r"(\d{6,})", value)
    if not m:
        raise ValueError("not a LinkedIn job id or URL: %r" % value)
    return m.group(1)


def search_url(query, location, days=0, remote=None, page=1):
    p = {}
    if query:
        p["keywords"] = query
    p["location"] = location
    if days and 0 < days < 9999:
        p["f_TPR"] = "r%d" % (days * 86400)
    wt = {"onsite": "1", "on-site": "1", "remote": "2", "hybrid": "3"}.get((remote or "").lower())
    if wt:
        p["f_WT"] = wt
    p["start"] = str((page - 1) * 10)
    return SEARCH_URL + "?" + urllib.parse.urlencode(p)


def fetch(url, retries=4):
    delay = 2.0
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8",
                                                   "Accept-Language": "en-GB,en;q=0.9"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            if e.code in (429,) or e.code >= 500:
                if attempt == retries:
                    raise
                time.sleep(delay + random.random())
                delay = min(delay * 2, 30)
                continue
            raise
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="LinkedIn public job listings (opt-in, low volume).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("-q", "--query", default="")
    s.add_argument("-l", "--location", required=True, help='e.g. "Dublin, County Dublin, Ireland" or "Ireland"')
    s.add_argument("--days", type=int, default=1, help="posted within N days (default 1)")
    s.add_argument("--remote", choices=("remote", "hybrid", "onsite"))
    s.add_argument("--pages", type=int, default=1)
    s.add_argument("--from-file")
    d = sub.add_parser("detail")
    d.add_argument("job")
    d.add_argument("--from-file")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "search":
            if a.from_file:
                rows = parse_cards(open(a.from_file, encoding="utf-8").read())
            else:
                rows, seen = [], set()
                for page in range(1, min(a.pages, MAX_PAGES) + 1):
                    if page > 1:
                        time.sleep(PAUSE)
                    got = parse_cards(fetch(search_url(a.query, a.location, a.days, a.remote, page)))
                    new = [r for r in got if r["ref"] not in seen]
                    seen.update(r["ref"] for r in new)
                    rows += new
                    if len(got) < 10:
                        break
            print(json.dumps(rows, indent=1, ensure_ascii=False))
            return 0 if rows else 1
        jid = job_id(a.job)
        page = open(a.from_file, encoding="utf-8").read() if a.from_file else fetch("%s/%s" % (DETAIL_URL, jid))
        if not page:
            print(json.dumps({"ref": "linkedin:" + jid, "active": False, "note": "not found (removed or closed)"}))
            return 1
        print(json.dumps(parse_detail(page, jid), indent=1, ensure_ascii=False))
        return 0
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("could not read LinkedIn listings: %s. Skip this source for this run; never get round a block."
              % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
