#!/usr/bin/env python3
"""Check a cover letter, note or application answer before anyone sees it.

    python3 letter_check.py letter.md --company "Acme" --role "Junior Data Analyst" \
        [--team "Claims Analytics"] [--source EVIDENCE.md] [--other-companies pipeline.json] [--kind letter|note]
        [--cv cv.md] [--ad ad.txt]

FAIL (exit 1)
  placeholders left in ([Company], {role}, XXX, TODO, [fill: ...])
  another company's name from your job list (a letter copied from another application)
  the company isn't named (letters)
  a number that isn't in your sources (--source)
  over 400 words (letters)
WARN
  the role isn't named; no concrete proof (a sentence with a number); a generic greeting;
  under 150 or over 350 words (letters; a short note is 3-4 sentences); stock phrases and AI tells
  (your own writing samples win: if you really write like that, keep it); a sentence that just
  restates a CV line (--cv) or echoes the ad (--ad): the letter should add what the CV can't

Adapted from cover.py in hunter-skill (MIT, Jake Schincariol).
"""

import argparse
import json
import re
import sys

PLACEHOLDER = re.compile(r"\[(?:company|role|team|name|fill[^\]]*|insert[^\]]*|x+)\]|\{[a-z_ ]+\}|\bXXX+\b|\bTODO\b|\bTBD\b", re.I)
GENERIC_GREETING = re.compile(r"to whom it may concern|dear sir(?: or madam)?|dear hiring manager", re.I)
STOCK = [
    "i am writing to express my interest", "i am writing to apply", "passionate about", "team player",
    "hit the ground running", "think outside the box", "results-driven", "go-getter", "synergy",
    "proven track record", "detail-oriented", "dynamic environment", "fast-paced environment",
    "in today's fast-paced", "i believe i would be a great fit", "perfect fit", "dream job",
    "leverage my", "leveraging my", "i am confident that", "thrilled", "delve", "tapestry", "testament to",
    "navigate the complexities", "ever-evolving", "seamlessly", "cutting-edge", "game-changer",
    "unwavering", "spearheaded", "honed my", "elevate", "embark", "a unique blend",
]
CONTRAST = re.compile(r"\bnot (?:just|only|merely) [^.;]{1,60}?,? but\b", re.I)


def words(text):
    return re.findall(r"[A-Za-z0-9'’-]+", text)


def numbers(text):
    out = set()
    for m in re.finditer(r"(?<![\w.])[€$£]?\d[\d,]*(?:\.\d+)?\s?(?:%|per ?cent|k|m|bn)?", text, re.I):
        n = re.sub(r"(per ?cent)$", "%", m.group(0).strip(), flags=re.I)
        out.add(re.sub(r"[€$£,\s]", "", n).lower())
    return out


STOP = set("""a an and the of to in for on with at by from as or but is are was were be been this that it its
our your their my we you they i he she his her them us me who which what when where how all any more most
other some such no not only so than too very can will just would could should have has had do did does
""".split())


def content_words(text):
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and len(w) > 2 and not w.isdigit()}


def overlaps(text, refs, threshold=0.7):
    """Sentences whose content words mostly come from one reference line."""
    ref_sets = [content_words(r) for r in refs if r.strip()]
    out = []
    for snt in re.split(r"(?<=[.!?])\s+", text):
        cw = content_words(snt)
        if len(cw) >= 5 and any(r and len(cw & r) / len(cw) >= threshold for r in ref_sets):
            out.append(snt.strip()[:70])
    return out


def check(text, company, role="", team="", sources=(), others=(), kind="letter", cv="", ad=""):
    res = []

    def add(name, status, detail):
        res.append((name, status, detail))

    ph = sorted(set(m.group(0) for m in PLACEHOLDER.finditer(text)))
    add("placeholders", "FAIL" if ph else "PASS", ", ".join(ph) if ph else "none")
    low = text.lower()
    wrong = sorted({o for o in others if o and o.lower() != company.lower()
                    and re.search(r"(?<!\w)" + re.escape(o.lower()) + r"(?!\w)", low)})
    add("other companies", "FAIL" if wrong else "PASS", ("remove: " + ", ".join(wrong)) if wrong else "none")
    if kind == "letter":
        add("company named", "PASS" if company.lower() in low else "FAIL", company)
    if role:
        missing = [w for w in words(role) if w.lower() not in low]
        add("role named", "PASS" if not missing else "WARN", role if not missing else "missing: " + " ".join(missing))
    if team:
        add("team named", "PASS" if any(w.lower() in low for w in words(team) if len(w) > 3) else "WARN", team)
    n = len(words(text))
    if kind == "letter":
        status = "FAIL" if n > 400 else ("WARN" if n > 350 or n < 150 else "PASS")
        add("length", status, "%d words (usually 150-350; never over 400)" % n)
    else:
        sentences = len(re.findall(r"[.!?](?:\s|$)", text))
        add("length", "WARN" if sentences > 5 else "PASS", "%d words, %d sentences (a note is 3-4)" % (n, sentences))
    proof = any(re.search(r"\d", s) for s in re.split(r"(?<=[.!?])\s+", text) if len(words(s)) > 5)
    add("concrete proof", "PASS" if proof else "WARN", "a sentence with a number" if proof else "add one true result with a number")
    add("greeting", "WARN" if GENERIC_GREETING.search(text) else "PASS",
        "use a name or the team" if GENERIC_GREETING.search(text) else "ok")
    stock = [s for s in STOCK if s in low] + (["'not X but Y' contrast"] if CONTRAST.search(text) else [])
    add("stock phrases", "WARN" if stock else "PASS", "; ".join(stock) if stock else "none")
    if cv:
        same = overlaps(text, cv.splitlines())
        add("adds to the CV", "WARN" if same else "PASS",
            ("restates a CV line: " + " | ".join(same)) if same else "no sentence just restates the CV")
    if ad:
        echo = overlaps(text, re.split(r"(?<=[.!?])\s+|\n", ad))
        add("own words", "WARN" if echo else "PASS",
            ("echoes the ad: " + " | ".join(echo)) if echo else "no sentence echoes the ad")
    if sources:
        src = numbers("\n".join(sources))
        new = sorted(numbers(text) - src)
        add("numbers traceable", "FAIL" if new else "PASS", ("not in your sources: " + ", ".join(new)) if new else "all found")
    return res


def companies_from(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    names = {j.get("company", "") for j in data.get("jobs", [])}
    return sorted(n for n in names if n and len(n) > 2)


def main(argv=None):
    p = argparse.ArgumentParser(description="Specific, true, short, nothing left over.")
    p.add_argument("file")
    p.add_argument("--company", required=True)
    p.add_argument("--role", default="")
    p.add_argument("--team", default="")
    p.add_argument("--source", action="append", default=[])
    p.add_argument("--other-companies", help="the job list snapshot (pipeline.json)")
    p.add_argument("--kind", choices=("letter", "note", "answer"), default="letter")
    p.add_argument("--cv", help="the tailored CV as text or markdown")
    p.add_argument("--ad", help="the job ad as text")
    a = p.parse_args(argv)
    text = open(a.file, encoding="utf-8").read()
    sources = [open(s, encoding="utf-8").read() for s in a.source]
    others = companies_from(a.other_companies) if a.other_companies else []
    cv = open(a.cv, encoding="utf-8").read() if a.cv else ""
    ad = open(a.ad, encoding="utf-8").read() if a.ad else ""
    res = check(text, a.company, a.role, a.team, sources, others, a.kind, cv, ad)
    for name, status, detail in res:
        print("%-4s  %-18s %s" % (status, name, detail))
    return 1 if any(s == "FAIL" for _, s, _ in res) else 0


if __name__ == "__main__":
    sys.exit(main())
