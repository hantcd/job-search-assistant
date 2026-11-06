#!/usr/bin/env python3
"""Turn a yes into a calendar invite: read the reply, find free times, make the event and its prep block.

    python3 booking.py intent --file reply.txt
    python3 booking.py slots --events busy.json --start 2026-11-09 [--days 5] [--length 30] [--zone Europe/Dublin]
    python3 booking.py reply --slots slots.json --name Siobhan [--zone Europe/Dublin]
    python3 booking.py event --kind chat --person "Siobhan Kelly" --company Acme --start 2026-11-10T11:00 \
        [--length 30] [--zone Europe/Dublin] [--card card.md]

intent: BOOK (they're happy to talk: offer times), INTERVIEW (a recruiter asks for
availability), THEIR_LINK (they sent a booking link: pick a slot there, on approval),
NO (a no or not now: stop, thank them), OTHER (read it and answer).

slots: up to 3 free times on different weekdays, inside working hours (09:00-17:30,
preferring 10:00-16:00), with 15 minutes clear either side, never in the past or at
weekends, from the person's busy times (Google Calendar's events as JSON: a list of
{start, end} in ISO format).

event: the calendar event (title, times, a video call, the prep card in its
description, reminders) and its prep block: 15 minutes before a chat, an hour the
afternoon before an interview. Created only after the other person confirms a time,
on the person's approval; Claude never accepts or sends an invitation unasked.
"""

import argparse
import datetime
import json
import re
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

BOOK = re.compile(r"\b(?:happy to (?:chat|talk|connect|help|meet)|(?:let'?s|we could|we can) (?:chat|talk|find a time|"
                  r"set up|grab|meet)|what (?:times?|days?) (?:work|suit|are good)|send (?:me|over) (?:some|a few) "
                  r"times|free (?:on|next|this)|grab (?:a )?(?:coffee|call)|sure,? (?:let'?s|i'?d be)|would love to "
                  r"(?:chat|connect)|jump on a call|hop on a call)\b", re.I)
INTERVIEW = re.compile(r"\b(?:schedule (?:a|an|your) (?:call|interview|screen|chat)|your availability|availability "
                       r"for|next stage|move (?:you )?forward|first[- ]round|phone screen|interview (?:with|slot)|"
                       r"book (?:a|an) (?:time|slot|interview))\b", re.I)
LINK = re.compile(r"https?://(?:www\.)?(?:calendly\.com|cal\.com|savvycal\.com|calendar\.app\.google|"
                  r"outlook\.office(?:365)?\.com/(?:owa/)?(?:calendar|bookwithme|book)|[\w.-]*chilipiper\.com|"
                  r"[\w.-]*goodtime\.io|[\w.-]*greenhouse\.io/[\w/-]*schedul|meetings\.hubspot\.com)\S*", re.I)
NO = re.compile(r"\b(?:not (?:able|in a position|hiring)|can'?t help|no longer|unfortunately|not the right time|"
                r"too busy|please don'?t|unsubscribe|not interested|decided (?:not|to move forward with other))\b", re.I)


def intent(text):
    m = LINK.search(text or "")
    if m:
        return "THEIR_LINK", m.group(0)
    if NO.search(text or "") and not BOOK.search(text or ""):
        return "NO", ""
    if INTERVIEW.search(text or ""):
        return "INTERVIEW", ""
    if BOOK.search(text or ""):
        return "BOOK", ""
    return "OTHER", ""


def _dt(s, tz):
    d = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=tz)
    return d.astimezone(tz)


def free_slots(busy, start, days=5, length=30, zone="Europe/Dublin", count=3, now=None,
               work=(9.0, 17.5), prefer=(10.0, 16.0), buffer=15):
    tz = ZoneInfo(zone) if ZoneInfo else datetime.timezone.utc
    now = now or datetime.datetime.now(tz)
    blocks = []
    for e in busy or []:
        try:
            blocks.append((_dt(e["start"], tz) - datetime.timedelta(minutes=buffer),
                           _dt(e["end"], tz) + datetime.timedelta(minutes=buffer)))
        except (KeyError, ValueError):
            continue
    out, d, seen_days = [], start, 0
    while len(out) < count and seen_days < days * 3:
        seen_days += 1
        if d.weekday() < 5:
            day_slots = []
            minute = int(work[0] * 60)
            while minute + length <= int(work[1] * 60):
                s = datetime.datetime(d.year, d.month, d.day, minute // 60, minute % 60, tzinfo=tz)
                e = s + datetime.timedelta(minutes=length)
                if s > now + datetime.timedelta(hours=12) and not any(s < b1 and e > b0 for b0, b1 in blocks):
                    pref = prefer[0] * 60 <= minute and minute + length <= prefer[1] * 60
                    day_slots.append((0 if pref else 1, abs(minute - 11 * 60), s))
                minute += 30
            if day_slots:
                out.append(sorted(day_slots)[0][2])
        d += datetime.timedelta(days=1)
    return out


def reply_text(slots, name, zone="Europe/Dublin"):
    label = "Irish time" if zone == "Europe/Dublin" else "UK time" if zone == "Europe/London" else zone
    times = "\n".join("- %s %d %s" % (s.strftime("%A"), s.day, s.strftime("%B, %H:%M")) for s in slots)
    return ("Thanks %s, that would be great. Would any of these work (%s)?\n%s\nOr suggest another time that suits "
            "you better, and I'll send a calendar invite with a video link." % (name, label, times))


def event(kind, person, company, start, length=30, zone="Europe/Dublin", card=""):
    tz = ZoneInfo(zone) if ZoneInfo else datetime.timezone.utc
    s = _dt(start, tz)
    e = s + datetime.timedelta(minutes=length)
    title = ("Coffee chat: %s (%s)" if kind == "chat" else "Interview: %s (%s)") % (person, company)
    main = {"summary": title, "start": s.isoformat(), "end": e.isoformat(), "time_zone": zone,
            "video_call": True, "description": card.strip(),
            "reminders": [{"method": "popup", "minutes": 30}, {"method": "popup", "minutes": 10}]}
    if kind == "chat":
        ps = s - datetime.timedelta(minutes=15)
        prep = {"summary": "Prep: %s" % title, "start": ps.isoformat(), "end": s.isoformat(), "time_zone": zone,
                "description": "Read the prep card in the chat's event: questions, the closing ask."}
    else:
        ps = (s - datetime.timedelta(days=1)).replace(hour=16, minute=0)
        while ps.weekday() >= 5:
            ps -= datetime.timedelta(days=1)
        prep = {"summary": "Prep: %s" % title, "start": ps.isoformat(),
                "end": (ps + datetime.timedelta(hours=1)).isoformat(), "time_zone": zone,
                "description": "The proof pack, the stories and a short mock interview (job-interview)."}
    return {"event": main, "prep_block": prep}


def main(argv=None):
    p = argparse.ArgumentParser(description="Replies to calendar invites.")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("intent")
    i.add_argument("--file", required=True)
    s = sub.add_parser("slots")
    s.add_argument("--events", required=True)
    s.add_argument("--start", required=True)
    s.add_argument("--days", type=int, default=5)
    s.add_argument("--length", type=int, default=30)
    s.add_argument("--zone", default="Europe/Dublin")
    r = sub.add_parser("reply")
    r.add_argument("--slots", required=True)
    r.add_argument("--name", required=True)
    r.add_argument("--zone", default="Europe/Dublin")
    e = sub.add_parser("event")
    e.add_argument("--kind", choices=("chat", "interview"), required=True)
    e.add_argument("--person", required=True)
    e.add_argument("--company", required=True)
    e.add_argument("--start", required=True)
    e.add_argument("--length", type=int, default=30)
    e.add_argument("--zone", default="Europe/Dublin")
    e.add_argument("--card", help="the prep card (markdown) for the event's description")
    a = p.parse_args(argv)
    if a.cmd == "intent":
        kind, link = intent(open(a.file, encoding="utf-8").read())
        print(kind + (" " + link if link else ""))
    elif a.cmd == "slots":
        busy = json.load(open(a.events, encoding="utf-8"))
        slots = free_slots(busy, datetime.date.fromisoformat(a.start), a.days, a.length, a.zone)
        print(json.dumps([x.isoformat() for x in slots], indent=1))
    elif a.cmd == "reply":
        tz = ZoneInfo(a.zone) if ZoneInfo else datetime.timezone.utc
        slots = [_dt(x, tz) for x in json.load(open(a.slots, encoding="utf-8"))]
        print(reply_text(slots, a.name, a.zone))
    else:
        card = open(a.card, encoding="utf-8").read() if a.card else ""
        print(json.dumps(event(a.kind, a.person, a.company, a.start, a.length, a.zone, card), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
