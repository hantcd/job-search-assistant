# Finding people and timing (job-connector)

Read with SKILL.md when searching for people on a team or planning send times.

## Finding people through Google

`outreach.py find` builds Google searches such as
`site:linkedin.com/in "Acme" "data analytics" "Trinity College Dublin"`: the
company, the team or job title, and something the person shares with them
(school first, then city). Two people per company is plenty.

- **In a chat with the person present:** open each Google link in the
  browser (the built-in browser or Claude in Chrome) and read Google's results
  page only. Never open, click or follow anything on linkedin.com. One or two
  results pages per company; if Google shows a CAPTCHA or an 'unusual traffic'
  page, stop and give the person the link to open themselves.
- **In automatic tasks:** Claude's own web search doesn't reliably honour
  `site:` (tested 2026-11-04: one or two profiles in 20 results, with no
  details), so the alert lists the Google links for the person to open, or
  for the next chat.
- Keep only what the results show: name, headline, employer, school,
  location, the profile link, and what they share with the person
  (`in_common`). Each contact stays UNVERIFIED until the person opens the
  profile and confirms they still work there (`employer_checked`); results go
  out of date.

## Searching on the person's computer, automatically

Claude's own web search doesn't find people (tested 2026-11-06: hiring-manager
searches returned only job listings), and scheduled tasks in the cloud have
no browser. So the people search is its own scheduled task that requires the
person's computer, "Referral search (on your computer)", set up with the
other automatic tasks and running in the Claude desktop app's built-in
browser whenever the app is open. If the computer is off, the run waits for
the next one and nothing is lost.

Each run takes the new jobs that passed the gates and haven't been searched
yet (`people_searched` empty), best scores first, at most 10, whether or not
the person already knows someone there: the best person for the role often
isn't in their network. For each: the hiring manager's title from the ad
(`outreach.py manager`; otherwise the most senior title in the job's function
there), then two team searches with what the person shares (school, city, a
past employer, from PROFILE.md), all through `outreach.py find` and read on
Google's results page only. At most 20 searches a run, a pause between them;
never open, click or follow anything on linkedin.com; a CAPTCHA or 'unusual
traffic' page stops the run and the report gives the links. Results go into
contacts as UNVERIFIED with `found_how` and `in_common`, and the job gets
`people_searched` with the date.

To find a hiring manager, the person can also run LinkedIn's people search in
their own browser; Claude may read that one results page with them present.
No automated searches on LinkedIn, no bulk profile visits.

## Timing

`outreach.py slots` plans three touches that never share a weekday and time
band, so one bad slot in someone's week can't sink every attempt: the first
the next weekday morning, 8-11am (Tuesday-Thursday mornings do best overall);
the follow-up on a different weekday at 2-5pm, when many replies arrive; the
last on a third weekday, early (7-8am) or early evening (6-8pm), when inboxes
are quieter. The recipient's time zone; no Friday afternoons or weekends.
Directors and above: 10 working days before the follow-up rather than 7. If
someone's public posts show when they're active, use that window. Record each
send's slot; after 20+ sends, suggest a better starting window from the
person's reply data, without over-reading small numbers. Follow-ups and stop
rules: job-followup.

## Searches only the person can run (LinkedIn)

From David DeGenova's finding-people cheat-sheet (Post Grad Project; ideas
only). `outreach.py linkedin --keywords "..." --company-slug ... --school-slug
...` builds the links and the filters to click; the person opens them in their
own LinkedIn. Claude never opens them, and never loops through results.

1. **Their school's alumni tab**: a keyword or career path "in quotes" (try it
   without the quotes too), filtered by where they live, what they studied and
   where they work.
2. **The company's People tab**, when applying to that company: filtered by
   school (theirs and nearby ones), city, and what they studied; last, 1st and
   2nd-degree connections. Anyone the person knows well who knows someone
   there can introduce them.
3. **A full people search**: All filters, several schools, several locations,
   current and past companies; their sport, scholarship, hometown or student
   society "in quotes" finds people with the same background.

The person pastes the results, or lets Claude read that one results page with
them present. Names go into contacts UNVERIFIED with found_how "LinkedIn
search you ran", and `network.py rank` orders them with everyone else.

## Which strangers answer most

Moderately weak ties (alumni, past colleagues' colleagues, a few mutual
connections) are the most useful strangers to ask: a LinkedIn experiment
with 20 million people found they led to more job moves than strong ties or
distant ones.

## Connection sessions (growing the network at target companies)

For people at the person's watched companies, top companies in their field
and their network's companies, past or present: alumni and the same function
first, then the team's peers and managers, from Google results and the
LinkedIn searches the person runs (never from Claude reading LinkedIn).

- `outreach.py invites` gives today's budget: at most 16 on a working day and
  80 in any 7 days (80% of the ~100 a week accounts report as LinkedIn's
  ceiling; LinkedIn publishes no number), none at weekends, none while 250+
  are pending, and the invitations pending over 3 weeks to withdraw (the
  person withdraws them; LinkedIn then blocks re-inviting for up to 3 weeks).
- Most requests go without a note (free accounts get 3 notes a month); the
  notes go to the people who matter most for an open job.
- In the session Claude opens each profile in turn in the person's browser,
  clicks Connect and Send without a note (or adds the approved note) as far
  as the dialog before Send, and the person clicks Send: one click each.
  Each is recorded as an outreach row (stage `invite`, `invite_pending`).
- Accepted: they join the network table, and `network.py` ranks them for
  future jobs. Never followed by a sales pitch or an automatic message.
- **The daily queue** (a scheduled task on the person's computer, weekdays
  before the working day): it builds today's queue up to the budget, from
  Google results only (never opening linkedin.com), as outreach rows with
  stage `invite` and status `drafted`, each with why, and sends one line:
  "16 people ready: say Connection session (about 2 minutes)". The session
  works through that queue; anything left rolls to the next day.
