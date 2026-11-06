#!/usr/bin/env python3
"""A career switch, mapped: each requirement of the target role against the person's evidence.

    python3 switch_map.py map switch.json
    python3 switch_map.py story story.txt --source EVIDENCE.md

switch.json:
  {"target": "Data Analyst",
   "requirements": [{"need": "SQL", "must": true, "seen_in": 12}, {"need": "Power BI dashboards", "seen_in": 9}],
   "evidence": ["Built a claims dashboard in SQL and Excel used by 12 managers", "..."],
   "synonyms": {"dashboards": ["dashboard", "reporting"]}}

map: STRONG when an evidence line covers the requirement's key words, PARTIAL
when it covers some, GAP when none; the evidence line is quoted for each, so
a STRONG is never a claim without a source. Coverage weights must-haves and
how often real ads ask for each. A first pass for the person and Claude to
correct together, not a verdict.
story: the 'why I'm switching' story; any number not in the sources fails.
Standard library only.
"""

import argparse
import json
import re
import sys

STOP = set("and or the a an of in to for with on using use experience knowledge strong good ability skills "
           "skill working work years year proven solid".split())
NUM = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)")


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def words(s, syn=None):
    w = {stem(x) for x in re.findall(r"[a-z0-9+#]+", s.lower()) if x not in STOP and len(x) > 1}
    for k, alts in (syn or {}).items():
        k, alts = stem(k.lower()), [stem(a.lower()) for a in alts]
        if k in w or any(a in w for a in alts):
            w |= {k, *alts}
    return w


def map_switch(d):
    syn = d.get("synonyms") or {}
    ev = [(e, words(e, syn)) for e in d.get("evidence", [])]
    rows, have, total = [], 0.0, 0.0
    for r in d.get("requirements", []):
        need = r["need"] if isinstance(r, dict) else str(r)
        must = bool(r.get("must")) if isinstance(r, dict) else False
        weight = (2 if must else 1) * max(1, int(r.get("seen_in", 1)) if isinstance(r, dict) else 1)
        nw = words(need, syn)
        best, cover = "", 0.0
        for e, ew in ev:
            c = len(nw & ew) / max(1, len(nw))
            if c > cover:
                best, cover = e, c
        level = "STRONG" if cover >= 0.99 or (cover >= 0.66 and len(nw) > 2) else "PARTIAL" if cover > 0 else "GAP"
        rows.append({"need": need, "must": must, "level": level, "evidence": best if level != "GAP" else ""})
        total += weight
        have += weight * {"STRONG": 1, "PARTIAL": 0.5, "GAP": 0}[level]
    return rows, round(100 * have / total) if total else 0


def story_check(story, sources):
    src = "\n".join(sources)
    srcn = {m.group(1).replace(",", "") for m in NUM.finditer(src)}
    bad = sorted({m.group(1).replace(",", "") for m in NUM.finditer(story)} - srcn)
    out = [("FAIL", "number %s isn't in your evidence" % n) for n in bad]
    n = len(re.findall(r"[.!?](?:\s|$)", story.strip()))
    if not 2 <= n <= 5:
        out.append(("WARN", "%d sentences: aim for 3-4" % n))
    if not out or all(o[0] != "FAIL" for o in out):
        out.append(("PASS", "every number is from your evidence"))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Map a career switch; check the switch story.")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("map")
    m.add_argument("file")
    s = sub.add_parser("story")
    s.add_argument("file")
    s.add_argument("--source", action="append", required=True)
    a = p.parse_args(argv)
    if a.cmd == "map":
        d = json.load(open(a.file, encoding="utf-8"))
        rows, cov = map_switch(d)
        print("Target: %s   coverage %d%% (must-haves and how often ads ask count more)" % (d.get("target", "?"), cov))
        for r in rows:
            print("%-7s %-35s %s" % (r["level"], (r["need"] + (" (must)" if r["must"] else ""))[:35],
                                     r["evidence"][:70] or "-- a gap: the plan needs proof for this"))
        return 0
    res = story_check(open(a.file, encoding="utf-8").read(), [open(x, encoding="utf-8").read() for x in a.source])
    for st, msg in res:
        print("%-4s %s" % (st, msg))
    return 1 if any(r[0] == "FAIL" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
