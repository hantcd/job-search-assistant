# Job Search Assistant for Claude

Turn Claude into a careful, personal job-search assistant: set it up in one
60–90 minute sitting, no coding needed. Free and open source.

**Claude drafts. You send.** Nothing goes out until you press Send or Submit
yourself.

**[Read the step-by-step guide](GUIDE.md)** · **[Download the guide as a PDF](https://github.com/hantcd/job-search-assistant/raw/main/GUIDE.pdf)** · **[Download the skill pack](https://github.com/hantcd/job-search-assistant/raw/main/dist/job-search-assistant-all.zip)**

> **Quick start**
> 1. You need a paid Claude plan (Pro or Max), a computer, and a folder of
>    your CVs and documents.
> 2. In Claude, create a project called *Job Search Assistant*.
> 3. Download [the skill pack](https://github.com/hantcd/job-search-assistant/raw/main/dist/job-search-assistant-all.zip),
>    then in Claude click **Customize → Plugins → + Add → Upload plugin** and
>    pick the zip. The guide has pictures of every screen.
> 4. Open [the guide](GUIDE.md) and follow Steps 2 to 6: two short chats about
>    you, then Claude builds and tests everything.
> 5. From then on, read the alerts and approve what you like. You press Send
>    and Submit yourself.

## What it does

Once it's set up, Claude works on your job search every weekday:

- **Finds jobs that suit you**, from company job pages, job boards, your email
  job alerts and community hiring threads, and checks each one is real and
  still open. It works with LinkedIn, Indeed, Welcome to the Jungle,
  Handshake, Jack & Jill and hundreds of company careers sites on Greenhouse,
  Lever and Ashby, and favours
  jobs posted in the last 24 hours that aren't reposts.
- **Scores each job** the same way every time, against what you said matters
  to you, and alerts you only about the best (at most 5 at a time).
- **Prepares an application pack** for the top jobs: a CV tailored to the job,
  a cover letter in your own voice, draft answers to the application
  questions, and people who could refer you. When you ask, it fills in the
  application on the company's own website while you watch, then stops so
  you can check it and press Submit.
- **Gets you referrals.** Across 38 million applications on Ashby, 40% of
  referred candidates reached an interview, against 3% of people who applied
  alone ([Ashby Talent Trends](https://www.ashbyhq.com/talent-trends-report/reports/referrals);
  averages, not a promise). Claude finds people on the team through Google,
  never by going onto LinkedIn, and drafts each step for you to send: a short
  hello, a thank-you, the referral ask with the job link and an easy way to
  say no, and one nudge before it stops. It warns you before you write to
  someone it couldn't verify, or to a recruiter at a company that just
  turned you down.
- **Drafts messages** to hiring managers and possible referrers, follows up
  politely, and stops at the first no.
- **Helps you get found** on LinkedIn, and prepares you for interviews and
  offers, with realistic mock interviews: it plays the interviewer, asks
  follow-up questions the way real panels do, and scores you so you can see
  what to practise.

Most people are hired through referrals and direct contact rather than cold
applications, so it works both routes.

## How it works

- **Skills**: this repository is a pack of 15 *skills*, instruction sets that
  teach Claude how to do each part of a job search well (finding jobs, CVs,
  cover letters, messages, interviews and more). You install them in Claude
  in one step.
- **Your files**: in two short chats, Claude reads your CVs and documents and
  writes a few private files about you: your experience, your writing style
  and your goals. The skills use these, so everything is personal to you.
- **Automatic tasks**: Claude then runs scheduled searches on weekdays and
  sends you alerts, using your job list to remember what it has already seen.
- **Built-in checks**: small programs inside the skills check the work, for
  example that every line of a CV comes from your own documents, and that no
  follow-up goes out after someone has said no. Claude never calls something
  ready without running its check and showing you the result.
- **A chief of staff (optional)**: in Claude Code or Cowork, one long session
  can run the whole search, handing work to helpers and keeping a dated
  record of what you decided and what's working.

### What it never does

- **Never sends, submits or posts anything without your yes** for that exact
  item. Emails are saved as drafts for you to send; you press Submit on every
  application.
- **Never invents anything.** Only facts from your own documents, or that you
  confirm, go into your CV, letters and answers.
- **Never types your passwords**, and never acts in LinkedIn, Reddit or X when
  you're not there.
- Text on web pages, in emails and in job ads is treated as information, never
  as instructions to Claude.

## What you need

- A **Claude Pro or Max** plan, used on a computer (the website or the desktop
  app). Your phone works later, for alerts.
- **60–90 minutes** in one sitting.
- **One folder of documents**: your CVs (old ones too), your LinkedIn data
  export, transcripts or course lists, certificates, links to your work, past
  cover letters, and 3–5 things you wrote yourself so Claude learns your style.
  Messy is fine. The [guide](GUIDE.md) lists everything, including how to get
  your LinkedIn export the day before.
- Optional: **Gmail** connected to Claude, so it can read job alerts, notice
  replies and save drafts for you.

It works for any kind of job, not just tech or sales. The guide's examples
are from Ireland; the setup asks where you are and adjusts.

## Get started, step by step

The **[guide](GUIDE.md)** walks you through every step with the exact text to
paste into Claude and a checklist after each one. In short:

1. **Create a project in Claude** called *Job Search Assistant*. Download
   [job-search-assistant-all.zip](https://github.com/hantcd/job-search-assistant/raw/main/dist/job-search-assistant-all.zip),
   then click **Customize → Plugins → + Add → Upload plugin** and pick the
   zip. The guide shows each screen with the button to press marked.
   *(About 10 minutes.)*
2. **Chat 1: Claude reads your documents.** Add your folder to the project and paste the
   guide's first prompt. Claude drafts your profile, your evidence and your
   writing style; you confirm or correct its guesses, mostly by clicking.
   *(About 20 minutes.)*
3. **Chat 2: your goals, scoring and plan.** Claude suggests the kinds of jobs
   to target, how to score them and how often to search; you approve the
   plan. *(15–20 minutes.)*
4. **Ask Claude to build it.** Paste the guide's build prompt. Claude writes
   the project's rules, your CVs, your LinkedIn profile text, the job list and
   the automatic tasks, then tests them. *(Claude works; you wait.)*
5. **Install it.** Paste the rules into the project's instructions, click
   **Schedule** on each automatic task, set up email job alerts, and update
   LinkedIn. *(10–15 minutes.)*
6. **Spot-check and switch on.** Run the daily search once, open three of the
   jobs it found, and check one application pack. *(10–15 minutes.)*
7. **Everyday use.** Read the alerts, approve what you like, press Send and
   Submit yourself.
8. **Add extras later** from the guide's list, whenever you want them.

Stuck? The guide's **If something goes wrong** section has a fix for the
common problems, each with the exact words to say to Claude.

## Downloads

| file | what it's for |
|---|---|
| [GUIDE.pdf](https://github.com/hantcd/job-search-assistant/raw/main/GUIDE.pdf) | the step-by-step guide, to read offline or print |
| [job-search-assistant-all.zip](https://github.com/hantcd/job-search-assistant/raw/main/dist/job-search-assistant-all.zip) | all 15 skills in one file: attach it in a Claude chat to install them (in Cowork, it also installs as a plugin) |
| [Single-skill zips](https://github.com/hantcd/job-search-assistant/tree/main/dist) | the same skills one at a time, to upload under **Customize > Skills** instead |

## Questions

**Does it cost anything?** The skill pack is free. You need a paid Claude plan
(Pro or Max). During setup Claude gives you a rough estimate of your weekly
usage.

**Where does my information go?** Your documents and the files Claude writes
about you stay in your own Claude project. Nothing about you goes into this
repository.

**Will it apply for jobs for me?** No. It prepares everything and can fill in
the company's own application form while you watch, but you check every
application and press Submit yourself.

**Which job sites does it use?** Company careers sites first, plus LinkedIn,
Indeed, Welcome to the Jungle, Handshake, Jack & Jill, specialist boards and
community hiring threads. Some sites don't allow automated reading, so for
those it reads the job alert emails you set up, and you can choose during
setup to let it read their job pages too. It never logs in to any of them for
you.

**Will it message people on LinkedIn by itself?** No. It drafts each message;
you approve it, and you click Send, one person at a time.

**Can I change things later?** Yes. Tell Claude in plain words (for example
*"stop showing me jobs that need German"*) and it updates your plan. Your
goals and privacy rules never change without your approval.

## Works even better with

Optional skills from other projects. The pack works without them; when one
is installed, the skills use it where it helps.

| skill | what it adds |
|---|---|
| Claude's **document skills** (Word, PDF, Excel, PowerPoint; built in) | editable Word CVs and letters, filling PDF and Word application forms, a spreadsheet backup of your job list, an offer comparison, slides for a presentation interview |
| [last30days](https://github.com/mvanhorn/last30days-skill) | what people said about a company or your field in the last 30 days, and what a company's new job ads say about where it's heading (no account logins used) |
| [superpowers](https://github.com/obra/superpowers) | working through big tasks with helpers in parallel, and checking work before calling it done |
| [chief-of-staff](https://github.com/mattpocock/skills) | the original of the pack's job-chief, for other long-running goals |
| [skill-creator](https://github.com/anthropics/skills) | turning a correction you keep making into a tested skill of your own |

## For technical users

The skills include tested Python scripts that enforce the rules that must
never slip (truth checks, stop rules, the posting check), read-only reviewer
agents and hooks that block sending in Cowork and Claude Code, and evals.
See **[TECHNICAL.md](TECHNICAL.md)** for the skill list, scripts, tests,
Claude Code install and credits, and **[CHANGELOG.md](CHANGELOG.md)** for
what changed in each version.

## Credits and licence

Free under the [MIT licence](LICENSE). It builds on several open-source
projects, credited in [LICENSE](LICENSE) and [TECHNICAL.md](TECHNICAL.md#credits):
hunter-skill, please-hire-me, ai-job-search, career-ops, reddit-automation,
Matt Pocock's skills, superpowers, humanizer and Jake's Resume.

This is an independent project, not made or endorsed by Anthropic. Claude is
a product of Anthropic.
