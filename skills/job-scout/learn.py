#!/usr/bin/env python3
"""Learn from what the person skips and from what gets interviews, and propose one-tap changes.

    python3 learn.py skips --file jobsearch/pipeline.json [--today 2026-11-20] [--days 28]
    python3 learn.py patterns --file jobsearch/pipeline.json

skips: the person skips a job in the session with one tap and a reason (the feedback
table: {kind: "skip", job_id, reason, date}). When one reason comes up 3+ times in 4
weeks, propose the matching change, as a yes/no for the next session (nothing changes
without the yes: exclusions and weights are the person's):
  too junior        -> add "junior", "graduate", "intern" to triage's exclude_titles
  too senior        -> add "senior", "lead", "principal", "head of" to exclude_titles
  wrong place       -> drop the places those jobs were in from triage's locations
  not my industry   -> exclude that industry (the jobs' industries are listed)
  pay too low       -> raise the minimum pay dealbreaker to the median of those jobs' pay
  not this company  -> add the company to exclude_companies
  wrong kind of role -> drop the title variant from the family (the titles are listed)
patterns: once there are 20+ applications, the interview rate by role family, route,
where the job was found, Fit band and base CV, each with its counts; groups of 8+
with no interviews are flagged; and which score part best separates the jobs that got
interviews from the ones that didn't (a tentative weight change to approve or not).
From ai-job-search's outcome recalibration and career-ops's patterns.
"""

import argparse
import datetime
import json
import statistics
import sys

REASONS = {
    "too junior": ("exclude_titles", ["junior", "graduate", "intern"]),
    "too senior": ("exclude_titles", ["senior", "lead", "principal", "head of"]),
    "wrong place": ("locations", None),
    "not my industry": ("exclude_industries", None),
    "pay too low": ("min_pay", None),
    "not this company": ("exclude_companies", None),
    "wrong kind of role": ("titles", None),
}
INTERVIEWED = ("screen", "interview", "offer", "accepted")


def day(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def skips(data, today, days=28):
    jobs = {j.get("id"): j for j in data.get("jobs", [])}
    recent = [f for f in data.get("feedback", []) if f.get("kind") == "skip" and day(f.get("date"))
              and (today - day(f["date"])).days <= days]
    by = {}
    for f in recent:
        by.setdefault(str(f.get("reason", "")).lower(), []).append(jobs.get(f.get("job_id"), {}))
    out = []
    for reason, js in sorted(by.items(), key=lambda x: -len(x[1])):
        if len(js) < 3 or reason not in REASONS:
            continue
        field, values = REASONS[reason]
        if field == "locations":
            values = sorted({j.get("location") for j in js if j.get("location")})
            ask = "Stop showing jobs in %s?" % ", ".join(values)
        elif field == "exclude_industries":
            values = sorted({j.get("industry") for j in js if j.get("industry")})
            ask = "Stop showing jobs in %s?" % (", ".join(values) or "these industries")
        elif field == "exclude_companies":
            values = sorted({j.get("company") for j in js if j.get("company")})
            ask = "Stop showing jobs at %s?" % ", ".join(values)
        elif field == "min_pay":
            pays = [j.get("pay", {}).get("base") for j in js if isinstance(j.get("pay"), dict)
                    and j["pay"].get("base")]
            values = [int(statistics.median(pays))] if pays else []
            ask = ("Raise your minimum pay to %s?" % values[0]) if values else "Raise your minimum pay?"
        elif field == "titles":
            values = sorted({j.get("title") for j in js if j.get("title")})
            ask = "Stop searching for titles like %s?" % "; ".join(values[:3])
        else:
            ask = "Skip jobs with %s in the title from now on?" % ", ".join("'%s'" % v for v in values)
        out.append({"reason": reason, "count": len(js), "field": field, "values": values, "ask": ask})
    return out


def band(fit):
    if fit is None:
        return "unscored"
    return "80+" if fit >= 80 else "70-79" if fit >= 70 else "60-69" if fit >= 60 else "under 60"


def patterns(data, min_apps=20):
    apps = [j for j in data.get("jobs", []) if j.get("applied")]
    if len(apps) < min_apps:
        return {"applications": len(apps), "note": "too few to tell: patterns start at %d applications" % min_apps}
    out = {"applications": len(apps), "interview_rate": round(sum(j.get("status") in INTERVIEWED or bool(
        j.get("interviews")) for j in apps) / float(len(apps)), 3), "by": {}, "flags": []}
    keys = {"role family": lambda j: j.get("role_family"), "route": lambda j: j.get("timing_call") or j.get("route"),
            "found on": lambda j: j.get("found_on"), "Fit band": lambda j: band(j.get("fit")),
            "base CV": lambda j: j.get("base_cv")}
    for name, fn in keys.items():
        groups = {}
        for j in apps:
            groups.setdefault(str(fn(j) or "unknown"), []).append(j)
        rows = {}
        for g, js in groups.items():
            hits = sum(j.get("status") in INTERVIEWED or bool(j.get("interviews")) for j in js)
            rows[g] = "%d of %d" % (hits, len(js))
            if len(js) >= 8 and hits == 0:
                out["flags"].append("%s '%s': 0 interviews from %d applications" % (name, g, len(js)))
        out["by"][name] = rows
    # which score part separates interviews from the rest
    parts = {}
    for j in apps:
        hit = j.get("status") in INTERVIEWED or bool(j.get("interviews"))
        for part, v in (j.get("score_breakdown") or {}).items():
            pts = v.get("rating") if isinstance(v, dict) else v
            if isinstance(pts, (int, float)):
                parts.setdefault(part, ([], []))[0 if hit else 1].append(pts)
    gaps = {p: round(statistics.mean(a) - statistics.mean(b), 2) for p, (a, b) in parts.items() if len(a) >= 3
            and len(b) >= 3}
    if gaps:
        best = max(gaps, key=gaps.get)
        worst = min(gaps, key=gaps.get)
        out["score_parts"] = gaps
        if best != worst and gaps[best] > 0.5:
            out["suggest"] = ("Tentative: '%s' separates interviews from the rest most (%.2f points higher); "
                              "'%s' least. Consider moving 5 weight points from '%s' to '%s'. Your call."
                              % (best, gaps[best], worst, worst, best))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Learn from skips and outcomes.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("skips")
    s.add_argument("--file", default="jobsearch/pipeline.json")
    s.add_argument("--today")
    s.add_argument("--days", type=int, default=28)
    t = sub.add_parser("patterns")
    t.add_argument("--file", default="jobsearch/pipeline.json")
    a = p.parse_args(argv)
    with open(a.file, encoding="utf-8") as fh:
        data = json.load(fh)
    if a.cmd == "skips":
        today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
        print(json.dumps(skips(data, today, a.days), indent=1, ensure_ascii=False))
    else:
        print(json.dumps(patterns(data), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
