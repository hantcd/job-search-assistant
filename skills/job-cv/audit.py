#!/usr/bin/env python3
"""Quick job audit: how well a CV matches one job ad, in under a minute.

    python3 audit.py ad.txt cv.pdf --role "Junior Data Analyst" [--bank keyword_bank.json] [--json]

Prints
  MATCH        a score out of 100: the ad's terms the CV shows, must-haves counting
               double and nice-to-haves half (reworded terms count half until the ad's
               wording is used)
  MISSING      the top 5 missing terms, must-haves first, then by how often the ad says them
  SKIM         the 10-second skim's pile (YES, MAYBE, NO) and its top 3 red flags
  NEXT         what to do: ask about each missing term (true? then add it in the ad's
               words; not true? it stays a gap), fix the red flags, and whether a
               tailored CV is worth it

The strong-candidate comparison (what the strongest likely applicant's CV shows that
this one doesn't) is written by Claude from the ad and the person's evidence; see
SKILL.md. Neither the score nor the comparison is an employer's ATS result: no
employer publishes its formula.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cvtext import find_terms, load_terms, read_text, term_regex  # noqa: E402
from keywords import compare  # noqa: E402
from skim import must_section, skim  # noqa: E402


def audit(ad, cv, role="", terms=None, bank=None, this_year=2026, graduate=False):
    terms = terms if terms is not None else load_terms()
    must, nice = must_section(ad)
    whole = compare(ad, cv, terms, bank)
    must_r = compare(must, cv, terms, bank) if must.strip() else None
    nice_r = compare(nice, cv, terms, bank) if nice.strip() else None
    must_set = set(must_r["covered"] + must_r["missing"] + [a for a, _ in must_r["reword"]]) if must_r else set()
    nice_set = set(nice_r["covered"] + nice_r["missing"] + [a for a, _ in nice_r["reword"]]) if nice_r else set()

    def weight(t):
        if t in must_set:
            return 2.0
        if t in nice_set and t not in must_set:
            return 0.5
        return 1.0

    # "Power BI or Tableau": one of them is enough, so the others aren't counted as missing
    shown = set(whole["covered"]) | {x for x, _ in whole["reword"]}
    either = set()
    for line in ad.splitlines():
        if re.search(r"\bor\b|/", line):
            on_line = set(find_terms(line, terms).values())
            if on_line & shown:
                either |= on_line - shown
    whole = dict(whole, missing=[t for t in whole["missing"] if t not in either])

    got = sum(weight(t) for t in whole["covered"]) + sum(weight(a) * 0.5 for a, _ in whole["reword"])
    total = sum(weight(t) for t in whole["covered"] + whole["missing"] + [a for a, _ in whole["reword"]])
    score = int(round(100.0 * got / total)) if total else 0

    def often(t):
        return len(term_regex(t).findall(ad))

    missing = sorted(whole["missing"], key=lambda t: (-weight(t), -often(t), t.lower()))
    s = skim(cv, role, "", this_year)
    nxt = []
    for t in missing[:5]:
        nxt.append("Ask: is '%s' true for you? Yes: add it in the ad's words. No: it stays a gap." % t)
    if whole["reword"]:
        nxt.append("Use the ad's wording where true: " + ", ".join("%s (CV says %s)" % x for x in whole["reword"][:5]))
    worth = 50  # about half of what's asked is enough to apply (a guide, not a rule; graduate schemes included)
    if score >= worth and s["pile"] != "NO":
        nxt.append("Worth a tailored CV: start job-cv's tailored CV steps.")
    elif score >= 33:
        nxt.append("A stretch: tailor only if the person confirms some missing terms, and name the biggest gap in the letter.")
    else:
        nxt.append("A long shot on this CV: say so plainly, and check whether the missing terms are real gaps.")
    return {"match": score, "missing": missing[:5], "must_haves_found": bool(must.strip()),
            "reword": whole["reword"], "pile": s["pile"], "red_flags": s["flags"][:3], "next": nxt}


def main(argv=None):
    p = argparse.ArgumentParser(description="Quick job audit: match score, top missing terms, skim flags.")
    p.add_argument("ad")
    p.add_argument("cv")
    p.add_argument("--role", default="")
    p.add_argument("--bank", help="JSON list of extra terms (your keyword bank)")
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--graduate", action="store_true", help="kept for older calls: every job is now worth tailoring from about half")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    bank = json.load(open(a.bank, encoding="utf-8")) if a.bank else None
    r = audit(read_text(a.ad), read_text(a.cv), a.role, bank=bank, this_year=a.year, graduate=a.graduate)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print("MATCH    %d/100  (the ad's terms the CV shows; must-haves count double%s)"
          % (r["match"], "" if r["must_haves_found"] else "; no must-have section found, all terms equal"))
    print("MISSING  " + (", ".join(r["missing"]) or "none"))
    print("SKIM     %s" % r["pile"])
    for i, f in enumerate(r["red_flags"], 1):
        print("  %d. %s" % (i, f))
    print("NEXT")
    for n in r["next"]:
        print("  - " + n)
    print("An estimate to guide edits, not an employer's ATS score.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
