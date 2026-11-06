#!/usr/bin/env python3
"""The application streak: planned days in a row with at least one application, freezes, earn-back, goals.

    python3 streak.py status --file jobsearch/pipeline.json --plan MASTER_PLAN.md [--today 2026-11-09] [--json]
    python3 streak.py at-risk --file jobsearch/pipeline.json --plan MASTER_PLAN.md   # exit 1 if today's streak is at risk

MASTER_PLAN.md lines it reads (defaults in brackets):
  Session days: Mon, Tue, Wed, Thu, Fri at 08:30      [weekdays at 08:30]
  Applications a day: 5-10                              [5-10: at least 5, at most 10]
  Streak goal: 30                                       [7, then 14, 30, 50, 100]
  Streak start: 2026-11-09                              [the first day with an application]

How it counts (lessons from Duolingo's published streak experiments):
- A planned day counts when at least one application went in that day: the streak
  is separate from the daily goal, so one application keeps it alive and a busy
  day doesn't break it. Days that aren't planned never break it; an application on
  one is a bonus. One email alone doesn't count: too easy to mean anything.
- Freezes: the person starts with 2 (giving new users two was one of Duolingo's
  biggest wins), earns 1 for every 10 planned days done, and holds at most 2
  (three was no better than two). A missed planned day uses one automatically.
- Earn back: a missed day with no freeze left is won back by applying to 2 jobs
  on the next planned day.
- A perfect streak is one that hasn't used a freeze.
- Milestones and goals: 7, 14, 30, 50, 100 and every 100 after; the person can
  set their own goal, and a goal they pick beats a pre-set harder one.
The job list's jobs table is the only source: `applied` dates. Nothing is stored.
"""

import argparse
import datetime
import json
import re
import sys

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MILESTONES = [3, 7, 14, 30, 50, 100]
FREEZE_START, FREEZE_MAX, FREEZE_EVERY = 2, 2, 10


def day(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def read_plan(text):
    out = {"days": [0, 1, 2, 3, 4], "time": "08:30", "per_day": 10, "per_day_min": 5, "goal": None, "start": None}
    for line in (text or "").splitlines():
        low = line.lower()
        if re.search(r"session days?|apply(?:ing)? days?|streak days?", low):
            ds = [i for i, d in enumerate(DAYS) if re.search(r"\b%s" % d, low)]
            if re.search(r"every ?day|daily|7 days", low):
                ds = list(range(7))
            elif re.search(r"weekdays", low):
                ds = [0, 1, 2, 3, 4]
            if ds:
                out["days"] = ds
            m = re.search(r"\b(\d{1,2})[:.](\d\d)\b", low)
            if m:
                out["time"] = "%02d:%s" % (int(m.group(1)), m.group(2))
        m = re.search(r"applications? (?:a|per) day:?\s*(\d+)(?:\s*(?:-|–|to)\s*(\d+))?", low)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
            out["per_day_min"], out["per_day"] = min(lo, hi), max(lo, hi)
        m = re.search(r"streak goal:?\s*(\d+)", low)
        if m:
            out["goal"] = int(m.group(1))
        m = re.search(r"streak start:?\s*(\d{4}-\d\d-\d\d)", low)
        if m:
            out["start"] = day(m.group(1))
    return out


def applied_counts(data):
    counts = {}
    for j in data.get("jobs", []):
        d = day(j.get("applied"))
        if d:
            counts[d] = counts.get(d, 0) + 1
    return counts


def next_milestone(n, goal=None):
    if goal and goal > n:
        return goal
    for m in MILESTONES:
        if m > n:
            return m
    return (n // 100 + 1) * 100


def status(data, plan, today):
    counts = applied_counts(data)
    planned = set(plan["days"])
    first = plan["start"] or (min(counts) if counts else today)
    streak, best, freezes, done_days, used_in_streak = 0, 0, FREEZE_START, 0, 0
    events = []
    d = first
    pending_earn_back = None  # (streak before the miss, the missed day)
    while d < today:
        n = counts.get(d, 0)
        if d.weekday() in planned:
            if pending_earn_back and n >= 2:
                streak = pending_earn_back[0] + 1
                events.append(("earned back", d))
                pending_earn_back = None
                done_days += 1
            elif pending_earn_back:
                streak, used_in_streak, pending_earn_back = (1 if n else 0), 0, None
                events.append(("reset", d))
                done_days += 1 if n else 0
            elif n:
                streak += 1
                done_days += 1
            elif streak and freezes:
                freezes -= 1
                used_in_streak += 1
                events.append(("freeze used", d))
            elif streak:
                pending_earn_back = (streak, d)
                streak = 0
                events.append(("missed", d))
            if n and done_days and done_days % FREEZE_EVERY == 0 and freezes < FREEZE_MAX:
                freezes += 1
                events.append(("freeze earned", d))
        elif n:
            streak += 1 if streak else 0  # a bonus day extends a live streak
        best = max(best, streak)
        d += datetime.timedelta(days=1)
    today_n = counts.get(today, 0)
    planned_today = today.weekday() in planned
    earn_back = None
    if pending_earn_back:
        earn_back = {"missed": pending_earn_back[1].isoformat(), "streak": pending_earn_back[0],
                     "need_today": 2 if planned_today else None}
    if planned_today and today_n:
        if earn_back and today_n >= 2:
            streak = earn_back["streak"] + 1
            earn_back = None
        elif earn_back:
            streak = 1  # a new streak has started; one more application today wins the old one back
            earn_back["need_today"] = 2 - today_n
        else:
            streak += 1
        state = "done"
    elif planned_today:
        state = "at risk" if (streak or earn_back) else "start"
    else:
        state = "rest day"
        if today_n and streak:
            streak += 1
    best = max(best, streak)
    monday = today - datetime.timedelta(days=today.weekday())
    week_apps = sum(n for x, n in counts.items() if monday <= x <= today)
    week_goal = plan.get("per_day_min", plan["per_day"]) * len(planned)
    return {"streak": streak, "best": best, "freezes": freezes, "perfect": used_in_streak == 0 and streak > 0,
            "today": state, "applied_today": today_n, "earn_back": earn_back,
            "next_milestone": next_milestone(streak, plan.get("goal")),
            "milestone_today": state == "done" and streak in MILESTONES + ([plan["goal"]] if plan.get("goal") else []),
            "week": {"applications": week_apps, "goal": week_goal}, "last_events": [(k, x.isoformat())
                                                                                  for k, x in events[-3:]],
            "plan": {"days": [DAYS[i].title() for i in sorted(planned)], "time": plan["time"],
                     "per_day": plan["per_day"], "per_day_min": plan.get("per_day_min", plan["per_day"])}}


def bar(n, goal, width=10):
    filled = min(width, int(round(width * n / float(goal)))) if goal else 0
    return "#" * filled + "-" * (width - filled)


def welcome(s, ready=None):
    """The opening line of the daily message: the streak first, then what keeps it."""
    n, nxt = s["streak"], s["next_milestone"]
    flame = "%d-day streak" % n if n else "No streak yet"
    perfect = " (perfect: no freezes used)" if s["perfect"] and n >= 7 else ""
    lines = []
    if s["today"] == "done" and s["earn_back"] and s["earn_back"]["need_today"]:
        lines.append("One more application today wins back your %d-day streak." % s["earn_back"]["streak"])
    elif s["today"] == "done":
        if s["milestone_today"]:
            lines.append("%s%s. %d planned days in a row: that's a real habit. Next goal: %d." % (flame, perfect, n,
                                                                                            nxt))
        else:
            lines.append("%s%s. Today's done. %d to go to %d." % (flame, perfect, nxt - n, nxt))
    elif s["earn_back"] and s["earn_back"]["need_today"]:
        lines.append("You missed %s. Apply to 2 jobs today to win back your %d-day streak." % (
            datetime.date.fromisoformat(s["earn_back"]["missed"]).strftime("%A"), s["earn_back"]["streak"]))
    elif s["today"] == "at risk":
        lines.append("%s%s. One application keeps it going today." % (flame, perfect))
    elif s["today"] == "start":
        lines.append("Day 1 starts with one application.")
    else:
        lines.append("%s. Rest day: an application today is a bonus." % flame)
    used = [x for x in s["last_events"] if x[0] == "freeze used"]
    if used and s["today"] != "done":
        lines.append("A streak freeze covered %s. %d left." % (
            datetime.date.fromisoformat(used[-1][1]).strftime("%A"), s["freezes"]))
    if ready:
        lines.append(ready)
    w = s["week"]
    lines.append("This week: [%s] %d of %d applications." % (bar(w["applications"], w["goal"]), w["applications"],
                                                             w["goal"]))
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="The application streak.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("status", "at-risk"):
        x = sub.add_parser(name)
        x.add_argument("--file", default="jobsearch/pipeline.json")
        x.add_argument("--plan", default="MASTER_PLAN.md")
        x.add_argument("--today")
        x.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    try:
        text = open(a.plan, encoding="utf-8").read()
    except OSError:
        text = ""
    with open(a.file, encoding="utf-8") as fh:
        s = status(json.load(fh), read_plan(text), today)
    if a.json:
        print(json.dumps(s, indent=1))
    else:
        print(welcome(s))
    if a.cmd == "at-risk":
        return 1 if s["today"] == "at risk" or (s["earn_back"] and s["earn_back"]["need_today"]) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
