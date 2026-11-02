#!/usr/bin/env python3
"""Two checks on a LaTeX CV that the PDF checks can't see.

    python3 tex_check.py escapes cv.tex
    python3 tex_check.py conversion original.pdf cv.tex      # or original.docx text saved as .txt/.md

escapes     In the CV's content (after \\begin{document}), characters LaTeX treats as
            commands: an unescaped % silently deletes the rest of the line; & breaks
            outside tables; # and _ break outside links; an odd number of $ starts maths
            mode. Write \\% \\& \\# \\_ \\$. Link targets in \\href{...} and \\url{...} are fine.
conversion  When a person's CV is turned into the LaTeX base, nothing may be lost or
            added: every word of the original must still be there. Lists words in the
            original that are missing from the LaTeX (FAIL) and words only in the LaTeX
            (WARN: headings and template words are fine; facts are not).

Exit 1 on any FAIL. Ideas from please-hire-me's app_docs.py (MIT, Alex Wang).
"""

import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cvtext import read_text  # noqa: E402

LINK_ARGS = re.compile(r"\\(?:href|url)\{[^}]*\}")
TABLE_ENVS = ("tabular", "tabular*", "tabularx", "array", "align")
TEMPLATE_WORDS = set("""education experience projects skills technical languages frameworks developer tools
libraries summary profile leadership activities interests volunteering publications certifications awards
references available request""".split())


def body_lines(tex):
    start = tex.find("\\begin{document}")
    start = 0 if start < 0 else start
    offset = tex[:start].count("\n")
    return [(offset + i + 1, line) for i, line in enumerate(tex[start:].splitlines())]


def escapes(tex):
    errs = []
    in_table = 0
    for n, raw in body_lines(tex):
        line = raw
        if line.lstrip().startswith("%"):
            continue
        for env in TABLE_ENVS:
            in_table += line.count("\\begin{%s}" % env) - line.count("\\end{%s}" % env)
        text = LINK_ARGS.sub("", line)
        pct = [m.start() for m in re.finditer(r"(?<!\\)%", text)]
        if pct and re.search(r"[A-Za-z0-9]", text[:pct[0]]) and text[:pct[0]].count("{") > text[:pct[0]].count("}"):
            errs.append("line %d: unescaped %% inside text (write \\%%); it deletes the rest of the line" % n)
        if in_table <= 0 and re.search(r"(?<!\\)&", text):
            errs.append("line %d: unescaped & (write \\&)" % n)
        if re.search(r"(?<!\\)#", text):
            errs.append("line %d: unescaped # (write \\#)" % n)
        if re.search(r"(?<![\\$])_", text) and not re.search(r"\$[^$]*_[^$]*\$", text):
            errs.append("line %d: unescaped _ (write \\_)" % n)
        if len(re.findall(r"(?<!\\)\$", text)) % 2:
            errs.append("line %d: odd number of $ (write \\$ for a currency sign)" % n)
    return errs


def words(text):
    return [w for w in re.findall(r"[a-z0-9][a-z0-9+#.%-]*", text.lower().replace("’", "'")) if len(w) > 1 or w.isdigit()]


def conversion(original_text, tex_text):
    a = Counter(w.rstrip(".") for w in words(original_text))
    b = Counter(w.rstrip(".") for w in words(tex_text))
    missing = a - b
    extra = Counter({w: n for w, n in (b - a).items() if w not in TEMPLATE_WORDS})
    return missing, extra


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2 or argv[0] not in ("escapes", "conversion"):
        print(__doc__)
        return 2
    if argv[0] == "escapes":
        errs = escapes(open(argv[1], encoding="utf-8").read())
        for e in errs:
            print("FAIL  " + e)
        print("Escapes: " + ("clean" if not errs else "%d problem(s)" % len(errs)))
        return 1 if errs else 0
    missing, extra = conversion(read_text(argv[1]), read_text(argv[2]))
    fmt = lambda c: ", ".join(w + (" x%d" % n if n > 1 else "") for w, n in sorted(c.items()))  # noqa: E731
    if missing:
        print("FAIL  in the original, missing from the LaTeX: " + fmt(missing))
    if extra:
        print("WARN  only in the LaTeX (check none is a new fact): " + fmt(extra))
    print("Conversion: " + ("nothing lost" if not missing else "%d word(s) lost" % sum(missing.values())))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
