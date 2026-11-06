#!/usr/bin/env python3
"""The 5-minute morning session: everything that needs the person, ranked, cut to fit their time.

    python3 today.py --file jobsearch/pipeline.json [--budget 300] [--evidence EVIDENCE.md] [--today 2026-11-09] [--json]

Gathers what only the person can do, from the job list:
  BOOK        a reply that says yes to a chat or asks for interview times
              (outreach rows marked booking: offer the times booking.py found)
  REPLY       someone answered and it's the person's turn (followup.py's YOUR TURN)
  THANK-YOU   within a day of an interview
  APPLY       queued applications with their pack ready (deadline soon first, then Fit)
  CHAT ASK    a chat request to someone who accepted a connection request
  SEND        other drafted messages (after-applying notes, asks) and due nudges
  CONNECT     today's connection queue, done together in one connection session
and ranks them by how directly they lead to a chat or an interview, then keeps
only what fits the person's daily time (default 5 minutes), each with a rough
time for one tap or a quick check. The rest waits for tomorrow, and the list
says what waited. Times are estimates for approving prepared items, not for
writing anything.

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

SECONDS = {"BOOK": 30, "REPLY": 30, "THANK-YOU": 20, "APPLY": 45, "CHAT ASK": 15, "SEND": 15, "CONNECT": 7}
VALUE = {"BOOK": 100, "REPLY": 90, "THANK-YOU": 85, "APPLY": 60, "CHAT ASK": 70, "SEND": 45, "CONNECT": 20}


def items(data, today):
    out = []
    contacts = {c.get("id"): c for c in data.get("contacts", [])}
    jobs = {j.get("id"): j for j in data.get("jobs", [])}
    for o in data.get("outreach", []):
        c = contacts.get(o.get("contact_id"), {})
        who = c.get("name") or o.get("contact_id")
        if o.get("booking") and not o.get("booked"):
            out.append(("BOOK", "%s: %s - send the times" % (who, o["booking"]), 0))
        elif o.get("status") == "drafted" and o.get("stage") == "invite":
            continue
        elif o.get("status") == "drafted":
            kind = "CHAT ASK" if o.get("stage") == "chat" else "SEND"
            job = jobs.get(o.get("job_id"), {})
            out.append((kind, "%s%s: %s" % (who, (" (%s)" % job.get("company")) if job else "",
                                            o.get("why") or o.get("stage") or "message"), 0))
    groups = due(data, today)
    for msg in groups.get("YOUR TURN", []):
        out.append(("REPLY", msg, 0))
    for msg in groups.get("DUE NOW", []):
        kind = "THANK-YOU" if msg.startswith("thank-you") else "SEND"
        out.append((kind, msg, 0))
    for j in data.get("jobs", []):
        if j.get("apply_queue") and j.get("status") not in ("applied", "screen", "interview", "offer", "rejected",
                                                          "closed", "withdrawn"):
            dl = day(j.get("deadline"))
            soon = dl is not None and 0 <= (dl - today).days <= 3
            bonus = (25 if soon else 0) + int((j.get("fit") or j.get("career_value") or 0) / 10)
            out.append(("APPLY", "%s, %s%s" % (j.get("company"), j.get("title"),
                                                " (closes %s)" % dl if soon else ""), bonus))
    invites = [o for o in data.get("outreach", []) if o.get("stage") == "invite" and o.get("status") == "drafted"]
    if invites:
        out.append(("CONNECT", "%d people in today's connection queue" % len(invites), 0, len(invites)))
    return out


def plan(data, today, budget=300):
    ranked = sorted(items(data, today), key=lambda x: -(VALUE[x[0]] + x[2]))
    keep, later, used = [], [], 0
    for it in ranked:
        kind, text = it[0], it[1]
        if kind == "CONNECT":
            n = it[3]
            fit = max(0, min(n, (budget - used) // SECONDS["CONNECT"]))
            if fit:
                keep.append({"kind": kind, "item": "%d of %d people in the connection queue" % (fit, n),
                             "seconds": fit * SECONDS["CONNECT"]})
                used += fit * SECONDS["CONNECT"]
            if fit < n:
                later.append({"kind": kind, "item": "%d connection requests" % (n - fit)})
            continue
        if used + SECONDS[kind] <= budget:
            keep.append({"kind": kind, "item": text, "seconds": SECONDS[kind]})
            used += SECONDS[kind]
        else:
            later.append({"kind": kind, "item": text})
    return {"today": keep, "minutes": round(used / 60.0, 1), "waits_for_tomorrow": later}


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
    p.add_argument("--today")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    r = plan(json.load(open(a.file, encoding="utf-8")), today, a.budget)
    r["when_you_have_10_minutes"] = extra(a.evidence, today)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print("TODAY, about %s minutes:" % r["minutes"])
    for i, x in enumerate(r["today"], 1):
        print("%2d. %-9s %s" % (i, x["kind"], x["item"]))
    if r["waits_for_tomorrow"]:
        print("Waits for tomorrow: %d item(s)" % len(r["waits_for_tomorrow"]))
    for x in r["when_you_have_10_minutes"]:
        print("When you have 10 minutes: %s" % x["item"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
