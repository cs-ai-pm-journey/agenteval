# agenteval Interface Contract — v0

## Purpose

agenteval is a language-agnostic evaluation harness. It scores agents over standardized transports (HTTP or CLI), never in-process. This document specifies the contract any agent must satisfy to be evaluated by agenteval.

## Design Principles

**Out-of-process by default.** The harness communicates with agents over HTTP or CLI, never through direct imports. This choice makes agenteval language-agnostic — a Node.js agent, a Python agent, and a Rust agent are all evaluated identically. The tradeoff: added transport overhead per call (network latency for HTTP, subprocess spawn cost for CLI). This overhead is measured and reported separately from agent-internal latency where possible.

**Pydantic-enforced schemas.** All scenarios and results are validated at the boundary using Pydantic v2 models. This prevents malformed data from silently propagating through the evaluation pipeline and gives clear error messages when contracts are violated. Downstream evaluation code never sees raw dicts — it always operates on validated models.

**Required labeling rationale.** Every scenario in a golden set requires a `labeling_rationale` field (minimum 20 characters). This is not decorative — the rationale defends the ground truth when a judge disputes a label, provides context for future golden set curation, and serves as interviewer-ready evidence for label decisions. A golden set without rationales is a golden set that cannot be defended.

## Core Data Models

See `src/agenteval/scenario.py` for canonical definitions.

### Scenario

Represents one test case. Fields:

- `id` (str): unique identifier within the golden set
- `input` (dict): payload passed to the agent — shape is agent-specific
- `expected_output` (dict): the correct response for this input
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
- `passed` (bool): did the agent produce the expected output?
- `agent_response` (AgentResponse): the actual response received
- `judge_reasoning` (Optional[str]): populated when using LLM-as-judge (Week 3)
- `run_index` (int): 0 for pass@1 runs; 0 to k-1 for pass^k runs
- `cost_usd` (Optional[float]): API cost for this specific run, if tracked

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

## Extension Points

To add a new adapter type (e.g., gRPC, WebSocket):

1. Subclass `AgentAdapter`
2. Implement `evaluate(scenario) -> AgentResponse`
3. Place in `src/agenteval/adapters/`

To wire in a new agent using an existing transport:

1. Subclass the appropriate transport adapter (HTTPAdapter or CLIAdapter)
2. Override `evaluate` to handle any request/response translation between the agent's native format and AgentResponse
3. Place in `src/agenteval/adapters/`

## Version

v0 — initial draft, subject to revision through Week 2 build. v1.0 will be tagged at end of Week 2 Sunday after adapters and reporting are complete.