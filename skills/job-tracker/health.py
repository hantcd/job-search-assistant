#!/usr/bin/env python3
"""Did the automatic tasks run? Find missed runs, say what to catch up, and alert once.

    python3 health.py check --file jobsearch/pipeline.json --expect "daily search=1-5@08:00,13:00" \
        --expect "email tracker=1-5@08:00" [--now 2026-11-06T09:30] [--hours 36]
    python3 health.py since --file jobsearch/pipeline.json --task "daily search"   # last good run, to catch up from

A task that hits a usage limit, or whose computer is off, never starts, so it writes
nothing to the run log: a missed run is an expected time with no run_log row for that
task before the next expected time (45 minutes' grace). Each task reads `since` at its
start and covers everything since its last good run, not just since its scheduled
time, so one missed morning costs nothing. The first run of the day reports missed
runs once ("2 runs missed yesterday (usage limit or computer off); caught up now"),
and the alert isn't repeated: a run_log row with task 'health' marks it sent.

--expect: "<task>=<days>@<HH:MM>[,<HH:MM>...]", days as 1-5 (Mon-Fri), 1-7 or a list
like 1,3,5. A task matches run_log rows whose task name contains every word of it.
"""

import argparse
import datetime
import json
import re
import sys

GRACE = datetime.timedelta(minutes=45)


def stamp(s):
    s = str(s or "").replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def parse_expect(spec):
    m = re.match(r"\s*(.+?)\s*=\s*([\d,\-]+)\s*@\s*([\d:,\s]+)$", spec)
    if not m:
        raise SystemExit("bad --expect %r (e.g. 'daily search=1-5@08:00,13:00')" % spec)
    name, days, times = m.groups()
    ds = set()
    for part in days.split(","):
        if "-" in part:
            a, b = part.split("-")
            ds.update(range(int(a) - 1, int(b)))
        elif part:
            ds.add(int(part) - 1)
    ts = [tuple(int(x) for x in t.strip().split(":")) for t in times.split(",") if t.strip()]
    return {"task": name.lower(), "days": sorted(ds), "times": sorted(ts)}


def expected_runs(exp, start, end):
    out, d = [], start.date()
    while d <= end.date():
        if d.weekday() in exp["days"]:
            for h, m in exp["times"]:
                t = datetime.datetime(d.year, d.month, d.day, h, m)
                if start <= t <= end - GRACE:
                    out.append(t)
        d += datetime.timedelta(days=1)
    return out


def matches(task, logged):
    """'daily search' matches 'Daily job search (08:00)': every word of the expected name appears."""
    words = re.findall(r"[a-z]+", task.lower())
    have = set(re.findall(r"[a-z]+", str(logged).lower()))
    return bool(words) and all(w in have for w in words)


def runs_of(data, task):
    out = []
    for r in data.get("run_log", []):
        if matches(task, r.get("task", "")) and not r.get("stopped_early") == "error":
            t = stamp(r.get("time"))
            if t:
                out.append(t)
    return sorted(out)


def check(data, expects, now, hours=36):
    start = now - datetime.timedelta(hours=hours)
    missed = []
    for exp in expects:
        runs = runs_of(data, exp["task"])
        times = expected_runs(exp, start, now)
        for i, t in enumerate(times):
            nxt = times[i + 1] if i + 1 < len(times) else now
            if not any(t - datetime.timedelta(minutes=10) <= r < nxt for r in runs):
                missed.append({"task": exp["task"], "expected": t.isoformat(timespec="minutes"),
                               "catch_up_since": (runs[-1].isoformat(timespec="minutes") if runs else None)})
    alerted_today = any("health" == str(r.get("task", "")).lower() and stamp(r.get("time"))
                        and stamp(r.get("time")).date() == now.date() for r in data.get("run_log", []))
    msg = None
    if missed and not alerted_today:
        tasks = sorted({m["task"] for m in missed})
        msg = ("%d automatic run%s missed in the last %d hours (%s), usually a usage limit or the computer being "
               "off; each task catches up from its last good run, so nothing is lost."
               % (len(missed), "" if len(missed) == 1 else "s", hours, ", ".join(tasks)))
    return {"missed": missed, "alert": msg, "log_row": {"time": now.isoformat(timespec="minutes"), "task": "health",
                                                          "sources_checked": len(expects), "new": 0, "updated": 0,
                                                          "closed": 0, "errors": len(missed), "stopped_early": False}
            if msg else None}


def since(data, task):
    runs = runs_of(data, task.lower())
    return runs[-1].isoformat(timespec="minutes") if runs else None


def main(argv=None):
    p = argparse.ArgumentParser(description="Missed automatic runs and what to catch up.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--file", default="jobsearch/pipeline.json")
    c.add_argument("--expect", action="append", required=True)
    c.add_argument("--now")
    c.add_argument("--hours", type=int, default=36)
    s = sub.add_parser("since")
    s.add_argument("--file", default="jobsearch/pipeline.json")
    s.add_argument("--task", required=True)
    a = p.parse_args(argv)
    with open(a.file, encoding="utf-8") as fh:
        data = json.load(fh)
    if a.cmd == "since":
        print(since(data, a.task) or "never: cover the last 7 days")
        return 0
    now = stamp(a.now) if a.now else datetime.datetime.now()
    out = check(data, [parse_expect(e) for e in a.expect], now, a.hours)
    print(json.dumps(out, indent=1))
    return 1 if out["missed"] else 0


if __name__ == "__main__":
    sys.exit(main())
