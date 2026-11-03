"""Fresh LinkedIn listings, employers' job data, and the Playwright form filler."""

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest

from _load import ROOT, fixture, load

D = dt.date


class FreshLinkedIn(unittest.TestCase):
    l = load("job-scout", "linkedin_jobs")

    def test_newest_first_last_24_hours(self):
        u = self.l.search_url("data analyst", "Ireland", days=1)
        self.assertIn("sortBy=DD", u)
        self.assertIn("f_TPR=r86400", u)

    def test_reposted_label(self):
        d = self.l.parse_detail(open(fixture("job-scout", "linkedin_reposted.html"), encoding="utf-8").read(), "4400000001")
        self.assertTrue(d["reposted"])
        self.assertEqual(d["posted_text"], "Reposted 3 hours ago")
        d = self.l.parse_detail(open(fixture("job-scout", "linkedin_detail.html"), encoding="utf-8").read(), "4345841651")
        self.assertFalse(d["reposted"])

    def test_old_id_is_a_repost(self):
        anchors = [{"date": "2026-10-30", "max_id": 4430000000}, {"date": "2026-11-02", "max_id": 4440000000}]
        old = {"ref": "linkedin:4425000000", "company": "Acme Ltd", "title": "Analyst"}
        new = {"ref": "linkedin:4441000000", "company": "Acme Ltd", "title": "Analyst"}
        today = D(2026, 11, 3)
        self.assertIn("2026-10-30", " ".join(self.l.repost_reasons(old, anchors, [], today)))
        self.assertEqual(self.l.repost_reasons(new, anchors, [], today), [])
        # an id older only than yesterday's highest isn't enough evidence
        mid = {"ref": "linkedin:4435000000", "company": "Acme Ltd", "title": "Analyst"}
        self.assertEqual(self.l.repost_reasons(mid, anchors, [], today), [])

    def test_same_role_found_earlier(self):
        jobs = [{"company": "ACME Ltd.", "title": "Junior Data Analyst", "first_found": "2026-10-20"}]
        row = {"ref": "linkedin:4441000000", "company": "Acme Ltd", "title": "Junior Data-Analyst"}
        self.assertTrue(self.l.repost_reasons(row, [], jobs, D(2026, 11, 3)))
        fresh_today = [{"company": "Acme Ltd", "title": "Junior Data Analyst", "first_found": "2026-11-03"}]
        self.assertEqual(self.l.repost_reasons(row, [], fresh_today, D(2026, 11, 3)), [])

    def test_fresh_drops_or_keeps(self):
        rows = [{"ref": "linkedin:1", "company": "A", "title": "x", "reposted": True},
                {"ref": "linkedin:2", "company": "B", "title": "y", "reposted": False}]
        kept, dropped = self.l.fresh([dict(r) for r in rows], [], [], D(2026, 11, 3))
        self.assertEqual([r["company"] for r in kept], ["B"])
        self.assertEqual(dropped[0]["repost_reasons"], ["labelled 'Reposted' on LinkedIn"])
        kept, dropped = self.l.fresh([dict(r) for r in rows], [], [], D(2026, 11, 3), keep_reposts=True)
        self.assertEqual(len(kept), 2)
        self.assertTrue(kept[0]["reposted"])

    def test_note_ids(self):
        a = self.l.note_ids([{"date": "2026-08-01", "max_id": 1}], [{"ref": "linkedin:44"}, {"ref": "linkedin:45"}],
                            D(2026, 11, 3))
        self.assertEqual(a, [{"date": "2026-11-03", "max_id": 45}])  # 60-day window drops August
        a = self.l.note_ids(a, [{"ref": "linkedin:50"}], D(2026, 11, 3))
        self.assertEqual(a, [{"date": "2026-11-03", "max_id": 50}])

    def test_cards_carry_reposted_flag(self):
        rows = self.l.parse_cards(open(fixture("job-scout", "linkedin_search.html"), encoding="utf-8").read())
        self.assertTrue(all("reposted" in r and "posted_text" in r for r in rows))

    def test_cli_saves_ids_to_the_job_list(self):
        with tempfile.TemporaryDirectory() as d:
            jl = os.path.join(d, "pipeline.json")
            json.dump({"jobs": [], "linkedin_ids": []}, open(jl, "w"))
            out = subprocess.run([sys.executable, os.path.join(ROOT, "skills", "job-scout", "linkedin_jobs.py"),
                                  "search", "-l", "Ireland", "--from-file",
                                  fixture("job-scout", "linkedin_search.html"), "--joblist", jl,
                                  "--today", "2026-07-10"], capture_output=True, text=True)
            self.assertEqual(len(json.loads(out.stdout)), 2)


class EmployerJobData(unittest.TestCase):
    j = load("job-scout", "jobposting")

    def test_reads_jobposting(self):
        rows = self.j.jobs(open(fixture("job-scout", "jobposting.html"), encoding="utf-8").read())
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["title"], r["company"], r["posted"], r["closes"]),
                         ("Junior Data Analyst", "Acme Ltd", "2026-11-02", "2026-11-30"))
        self.assertEqual(r["pay"], "EUR 42000-48000 per year")
        self.assertEqual(r["reference"], "R-1042")
        self.assertEqual(r["remote"], "remote")
        self.assertIn("Power BI", r["description"])
        self.assertNotIn("<", r["description"])

    def test_no_data(self):
        self.assertEqual(self.j.jobs("<html><body>No structured data</body></html>"), [])
        self.assertEqual(self.j.jobs('<script type="application/ld+json">{not json</script>'), [])


try:
    import playwright.sync_api  # noqa: F401
    HAVE_PLAYWRIGHT = True
except ImportError:
    HAVE_PLAYWRIGHT = False


@unittest.skipUnless(HAVE_PLAYWRIGHT, "Playwright isn't installed")
class FormFiller(unittest.TestCase):
    SCRIPT = os.path.join(ROOT, "skills", "job-apply", "apply_form.py")

    def run_fill(self, page, d):
        return subprocess.run([sys.executable, self.SCRIPT, "fill", "file://" + fixture("job-apply", page),
                               "--answers", fixture("job-apply", "answers.json"), "--cv", fixture("job-apply", "cv.pdf"),
                               "--headless", "--no-wait", "--profile", "",
                               "--readback", os.path.join(d, "filled.json"), "--shot", os.path.join(d, "form.png")],
                              capture_output=True, text=True, timeout=120)

    def test_fills_reads_back_and_stops_at_submit(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.run_fill("form.html", d)
            got = {r["label"].rstrip(" *"): r["answer"] for r in json.load(open(os.path.join(d, "filled.json")))}
            self.assertEqual(got["First name"], "Aoife")
            self.assertEqual(got["How did you hear about us?"], "Company website")
            self.assertEqual(got["I have read the privacy notice"], "yes")  # the person's own answer
            # YOU questions stay empty: sponsorship and current salary are the person's
            self.assertEqual(got["Do you require visa sponsorship to work in Ireland?"], "")
            self.assertEqual(got["What is your current salary?"], "")
            self.assertIn("STOPPED AT SUBMIT", out.stdout)
            self.assertIn("required and empty: Do you require visa sponsorship", out.stdout)
            self.assertEqual(out.returncode, 1)  # a required field is still the person's to answer
            self.assertTrue(os.path.exists(os.path.join(d, "form.png")))

    def test_never_submits(self):
        from playwright.sync_api import sync_playwright
        mod = load("job-apply", "apply_form")
        answers = json.load(open(fixture("job-apply", "answers.json")))
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            page = b.new_page()
            url = "file://" + fixture("job-apply", "form.html")
            page.goto(url)
            mod.fill(page, answers, fixture("job-apply", "cv.pdf"))
            page.wait_for_timeout(300)
            self.assertEqual(page.url, url)
            self.assertNotEqual(page.title(), "SUBMITTED")
            b.close()

    def test_login_wall_stops(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.run_fill("login.html", d)
            self.assertEqual(out.returncode, 3)
            self.assertIn("needs a login", out.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, "filled.json")))

    def test_captcha_noted(self):
        from playwright.sync_api import sync_playwright
        mod = load("job-apply", "apply_form")
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            page = b.new_page()
            page.goto("file://" + fixture("job-apply", "captcha.html"))
            self.assertEqual(mod.page_state(page), "captcha")
            page.goto("file://" + fixture("job-apply", "login.html"))
            self.assertEqual(mod.page_state(page), "login")
            b.close()

    def test_scan_lists_questions(self):
        out = subprocess.run([sys.executable, self.SCRIPT, "scan", "file://" + fixture("job-apply", "form.html")],
                             capture_output=True, text=True, timeout=120)
        rows = json.loads(out.stdout)
        labels = [r["label"] for r in rows]
        self.assertIn("Resume/CV *", labels)
        sponsor = next(r for r in rows if r["label"].startswith("Do you require visa"))
        self.assertEqual((sponsor["type"], sponsor["required"]), ("radio", True))
        why = next(r for r in rows if r["label"].startswith("Why do you"))
        self.assertEqual(why["max_length"], 255)


if __name__ == "__main__":
    unittest.main()
