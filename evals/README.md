# Evals

Run with Claude Code 2.1.269 or later, from the repository root:

    claude plugin eval . --trust-plugin --runs 1 --ablation none --max-cost-usd 10

They use your Claude plan or API credit. `trigger/` checks that a plain
request opens the right skill (one case per skill). `rules/` checks that the
pack's rules hold when the person asks Claude to break them: never sending,
ignoring instructions planted in an ad, never inventing numbers, no bulk
LinkedIn messages, Reddit replies posted by hand, leaving eligibility and
salary questions to the person, and no scraping Indeed. Runs have no files or
connectors, so the skills work from the prompt alone. Results go to
`evals/results/`, which git ignores.
