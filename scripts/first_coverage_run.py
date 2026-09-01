"""First real coverage run: all 20 golden set cases against the live
Block 8 Copilot deployment. Costs real money (~20 GPT-4o pipeline calls).
Run manually with:
    uv run python scripts/first_coverage_run.py
"""

from agenteval.adapters.copilot import BlockEightCopilotAdapter
from agenteval.core import load_golden_set, run_coverage

GOLDEN_SET_PATH = "golden_sets/block_8_copilot/v1.jsonl"
ENDPOINT = "https://smart-reply-copilot.onrender.com/api/process"

scenarios = load_golden_set(GOLDEN_SET_PATH)
adapter = BlockEightCopilotAdapter(endpoint=ENDPOINT, timeout=30.0)

print(f"Running {len(scenarios)} scenarios against {ENDPOINT}...\n")

results = run_coverage(adapter, scenarios)

passed = sum(1 for r in results if r.passed)
total = len(results)

print(f"\n{'=' * 60}")
print(f"COVERAGE RESULTS: {passed}/{total} passed ({passed / total:.1%})")
print(f"{'=' * 60}\n")

for result in results:
    status = "PASS" if result.passed else "FAIL"
    scenario = next(s for s in scenarios if s.id == result.scenario_id)
    print(f"[{status}] {result.scenario_id} ({scenario.case_type.value})")
    print(f"    expected: {scenario.expected_output}")
    print(f"    actual:   {result.agent_response.output}")
    print(f"    confidence: {result.agent_response.confidence:.3f} | latency: {result.agent_response.latency_ms:.0f}ms")
    print()