#!/usr/bin/env python3
"""What's due today, from the job list snapshot, with stop rules no draft can break.

    python3 followup.py due --file jobsearch/pipeline.json --today 2026-10-20
    python3 followup.py can-follow-up <contact_id> --file jobsearch/pipeline.json --today 2026-10-20

Groups (printed in this order):
  DRAFTS WAITING FOR YOUR YES   outreach drafted but not approved
  YOUR TURN                     they replied; answer them (answering is never a 'follow-up')
  DUE NOW                       outreach and application follow-ups, thank-yous, deadlines
  WAITING                       sent, nothing due yet
  STOPPED                       closed by a stop rule (and why)

Outreach cadence (working days, the 2-Hour Job Search's 3B7 rule): no reply after
3, suggest another person at the company; after 7 (10 for directors and above),
one follow-up that adds something new; a last one a week later saying it's the
last; then stop.
Stop rules, applied to the PERSON across every channel: the first 'no' or sign
of disinterest ends it; at most 2 follow-ups; nothing after 21 days of silence
(from their last reply, or the first message if they never replied); a pending
LinkedIn invitation gets no follow-up; a stop request (do_not_contact) is
honoured forever. An email and a LinkedIn request on the same day are one
opening. A reply from them resets the count. A comment on their LinkedIn post (a message
row with kind 'comment', posted by the person) is a touch, not a message: it never
counts as a follow-up, so a job's three touches are the comment, the message and
one nudge.
The referral ask (outreach stage 'ask', the route's one message): one short nudge,
then stop. REFERRAL FIRST (route 'referral_first' on the outreach row): after 2
working days with no referral, apply anyway and nudge once. APPLY NOW + REACH
OUT: the nudge after 5 working days.
Applications: a follow-up 7 days after applying with no reply, 3 days after a
reply or a test with nothing since (to the agency recruiter for agency roles),
a thank-you within a day of each interview, deadline reminders 3 days and 1 day
before closing, and 'stale' after 4 weeks with no news.

Stop-rule logic adapted from hunter-skill (MIT, Jake Schincariol). Sends nothing.
"""

import argparse
import datetime
import json
import os
import sys

STOP_WORDS = ("not interested", "no thanks", "no thank you", "please stop", "stop contacting", "unsubscribe",
              "don't contact", "do not contact", "remove me", "not hiring", "role has been filled",
              "position has been filled", "no openings", "not right now", "not at this time")


def day(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def working_days_between(a, b):
    """Working days after a, up to and including b."""
    n, d = 0, a
    while d < b:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def thread_state(o, contact, today):
    """Return (group, message) for one outreach thread."""
    msgs = sorted(o.get("messages", []), key=lambda m: str(m.get("date")))
    name = contact.get("name", o.get("contact_id"))
    if contact.get("do_not_contact") or "do not contact" in str(contact.get("notes", "")).lower():
        return "STOPPED", "%s asked not to be contacted: never again, on any channel" % name
    if o.get("status") in ("declined", "closed"):
        return "STOPPED", "%s: thread %s" % (name, o.get("status"))
    if o.get("status") == "drafted" or (o.get("draft") and not o.get("approval")):
        return "DRAFTS", "%s (%s): draft waiting for your yes" % (name, o.get("channel"))
    ins = [m for m in msgs if m.get("direction") == "in"]
    for m in ins:
        if any(w in str(m.get("text", "")).lower() for w in STOP_WORDS):
            return "STOPPED", "%s said no or not now on %s: stop, and don't argue" % (name, m.get("date"))
    if msgs and msgs[-1].get("direction") == "in" and o.get("status") != "booked":
        return "YOUR TURN", "%s replied on %s: answer them" % (name, msgs[-1].get("date"))
    comments = [m for m in msgs if m.get("direction") == "out" and m.get("kind") == "comment"]
    outs = [m for m in msgs if m.get("direction") == "out" and m.get("kind") != "comment"]
    if not outs:
        if comments:
            return "DUE NOW", "%s: you commented on their post; send the message (touch 2)" % name
        return "WAITING", "%s: nothing sent yet" % name
    last_in = day(ins[-1]["date"]) if ins else None
    after = [m for m in outs if not last_in or day(m["date"]) > last_in]
    opening_day = day(after[0]["date"]) if after else None
    follow_ups = len({m["date"][:10] for m in after if day(m["date"]) != opening_day})
    silence_from = last_in or day(outs[0]["date"])
    if (today - silence_from).days > 21:
        return "STOPPED", "%s: over 21 days of silence; stop" % name
    if follow_ups >= 2:
        return "STOPPED", "%s: two follow-ups sent; stop" % name
    if o.get("invite_pending") and o.get("channel") == "linkedin":
        return "WAITING", "%s: LinkedIn invitation pending (no follow-up on an invitation)" % name
    last_out = day(after[-1]["date"]) if after else day(outs[-1]["date"])
    wd = working_days_between(last_out, today)
    if o.get("stage") in ("ask", "nudge"):
        if follow_ups >= 1 or o.get("stage") == "nudge":
            return "STOPPED", "%s: the referral ask was nudged once; stop and thank them if they answer" % name
        first = str(o.get("route", "")).lower().replace(" ", "_").startswith("referral")
        wait = 2 if first else 5
        if wd >= wait:
            if first:
                return "DUE NOW", ("%s: the 2-day referral wait is up: apply now, then one short nudge saying "
                                   "you've applied (with the reference), then stop" % name)
            return "DUE NOW", "%s: one short nudge on the ask, then stop" % name
        return "WAITING", "%s: ask sent; one nudge after %d working days (%d so far)" % (name, wait, wd)
    wait = 10 if contact.get("senior") else 7
    if follow_ups == 0:
        if wd >= wait:
            return "DUE NOW", "%s: follow-up 1 (adds something new; use the other channel and a new weekday and time)" % name
        if wd >= 3 and not o.get("suggested_other"):
            return "DUE NOW", "%s: no reply after 3 working days; suggest another person at %s (keep this thread)" % (
                name, contact.get("company", "the company"))
        return "WAITING", "%s: follow-up 1 due after %d working days (%d so far)" % (name, wait, wd)
    if wd >= 5:
        return "DUE NOW", "%s: last follow-up (say it's the last; a third weekday and time)" % name
    return "WAITING", "%s: last follow-up due 5 working days after the first (%d so far)" % (name, wd)


def application_items(data, today):
    due, waiting = [], []
    for j in data.get("jobs", []):
        st = j.get("status")
        label = "%s, %s" % (j.get("company"), j.get("title"))
        dl = day(j.get("deadline"))
        if dl and st in ("new", "open") and (dl - today).days in (3, 1):
            due.append("deadline: %s closes in %d day(s) (%s)" % (label, (dl - today).days, dl))
        for iv in j.get("interviews", []):
            d = day(iv.get("date"))
            if d and d <= today and (today - d).days <= 1 and not iv.get("thank_you_sent"):
                due.append("thank-you: %s interview on %s (send within a day)" % (label, d))
        if st not in ("applied", "screen", "interview"):
            continue
        applied = day(j.get("applied"))
        last_reply = day(j.get("last_reply"))
        last_fu = day(j.get("last_follow_up"))
        to = "the agency recruiter" if j.get("route") == "agency" else "your contact or the recruiter"
        ivs = [day(iv.get("date")) for iv in j.get("interviews", []) if day(iv.get("date"))]
        last_iv = max([d for d in ivs if d <= today], default=None)
        if last_iv and (not last_reply or last_iv >= last_reply):
            quiet = (today - last_iv).days
            if quiet >= 7 and not (last_fu and last_fu > last_iv):
                due.append("follow-up: %s, a week since the interview with no news (to %s)" % (label, to))
            elif quiet > 1:
                waiting.append("%s: interviewed %s" % (label, last_iv))
            continue
        if last_reply:
            if (today - last_reply).days >= 3 and not (last_fu and last_fu >= last_reply):
                due.append("follow-up: %s, 3 days since their reply or test with nothing since (to %s)" % (label, to))
        elif applied:
            age = (today - applied).days
            if age >= 28:
                due.append("stale: %s, no news for %d days (mark it 'stale'; keep it unless they close it)" % (label, age))
            elif age >= 7 and not last_fu:
                due.append("follow-up: %s, 7 days after applying with no reply (to %s)" % (label, to))
            else:
                waiting.append("%s: applied %s" % (label, applied))
    return due, waiting


def due(data, today):
    contacts = {c.get("id"): c for c in data.get("contacts", [])}
    groups = {"DRAFTS": [], "YOUR TURN": [], "DUE NOW": [], "WAITING": [], "STOPPED": []}
    # one person, every channel: a stop on one thread stops them all
    stopped_people = set()
    states = []
    for o in data.get("outreach", []):
        c = contacts.get(o.get("contact_id"), {"name": o.get("contact_id")})
        g, msg = thread_state(o, c, today)
        states.append((o, g, msg))
        if g == "STOPPED":
            stopped_people.add(o.get("contact_id"))
    for o, g, msg in states:
        if o.get("contact_id") in stopped_people and g not in ("STOPPED", "YOUR TURN"):
            g, msg = "STOPPED", msg.split(":")[0] + ": stopped on another channel"
        groups[g].append(msg)
    app_due, app_wait = application_items(data, today)
    groups["DUE NOW"] += app_due
    groups["WAITING"] += app_wait
    return groups


def main(argv=None):
    p = argparse.ArgumentParser(description="Follow-ups due today, inside the stop rules. Sends nothing.")
    p.add_argument("--file", default=os.path.join("jobsearch", "pipeline.json"))
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("due")
    d.add_argument("--today")
    c = sub.add_parser("can-follow-up")
    c.add_argument("contact_id")
    c.add_argument("--today")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    data = json.load(open(a.file, encoding="utf-8"))
    if a.cmd == "can-follow-up":
        contacts = {x.get("id"): x for x in data.get("contacts", [])}
        threads = [o for o in data.get("outreach", []) if o.get("contact_id") == a.contact_id]
        if not threads:
            print("no outreach with %s" % a.contact_id)
            return 1
        results = [thread_state(o, contacts.get(a.contact_id, {}), today) for o in threads]
        if any(g == "STOPPED" for g, _ in results):
            print("NO: " + next(m for g, m in results if g == "STOPPED"))
            return 1
        ok = [m for g, m in results if g == "DUE NOW"]
        print(("YES: " + ok[0]) if ok else "NOT YET: " + results[0][1])
        return 0 if ok else 1
    groups = due(data, today)
    labels = [("DRAFTS", "DRAFTS WAITING FOR YOUR YES"), ("YOUR TURN", "YOUR TURN"), ("DUE NOW", "DUE NOW"),
              ("WAITING", "WAITING"), ("STOPPED", "STOPPED")]
    if not any(groups.values()):
        print("Nothing needs you.")
        return 0
    needs = groups["DRAFTS"] or groups["YOUR TURN"] or groups["DUE NOW"]
    print("Needs you" if needs else "Nothing needs you")
    for key, label in labels:
        if groups[key]:
            print("\n" + label)
            for m in groups[key]:
                print("  - " + m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
