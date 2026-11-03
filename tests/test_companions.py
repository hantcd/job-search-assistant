"""job-chief's wiki lint, and how skills point at other skills."""

import datetime as dt
import glob
import os
import re
import tempfile
import unittest

from _load import ROOT, load


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class Wiki(unittest.TestCase):
    w = load("job-chief", "wiki_check")
    TODAY = dt.date(2026, 11, 3)

    def status(self, results):
        return {(s, page) for s, page, _ in results}

    def test_clean_wiki_passes(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "index.md", "# Wiki\n- [Languages](languages.md): German roles\n- [Referrals](referrals.md): routes\n")
            write(d, "languages.md", "- 2026-11-03: Aoife skips roles needing German. See [Referrals](referrals.md).\n")
            write(d, "referrals.md", "- 2026-11-03: 4 of 5 interviews came from referrals ([languages](languages.md)).\n")
            res = self.w.check(d, self.TODAY)
            self.assertEqual(res[0][0], "PASS", res)

    def test_problems_found(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "index.md", "- [A](a.md): a\n- [Gone](gone.md): missing\n")
            write(d, "a.md", "- Referrals are currently the best route.\n- 2026-01-02: an old note. Superseded.\n")
            write(d, "b.md", "- 2026-11-01: not in the index\n")
            res = self.w.check(d, self.TODAY)
            s = self.status(res)
            self.assertIn(("FAIL", "index.md"), s)  # links to gone.md
            self.assertIn(("FAIL", "b.md"), s)  # not indexed
            details = " ".join(x[2] for x in res if x[1] == "a.md")
            self.assertIn("no date", details)
            self.assertIn("superseded, but by what", details)
            self.assertIn("over 90 days old", details)

    def test_no_index(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.md", "- 2026-11-01: x\n")
            self.assertEqual(self.w.check(d, self.TODAY)[0][0], "FAIL")


class Companions(unittest.TestCase):
    KNOWN = ("docx", "pdf", "xlsx", "pptx", "last30days", "skill-creator", "superpowers", "brainstorming",
             "chief-of-staff", "dispatching-parallel-agents", "verification-before-completion", "Slides")

    def test_other_skills_sections_name_real_skills_and_a_fallback_or_rule(self):
        found = 0
        for p in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")):
            text = open(p, encoding="utf-8").read()
            m = re.search(r"## Other skills it uses \(if installed\)\n([\s\S]*?)\n## ", text)
            if not m:
                continue
            found += 1
            names = re.findall(r"\*\*([\w-]+)\*\*", m.group(1))
            self.assertTrue(names, p)
            for n in names:
                self.assertIn(n, self.KNOWN, "%s: %s" % (p, n))
        self.assertGreaterEqual(found, 8)

    def test_last30days_never_uses_accounts(self):
        text = open(os.path.join(ROOT, "skills", "job-research", "SKILL.md"), encoding="utf-8").read()
        self.assertIn("never the person's\n  X, LinkedIn or browser cookies", text)

    def test_evidence_rule_in_consent(self):
        self.assertIn("Evidence before claims", open(os.path.join(ROOT, "CONSENT.md"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
