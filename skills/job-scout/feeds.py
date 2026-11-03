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
    python3 feeds.py live "https://jobs.lever.co/someco/0a1b..."      # still open? (Greenhouse, Lever, Ashby)
    python3 feeds.py questions "https://job-boards.greenhouse.io/intercom/jobs/123"   # the form's questions

live      asks the hiring system itself whether one job is still open: LIVE,
          CLOSED (a 404 or 410, or the job is gone from the company's Ashby
          board) or UNKNOWN (anything else: a block, a redirect, an error).
          Only CLOSED is definitive; UNKNOWN falls back to opening the page,
          and to job-tracker's 3-tries-over-48-hours rule.
questions lists a Greenhouse job's application questions from its public API,
          as form.json for job-apply's answers.py (each with required and its
          options; equality-monitoring questions are marked for the person).
          Lever and Ashby don't publish their forms: use job-apply's
          apply_form.py scan.

Output: JSON rows {company, title, location, url, ref, posted, remote, text, source}.
detect also gives the job's own application page (Lever: .../apply; Ashby:
.../application; Greenhouse: the job page).
Liveness and application-URL ideas from career-ops (MIT, Santiago Fernández
de Valderrama).
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
import urllib.error
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


JOB_PATTERNS = [
    ("greenhouse", r"(?:job-boards|boards)\.(?:eu\.)?greenhouse\.io/([\w-]+)/jobs/(\d+)"),
    ("greenhouse", r"greenhouse\.io/embed/job_app\?for=([\w-]+)&(?:amp;)?token=(\d+)"),
    ("lever", r"jobs\.(?:eu\.)?lever\.co/([\w-]+)/([0-9a-f-]{36})"),
    ("ashby", r"jobs\.ashbyhq\.com/([\w.%-]+)/([0-9a-f-]{36})"),
]
SINGLE = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job}",
    "lever": "https://api.lever.co/v0/postings/{token}/{job}",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{token}",  # no single-job endpoint: check the board
}
QUESTIONS = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job}?questions=true"


def job_ref(url):
    """(ats, board token, job id) for a Greenhouse, Lever or Ashby job link, else (None, '', '')."""
    for name, pat in JOB_PATTERNS:
        m = re.search(pat, url or "", re.I)
        if m:
            return name, m.group(1), m.group(2)
    return None, "", ""


def apply_url(kind, token, job, url=""):
    """The job's own application form (EU-hosted Lever jobs keep their EU address)."""
    if kind == "lever":
        host = "jobs.eu.lever.co" if "jobs.eu.lever.co" in (url or "") else "jobs.lever.co"
        return "https://%s/%s/%s/apply" % (host, token, job)
    if kind == "ashby":
        return "https://jobs.ashbyhq.com/%s/%s/application" % (token, job)
    if kind == "greenhouse":
        return "https://job-boards.greenhouse.io/%s/jobs/%s" % (token, job)
    return ""


def liveness(kind, status, data, job):
    """(LIVE | CLOSED | UNKNOWN, reason). Conservative: a wrong CLOSED loses a real job."""
    if status in (404, 410):
        return "CLOSED", "the hiring system says this job no longer exists (HTTP %d)" % status
    if status != 200 or data is None:
        return "UNKNOWN", "no clear answer (HTTP %s): open the job page instead" % status
    if kind == "ashby":
        jobs = (data or {}).get("jobs")
        if not isinstance(jobs, list):
            return "UNKNOWN", "the Ashby board didn't load as expected"
        match = [j for j in jobs if str(j.get("id")) == str(job)]
        if not match:
            return "CLOSED", "no longer on the company's Ashby board (%d jobs listed)" % len(jobs)
        if match[0].get("isListed") is False:
            return "CLOSED", "unlisted on the company's Ashby board"
        return "LIVE", "listed on the company's Ashby board"
    if kind == "lever" and isinstance(data, dict) and data.get("ok") is False:
        return "CLOSED", "Lever says the posting isn't available"
    return "LIVE", "the hiring system still lists it"


FIELD_TYPES = {"input_text": "text", "textarea": "textarea", "input_file": "file", "input_hidden": None,
               "multi_value_single_select": "select", "multi_value_multi_select": "checkbox"}


def greenhouse_questions(data):
    """form.json rows from a Greenhouse ?questions=true response."""
    rows = []

    def add(q, group=""):
        fields = [f for f in q.get("fields") or [] if FIELD_TYPES.get(f.get("type")) is not None]
        if not fields:
            return
        f = fields[0]
        row = {"label": (q.get("label") or "").strip(), "type": FIELD_TYPES[f["type"]],
               "required": bool(q.get("required")), "field": f.get("name", "")}
        opts = [v.get("label") for v in f.get("values") or [] if v.get("label")]
        if opts:
            row["options"] = opts
        if any(x.get("type") == "textarea" for x in fields[1:]) and row["type"] == "file":
            row["or_paste"] = True  # the CV or letter can also be pasted as text
        if group:
            row["group"] = group
        rows.append(row)

    for q in (data or {}).get("questions") or []:
        add(q)
    for q in (data or {}).get("location_questions") or []:
        add(q, "location")
    for block in (data or {}).get("compliance") or []:
        for q in block.get("questions") or []:
            add(q, "equality monitoring (%s): the person's choice; 'decline to answer' is always fine" % block.get("type", ""))
    demo = (data or {}).get("demographic_questions") or {}
    for q in demo.get("questions") or []:
        q = dict(q, fields=[{"name": "demographic_%s" % q.get("id", ""), "type": "multi_value_single_select",
                             "values": [{"label": a.get("label")} for a in q.get("answer_options") or []]}])
        add(q, "equality monitoring: the person's choice")
    return rows


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
                         # workplaceType wins: a live board on 2026-11-03 had isRemote true on Hybrid roles
                         "remote": (j.get("workplaceType") == "Remote") if j.get("workplaceType") else bool(j.get("isRemote")),
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
    lv = sub.add_parser("live")
    lv.add_argument("url")
    lv.add_argument("--from-file", help="the API response saved another way (web fetch)")
    lv.add_argument("--status", type=int, default=200, help="its HTTP status, with --from-file")
    qs = sub.add_parser("questions")
    qs.add_argument("url")
    qs.add_argument("--from-file")
    qs.add_argument("--out")
    a = p.parse_args(argv)

    if a.cmd == "url":
        print(FEEDS[a.kind].format(token=a.token))
        return 0
    if a.cmd == "detect":
        name, token = detect(a.url)
        kind, board, job = job_ref(a.url)
        print(json.dumps({"ats": name or "unknown", "token": token,
                          "feed": FEEDS[name].format(token=token) if name in FEEDS and token else "",
                          "job": job, "apply": apply_url(kind, board, job, a.url) if kind else ""}))
        return 0
    if a.cmd in ("live", "questions"):
        kind, board, job = job_ref(a.url)
        if not kind or (a.cmd == "questions" and kind != "greenhouse"):
            print("not a %s job link; use apply_form.py scan on the form instead"
                  % ("Greenhouse" if a.cmd == "questions" else "Greenhouse, Lever or Ashby"), file=sys.stderr)
            return 2
        url = (QUESTIONS if a.cmd == "questions" else SINGLE[kind]).format(token=board, job=job)
        status, data = 200, None
        try:
            if a.from_file:
                status = getattr(a, "status", 200)
                with open(a.from_file, encoding="utf-8") as fh:
                    text = fh.read()
                data = json.loads(text) if text.strip() else None
            else:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception as e:  # blocked, offline, bad JSON
            if a.cmd == "live":
                print(json.dumps({"status": "UNKNOWN", "reason": "couldn't reach %s (%s): fetch it with web fetch "
                                  "and pass --from-file" % (url, e)}))
                return 2
            print("couldn't read %s (%s); fetch it with web fetch and pass --from-file" % (url, e), file=sys.stderr)
            return 2
        if a.cmd == "live":
            verdict, reason = liveness(kind, status, data, job)
            print(json.dumps({"status": verdict, "reason": reason, "ats": kind, "job": job, "checked": url}))
            return 0 if verdict == "LIVE" else 1
        if status != 200:
            print("Greenhouse answered HTTP %d: the job may be closed (try live)" % status, file=sys.stderr)
            return 1
        text = json.dumps(greenhouse_questions(data), indent=1, ensure_ascii=False)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text)
        print(text)
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
