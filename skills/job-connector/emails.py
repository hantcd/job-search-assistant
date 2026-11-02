#!/usr/bin/env python3
"""Likely work email addresses for one named person, each a guess with a confidence, plus the privacy label.

    python3 emails.py guess --name "Siobhan Kelly" --domain acme.ie [--known "Ciara Doyle ciara.doyle@acme.ie"]
    python3 emails.py privacy --method published-work-page

Candidates come from common work-email patterns, and much more confidently from
the pattern of an address you already know at the same company. Every result
is a GUESS until you find it published on a public page. This tool never
contacts a mail server to test an address, and never looks up personal email
addresses, mobile numbers or home details.

Privacy labels (the default reasoning; Claude adjusts for the case and you decide):
  given                  you were given it                                   no label needed
  published-work-page    on the company site, a press release, a speaker page LOW
  company-pattern        the company's usual format applied to a public name   MEDIUM
  lookup-tool            a tool such as Hunter.io run by you                   MEDIUM
  data-broker            enrichment extensions or bought lists (Apollo, Lusha, Kaspr)  HIGH: not used
  personal               personal email, mobile or home details               refused

Pattern idea adapted from hunter-skill (MIT, Jake Schincariol).
"""

import argparse
import json
import re
import sys
import unicodedata

PATTERNS = [  # (pattern, base confidence when nothing is known)
    ("{first}.{last}", 0.40), ("{first}", 0.15), ("{f}{last}", 0.15), ("{first}{last}", 0.10),
    ("{first}_{last}", 0.05), ("{f}.{last}", 0.05), ("{last}", 0.03), ("{first}{l}", 0.03),
]
PRIVACY = {
    "given": ("GIVEN", "You gave this address."),
    "published-work-page": ("LOW", "Published by the person or employer for work contact; one relevant, one-to-one message fits that purpose."),
    "company-pattern": ("MEDIUM", "A guess from the company's format: work-related and one-to-one, but the person didn't publish it. Safer: LinkedIn, a mutual contact, or the company's general address."),
    "lookup-tool": ("MEDIUM", "A third-party tool inferred it from public pages; check its source, keep it to one relevant message, and stop if asked."),
    "data-broker": ("HIGH", "Enrichment tools that harvest contact data break LinkedIn's rules, and France's regulator fined one (Kaspr) EUR 240,000 in 2024. Not used."),
    "personal": ("REFUSED", "Personal email, mobile or home details are never looked up."),
}


def ascii_name(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z\s'-]", "", s.lower()).replace("'", "").strip()


def parts(name):
    bits = [b for b in re.split(r"[\s-]+", ascii_name(name)) if b]
    if len(bits) < 2:
        raise ValueError("need a first and last name, got %r" % name)
    first, last = bits[0], bits[-1]
    return {"first": first, "last": last, "f": first[0], "l": last[0]}


def which_pattern(known_name, known_email):
    local = known_email.split("@")[0].lower()
    p = parts(known_name)
    for pat, _ in PATTERNS:
        if pat.format(**p) == local:
            return pat
    return None


def guess(name, domain, known=None):
    p = parts(name)
    domain = domain.lower().lstrip("@")
    learned = None
    if known:
        m = re.match(r"(.+?)\s+(\S+@\S+)$", known.strip())
        if m:
            learned = which_pattern(m.group(1), m.group(2))
    out = []
    for pat, conf in PATTERNS:
        c = conf
        if learned:
            c = 0.80 if pat == learned else conf * 0.25
        out.append({"email": pat.format(**p) + "@" + domain, "confidence": round(c, 2),
                    "level": "high" if c >= 0.7 else ("medium" if c >= 0.3 else "low"),
                    "status": "GUESS", "pattern": pat})
    out.sort(key=lambda r: -r["confidence"])
    return out, learned


def main(argv=None):
    ap = argparse.ArgumentParser(description="Work email guesses with a confidence, and the privacy label.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("guess")
    g.add_argument("--name", required=True)
    g.add_argument("--domain", required=True)
    g.add_argument("--known", help='"Full Name address@domain" of someone at the same company')
    g.add_argument("--top", type=int, default=3)
    pr = sub.add_parser("privacy")
    pr.add_argument("--method", required=True, choices=sorted(PRIVACY))
    a = ap.parse_args(argv)
    if a.cmd == "privacy":
        level, why = PRIVACY[a.method]
        print(json.dumps({"method": a.method, "risk": level, "reasoning": why}, indent=1))
        return 3 if level in ("HIGH", "REFUSED") else 0
    try:
        rows, learned = guess(a.name, a.domain, a.known)
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    level, why = PRIVACY["company-pattern"]
    print(json.dumps({"pattern_learned": learned, "candidates": rows[: a.top], "privacy_risk": level,
                      "reasoning": why, "rules": ["Every candidate is a GUESS, never 'verified'.",
                                                 "If confidence is low, lead with LinkedIn or a mutual contact.",
                                                 "If an email bounces, don't try the other guesses: switch channel."]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
