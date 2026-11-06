#!/usr/bin/env python3
"""The person got the job: close everything kindly, thank everyone, stop the tasks, and tidy the data.

    python3 wrapup.py plan --file jobsearch/pipeline.json --job acme-account-executive [--today 2026-12-01]
    python3 wrapup.py anonymise --file jobsearch/pipeline.json [--older-than 365 | --all] --yes

plan lists, for the person to approve in one card:
  withdraw  every other live application (applied, screen, interview, offer), each with a
            short, gracious withdrawal email draft to the recruiter or contact
  thank     everyone who helped: referrers, people who had a chat, who replied, or who
            passed the CV on, with a thank-you draft that says where the person landed
  pause     the automatic tasks to stop (all the job-search ones) and the streak, ended
            with a final count rather than broken
  linkedin  the profile steps: new role, Open to Work off, headline updated
  keep      what's worth keeping: the achievement bank, CVs, story grid, and the network
  data      contact details of people who aren't friends or colleagues get anonymised
            after 30 days, on the person's yes
  celebrate one line, with the numbers: days, applications, chats, interviews.
anonymise (only with --yes, the person's yes for this): removes names, emails, phone
numbers and profile links of contacts with no outreach in the period (or all, after
wrap-up), keeping company, role and dates so the counts still work. Personal data is
kept only as long as the search needs it. To delete everything, the person deletes the
job list page and the project files themselves.
"""

import argparse
import datetime
import json
import sys

LIVE = ("applied", "screen", "interview", "offer")
HELPED = ("replied", "booked")
PII = ("name", "email", "phone", "profile", "linkedin", "url", "personal_email", "notes")


def day(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def plan(data, job_id, today):
    jobs = {j.get("id"): j for j in data.get("jobs", [])}
    won = jobs.get(job_id)
    if not won:
        raise SystemExit("no job %s" % job_id)
    contacts = {c.get("id"): c for c in data.get("contacts", [])}
    withdraw = [{"job": j.get("id"), "company": j.get("company"), "title": j.get("title"), "status": j.get("status"),
                 "draft": "Thank you for considering me for the %s role. I've accepted another offer, so I'd like to "
                          "withdraw my application. I enjoyed learning about %s and hope our paths cross again."
                          % (j.get("title"), j.get("company"))}
                for j in data.get("jobs", []) if j.get("id") != job_id and j.get("status") in LIVE]
    helpers = {}
    for o in data.get("outreach", []):
        if o.get("status") in HELPED or o.get("chat_held") or o.get("stage") in ("referral", "ask") and o.get(
                "status") == "replied":
            c = contacts.get(o.get("contact_id"), {})
            helpers[o.get("contact_id")] = c.get("name") or o.get("contact_id")
    for j in data.get("jobs", []):
        if j.get("referred_by"):
            helpers.setdefault(j["referred_by"], j["referred_by"])
    thank = [{"contact": cid, "name": n, "draft": "I wanted to let you know I've accepted a role as %s at %s. Thank "
                                                  "you for your help along the way; it made a difference."
                                                  % (won.get("title"), won.get("company"))}
             for cid, n in sorted(helpers.items(), key=lambda x: str(x[1]))]
    applied = [j for j in data.get("jobs", []) if j.get("applied")]
    first = min([day(j["applied"]) for j in applied if day(j.get("applied"))], default=today)
    chats = sum(1 for o in data.get("outreach", []) if o.get("chat_held") or o.get("booked"))
    interviews = sum(len(j.get("interviews") or []) for j in data.get("jobs", []))
    return {"won": {"company": won.get("company"), "title": won.get("title")},
            "withdraw": withdraw, "thank": thank,
            "pause": ["every 'Job search:' scheduled task (pause, don't delete, in case of a restart)",
                      "the streak: ended at its final count, not broken"],
            "linkedin": ["add the new role (start date)", "turn Open to Work off", "update the headline",
                         "thank-you post optional, the person writes it"],
            "keep": ["the achievement bank and master CV", "the story grid", "the network table"],
            "data": "anonymise contact details of people outside the person's network after 30 days "
                    "(wrapup.py anonymise --all --yes, on the person's yes)",
            "celebrate": "%d days, %d applications, %d chats, %d interviews, and a yes from %s."
                         % ((today - first).days, len(applied), chats, interviews, won.get("company"))}


def anonymise(data, today, older_than=365, everything=False):
    last = {}
    for o in data.get("outreach", []):
        for m in o.get("messages", []) or []:
            d = day(m.get("date"))
            if d:
                last[o.get("contact_id")] = max(d, last.get(o.get("contact_id"), d))
    keep = {n.get("contact_id") for n in data.get("network", []) if isinstance(n, dict)}
    done = 0
    for c in data.get("contacts", []):
        if c.get("anonymised") or c.get("id") in keep:
            continue
        recent = last.get(c.get("id"))
        if everything or not recent or (today - recent).days > older_than:
            for k in PII:
                c.pop(k, None)
            c["name"] = "(anonymised)"
            c["anonymised"] = today.isoformat()
            done += 1
    return done


def main(argv=None):
    p = argparse.ArgumentParser(description="Wrap up a won search, and anonymise old contact data.")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--file", default="jobsearch/pipeline.json")
    pl.add_argument("--job", required=True)
    pl.add_argument("--today")
    an = sub.add_parser("anonymise")
    an.add_argument("--file", default="jobsearch/pipeline.json")
    an.add_argument("--older-than", type=int, default=365)
    an.add_argument("--all", action="store_true")
    an.add_argument("--yes", action="store_true", help="the person said yes to this")
    an.add_argument("--today")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    with open(a.file, encoding="utf-8") as fh:
        data = json.load(fh)
    if a.cmd == "plan":
        print(json.dumps(plan(data, a.job, today), indent=1, ensure_ascii=False))
        return 0
    if not a.yes:
        print("REFUSED: anonymising needs the person's yes (--yes)")
        return 1
    n = anonymise(data, today, a.older_than, a.all)
    with open(a.file, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("anonymised %d contact(s)" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
