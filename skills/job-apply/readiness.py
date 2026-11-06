#!/usr/bin/env python3
"""The readiness card for one application: red, orange and green, each with its gaps and fixes, and three choices.

    python3 readiness.py build --map reqmap.json [--years-need 4 --years-have 2.5] [--json]

reqmap.json is job-cv's requirements map for this job, one row per requirement:
  {"job": "Acme, Account Executive",
   "requirements": [{"text": "Salesforce", "must": true, "evidence": "none" | "partial" | "strong",
                     "on_cv": true, "fix": "...", "fix_kind": "ready" | "needs you" | "later"}],
   "add_ons": [{"text": "a portfolio link", "fix": "...", "fix_kind": "ready"}]}

Apply when the person has about half of what's asked: internships, placements,
part-time work and coursework count as evidence and experience. Overshooting is fine,
and so is undershooting slightly. The card says how much of the must-haves is covered
(strong counts 1, partial a half) and whether that's about half or more.
Red: a must-have with no evidence, or a third to a half of the years asked.
Orange: a must-have with only partial evidence; a nice-to-have with none; years from
about half up to what's asked; something the evidence has that the CV doesn't show; an add-on that would
help (a line in the note, a link, a certificate in progress).
Green: the must-haves the evidence covers strongly.
Each gap carries a fix, even one that isn't in the evidence yet, labelled:
  ready      Claude can do it now and it stays true (reword, reorder, a keyword the
             evidence supports, a line in the note that names the gap, a link the
             person has)
  needs you  a fact only the person can confirm ("Have you used Salesforce?"); applied
             only if they answer yes
  later      something to do (a free course, a small project); listed, and saved as a
             plan in the profile, never claimed as done
No red and no orange: "No gaps", and the application goes as it is.
The three choices: send as is; make the suggested changes (the ready ones, plus any
'needs you' the person answers yes to; the truth check runs again); make the changes
and save them to the profile (the improved lines into the achievement bank and base
CV, confirmed facts into EVIDENCE.md, 'later' items into its Missing evidence table).
"""

import argparse
import json
import sys

APPLY_AT, STRETCH_FROM = 0.5, 0.33  # guides, not rules: about half of what is asked is enough
CHOICES = ["Send as is", "Make suggested changes", "Make suggested changes and save to profile"]


def build(reqmap, years_need=None, years_have=None):
    red, orange, green = [], [], []

    def gap(where, text, fix, kind):
        where.append({"gap": text, "fix": fix or "", "fix_kind": kind or "ready"})

    for r in reqmap.get("requirements", []):
        ev, must = (r.get("evidence") or "none").lower(), bool(r.get("must"))
        if ev == "strong":
            if r.get("on_cv") is False:
                gap(orange, "%s: in your evidence but not on this CV" % r["text"],
                    r.get("fix") or "add it to the most relevant role, in the ad's words", "ready")
            else:
                green.append(r["text"])
        elif must and ev == "none":
            gap(red, "%s (must-have): no evidence yet" % r["text"], r.get("fix"), r.get("fix_kind") or "needs you")
        elif must:
            gap(orange, "%s (must-have): only partly shown" % r["text"], r.get("fix"), r.get("fix_kind"))
        elif ev == "none":
            gap(orange, "%s (nice to have): not shown" % r["text"], r.get("fix"), r.get("fix_kind") or "later")
        else:
            green.append(r["text"])
    if years_need and years_have is not None:
        share = float(years_have) / years_need
        if share < STRETCH_FROM:
            gap(red, "%g years against %d+ asked (under a third): a long shot" % (years_have, years_need),
                "lead with the scope and results that match the level, and say why now in the note", "ready")
        elif share < APPLY_AT:
            gap(red, "%g years against %d+ asked (a stretch)" % (years_have, years_need),
                "show the level, not the years: the biggest scope, results against target, a promotion or "
                "early responsibility, in the top third", "ready")
        elif share < 1:
            gap(orange, "%g years against %d+ asked (within reach: apply)" % (years_have, years_need),
                "count relevant internships, part-time work and coursework; put the most senior-level result "
                "first; never inflate the dates", "ready")
    for a in reqmap.get("add_ons", []):
        gap(orange, a["text"], a.get("fix"), a.get("fix_kind"))
    musts = [r for r in reqmap.get("requirements", []) if r.get("must")]
    got = sum(1.0 if (r.get("evidence") or "").lower() == "strong" else 0.5 if (r.get("evidence") or "").lower()
              == "partial" else 0 for r in musts)
    cover = round(got / len(musts), 2) if musts else 1.0
    colour = "red" if red else "orange" if orange else "green"
    return {"job": reqmap.get("job", ""), "colour": colour, "red": red, "orange": orange, "green": green,
            "no_gaps": not red and not orange, "must_have_cover": cover,
            "advice": "apply" if cover >= 0.5 else "a long shot: apply if you want this one",
            "choices": ["Send as is"] if not red and not orange else CHOICES,
            "needs_you": [g for g in red + orange if g["fix_kind"] == "needs you"]}


def text(card):
    if card["no_gaps"]:
        return "%s: no gaps. Sending as it is." % card["job"]
    out = ["%s: %s. You have about %d%% of the must-haves: %s." % (
        card["job"], card["colour"].upper(), round(100 * card["must_have_cover"]), card["advice"])]
    for name, items in (("Red", card["red"]), ("Orange", card["orange"])):
        if items:
            out.append(name + ":")
            for g in items:
                out.append("- %s. Fix (%s): %s" % (g["gap"], g["fix_kind"], g["fix"] or "say it plainly in the note"))
    if card["green"]:
        out.append("Green: %s." % ", ".join(card["green"][:6]))
    out.append("Choose: " + " / ".join(card["choices"]))
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description="Red, orange and green for one application, with fixes and three choices.")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--map", required=True, help="job-cv's requirements map for this job (JSON)")
    b.add_argument("--years-need", type=int)
    b.add_argument("--years-have", type=float)
    b.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    with open(a.map, encoding="utf-8") as fh:
        card = build(json.load(fh), a.years_need, a.years_have)
    print(json.dumps(card, indent=1, ensure_ascii=False) if a.json else text(card))
    return 0


if __name__ == "__main__":
    sys.exit(main())
