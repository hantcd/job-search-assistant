# PREFERENCES_AND_SCORING.md (example: Aoife Byrne, fictional)

## Role families
1. Data analyst (primary): Junior Data Analyst, Data Analyst, BI Analyst, Reporting Analyst. Graduate to 2 years. Insurance, fintech, health, public sector. Dublin or remote in Ireland.
2. Finance analyst: Graduate Analyst, FP&A Analyst. Banks and insurers. Dublin, Galway.

## Excluded
Sales-heavy roles; unpaid internships; roles needing fluent German or French.

## Dealbreakers (pass or fail)
Pay under €35,000; more than 3 days a week in the office; outside Ireland.

## Career Value preset: "Learn fast" (weights total 100)
| part | weight | 0 looks like | 5 looks like |
|---|---|---|---|
| learning | 30 | repetitive reporting, no mentor | a strong data team, real modelling work |
| pay | 20 | at the floor | top quartile for the level |
| people | 15 | ... | ... |
| responsibility | 15 | ... | ... |
| stability | 10 | ... | ... |
| prestige | 10 | ... | ... |

## Attainability (separate; a hard job never lowers Career Value)
must-haves met 40, level fit 25, eligibility 15, connection 10, competition 10.

## Alert rules
Alert at Career Value 70+ and Attainability 40+, at most 5 per alert; automatic packs for 75+, top 2 per alert, up to 4 a week.

```json
{"career_value": {"weights": {"learning": 30, "pay": 20, "people": 15, "responsibility": 15, "stability": 10, "prestige": 10}},
 "attainability": {"weights": {"must_haves_met": 40, "level_fit": 25, "eligibility": 15, "connection": 10, "competition": 10}},
 "thresholds": {"alert_career_value": 70, "alert_attainability": 40, "pack_career_value": 75},
 "max_alerts": 5, "packs_per_alert": 2}
```
