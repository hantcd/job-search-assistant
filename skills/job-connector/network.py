#!/usr/bin/env python3
"""People the person already knows at each job's company, from their LinkedIn connections export.

    python3 network.py match --file jobsearch/pipeline.json [--job <id>] [--top 5] [--write] [--today 2026-11-06]
    python3 network.py rank --file jobsearch/pipeline.json --job <id> [--manager "Head of Sales Development"] [--top 3]
    python3 network.py route --file jobsearch/pipeline.json --job <id> [--today 2026-11-06]
    python3 network.py plan --file jobsearch/pipeline.json --job <id> [--manager "..."] [--today 2026-11-06]

plan: who to contact for one job, in two waves, as a fallback if the first people
don't answer: up to 4 people (the hiring manager, the recruiter and 1-2 on the
team), the best 2 now (one in recruiting and one on the team where both exist),
the next 2 only if nobody has replied after 3 working days, never more than 2 in
recruiting or 2 on the team, and a different message for each (they compare
notes). From Wonsulting's 'pivot to a peer' and Management Consulted's 2/2/2 rule.

route: REFERRAL FIRST or APPLY NOW + REACH OUT for one job, with the dates.
  REFERRAL FIRST  someone who knows the person or their work is at the company (tie_strength
                  set, or knows_work), the job isn't closing within 5 days, and the person hasn't
                  applied there in the last 6 months: ask today, apply after at most 2 working
                  days whatever happens (the referral should go in before the application,
                  since many systems credit whichever came first), one nudge, then stop.
  APPLY NOW + REACH OUT  everything else: apply today, then the same day one message each
                  to the 2-3 people best for the role (rank), one nudge after 5 working days,
                  then stop. A referral after applying can still help as a word to the recruiter.
  ALREADY APPLIED  ask the best-placed person for a word with the recruiter, not a referral.

rank: who to contact for one job, from everyone known about it: the person's
connections there and the people found for it (Google, the company site).
The best people FOR THE ROLE come first, whether or not the person knows them:
the likely hiring manager, then senior people on the team, then the team, then
a recruiter for that team; what they share with the person (school, city, a
past employer) and an existing connection only break ties. Each comes with the
first step: a message (already connected), a connection request with a short
note, or an email for a hiring manager.

For every open job (or one), finds the person's first-degree connections at
that company and ranks them for a referral: the same function as the job
first (sales, engineering, product...), then people senior enough to be the
hiring manager or close to them, then known ties and recent connections. With
--write, the top ones go into the contacts table (found_how: the connections
export, employer UNVERIFIED until the person checks the profile, since the
export can be out of date) and each job gets a people_you_know summary for
its alert. This runs for every job that passes the gates, not only the ones
that get a pack: it needs no web access and takes a second.

The network table is private: used only for referral suggestions, never
shared, never contacted without the person's yes for each message.
Standard library only.
"""

import argparse
import datetime
import json
import os
import re
import sys
import unicodedata

FUNCTIONS = {
    "sales": r"sales|business development|\bbdr\b|\bsdr\b|\badr\b|account (?:executive|manager|development)|"
             r"partnership|revenue|growth|go.to.market|\bgtm\b|commercial|inside sales",
    "customer": r"customer success|account management|client (?:success|portfolio|relationship)|onboarding|support",
    "solutions": r"solutions? (?:engineer|architect|consultant)|architect|sales engineer|pre.?sales|technical account|"
                 r"forward deployed|implementation",
    "engineering": r"engineer|developer|software|platform|infrastructure|devops|\bsre\b",
    "data": r"\bdata\b|analytics|analyst|machine learning|\bml\b|\bai\b|scientist",
    "product": r"product (?:manager|management|owner|ops)|\bpm\b",
    "design": r"design|ux|ui\b",
    "marketing": r"marketing|brand|content|communications|\bpr\b",
    "finance": r"finance|accounting|\bfx\b|treasury|payments? operations",
    "people": r"recruit|talent|people (?:partner|team|ops)|\bhr\b|human resources",
    "operations": r"operations|\bops\b|strategy|chief of staff|founder'?s associate",
}
FUNC_RE = {k: re.compile(v, re.I) for k, v in FUNCTIONS.items()}
GTM = {"sales", "customer", "solutions"}  # one go-to-market organisation in most companies
SENIOR = re.compile(r"\b(?:manager|head|lead|director|vp|vice president|chief|founder|principal)\b", re.I)
SUFFIX = re.compile(r"\b(?:ltd|limited|inc|plc|llc|gmbh|dac|teoranta|corp|corporation|co|group|holdings|ireland|uk|emea)\b")


def norm_company(s):
    s = re.sub(r"\(.*?\)", " ", str(s or "").lower())
    s = re.sub(r"[^a-z0-9& ]+", " ", s)
    s = SUFFIX.sub(" ", s)
    return " ".join(s.split())


def same_company(job_company, conn_company):
    a, b = norm_company(job_company), norm_company(conn_company)
    if not a or not b:
        return False
    return a == b or b.startswith(a + " ") or a.startswith(b + " ")


def functions(text):
    return {k for k, rx in FUNC_RE.items() if rx.search(text or "")}


def score(conn, job_funcs, today):
    pos = conn.get("position") or ""
    pf = functions(pos)
    s, why = 0, []
    if job_funcs & pf:
        s += 50
        why.append("same function (%s)" % ", ".join(sorted(job_funcs & pf)))
    elif job_funcs & GTM and pf & GTM:
        s += 35
        why.append("same go-to-market organisation")
    if "people" in pf:
        s += 20
        why.append("recruiting")
    if SENIOR.search(pos) and (job_funcs & pf or (job_funcs & GTM and pf & GTM)):
        s += 25
        why.append("senior on that team: may be the hiring manager or close to them")
    elif SENIOR.search(pos):
        s += 8
    if str(conn.get("tie_strength", "")).lower() not in ("", "unknown"):
        s += 15
        why.append("you know them (%s)" % conn.get("tie_strength"))
    try:
        age = (today - datetime.date.fromisoformat(str(conn.get("connected_on"))[:10])).days
        if age < 730:
            s += 5
    except ValueError:
        pass
    return s, why or ["works there"]


def contact_id(conn, company):
    s = unicodedata.normalize("NFKD", "%s %s" % (conn.get("name", ""), company))
    s = s.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def match(data, today, job_id=None, top=5):
    net = [r for r in data.get("network", []) if isinstance(r, dict)]
    out = {}
    for j in data.get("jobs", []):
        if job_id and j.get("id") != job_id:
            continue
        if not job_id and j.get("status") not in ("new", "open", "applied", "screen", "interview"):
            continue
        jf = functions(j.get("title", "")) or functions(j.get("role_family", ""))
        found = [c for c in net if same_company(j.get("company"), c.get("company"))]
        ranked = sorted(((score(c, jf, today), c) for c in found), key=lambda x: -x[0][0])
        out[j["id"]] = {
            "company": j.get("company"), "title": j.get("title"), "total": len(found),
            "same_function": sum(1 for (s, why), c in ranked if s >= 35),
            "top": [{"name": c.get("name"), "position": c.get("position"), "linkedin": c.get("linkedin"),
                     "connected_on": c.get("connected_on"), "why": "; ".join(why), "score": s}
                    for (s, why), c in ranked[:top]],
        }
    return out


def write(data, matches, today):
    contacts = {c.get("id"): c for c in data.setdefault("contacts", [])}
    added = 0
    for jid, m in matches.items():
        ids = []
        for p in m["top"]:
            cid = contact_id(p, m["company"])
            ids.append(cid)
            if cid in contacts:
                continue
            row = {"id": cid, "name": p["name"], "role": p.get("position", ""), "company": m["company"],
                   "linkedin": p.get("linkedin", ""), "email_confidence": "", "privacy_risk": "",
                   "found_how": "your LinkedIn connections export (connected %s)" % (p.get("connected_on") or "?"),
                   "in_common": "first-degree connection", "employer_checked": "", "referred": False,
                   "notes": "%s: %s" % (today.isoformat(), p["why"])}
            data["contacts"].append(row)
            contacts[cid] = row
            added += 1
        for j in data["jobs"]:
            if j.get("id") == jid:
                j["people_you_know"] = {"total": m["total"], "same_function": m["same_function"], "contacts": ids,
                                        "checked": today.isoformat()}
    return added


COMMON = re.compile(r"school|college|university|alum|grad|same city|city|past employer|worked at|former|first-degree", re.I)


def rank(data, job_id, manager_titles=(), top=3, today=None):
    today = today or datetime.date.today()
    job = next((j for j in data.get("jobs", []) if j.get("id") == job_id), None)
    if job is None:
        raise ValueError("no job with id %r" % job_id)
    jf = functions(job.get("title", "")) or functions(job.get("role_family", ""))
    mgr_words = [set(re.findall(r"[a-z]{3,}", t.lower())) - {"the", "and", "for"} for t in manager_titles]
    net = {norm_company(c.get("company")) + "|" + (c.get("name") or "").lower(): c
           for c in data.get("network", []) if same_company(job.get("company"), c.get("company"))}
    people = {}
    for c in data.get("contacts", []):
        if same_company(job.get("company"), c.get("company")) and not c.get("do_not_contact"):
            people[(c.get("name") or "").lower()] = dict(c)
    for k, c in net.items():
        nm = (c.get("name") or "").lower()
        people.setdefault(nm, {"name": c.get("name"), "role": c.get("position", ""), "company": job.get("company"),
                               "linkedin": c.get("linkedin", ""), "in_common": "first-degree connection"})
    out = []
    for nm, p in people.items():
        role = p.get("role") or ""
        pf = functions(role)
        rw = set(re.findall(r"[a-z]{3,}", role.lower()))
        s, why = 5, []
        if any(w and len(w & rw) >= max(2, len(w) - 1) for w in mgr_words):
            s, why = 60, ["likely the hiring manager (the ad: reports to %s)" % manager_titles[0]]
        elif SENIOR.search(role) and (jf & pf or (jf & GTM and pf & GTM)):
            s, why = 45, ["senior on the team: the hiring manager or close to them"]
        elif jf & pf or (jf & GTM and pf & GTM):
            s, why = 35, ["on the team"]
        elif "people" in pf:
            s, why = 25, ["recruits there"]
        else:
            why = ["works there"]
        connected = nm in {k.split("|", 1)[1] for k in net}
        common = str(p.get("in_common", ""))
        if COMMON.search(common.replace("first-degree connection", "")):
            s += 15
            why.append("shares: %s" % common)
        if connected:
            s += 10
            why.append("already connected")
        if s >= 60 and not connected:
            step = "email (hiring manager) and a connection request without a note"
        elif connected:
            step = "message (you're connected)"
        else:
            step = "connection request with a short note"
        out.append({"name": p.get("name"), "role": role, "score": s, "why": "; ".join(why), "first_step": step,
                    "verified": bool(p.get("employer_checked"))})
    out.sort(key=lambda r: -r["score"])
    return out[:top]


WARM = re.compile(r"strong|medium|close|friend|family|worked (?:with|together)|colleague|classmate|manager|know", re.I)


def add_working_days(d, n):
    while n > 0:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def knows_them(c):
    """Someone who knows the person or their work (not just a first-degree connection)."""
    if c.get("knows_work") is True:
        return True
    tie = str(c.get("tie_strength", "")).strip()
    return bool(tie) and tie.lower() not in ("unknown", "weak", "none", "no") and bool(WARM.search(tie))


def route(data, job_id, today=None):
    today = today or datetime.date.today()
    job = next((j for j in data.get("jobs", []) if j.get("id") == job_id), None)
    if job is None:
        raise ValueError("no job with id %r" % job_id)
    company = job.get("company")
    company_of = {j.get("id"): j.get("company") for j in data.get("jobs", [])}
    apps = [a for a in data.get("applications", []) if a.get("job_id") == job_id
            or same_company(company, company_of.get(a.get("job_id")) or a.get("company", ""))]
    if any(a.get("job_id") == job_id and a.get("submitted") for a in apps):
        return {"route": "ALREADY APPLIED", "why": "you've applied: ask the best-placed person for a word with the recruiter",
                "ask_on": today.isoformat(), "apply_by": None, "nudge_on": add_working_days(today, 5).isoformat(),
                "warm": []}
    warm = []
    for c in data.get("contacts", []) + data.get("network", []):
        if isinstance(c, dict) and same_company(company, c.get("company")) and not c.get("do_not_contact") \
                and knows_them(c):
            nm = c.get("name")
            if nm and nm not in warm:
                warm.append(nm)
    why = []
    closes = None
    try:
        closes = datetime.date.fromisoformat(str(job.get("deadline"))[:10]) if job.get("deadline") else None
    except ValueError:
        pass
    recent = []
    for a in apps:
        try:
            when = datetime.date.fromisoformat(str(a.get("submitted"))[:10])
        except (TypeError, ValueError):
            continue
        if (today - when).days <= 183:
            recent.append(a)
    if not warm:
        why.append("nobody there knows you or your work yet")
    if closes and (closes - today).days <= 5:
        why.append("it closes %s, too soon to wait" % closes.isoformat())
    if recent:
        why.append("you applied to %s in the last 6 months, so a referral may not count" % company)
    if warm and not why:
        return {"route": "REFERRAL FIRST",
                "why": "%s know%s you or your work: ask today, apply by the date below whatever happens"
                       % (", ".join(warm[:3]), "s" if len(warm) == 1 else ""),
                "ask_on": today.isoformat(), "apply_by": add_working_days(today, 2).isoformat(),
                "nudge_on": add_working_days(today, 2).isoformat(), "warm": warm}
    return {"route": "APPLY NOW + REACH OUT", "why": "; ".join(why) or "apply early",
            "ask_on": today.isoformat(), "apply_by": today.isoformat(),
            "nudge_on": add_working_days(today, 5).isoformat(), "warm": warm}


RECRUITING = re.compile(r"recruit|talent|sourc|\bhr\b|human resources|people (?:partner|team|ops)", re.I)


def plan(data, job_id, manager_titles=(), today=None, max_people=4):
    today = today or datetime.date.today()
    ranked = rank(data, job_id, manager_titles, top=50, today=today)
    rec = [r for r in ranked if RECRUITING.search(r.get("role") or "")]
    team = [r for r in ranked if r not in rec]
    first = []
    if team:
        first.append(team.pop(0))
    if rec:
        first.append(rec.pop(0))
    while len(first) < 2 and team:
        first.append(team.pop(0))
    counts = {"recruiting": sum(1 for r in first if RECRUITING.search(r.get("role") or "")),
              "team": sum(1 for r in first if not RECRUITING.search(r.get("role") or ""))}
    second = []
    for r in sorted(team + rec, key=lambda x: -x["score"]):
        b = "recruiting" if RECRUITING.search(r.get("role") or "") else "team"
        if counts[b] < 2 and len(first) + len(second) < max_people:
            second.append(r)
            counts[b] += 1
    later = add_working_days(today, 3).isoformat()
    return {"now": [dict(r, wave=1, send_on=today.isoformat()) for r in first],
            "if_no_reply": [dict(r, wave=2, send_on=later) for r in second]}


def summary_line(m):
    if not m["total"]:
        return "People you know: none yet (search for two on the team)"
    return "People you know: %d at %s (%d in the same function)" % (m["total"], m["company"], m["same_function"])


def main(argv=None):
    p = argparse.ArgumentParser(description="Your connections at each job's company, ranked for a referral.")
    p.add_argument("--file", default=os.path.join("jobsearch", "pipeline.json"))
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match")
    m.add_argument("--job")
    m.add_argument("--top", type=int, default=5)
    m.add_argument("--write", action="store_true")
    m.add_argument("--today")
    r = sub.add_parser("rank")
    r.add_argument("--job", required=True)
    r.add_argument("--manager", action="append", default=[])
    r.add_argument("--top", type=int, default=3)
    pl = sub.add_parser("plan")
    pl.add_argument("--job", required=True)
    pl.add_argument("--manager", action="append", default=[])
    pl.add_argument("--today")
    rt = sub.add_parser("route")
    rt.add_argument("--job", required=True)
    rt.add_argument("--today")
    for q in (r,):
        q.add_argument("--today")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    data = json.load(open(a.file, encoding="utf-8"))
    if a.cmd == "plan":
        r = plan(data, a.job, a.manager, today)
        for wave, rows in (("NOW", r["now"]), ("IF NO REPLY BY " + (r["if_no_reply"][0]["send_on"] if r["if_no_reply"] else "-"),
                                                r["if_no_reply"])):
            print(wave)
            for x in rows:
                print("  %-26s %-40s %s" % ((x["name"] or "")[:26], (x["role"] or "")[:40], x["why"]))
        print("A different message for each; at most 2 in recruiting and 2 on the team.")
        return 0
    if a.cmd == "route":
        r = route(data, a.job, today)
        print("%s: %s" % (r["route"], r["why"]))
        print("ask %s | apply by %s | one nudge %s, then stop" % (r["ask_on"], r["apply_by"] or "-", r["nudge_on"]))
        return 0
    if a.cmd == "rank":
        for r in rank(data, a.job, a.manager, a.top, today):
            print("%-26s %-40s %s | %s%s" % ((r["name"] or "")[:26], (r["role"] or "")[:40], r["why"], r["first_step"],
                                             "" if r["verified"] else " | UNVERIFIED"))
        return 0
    res = match(data, today, a.job, a.top)
    for jid, r in res.items():
        print("%s | %s: %s" % (r["company"], r["title"], summary_line(r)))
        for t in r["top"]:
            print("    %-28s %-45s %s" % (t["name"][:28], (t["position"] or "")[:45], t["why"]))
    if a.write:
        n = write(data, res, today)
        with open(a.file, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
        print("added %d contact(s); each is UNVERIFIED until you open the profile" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
