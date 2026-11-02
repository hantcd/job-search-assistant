#!/usr/bin/env python3
"""Events from the job list's Events table: what to register for today, what's coming, what to follow up.

    python3 events.py due --file jobsearch/pipeline.json --today 2026-10-16 [--days 14]

Each event: {"name", "date", "place", "link", "registration_opens", "places_limited", "registered",
             "attended", "people_to_meet": [...], "follow_ups_sent": false, "speaker_call_deadline"}

REGISTER TODAY  registration opens today (or opened and you haven't registered) and places are limited
REGISTER        registration is open, not yet registered
COMING UP       within --days, registered: prepare openers for the people to meet
FOLLOW UP       attended in the last 2 days and follow-ups not sent (send within 48 hours)
SPEAKER CALL    a call for speakers closes within 14 days
"""

import argparse
import datetime
import json
import os
import sys


def day(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def due(events, today, days=14):
    out = {"REGISTER TODAY": [], "REGISTER": [], "COMING UP": [], "FOLLOW UP": [], "SPEAKER CALL": []}
    for e in events:
        d, opens = day(e.get("date")), day(e.get("registration_opens"))
        label = "%s (%s, %s)" % (e.get("name"), e.get("date"), e.get("place", "online?"))
        if d and d >= today and not e.get("registered"):
            if opens and opens <= today and e.get("places_limited"):
                out["REGISTER TODAY"].append(label)
            elif not opens or opens <= today:
                out["REGISTER"].append(label)
        if d and e.get("registered") and 0 <= (d - today).days <= days:
            people = ", ".join(e.get("people_to_meet", [])) or "nobody listed yet"
            out["COMING UP"].append("%s: people to meet: %s" % (label, people))
        if d and e.get("attended") and 0 <= (today - d).days <= 2 and not e.get("follow_ups_sent"):
            out["FOLLOW UP"].append("%s: send follow-ups within 48 hours of the event" % label)
        sc = day(e.get("speaker_call_deadline"))
        if sc and 0 <= (sc - today).days <= 14:
            out["SPEAKER CALL"].append("%s: speaker call closes %s" % (label, sc))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Event reminders from the job list.")
    p.add_argument("--file", default=os.path.join("jobsearch", "pipeline.json"))
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("due")
    d.add_argument("--today")
    d.add_argument("--days", type=int, default=14)
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    data = json.load(open(a.file, encoding="utf-8"))
    out = due(data.get("events", []), today, a.days)
    if not any(out.values()):
        print("No events need you.")
        return 0
    for k, items in out.items():
        if items:
            print(k)
            for i in items:
                print("  - " + i)
    return 0


if __name__ == "__main__":
    sys.exit(main())
