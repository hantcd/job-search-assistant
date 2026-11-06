#!/usr/bin/env python3
"""What's working: funnels from the job list snapshot, with counts, small-number warnings and a diagnosis.

    python3 funnel.py report --file jobsearch/pipeline.json [--json]
    python3 funnel.py thresholds --file jobsearch/pipeline.json --fit 60
    python3 funnel.py --file jobsearch/pipeline.json targets --plan MASTER_PLAN.md [--chats 1 --interviews 2 --capacity 5]

calibrate: after the first week, if jobs good enough for a pack come in under
'Applications a day' (default 5-10) on 4 of the last 5 planned days, lower the
pack threshold 5 points (floor 50) and widen the search; over it, raise 5
(ceiling 80). One change a week; the person asked for this to happen by
itself, and each change is reported and can be undone by saying so.

targets: works back from the weekly targets (MASTER_PLAN.md's 'Weekly targets:'
line; defaults 1 coffee chat, 2 interviews, 5 applications; flags override) to
the chat asks, connection requests and applications this week needs.

thresholds: how the scored jobs sit against the alert thresholds. With 10+
scored jobs and none alert-worthy, it suggests a recalibration for the person
to approve or decline (the scoring weights, a threshold, or the targets); it
never changes anything itself.

Applications: applied -> replied -> interview -> offer
Outreach:     sent -> replied -> chat -> referral
Each split by role family, route, base CV, channel, send time and how soon
after posting you applied. Every rate shows its counts ('2 of 14'); a group
under 10 is labelled 'too few to tell'. The diagnosis names the weakest stage
only once there are 20+ applications, and never changes anything by itself:
the weekly check proposes, the person decides.
"""

import argparse
import datetime
import json
import os
import re
import statistics
import sys

MIN_GROUP = 10
MIN_DIAGNOSIS = 20
REPLIED = ("screen", "interview", "offer", "accepted")
INTERVIEWED = ("interview", "offer", "accepted")
OFFERED = ("offer", "accepted")


def day(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


# Response rates by where people applied, from Huntr's tracked applications (US, self-reported
# by its users, 2026, 600,000+): a public benchmark to compare with, not a promise.
BENCHMARK = {"google jobs": 11.29, "governmentjobs": 8.67, "wellfound": 5.95, "glassdoor": 5.46, "handshake": 5.06,
             "welcome to the jungle": 4.52, "indeed": 4.46, "linkedin": 3.10, "ziprecruiter": 2.82}


def source_of(j):
    s = str(j.get("source") or j.get("found_on") or "").lower()
    for k in BENCHMARK:
        if k in s:
            return k
    if "company" in s or "careers" in s or "feed" in s or "watched" in s or "hidden" in s:
        return "company site"
    return s or "unlabelled"


def app_rows(data):
    apps = {a.get("job_id"): a for a in data.get("applications", [])}
    rows = []
    for j in data.get("jobs", []):
        if not j.get("applied"):
            continue
        st = j.get("status")
        a = apps.get(j.get("id"), {})
        posted, applied = day(j.get("posted")), day(j.get("applied"))
        rows.append({
            "replied": st in REPLIED or bool(j.get("last_reply")) or bool(j.get("interviews")),
            "interview": st in INTERVIEWED or bool(j.get("interviews")),
            "offer": st in OFFERED,
            "role_family": j.get("role_family") or "unlabelled",
            "route": j.get("route") or "unlabelled",
            "found_on": source_of(j),
            "base_cv": a.get("base_cv") or "unlabelled",
            "applied_within_48h": ("yes" if posted and applied and (applied - posted).days <= 2 else
                                   "no" if posted and applied else "unknown"),
            "days_to_reply": ((day(j.get("last_reply")) - applied).days
                              if j.get("last_reply") and applied and day(j.get("last_reply")) else None),
        })
    return rows


def outreach_rows(data):
    contacts = {c.get("id"): c for c in data.get("contacts", [])}
    rows = []
    for o in data.get("outreach", []):
        msgs = o.get("messages", [])
        outs = [m for m in msgs if m.get("direction") == "out"]
        if not outs:
            continue
        c = contacts.get(o.get("contact_id"), {})
        rows.append({
            "replied": any(m.get("direction") == "in" for m in msgs),
            "chat": o.get("status") == "booked" or bool(o.get("booked")),
            "referral": bool(c.get("referred")),
            "channel": o.get("channel") or "unlabelled",
            "send_time": outs[0].get("slot") or "unlabelled",
        })
    return rows


def rate(n, d):
    return "%d of %d" % (n, d) + ("" if d == 0 else " (%d%%)" % round(100.0 * n / d))


def split(rows, key, stages):
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    out = {}
    for g, rs in sorted(groups.items()):
        line = {s: rate(sum(1 for r in rs if r[s]), len(rs)) for s in stages}
        line["n"] = len(rs)
        if len(rs) < MIN_GROUP:
            line["label"] = "too few to tell"
        out[g] = line
    return out


def diagnose(apps):
    n = len(apps)
    if n < MIN_DIAGNOSIS:
        return "Too early to judge: %d application(s); wait for %d+." % (n, MIN_DIAGNOSIS)
    rep = sum(r["replied"] for r in apps)
    iv = sum(r["interview"] for r in apps)
    off = sum(r["offer"] for r in apps)
    if rep / n < 0.10:
        return "Weakest stage: replies (%s). Check targeting and the CV's first third." % rate(rep, n)
    if rep and iv / rep < 0.35:
        return "Weakest stage: replies to interviews (%s). Check your pitch and fit for these roles." % rate(iv, rep)
    if iv >= 3 and off == 0:
        return "Weakest stage: interviews to offers (%s). More interview practice." % rate(off, iv)
    return "No stage stands out yet (%s replied, %s interviewed)." % (rate(rep, n), rate(iv, n))


def report(data):
    apps = app_rows(data)
    outs = outreach_rows(data)
    A = ("replied", "interview", "offer")
    O = ("replied", "chat", "referral")
    days = [r["days_to_reply"] for r in apps if r["days_to_reply"] is not None]
    return {
        "applications": {"total": len(apps), **{s: rate(sum(r[s] for r in apps), len(apps)) for s in A}},
        "outreach": {"total": len(outs), **{s: rate(sum(r[s] for r in outs), len(outs)) for s in O}},
        "median_days_to_first_reply": statistics.median(days) if days else None,
        "by": {k: split(apps, k, A) for k in ("role_family", "route", "base_cv", "applied_within_48h", "found_on")},
        "benchmark_response_rate_pct": BENCHMARK,
        "outreach_by": {k: split(outs, k, O) for k in ("channel", "send_time")},
        "diagnosis": diagnose(apps),
    }


def fit_of(j, weights=(60, 40)):
    if isinstance(j.get("fit"), (int, float)):
        return j["fit"]
    if isinstance(j.get("career_value"), (int, float)) and isinstance(j.get("attainability"), (int, float)):
        return int(round((j["career_value"] * weights[0] + j["attainability"] * weights[1]) / 100.0))
    return None


def thresholds(data, fit_min=60, weights=(60, 40)):
    scored = [(j, fit_of(j, weights)) for j in data.get("jobs", [])]
    scored = [(j, f) for j, f in scored if f is not None]
    above = [j for j, f in scored if f >= fit_min]
    top = sorted(scored, key=lambda x: -x[1])[:5]
    out = {"scored": len(scored), "alert_worthy": len(above),
           "top": [(j.get("company"), j.get("title"), f) for j, f in top]}
    if len(scored) >= 10 and not above:
        fits = sorted(f for _, f in scored)
        p90 = fits[int(0.9 * (len(fits) - 1))]
        out["suggest"] = ("No job has reached the alert threshold in %d scored (best Fit %s; 90th percentile %s; "
                          "threshold %s). Optional: review what drags Fit down (the weights, the targets, or the "
                          "companies watched), or lower the threshold. Your call." % (len(scored), top[0][1], p90, fit_min))
    return out


# Starting assumptions until the person's own numbers exist (10+ of each), each labelled.
PRIORS = {"accept": (0.30, "starting guess: connection requests accepted"),
          "chat": (0.15, "starting guess: chat asks that become a chat"),
          "interview_cold": (0.03, "Ashby 2021-24: cold applications reaching interview"),
          "interview_referred": (0.40, "Ashby 2021-24: referred applications reaching interview")}


def own_rate(hits, total, prior):
    return (hits / float(total), "your numbers (%d of %d)" % (hits, total)) if total >= 10 else prior


TARGETS = re.compile(r"(\d+)\s*(?:coffee[- ])?chats?\b|(\d+)\s*interviews?\b|(\d+)\s*applications?\b", re.I)


def plan_targets(text):
    """Read the weekly targets from MASTER_PLAN.md: the line naming 'weekly target(s)', e.g.
    'Weekly targets: 1 coffee chat, 2 interviews, 5 applications'. Missing numbers stay None."""
    out = {"chats": None, "interviews": None, "capacity": None}
    for line in (text or "").splitlines():
        if re.search(r"weekly targets?|targets? (?:a|per) week", line, re.I):
            for m in TARGETS.finditer(line):
                if m.group(1):
                    out["chats"] = int(m.group(1))
                elif m.group(2):
                    out["interviews"] = int(m.group(2))
                elif m.group(3):
                    out["capacity"] = int(m.group(3))
            break
    return out


def weekly_plan(data, today, chats=1, interviews=2, apps_cap=5, invite_cap=80):
    """Work back from weekly targets (chats, interviews) to this week's volume, and say how far along it is."""
    invites = [o for o in data.get("outreach", []) if o.get("stage") in ("invite", "note") and o.get("messages")]
    asks = [o for o in data.get("outreach", []) if o.get("stage") == "chat" and o.get("messages")]
    accept, accept_src = own_rate(sum(1 for o in invites if o.get("accepted")), len(invites), PRIORS["accept"])
    chat, chat_src = own_rate(sum(1 for o in asks if o.get("chat_held") or o.get("booked")), len(asks), PRIORS["chat"])
    apps = app_rows(data)
    referred = [r for r in apps if r.get("route") in ("REFERRAL FIRST", "referral_first", "referral")]
    cold = [r for r in apps if r not in referred]
    p_cold, cold_src = own_rate(sum(r["interview"] for r in cold), len(cold), PRIORS["interview_cold"])
    p_ref, ref_src = own_rate(sum(r["interview"] for r in referred), len(referred), PRIORS["interview_referred"])
    share = len(referred) / float(len(apps)) if apps else 0.2
    p_int = share * p_ref + (1 - share) * p_cold
    import math

    def ceil(x):
        return int(math.ceil(round(x, 6)))
    need_asks = ceil(chats / chat) if chat else 0
    need_invites = min(invite_cap, ceil(need_asks / accept)) if accept else invite_cap
    need_apps = ceil(interviews / p_int) if p_int else 0
    expect_int = round(min(need_apps, apps_cap) * p_int, 1)
    monday = today - datetime.timedelta(days=today.weekday())
    booked = sum(1 for o in data.get("outreach", []) if o.get("booked") and day(o["booked"]) and
                 day(o["booked"]) >= monday)
    ivs = sum(1 for j in data.get("jobs", []) for iv in j.get("interviews", []) or []
              if day(iv.get("date")) and day(iv.get("date")) >= monday)
    advice = []
    if need_apps > apps_cap:
        advice.append("%d applications a week would be needed at these rates but capacity is %d: more referral-first "
                      "jobs and fallback contacts raise the rate, or raise capacity" % (need_apps, apps_cap))
    return {"targets": {"chats": chats, "interviews": interviews},
            "this_week": {"chats_booked": booked, "interviews": ivs},
            "needed_per_week": {"chat_asks": need_asks, "connection_requests": need_invites,
                                "applications": min(need_apps, apps_cap)},
            "expected_interviews_at_capacity": expect_int,
            "rates": {"accept": [round(accept, 2), accept_src], "chat": [round(chat, 2), chat_src],
                      "interview_cold": [p_cold, cold_src], "interview_referred": [p_ref, ref_src]},
            "advice": advice}


FIT_FLOOR, FIT_CEILING, FIT_STEP = 50, 80, 5


def calibrate(data, today, pack_fit, per_day=(5, 10), days=(0, 1, 2, 3, 4), last_change=None):
    """After the first week: if the jobs good enough for a pack keep coming in under the daily minimum (or over
    the maximum), move the pack threshold one step and say how to widen (or narrow) the search. A job found on
    a day off counts for the next planned day. 'Consistently' means 4 of the last 5 planned days."""
    lo, hi = per_day
    found = [day(j.get("first_found")) for j in data.get("jobs", []) if (j.get("fit") or 0) >= pack_fit]
    found = [d for d in found if d]
    applied = sorted(d for d in (day(j.get("applied")) for j in data.get("jobs", [])) if d)
    start = applied[0] if applied else None
    if not start or (today - start).days < 7:
        return {"action": "too early", "reason": "needs a week of sessions first", "pack_fit": pack_fit}
    if last_change and (today - last_change).days < 7:
        return {"action": "wait", "reason": "changed on %s; one change a week" % last_change, "pack_fit": pack_fit}
    planned, d = [], today - datetime.timedelta(days=1)
    while len(planned) < 5 and d >= start:
        if d.weekday() in days:
            planned.append(d)
        d -= datetime.timedelta(days=1)
    counts = []
    for i, p in enumerate(planned):
        prev = planned[i + 1] if i + 1 < len(planned) else p - datetime.timedelta(days=7)
        counts.append(sum(1 for f in found if prev < f <= p))
    low = sum(1 for c in counts if c < lo)
    high = sum(1 for c in counts if c > hi)
    out = {"days": [(p.isoformat(), c) for p, c in zip(planned, counts)], "pack_fit": pack_fit,
           "range": [lo, hi]}
    if len(counts) >= 4 and low >= 4 and pack_fit > FIT_FLOOR:
        out.update(action="lower", to=max(FIT_FLOOR, pack_fit - FIT_STEP),
                   reason="%d of the last %d planned days had fewer than %d jobs good enough for a pack" % (
                       low, len(counts), lo),
                   search=["add the title variants and companies the weekly check found missing",
                           "add the next 10 lesser-known growing companies (job-scout hidden.py rank)",
                           "add any job site in the role families' country not yet searched",
                           "widen the location (commutable towns, remote within the country) if the plan allows"])
    elif len(counts) >= 4 and low >= 4:
        out.update(action="widen search", reason="fewer than %d a day and the threshold is already at its floor "
                   "(%d)" % (lo, FIT_FLOOR), search=["the same widening steps; consider another role family"])
    elif len(counts) >= 4 and high >= 4 and pack_fit < FIT_CEILING:
        out.update(action="raise", to=min(FIT_CEILING, pack_fit + FIT_STEP),
                   reason="%d of the last %d planned days had more than %d jobs good enough for a pack" % (
                       high, len(counts), hi),
                   search=["keep every source; the higher bar keeps the best %d a day" % hi])
    else:
        out.update(action="none", reason="within %d-%d a day" % (lo, hi))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Funnels with counts and a diagnosis.")
    p.add_argument("--file", default=os.path.join("jobsearch", "pipeline.json"))
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("--json", action="store_true")
    t = sub.add_parser("thresholds")
    t.add_argument("--fit", type=int, default=60, help="the alert threshold for Fit")
    cb = sub.add_parser("calibrate", help="after week 1: move the pack threshold if jobs stay under 5 or over 10 a day")
    cb.add_argument("--pack-fit", type=int, required=True, help="the current pack threshold")
    cb.add_argument("--plan", help="MASTER_PLAN.md: 'Applications a day: 5-10' and the session days")
    cb.add_argument("--last-change", help="date of the last automatic change")
    cb.add_argument("--today")
    wp = sub.add_parser("targets")
    wp.add_argument("--plan", help="MASTER_PLAN.md: reads its 'Weekly targets:' line (flags override it)")
    wp.add_argument("--chats", type=int, help="coffee chats a week (default 1)")
    wp.add_argument("--interviews", type=int, help="interviews a week (default 2)")
    wp.add_argument("--capacity", type=int, help="applications a week the person can make (default 5)")
    wp.add_argument("--today")
    a = p.parse_args(argv)
    if a.cmd == "calibrate":
        today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "job-followup"))
        import streak  # noqa: E402
        st = streak.read_plan(open(a.plan, encoding="utf-8").read() if a.plan and os.path.exists(a.plan) else "")
        out = calibrate(json.load(open(a.file, encoding="utf-8")), today, a.pack_fit,
                        (st["per_day_min"], st["per_day"]), st["days"],
                        datetime.date.fromisoformat(a.last_change) if a.last_change else None)
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "targets":
        today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
        t = plan_targets(open(a.plan, encoding="utf-8").read()) if a.plan and os.path.exists(a.plan) else {}
        pick = lambda flag, key, default: flag if flag is not None else (t.get(key) if t.get(key) is not None
                                                                        else default)
        out = weekly_plan(json.load(open(a.file, encoding="utf-8")), today, pick(a.chats, "chats", 1),
                          pick(a.interviews, "interviews", 2), pick(a.capacity, "capacity", 5))
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "thresholds":
        out = thresholds(json.load(open(a.file, encoding="utf-8")), a.fit)
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    rep = report(json.load(open(a.file, encoding="utf-8")))
    if a.json:
        print(json.dumps(rep, indent=1))
        return 0
    A = rep["applications"]
    O = rep["outreach"]
    print("Applications: %d; replied %s; interview %s; offer %s" % (A["total"], A["replied"], A["interview"], A["offer"]))
    print("Outreach: %d; replied %s; chats %s; referrals %s" % (O["total"], O["replied"], O["chat"], O["referral"]))
    if rep["median_days_to_first_reply"] is not None:
        print("Median days to first reply: %s" % rep["median_days_to_first_reply"])
    for title, block in (("By", rep["by"]), ("Outreach by", rep["outreach_by"])):
        for key, groups in block.items():
            print("\n%s %s:" % (title, key.replace("_", " ")))
            for g, line in groups.items():
                parts = ", ".join("%s %s" % (k, v) for k, v in line.items() if k not in ("n", "label"))
                print("  %-18s %s%s" % (g, parts, "  [too few to tell]" if line.get("label") else ""))
    print("\n" + rep["diagnosis"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
