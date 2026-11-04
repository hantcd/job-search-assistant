#!/usr/bin/env python3
"""Prove a tailored CV, cover letter or answer adds nothing that isn't in your evidence.

    python3 truth_check.py draft.tex --source EVIDENCE.md --source master_cv.md [--allow "Acme" --allow "Data Analyst"] [--corrections CORRECTIONS.md]

FAIL  a number, or a known skill or qualification, that no source contains (exit 1)
FAIL  'published' for work the evidence calls under review, submitted, a preprint or internal
FAIL  a mistake the person already corrected (a 'wrong -> right' line in CORRECTIONS.md) is back
WARN  an ownership verb stronger than the evidence: the CV says 'led' where the
      matching evidence line says 'contributed to' or 'helped'
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


# How much ownership a verb claims: 1 helped, 2 did it, 3 led or owned it.
VERB_TIERS = {
    1: r"helped|helping|assisted|supported|contributed|participated|took part|was involved|worked on|collaborated",
    2: r"built|developed|created|designed|wrote|implemented|analy[sz]ed|ran|delivered|produced|automated|made|"
       r"prepared|tested|researched|organi[sz]ed|coordinated|improved|reduced|increased",
    3: r"led|lead|owned|managed|headed|directed|spearheaded|drove|oversaw|launched|founded|architected|championed|"
       r"supervised|ran the|was responsible for",
}
VERB_RE = {t: re.compile(r"\b(?:%s)\b" % pat, re.I) for t, pat in VERB_TIERS.items()}
STOP = COMMON | set("""using used across into over under within team project projects work worked new data""".split())
UNPUBLISHED = re.compile(r"under review|submitted|preprint|in preparation|internal|unpublished|draft", re.I)


def tier(line):
    """The strongest ownership a line claims (0 when it names none)."""
    return max([t for t, rx in VERB_RE.items() if rx.search(line)], default=0)


def content_words(line):
    return {w for w in re.findall(r"[a-z][a-z0-9+#-]{3,}", line.lower()) if w not in STOP
            and not any(rx.fullmatch(w) for rx in VERB_RE.values())}


def lines_of(text):
    out = []
    for l in text.splitlines():
        l = re.sub(r"\\(?:item|resumeItem|textbf|emph)\b|[{}\\]", " ", l)
        l = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", l).strip()
        if len(l) > 15:
            out.append(l)
    return out


def best_match(line, src_lines, need=3):
    words = content_words(line)
    best, score = None, 0
    for s in src_lines:
        n = len(words & content_words(s))
        if n > score:
            best, score = s, n
    return best if score >= need else None


def overclaims(draft, sources):
    """CV lines that claim more ownership, or a firmer publication status, than the evidence."""
    src_lines = [l for s in sources for l in lines_of(s)]
    fails, warns = [], []
    for line in lines_of(draft):
        ev = best_match(line, src_lines)
        if not ev:
            continue
        if re.search(r"\bpublished\b", line, re.I) and UNPUBLISHED.search(ev) and not re.search(r"\bpublished\b", ev, re.I):
            fails.append("'published' is too strong: the evidence says %r" % UNPUBLISHED.search(ev).group(0))
        d, e = tier(line), tier(ev)
        if d > e and e:
            dv = next(rx.search(line).group(0) for t, rx in sorted(VERB_RE.items(), reverse=True) if t == d)
            ev_v = next(rx.search(ev).group(0) for t, rx in sorted(VERB_RE.items(), reverse=True) if t == e)
            warns.append("ownership upgraded: the CV says '%s' where the evidence says '%s' (%s...): use the "
                         "evidence's verb unless the person confirms more" % (dv, ev_v, ev[:60]))
    return fails, warns


def corrections_back(draft, corrections_text):
    out = []
    low = draft.lower()
    for l in corrections_text.splitlines():
        m = re.match(r"\s*[-*]?\s*(.+?)\s*(?:->|=>|→)\s*(.+)$", l)
        if m and m.group(1).strip().lower() in low:
            out.append("a corrected mistake is back: '%s' (the person changed it to '%s')" % (m.group(1).strip(), m.group(2).strip()))
    return out


def check(draft, sources, allow=(), corrections=""):
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
        if w.lower() not in src_low and w not in known and w.lower() not in COMMON and not tier(w) \
                and w.lower() != "published":
            warns.append("new word '%s': check it's true (a name, place or product?)" % w)
    f2, w2 = overclaims(draft, sources)
    fails += f2 + corrections_back(draft, corrections or "")
    warns += w2
    return fails, warns


def main(argv=None):
    p = argparse.ArgumentParser(description="Nothing invented: numbers and skills must come from your sources.")
    p.add_argument("draft")
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--allow", action="append", default=[])
    p.add_argument("--corrections", help="CORRECTIONS.md: one 'wrong -> right' per line")
    a = p.parse_args(argv)
    corr = read_text(a.corrections) if a.corrections and os.path.exists(a.corrections) else ""
    fails, warns = check(read_text(a.draft), [read_text(s) for s in a.source], a.allow, corr)
    for f in fails:
        print("FAIL  " + f)
    for w in warns:
        print("WARN  " + w)
    print("Truth check: " + ("CLEAN" if not fails else "%d invented item(s): remove them, or confirm them with the person and add them to EVIDENCE.md" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
