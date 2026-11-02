#!/usr/bin/env python3
"""Offers in numbers: pay year by year, offers side by side, and a counter range with sources.

    python3 offer.py total offer.json [--years 4]
    python3 offer.py compare offer1.json offer2.json [--years 4]
    python3 offer.py counter offer.json --bench bench.json

offer.json (only what the offer says; leave out what it doesn't):
  {"company", "role", "currency": "EUR", "base": 52000,
   "bonus_target_pct": 10, "bonus_reliability": "high|medium|low|unknown",
   "commission_ote": 0, "sign_on": 3000,
   "equity": {"grant_value": 20000, "vesting": [25, 25, 25, 25], "cliff_months": 12, "kind": "RSU|options"},
   "pension_employer_pct": 5, "health_value": 1200, "other_benefits_value": 0,
   "notes": "..."}
bench.json: [{"source", "url", "date", "low", "mid", "high"}]: every market number needs a source.

Variable pay is shown apart from guaranteed pay and labelled with its
reliability, because a bonus 'target' isn't a promise. Options are not cash:
their value depends on a future sale or listing, so they're shown separately.
Adapted from offer.py in hunter-skill (MIT, Jake Schincariol). Information, not
financial advice.
"""

import argparse
import json
import sys


def years_table(o, years=4):
    rows = []
    eq = o.get("equity") or {}
    vest = eq.get("vesting") or []
    if vest and abs(sum(vest) - 100) > 0.01:
        raise ValueError("equity vesting percentages must total 100, got %s" % sum(vest))
    for y in range(1, years + 1):
        base = float(o.get("base", 0))
        guaranteed = base + (o.get("sign_on", 0) if y == 1 else 0)
        pension = base * o.get("pension_employer_pct", 0) / 100.0
        benefits = pension + o.get("health_value", 0) + o.get("other_benefits_value", 0)
        variable = base * o.get("bonus_target_pct", 0) / 100.0 + o.get("commission_ote", 0)
        equity = eq.get("grant_value", 0) * (vest[y - 1] / 100.0 if y <= len(vest) else 0)
        rows.append({"year": y, "guaranteed": round(guaranteed), "benefits": round(benefits),
                     "variable_target": round(variable), "equity": round(equity),
                     "total_if_targets_met": round(guaranteed + benefits + variable + equity)})
    return rows


def show(o, years):
    rows = years_table(o, years)
    cur = o.get("currency", "EUR")
    print("%s, %s (%s)" % (o.get("company", "?"), o.get("role", "?"), cur))
    print("  year  guaranteed  benefits  variable*  equity**  total if targets met")
    for r in rows:
        print("  %4d  %10s  %8s  %9s  %8s  %s" % (r["year"], f"{r['guaranteed']:,}", f"{r['benefits']:,}",
                                                 f"{r['variable_target']:,}", f"{r['equity']:,}",
                                                 f"{r['total_if_targets_met']:,}"))
    print("  * variable pay at target; reliability: %s" % o.get("bonus_reliability", "unknown"))
    eq = o.get("equity") or {}
    if eq:
        print("  ** %s, vesting %s%s" % (eq.get("kind", "equity"), "/".join(str(v) for v in eq.get("vesting", [])),
                                       ", %d-month cliff" % eq["cliff_months"] if eq.get("cliff_months") else ""))
        if eq.get("kind", "").lower() == "options":
            print("     options are worth something only if the company is sold or lists; treat as a maybe")
    return rows


def counter(o, bench):
    for b in bench:
        if not b.get("source") or not (b.get("url") or b.get("date")):
            raise ValueError("every benchmark needs a source and a link or date: %r" % b)
    mids = sorted(b["mid"] for b in bench if b.get("mid"))
    highs = sorted(b["high"] for b in bench if b.get("high"))
    if not mids:
        raise ValueError("no benchmark midpoints")
    mid = mids[len(mids) // 2]
    high = highs[len(highs) // 2] if highs else mid
    base = o.get("base", 0)
    ask_low = max(base, round(mid / 500.0) * 500)
    ask_high = max(ask_low, round((mid + 0.75 * (high - mid)) / 500.0) * 500)
    return {"current_base": base, "market_mid": mid, "market_high": high,
            "counter_range": [ask_low, ask_high],
            "say": "Based on %s, roles like this pay around %s-%s. Could you get the base to %s?"
                   % ("; ".join(b["source"] for b in bench), f"{mid:,}", f"{high:,}", f"{ask_high:,}"),
            "note": "A number near the top of a sourced range, with a reason; include non-salary asks; stay positive."}


def main(argv=None):
    p = argparse.ArgumentParser(description="Offer arithmetic. Information, not financial advice.")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("total")
    t.add_argument("offer")
    t.add_argument("--years", type=int, default=4)
    c = sub.add_parser("compare")
    c.add_argument("offers", nargs="+")
    c.add_argument("--years", type=int, default=4)
    k = sub.add_parser("counter")
    k.add_argument("offer")
    k.add_argument("--bench", required=True)
    a = p.parse_args(argv)
    try:
        if a.cmd == "total":
            show(json.load(open(a.offer, encoding="utf-8")), a.years)
        elif a.cmd == "compare":
            sums = []
            for f in a.offers:
                o = json.load(open(f, encoding="utf-8"))
                rows = show(o, a.years)
                g = sum(r["guaranteed"] + r["benefits"] for r in rows)
                sums.append((o.get("company"), g, sum(r["total_if_targets_met"] for r in rows)))
                print()
            print("Over %d years: guaranteed + benefits | if targets met" % a.years)
            for name, g, tot in sums:
                print("  %-20s %12s | %s" % (name, f"{g:,}", f"{tot:,}"))
        else:
            print(json.dumps(counter(json.load(open(a.offer, encoding="utf-8")),
                                     json.load(open(a.bench, encoding="utf-8"))), indent=1))
    except (ValueError, KeyError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
