#!/usr/bin/env python3
"""Find the hidden gates in a job ad before anyone scores it or opens a form.

    python3 gates.py ad.txt [--years-max 2] [--needs-sponsorship] [--languages "English:C2,Irish:B1"]
                            [--not-citizen] [--json]

Titles mislead: "Early Career" can mean 1-3 years after graduating, a plain
"Analyst" ad can say "this is a senior role" in paragraph three, and a company
that sponsors visas can refuse it for one role. This reads the whole ad and
lists, with the surrounding words so a person can judge:

  YEARS        "3+ years", "six (6) years", "1-3 years post-graduation" (founder bios
               like "spent 18 years at Google" are shown, not counted)
  SENIORITY    senior, staff-level, lead, proven track record, at scale, expert, on-call
  SPONSORSHIP  "sponsorship is not offered", "must have the right to work"
  CITIZENSHIP  citizenship, security clearance, export control
  NOT-GRAD     "not a role for new graduates / internships"
  INTERNSHIP   an internship that reads like a full-time title
  PAY          a pay range in the text (feeds often leave the pay field empty)
  ELIGIBILITY  who may apply: citizenship or permanent residency, or an explicit welcome
               ("international applicants welcome", "we sponsor"). Silence is not permission:
               big graduate schemes often state their rules only on their own site, and a
               company-wide welcome doesn't cover every role, so a silent ad is UNVERIFIED
  LANGUAGE     a language the role itself requires, with its level, against the person's
               languages (--languages, CEFR A1-C2): not spoken at all is a FAIL; a higher
               level than theirs ("fluent", "native", "C1") is a FLAG for them to decide.
               The language the ad is written in is not a requirement.

With --years-max or --needs-sponsorship, a hard mismatch is marked SKIP (no fact
could make the person eligible), which is different from a missing detail the
person could supply. Quote the exact wording when ruling a job out. Ideas from
please-hire-me's field notes (MIT, Alex Wang) and ai-job-search's eligibility and
language gates (MIT, Mads Lorentzen).
"""

import argparse
import json
import re
import sys

NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10}
YEARS = re.compile(r"\b(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)?\s*(\d{1,2})?\s*\+?\s*years?\b"
                   r"|\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*\(?(\d{0,2})\)?\s*\+?\s*years?\b", re.I)
BIO = re.compile(r"\b(spent|founded|founder|ceo|our team has|combined|history|since|over the past|for the past)\b", re.I)
REQ = re.compile(r"\b(experience|require|minimum|at least|must|you have|you've|qualification)\b", re.I)
SENIOR = re.compile(r"\b(senior|staff[- ]level|principal|lead (?:engineer|analyst)|proven track record|track record"
                    r"|at (?:\w+ )?scale|expert(?:ise)? in|on-call rotations?|seasoned|extensive experience)\b", re.I)
SPONSOR = re.compile(r"(sponsorship (?:is )?not (?:offered|available|provided)|(?:not|unable to|cannot|can't) (?:offer|provide|support) "
                     r"(?:visa |immigration )?sponsorship|no (?:visa |immigration )?sponsorship|must (?:already )?have (?:the )?right to work"
                     r"|without (?:the need for )?(?:visa )?sponsorship)", re.I)
CITIZEN = re.compile(r"\b(citizenship|citizens? only|security clearance|clearance required|itar|export control|us person)\b", re.I)
NOTGRAD = re.compile(r"not (?:a role |suitable |open )?for (?:interns(?:hips)?|new grad(?:uate)?s?|graduates)", re.I)
INTERN = re.compile(r"\b(as an intern|internship|summer 20\d\d|placement year|12-month placement)\b", re.I)
PR = re.compile(r"\b(permanent residen(?:t|cy|ce)|pr (?:holders?|required)|stamp 4|right to reside|full working rights)\b", re.I)
WELCOME = re.compile(r"(international (?:applicants|candidates) (?:are )?welcome|visa (?:holders|sponsorship) (?:considered|available|offered)"
                     r"|we (?:can |will |do )?sponsor|sponsorship (?:is )?(?:available|offered|provided)|critical skills (?:employment )?permit)", re.I)
LANGS = ["English", "Irish", "French", "German", "Spanish", "Italian", "Portuguese", "Dutch", "Flemish", "Polish",
         "Danish", "Swedish", "Norwegian", "Finnish", "Mandarin", "Chinese", "Cantonese", "Japanese", "Korean",
         "Arabic", "Russian", "Ukrainian", "Hindi", "Turkish", "Greek", "Czech", "Slovak", "Hungarian", "Romanian",
         "Bulgarian", "Croatian", "Lithuanian", "Latvian", "Estonian", "Hebrew", "Vietnamese", "Thai", "Indonesian"]
LEVEL_WORDS = [(r"native|mother[- ]tongue|bilingual|c2", 6), (r"fluent|fluency|business(?:[- ]level)?|professional|proficien\w*|c1|excellent|full professional", 5),
               (r"b2|good|strong|working", 4), (r"conversational|b1|intermediate", 3), (r"basic|a2|a1|elementary", 2)]
CEFR = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6, "NATIVE": 6}
_LANG = "|".join(LANGS)
LANG_REQ = re.compile(r"(?:(?P<lvl1>native|fluent|fluency in|business[- ]level|professional|proficient in|excellent|good|strong|working|conversational|basic|C1|C2|B1|B2)\s+(?:(?:written|spoken|verbal) (?:and (?:written|spoken|verbal) )?)?(?:knowledge of |command of |skills in )?(?P<lang1>%s)\b(?:\s+(?:speaker|skills|language))?)"
                      r"|(?:\b(?P<lang2>%s)\b(?: language)?(?: skills)?\s*(?:\((?P<lvl2>[ABC][12])\)|(?:at |to )?(?P<lvl3>[ABC][12]) level|(?:is |are )?(?:required|essential|a must|mandatory|needed)))" % (_LANG, _LANG), re.I)
PAY = re.compile(r"(?:€|\$|£)\s?\d[\d,.]*\s?(?:k|K)?\s*(?:-|–|to)\s*(?:€|\$|£)?\s?\d[\d,.]*\s?(?:k|K)?", re.I)


def ctx(text, m, width=60):
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def years_found(text):
    out = []
    for m in YEARS.finditer(text):
        if m.group(1):
            low = int(m.group(1))
        else:
            low = int(m.group(4)) if m.group(4) else NUMWORDS[m.group(3).lower()]
        sentence = ctx(text, m, 80)
        bio = bool(BIO.search(sentence)) and not REQ.search(sentence)
        out.append({"years": low, "bio": bio, "post_grad": bool(re.search(r"post[- ]?grad", sentence, re.I)),
                    "context": sentence})
    return out


def level_of(word):
    w = (word or "").lower()
    for pat, n in LEVEL_WORDS:
        if re.fullmatch(pat, w) or re.search(r"\b(%s)\b" % pat, w):
            return n
    return 1  # named without a level


def parse_languages(spec):
    out = {}
    for part in (spec or "").split(","):
        if ":" in part:
            name, lvl = part.split(":", 1)
            out[name.strip().lower()] = CEFR.get(lvl.strip().upper(), 1)
    return out


def languages(text, mine=None):
    found = []
    for m in LANG_REQ.finditer(text):
        lang = (m.group("lang1") or m.group("lang2")).title()
        lvl_word = m.group("lvl1") or m.group("lvl2") or m.group("lvl3") or ""
        need = level_of(lvl_word)
        after = re.split(r"[.;,\n]| and ", text[m.end(): m.end() + 40])[0]  # this clause only
        preferred = bool(re.search(r"\b(a plus|nice to have|desirable|an advantage|advantageous|preferred|bonus|beneficial)\b", after, re.I))
        item = {"language": lang, "level_word": lvl_word or "required", "need": need, "match": m.group(0).strip(),
                "preferred": preferred, "context": ctx(text, m)}
        if preferred:
            item["verdict"] = "NICE TO HAVE"
        elif mine is not None:
            have = mine.get(lang.lower())
            if have is None and lang.lower() in ("mandarin", "cantonese"):
                have = mine.get("chinese")
            item["verdict"] = "FAIL" if have is None else ("FLAG" if need > have else "PASS")
        found.append(item)
    return found


def scan(text, years_max=None, needs_sponsorship=False, my_languages=None, not_citizen=False):
    found = {"YEARS": years_found(text)}
    for name, rx in (("SENIORITY", SENIOR), ("SPONSORSHIP", SPONSOR), ("CITIZENSHIP", CITIZEN),
                     ("NOT-GRAD", NOTGRAD), ("INTERNSHIP", INTERN), ("PAY", PAY)):
        found[name] = [{"match": m.group(0), "context": ctx(text, m)} for m in rx.finditer(text)]
    elig = [{"match": m.group(0), "context": ctx(text, m), "kind": "requires citizenship or residency"}
             for m in PR.finditer(text)]
    elig += [{"match": m.group(0), "context": ctx(text, m), "kind": "welcomes international applicants (this role)"}
             for m in WELCOME.finditer(text)]
    if not elig and not found["CITIZENSHIP"]:
        elig.append({"match": "", "context": "", "kind": "UNVERIFIED: the ad doesn't say who may apply; check the "
                     "employer's own careers or international-applicant page (silence is not permission)"})
    found["ELIGIBILITY"] = elig
    found["LANGUAGE"] = languages(text, my_languages)
    skip = []
    if not_citizen and (found["CITIZENSHIP"] or any(e["kind"].startswith("requires") for e in elig)):
        q = (found["CITIZENSHIP"] or [e for e in elig if e["kind"].startswith("requires")])[0]
        skip.append('citizenship, residency or clearance required: "%s"' % q["match"])
    for l in found["LANGUAGE"]:
        if l.get("verdict") == "FAIL":
            skip.append('needs %s, which the person doesn\'t list: "%s"' % (l["language"], l["match"]))
    req_years = [y["years"] for y in found["YEARS"] if not y["bio"]]
    if years_max is not None and req_years and min(req_years) > years_max:
        skip.append("needs %d+ years; the person's ceiling is %d" % (min(req_years), years_max))
    if needs_sponsorship and found["SPONSORSHIP"]:
        skip.append("this role offers no visa sponsorship")
    if found["NOT-GRAD"] and years_max is not None and years_max <= 1:
        skip.append("not open to new graduates")
    return found, skip


def main(argv=None):
    p = argparse.ArgumentParser(description="Hidden gates in a job ad.")
    p.add_argument("ad")
    p.add_argument("--years-max", type=int)
    p.add_argument("--needs-sponsorship", action="store_true")
    p.add_argument("--languages", help='the person\'s languages, e.g. "English:C2,Irish:B1"')
    p.add_argument("--not-citizen", action="store_true", help="the person isn't a citizen or resident where the job is")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    found, skip = scan(open(a.ad, encoding="utf-8").read(), a.years_max, a.needs_sponsorship,
                       parse_languages(a.languages) if a.languages else None, a.not_citizen)
    if a.json:
        print(json.dumps({"found": found, "skip": skip}, indent=1, ensure_ascii=False))
        return 1 if skip else 0
    for k, items in found.items():
        for it in items:
            tag = " (looks like a bio, not a requirement)" if it.get("bio") else ""
            if k == "ELIGIBILITY":
                tag = "  [%s]" % it["kind"]
            if k == "LANGUAGE":
                tag = "  [%s %s%s]" % (it["language"], it["level_word"], (": " + it["verdict"]) if it.get("verdict") else "")
            print("%-12s %s%s" % (k, it["context"] or "-", tag))
    flags = [l for l in found["LANGUAGE"] if l.get("verdict") == "FLAG"]
    for l in flags:
        print("FLAG: %s at '%s' may be above the person's level; they decide." % (l["language"], l["level_word"]))
    print("SKIP: " + "; ".join(skip) if skip else "No hard mismatch found. Read the whole ad anyway.")
    return 1 if skip else 0


if __name__ == "__main__":
    sys.exit(main())
