# Wednesday: First Real Coverage Run — Notes

Exploratory run, not the formal Saturday coverage report. Captured here so
the findings survive past terminal scrollback and feed directly into
`block8_analysis.md` later.

## Setup

- Golden Set v1, partial: 20 cases (12 normal, 6 ambiguous, 2 should-abstain)
- Target: live Render deployment, `https://smart-reply-copilot.onrender.com/api/process`
- Adapter: `BlockEightCopilotAdapter`, k=1 (pass@1 only — no pass^k yet, that's Thursday)
- Run script: `scripts/first_coverage_run.py`

## Headline Results

**17/20 passed (85.0%)** — but the aggregate number hides the real story. By case type:

| Case type | Pass rate |
|---|---|
| Normal | 12/12 (100%) |
| Ambiguous | 5/6 (83%) |
| Should-abstain | 0/2 (0%) |

## Findings

### 1. Copilot is confidently wrong, not just wrong (the headline finding)

On both should-abstain cases (empty ticket, gibberish), Copilot returned a
category (both "General Inquiry") with confidence in the **0.82-0.85** range
— statistically indistinguishable from its confidence on clear-cut normal
cases (0.867-0.933). On `b8-ambig-001`, the one genuine-boundary case it
disagreed with our committed label on, it returned its *highest* confidence
of the entire run: **0.933**.

Conclusion: Copilot's confidence score does not discriminate between "this
input is genuinely clear," "this input is a contested boundary case," and
"this input is not a real support ticket at all." A single scalar
confidence in the high 0.8s-0.9s shows up regardless of which of those three
is actually true. This is the central evidence for the "What pass@1 hides"
write-up — confidence alone cannot be trusted as a reliability signal for
this system.

### 2. `b8-ambig-001` (undo-depth case): legitimate two-sided disagreement

We committed to `Feature Request` (bounded undo history as deliberate
design tradeoff); Copilot classified it `Bug Report` (user-reported broken
behavior). Both readings are defensible — this is the boundary case working
as intended, not a system defect. Worth citing in the analysis doc as a
concrete example of genuine inter-annotator-style disagreement, not folded
into "failures" without this context.

### 3. Cold-start latency outlier — operational note for Saturday

`b8-normal-001` (the first call of the run) took **28,400ms**. Every other
call in the run landed between **3,800ms and 8,000ms**. Near-certain cause:
Render's free tier sleeps the service after idle time and pays a ~20-25s
wake-up penalty on the first request after a gap; the service then stayed
warm for the rest of the run.

Action for Saturday: either (a) issue one throwaway warm-up call before
starting the officially timed coverage/reliability runs, or (b) keep the
cold-start call and report it explicitly as a documented cost of free-tier
hosting rather than silently averaging it into latency stats. Decide before
Saturday's Block 1 starts — don't let it quietly skew a mean or p95.

## Open Threads for Later in the Week

- Thursday: does Copilot's category choice on `b8-ambig-001` stay
  consistent across a pass^k=8 rerun, or does it flip between Bug Report
  and Feature Request? Flip-flopping would be strong evidence of genuine
  model-level uncertainty on this boundary despite the high confidence
  score reported once.
- Friday/Saturday: cost estimation still needs a token-count heuristic
  approach — Copilot's API response has no usage/cost data, confirmed via
  Codex's read-only investigation of the repo.
