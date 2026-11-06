#!/usr/bin/env python3
"""Check a portfolio page before it's published: true numbers, no private details, readable everywhere.

    python3 portfolio_check.py site.html --source EVIDENCE.md [--source PROFILE.md] [--allow-phone] [--max-kb 600]

FAIL  a number on the page that isn't in the sources (the case studies' results must be real)
FAIL  private details: a phone number (unless --allow-phone), a date of birth, a PPS or other ID number,
      a street address
FAIL  an image without alt text; no <title>; no viewport meta (it won't read on a phone)
FAIL  a tracking or analytics script
WARN  no meta description; the page over --max-kb; a case study section without a number
Standard library only.
"""

import argparse
import html
import os
import re
import sys

NUM = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)(?:\s*(%|k\b|m\b|x\b))?")
PHONE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(?0\d{1,4}\)?[\s-]?)\d{3}[\s-]?\d{3,4}\b")
DOB = re.compile(r"\b(?:date of birth|d\.o\.b|born on)\b", re.I)
IDNUM = re.compile(r"\b(?:\d{7}[A-W][A-IW]?|PPSN?\b|passport (?:no|number))", re.I)
ADDRESS = re.compile(r"\b\d{1,4}\s+[A-Z][a-z]+\s+(?:Street|St\.|Road|Rd\.|Avenue|Ave\.|Lane|Drive|Park|Terrace)\b")
TRACKING = re.compile(r"google-analytics|googletagmanager|gtag\(|facebook\.net|fbq\(|hotjar|segment\.com|mixpanel|plausible\.io", re.I)
YEAR = re.compile(r"^(?:19|20)\d\d$")


def text_of(page):
    page = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", page))


def numbers(s):
    return {m.group(1).replace(",", "") for m in NUM.finditer(s)}


def check(page, sources, allow_phone=False, max_kb=600):
    out = []
    text = text_of(page)
    src = "\n".join(sources)
    new = sorted(n for n in numbers(text) - numbers(src) if not YEAR.match(n) and n not in ("0", "1"))
    for n in new:
        out.append(("FAIL", "number", "%s isn't in your evidence: a result on the page must be real" % n))
    if not allow_phone and PHONE.search(text):
        out.append(("FAIL", "private", "a phone number: leave it off unless you want it public (--allow-phone)"))
    for rx, what in ((DOB, "a date of birth"), (IDNUM, "an ID number"), (ADDRESS, "a street address")):
        if rx.search(text):
            out.append(("FAIL", "private", "%s: keep it off a public page" % what))
    for m in re.finditer(r"<img\b[^>]*>", page, re.I):
        if not re.search(r'\balt\s*=\s*"[^"]+"', m.group(0), re.I):
            out.append(("FAIL", "alt text", "an image without alt text: %s" % m.group(0)[:60]))
    if not re.search(r"<title>[^<]{3,}</title>", page, re.I):
        out.append(("FAIL", "title", "add a <title> (your name and target role)"))
    if not re.search(r'<meta[^>]+name="viewport"', page, re.I):
        out.append(("FAIL", "phone", "add a viewport meta tag so it reads on a phone"))
    if TRACKING.search(page):
        out.append(("FAIL", "tracking", "a tracking or analytics script: leave it out"))
    if not re.search(r'<meta[^>]+name="description"', page, re.I):
        out.append(("WARN", "description", "add a one-line meta description"))
    kb = len(page.encode("utf-8")) / 1024
    if kb > max_kb:
        out.append(("WARN", "size", "%.0f KB: over %d KB loads slowly on a phone" % (kb, max_kb)))
    for sec in re.findall(r"<(?:section|article)\b[^>]*>(.*?)</(?:section|article)>", page, re.S | re.I):
        t = text_of(sec)
        if re.search(r"case study|project|result", t, re.I) and not NUM.search(t):
            out.append(("WARN", "result", "a case study without a number: add its result from your evidence"))
    if not any(r[0] == "FAIL" for r in out):
        out.append(("PASS", "page", "ready to publish when you say so"))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Check a portfolio page before publishing.")
    p.add_argument("page")
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--allow-phone", action="store_true")
    p.add_argument("--max-kb", type=int, default=600)
    a = p.parse_args(argv)
    res = check(open(a.page, encoding="utf-8").read(),
                [open(s, encoding="utf-8").read() for s in a.source if os.path.exists(s)], a.allow_phone, a.max_kb)
    for st, what, detail in res:
        print("%-4s %-11s %s" % (st, what, detail))
    return 1 if any(r[0] == "FAIL" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
