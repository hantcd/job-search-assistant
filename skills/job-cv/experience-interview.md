# The experience interview

A short, spoken interview about one role, for when the documents don't say
enough. Typical case: the newest job is on LinkedIn with two lines and on no
CV, so every CV built from the old CVs leaves out the role a recruiter reads
first. `depth.py` finds these roles; this file says how to run the interview.

## Why it matters

- Recruiters look at the current title and company first, then the previous
  one, then the dates (the Ladders' 2018 eye-tracking study: about 7.4
  seconds a CV). A thin newest role weakens the top of the page.
- Hiring managers read for scope, results tied to the person's own decisions,
  growing responsibility, and evidence that matches the role. They want the
  result measured against something (Laszlo Bock: "accomplished X, relative
  to Y, by doing Z"). Duties alone don't get interviews.
- Employers of new graduates look first for problem-solving (nearly 90%),
  teamwork (nearly 80%) and initiative (NACE Job Outlook 2025). McKinsey's
  recruiters want impact, teamwork and leadership, and all relevant work,
  part-time jobs included.
- People forget their best work. Resume writers find it by asking ("What
  did you start that wasn't there before?", "How do you know you were good
  at it?"). Hiring managers find it by probing one accomplishment in depth
  (Lou Adler) and by walking through every job in turn (Topgrading: what you
  were hired to do, your successes, the low points, what your boss would
  say, why you left).
- Speaking is about three times faster than typing on a phone (Stanford,
  2016), and people say more when they talk. So the interview is spoken.

## Before asking anything

Find everything that's already written down, so the person only answers
what can't be found:
1. **Old CVs and the LinkedIn profile**: merge them into one timeline. The
   newest entry from any source wins, and a role that's only on LinkedIn is
   never dropped. With the LinkedIn data export, run `depth.py roles
   --linkedin Positions.csv` to list positions missing from EVIDENCE.md.
2. **Gmail and Drive**, if connected: search the company's name with offer,
   contract, review, appraisal, promotion, target, quota, results, award,
   congratulations, thank you, launch, report and deck. Use the person's own
   results only. Each fact found is DOCUMENTED with its source ("email
   12 Mar 2026: Q1 results"). Ask before using an employer's confidential
   figures or a client's name; praise from someone else is quoted only with
   the person's OK.
3. **The role families' job ads**: the must-haves that keep coming up in
   the keyword bank (or in 5 real ads, at setup) that EVIDENCE.md doesn't
   cover go into `--terms`. They're asked first.

Then run `depth.py questions --evidence EVIDENCE.md --role "<company>"
--family "<role family>" [--terms gaps.txt]`.

## Running it

- Say first, once: "This works best out loud. Tap the microphone in the
  message box and talk as you would to a friend (on a phone, hold it while
  you talk). Rambling is fine, I'll sort it out. Voice mode, the sound-wave
  icon, also works if you'd rather have a conversation (not in Cowork)."
- **One question at a time.** After each answer, ask at most two follow-ups,
  only for what's missing: a number ("roughly how many?"), the person's own
  part ("you, or the team?"), or the result ("what changed?"). Then move on.
- Never suggest a number or an achievement. If the person can't remember a
  figure, ask for a range they're sure of ("more or less than 20?") and
  record it as 'about', in their words.
- About 10 minutes, at most 12 questions. "Stop" saves where it got to, and
  the next session picks up there.
- Different from the question rounds in SKILL.md: those confirm facts with a
  recommended answer; this gathers stories, so there's no recommended answer.

## Afterwards

1. Read back the new facts as EVIDENCE.md lines, one fact per line, each
   CONFIRMED (interview <date>), with 'about' kept where the person said it.
   The person says yes or fixes them. Nothing the person didn't say goes in.
2. Write them to EVIDENCE.md (in the project), run `depth.py mark --status
   done`, and update the achievement bank.
3. Offer to rebuild the base CVs that use the role, with the truth check.
   The strongest true version applies when writing, never more than they said.
4. Keep two of the stories for job-interview's story grid: the proudest one
   and the low point.

## When it runs

- **At setup** (chat 1): after the timeline, for every current or recent
  role `depth.py roles` marks THIN or MISSING. At this point Claude asks
  roughly which roles the person is going for, so the role family's
  questions are used. In chat 2, once the role families are set, each
  family's must-haves without evidence are asked about too.
- **When a gap shows**: a requirements map with two or more must-haves that
  have no evidence, or a base CV with no number in its top third, offers the
  interview for the role most likely to hold the evidence.
- **The person's choice**: when a role is thin, ask once: "Do it now
  (about 10 minutes, spoken), or remind me in my morning session?" With a
  reminder, the morning session shows it as "when you have 10 minutes"
  (today.py --evidence), outside the daily time. "Not now" marks it declined,
  and it isn't offered again for 30 days.
