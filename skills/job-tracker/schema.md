# Job list schema

One JSON object; each table is a list of rows. Dates are `YYYY-MM-DD` (a
message may add a time: `2026-10-12T09:30`). Extra fields are kept. Fields
marked * are checked by `pipeline.py validate`.

## jobs
| field | meaning |
|---|---|
| id* | `company-title`, e.g. `acme-junior-data-analyst` |
| company*, title*, location, remote | as on the official posting |
| url | the official link (the company's own page or ATS) |
| other_links | copies elsewhere (LinkedIn, job sites) |
| ref | the posting's reference number |
| posted*, first_found*, last_checked* | dates |
| reposts | dates the same role was posted again |
| status* | new, open, applied, screen, interview, offer, accepted, rejected, withdrawn, closed, ignored |
| applied* | date applied (needed once status is applied or later) |
| deadline | closing date, for reminders 3 days and 1 day before |
| role_family | which role family it belongs to |
| dealbreakers_passed, dealbreaker_notes | pass or fail, and why |
| fit, career_value*, attainability* | 0-100 (from `job-scout/score.py`; Fit is the one the person sees: by default 60% Career Value + 40% Attainability) |
| score_breakdown | each part's points, rating, support and reason |
| confidence* | HIGH, MEDIUM or LOW, plus up to 3 checks that could change it |
| legitimacy* | HIGH CONFIDENCE, PROCEED WITH CAUTION or SUSPICIOUS, with reasons |
| pay | {base, variable, benefits, text, reliability: high, medium, low or unknown} |
| route* | portal, agency, referral or direct; agency also records the agency |
| alerted* | date the person was alerted |
| last_reply, last_follow_up | dates, for follow-ups by stage |
| interviews | [{date, stage, format, questions, feedback, thank_you_sent}] |
| rejected | date the application was rejected (set by `move`) |
| notes | dated lines, e.g. `2026-10-16: open -> applied` |
| fetch_attempts, first_unreachable, last_fetch_error | failed page loads (closed as unreachable after 3 tries over 48+ hours) |
| closed_reason | e.g. unreachable |
| apply_queue | on the apply list: {added, preview (every question and answer, files, declarations word for word), person_submits (the employer asks AI agents not to apply: the person presses Submit), streak_keeper (a real, open job below the usual Fit, kept ready so the streak can go on)} |

## applications
job_id*, pack_made*, base_cv, entries_used, answers [{question, answer}] and
confirmation (a screenshot or the confirmation email) once submitted, and the
archive: posting_text (as posting_guard cleaned it), cv_sent and letter_sent
(the exact files), screening_weights* {search, scan,
read} totalling 100, timing_call (REFERRAL FIRST, APPLY NOW + REACH OUT or
ALREADY APPLIED, from job-connector's `network.py route`), documents (links), edits (what the person changed),
submitted*, outcome.

## contacts
id* (`name-company`), name, role, company, linkedin, email*, email_confidence*
(given, published, verified, high, medium, low, unknown), phone (work numbers
only, with phone_type: office, direct, mobile, unknown), found_how* (a URL when
'published', or the tool: "Hunter via Orthogonal", "Apollo", "RocketReach"), privacy_risk* (LOW, MEDIUM, HIGH), privacy_decision* (the
person's choice and date: required for any email they weren't given), senior
(directors and above wait 10 working days before a follow-up), referred,
employer_checked* (the date the person opened the profile and saw they still
work there; empty = UNVERIFIED), in_common (what they share with the person,
from public results only), knows_work (true when they know the person or their
work: makes the route REFERRAL FIRST), tie_strength, do_not_contact (true after a stop request: never
contacted again), notes.

Before any draft or send to a contact, `pipeline.py contact-check` returns
STOP, CHECK or OK: CHECK lists an unverified employer, a link to a rejected
application, or a recruiter at a company that rejected the person in the last
180 days, each said to the person before they decide.

## outreach
contact_id*, job_id*, channel* (email, linkedin, phone, in-person, other),
status* (drafted, sent, replied, booked, declined, closed), messages* [{date,
direction: out or in, slot (e.g. 'Tue morning'), text}], draft {text,
subject}, approval {reply, date, hash} (the person's exact yes),
booking (what to offer: 'chat, 3 slots' or 'interview times'), booked (the
date a time was confirmed), accepted (the date a connection request was
accepted), draft_needed, chat_held; stage* (ask and nudge for a job's route; note, thanks and chat for building
a network without a job in mind), route (referral_first or apply_now, from
`network.py route`: sets when the one nudge is due), invite_pending (a
LinkedIn invitation: no follow-up), suggested_other (a
second person suggested after 3 working days), next_followup*, booked {when,
minutes, where}, about_role (a comment row: true when the post is about the
role or its team; only those are offered).

A draft is never in `messages`: messages hold only what really went out or
came in.

## email_log
message_id* (each processed once), date*, from*, subject* (all required when a
status changes), job_id, change (what was updated, or 'proposed' while waiting
for the person), decision.

## reddit
url*, subreddit*, kind* (HIRING, HELP or INSIDE INFO), found*, why (one line:
why the person can genuinely help), rule (the subreddit rule that applies, and
the date it was read), draft, posted (the date the person says they posted
it; Claude never posts), replies. Kept by job-reddit; `reddit_check.py cap`
counts the week's posted replies.

## linkedin_ids
date*, max_id*: the highest LinkedIn job id seen that day (kept 60 days), written
by `linkedin_jobs.py --joblist`. A listing whose id is lower than one seen 2+
days earlier was first posted before then: a repost.

## run_log
time*, task*, sources_checked, new, updated, closed, errors, stopped_early (and why).

## Other tables
companies (company notes, plus limit_max, limit_window_days, limit_scope and
resets when a company limits applications per person), events, offers, feedback, story_grid,
keyword_bank, watched, network, signals, form_notes (site, quirk, handling, date: job-apply's form
memory), hidden (job-scout's `hidden.py`: growing companies most applicants miss, with source,
funding date, size, feed and status): lists of rows; see the skill that
keeps each.
