#!/usr/bin/env python3
"""The daily session: everything that needs the person, ranked, cut to fit their time (default 5 minutes).

    python3 today.py --file jobsearch/pipeline.json [--plan MASTER_PLAN.md] [--budget 300] [--evidence EVIDENCE.md]
        [--today 2026-11-09] [--json]

First what only the person can answer: BOOK (offer the times booking.py found),
REPLY (their turn), THANK-YOU, CHAT ASK (someone accepted a connection request).
Then the jobs, one bundle each, best first (deadline soon, then Fit), up to the
plan's 'Applications a day' (default 10):
  pass 1, in the chat: APPLY (the preview card: every answer and file; Claude
    submits after the tap) and EMAIL to the two hiring-team people. SUBMIT
    instead of APPLY where the employer asks AI agents not to apply: Claude
    fills the fields and uploads the files, the person reviews and presses Submit.
  pass 2, on the page: LINKEDIN, a connection request (or a message to someone
    already connected) to the same two people for the best jobs, within the
    daily cap (16), and COMMENT where one of them posted about the role.
Then other messages, nudges and the general connection queue. Up to 16 approvals
fit in one card, so an application or email is a few seconds of the person's
time; Claude's filling and submitting happen afterwards. If no job is queued,
the streak-keeper (a real, open job below the usual Fit) is offered so the streak
can go on. With --plan, the result opens with the streak (streak.py).

With --evidence, a current or recent role that's thin on evidence (job-cv's
depth.py) is offered once a day as "when you have 10 minutes": a spoken
interview about it. It sits outside the daily time, and stops once the person
does it, or for 30 days if they say not now.
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from followup import due, day  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", "job-connector"))

# Seconds of the person's time. Applications and emails are approved from preview cards in the chat (up to 16
# in one card), so each is a glance and a tap; Claude submits and sends afterwards. LinkedIn steps and a Submit
# the person presses themselves happen on the page: Claude opens it and fills it, the person clicks.
SECONDS = {"BOOK": 20, "REPLY": 20, "THANK-YOU": 10, "CHAT ASK": 5, "SEND": 5, "APPLY": 6, "SUBMIT": 15,
           "EMAIL": 3, "LINKEDIN": 10, "COMMENT": 12, "CONNECT": 10}
VALUE = {"BOOK": 100, "REPLY": 90, "THANK-YOU": 85, "CHAT ASK": 70, "APPLY": 60, "SEND": 45, "CONNECT": 20}
DONE = ("applied", "screen", "interview", "offer", "accepted", "rejected", "closed", "withdrawn", "ignored")
LINKEDIN_PER_JOB = 2


def _who(o, contacts):
    c = contacts.get(o.get("contact_id"), {})
    return c.get("name") or o.get("contact_id") or "someone"


def bundles(data, today):
    """One bundle per queued job: the application, then the drafted touches to its hiring team."""
    contacts = {c.get("id"): c for c in data.get("contacts", [])}
    rows = {}
    for o in data.get("outreach", []):
        if o.get("status") == "drafted" and o.get("job_id"):
            rows.setdefault(o["job_id"], []).append(o)
    out = []
    for j in data.get("jobs", []):
        q = j.get("apply_queue")
        if not q or j.get("status") in DONE:
            continue
        dl = day(j.get("deadline"))
        soon = dl is not None and 0 <= (dl - today).days <= 3
        q = q if isinstance(q, dict) else {}
        b = {"job_id": j.get("id"), "label": "%s, %s%s" % (j.get("company"), j.get("title"),
                                                         " (closes %s)" % dl if soon else ""),
             "value": VALUE["APPLY"] + (25 if soon else 0) + int((j.get("fit") or j.get("career_value") or 0) / 10),
             "person_submits": bool(q.get("person_submits")), "streak_keeper": bool(q.get("streak_keeper")),
             "emails": [], "linkedin": [], "invites": [], "comment": None}
        for o in rows.get(j.get("id"), []):
            if o.get("channel") == "email":
                b["emails"].append(_who(o, contacts))
            elif o.get("stage") == "comment":
                if o.get("about_role"):
                    b["comment"] = _who(o, contacts)
            elif o.get("channel") == "linkedin" and o.get("stage") in ("invite", "note"):
                b["invites"].append(_who(o, contacts))
            elif o.get("channel") in ("linkedin", "handshake"):
                b["linkedin"].append(_who(o, contacts))
        out.append(b)
    out.sort(key=lambda b: (b["streak_keeper"], -b["value"]))
    return out


def items(data, today):
    out = []
    contacts = {c.get("id"): c for c in data.get("contacts", [])}
    queued = {j.get("id") for j in data.get("jobs", []) if j.get("apply_queue") and j.get("status") not in DONE}
    for o in data.get("outreach", []):
        who = _who(o, contacts)
        if o.get("booking") and not o.get("booked"):
            out.append(("BOOK", "%s: %s - send the times" % (who, o["booking"]), 0))
        elif o.get("status") != "drafted" or o.get("stage") in ("invite", "note", "comment"):
            continue
        elif o.get("job_id") in queued:
            continue  # part of that job's bundle
        else:
            kind = "CHAT ASK" if o.get("stage") == "chat" else "SEND"
            out.append((kind, "%s: %s" % (who, o.get("why") or o.get("stage") or "message"), 0))
    groups = due(data, today)
    for msg in groups.get("YOUR TURN", []):
        out.append(("REPLY", msg, 0))
    for msg in groups.get("DUE NOW", []):
        out.append(("THANK-YOU" if msg.startswith("thank-you") else "SEND", msg, 0))
    return out


def plan(data, today, budget=300, per_day=10):
    try:
        from outreach import invite_budget  # noqa: E402
        invites_left = invite_budget(data, today)["left_today"]
    except ImportError:  # pragma: no cover
        invites_left = 0
    keep, later, used = [], [], 0

    def add(kind, text, job=None, n=1):
        nonlocal used
        sec = SECONDS[kind] * n
        if used + sec <= budget:
            keep.append({"kind": kind, "item": text, "seconds": sec, "job_id": job})
            used += sec
            return True
        later.append({"kind": kind, "item": text, "job_id": job})
        return False

    singles = sorted(items(data, today), key=lambda x: -(VALUE[x[0]] + x[2]))
    for kind, text, _ in [x for x in singles if VALUE[x[0]] >= VALUE["CHAT ASK"]]:
        add(kind, text)
    # Pass 1, in the chat: every job's application and its two emails (a glance and a tap each).
    jobs_done, done = 0, []
    all_b = bundles(data, today)
    real = [b for b in all_b if not b["streak_keeper"]]
    for b in (real or all_b[:1]):
        if jobs_done >= per_day:
            later.append({"kind": "APPLY", "item": b["label"], "job_id": b["job_id"]})
            continue
        label = b["label"] + (" (you press Submit: the employer asks AI agents not to apply)"
                              if b["person_submits"] else "") + (
            " (keeps your streak: below your usual Fit)" if b["streak_keeper"] else "")
        if not add("SUBMIT" if b["person_submits"] else "APPLY", label, b["job_id"]):
            continue
        jobs_done += 1
        done.append(b)
        for who in b["emails"][:2]:
            add("EMAIL", "%s: email to %s" % (b["label"], who), b["job_id"])
    # Pass 2, on the page: LinkedIn for the best jobs first (2 people each, within the daily cap), then a
    # comment where someone on the hiring team posted about the role.
    for b in done:
        n_inv = min(LINKEDIN_PER_JOB, len(b["invites"]), invites_left)
        for who in b["invites"][:n_inv]:
            if add("LINKEDIN", "%s: connection request to %s" % (b["label"], who), b["job_id"]):
                invites_left -= 1
        for who in b["linkedin"][:LINKEDIN_PER_JOB]:
            add("LINKEDIN", "%s: LinkedIn message to %s" % (b["label"], who), b["job_id"])
        if b["comment"]:
            add("COMMENT", "%s: comment on %s's post about the role" % (b["label"], b["comment"]), b["job_id"])
    for kind, text, _ in [x for x in singles if VALUE[x[0]] < VALUE["CHAT ASK"]]:
        add(kind, text)
    queue = [o for o in data.get("outreach", []) if o.get("stage") in ("invite", "note") and o.get("status") ==
             "drafted" and not o.get("job_id")]
    n = min(len(queue), invites_left, max(0, (budget - used) // SECONDS["CONNECT"]))
    if n:
        add("CONNECT", "%d people in the connection queue" % n, n=n)
    if len(queue) > n:
        later.append({"kind": "CONNECT", "item": "%d connection requests" % (len(queue) - n)})
    taps_chat = sum(1 for x in keep if x["kind"] in ("APPLY", "EMAIL", "SEND", "CHAT ASK", "THANK-YOU", "BOOK", "REPLY"))
    return {"today": keep, "minutes": round(used / 60.0, 1), "jobs": jobs_done,
            "approve_in_chat": taps_chat, "on_the_page": len(keep) - taps_chat,
            "no_application_ready": jobs_done == 0, "waits_for_tomorrow": later}


def extra(evidence_path, today):
    """The experience interview, offered outside the daily time when a recent role is thin."""
    if not evidence_path or not os.path.exists(evidence_path):
        return []
    sys.path.insert(0, os.path.join(HERE, "..", "job-cv"))
    import depth  # noqa: E402
    with open(evidence_path, encoding="utf-8") as fh:
        todo = [r for r in depth.roles(fh.read(), today) if r["offer"]]
    if not todo:
        return []
    r = todo[0]
    return [{"kind": "INTERVIEW ME", "minutes": 10,
             "role": r["role"],
             "item": "%s (%s) %s: a 10-minute spoken interview fixes it. Say 'Interview me' or 'Not now'."
                     % ("Your newest role" if r["newest"] else "A recent role", ", ".join(r["role"].split(", ")[:2]),
                        "isn't in your evidence" if r["status"] == "MISSING" else "is thin on evidence")}]


def main(argv=None):
    p = argparse.ArgumentParser(description="The ranked 5-minute morning session.")
    p.add_argument("--file", default="jobsearch/pipeline.json")
    p.add_argument("--budget", type=int, default=300, help="seconds the person gives it each day (default 300)")
    p.add_argument("--evidence", help="EVIDENCE.md: offer the experience interview when a recent role is thin")
    p.add_argument("--plan", help="MASTER_PLAN.md: applications a day and the streak (streak.py)")
    p.add_argument("--today")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    with open(a.file, encoding="utf-8") as fh:
        data = json.load(fh)
    settings = None
    if a.plan and os.path.exists(a.plan):
        import streak  # noqa: E402
        with open(a.plan, encoding="utf-8") as fh:
            settings = streak.read_plan(fh.read())
    r = plan(data, today, a.budget, settings["per_day"] if settings else 10)
    r["when_you_have_10_minutes"] = extra(a.evidence, today)
    if settings:
        s = streak.status(data, settings, today)
        ready = ("Your %d job%s ready: about %s minutes, %d taps in the chat and %d clicks on the page. Say Go."
                 % (r["jobs"], " is" if r["jobs"] == 1 else "s are", r["minutes"], r["approve_in_chat"],
                    r["on_the_page"]) if r["jobs"] else
                 "No application is ready yet: say Go and Claude finds one to keep your streak.")
        r["streak"] = s
        r["welcome"] = streak.welcome(s, ready)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    if r.get("welcome"):
        print(r["welcome"])
    print("TODAY, %d job%s, about %s minutes:" % (r["jobs"], "" if r["jobs"] == 1 else "s", r["minutes"]))
    for i, x in enumerate(r["today"], 1):
        print("%2d. %-9s %s" % (i, x["kind"], x["item"]))
    if r["waits_for_tomorrow"]:
        print("Waits for tomorrow: %d item(s)" % len(r["waits_for_tomorrow"]))
    for x in r["when_you_have_10_minutes"]:
        print("When you have 10 minutes: %s" % x["item"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
