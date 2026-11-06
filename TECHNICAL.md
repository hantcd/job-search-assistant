# Technical reference

For people who want to know how the skill pack works, run its scripts and tests, or use it in Claude Code. To set it up as a job seeker, start with the [README](README.md) and the [guide](GUIDE.md).

## The skill pack

Seventeen Claude skills that run a careful, personal job search: find and
score jobs, tailor true CVs and letters, reach the right people, follow up
politely, prepare for interviews and offers, and, as add-ons, build a
portfolio site and plan a career switch. Free, MIT.

It's the engine behind the guide *Build Your Own Job-Search Assistant with
Claude*. The guide's two short chats write your personal files (your evidence,
your writing style, your goals and scoring); these skills read them. Nothing
is sent or submitted without your yes.

### The seventeen skills

| skill | what it does |
|---|---|
| `job-tracker` | Keeps the job list every skill shares, checks it after every change, and says where things stand |
| `job-scout` | Finds jobs from public feeds, sites, email alerts and communities; checks each is real and open; scores it the same way every time; decides what to alert |
| `job-research` | Company notes: values, the hiring system, interview stages and reports, each labelled, linked and dated |
| `job-cv` | Achievement bank, master CV, base CVs and tailored CVs in a style preset, weighted for how they'll be read first; truth, keyword and layout checks |
| `job-cover` | Cover letters and notes in your voice; checks for truth, leftovers and AI tells |
| `job-apply` | The full application pack for one job, a hiring-manager review pass, and forms filled while you watch and submitted on your approval |
| `job-connector` | A route per job (referral first or apply now); the hiring manager, recruiter and team; work emails from connected tools; messages sent on your one-click yes; privacy checks; send times |
| `job-followup` | What's due today, inside stop rules that end a thread at the first no |
| `job-linkedin` | Your profile pack scored out of 100, posts and comments at your visibility level, and sorting messages you paste |
| `job-reddit` | Threads where you can genuinely help or someone is hiring, with short honest replies you post yourself |
| `job-interview` | Stage-by-stage prep, STAR answers from a story grid, mock interviews, thank-yous and red flags |
| `job-offer` | Pay year by year, market pay with sources, a contract read-through and a negotiation email |
| `job-weekly` | The weekly check: what the search is missing, a monthly skills gap, and what's working once there's enough data |
| `job-network` | Events and speaker calls, informational chats, and referee briefings |
| `job-portfolio` (add-on) | A one-page portfolio site from your evidence: case studies with real results and proof, checked for truth and privacy, published where you choose |
| `job-switch` (add-on) | A career-switch plan: your evidence mapped to the target role, bridge roles, the quickest credible proof for each gap, and a checked 'why I'm switching' story |
| `job-chief` | Runs the whole search as one ongoing goal in Claude Code or Cowork: subagents for the work, a dated wiki of decisions and lessons, one improvement proposed each time |

Every skill has the same shape: what it reads and writes, numbered steps, a
worked example (the same fictional graduate, Aoife Byrne, all the way
through), what it never does, and the same consent section (`CONSENT.md`).
Rules that must never slip are enforced by the scripts, not just described.

## Agents and hooks (Cowork and Claude Code)

The plugin also brings three agents and three hooks. Ordinary chats ignore
them, so the skills fall back to doing the same steps themselves.

| agent | can use | what it does |
|---|---|---|
| `posting-reader` | Read, Grep | the only agent that reads job-ad text; reports its facts with exact quotes, and has nothing to act with if an ad tries to instruct it |
| `hiring-manager-reviewer` | Read, Grep, Glob | reviews a finished pack as the hiring manager would, without having seen it drafted |
| `fact-checker` | Read, Grep, web fetch and search | checks every company fact and pay figure against its source: confirmed, contradicted, not found or out of date |

| hook | when | what it does |
|---|---|---|
| `no_send.py` | before any mail, chat or social tool | asks you before every send, reply, forward and post (one click to approve), refuses them outright in LinkedIn, Reddit and X; asks before calendar invitations to other people |
| `check_joblist.py` | after Claude writes `pipeline.json` | checks the job list at once and makes Claude fix any error |
| `flag_page.py` | after a web page, job ad or email is read | runs the posting check and quotes any hidden instructions, so they're shown to you and never followed |

The send block applies in every session while the plugin is on. To switch it
off for other work, turn off **Block sending** in the plugin's settings (or
disable the plugin). The hooks need `python3`.

## Install

**In the Claude app (web or desktop):** turn on Settings > Capabilities >
Create and edit files. Then either:
- Customize > Plugins > + Add > Add marketplace > Add from a repository >
  `hantcd/job-search-assistant`, 'Sync automatically' on, Sync; then add the
  plugin from Discover. New versions then arrive by themselves, and
  job-weekly's `update_check.py` applies the setup changes that come with
  them (automatically when they need nothing from you, as optional items
  when they do); or
- Customize > Plugins > + Add > Upload plugin, and choose
  `dist/job-search-assistant-all.zip` (it's also a plugin); or
- download this repository's skill zips (one per skill, in `dist/`) and upload
  each under Customize > Skills; or
- attach `dist/job-search-assistant-all.zip` in a chat in your Job Search
  Assistant project and say: *Install these 17 skills*. Claude offers a save
  card for each; click Save on all 17.

**In Cowork**, to get the agents and hooks as well: Customize > Plugins >
Add > Upload plugin, and choose `dist/job-search-assistant-all.zip` (it's
also a plugin).

**In Claude Code**, as a plugin:

```
/plugin marketplace add hantcd/job-search-assistant
/plugin install job-search-assistant@job-search-assistant
```

Or copy the folders: `cp -r skills/job-* ~/.claude/skills/`.

Skill descriptions are under 200 characters, as the Claude app requires.

## Your files (written by the guide's chats)

| file | what |
|---|---|
| PROFILE.md | your facts, constraints, CV contact details, referees, network, past outcomes |
| EVIDENCE.md | each experience, every fact labelled DOCUMENTED, CONFIRMED, GUESSED or UNKNOWN |
| VOICE.md | your writing style, with excerpts |
| PREFERENCES_AND_SCORING.md | role families, exclusions, dealbreakers, and a JSON block of weights and thresholds (`python3 skills/job-scout/score.py example-prefs`) |
| MASTER_PLAN.md | the approved plan: schedules, presets, starting CV weights, outreach, privacy |

The job list lives where your plan says (a page in Claude with a built-in
database by default; a Google Sheet; or a local `jobsearch/pipeline.json`).
The scripts work on a JSON snapshot of it; `skills/job-tracker/schema.md` has
every field.

## The scripts

Standard-library Python 3.8+. `layout_check.py` and reading PDFs need PyMuPDF
(`pip install pymupdf`); compiling CVs needs pdfLaTeX; `apply_form.py` needs
Playwright (`pip install playwright`, then `playwright install chromium`).
Nothing here sends or submits anything.

```bash
python3 skills/job-tracker/pipeline.py validate
python3 skills/job-scout/feeds.py fetch greenhouse intercom --title analyst --location dublin
python3 skills/job-scout/posting_guard.py --in ad.html --html
python3 skills/job-scout/gates.py ad.txt --years-max 2 --languages "English:C2,Irish:B1"
python3 skills/job-scout/fetch_page.py URL --text            # one robots-checked retry after a 403
python3 skills/job-scout/linkedin_jobs.py search -q "data analyst" -l "Ireland" --joblist jobsearch/pipeline.json   # opt-in: last 24h, newest first, reposts dropped
python3 skills/job-scout/jobposting.py page.html --url URL   # the employer's own job data (schema.org JobPosting)
python3 skills/job-scout/feeds.py live URL                     # Greenhouse, Lever, Ashby: LIVE, CLOSED or UNKNOWN
python3 skills/job-scout/feeds.py questions GREENHOUSE_URL     # a Greenhouse job's exact application questions
python3 skills/job-scout/score.py score ratings.json --prefs PREFERENCES_AND_SCORING.md
python3 skills/job-tracker/pipeline.py can-apply acme-junior-data-analyst
python3 skills/job-connector/network.py --file jobsearch/pipeline.json route --job acme-junior-data-analyst
python3 skills/job-connector/network.py --file jobsearch/pipeline.json plan --job acme-junior-data-analyst
python3 skills/job-scout/hidden.py queries --industry fintech --place Dublin --country IE
python3 skills/job-scout/hidden.py rank --file jobsearch/pipeline.json --industry fintech --place Dublin
python3 skills/job-network/chat_prep.py check prep.md
python3 skills/job-linkedin/post_check.py post.txt --format document
python3 skills/job-connector/network.py --file jobsearch/pipeline.json companies --top 20
python3 skills/job-connector/outreach.py linkedin --keywords "data analytics" --company-slug acme --school-slug trinity-college-dublin
python3 skills/job-cv/audit.py ad.txt cv.pdf --role "Junior Data Analyst"
python3 skills/job-cv/skim.py cv.pdf --role "Junior Data Analyst" --ad ad.txt
python3 skills/job-cv/keywords.py ad.txt cv.tex
python3 skills/job-cv/truth_check.py cv.tex --source EVIDENCE.md
python3 skills/job-cv/tex_check.py escapes cv.tex
python3 skills/job-cv/tex_check.py conversion original_cv.pdf base.tex
python3 skills/job-cv/layout_check.py cv.pdf cv.log --pages 1
python3 skills/job-cv/parse_check.py cv.pdf --name "Aoife Byrne" --headings "Experience,Education,Skills"
python3 skills/job-cover/letter_check.py letter.md --company "Acme Ltd" --source EVIDENCE.md
python3 skills/job-apply/answers.py form.json
python3 skills/job-apply/answers.py lengths filled.json
python3 skills/job-apply/apply_form.py fill URL --answers answers.json --cv cv.pdf   # Playwright: fills, reads back, stops at Submit
python3 skills/job-connector/outreach.py slots --start 2026-10-16
python3 skills/job-connector/emails.py guess --name "Siobhan Kelly" --domain acme.ie
python3 skills/job-followup/followup.py due
python3 skills/job-interview/star.py check answer.txt
python3 skills/job-interview/invite.py invite.ics --zone Europe/Dublin
python3 skills/job-interview/mock.py check mock.json --source EVIDENCE.md
python3 skills/job-offer/offer.py total offer.json
python3 skills/job-weekly/funnel.py report
python3 skills/job-network/events.py due
python3 skills/job-research/notes_check.py notes/acme.md
python3 skills/job-linkedin/profile_check.py limits pack.json
python3 skills/job-reddit/reddit_check.py check draft.json --previous replies.json
```

Tests (offline fixtures):

```bash
python3 -m unittest discover -s tests -v
```

Evals (Claude Code 2.1.269 or later; they use your Claude plan or API credit):
does each request open the right skill, and does Claude keep the rules when
asked to break them?

```bash
claude plugin eval . --trust-plugin --runs 1 --ablation none --max-cost-usd 10
```

## Companion skills

Skills reference these by name under "Other skills it uses (if installed)",
always with a fallback. None is bundled: Anthropic's document skills are
proprietary and built into Claude; the others are installed from their own
repositories.

- **docx, pdf, xlsx, pptx** (Anthropic): job-cv, job-cover, job-apply,
  job-tracker, job-interview, job-offer.
- **last30days** (Matt Van Horn, MIT): job-research, job-interview,
  job-weekly. Only sources that need no account; never the person's X,
  LinkedIn or browser cookies; results go through the posting check.
- **superpowers** (Jesse Vincent, MIT): job-chief and job-apply; its
  verification-before-completion is adapted as the evidence rule in
  `CONSENT.md`.
- **skill-creator** (Anthropic, Apache 2.0): job-weekly, for a person's own
  extras; and for contributors, to test skill descriptions alongside
  `claude plugin eval`.

Contributing: plan changes with superpowers' writing-plans, keep every
`SKILL.md` under 300 lines with the same sections, add tests for any rule a
script enforces, and run the unit tests and evals before a release.

## Using it in Claude Code? Keep your data out of git

Your personal files (PROFILE.md, EVIDENCE.md, VOICE.md, PREFERENCES_AND_SCORING.md,
MASTER_PLAN.md and `jobsearch/`) never belong in this repository. The
`.gitignore` here excludes them, but a fork of a public GitHub repository is
always public: keep your own copy in a private repository, or outside git
altogether. Update by version (see `CHANGELOG.md`), not by pulling whatever is
newest.

## Fine print

- **Nothing goes out without your yes**, for that exact item, and each yes
  is one click. Claude sends an email from your Gmail when you tap Approve
  for it. On an employer's site Claude fills the form while you watch, shows
  every answer and declaration in the chat, and presses Submit when you
  approve that application (you press it yourself where the employer asks AI
  agents not to apply). LinkedIn notes and messages are pasted by Claude in
  your browser while you watch, one person at a time, and you click Send.
  Automatic tasks never act in LinkedIn and never send or submit anything. LinkedIn's User Agreement forbids bots and automated
  activity; keeping every step watched and human-paced is the safeguard, and
  the choice is yours.
- **Nothing invented.** Only facts from your evidence go into anything in your
  name; the truth check fails on a number or skill that isn't there.
- **LinkedIn listings are opt-in.** Reading LinkedIn's public, logged-out job
  listings is off unless your plan turns it on. LinkedIn's User Agreement
  forbids automated access, so it's your informed choice; it stays low volume
  and never touches your account, profiles or people.
- **Reddit.** Claude finds threads and drafts replies; you post them by hand
  from your own account, within each subreddit's rules and a weekly limit you
  set. Never a second account, never votes, never a job pitch in a reply that
  answers someone's question.
- **Blocked pages.** After a 403, one retry with ordinary browser headers, only
  where the site's robots.txt allows it. Never round a login, a CAPTCHA or a
  robots.txt refusal.
- **Privacy.** Work details only, for the hiring manager, the team and
  referral contacts on a job you're pursuing: from public pages, a checked
  guess at the address format, or a contact-data tool you connect
  (Orthogonal with Hunter, Apollo, RocketReach). Each gets its source and a
  LOW, MEDIUM or HIGH privacy label with reasoning, and you decide. Never
  personal emails or home details; a mobile or personal number is HIGH risk
  and used only if you say so; Claude never calls or texts. France's
  regulator fined Kaspr in 2024 for contact data taken from LinkedIn, so
  tools built that way are labelled HIGH.
- **Stop rules.** The first no, two follow-ups, or 21 days of silence ends a
  thread; a request to stop is honoured forever.
- **No guarantees.** It makes you better prepared and better connected; it
  can't promise an interview, an offer or a number. Information, not legal or
  financial advice.

## Credits

- [hunter-skill](https://github.com/Jakeschincariol/hunter-skill) (MIT, Jake
  Schincariol): the one-skill-per-job structure, scripts that enforce rules,
  the public board list, LinkedIn field limits, the email-guess and stop-rule
  ideas, and the cover-letter and truth checks this pack adapts.
- [please-hire-me](https://github.com/alecswang/please-hire-me) (MIT, Alex
  Wang): about 220 more verified job boards, per-company application limits,
  the company cap and mid-interview hold, hidden-gate checks, form read-back
  and browser-hygiene rules, the LaTeX escape and conversion checks, and the
  letter-overlap warning. This pack keeps its own rule: it never submits.
- [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) (MIT, Mads
  Lorentzen): the posting integrity check, robots-checked page retry and
  LinkedIn listings reader (ported, with their tests), the eligibility and
  language gates, the ATS parse check, orphaned-title and early-page checks,
  relevance-weighted cutting, application archives, the email-tracker rules,
  the fresh reviewer, the unreachable-ad retry rule, and evidence from your own
  public links. Earlier: the review pass, layout checks and the call before
  applying.
- [reddit-automation](https://github.com/flowkit-labs/skills) (MIT, doany.ai):
  the find-then-draft method, experience grammar, the mention gate and the
  register check behind job-reddit.
- [mattpocock/skills](https://github.com/mattpocock/skills) (MIT, Matt
  Pocock): the grilling skill's question rounds, used in setup and wherever a
  skill interviews you.
- [Anthropic's skill-creator](https://github.com/anthropics/skills) and
  Claude Code's plugin evals: the idea of testing skill choice and behaviour,
  not just scripts.
- [Jake's Resume](https://github.com/jakegut/resume) (MIT, Jake Gutierrez),
  based on sb2nov/resume: the CV template.
- [humanizer](https://github.com/blader/humanizer) (MIT, Siqi Chen), drawing
  on Wikipedia's "Signs of AI writing": the writing check.
- [career-ops](https://github.com/career-ops-hq/career-ops) (MIT, Santiago
  Fernández de Valderrama): the Greenhouse, Lever and Ashby liveness check
  and application links, reading interview invites and panels, and the
  practice interviewer; earlier, ideas for legitimacy ratings, score
  confidence, agency handling and review passes.
- [greenroom](https://github.com/YunyueLi/greenroom) (Yunyue Li): ideas for
  the mock interview (the follow-up chain, real and pressure modes, the five
  scores). Ideas only; none of its text is used.
- Ideas only, none of their text used: [claude-resume-kit](https://github.com/ARPeeketi/claude-resume-kit)
  (verb discipline, provenance, a corrections log),
  [InterviewThread](https://github.com/weiyu1029/Interview_Thread_AI) (the proof pack),
  [interview-skills](https://github.com/jennifer88huang/interview-skills) (strong vs weak answers),
  [swe-interview-coach](https://github.com/kirilxd/swe-interview-coach) and
  [JobSync](https://github.com/Gsync/jobsync) (debriefs after real interviews),
  [offer-toolkit-skill](https://github.com/yanliudesign/offer-toolkit-skill) and
  [behavior-question-skill](https://github.com/yanliudesign/behavior-question-skill)
  (negotiation stop-lines, story tags), [Dossier](https://github.com/AienTech/dossier)
  (applications by email), [linkedin-skills](https://github.com/sergebulaev/linkedin-skills)
  (installing from GitHub in the Claude app) and [Job Seek](https://github.com/colophon-group/jobseek)
  (its free connector as a job source).
- The REFER kit (10x.with.ai): ideas for the referral path, Google searches
  for people on a team, checking each name and not greeting a recruiter who
  just rejected you. Ideas only; none of its text is used.
- [MavGPT's AI job seekers guide](https://mavgpt.ai/resources/ai-resume-job-search-guide)
  (Maverick Maltin): ideas for the quick job audit, the 10-second skim with
  a yes, maybe or no pile, the cover letter's gap paragraph and a short
  try-it message. Ideas only; none of its text is used.
- [David DeGenova](https://davidatpgp.netlify.app) (Post Grad Project): the
  three touches including a comment on the post about the job, the LinkedIn
  searches the person runs (alumni tab, company People tab, 2nd-degree
  intros) and the chat prep with its closing ask. Ideas only; none of his
  text is used.
- Ideas only, none of their text used: Leila and Alex Hormozi (screening
  questions; "do it, don't offer"), Brian DeChesare's Mergers & Inquisitions
  (the mini-ask and real ask), Management Consulted (the 2/2/2 rule),
  Wonsulting (the 10-day sequence and pivot to a peer), Sinéad Brady and UCC
  Careers (apply at 60-70% for graduate schemes), and
  [attainmentlabs/linkedin-algorithm-skill](https://github.com/attainmentlabs/linkedin-algorithm-skill)
  (comment depth).
- Ideas only, none of their text used: [Proficiently](https://github.com/proficientlyjobs/proficiently-claude-skills)
  (network scan), [jobautopilot](https://github.com/jerronl/jobautopilot-claude)
  (a knowledge base of form quirks),
  [backpropagation6/claude-linkedin-automation](https://github.com/backpropagation6/claude-linkedin-automation)
  (absence isn't proof) and [job-apply-ai](https://github.com/ShipItAndPray/job-apply-ai)
  (reading each form back from a screenshot before submitting, which the pack already did).
- The 2-Hour Job Search (Steve Dalton) for the 3B7 follow-up rule, and the
  other experts and studies cited in the guide.

MIT licence: see `LICENSE`.
