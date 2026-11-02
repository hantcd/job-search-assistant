#!/usr/bin/env python3
"""Which of a job ad's skills and qualifications your CV shows, in the ad's own words.

    python3 keywords.py ad.txt cv.tex [--bank keyword_bank.json]

Reports three lists:
  COVERED  in the CV, worded as the ad words it
  REWORD   in the CV, but worded differently (use the ad's wording where true)
  MISSING  not in the CV: ask the person whether it's true; if not, it stays a gap

Also lists abbreviations that appear without their full form (or the reverse),
since searches use either. This is a check you can read line by line, not a
copy of any employer's ATS, which don't publish their formulas.
"""

import argparse
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cvtext import find_terms, load_terms, read_text, term_regex


def ad_terms(ad, terms, bank=None):
    found = find_terms(ad, terms)
    if bank:
        for t in bank:
            if term_regex(t).search(ad):
                found.setdefault(t, t)
    return found


def compare(ad, cv, terms, bank=None):
    wanted = ad_terms(ad, terms, bank)
    groups = {g[0]: g for g in terms}
    covered, reword, missing = [], [], []
    for canon, ad_word in sorted(wanted.items(), key=lambda kv: kv[0].lower()):
        if term_regex(ad_word).search(cv):
            covered.append(ad_word)
            continue
        alts = [w for w in groups.get(canon, [canon]) if w != ad_word]
        hit = next((w for w in alts if term_regex(w).search(cv)), None)
        if hit:
            reword.append((ad_word, hit))
        else:
            missing.append(ad_word)
    # abbreviation pairs: both forms help search
    pairs = []
    for g in terms:
        short = [w for w in g if re.fullmatch(r"[A-Z0-9/&+#.]{2,6}", w)]
        long_ = [w for w in g if " " in w and w.lower() == w.lower() and len(w) > 6]
        if short and long_:
            has_s = any(term_regex(w).search(cv) for w in short)
            has_l = any(term_regex(w).search(cv) for w in long_)
            if g[0] in wanted and has_s != has_l:
                pairs.append("%s / %s" % (short[0], long_[0]))
    total = len(wanted)
    pct = int(round(100.0 * len(covered) / total)) if total else 100
    return {"covered": covered, "reword": reword, "missing": missing, "abbreviations": pairs, "coverage": pct}


def main(argv=None):
    p = argparse.ArgumentParser(description="Job ad terms the CV shows, in the ad's own words.")
    p.add_argument("ad")
    p.add_argument("cv")
    p.add_argument("--bank", help="JSON list of extra terms (your keyword bank)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    bank = json.load(open(a.bank, encoding="utf-8")) if a.bank else None
    r = compare(read_text(a.ad), read_text(a.cv), load_terms(), bank)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print("Coverage of the ad's terms, in its own words: %d%%" % r["coverage"])
    print("COVERED  " + (", ".join(r["covered"]) or "none"))
    print("REWORD   " + (", ".join("%s (CV says %s)" % x for x in r["reword"]) or "none"))
    print("MISSING  " + (", ".join(r["missing"]) or "none"))
    if r["abbreviations"]:
        print("BOTH FORMS help search: " + ", ".join(r["abbreviations"]))
    print("Only add a missing term if the person confirms it's true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
