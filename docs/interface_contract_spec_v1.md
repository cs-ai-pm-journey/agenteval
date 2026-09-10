# agenteval Interface Contract — v1

## Purpose

agenteval is a language-agnostic evaluation harness. It scores agents over standardized transports (HTTP or CLI), never in-process, and validates its own scoring against independent human judgment rather than trusting either a simple matcher or an LLM judge unverified. This document specifies the contract any agent must satisfy to be evaluated by agenteval, and the contract the evaluation pipeline itself follows.

## Design Principles

**Out-of-process by default.** The harness communicates with agents over HTTP or CLI, never through direct imports. This choice makes agenteval language-agnostic — a Node.js agent, a Python agent, and a Rust agent are all evaluated identically. The tradeoff: added transport overhead per call (network latency for HTTP, subprocess spawn cost for CLI). This overhead is measured and reported separately from agent-internal latency where possible.

**Pydantic-enforced schemas.** All scenarios and results are validated at the boundary using Pydantic v2 models. This prevents malformed data from silently propagating through the evaluation pipeline and gives clear error messages when contracts are violated. Downstream evaluation code never sees raw dicts — it always operates on validated models.

**Required labeling rationale.** Every scenario in a golden set requires a `labeling_rationale` field (minimum 20 characters). This is not decorative — the rationale defends the ground truth when a judge disputes a label, provides context for future golden set curation, and serves as interviewer-ready evidence for label decisions.

**No scorer is trusted unvalidated.** A deterministic field-matcher (`simple_match`) and an LLM judge (`Judge`) are both available, and neither is treated as ground truth on its own. The judge is validated against independent human labels using Cohen's kappa (`agenteval.kappa`) before its scores are used in any reported finding. See "Judge Validation" below — this is now a required step, not optional polish.

## Core Data Models

See `src/agenteval/scenario.py` for canonical definitions.

### Scenario

Represents one test case. Fields:

- `id` (str): unique identifier within the golden set
- `input` (dict): payload passed to the agent — shape is agent-specific
- `expected_output` (dict): the correct response for this input — specifies only the field(s) that matter for scoring; agents may legitimately return additional fields not listed here (see "Extra Fields" below)
- `case_type` (CaseType enum): normal, ambiguous, should_abstain, adversarial, or multi_intent
- `labeling_rationale` (str, min 20 chars): explanation of why expected_output is correct
- `tags` (list[str]): free-form labels for filtering and analysis
- `reliability_subset` (bool): if True, this scenario is included in pass^k runs

### AgentResponse

The standardized response returned by any adapter. Fields:

- `output` (dict): the agent's actual response, in whatever structure the agent produces
- `confidence` (Optional[float]): agent-reported confidence, if available
- `metadata` (dict): additional context (reasoning traces, raw responses, etc.)
- `latency_ms` (Optional[float]): time from adapter call to response

### ScenarioResult

The outcome of running one scenario one time. Fields:

- `scenario_id` (str): reference back to the source scenario
- `passed` (bool): did the agent produce the expected output, per `simple_match`?
- `agent_response` (AgentResponse): the actual response received
- `judge_reasoning` (Optional[str]): reserved for a judge's reasoning when integrated directly into a `ScenarioResult`
- `run_index` (int): 0 for pass@1 runs; 0 to k-1 for pass^k runs
- `cost_usd` (Optional[float]): API cost for this specific run, if tracked

**Known gap (disclosed, not silently carried forward):** `judge_reasoning` has existed on this model since v0, but as of this version nothing populates it. The actual Week 3 judge pipeline (`scripts/run_judge_scoring.py`) does not construct `ScenarioResult` objects — it reads a completed coverage run's JSON output directly, joins it against the golden set, and writes judge scores to a separate file (`results/block8/judge_scores.jsonl`). This works and is validated (see below), but it means the judge pipeline runs alongside `core.py`'s `ScenarioResult`-based flow rather than through it. Unifying these — either by having `run_coverage` optionally invoke the judge per-scenario and populate `judge_reasoning` directly, or by formally deprecating the field — is unresolved and should be decided before Block 11 reuses this harness, not discovered again from scratch.

### Extra Fields Convention

`expected_output` lists only the field(s) that matter for scoring. An agent's actual output may include additional fields beyond those (e.g. `tone`, `urgency` alongside `category`) without penalty — this is normal, expected agent behavior, not a defect. Both `simple_match` (`core.py`) and the judge prompt (`judge.py`) are required to follow this convention. This was violated once, by the judge prompt, before the convention was written down here: the original Week 3 Monday judge prompt penalized extra fields as errors, diverging from `simple_match`'s established behavior. It was caught by a 3-case smoke test before any real data was scored, fixed the same day, and is now stated explicitly as a contract requirement so it can't regress silently in either scorer.

## Adapter Contract

Adapters bridge between agenteval's Scenario contract and an agent's native interface. All adapters implement the same abstract interface:

```python
class AgentAdapter(ABC):
    @abstractmethod
    def evaluate(self, scenario: Scenario) -> AgentResponse:
        ...
```

Two concrete adapters are provided:

- **HTTPAdapter** — POSTs the scenario input to a configured endpoint, parses JSON response into AgentResponse
- **CLIAdapter** — Spawns a subprocess, pipes scenario input via stdin, parses stdout JSON into AgentResponse

Agent-specific adapters (e.g., `BlockEightCopilotAdapter`) extend these base adapters and handle any per-agent request/response translation.

## Judge Contract

`src/agenteval/judge.py` defines the LLM-as-judge implementation.

### Judgment

The result of one judge call. Fields:

- `score` (JudgmentScore enum): `pass`, `partial`, or `fail` — three-point, not binary
- `reasoning` (str, min 20 chars): the judge's stated reasoning for the score
- `cost_usd` (Optional[float]): computed from the underlying API call's token usage
- `raw_response` (Optional[str]): the unparsed model output, kept for debugging parse failures

### Judge

Constructed with a `model` (default `claude-sonnet-5`) and `max_retries`. Requires `ANTHROPIC_API_KEY` in the environment (loaded via `.env`, never committed — see `.gitignore`). Deliberately cross-model: the judge runs on Claude while the system under test (Block 8 Copilot) runs on GPT-4o, so the judge doesn't share training data or failure modes with the system it's scoring. `judge()` raises `JudgeParseError` (not a silent fallback) if the model's output can't be parsed as valid JSON after retries — a judge call that can't be trusted must fail loudly, not degrade quietly into a default score.

### Judge Validation (required, not optional)

A judge's agreement with a deterministic matcher on cases with little room to diverge (e.g. single unambiguous categorical labels) is not evidence the judge is trustworthy — it may just mean the judge is behaving consistently with its own instructions. Real validation requires an independent signal: human labels produced without seeing the judge's scores, compared via Cohen's kappa (`src/agenteval/kappa.py`, implemented directly rather than via a new dependency).

Process, as run for Block 8 in Week 3:

1. `scripts/build_labeling_worksheet.py` — generates a worksheet joining input/expected/rationale/actual output per scenario, deliberately excluding the judge's own score, for a human to label blind
2. Human fills in `human_score` (`pass`/`partial`/`fail`) and `human_reasoning` per scenario
3. `scripts/finalize_human_labels.py` — validates the filled worksheet (rejects blank scores, invalid values, missing scenarios) before converting it to `human_labels.jsonl`; writes nothing if validation fails
4. `scripts/judge_validation.py` — computes overall Cohen's kappa, a confusion matrix, per-case-type agreement, and writes every individual disagreement (both sides' reasoning) to `results/block8/disagreements.jsonl` and a full report to `docs/judge_validation_report.md`

This process caught a real labeling error in step 2 before it reached a report (all `should_abstain` cases initially mislabeled `pass` despite reasoning arguing `fail`) — kappa moved from 0.060 to 0.654 once corrected. The validation scripts don't just compute a number; the worksheet/finalize split exists specifically to make a mistake like that visible and fixable before it's load-bearing.

## Extension Points

To add a new adapter type (e.g., gRPC, WebSocket):

1. Subclass `AgentAdapter`
2. Implement `evaluate(scenario) -> AgentResponse`
3. Place in `src/agenteval/adapters/`

To wire in a new agent using an existing transport:

1. Subclass the appropriate transport adapter (HTTPAdapter or CLIAdapter)
2. Override `evaluate` to handle any request/response translation between the agent's native format and AgentResponse
3. Place in `src/agenteval/adapters/`

To validate a judge against a new golden set:

1. Run `build_labeling_worksheet.py` against the golden set and coverage run
2. Get independent human labels (blind to judge scores)
3. Run `finalize_human_labels.py`, then `judge_validation.py`
4. Do not report judge scores as findings until this has run and kappa is disclosed alongside the results

## Version

v1 — tagged end of Week 3, after the judge was built, validated against independent human labels, and both scorers' extra-fields convention was made explicit. Supersedes v0 (initial draft, Week 2). The `ScenarioResult.judge_reasoning` integration gap noted above is the known open item carried into Block 11 planning, not resolved here.
