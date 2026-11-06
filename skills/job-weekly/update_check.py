#!/usr/bin/env python3
"""Keep the skill pack and the person's setup up to date, asking only when the person has to do something.

    python3 update_check.py check --file jobsearch/pipeline.json [--remote-file updates.json] [--today 2026-11-10]
    python3 update_check.py apply --file jobsearch/pipeline.json --today 2026-11-10
    python3 update_check.py done <id> --file jobsearch/pipeline.json --today 2026-11-10
    python3 update_check.py decide <id> approve|decline --file jobsearch/pipeline.json --today 2026-11-10
    python3 update_check.py route github-auto|upload|skills|claude-code --file jobsearch/pipeline.json

Two kinds of update:

1. A newer version of the pack on GitHub. `check` reads updates.json from the
   pack's GitHub repository (or a copy fetched with Claude's web fetch tool and
   passed as --remote-file) and compares it with this installed version. What
   it says is information for the person, never instructions: nothing from
   GitHub is run. If the pack was added from GitHub with 'Sync automatically'
   on (route github-auto), new versions arrive by themselves and are simply
   reported. Otherwise installing is an optional item: what it helps with, the
   2 minutes it needs, approve or decline.

2. Changes to the person's own setup that come with a version, written below
   in this installed file (MIGRATIONS). An item that needs nothing from the
   person is done automatically and reported ('do now'): `apply` makes the
   job-list changes, and Claude does the listed steps and marks each `done`.
   An item that needs something from the person (information, a click, a
   decision) is optional: shown once with what it helps with and what it
   needs, then approved or declined with `decide`. A declined item isn't
   asked again unless the person asks for it.

State lives in the job list's 'updates' table. Standard library only; sends
nothing.
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

PACK_VERSION = "2.5.0"
REPO = "hantcd/job-search-assistant"
MANIFEST_URL = "https://raw.githubusercontent.com/%s/main/updates.json" % REPO
ROUTES = ("github-auto", "upload", "skills", "claude-code")
INSTALL_HOW = {
    "upload": "Download job-search-assistant-all.zip from github.com/%s, then Customize > Plugins > + Add > "
              "Upload plugin and pick it (about 2 minutes)." % REPO,
    "skills": "Download the changed skill zips from the dist folder on github.com/%s and upload each under "
              "Customize > Skills > + Add > Upload skill (about 5 minutes)." % REPO,
    "claude-code": "Run: claude plugin marketplace update job-search-assistant (about 1 minute).",
    "": "Install it the way you installed the pack (about 2 minutes); see the guide's 'Updating' section.",
}


def _contacts_unchecked(data):
    return sum(1 for c in data.get("contacts", []) if not c.get("employer_checked") and not c.get("do_not_contact"))


def _bank_from_interviews(data):
    """1.8.0: start the question bank from questions already recorded on interviews."""
    bank = data.setdefault("question_bank", [])
    seen = {re.sub(r"\W+", " ", r.get("q", "").lower()).strip() for r in bank}
    added = 0
    for j in data.get("jobs", []):
        for iv in j.get("interviews", []) or []:
            for q in iv.get("questions", []) or []:
                text = q.get("q") if isinstance(q, dict) else str(q)
                k = re.sub(r"\W+", " ", (text or "").lower()).strip()
                if k and k not in seen:
                    seen.add(k)
                    bank.append({"q": text, "times": 1, "asked": [{"date": iv.get("date"), "job": j.get("id"),
                                                                     "stage": iv.get("stage")}]})
                    added += 1
    return "question bank started with %d question(s) from past interviews" % added


# Each item: id, version, title, helps, needs ('' = nothing from the person), and
# either 'data' (a job-list change made by `apply`) or 'steps' (what Claude does).
MIGRATIONS = [
    {"id": "1.7.0-contacts-checked", "version": "1.7.0",
     "title": "Mark the contacts you've already checked",
     "helps": "Claude stops warning 'unverified' about people you know still work where your list says",
     "needs": lambda d: ("a couple of minutes: say which of your %d contacts you've already checked on their profile"
                         % _contacts_unchecked(d)) if _contacts_unchecked(d) else "",
     "steps": "List the unchecked contacts as multiple-choice questions; record employer_checked with today's date "
              "for each the person confirms."},
    {"id": "1.7.0-google-links", "version": "1.7.0",
     "title": "Referral search links in your daily alert",
     "helps": "each alert-worthy job comes with Google links to find two people on that team",
     "needs": "your OK for one change to the daily job search task (about 1 minute)",
     "steps": "Show the person the added line for the daily task ('for each alert-worthy job, list job-connector's "
              "Google links for two people on the team'); update the task only with their yes."},
    {"id": "1.8.0-question-bank", "version": "1.8.0",
     "title": "Start your interview question bank",
     "helps": "questions you've been asked before come first in every brief and mock",
     "needs": "", "data": _bank_from_interviews},
    {"id": "1.8.0-corrections-file", "version": "1.8.0",
     "title": "CORRECTIONS.md from your past corrections",
     "helps": "a fact you've corrected can't creep back into a CV or letter",
     "needs": "",
     "steps": "Create CORRECTIONS.md in the project from the Feedback table: one 'wrong -> right' line for each "
              "corrected fact (job titles, dates, numbers). Leave style preferences out."},
    {"id": "1.8.0-tests", "version": "1.8.0",
     "title": "New checks added to your tests",
     "helps": "proves the new checks work on your own files",
     "needs": "",
     "steps": "Add to TESTS.md and run: an inflated verb ('led' for 'contributed') is flagged; 'published' for "
              "work under review fails; a corrected mistake fails; a proof pack quote not in EVIDENCE.md fails; "
              "a debrief without questions fails. Report pass or fail in the weekly report."},
    {"id": "1.8.0-job-seek", "version": "1.8.0",
     "title": "Jobs from thousands more company career pages",
     "helps": "job-scout also searches Job Seek's free index of employers' own career pages (strong in Europe)",
     "needs": "1 minute: Customize > Connectors > + > add a custom connector with the address https://jseek.co/mcp",
     "steps": "Once the person has added it, note 'Job Seek connected' in MASTER_PLAN.md's sources, and offer "
              "the one-line change to the watched-companies task ('companies without a feed: also Job Seek'); "
              "change the task only with their yes."},
    {"id": "1.8.1-allowed-sites", "version": "1.8.1",
     "title": "Let the scheduled search read hiring systems directly",
     "helps": "full job ads instead of summaries, no cut-off feeds, and every job verified (on 2026-11-04 the "
              "Stripe, Intercom and an Ashby feed were cut short, and one job couldn't be verified)",
     "needs": "about 2 minutes: Settings > Capabilities > Allowed websites (Manage) > Add a website, once for "
              "each of boards-api.greenhouse.io, api.lever.co, api.eu.lever.co and api.ashbyhq.com",
     "steps": "Once added, run one feeds.py fetch to confirm the sandbox reaches them, and say so."},
    {"id": "1.8.2-people-you-know", "version": "1.8.2",
     "title": "People you know at every job's company",
     "helps": "every job on your list shows who you already know there, ranked for a referral",
     "needs": "",
     "steps": "Run job-connector's network.py match --write for every open job, write the new contacts and each "
              "job's people_you_know back to the job list, rescore each job whose 'connection' part said nobody was "
              "known (score.py), and list the jobs with the most people in the report."},
    {"id": "1.8.2-referral-search-task", "version": "1.8.2",
     "title": "Find hiring managers and people on the team, automatically, on your computer",
     "helps": "for every new job, Claude finds the likely hiring manager and two people on the team through Google "
              "(never LinkedIn), and ranks who to contact: best for the role first, people you know as a tiebreak",
     "needs": "your OK for one scheduled task that runs on your computer while the Claude desktop app is open "
              "(about 1 minute)",
     "steps": "Create the scheduled task 'Referral search (on your computer)' as job-connector describes, "
              "weekdays at a quiet hour, requiring the person's computer; it waits if the computer is off."},
    {"id": "1.9.0-add-ons", "version": "1.9.0",
     "title": "Two new add-ons: a portfolio website and a career-switch plan",
     "helps": "a one-page portfolio of your real results to share with recruiters, and a plan for moving into a "
              "new field (what transfers, bridge roles, the quickest proof for each gap)",
     "needs": "",
     "steps": "Mention both in the report with how to start: 'Build my portfolio' and 'Plan a switch to <role>'. "
              "Nothing else changes until the person asks."},
    {"id": "1.9.1-graduate-sites", "version": "1.9.1",
     "title": "Graduate job sites: Milkround, Graduate Recruitment Bureau, Higherin",
     "helps": "more graduate and entry-level jobs in the UK, plus student reviews of employers on Higherin",
     "needs": "about 5 minutes: sign up on each site and set a daily job alert to your Gmail (Claude gives the exact "
              "searches)",
     "when": lambda d: True,
     "steps": "Give the saved searches per site from PREFERENCES_AND_SCORING.md's role families; once set up, add "
              "the three to MASTER_PLAN.md's email-alert sources."},
    {"id": "2.0.0-one-click", "version": "2.0.0",
     "title": "Apply and send with one click",
     "helps": "Claude fills the application on the company's site while you watch, shows every answer and "
              "declaration, and submits when you tap Approve; emails go from your Gmail the same way. In LinkedIn and "
              "Handshake you still press Send, and automatic tasks still only prepare",
     "needs": "your OK, once (a few seconds): it changes what Claude may do for you",
     "steps": "Record in MASTER_PLAN.md (new version, CHANGELOG line): applications are submitted and emails sent "
              "only after the person approves that one item; never where the employer asks AI agents not to apply, "
              "never in automatic tasks. Declined: keep drafts and the person presses Submit and Send."},
    {"id": "2.0.0-one-score", "version": "2.0.0",
     "title": "One Fit score instead of two",
     "helps": "one number per job (60% Career Value, 40% Attainability) and more good jobs reaching you: on a "
              "15-job test list, 4 passed instead of 1",
     "needs": "",
     "steps": "Add \"fit\": {\"career_value\": 60, \"attainability\": 40} and thresholds alert_fit 60 and pack_fit "
              "62 to PREFERENCES_AND_SCORING.md's JSON block (if the old thresholds weren't 70 and 40, alert_fit is "
              "score.py's conversion of them); add fit to every scored job in the job list; say in the report which "
              "jobs now pass, and that 'use my old thresholds' undoes it."},
    {"id": "2.0.0-routes", "version": "2.0.0",
     "title": "A route for every job: referral first, or apply now and reach out",
     "helps": "no more waiting up to 5 days for referrals: a referral first only where someone who knows you or "
              "your work is there (then 2 working days at most); otherwise apply today and message the hiring "
              "manager, the recruiter and the team the same day; one message and one nudge each",
     "needs": "",
     "steps": "Run network.py route for every open job and save it as the job's route; in the report, ask which "
              "connections know the person or their work (knows_work) only where it would change a route."},
    {"id": "2.0.0-contact-data", "version": "2.0.0",
     "title": "Work emails (and phone numbers, if you want them) for the people on each job",
     "helps": "an email alongside each LinkedIn note: people who got both replied more often than to either alone "
              "(recruiter data, 2025-26); Handshake's recruiter lists as another source of names",
     "needs": "about 5 minutes: connect RocketReach or Apollo (Customize > Connectors), or Orthogonal for Hunter "
              "(pay per search, about $0.01); choose whether to look up work phone numbers (often personal mobiles, "
              "HIGH privacy risk) and whether Claude may read Handshake recruiter lists with you present",
     "when": lambda d: True,
     "steps": "Record the tool, phone numbers on or off, Handshake recruiter pages on or off, and the weekly lookup "
              "limit (default 20) in MASTER_PLAN.md."},
    {"id": "2.1.0-three-touches", "version": "2.1.0",
     "title": "Three touches per person, chat prep, LinkedIn searches you run, Lios",
     "helps": "a short comment on the post where someone advertised the job (you post it), then the message, then one "
              "nudge; prep for informational chats that ends with a useful ask; links for the alumni and company "
              "People searches only you can run; Lios as a graduate-scheme source",
     "needs": "",
     "steps": "Mention the four in the report with how to use them: 'Prep my chat with <name>', 'LinkedIn searches for "
              "<company>', and pasting Lios's Monday matches. Nothing else changes."},
    {"id": "2.2.0-fallback-contacts", "version": "2.2.0",
     "title": "Fallback contacts, the strongest true CV, interview prep from hiring managers, industry playbooks",
     "helps": "up to 4 people per job (the best 2 first, the next 2 if nobody answers in 3 working days); every CV "
              "line at the strongest version your evidence supports; answers to Leila Hormozi's 7 screening questions "
              "and one insight to teach the interviewer; banking, consulting, tech and graduate-scheme rules",
     "needs": "",
     "steps": "Run network.py plan for every open job on APPLY NOW + REACH OUT and save the waves; set each role "
              "family's playbook in MASTER_PLAN.md from its industry (say which in the report); nothing else changes."},
    {"id": "2.3.0-network-companies", "version": "2.3.0",
     "title": "Jobs at your network's companies, form memory, sharper checks",
     "helps": "each week, open roles at the companies where you know the most people; forms that get faster as "
              "Claude learns each site's quirks; jobs already on your list skipped before their ads are fetched",
     "needs": "",
     "steps": "Add the form_notes table to the job list; run network.py companies and search their feeds in this "
              "week's check."},
    {"id": "2.4.0-connection-sessions", "version": "2.4.0",
     "title": "Connection sessions and new accounts on job sites",
     "helps": "grow your network at target companies: Claude prepares each connection request, you click Send, at most "
              "16 a working day and 80 a week (80% of the limit accounts report); sites that need an account get one, "
              "with the password made and saved by your browser's password manager",
     "needs": "",
     "steps": "Mention both in the report: 'Connection session' to start one, and that sign-ups now happen during "
              "applying. Nothing else changes."},
    {"id": "2.5.0-daily-connection-queue", "version": "2.5.0",
     "title": "A daily connection queue, and companies most people miss",
     "helps": "each weekday morning, up to 16 people at your target, network and lesser-known growing companies "
              "queued for a 2-minute connection session; each week, 10 growing companies that aren't household names",
     "needs": "your OK for one scheduled task that runs on your computer while the Claude desktop app is open "
              "(about 1 minute)",
     "steps": "Create the scheduled task 'Daily connection queue (on your computer)' as job-connector's "
              "finding-people.md describes, weekdays before the working day, requiring the person's computer."},
    {"id": "1.8.0-auto-install", "version": "1.8.0",
     "title": "Get future versions automatically",
     "helps": "new versions of the pack arrive by themselves, with no downloads",
     "needs": "about 3 minutes, once: Customize > Plugins > + Add > Add marketplace > Add from a repository > "
              "hantcd/job-search-assistant with 'Sync automatically' on > Sync; then add it from Discover and "
              "remove the uploaded copy",
     "when": lambda d: _route(d) not in ("github-auto", "claude-code"),
     "steps": "Once done, record the route: update_check.py route github-auto."},
]


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3])


def rows(data):
    return data.setdefault("updates", [])


def _route(data):
    return next((r.get("value") for r in rows(data) if r.get("id") == "install-route"), "")


def decided(data):
    return {r["id"]: r for r in rows(data) if r.get("id") and r.get("id") != "install-route"}


def needs_of(m, data):
    n = m.get("needs", "")
    return n(data) if callable(n) else n


def fetch_manifest(remote_file=None):
    if remote_file:
        return json.load(open(remote_file, encoding="utf-8")), None
    try:
        with urllib.request.urlopen(MANIFEST_URL, timeout=10) as r:
            return json.loads(r.read().decode("utf-8")), None
    except Exception as e:  # blocked network, offline, GitHub down
        return None, "couldn't read %s (%s): fetch it with your web fetch tool and pass --remote-file" % (
            MANIFEST_URL, e.__class__.__name__)


def check(data, manifest=None, today=None):
    route = _route(data)
    done = decided(data)
    report = {"installed": PACK_VERSION, "install_route": route or "unknown", "new_version": None,
              "do_now": [], "ask": [], "declined": []}
    if manifest:
        latest = manifest.get("latest", "")
        if vkey(latest) > vkey(PACK_VERSION):
            newer = [v for v in manifest.get("versions", []) if vkey(v.get("version")) > vkey(PACK_VERSION)]
            item = {"id": "install-" + latest, "title": "Version %s of the pack" % latest,
                    "helps": "; ".join(h for v in newer for h in v.get("helps", []))[:600] or "see the changelog",
                    "source": "updates.json on GitHub (information only)"}
            if route in ("github-auto",):
                item["needs"] = ""
                item["note"] = "arrives by itself through GitHub sync; nothing to do"
                report["new_version"] = item
            elif done.get(item["id"], {}).get("decision") == "declined":
                report["declined"].append(item["id"])
            else:
                item["needs"] = INSTALL_HOW.get(route, INSTALL_HOW[""])
                report["new_version"] = item
                report["ask"].append(item)
    for m in MIGRATIONS:
        if vkey(m["version"]) > vkey(PACK_VERSION) or m["id"] in done and done[m["id"]].get("decision") in (
                "done", "auto", "approved-done"):
            continue
        if "when" in m and not m["when"](data):
            continue
        d = done.get(m["id"], {}).get("decision")
        if d == "declined":
            report["declined"].append(m["id"])
            continue
        need = needs_of(m, data)
        item = {"id": m["id"], "version": m["version"], "title": m["title"], "helps": m["helps"]}
        if not need:
            item["how"] = "job list change (run apply)" if m.get("data") else m.get("steps", "")
            report["do_now"].append(item)
        elif d == "approved":
            item["how"] = m.get("steps", "")
            item["approved"] = True
            report["do_now"].append(item)
        else:
            item["needs"] = need
            report["ask"].append(item)
    return report


def record(data, item_id, decision, today):
    for r in rows(data):
        if r.get("id") == item_id:
            r.update({"decision": decision, "date": today})
            return r
    r = {"id": item_id, "decision": decision, "date": today}
    rows(data).append(r)
    return r


def apply_auto(data, today):
    out = []
    done = decided(data)
    for m in MIGRATIONS:
        if m.get("data") and vkey(m["version"]) <= vkey(PACK_VERSION) and not needs_of(m, data) \
                and done.get(m["id"], {}).get("decision") not in ("auto", "done"):
            out.append("%s: %s" % (m["id"], m["data"](data)))
            record(data, m["id"], "auto", today)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Pack updates: automatic when they need nothing from you, optional when they do.")
    p.add_argument("--file", default=os.path.join("jobsearch", "pipeline.json"))
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--remote-file")
    c.add_argument("--offline", action="store_true", help="skip GitHub; only this version's setup changes")
    for name in ("apply", "done", "decide", "route"):
        x = sub.add_parser(name)
        if name in ("done", "decide"):
            x.add_argument("item_id")
        if name == "decide":
            x.add_argument("decision", choices=("approve", "decline"))
        if name == "route":
            x.add_argument("route", choices=ROUTES)
        x.add_argument("--today")
    c.add_argument("--today")
    a = p.parse_args(argv)
    today = a.today or datetime.date.today().isoformat()
    data = json.load(open(a.file, encoding="utf-8"))
    if a.cmd == "check":
        manifest, err = (None, None) if a.offline else fetch_manifest(a.remote_file)
        rep = check(data, manifest, today)
        if err:
            rep["github"] = err
        print(json.dumps(rep, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "apply":
        for line in apply_auto(data, today) or ["nothing to change in the job list"]:
            print(line)
    elif a.cmd == "done":
        record(data, a.item_id, "done", today)
        print("%s done" % a.item_id)
    elif a.cmd == "decide":
        record(data, a.item_id, "approved" if a.decision == "approve" else "declined", today)
        print("%s %s" % (a.item_id, "approved" if a.decision == "approve" else "declined: not asked again"))
    elif a.cmd == "route":
        rs = rows(data)
        r = next((x for x in rs if x.get("id") == "install-route"), None)
        if r:
            r["value"] = a.route
        else:
            rs.append({"id": "install-route", "value": a.route, "date": today})
        print("install route: %s" % a.route)
    with open(a.file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
