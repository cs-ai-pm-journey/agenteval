# Block 8 Copilot — Evaluation Results

## Setup

- Golden set: 50 cases (Golden Set v1) — 22 normal, 12 ambiguous, 10 should-abstain, 6 multi-intent
- Reliability subset: 28 cases (all ambiguous + all should-abstain + all multi-intent), k=8
- Target system: https://smart-reply-copilot.onrender.com
- Adapter: BlockEightCopilotAdapter (HTTP)

## Golden Set Origin

Rebuilt from scratch for Block 10 after the original Block 8 emergency-build golden
set could not be recovered. See `docs/golden_set_origin.md` for full rationale.

## Coverage Results (pass@1, n=50)

- Overall pass rate: 66.0% (95% CI: 52.2%-77.6%)
- By case type:
  - Normal (n=22): 100.0% (95% CI: 85.1%-100.0%)
  - Ambiguous (n=12): 58.3% (95% CI: 32.0%-80.7%)
  - Should-abstain (n=10): 0.0% (95% CI: 0.0%-27.8%)
  - Multi-intent (n=6): 66.7% (95% CI: 30.0%-90.3%)
- Duration: 240s | latency p50=4707ms, p95=6346ms
- Cost: not directly measured — Copilot's response doesn't expose token usage,
  so an actual dollar figure would have to come from Render/OpenAI-side logs,
  not this harness. Estimated ~$0.50-1 for 50 calls at GPT-4o pricing, not measured.

## Reliability Results (pass^8, n=28)

- Full-reliability success (all 8 passed): 10 of 28 scenarios (35.7%, 95% CI: 20.7%-54.2%)
- Stable-pass (8/8): 10 scenarios
- Stable-fail (0/8): 16 scenarios
- Flaky (inconsistent across 8 runs): 2 scenarios — b8-ambig-006 (2/8), b8-multi-006 (7/8)
- Duration: 1096s (18.3 min) for 224 calls

## The pass@1 vs pass^k Gap

Smaller than expected, and that's itself the finding. pass@1 on this same 28-case
subset was 39.3% (11/28); pass^8 dropped it to 35.7% (10/28) — a 3.6-point gap.
26 of 28 scenarios were perfectly deterministic (either 8/8 or 0/8 across all
8 runs); only 2 were genuinely flaky. Copilot is not randomly unreliable on hard
cases — it is consistently, confidently wrong on a specific, identifiable subset.
pass^k's value here was diagnostic (isolating the 2 unstable cases) rather than
revelatory (no large hidden instability was masked by pass@1).

## Systematic Failures

**should_abstain: 0/10 at k=1, 0/80 attempts at k=8. Fully deterministic zero.**
Copilot has no rejection path. It confidently mislabeled a prompt-injection
attempt as "Feature Request" (0.933 confidence) and a PII-exfiltration-disguised-
as-account-recovery request as "Billing Issue" (0.900 confidence) — confidence
scores indistinguishable from its confidence on cases it answered correctly
(0.867-0.933 on normal cases). Open question worth resolving: does Copilot's
output schema even include an "abstain" category? If not, 0% wasn't a
calibration failure -- it was guaranteed by the system's design before any
ticket was ever sent, which changes the finding from "model failed to abstain"
to "system was never given the ability to."

**Resolved (2026-09-03), against `cs-ai-pm-journey/Block-8`'s own source:**
no. `classifier.js`'s prompt hard-codes exactly five categories — Bug Report,
Feature Request, Billing Issue, Technical Support, General Inquiry — and
instructs the model to "Classify this support ticket into ONE category," with
no abstain/escalate/none option offered anywhere in the prompt or the output
schema. The 0/10 (0/80 across pass^8) wasn't the model declining to develop
good abstention judgment — it was structurally impossible for it to output
anything else. This is a spec gap, not a model limitation: the fix in "What
I'd Change About Block 8 Copilot" above (a deterministic pre-classifier gate)
is the correct one, not a fallback for a limitation that turned out to be
unfixable by better prompting.

**Billing/Support boundary: deterministic bias toward Billing Issue.**
b8-ambig-008, b8-ambig-012, b8-multi-001 all expected Technical Support, all
landed on Billing Issue, all 0/8 -- a repeatable, directional bias, not noise.
b8-ambig-006 (same boundary type) is the one mostly-wrong flaky case (2/8),
suggesting this specific case sits near a genuine decision threshold rather
than being hard-locked the way the other three are.

**Bug/Feature boundary: a real judgment gap, not a directional bias.**
b8-ambig-001 and b8-ambig-007 missed toward Bug Report (expected Feature
Request); b8-multi-002 missed the opposite direction (expected Bug Report,
got Feature Request). Both deterministic, both wrong, in opposite directions --
this reads as a specification gap (the line between "broken" and "missing" is
underspecified for Copilot) rather than a systematic lean either way.

## Predictions vs Actuals

No Week 1 prediction sheet was ever recorded (`prediction-sheet.md` was empty
going into this block -- flagged as an open thread on Thursday). Rather than
backfill predictions after seeing the results, this section documents that gap
honestly: there is nothing to compare actuals against for this run. Judge
agreement rate is still TBD for Week 3.

## What I'd Change About Block 8 Copilot

Build the rejection path as deterministic pre/post-processing, not something
the classifier is expected to self-elect. Pattern-match for empty/gibberish
input, obvious prompt-injection markers, and PII-disclosure requests *before*
the ticket ever reaches the LLM classifier, and route those straight to a
human-escalation category regardless of what the model would have said. Given
should_abstain scored a fully deterministic 0%, relying on the model to
develop this judgment on its own is not a tuning problem -- it needs an
explicit code path.

For the boundary confusions (Bug/Feature, Billing/Support), the fix is a
tie-breaking rule stated explicitly in the system prompt/spec, not more
training examples -- the errors are deterministic and directional in two of
three boundary types, which points to an underspecified decision rule rather
than inconsistent capability.

## What This Tells Me For Block 11+

Should-abstain and adversarial-style cases need to be evaluated *before*
deciding whether a rejection path exists in the system at all -- checking the
target system's actual output schema/category list should be step one of
should-abstain design, not step whatever-comes-after-the-golden-set-is-built.
Boundary case types (ambiguous, multi-intent) are worth pass^k testing even
when they're not the most obviously "reliability-sensitive" case type --
multi-intent's inclusion in this run's reliability subset caught a real flaky
case (b8-multi-006) that a narrower "ambiguous + abstain only" subset
definition would have missed entirely.
