#!/usr/bin/env python3
"""Find the roles with too little evidence, and plan the questions that fill them.

    python3 depth.py roles --evidence EVIDENCE.md [--linkedin Positions.csv] [--today 2026-11-06] [--json]
    python3 depth.py questions --evidence EVIDENCE.md --role "Account Executive, C4P" \
        [--family "Account Executive"] [--family "Partnerships"] [--terms gaps.txt] [--max 12] [--json]
    python3 depth.py mark --evidence EVIDENCE.md --role "C4P" --status done|declined [--today ...]

roles: every dated work section in EVIDENCE.md ('## Title, Company (Jun 2024 - present)'),
scored for how well it's documented. A reader looks at the current title and company
first (the Ladders' 2018 eye-tracking study), so the newest role, and every role
that ended in the last 3 years, needs at least 4 facts, 2 of them with numbers, a
result and its scope. Older roles need 2 facts and a number. Facts labelled GUESSED
or UNVERIFIED don't count. With LinkedIn's Positions.csv (from the data export), any
position missing from EVIDENCE.md is listed as MISSING: the case where a newest
role is on LinkedIn but on no CV. Order: missing, then thin, newest first.

questions: the interview plan for one role, one question at a time. The core
questions (what you were hired to do, scope, the accomplishment you're proudest
of, how you know it worked, why you, what you started, recognition, the low
point, what your manager would say, who you worked with, tools, why you left)
skip anything the evidence already covers; each role family adds what its hiring
managers look for (quota and rank for sales, what shipped and the metric for
product, and so on: experience_questions.json). --terms (one per line) puts
requirements from the family's job ads that no evidence covers first.

mark: records '- Interview: done <date>' or '- Interview: declined <date>' in the
role's section. A declined role isn't offered again for 30 days; a done one isn't
offered again unless it's still MISSING.
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                       "dec"], 1)}
DATES = re.compile(r"\(([^()]*\b(?:19|20)\d\d\b[^()]*)\)\s*$")
EDU = re.compile(r"\b(bsc|msc|ba|ma|mba|phd|degree|diploma|university|college|school|leaving cert|a-levels|"
                 r"certificate|certification|course)\b", re.I)
NUMBER = re.compile(r"(?<![\w-])(?:€|£|\$)?\d[\d,.]*\s*(?:%|k\b|m\b|bn\b|x\b)?")
YEAR = re.compile(r"^(?:19|20)\d\d$")
RESULT = re.compile(r"\b(cut|reduc|grew|grow|increas|rais|sav|won|win|closed|deliver|launch|improv|doubl|tripl|"
                    r"exceed|beat|hit|achiev|generat|sign|book|convert|retain|renew|ship|built|cut)\w*", re.I)
SCOPE = re.compile(r"\b(team|people|staff|reports|budget|clients?|customers?|accounts?|users?|territory|quota|"
                   r"portfolio|managers?|markets?|countries|stores|sites|merchants|partners|pipeline|volume)\b", re.I)
WEAK = re.compile(r"\b(GUESSED|UNVERIFIED)\b")
LINKEDIN_ONLY = re.compile(r"\blinkedin\b", re.I)
MARK = re.compile(r"^-\s*Interview:\s*(done|declined)\s+(\d{4}-\d\d-\d\d)", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(ltd|limited|plc|inc|llc|gmbh|dac|group|holdings)\b\.?", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def parse_date(text, end=False):
    t = (text or "").strip().lower()
    if not t:
        return None
    if re.search(r"present|now|current|today", t):
        return "present"
    m = re.search(r"([a-z]{3})[a-z]*\.?\s+((?:19|20)\d\d)", t)
    if m and m.group(1) in MONTHS:
        return datetime.date(int(m.group(2)), MONTHS[m.group(1)], 1)
    m = re.search(r"((?:19|20)\d\d)-(\d\d)", t)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), 1)
    m = re.search(r"((?:19|20)\d\d)", t)
    if m:
        return datetime.date(int(m.group(1)), 12 if end else 1, 1)
    return None


def span(text):
    parts = re.split(r"\s+(?:-|–|—|to)\s+", text.strip(), maxsplit=1)
    start = parse_date(parts[0])
    end = parse_date(parts[1], end=True) if len(parts) > 1 else start
    return (None if start == "present" else start), end


def sections(text):
    out, cur = [], None
    for line in (text or "").splitlines():
        if line.startswith("## "):
            cur = {"heading": line[3:].strip(), "lines": []}
            out.append(cur)
        elif cur is not None and line.strip().startswith("-"):
            cur["lines"].append(line.strip())
    return out


def has_number(line):
    for m in NUMBER.finditer(line):
        tok = m.group(0).strip().strip(".,")
        if tok and not YEAR.match(tok):
            return True
    return False


def score(sec, today):
    head = sec["heading"]
    m = DATES.search(head)
    if not m or EDU.search(head):
        return None
    start, end = span(m.group(1))
    title_company = head[:m.start()].strip().rstrip(",")
    marks = [MARK.match(l) for l in sec["lines"]]
    marks = [(x.group(1).lower(), datetime.date.fromisoformat(x.group(2))) for x in marks if x]
    facts = [l for l in sec["lines"] if not MARK.match(l) and not WEAK.search(l)]
    numbers = sum(1 for l in facts if has_number(l))
    results = sum(1 for l in facts if RESULT.search(l) and has_number(l))
    scope = any(SCOPE.search(l) and has_number(l) for l in facts)
    only_linkedin = bool(facts) and all(LINKEDIN_ONLY.search(l) for l in facts)
    current = end == "present"
    months_ago = 0 if current or end is None else (today.year - end.year) * 12 + today.month - end.month
    recent = current or months_ago <= 36
    need = {"facts": 4, "numbers": 2, "results": 1, "scope": 1} if recent else {"facts": 2, "numbers": 1,
                                                                                "results": 0, "scope": 0}
    missing = []
    if len(facts) < need["facts"]:
        missing.append("%d more facts" % (need["facts"] - len(facts)))
    if numbers < need["numbers"]:
        missing.append("%d more with a number" % (need["numbers"] - numbers))
    if results < need["results"]:
        missing.append("a result")
    if need["scope"] and not scope:
        missing.append("the scope (team, budget, accounts...)")
    if only_linkedin:
        missing.append("detail beyond the LinkedIn entry")
    return {"role": title_company, "dates": m.group(1), "start": start.isoformat() if start else None,
            "current": current, "months_since_end": months_ago, "facts": len(facts), "with_numbers": numbers,
            "results": results, "scope": scope, "status": "THIN" if missing else "OK", "missing": missing,
            "marks": [(k, d.isoformat()) for k, d in marks]}


def linkedin_positions(path):
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        out.append({"company": r.get("Company Name") or r.get("Company") or "", "title": r.get("Title") or "",
                    "started": r.get("Started On") or "", "finished": r.get("Finished On") or "",
                    "description": r.get("Description") or ""})
    return out


def roles(evidence_text, today, linkedin=None):
    found = [r for r in (score(s, today) for s in sections(evidence_text)) if r]
    known = " ".join(norm(r["role"]) for r in found)
    for p in linkedin or []:
        key = norm(p["company"])
        if key and key not in known:
            end = parse_date(p["finished"], end=True) if p["finished"] else "present"
            st = parse_date(p["started"])
            found.append({"role": "%s, %s" % (p["title"], p["company"]), "dates": "%s - %s" % (
                p["started"], p["finished"] or "present"),
                "start": st.isoformat() if isinstance(st, datetime.date) else None, "current": end == "present",
                "months_since_end": 0 if end in ("present", None) else
                (today.year - end.year) * 12 + today.month - end.month, "facts": 0, "with_numbers": 0,
                "results": 0, "scope": False, "status": "MISSING",
                "missing": ["on LinkedIn but not in EVIDENCE.md: the whole role"], "marks": []})
    for r in found:
        r["offer"] = offer(r, today)
    rank = {"MISSING": 0, "THIN": 1, "OK": 2}
    found.sort(key=lambda r: (not r["offer"], not r["current"], r["months_since_end"], rank[r["status"]]))
    newest = min(found, key=lambda r: (not r["current"], r["months_since_end"]), default=None)
    for r in found:
        r["newest"] = r is newest
    return found


def offer(r, today):
    """Whether to offer the interview now: a current or recent role (ended in the last 3 years) that is thin or
    missing, not declined in the last 30 days and not already done. Older thin roles are listed, not offered."""
    if r["status"] == "OK" or not (r["current"] or r["months_since_end"] <= 36):
        return False
    for kind, d in r.get("marks", []):
        d = datetime.date.fromisoformat(d)
        if kind == "declined" and (today - d).days < 30:
            return False
        if kind == "done" and r["status"] != "MISSING":
            return False
    return True


def load_bank():
    with open(os.path.join(HERE, "experience_questions.json"), encoding="utf-8") as fh:
        return json.load(fh)


def families_for(names, role_text, bank):
    hits = []
    for text in list(names or []) + [role_text]:
        for key, fam in bank["families"].items():
            if key not in hits and re.search(fam["match"], text or "", re.I):
                hits.append(key)
    return hits[:2]


def questions(evidence_text, role, families=(), terms=(), today=None, cap=12):
    bank = load_bank()
    sec = next((s for s in sections(evidence_text) if norm(role) and norm(role) in norm(s["heading"])), None)
    lines = sec["lines"] if sec else []
    body = "\n".join(l for l in lines if not WEAK.search(l))
    ended = bool(sec) and not re.search(r"present|now|current", sec["heading"], re.I)
    plan = []
    for t in [t.strip() for t in terms or () if t.strip()]:
        if not re.search(re.escape(t), body, re.I):
            plan.append({"id": "gap", "ask": "Jobs you're going for ask for %s. Did you do any of that in this role? "
                         "Tell me about one time." % t, "why": "A requirement in your target ads with no evidence "
                         "yet."})
    core = bank["core"]
    for q in core:
        if q.get("only_if") == "ended" and not ended:
            continue
        if q["covered"] and re.search(q["covered"], body, re.I):
            continue
        plan.append({"id": q["id"], "ask": q["ask"], "why": q["why"]})
    fams = families_for(families, (sec or {}).get("heading", role), bank)
    fam_qs = [[{"id": "family:" + f, "ask": a, "why": "What %s hiring managers look for." % f.replace("_", " ")}
               for a in bank["families"][f]["asks"]] for f in fams]
    # Gaps from the ads, three core questions, the main family's, two more core, the second family's first two,
    # then the rest: a short interview still covers the role, the field and the proof.
    head, tail = [q for q in plan if q["id"] == "gap"], [q for q in plan if q["id"] != "gap"]
    first = fam_qs[0] if fam_qs else []
    second = fam_qs[1] if len(fam_qs) > 1 else []
    ordered = head + tail[:3] + first + tail[3:5] + second[:2] + tail[5:] + second[2:]
    return {"role": (sec or {}).get("heading", role), "families": fams, "found_in_evidence": bool(sec),
            "questions": ordered[:cap], "minutes": min(15, max(5, len(ordered[:cap]))),
            "how": "One question at a time. Answer out loud: tap the microphone in the message box (on a phone, "
                   "hold it while you talk), or use voice mode for a spoken conversation. Rambling is fine."}


def mark(path, role, status, today):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    idx = next((i for i, l in enumerate(lines) if l.startswith("## ") and norm(role) in norm(l)), None)
    if idx is None:
        raise SystemExit("no section for %s in %s" % (role, path))
    j = idx + 1
    while j < len(lines) and not lines[j].startswith("## "):
        j += 1
    lines.insert(j, "- Interview: %s %s" % (status, today.isoformat()))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return lines[idx]


def main(argv=None):
    p = argparse.ArgumentParser(description="Thin roles and the questions that fill them.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("roles")
    r.add_argument("--evidence", required=True)
    r.add_argument("--linkedin", help="Positions.csv from LinkedIn's data export")
    r.add_argument("--today")
    r.add_argument("--json", action="store_true")
    q = sub.add_parser("questions")
    q.add_argument("--evidence", required=True)
    q.add_argument("--role", required=True)
    q.add_argument("--family", action="append", default=[])
    q.add_argument("--terms", help="requirements with no evidence, one per line")
    q.add_argument("--max", type=int, default=12)
    q.add_argument("--json", action="store_true")
    m = sub.add_parser("mark")
    m.add_argument("--evidence", required=True)
    m.add_argument("--role", required=True)
    m.add_argument("--status", required=True, choices=("done", "declined"))
    m.add_argument("--today")
    a = p.parse_args(argv)
    today = datetime.date.fromisoformat(a.today) if getattr(a, "today", None) else datetime.date.today()
    if a.cmd == "mark":
        print("marked %s: %s" % (a.status, mark(a.evidence, a.role, a.status, today)))
        return 0
    text = open(a.evidence, encoding="utf-8").read() if os.path.exists(a.evidence) else ""
    if a.cmd == "roles":
        li = linkedin_positions(a.linkedin) if a.linkedin else None
        out = roles(text, today, li)
        if a.json:
            print(json.dumps(out, indent=1, ensure_ascii=False))
            return 0
        for x in out:
            print("%-7s %s%s (%s): %d facts, %d with numbers%s" % (
                x["status"], x["role"], " [newest]" if x["newest"] else "", x["dates"], x["facts"],
                x["with_numbers"], "; needs " + ", ".join(x["missing"]) if x["missing"] else ""))
        todo = [x for x in out if x["offer"]]
        print("Interview: %s" % ("; ".join(x["role"] for x in todo) if todo else "none needed"))
        return 1 if todo else 0
    terms = open(a.terms, encoding="utf-8").read().splitlines() if a.terms else ()
    out = questions(text, a.role, a.family, terms, today, a.max)
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    print("%s (%s), about %d minutes. %s" % (out["role"], ", ".join(out["families"]) or "general", out["minutes"],
                                             out["how"]))
    for i, x in enumerate(out["questions"], 1):
        print("%2d. %s" % (i, x["ask"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
