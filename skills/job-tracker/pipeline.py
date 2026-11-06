#!/usr/bin/env python3
"""The job list as one JSON snapshot: jobs, applications, contacts, outreach and the run log.

Every skill in this pack reads and writes the same shape. Where your job list
lives (a page in Claude with a built-in database, a Google Sheet, or a local
file) doesn't matter: Claude copies the rows into a snapshot file, runs this
tool, and writes the changes back. This tool owns the schema and checks it.

Commands (all take --file, default jobsearch/pipeline.json; date-dependent ones take --today):

    python3 pipeline.py init
    python3 pipeline.py validate
    python3 pipeline.py add-job --company Acme --title "Junior Data Analyst" --url URL [--ref R123] [--posted 2026-10-12]
    python3 pipeline.py move acme-junior-data-analyst applied --today 2026-10-16
    python3 pipeline.py summary --today 2026-10-19
    python3 pipeline.py stale --today 2026-10-19
    python3 pipeline.py export --what jobs --out jobs.csv
    python3 pipeline.py can-apply acme-junior-data-analyst --today 2026-10-16 [--cap 2]
    python3 pipeline.py unreachable acme-junior-data-analyst --error "HTTP 503" --now 2026-10-16T08:00
    python3 pipeline.py reachable acme-junior-data-analyst
    python3 pipeline.py contact-check siobhan-kelly-acme [--job acme-junior-data-analyst] --today 2026-10-20
    python3 pipeline.py coverage --task watched          # every watched company accounted for in the last run
    python3 pipeline.py queue add acme-junior-data-analyst --today 2026-11-04   # the person said 'apply to this'
    python3 pipeline.py queue list                       # what's ready for the next apply session

Standard library only. Nothing here sends anything: it is a record.
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys

DEFAULT_FILE = os.path.join("jobsearch", "pipeline.json")

STATUSES = ("new", "open", "applied", "screen", "interview", "offer", "accepted",
            "rejected", "withdrawn", "closed", "ignored")
ACTIVE = ("new", "open", "applied", "screen", "interview", "offer")
APPLIED_OR_LATER = ("applied", "screen", "interview", "offer", "accepted", "rejected", "withdrawn")
LEGITIMACY = ("HIGH CONFIDENCE", "PROCEED WITH CAUTION", "SUSPICIOUS", "")
CONFIDENCE = ("HIGH", "MEDIUM", "LOW", "")
ROUTES = ("portal", "agency", "referral", "direct", "")
CHANNELS = ("email", "linkedin", "phone", "in-person", "other")
OUTREACH_STATUSES = ("drafted", "sent", "replied", "booked", "declined", "closed")
PRIVACY = ("LOW", "MEDIUM", "HIGH", "GIVEN", "")
EMAIL_CONFIDENCE = ("published", "given", "high", "medium", "low", "unknown", "")
# Steps of the referral path (job-connector): connection note, thank-you after they
# accept, a short chat, the referral ask, one nudge.
STAGES = ("note", "thanks", "chat", "ask", "nudge", "")
RECRUITER_RE = re.compile(r"recruit|talent|sourc|\bhr\b|human resources|people (?:partner|team|ops)", re.I)
TEAM_CAP = 2  # at most 2 people per part of a company (recruiting, the team) in 2 weeks
TEAM_WINDOW = 14
REJECTION_WINDOW = 180  # days a rejection at a company is worth a warning before writing to its recruiters
TABLES = ("jobs", "applications", "contacts", "outreach", "run_log", "email_log")
# Free-form tables the skills also keep (checked only for being lists):
OTHER_TABLES = ("hidden", "form_notes", "companies", "events", "offers", "feedback", "story_grid",
                "keyword_bank", "watched", "network", "signals", "reddit", "linkedin_ids",
                "question_bank", "updates")

STALE_DAYS = 28  # 'stale' after 4 weeks with no news
LIFETIME_CAP = 2  # applications to one company, ever, unless the person raises it
HERE = os.path.dirname(os.path.abspath(__file__))
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ]\d{2}:\d{2}(?::\d{2})?)?$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class PipelineError(Exception):
    pass


def day(s, what="date"):
    if isinstance(s, datetime.date):
        return s
    m = DATE_RE.match(str(s or "").strip())
    if not m:
        raise PipelineError("%s must be YYYY-MM-DD, got %r" % (what, s))
    try:
        return datetime.date(*map(int, m.group(1).split("-")))
    except ValueError:
        raise PipelineError("%s is not a real date: %r" % (what, s))


def day_or_none(s):
    try:
        return day(s) if s else None
    except PipelineError:
        return None


def today_from(arg):
    return day(arg, "--today") if arg else datetime.date.today()


def slug(*parts):
    s = "-".join(p for p in parts if p)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "item"


def norm(s):
    """Loose form of a company or title for duplicate checks."""
    s = re.sub(r"\(.*?\)", " ", str(s or "").lower())
    s = re.sub(r"\b(ltd|limited|inc|plc|llc|gmbh|dac|teoranta)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def empty():
    return {k: [] for k in TABLES}


def load(path, must_exist=True):
    if not os.path.exists(path):
        if must_exist:
            raise PipelineError("no snapshot at %s (run: pipeline.py init)" % path)
        return empty()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        raise PipelineError("%s is not valid JSON: %s" % (path, e))
    if not isinstance(data, dict):
        raise PipelineError("%s must hold a JSON object" % path)
    for k in TABLES:
        if data.get(k) is None:
            data[k] = []
    return data


def save(path, data):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- checks

def validate(data):
    """Return (errors, warnings)."""
    errors, warnings = [], []
    for k in TABLES + OTHER_TABLES:
        if k in data and not isinstance(data[k], list):
            errors.append("%s must be a list" % k)
    if errors:
        return errors, warnings

    def check_date(where, v, optional=True):
        if v in (None, "") and optional:
            return
        if not DATE_RE.match(str(v)) or day_or_none(v) is None:
            errors.append("%s: bad date %r" % (where, v))

    job_ids = set()
    for i, j in enumerate(data["jobs"]):
        w = "jobs[%d]" % i
        jid = j.get("id")
        if not jid:
            errors.append(w + ": missing id")
        elif jid in job_ids:
            errors.append(w + ": duplicate id " + jid)
        job_ids.add(jid)
        for f in ("company", "title"):
            if not j.get(f):
                errors.append("%s: missing %s" % (w, f))
        if j.get("status", "new") not in STATUSES:
            errors.append("%s: unknown status %r" % (w, j.get("status")))
        for f in ("posted", "first_found", "last_checked", "alerted", "applied"):
            check_date("%s.%s" % (w, f), j.get(f))
        for f in ("fit", "career_value", "attainability"):
            v = j.get(f)
            if v not in (None, "") and not (isinstance(v, (int, float)) and 0 <= v <= 100):
                errors.append("%s.%s must be 0-100, got %r" % (w, f, v))
        if j.get("legitimacy", "") not in LEGITIMACY:
            errors.append("%s.legitimacy must be one of %s" % (w, ", ".join(x for x in LEGITIMACY if x)))
        if j.get("confidence", "") not in CONFIDENCE:
            errors.append("%s.confidence must be HIGH, MEDIUM or LOW" % w)
        if j.get("route", "") not in ROUTES:
            errors.append("%s.route must be one of %s" % (w, ", ".join(x for x in ROUTES if x)))
        if j.get("status") in APPLIED_OR_LATER and not j.get("applied") and j.get("status") not in ("withdrawn",):
            warnings.append("%s (%s): status %s but no applied date" % (w, jid, j.get("status")))

    # one route per role: never through an agency AND directly
    seen = {}
    for j in data["jobs"]:
        if j.get("status") in APPLIED_OR_LATER and j.get("route"):
            key = (norm(j.get("company")), norm(j.get("title")))
            if key in seen and seen[key] != j.get("route") and "agency" in (seen[key], j.get("route")):
                errors.append("applied to %s / %s both through an agency and directly" % (j.get("company"), j.get("title")))
            seen.setdefault(key, j.get("route"))

    for i, a in enumerate(data["applications"]):
        w = "applications[%d]" % i
        if a.get("job_id") not in job_ids:
            errors.append("%s: job_id %r is not in jobs" % (w, a.get("job_id")))
        for f in ("pack_made", "submitted"):
            check_date("%s.%s" % (w, f), a.get(f))
        if a.get("submitted") and not (a.get("answers") and a.get("confirmation")):
            warnings.append("%s: submitted, but the answers given and the confirmation (screenshot or email) aren't saved" % w)
        wts = a.get("screening_weights")
        if wts:
            if set(wts) != {"search", "scan", "read"} or sum(wts.values()) != 100:
                errors.append("%s.screening_weights must be search/scan/read totalling 100" % w)

    contact_ids = set()
    for i, c in enumerate(data["contacts"]):
        w = "contacts[%d]" % i
        cid = c.get("id")
        if not cid:
            errors.append(w + ": missing id")
        elif cid in contact_ids:
            errors.append(w + ": duplicate id " + cid)
        contact_ids.add(cid)
        em = c.get("email")
        if em and not EMAIL_RE.match(em):
            errors.append("%s: invalid email %r" % (w, em))
        conf = str(c.get("email_confidence", "")).lower()
        if conf not in EMAIL_CONFIDENCE:
            errors.append("%s.email_confidence must be one of %s" % (w, ", ".join(x for x in EMAIL_CONFIDENCE if x)))
        if conf == "published" and not str(c.get("found_how", "")).startswith("http"):
            errors.append("%s: a 'published' email needs found_how = the URL where it appears" % w)
        if em and conf not in ("given",) and not c.get("privacy_decision"):
            errors.append("%s: an email you weren't given needs a privacy_risk and your privacy_decision" % w)
        if c.get("privacy_risk", "") not in PRIVACY:
            errors.append("%s.privacy_risk must be LOW, MEDIUM or HIGH" % w)
        check_date(w + ".employer_checked", c.get("employer_checked"))

    for i, o in enumerate(data["outreach"]):
        w = "outreach[%d]" % i
        if o.get("contact_id") not in contact_ids:
            errors.append("%s: contact_id %r is not in contacts" % (w, o.get("contact_id")))
        if o.get("job_id") and o.get("job_id") not in job_ids:
            errors.append("%s: job_id %r is not in jobs" % (w, o.get("job_id")))
        if o.get("channel") not in CHANNELS:
            errors.append("%s: unknown channel %r" % (w, o.get("channel")))
        if o.get("status") not in OUTREACH_STATUSES:
            errors.append("%s: unknown status %r" % (w, o.get("status")))
        prev = None
        for k, m in enumerate(o.get("messages", [])):
            check_date("%s.messages[%d].date" % (w, k), m.get("date"), optional=False)
            if m.get("direction") not in ("out", "in"):
                errors.append("%s.messages[%d]: direction must be out or in" % (w, k))
            d = day_or_none(m.get("date"))
            if prev and d and d < prev:
                warnings.append("%s: messages out of order" % w)
            prev = d or prev
        check_date(w + ".next_followup", o.get("next_followup"))
        if o.get("stage", "") not in STAGES:
            errors.append("%s.stage must be one of %s" % (w, ", ".join(x for x in STAGES if x)))

    seen_ids = set()
    for i, e in enumerate(data.get("email_log", [])):
        mid = e.get("message_id")
        if not mid:
            errors.append("email_log[%d]: needs the message_id" % i)
        elif mid in seen_ids:
            errors.append("email_log[%d]: message %s was already processed" % (i, mid))
        seen_ids.add(mid)
        if e.get("change") and not (e.get("from") and e.get("subject") and e.get("date")):
            errors.append("email_log[%d]: a status change must cite the email (from, subject, date)" % i)

    for i, r in enumerate(data["run_log"]):
        if not r.get("time") or not r.get("task"):
            errors.append("run_log[%d]: needs time and task" % i)
        for name, status in (r.get("coverage") or {}).items():
            st = str(status)
            if not (st.startswith("checked") or re.match(r"not checked: .{4,}", st)):
                errors.append("run_log[%d].coverage[%s]: 'checked: <how>' or 'not checked: <reason>'" % (i, name))
    return errors, warnings


# ---------------------------------------------------------------- jobs

def find_duplicate(data, company, title, url=None, ref=None):
    for j in data["jobs"]:
        if ref and j.get("ref") and str(j["ref"]).strip().lower() == str(ref).strip().lower() \
                and norm(j.get("company")) == norm(company):
            return j
        if url and (j.get("url") == url or url in (j.get("other_links") or [])):
            return j
        if norm(j.get("company")) == norm(company) and norm(j.get("title")) == norm(title) \
                and j.get("status") not in ("closed", "rejected", "withdrawn", "ignored"):
            return j
    return None


def add_job(data, today, company, title, url=None, ref=None, posted=None, location="", source=""):
    """Add a job, or update the existing row if it's the same job (same ref, link, or company+title)."""
    dup = find_duplicate(data, company, title, url, ref)
    if dup:
        if url and url != dup.get("url") and url not in dup.setdefault("other_links", []):
            dup["other_links"].append(url)
        dup["last_checked"] = today.isoformat()
        if posted and posted != dup.get("posted"):
            dup.setdefault("reposts", []).append(posted)
        return dup, False
    jid = slug(company, title)
    ids = {j.get("id") for j in data["jobs"]}
    base, n = jid, 2
    while jid in ids:
        jid, n = "%s-%d" % (base, n), n + 1
    row = {"id": jid, "company": company, "title": title, "location": location, "url": url or "",
           "other_links": [], "ref": ref or "", "posted": posted or "", "first_found": today.isoformat(),
           "last_checked": today.isoformat(), "status": "new", "source": source, "notes": ""}
    data["jobs"].append(row)
    return row, True


def move(data, job_id, status, today):
    if status not in STATUSES:
        raise PipelineError("unknown status %r (one of: %s)" % (status, ", ".join(STATUSES)))
    for j in data["jobs"]:
        if j.get("id") == job_id:
            old = j.get("status", "new")
            j["status"] = status
            if status == "applied" and not j.get("applied"):
                j["applied"] = today.isoformat()
            if status == "rejected" and not j.get("rejected"):
                j["rejected"] = today.isoformat()
            j["notes"] = (j.get("notes", "") + "\n%s: %s -> %s" % (today.isoformat(), old, status)).strip()
            return j
    raise PipelineError("no job with id %r" % job_id)


def rejected_on(data, job):
    """When a job was rejected: its 'rejected' field, the dated note that moved it, or its last activity."""
    d = day_or_none(job.get("rejected"))
    if d:
        return d
    for line in reversed(str(job.get("notes", "")).splitlines()):
        if line.rstrip().endswith("-> rejected"):
            d = day_or_none(line[:10])
            if d:
                return d
    return last_activity(data, job)


def contact_check(data, contact_id, today, job_id=None):
    """Run before drafting or sending anything to one person.

    Returns (verdict, reasons): STOP (never contact), CHECK (tell the person each
    reason before they decide) or OK.
    """
    c = next((x for x in data["contacts"] if x.get("id") == contact_id), None)
    if c is None:
        raise PipelineError("no contact with id %r" % contact_id)
    name = c.get("name") or contact_id
    company = c.get("company", "")
    stop, check = [], []
    if c.get("do_not_contact"):
        stop.append("%s asked not to be contacted: never again, on any channel" % name)
    if not c.get("employer_checked"):
        check.append("UNVERIFIED: search results go out of date. Open %s's profile and check they still work at %s"
                     % (name, company or "this company"))
    jobs = {j.get("id"): j for j in data["jobs"]}
    linked = {o.get("job_id") for o in data["outreach"] if o.get("contact_id") == contact_id}
    for a in data["applications"]:
        ids = [x.get("id") if isinstance(x, dict) else x for x in a.get("contacts", []) or []]
        if contact_id in ids:
            linked.add(a.get("job_id"))
    seen = set()
    for jid in sorted(x for x in linked if x):
        j = jobs.get(jid)
        if j and j.get("status") == "rejected":
            seen.add(jid)
            check.append("%s is linked to your application for %s at %s, which was rejected on %s"
                         % (name, j.get("title"), j.get("company"), rejected_on(data, j)))
    if RECRUITER_RE.search(str(c.get("role", ""))) and company:
        for j in data["jobs"]:
            if j.get("id") in seen or j.get("status") != "rejected" or norm(j.get("company")) != norm(company):
                continue
            d = rejected_on(data, j)
            if d and (today - d).days <= REJECTION_WINDOW:
                check.append("%s recruits at %s, which rejected you for %s on %s: may be the same recruiter"
                             % (name, j.get("company"), j.get("title"), d))
    if company:
        bucket = "recruiting" if RECRUITER_RE.search(str(c.get("role", ""))) else "the team"
        others = {}
        by_id = {x.get("id"): x for x in data["contacts"]}
        for o in data["outreach"]:
            oc = by_id.get(o.get("contact_id"))
            if not oc or oc.get("id") == contact_id or norm(oc.get("company")) != norm(company):
                continue
            ob = "recruiting" if RECRUITER_RE.search(str(oc.get("role", ""))) else "the team"
            for m in o.get("messages", []) or []:
                try:
                    d = datetime.date.fromisoformat(str(m.get("date"))[:10])
                except ValueError:
                    continue
                if m.get("direction") == "out" and ob == bucket and 0 <= (today - d).days <= TEAM_WINDOW:
                    others[oc.get("name") or oc.get("id")] = d
        if len(others) >= TEAM_CAP:
            check.append("you've already written to %d people in %s at %s in the last 2 weeks (%s): wait, or pick "
                         "someone in another part of the company" % (len(others), bucket, company,
                                                                     ", ".join(sorted(others))))
    if job_id and job_id not in jobs:
        raise PipelineError("no job with id %r" % job_id)
    if stop:
        return "STOP", stop + check
    return ("CHECK" if check else "OK"), check


def coverage(data, task="watched"):
    """Watched companies the last run of a task didn't account for, and skips without a reason."""
    runs = [r for r in data["run_log"] if task.lower() in str(r.get("task", "")).lower()]
    if not runs:
        raise PipelineError("no run of %r in the run log yet" % task)
    cov = runs[-1].get("coverage") or {}
    names = [w.get("company") or w.get("name") for w in data.get("watched", []) if isinstance(w, dict)]
    low = {norm(k): v for k, v in cov.items()}
    missing = [n for n in names if n and norm(n) not in low]
    skipped = {k: v for k, v in cov.items() if str(v).startswith("not checked")}
    return missing, skipped


def queue_add(data, job_id, today):
    for j in data["jobs"]:
        if j.get("id") == job_id:
            j["apply_queue"] = {"added": today.isoformat()}
            return j
    raise PipelineError("no job with id %r" % job_id)


def queue_list(data):
    """Each queued job and what's ready: pack, answers, referral drafts."""
    rows = []
    apps = {a.get("job_id"): a for a in data["applications"]}
    for j in data["jobs"]:
        if not j.get("apply_queue") or j.get("status") in APPLIED_OR_LATER:
            continue
        a = apps.get(j["id"], {})
        drafts = [o for o in data["outreach"] if o.get("job_id") == j["id"] and o.get("status") == "drafted"]
        ready = {"pack": bool(a.get("pack_made")), "answers": bool(a.get("answers")), "referral drafts": len(drafts)}
        todo = [k for k in ("pack", "answers") if not ready[k]]
        rows.append({"job": j["id"], "company": j.get("company"), "title": j.get("title"), "url": j.get("url"),
                     "ready": ready, "to do before the session": todo})
    return rows


def last_activity(data, job):
    dates = [day_or_none(job.get(f)) for f in ("applied", "last_update", "last_reply", "last_follow_up")]
    dates += [day_or_none(iv.get("date")) for iv in job.get("interviews", [])]
    for o in data["outreach"]:
        if o.get("job_id") == job.get("id"):
            dates += [day_or_none(m.get("date")) for m in o.get("messages", [])]
    for line in str(job.get("notes", "")).splitlines():
        dates.append(day_or_none(line[:10]))
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def stale(data, today, days=STALE_DAYS):
    out = []
    for j in data["jobs"]:
        if j.get("status") in ("applied", "screen", "interview"):
            last = last_activity(data, j)
            if last and (today - last).days >= days:
                out.append((j, (today - last).days))
    return out


def summary(data, today):
    counts = {}
    for j in data["jobs"]:
        counts[j.get("status", "new")] = counts.get(j.get("status", "new"), 0) + 1
    week_ago = today - datetime.timedelta(days=7)
    conv = replies = apps = 0
    for o in data["outreach"]:
        got = 0
        for m in o.get("messages", []):
            d = day_or_none(m.get("date"))
            if d and week_ago < d <= today and m.get("direction") == "in":
                got += 1
        replies += got
        if got:
            conv += 1  # a conversation: someone wrote back this week
    for j in data["jobs"]:
        d = day_or_none(j.get("applied"))
        if d and week_ago < d <= today:
            apps += 1
    line = "This week: %d conversation%s, %d repl%s, %d application%s." % (
        conv, "" if conv == 1 else "s", replies, "y" if replies == 1 else "ies", apps, "" if apps == 1 else "s")
    return counts, line


def known_limits(data):
    """Company limits: the pack's list, plus any the person recorded in the companies table."""
    out = {}
    try:
        with open(os.path.join(HERE, "limits.json"), encoding="utf-8") as fh:
            for row in json.load(fh)["limits"]:
                out[norm(row["company"])] = row
    except (OSError, ValueError, KeyError):
        pass
    for c in data.get("companies", []) or []:
        if c.get("limit_max") and c.get("limit_window_days"):
            out[norm(c.get("company"))] = {"company": c.get("company"), "max": c["limit_max"],
                                           "window_days": c["limit_window_days"], "scope": c.get("limit_scope", "")}
    return out


def can_apply(data, job_id, today, cap=LIFETIME_CAP):
    """Before any application: (verdict, reasons). verdict is OK, ASK (needs the person's yes) or BLOCK."""
    job = next((j for j in data["jobs"] if j.get("id") == job_id), None)
    if not job:
        raise PipelineError("no job with id %r" % job_id)
    co = norm(job.get("company"))
    same = [j for j in data["jobs"] if norm(j.get("company")) == co and j.get("id") != job_id]
    applied = [j for j in same if j.get("status") in APPLIED_OR_LATER and day_or_none(j.get("applied"))]
    block, ask = [], []
    if job.get("status") in APPLIED_OR_LATER:
        block.append("already applied to this role on %s" % job.get("applied"))
    if len(applied) >= cap:
        block.append("%d application(s) to %s already; the cap is %d per company (raise it only if the person says so)"
                     % (len(applied), job.get("company"), cap))
    if any(day_or_none(j.get("applied")) == today for j in applied):
        block.append("already applied to %s today: one role per company per day" % job.get("company"))
    live = [j for j in same if j.get("status") in ("screen", "interview", "offer")]
    if live:
        ask.append("mid-process at %s (%s): a new application there needs the person's yes"
                   % (job.get("company"), ", ".join("%s: %s" % (j["title"], j["status"]) for j in live)))
    for j in same:
        if norm(j.get("title")) == norm(job.get("title")) and j.get("status") in APPLIED_OR_LATER \
                and "agency" in (j.get("route"), job.get("route")) and j.get("route") != job.get("route"):
            block.append("already applied to this role %s; never both through an agency and directly"
                         % ("through an agency" if j.get("route") == "agency" else "directly"))
    lim = known_limits(data).get(co)
    if lim:
        since = today - datetime.timedelta(days=int(lim["window_days"]))
        recent = [j for j in applied if day_or_none(j.get("applied")) and day_or_none(j.get("applied")) > since]
        if len(recent) >= int(lim["max"]):
            block.append("%s allows %s application(s) per %s days (%s); %d already in that window"
                         % (lim["company"], lim["max"], lim["window_days"], lim.get("scope", ""), len(recent)))
        else:
            ask.append("%s limits applications (%s per %s days, %s): make this one count"
                       % (lim["company"], lim["max"], lim["window_days"], lim.get("scope", "")))
    verdict = "BLOCK" if block else ("ASK" if ask else "OK")
    return verdict, block + ask


UNREACHABLE_TRIES = 3
UNREACHABLE_SPAN_H = 48


def stamp(s):
    s = str(s or "")
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s[:19] if "T" in s else s[:10], fmt)
        except ValueError:
            continue
    raise PipelineError("bad date/time %r (YYYY-MM-DDTHH:MM)" % s)


def unreachable(data, job_id, error, now):
    """One failed fetch. After 3 failures at least 48 hours apart (first to last), the job is closed as unreachable,
    so one outage never closes a job."""
    job = next((j for j in data["jobs"] if j.get("id") == job_id), None)
    if not job:
        raise PipelineError("no job with id %r" % job_id)
    job["fetch_attempts"] = int(job.get("fetch_attempts", 0)) + 1
    job.setdefault("first_unreachable", now.strftime("%Y-%m-%dT%H:%M"))
    job["last_fetch_error"] = re.sub(r"\s+", " ", str(error))[:200]  # a short reason, never page text
    span = (now - stamp(job["first_unreachable"])).total_seconds() / 3600
    if job["fetch_attempts"] >= UNREACHABLE_TRIES and span >= UNREACHABLE_SPAN_H:
        job["status"] = "closed"
        job["closed_reason"] = "unreachable"
        job["notes"] = (job.get("notes", "") + "\n%s: closed: page unreachable %d times over %d hours"
                        % (now.date().isoformat(), job["fetch_attempts"], span)).strip()
        return job, True
    return job, False


def reachable(data, job_id):
    for j in data["jobs"]:
        if j.get("id") == job_id:
            for f in ("fetch_attempts", "first_unreachable", "last_fetch_error"):
                j.pop(f, None)
            return j
    raise PipelineError("no job with id %r" % job_id)


def csv_safe(v):
    """A cell from a job ad must never run as a spreadsheet formula."""
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def export(data, what, out):
    rows = data.get(what) or []
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([csv_safe(json.dumps(r.get(c), ensure_ascii=False) if isinstance(r.get(c), (list, dict))
                                 else r.get(c, "")) for c in cols])
    return len(rows)


def main(argv=None):
    p = argparse.ArgumentParser(description="The job list snapshot: schema, checks and summaries.")
    p.add_argument("--file", default=DEFAULT_FILE)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("validate")
    a = sub.add_parser("add-job")
    for f in ("company", "title"):
        a.add_argument("--" + f, required=True)
    for f in ("url", "ref", "posted", "location", "source", "today"):
        a.add_argument("--" + f)
    m = sub.add_parser("move")
    m.add_argument("job_id")
    m.add_argument("status")
    m.add_argument("--today")
    for name in ("summary", "stale"):
        s = sub.add_parser(name)
        s.add_argument("--today")
    c = sub.add_parser("can-apply")
    c.add_argument("job_id")
    c.add_argument("--today")
    c.add_argument("--cap", type=int, default=LIFETIME_CAP)
    u = sub.add_parser("unreachable")
    u.add_argument("job_id")
    u.add_argument("--error", required=True)
    u.add_argument("--now", help="YYYY-MM-DDTHH:MM (default: now)")
    r = sub.add_parser("reachable")
    r.add_argument("job_id")
    cv = sub.add_parser("coverage")
    cv.add_argument("--task", default="watched")
    q = sub.add_parser("queue")
    q.add_argument("action", choices=("add", "list", "remove"))
    q.add_argument("job_id", nargs="?")
    q.add_argument("--today")
    cc = sub.add_parser("contact-check")
    cc.add_argument("contact_id")
    cc.add_argument("--job")
    cc.add_argument("--today")
    e = sub.add_parser("export")
    e.add_argument("--what", default="jobs", choices=TABLES + OTHER_TABLES)
    e.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        if a.cmd == "init":
            if os.path.exists(a.file):
                print("%s already exists; nothing changed" % a.file)
            else:
                save(a.file, empty())
                print("created %s" % a.file)
            return 0
        data = load(a.file)
        if a.cmd == "validate":
            errs, warns = validate(data)
            for w in warns:
                print("WARN  " + w)
            for e in errs:
                print("ERROR " + e)
            print("OK" if not errs else "%d error(s)" % len(errs))
            return 1 if errs else 0
        if a.cmd == "add-job":
            row, new = add_job(data, today_from(a.today), a.company, a.title, a.url, a.ref, a.posted,
                               a.location or "", a.source or "")
            save(a.file, data)
            print(("added " if new else "already listed, updated ") + row["id"])
            return 0
        if a.cmd == "move":
            row = move(data, a.job_id, a.status, today_from(a.today))
            save(a.file, data)
            print("%s is now %s" % (row["id"], row["status"]))
            return 0
        if a.cmd == "summary":
            counts, line = summary(data, today_from(a.today))
            print(line)
            for s in STATUSES:
                if counts.get(s):
                    print("  %-10s %d" % (s, counts[s]))
            return 0
        if a.cmd == "stale":
            rows = stale(data, today_from(a.today))
            for j, n in rows:
                print("STALE %s (%s, %s): no news for %d days" % (j["id"], j["company"], j["title"], n))
            if not rows:
                print("nothing stale")
            return 0
        if a.cmd == "can-apply":
            verdict, reasons = can_apply(data, a.job_id, today_from(a.today), a.cap)
            print(verdict)
            for r in reasons:
                print("  - " + r)
            return {"OK": 0, "ASK": 3, "BLOCK": 1}[verdict]
        if a.cmd == "unreachable":
            now = stamp(a.now) if a.now else datetime.datetime.now()
            job, closed = unreachable(data, a.job_id, a.error, now)
            save(a.file, data)
            print(("closed as unreachable after %d tries" if closed else "unreachable (try %d); it stays open")
                  % job["fetch_attempts"])
            return 0
        if a.cmd == "reachable":
            reachable(data, a.job_id)
            save(a.file, data)
            print("reachable again")
            return 0
        if a.cmd == "coverage":
            missing, skipped = coverage(data, a.task)
            for n in missing:
                print("NOT ACCOUNTED FOR  %s: check it, or record 'not checked: <reason>'" % n)
            for n, why in skipped.items():
                print("SKIPPED            %s: %s" % (n, why))
            print("every watched company accounted for" if not missing else "%d not accounted for" % len(missing))
            return 1 if missing else 0
        if a.cmd == "queue":
            if a.action == "list":
                print(json.dumps(queue_list(data), indent=1, ensure_ascii=False))
                return 0
            if not a.job_id:
                raise PipelineError("which job? give its id")
            if a.action == "add":
                queue_add(data, a.job_id, today_from(a.today))
            else:
                for j in data["jobs"]:
                    if j.get("id") == a.job_id:
                        j.pop("apply_queue", None)
            save(a.file, data)
            print("%s %s the apply list" % (a.job_id, "added to" if a.action == "add" else "removed from"))
            return 0
        if a.cmd == "contact-check":
            verdict, reasons = contact_check(data, a.contact_id, today_from(a.today), a.job)
            print(verdict)
            for r in reasons:
                print("  - " + r)
            return {"OK": 0, "CHECK": 3, "STOP": 1}[verdict]
        if a.cmd == "export":
            n = export(data, a.what, a.out)
            print("wrote %d row(s) to %s" % (n, a.out))
            return 0
    except PipelineError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
