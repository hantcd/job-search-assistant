# Changelog

Versions of the pack. Update to a version, not to whatever is newest, and read
what changed first.

## 1.5.0 (2026-11-03)
- New skill, job-chief: runs the whole search as one ongoing goal in Claude
  Code or Cowork, with subagents for the work (side by side only when
  independent; job list writes one at a time), a dated wiki of decisions and
  lessons, and `wiki_check.py` to lint it. Adapted from Matt Pocock's
  chief-of-staff and obra/superpowers' dispatching-parallel-agents (MIT).
- Evidence before claims, in every skill's rules: nothing is called ready or
  passing without running its check in that session and showing the result.
  Adapted from superpowers' verification-before-completion (MIT).
- "Other skills it uses (if installed)" in eight skills: Claude's document
  skills (Word, PDF, Excel, PowerPoint), last30days, superpowers and
  skill-creator, each with its limits and a fallback.

## 1.4.0 (2026-11-03)
- LinkedIn listings (still opt-in): the last 24 hours, newest first, reposts
  dropped. A repost is caught by its 'Reposted' label, by its job id (a repost
  keeps the first listing's id; the job list saves the highest id seen each
  day) and by the same role found 2+ days earlier; each drop is logged.
- Applying on the company's own site, not LinkedIn Easy Apply or a board's
  quick apply. New `apply_form.py`: Playwright fills the form in a visible
  window, attaches the CV, reads every value back, saves a screenshot and
  stops at Submit. It never clicks a button or presses Enter, never types a
  password, leaves eligibility and salary questions to the person, and stops
  at a login or CAPTCHA.
- New sources: Welcome to the Jungle and Handshake (job alert emails and
  pastes; reading their job pages is a separate opt-in, as their terms forbid
  scraping) and Jack & Jill (its match emails). New `jobposting.py` reads an
  employer's own structured job data from any job page.
- Consent section: the Welcome to the Jungle and Handshake opt-in.

## 1.3.1 (2026-11-02)
- The setup guide is now in the repository: GUIDE.md to read on GitHub, and
  GUIDE.pdf to download or print. Its install step links straight to the skill
  pack download.
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
