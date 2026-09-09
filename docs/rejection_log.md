# Rejection Log

One entry per block: something deliberately left to deterministic code
instead of a model, or a case explicitly not automated. This is the
interview opening move -- knowing what NOT to hand to an LLM is the
differentiating judgment, not a footnote.

## B10 -- Should-abstain routing in Block 8 Copilot

**What I'd move to deterministic code:** the rejection/abstain path.

**Why:** the golden set's should_abstain cases (empty input, gibberish,
legal advice, medical questions, prompt injection, PII exfiltration
disguised as account recovery, fraud, discretionary exceptions) scored
0/10 at pass@1 and a fully deterministic 0/80 across pass^8 (10 cases x
8 runs each). That's not a calibration problem a better model closes --
it's evidence the system has no rejection path at all, and confidence
scores on those failures (0.817-0.933) were indistinguishable from
confidence on cases it got right, so the model itself gives no signal
you could threshold on to catch this after the fact.

**The fix, if built:** a deterministic pre-classifier gate ahead of the
LLM call -- pattern-match for empty/gibberish input, known prompt-
injection markers, and PII-disclosure requests, and route those straight
to human escalation regardless of what the downstream model would have
said. This only works if it runs *before* the categorical classifier,
not as a post-hoc filter on its output.

**Open question this doesn't resolve:** whether "abstain" is even in
Copilot's output schema today. If it isn't, 0% wasn't a failure to
abstain -- it was guaranteed by the system's design before a single
ticket was sent. That's a different diagnosis (spec gap, not model
gap) and would need checking Copilot's actual category list/prompt
before claiming the fix above is even the right one.

**Resolved (2026-09-03):** checked `classifier.js` in
`cs-ai-pm-journey/Block-8` directly -- the prompt hard-codes exactly five
categories with no abstain/escalate option. Spec gap confirmed, not model
gap. The fix above (a deterministic gate ahead of the LLM call) stands.

**Status:** documented, not built. Treating this as a deliberate,
scoped decision rather than folding an unplanned Copilot rebuild into
B10's actual deliverable (the harness itself).
