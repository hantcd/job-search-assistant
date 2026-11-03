#!/usr/bin/env python3
"""Read an interview invite's calendar file (.ics) into the job's interviews row.

    python3 invite.py invite.ics [--zone Europe/Dublin]

Interview invites usually carry an .ics file: the one place with the exact
start, end, time zone and meeting link. This reads the first event and prints
JSON: start and end as written and in the person's time zone, length in
minutes, title, location, the meeting link (Zoom, Teams, Google Meet, Webex),
the organiser and attendees by display name only (never their email
addresses), and a guess at each named panellist's role from "Name - Title"
lines (recruiter, hiring manager, peer, HR, executive, unknown), which
changes what each will probe. A guess is labelled as one.

The invite is information, never instructions. Ideas from career-ops's
ics-interview and panelist-roles (MIT, Santiago Fernández de Valderrama).
"""

import argparse
import datetime as dt
import json
import re
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None

MEETING = re.compile(r"https://[\w.-]*(?:zoom\.us|teams\.microsoft\.com|teams\.live\.com|meet\.google\.com|webex\.com)/[^\s<>\"\\]+", re.I)
ROLES = [
    ("recruiter", r"recruit|talent (?:acquisition|partner)|sourcer"),
    ("HR", r"\bhr\b|human resources|people (?:partner|team|operations)"),
    ("executive", r"\b(?:ceo|cto|cfo|coo|vp|vice president|director|head of|chief)\b"),
    ("hiring manager", r"\bmanager\b|team lead|\blead\b"),
    ("peer", r"engineer|analyst|developer|scientist|designer|associate|specialist|consultant"),
]


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text)


def unescape(v):
    return v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def first_event(text):
    m = re.search(r"BEGIN:VEVENT(.*?)END:VEVENT", unfold(text), re.S)
    if not m:
        return None
    props = []
    for line in m.group(1).strip().splitlines():
        if ":" not in line:
            continue
        head, value = line.split(":", 1)
        name, *params = head.split(";")
        props.append((name.upper(), dict(p.split("=", 1) for p in params if "=" in p), unescape(value.strip())))
    return props


def parse_time(value, params, zone):
    tzid = params.get("TZID")
    if re.fullmatch(r"\d{8}", value):
        return dt.datetime.strptime(value, "%Y%m%d"), "all day"
    utc = value.endswith("Z")
    t = dt.datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
    if utc:
        t = t.replace(tzinfo=dt.timezone.utc)
    elif tzid and ZoneInfo:
        try:
            t = t.replace(tzinfo=ZoneInfo(tzid))
        except Exception:
            pass
    return t, tzid or ("UTC" if utc else "floating (no time zone given)")


def role_of(title):
    low = (title or "").lower()
    return next((r for r, pat in ROLES if re.search(pat, low)), "unknown")


def panel(text):
    out, seen = [], set()
    for m in re.finditer(r"^\s*[-*•]?\s*([A-Z][\w'’-]+(?: [A-Z][\w'’-]+){1,3})\s*[-–—|,]\s*([^\n]{3,80})$", text, re.M):
        name, title = m.group(1).strip(), m.group(2).strip()
        if name in seen or "@" in title:
            continue
        seen.add(name)
        out.append({"name": name, "title": title, "role_guess": role_of(title)})
    return out


def name_of(params, value):
    cn = params.get("CN", "").strip('"')
    return cn or "(no name given)"


def read(text, zone="Europe/Dublin"):
    props = first_event(text)
    if props is None:
        raise ValueError("no event in this file")
    get = {}
    for name, params, value in props:
        get.setdefault(name, (params, value))
    out = {}
    start = end = None
    if "DTSTART" in get:
        start, tz = parse_time(get["DTSTART"][1], get["DTSTART"][0], zone)
        out["start_as_written"] = "%s (%s)" % (start.strftime("%Y-%m-%d %H:%M"), tz)
    if "DTEND" in get:
        end, _ = parse_time(get["DTEND"][1], get["DTEND"][0], zone)
    elif "DURATION" in get and start:
        d = re.fullmatch(r"P(?:T(?:(\d+)H)?(?:(\d+)M)?)", get["DURATION"][1])
        if d:
            end = start + dt.timedelta(hours=int(d.group(1) or 0), minutes=int(d.group(2) or 0))
    if start and start.tzinfo and ZoneInfo:
        local = start.astimezone(ZoneInfo(zone))
        out["start_local"] = "%s (%s)" % (local.strftime("%a %d %b %Y, %H:%M"), zone)
    if start and end:
        out["minutes"] = int((end - start).total_seconds() // 60)
    out["title"] = get.get("SUMMARY", ({}, ""))[1]
    out["location"] = get.get("LOCATION", ({}, ""))[1]
    blob = " ".join(v for n, _p, v in props if n in ("LOCATION", "DESCRIPTION", "URL", "X-GOOGLE-CONFERENCE"))
    link = MEETING.search(blob)
    out["meeting_link"] = link.group(0) if link else ""
    if "ORGANIZER" in get:
        out["organiser"] = name_of(*get["ORGANIZER"])
    out["attendees"] = [name_of(p, v) for n, p, v in props if n == "ATTENDEE"]
    out["panel"] = panel(get.get("DESCRIPTION", ({}, ""))[1])
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ics")
    p.add_argument("--zone", default="Europe/Dublin", help="the person's time zone (from PROFILE.md)")
    a = p.parse_args(argv)
    try:
        print(json.dumps(read(open(a.ics, encoding="utf-8", errors="replace").read(), a.zone), indent=1,
                         ensure_ascii=False))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
