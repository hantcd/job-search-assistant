# Changelog

Versions of the pack. Update to a version, not to whatever is newest, and read
what changed first.

## 1.3.1 (2026-11-02)
- The setup guide is now in the repository: GUIDE.md to read on GitHub, and
  GUIDE.pdf to download or print. Its install step links to this repository's
  releases.
- A README written for job seekers: what it does, what you need, and the
  setup step by step. The technical reference moved to TECHNICAL.md.

## 1.3.0 (2026-10-27)
- New skill, job-reddit: threads where the person can genuinely help or
  someone is hiring, short honest drafts the person posts by hand,
  `reddit_check.py` for drafts and the weekly limit. Adapted from
  reddit-automation (MIT, doany.ai).
- Job-board connectors: Indeed's official connector (and ZipRecruiter or Dice
  for US roles) in job-scout, job-research and job-offer, instead of email
  alerts where connected.
- Agents (Cowork and Claude Code): posting-reader (read-only, the only agent
  that reads ad text), hiring-manager-reviewer (read-only) and fact-checker.
- Hooks (Cowork and Claude Code): sending, replying, forwarding and posting
  blocked (drafts still work; a setting turns it off); the job list checked
  after every write; the posting check run on every page, ad and email read.
- Evals for `claude plugin eval`: a trigger case per skill and seven cases
  where the person asks Claude to break a rule.
- Question rounds, with a recommended answer for each question, wherever a
  skill interviews the person. Adapted from Matt Pocock's grilling skill (MIT).
- Consent section: Reddit replies are posted by the person; hooks block
  sending where they run.

## 1.2.0 (2026-10-21)
- job-scout: posting integrity check on every ad (hidden text, invisible and tag
  characters, look-alike letters, lines aimed at an AI); one robots-checked
  retry after a 403; opt-in LinkedIn public listings reader; eligibility and
  language gates; unreachable ads closed only after 3 failures over 48+ hours.
- job-cv: ATS parse check; orphaned entry titles and early page breaks;
  relevance-weighted cutting.
- job-apply: archive of the ad and the exact CV and letter sent; a fresh
  reviewer where one is available.
- job-interview: prep from the archived application and earlier rounds.
- job-tracker: email tracker cites its source email and processes each once;
  CSV export can't run formulas.
- Consent section: LinkedIn listings exception (opt-in) and the robots rule.
- From ai-job-search (MIT, Mads Lorentzen).

## 1.1.0 (2026-10-18)
- Company caps and per-person limits, mid-interview hold, hidden-gate checks,
  form read-back, browser hygiene, application records, LaTeX escape and
  conversion checks, letter overlap, about 260 verified boards. From
  please-hire-me (MIT, Alex Wang).

## 1.0.0 (2026-10-17)
- Thirteen skills with scripts and tests, built from the guide's rules in
  hunter-skill's one-skill-per-job structure (MIT, Jake Schincariol).
