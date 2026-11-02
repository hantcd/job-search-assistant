#!/usr/bin/env python3
"""Prove a tailored CV, cover letter or answer adds nothing that isn't in your evidence.

    python3 truth_check.py draft.tex --source EVIDENCE.md --source master_cv.md [--allow "Acme" --allow "Data Analyst"]

FAIL  a number, or a known skill or qualification, that no source contains (exit 1)
WARN  other new capitalised words to check by hand (names, places, products)

Sources are the files the facts come from: EVIDENCE.md, PROFILE.md, the master
CV, and answers the person confirmed. --allow adds words you know are fine
(the company and role you're writing to). Rewording is fine; inventing isn't.
Adapted from the truth check in hunter-skill (MIT, Jake Schincariol).
"""

import argparse
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cvtext import AMBIGUOUS, find_terms, load_terms, numbers, read_text

COMMON = set("""a an and the of to in for on with at by from as or but not is are was were be been this that
these those it its our your their my we you they i he she his her them us me who whom which what when where why
how all any each more most other some such no nor only own same so than too very can will just should now
dear hello hi regards sincerely kind best thanks thank yours faithfully january february march april may june
july august september october november december monday tuesday wednesday thursday friday saturday sunday
experience education skills projects summary profile interests volunteering references available request
leadership activities certifications awards publications languages contact email phone linkedin github portfolio
present current""".split())


def cap_words(text):
    """Capitalised words that aren't at the start of a sentence or line."""
    out = set()
    for m in re.finditer(r"(?<=[a-z0-9,;:)]\s)([A-Z][A-Za-z0-9&+.-]{1,})", text):
        w = m.group(1).rstrip(".")
        if w.lower() not in COMMON:
            out.add(w)
    for m in re.finditer(r"\b([A-Z]{2,}[A-Za-z0-9]*)\b", text):  # acronyms anywhere
        out.add(m.group(1))
    return out


def check(draft, sources, allow=()):
    terms = load_terms()
    src = "\n".join(sources) + "\n" + "\n".join(allow)
    src_low = src.lower()
    fails, warns = [], []
    src_nums = numbers(src)
    for n in sorted(numbers(draft) - src_nums, key=lambda x: (len(x), x)):
        fails.append("number %s is not in your sources" % n)
    d_terms = find_terms(draft, terms)
    s_terms = find_terms(src, terms)
    for canon, word in sorted(d_terms.items()):
        if canon not in s_terms:
            msg = "skill or qualification '%s' is not in your sources" % word
            (warns if word in AMBIGUOUS or canon in AMBIGUOUS else fails).append(msg)
    known = {w for g in terms for w in g}
    for w in sorted(cap_words(draft)):
        if w.lower() not in src_low and w not in known and w.lower() not in COMMON:
            warns.append("new word '%s': check it's true (a name, place or product?)" % w)
    return fails, warns


def main(argv=None):
    p = argparse.ArgumentParser(description="Nothing invented: numbers and skills must come from your sources.")
    p.add_argument("draft")
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--allow", action="append", default=[])
    a = p.parse_args(argv)
    fails, warns = check(read_text(a.draft), [read_text(s) for s in a.source], a.allow)
    for f in fails:
        print("FAIL  " + f)
    for w in warns:
        print("WARN  " + w)
    print("Truth check: " + ("CLEAN" if not fails else "%d invented item(s): remove them, or confirm them with the person and add them to EVIDENCE.md" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
