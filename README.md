# agenteval

A language-agnostic evaluation harness for AI agents. It scores an agent's
outputs against a golden set of labeled scenarios, at pass@1 (does it work
once) and pass^k (does it work reliably, every time), with Wilson confidence
intervals so results read as "94.0% (95% CI: 83.0%-98.0%)" instead of a bare
percentage that hides how small your sample actually is.

## Why this exists

Two failure modes this tool is built to catch, that a simple accuracy
number hides:

1. **Reliability collapse under repetition.** A system that passes a test
   case 6 times out of 8 isn't "mostly reliable" — it's a coin flip your
   users eventually lose. `pass^k` only counts a scenario as passing if
   *every* one of k runs succeeds.
2. **Confident failure on cases that should get no confident answer at all.**
   A golden set needs `should_abstain` cases as first-class citizens, not an
   afterthought — a system that never once declines to answer is a design
   gap, not a calibration nuance.

## Install

```bash
uv sync
```

## The contract

`agenteval` never calls an agent in-process. Every agent is reached through
an **adapter** that implements one method:

```python
class AgentAdapter(ABC):
    @abstractmethod
    def evaluate(self, scenario: Scenario) -> AgentResponse:
        ...
```

`Scenario` and `AgentResponse` are the fixed contract on either side of that
call (see `src/agenteval/scenario.py`). Two adapters ship out of the box:

- `HTTPAdapter` — POSTs `scenario.input` as JSON to an endpoint.
- `CLIAdapter` — pipes `scenario.input` as JSON to a subprocess's stdin.

Both expect the target to speak `agenteval`'s native shape
(`{"output": {...}, "confidence": ..., "metadata": {...}}`). If your agent
speaks something else — like Block 8 Copilot's own
`{"classification": {...}, "tone": {...}, "response": {...}}` shape — write
a thin translating adapter instead. `src/agenteval/adapters/copilot.py` is
the reference implementation:

```python
class BlockEightCopilotAdapter(HTTPAdapter):
    """Translates between agenteval's contract and Copilot's native
    POST /api/process request/response shape."""

    def evaluate(self, scenario: Scenario) -> AgentResponse:
        response = requests.post(
            self.endpoint,
            json={"ticketText": scenario.input.get("text", "")},
            timeout=self.timeout,
        )
        data = response.json()
        return AgentResponse(
            output={"category": data["classification"]["category"], ...},
            confidence=data.get("overallConfidence"),
            ...
        )
```

That's the whole extension point: subclass `HTTPAdapter` or `CLIAdapter` (or
`AgentAdapter` directly for something more exotic), translate the target's
native format into `AgentResponse`, done. The harness scores it identically
to every other adapter.

## Golden sets

A golden set is a `.jsonl` file, one `Scenario` per line:

```json
{"id": "b8-normal-001", "input": {"text": "..."}, "expected_output": {"category": "Bug Report"}, "case_type": "normal", "labeling_rationale": "...", "tags": [...], "reliability_subset": false}
```

`case_type` is one of `normal`, `ambiguous`, `should_abstain`, `adversarial`,
`multi_intent` — see `docs/golden_set_origin.md` for the design rationale and
target distribution. `labeling_rationale` is required (min 20 characters):
every expected answer needs a stated reason, so the label defends itself
later.

## Running it

```python
from agenteval.core import load_golden_set, run_coverage, run_reliability, coverage_report, reliability_report, format_pct_ci
from agenteval.adapters.copilot import BlockEightCopilotAdapter

scenarios = load_golden_set("golden_sets/block_8_copilot/v1.jsonl")
adapter = BlockEightCopilotAdapter(endpoint="https://your-agent/api/process", timeout=60.0)

# pass@1 across the full set
results = run_coverage(adapter, scenarios)
print(format_pct_ci(coverage_report(results)))

# pass^k across just the reliability subset
subset = [s for s in scenarios if s.reliability_subset]
results_by_scenario = run_reliability(adapter, subset, k=8)
print(format_pct_ci(reliability_report(results_by_scenario), key="pass_k_rate"))
```

`scripts/first_coverage_run.py` and `scripts/reliability_run.py` are the
real, runnable versions of the above, including Wilson CIs, per-case-type
breakdown, JSON output, and resilience against the target system erroring
or timing out mid-run — a single failed call is recorded as a failed
result, not a crashed harness.

## Worked example: Block 8 Copilot

Everything above is demonstrated end to end against a real, live system —
not a stub. See `docs/block8_analysis.md` for the actual results: 66.0%
pass@1 on 50 cases, 35.7% pass^8 on the 28-case reliability subset, and the
finding that most of that gap isn't randomness — it's a system with
literally no should-abstain path, confidently misclassifying prompt
injection and PII-exfiltration attempts at the same confidence it gives
correct answers.

## Docs

- `docs/golden_set_origin.md` — why the golden set was rebuilt from scratch, and its target case-type distribution.
- `docs/block8_analysis.md` — the real evaluation results and analysis against Block 8 Copilot.
- `docs/rejection_log.md` — what was deliberately left to deterministic code instead of a model, and why.
- `docs/interface_contract_spec_v0.md` — the formal adapter interface contract.

## Status

Actively built as part of an evaluation-methodology learning block. Golden
Set v1 is at 50 cases. Reliability subset covers ambiguous, should-abstain,
and multi-intent case types (28 cases). Not yet published as an installable
package for others to run against their own agents — that's tracked
separately.
