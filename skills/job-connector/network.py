#!/usr/bin/env python3
"""People the person already knows at each job's company, from their LinkedIn connections export.

    python3 network.py match --file jobsearch/pipeline.json [--job <id>] [--top 5] [--write] [--today 2026-11-06]
    python3 network.py rank --file jobsearch/pipeline.json --job <id> [--manager "Head of Sales Development"] [--top 3]

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
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    data = json.load(open(a.file, encoding="utf-8"))
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
