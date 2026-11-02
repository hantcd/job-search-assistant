#!/usr/bin/env python3
"""Outreach drafts: check the message, plan send times, and record an exact yes.

    python3 outreach.py check --channel email --file draft.txt --subject "Junior Data Analyst role" --role "Junior Data Analyst"
    python3 outreach.py check --channel note --file note.txt          # LinkedIn connection note
    python3 outreach.py slots --start 2026-10-16 [--senior] [--active-window "Tue 09:00-10:00"]
    python3 outreach.py approve --file draft.txt --reply "yes"

check: emails under 75 words, a subject naming the role, no attachment in a first
email, one clear question; LinkedIn messages 2-4 sentences; connection notes at
most 200 characters; no 'I found you on...' openings.

slots: three touches that never share a weekday and time band, so one bad slot
in someone's week can't sink every attempt: the first on the next weekday
morning (8-11am, Tuesday to Thursday preferred); a follow-up 7 working days
later (10 for directors and above) at 2-5pm on a different weekday; the last a
week after that, early (7-8am) or early evening (6-8pm) on a third weekday. No
Friday afternoons or weekends. Times are the recipient's local time.

approve: only a clear yes for this exact text counts ("yes", "yes, send it",
"send it", "approved"). "Sure", "ok", "yes to all" and "yes but..." are refused,
and an edited draft needs a new yes. Prints the approval record to store with
the outreach row.

Nothing here sends anything.
"""

import argparse
import datetime
import hashlib
import json
import re
import sys

YES = re.compile(r"^\s*(yes|yes,? (?:please )?send(?: it| this)?|send(?: it| this)?|approved?|yes,? approved?|go ahead)\s*[.!]?\s*$", re.I)
BANDS = {"morning": ("08:00", "11:00"), "afternoon": ("14:00", "17:00"), "early": ("07:00", "08:00"),
         "evening": ("18:00", "20:00")}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def check(channel, text, subject="", role=""):
    res = []

    def add(name, status, detail):
        res.append((name, status, detail))

    words = len(re.findall(r"[A-Za-z0-9'’-]+", text))
    if channel == "email":
        add("length", "PASS" if words < 75 else "FAIL", "%d words (under 75)" % words)
        if not subject:
            add("subject", "FAIL", "add a subject that names the role")
        else:
            rw = [w for w in re.findall(r"[A-Za-z]+", role) if len(w) > 2]
            ok = (not rw) or all(w.lower() in subject.lower() for w in rw)
            add("subject", "PASS" if ok else "WARN", subject)
        att = re.search(r"\battach(ed|ment)?\b|\bplease find\b", text, re.I)
        add("no attachment", "WARN" if att else "PASS", "no CV attached in a first email" if att else "none")
    elif channel == "linkedin":
        n = len(sentences(text))
        add("length", "PASS" if 2 <= n <= 4 else "WARN", "%d sentences (2-4), %d characters" % (n, len(text)))
    elif channel == "note":
        add("length", "PASS" if len(text) <= 200 else "FAIL", "%d / 200 characters" % len(text))
    asks = text.count("?")
    if channel != "note":
        add("one ask", "PASS" if asks == 1 else "WARN", "%d question(s); one small ask, as a question" % asks)
    if re.search(r"\b(i )?(found|came across|saw) (you|your profile) (on|via)\b", text, re.I):
        add("opening", "WARN", "open with your connection or result, not how you found them")
    if re.search(r"\bjob\b.*\?|\bany (openings|vacancies)\b", text, re.I) and channel != "email":
        add("ask", "WARN", "networking messages ask for advice, not a job")
    return res


def working_days_after(d, n):
    while n > 0:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def next_weekday(d, avoid=(), prefer=(1, 2, 3), allow_friday=True):
    """The first day from d that's a weekday not in avoid, preferring Tue-Thu within the same week."""
    for step in range(0, 14):
        c = d + datetime.timedelta(days=step)
        if c.weekday() >= 5 or c.weekday() in avoid:
            continue
        if c.weekday() == 4 and not allow_friday:
            continue
        if prefer and c.weekday() not in prefer:
            later = [c + datetime.timedelta(days=k) for k in range(1, 4)]
            if any(x.weekday() in prefer and x.weekday() not in avoid and x.isocalendar()[1] == c.isocalendar()[1]
                   for x in later):
                continue
        return c
    return d


def slots(start, senior=False):
    """Three touches, never the same weekday and band twice."""
    first = next_weekday(start + datetime.timedelta(days=1))
    plan = [(first, "morning")]
    fu_day = next_weekday(working_days_after(first, 10 if senior else 7), avoid={first.weekday()},
                          prefer=(), allow_friday=False)  # 2-5pm: never a Friday afternoon
    plan.append((fu_day, "afternoon"))
    last_base = working_days_after(fu_day, 5)
    last_day = next_weekday(last_base, avoid={first.weekday(), fu_day.weekday()}, prefer=())
    plan.append((last_day, "early" if last_day.weekday() in (0, 1) else "evening"))
    if last_day.weekday() == 4 and plan[-1][1] == "evening":
        plan[-1] = (last_day, "early")  # no Friday evenings either
    out = []
    for (d, band), label in zip(plan, ("first message", "follow-up", "last follow-up")):
        a, b = BANDS[band]
        out.append({"touch": label, "date": d.isoformat(), "day": DAYS[d.weekday()], "band": band,
                    "window": "%s-%s" % (a, b)})
    return out


def approve(text, reply):
    if not YES.match(reply or ""):
        return None, ("Not a clear yes for this exact message (%r). Ask again: 'Send this exact message? yes or no'."
                      % reply)
    h = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]
    return {"reply": reply.strip(), "date": datetime.date.today().isoformat(), "hash": h}, None


def main(argv=None):
    p = argparse.ArgumentParser(description="Check, time and approve outreach drafts. Sends nothing.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--channel", choices=("email", "linkedin", "note"), required=True)
    c.add_argument("--file", required=True)
    c.add_argument("--subject", default="")
    c.add_argument("--role", default="")
    s = sub.add_parser("slots")
    s.add_argument("--start", help="today's date, YYYY-MM-DD")
    s.add_argument("--senior", action="store_true", help="directors and above: wait 10 working days")
    s.add_argument("--active-window", help="when their public posts show they're active, e.g. 'Tue 09:00-10:00'")
    ap = sub.add_parser("approve")
    ap.add_argument("--file", required=True)
    ap.add_argument("--reply", required=True)
    a = p.parse_args(argv)
    if a.cmd == "check":
        res = check(a.channel, open(a.file, encoding="utf-8").read(), a.subject, a.role)
        for name, st, detail in res:
            print("%-4s  %-14s %s" % (st, name, detail))
        return 1 if any(st == "FAIL" for _, st, _ in res) else 0
    if a.cmd == "slots":
        start = datetime.date.fromisoformat(a.start) if a.start else datetime.date.today()
        plan = slots(start, a.senior)
        if a.active_window:
            plan[0]["note"] = "their public activity suggests %s: use that for the first message" % a.active_window
        print(json.dumps(plan, indent=1))
        return 0
    rec, err = approve(open(a.file, encoding="utf-8").read(), a.reply)
    if err:
        print(err, file=sys.stderr)
        return 1
    print(json.dumps(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
