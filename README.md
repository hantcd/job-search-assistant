# Job Search Assistant for Claude

Turn Claude into a careful, personal job-search assistant: set it up in one
60–90 minute sitting, no coding needed. Free and open source.

**[Read the step-by-step guide](GUIDE.md)** · **[Download the guide as a PDF](https://github.com/hantcd/job-search-assistant/raw/main/GUIDE.pdf)** · **[Download the skill pack](https://github.com/hantcd/job-search-assistant/raw/main/dist/job-search-assistant-all.zip)**

## What it does

Once it's set up, Claude works on your job search every weekday:

- **Finds jobs that suit you**, from company job pages, job boards, your email
  job alerts and community hiring threads, and checks each one is real and
  still open.
- **Scores each job** the same way every time, against what you said matters
  to you, and alerts you only about the best (at most 5 at a time).
- **Prepares an application pack** for the top jobs: a CV tailored to the job,
  a cover letter in your own voice, draft answers to the application
  questions, and people who could refer you.
- **Drafts messages** to hiring managers and possible referrers, follows up
  politely, and stops at the first no.
- **Helps you get found** on LinkedIn, and prepares you for interviews and
  offers.

Most people are hired through referrals and direct contact rather than cold
applications, so it works both routes.

## How it works

- **Skills**: this repository is a pack of 14 *skills*, instruction sets that
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
  follow-up goes out after someone has said no.

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
   attach it in a chat in the project and say *Install these 14 skills*, then
   click **Save** on each card. *(About 10 minutes.)*
2. **Chat 1: Claude reads your documents.** Attach your folder and paste the
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
| [job-search-assistant-all.zip](https://github.com/hantcd/job-search-assistant/raw/main/dist/job-search-assistant-all.zip) | all 14 skills in one file: attach it in a Claude chat to install them (in Cowork, it also installs as a plugin) |
| [Single-skill zips](https://github.com/hantcd/job-search-assistant/tree/main/dist) | the same skills one at a time, to upload under **Customize > Skills** instead |

## Questions

**Does it cost anything?** The skill pack is free. You need a paid Claude plan
(Pro or Max). During setup Claude gives you a rough estimate of your weekly
usage.

**Where does my information go?** Your documents and the files Claude writes
about you stay in your own Claude project. Nothing about you goes into this
repository.

**Will it apply for jobs for me?** No. It prepares everything and can fill in
forms while you watch, but you check every application and press Submit
yourself.

**Will it message people on LinkedIn by itself?** No. It drafts each message;
you approve it, and you click Send, one person at a time.

**Can I change things later?** Yes. Tell Claude in plain words (for example
*"stop showing me jobs that need German"*) and it updates your plan. Your
goals and privacy rules never change without your approval.

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
hunter-skill, please-hire-me, ai-job-search, reddit-automation, Matt Pocock's
skills, humanizer and Jake's Resume.

This is an independent project, not made or endorsed by Anthropic. Claude is
a product of Anthropic.
