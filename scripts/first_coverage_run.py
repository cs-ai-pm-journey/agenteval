"""Coverage run: all 50 golden set cases against the live Block 8 Copilot
deployment. Costs real money (~50 GPT-4o pipeline calls).
Run manually with:
    uv run python scripts/first_coverage_run.py
"""

import json
import time
from datetime import date

from agenteval.adapters.copilot import BlockEightCopilotAdapter
from agenteval.core import (
    load_golden_set, run_coverage,
    coverage_report, coverage_by_case_type, format_pct_ci,
)

GOLDEN_SET_PATH = "golden_sets/block_8_copilot/v1.jsonl"
ENDPOINT = "https://smart-reply-copilot.onrender.com/api/process"

scenarios = load_golden_set(GOLDEN_SET_PATH)
adapter = BlockEightCopilotAdapter(endpoint=ENDPOINT, timeout=30.0)

print(f"Running {len(scenarios)} scenarios against {ENDPOINT}...\n")

start = time.time()
results = run_coverage(adapter, scenarios)
duration_seconds = time.time() - start

cov = coverage_report(results)
by_type = coverage_by_case_type(results, scenarios)
latencies = sorted(r.agent_response.latency_ms for r in results)
p50 = latencies[len(latencies) // 2]
p95 = latencies[int(len(latencies) * 0.95)]

print(f"\n{'=' * 60}")
print(f"COVERAGE: {format_pct_ci(cov)}  (n={cov['n']})")
for case_type, rep in by_type.items():
    print(f"  {case_type}: {format_pct_ci(rep)} (n={rep['n']})")
print(f"Duration: {duration_seconds:.0f}s | latency p50={p50:.0f}ms p95={p95:.0f}ms")
print(f"{'=' * 60}\n")

for result in results:
    status = "PASS" if result.passed else "FAIL"
    scenario = next(s for s in scenarios if s.id == result.scenario_id)
    print(f"[{status}] {result.scenario_id} ({scenario.case_type.value})")
    print(f"    expected: {scenario.expected_output}")
    print(f"    actual:   {result.agent_response.output}")
    conf = result.agent_response.confidence
    print(f"    confidence: {conf:.3f} | latency: {result.agent_response.latency_ms:.0f}ms")
    print()

output_path = f"results/block8/coverage_{date.today().isoformat()}.json"
with open(output_path, "w") as f:
    json.dump({
        "run_id": f"coverage-{date.today().isoformat()}",
        "adapter": "BlockEightCopilotAdapter",
        "endpoint": ENDPOINT,
        "golden_set_version": "v1",
        "total_scenarios": cov["n"],
        "results_summary": {
            "pass_rate": cov["accuracy"],
            "ci_95": [cov["ci_low"], cov["ci_high"]],
            "by_case_type": {
                ct: {"pass_rate": r["accuracy"], "ci_95": [r["ci_low"], r["ci_high"]], "n": r["n"]}
                for ct, r in by_type.items()
            },
        },
        "duration_seconds": duration_seconds,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "individual_results": [
            {
                "scenario_id": r.scenario_id,
                "passed": r.passed,
                "expected": next(s for s in scenarios if s.id == r.scenario_id).expected_output,
                "actual": r.agent_response.output,
                "confidence": r.agent_response.confidence,
                "latency_ms": r.agent_response.latency_ms,
            }
            for r in results
        ],
    }, f, indent=2)

print(f"Saved to {output_path}")
