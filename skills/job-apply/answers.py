#!/usr/bin/env python3
"""Sort an application form's questions: what Claude may fill, and what only the person answers.

    python3 answers.py form.json
    python3 answers.py lengths filled.json     # before stopping at Submit: anything the form will cut off?

form.json: a list of questions, each a string or {"label": "...", "type": "text|select|checkbox|file", "required": true}.

Each question gets one of:
  FILL       a fact from PROFILE.md or EVIDENCE.md (name, links, education, availability)
  DRAFT      a written answer Claude drafts from evidence, for the person to approve
  YOU        only the person answers: eligibility and sponsorship, salary history,
             expected pay (Claude may suggest a market-based range), diversity and
             equality questions, health, criminal record, age or date of birth,
             references' contact details, legal declarations and consent boxes
  SKIP-PASSWORD  never typed by Claude: the person logs in themselves

Consent questions get a note: a marketing or talent-pool consent (sharing your
details for advertising, newsletters, future roles) is not a condition of being
considered, and 'required' means an option must be picked, not that it must be
Yes. Recording consent for interviews is the person's choice.

Prints a table and exits 1 if any required question is YOU (so the form can't be
called finished until the person has answered it).

lengths: filled.json is a list of {"label", "answer", "max_length"} read back from
the form. Many forms silently cut text at their limit (255 characters is common);
this lists every answer that's too long, so it can be shortened before Submit.
Ideas from please-hire-me's field notes (MIT, Alex Wang).
"""

import argparse
import json
import re
import sys

RULES = [
    ("SKIP-PASSWORD", r"password|passcode|security question|one-time code|otp\b|verification code"),
    ("YOU", r"right to work|work permit|visa|sponsor|stamp \d|eligib|authori[sz]ed to work|citizenship|nationality"),
    ("YOU", r"current salary|salary history|previous salary|past salary|current (?:pay|compensation|package)|last salary"),
    ("YOU", r"expected salary|salary expectation|desired (?:salary|pay)|compensation expectation|expected pay"),
    ("YOU", r"gender|\bsex\b|pronoun|ethnic|\brace\b|religio|belief|sexual orientation|disabilit|marital|civil status|family status|traveller|veteran|\bage\b|how old|date of birth|\bdob\b|pregnan"),
    ("YOU", r"health|medical|criminal|conviction|offence|garda vett|background check consent"),
    ("YOU", r"i (?:agree|consent|confirm|declare|certify)|\bconsent\b|opt[- ](?:in|out)|terms and conditions|privacy (?:notice|policy)|declaration|signature"),
    ("YOU", r"referee|reference (?:name|email|phone|contact)"),
    ("DRAFT", r"why (?:do you|are you|this)|tell us|describe|cover letter|motivation|what interests|additional information|anything else|example of|a time when|competenc"),
    ("FILL", r"name|email|phone|mobile|address|city|location|linkedin|github|portfolio|website|degree|university|college|school|graduat|qualification|employer|job title|start date|notice period|availability|relocat|language|years of experience|cv|resume|résumé"),
]


NOTES = [
    (r"marketing|advertis|third[- ]part|newsletter|talent (?:community|pool)|future (?:roles|opportunities|vacancies)",
     "consent beyond this application: not a condition; the privacy-preserving answer is fine"),
    (r"record(?:ed|ing)? (?:the |your )?interview|interview.{0,20}record", "interview recording: the person's choice"),
]


def note(label):
    low = label.lower()
    return next((n for pat, n in NOTES if re.search(pat, low)), "")


def lengths(rows):
    out = []
    for r in rows:
        mx = r.get("max_length")
        n = len(r.get("answer", ""))
        if mx and n > int(mx):
            out.append("%s: %d characters, the field takes %s; shorten it before Submit" % (r.get("label"), n, mx))
    return out


def classify(label):
    low = label.lower()
    for kind, pat in RULES:
        if re.search(pat, low):
            return kind
    return "DRAFT"


def main(argv=None):
    p = argparse.ArgumentParser(description="Which form questions Claude may fill and which are yours.")
    p.add_argument("form", help="form.json, or 'lengths' then filled.json")
    p.add_argument("filled", nargs="?")
    a = p.parse_args(argv)
    if a.form == "lengths":
        bad = lengths(json.load(open(a.filled, encoding="utf-8")))
        for b in bad:
            print("TOO LONG  " + b)
        print("All answers fit." if not bad else "%d answer(s) would be cut off." % len(bad))
        return 1 if bad else 0
    qs = json.load(open(a.form, encoding="utf-8"))
    blocked = 0
    for q in qs:
        label = q if isinstance(q, str) else q.get("label", "")
        req = (not isinstance(q, str)) and bool(q.get("required"))
        kind = classify(label)
        if kind == "YOU" and req:
            blocked += 1
        n = note(label)
        print("%-13s %s%s%s" % (kind, label, " (required)" if req else "", ("  [" + n + "]") if n else ""))
    if blocked:
        print("\n%d required question(s) only you can answer. Claude leaves them blank and flagged." % blocked)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
