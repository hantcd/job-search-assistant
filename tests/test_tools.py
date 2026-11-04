"""Tests for every script in the pack. Run: python3 -m unittest discover -s tests -v"""

import copy
import datetime
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from _load import fixture, load

D = datetime.date
PIPE = json.load(open(fixture("pipeline.json"), encoding="utf-8"))


def quiet(fn, *a, **k):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = fn(*a, **k)
    return code, out.getvalue(), err.getvalue()


class Tracker(unittest.TestCase):
    p = load("job-tracker", "pipeline")

    def test_fixture_is_valid(self):
        errs, _ = self.p.validate(copy.deepcopy(PIPE))
        self.assertEqual(errs, [])

    def test_two_runs_dont_duplicate(self):
        data = self.p.empty()
        _, new1 = self.p.add_job(data, D(2026, 10, 16), "Acme Ltd", "Junior Data Analyst", "https://a/1", "R-1")
        _, new2 = self.p.add_job(data, D(2026, 10, 16), "Acme Ltd", "Junior Data Analyst", "https://a/1", "R-1")
        self.assertTrue(new1)
        self.assertFalse(new2)
        self.assertEqual(len(data["jobs"]), 1)

    def test_linkedin_copy_saves_once(self):
        data = self.p.empty()
        self.p.add_job(data, D(2026, 10, 16), "Acme Ltd", "Junior Data Analyst", "https://acme.ie/jobs/1")
        row, new = self.p.add_job(data, D(2026, 10, 17), "Acme", "Junior Data Analyst (Dublin)",
                                  "https://www.linkedin.com/jobs/view/99")
        self.assertFalse(new)
        self.assertIn("https://www.linkedin.com/jobs/view/99", row["other_links"])

    def test_repost_updates_row(self):
        data = self.p.empty()
        self.p.add_job(data, D(2026, 9, 1), "Acme", "Analyst", ref="R-9", posted="2026-09-01")
        row, new = self.p.add_job(data, D(2026, 10, 1), "Acme", "Analyst", ref="R-9", posted="2026-10-01")
        self.assertFalse(new)
        self.assertEqual(row["reposts"], ["2026-10-01"])

    def test_agency_and_direct_is_an_error(self):
        data = copy.deepcopy(PIPE)
        data["jobs"].append({"id": "corrib-direct", "company": "Corrib Bank", "title": "Graduate Analyst",
                             "status": "applied", "applied": "2026-10-01", "route": "portal"})
        errs, _ = self.p.validate(data)
        self.assertTrue(any("agency and directly" in e for e in errs))

    def test_guessed_email_needs_privacy_decision(self):
        data = copy.deepcopy(PIPE)
        data["contacts"][0]["privacy_decision"] = ""
        errs, _ = self.p.validate(data)
        self.assertTrue(any("privacy" in e for e in errs))

    def test_published_needs_url(self):
        data = copy.deepcopy(PIPE)
        data["contacts"][0]["email_confidence"] = "published"
        errs, _ = self.p.validate(data)
        self.assertTrue(any("published" in e for e in errs))

    def test_bad_weights(self):
        data = copy.deepcopy(PIPE)
        data["applications"][0]["screening_weights"] = {"search": 50, "scan": 35, "read": 25}
        errs, _ = self.p.validate(data)
        self.assertTrue(any("totalling 100" in e for e in errs))

    def test_summary_counts_conversations(self):
        _, line = self.p.summary(PIPE, D(2026, 10, 20))
        self.assertEqual(line, "This week: 1 conversation, 1 reply, 0 applications.")

    def test_stale_after_four_weeks(self):
        ids = [j["id"] for j, _ in self.p.stale(PIPE, D(2026, 10, 20))]
        self.assertEqual(ids, ["corrib-bank-graduate-analyst"])

    def test_move_sets_applied(self):
        data = copy.deepcopy(PIPE)
        row = self.p.move(data, "liffey-labs-bi-analyst", "applied", D(2026, 10, 20))
        self.assertEqual(row["applied"], "2026-10-20")
        with self.assertRaises(self.p.PipelineError):
            self.p.move(data, "liffey-labs-bi-analyst", "hired", D(2026, 10, 20))

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "p.json")
            self.assertEqual(quiet(self.p.main, ["--file", f, "init"])[0], 0)
            self.assertEqual(quiet(self.p.main, ["--file", f, "add-job", "--company", "A", "--title", "B",
                                                 "--today", "2026-10-16"])[0], 0)
            self.assertEqual(quiet(self.p.main, ["--file", f, "validate"])[0], 0)
            out = os.path.join(d, "jobs.csv")
            self.assertEqual(quiet(self.p.main, ["--file", f, "export", "--what", "jobs", "--out", out])[0], 0)
            self.assertIn("company", open(out).read())


class Scout(unittest.TestCase):
    f = load("job-scout", "feeds")
    s = load("job-scout", "score")

    def test_greenhouse(self):
        rows = self.f.normalise("greenhouse", json.load(open(fixture("job-scout", "greenhouse.json"))))
        self.assertEqual(rows[0]["ref"], "R-101")
        self.assertEqual(rows[0]["posted"], "2026-10-15")
        self.assertIn("SQL and Power BI", rows[0]["text"])
        self.assertTrue(rows[1]["remote"])

    def test_lever_and_ashby(self):
        lv = self.f.normalise("lever", json.load(open(fixture("job-scout", "lever.json"))), "Liffey Labs")
        self.assertEqual(lv[0]["company"], "Liffey Labs")
        self.assertRegex(lv[0]["posted"], r"^20\d\d-\d\d-\d\d$")
        ab = self.f.normalise("ashby", json.load(open(fixture("job-scout", "ashby.json"))), "Liffey Labs")
        self.assertEqual([r["title"] for r in ab], ["BI Analyst"])  # unlisted roles dropped

    def test_filters(self):
        rows = self.f.normalise("greenhouse", json.load(open(fixture("job-scout", "greenhouse.json"))))
        keep = [r for r in rows if self.f.keep(r, ["analyst"], ["dublin"], 30, D(2026, 10, 16), False)]
        self.assertEqual([r["title"] for r in keep], ["Junior Data Analyst"])

    def test_detect(self):
        self.assertEqual(self.f.detect("https://job-boards.greenhouse.io/intercom/jobs/123"), ("greenhouse", "intercom"))
        self.assertEqual(self.f.detect("https://acme.wd3.myworkdayjobs.com/en-US/careers")[0], "workday")
        self.assertEqual(self.f.detect("https://example.com/careers"), (None, ""))

    def test_from_file_cli(self):
        code, out, _ = quiet(self.f.main, ["fetch", "greenhouse", "acme", "--from-file",
                                           fixture("job-scout", "greenhouse.json"), "--title", "analyst",
                                           "--no-text"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)), 1)

    def test_boards_file(self):
        b = json.load(open(os.path.join(os.path.dirname(self.f.__file__), "boards.json")))
        self.assertTrue(all(x["type"] in ("greenhouse", "lever", "ashby", "careers-page") for x in b["boards"]))

    def prefs(self):
        return self.s.read_prefs(fixture("prefs.md"))

    def job(self, rating=4, support="supported", posted="2026-10-15"):
        cv = {k: {"rating": rating, "support": support} for k in ("learning", "pay", "people", "responsibility",
                                                                   "stability", "prestige")}
        at = {k: {"rating": rating, "support": support} for k in ("must_haves_met", "level_fit", "eligibility",
                                                                  "connection", "competition")}
        return {"id": "j", "posted": posted, "career_value": cv, "attainability": at}

    def test_exact_scores(self):
        r = self.s.score_all([self.job(4)], self.prefs(), D(2026, 10, 16))[0]
        self.assertEqual((r["career_value"], r["attainability"], r["confidence"]), (80, 80, "HIGH"))
        self.assertTrue(r["apply_today"])

    def test_unknown_never_neutral(self):
        j = self.job(4)
        j["career_value"]["pay"] = {"rating": 5, "support": "unknown"}
        r = self.s.score_all([j], self.prefs(), D(2026, 10, 16))[0]
        self.assertEqual(r["score_breakdown"]["career_value"]["pay"]["rating"], 2)
        self.assertEqual(r["confidence"], "LOW")  # pay is a key part (second-highest weight)
        self.assertTrue(r["checks"])

    def test_partial_is_medium(self):
        j = self.job(4)
        j["career_value"]["stability"]["support"] = "partial"
        self.assertEqual(self.s.score_all([j], self.prefs(), D(2026, 10, 16))[0]["confidence"], "MEDIUM")

    def test_hard_job_keeps_career_value(self):
        easy, hard = self.job(4), self.job(4)
        for p in hard["attainability"].values():
            p["rating"] = 1
        a, b = self.s.score_all([easy, hard], self.prefs(), D(2026, 10, 16))
        self.assertEqual(a["career_value"], b["career_value"])

    def test_fresh_first_among_similar(self):
        old, new = self.job(4, posted="2026-09-01"), self.job(4, posted="2026-10-15")
        old["id"], new["id"] = "old", "new"
        new["career_value"]["prestige"]["rating"] = 3  # 2 points lower
        ranked = self.s.score_all([old, new], self.prefs(), D(2026, 10, 16))
        self.assertEqual([r["id"] for r in ranked], ["new", "old"])

    def test_weights_must_total_100(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"career_value": {"weights": {"a": 50}}, "attainability": {"weights": {"b": 100}}}, fh)
        with self.assertRaises(self.s.ScoreError):
            self.s.read_prefs(fh.name)
        os.unlink(fh.name)

    def test_stale_repost_is_suspicious_without_changing_score(self):
        j = self.job(4, posted="2026-07-01")
        j["signals"] = {"reposts_90d": 3, "apply_works": True}
        r = self.s.score_all([j], self.prefs(), D(2026, 10, 16))[0]
        self.assertEqual(r["legitimacy"], "SUSPICIOUS")
        self.assertEqual(r["career_value"], 80)

    def test_legitimacy_levels(self):
        self.assertEqual(self.s.legitimacy({"age_days": 3, "on_company_site": True})[0], "HIGH CONFIDENCE")
        self.assertEqual(self.s.legitimacy({"age_days": 70})[0], "PROCEED WITH CAUTION")
        self.assertEqual(self.s.legitimacy({"apply_works": False})[0], "SUSPICIOUS")

    def test_alerts_cap_and_packs(self):
        jobs = []
        for i in range(8):
            j = self.job(4)
            j["id"] = "j%d" % i
            jobs.append(j)
        scored = self.s.score_all(jobs, self.prefs(), D(2026, 10, 16))
        keep, packs = self.s.alerts(scored, self.prefs())
        self.assertEqual(len(keep), 5)
        self.assertEqual(len(packs), 2)

    def test_empty_run_is_one_line(self):
        code, out, _ = quiet(self.s.main, ["alerts", fixture("job-scout", "empty_scored.json"), "--prefs",
                                           fixture("prefs.md")])
        self.assertEqual(out.strip().count("\n"), 0)
        self.assertEqual(code, 1)


class CV(unittest.TestCase):
    t = load("job-cv", "truth_check")
    k = load("job-cv", "keywords")
    c = load("job-cv", "cvtext")

    def read(self, name):
        return self.c.read_text(fixture("job-cv", name))

    def test_clean_cv_passes(self):
        fails, _ = self.t.check(self.read("cv_good.md"), [self.read("evidence.md")])
        self.assertEqual(fails, [])

    def test_invented_number_and_skill_fail(self):
        fails, warns = self.t.check(self.read("cv_invented.md"), [self.read("evidence.md")])
        joined = " ".join(fails)
        for item in ("25", "50k", "Tableau", "dbt", "stakeholder management"):
            self.assertIn(item, joined)
        self.assertTrue(any("Deloitte" in w for w in warns))

    def test_ad_wording_preferred(self):
        r = self.k.compare(self.read("ad.txt"), self.read("cv_good.md"), self.c.load_terms())
        self.assertIn("MS Excel", r["covered"])
        self.assertIn("Tableau", r["missing"])

    def test_reword_detected(self):
        r = self.k.compare("Requirements: Golang", "Built services in Go.", self.c.load_terms())
        self.assertEqual(r["reword"], [("Golang", "Go")])

    def test_tex_is_read(self):
        txt = self.c.tex_to_text(r"\resumeItem{Cut report time by 85\% with \textbf{Python}}")
        self.assertIn("85%", txt)
        self.assertIn("Python", txt)

    def test_numbers_normalised(self):
        self.assertEqual(self.c.numbers("cut 38 per cent, saved €1,200 and 4M rows"), {"38%", "1200", "4m"})

    def test_template_compiles_settings(self):
        tex = open(os.path.join(os.path.dirname(self.t.__file__), "jakes-resume.tex")).read()
        self.assertIn("\\pdfgentounicode=1", tex)
        self.assertIn("License : MIT", tex)


@unittest.skipUnless(os.path.exists(fixture("job-cv", "one_page.pdf")), "PDF fixtures missing")
class Layout(unittest.TestCase):
    def setUp(self):
        try:
            self.l = load("job-cv", "layout_check")
        except SystemExit:
            self.skipTest("PyMuPDF not installed")

    def results(self, *args, pages=1):
        return {name: (ok, hard) for name, ok, _, hard in self.l.check(*args, max_pages=pages)}

    def test_one_page_passes(self):
        r = self.results(fixture("job-cv", "one_page.pdf"), fixture("job-cv", "one_page.log"))
        self.assertTrue(all(ok or not hard for ok, hard in r.values()))

    def test_overflow_fails_one_page_limit(self):
        r = self.results(fixture("job-cv", "two_pages.pdf"))
        self.assertFalse(r["pages"][0])

    def test_two_page_preset_allows_it(self):
        r = self.results(fixture("job-cv", "two_pages.pdf"), pages=2)
        self.assertTrue(r["pages"][0])
        self.assertFalse(r["page fill"][0])  # short second page: a warning, not a failure

    def test_widow_word_found(self):
        r = self.results(fixture("job-cv", "two_pages.pdf"), pages=2)
        self.assertFalse(r["no 1-2 word bullet endings"][0])


class Cover(unittest.TestCase):
    l = load("job-cover", "letter_check")
    c = load("job-cover", "clean_text")

    GOOD = ("Dear Siobhan,\n\nYour team's post on claims dashboards caught my eye, because I built one at Brightwater "
            "Insurance that 12 managers now use every week. Acme Ltd's Junior Data Analyst role asks for SQL and "
            "Power BI, and that's most of what I did there. " + "I also automated a monthly report in Python, "
            "cutting it from 6 hours to 40 minutes. " * 3 + "Could we talk next week?\n\nAoife")

    def statuses(self, text, **kw):
        return {n: s for n, s, _ in self.l.check(text, "Acme Ltd", "Junior Data Analyst", **kw)}

    def test_good_letter(self):
        st = self.statuses(self.GOOD, sources=[open(fixture("job-cv", "evidence.md")).read()])
        self.assertNotIn("FAIL", st.values())

    def test_placeholder_and_wrong_company_fail(self):
        st = self.statuses(self.GOOD.replace("Acme Ltd's", "[Company]'s") + " I'd love to join Corrib Bank.",
                           others=["Corrib Bank", "Acme Ltd"])
        self.assertEqual(st["placeholders"], "FAIL")
        self.assertEqual(st["other companies"], "FAIL")
        self.assertEqual(st["company named"], "FAIL")

    def test_invented_number_fails(self):
        st = self.statuses(self.GOOD.replace("12 managers", "30 managers"),
                           sources=[open(fixture("job-cv", "evidence.md")).read()])
        self.assertEqual(st["numbers traceable"], "FAIL")

    def test_stock_phrases_warn_only(self):
        st = self.statuses("I am writing to express my interest. I am passionate about data. " + self.GOOD)
        self.assertEqual(st["stock phrases"], "WARN")

    def test_clean_text(self):
        out, counts = self.c.clean("It’s done​ “now” — really")
        self.assertEqual(out, "It's done \"now\" — really")  # dashes kept
        self.assertEqual(counts, {"invisible": 1, "spaces": 1, "quotes": 3})


class Apply(unittest.TestCase):
    a = load("job-apply", "answers")

    def test_classify(self):
        cases = {"First name": "FILL", "Do you require visa sponsorship?": "YOU", "Current salary": "YOU",
                 "Expected salary": "YOU", "Gender": "YOU", "What languages do you speak?": "FILL",
                 "Why do you want to work here?": "DRAFT", "Create a password": "SKIP-PASSWORD",
                 "I confirm the information is accurate": "YOU", "Date of birth": "YOU",
                 "LinkedIn profile URL": "FILL", "Notice period": "FILL"}
        for q, want in cases.items():
            self.assertEqual(self.a.classify(q), want, q)

    def test_required_sensitive_blocks(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump([{"label": "Right to work in Ireland?", "required": True}, "Email"], fh)
        code, out, _ = quiet(self.a.main, [fh.name])
        os.unlink(fh.name)
        self.assertEqual(code, 1)
        self.assertIn("only you can answer", out)


class LinkedIn(unittest.TestCase):
    p = load("job-linkedin", "profile_check")

    def test_limits(self):
        rows = self.p.check_limits({"headline": "x" * 221, "about": "ok", "skills": [], "invitation_note": "y" * 201})
        st = {n: s for s, n, _ in rows}
        self.assertEqual(st["headline"], "FAIL")
        self.assertEqual(st["invitation_note"], "FAIL")

    def test_rubric_totals_100(self):
        self.assertEqual(sum(self.p.RUBRIC.values()), 100)

    def test_activity_full_when_off(self):
        total, _ = self.p.score({k: 0 for k in self.p.RUBRIC}, "off")
        self.assertEqual(total, 10)

    def test_points_out_of_range(self):
        with self.assertRaises(ValueError):
            self.p.score({"headline": 13})


class Connector(unittest.TestCase):
    o = load("job-connector", "outreach")
    e = load("job-connector", "emails")

    def test_email_check(self):
        res = {n: s for n, s, _ in self.o.check("email", "Hi Siobhan, " + "word " * 80 + "?",
                                                  "Junior Data Analyst role", "Junior Data Analyst")}
        self.assertEqual(res["length"], "FAIL")
        res = {n: s for n, s, _ in self.o.check("email", "Hi Siobhan, quick question about the role?",
                                                  "Hello", "Junior Data Analyst")}
        self.assertEqual(res["subject"], "WARN")

    def test_note_limit(self):
        res = {n: s for n, s, _ in self.o.check("note", "x" * 201)}
        self.assertEqual(res["length"], "FAIL")

    def test_slots_never_repeat(self):
        for start in range(10, 24):
            plan = self.o.slots(D(2026, 10, start))
            days = [p["day"] for p in plan]
            self.assertEqual(len(set(days)), 3, plan)
            for p in plan:
                self.assertNotIn(p["day"], ("Sat", "Sun"))
                if p["day"] == "Fri":
                    self.assertIn(p["band"], ("morning", "early"))
            self.assertEqual(plan[0]["band"], "morning")
            self.assertEqual(plan[1]["band"], "afternoon")

    def test_senior_waits_longer(self):
        a = self.o.slots(D(2026, 10, 12))
        b = self.o.slots(D(2026, 10, 12), senior=True)
        self.assertGreater(b[1]["date"], a[1]["date"])

    def test_exact_yes_only(self):
        for ok in ("yes", "Yes, send it", "send it", "approved"):
            self.assertIsNotNone(self.o.approve("draft", ok)[0], ok)
        for bad in ("sure", "ok", "yes to all", "yes but change the subject", "yeah maybe"):
            self.assertIsNone(self.o.approve("draft", bad)[0], bad)

    def test_hash_changes_with_edit(self):
        a = self.o.approve("draft one", "yes")[0]["hash"]
        b = self.o.approve("draft two", "yes")[0]["hash"]
        self.assertNotEqual(a, b)

    def test_email_guess_learns_pattern(self):
        rows, learned = self.e.guess("Siobhán O'Brien", "acme.ie", "Ciara Doyle ciara.doyle@acme.ie")
        self.assertEqual(learned, "{first}.{last}")
        self.assertEqual(rows[0]["email"], "siobhan.obrien@acme.ie")
        self.assertTrue(all(r["status"] == "GUESS" for r in rows))

    def test_privacy_labels(self):
        self.assertEqual(self.e.PRIVACY["published-work-page"][0], "LOW")
        self.assertEqual(self.e.PRIVACY["company-pattern"][0], "MEDIUM")
        self.assertEqual(self.e.PRIVACY["data-broker"][0], "HIGH")
        code, _, _ = quiet(self.e.main, ["privacy", "--method", "personal"])
        self.assertEqual(code, 3)


class Followup(unittest.TestCase):
    f = load("job-followup", "followup")

    def groups(self, data=None, today=D(2026, 10, 20)):
        return self.f.due(data or copy.deepcopy(PIPE), today)

    def test_groups(self):
        g = self.groups()
        self.assertTrue(any("Declan" in m for m in g["DRAFTS"]))
        self.assertTrue(any("Niamh" in m for m in g["YOUR TURN"]))
        self.assertTrue(any("Siobhan" in m and "follow-up 1" in m for m in g["DUE NOW"]))
        self.assertTrue(any("Tom Ryan" in m for m in g["STOPPED"]))
        self.assertTrue(any("thank-you" in m for m in g["DUE NOW"]))
        self.assertTrue(any("deadline" in m for m in g["DUE NOW"]))
        self.assertTrue(any("stale" in m for m in g["DUE NOW"]))
        self.assertFalse(any("Brightwater" in m and "3 days since" in m for m in g["DUE NOW"]))

    def thread(self, *msgs, **kw):
        o = {"contact_id": "c", "channel": "email", "status": "sent",
             "messages": [{"date": d, "direction": dr, "text": t} for d, dr, t in msgs]}
        o.update(kw)
        return o

    def test_three_day_hint_then_wait(self):
        g, m = self.f.thread_state(self.thread(("2026-10-12", "out", "hi")), {"name": "X"}, D(2026, 10, 15))
        self.assertEqual(g, "DUE NOW")
        self.assertIn("another person", m)

    def test_two_follow_ups_then_stop(self):
        t = self.thread(("2026-10-01", "out", "a"), ("2026-10-12", "out", "b"), ("2026-10-19", "out", "c"))
        self.assertEqual(self.f.thread_state(t, {"name": "X"}, D(2026, 10, 20))[0], "STOPPED")

    def test_same_day_email_and_linkedin_is_one_opening(self):
        t = self.thread(("2026-10-12T09:00", "out", "email"), ("2026-10-12T09:05", "out", "connect"))
        g, m = self.f.thread_state(t, {"name": "X"}, D(2026, 10, 21))
        self.assertIn("follow-up 1", m)

    def test_21_days_silence(self):
        t = self.thread(("2026-09-20", "out", "a"))
        self.assertEqual(self.f.thread_state(t, {"name": "X"}, D(2026, 10, 20))[0], "STOPPED")

    def test_first_no_stops_every_channel(self):
        data = copy.deepcopy(PIPE)
        data["outreach"].append({"contact_id": "niamh-walsh-corrib", "channel": "linkedin", "status": "sent",
                                 "messages": [{"date": "2026-10-01", "direction": "out", "text": "hi"},
                                              {"date": "2026-10-02", "direction": "in", "text": "Not right now, sorry"}]})
        g = self.groups(data)
        self.assertTrue(any("Niamh" in m for m in g["STOPPED"]))

    def test_reply_resets_count(self):
        t = self.thread(("2026-10-01", "out", "a"), ("2026-10-08", "out", "b"), ("2026-10-09", "in", "tell me more"),
                        ("2026-10-09", "out", "answer"))
        g, _ = self.f.thread_state(t, {"name": "X"}, D(2026, 10, 12))
        self.assertNotEqual(g, "STOPPED")

    def test_invite_gets_no_follow_up(self):
        t = self.thread(("2026-10-01", "out", "note"), channel="linkedin", invite_pending=True)
        self.assertEqual(self.f.thread_state(t, {"name": "X"}, D(2026, 10, 15))[0], "WAITING")

    def test_senior_waits_ten(self):
        t = self.thread(("2026-10-09", "out", "a"))
        self.assertNotIn("follow-up 1", self.f.thread_state(t, {"name": "X", "senior": True}, D(2026, 10, 20))[1])

    def test_agency_follow_up_goes_to_agency(self):
        data = copy.deepcopy(PIPE)
        for j in data["jobs"]:
            if j["id"] == "corrib-bank-graduate-analyst":
                j["applied"] = "2026-10-10"
        g = self.groups(data)
        self.assertTrue(any("Corrib" in m and "agency recruiter" in m for m in g["DUE NOW"]))


class Interview(unittest.TestCase):
    s = load("job-interview", "star")

    def test_full_star(self):
        ans = ("During my internship at Brightwater Insurance, the claims team needed a weekly view of open claims. "
               "My job was to build it. I built a Power BI dashboard and I met each manager to agree the measures. "
               "As a result 12 managers now use it weekly. ") * 2
        score, parts, _ = self.s.check(ans)
        self.assertEqual(score, 5)

    def test_we_only_is_flagged(self):
        score, parts, tips = self.s.check("We worked on a project and we finished it.")
        self.assertFalse(parts["action"])
        self.assertTrue(any("YOU did" in t for t in tips))

    def test_grid_gaps(self):
        cover, gaps, thin = self.s.grid({"stories": [{"name": "dashboard", "themes": ["a challenge", "leadership"]}]})
        self.assertIn("a failure", gaps)
        self.assertIn("leadership", thin)


class Offer(unittest.TestCase):
    o = load("job-offer", "offer")
    OFFER = {"company": "Acme", "role": "Analyst", "base": 50000, "bonus_target_pct": 10, "sign_on": 2000,
             "pension_employer_pct": 5, "equity": {"grant_value": 8000, "vesting": [25, 25, 25, 25], "kind": "RSU"}}

    def test_years(self):
        rows = self.o.years_table(self.OFFER, 4)
        self.assertEqual(rows[0]["guaranteed"], 52000)
        self.assertEqual(rows[1]["guaranteed"], 50000)
        self.assertEqual(rows[0]["variable_target"], 5000)
        self.assertEqual(rows[0]["equity"], 2000)
        self.assertEqual(rows[0]["benefits"], 2500)

    def test_backloaded_vesting(self):
        o = dict(self.OFFER, equity={"grant_value": 10000, "vesting": [5, 15, 40, 40]})
        self.assertEqual([r["equity"] for r in self.o.years_table(o)], [500, 1500, 4000, 4000])

    def test_bad_vesting(self):
        with self.assertRaises(ValueError):
            self.o.years_table(dict(self.OFFER, equity={"grant_value": 1, "vesting": [50, 30]}))

    def test_counter_needs_sources(self):
        with self.assertRaises(ValueError):
            self.o.counter(self.OFFER, [{"mid": 55000, "high": 62000}])
        r = self.o.counter(self.OFFER, [{"source": "Hays Salary Guide 2026", "date": "2026-01", "mid": 55000,
                                         "high": 62000}])
        self.assertEqual(r["counter_range"][0], 55000)
        self.assertGreaterEqual(r["counter_range"][1], 60000)


class Weekly(unittest.TestCase):
    w = load("job-weekly", "funnel")

    def test_counts_and_small_groups(self):
        r = self.w.report(copy.deepcopy(PIPE))
        self.assertEqual(r["applications"]["replied"], "1 of 3 (33%)")
        self.assertEqual(r["by"]["route"]["referral"]["label"], "too few to tell")
        self.assertIn("Too early", r["diagnosis"])

    def test_diagnosis_after_20(self):
        data = {"jobs": [{"id": str(i), "company": "C", "title": "T", "applied": "2026-10-01", "status": "applied"}
                         for i in range(25)]}
        self.assertIn("replies", self.w.report(data)["diagnosis"])
        for j in data["jobs"][:10]:
            j["status"] = "interview"
        self.assertIn("offers", self.w.report(data)["diagnosis"])


class Research(unittest.TestCase):
    n = load("job-research", "notes_check")

    def test_labels_links_dates(self):
        text = ("Researched: 2026-10-01\n"
                "- Values: ownership, learning (OFFICIAL, https://acme.ie/about, 2026-10-01)\n"
                "- Online SQL test then two interviews (SEVERAL REPORTS, https://glassdoor.ie/x, 2026-09)\n"
                "- Probably uses Workday (GUESS, 2026-10-01)\n"
                "- Team size (fill in)\n")
        errors, todo, newest, stale = self.n.check(text, D(2026, 10, 16))
        self.assertEqual(errors, [])
        self.assertEqual(len(todo), 1)
        self.assertFalse(stale)

    def test_missing_link_and_stale(self):
        errors, _, _, stale = self.n.check("- Interviews are easy (ONE REPORT, 2026-01-01)\n", D(2026, 10, 16))
        self.assertTrue(any("no link" in e for e in errors))
        self.assertTrue(stale)


class Network(unittest.TestCase):
    e = load("job-network", "events")

    def test_register_today_and_speaker_call(self):
        out = self.e.due(PIPE["events"], D(2026, 10, 20))
        self.assertTrue(out["REGISTER TODAY"])
        self.assertTrue(out["SPEAKER CALL"])

    def test_follow_up_within_48h(self):
        ev = [{"name": "Meetup", "date": "2026-10-19", "registered": True, "attended": True}]
        self.assertTrue(self.e.due(ev, D(2026, 10, 20))["FOLLOW UP"])
        self.assertFalse(self.e.due(ev, D(2026, 10, 23))["FOLLOW UP"])


if __name__ == "__main__":
    unittest.main()


class CanApply(unittest.TestCase):
    p = load("job-tracker", "pipeline")

    def data(self):
        return copy.deepcopy(PIPE)

    def add(self, data, jid, company, title, status="open", applied=None, route="portal"):
        data["jobs"].append({"id": jid, "company": company, "title": title, "status": status,
                             "applied": applied or "", "route": route})

    def test_ok(self):
        self.assertEqual(self.p.can_apply(self.data(), "liffey-labs-bi-analyst", D(2026, 10, 20))[0], "OK")

    def test_already_applied(self):
        v, r = self.p.can_apply(self.data(), "acme-junior-data-analyst", D(2026, 10, 20))
        self.assertEqual(v, "BLOCK")

    def test_mid_interview_asks(self):
        d = self.data()
        self.add(d, "brightwater-bi", "Brightwater Insurance", "BI Analyst")
        v, r = self.p.can_apply(d, "brightwater-bi", D(2026, 10, 20))
        self.assertEqual(v, "ASK")
        self.assertIn("mid-process", r[0])

    def test_cap_and_same_day(self):
        d = self.data()
        self.add(d, "acme-2", "Acme Ltd", "Data Engineer", "applied", "2026-10-20")
        self.add(d, "acme-3", "Acme Ltd", "BI Analyst")
        v, r = self.p.can_apply(d, "acme-3", D(2026, 10, 20))
        self.assertEqual(v, "BLOCK")
        joined = " ".join(r)
        self.assertIn("cap is 2", joined)
        self.assertIn("today", joined)
        self.assertEqual(self.p.can_apply(d, "acme-3", D(2026, 10, 25), cap=3)[0], "OK")

    def test_agency_and_direct(self):
        d = self.data()
        self.add(d, "corrib-direct", "Corrib Bank", "Graduate Analyst", route="portal")
        v, r = self.p.can_apply(d, "corrib-direct", D(2026, 10, 20))
        self.assertEqual(v, "BLOCK")
        self.assertIn("agency", " ".join(r))

    def test_company_limit(self):
        d = {"jobs": [], "applications": [], "contacts": [], "outreach": [], "run_log": []}
        for i in range(5):
            self.add(d, "oa-%d" % i, "OpenAI", "Role %d" % i, "applied", "2026-0%d-01" % (i + 5))
        self.add(d, "oa-new", "OpenAI", "New role")
        v, r = self.p.can_apply(d, "oa-new", D(2026, 10, 20), cap=10)
        self.assertEqual(v, "BLOCK")
        self.assertIn("180 days", " ".join(r))
        d["jobs"] = d["jobs"][3:]
        self.assertEqual(self.p.can_apply(d, "oa-new", D(2026, 10, 20), cap=10)[0], "ASK")

    def test_recorded_limit_in_company_notes(self):
        d = self.data()
        d["companies"] = [{"company": "Liffey Labs", "limit_max": 1, "limit_window_days": 365}]
        self.add(d, "liffey-old", "Liffey Labs", "Data Analyst", "rejected", "2026-06-01")
        self.assertEqual(self.p.can_apply(d, "liffey-labs-bi-analyst", D(2026, 10, 20))[0], "BLOCK")

    def test_submitted_without_record_warns(self):
        _, warns = self.p.validate(self.data())
        self.assertTrue(any("answers given" in w for w in warns))


class Gates(unittest.TestCase):
    g = load("job-scout", "gates")

    def test_tricky_ad(self):
        found, skip = self.g.scan(open(fixture("job-scout", "gated_ad.txt")).read(), years_max=2, needs_sponsorship=True)
        ys = found["YEARS"]
        self.assertTrue(any(y["years"] == 18 and y["bio"] for y in ys))
        self.assertTrue(any(y["years"] == 6 and not y["bio"] for y in ys))
        self.assertTrue(found["SPONSORSHIP"])
        self.assertTrue(found["NOT-GRAD"])
        self.assertTrue(found["PAY"])
        self.assertTrue(any("6+ years" in s for s in skip))

    def test_post_grad_and_scale(self):
        found, _ = self.g.scan("Early Career: 1-3 years of full-time work experience post-graduation. "
                               "You've built systems at meaningful scale.")
        self.assertTrue(found["YEARS"][0]["post_grad"])
        self.assertTrue(found["SENIORITY"])

    def test_clean_ad(self):
        found, skip = self.g.scan("Graduate Data Analyst. We train you. Hybrid in Dublin.", years_max=1)
        self.assertEqual(skip, [])


class TexChecks(unittest.TestCase):
    t = load("job-cv", "tex_check")

    def test_escapes(self):
        bad = ("\\documentclass{article}\n% a comment with 100% and & is fine\n\\begin{document}\n"
               "\\resumeItem{Cut report time by 85% for the team}\n\\resumeItem{R\\&D and Q&A}\n"
               "\\href{https://x.com/a_b#c}{site} $|$ \\textbf{ok}\n\\end{document}\n")
        errs = " ".join(self.t.escapes(bad))
        self.assertIn("line 4", errs)
        self.assertIn("unescaped &", errs)
        self.assertNotIn("#", errs.replace("\\#", ""))

    def test_template_is_clean(self):
        tex = open(os.path.join(os.path.dirname(self.t.__file__), "jakes-resume.tex")).read()
        self.assertEqual(self.t.escapes(tex), [])

    def test_conversion(self):
        missing, extra = self.t.conversion("Built a Flask API used by 40 teams", "Built a Django API used by 40 teams")
        self.assertIn("flask", missing)
        self.assertIn("django", extra)
        missing, _ = self.t.conversion("Built a Flask API", "\\begin{document}\\resumeItem{Built a Flask API}\\end{document}")
        self.assertEqual(sum(missing.values()), 0)


class LetterOverlap(unittest.TestCase):
    l = load("job-cover", "letter_check")

    def test_restates_cv_and_echoes_ad(self):
        cv = "- Built a Power BI dashboard for the claims team at Brightwater Insurance, used weekly by 12 managers"
        ad = "We need someone with strong SQL and Power BI skills to build dashboards for our claims team."
        text = ("At Brightwater Insurance I built a Power BI dashboard for the claims team, used weekly by 12 managers. "
                "You need someone with strong SQL and Power BI skills to build dashboards for the claims team. "
                "First I'd want to understand why renewals dip in March.")
        st = {n: s for n, s, _ in self.l.check(text, "Acme", kind="note", cv=cv, ad=ad)}
        self.assertEqual(st["adds to the CV"], "WARN")
        self.assertEqual(st["own words"], "WARN")

    def test_fresh_sentences_pass(self):
        st = {n: s for n, s, _ in self.l.check("Your renewals team wrote about March churn; I'd start there.",
                                              "Acme", kind="note", cv="Built dashboards in Power BI", ad="SQL needed")}
        self.assertEqual(st["adds to the CV"], "PASS")


class ApplyExtras(unittest.TestCase):
    a = load("job-apply", "answers")

    def test_lengths(self):
        bad = self.a.lengths([{"label": "Why us?", "answer": "x" * 300, "max_length": 255},
                              {"label": "Name", "answer": "Aoife", "max_length": 100}])
        self.assertEqual(len(bad), 1)

    def test_consent_notes(self):
        self.assertEqual(self.a.classify("Do you consent to your interview being recorded?"), "YOU")
        self.assertIn("not a condition", self.a.note("I agree to receive marketing from third parties"))

    def test_board_list_grew(self):
        b = json.load(open(os.path.join(os.path.dirname(load("job-scout", "feeds").__file__), "boards.json")))
        self.assertGreaterEqual(sum(1 for x in b["boards"] if x["type"] != "careers-page"), 250)


class LinkedInListings(unittest.TestCase):
    l = load("job-scout", "linkedin_jobs")

    def test_cards(self):
        rows = self.l.parse_cards(open(fixture("job-scout", "linkedin_search.html"), encoding="utf-8").read())
        self.assertEqual([r["ref"] for r in rows], ["linkedin:4425498329", "linkedin:4425494976"])
        self.assertEqual(rows[0]["company"], "Humans.tech")
        self.assertEqual(rows[0]["posted"], "2026-07-10")
        self.assertNotIn("?", rows[0]["url"])

    def test_detail(self):
        d = self.l.parse_detail(open(fixture("job-scout", "linkedin_detail.html"), encoding="utf-8").read(), "4345841651")
        self.assertIn("Agentic AI Engineer", d["title"])
        self.assertIn("agentic", d["text"].lower())
        self.assertIn("active", d)

    def test_url_and_ids(self):
        u = self.l.search_url("data analyst", "Dublin, County Dublin, Ireland", days=1, remote="hybrid", page=2)
        self.assertIn("f_TPR=r86400", u)
        self.assertIn("f_WT=3", u)
        self.assertIn("start=10", u)
        self.assertEqual(self.l.job_id("https://ie.linkedin.com/jobs/view/data-analyst-at-acme-4425498329?x=1"), "4425498329")
        self.assertEqual(self.l.MAX_PAGES, 3)

    def test_skill_says_opt_in(self):
        text = open(os.path.join(os.path.dirname(self.l.__file__), "SKILL.md"), encoding="utf-8").read()
        self.assertIn("only if MASTER_PLAN.md turns them on", text)


class EligibilityLanguage(unittest.TestCase):
    g = load("job-scout", "gates")
    AD = ("Customer Insights Analyst, Dublin. The ideal candidate has fluent German and good English skills. "
          "French (B2) is a plus. Candidates must have the right to reside in Ireland (Stamp 4 or EU citizenship).")

    def test_languages(self):
        found, skip = self.g.scan(self.AD, my_languages=self.g.parse_languages("English:C2,French:B1"))
        v = {l["language"]: l["verdict"] for l in found["LANGUAGE"]}
        self.assertEqual(v, {"German": "FAIL", "English": "PASS", "French": "NICE TO HAVE"})
        self.assertTrue(any('"fluent German"' in s for s in skip))

    def test_flag_higher_level(self):
        found, _ = self.g.scan("Fluent English required.", my_languages=self.g.parse_languages("English:B2"))
        self.assertEqual(found["LANGUAGE"][0]["verdict"], "FLAG")

    def test_eligibility(self):
        found, skip = self.g.scan(self.AD, not_citizen=True)
        self.assertTrue(any(e["kind"].startswith("requires") for e in found["ELIGIBILITY"]))
        self.assertTrue(skip)
        found, _ = self.g.scan("Graduate Analyst in Dublin. Great team.")
        self.assertTrue(found["ELIGIBILITY"][0]["kind"].startswith("UNVERIFIED"))
        found, _ = self.g.scan("International applicants welcome; we sponsor Critical Skills Employment Permits.")
        self.assertTrue(any("welcomes" in e["kind"] for e in found["ELIGIBILITY"]))


class ParseAndLayout(unittest.TestCase):
    def setUp(self):
        try:
            self.p = load("job-cv", "parse_check")
            self.l = load("job-cv", "layout_check")
        except (SystemExit, ImportError):
            self.skipTest("PyMuPDF not installed")

    def test_parse_good(self):
        text = self.p.read_text(fixture("job-cv", "one_page.pdf"))
        res = {n: s for n, s, _ in self.p.check(text, "Jake Ryan", headings=["Education", "Experience", "Projects"],
                                                terms=["Python"])}
        self.assertNotIn("FAIL", res.values())

    def test_parse_problems(self):
        text = "Jake Ryan\n" + "word " * 60 + "(cid:12)  ﬁnance Experience Education"
        res = {n: s for n, s, _ in self.p.check(text, "Jake Ryan", email="jake@su.edu", phone="+1 123 456 7890",
                                                headings=["Education", "Experience"], terms=["Kubernetes"])}
        for k in ("no garbled glyphs", "no ligature glyphs", "email as text", "phone as text", "headings in order",
                  "term: Kubernetes"):
            self.assertEqual(res[k], "FAIL", k)

    def test_orphaned_title(self):
        r = {n: ok for n, ok, _, _ in self.l.check(fixture("job-cv", "orphan.pdf"), max_pages=2)}
        self.assertFalse(r["no orphaned entry title"])
        r = {n: ok for n, ok, _, _ in self.l.check(fixture("job-cv", "two_pages.pdf"), max_pages=2)}
        self.assertTrue(r["no orphaned entry title"])


class TrackerExtras(unittest.TestCase):
    p = load("job-tracker", "pipeline")

    def test_unreachable_needs_three_tries_over_48h(self):
        d = copy.deepcopy(PIPE)
        jid = "liffey-labs-bi-analyst"
        dt = datetime.datetime
        self.assertFalse(self.p.unreachable(d, jid, "HTTP 503", dt(2026, 10, 20, 8, 0))[1])
        self.assertFalse(self.p.unreachable(d, jid, "HTTP 503", dt(2026, 10, 20, 13, 0))[1])
        self.assertFalse(self.p.unreachable(d, jid, "HTTP 503", dt(2026, 10, 21, 8, 0))[1])  # 3 tries, 24h
        job, closed = self.p.unreachable(d, jid, "HTTP 503 " + "x" * 500, dt(2026, 10, 22, 8, 0))
        self.assertTrue(closed)
        self.assertEqual(job["status"], "closed")
        self.assertLessEqual(len(job["last_fetch_error"]), 200)

    def test_reachable_resets(self):
        d = copy.deepcopy(PIPE)
        self.p.unreachable(d, "liffey-labs-bi-analyst", "timeout", datetime.datetime(2026, 10, 20, 8))
        job = self.p.reachable(d, "liffey-labs-bi-analyst")
        self.assertNotIn("fetch_attempts", job)

    def test_csv_formula_guard(self):
        self.assertEqual(self.p.csv_safe('=HYPERLINK("http://x")'), '\'=HYPERLINK("http://x")')
        self.assertEqual(self.p.csv_safe("Data Analyst"), "Data Analyst")
        with tempfile.TemporaryDirectory() as dd:
            out = os.path.join(dd, "jobs.csv")
            d = {"jobs": [{"id": "a", "company": "@evil", "title": "-cmd"}]}
            self.p.export(d, "jobs", out)
            text = open(out, encoding="utf-8").read()
            self.assertIn("'@evil", text)
            self.assertIn("'-cmd", text)

    def test_email_log(self):
        d = copy.deepcopy(PIPE)
        d["email_log"] = [{"message_id": "m1", "date": "2026-10-20", "from": "hr@acme.ie", "subject": "Interview",
                           "change": "status interview"},
                          {"message_id": "m1", "date": "2026-10-20"},
                          {"message_id": "m2", "change": "status rejected"}]
        errs, _ = self.p.validate(d)
        joined = " ".join(errs)
        self.assertIn("already processed", joined)
        self.assertIn("must cite the email", joined)


class ReferralPath(unittest.TestCase):
    """Lessons from the REFER kit: check names, don't greet the recruiter who rejected you, ask well, nudge once."""
    p = load("job-tracker", "pipeline")
    o = load("job-connector", "outreach")
    f = load("job-followup", "followup")

    def data(self):
        return copy.deepcopy(PIPE)

    def test_unverified_employer_needs_a_check(self):
        v, why = self.p.contact_check(self.data(), "siobhan-kelly-acme", D(2026, 10, 20))
        self.assertEqual(v, "CHECK")
        self.assertTrue(any("UNVERIFIED" in r and "Acme" in r for r in why))

    def test_checked_employer_is_ok(self):
        d = self.data()
        d["contacts"][0]["employer_checked"] = "2026-10-18"
        self.assertEqual(self.p.contact_check(d, "siobhan-kelly-acme", D(2026, 10, 20)), ("OK", []))

    def test_do_not_contact_stops(self):
        self.assertEqual(self.p.contact_check(self.data(), "tom-ryan-liffey", D(2026, 10, 20))[0], "STOP")

    def test_contact_on_rejected_application(self):
        d = self.data()
        d["contacts"][0]["employer_checked"] = "2026-10-18"
        self.p.move(d, "acme-junior-data-analyst", "rejected", D(2026, 10, 19))
        v, why = self.p.contact_check(d, "siobhan-kelly-acme", D(2026, 10, 20))
        self.assertEqual(v, "CHECK")
        self.assertTrue(any("rejected on 2026-10-19" in r for r in why))

    def test_recruiter_at_company_that_rejected_you(self):
        d = self.data()
        d["contacts"].append({"id": "aoife-hr-acme", "name": "Aoife Hart", "role": "Talent Acquisition Partner",
                              "company": "Acme", "employer_checked": "2026-10-18"})
        self.p.move(d, "acme-junior-data-analyst", "rejected", D(2026, 10, 1))
        v, why = self.p.contact_check(d, "aoife-hr-acme", D(2026, 10, 20))
        self.assertEqual(v, "CHECK")
        self.assertTrue(any("recruits at" in r for r in why))
        # long ago: no warning
        self.assertEqual(self.p.contact_check(d, "aoife-hr-acme", D(2027, 6, 1))[0], "OK")

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "p.json")
            json.dump(self.data(), open(path, "w"))
            code, out, _ = quiet(self.p.main, ["--file", path, "contact-check", "siobhan-kelly-acme", "--today", "2026-10-20"])
            self.assertEqual(code, 3)
            self.assertIn("CHECK", out)
            code, _, _ = quiet(self.p.main, ["--file", path, "contact-check", "tom-ryan-liffey", "--today", "2026-10-20"])
            self.assertEqual(code, 1)

    def test_stage_and_date_validated(self):
        d = self.data()
        d["outreach"][0]["stage"] = "beg"
        d["contacts"][0]["employer_checked"] = "last week"
        errs, _ = self.p.validate(d)
        self.assertTrue(any("stage" in e for e in errs))
        self.assertTrue(any("employer_checked" in e for e in errs))

    def test_referral_ask_needs_link_and_easy_no(self):
        bad = "Would you refer me for the analyst role?"
        res = {n: s for n, s, _ in self.o.check("linkedin", bad, stage="ask")}
        self.assertEqual(res["job link"], "FAIL")
        self.assertEqual(res["easy no"], "FAIL")
        good = ("Thanks again, Siobhan. Would you be open to referring me for this role?\n"
                "Job: https://example.com/jobs/1\n- Built a dashboard 12 managers use\n"
                "If you'd rather not, no problem at all.")
        res = {n: s for n, s, _ in self.o.check("linkedin", good, stage="ask")}
        self.assertEqual((res["job link"], res["easy no"], res["why I fit"]), ("PASS", "PASS", "PASS"))
        self.assertNotIn("ask", res)  # a referral ask may mention the job

    def test_flattery_flagged_for_checking(self):
        res = {n: s for n, s, _ in self.o.check("note", "Hi Ana, fellow TCD grad here. Your post on dbt was great.")}
        self.assertEqual(res["true?"], "WARN")

    def test_google_queries_never_linkedin_pages(self):
        q = self.o.find_queries("Acme", "data analytics", school="Trinity College Dublin", city="Dublin")
        self.assertEqual([x["shared"] for x in q], ["school", "city"])
        for x in q:
            self.assertTrue(x["google"].startswith("https://www.google.com/search"))
            self.assertIn('site:linkedin.com/in "Acme" "data analytics"', x["query"])

    def thread(self, *msgs, **kw):
        o = {"contact_id": "c", "channel": "linkedin", "status": "sent",
             "messages": [{"date": d, "direction": dr, "text": t} for d, dr, t in msgs]}
        o.update(kw)
        return o

    def test_ask_nudged_once_then_stop(self):
        base = [("2026-10-01", "out", "note"), ("2026-10-05", "in", "happy to chat"), ("2026-10-06", "out", "ask")]
        t = self.thread(*base, stage="ask")
        self.assertEqual(self.f.thread_state(t, {"name": "X"}, D(2026, 10, 9))[0], "WAITING")
        g, m = self.f.thread_state(t, {"name": "X"}, D(2026, 10, 13))
        self.assertEqual(g, "DUE NOW")
        self.assertIn("nudge", m)
        t = self.thread(*base, ("2026-10-13", "out", "nudge"), stage="nudge")
        self.assertEqual(self.f.thread_state(t, {"name": "X"}, D(2026, 10, 20))[0], "STOPPED")
