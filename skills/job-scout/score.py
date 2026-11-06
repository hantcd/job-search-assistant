#!/usr/bin/env python3
"""Score jobs the same way every time: one Fit score (from Career Value and Attainability), confidence and legitimacy.

Claude reads each ad and rates every part of your scoring (0-5, with a reason
and how well the ad supports it). This script does the arithmetic, so the same
ratings always give the same score, and it rates whether the posting looks
real. Your weights and thresholds come from the JSON block in
PREFERENCES_AND_SCORING.md (format below).

    python3 score.py score ratings.json --prefs PREFERENCES_AND_SCORING.md --today 2026-10-16
    python3 score.py alerts scored.json --prefs PREFERENCES_AND_SCORING.md
    python3 score.py legitimacy signals.json
    python3 score.py example-prefs

ratings.json: a list of
  {"id", "posted", "thin_ad": false,
   "career_value":  {"<part>": {"rating": 0-5, "support": "supported|partial|unknown", "why": "..."}},
   "attainability": {"<part>": {...}},
   "signals": {...}}            # optional, for the legitimacy rating (see legitimacy below)

Fit: the one score the person sees, out of 100: by default 60% Career Value
(how good the job is for them) and 40% Attainability (how likely they are to
get it), set in prefs "fit". Alerts and packs use Fit; the two parts stay in
the breakdown to explain it.

Rules: weights total 100 in each part; Career Value never goes down because a
job is hard (that's Attainability's job); missing evidence never counts as
neutral, so an 'unknown' part scores at most 2 of 5; jobs under 48 hours old
are flagged APPLY TODAY and rank first among similar scores (within 5 points).
"""

import argparse
import datetime
import json
import re
import sys

SUPPORT = ("supported", "partial", "unknown")
UNKNOWN_CAP = 2  # an unknown part can't score above 2/5

EXAMPLE_PREFS = {
    "career_value": {"weights": {"learning": 30, "pay": 20, "people": 15, "responsibility": 15,
                                 "stability": 10, "prestige": 10}},
    "attainability": {"weights": {"must_haves_met": 40, "level_fit": 25, "eligibility": 15,
                                  "connection": 10, "competition": 10}},
    "fit": {"career_value": 60, "attainability": 40},
    "thresholds": {"alert_fit": 60, "pack_fit": 62},
    "max_alerts": 5,
    "packs_per_alert": 2,
    "_current_job": "optional, for someone in work: {\"career_value\": 64, \"margin\": 5} (their current job "
                    "rated on the same Career Value parts); alerts then only include jobs that beat it by the margin",
}


class ScoreError(Exception):
    pass


def read_prefs(path):
    """The first ```json block in PREFERENCES_AND_SCORING.md (or a plain .json file)."""
    text = open(path, encoding="utf-8").read()
    if path.endswith(".json"):
        prefs = json.loads(text)
    else:
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
        if not m:
            raise ScoreError("no ```json block in %s (see: score.py example-prefs)" % path)
        prefs = json.loads(m.group(1))
    for key in ("career_value", "attainability"):
        w = prefs.get(key, {}).get("weights")
        if not w:
            raise ScoreError("prefs need %s.weights" % key)
        if sum(w.values()) != 100:
            raise ScoreError("%s weights total %d, not 100" % (key, sum(w.values())))
    f = prefs.setdefault("fit", {"career_value": 60, "attainability": 40})
    if f.get("career_value", 0) + f.get("attainability", 0) != 100:
        raise ScoreError("fit weights total %d, not 100" % (f.get("career_value", 0) + f.get("attainability", 0)))
    t = prefs.setdefault("thresholds", {})
    if "alert_fit" not in t:
        t["alert_fit"] = convert_threshold(t, f)
        t.setdefault("pack_fit", t["alert_fit"] + 2)
    return prefs


def fit_of(cv, att, f):
    return int(round((cv * f.get("career_value", 60) + att * f.get("attainability", 40)) / 100.0))


def convert_threshold(t, f):
    """Older plans set two thresholds; the default pair (70, 40) becomes Fit 60, others are combined."""
    cv, att = t.get("alert_career_value", 70), t.get("alert_attainability", 40)
    if (cv, att) == (70, 40):
        return 60
    return fit_of(cv, att, f)


def part_score(weights, parts, label):
    total, breakdown, notes = 0.0, {}, []
    for name, weight in weights.items():
        p = parts.get(name)
        if p is None:
            p = {"rating": 0, "support": "unknown", "why": "not rated"}
            notes.append("%s.%s not rated: counted as unknown" % (label, name))
        r = p.get("rating")
        if not isinstance(r, (int, float)) or not 0 <= r <= 5:
            raise ScoreError("%s.%s rating must be 0-5, got %r" % (label, name, r))
        s = p.get("support", "unknown")
        if s not in SUPPORT:
            raise ScoreError("%s.%s support must be supported, partial or unknown" % (label, name))
        used = min(r, UNKNOWN_CAP) if s == "unknown" else r
        if used != r:
            notes.append("%s.%s is unknown, so %s/5 was capped at %d" % (label, name, r, UNKNOWN_CAP))
        pts = weight * used / 5.0
        total += pts
        breakdown[name] = {"points": round(pts, 1), "of": weight, "rating": used, "support": s,
                           "why": p.get("why", "")}
    extra = set(parts) - set(weights)
    if extra:
        notes.append("%s parts not in your weights, ignored: %s" % (label, ", ".join(sorted(extra))))
    return int(round(total)), breakdown, notes


def confidence(weights_cv, weights_att, job):
    """HIGH only if every part is supported; LOW if the ad is thin or a key part is unknown."""
    allparts = []
    for key, weights in (("career_value", weights_cv), ("attainability", weights_att)):
        parts = job.get(key, {})
        top = sorted(weights, key=weights.get, reverse=True)[:2]  # the key parts
        for name in weights:
            s = (parts.get(name) or {}).get("support", "unknown")
            allparts.append((key, name, s, name in top))
    if job.get("thin_ad") or any(s == "unknown" and key_part for _, _, s, key_part in allparts):
        level = "LOW"
    elif all(s == "supported" for _, _, s, _ in allparts):
        level = "HIGH"
    else:
        level = "MEDIUM"
    checks = ["%s: %s" % (n, "find out" if s == "unknown" else "confirm")
              for key, n, s, k in sorted(allparts, key=lambda x: (not x[3], x[2] != "unknown"))
              if s != "supported"][:3]
    return level, checks


def legitimacy(sig):
    """Rate whether a posting looks real and active. Never changes the score.

    signals: age_days, reposts_90d, apply_works (true/false/null), vague (bool),
    recent_layoffs (bool), on_company_site (true/false/null)
    """
    age = sig.get("age_days")
    reposts = sig.get("reposts_90d") or 0
    reasons = []
    if age is not None and age > 60:
        reasons.append("posted %d days ago (over 60 is concerning)" % age)
    if reposts >= 2:
        reasons.append("the same role was posted %d times in 90 days" % reposts)
    if sig.get("apply_works") is False:
        reasons.append("the apply button doesn't work")
    if sig.get("vague"):
        reasons.append("the ad is vague or contradicts itself")
    if sig.get("recent_layoffs"):
        reasons.append("the company had recent layoffs")
    if sig.get("on_company_site") is False:
        reasons.append("not found on the company's own site")
    stale_repost = age is not None and age > 60 and reposts >= 2
    if stale_repost or sig.get("apply_works") is False or (sig.get("vague") and sig.get("on_company_site") is False):
        rating = "SUSPICIOUS"
    elif reasons:
        rating = "PROCEED WITH CAUTION"
    else:
        rating = "HIGH CONFIDENCE"
    return rating, reasons


def age_days(posted, today):
    try:
        return (today - datetime.date.fromisoformat(str(posted)[:10])).days
    except (TypeError, ValueError):
        return None


def score_all(jobs, prefs, today):
    wcv = prefs["career_value"]["weights"]
    watt = prefs["attainability"]["weights"]
    out = []
    for job in jobs:
        cv, cv_b, n1 = part_score(wcv, job.get("career_value", {}), "career_value")
        att, att_b, n2 = part_score(watt, job.get("attainability", {}), "attainability")
        level, checks = confidence(wcv, watt, job)
        age = age_days(job.get("posted"), today)
        row = {"id": job.get("id"), "fit": fit_of(cv, att, prefs.get("fit", {})),
               "career_value": cv, "attainability": att, "confidence": level,
               "checks": checks, "apply_today": age is not None and 0 <= age < 2,
               "age_days": age, "score_breakdown": {"career_value": cv_b, "attainability": att_b},
               "notes": n1 + n2}
        if "signals" in job:
            sig = dict(job["signals"])
            sig.setdefault("age_days", age)
            row["legitimacy"], row["legitimacy_reasons"] = legitimacy(sig)
        out.append(row)
    return rank(out)


def key(r):
    return r.get("fit", r.get("career_value", 0))


def rank(rows):
    """Highest Fit first; among scores within 5 points, fresher first."""
    rows = sorted(rows, key=lambda r: -key(r))
    ranked = []
    while rows:
        top = key(rows[0])
        band = [r for r in rows if top - key(r) <= 5]
        rows = [r for r in rows if top - key(r) > 5]
        band.sort(key=lambda r: (not r.get("apply_today"), r.get("age_days") if r.get("age_days") is not None else 9999,
                                 -key(r)))
        ranked.extend(band)
    return ranked


def alerts(scored, prefs):
    t = prefs.get("thresholds", {})
    f = prefs.get("fit", {"career_value": 60, "attainability": 40})
    fit_min = t["alert_fit"] if "alert_fit" in t else convert_threshold(t, f)
    for r in scored:
        r.setdefault("fit", fit_of(r["career_value"], r["attainability"], f))
    keep = [r for r in scored if r["fit"] >= fit_min
            and r.get("legitimacy") != "SUSPICIOUS" and not r.get("alerted")]
    cur = prefs.get("current_job")
    if cur and cur.get("career_value") is not None:
        # Someone already in work only hears about jobs that beat the one they have, on their own Career Value.
        bar = cur["career_value"] + cur.get("margin", 5)
        for r in keep:
            r["beats_current_by"] = r["career_value"] - cur["career_value"]
        keep = [r for r in keep if r["career_value"] >= bar]
    keep = rank(keep)[: prefs.get("max_alerts", 5)]
    pack_min = t.get("pack_fit", fit_min + 2)
    packs = [r["id"] for r in keep if r["fit"] >= pack_min][: prefs.get("packs_per_alert", 2)]
    return keep, packs


def main(argv=None):
    p = argparse.ArgumentParser(description="Fit (from Career Value and Attainability), confidence and legitimacy.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("ratings")
    s.add_argument("--prefs", required=True)
    s.add_argument("--today")
    a = sub.add_parser("alerts")
    a.add_argument("scored")
    a.add_argument("--prefs", required=True)
    l = sub.add_parser("legitimacy")
    l.add_argument("signals")
    sub.add_parser("example-prefs")
    a = p.parse_args(argv)
    try:
        if a.cmd == "example-prefs":
            print("```json\n" + json.dumps(EXAMPLE_PREFS, indent=1) + "\n```")
            return 0
        if a.cmd == "legitimacy":
            rating, reasons = legitimacy(json.load(open(a.signals, encoding="utf-8")))
            print(json.dumps({"legitimacy": rating, "reasons": reasons}, indent=1))
            return 0
        prefs = read_prefs(a.prefs)
        if a.cmd == "score":
            today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
            jobs = json.load(open(a.ratings, encoding="utf-8"))
            print(json.dumps(score_all(jobs, prefs, today), indent=1, ensure_ascii=False))
            return 0
        if a.cmd == "alerts":
            keep, packs = alerts(json.load(open(a.scored, encoding="utf-8")), prefs)
            if not keep:
                print("Nothing new above your thresholds.")
                return 1
            print(json.dumps({"alert": [r["id"] for r in keep], "make_packs": packs}, indent=1))
            return 0
    except (ScoreError, ValueError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
