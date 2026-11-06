# Changelog

Versions of the pack. Update to a version, not to whatever is newest, and read
what changed first.

## 1.9.1 (2026-11-06)
- Graduate job sites in job-scout: Milkround, Graduate Recruitment Bureau and
  Higherin (formerly RateMyPlacement) for the UK, alongside gradireland,
  through their email job alerts; each job verified on the employer's page.
  An optional update gives the person the exact saved searches to set up.

## 1.9.0 (2026-11-06)
The pack now covers the nine common uses of AI in a job search (find real
jobs, positioning, CV and letter, applying, emailing hiring managers,
referrals, a portfolio site, interview prep, switching careers):
- New add-on skill, job-portfolio: a one-page portfolio site from
  EVIDENCE.md (case studies with real results and proof), checked by
  `portfolio_check.py` (numbers from the evidence, no private details, alt
  text, readable on a phone, no tracking), published where the person chooses
  with their yes.
- New add-on skill, job-switch: `switch_map.py` maps each requirement of the
  target role (from real ads) to the person's evidence (STRONG, PARTIAL,
  GAP, each quoting its evidence), then bridge roles, a gap plan with the
  quickest credible proof, a checked 'why I'm switching' story, a reframed
  CV and chats with people who made the same switch.
- Applying: the batch apply session fills each queued form in turn while the
  person watches; they press Submit and say "next". Claude never submits.
- 17 skills.

## 1.8.3 (2026-11-06)
- Who to contact, best for the role first (`network.py rank`): the likely
  hiring manager, senior people on the team, the team, then a recruiter;
  shared school, city or past employer and an existing connection only break
  ties. Each person comes with the first step (message, connection request
  with a note, or an email for the hiring manager).
- The referral search on the person's computer now covers every new job,
  not only jobs where they know nobody, and is set up with the other
  automatic tasks.

## 1.8.2 (2026-11-06)
Referrals, after a live check of the person's job list found 15 jobs, an
empty contacts table, and connections at 9 of the 15 companies that had never
been surfaced (referral finding waited for packs, and packs wait for alerts):
- `network.py match` (job-connector) ranks the person's connections at each
  job's company for a referral (same function or go-to-market team, possible
  hiring managers, recruiters, known ties) and runs for every job that passes
  the gates, right after scoring; alerts show "People you know" for every job.
- `outreach.py manager` reads the hiring manager's title from the ad
  ("reports to ...").
- Claude's own web search doesn't find people (tested), and cloud runs have no
  browser, so the people search runs as an optional scheduled task on the
  person's computer, in the desktop app's browser, reading Google's results
  only, never LinkedIn; it stops at a CAPTCHA.
- Update check: matching runs automatically for existing jobs; the computer
  task is optional, with the person's OK.

## 1.8.1 (2026-11-04)
Fixes from the first scheduled run (watched companies, 2026-11-04):
- Web fetch returned summaries, and the Stripe, Intercom and an Ashby feed
  came back cut off. `feeds.py shortlist` now reads the light list (titles,
  places, dates), keeps the matches and fetches each full ad on its own
  (`feeds.py job`, about 7 KB), so the posting check runs on the real ad; a
  list short of its own total is reported as partly checked. Optional update:
  let the sandbox reach the hiring systems (Settings > Capabilities > Allowed
  websites), so feeds are read directly.
- Coverage: every watched company gets 'checked: <how>' or 'not checked:
  <reason>' in the run log (`pipeline.py coverage`); no source is skipped
  silently. Companies without a feed are searched through Job Seek, Indeed
  and email alerts.
- The apply list: "apply to these" from anywhere adds them (`pipeline.py
  queue`); the next daily search prepares the pack, the form's questions with
  draft answers and referral drafts; the next live session fills the forms
  and the person presses Submit.
- An employer's request that AI agents not apply is reported (`posting_guard`
  `ai_opt_out`, `apply_form.py` note), never followed as an instruction and
  never changes the score; filling the form is the person's call, and they
  press Submit.
- Weekly: `funnel.py thresholds` suggests a recalibration when 10+ jobs are
  scored and none reach the alert thresholds.

## 1.8.0 (2026-11-04)
Ideas from the best-rated job-search, interview and career repositories on
GitHub, and automatic updates:
- Updates: job-weekly's `update_check.py` compares the installed version with
  `updates.json` on GitHub (information only; nothing from GitHub is run).
  Setup changes that need nothing from the person happen automatically and
  are reported; anything that needs the person (information, a click, a
  decision) is optional, shown once with what it helps with and what it
  needs, then approved or declined. Installed from GitHub with 'Sync
  automatically' on, new versions arrive by themselves (tested in the Claude
  app on 2026-11-04). Say "check for updates" any time.
- Install from GitHub: Customize > Plugins > Add marketplace > Add from a
  repository > hantcd/job-search-assistant, with automatic sync. Now the
  guide's main install route; uploading the zip still works.
- Job Seek (jseek.co) as an optional job source: a free connector over
  thousands of employers' own career pages (tested from Dublin).
- Interviews: a debrief after each real interview (`debrief.py`) feeding a
  question bank; a one-page proof pack before each round (`proofpack.py`:
  three proofs quoted from EVIDENCE.md, three real gaps, 3-5 stories, ten
  follow-ups, a 30-minute plan); strong-vs-weak answer comparisons; company
  values in the story grid, with an opening line per theme; links to the
  Tech Interview Handbook, System Design Primer and Coding Interview
  University for technical roles.
- CVs: the truth check flags ownership verbs stronger than the evidence
  ('led' for 'contributed to'), fails 'published' for work under review, and
  fails corrected mistakes that come back (CORRECTIONS.md).
- Offers: ask, accept and walk-away lines set before any call
  (`offer.py lines`), and a negotiation rehearsal with recruiter pushback.
- Applications by email (`outreach.py check --stage application`), and a
  fresh-chat review where no separate reviewer agent can run.
- From: claude-resume-kit, InterviewThread, interview-skills,
  swe-interview-coach, JobSync, offer-toolkit-skill, behavior-question-skill,
  Dossier, linkedin-skills (install steps) and Job Seek. Ideas only; none of
  their text is used.

## 1.7.0 (2026-11-04)
Referral lessons from a short referral kit (10x.with.ai's REFER kit):
- Finding people through Google: `outreach.py find` builds searches like
  `site:linkedin.com/in "Acme" "data analytics" "Trinity College Dublin"`,
  read on Google's own page in the person's browser while they watch, never
  on linkedin.com. Claude's own web search doesn't honour `site:` reliably
  (tested: one or two profiles in 20 results), so automatic tasks list the
  links instead.
- Each contact is UNVERIFIED until the person opens the profile and confirms
  they still work there (`employer_checked`).
- `pipeline.py contact-check` runs before any draft: STOP for do-not-contact;
  CHECK for an unverified employer, a link to a rejected application, or a
  recruiter at a company that rejected the person in the last 180 days.
  `move ... rejected` now records the date.
- The referral path, one step and one yes at a time (outreach `stage`): note,
  thank-you with a 10-minute ask, chat, the referral ask, one nudge.
  `outreach.py check --stage ask` needs the job link, an easy way to say no
  and at most 3 'why I fit' lines; job-followup allows one nudge after 5
  working days, then stops.
- Notes mentioning their post, talk or school are flagged for the person to
  confirm; out of personalised notes, connect without one and message after
  they accept.
- The Ashby referral figures (40% of referred candidates reach interview,
  3% of those who apply alone) now open job-connector, the README and the
  guide, with "Claude drafts. You send."
- New rules eval: rule-referral-checks.

## Guide update (2026-11-03)
- Screenshots of every Claude screen the guide sends you to, with the button
  to press marked in red: new project, the project page, Create and edit
  files, memory, uploading the pack, connectors, attaching your documents,
  saving files to the project, the instructions box and Scheduled. Personal
  details are blurred.
- Paths updated to the current Claude app: connectors are under Customize >
  Connectors; the pack installs in one go with Customize > Plugins > Upload
  plugin; the switch to check is Create and edit files; web search has no
  switch.
- How to keep the project separate from your other chats' memory.
- Step 2 adds your whole documents folder to the project (Context > Add >
  Upload from device > Folder), since a chat takes at most 20 files at a time;
  unzip the LinkedIn export into the folder first.

## 1.6.1 (2026-11-03)
Checked live from Ireland, through the person's own browser:
- Indeed's connector covers Ireland. It has no date filter and mixes in loosely
  related titles, and its job ids work only in one session, so job-scout
  filters by posted date and saves the job's link instead of its id;
  job-research quotes Indeed's small sample sizes.
- LinkedIn's logged-out search returned 10 jobs from the last 24 hours, one
  with a job id 70 million below the rest, shown as "9 hours ago": a repost
  with no "Reposted" label. linkedin_jobs.py now drops ids far below the rest
  of the same search, so reposts are caught on the first run.
- Greenhouse, Lever and Ashby APIs matched the scripts. Fixes: Ashby's
  isRemote is true on hybrid roles, so its workplaceType now wins; EU-hosted
  Lever jobs keep their EU application address.
- A real Greenhouse form uses custom drop-downs, file fields labelled only
  "Attach" and an invisible reCAPTCHA. apply_form.py now picks drop-down
  options by clicking the matching one, tells the CV and letter fields apart
  by their ids, and skips hidden helper inputs. answers.py now leaves
  data-protection acknowledgements to the person, and fills "How did you hear
  about this job?" and "current company" from the person's files.
- Hooks find Python as python3, python or py (Windows); if none is found,
  sending stays blocked.
- A quick start at the top of the README.

## 1.6.0 (2026-11-03)
- Greenhouse, Lever and Ashby: `feeds.py live` asks the hiring system whether
  a job is still open (only a 404, 410 or a job gone from the board counts as
  closed); `feeds.py questions` lists a Greenhouse job's exact application
  questions from its public API for `answers.py`; `detect` gives each job's
  application form. `apply_form.py` opens Lever and Ashby jobs at their
  application form, attaches the CV before typing (these systems fill fields
  from it), and fills a single 'Full name' field.
- answers.py: marketing opt-ins ('email me about future openings'), export
  control and 'have you worked here before' questions are the person's.
- Mock interviews: set-up in one round (round, full or focused, practice or
  real, pressure only if asked), the interviewer from the invite and company
  notes, a five-step follow-up chain on every result, five scores, a report
  with three fixes, and `mock.py` to check reports (no invented numbers in
  coaching) and show progress. New `invite.py` reads an invite's .ics: time
  in the person's zone, length, meeting link and the named panel.
- Ideas from career-ops (MIT) and greenroom's mock-interview.

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
