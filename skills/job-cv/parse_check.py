#!/usr/bin/env python3
"""Read a CV the way an applicant tracking system does: from the PDF's text layer.

    python3 parse_check.py cv.pdf --name "Aoife Byrne" --email aoife.byrne@example.com --phone "+353 87 123 4567" \
        --headings "Experience,Education,Skills" --term SQL --term "Power BI"

A CV can look perfect and still extract as garbage: icon fonts where the email
should be, ligatures that turn "fi" into one unknown glyph, multi-column text
read in the wrong order. This checks the extracted text:

  FAIL  almost no text; (cid:NNN) markers, replacement characters or private-use
        glyphs (icon fonts); ligature characters (fi, fl as one glyph); the name
        not near the top; the email or phone missing as plain text (a contact
        detail carried only by an icon or a link is invisible to an ATS);
        a heading missing or out of order; a must-have term missing
  PASS  otherwise

Needs PyMuPDF (pip install pymupdf). Ideas from ai-job-search's ATS check (MIT,
Mads Lorentzen).
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cvtext import read_text  # noqa: E402

LIGATURES = "ﬀﬁﬂﬃﬄﬅﬆ"


def check(text, name="", email="", phone="", headings=(), terms=()):
    res = []

    def add(n, ok, detail):
        res.append((n, "PASS" if ok else "FAIL", detail))

    words = re.findall(r"\w+", text)
    add("text layer", len(words) > 50, "%d words extracted" % len(words))
    cid = len(re.findall(r"\(cid:\d+\)", text))
    bad = text.count("�")
    pua = sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF)
    add("no garbled glyphs", not (cid or bad or pua),
        "none" if not (cid or bad or pua) else "%d (cid:) markers, %d replacement characters, %d icon-font glyphs" % (cid, bad, pua))
    lig = sum(text.count(c) for c in LIGATURES)
    add("no ligature glyphs", not lig, "none" if not lig else "%d ligature glyph(s): add \\input{glyphtounicode} and \\pdfgentounicode=1" % lig)
    flat = re.sub(r"\s+", " ", text)
    if name:
        i = flat.lower().find(name.lower())
        add("name at the top", 0 <= i < 200, "found at character %d" % i if i >= 0 else "not found as text")
    if email:
        add("email as text", email.lower() in flat.lower(), email)
    else:
        add("email as text", bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", flat)), "any email address")
    if phone:
        digits = re.sub(r"\D", "", phone)[-8:]
        add("phone as text", digits in re.sub(r"\D", "", flat), phone)
    if headings:
        pos, last, ok, missing = [], -1, True, []
        low = flat.lower()
        for h in headings:
            m = re.search(r"\b%s\b" % re.escape(h.lower()), low)
            if not m:
                missing.append(h)
                ok = False
                continue
            if m.start() < last:
                ok = False
            last = m.start()
            pos.append(h)
        add("headings in order", ok, "missing: " + ", ".join(missing) if missing else " > ".join(pos))
    for t in terms:
        add("term: " + t, re.search(r"(?<!\w)%s(?!\w)" % re.escape(t), flat, re.I) is not None, t)
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description="What an ATS reads from the CV's text layer.")
    p.add_argument("pdf")
    p.add_argument("--name", default="")
    p.add_argument("--email", default="")
    p.add_argument("--phone", default="")
    p.add_argument("--headings", default="", help="comma-separated, in the order they appear")
    p.add_argument("--term", action="append", default=[], help="a must-have term from the job ad")
    a = p.parse_args(argv)
    text = read_text(a.pdf)
    res = check(text, a.name, a.email, a.phone, [h.strip() for h in a.headings.split(",") if h.strip()], a.term)
    for n, st, d in res:
        print("%-4s  %-22s %s" % (st, n, d))
    return 1 if any(st == "FAIL" for _, st, _ in res) else 0


if __name__ == "__main__":
    sys.exit(main())
