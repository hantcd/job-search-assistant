#!/usr/bin/env python3
"""Make text safe to paste into an application form or email.

    python3 clean_text.py in.txt > out.txt      (or pipe text in)

Removes invisible characters (zero-width spaces and joiners, soft hyphens,
byte-order marks, direction marks), turns non-breaking spaces into spaces, and
uses plain quotes and apostrophes. Dashes are kept: if the person writes with
them, they're theirs. Prints a count of what changed to stderr.
"""

import sys

INVISIBLE = {"​": "", "‌": "", "‍": "", "⁠": "", "﻿": "", "­": "",
             "‎": "", "‏": "", "‪": "", "‫": "", "‬": "", "‭": "", "‮": ""}
SPACES = {" ": " ", " ": " ", " ": " ", " ": " "}
QUOTES = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"',
          "„": '"', "′": "'", "″": '"'}


def clean(text):
    counts = {"invisible": 0, "spaces": 0, "quotes": 0}
    out = []
    for ch in text:
        if ch in INVISIBLE:
            counts["invisible"] += 1
            continue
        if ch in SPACES:
            counts["spaces"] += 1
            out.append(" ")
        elif ch in QUOTES:
            counts["quotes"] += 1
            out.append(QUOTES[ch])
        else:
            out.append(ch)
    return "".join(out), counts


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    text = open(argv[0], encoding="utf-8").read() if argv else sys.stdin.read()
    cleaned, counts = clean(text)
    sys.stdout.write(cleaned)
    print("removed %(invisible)d invisible character(s), fixed %(spaces)d space(s) and %(quotes)d quote(s)" % counts,
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
