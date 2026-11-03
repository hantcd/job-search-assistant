#!/usr/bin/env python3
"""Fill a job application form on the company's own site with Playwright, and stop at Submit.

    python3 apply_form.py scan URL [--out form.json]
    python3 apply_form.py fill URL --answers answers.json [--cv cv.pdf] [--letter letter.pdf]
                          [--profile ~/.job-search-browser] [--readback filled.json] [--shot form.png]
                          [--headless] [--no-wait]

scan   lists the form's questions (label, type, required, options, max_length)
       as form.json, which answers.py sorts into FILL, DRAFT and YOU. It also
       reports a login wall or a CAPTCHA.
fill   opens the form in a visible browser on the person's computer, fills it
       from answers.json, attaches the CV (and letter), reads every value back
       from the page, saves filled.json for `answers.py lengths` and a
       screenshot, and then waits with the browser open. The person checks the
       form and clicks Submit themselves, then closes the window.

answers.json: [{"label": "First name", "answer": "Aoife"}, ...]. An answer to a
YOU question (eligibility, sponsorship, salary, diversity, health, declarations:
see answers.py) is filled only if the row says "from_person": true, meaning the
person gave that exact answer. Questions with no answer are left empty.

What it never does: click Submit or any other button, press Enter, type into a
password field, solve or get round a CAPTCHA, or leave the company's own site.
If the page asks for a login, it stops and asks the person to log in in the
open window (the browser profile keeps them logged in for next time). Custom
widgets it can't fill are listed for the person to do by hand.

Needs Playwright (`pip install playwright` then `playwright install chromium`).
Runs on the person's own computer (Claude Code), where they can see the window;
in the Claude app, use Claude in Chrome or the built-in browser instead.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import answers as answer_rules  # noqa: E402

COLLECT = r"""
() => {
  const out = [];
  const seen = new Set();
  const textOf = el => (el ? el.innerText || el.textContent || '' : '').replace(/\s+/g, ' ').trim();
  function labelFor(el) {
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
    const by = el.getAttribute('aria-labelledby');
    if (by) return by.split(/\s+/).map(id => textOf(document.getElementById(id))).join(' ');
    if (el.id) { const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]'); if (l) return textOf(l); }
    const wrap = el.closest('label'); if (wrap) return textOf(wrap);
    const fs = el.closest('fieldset'); if (fs && fs.querySelector('legend')) return textOf(fs.querySelector('legend'));
    return el.getAttribute('placeholder') || el.getAttribute('name') || '';
  }
  const els = document.querySelectorAll('input, select, textarea');
  els.forEach((el, i) => {
    const type = (el.tagName === 'SELECT') ? 'select' : (el.tagName === 'TEXTAREA') ? 'textarea' : (el.type || 'text');
    if (['hidden', 'submit', 'button', 'reset', 'image'].includes(type)) return;
    el.setAttribute('data-jsa', String(i));
    let label = labelFor(el);
    if (type === 'radio') {
      const fs = el.closest('fieldset');
      const group = fs && fs.querySelector('legend') ? textOf(fs.querySelector('legend')) : el.name;
      const key = 'radio:' + el.name;
      const own = el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      const optionText = own ? textOf(own) : (el.closest('label') ? textOf(el.closest('label')) : el.value);
      if (seen.has(key)) { out.find(o => o.key === key).options.push({text: optionText, sel: '[data-jsa="' + i + '"]'}); return; }
      seen.add(key);
      out.push({key, label: group, type: 'radio', required: el.required, options: [{text: optionText, sel: '[data-jsa="' + i + '"]'}], sel: null});
      return;
    }
    const opts = type === 'select' ? Array.from(el.options).map(o => o.text.trim()).filter(Boolean) : undefined;
    const max = el.maxLength && el.maxLength > 0 ? el.maxLength : undefined;
    out.push({key: 'f' + i, label: label, type, required: el.required || el.getAttribute('aria-required') === 'true',
              options: opts, max_length: max, sel: '[data-jsa="' + i + '"]', name: el.name || ''});
  });
  return out;
}
"""

CAPTCHA = re.compile(r"recaptcha|hcaptcha|turnstile|challenges\.cloudflare|captcha", re.I)
FILE_CV = re.compile(r"resume|résumé|\bcv\b|curriculum", re.I)
FILE_LETTER = re.compile(r"cover", re.I)
YES = re.compile(r"^(yes|true|y|1|checked|agree)$", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower().replace("*", "")).strip()


def match(label, answers):
    """The answer row for this field's label, or None."""
    n = norm(label)
    if not n:
        return None
    for a in answers:
        if norm(a.get("label")) == n:
            return a
    for a in answers:
        al = norm(a.get("label"))
        if al and (al in n or n in al) and min(len(al), len(n)) >= 4:
            return a
    return None


def category(label):
    got = answer_rules.classify(label)
    return got[0] if isinstance(got, (tuple, list)) else got


def page_state(page):
    """'login' if a password field is showing, 'captcha' if a CAPTCHA is on the page, else ''."""
    if page.locator("input[type=password]").count():
        return "login"
    frames = " ".join(f.url for f in page.frames)
    html = page.content()[:400000]
    if CAPTCHA.search(frames) or re.search(r'class="[^"]*(g-recaptcha|h-captcha|cf-turnstile)', html):
        return "captcha"
    return ""


def scan(page):
    fields = page.evaluate(COLLECT)
    out = []
    for f in fields:
        row = {"label": f["label"], "type": f["type"], "required": bool(f["required"])}
        if f.get("options"):
            row["options"] = [o["text"] if isinstance(o, dict) else o for o in f["options"]]
        if f.get("max_length"):
            row["max_length"] = f["max_length"]
        out.append(row)
    return fields, out


def fill(page, answers, cv=None, letter=None):
    """Fill what can be filled. Returns (report rows, readback rows)."""
    fields = page.evaluate(COLLECT)
    report, readback = [], []
    for f in fields:
        label, typ = f["label"], f["type"]
        if typ == "password":
            report.append(("SKIP", label, "password: the person types it"))
            continue
        if typ == "file":
            path = letter if FILE_LETTER.search(label) else cv
            if path:
                page.set_input_files(f["sel"], path)
                report.append(("FILLED", label, os.path.basename(path)))
            else:
                report.append(("EMPTY", label, "no file given"))
            continue
        a = match(label, answers)
        if a is None or a.get("answer") in (None, ""):
            report.append(("EMPTY", label, "required: needs an answer" if f["required"] else "no answer"))
            continue
        cat = category(label)
        if cat in ("YOU", "SKIP-PASSWORD") and not a.get("from_person"):
            report.append(("LEFT", label, "%s question: only the person answers" % cat))
            continue
        value = str(a["answer"])
        try:
            if typ == "select":
                try:
                    page.select_option(f["sel"], label=value)
                except Exception:
                    page.select_option(f["sel"], value=value)
            elif typ == "radio":
                choice = next((o for o in f["options"] if norm(o["text"]) == norm(value)), None)
                if not choice:
                    report.append(("EMPTY", label, "no option called %r" % value))
                    continue
                page.check(choice["sel"])
            elif typ == "checkbox":
                if YES.match(value):
                    page.check(f["sel"])
                else:
                    page.uncheck(f["sel"])
            else:
                page.fill(f["sel"], value)
            report.append(("FILLED", label, value[:60]))
        except Exception as exc:  # custom widgets, hidden inputs
            report.append(("BY HAND", label, "couldn't fill (%s): do it by hand" % type(exc).__name__))
    return report, read_back(page)


def problems(readback, answers):
    """Read-back checks: required fields empty, values that don't match the pack, text cut off."""
    out = []
    for r in readback:
        if r["required"] and not str(r["answer"]).strip():
            out.append("required and empty: %s" % r["label"])
        a = match(r["label"], answers)
        if a and r["answer"] and a.get("answer") and norm(r["answer"]) != norm(str(a["answer"])) \
                and not r.get("max_length"):
            out.append("page shows %r for %s, the pack says %r" % (r["answer"][:40], r["label"], str(a["answer"])[:40]))
        if r.get("max_length") and a and len(str(a.get("answer", ""))) > r["max_length"]:
            out.append("cut off at %d characters: %s" % (r["max_length"], r["label"]))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("url")
    s.add_argument("--out")
    s.add_argument("--profile")
    f = sub.add_parser("fill")
    f.add_argument("url")
    f.add_argument("--answers", required=True)
    f.add_argument("--cv")
    f.add_argument("--letter")
    f.add_argument("--profile", default=os.path.expanduser("~/.job-search-browser"))
    f.add_argument("--readback", default="filled.json")
    f.add_argument("--shot", default="form.png")
    f.add_argument("--headless", action="store_true", help="for tests only: the person can't see or submit")
    f.add_argument("--no-wait", action="store_true", help="close the browser when done instead of waiting")
    a = p.parse_args(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright isn't installed: pip install playwright, then: playwright install chromium", file=sys.stderr)
        return 2
    with sync_playwright() as pw:
        headless = a.cmd == "scan" or a.headless
        if a.profile and a.cmd == "fill":
            ctx = pw.chromium.launch_persistent_context(a.profile, headless=headless)
        else:
            ctx = pw.chromium.launch(headless=headless).new_context()
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(a.url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)  # forms that build themselves after load
        state = page_state(page)
        if a.cmd == "scan":
            _, rows = scan(page)
            text = json.dumps(rows, indent=1, ensure_ascii=False)
            if a.out:
                open(a.out, "w", encoding="utf-8").write(text)
            print(text)
            if state:
                print("NOTE: %s on this page" % state, file=sys.stderr)
            ctx.close()
            return 0
        if state == "login":
            print("STOP: this form needs a login. Ask the person to log in in the open window "
                  "(Claude never types passwords), then run fill again.", file=sys.stderr)
            if not a.headless and not a.no_wait:
                page.wait_for_event("close", timeout=0)
            ctx.close()
            return 3
        answers = json.load(open(a.answers, encoding="utf-8"))
        report, readback = fill(page, answers, a.cv, a.letter)
        page.wait_for_timeout(1000)  # some forms clear fields typed while loading: read back after a pause
        readback = read_back(page)
        open(a.readback, "w", encoding="utf-8").write(json.dumps(readback, indent=1, ensure_ascii=False))
        page.screenshot(path=a.shot, full_page=True)
        for status, label, detail in report:
            print("%-8s %-40s %s" % (status, label[:40], detail))
        issues = problems(readback, answers)
        for i in issues:
            print("CHECK    " + i)
        if state == "captcha":
            print("NOTE     there's a CAPTCHA: the person completes it, never Claude")
        print("STOPPED AT SUBMIT. Nothing was submitted. The person checks the form, then clicks Submit "
              "themselves.")
        if not a.headless and not a.no_wait:
            page.wait_for_event("close", timeout=0)
        ctx.close()
        return 1 if issues else 0


def read_back(page):
    """Every value as the page now shows it (some widgets show a value that isn't saved)."""
    rows = []
    for f in page.evaluate(COLLECT):
        if f["type"] in ("password", "file"):
            continue
        if f["type"] == "radio":
            picked = [o["text"] for o in f["options"] if page.is_checked(o["sel"])]
            val = picked[0] if picked else ""
        elif f["type"] == "checkbox":
            val = "yes" if page.is_checked(f["sel"]) else ""
        elif f["type"] == "select":
            val = page.eval_on_selector(f["sel"], "el => el.selectedOptions.length ? el.selectedOptions[0].text : ''")
        else:
            val = page.input_value(f["sel"])
        rows.append({"label": f["label"], "answer": val, "max_length": f.get("max_length") or 0,
                     "required": bool(f["required"])})
    return rows


if __name__ == "__main__":
    sys.exit(main())
