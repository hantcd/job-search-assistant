#!/usr/bin/env python3
"""The 10-second skim: what a busy reader sees first, the red flags, and a pile.

    python3 skim.py cv.pdf --role "Junior Data Analyst" [--ad ad.txt] [--json]

A recruiter sorting a pile reads the top third and a few bullets, then puts the CV
in yes, maybe or no. This script estimates that skim from the text alone:

  RED FLAGS (strongest first, the top 3 shown first)
    the top third doesn't name the job you're after
    no result with a number in the top third
    under a third of the bullets have a number
    bullets that open with "Responsible for", "Helped with", "Duties included"...
    bullets over two lines
    a gap of a year or more between dated roles, with no line explaining it
    personal details Irish and UK employers don't ask for (date of birth, age,
      marital status, nationality, a photo)
    (with --ad) the ad's must-have terms missing from the whole CV
  PILE  YES (no strong flag, at most one other), MAYBE, or NO (two or more strong flags)

It is an estimate of a quick human read, not an employer's screening and not an ATS
score. Fixes come from the person's evidence: a missing number is asked for, never
made up.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cvtext import read_text  # noqa: E402

WEAK = re.compile(r"^(?:responsible for|helped (?:with|to)?|duties (?:included|include)|worked on|assisted (?:with|in)?|"
                  r"tasks included|involved in|participated in|in charge of)\b", re.I)
BULLET = re.compile(r"^\s*(?:[-*•▪◦·‣]|\\item)\s*(.+)$")
PERSONAL = re.compile(r"\b(?:date of birth|d\.o\.b\.?|dob|born (?:on|in) \d|age:?\s*\d{2}\b|marital status|"
                      r"status:?\s*(?:single|married)|nationality|religion|\\includegraphics|photo(?:graph)?:)", re.I)
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
RANGE = re.compile(r"(?:(%s)[a-z]*\.?\s+)?((?:19|20)\d\d)\s*(?:-|–|—|to)\s*(?:(?:(%s)[a-z]*\.?\s+)?((?:19|20)\d\d)|"
                   r"(present|now|current|today|date))" % (MONTHS, MONTHS), re.I)
GAP_NOTE = re.compile(r"\b(?:career break|travell?ing|travel|caring|carer|parental|maternity|paternity|sabbatical|"
                      r"study|studying|full-time study|illness|recovery|volunteer(?:ing)?|gap year)\b", re.I)
MUST_HEAD = re.compile(r"^\s*(?:requirements|what you(?:'|’)ll (?:need|bring)|what we(?:'|’)re looking for|must[- ]haves?|"
                       r"essential|qualifications|about you|you have|you(?:'|’)ll have|who you are)\b", re.I)
NICE_HEAD = re.compile(r"^\s*(?:nice[- ]to[- ]have|bonus|preferred|desirable|it(?:'|’)s a plus|plus if|extra credit|"
                       r"what we offer|benefits|perks)\b", re.I)


def month_num(m):
    if not m:
        return None
    return MONTHS.split("|").index(m.lower()[:3]) + 1 if m.lower()[:3] in MONTHS.split("|") else None


def ranges(text, this_year=2026):
    out = []
    for m in RANGE.finditer(text):
        m1, y1, m2, y2, now = m.groups()
        start = int(y1) + ((month_num(m1) or 1) - 1) / 12.0
        end = this_year + 0.99 if now else int(y2) + ((month_num(m2) or 12) - 1) / 12.0
        if end >= start:
            out.append((start, end, m.group(0)))
    return out


def gaps(text, this_year=2026, min_years=1.0):
    rs = sorted(ranges(text, this_year))
    out, reach = [], None
    for start, end, label in rs:
        if reach is not None and start - reach[0] >= min_years:
            out.append("between '%s' and '%s'" % (reach[1], label))
        if reach is None or end > reach[0]:
            reach = (end, label)
    return out


def must_section(ad):
    """The ad's must-have lines (under a requirements heading, before a nice-to-have heading)."""
    must, nice, mode = [], [], None
    for line in ad.splitlines():
        if NICE_HEAD.match(line):
            mode = "nice"
            continue
        if MUST_HEAD.match(line):
            mode = "must"
            continue
        if mode == "must":
            must.append(line)
        elif mode == "nice":
            nice.append(line)
    return "\n".join(must), "\n".join(nice)


def bullets(text):
    out = []
    for line in text.splitlines():
        m = BULLET.match(line)
        if m and len(m.group(1).split()) >= 3:
            out.append(m.group(1).strip())
    return out


def skim(cv, role="", ad="", this_year=2026):
    lines = [l for l in cv.splitlines() if l.strip()]
    top = "\n".join(lines[:max(6, len(lines) // 3)])
    flags = []  # (strength 3 strong / 2 / 1, text)

    if role:
        role_words = [w for w in re.findall(r"[A-Za-z]+", role) if len(w) > 2 and w.lower() not in ("junior", "senior", "graduate", "associate", "the", "and")]
        hit = [w for w in role_words if re.search(r"\b%s" % re.escape(w), top, re.I)]
        if role_words and len(hit) < max(1, len(role_words) // 2 + len(role_words) % 2):
            flags.append((3, "The top third doesn't say you're a %s: add a headline that names the role." % role))
    if not re.search(r"\d+\s?(?:%|per ?cent|x|k\b|m\b|hours?|days?|weeks?|people|managers|users|customers|clients)|[€$£]\s?\d", top, re.I):
        flags.append((3, "No result with a number in the top third: lead with your strongest true result."))
    bs = bullets(cv)
    if bs:
        with_num = [b for b in bs if re.search(r"\d", b)]
        if len(with_num) * 3 < len(bs):
            flags.append((2, "Only %d of %d bullets have a number: ask yourself 'how many, how much, how fast' for each."
                          % (len(with_num), len(bs))))
        weak = [b for b in bs if WEAK.match(b)]
        if weak:
            flags.append((2 if len(weak) > 1 else 1, "%d bullet(s) open with a duty, not a result: \"%s\"" % (len(weak), weak[0][:60])))
        long_ = [b for b in bs if len(b) > 200 or len(b.split()) > 34]
        if long_:
            flags.append((1, "%d bullet(s) run over two lines: \"%s...\"" % (len(long_), long_[0][:50])))
    g = gaps(cv, this_year)
    if g and not GAP_NOTE.search(cv):
        flags.append((2, "A gap of a year or more %s with nothing explaining it: one honest line is enough." % g[0]))
    pers = sorted({m.group(0).strip().lower() for m in PERSONAL.finditer(cv)})
    if pers:
        flags.append((2, "Personal details Irish and UK employers don't ask for: %s. Remove them." % ", ".join(pers)))
    if ad:
        from keywords import compare  # noqa: E402
        from cvtext import load_terms  # noqa: E402
        must, _ = must_section(ad)
        r = compare(must or ad, cv, load_terms())
        if r["missing"] and len(r["missing"]) * 2 >= len(r["missing"]) + len(r["covered"]) + len(r["reword"]):
            flags.append((3, "Half or more of the ad's must-haves aren't on the CV: %s." % ", ".join(r["missing"][:5])))
    flags.sort(key=lambda f: -f[0])
    strong = sum(1 for f in flags if f[0] == 3)
    if strong >= 2:
        pile = "NO"
    elif strong == 1 or len(flags) > 2:
        pile = "MAYBE"
    else:
        pile = "YES"
    return {"pile": pile, "flags": [f[1] for f in flags], "strong": strong, "top_third": top}


def main(argv=None):
    p = argparse.ArgumentParser(description="The 10-second skim: red flags and a yes/maybe/no pile.")
    p.add_argument("cv")
    p.add_argument("--role", default="")
    p.add_argument("--ad")
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    r = skim(read_text(a.cv), a.role, read_text(a.ad) if a.ad else "", a.year)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print("PILE: %s  (an estimate of a 10-second human skim, not an employer's screening)" % r["pile"])
    for i, f in enumerate(r["flags"], 1):
        print("%s %d. %s" % ("RED FLAG" if i <= 3 else "also    ", i, f))
    if not r["flags"]:
        print("No red flags in the skim.")
    print("Fix from the evidence: a missing number is asked for, never made up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
