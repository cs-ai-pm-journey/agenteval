# Second Worked Example: expense_router

Everything in this repo so far has been demonstrated against one real system:
Block 8 Copilot. That's not enough to claim the harness itself is
language-agnostic and agent-agnostic — it's only proof that it works against
*that* one HTTP-speaking, LLM-backed classifier. This example exists to
close that gap: a second agent, deliberately different on every axis that
matters, run through the same harness with no code changes to `core.py`,
`scenario.py`, or the CLI adapter.

## What's different from the Copilot example, on purpose

- **Transport:** CLI (stdin/stdout JSON), not HTTP. `CLIAdapter` had never
  been exercised against a real agent before this — only Copilot's
  `HTTPAdapter` path had.
- **No translating adapter needed.** `examples/expense_router/agent.py`
  speaks agenteval's native contract (`{"output": ..., "confidence": ...,
  "metadata": ...}`) directly, so `CLIAdapter` is used unmodified. Contrast
  with `BlockEightCopilotAdapter`, which exists specifically to translate
  Copilot's own response shape into that contract. Together, the two
  examples cover both cases the adapter pattern is meant to handle: an agent
  that already speaks your contract, and one that doesn't.
- **Not an LLM.** `agent.py` is a deterministic, rule-based keyword
  classifier — zero API cost, zero network dependency, instant. This is
  also why `pass^k` reliability testing was actually run here (k=8, on the
  10-case reliability subset) rather than skipped: a non-LLM agent should
  be perfectly stable across repeated runs, and the point of running it
  anyway is to demonstrate that, not just assert it. Result: 9 stable-pass,
  1 stable-fail, 0 flaky — confirmed, not assumed.
- **Built with the fix Block 8 needed.** `docs/block8_analysis.md`'s "What
  I'd Change" section recommended a deterministic pre-classifier gate for
  should-abstain and adversarial cases, built as explicit code rather than
  left to the model's judgment. `expense_router` is that recommendation,
  built for real: an explicit `Needs Human Review` category, a dollar-amount
  policy threshold checked before any keyword matching, and instruction-
  injection marker detection checked first of all.

## Domain

A rule-based expense-report categorizer. Given a line-item description, it
assigns one of five categories (`Travel`, `Meals & Entertainment`,
`Software & Subscriptions`, `Office Supplies`, `Equipment`) or escalates to
`Needs Human Review` when the input is empty, gibberish, over a $5,000
policy threshold, out of scope for the five categories, or shows signs of
an instruction-injection attempt.

## Results (Golden Set v1, 16 cases)

Coverage (pass@1): **14/16 = 87.5%** (95% CI: 64.0%–96.5%)

| case_type | pass rate | n |
|---|---|---|
| normal | 83% | 6 |
| ambiguous | 100% | 2 |
| should_abstain | 100% | 4 |
| multi_intent | 50% | 2 |
| adversarial | 100% | 2 |

Reliability (pass^8, n=10 reliability-subset cases): 9 stable-pass, 1
stable-fail, 0 flaky.

## The finding that matters: should_abstain and adversarial went from 0% to 100%

Block 8 Copilot scored 0/10 on should_abstain cases — a fully deterministic
zero, because its output schema had no abstain option at all. Copilot was
never tested against adversarial-style prompt-injection cases directly
(Block 8's golden set didn't include that case type), but the same
structural gap — no code path that could refuse to answer — would apply
identically.

`expense_router` scores 4/4 on should_abstain and 2/2 on adversarial. Not
because it's a smarter system — it's a much dumber one, keyword matching
with no learning at all — but because it has an explicit `Needs Human
Review` branch and a policy gate that runs *before* categorization is
attempted, exactly the fix recommended for Copilot. This is the causal
story the numbers are meant to support, not just decoration: a system that
CAN decline to answer, checked deterministically before any model or rule
engine gets to guess, categorically outperforms one that can't — regardless
of how sophisticated the underlying classifier is on the cases it does
attempt.

## The finding that keeps this honest: it isn't a perfect system either

87.5%, not 100%, and the two misses are real, not manufactured for
narrative balance:

**`exp-normal-006`** ("Monthly hosting bill for our staging environment,
$95") — a human reviewer finds this unambiguously `Software &
Subscriptions`. The agent returns `Needs Human Review` because its keyword
list checks for the literal phrase "cloud hosting" and this text says
"hosting bill" instead. This is a pure keyword-coverage gap, the exact
failure mode a rule-based system is structurally prone to and an LLM-backed
one generally isn't — a useful contrast with Copilot's failures, which were
about missing code paths, not missing vocabulary.

**`exp-multi-002`** ("Team dinner and then we expensed the Uber home too,
$140") — the golden set's rationale treats the dinner as the dominant
intent (`Meals & Entertainment`); the agent returns `Travel` because its
keyword list checks `Travel` (which matches "Uber") before it ever checks
`Meals & Entertainment`. This is a rule-ordering bug, not a judgment
failure — the agent doesn't weigh which purchase is "primary," it just
takes the first keyword match in a fixed priority list.

**A real bug was also caught and fixed before this golden set was
finalized**, worth disclosing in the same spirit as `block8_analysis.md`'s
methodology-lapse section: the original amount-extraction regex for the
$5,000 policy threshold matched a stray comma in normal sentence
punctuation (e.g. "Chicago, $9,500") before it ever reached the actual
dollar figure, silently failed to parse it, and let the threshold check
never fire. `"Client dinner in Chicago, $9,500"` was miscategorized as
`Meals & Entertainment` instead of being escalated. Caught by hand-testing
draft golden-set cases against the agent before writing down expected
answers, fixed the same session, confirmed via `exp-abstain-003`. A policy
gate with a silent bug in it is worse than no gate at all, because it
creates false confidence that large expenses are being caught -- exactly
the kind of thing this harness, and the discipline of hand-verifying
expected outputs before trusting them, exists to catch.

## Files

- `examples/expense_router/agent.py` — the CLI agent
- `golden_sets/expense_router/v1.jsonl` — 16-case golden set, all five case types represented
- `scripts/second_worked_example_run.py` — runs coverage + reliability, writes results
- `results/expense_router/coverage_2026-09-10.json`, `results/expense_router/reliability_2026-09-10.json` — raw output
