"""The pack's shape: every skill complete, within the Claude app's limits, with the same consent section."""

import glob
import json
import os
import re
import unittest

from _load import ROOT

SKILLS = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
CONSENT = open(os.path.join(ROOT, "CONSENT.md"), encoding="utf-8").read().strip()


def front(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return dict(line.split(": ", 1) for line in m.group(1).splitlines()) if m else {}


class Repo(unittest.TestCase):
    def test_seventeen_skills(self):
        self.assertEqual(len(SKILLS), 17)

    def test_frontmatter(self):
        for p in SKILLS:
            fm = front(open(p, encoding="utf-8").read())
            folder = os.path.basename(os.path.dirname(p))
            self.assertEqual(fm.get("name"), folder, p)
            self.assertRegex(fm["name"], r"^[a-z0-9-]{1,64}$")
            d = fm.get("description", "")
            self.assertTrue(0 < len(d) <= 200, "%s: description is %d characters" % (folder, len(d)))
            self.assertNotRegex(d, r"[<>]")

    def test_size_and_sections(self):
        for p in SKILLS:
            text = open(p, encoding="utf-8").read()
            self.assertLess(text.count("\n"), 300, p)
            for h in ("## Reads and writes", "## Example", "## What it never does", "## Consent and safety"):
                self.assertTrue(h in text, "%s lacks %s" % (os.path.basename(os.path.dirname(p)), h))

    def test_consent_identical(self):
        for p in SKILLS:
            text = open(p, encoding="utf-8").read()
            self.assertTrue(CONSENT in text, p)
            self.assertNotIn("{{CONSENT}}", text)

    def test_scripts_mentioned_exist(self):
        for p in SKILLS:
            folder = os.path.dirname(p)
            for script in re.findall(r'\$SKILL_DIR/([\w.-]+\.py)', open(p, encoding="utf-8").read()):
                self.assertTrue(os.path.exists(os.path.join(folder, script)), "%s: %s missing" % (p, script))

    def test_every_script_has_help(self):
        for py in glob.glob(os.path.join(ROOT, "skills", "*", "*.py")) + glob.glob(os.path.join(ROOT, "hooks", "*.py")):
            src = open(py, encoding="utf-8").read()
            self.assertTrue(src.lstrip().startswith(('#!/usr/bin/env python3', '"""', '# Adapted from')), py)

    def test_manifests(self):
        for f in ("plugin.json", "marketplace.json"):
            json.load(open(os.path.join(ROOT, ".claude-plugin", f), encoding="utf-8"))

    def test_example_prefs_parse(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("s", os.path.join(ROOT, "skills", "job-scout", "score.py"))
        s = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(s)
        s.read_prefs(os.path.join(ROOT, "examples", "PREFERENCES_AND_SCORING.example.md"))

    def test_credits(self):
        lic = open(os.path.join(ROOT, "LICENSE"), encoding="utf-8").read()
        for who in ("Jake Schincariol", "Jake Gutierrez", "Siqi Chen", "Alex Wang", "Mads Lorentzen",
                    "doany.ai", "Matt Pocock", "Jesse Vincent", "Santiago"):
            self.assertIn(who, lic)


if __name__ == "__main__":
    unittest.main()
