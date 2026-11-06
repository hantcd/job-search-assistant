#!/usr/bin/env python3
"""Check a LinkedIn post draft against what's known about reach, each rule with how sure we are.

    python3 post_check.py post.txt [--format text|document|image]

Confidence: CONFIRMED (LinkedIn staff have said so), LARGE-SCALE (patterns in
datasets of millions of posts: Richard van der Blom, AuthoredUp, Buffer),
PRACTITIONER (creators' experience). Gathered by
attainmentlabs/linkedin-algorithm-skill; ideas only, none of its text is used.

FAIL  an external link in the body (put it in the first comment); 6+ hashtags
WARN  the first ~210 characters (before 'see more') don't hook: no number,
      question or concrete claim; under 600 or over 1,500 characters;
      no closing question; a wall of text (a paragraph over 4 lines);
      'Great post'-style engagement bait ("comment YES", "like if")
NOTE  document (PDF carousel) posts reach furthest in every large dataset;
      reply to comments in the first hour.
The post is the person's: they edit and post it themselves.
"""

import argparse
import re
import sys

URL = re.compile(r"https?://\S+|www\.\S+")
BAIT = re.compile(r"\b(?:comment (?:yes|below|'?\w+'? if)|like if|tag (?:a|someone)|share if|agree\?$)", re.I | re.M)


def check(text, fmt="text"):
    res = []

    def add(status, conf, name, detail):
        res.append((status, conf, name, detail))

    body = text.strip()
    if URL.search(body):
        add("FAIL", "LARGE-SCALE", "links", "an external link in the post cuts its reach: put it in the first comment")
    tags = re.findall(r"(?<!\w)#\w+", body)
    if len(tags) >= 6:
        add("FAIL", "LARGE-SCALE", "hashtags", "%d hashtags: 6+ goes with much lower reach; use 0-3" % len(tags))
    elif tags:
        add("PASS", "LARGE-SCALE", "hashtags", "%d (0-3 is fine)" % len(tags))
    hook = body[:210]
    if not (re.search(r"\d", hook) or "?" in hook or re.search(r"\b(?:I|we) (?:built|cut|learned|got|lost|made|was)\b", hook)):
        add("WARN", "CONFIRMED", "hook", "the first ~210 characters show before 'see more': lead with a number, a "
            "question or what happened")
    n = len(body)
    add("PASS" if 600 <= n <= 1500 else "WARN", "PRACTITIONER", "length",
        "%d characters (about 900-1,300 reads well)" % n)
    last = [l for l in body.splitlines() if l.strip()][-1:] or [""]
    add("PASS" if last[0].strip().endswith("?") else "WARN", "PRACTITIONER", "closing question",
        "end with a question only this post could ask, so comments come in")
    long_par = [p for p in re.split(r"\n\s*\n", body) if len(p) > 320]
    if long_par:
        add("WARN", "PRACTITIONER", "white space", "a paragraph over about 4 lines: break it up")
    if BAIT.search(body):
        add("WARN", "CONFIRMED", "engagement bait", "LinkedIn demotes asks like 'comment YES' or 'like if'")
    if fmt != "document":
        add("NOTE", "LARGE-SCALE", "format", "document (PDF carousel) posts reach furthest; worth it for proof of work")
    add("NOTE", "CONFIRMED", "timing", "the first 60-90 minutes matter: reply to comments in the first hour")
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description="A LinkedIn post draft against reach signals, with confidence.")
    p.add_argument("file")
    p.add_argument("--format", default="text", choices=("text", "document", "image"))
    a = p.parse_args(argv)
    res = check(open(a.file, encoding="utf-8").read(), a.format)
    for status, conf, name, detail in res:
        print("%-4s  %-12s %-16s %s" % (status, conf, name, detail))
    return 1 if any(r[0] == "FAIL" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
