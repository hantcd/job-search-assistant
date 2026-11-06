# Changelog

Versions of the pack. Update to a version, not to whatever is newest, and read
what changed first.

## 3.3.0 (2026-11-06)
- 'Applications a day' is a range, default 5-10 (`streak.py` reads '5-10';
  the week's bar aims at the minimum, the session stops at the maximum).
- job-weekly `funnel.py calibrate`: from the end of the first week, when
  pack-worthy jobs come in under the minimum on 4 of the last 5 planned days,
  the pack threshold drops 5 points (floor 50) and the search widens; over the
  maximum, it rises 5 (ceiling 80). One change a week, reported in one line,
  undone on request; on by default ('Auto-calibration: on'), as asked.
- Models: Sonnet for every automatic task by default; Opus only for
  complicated work Sonnet may struggle with, work it has struggled with, or
  re-checking a task it got wrong.

## 3.2.0 (2026-11-06)
Maximum results in as few clicks as possible.
- job-followup `today.py`: one bundle per queued job, best first, up to the
  plan's 'Applications a day' (default 10). Pass 1 in the chat: the
  application (its preview: every answer, file and declaration) and emails
  to the two hiring-team people, up to 16 approvals in one card; Claude
  submits and sends afterwards. Pass 2 on the page: connection requests (or
  messages) to the same two people for the best jobs within the daily cap
  (16, so about 8 jobs), a comment only where one of them posted about the
  role (`about_role`), and Submit by the person where the employer asks AI
  agents not to apply (Claude fills the fields and uploads the files). 15
  jobs fit in about 5 minutes of the person's time.
- job-followup `streak.py`: the application streak, on the person's planned
  days and time ('Session days: Mon, Tue, Wed, Thu, Fri at 08:30'). One
  application keeps it; 2 freezes to start, one earned per 10 days done,
  at most 2; earn-back with 2 applications the next planned day; milestones
  3, 7, 14, 30, 50, 100 or the person's goal; perfect streaks; the week's bar.
  `at-risk` drives the optional evening reminder. After Duolingo's published
  streak experiments.
- job-apply: the prep run keeps at least one job ready every planned day (a
  `streak_keeper` below the Fit threshold when nothing passes); job-site
  accounts are encouraged: Continue with Google, or the browser's suggested
  password, then the person clicks Create account.
- LinkedIn comments: Claude pastes the comment, the person clicks Post.

## 3.1.0 (2026-11-06)
- job-cv `depth.py` and `experience-interview.md`: the experience interview.
  `roles` scores every dated role in EVIDENCE.md and, with LinkedIn's
  Positions.csv, lists positions missing from it; a current or recent role
  (ended in the last 3 years) needs 4 facts, 2 with numbers, a result and
  its scope, and GUESSED or UNVERIFIED lines don't count. `questions` plans
  about 10 minutes, one question at a time, answered by dictation or voice
  mode: Topgrading's role walk-through, Lou Adler's accomplishment probes,
  Laszlo Bock's 'relative to Y', resume writers' questions, plus what each
  role family's hiring managers look for (`experience_questions.json`), with
  must-haves from the family's ads first. Old CVs, LinkedIn, Gmail and Drive
  are read first. Runs at setup, when a CV's requirements map shows two or
  more must-haves without evidence, and, if the person chooses, from the
  morning session (`today.py --evidence`), outside the daily time; 'Not
  now' waits 30 days (`depth.py mark`).
- job-weekly `funnel.py targets --plan MASTER_PLAN.md`: reads the 'Weekly
  targets:' line; defaults are now 1 coffee chat, 2 interviews and 5
  applications a week, and the person changes them by saying so.

## 3.0.0 (2026-11-06)
The goal: about 5 minutes a day, a calendar of chats and interviews, and the
best odds of an offer.
- job-followup `today.py`: the morning session ('Go'): bookings, replies,
  thank-yous, applications (deadline soon, then Fit), chat asks, messages
  and the connection queue, ranked by how directly each leads to a chat or
  interview and cut to the person's daily time (default 5 minutes).
- job-network `booking.py`: reply intent (BOOK, INTERVIEW, THEIR_LINK, NO,
  OTHER), 3 free slots on different weekdays from Google Calendar busy times,
  the reply, and on confirmation the event (video call, the prep card in the
  description, reminders) and its prep block.
- job-connector `outreach.py accepted`: LinkedIn's "accepted your
  invitation" emails become drafted chat asks.
- job-weekly `funnel.py targets`: from weekly chat and interview targets back
  to chat asks, connection requests and applications, using the person's
  own rates once there are 10+ (labelled starting assumptions until then).
- job-followup after each round: referrer update and value-add follow-up
  within 2 days, references briefed before a final round, other processes
  asked for their timelines once one reaches a final round or an offer.

## 2.6.0 (2026-11-06)
- job-scout `hidden.py` and `hidden_sources.json`: growing companies most
  applicants miss. Sources by country and cadence (funding news, Series A/B
  rounds, Silicon Republic, Irish Tech News, Enterprise Ireland's start-up
  directory, TechIreland's funding review, Deloitte's Fast 50 and EMEA Fast
  500, the FT 1000, the Sunday Times 100, UKTN, Tech.eu and Sifted, VC
  portfolios, Y Combinator, exhibitor and member lists, alternatives to the
  big names, own-site postings); `add` skips watched, known and 1,000+ staff
  companies; `feeds` guesses their public job feeds; `rank` scores recent
  funding, size, place, industry and open roles. Kept in the job list's
  `hidden` table; job-weekly adds about 10 a week and the daily search reads
  their feeds.
- Irish boards in access.md: RecruitIreland, JobAlert.ie, JobsIreland.ie,
  Hays Ireland (alert emails) and publicjobs.ie (public sector); Google Jobs
  read on the person's computer.
- `funnel.py report`: results by where the job was found, beside Huntr's
  2026 response rates by site (US, self-reported) as a benchmark.

## 2.5.0 (2026-11-06)
- The daily connection queue: a scheduled task on the person's computer
  builds each weekday's queue up to `outreach.py invites`' budget from Google
  results only (never opening linkedin.com), plus Monday searches for roles
  posted only on companies' own hiring systems; the person runs the 2-minute
  connection session and clicks Send.
- job-weekly "Companies most people miss": 10 growing, lesser-known companies
  a week from funding news, Enterprise Ireland's start-up directory,
  Deloitte's Fast 50 and EMEA Fast 500, the FT 1000, the Sunday Times 100,
  exhibitor and member lists, and competitors, suppliers and customers of the
  big names.
- job-cv: own your slice of team work; relative metrics; a functional title
  in brackets beside the exact official title, only for work the evidence
  shows. job-linkedin `profile_check.py limits` warns on 'Aspiring...' and
  'Seeking opportunities' headlines and on 'assisted with' and 'helped with'.

## 2.4.0 (2026-11-06)
- Connection sessions (job-connector, `finding-people.md`): people at watched,
  top and network companies, alumni and the same function first; Claude
  opens each profile in turn and prepares the request; the person clicks
  Send. `outreach.py invites` keeps to 80% of the ~100 a week accounts report
  as LinkedIn's ceiling (16 a working day, 80 in 7 days), none at weekends or
  with 250+ pending, and lists invitations pending over 3 weeks to withdraw.
  The consent rules say so in every skill. Claude still never sends in
  LinkedIn itself, and automatic tasks never act there.
- Accounts on job sites (job-apply): Claude fills the sign-up and uses the
  browser's own suggested strong password, so the password manager makes
  and saves it; Claude opens the verification email and records that the
  account exists. It never sees, types or stores a password.

## 2.3.0 (2026-11-06)
Ideas from other open-source job and LinkedIn skills (none of their text is used):
- `network.py companies`: the companies where the person knows the most
  people, not yet watched; job-weekly searches their feeds for open roles
  (Proficiently's network scan). A source, not a settings change.
- job-apply form memory: the `form_notes` table records each site's quirks
  and is read before the next form (jobautopilot's knowledge base).
- `feeds.py shortlist --seen pipeline.json` skips jobs already on the list
  before their ads are fetched (ai-job-search's seen filter).
- job-linkedin `post_check.py`: links in the body and 6+ hashtags fail; the
  hook before 'see more', length, a closing question, paragraph size and
  engagement bait are warned; each rule labelled CONFIRMED, LARGE-SCALE or
  PRACTITIONER (attainmentlabs/linkedin-algorithm-skill).
- job-research `notes_check.py` warns on a flat 'no' or 'never' without
  where it was looked for (the epistemic gate in
  backpropagation6/claude-linkedin-automation).
- Not adopted: tools that drive the person's LinkedIn account or scrape it
  (stealth-browser MCP servers, cloud invite senders, paid LinkedIn scrapers),
  and tools that create accounts or store passwords to submit applications.

## 2.2.0 (2026-11-06)
- Fallback contacts (`network.py plan`): up to 4 people per job in two
  waves, the best 2 now (one in recruiting, one on the team), the next 2
  only after 3 working days without a reply (`followup.py` flags it on
  APPLY NOW + REACH OUT threads), a different message each.
  `pipeline.py contact-check` warns at 2 people in recruiting or 2 on the
  team at one company within 2 weeks (Management Consulted's 2/2/2,
  Wonsulting's pivot to a peer).
- job-cv: "the strongest true version" of every line (the biggest verb the
  evidence supports, honest 'about' estimates the person confirms, projects
  and societies as experience); never invented titles, dates, employers,
  grades, skills or numbers. `audit.py --graduate` treats 60+ as worth
  tailoring.
- job-interview: answers to Leila Hormozi's 7 screening questions and one
  insight to teach the interviewer; job-apply: at small and founder-led
  firms, the finished work sample by default (Alex Hormozi).
- job-connector `playbooks.md`: banking (Mergers & Inquisitions), consulting
  (Management Consulted), tech (Wonsulting) and Irish/UK graduate schemes
  (Sinéad Brady, UCC Careers, ISE, Prospects).
- Comments on a post: 15+ words preferred (LinkedIn ranking research
  gathered by attainmentlabs/linkedin-algorithm-skill).

## 2.1.0 (2026-11-06)
Ideas from David DeGenova's job-search material (Post Grad Project:
davidatpgp.netlify.app and his finding-people and conversation-prep
cheat-sheets); none of his text is used.
- Three touches per person, then stop: a comment on the post where someone
  advertised the role (`outreach.py check --channel comment`: specific, under
  300 characters, no link, CV or referral ask; the person posts it by hand),
  the message, and one nudge. `followup.py` never counts a comment as a
  follow-up.
- `outreach.py linkedin`: links and filters for the searches only the person
  can run (their alumni tab, the company's People tab ending on 1st and
  2nd-degree connections, a people search); Claude never opens them.
- job-network: chat prep (research, 4-5 questions under Their story, The
  industry, Things you can do, and a closing ask, including feedback on core
  interview answers), checked by `chat_prep.py`; job-interview drafts that
  feedback email when someone agrees.
- Sources: Lios (graduate schemes, internships, spring weeks: the person
  pastes its matches; deadlines through its calendar sync) and Post Grad
  Project's H-1B exempt employer directory for people who need US
  sponsorship.

## 2.0.0 (2026-11-06)
Behaviour changes, each from the person's choices after a research pass on
referral timing and contact routes:
- **One click to apply or send.** job-apply fills the form while the person
  watches, shows every answer and declaration in an approval card, and
  submits on Approve (never where the employer asks AI agents not to apply,
  never in automatic tasks, never at a login, CAPTCHA or payment). Emails go
  from Gmail on Approve. The `no_send` hook now asks before every send (one
  click) and refuses only in LinkedIn, Handshake, Reddit and X, where the
  person clicks Send. The consent rules in every skill say so. An optional
  update asks for the person's OK first.
- **A route per job** (`network.py route`): REFERRAL FIRST only when someone
  who knows the person or their work is there, the job isn't closing within
  5 days and there's no application there in 6 months (ask today, apply
  after at most 2 working days); otherwise APPLY NOW + REACH OUT the same
  day; ALREADY APPLIED asks for a word with the recruiter. Referral messages
  drop from five steps to the ask and one nudge (`followup.py` times the
  nudge by route).
- **Recruiters and the hiring team after applying**: an after-applying note
  (`outreach.py check --stage applied`: says you applied, names the role, a
  real result, no stock enthusiasm); names from LinkedIn posts that
  advertised the role and recruiter searches (`outreach.py find --posts
  --recruiters`, read on Google only) and Handshake's recruiter lists (with
  the person present, opt-in); Handshake messages work like LinkedIn.
- **Work emails and phone numbers**: RocketReach, Apollo or Hunter through
  Orthogonal when connected, each with its source and a privacy label
  (`emails.py privacy`: contact-database and work-phone MEDIUM, mobile HIGH
  and only if the person turns phones on); never personal emails or home
  details; Claude never calls or texts. Search and timing detail moved to
  job-connector's `finding-people.md`.
- **One Fit score** (`score.py`): 60% Career Value + 40% Attainability,
  alerts at Fit 60 (old 70/40 thresholds convert to 60); `funnel.py
  thresholds --fit`.
- **Lighter setup**: chats 1 and 2 ask only the essentials (about 10
  minutes each) and the rest when it first matters; setup is 45-60 minutes.
- Fixed: an update note named a real person; it now says "the person".

## 1.10.0 (2026-11-06)
- job-cv: `audit.py`, a quick job audit for any ad: a match score out of 100
  (must-haves count double, nice-to-haves half, "X or Y" needs one), the top
  5 missing terms, and the skim's pile and top 3 red flags; Claude adds a
  strong-candidate comparison from the ad and the evidence.
- job-cv: `skim.py`, the 10-second skim: red flags strongest first (no
  target role or number in the top third, few numbers, duty openers, long
  bullets, unexplained gaps of a year or more, personal details, missing
  must-haves) and a YES, MAYBE or NO pile. Replaces the 7-second check.
- job-cover: the letter faces the biggest gap in one or two sentences with
  the true reframe; `letter_check.py --gap` warns when it doesn't, and any
  apology for a gap is flagged.
- QUICKSTART.md and a guide section: a 10-minute message for any Claude
  chat, free plan included, before setup.
- Ideas from MavGPT's AI job seekers guide; none of its text is used.

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
