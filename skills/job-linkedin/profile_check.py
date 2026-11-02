#!/usr/bin/env python3
"""Check a LinkedIn profile pack: field limits, job-ad keywords, and the 100-point score.

    python3 profile_check.py limits pack.json
    python3 profile_check.py keywords pack.json --terms keyword_bank.json
    python3 profile_check.py score ratings.json [--visibility off|light|active]

pack.json:    {"headline", "about", "skills": [...], "positions": [{"title", "description"}],
               "invitation_note"}
ratings.json: points per rubric part, e.g. {"headline": 9, "about_opening": 6, ...} with a reason each:
              {"headline": {"points": 9, "why": "..."}}

The rubric (out of 100): headline 12, About opening (before 'see more') 10, rest of
About 8, current role 10, older roles 6, skills 8, Featured 8, recommendations 8,
photo and banner 8, job-search settings (target city, Open to Work, verified
identity and workplace, custom URL) 12, activity 10 (full marks when visibility is Off).
Limits come from limits.json (LinkedIn Help where stated, otherwise as widely
reported; LinkedIn's own character counter is the authority).
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUBRIC = {"headline": 12, "about_opening": 10, "about_rest": 8, "current_role": 10, "older_roles": 6,
          "skills": 8, "featured": 8, "recommendations": 8, "photo_banner": 8, "settings": 12, "activity": 10}
REWRITE_CANT_FIX = ("recommendations", "activity")


def limits():
    with open(os.path.join(HERE, "limits.json"), encoding="utf-8") as fh:
        return json.load(fh)["fields"]


def check_limits(pack):
    L = limits()
    out = []

    def length(name, text):
        m = L[name]["max"]
        n = len(text or "")
        out.append(("FAIL" if n > m else "PASS", name, "%d / %d characters" % (n, m)))

    length("headline", pack.get("headline", ""))
    length("about", pack.get("about", ""))
    skills = pack.get("skills", [])
    out.append(("FAIL" if len(skills) > L["skills"]["max"] else "PASS", "skills", "%d / %d skills" % (len(skills), L["skills"]["max"])))
    for i, pos in enumerate(pack.get("positions", [])):
        length("position_title", pos.get("title", ""))
        length("position_description", pos.get("description", ""))
    if pack.get("invitation_note"):
        length("invitation_note", pack["invitation_note"])
    about = pack.get("about", "")
    opening = about[:265]
    out.append(("INFO", "about opening", "first ~265 characters show before 'see more': %r" % opening[:80]))
    if re.search(r"#\w", pack.get("headline", "") + about):
        out.append(("WARN", "hashtags", "hashtags in the headline or About add little; cut them"))
    return out


def keyword_coverage(pack, terms):
    text = " ".join([pack.get("headline", ""), pack.get("about", ""), " ".join(pack.get("skills", []))] +
                    [p.get("title", "") + " " + p.get("description", "") for p in pack.get("positions", [])]).lower()
    have = [t for t in terms if t.lower() in text]
    miss = [t for t in terms if t.lower() not in text]
    head = pack.get("headline", "").lower()
    return have, miss, [t for t in terms if t.lower() in head]


def score(ratings, visibility="light"):
    total, rows = 0, []
    for part, maxpts in RUBRIC.items():
        r = ratings.get(part, 0)
        pts, why = (r.get("points", 0), r.get("why", "")) if isinstance(r, dict) else (r, "")
        if part == "activity" and visibility == "off":
            pts, why = maxpts, "visibility is Off: full marks"
        if not 0 <= pts <= maxpts:
            raise ValueError("%s must be 0-%d, got %r" % (part, maxpts, pts))
        total += pts
        rows.append((part, pts, maxpts, why))
    rows.sort(key=lambda r: -(r[2] - r[1]))  # most points lost first
    return total, rows


def main(argv=None):
    p = argparse.ArgumentParser(description="LinkedIn profile pack checks.")
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("limits")
    l.add_argument("pack")
    k = sub.add_parser("keywords")
    k.add_argument("pack")
    k.add_argument("--terms", required=True, help="JSON list of terms (keyword bank for the primary role family)")
    s = sub.add_parser("score")
    s.add_argument("ratings")
    s.add_argument("--visibility", choices=("off", "light", "active"), default="light")
    a = p.parse_args(argv)
    if a.cmd == "limits":
        rows = check_limits(json.load(open(a.pack, encoding="utf-8")))
        for st, name, detail in rows:
            print("%-4s  %-22s %s" % (st, name, detail))
        return 1 if any(r[0] == "FAIL" for r in rows) else 0
    if a.cmd == "keywords":
        have, miss, head = keyword_coverage(json.load(open(a.pack, encoding="utf-8")),
                                            json.load(open(a.terms, encoding="utf-8")))
        print("IN PROFILE   " + (", ".join(have) or "none"))
        print("IN HEADLINE  " + (", ".join(head) or "none"))
        print("MISSING      " + (", ".join(miss) or "none") + "  (add only what's true)")
        return 0
    total, rows = score(json.load(open(a.ratings, encoding="utf-8")), a.visibility)
    print("Profile score: %d/100" % total)
    for part, pts, mx, why in rows:
        flag = "  (a rewrite can't fix this)" if part in REWRITE_CANT_FIX and pts < mx else ""
        print("  %-16s %2d/%-2d %s%s" % (part, pts, mx, why, flag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
